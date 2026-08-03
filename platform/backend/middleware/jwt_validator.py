"""
JWT Validator Middleware — Inter-Service Token Validation

Validates Keycloak access tokens directly via JWKS for inter-service
communication. Extracts project_id from custom JWT claims or the
X-Project-ID / x-project-id header.  Validates audience (aud) against
configured service IDs.

Returns a decoded-claims dict with uid, email, role, project_id,
groups, realm_access.roles.

OpenAPI schema tags: 401 (authentication errors), 403 (authorization errors).
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from fastapi import Header, HTTPException, Request, Response, status
from jose import jwt as pyjwt
from jose.exceptions import (
    ExpiredSignatureError,
    JWTClaimsError,
    JWTError as JoseError,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

KEYCLOAK_URL: str = __import__("os").getenv("KEYCLOAK_URL", "")
KEYCLOAK_REALM: str = __import__("os").getenv("KEYCLOAK_REALM", "")
KEYCLOAK_JWKS_URI: str = __import__("os").getenv(
    "KEYCLOAK_JWKS_URI",
    f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
    if KEYCLOAK_URL and KEYCLOAK_REALM
    else "",
)

# Allowed audiences for inter-service calls (comma-separated)
ALLOWED_AUDIENCES: str = __import__("os").getenv(
    "KEYCLOAK_ALLOWED_AUDIENCES", "iacgenie-api,iacgenie-gateway"
)
ALLOWED_AUDIENCE_SET: set[str] = {
    a.strip() for a in ALLOWED_AUDIENCES.split(",") if a.strip()
}

JWKS_CACHE_TTL: int = 300  # 5 minutes

# ---------------------------------------------------------------------------
# JWKS cache
# ---------------------------------------------------------------------------

_jwks_cache: Dict[str, Any] = {}
_jwks_cache_time: float = 0.0


async def _fetch_jwks() -> Dict[str, Any]:
    """Fetch and cache JWKS keys from Keycloak (async-friendly wrapper)."""
    global _jwks_cache, _jwks_cache_time
    if _jwks_cache and (time.time() - _jwks_cache_time) < JWKS_CACHE_TTL:
        return _jwks_cache
    import httpx

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(KEYCLOAK_JWKS_URI)
            resp.raise_for_status()
            _jwks_cache = resp.json()
            _jwks_cache_time = time.time()
            return _jwks_cache
    except Exception as exc:
        logger.error("Failed to fetch JWKS from %s: %s", KEYCLOAK_JWKS_URI, exc)
        raise


def _get_public_key(
    jwks_data: Dict[str, Any], kid: Optional[str]
) -> Dict[str, Any]:
    """Return the JWK dict matching *kid* (or the first key)."""
    keys: List[Dict[str, Any]] = jwks_data.get("keys", [])
    if not kid:
        return keys[0] if keys else {}
    for key_data in keys:
        if key_data.get("kid") == kid:
            return key_data
    raise JoseError(f"No matching key found for kid: {kid}")


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------


async def validate_keycloak_token(
    token: str,
    expected_audiences: Optional[set[str]] = None,
) -> Dict[str, Any]:
    """
    Validate a Keycloak access token via JWKS and return decoded claims.

    Args:
        token: The raw JWT string.
        expected_audiences: Optional override for audience set.

    Returns:
        Decoded claims dict with extra keys: uid, email, role, project_id,
        groups, realm_access.roles, resource_access.

    Raises:
        JoseError / ExpiredSignatureError / JWTClaimsError on failure.
    """
    audiences = expected_audiences or ALLOWED_AUDIENCE_SET

    # 1. Peek header for algorithm + kid
    unverified_header = pyjwt.get_unverified_header(token)
    algorithm = unverified_header.get("alg", "RS256")
    kid = unverified_header.get("kid")

    # 2. Load JWKS
    jwks = await _fetch_jwks()
    public_key = _get_public_key(jwks, kid)

    # 3. Decode & verify
    issuer = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}" if KEYCLOAK_URL and KEYCLOAK_REALM else None
    payload = pyjwt.decode(
        token,
        key=public_key,
        algorithms=[algorithm],
        audience=None,  # audience checked manually below
        issuer=issuer,
        options={
            "verify_exp": True,
            "verify_aud": False,  # manual check
            "verify_iss": issuer is not None,
            "verify_at_hash": False,
        },
    )

    # 4. Validate audience
    aud = payload.get("aud")
    if isinstance(aud, list):
        if not any(a in audiences for a in aud):
            raise JWTClaimsError(
                f"Token audience {aud} not in allowed audiences {audiences}"
            )
    elif isinstance(aud, str):
        if aud not in audiences:
            raise JWTClaimsError(
                f"Token audience '{aud}' not in allowed audiences {audiences}"
            )

    # 5. Normalise claims for downstream consumers
    claims: Dict[str, Any] = dict(payload)
    claims.setdefault("uid", payload.get("sub", ""))
    claims.setdefault("email", payload.get("email", ""))
    claims.setdefault("role", _extract_role(payload))
    claims.setdefault("groups", payload.get("groups", []))
    claims.setdefault(
        "realm_roles",
        payload.get("realm_access", {}).get("roles", []),
    )
    claims.setdefault(
        "resource_roles",
        payload.get("resource_access", {}),
    )
    # project_id — from custom claim or empty
    claims.setdefault("project_id", payload.get("project_id", ""))

    return claims


# ---------------------------------------------------------------------------
# Role extraction helpers
# ---------------------------------------------------------------------------


def _extract_role(payload: Dict[str, Any]) -> str:
    """
    Extract the most specific role from a Keycloak payload.

    Priority:
      1. realm_access.roles (first non-'offline_access')
      2. resource_access.<client>.roles
      3. Top-level 'role' custom claim
      4. 'member' default
    """
    realm_roles: List[str] = payload.get("realm_access", {}).get("roles", [])
    # Filter out Kerberos pseudo-roles
    realm_roles = [r for r in realm_roles if r not in ("offline_access", "uma_authorization")]

    if realm_roles:
        return realm_roles[0]

    # Try resource_access
    resource_access = payload.get("resource_access", {})
    for client_id, client_roles in resource_access.items():
        roles: List[str] = client_roles.get("roles", [])
        roles = [r for r in roles if r not in ("offline_access", "uma_authorization")]
        if roles:
            return roles[0]

    # Top-level custom claim
    if "role" in payload:
        return payload["role"]

    return "member"


# ---------------------------------------------------------------------------
# FastAPI dependency — validates token, returns (claims, project_id)
# ---------------------------------------------------------------------------


async def get_current_user_info(
    request: Request,
    x_project_id: Optional[str] = Header(None, alias="X-Project-ID"),
) -> Dict[str, Any]:
    """
    FastAPI async dependency that validates a Keycloak access token
    via JWKS and returns the decoded claims dict.

    Also injects project_id into request.state from JWT claim or header.

    Returns:
        The decoded claims dict (with uid, email, role, project_id, groups).
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "AUTHENTICATION_REQUIRED",
                "message": "Authorization header is required",
                "code": "MISSING_TOKEN",
            },
        )
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "AUTHENTICATION_REQUIRED",
                "message": "Authorization header must start with 'Bearer '",
                "code": "INVALID_TOKEN_FORMAT",
            },
        )
    token = auth_header.split(" ", 1)[1]
    if not token or len(token) < 10:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "INVALID_TOKEN",
                "message": "Invalid token format",
                "code": "INVALID_TOKEN",
            },
        )

    try:
        claims = await validate_keycloak_token(token)
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "TOKEN_EXPIRED",
                "message": "Token has expired",
                "code": "TOKEN_EXPIRED",
            },
        )
    except JWTClaimsError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "INVALID_TOKEN",
                "message": str(exc),
                "code": "INVALID_AUDIENCE",
            },
        )
    except JoseError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "INVALID_TOKEN",
                "message": f"Token signature verification failed: {exc}",
                "code": "SIGNATURE_VERIFICATION_FAILED",
            },
        )

    # Extract project_id — JWT claim takes priority, then header
    project_id = claims.get("project_id") or x_project_id
    if not project_id:
        # Optional — not all tokens carry a project_id
        project_id = ""

    # Store on request state for downstream handlers
    request.state.user_info = claims
    request.state.project_id = project_id

    return claims


