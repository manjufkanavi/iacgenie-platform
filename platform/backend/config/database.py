"""

Database Configuration

PostgreSQL-only database configuration with connection pooling

"""

import os

from typing import Dict, Any, Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

from config.logging import get_logger

logger = get_logger("database.config")

# Get the directory where this script is located

# The .env file should be in the backend directory (iacgenie-ai/backend/.env)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

ENV_FILE_PATH = os.path.join(os.path.dirname(SCRIPT_DIR), ".env")

# Load .env file to ensure environment variables are set before Settings initialization

from dotenv import load_dotenv

load_dotenv(ENV_FILE_PATH, override=True)


class DatabaseSettings(BaseSettings):
    """Database configuration settings supporting PostgreSQL and SQLite"""

    # In pydantic-settings v2, use model_config with extra='ignore' or 'allow'
    # Environment variables are loaded via load_dotenv above
    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",  # Use 'ignore' to ignore unknown env vars
    )
    # Field name must match the environment variable name (case-insensitive)
    DATABASE_PROVIDER: str = os.getenv("DATABASE_PROVIDER", "sqlite")
    # PostgreSQL settings
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DATABASE: str = "iacgenie"
    POSTGRES_USER: str = "iacgenie_user"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_SSL_MODE: str = "prefer"
    # Connection pooling settings
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 30
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    DB_POOL_PRE_PING: bool = True
    # Connection monitoring
    DB_CONNECTION_MONITORING: bool = True
    DB_HEALTH_CHECK_INTERVAL: int = 300
    # SQLite path (for backward compatibility with code that expects sqlite_path)
    SQLITE_PATH: str = "iacgenie.db"

    @property
    def provider(self) -> str:
        """Get database provider"""
        return self.DATABASE_PROVIDER

    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL"""
        if self.POSTGRES_PASSWORD:
            return (
                f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}"
                f"/{self.POSTGRES_DATABASE}?sslmode={self.POSTGRES_SSL_MODE}"
            )
        else:
            return (
                f"postgresql://{self.POSTGRES_USER}@{self.POSTGRES_HOST}"
                f":{self.POSTGRES_PORT}/{self.POSTGRES_DATABASE}"
                f"?sslmode={self.POSTGRES_SSL_MODE}"
            )

    @property
    def postgres_async_url(self) -> str:
        """Get PostgreSQL async connection URL (without sslmode for asyncpg)"""
        if self.POSTGRES_PASSWORD:
            return f"postgresql+asyncpg://{self.POSTGRES_USER}:{
                self.POSTGRES_PASSWORD
            }@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DATABASE}"
        else:
            return (
                f"postgresql+asyncpg://{self.POSTGRES_USER}@{self.POSTGRES_HOST}"
                f":{self.POSTGRES_PORT}/{self.POSTGRES_DATABASE}"
            )

    @property
    def pool_size(self) -> int:
        """Get pool size (alias for DB_POOL_SIZE)"""
        return self.DB_POOL_SIZE

    @property
    def max_overflow(self) -> int:
        """Get max overflow (alias for DB_MAX_OVERFLOW)"""
        return self.DB_MAX_OVERFLOW

    @property
    def connection_monitoring(self) -> bool:
        """Get connection monitoring flag (alias for DB_CONNECTION_MONITORING)"""
        return self.DB_CONNECTION_MONITORING

    @property
    def health_check_interval(self) -> int:
        """Get health check interval (alias for DB_HEALTH_CHECK_INTERVAL)"""
        return self.DB_HEALTH_CHECK_INTERVAL

    @property
    def pool_timeout(self) -> int:
        """Get pool timeout (alias for DB_POOL_TIMEOUT)"""
        return self.DB_POOL_TIMEOUT

    @property
    def pool_recycle(self) -> int:
        """Get pool recycle (alias for DB_POOL_RECYCLE)"""
        return self.DB_POOL_RECYCLE

    @property
    def pool_pre_ping(self) -> bool:
        """Get pool pre-ping (alias for DB_POOL_PRE_PING)"""
        return self.DB_POOL_PRE_PING

    @property
    def sqlite_path(self) -> str:
        """Get SQLite database path (for backward compatibility)"""
        return self.SQLITE_PATH

    @property
    def sqlite_url(self) -> str:
        """Get SQLite database URL (for backward compatibility)"""
        return f"sqlite:///{self.SQLITE_PATH}"

    def get_pool_config(self) -> Dict[str, Any]:
        """Get connection pool configuration"""
        return {
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "pool_timeout": self.pool_timeout,
            "pool_recycle": self.pool_recycle,
            "pool_pre_ping": self.pool_pre_ping,
            "echo": os.getenv("DB_ECHO", "false").lower() == "true",
        }


# Global database settings instance (initialized lazily)


_db_settings_instance: Optional[DatabaseSettings] = None


def get_database_settings() -> DatabaseSettings:
    """Get PostgreSQL database settings instance (lazy initialization)"""
    global _db_settings_instance
    if _db_settings_instance is None:
        _db_settings_instance = DatabaseSettings()
    return _db_settings_instance


# For backward compatibility, export db_settings (will be initialized on first use)


db_settings = get_database_settings()
