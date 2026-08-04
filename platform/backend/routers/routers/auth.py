"""

Authentication router for PostgreSQL-based authentication

This module provides authentication endpoints using PostgreSQL database

with password hashing (bcrypt) and JWT tokens.

Authentication Features:

- All authentication uses PostgreSQL database stored in backend/db/adapters/postgres_adapter.py

- Passwords are hashed using bcrypt before storage

- JWT tokens are generated and verified server-side

- Email verification is automatic (no email sending required for local dev)

See backend/auth_providers/local.py for KeycloakAuthProvider implementation.

"""

from fastapi import APIRouter, HTTPException, Request, Query, Depends

from fastapi.responses import JSONResponse, RedirectResponse

from typing import Optional, List, Dict, Any

from datetime import datetime

import logging

import os


logger = logging.getLogger(__name__)
from schemas.auth import (
    TokenRequest,
    TokenResponse,
    TokenVerifyRequest,
    TokenVerifyResponse,
    SignupRequest,
    SignupResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    AuthErrorResponse,
    OtpRequest,
    ResendOtpRequest,
    VerifyOtpForPasswordResetRequest,
    PasswordResetWithOtpRequest,
    OtpVerificationRequest,
    ResendOtpResponse,
    ForgotPasswordOtpRequest,
    RefreshTokenRequest,
)

# Email Service imports

try:
    from services.smtp2go_email_service import smtp2go_email_service

    EMAIL_SERVICE_AVAILABLE = True
except ImportError:
    logger.warning("Email service not available")
    EMAIL_SERVICE_AVAILABLE = False
# Import JWT token utilities

import importlib.util

_OTP_AVAILABLE = importlib.util.find_spec("utils.jwt_utils") is not None
try:
    if _OTP_AVAILABLE:
        from utils.jwt_utils import generate_token, verify_otp_token, JWTError
    OTP_AVAILABLE = _OTP_AVAILABLE
except ImportError:
    logger.warning("OTP utilities not available")
    OTP_AVAILABLE = False
# New email request schemas

from pydantic import BaseModel


class SendWelcomeEmailRequest(BaseModel):
    to_email: str
    start_url: str
    dashboard_url: str
    docs_url: str
    user_name: Optional[str] = None


class SendDeploymentSuccessRequest(BaseModel):
    to_email: str
    deployment_id: str
    cloud_provider: str
    region: str
    generation_id: str
    elapsed_time: str
    resources: List[Dict[str, Any]]
    deployments_url: str
    user_name: Optional[str] = None


class SendGenerationCompleteRequest(BaseModel):
    to_email: str
    generation_id: str
    ai_model: str
    cloud_provider: str
    file_count: int
    total_lines: int
    files: List[Dict[str, Any]]
    quality_score: int
    security_score: int
    efficiency_score: int
    dashboard_url: str
    user_name: Optional[str] = None


class SendSecurityAlertRequest(BaseModel):
    to_email: str
    alert_id: str
    change_timestamp: str
    ip_address: str
    device_info: str
    location: str
    security_center_url: str
    user_name: Optional[str] = None


from middleware.error_handling import create_success_response, error_handler
from middleware.auth_middleware import verify_token as auth_verify_token

# Import KeycloakAuthProvider for PostgreSQL-based authentication

try:
    LOCAL_AUTH_AVAILABLE = True
except ImportError:
    LOCAL_AUTH_AVAILABLE = False
NOTIFICATION_SERVICE_AVAILABLE = EMAIL_SERVICE_AVAILABLE

# Import AuthService for unified authentication operations

try:
    from services.auth_service import auth_service

    AUTH_SERVICE_AVAILABLE = True
except ImportError:
    logger.warning("AuthService not available")
    AUTH_SERVICE_AVAILABLE = False
# Import database provider

try:
    from db.db_provider import db_provider

    DB_AVAILABLE = True
except ImportError:
    logger.warning("Database provider not available")
    DB_AVAILABLE = False
