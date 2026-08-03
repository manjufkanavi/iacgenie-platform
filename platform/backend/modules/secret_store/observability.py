"""

Secret Store Observability

OpenTelemetry tracing and metrics for the Secret Store module.

"""

import functools

import time

from contextlib import contextmanager

from typing import Any, Callable, Dict, Optional

from opentelemetry import trace, metrics

from opentelemetry.trace import SpanKind, Status, StatusCode

# Get tracer and meter from OpenTelemetry

tracer = trace.get_tracer(__name__)

meter = metrics.get_meter(__name__)

# Metrics

SECRET_ACCESS_COUNTER = meter.create_counter(
    name="secret_store_secret_access_total",
    description="Total number of secret access attempts",
)

SECRET_ACCESS_DURATION_HISTOGRAM = meter.create_histogram(
    name="secret_store_secret_access_duration_seconds",
    description="Duration of secret access operations",
)

SECRET_ACCESS_FAILURE_COUNTER = meter.create_counter(
    name="secret_store_secret_access_failure_total",
    description="Total number of secret access failures",
)

# Secret operation types

SECRET_OPERATION_TYPES = ["create", "read", "update", "delete", "access", "generate"]

# Secret types

SECRET_TYPES = ["git_token", "ci_pat", "llm_api_key", "sandbox_creds", "generic"]


def record_secret_access_metric(
    user_id: str,
    secret_name: str,
    operation: str,
    success: bool,
    duration_seconds: Optional[float] = None,
    secret_type: str = "generic",
) -> None:
    """
    Record a secret access metric.
    Args:
        user_id: The tenant/user ID.
        secret_name: The name of the secret.
        operation: The operation performed (access, create, update, delete, generate).
        success: Whether the operation succeeded.
        duration_seconds: Duration of the operation in seconds (optional).
        secret_type: Type of secret (default: 'generic').
    """
    # Add operation and secret_type as labels
    labels = {
        "user_id": user_id,
        "secret_name": secret_name,
        "operation": operation,
        "secret_type": secret_type,
        "success": str(success).lower(),
    }
    # Increment counter
    if success:
        SECRET_ACCESS_COUNTER.add(1, labels)
    else:
        SECRET_ACCESS_FAILURE_COUNTER.add(1, labels)
    # Record duration if provided
    if duration_seconds is not None:
        SECRET_ACCESS_DURATION_HISTOGRAM.record(duration_seconds, labels)


@contextmanager
def secret_access_span(
    name: str,
    user_id: str,
    secret_name: str,
    operation: str,
    secret_type: str = "generic",
) -> Any:
    """
    Context manager for secret access tracing span.
    Args:
        name: Span name.
        user_id: The tenant/user ID.
        secret_name: The name of the secret.
        operation: The operation being performed.
        secret_type: Type of secret (default: 'generic').
    Yields:
        The span object.
    """
    span_attributes = {
        "user_id": user_id,
        "secret_name": secret_name,
        "operation": operation,
        "secret_type": secret_type,
    }
    with tracer.start_as_current_span(
        f"secret_store.{name}",
        attributes=span_attributes,
        kind=SpanKind.INTERNAL,
    ) as span:
        try:
            yield span
            span.set_status(Status(StatusCode.OK))
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            raise


