"""

Workflow Engine Configuration

Configuration settings for the workflow engine including Redis, Celery,

and workflow-specific parameters.

"""

from pydantic_settings import SettingsConfigDict, BaseSettings

from typing import Optional


class WorkflowConfig(BaseSettings):
    """Configuration for workflow engine and task orchestration."""

    # Redis Configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    @property
    def redis_url(self) -> str:
        """Construct Redis URL from components."""
        password_part = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{password_part}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Celery Configuration
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    CELERY_TASK_TRACK_STARTED: bool = True
    CELERY_TASK_TIME_LIMIT: int = 3600  # 1 hour
    # Workflow Settings
    MAX_ITERATIONS: int = 5
    RETRY_MAX_ATTEMPTS: int = 3
    RETRY_BACKOFF_MULTIPLIER: float = 2.0
    RETRY_INITIAL_DELAY: float = 1.0  # seconds
    # State Machine Settings
    STATE_TRANSITION_TIMEOUT: int = 300  # 5 minutes
    SESSION_TIMEOUT: int = 3600  # 1 hour
    # Dead Letter Queue
    DLQ_ENABLED: bool = True
    DLQ_MAX_SIZE: int = 1000
    # Saga Pattern
    SAGA_ENABLED: bool = True
    SAGA_COMPENSATION_TIMEOUT: int = 600  # 10 minutes
    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="WORKFLOW_", case_sensitive=True, extra="ignore"
    )


# Global configuration instance


workflow_config = WorkflowConfig()
