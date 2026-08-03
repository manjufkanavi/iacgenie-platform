"""Configuration for Git & CI/CD Integration."""

from pydantic_settings import SettingsConfigDict, BaseSettings

from pydantic import Field


class GitCicdConfig(BaseSettings):
    """Configuration for Git & CI/CD integration."""

    # GitHub configuration
    GITHUB_APP_ID: str = Field(default="", validation_alias="GITHUB_APP_ID")
    GITHUB_PRIVATE_KEY: str = Field(default="", validation_alias="GITHUB_PRIVATE_KEY")
    GITHUB_INSTALLATION_ID: str = Field(
        default="", validation_alias="GITHUB_INSTALLATION_ID"
    )
    # GitLab configuration
    GITLAB_URL: str = Field(default="", validation_alias="GITLAB_URL")
    GITLAB_TOKEN: str = Field(default="", validation_alias="GITLAB_TOKEN")
    # Bitbucket configuration
    BITBUCKET_URL: str = Field(default="", validation_alias="BITBUCKET_URL")
    BITBUCKET_USERNAME: str = Field(default="", validation_alias="BITBUCKET_USERNAME")
    BITBUCKET_APP_PASSWORD: str = Field(
        default="", validation_alias="BITBUCKET_APP_PASSWORD"
    )
    # Idempotency
    IDEMPOTENCY_TTL_HOURS: int = Field(
        default=1, validation_alias="IDEMPOTENCY_TTL_HOURS"
    )
    # Webhook security
    WEBHOOK_REPLAY_PROTECTION_WINDOW_MINUTES: int = Field(
        default=5, validation_alias="WEBHOOK_REPLAY_PROTECTION_WINDOW_MINUTES"
    )
    WEBHOOK_SIGNATURE_SECRET: str = Field(
        default="", validation_alias="WEBHOOK_SIGNATURE_SECRET"
    )
    # Logging
    LOG_LEVEL: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )


# Global configuration instance


def get_config() -> GitCicdConfig:
    """Get the global configuration."""
    return GitCicdConfig()


# Global config instance for direct import


config = get_config()