def trace_secret_access(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to trace secret access operations.
    Args:
        func: The function to trace.
    Returns:
        The wrapped function.
    """

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Extract parameters from function call
        user_id = kwargs.get("user_id", "")
        secret_name = kwargs.get("secret_name", "")
        operation = kwargs.get("operation", "unknown")
        secret_type = kwargs.get("secret_type", "generic")
        session_id = kwargs.get("session_id", "")
        build_id = kwargs.get("build_id", "")
        span_attributes = {
            "user_id": user_id,
            "secret_name": secret_name,
            "operation": operation,
            "secret_type": secret_type,
            "session_id": session_id,
            "build_id": build_id,
        }
        with tracer.start_as_current_span(
            f"secret_store.{func.__name__}",
            attributes=span_attributes,
            kind=SpanKind.INTERNAL,
        ) as span:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                # Record metrics
                record_secret_access_metric(
                    user_id=user_id,
                    secret_name=secret_name,
                    operation=operation,
                    success=True,
                    duration_seconds=duration,
                    secret_type=secret_type,
                )
                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as e:
                duration = time.time() - start_time
                # Record metrics
                record_secret_access_metric(
                    user_id=user_id,
                    secret_name=secret_name,
                    operation=operation,
                    success=False,
                    duration_seconds=duration,
                    secret_type=secret_type,
                )
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper


def trace_secret_access_async(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator to trace async secret access operations.
    Args:
        func: The async function to trace.
    Returns:
        The wrapped async function.
    """

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Extract parameters from function call
        user_id = kwargs.get("user_id", "")
        secret_name = kwargs.get("secret_name", "")
        operation = kwargs.get("operation", "unknown")
        secret_type = kwargs.get("secret_type", "generic")
        session_id = kwargs.get("session_id", "")
        build_id = kwargs.get("build_id", "")
        span_attributes = {
            "user_id": user_id,
            "secret_name": secret_name,
            "operation": operation,
            "secret_type": secret_type,
            "session_id": session_id,
            "build_id": build_id,
        }
        with tracer.start_as_current_span(
            f"secret_store.{func.__name__}",
            attributes=span_attributes,
            kind=SpanKind.INTERNAL,
        ) as span:
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                # Record metrics
                record_secret_access_metric(
                    user_id=user_id,
                    secret_name=secret_name,
                    operation=operation,
                    success=True,
                    duration_seconds=duration,
                    secret_type=secret_type,
                )
                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as e:
                duration = time.time() - start_time
                # Record metrics
                record_secret_access_metric(
                    user_id=user_id,
                    secret_name=secret_name,
                    operation=operation,
                    success=False,
                    duration_seconds=duration,
                    secret_type=secret_type,
                )
                span.set_status(Status(StatusCode.ERROR, str(e)))
                raise

    return wrapper


class SecretAccessMetrics:
    """
    Metrics class for Secret Store.
    Provides methods for recording custom metrics.
    """

    def __init__(self) -> None:
        """Initialize the metrics class."""
        self._meter = meter

    def record_secret_retrieval(
        self,
        user_id: str,
        secret_name: str,
        duration_ms: float,
        vault_path: str,
    ) -> None:
        """
        Record secret retrieval metrics.
        Args:
            user_id: The tenant/user ID.
            secret_name: The name of the secret.
            duration_ms: Duration in milliseconds.
            vault_path: Vault path of the secret.
        """
        labels = {
            "user_id": user_id,
            "secret_name": secret_name,
            "vault_path": vault_path,
        }
        # Record duration histogram
        SECRET_ACCESS_DURATION_HISTOGRAM.record(
            duration_ms / 1000.0,  # Convert to seconds
            labels,
        )

    def record_token_generation(
        self,
        user_id: str,
        secret_name: str,
        ttl_minutes: int,
        duration_ms: float,
    ) -> None:
        """
        Record token generation metrics.
        Args:
            user_id: The tenant/user ID.
            secret_name: The name of the secret.
            ttl_minutes: Token TTL in minutes.
            duration_ms: Duration in milliseconds.
        """
        labels = {
            "user_id": user_id,
            "secret_name": secret_name,
            "ttl_minutes": str(ttl_minutes),
        }
        # Record duration histogram
        SECRET_ACCESS_DURATION_HISTOGRAM.record(
            duration_ms / 1000.0,  # Convert to seconds
            labels,
        )

    def record_audit_log(
        self,
        user_id: str,
        secret_name: str,
        operation: str,
        success: bool,
    ) -> None:
        """
        Record audit log metrics.
        Args:
            user_id: The tenant/user ID.
            secret_name: The name of the secret.
            operation: The audit operation.
            success: Whether the audit log was written successfully.
        """
        labels = {
            "user_id": user_id,
            "secret_name": secret_name,
            "operation": operation,
            "success": str(success).lower(),
        }
        # Increment counter
        if success:
            SECRET_ACCESS_COUNTER.add(1, labels)
        else:
            SECRET_ACCESS_FAILURE_COUNTER.add(1, labels)

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get current metrics.
        Returns:
            Dictionary of current metrics.
        """
        return {
            "secret_access_total": SECRET_ACCESS_COUNTER,
            "secret_access_duration": SECRET_ACCESS_DURATION_HISTOGRAM,
            "secret_access_failure_total": SECRET_ACCESS_FAILURE_COUNTER,
        }


def observe_secret_access(
    user_id: str,
    secret_name: str,
    operation: str,
    secret_type: str = "generic",
) -> Callable[..., Any]:
    """
    Decorator factory for observing secret access.
    Args:
        user_id: The tenant/user ID.
        secret_name: The name of the secret.
        operation: The operation being performed.
        secret_type: Type of secret (default: 'generic').
    Returns:
        The decorator.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            span_attributes = {
                "user_id": user_id,
                "secret_name": secret_name,
                "operation": operation,
                "secret_type": secret_type,
            }
            with tracer.start_as_current_span(
                f"secret_store.{func.__name__}",
                attributes=span_attributes,
                kind=SpanKind.INTERNAL,
            ) as span:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    record_secret_access_metric(
                        user_id=user_id,
                        secret_name=secret_name,
                        operation=operation,
                        success=True,
                        duration_seconds=duration,
                        secret_type=secret_type,
                    )
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    record_secret_access_metric(
                        user_id=user_id,
                        secret_name=secret_name,
                        operation=operation,
                        success=False,
                        duration_seconds=duration,
                        secret_type=secret_type,
                    )
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise

        return wrapper

    return decorator