router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post(
    "/signup",
    response_model=SignupResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Bad Request - Invalid input"},
        409: {
            "model": AuthErrorResponse,
            "description": "Conflict - Email already exists",
        },
        500: {"model": AuthErrorResponse, "description": "Internal Server Error"},
    },
    summary="Register User",
    description="""
    Register a new user with email and password using the authentication provider.
    Returns user info, token, OTP token (for email verification), and message.
    User can be logged in immediately after signup.
    """,
)
async def register_user(request: SignupRequest) -> Any:
    """
    Register a new user with email and password
    Creates a new user account using PostgreSQL database,
    sends an OTP verification email, and returns user information with JWT token and OTP token.
    **Response includes:**
    - User info (uid, email, displayName)
    - Authentication token
    - OTP token (for email verification via OTP flow)
    **FIX**: This endpoint now returns an authentication token and OTP token so users can be
    logged in immediately after registration without needing to sign in separately.
    """
    try:
        # Register user with Keycloak (native email verification flow)
        if not LOCAL_AUTH_AVAILABLE:
            error_response = error_handler.create_error_response(
                message="Authentication provider not available. Please check backend configuration.",
                error_code="INTERNAL_ERROR",
                status_code=500,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
        result = await auth_service.register_user(
            email=request.email,
            password=request.password,
            display_name=request.displayName,
        )
        if result.success:
            # Registration successful — Keycloak has sent a verification email
            response_data: Dict[str, Any] = {}
            if hasattr(result, "user") and result.user:
                # Add flat fields directly to data for test compatibility
                response_data["uid"] = result.user.get("uid")
                response_data["email"] = result.user.get("email")
                response_data["displayName"] = result.user.get("displayName")
                response_data["emailVerified"] = False
                response_data["role"] = result.user.get("role", "user")

                # Also keep nested "user" for backward compatibility
                response_data["user"] = {
                    "uid": result.user.get("uid"),
                    "email": result.user.get("email"),
                    "displayName": result.user.get("displayName"),
                    "emailVerified": False,
                    "role": result.user.get("role", "user"),
                }
            response_data["message"] = (
                "Account created successfully. Please check your email for a verification link."
            )
            return create_success_response(
                data=response_data, message="Signup successful"
            )
        else:
            # Registration failed
            assert result.error is not None
            error_response = error_handler.create_error_response(
                message=result.error.message,
                error_code=result.error.type.value,
                status_code=result.error.status_code,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
    except Exception as e:
        logger.error(f"Unexpected error during user registration: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Internal server error occurred during registration",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"], content=error_response
        )


@router.post(
    "/verify-email/{token}",
    summary="Verify Email Address",
    description="""
    Verify a user's email address using the verification token.
    This endpoint validates the email verification token and marks
    the user's email as verified in the database.
    **Path Parameters:**
    - `token`: The verification token sent to the user's email
    **Success Response:**
    ```json
    {
      "success": true,
      "message": "Email verified successfully"
    }
    ```
    **Error Responses:**
    - 400: Invalid or expired token
    - 500: Internal server error
    """,
)
async def verify_email(token: str) -> Any:
    """
    Verify user email with token
    Validates the email verification token and marks the user's email
    as verified in the PostgreSQL database.
    """
    try:
        if not token or not token.strip():
            error_response = error_handler.create_error_response(
                message="Verification token is required and cannot be empty",
                error_code="INVALID_INPUT",
                status_code=400,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
        # Verify email with auth service
        result = await auth_service.verify_email(token=token)
        if result.success:
            # Email verification successful
            return create_success_response(
                data={"verified": True, "message": "Email verified successfully"},
                message="Email verification successful",
            )
        else:
            # Email verification failed
            assert result.error is not None
            error_response = error_handler.create_error_response(
                message=result.error.message,
                error_code=result.error.type.value,
                status_code=result.error.status_code,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
    except Exception as e:
        logger.error(f"Unexpected error during email verification: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Internal server error occurred during email verification",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"], content=error_response
        )


@router.delete(
    "/users/{email}",
    summary="Delete a user",
    description="Delete a user from both the authentication provider and local database.",
)
async def delete_user(email: str) -> JSONResponse:
    """Delete a user by email from Keycloak and local PostgreSQL."""
    result = await auth_service.delete_user(email)
    if result.success:
        return JSONResponse(
            status_code=200,
            content={"message": "User deleted successfully", "email": email},
        )
    error = result.error
    return JSONResponse(
        status_code=error.status_code if error else 500,
        content={"message": error.message if error else "Failed to delete user"},
    )


@router.post(
    "/reset-password",
    response_model=PasswordResetResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Bad Request - Invalid input"},
        500: {"model": AuthErrorResponse, "description": "Internal Server Error"},
    },
    summary="Send Password Reset Email",
    description="""
    Send a password reset email to the user's email address using the authentication provider.
    Returns a generic message for security.
    """,
)
async def send_password_reset(request: PasswordResetRequest) -> Any:
    """
    Send password reset email
    Sends a password reset link/token to the user's email address using
    the configured authentication provider.
    """
    try:
        # Send password reset email with auth service
        result = await auth_service.send_password_reset(email=request.email)
        if result.success:
            # Password reset email sent successfully
            return create_success_response(
                data={
                    "email": request.email,
                    "message": "If this email exists, a password reset link has been sent",
                },
                message="Password reset email sent",
            )
        else:
            # Password reset failed
            assert result.error is not None
            error_response = error_handler.create_error_response(
                message=result.error.message,
                error_code=result.error.type.value,
                status_code=result.error.status_code,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
    except Exception as e:
        logger.error(f"Unexpected error during password reset: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Internal server error occurred during password reset",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"], content=error_response
        )


class LoginRequest(BaseModel):
    """Request model for standard login"""

    email: str
    password: str


@router.post(
    "/login",
    response_model=TokenResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Bad Request - Invalid input"},
        401: {
            "model": AuthErrorResponse,
            "description": "Unauthorized - Invalid credentials",
        },
        403: {
            "model": AuthErrorResponse,
            "description": "Forbidden - Account disabled",
        },
        500: {"model": AuthErrorResponse, "description": "Internal Server Error"},
    },
    summary="User Login",
    description="Authenticate a user and return access and refresh tokens.",
)
async def login(request: LoginRequest, req: Request) -> Any:
    """Authenticate a user with email and password via Keycloak ROPC"""
    result = await auth_service.authenticate_with_credentials(
        email=request.email,
        password=request.password,
    )
    if result.success:
        response_data = {
            "token": result.token,
            "refreshToken": result.refresh_token,
            "expiresIn": result.expires_in,
            "user": {
                "uid": result.user.get("uid"),  # type: ignore
                "email": result.user.get("email"),  # type: ignore
                "displayName": result.user.get("displayName"),  # type: ignore
                "emailVerified": result.user.get("emailVerified", True),  # type: ignore
                "role": result.user.get("role", "user"),  # type: ignore
            },
        }
        return create_success_response(data=response_data, message="Login successful")
    else:
        assert result.error is not None
        error_response = error_handler.create_error_response(
            message=result.error.message,
            error_code=result.error.type.value,
            status_code=result.error.status_code,
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"],
            content=error_response,
        )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Bad Request"},
        401: {"model": AuthErrorResponse, "description": "Unauthorized"},
        500: {"model": AuthErrorResponse, "description": "Internal Server Error"},
    },
    summary="Refresh Token",
    description="Refresh an access token using a refresh token.",
)
async def refresh_token(request: RefreshTokenRequest) -> Any:
    """Refresh an access token"""
    try:
        if not AUTH_SERVICE_AVAILABLE:
            error_response = error_handler.create_error_response(
                message="Authentication provider not available.",
                error_code="INTERNAL_ERROR",
                status_code=500,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )

        result = await auth_service.refresh_token(request.refresh_token)
        if result.success:
            response_data: Dict[str, Any] = {}
            if hasattr(result, "user") and result.user:
                response_data["user"] = result.user
            if hasattr(result, "token") and result.token:
                response_data["token"] = result.token
            if hasattr(result, "refresh_token") and result.refresh_token:
                response_data["refreshToken"] = result.refresh_token
            if hasattr(result, "expires_in") and result.expires_in:
                response_data["expiresIn"] = result.expires_in
            return create_success_response(
                data=response_data, message="Token refreshed successfully"
            )
        else:
            assert result.error is not None
            error_response = error_handler.create_error_response(
                message=result.error.message,
                error_code=result.error.type.value,
                status_code=result.error.status_code,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        error_response = error_handler.create_error_response(
            message="An unexpected error occurred during token refresh.",
            error_code="INTERNAL_ERROR",
            status_code=500,
            details={"original_error": str(e)},
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"],
            content=error_response,
        )


@router.post(
    "/token",
    response_model=TokenResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Bad Request - Invalid input"},
        401: {
            "model": AuthErrorResponse,
            "description": "Unauthorized - Invalid credentials or token",
        },
        409: {
            "model": AuthErrorResponse,
            "description": "Conflict - Email already exists",
        },
        500: {"model": AuthErrorResponse, "description": "Internal Server Error"},
    },
    summary="Unified Authentication Endpoint",
    description="""
    Unified authentication endpoint that handles all auth operations via the 'action' parameter.
    **Supported Actions:**
    - `login`: Authenticate with email/password using PostgreSQL database
    - `signup`: Register new user with email/password to PostgreSQL database
    - `reset_password`: Send password reset token (stored in DB, logged for local dev)
    - `verify_token`: Verify JWT token issued by auth provider
    **Request Examples:**
    **Login:**
    ```json
    {
      "action": "login",
      "email": "user@example.com",
      "password": "password123"
    }
    ```
    **Signup:**
    ```json
    {
      "action": "signup",
      "email": "user@example.com",
      "password": "password123",
      "displayName": "John Doe"
    }
    ```
    **Password Reset:**
    ```json
    {
      "action": "reset_password",
      "email": "user@example.com"
    }
    ```
    **Token Verification:**
    ```json
    {
      "action": "verify_token",
      "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    ```
    """,
)
async def unified_auth_endpoint(request: TokenRequest, req: Request) -> Any:
    """
    Unified authentication endpoint using Keycloak with PostgreSQL
    Handles all authentication operations based on the 'action' parameter:
    - login: Authenticate with credentials from PostgreSQL database
    - signup: Register new user to PostgreSQL database
    - reset_password: Generate password reset token stored in DB
    - verify_token: Verify JWT token issued by auth provider
    All authentication uses the KeycloakAuthProvider which stores users in PostgreSQL
    with bcrypt-hashed passwords. See backend/auth_providers/local.py for implementation.
    """
    try:
        action = (
            request.action or "login"
        )  # Default to login for backward compatibility
        logger.warning(
            f"DEPRECATED: Usage of unified POST /api/auth/token "
            f"for action='{action}' is deprecated. "
            f"Please use the dedicated endpoints "
            f"(/login, /signup, /reset-password, /token/verify)."
        )
        if not LOCAL_AUTH_AVAILABLE:
            error_response = error_handler.create_error_response(
                message="Authentication provider not available. Please check backend configuration.",
                error_code="INTERNAL_ERROR",
                status_code=500,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
        if action == "login":
            # Direct email/password login via Keycloak ROPC
            if not (request.email and request.password):
                error_response = error_handler.create_error_response(
                    message="Email and password are required for login",
                    error_code="INVALID_INPUT",
                    status_code=400,
                )
                return JSONResponse(
                    status_code=error_response["error"]["statusCode"],
                    content=error_response,
                )
            result = await auth_service.authenticate_with_credentials(
                email=request.email,
                password=request.password,
            )
        elif action == "signup":
            # Handle signup using Keycloak
            if not (request.email and request.password):
                error_response = error_handler.create_error_response(
                    message="Email and password are required for signup",
                    error_code="INVALID_INPUT",
                    status_code=400,
                )
                return JSONResponse(
                    status_code=error_response["error"]["statusCode"],
                    content=error_response,
                )
            result = await auth_service.register_user(
                email=request.email,
                password=request.password,
                display_name=request.displayName,
                first_name=request.firstName,
                last_name=request.lastName,
            )
            # Do not generate session token here, user needs to verify email first.
            # The otp_token generated by the auth provider will be returned instead.
        elif action == "reset_password":
            # Handle password reset using Keycloak
            if not request.email:
                error_response = error_handler.create_error_response(
                    message="Email is required for password reset",
                    error_code="INVALID_INPUT",
                    status_code=400,
                )
                return JSONResponse(
                    status_code=error_response["error"]["statusCode"],
                    content=error_response,
                )
            result = await auth_service.send_password_reset(request.email)
        elif action == "verify_token":
            # Handle token verification using Keycloak
            if not request.token:
                error_response = error_handler.create_error_response(
                    message="Token is required for verification",
                    error_code="INVALID_INPUT",
                    status_code=400,
                )
                return JSONResponse(
                    status_code=error_response["error"]["statusCode"],
                    content=error_response,
                )
            result = await auth_service.verify_token(request.token)
        else:
            # Invalid action
            error_response = error_handler.create_error_response(
                message=f"Invalid action: {action}. Supported actions: login, signup, reset_password, verify_token",
                error_code="INVALID_INPUT",
                status_code=400,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
        if result.success:
            # Operation successful - format response for frontend
            response_data: Dict[str, Any] = {}
            # Include user data if available
            if hasattr(result, "user") and result.user:
                response_data["user"] = result.user
            # Include token if available
            if hasattr(result, "token") and result.token:
                response_data["token"] = result.token
            # Include otp_token if available (for signup with OTP verification)
            if hasattr(result, "otp_token") and result.otp_token:
                response_data["otp_token"] = result.otp_token
            # Include expiration if available
            if hasattr(result, "expires_in") and result.expires_in:
                response_data["expiresIn"] = result.expires_in
            # Include additional data for specific actions
            if action == "signup" and hasattr(result, "user"):
                # If no otp_token, this is link-based verification (Keycloak flow)
                has_otp_token = bool(response_data.get("otp_token"))
                if has_otp_token:
                    response_data["message"] = (
                        "Account created. Please check your email for the OTP code."
                    )
                elif result.token:
                    response_data["message"] = (
                        "Account created successfully. You can now sign in."
                    )
                else:
                    response_data["message"] = (
                        "Account created! A verification link has been sent to your email. "
                        "Please check your inbox and click the link to activate your account."
                    )
            return create_success_response(
                data=response_data,
                message=f"{action.replace('_', ' ').title()} successful",
            )
        else:
            # Operation failed - format error for frontend
            assert result.error is not None
            error_response = error_handler.create_error_response(
                message=result.error.message,
                error_code=result.error.type.value,
                status_code=result.error.status_code,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
    except Exception as e:
        logger.error(
            f"Unexpected error during {request.action or 'authentication'}: {str(e)}"
        )
        error_response = error_handler.create_error_response(
            message="Internal server error occurred",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"], content=error_response
        )


@router.post(
    "/token/verify",
    response_model=TokenVerifyResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Bad Request - Invalid input"},
        401: {
            "model": AuthErrorResponse,
            "description": "Unauthorized - Invalid token",
        },
        500: {"model": AuthErrorResponse, "description": "Internal Server Error"},
    },
    summary="Verify Token",
    description="""
    Verify an auth token and return decoded claims.
    This endpoint validates a token issued by the configured authentication provider
    and returns the decoded user information and claims if the token is valid.
    **Use Cases:**
    - Validate tokens from client applications
    - Extract user information from tokens
    - Check token expiration and validity
    **Error Codes:**
    - `INVALID_TOKEN`: Token is invalid or expired
    - `INTERNAL_ERROR`: Server error
    """,
)
async def verify_token(request: TokenVerifyRequest) -> Any:
    """
    Verify auth token
    Validates a token issued by the configured authentication provider
    and returns the decoded user information and claims if the token is valid.
    """
    try:
        # Validate token is not empty
        if not request.token or not request.token.strip():
            error_response = error_handler.create_error_response(
                message="Token is required and cannot be empty",
                error_code="INVALID_INPUT",
                status_code=422,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
        # Verify token with auth service
        result = await auth_service.verify_token(token=request.token)
        if result.success:
            # Token is valid
            return create_success_response(
                data={"valid": True, "user": result.user}, message="Token is valid"
            )
        else:
            # Token verification failed
            assert result.error is not None
            error_response = error_handler.create_error_response(
                message=result.error.message,
                error_code=result.error.type.value,
                status_code=result.error.status_code,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Internal server error occurred during token verification",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"], content=error_response
        )


@router.post(
    "/token/refresh",
    response_model=TokenResponse,
    responses={
        401: {
            "model": AuthErrorResponse,
            "description": "Unauthorized - Invalid or expired token",
        },
    },
    summary="Refresh Token",
    description="""
    Refresh an expiring or soon-to-expire JWT token with a new one.
    This endpoint verifies the provided token and issues a fresh JWT token
    if the original is still valid. Useful for proactive token refresh before
    expiration to avoid 401 errors on API calls.
    **Use Cases:**
    - Proactively refresh tokens before they expire
    - Recover from expired tokens by re-authenticating silently
    - Extend session without requiring user to re-enter credentials
    **Error Codes:**
    - `TOKEN_EXPIRED`: Token has expired and cannot be refreshed
    - `INVALID_TOKEN`: Token is invalid
    """,
)
async def refresh_auth_token(request: TokenVerifyRequest) -> Any:
    """
    Refresh an expiring JWT token with a new one
    Verifies the provided token is valid and issues a fresh token.
    If the token is still valid (even if near expiry), a new token is returned.
    """
    try:
        if not request.token or not request.token.strip():
            error_response = error_handler.create_error_response(
                message="Token is required and cannot be empty",
                error_code="INVALID_INPUT",
                status_code=422,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
        # Try to refresh via the auth provider
        result = await auth_service.refresh_token(request.token)
        if result.success and result.token:
            return create_success_response(
                data={
                    "token": result.token,
                    "expiresIn": result.expires_in or 900,
                    "user": result.user,
                },
                message="Token refreshed successfully",
            )
        # Provider refresh failed - try direct JWT refresh as fallback
        try:
            from ..utils.jwt_utils import (
                refresh_token as jwt_refresh_token,
                verify_token,
            )

            claims = verify_token(request.token)
            new_token = jwt_refresh_token(request.token)
            user = {
                "uid": claims.get("sub", ""),
                "email": claims.get("email", ""),
                "role": claims.get("role", "user"),
            }
            return create_success_response(
                data={
                    "token": new_token,
                    "expiresIn": 900,
                    "user": user,
                },
                message="Token refreshed successfully",
            )
        except Exception as jwt_err:
            logger.error(f"JWT token refresh fallback failed: {str(jwt_err)}")
            error_response = error_handler.create_error_response(
                message="Token has expired and cannot be refreshed. Please log in again.",
                error_code="TOKEN_EXPIRED",
                status_code=401,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
    except Exception as e:
        logger.error(f"Token refresh failed: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Token refresh failed",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"], content=error_response
        )


@router.get(
    "/health",
    summary="Authentication Health Check",
    description="Check the health of the authentication service",
    responses={
        200: {"description": "Authentication service is healthy"},
        500: {"description": "Authentication service is unhealthy"},
    },
)
async def auth_health_check() -> Any:
    """
    Check authentication service health
    Verifies that the authentication service is properly configured
    and accessible.
    """
    try:
        # Check if auth service is healthy
        is_healthy = await auth_service.health_check()
        if is_healthy:
            return create_success_response(
                data={
                    "service": auth_service.get_provider_name(),
                    "status": "healthy",
                    "configured": True,
                },
                message="Authentication service is healthy",
            )
        else:
            return JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "message": "Authentication service is unhealthy",
                    "timestamp": datetime.now().isoformat(),
                },
            )
    except Exception as e:
        logger.error(f"Authentication health check failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": "Authentication service is unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            },
        )


@router.get(
    "/me",
    summary="Get Current User Info",
    description="""
    Returns the authenticated user's info if the token is valid. Requires Authorization header.
    """,
    responses={
        200: {"description": "User info returned"},
        401: {"description": "Unauthorized - Invalid or missing token"},
    },
)
async def get_current_user(request: Request) -> Any:
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "success": False,
                    "error": {
                        "code": "AUTHENTICATION_REQUIRED",
                        "message": "Authorization header is required",
                        "statusCode": 401,
                    },
                },
            )
        token = auth_header.split(" ")[1]
        result = await auth_service.verify_token(token)
        if result.success:
            return create_success_response(
                data={"user": result.user}, message="User info returned"
            )
        else:
            assert result.error is not None
            error_response = error_handler.create_error_response(
                message=result.error.message,
                error_code=result.error.type.value,
                status_code=result.error.status_code,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
    except Exception as e:
        logger.error(f"Unexpected error in /auth/me: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error occurred",
                    "statusCode": 500,
                },
            },
        )


