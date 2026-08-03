# Workflow Engine Configuration

"""

Configuration settings for the Workflow Engine. Defines environment

variables, default values, and configuration validation.

"""

from __future__ import annotations

import os

from dataclasses import dataclass, field

from typing import Optional

# Default configuration constants (re-exported from __init__.py)

DEFAULT_MAX_ITERATIONS = 5

DEFAULT_MAX_RETRY_ATTEMPTS = 3

DEFAULT_IDEMPOTENCY_TTL = 3600

DEFAULT_SAGA_COMPENSATION_TIMEOUT = 1800


@dataclass
class WorkflowEngineConfig:
    """Configuration for the Workflow Engine."""

    # Core settings
    max_iterations: int = 5
    max_retry_attempts: int = 3
    idempotency_ttl: int = 3600  # 1 hour in seconds
    saga_compensation_timeout: int = 1800  # 30 minutes in seconds
    log_level: str = "info"
    # State machine settings
    state_machine_enabled: bool = True
    transition_timeout: int = 200  # 200ms timeout for state transitions
    # Retry settings
    retry_base_delay: float = 1.0
    retry_max_delay: float = 60.0
    retry_multiplier: float = 2.0
    # Dead-letter queue settings
    dlq_enabled: bool = True
    dlq_max_entries: int = 1000
    dlq_retention_days: int = 30
    # Saga settings
    saga_enabled: bool = True
    saga_compensation_enabled: bool = True
    # External service settings
    redis_url: str = "redis://localhost:6379"
    postgres_url: str = "postgresql://localhost:5432/iacgenie"
    minio_endpoint: str = "http://localhost:9000"
    vault_addr: str = "http://localhost:8200"
    # Tracing settings
    tracing_enabled: bool = True
    tracing_sample_rate: float = 0.1
    tracing_endpoint: str = "http://localhost:4317"
    # Performance settings
    max_concurrent_sessions: int = 50
    session_timeout_minutes: int = 60
    pre_warmed_sandbox_pool_size: int = 10
    # Security settings
    tenant_header: str = "X-Tenant-ID"
    rate_limit_per_tenant: int = 1000
    rate_limit_window_seconds: int = 60
    # Feature flags
    enable_git_integration: bool = True
    enable_ci_trigger: bool = True
    enable_artifact_store: bool = True
    enable_secrets_management: bool = True
    # Error escalation settings
    consecutive_error_threshold: int = 3
    escalation_enabled: bool = True

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.max_iterations < 1:
            raise ValueError("max_iterations must be at least 1")
        if self.max_retry_attempts < 0:
            raise ValueError("max_retry_attempts must be non-negative")
        if self.idempotency_ttl < 60:
            raise ValueError("idempotency_ttl must be at least 60 seconds")
        if self.saga_compensation_timeout < 60:
            raise ValueError("saga_compensation_timeout must be at least 60 seconds")
        if self.transition_timeout < 100:
            raise ValueError("transition_timeout must be at least 100ms")
        if self.max_concurrent_sessions < 1:
            raise ValueError("max_concurrent_sessions must be at least 1")

    @classmethod
    def from_env(cls) -> WorkflowEngineConfig:
        """Create configuration from environment variables."""
        return cls(
            max_iterations=int(os.getenv("MAX_ITERATIONS", "5")),
            max_retry_attempts=int(os.getenv("MAX_RETRY_ATTEMPTS", "3")),
            idempotency_ttl=int(os.getenv("IDEMPOTENCY_TTL", "3600")),
            saga_compensation_timeout=int(
                os.getenv("SAGA_COMPENSATION_TIMEOUT", "1800")
            ),
            log_level=os.getenv("LOG_LEVEL", "info"),
            state_machine_enabled=os.getenv("STATE_MACHINE_ENABLED", "true").lower()
            == "true",
            transition_timeout=int(os.getenv("TRANSITION_TIMEOUT", "200")),
            retry_base_delay=float(os.getenv("RETRY_BASE_DELAY", "1.0")),
            retry_max_delay=float(os.getenv("RETRY_MAX_DELAY", "60.0")),
            retry_multiplier=float(os.getenv("RETRY_MULTIPLIER", "2.0")),
            dlq_enabled=os.getenv("DLQ_ENABLED", "true").lower() == "true",
            dlq_max_entries=int(os.getenv("DLQ_MAX_ENTRIES", "1000")),
            dlq_retention_days=int(os.getenv("DLQ_RETENTION_DAYS", "30")),
            saga_enabled=os.getenv("SAGA_ENABLED", "true").lower() == "true",
            saga_compensation_enabled=os.getenv(
                "SAGA_COMPENSATION_ENABLED", "true"
            ).lower()
            == "true",
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
            postgres_url=os.getenv(
                "POSTGRES_URL",
                os.getenv("DATABASE_URL", "postgresql://localhost:5432/iacgenie"),
            ),
            minio_endpoint=os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
            vault_addr=os.getenv("VAULT_ADDR", "http://localhost:8200"),
            tracing_enabled=os.getenv("TRACING_ENABLED", "true").lower() == "true",
            tracing_sample_rate=float(os.getenv("TRACING_SAMPLE_RATE", "0.1")),
            tracing_endpoint=os.getenv("TRACING_ENDPOINT", "http://localhost:4317"),
            max_concurrent_sessions=int(os.getenv("MAX_CONCURRENT_SESSIONS", "50")),
            session_timeout_minutes=int(os.getenv("SESSION_TIMEOUT_MINUTES", "60")),
            pre_warmed_sandbox_pool_size=int(
                os.getenv("PRE_WARMED_SANDBOX_POOL_SIZE", "10")
            ),
            tenant_header=os.getenv("TENANT_HEADER", "X-Tenant-ID"),
            rate_limit_per_tenant=int(os.getenv("RATE_LIMIT_PER_TENANT", "1000")),
            rate_limit_window_seconds=int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60")),
            enable_git_integration=os.getenv("ENABLE_GIT_INTEGRATION", "true").lower()
            == "true",
            enable_ci_trigger=os.getenv("ENABLE_CI_TRIGGER", "true").lower() == "true",
            enable_artifact_store=os.getenv("ENABLE_ARTIFACT_STORE", "true").lower()
            == "true",
            enable_secrets_management=os.getenv(
                "ENABLE_SECRETS_MANAGEMENT", "true"
            ).lower()
            == "true",
            consecutive_error_threshold=int(
                os.getenv("CONSECUTIVE_ERROR_THRESHOLD", "3")
            ),
            escalation_enabled=os.getenv("ESCALATION_ENABLED", "true").lower()
            == "true",
        )


