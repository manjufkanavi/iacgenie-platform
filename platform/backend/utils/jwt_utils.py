"""

JWT Token Utilities

Provides JWT token generation and verification for local authentication.

"""

import jwt

import os


import uuid

from datetime import datetime, timedelta, timezone

from typing import Dict, Any, Optional, Tuple

from config.logging import get_logger

logger = get_logger("jwt_utils")


class JWTError(Exception):
    """JWT-related errors"""

    pass


class TokenExpiredError(JWTError):
    """Token has expired"""

    pass


class InvalidTokenError(JWTError):
    """Token is invalid"""

    pass


# Configuration


_jwt_secret = os.getenv("JWT_SECRET")

if not _jwt_secret:
    raise ValueError(
        "JWT_SECRET environment variable is required but not set. "
        "Set a cryptographically random secret (>= 32 bytes). "
        "Generate one with: python -c 'import secrets; print(secrets.token_urlsafe(64))'"
    )
# Validate minimum entropy: at least 32 bytes of unique characters

if len(set(_jwt_secret)) < 8:
    raise ValueError(
        "JWT_SECRET lacks sufficient entropy. "
        "Use at least 8 distinct characters (>= 32 random bytes recommended)."
    )
JWT_SECRET = _jwt_secret

del _jwt_secret  # Prevent accidental direct access

JWT_GRACE_SECRETS_ENV = os.getenv("JWT_GRACE_SECRETS", "")

JWT_GRACE_SECRETS = [s.strip() for s in JWT_GRACE_SECRETS_ENV.split(",") if s.strip()]

JWT_ALGORITHM = "HS256"

JWT_DEFAULT_EXPIRATION = int(
    os.getenv("JWT_EXPIRATION", "900")
)  # 15 minutes in seconds

JWT_REFRESH_EXPIRATION = int(
    os.getenv("JWT_REFRESH_EXPIRATION", "604800")
)  # 7 days in seconds

# Issuer and audience derived from env vars (brand-independent)

JWT_ISSUER = os.getenv("JWT_ISSUER", "iacgenie-api")

JWT_AUDIENCE = os.getenv("JWT_AUDIENCE", "iacgenie-frontend")

# OTP Configuration

OTP_LENGTH = int(os.getenv("OTP_LENGTH", "6"))

OTP_EXPIRATION_MINUTES = int(os.getenv("OTP_EXPIRATION_MINUTES", "10"))


def _decode_token_with_grace(token: str, **kwargs: Any) -> Dict[str, Any]:
    """Helper to decode tokens attempting JWT_SECRET then JWT_GRACE_SECRETS"""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM], **kwargs)
    except jwt.ExpiredSignatureError:
        raise
    except jwt.InvalidSignatureError:
        for secret in JWT_GRACE_SECRETS:
            try:
                return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM], **kwargs)
            except jwt.ExpiredSignatureError:
                raise
            except jwt.InvalidTokenError:
                continue
        raise