@router.get(
    "/roles",
    summary="Get User Roles",
    description="Get the authenticated user's global and project-specific roles.",
)
async def get_roles(
    token: Dict[str, Any] = Depends(auth_verify_token),
) -> Dict[str, Any]:
    """Get the authenticated user's global and project-specific roles"""
    global_role = token.get("role", "user")
    return {"roles": {"global": global_role, "projects": {}}}


@router.post(
    "/verify-otp",
    response_model=SignupResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Bad Request - Invalid input"},
        401: {
            "model": AuthErrorResponse,
            "description": "Unauthorized - Invalid token",
        },
        500: {"model": AuthErrorResponse, "description": "Internal Server Error"},
    },
    summary="Verify OTP",
    description="""
    Verify a user's OTP and mark email as verified.
    **Request Body:**
    ```json
    {
      "token": "otp_verification_token_here"
    }
    ```
    **Success Response:**
    ```json
    {
      "success": true,
      "message": "Email verified successfully"
    }
    ```
    **Error Responses:**
    - 400: Invalid or expired token
    - 500: Internal server error
    """,
)
async def verify_otp(request: OtpRequest) -> Any:
    """
    Verify user OTP
    Validates the OTP token and marks the user's email as verified.
    """
    try:
        if not request.token or not request.token.strip():
            error_response = error_handler.create_error_response(
                message="OTP token is required and cannot be empty",
                error_code="INVALID_INPUT",
                status_code=400,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
        # Verify OTP with auth provider
        if not LOCAL_AUTH_AVAILABLE:
            error_response = error_handler.create_error_response(
                message="Authentication provider not available",
                error_code="INTERNAL_ERROR",
                status_code=500,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
        result = await auth_service.verify_otp(token=request.token, otp=request.otp)
        if result.success:
            return create_success_response(
                data={"verified": True, "message": "Email verified successfully"},
                message="OTP verification successful",
            )
        else:
            assert result.error is not None
            error_response = error_handler.create_error_response(
                message=result.error.message,
                error_code=result.error.type.value,
                status_code=result.error.status_code,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
    except Exception as e:
        logger.error(f"Unexpected error during OTP verification: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Internal server error occurred during OTP verification",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"], content=error_response
        )


@router.post(
    "/resend-otp",
    response_model=ResendOtpResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Bad Request - Invalid input"},
        500: {"model": AuthErrorResponse, "description": "Internal Server Error"},
    },
    summary="Resend OTP",
    description="Resend the OTP verification email to the user.",
)
async def resend_otp(request: ResendOtpRequest) -> Any:
    try:
        result = await auth_service.resend_otp(token=request.token, email=request.email)
        if result.success:
            return create_success_response(
                data={"otp_token": result.otp_token}, message="OTP resent successfully"
            )
        assert result.error is not None
        error_response = error_handler.create_error_response(
            message=result.error.message,
            error_code=result.error.type.value,
            status_code=result.error.status_code,
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"], content=error_response
        )
    except Exception as e:
        logger.error(f"Unexpected error during OTP resend: {str(e)}")
        error_response = error_handler.create_error_response(
            "Internal error", "INTERNAL_ERROR", 500
        )
        return JSONResponse(status_code=500, content=error_response)


@router.post(
    "/forgot-password-otp",
    response_model=PasswordResetResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Bad Request - Invalid input"},
        500: {"model": AuthErrorResponse, "description": "Internal Server Error"},
    },
    summary="Send OTP for Password Reset",
)
async def forgot_password_otp(request: ForgotPasswordOtpRequest) -> Any:
    try:
        result = await auth_service.forgot_password_otp(request.email)
        if result.success:
            return create_success_response(
                data={"token": result.otp_token}, message="OTP sent successfully"
            )
        assert result.error is not None
        error_response = error_handler.create_error_response(
            message=result.error.message,
            error_code=result.error.type.value,
            status_code=result.error.status_code,
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"], content=error_response
        )
    except Exception as e:
        logger.error(f"Unexpected error during forgot password: {str(e)}")
        error_response = error_handler.create_error_response(
            "Internal error", "INTERNAL_ERROR", 500
        )
        return JSONResponse(status_code=500, content=error_response)


class VerifyOtpForPasswordResetResponse(BaseModel):
    """Response model for verify OTP for password reset"""

    success: bool
    message: str
    data: Dict[str, Any]
    timestamp: str


@router.post(
    "/verify-otp-for-password-reset",
    response_model=TokenResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Bad Request - Invalid input"},
        401: {
            "model": AuthErrorResponse,
            "description": "Unauthorized - Invalid token",
        },
        500: {"model": AuthErrorResponse, "description": "Internal Server Error"},
    },
    summary="Verify OTP for Password Reset",
)
async def verify_otp_for_password_reset(
    request: VerifyOtpForPasswordResetRequest,
) -> Any:
    try:
        result = await auth_service.verify_otp_for_password_reset(
            token=request.token, otp=request.otp
        )
        if result.success:
            return create_success_response(
                data={"reset_token": result.token}, message="OTP verified successfully"
            )
        assert result.error is not None
        error_response = error_handler.create_error_response(
            message=result.error.message,
            error_code=result.error.type.value,
            status_code=result.error.status_code,
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"], content=error_response
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        error_response = error_handler.create_error_response(
            "Internal error", "INTERNAL_ERROR", 500
        )
        return JSONResponse(status_code=500, content=error_response)


@router.post(
    "/reset-password-with-otp",
    response_model=TokenResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Bad Request - Invalid input"},
        500: {"model": AuthErrorResponse, "description": "Internal Server Error"},
    },
    summary="Reset Password with Verified OTP",
)
async def reset_password_with_otp(request: PasswordResetWithOtpRequest) -> Any:
    try:
        result = await auth_service.reset_password_with_otp(
            token=request.token, new_password=request.new_password
        )
        if result.success:
            return create_success_response(
                data={"message": "Password reset successfully"},
                message="Password reset successfully",
            )
        assert result.error is not None
        error_response = error_handler.create_error_response(
            message=result.error.message,
            error_code=result.error.type.value,
            status_code=result.error.status_code,
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"], content=error_response
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        error_response = error_handler.create_error_response(
            "Internal error", "INTERNAL_ERROR", 500
        )
        return JSONResponse(status_code=500, content=error_response)


@router.post(
    "/send-welcome",
    response_model=SignupResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Bad Request - Invalid input"},
        500: {"model": AuthErrorResponse, "description": "Internal Server Error"},
    },
    summary="Send Welcome Email",
    description="""
    Send a welcome email to a newly registered user.
    **Request Body:**
    ```json
    {
      "to_email": "user@example.com",
      "start_url": "https://iacgenie.ai/generate",
      "dashboard_url": "https://iacgenie.ai/dashboard",
      "docs_url": "https://docs.iacgenie.ai",
      "user_name": "John Doe"
    }
    ```
    """,
)
async def send_welcome_email(request: SendWelcomeEmailRequest) -> Any:
    """Send welcome email to newly registered user"""
    try:
        if not EMAIL_SERVICE_AVAILABLE:
            error_response = error_handler.create_error_response(
                message="Email service not available. Please configure SMTP2GO settings.",
                error_code="EMAIL_SERVICE_UNAVAILABLE",
                status_code=503,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
        if not request.to_email or not request.start_url or not request.dashboard_url:
            error_response = error_handler.create_error_response(
                message="Email, start_url, and dashboard_url are required",
                error_code="INVALID_INPUT",
                status_code=400,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
        result = await smtp2go_email_service.send_welcome_email(
            to_email=request.to_email,
            start_url=request.start_url,
            dashboard_url=request.dashboard_url,
            docs_url=request.docs_url,
            user_name=request.user_name,
        )
        if result.success:
            return create_success_response(
                data={"email": request.to_email, "message_id": result.message_id},
                message="Welcome email sent successfully",
            )
        else:
            error_response = error_handler.create_error_response(
                message=result.error_message or "Failed to send welcome email",
                error_code="EMAIL_SEND_FAILED",
                status_code=500,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
    except Exception as e:
        logger.error(f"Unexpected error during welcome email send: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Internal server error occurred during welcome email send",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"], content=error_response
        )


@router.post(
    "/send-deployment-success",
    response_model=SignupResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Bad Request - Invalid input"},
        500: {"model": AuthErrorResponse, "description": "Internal Server Error"},
    },
    summary="Send Deployment Success Email",
    description="""
    Send a deployment success email after infrastructure is deployed.
    **Request Body:**
    ```json
    {
      "to_email": "user@example.com",
      "deployment_id": "dep_123456",
      "cloud_provider": "aws",
      "region": "us-west-2",
      "generation_id": "gen_789012",
      "elapsed_time": "5m 32s",
      "resources": [
        {"type": "EC2 Instance", "name": "web-server", "estimated_cost": "$45/month"},
        {"type": "Security Group", "name": "web-sg", "estimated_cost": "$0/month"}
      ],
      "deployments_url": "https://iacgenie.ai/deployments",
      "user_name": "John Doe"
    }
    ```
    """,
)
async def send_deployment_success_email(request: SendDeploymentSuccessRequest) -> Any:
    """Send deployment success email"""
    try:
        if not EMAIL_SERVICE_AVAILABLE:
            error_response = error_handler.create_error_response(
                message="Email service not available. Please configure SMTP2GO settings.",
                error_code="EMAIL_SERVICE_UNAVAILABLE",
                status_code=503,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
        required_fields = [
            "to_email",
            "deployment_id",
            "cloud_provider",
            "region",
            "generation_id",
            "elapsed_time",
            "resources",
            "deployments_url",
        ]
        for field in required_fields:
            if not getattr(request, field):
                error_response = error_handler.create_error_response(
                    message=f"Required field missing: {field}",
                    error_code="INVALID_INPUT",
                    status_code=400,
                )
                return JSONResponse(
                    status_code=error_response["error"]["statusCode"],
                    content=error_response,
                )
        result = await smtp2go_email_service.send_deployment_success_email(
            to_email=request.to_email,
            deployment_id=request.deployment_id,
            cloud_provider=request.cloud_provider,
            region=request.region,
            generation_id=request.generation_id,
            elapsed_time=request.elapsed_time,
            resources=request.resources,
            deployments_url=request.deployments_url,
            user_name=request.user_name,
        )
        if result.success:
            return create_success_response(
                data={"email": request.to_email, "message_id": result.message_id},
                message="Deployment success email sent successfully",
            )
        else:
            error_response = error_handler.create_error_response(
                message=result.error_message
                or "Failed to send deployment success email",
                error_code="EMAIL_SEND_FAILED",
                status_code=500,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
    except Exception as e:
        logger.error(f"Unexpected error during deployment success email send: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Internal server error occurred during deployment success email send",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"], content=error_response
        )


@router.post(
    "/send-generation-complete",
    response_model=SignupResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Bad Request - Invalid input"},
        500: {"model": AuthErrorResponse, "description": "Internal Server Error"},
    },
    summary="Send Generation Complete Email",
    description="""
    Send a generation completion email after code is generated.
    **Request Body:**
    ```json
    {
      "to_email": "user@example.com",
      "generation_id": "gen_123456",
      "ai_model": "google-gemini-1.5-flash",
      "cloud_provider": "aws",
      "file_count": 6,
      "total_lines": 450,
      "files": [
        {"name": "main.tf", "lines": 120, "size": "4.5KB"},
        {"name": "variables.tf", "lines": 30, "size": "1.2KB"}
      ],
      "quality_score": 85,
      "security_score": 90,
      "efficiency_score": 78,
      "dashboard_url": "https://iacgenie.ai/generations/abc123",
      "user_name": "John Doe"
    }
    ```
    """,
)
async def send_generation_complete_email(request: SendGenerationCompleteRequest) -> Any:
    """Send generation completion email"""
    try:
        if not EMAIL_SERVICE_AVAILABLE:
            error_response = error_handler.create_error_response(
                message="Email service not available. Please configure SMTP2GO settings.",
                error_code="EMAIL_SERVICE_UNAVAILABLE",
                status_code=503,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
        required_fields = [
            "to_email",
            "generation_id",
            "ai_model",
            "cloud_provider",
            "file_count",
            "total_lines",
            "files",
            "quality_score",
            "security_score",
            "efficiency_score",
            "dashboard_url",
        ]
        for field in required_fields:
            if not getattr(request, field):
                error_response = error_handler.create_error_response(
                    message=f"Required field missing: {field}",
                    error_code="INVALID_INPUT",
                    status_code=400,
                )
                return JSONResponse(
                    status_code=error_response["error"]["statusCode"],
                    content=error_response,
                )
        result = await smtp2go_email_service.send_generation_complete_email(
            to_email=request.to_email,
            generation_id=request.generation_id,
            ai_model=request.ai_model,
            cloud_provider=request.cloud_provider,
            file_count=request.file_count,
            total_lines=request.total_lines,
            files=request.files,
            quality_score=request.quality_score,
            security_score=request.security_score,
            efficiency_score=request.efficiency_score,
            dashboard_url=request.dashboard_url,
            user_name=request.user_name,
        )
        if result.success:
            return create_success_response(
                data={"email": request.to_email, "message_id": result.message_id},
                message="Generation complete email sent successfully",
            )
        else:
            error_response = error_handler.create_error_response(
                message=result.error_message
                or "Failed to send generation complete email",
                error_code="EMAIL_SEND_FAILED",
                status_code=500,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
    except Exception as e:
        logger.error(
            f"Unexpected error during generation complete email send: {str(e)}"
        )
        error_response = error_handler.create_error_response(
            message="Internal server error occurred during generation complete email send",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"], content=error_response
        )


@router.post(
    "/verify-otp-and-login",
    response_model=SignupResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Bad Request - Invalid input"},
        401: {
            "model": AuthErrorResponse,
            "description": "Unauthorized - Invalid token",
        },
        500: {"model": AuthErrorResponse, "description": "Internal Server Error"},
    },
    summary="Verify OTP and Login",
    description="""
    Verify an OTP token and login the user without requiring password.
    This endpoint is used for password reset flow where OTP verification
    authenticates the user without a password.
    **Request Body:**
    ```json
    {
      "token": "otp_verification_token"
    }
    ```
    **Success Response:**
    ```json
    {
      "success": true,
      "message": "OTP verified successfully. Login successful.",
      "data": {
        "user": {
          "uid": "user-id",
          "email": "user@example.com",
          "displayName": "User Name"
        },
        "token": "auth_token_here",
        "expiresIn": 3600
      }
    }
    ```
    **Error Responses:**
    - 400: Invalid or expired token
    - 500: Internal server error
    """,
)
async def verify_otp_and_login(request: OtpVerificationRequest) -> Any:
    """
    Verify OTP token and login user without password.
    This endpoint is specifically for password reset flow where
    OTP verification authenticates the user without requiring a new password.
    """
    try:
        if not request.token or not request.token.strip():
            error_response = error_handler.create_error_response(
                message="Token is required and cannot be empty",
                error_code="INVALID_INPUT",
                status_code=400,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
        if not LOCAL_AUTH_AVAILABLE:
            error_response = error_handler.create_error_response(
                message="Authentication provider not available",
                error_code="INTERNAL_ERROR",
                status_code=500,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
        # Verify OTP token
        is_valid, user_id, email, error_message = verify_otp_token(request.token)
        if not is_valid:
            error_response = error_handler.create_error_response(
                message=error_message or "Invalid or expired token",
                error_code="INVALID_TOKEN",
                status_code=401,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
        # Get user from database
        user = await db_provider.get_user(user_id)  # type: ignore[arg-type]
        if not user:
            error_response = error_handler.create_error_response(
                message="User not found", error_code="USER_NOT_FOUND", status_code=404
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
        # Get stored OTP hash from database for this user
        stored_otp_hash = user.get("password_reset_otp_hash")
        if not stored_otp_hash:
            error_response = error_handler.create_error_response(
                message="OTP not found. Please request a new verification code.",
                error_code="OTP_NOT_FOUND",
                status_code=400,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
        # Verify OTP by decoding the token and comparing hash
        try:
            from utils.jwt_utils import JWT_SECRET, JWT_ALGORITHM
            import jwt

            # Decode token without verification to get OTP hash
            decoded_token = jwt.decode(
                request.token,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
                options={"verify_exp": False},
            )
            token_otp_hash = decoded_token.get("otp_hash")
            if not token_otp_hash:
                error_response = error_handler.create_error_response(
                    message="Invalid token structure",
                    error_code="INVALID_TOKEN",
                    status_code=400,
                )
                return JSONResponse(
                    status_code=error_response["error"]["statusCode"],
                    content=error_response,
                )
            # Verify the OTP hash matches (token contains partial hash)
            if token_otp_hash != stored_otp_hash[:8]:
                error_response = error_handler.create_error_response(
                    message="Invalid OTP", error_code="INVALID_OTP", status_code=401
                )
                return JSONResponse(
                    status_code=error_response["error"]["statusCode"],
                    content=error_response,
                )
        except jwt.InvalidTokenError:
            error_response = error_handler.create_error_response(
                message="Invalid OTP token", error_code="INVALID_TOKEN", status_code=401
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
        except Exception as e:
            logger.error(f"Failed to verify OTP token: {str(e)}")
            error_response = error_handler.create_error_response(
                message="Failed to verify OTP",
                error_code="INTERNAL_ERROR",
                status_code=500,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
        logger.info(f"OTP verified successfully for user {user_id}")
        # Generate new authentication token (no password needed)
        try:
            auth_token = generate_token(
                user_id=user_id,  # type: ignore[arg-type]
                email=email,  # type: ignore[arg-type]
                role=user.get("role", "user"),
            )
        except JWTError as e:
            logger.warning(f"Failed to generate auth token: {str(e)}")
            auth_token = None
        return create_success_response(
            data={
                "user": {
                    "uid": user_id,
                    "email": email,
                    "displayName": user.get("name", ""),
                    "role": user.get("role", "user"),
                },
                "token": auth_token,
                "expiresIn": 3600,
            },
            message="OTP verified successfully. Login successful.",
        )
    except Exception as e:
        logger.error(f"Unexpected error during OTP verification and login: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Internal server error occurred during OTP verification",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"], content=error_response
        )


@router.post(
    "/send-security-alert",
    response_model=SignupResponse,
    responses={
        400: {"model": AuthErrorResponse, "description": "Bad Request - Invalid input"},
        500: {"model": AuthErrorResponse, "description": "Internal Server Error"},
    },
    summary="Send Security Alert Email",
    description="""
    Send a security alert email for password changes or suspicious activity.
    **Request Body:**
    ```json
    {
      "to_email": "user@example.com",
      "alert_id": "sec_123456",
      "change_timestamp": "2026-03-23 10:45:00 UTC",
      "ip_address": "192.168.1.100",
      "device_info": "Chrome 122 on Windows 11",
      "location": "New York, NY, United States",
      "security_center_url": "https://iacgenie.ai/settings/security",
      "user_name": "John Doe"
    }
    ```
    """,
)
async def send_security_alert_email(request: SendSecurityAlertRequest) -> Any:
    """Send security alert email"""
    try:
        if not EMAIL_SERVICE_AVAILABLE:
            error_response = error_handler.create_error_response(
                message="Email service not available. Please configure SMTP2GO settings.",
                error_code="EMAIL_SERVICE_UNAVAILABLE",
                status_code=503,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
        required_fields = [
            "to_email",
            "alert_id",
            "change_timestamp",
            "ip_address",
            "device_info",
            "location",
            "security_center_url",
        ]
        for field in required_fields:
            if not getattr(request, field):
                error_response = error_handler.create_error_response(
                    message=f"Required field missing: {field}",
                    error_code="INVALID_INPUT",
                    status_code=400,
                )
                return JSONResponse(
                    status_code=error_response["error"]["statusCode"],
                    content=error_response,
                )
        result = await smtp2go_email_service.send_security_alert_email(
            to_email=request.to_email,
            alert_id=request.alert_id,
            change_timestamp=request.change_timestamp,
            ip_address=request.ip_address,
            device_info=request.device_info,
            location=request.location,
            security_center_url=request.security_center_url,
            user_name=request.user_name,
        )
        if result.success:
            return create_success_response(
                data={"email": request.to_email, "message_id": result.message_id},
                message="Security alert email sent successfully",
            )
        else:
            error_response = error_handler.create_error_response(
                message=result.error_message or "Failed to send security alert email",
                error_code="EMAIL_SEND_FAILED",
                status_code=500,
            )
            return JSONResponse(
                status_code=error_response["error"]["statusCode"],
                content=error_response,
            )
    except Exception as e:
        logger.error(f"Unexpected error during security alert email send: {str(e)}")
        error_response = error_handler.create_error_response(
            message="Internal server error occurred during security alert email send",
            error_code="INTERNAL_ERROR",
            status_code=500,
        )
        return JSONResponse(
            status_code=error_response["error"]["statusCode"], content=error_response
        )


# ==========================================

# Refresh Token Endpoint

# ==========================================


@router.post(
    "/refresh",
    responses={
        400: {
            "model": AuthErrorResponse,
            "description": "Bad Request - Missing refresh token",
        },
        401: {
            "model": AuthErrorResponse,
            "description": "Unauthorized - Invalid or expired refresh token",
        },
        500: {"model": AuthErrorResponse, "description": "Internal Server Error"},
    },
    summary="Refresh Access Token",
    description="""
    Refresh an access token using a valid refresh token.
    Implements refresh token rotation for security: each refresh invalidates the old
    refresh token and issues a new access + refresh token pair.
    **Request Body:**
    ```json
    {
      "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6..."
    }
    ```
    **Response:**
    ```json
    {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6...",
      "token_type": "Bearer",
      "expires_in": 3600,
      "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6..."
    }
    ```
    """,
)
async def refresh_access_token(request: Request) -> Any:
    """Refresh an access token using a valid refresh token with rotation"""
    try:
        from db.db_provider import db_provider as db

        # Parse request body
        body = await request.json()
        refresh_token_str = body.get("refresh_token") if body else None
        if not refresh_token_str:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "INVALID_INPUT",
                    "message": "refresh_token is required",
                    "code": "MISSING_REFRESH_TOKEN",
                },
            )
        # Hash the refresh token for DB lookup
        from utils.jwt_utils import get_refresh_token_hash

        token_hash = get_refresh_token_hash(refresh_token_str)
        # Check if token exists and is not revoked (use adapter directly)
        token_record = None
        if hasattr(db, "adapter"):
            adapter = db.adapter
            if hasattr(adapter, "get_refresh_token_by_hash"):
                token_record = await adapter.get_refresh_token_by_hash(token_hash)
        if not token_record:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "AUTHENTICATION_REQUIRED",
                    "message": "Invalid refresh token",
                    "code": "INVALID_REFRESH_TOKEN",
                },
            )
        # Check expiration
        expires_at = token_record.get("expires_at")
        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)
        if expires_at < datetime.utcnow():
            # Revoke expired token
            if hasattr(db, "adapter") and hasattr(
                db.adapter, "revoke_refresh_token_by_hash"
            ):
                await db.adapter.revoke_refresh_token_by_hash(token_hash)
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "AUTHENTICATION_REQUIRED",
                    "message": "Refresh token has expired",
                    "code": "EXPIRED_REFRESH_TOKEN",
                },
            )
        # Get user info
        user = await db.get_user(token_record["user_id"])
        if not user:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "AUTHENTICATION_REQUIRED",
                    "message": "User not found",
                    "code": "USER_NOT_FOUND",
                },
            )
        # Rotate: revoke old token, issue new ones
        if hasattr(db, "adapter") and hasattr(
            db.adapter, "revoke_refresh_token_by_hash"
        ):
            await db.adapter.revoke_refresh_token_by_hash(token_hash)
        # Generate new access token
        from utils.jwt_utils import (
            generate_token,
            generate_refresh_token as gen_refresh,
        )

        new_access_token = generate_token(
            user_id=user["id"], email=user["email"], role=user.get("role", "user")
        )
        # Generate new refresh token
        new_refresh_str, new_refresh_meta = gen_refresh(
            user_id=user["id"], client_id=token_record.get("client_id", "web-app")
        )
        new_refresh_meta["rotated_from_id"] = token_record.get("id")
        if hasattr(db, "adapter") and hasattr(db.adapter, "create_refresh_token"):
            await db.adapter.create_refresh_token(new_refresh_meta)
        # Log the rotation in auth audit logs
        if hasattr(db, "adapter") and hasattr(db.adapter, "create_auth_audit_log"):
            await db.adapter.create_auth_audit_log(
                {
                    "event_type": "token_refreshed",
                    "user_id": user["id"],
                    "success": True,
                }
            )
        return {
            "access_token": new_access_token,
            "token_type": "Bearer",
            "expires_in": 3600,
            "refresh_token": new_refresh_str,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error during token refresh: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "INTERNAL_ERROR",
                "message": "Internal server error during token refresh",
            },
        )


# ==========================================

# Config and Logout endpoints

# ==========================================


@router.get(
    "/config",
    summary="Get Authentication Configuration",
    description="Returns the current authentication configuration, including active provider and capabilities.",
)
async def get_auth_config() -> Any:
    """Get active auth provider and capabilities"""
    try:
        from auth_providers.factory import AuthProviderFactory

        provider_name = os.getenv("AUTH_PROVIDER", "local").lower()
        try:
            from auth_providers.factory import create_auth_provider

            provider = create_auth_provider(provider_name)
        except ValueError:
            provider = None
        return {
            "active_provider": provider_name,
            "available_providers": AuthProviderFactory.get_available_providers(),
            "capabilities": {
                "sso": provider_name in ["keycloak", "saml"],
                "password_reset": hasattr(provider, "send_password_reset"),
                "otp_verification": hasattr(provider, "verify_otp"),
            },
        }
    except Exception as e:
        logger.error(f"Failed to get auth config: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/logout",
    summary="Logout user",
    description="Logout a user by revoking their refresh token and access token.",
)
async def logout(request: Request) -> Any:
    """Logout and invalidate refresh token and access token"""
    try:
        from db.db_provider import db_provider as db

        body = await request.json()
        refresh_token_str = body.get("refresh_token")
        if not refresh_token_str:
            return {
                "success": True,
                "message": "Logged out successfully (no token provided)",
            }
        from utils.jwt_utils import get_refresh_token_hash

        token_hash = get_refresh_token_hash(refresh_token_str)
        if hasattr(db, "adapter") and hasattr(
            db.adapter, "revoke_refresh_token_by_hash"
        ):
            await db.adapter.revoke_refresh_token_by_hash(token_hash)
        # Revoke access token's jti if provided
        access_token_str = body.get("access_token")
        if access_token_str:
            try:
                from utils.token_revocation import get_revocation_store
                import jwt as pyjwt

                payload = pyjwt.decode(
                    access_token_str,
                    # nosemgrep: python.jwt.security.unverified-jwt-decode.unverified-jwt-decode
                    options={
                        # nosemgrep: python.jwt.security.unverified-jwt-decode.unverified-jwt-decode
                        "verify_signature": False,
                        "verify_exp": False,
                        "verify_aud": False,
                        "verify_iss": False,
                    },
                )
                jti = payload.get("jti")
                exp = payload.get("exp")
                if jti and exp:
                    store = get_revocation_store()
                    if store.enabled:
                        try:
                            await store.revoke(
                                jti,
                                user_id=payload.get("sub", ""),
                                expires_at_timestamp=exp,
                            )
                        except Exception as e:
                            logger.warning(
                                f"Failed to revoke access token during logout: {e}"
                            )
            except Exception as e:
                logger.warning(f"Failed to revoke access token during logout: {e}")
        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        logger.error(f"Failed to logout: {str(e)}")
        return {"success": True, "message": "Logged out successfully (with errors)"}


# Google OAuth via Keycloak Identity Provider
@router.get("/google")
async def google_login(request: Request) -> RedirectResponse:
    """Redirect user to Keycloak's Google Identity Provider login"""
    from auth_providers.keycloak import (
        KEYCLOAK_URL,
        KEYCLOAK_REALM,
        KeycloakAuthProvider,
    )

    if not KEYCLOAK_URL or not KEYCLOAK_REALM:
        raise HTTPException(
            status_code=503,
            detail="Keycloak not configured. Set KEYCLOAK_URL and KEYCLOAK_REALM environment variables.",
        )
    provider = KeycloakAuthProvider()
    auth_url, code_verifier = provider.get_authorization_url(
        state=request.query_params.get("state"),
        redirect_uri=request.query_params.get("redirect_uri"),
        idp_hint="google",
    )
    response = RedirectResponse(url=auth_url, status_code=302)
    response.set_cookie(
        key="keycloak_code_verifier",
        value=code_verifier,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=300,
    )
    return response


# GitHub OAuth via Keycloak Identity Provider
@router.get("/github")
async def github_login(request: Request) -> RedirectResponse:
    """Redirect user to Keycloak's GitHub Identity Provider login"""
    from auth_providers.keycloak import (
        KEYCLOAK_URL,
        KEYCLOAK_REALM,
        KeycloakAuthProvider,
    )

    if not KEYCLOAK_URL or not KEYCLOAK_REALM:
        raise HTTPException(
            status_code=503,
            detail="Keycloak not configured. Set KEYCLOAK_URL and KEYCLOAK_REALM environment variables.",
        )
    provider = KeycloakAuthProvider()
    auth_url, code_verifier = provider.get_authorization_url(
        state=request.query_params.get("state"),
        redirect_uri=request.query_params.get("redirect_uri"),
        idp_hint="github",
    )
    response = RedirectResponse(url=auth_url, status_code=302)
    response.set_cookie(
        key="keycloak_code_verifier",
        value=code_verifier,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=300,
    )
    return response


# =============================================================================

# Keycloak OAuth2/OIDC Routes

# =============================================================================


@router.get("/keycloak/login")
async def keycloak_login(
    request: Request,
    redirect_uri: Optional[str] = Query(
        None, description="Frontend redirect URI for post-login return"
    ),
    state: Optional[str] = Query(None, description="Optional CSRF state parameter"),
) -> RedirectResponse:
    """Redirect user to Keycloak authorization page with PKCE"""
    from auth_providers.keycloak import (
        KEYCLOAK_URL,
        KEYCLOAK_REALM,
        KeycloakAuthProvider,
    )

    if not KEYCLOAK_URL or not KEYCLOAK_REALM:
        raise HTTPException(
            status_code=503,
            detail="Keycloak not configured. Set KEYCLOAK_URL and KEYCLOAK_REALM environment variables.",
        )
    provider = KeycloakAuthProvider()
    auth_url, code_verifier = provider.get_authorization_url(
        state=state,
        redirect_uri=redirect_uri,
    )
    # Store code_verifier in secure httpOnly cookie for callback verification
    response = RedirectResponse(url=auth_url, status_code=302)
    response.set_cookie(
        key="keycloak_code_verifier",
        value=code_verifier,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=300,  # 5 minutes
    )
    return response


@router.get("/keycloak/callback")
async def keycloak_callback(
    request: Request,
    code: Optional[str] = Query(None, description="Authorization code from Keycloak"),
    state: Optional[str] = Query(None, description="CSRF state parameter"),
    error: Optional[str] = Query(None, description="Error from Keycloak"),
    redirect: Optional[str] = Query(None, description="Custom frontend redirect URL"),
) -> RedirectResponse:
    """Exchange Keycloak authorization code for tokens, create login session"""
    from urllib.parse import urlencode
    from auth_providers.keycloak import KeycloakAuthProvider

    frontend_base = redirect or os.getenv("VITE_API_BASE_URL", "http://localhost:5173")
    # Handle Keycloak error
    if error:
        desc = request.query_params.get(
            "error_description", "Keycloak authentication failed"
        )
        return RedirectResponse(url=f"{frontend_base}/signin?error={desc}")
    if not code:
        return RedirectResponse(
            url=f"{frontend_base}/signin?error=Invalid callback parameters"
        )
    # Retrieve code_verifier from cookie (set by login endpoint)
    cookie_val = request.cookies.get("keycloak_code_verifier")
    if not cookie_val:
        return RedirectResponse(
            url=f"{frontend_base}/signin?error=Authentication session expired. Please try again."
        )
    # Clear the code_verifier cookie
    response = RedirectResponse(
        url=f"{frontend_base}/signin?pending=true", status_code=302
    )
    response.delete_cookie(key="keycloak_code_verifier")
    try:
        provider = KeycloakAuthProvider()
        redirect_uri = (
            f"{os.getenv('VITE_API_BASE_URL', 'http://localhost:5173')}/auth/callback"
        )
        result = await provider.authenticate_with_code(
            code=code,
            code_verifier=cookie_val,
            redirect_uri=redirect_uri,
        )
        if not result.success or not result.token:
            error_msg = (
                result.error.message
                if result.error
                else "Keycloak authentication failed"
            )
            return RedirectResponse(url=f"{frontend_base}/signin?error={error_msg}")
        # Redirect frontend with local JWT and Keycloak refresh token
        params = urlencode({"token": result.token, "provider": "keycloak"})
        if result.refresh_token:
            params += f"&kc_refresh_token={result.refresh_token}"
        return RedirectResponse(url=f"{frontend_base}/auth/callback?{params}")
    except Exception as e:
        logger.error(f"Keycloak callback failed: {e}")
        return RedirectResponse(
            url=f"{frontend_base}/signin?error=Keycloak authentication failed"
        )


@router.post("/keycloak/logout")
async def keycloak_logout(request: Request) -> Dict[str, Any]:
    """Invalidate local token and terminate Keycloak IdP session"""
    from auth_providers.keycloak import KeycloakAuthProvider

    # Extract Bearer token from Authorization header
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    token = auth_header[7:]
    user_id = None
    # Invalidate the local JWT and extract user ID
    try:
        import jwt as pyjwt

        payload = pyjwt.decode(
            token,
            # nosemgrep: python.jwt.security.unverified-jwt-decode.unverified-jwt-decode
            options={
                "verify_signature": False,  # nosemgrep: python.jwt.security.unverified-jwt-decode.unverified-jwt-decode
                "verify_exp": False,
                "verify_aud": False,
                "verify_iss": False,
            },
        )
        user_id = payload.get("sub")
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp and user_id:
            try:
                from utils.token_revocation import get_revocation_store

                store = get_revocation_store()
                if store.enabled:
                    try:
                        await store.revoke(
                            jti, user_id=str(user_id), expires_at_timestamp=exp
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to revoke access token during logout: {e}"
                        )
            except Exception as e:
                logger.warning(f"Failed to revoke access token during logout: {e}")
    except Exception:
        pass  # Token already expired or invalid — still try Keycloak logout below
    # If token decode failed, fall back to user_id from request body
    if not user_id:
        try:
            body = await request.json()
            user_id = body.get("user_id")
        except Exception:
            pass
    if not user_id:
        return {"success": True, "message": "Logged out successfully"}
    # Terminate Keycloak session using stored refresh token
    try:
        provider = KeycloakAuthProvider()
        await provider.terminate_keycloak_session(user_id)
    except Exception as e:
        logger.warning(f"Keycloak session logout failed (non-critical): {e}")
    return {"success": True, "message": "Logged out successfully"}
