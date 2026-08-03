"""

Password Utilities

Provides secure password hashing and verification using bcrypt.

"""

import bcrypt

import re

from typing import Optional, Tuple

from config.logging import get_logger

logger = get_logger("password_utils")


class PasswordError(Exception):
    """Password-related errors"""

    pass


class PasswordValidationError(PasswordError):
    """Password validation error"""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(message)
        self.field = field


class PasswordStrength:
    """Password strength levels"""

    WEAK = "weak"
    MEDIUM = "medium"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


def hash_password(password: str, cost_factor: int = 12) -> str:
    """
    Hash a password using bcrypt with configurable cost factor.
    Args:
        password: Plain text password
        cost_factor: bcrypt work factor (minimum 12 recommended)
    Returns:
        Hashed password string
    Raises:
        PasswordError: If password is empty or too short
    """
    if not password:
        raise PasswordError("Password cannot be empty")
    if len(password) < 8:
        raise PasswordError("Password must be at least 8 characters long")
    try:
        salt = bcrypt.gensalt(rounds=cost_factor)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")
    except Exception as e:
        logger.error(f"Failed to hash password: {str(e)}")
        raise PasswordError("Failed to hash password")


def get_bcrypt_cost_factor(hashed_password: str) -> int:
    """Extract the bcrypt cost factor from a hash string.
    Args:
        hashed_password: A bcrypt hash string (e.g., $2b$12$...)
    Returns:
        The cost factor as an integer, or 4 if parsing fails.
    """
    parts = hashed_password.split("$")
    return int(parts[2]) if len(parts) >= 3 else 4


def verify_password_strength(hashed_password: str) -> Tuple[bool, Optional[str]]:
    """Verify that a bcrypt hash uses a sufficient cost factor.
    Args:
        hashed_password: A bcrypt hash string
    Returns:
        Tuple of (is_strong_enough, error_message_or_none)
    """
    cost = get_bcrypt_cost_factor(hashed_password)
    if cost < 12:
        return (
            False,
            f"Password hash uses weak bcrypt cost factor ({cost}), minimum is 12",
        )
    return True, None


def hash_password_for_comparison(password: str) -> str:
    """Hash a password for comparison against history entries.
    Uses the same cost factor as new hashes to ensure consistent comparison.
    """
    return hash_password(password, cost_factor=12)


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hashed password
    Args:
        password: Plain text password to verify
        hashed_password: Hashed password to compare against
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception as e:
        logger.error(f"Failed to verify password: {str(e)}")
        return False


def validate_password(
    password: str,
    min_length: int = 8,
    require_uppercase: bool = True,
    require_lowercase: bool = True,
    require_number: bool = True,
    require_special: bool = True,
) -> Tuple[bool, Optional[str], str]:
    """
    Validate password strength
    Args:
        password: Password to validate
        min_length: Minimum password length (default: 8)
        require_uppercase: Require at least one uppercase letter (default: True)
        require_lowercase: Require at least one lowercase letter (default: True)
        require_number: Require at least one number (default: True)
        require_special: Require at least one special character (default: True)
    Returns:
        Tuple of (is_valid, error_message, strength_level)
    """
    errors = []
    # Check length
    if len(password) < min_length:
        errors.append(f"Password must be at least {min_length} characters long")
    # Check for uppercase
    if require_uppercase and not re.search(r"[A-Z]", password):
        errors.append("Password must contain at least one uppercase letter")
    # Check for lowercase
    if require_lowercase and not re.search(r"[a-z]", password):
        errors.append("Password must contain at least one lowercase letter")
    # Check for number
    if require_number and not re.search(r"\d", password):
        errors.append("Password must contain at least one number")
    # Check for special character
    if require_special and not re.search(
        r'[!@#$%^&*()_+\-=\[\]{};:"\\|,<.>/?]', password
    ):
        errors.append("Password must contain at least one special character")
    # Calculate strength
    strength = calculate_password_strength(password)
    if errors:
        return False, "; ".join(errors), strength
    return True, None, strength


def calculate_password_strength(password: str) -> str:
    """
    Calculate password strength based on complexity
    Args:
        password: Password to analyze
    Returns:
        PasswordStrength level
    """
    score = 0
    # Length score
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if len(password) >= 16:
        score += 1
    # Complexity score
    if re.search(r"[a-z]", password):
        score += 1
    if re.search(r"[A-Z]", password):
        score += 1
    if re.search(r"\d", password):
        score += 1
    if re.search(r'[!@#$%^&*()_+\-=\[\]{};:"\\|,<.>/?]', password):
        score += 1
    # Determine strength
    if score <= 2:
        return PasswordStrength.WEAK
    elif score <= 4:
        return PasswordStrength.MEDIUM
    elif score <= 6:
        return PasswordStrength.STRONG
    else:
        return PasswordStrength.VERY_STRONG


def generate_password_reset_token() -> str:
    """
    Generate a secure random token for password reset
    Returns:
        Random token string
    """
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits
    token = "".join(secrets.choice(alphabet) for _ in range(64))
    return token


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Validate email format
    Args:
        email: Email address to validate
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not email:
        return False, "Email is required"
    # Basic email validation regex
    email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_regex, email):
        return False, "Invalid email format"
    # Check for common issues
    if " " in email:
        return False, "Email cannot contain spaces"
    if email.count("@") != 1:
        return False, "Email must contain exactly one @ symbol"
    return True, None


def sanitize_display_name(display_name: Optional[str]) -> str:
    """
    Sanitize display name for safe storage
    Args:
        display_name: Raw display name
    Returns:
        Sanitized display name
    """
    if not display_name:
        return "User"
    # Remove leading/trailing whitespace
    sanitized = display_name.strip()
    # Remove potentially dangerous characters
    dangerous_chars = ["<", ">", '"', "'", "\\", "\n", "\r", "\t"]
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, "")
    # Limit length
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    return sanitized if sanitized else "User"
