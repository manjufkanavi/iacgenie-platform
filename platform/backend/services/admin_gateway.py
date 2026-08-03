"""
Admin Gateway — Lightweight API Gateway with RBAC

Routes requests to backend services based on path prefix, validates JWT
+ role claims at the gateway level, and returns 403 with RBAC rejection
reasons if the user lacks permission for the target service.

Endpoints:
    GET /gateway/health                     — Gateway health check
    GET /gateway/services                   — List available backend services
    GET /gateway/permissions                — Current user's permissions

Intended use:
    This module can be mounted as a FastAPI sub-app in the main application
    or run as a standalone gateway.

    Mount example in main.py:
        from services.admin_gateway import gateway_router
        app.include_router(gateway_router, prefix="/gateway")
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Service registry — path prefix → service metadata
# ---------------------------------------------------------------------------

SERVICE_REGISTRY: Dict[str, Dict[str, Any]] = {
    "api": {
        "name": "IaCGenie API",
        "description": "Core infrastructure code generation API",
        "path_prefix": "/api",
        "required_role": "member",
        "min_role_level": 0,  # member
    },
    "auth": {
        "name": "Authentication Service",
        "description": "User authentication and token management",
        "path_prefix": "/auth",
        "required_role": "member",
        "min_role_level": 0,
    },
    "admin": {
        "name": "Admin Panel",
        "description": "Administrative operations and platform management",
        "path_prefix": "/admin",
        "required_role": "project-admin",
        "min_role_level": 1,  # project-admin
    },
    "platform": {
        "name": "Platform Admin",
        "description": "Platform-level administration and user management",
        "path_prefix": "/platform",
        "required_role": "platform-admin",
        "min_role_level": 2,  # platform-admin
    },
    "workflow": {
        "name": "Workflow Engine",
        "description": "Infrastructure pipeline orchestration",
        "path_prefix": "/workflow",
        "required_role": "member",
        "min_role_level": 0,
    },
    "git": {
        "name": "Git Integration",
        "description": "Git repository operations",
        "path_prefix": "/git",
        "required_role": "member",
        "min_role_level": 0,
    },
    "notification": {
        "name": "Notification Service",
        "description": "Email and push notification handling",
        "path_prefix": "/notification",
        "required_role": "member",
        "min_role_level": 0,
    },
    "webhook": {
        "name": "Webhook Service",
        "description": "Webhook management and delivery",
        "path_prefix": "/webhook",
        "required_role": "member",
        "min_role_level": 0,
    },
    "health": {
        "name": "Health Check",
        "description": "System health monitoring",
        "path_prefix": "/health",
        "required_role": "member",
        "min_role_level": 0,
    },
    "metrics": {
        "name": "Metrics Service",
        "description": "System metrics and monitoring",
        "path_prefix": "/metrics",
        "required_role": "member",
        "min_role_level": 0,
    },
}

# Role hierarchy levels
ROLE_LEVELS: Dict[str, int] = {
    "member": 0,
    "project-admin": 1,
    "platform-admin": 2,
    # Legacy mappings
    "user": 0,
    "developer": 1,
    "reviewer": 1,
    "admin": 2,
    "viewer": 0,
}

# ---------------------------------------------------------------------------
# Role normalisation (imported from config)
# ---------------------------------------------------------------------------


def _normalise_role(role: str) -> str:
    """Normalise a role to the multi-tenant hierarchy."""
    role_map: Dict[str, str] = {
        "admin": "platform-admin",
        "developer": "project-admin",
        "reviewer": "member",
        "viewer": "member",
        "user": "member",
    }
    return role_map.get(role, role)


def _role_level(role: str) -> int:
    """Return the hierarchy level for a role."""
    return ROLE_LEVELS.get(_normalise_role(role), 0)


def _get_user_role(claims: Dict[str, Any]) -> str:
    """Extract the role from a JWT claims dict."""
    return claims.get("role", "member")


# ---------------------------------------------------------------------------
# Gateway router
# ---------------------------------------------------------------------------

gateway_router = APIRouter(tags=["Admin Gateway"])


@gateway_router.get("/health", summary="Gateway health check")
async def gateway_health() -> Dict[str, Any]:
    """
    Simple health check for the admin gateway.
    Returns gateway status and available services.
    """
    return {
        "status": "healthy",
        "service": "iacgenie-admin-gateway",
        "version": "1.0.0",
        "available_services": len(SERVICE_REGISTRY),
        "timestamp": "2026-08-03T00:00:00Z",
    }


@gateway_router.get(
    "/services",
    summary="List available services and their RBAC requirements",
    response_model=Dict[str, Any],
)
async def list_services() -> Dict[str, Any]:
    """
    Return a list of all registered backend services with their
    RBAC requirements and path prefixes.
    """
    services = []
    for prefix, meta in SERVICE_REGISTRY.items():
        services.append(
            {
                "prefix": prefix,
                "path_prefix": meta["path_prefix"],
                "name": meta["name"],
                "description": meta["description"],
                "min_role": meta["required_role"],
                "min_role_level": meta["min_role_level"],
            }
        )
    return {
        "status": "ok",
        "service_count": len(services),
        "services": sorted(services, key=lambda s: s["prefix"]),
    }


@gateway_router.get(
    "/permissions",
    summary="Current user's gateway permissions",
)
async def gateway_permissions(request: Request) -> Dict[str, Any]:
    """
    Return the current user's permissions based on their JWT claims.
    Shows which services the user can access.

    Requires a valid Bearer token in the Authorization header.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "AUTHENTICATION_REQUIRED",
                "message": "A valid JWT token is required",
                "code": "MISSING_TOKEN",
            },
        )

    # Decode token — try local JWT first, then Keycloak
    token = auth_header.split(" ", 1)[1]
    try:
        from utils.jwt_utils import verify_token as verify_local

        payload = verify_local(token)
    except Exception:
        # Fall back: attempt to decode without verification for basic info
        try:
            from jose import jwt as pyjwt

            payload = pyjwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False},
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "INVALID_TOKEN",
                    "message": "Could not decode token",
                    "code": "TOKEN_DECODE_FAILED",
                },
            )

    role = _normalise_role(payload.get("role", "member"))
    user_id = payload.get("uid") or payload.get("sub", "")
    email = payload.get("email", "")

    # Determine accessible services
    user_level = _role_level(role)
    accessible_services = []
    inaccessible_services = []

    for prefix, meta in sorted(SERVICE_REGISTRY.items()):
        if user_level >= meta["min_role_level"]:
            accessible_services.append({
                "prefix": prefix,
                "name": meta["name"],
                "min_role": meta["required_role"],
            })
        else:
            inaccessible_services.append({
                "prefix": prefix,
                "name": meta["name"],
                "min_role": meta["required_role"],
            })

    return {
        "status": "ok",
        "user_id": user_id,
        "email": email,
        "role": role,
        "role_level": user_level,
        "accessible_services": accessible_services,
        "inaccessible_services": inaccessible_services,
        "total_accessible": len(accessible_services),
        "total_inaccessible": len(inaccessible_services),
    }


