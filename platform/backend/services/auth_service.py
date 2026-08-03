"""

Authentication Service

PostgreSQL-only authentication service using LocalAuthProvider.

"""

import os

import logging

from typing import Dict, Any, Optional

from auth_providers.base import AuthProvider, AuthResult, AuthError, AuthErrorType

from auth_providers.factory import create_auth_provider

logger = logging.getLogger(__name__)


class AuthService:
    """Authentication service that dynamically loads pluggable providers"""

    def __init__(self) -> None:
        self.provider: Optional[AuthProvider] = None
        self._initialize_provider()

    def _initialize_provider(self) -> None:
        """Initialize the active authentication provider dynamically"""
        try:
            provider_name = os.getenv("AUTH_PROVIDER", "local").lower()
            self.provider = create_auth_provider(provider_name)
            logger.info(f"Initialized dynamic authentication provider: {provider_name}")
        except Exception as e:
            logger.error(f"Failed to initialize authentication provider: {str(e)}")
            raise

    async def authenticate_with_credentials(
        self, email: str, password: str
    ) -> AuthResult:
        """
        Authenticate user with email and password
        Args:
            email: User's email address
            password: User's password
        Returns:
            AuthResult with success status and user data or error
        """
        if not self.provider:
            return AuthResult(
                success=False,
                error=AuthError(
                    type=AuthErrorType.INTERNAL_ERROR,
                    message="Authentication provider not initialized",
                    status_code=500,
                ),
            )
        return await self.provider.authenticate_with_credentials(email, password)

    async def authenticate_with_token(self, token: str) -> AuthResult:
        """
        Authenticate user with an existing token
        Args:
            token: Authentication token
        Returns:
            AuthResult with success status and user data or error
        """
        if not self.provider:
            return AuthResult(
                success=False,
                error=AuthError(
                    type=AuthErrorType.INTERNAL_ERROR,
                    message="Authentication provider not initialized",
                    status_code=500,
                ),
            )
        return await self.provider.authenticate_with_token(token)

    async def refresh_token(self, refresh_token: str) -> AuthResult:
        """
        Refresh an authentication token
        Args:
            refresh_token: Refresh token string
        Returns:
            AuthResult with success status and new tokens
        """
        if not self.provider:
            return AuthResult(
                success=False,
                error=AuthError(
                    type=AuthErrorType.INTERNAL_ERROR,
                    message="Authentication provider not initialized",
                    status_code=500,
                ),
            )
        if hasattr(self.provider, "refresh_token"):
            return await self.provider.refresh_token(refresh_token)
        return AuthResult(
            success=False,
            error=AuthError(
                type=AuthErrorType.INTERNAL_ERROR,
                message="refresh_token not supported by current provider",
                status_code=501,
            ),
        )

    async def register_user(
        self,
        email: str,
        password: str,
        display_name: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ) -> AuthResult:
        """
        Register a new user
        Args:
            email: User's email address
            password: User's password
            display_name: Optional display name
            first_name: Optional first name
            last_name: Optional last name
        Returns:
            AuthResult with success status and user data or error
        """
        if not self.provider:
            return AuthResult(
                success=False,
                error=AuthError(
                    type=AuthErrorType.INTERNAL_ERROR,
                    message="Authentication provider not initialized",
                    status_code=500,
                ),
            )
        return await self.provider.register_user(  # type: ignore
            email, password, display_name, first_name, last_name
        )

    async def verify_token(self, token: str) -> AuthResult:
        """
        Verify an authentication token
        Args:
            token: Token to verify
        Returns:
            AuthResult with verification status and user data or error
        """
        if not self.provider:
            return AuthResult(
                success=False,
                error=AuthError(
                    type=AuthErrorType.INTERNAL_ERROR,
                    message="Authentication provider not initialized",
                    status_code=500,
                ),
            )
        return await self.provider.verify_token(token)

    async def send_password_reset(self, email: str) -> AuthResult:
        """
        Send password reset email
        Args:
            email: User's email address
        Returns:
            AuthResult with success status or error
        """
        if not self.provider:
            return AuthResult(
                success=False,
                error=AuthError(
                    type=AuthErrorType.INTERNAL_ERROR,
                    message="Authentication provider not initialized",
                    status_code=500,
                ),
            )
        return await self.provider.send_password_reset(email)

    async def health_check(self) -> bool:
        """
        Check if authentication service is healthy
        Returns:
            True if healthy, False otherwise
        """
        if not self.provider:
            return False
        result = await self.provider.health_check()
        return bool(result)

    def get_provider_name(self) -> str:
        """Get name of current authentication provider"""
        if not self.provider:
            return "none"
        return os.getenv("AUTH_PROVIDER", "local").lower()

    async def verify_email(self, token: str) -> AuthResult:
        """
        Verify email with verification token
        Args:
            token: Email verification token
        Returns:
            AuthResult with success status or error
        """
        if not self.provider:
            return AuthResult(
                success=False,
                error=AuthError(
                    type=AuthErrorType.INTERNAL_ERROR,
                    message="Authentication provider not initialized",
                    status_code=500,
                ),
            )
        return await self.provider.verify_email(token)

    async def delete_user(self, email: str) -> AuthResult:
        """Delete a user from the authentication provider and local database."""
        if not self.provider:
            return AuthResult(
                success=False,
                error=AuthError(
                    type=AuthErrorType.INTERNAL_ERROR,
                    message="Authentication provider not initialized",
                    status_code=500,
                ),
            )
        return await self.provider.delete_user(email)

    async def invite_user(
        self, email: str, role: Optional[str] = None, sender_email: Optional[str] = None
    ) -> AuthResult:
        """
        Invite a new user to the system
        Args:
            email: User's email address
            role: Optional user role (user, admin)
            sender_email: Email of the sender
        Returns:
            AuthResult with success status or error
        """
        if not self.provider:
            return AuthResult(
                success=False,
                error=AuthError(
                    type=AuthErrorType.INTERNAL_ERROR,
                    message="Authentication provider not initialized",
                    status_code=500,
                ),
            )
        return await self.provider.invite_user(email, role, sender_email)

    async def verify_otp(self, token: str, otp: str | None = None) -> AuthResult:
        """Verify OTP for email verification or general OTP flow"""
        if not self.provider:
            return AuthResult(
                success=False,
                error=AuthError(
                    type=AuthErrorType.INTERNAL_ERROR,
                    message="Not initialized",
                    status_code=500,
                ),
            )
        if hasattr(self.provider, "verify_otp"):
            return await getattr(self.provider, "verify_otp")(token, otp)
        return AuthResult(
            success=False,
            error=AuthError(
                type=AuthErrorType.INTERNAL_ERROR,
                message="verify_otp not supported",
                status_code=501,
            ),
        )

    async def resend_otp(self, token: str, email: str) -> AuthResult:
        """Resend OTP"""
        if not self.provider:
            return AuthResult(
                success=False,
                error=AuthError(
                    type=AuthErrorType.INTERNAL_ERROR,
                    message="Not initialized",
                    status_code=500,
                ),
            )
        if hasattr(self.provider, "resend_otp"):
            return await getattr(self.provider, "resend_otp")(token, email)
        return AuthResult(
            success=False,
            error=AuthError(
                type=AuthErrorType.INTERNAL_ERROR,
                message="resend_otp not supported",
                status_code=501,
            ),
        )

    async def forgot_password_otp(self, email: str) -> AuthResult:
        """Generate OTP for password reset"""
        if not self.provider:
            return AuthResult(
                success=False,
                error=AuthError(
                    type=AuthErrorType.INTERNAL_ERROR,
                    message="Not initialized",
                    status_code=500,
                ),
            )
        if hasattr(self.provider, "forgot_password_otp"):
            return await getattr(self.provider, "forgot_password_otp")(email)
        return AuthResult(
            success=False,
            error=AuthError(
                type=AuthErrorType.INTERNAL_ERROR,
                message="forgot_password_otp not supported",
                status_code=501,
            ),
        )

    async def verify_otp_for_password_reset(
        self, token: str, otp: str | None = None
    ) -> AuthResult:
        """Verify OTP specifically for password reset flow"""
        if not self.provider:
            return AuthResult(
                success=False,
                error=AuthError(
                    type=AuthErrorType.INTERNAL_ERROR,
                    message="Not initialized",
                    status_code=500,
                ),
            )
        if hasattr(self.provider, "verify_otp_for_password_reset"):
            return await getattr(self.provider, "verify_otp_for_password_reset")(
                token, otp
            )
        return AuthResult(
            success=False,
            error=AuthError(
                type=AuthErrorType.INTERNAL_ERROR,
                message="verify_otp_for_password_reset not supported",
                status_code=501,
            ),
        )

    async def reset_password_with_otp(
        self, token: str, new_password: str
    ) -> AuthResult:
        """Reset password using verified OTP token"""
        if not self.provider:
            return AuthResult(
                success=False,
                error=AuthError(
                    type=AuthErrorType.INTERNAL_ERROR,
                    message="Not initialized",
                    status_code=500,
                ),
            )
        if hasattr(self.provider, "reset_password_with_otp"):
            return await getattr(self.provider, "reset_password_with_otp")(
                token, new_password
            )
        return AuthResult(
            success=False,
            error=AuthError(
                type=AuthErrorType.INTERNAL_ERROR,
                message="reset_password_with_otp not supported",
                status_code=501,
            ),
        )

    async def verify_otp_and_login(
        self, token: str, otp: str | None = None
    ) -> AuthResult:
        """Verify OTP and generate session token"""
        if not self.provider:
            return AuthResult(
                success=False,
                error=AuthError(
                    type=AuthErrorType.INTERNAL_ERROR,
                    message="Not initialized",
                    status_code=500,
                ),
            )
        if hasattr(self.provider, "verify_otp_and_login"):
            return await getattr(self.provider, "verify_otp_and_login")(token, otp)
        return AuthResult(
            success=False,
            error=AuthError(
                type=AuthErrorType.INTERNAL_ERROR,
                message="verify_otp_and_login not supported",
                status_code=501,
            ),
        )


# Standalone invite_user function for admin router compatibility


async def invite_user(
    email: str, display_name: Optional[str] = None, role: Optional[str] = None
) -> Dict[str, Any]:
    """
    Standalone invite_user function for admin router compatibility.
    Args:
        email: User's email address
        display_name: Optional display name (renamed from sender_email for clarity)
        role: Optional user role (user, admin)
    Returns:
        Dictionary with success status and user data or error
    """
    try:
        result = await auth_service.provider.invite_user(email, role, display_name)  # type: ignore[union-attr]
        # Convert AuthResult to dict for API response
        if result.success:
            return {
                "success": True,
                "user": result.user,
                "invitation_link": f"/verify?token={result.token}"
                if hasattr(result, "token")
                else None,
                "email_sent": True,
            }
        else:
            error_dict = {}
            if result.error:
                error_dict = {"message": str(result.error)}
            return {"success": False, "error": error_dict}
    except Exception as e:
        logger.error(f"Failed to invite user: {str(e)}")
        return {
            "success": False,
            "message": f"Failed to invite user: {str(e)}",
            "error": {"type": "INTERNAL_ERROR", "message": str(e), "status_code": 500},
        }


# Global instance

auth_service = AuthService()
