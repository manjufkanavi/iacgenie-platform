"""Prometheus metrics for pipeline execution."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, REGISTRY

# Pipeline lifecycle metrics

PIPELINE_CREATED = Counter(
    "pipeline_created_total",
    "Total pipelines created",
    ["tenant_id"],
)

PIPELINE_COMPLETED = Counter(
    "pipeline_completed_total",
    "Total pipelines completed successfully",
    ["tenant_id"],
)

PIPELINE_FAILED = Counter(
    "pipeline_failed_total",
    "Total pipelines that failed",
    ["tenant_id"],
)

# Phase transition metric

PHASE_TRANSITION = Counter(
    "pipeline_phase_transition_total",
    "Phase transitions in pipelines",
    ["from_phase", "to_phase"],
)

# Duration metrics

PIPELINE_DURATION = Histogram(
    "pipeline_duration_seconds",
    "Pipeline execution duration from start to completion",
    ["final_phase"],
)

AGENT_EXECUTION_TIME = Histogram(
    "agent_execution_seconds",
    "Agent execution time per phase",
    ["agent_type", "phase"],
)

# Error metrics

ERROR_COUNT = Counter(
    "pipeline_error_total",
    "Pipeline errors by severity and category",
    ["severity", "category"],
)

# Active pipeline gauge

ACTIVE_PIPELINES = Gauge(
    "active_pipelines",
    "Number of currently running pipelines",
)


def init_metrics() -> None:
    """Register all metrics with the Prometheus registry."""
    # Metrics are auto-registered on creation; this is a no-op placeholder
    # for explicit initialization if needed in the future.
    pass


def get_metrics() -> bytes:
    """Return Prometheus-formatted metrics string."""
    return generate_latest(REGISTRY)


def record_phase_transition(from_phase: str, to_phase: str) -> None:
    PHASE_TRANSITION.labels(from_phase=from_phase, to_phase=to_phase).inc()


def record_agent_execution(
    agent_type: str, phase: str, duration_seconds: float
) -> None:
    AGENT_EXECUTION_TIME.labels(agent_type=agent_type, phase=phase).observe(
        duration_seconds
    )


def record_error(severity: str, category: str) -> None:
    ERROR_COUNT.labels(severity=severity, category=category).inc()


# Generation metrics
GENERATION_COUNT = Counter(
    "iacgenie_generations_total",
    "Total generations by provider",
    ["provider", "status"],
)

GENERATION_DURATION = Histogram(
    "iacgenie_generation_duration_seconds",
    "Time to complete a generation",
    ["provider"],
)

TOKEN_USAGE = Histogram(
    "iacgenie_token_usage",
    "Tokens used per generation",
    ["type"],  # prompt, completion, total
)

ACTIVE_GENERATIONS = Gauge(
    "iacgenie_active_generations",
    "Currently running generations",
)

CONNECTION_COUNT = Gauge(
    "iacgenie_websocket_connections",
    "Connected WebSocket clients",
)
