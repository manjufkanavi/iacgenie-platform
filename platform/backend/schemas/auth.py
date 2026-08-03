"""

Authentication schemas for Iacgenie AI

"""

from pydantic import BaseModel, Field, ConfigDict, field_validator

from typing import Optional


def validate_email(v: str) -> str:
    """Validate email but allow .local, .test and .localhost domains for local development"""
    if v is None:
        return v
    if isinstance(v, str):
        v = v.strip()
    if not v:
        raise ValueError("Email cannot be empty")
    # Allow standard email formats and .local/.test/.localhost domains for local development
    if "@" in v:
        domain = v.split("@")[-1].lower()
        # Allow standard TLDs and local development domains
        allowed_domains = [".local", ".test", ".localhost"]
        has_valid_tld = "." in domain and domain.split(".")[-1].isalpha()
        if has_valid_tld or any(domain.endswith(d) for d in allowed_domains):
            return v
    # Use default EmailStr validation for standard emails
    try:
        from pydantic import EmailStr

        return str(EmailStr(v))
    except Exception:
        raise ValueError("Invalid email format")


class TokenRequest(BaseModel):
    """Request schema for unified authentication endpoint"""

    action: Optional[str] = Field(
        None,
        description="Authentication action: 'login', 'signup', 'reset_password', or 'verify_token'",
        examples=["login"],
    )
    email: Optional[str] = Field(
        None,
        description="User's email address (required for login, signup, reset_password)",
        examples=["user@example.com"],
    )
    password: Optional[str] = Field(
        None,
        description="User's password (required for login, signup, minimum 6 characters)",
        min_length=6,
        examples=["userpassword123"],
    )
    token: Optional[str] = Field(
        None,
        description="Authentication token (for verify_token action or token-based login)",
        examples=["eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    displayName: Optional[str] = Field(
        None,
        description="User's display name (for signup action)",
        examples=["John Doe"],
    )
    firstName: Optional[str] = Field(
        None,
        description="User's first name (for signup action)",
        examples=["John"],
    )
    lastName: Optional[str] = Field(
        None,
        description="User's last name (for signup action)",
        examples=["Doe"],
    )

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, v: Optional[str]) -> Optional[str]:
        """Validate email format if provided"""
        if v is None:
            return v
        return validate_email(v)

    def __init__(self, **data):
        super().__init__(**data)
        # Validate based on action
        if self.action == "login":
            if not (self.email and self.password):
                raise ValueError("Email and password are required for login")
        elif self.action == "signup":
            if not (self.email and self.password):
                raise ValueError("Email and password are required for signup")
        elif self.action == "reset_password":
            if not self.email:
                raise ValueError("Email is required for password reset")
        elif self.action == "verify_token":
            if not self.token:
                raise ValueError("Token is required for token verification")
        elif not self.action:
            # Backward compatibility: if no action specified, use old logic
            if not ((self.email and self.password) or self.token):
                raise ValueError("Either email/password or token must be provided")


