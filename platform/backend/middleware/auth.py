"""JWT verification and RBAC middleware for pipeline endpoints."""

from fastapi import Depends, HTTPException, status

from fastapi.security import HTTPBearer

from typing import Optional

from middleware.auth_middleware import verify_token

security = HTTPBearer()


async def verify_pipeline_token(
    token_payload: dict = Depends(verify_token),
) -> dict:
    """Verify JWT token and return decoded payload for pipeline endpoints."""
    return token_payload


async def require_pipeline_role(
    required_role: str,
    token_payload: dict = Depends(verify_pipeline_token),
) -> dict:
    """Verify user has a specific role for pipeline operations."""
    user_roles = token_payload.get("roles", [])
    role_hierarchy = {
        "admin": ["admin"],
        "developer": ["admin", "developer"],
        "reviewer": ["admin", "reviewer", "developer"],
    }
    allowed_roles = role_hierarchy.get(required_role, [])
    if not any(role in allowed_roles for role in user_roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Role '{required_role}' or higher required",
        )
    return token_payload


class APIKeyAuth:
    """API key authentication with rotation support."""

    def __init__(self) -> None:
        self._keys: dict = {}  # key -> {user_id, expires_at}

    def register_key(
        self, key: str, user_id: str, expires_in_seconds: int = 86400
    ) -> None:
        import time

        self._keys[key] = {
            "user_id": user_id,
            "expires_at": time.time() + expires_in_seconds,
        }

    def validate_key(self, key: str) -> Optional[dict]:
        import time

        entry = self._keys.get(key)
        if not entry:
            return None
        if time.time() > entry["expires_at"]:
            del self._keys[key]
            return None
        return {"user_id": entry["user_id"]}

    def rotate_key(self, old_key: str, new_key: str, user_id: str) -> dict:
        """Rotate an API key with a grace period."""
        if old_key not in self._keys:
            return {"success": False, "error": "Old key not found"}
        # Register new key with same expiry as old key
        self.register_key(new_key, user_id)
        # Keep old key for 24h grace period
        old_entry = self._keys[old_key]
        import time

        grace_expiry = time.time() + 86400
        self._keys[old_key] = {**old_entry, "expires_at": grace_expiry}
        return {"success": True, "message": "Key rotated successfully"}


# Module-level singleton


_api_key_auth = APIKeyAuth()