def generate_token(
    user_id: str,
    email: str,
    role: str = "user",
    expires_in: Optional[int] = None,
    additional_claims: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate a JWT token for a user
    Args:
        user_id: User's unique identifier
        email: User's email address
        role: User's role (default: 'user')
        expires_in: Token expiration time in seconds (default: from env)
        additional_claims: Additional claims to include in token
    Returns:
        JWT token string
    Raises:
        JWTError: If token generation fails
    """
    try:
        # Calculate expiration time
        expiration = expires_in or JWT_DEFAULT_EXPIRATION
        exp_time = datetime.now(timezone.utc) + timedelta(seconds=expiration)
        # Build payload
        payload = {
            "sub": user_id,  # Subject (user ID)
            "email": email,
            "role": role,
            "iat": int(datetime.now(timezone.utc).timestamp()),  # Issued at
            "exp": int(exp_time.timestamp()),  # Expiration
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
            "jti": str(uuid.uuid4()),  # Unique token identifier for revocation
        }
        # Add additional claims if provided
        if additional_claims:
            payload.update(additional_claims)
        # Generate token
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        logger.debug(f"Generated token for user {user_id}, expires at {exp_time}")
        return token
    except Exception as e:
        logger.error(f"Failed to generate token: {str(e)}")
        raise JWTError(f"Failed to generate token: {str(e)}")


def verify_token(token: str) -> Dict[str, Any]:
    """
    Verify and decode a JWT token
    Args:
        token: JWT token string to verify
    Returns:
        Decoded token payload
    Raises:
        TokenExpiredError: If token has expired
        InvalidTokenError: If token is invalid
        JWTError: For other JWT errors
    """
    try:
        # Decode and verify token
        payload = _decode_token_with_grace(
            token, audience=JWT_AUDIENCE, issuer=JWT_ISSUER
        )
        logger.debug(f"Verified token for user {payload.get('sub')}")
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        raise TokenExpiredError("Token has expired")
    except jwt.InvalidAudienceError:
        logger.warning("Invalid token audience")
        raise InvalidTokenError("Invalid token audience")
    except jwt.InvalidIssuerError:
        logger.warning("Invalid token issuer")
        raise InvalidTokenError("Invalid token issuer")
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        raise InvalidTokenError(f"Invalid token: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to verify token: {str(e)}")
        raise JWTError(f"Failed to verify token: {str(e)}")


def refresh_token(old_token: str) -> str:
    """
    Refresh an existing token
    Args:
        old_token: Existing JWT token to refresh
    Returns:
        New JWT token string
    Raises:
        TokenExpiredError: If old token has expired
        InvalidTokenError: If old token is invalid
        JWTError: For other JWT errors
    """
    try:
        # Verify old token
        payload = verify_token(old_token)
        # Generate new token with same claims
        new_token = generate_token(
            user_id=payload["sub"],
            email=payload["email"],
            role=payload.get("role", "user"),
            additional_claims={
                k: v
                for k, v in payload.items()
                if k not in ["sub", "email", "role", "iat", "exp", "iss", "aud"]
            },
        )
        logger.info(f"Refreshed token for user {payload['sub']}")
        return new_token
    except Exception as e:
        logger.error(f"Failed to refresh token: {str(e)}")
        raise JWTError(f"Failed to refresh token: {str(e)}")


def generate_refresh_token(
    user_id: str, client_id: Optional[str] = None
) -> Tuple[str, Dict[str, Any]]:
    """
    Generate a cryptographically secure refresh token and its metadata.
    Returns a plain-text token to return to the client, and a metadata dict
    containing the hashed token for database storage.
    Args:
        user_id: User's unique identifier
        client_id: Optional client identifier
    Returns:
        Tuple of (plain_refresh_token, token_metadata_dict)
        The plain token must be returned to the client.
        The metadata dict should be stored in the database.
    """
    import secrets
    import hashlib

    plain_token = secrets.token_urlsafe(64)  # ~86 chars of entropy
    token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
    expires_at = datetime.now(timezone.utc) + timedelta(
        seconds=JWT_REFRESH_EXPIRATION
    )  # 7 days
    metadata = {
        "user_id": user_id,
        "client_id": client_id or "web-app",
        "token_hash": token_hash,
        "expires_at": expires_at.isoformat(),
    }
    logger.info(f"Generated refresh token for user {user_id}")
    return plain_token, metadata


def get_refresh_token_hash(token: str) -> str:
    """
    Compute the SHA-256 hash of a refresh token for database lookup.
    Args:
        token: Plain-text refresh token
    Returns:
        Hex digest of the SHA-256 hash
    """
    import hashlib

    return hashlib.sha256(token.encode()).hexdigest()


def get_token_expiration(token: str) -> Optional[datetime]:
    """
    Get expiration time from a token without verifying it
    Args:
        token: JWT token string
    Returns:
        Expiration datetime or None if token is invalid
    """
    try:
        payload = _decode_token_with_grace(
            token,
            options={"verify_exp": False, "verify_aud": False, "verify_iss": False},
        )
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            return datetime.utcfromtimestamp(exp_timestamp)
        return None
    except Exception:
        return None


def is_token_expired(token: str) -> bool:
    """
    Check if a token has expired
    Args:
        token: JWT token string
    Returns:
        True if token is expired, False otherwise
    """
    try:
        exp_time = get_token_expiration(token)
        if not exp_time:
            return True
        return exp_time < datetime.now(timezone.utc)
    except Exception:
        return True


def extract_user_id(token: str) -> Optional[str]:
    """
    Extract user ID from a token without full verification
    Args:
        token: JWT token string
    Returns:
        User ID or None if token is invalid
    """
    try:
        payload = _decode_token_with_grace(
            token,
            options={"verify_exp": False, "verify_aud": False, "verify_iss": False},
        )
        return payload.get("sub")
    except Exception:
        return None


def generate_verification_token(user_id: str, email: str) -> str:
    """
    Generate an email verification token
    Args:
        user_id: User's unique identifier
        email: User's email address
    Returns:
        Verification token string
    """
    try:
        # Verification tokens have 24 hour expiration
        expiration = datetime.now(timezone.utc) + timedelta(hours=24)
        payload = {
            "sub": user_id,
            "email": email,
            "type": "email_verification",
            "iat": datetime.now(timezone.utc),
            "exp": expiration,
            "iss": JWT_ISSUER,
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        logger.info(f"Generated verification token for user {user_id}, email {email}")
        return token
    except Exception as e:
        logger.error(f"Failed to generate verification token: {str(e)}")
        raise JWTError(f"Failed to generate verification token: {str(e)}")


def verify_verification_token(
    token: str,
) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """
    Verify an email verification token
    Args:
        token: Verification token string
    Returns:
        Tuple of (is_valid, user_id, email, error_message)
    """
    try:
        payload = _decode_token_with_grace(token, issuer=JWT_ISSUER)
        # Check if it's a verification token
        if payload.get("type") != "email_verification":
            return False, None, None, "Invalid verification token type"
        user_id = payload.get("sub")
        email = payload.get("email")
        logger.info(f"Verified verification token for user {user_id}, email {email}")
        return True, user_id, email, None
    except jwt.ExpiredSignatureError:
        return False, None, None, "Verification token has expired"
    except jwt.InvalidTokenError as e:
        return False, None, None, f"Invalid verification token: {str(e)}"
    except Exception as e:
        logger.error(f"Failed to verify verification token: {str(e)}")
        return False, None, None, "Failed to verify verification token"


def generate_reset_token(user_id: str) -> str:
    """
    Generate a password reset token
    Args:
        user_id: User's unique identifier
    Returns:
        Reset token string
    """
    try:
        # Reset tokens have longer expiration (24 hours)
        expiration = datetime.now(timezone.utc) + timedelta(hours=24)
        payload = {
            "sub": user_id,
            "type": "password_reset",
            "iat": datetime.now(timezone.utc),
            "exp": expiration,
            "iss": JWT_ISSUER,
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        logger.info(f"Generated reset token for user {user_id}")
        return token
    except Exception as e:
        logger.error(f"Failed to generate reset token: {str(e)}")
        raise JWTError(f"Failed to generate reset token: {str(e)}")


def verify_reset_token(token: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Verify a password reset token
    Args:
        token: Reset token string
    Returns:
        Tuple of (is_valid, user_id, error_message)
    """
    try:
        payload = _decode_token_with_grace(token, issuer=JWT_ISSUER)
        # Check if it's a reset token
        if payload.get("type") != "password_reset":
            return False, None, "Invalid reset token type"
        user_id = payload.get("sub")
        logger.info(f"Verified reset token for user {user_id}")
        return True, user_id, None
    except jwt.ExpiredSignatureError:
        return False, None, "Reset token has expired"
    except jwt.InvalidTokenError as e:
        return False, None, f"Invalid reset token: {str(e)}"
    except Exception as e:
        logger.error(f"Failed to verify reset token: {str(e)}")
        return False, None, "Failed to verify reset token"


def generate_otp() -> str:
    """
    Generate a random OTP (One-Time Password)
    Returns:
        Numeric OTP string
    """
    import secrets

    # Generate a 6-digit numeric code
    otp = "".join(str(secrets.randbelow(10)) for _ in range(OTP_LENGTH))
    logger.info(f"Generated OTP: {otp[:3]}*** (length: {len(otp)})")
    return otp


def hash_otp(otp: str) -> str:
    """
    Hash an OTP for secure storage
    Args:
        otp: The OTP to hash
    Returns:
        bcrypt hashed OTP
    """
    import bcrypt

    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(otp.encode("utf-8"), salt).decode("utf-8")


def verify_otp_hash(stored_hash: str, otp: str) -> bool:
    """
    Verify an OTP against its stored hash
    Args:
        stored_hash: The hashed OTP from database
        otp: The OTP to verify
    Returns:
        True if OTP matches, False otherwise
    """
    import bcrypt

    try:
        # Check if the stored_hash is a bcrypt hash (starts with $2b$ or $2a$)
        # Fallback to sha256 for backward compatibility with old OTPs
        if stored_hash.startswith("$2"):
            return bcrypt.checkpw(otp.encode("utf-8"), stored_hash.encode("utf-8"))
        else:
            import hashlib

            return hashlib.sha256(otp.encode()).hexdigest() == stored_hash
    except Exception:
        return False


def generate_otp_token(
    user_id: str, email: str, otp: str, token_type: str = "otp_verification"
) -> Tuple[str, datetime]:
    """
    Generate a JWT token for OTP verification
    Args:
        user_id: User's unique identifier
        email: User's email address
        otp: The OTP to encode in token
        token_type: Type of OTP token
    Returns:
        Tuple of (token, expiration_time)
    """
    try:
        # OTP tokens have shorter expiration (10 minutes by default)
        expiration = datetime.now(timezone.utc) + timedelta(
            minutes=OTP_EXPIRATION_MINUTES
        )
        payload = {
            "sub": user_id,
            "email": email,
            "type": token_type,
            "iat": datetime.now(timezone.utc),
            "exp": expiration,
            "iss": JWT_ISSUER,
            # Store full OTP hash for verification
            "otp_hash": hash_otp(otp),
        }
        token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        logger.info(f"Generated OTP token for user {user_id}, expires at {expiration}")
        return token, expiration
    except Exception as e:
        logger.error(f"Failed to generate OTP token: {str(e)}")
        raise JWTError(f"Failed to generate OTP token: {str(e)}")


def verify_otp_token(
    token: str, otp: str | None = None
) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
    """
    Verify an OTP token and optionally verify the OTP code itself
    Args:
        token: OTP token string
        otp: The plaintext OTP code to verify (if provided)
    Returns:
        Tuple of (is_valid, user_id, email, error_message)
    """
    try:
        payload = _decode_token_with_grace(token, issuer=JWT_ISSUER)
        # Check if it's an OTP token
        if payload.get("type") not in ("otp_verification", "password_reset_otp"):
            return False, None, None, "Invalid OTP token type"
        # Verify the OTP if provided
        if otp is not None:
            stored_hash = payload.get("otp_hash")
            if not stored_hash or not verify_otp_hash(stored_hash, otp):
                return False, None, None, "Invalid OTP code"
        user_id = payload.get("sub")
        email = payload.get("email")
        logger.info(f"Verified OTP token for user {user_id}, email {email}")
        return True, user_id, email, None
    except jwt.ExpiredSignatureError:
        return False, None, None, "OTP has expired"
    except jwt.InvalidTokenError as e:
        return False, None, None, f"Invalid OTP token: {str(e)}"
    except Exception as e:
        logger.error(f"Failed to verify OTP token: {str(e)}")
        return False, None, None, "Failed to verify OTP token"
