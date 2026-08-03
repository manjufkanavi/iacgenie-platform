"""

Metrics Service

Provides Prometheus metrics collection and exposure,
including LLM proxy metrics.

"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from config.logging import get_logger

logger = get_logger("metrics")


class MetricsService:
    """Prometheus metrics collection service"""

    def __init__(self) -> None:
        # HTTP request metrics
        self.http_requests_total = Counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status_code"],
        )
        self.http_request_duration_seconds = Histogram(
            "http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint"],
        )
        # LLM proxy metrics
        self.llm_requests_total = Counter(
            "llm_requests_total",
            "Total LLM requests per model and status",
            ["model", "status", "cached"],
        )
        self.llm_latency_seconds = Histogram(
            "llm_latency_seconds",
            "LLM completion latency in seconds",
            ["provider", "model", "status"],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0],
        )
        self.llm_token_total = Counter(
            "llm_token_usage_total",
            "Total tokens consumed per model",
            ["provider", "model"],
        )
        self.llm_cost_total = Counter(
            "llm_cost_total", "Total estimated cost in USD per model", ["model"]
        )
        self.llm_failover_total = Counter(
            "llm_failover_total",
            "Total model failovers triggered",
            ["from_model", "to_model"],
        )
        self.llm_cache_hits_total = Counter(
            "llm_cache_hits_total", "Total cache hits for LLM responses", ["model"]
        )
        self.llm_cache_misses_total = Counter(
            "llm_cache_misses_total", "Total cache misses for LLM responses", ["model"]
        )
        self.llm_active_requests = Gauge(
            "llm_active_requests", "Current active LLM requests", ["model"]
        )
        # System metrics
        self.database_connections_gauge = Gauge(
            "database_connections_total", "Number of active database connections"
        )
        self.redis_connections_gauge = Gauge(
            "redis_connections_total", "Number of active Redis connections"
        )
        # Error metrics
        self.errors_total = Counter(
            "errors_total", "Total errors by type", ["error_type", "component"]
        )
        # Authentication metrics
        self.auth_attempts_total = Counter(
            "auth_attempts_total", "Total authentication attempts", ["method", "status"]
        )
        self.auth_failures_total = Counter(
            "auth_failures_total", "Total authentication failures", ["reason"]
        )

    def record_http_request(
        self, method: str, endpoint: str, status_code: int, duration: float
    ) -> None:
        """Record HTTP request metrics"""
        self.http_requests_total.labels(
            method=method, endpoint=endpoint, status_code=status_code
        ).inc()
        self.http_request_duration_seconds.labels(
            method=method, endpoint=endpoint
        ).observe(duration)

    def record_error(self, error_type: str, component: str) -> None:
        """Record error metrics"""
        self.errors_total.labels(error_type=error_type, component=component).inc()

    def record_auth_attempt(self, method: str, status: str) -> None:
        """Record authentication attempt metrics"""
        self.auth_attempts_total.labels(method=method, status=status).inc()
        if status == "failure":
            self.auth_failures_total.labels(reason=method).inc()

    def set_database_connections(self, count: int) -> None:
        """Set database connections gauge"""
        self.database_connections_gauge.set(count)

    def set_redis_connections(self, count: int) -> None:
        """Set Redis connections gauge"""
        self.redis_connections_gauge.set(count)

    def record_llm_request(
        self, model: str, status: str = "success", cached: bool = False
    ) -> None:
        """Record LLM request."""
        self.llm_requests_total.labels(
            model=model, status=status, cached=str(cached).lower()
        ).inc()

    def record_llm_latency(
        self, provider: str, model: str, latency_s: float, status: str = "success"
    ) -> None:
        """Record LLM latency."""
        self.llm_latency_seconds.labels(
            provider=provider, model=model, status=status
        ).observe(latency_s)

    def record_llm_tokens(self, provider: str, model: str, total_tokens: int) -> None:
        """Record token usage."""
        if total_tokens > 0:
            self.llm_token_total.labels(provider=provider, model=model).inc(
                total_tokens
            )

    def record_llm_cost(self, model: str, cost_usd: float) -> None:
        """Record estimated cost."""
        if cost_usd > 0:
            self.llm_cost_total.labels(model=model).inc(cost_usd)

    def record_llm_failover(self, from_model: str, to_model: str) -> None:
        """Record model failover."""
        self.llm_failover_total.labels(from_model=from_model, to_model=to_model).inc()

    def record_llm_cache_hit(self, model: str) -> None:
        """Record cache hit."""
        self.llm_cache_hits_total.labels(model=model).inc()

    def record_llm_cache_miss(self, model: str) -> None:
        """Record cache miss."""
        self.llm_cache_misses_total.labels(model=model).inc()

    def set_llm_active_requests(self, model: str, count: int) -> None:
        """Set active LLM request count."""
        self.llm_active_requests.labels(model=model).set(count)

    def record_database_health_check(
        self, provider: str, is_healthy: bool, duration_ms: float
    ) -> None:
        """Record database health check metrics"""
        health_status = "healthy" if is_healthy else "unhealthy"
        self.errors_total.labels(
            error_type="database_health", component=provider
        ).inc() if not is_healthy else None
        logger.debug(
            f"Database health check recorded: {provider} - {health_status} - {duration_ms}ms"
        )

    def get_metrics(self) -> bytes:
        """Get Prometheus metrics as bytes"""
        return generate_latest()

    def get_metrics_content_type(self) -> str:
        """Get content type for metrics endpoint"""
        return CONTENT_TYPE_LATEST


# Global metrics service instance


metrics_service = MetricsService()
