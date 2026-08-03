"""OpenTelemetry tracing integration for pipeline execution."""

from typing import Dict, Any

import uuid

_tracer: Any = None


def init_tracing(service_name: str = "iacgenie-backend") -> None:
    """Initialize OpenTelemetry tracer provider with console exporter."""
    global _tracer
    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.resources import Resource

        resource = Resource.create({"service.name": service_name})
        provider = TracerProvider(resource=resource)
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        otlp_exporter = OTLPSpanExporter(
            endpoint="http://otel-collector:4317", insecure=True
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer(service_name)
    except ImportError:
        # Fallback: no-op tracer when OpenTelemetry is not installed
        _tracer = _NoOpTracer()


def get_tracer(name: str = "iacgenie") -> Any:
    if _tracer is None:
        init_tracing()
    return _tracer


def start_pipeline_trace(session_id: str) -> Dict[str, Any]:
    """Start a trace span for an entire pipeline execution."""
    tracer = get_tracer()
    span = tracer.start_span(f"pipeline.{session_id}")
    span.set_attribute("pipeline.session_id", session_id)
    return {
        "trace_id": format(span.get_span_context().trace_id, "032x"),
        "span_id": span,
    }


def end_pipeline_trace(span: Any, status: str) -> None:
    """End a pipeline trace span."""
    if span is not None:
        span.set_attribute("pipeline.status", status)
        span.end()


def start_phase_span(trace_id: str, phase_name: str) -> Dict[str, Any]:
    """Start a span for a single pipeline phase."""
    tracer = get_tracer()
    span = tracer.start_span(f"phase.{phase_name}")
    span.set_attribute("pipeline.trace_id", trace_id)
    span.set_attribute("phase.name", phase_name)
    return {"span_id": format(span.get_span_context().span_id, "016x"), "span": span}


def end_phase_span(span: Any, status: str) -> None:
    """End a phase span."""
    if span is not None:
        span.set_attribute("phase.status", status)
        span.end()


def shutdown_tracing() -> None:
    """Gracefully shut down the tracer provider."""
    if hasattr(_tracer, "shutdown"):
        _tracer.shutdown()


class _NoOpTracer:
    """Minimal no-op tracer when OpenTelemetry is not installed."""

    def start_span(self, name: str) -> "_NoOpSpan":
        return _NoOpSpan(name)

    def shutdown(self):
        pass


class _NoOpSpan:
    """Minimal no-op span."""

    def __init__(self, name: str):
        self.name = name

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def end(self) -> None:
        pass

    @property
    def get_span_context(self):

        class Context:
            trace_id = int(uuid.uuid4().hex[:32], 16)
            span_id = int(uuid.uuid4().hex[:16], 16)

        return Context()