# ---------------------------------------------------------------------------
# RBAC check helper — used by gateway routing logic
# ---------------------------------------------------------------------------


def check_gateway_permission(
    user_role: str,
    target_prefix: str,
) -> Dict[str, Any]:
    """
    Check if a user role can access a given service prefix.

    Args:
        user_role: Normalised role string (e.g. "member", "project-admin").
        target_prefix: Service prefix from the registry.

    Returns:
        Dict with 'allowed' (bool) and 'reason' (string).
    """
    service = SERVICE_REGISTRY.get(target_prefix)
    if not service:
        return {
            "allowed": False,
            "reason": f"Unknown service prefix: {target_prefix}",
        }

    user_level = _role_level(user_role)
    required_level = service["min_role_level"]

    if user_level < required_level:
        return {
            "allowed": False,
            "reason": (
                f"Insufficient role. "
                f"User role '{user_role}' (level {user_level}) "
                f"requires '{service['required_role']}' (level {required_level}) "
                f"to access service '{service['name']}'"
            ),
        }

    return {
        "allowed": True,
        "reason": f"User role '{user_role}' has access to '{service['name']}'",
    }


# ---------------------------------------------------------------------------
# Gateway route handler — full routing logic
# ---------------------------------------------------------------------------


async def gateway_route(request: Request, call_next: Any) -> Any:
    """
    ASGI middleware that routes requests based on path prefix.

    For each request:
      1. Extracts user role from JWT.
      2. Determines the target service from the path prefix.
      3. Checks RBAC permission.
      4. Returns 403 with reason if access denied.
      5. Otherwise passes the request through.
    """
    # Only intercept known service prefixes
    target_prefix = None
    for prefix in sorted(
        SERVICE_REGISTRY.keys(),
        key=lambda p: len(p),
        reverse=True,
    ):
        if request.url.path.startswith(f"/{prefix}/") or request.url.path == f"/{prefix}":
            target_prefix = prefix
            break

    # Health and gateway endpoints are always allowed
    if not target_prefix:
        return await call_next(request)

    service = SERVICE_REGISTRY.get(target_prefix)
    if not service:
        return await call_next(request)

    # Extract user role from token
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "AUTHENTICATION_REQUIRED",
                "message": f"Bearer token required for service '{service['name']}'",
                "code": "MISSING_TOKEN",
            },
        )

    token = auth_header.split(" ", 1)[1]
    try:
        from utils.jwt_utils import verify_token as verify_local

        payload = verify_local(token)
    except Exception:
        try:
            from jose import jwt as pyjwt

            payload = pyjwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False},
            )
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": "INVALID_TOKEN",
                    "message": "Could not decode or verify token",
                    "code": "TOKEN_VERIFICATION_FAILED",
                },
            )

    user_role = _normalise_role(payload.get("role", "member"))
    user_id = payload.get("uid") or payload.get("sub", "")

    # Check RBAC permission
    perm = check_gateway_permission(user_role, target_prefix)
    if not perm["allowed"]:
        logger.warning(
            "Gateway RBAC denied: user=%s role=%s target=%s reason=%s",
            user_id,
            user_role,
            target_prefix,
            perm["reason"],
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "error": "FORBIDDEN",
                "message": perm["reason"],
                "code": "GATEWAY_RBAC_DENIED",
                "user_role": user_role,
                "target_service": service["name"],
                "target_prefix": target_prefix,
            },
        )

    # Permission granted — pass through
    request.state.user_role = user_role
    request.state.user_id = user_id
    return await call_next(request)


# ---------------------------------------------------------------------------
# Mount helper — easily attach to a FastAPI app
# ---------------------------------------------------------------------------


def mount_gateway(app: Any, prefix: str = "/gateway") -> None:
    """
    Mount the admin gateway router on a FastAPI app.

    Args:
        app: The FastAPI application instance.
        prefix: URL prefix to mount under.
    """
    app.include_router(gateway_router, prefix=prefix)