class SignupRequest(BaseModel):
    """Request schema for user registration"""

    model_config = ConfigDict(validate_default=True)
    email: str = Field(
        ..., description="User's email address", examples=["user@example.com"]
    )
    password: str = Field(
        ...,
        description="User's password (minimum 6 characters)",
        min_length=6,
        examples=["userpassword123"],
    )
    displayName: Optional[str] = Field(
        None, description="User's display name", examples=["John Doe"]
    )
    firstName: Optional[str] = Field(
        None, description="User's first name", examples=["John"]
    )
    lastName: Optional[str] = Field(
        None, description="User's last name", examples=["Doe"]
    )

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, v: str) -> str:
        """Validate email format allowing .local, .test and .localhost domains"""
        return validate_email(v)

    @field_validator("password")
    @classmethod
    def validate_password_field(cls, v: str) -> str:
        """Validate password strength based on environment policy"""
        import os

        min_len = int(os.getenv("PASSWORD_MIN_LENGTH", "8"))
        req_upper = os.getenv("PASSWORD_REQUIRE_UPPERCASE", "true").lower() == "true"
        req_lower = os.getenv("PASSWORD_REQUIRE_LOWERCASE", "true").lower() == "true"
        req_num = os.getenv("PASSWORD_REQUIRE_NUMBER", "true").lower() == "true"
        req_special = os.getenv("PASSWORD_REQUIRE_SPECIAL", "true").lower() == "true"

        if len(v) < min_len:
            raise ValueError(f"Password must be at least {min_len} characters long")
        if req_upper and not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if req_lower and not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if req_num and not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one number")
        if req_special and not any(not c.isalnum() for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class PasswordResetRequest(BaseModel):
    """Request schema for password reset"""

    model_config = ConfigDict(validate_default=True)
    email: str = Field(
        ..., description="User's email address", examples=["user@example.com"]
    )

    @field_validator("email")
    @classmethod
    def validate_email_field(cls, v: str) -> str:
        """Validate email format allowing .local, .test and .localhost domains"""
        return validate_email(v)


class TokenResponse(BaseModel):
    """Response schema for successful authentication"""

    success: bool = Field(True, description="Operation success status")
    message: str = Field("Authentication successful", description="Success message")
    data: dict = Field(
        ...,
        description="Authentication data",
        examples=[
            {
                "token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
                "expiresIn": 3600,
                "user": {
                    "uid": "user123",
                    "email": "user@example.com",
                    "emailVerified": True,
                },
            }
        ],
    )
    timestamp: str = Field(..., description="ISO timestamp of response")


class SignupResponse(BaseModel):
    """Response schema for successful user registration"""

    success: bool = Field(True, description="Operation success status")
    message: str = Field("User registered successfully", description="Success message")
    data: dict = Field(
        ...,
        description="Registration data",
        examples=[
            {
                "uid": "user123",
                "email": "user@example.com",
                "emailVerified": False,
                "message": "Please check your email to verify your account",
            }
        ],
    )
    timestamp: str = Field(..., description="ISO timestamp of response")


class PasswordResetResponse(BaseModel):
    """Response schema for password reset request"""

    success: bool = Field(True, description="Operation success status")
    message: str = Field("Password reset email sent", description="Success message")
    data: dict = Field(
        ...,
        description="Reset data",
        examples=[
            {
                "email": "user@example.com",
                "message": "If this email exists, a password reset link has been sent",
            }
        ],
    )
    timestamp: str = Field(..., description="ISO timestamp of response")


class TokenVerifyRequest(BaseModel):
    """Request schema for token verification"""

    token: str = Field(
        ...,
        description="Authentication token to verify",
        examples=["eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )


class TokenVerifyResponse(BaseModel):
    """Response schema for token verification"""

    success: bool = Field(True, description="Operation success status")
    message: str = Field("Token is valid", description="Verification message")
    data: dict = Field(
        ...,
        description="Token claims and user information",
        examples=[
            {
                "valid": True,
                "claims": {
                    "sub": "user123",
                    "email": "user@example.com",
                    "email_verified": True,
                    "iat": 1640995200,
                    "exp": 1640998800,
                },
                "user": {
                    "uid": "user123",
                    "email": "user@example.com",
                    "emailVerified": True,
                },
            }
        ],
    )
    timestamp: str = Field(..., description="ISO timestamp of response")


class AuthErrorResponse(BaseModel):
    """Error response schema for authentication failures"""

    success: bool = Field(False, description="Operation success status")
    error: dict = Field(
        ...,
        description="Error details",
        examples=[
            {
                "code": "INVALID_CREDENTIALS",
                "message": "The email or password provided is incorrect.",
                "statusCode": 401,
                "details": {},
                "timestamp": "2025-01-06T17:00:00.000Z",
            }
        ],
    )


class OAuthResponse(BaseModel):
    """OAuth/OIDC authentication response schema"""

    accessToken: str = Field(..., description="OAuth access token")
    email: str = Field(..., description="User's email address")
    refreshToken: str = Field(..., description="Refresh token")
    expiresIn: str = Field(..., description="Token expiration time in seconds")
    provider: str = Field(..., description="Auth provider name")
    registered: bool = Field(..., description="Whether the user is newly registered")


class OtpRequest(BaseModel):
    """Request model for OTP verification"""

    token: str = Field(..., description="The OTP JWT token")
    otp: Optional[str] = Field(None, description="The 6-digit OTP code")


class ResendOtpRequest(BaseModel):
    """Request model for resending OTP"""

    token: str = Field(..., description="The original OTP JWT token")
    email: str = Field(..., description="User email")


class VerifyOtpForPasswordResetRequest(BaseModel):
    """Request model for verify OTP for password reset"""

    token: str = Field(..., description="The OTP JWT token")
    otp: Optional[str] = Field(None, description="The 6-digit OTP code")


class PasswordResetWithOtpRequest(BaseModel):
    """Request model for resetting password using verified reset_token"""

    token: str = Field(..., description="The verified reset token")
    new_password: str = Field(..., description="The new password")


class OtpVerificationRequest(BaseModel):
    """Request model for OTP verification and login"""

    token: str = Field(..., description="The OTP JWT token")
    otp: Optional[str] = Field(None, description="The 6-digit OTP code")


class ForgotPasswordOtpRequest(BaseModel):
    """Request model for forgot password OTP"""

    email: str = Field(..., description="User's email address")


class ResendOtpResponse(BaseModel):
    """Response model for resending OTP"""

    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: Optional[dict] = None
    timestamp: str = Field(..., description="ISO timestamp")


class OtpVerificationResponse(BaseModel):
    """Response model for OTP verification"""

    success: bool = Field(True, description="Operation success status")
    message: str = Field(..., description="Success message")
    data: dict = Field(...)
    timestamp: str = Field(..., description="ISO timestamp")


class RefreshTokenRequest(BaseModel):
    """Request model for refreshing token"""

    refresh_token: str = Field(..., description="The refresh token string")
