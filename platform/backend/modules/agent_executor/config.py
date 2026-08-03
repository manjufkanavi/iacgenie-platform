"""Configuration management for Agent Executor."""

from pydantic_settings import SettingsConfigDict, BaseSettings

from pydantic import Field

from typing import Dict, Any


class AgentExecutorConfig(BaseSettings):
    """Configuration class for Agent Executor with type-safe validation."""

    # Agent process management
    MAX_AGENT_PROCESSES: int = Field(default=5, validation_alias="MAX_AGENT_PROCESSES")
    AGENT_TIMEOUT_SECONDS: int = Field(
        default=300, validation_alias="AGENT_TIMEOUT_SECONDS"
    )
    MEMORY_LIMIT_MB: int = Field(default=2048, validation_alias="MEMORY_LIMIT_MB")
    CPU_LIMIT: float = Field(default=1.0, validation_alias="CPU_LIMIT")
    TOOL_INJECTION_TIMEOUT: int = Field(
        default=10, validation_alias="TOOL_INJECTION_TIMEOUT"
    )
    # Redis configuration
    REDIS_HOST: str = Field(default="localhost", validation_alias="REDIS_HOST")
    REDIS_PORT: int = Field(default=6379, validation_alias="REDIS_PORT")
    REDIS_DB: int = Field(default=0, validation_alias="REDIS_DB")
    # Task queue names
    CODER_TASK_QUEUE: str = Field(
        default="coder_tasks", validation_alias="CODER_TASK_QUEUE"
    )
    VALIDATOR_TASK_QUEUE: str = Field(
        default="validator_tasks", validation_alias="VALIDATOR_TASK_QUEUE"
    )
    PLANNER_TASK_QUEUE: str = Field(
        default="planner_tasks", validation_alias="PLANNER_TASK_QUEUE"
    )
    APPLIER_TASK_QUEUE: str = Field(
        default="applier_tasks", validation_alias="APPLIER_TASK_QUEUE"
    )
    TESTER_TASK_QUEUE: str = Field(
        default="tester_tasks", validation_alias="TESTER_TASK_QUEUE"
    )
    # Internal API endpoints
    LLM_PROXY_URL: str = Field(
        default="http://localhost:8080/llm", validation_alias="LLM_PROXY_URL"
    )
    SANDBOX_MANAGER_URL: str = Field(
        default="http://localhost:8081/sandbox", validation_alias="SANDBOX_MANAGER_URL"
    )
    # Security settings
    ALLOWED_COMMANDS: list = Field(
        default=["tofu", "git"], validation_alias="ALLOWED_COMMANDS"
    )
    # Logging configuration
    LOG_LEVEL: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    LOG_FORMAT: str = Field(
        default="%(asctime)s | %(name)s | %(levelname)s | %(session_id)s | %(build_id)s | %(message)s",
        validation_alias="LOG_FORMAT",
    )
    # Resource monitoring thresholds
    RESOURCE_THRESHOLD_CPU: float = Field(
        default=80.0, validation_alias="RESOURCE_THRESHOLD_CPU"
    )
    RESOURCE_THRESHOLD_MEMORY: float = Field(
        default=1800.0, validation_alias="RESOURCE_THRESHOLD_MEMORY"
    )
    model_config = SettingsConfigDict(env_file_encoding="utf-8", case_sensitive=False)

    def validate_configuration(self) -> Dict[str, Any]:
        """Validate configuration settings and return any issues."""
        issues = []
        if self.MAX_AGENT_PROCESSES < 1:
            issues.append("MAX_AGENT_PROCESSES must be at least 1")
        if self.AGENT_TIMEOUT_SECONDS < 60:
            issues.append("AGENT_TIMEOUT_SECONDS should be at least 60 seconds")
        if self.MEMORY_LIMIT_MB < 512:
            issues.append("MEMORY_LIMIT_MB should be at least 512 MB")
        if self.CPU_LIMIT < 0.1:
            issues.append("CPU_LIMIT should be at least 0.1")
        if not self.ALLOWED_COMMANDS:
            issues.append("ALLOWED_COMMANDS list must not be empty")
        return {"valid": len(issues) == 0, "issues": issues}


# Create a global instance for easy access


config = AgentExecutorConfig()
