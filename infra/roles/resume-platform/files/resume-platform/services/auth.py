"""Keycloak OIDC authentication service."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from jose import jwt

logger = logging.getLogger(__name__)

# ── Keycloak Configuration ─────────────────────────────────────────────

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "iacgenie")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "resume-platform")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "CHANGE_ME")
AUTH_WRAPPER_URL = os.getenv("AUTH_WRAPPER_URL", "http://auth-wrapper:9096")

# ── Token Validation ───────────────────────────────────────────────────

async def validate_token(token: str) -> dict[str, Any] | None:
    """Validate JWT token via auth-wrapper or Keycloak directly."""
    # Try auth-wrapper first (preferred)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{AUTH_WRAPPER_URL}/validate",
                json={"token": token},
            )
            if resp.status_code == 200:
                return resp.json()
    except Exception as e:
        logger.warning(f"Auth-wrapper validation failed: {e}")

    # Fallback: validate via Keycloak introspection
    return await _validate_via_keycloak(token)


async def _validate_via_keycloak(token: str) -> dict[str, Any] | None:
    """Validate token via Keycloak introspection endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token/introspect",
                data={
                    "token": token,
                    "client_id": KEYCLOAK_CLIENT_ID,
                    "client_secret": KEYCLOAK_CLIENT_SECRET,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("active"):
                    return {
                        "sub": data.get("sub"),
                        "email": data.get("email"),
                        "name": data.get("preferred_username"),
                        "roles": data.get("roles", []),
                    }
    except Exception as e:
        logger.warning(f"Keycloak introspection failed: {e}")

    return None


async def get_user_from_token(token: str) -> dict[str, Any] | None:
    """Extract user info from token and return user dict."""
    info = await validate_token(token)
    if not info:
        return None

    return {
        "keycloak_id": info.get("sub"),
        "email": info.get("email"),
        "name": info.get("name"),
    }


def get_auth_wrapper_url() -> str:
    """Get the auth-wrapper URL for redirect-based auth."""
    return AUTH_WRAPPER_URL
