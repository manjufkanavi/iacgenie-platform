"""

Secret Store Exceptions

Custom exception classes for the Secret Store module.

"""

from typing import Optional


class SecretStoreError(Exception):
    """Base exception for all Secret Store errors."""

    def __init__(
        self,
        message: str,
        secret_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        self.message = message
        self.secret_name = secret_name
        self.user_id = user_id
        super().__init__(self._format_message())

    def _format_message(self) -> str:
        """Format the error message with context."""
        parts = [self.message]
        if self.secret_name:
            parts.append(f"secret_name={self.secret_name}")
        if self.user_id:
            parts.append(f"user_id={self.user_id}")
        return "; ".join(parts)


class SecretNotFoundError(SecretStoreError):
    """Raised when a secret is not found."""

    def __init__(self, secret_name: str, user_id: str):
        super().__init__(
            message="Secret not found", secret_name=secret_name, user_id=user_id
        )


class SecretAccessDeniedError(SecretStoreError):
    """Raised when access to a secret is denied."""

    def __init__(self, secret_name: str, user_id: str, reason: Optional[str] = None):
        self.reason = reason
        msg = "Access denied to secret"
        if reason:
            msg = f"{msg}: {reason}"
        super().__init__(message=msg, secret_name=secret_name, user_id=user_id)


class SecretEncryptionError(SecretStoreError):
    """Raised when encryption/decryption fails."""

    def __init__(self, secret_name: str, user_id: str, error: Optional[str] = None):
        self.error = error
        msg = "Secret encryption/decryption failed"
        if error:
            msg = f"{msg}: {error}"
        super().__init__(message=msg, secret_name=secret_name, user_id=user_id)


class VaultConnectionError(SecretStoreError):
    """Raised when Vault connection fails."""

    def __init__(self, vault_addr: str, error: Optional[str] = None):
        self.vault_addr = vault_addr
        self.error = error
        msg = f"Failed to connect to Vault at {vault_addr}"
        if error:
            msg = f"{msg}: {error}"
        super().__init__(message=msg)


class AuditLogError(SecretStoreError):
    """Raised when audit logging fails."""

    def __init__(self, secret_name: str, user_id: str, error: Optional[str] = None):
        self.error = error
        msg = "Failed to write audit log"
        if error:
            msg = f"{msg}: {error}"
        super().__init__(message=msg, secret_name=secret_name, user_id=user_id)


class InvalidSecretNameError(SecretStoreError):
    """Raised when a secret name is invalid."""

    def __init__(self, secret_name: str, reason: str):
        self.reason = reason
        super().__init__(
            message=f"Invalid secret name: {reason}",
            secret_name=secret_name,
            user_id=None,
        )


class SecretSizeExceededError(SecretStoreError):
    """Raised when a secret exceeds the maximum size."""

    def __init__(self, secret_name: str, user_id: str, size: int, max_size: int):
        self.size = size
        self.max_size = max_size
        super().__init__(
            message=f"Secret size ({size} bytes) exceeds maximum ({max_size} bytes)",
            secret_name=secret_name,
            user_id=user_id,
        )


class TokenGenerationError(SecretStoreError):
    """Raised when token generation fails."""

    def __init__(self, secret_name: str, user_id: str, error: Optional[str] = None):
        self.error = error
        msg = "Token generation failed"
        if error:
            msg = f"{msg}: {error}"
        super().__init__(message=msg, secret_name=secret_name, user_id=user_id)


class IdempotencyKeyConflictError(SecretStoreError):
    """Raised when an idempotency key conflict occurs."""

    def __init__(self, idempotency_key: str, existing_result: dict):
        self.idempotency_key = idempotency_key
        self.existing_result = existing_result
        super().__init__(
            message=f"Idempotency key already exists: {idempotency_key}",
            secret_name=None,
            user_id=None,
        )


class SecretAlreadyExistsError(SecretStoreError):
    """Raised when a secret already exists."""

    def __init__(self, secret_name: str, user_id: str):
        super().__init__(
            message="Secret already exists", secret_name=secret_name, user_id=user_id
        )


class SecretTooLargeError(SecretStoreError):
    """Raised when a secret exceeds the maximum size."""

    def __init__(self, secret_name: str, user_id: str, size: int, max_size: int):
        self.size = size
        self.max_size = max_size
        super().__init__(
            message=f"Secret size ({size} bytes) exceeds maximum ({max_size} bytes)",
            secret_name=secret_name,
            user_id=user_id,
        )


class SecretValidationError(SecretStoreError):
    """Raised when secret validation fails."""

    def __init__(
        self,
        message: str,
        secret_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        super().__init__(message=message, secret_name=secret_name, user_id=user_id)


class SecretAccessError(SecretStoreError):
    """Raised when access to a secret fails."""

    def __init__(
        self,
        message: str,
        secret_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ):
        super().__init__(message=message, secret_name=secret_name, user_id=user_id)


class TenantIdMissingError(SecretStoreError):
    """Raised when tenant ID is missing."""

    def __init__(self) -> None:
        super().__init__(
            message="Tenant ID is required but missing", secret_name=None, user_id=None
        )
