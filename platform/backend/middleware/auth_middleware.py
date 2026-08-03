"""

Enhanced Authentication Middleware

Provides consistent token validation with security features.

Delegates to AuthProvider implementations via the factory pattern.

"""

import logging

from typing import Dict, Any

from fastapi import Request, HTTPException, Depends

from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Security configuration

MAX_TOKEN_AGE = 3600  # 1 hour in seconds


class AuthMiddleware:
    """Enhanced authentication middleware with security features"""

    def __init__(self) -> None:
        """Initialize middleware. Token verification uses local JWT only."""
        logger.info("AuthMiddleware initialized (local JWT verification)")

    async def verify_token(self, request: Request) -> Dict[str, Any]:
        """
        Verify the local JWT issued after authentication.
        All tokens in this API are local HS256 JWTs issued after successful
        authentication via Keycloak (or other configured provider).
        Args:
            request: FastAPI request object
        Returns:
            Decoded token claims with 'uid', 'email', 'role' keys
        Raises:
            HTTPException: If token is invalid, expired, or missing
        """
        try:
            # Extract token from Authorization header
            auth_header = request.headers.get("Authorization")
            if not auth_header:
                self._log_auth_failure(request, "Missing Authorization header")
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": "AUTHENTICATION_REQUIRED",
                        "message": "Authorization header is required",
                        "code": "MISSING_TOKEN",
                    },
                )
            if not auth_header.startswith("Bearer "):
                self._log_auth_failure(request, "Invalid Authorization header format")
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": "AUTHENTICATION_REQUIRED",
                        "message": "Authorization header must start with 'Bearer '",
                        "code": "INVALID_TOKEN_FORMAT",
                    },
                )
            token = auth_header.split(" ")[1]
            if not token or len(token) < 10:
                self._log_auth_failure(request, "Token too short or empty")
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": "AUTHENTICATION_REQUIRED",
                        "message": "Invalid token format",
                        "code": "INVALID_TOKEN",
                    },
                )
            # Verify the local JWT
            from utils.jwt_utils import (
                verify_token as verify_local_token,
                TokenExpiredError,
            )

            try:
                payload = verify_local_token(token)
            except TokenExpiredError:
                self._log_auth_failure(request, "Token has expired")
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": "TOKEN_EXPIRED",
                        "message": "Token has expired",
                        "code": "TOKEN_EXPIRED",
                    },
                )
            user_id = payload.get("sub")
            email = payload.get("email")
            role = payload.get("role", "user")
            if not user_id or not email:
                self._log_auth_failure(request, "Token missing required claims")
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": "INVALID_TOKEN",
                        "message": "Token missing required claims",
                        "code": "INVALID_CLAIMS",
                    },
                )
            decoded_token = {
                "uid": user_id,
                "email": email,
                "role": role,
                "iss": payload.get("iss"),
                "aud": payload.get("aud"),
                "exp": payload.get("exp"),
                "iat": payload.get("iat"),
                "jti": payload.get("jti"),
            }
            # Check token revocation
            jti = decoded_token.get("jti")
            if jti:
                try:
                    from utils.token_revocation import get_revocation_store

                    if await get_revocation_store().is_revoked(jti):
                        self._log_auth_failure(request, "Token has been revoked")
                        raise HTTPException(
                            status_code=401,
                            detail={
                                "error": "TOKEN_REVOKED",
                                "message": "Token has been revoked",
                                "code": "TOKEN_REVOKED",
                            },
                        )
                except Exception as e:
                    logger.warning(
                        f"Revocation check failed for jti={jti}: {e}. Allowing request."
                    )
            # Validate required claims
            self._validate_token_claims(decoded_token, request)
            # Add claims key for compatibility
            if "claims" not in decoded_token:
                skip_keys = {"iss", "aud", "exp", "iat", "uid", "email"}
                decoded_token["claims"] = {
                    k: decoded_token[k] for k in decoded_token if k not in skip_keys
                }
            self._log_auth_success(request, decoded_token)
            return dict(decoded_token)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Unexpected authentication error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "INTERNAL_ERROR",
                    "message": "Internal authentication error",
                    "code": "INTERNAL_ERROR",
                },
            )

    def _validate_token_claims(self, token: Dict[str, Any], request: Request) -> None:
        """Lightweight sanity check for token claims.
        Full claim validation is delegated to the auth provider. This method
        ensures basic compatibility fields exist and the token isn't expired.
        """
        # Ensure uid is present (normalized from sub/uid by provider)
        if "uid" not in token or not token.get("uid"):
            self._log_auth_failure(request, "Token missing user ID (uid)")
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "AUTHENTICATION_REQUIRED",
                    "message": "Token missing required claims",
                    "code": "INVALID_CLAIMS",
                },
            )
        if "email" not in token or not token.get("email"):
            self._log_auth_failure(request, "Token missing email")
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "AUTHENTICATION_REQUIRED",
                    "message": "Token missing required claims",
                    "code": "INVALID_CLAIMS",
                },
            )
        # Check token expiration
        exp_time = token.get("exp")
        if exp_time:
            now = datetime.now(timezone.utc).timestamp()
            if now > exp_time:
                self._log_auth_failure(request, "Token has expired")
                raise HTTPException(
                    status_code=401,
                    detail={
                        "error": "AUTHENTICATION_REQUIRED",
                        "message": "Token has expired",
                        "code": "TOKEN_EXPIRED",
                    },
                )

    def _log_auth_failure(self, request: Request, reason: str) -> None:
        """Log authentication failure"""
        client_host = request.client.host if request.client else "Unknown"
        logger.warning(
            f"Authentication failed - {reason} | "
            f"IP: {client_host} | "
            f"Path: {request.url.path} | "
            f"Method: {request.method} | "
            f"User-Agent: {request.headers.get('user-agent', 'Unknown')}"
        )

    def _log_auth_success(self, request: Request, token: Dict[str, Any]) -> None:
        """Log successful authentication"""
        client_host = request.client.host if request.client else "Unknown"
        logger.info(
            f"Authentication successful | "
            f"User: {token.get('uid', 'Unknown')} | "
            f"Email: {token.get('email', 'Unknown')} | "
            f"IP: {client_host} | "
            f"Path: {request.url.path} | "
            f"Method: {request.method}"
        )


# Global middleware instance


auth_middleware = AuthMiddleware()

# Convenience functions for dependency injection (async-compatible)


async def verify_token(request: Request) -> Dict[str, Any]:
    """Token verification delegated to the configured auth provider"""
    return await auth_middleware.verify_token(request)


# Backwards compatibility alias
verify_access_token = verify_token


def require_admin(token: Dict[str, Any] = Depends(verify_token)) -> Dict[str, Any]:
    """Require admin privileges"""
    from config.roles import is_admin

    role = token.get("role", "user")
    if not is_admin(role):
        logger.warning(f"Admin access denied for user: {token.get('uid')}")
        raise HTTPException(
            status_code=403,
            detail={
                "error": "FORBIDDEN",
                "message": "Admin privileges required",
                "code": "ADMIN_REQUIRED",
            },
        )
    return token


def get_user_id(token: Dict[str, Any] = Depends(verify_token)) -> str:
    """Get user ID from token"""
    user_id = token.get("uid")
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail={
                "error": "AUTHENTICATION_REQUIRED",
                "message": "User ID not found in token",
                "code": "MISSING_USER_ID",
            },
        )
    return user_id


def get_current_user_id(user: Dict[str, Any] = Depends(verify_token)) -> str:
    """Get current user ID (alias for backward compatibility)"""
    return user.get("uid", "default-user-id") or "default-user-id"