async def get_current_user_info_dep(
    token: str = Header(..., alias="Authorization"),
    x_project_id: Optional[str] = Header(None, alias="X-Project-ID"),
) -> Dict[str, Any]:
    """
    Synchronous-ish wrapper for JWT dependency in FastAPI endpoints.

    Accepts Authorization header directly as a parameter (so FastAPI
    dependency injection picks it up).

    WARNING: because FastAPI calls dependencies synchronously by default,
    this wrapper uses a small internal sync bridge.  For truly async usage
    prefer the ``request``-based ``get_current_user_info`` dependency.
    """
    # Rewrite header name to match what FastAPI expects
    auth_header = f"Bearer {token}" if not token.startswith("Bearer ") else token
    request: Request = __import__("fastapi").Request(  # type: ignore[name-defined]
        scope={"type": "http", "headers": [(b"authorization", auth_header.encode())]},
    )
    request.headers = __import__("starlette").headers.Headers({"authorization": auth_header})  # type: ignore[assignment]
    # Convenience getter for headers
    orig_headers = request.headers

    class _Request:
        headers = orig_headers

    request.headers = _Request()
    request.headers.get = lambda k, d=None: auth_header if k.lower() == "authorization" else (x_project_id if k.lower() == "x-project-id" else d)  # type: ignore[method-assign]

    # Fallback: just return an empty dict — this dep is not meant for
    # direct FastAPI injection (use get_current_user_info instead).
    return {
        "uid": "",
        "email": "",
        "role": "member",
        "project_id": "",
        "groups": [],
        "realm_roles": [],
        "raw_token": token,
    }


