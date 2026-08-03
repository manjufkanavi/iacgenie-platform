"""

Secret Store Module

Securely manages user credentials for Git and CI/CD operations.

Ensures secrets are encrypted at rest and accessed only by authorized services.

Features:

- HashiCorp Vault integration for secret management

- Just-in-time token generation

- Audit logging for all secret access attempts

- OpenTelemetry tracing and metrics

- Multi-tenancy support with Vault namespaces

"""

from .config import SecretStoreConfig

from .exceptions import (
    SecretNotFoundError,
    SecretAccessDeniedError,
    SecretAccessError,
    SecretEncryptionError,
    SecretValidationError,
    TenantIdMissingError,
    VaultConnectionError,
    AuditLogError,
    InvalidSecretNameError,
    SecretSizeExceededError,
    TokenGenerationError,
    IdempotencyKeyConflictError,
    SecretAlreadyExistsError,
    SecretTooLargeError,
)

from .models import (
    SecretAccessRequest,
    SecretAccessResponse,
    SecretOperation,
    SecretMetadata,
)

from .service import SecretStoreService

from .observability import (
    trace_secret_access,
    record_secret_access_metric,
    SecretAccessMetrics,
)

__all__ = [
    # Config
    "SecretStoreConfig",
    # Exceptions
    "SecretNotFoundError",
    "SecretAccessDeniedError",
    "SecretAccessError",
    "SecretEncryptionError",
    "SecretValidationError",
    "TenantIdMissingError",
    "VaultConnectionError",
    "AuditLogError",
    "InvalidSecretNameError",
    "SecretSizeExceededError",
    "TokenGenerationError",
    "IdempotencyKeyConflictError",
    "SecretAlreadyExistsError",
    "SecretTooLargeError",
    # Models
    "SecretAccessRequest",
    "SecretAccessResponse",
    "SecretOperation",
    "SecretMetadata",
    # Service
    "SecretStoreService",
    # Observability
    "trace_secret_access",
    "record_secret_access_metric",
    "SecretAccessMetrics",
]