@dataclass
class StateTransitionConfig:
    """Configuration for state transitions."""

    allowed_transitions: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Set default allowed transitions if none provided."""
        if not self.allowed_transitions:
            self.allowed_transitions = {
                "CREATED": ["CODING"],
                "CODING": ["VALIDATING", "FAILED", "HUMAN_REVIEW"],
                "VALIDATING": ["PLANNING", "CODING", "FAILED", "HUMAN_REVIEW"],
                "PLANNING": ["APPLYING", "CODING", "FAILED", "HUMAN_REVIEW"],
                "APPLYING": ["TESTING", "CODING", "FAILED", "HUMAN_REVIEW"],
                "TESTING": ["GIT_PUSH", "CODING", "HUMAN_REVIEW"],
                "GIT_PUSH": ["CI_TRIGGER", "FAILED", "HUMAN_REVIEW"],
                "CI_TRIGGER": ["CI_MONITOR", "FAILED", "HUMAN_REVIEW"],
                "CI_MONITOR": ["COMPLETED", "CI_FAILED", "HUMAN_REVIEW"],
                "CI_FAILED": ["FAILED", "HUMAN_REVIEW"],
                "COMPLETED": [],  # Terminal state
                "FAILED": [],  # Terminal state
                "HUMAN_REVIEW": ["COMPLETED", "FAILED"],  # Escalated to human
            }

    @classmethod
    def from_env(cls) -> StateTransitionConfig:
        """Create state transition configuration from environment variables."""
        return cls(
            allowed_transitions={
                "CREATED": ["CODING"],
                "CODING": ["VALIDATING", "FAILED", "HUMAN_REVIEW"],
                "VALIDATING": ["PLANNING", "CODING", "FAILED", "HUMAN_REVIEW"],
                "PLANNING": ["APPLYING", "CODING", "FAILED", "HUMAN_REVIEW"],
                "APPLYING": ["TESTING", "CODING", "FAILED", "HUMAN_REVIEW"],
                "TESTING": ["GIT_PUSH", "CODING", "HUMAN_REVIEW"],
                "GIT_PUSH": ["CI_TRIGGER", "FAILED", "HUMAN_REVIEW"],
                "CI_TRIGGER": ["CI_MONITOR", "FAILED", "HUMAN_REVIEW"],
                "CI_MONITOR": ["COMPLETED", "CI_FAILED", "HUMAN_REVIEW"],
                "CI_FAILED": ["FAILED", "HUMAN_REVIEW"],
                "COMPLETED": [],
                "FAILED": [],
                "HUMAN_REVIEW": ["COMPLETED", "FAILED"],
            }
        )


@dataclass
class RetryConfig:
    """Configuration for retry logic."""

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    multiplier: float = 2.0
    jitter_enabled: bool = True

    def calculate_delay(self, retry_count: int) -> float:
        """Calculate delay for a given retry count using exponential backoff."""
        delay = self.base_delay * (self.multiplier**retry_count)
        if self.jitter_enabled:
            import random

            delay = delay * (0.5 + random.random())  # ±50% jitter
        return min(delay, self.max_delay)

    @classmethod
    def from_env(cls) -> RetryConfig:
        """Create retry configuration from environment variables."""
        return cls(
            max_retries=int(os.getenv("MAX_RETRY_ATTEMPTS", "3")),
            base_delay=float(os.getenv("RETRY_BASE_DELAY", "1.0")),
            max_delay=float(os.getenv("RETRY_MAX_DELAY", "60.0")),
            multiplier=float(os.getenv("RETRY_MULTIPLIER", "2.0")),
            jitter_enabled=os.getenv("RETRY_JITTER_ENABLED", "true").lower() == "true",
        )


@dataclass
class DLQConfig:
    """Configuration for dead-letter queue."""

    enabled: bool = True
    max_entries: int = 1000
    retention_days: int = 30
    notification_enabled: bool = False
    notification_endpoint: Optional[str] = None

    @classmethod
    def from_env(cls) -> DLQConfig:
        """Create DLQ configuration from environment variables."""
        return cls(
            enabled=os.getenv("DLQ_ENABLED", "true").lower() == "true",
            max_entries=int(os.getenv("DLQ_MAX_ENTRIES", "1000")),
            retention_days=int(os.getenv("DLQ_RETENTION_DAYS", "30")),
            notification_enabled=os.getenv("DLQ_NOTIFICATION_ENABLED", "false").lower()
            == "true",
            notification_endpoint=os.getenv("DLQ_NOTIFICATION_ENDPOINT"),
        )


@dataclass
class SagaConfig:
    """Configuration for saga pattern."""

    enabled: bool = True
    compensation_enabled: bool = True
    compensation_timeout: int = 1800  # 30 minutes
    max_saga_duration: int = 3600  # 1 hour

    @classmethod
    def from_env(cls) -> SagaConfig:
        """Create saga configuration from environment variables."""
        return cls(
            enabled=os.getenv("SAGA_ENABLED", "true").lower() == "true",
            compensation_enabled=os.getenv("SAGA_COMPENSATION_ENABLED", "true").lower()
            == "true",
            compensation_timeout=int(os.getenv("SAGA_COMPENSATION_TIMEOUT", "1800")),
            max_saga_duration=int(os.getenv("SAGA_MAX_DURATION", "3600")),
        )


def get_config() -> WorkflowEngineConfig:
    """Get the global configuration."""
    return WorkflowEngineConfig.from_env()


# Backward compatibility alias


WorkflowConfig = WorkflowEngineConfig