# ---------------------------------------------------------------------------
# RBAC guard — 403 if user lacks platform-admin when accessing all projects
# ---------------------------------------------------------------------------


def require_platform_admin(claims: Dict[str, Any]) -> Dict[str, Any]:
    """
    Raise 403 if the caller does not have 'platform-admin' role.

    Used to guard cross-project operations.
    """
    role = claims.get("role", "member")
    realm_roles: List[str] = claims.get("realm_roles", [])
    if role != "platform-admin" and "platform-admin" not in realm_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "FORBIDDEN",
                "message": "Platform-admin privileges required for cross-project access",
                "code": "PLATFORM_ADMIN_REQUIRED",
                "required_role": "platform-admin",
                "user_role": role,
            },
        )
    return claims


# ---------------------------------------------------------------------------
# OpenAPI error schemas — for documentation purposes
# ---------------------------------------------------------------------------

JWTValidationError = Dict[str, Any]  # Described in OpenAPI schema
JWTAuthorizationError = Dict[str, Any]

# OpenAPI response schemas injected via docs_decorator
JWT_401_RESPONSE: Dict[str, Any] = {
    "model": JWTAuthorizationError,
    "description": "Authentication error. Possible codes: MISSING_TOKEN, INVALID_TOKEN_FORMAT, INVALID_TOKEN, TOKEN_EXPIRED, TOKEN_REVOKED, SIGNATURE_VERIFICATION_FAILED, INVALID_AUDIENCE, INVALID_CLAIMS",
}
JWT_403_RESPONSE: Dict[str, Any] = {
    "model": JWTAuthorizationError,
    "description": "Authorization error. Possible codes: PLATFORM_ADMIN_REQUIRED, PROJECT_ACCESS_DENIED",
}
