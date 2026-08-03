"""

Storage Configuration

Configuration settings for MinIO object storage and HashiCorp Vault

secret management.

"""

from pydantic_settings import SettingsConfigDict, BaseSettings

from typing import Optional, List


class StorageConfig(BaseSettings):
    """Configuration for storage services (MinIO and Vault)."""

    # MinIO Configuration
    MINIO_ENDPOINT: str = "http://localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_REGION: str = "us-east-1"
    # MinIO Buckets
    MINIO_ARTIFACTS_BUCKET: str = "artifacts"
    MINIO_LOGS_BUCKET: str = "logs"
    MINIO_PLANS_BUCKET: str = "plans"
    MINIO_OUTPUTS_BUCKET: str = "outputs"

    @property
    def minio_buckets(self) -> List[str]:
        """Return list of all configured MinIO buckets."""
        return [
            self.MINIO_ARTIFACTS_BUCKET,
            self.MINIO_LOGS_BUCKET,
            self.MINIO_PLANS_BUCKET,
            self.MINIO_OUTPUTS_BUCKET,
        ]

    # Vault Configuration
    VAULT_ADDR: str = "http://localhost:8200"
    VAULT_TOKEN: Optional[str] = None
    VAULT_NAMESPACE_PREFIX: str = "iacgenie"
    VAULT_MOUNT_POINT: str = "secret"
    VAULT_KV_VERSION: int = 2
    # Vault Secret Paths
    VAULT_SECRETS_PATH: str = "secrets"
    VAULT_GIT_TOKENS_PATH: str = "git_tokens"
    VAULT_CI_PAT_PATH: str = "ci_pats"
    VAULT_CLOUD_CREDENTIALS_PATH: str = "cloud_credentials"
    # Vault TTL Settings
    VAULT_DEFAULT_TTL: str = "1h"
    VAULT_MAX_TTL: str = "24h"
    VAULT_GIT_TOKEN_TTL: str = "1h"
    VAULT_CI_PAT_TTL: str = "1h"
    # PostgreSQL Configuration (for module metadata)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DATABASE: str = "iacgenie"
    POSTGRES_USER: str = "iacgenie_user"
    POSTGRES_PASSWORD: str = "iacgenie_password"
    POSTGRES_SCHEMA: str = "public"

    @property
    def postgres_url(self) -> str:
        """Construct PostgreSQL URL from components."""
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DATABASE}"
        )

    # Connection Pool Settings
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600  # 1 hour
    # Artifact Storage Settings
    ARTIFACT_MAX_SIZE: int = 10485760  # 10MB
    ARTIFACT_DEFAULT_TTL: int = 604800  # 7 days in seconds
    ARTIFACT_CLEANUP_INTERVAL: int = 86400  # 1 day in seconds
    # Encryption
    ENCRYPTION_ENABLED: bool = True
    ENCRYPTION_KEY: Optional[str] = None  # Generated if not provided
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="STORAGE_", case_sensitive=True, extra="ignore"
    )


# Global configuration instance


storage_config = StorageConfig()
