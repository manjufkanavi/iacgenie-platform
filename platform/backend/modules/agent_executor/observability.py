"""Observability for Agent Executor."""

import time

from typing import Any, Callable, Dict, Optional

from opentelemetry import context as opentelemetry_context

from opentelemetry.sdk.trace import TracerProvider


from opentelemetry.sdk.trace.export import BatchSpanProcessor

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

from opentelemetry import trace as otel_trace

from opentelemetry.trace import SpanKind, Status, StatusCode

from opentelemetry import baggage

from opentelemetry.context import get_current

from .config import config

from .logging import logger

# Initialize the OpenTelemetry tracer

tracer_provider = TracerProvider()

span_exporter = OTLPSpanExporter(
    endpoint=config.LLM_PROXY_URL.replace("http://", "http://"), insecure=True
)

span_processor = BatchSpanProcessor(span_exporter)

tracer_provider.add_span_processor(span_processor)

# Set the global tracer provider

otel_trace.set_tracer_provider(tracer_provider)

# Create a tracer instance

tracer = otel_trace.get_tracer(__name__)

# Set up baggage for context propagation


def setup_tracing() -> Any:
    """Set up OpenTelemetry tracing for the application."""
    logger.info("OpenTelemetry tracing initialized")
    # Set up context propagation
    # This ensures trace context is propagated across processes
    # set_local_propagator was deprecated/removed in newer OpenTelemetry versions
    # Context propagation is now handled by set_global_textmap
    pass
    # Set up global trace context
    context = opentelemetry_context.get_current()
    if context is None:
        context = opentelemetry_context.set_value("trace_id", "unknown")
    return context


# Define a custom decorator for OpenTelemetry tracing


def trace(
    operation_name: Optional[str] = None, kind: SpanKind = SpanKind.INTERNAL
) -> Callable[..., Any]:
    """Decorator to trace function execution with OpenTelemetry."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:

        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get the operation name
            op_name = operation_name or func.__name__
            # Create a new span
            span = tracer.start_span(op_name, kind=kind)
            # Add context to the span
            get_current()
            opentelemetry_context.set_value("operation_name", op_name)
            opentelemetry_context.set_value("function_name", func.__name__)
            # Set up baggage with session and build IDs
            session_id = kwargs.get("session_id") or (
                args[0].get("session_id") if args else None
            )
            build_id = kwargs.get("build_id") or (
                args[0].get("build_id") if args else None
            )
            if session_id:
                baggage.set_baggage("session_id", str(session_id))
            if build_id:
                baggage.set_baggage("build_id", str(build_id))
            # Set up trace context with request ID
            request_id = str(time.time())
            baggage.set_baggage("request_id", request_id)
            # Set up trace context with operation type
            baggage.set_baggage("operation_type", op_name)
            # Execute the function
            try:
                result = func(*args, **kwargs)
                span.set_status(Status(StatusCode.OK))
                return result
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR))
                span.record_exception(e)
                logger.error(
                    "Traced operation failed",
                    extra={
                        "operation": op_name,
                        "error": str(e),
                        "session_id": session_id,
                        "build_id": build_id,
                    },
                )
                raise
            finally:
                # End the span
                span.end()

        return wrapper

    return decorator


# Helper functions for observability


def get_trace_context() -> Dict[str, Any]:
    """Get the current trace context."""
    context = get_current()
    return {
        "trace_id": context.get("trace_id") or "unknown",
        "span_id": context.get("span_id") or "unknown",
        "trace_state": context.get("trace_state") or "unknown",
    }


def add_trace_metadata(operation_name: str, metadata: Dict[str, Any]) -> None:
    """Add metadata to the current trace."""
    span = otel_trace.get_current_span()
    if span:
        for key, value in metadata.items():
            span.add_event(
                f"{operation_name}_metadata",
                {"key": key, "value": str(value), "timestamp": time.time()},
            )


def log_info(message: str, extra: Optional[Dict[str, Any]] = None) -> None:
    """Log an info message with trace context."""
    logger.info(message, extra=extra)


def log_error(message: str, extra: Optional[Dict[str, Any]] = None) -> None:
    """Log an error message with trace context."""
    logger.error(message, extra=extra)


def log_debug(message: str, extra: Optional[Dict[str, Any]] = None) -> None:
    """Log a debug message with trace context."""
    logger.debug(message, extra=extra)


def log_warning(message: str, extra: Optional[Dict[str, Any]] = None) -> None:
    """Log a warning message with trace context."""
    logger.warning(message, extra=extra)


# Export the tracer for use in other modules


__all__ = [
    "tracer",
    "trace",
    "setup_tracing",
    "get_trace_context",
    "add_trace_metadata",
    "log_info",
    "log_error",
    "log_debug",
    "log_warning",
]
