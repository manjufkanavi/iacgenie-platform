"""

Secret Store Configuration

Handles all configuration for the Secret Store module including Vault connection,

audit settings, and security parameters.

"""

import os

from dataclasses import dataclass

from typing import Optional


@dataclass
class SecretStoreConfig:
    """Configuration for the Secret Store module."""

    # Vault configuration
    vault_addr: str
    vault_token: Optional[str] = None
    vault_namespace: Optional[str] = None
    vault_timeout_seconds: int = 30
    vault_role: str = "secret-store"
    # OpenBao configuration
    openbao_addr: str = "http://localhost:8200"
    openbao_token: Optional[str] = None
    openbao_namespace: Optional[str] = None
    openbao_timeout_seconds: int = 30
    openbao_role: str = "secret-store"
    # Secret configuration
    secret_ttl_minutes: int = 60
    max_secret_size_bytes: int = (
        65536  # 64 KB — supports GCP JSON credentials (~2-4 KB)
    )
    # Audit configuration
    audit_log_retention_days: int = 90
    audit_log_file: str = "/var/log/secret_store/audit.log"
    # Kubernetes authentication
    kubernetes_auth_path: str = "kubernetes"
    kubernetes_role: str = "secret-store"
    # Token generation
    token_ttl_minutes: int = 60
    token_min_length: int = 32
    # Security
    redact_patterns: tuple = (
        "token",
        "password",
        "secret",
        "key",
        "credential",
        "api_key",
        "api-key",
        "auth_token",
        "access_token",
        "refresh_token",
    )

    def __post_init__(self) -> None:
        """Validate configuration after dataclass initialization."""
        self.validate()

    def __repr__(self) -> str:
        """Represent config with sensitive fields redacted."""
        import dataclasses

        fields = dataclasses.fields(self)
        parts = []
        for field in fields:
            val = getattr(self, field.name)
            if field.name in ("openbao_token", "vault_token") and val:
                val = "***REDACTED***"
            parts.append(f"{field.name}={val!r}")
        return f"{self.__class__.__name__}({', '.join(parts)})"

    @classmethod
    def from_env(cls) -> "SecretStoreConfig":
        """Create configuration from environment variables."""
        # Prefer OpenBao if available, fall back to Vault for backward compat
        openbao_addr = os.environ.get("OPENBAO_ADDR") or "http://localhost:8200"
        vault_addr = os.environ.get("VAULT_ADDR") or openbao_addr
        # Use OpenBao token if available, otherwise fall back to Vault token
        openbao_token = os.environ.get("OPENBAO_TOKEN") or os.environ.get("VAULT_TOKEN")
        return cls(
            vault_addr=vault_addr,
            vault_token=os.environ.get("VAULT_TOKEN"),
            vault_namespace=os.environ.get("VAULT_NAMESPACE"),
            secret_ttl_minutes=int(os.environ.get("SECRET_TTL_MINUTES", "60")),
            max_secret_size_bytes=int(os.environ.get("MAX_SECRET_SIZE_BYTES", "1024")),
            audit_log_retention_days=int(
                os.environ.get("AUDIT_LOG_RETENTION_DAYS", "90")
            ),
            kubernetes_auth_path=os.environ.get(
                "VAULT_KUBERNETES_AUTH_PATH", "kubernetes"
            ),
            kubernetes_role=os.environ.get("VAULT_KUBERNETES_ROLE", "secret-store"),
            token_ttl_minutes=int(os.environ.get("TOKEN_TTL_MINUTES", "60")),
            token_min_length=int(os.environ.get("TOKEN_MIN_LENGTH", "32")),
            openbao_addr=openbao_addr,
            openbao_token=openbao_token,
            openbao_namespace=os.environ.get("OPENBAO_NAMESPACE"),
            openbao_timeout_seconds=int(
                os.environ.get("OPENBAO_TIMEOUT_SECONDS", "30")
            ),
            openbao_role=os.environ.get("OPENBAO_ROLE", "secret-store"),
        )

    def validate(self) -> None:
        """Validate configuration values."""
        errors = []
        if not self.vault_addr:
            errors.append("VAULT_ADDR is required")
        # OpenBao address validation (override if set)
        if self.openbao_addr and self.openbao_addr != "http://localhost:8200":
            if not self.openbao_addr.startswith(("http://", "https://")):
                errors.append("OPENBAO_ADDR must start with http:// or https://")
        if self.secret_ttl_minutes < 1 or self.secret_ttl_minutes > 1440:
            errors.append("SECRET_TTL_MINUTES must be between 1 and 1440")
        if self.max_secret_size_bytes < 1 or self.max_secret_size_bytes > 10485760:
            errors.append("MAX_SECRET_SIZE_BYTES must be between 1 and 1048576")
        if self.audit_log_retention_days < 1 or self.audit_log_retention_days > 365:
            errors.append("AUDIT_LOG_RETENTION_DAYS must be between 1 and 365")
        if self.token_ttl_minutes < 1 or self.token_ttl_minutes > 1440:
            errors.append("TOKEN_TTL_MINUTES must be between 1 and 1440")
        if self.token_min_length < 16 or self.token_min_length > 256:
            errors.append("TOKEN_MIN_LENGTH must be between 16 and 256")
        if errors:
            raise ValueError("Invalid configuration: " + "; ".join(errors))

    @property
    def vault_address(self) -> str:
        """Get the Vault address."""
        return self.vault_addr

    @property
    def is_kubernetes_auth(self) -> bool:
        """Check if Kubernetes authentication is enabled."""
        return self.vault_token is None

    @property
    def vault_headers(self) -> dict:
        """Get Vault API headers."""
        headers = {"Content-Type": "application/json"}
        if self.vault_token:
            headers["X-Vault-Token"] = self.vault_token
        if self.vault_namespace:
            headers["X-Vault-Namespace"] = self.vault_namespace
        return headers

    @property
    def openbao_headers(self) -> dict:
        """Get OpenBao API headers."""
        headers = {"Content-Type": "application/json"}
        if self.openbao_token:
            headers["X-Vault-Token"] = self.openbao_token
        if self.openbao_namespace:
            headers["X-Vault-Namespace"] = self.openbao_namespace
        return headers

    @property
    def is_openbao(self) -> bool:
        """Check if OpenBao is configured (preferred over Vault)."""
        return bool(self.openbao_addr and self.openbao_token)

    @property
    def active_addr(self) -> str:
        """Get the active secret store address (OpenBao preferred, Vault fallback)."""
        if self.is_openbao:
            return self.openbao_addr
        return self.vault_addr

    @property
    def active_token(self) -> Optional[str]:
        """Get the active secret store token."""
        if self.is_openbao:
            return self.openbao_token
        return self.vault_token

    @property
    def active_headers(self) -> dict:
        """Get active secret store headers (OpenBao preferred, Vault fallback)."""
        if self.is_openbao:
            return self.openbao_headers
        return self.vault_headers
