"""
Maestro-Hive OpenTelemetry Tracing Module
Epic: MD-1901 - Maestro-Hive Observability Integration
Task: MD-1905 - Integrate OpenTelemetry tracing

Provides:
- Distributed tracing with OpenTelemetry
- Trace context propagation
- Span creation and management
- OTLP exporter configuration
"""

import functools
import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, TypeVar

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.trace import Span, SpanKind, Status, StatusCode, Tracer

F = TypeVar("F", bound=Callable[..., Any])


# =============================================================================
# Configuration
# =============================================================================


@dataclass
class TracingConfig:
    """
    Configuration for OpenTelemetry tracing.

    Attributes:
        service_name: Name of the service for tracing
        environment: Deployment environment
        otlp_endpoint: OTLP collector endpoint
        enable_console_export: Whether to export spans to console (dev mode)
        sample_rate: Sampling rate (0.0 to 1.0)
        enabled: Whether tracing is enabled
    """

    service_name: str = "maestro-hive"
    environment: str = field(default_factory=lambda: os.getenv("HIVE_ENV", "development"))
    otlp_endpoint: Optional[str] = field(
        default_factory=lambda: os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    )
    enable_console_export: bool = field(
        default_factory=lambda: os.getenv("HIVE_ENV", "development") == "development"
    )
    sample_rate: float = 1.0
    enabled: bool = field(
        default_factory=lambda: os.getenv("OTEL_TRACING_ENABLED", "true").lower() == "true"
    )


# =============================================================================
# Tracing Setup
# =============================================================================

_tracer_provider: Optional[TracerProvider] = None
_config: Optional[TracingConfig] = None


def configure_tracing(config: Optional[TracingConfig] = None) -> None:
    """
    Configure OpenTelemetry tracing for Maestro-Hive.

    Args:
        config: Tracing configuration. If None, uses defaults.

    Example:
        >>> config = TracingConfig(
        ...     service_name="maestro-hive",
        ...     otlp_endpoint="http://jaeger:4317",
        ... )
        >>> configure_tracing(config)
    """
    global _tracer_provider, _config

    _config = config or TracingConfig()

    if not _config.enabled:
        return

    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": _config.service_name,
            "service.version": "1.0.0",
            "deployment.environment": _config.environment,
            "service.component": "trimodal-validation",
        }
    )

    # Create tracer provider
    _tracer_provider = TracerProvider(resource=resource)

    # Add OTLP exporter if endpoint is configured
    if _config.otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(
            endpoint=_config.otlp_endpoint,
            insecure=True,
        )
        _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Add console exporter for development
    if _config.enable_console_export and not _config.otlp_endpoint:
        console_exporter = ConsoleSpanExporter()
        _tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))

    # Set as global tracer provider
    trace.set_tracer_provider(_tracer_provider)

    # Instrument logging to include trace context
    LoggingInstrumentor().instrument()


def get_tracer(name: str = "maestro-hive") -> Tracer:
    """
    Get a tracer instance.

    Args:
        name: Tracer name (typically module name)

    Returns:
        OpenTelemetry Tracer instance

    Example:
        >>> tracer = get_tracer(__name__)
        >>> with tracer.start_as_current_span("operation"):
        ...     do_work()
    """
    return trace.get_tracer(name)


def get_current_span() -> Span:
    """Get the current active span."""
    return trace.get_current_span()


def get_trace_context() -> Dict[str, str]:
    """
    Get current trace context for propagation.

    Returns:
        Dictionary with trace_id and span_id
    """
    span = get_current_span()
    ctx = span.get_span_context()

    if ctx.is_valid:
        return {
            "trace_id": format(ctx.trace_id, "032x"),
            "span_id": format(ctx.span_id, "016x"),
        }
    return {}


# =============================================================================
# Decorators
# =============================================================================


def trace_function(
    name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None,
) -> Callable[[F], F]:
    """
    Decorator to trace a function execution.

    Args:
        name: Span name (defaults to function name)
        kind: Span kind (INTERNAL, SERVER, CLIENT, PRODUCER, CONSUMER)
        attributes: Additional span attributes

    Returns:
        Decorated function

    Example:
        @trace_function(name="process_audit", attributes={"stream": "dde"})
        async def process_audit(iteration_id: str):
            ...
    """

    def decorator(func: F) -> F:
        span_name = name or func.__name__
        tracer = get_tracer(func.__module__ or "maestro-hive")

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(
                span_name,
                kind=kind,
                attributes=attributes or {},
            ) as span:
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            with tracer.start_as_current_span(
                span_name,
                kind=kind,
                attributes=attributes or {},
            ) as span:
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


# =============================================================================
# Context Managers
# =============================================================================


class TracedOperation:
    """
    Context manager for creating traced operations.

    Example:
        >>> with TracedOperation("audit_execution", iteration_id="abc123") as span:
        ...     result = execute_audit()
        ...     span.set_attribute("verdict", result.verdict)
    """

    def __init__(
        self,
        name: str,
        kind: SpanKind = SpanKind.INTERNAL,
        **attributes: Any,
    ):
        self.name = name
        self.kind = kind
        self.attributes = attributes
        self._tracer = get_tracer("maestro-hive")
        self._span: Optional[Span] = None

    def __enter__(self) -> Span:
        self._span = self._tracer.start_span(
            self.name,
            kind=self.kind,
            attributes=self.attributes,
        )
        return self._span

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._span:
            if exc_type is not None:
                self._span.set_status(Status(StatusCode.ERROR, str(exc_val)))
                self._span.record_exception(exc_val)
            else:
                self._span.set_status(Status(StatusCode.OK))
            self._span.end()


# =============================================================================
# Convenience Functions
# =============================================================================


def add_span_attributes(**attributes: Any) -> None:
    """
    Add attributes to the current span.

    Args:
        **attributes: Key-value pairs to add as span attributes

    Example:
        >>> add_span_attributes(iteration_id="abc123", verdict="ALL_PASS")
    """
    span = get_current_span()
    for key, value in attributes.items():
        if value is not None:
            span.set_attribute(key, value)


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    Add an event to the current span.

    Args:
        name: Event name
        attributes: Optional event attributes

    Example:
        >>> add_span_event("dde_completed", {"passed": True, "violations": 0})
    """
    span = get_current_span()
    span.add_event(name, attributes=attributes or {})


def record_exception(exception: Exception, attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    Record an exception in the current span.

    Args:
        exception: Exception to record
        attributes: Optional additional attributes
    """
    span = get_current_span()
    span.record_exception(exception, attributes=attributes or {})
    span.set_status(Status(StatusCode.ERROR, str(exception)))


# =============================================================================
# Trimodal-Specific Tracing
# =============================================================================


def trace_audit_execution(iteration_id: str, task_id: Optional[str] = None):
    """
    Create a traced context for a trimodal audit execution.

    Args:
        iteration_id: Execution iteration ID
        task_id: Optional JIRA task ID

    Returns:
        TracedOperation context manager

    Example:
        >>> with trace_audit_execution("iter_123", "MD-1234") as span:
        ...     result = run_trimodal_audit()
        ...     span.set_attribute("verdict", result.verdict)
    """
    return TracedOperation(
        "trimodal_audit",
        kind=SpanKind.INTERNAL,
        iteration_id=iteration_id,
        task_id=task_id or "unknown",
    )


def trace_stream_execution(stream: str, iteration_id: str):
    """
    Create a traced context for a single stream execution (DDE, BDV, ACC).

    Args:
        stream: Stream name (dde, bdv, acc)
        iteration_id: Execution iteration ID

    Returns:
        TracedOperation context manager

    Example:
        >>> with trace_stream_execution("dde", "iter_123") as span:
        ...     result = run_dde_checks()
        ...     span.set_attribute("passed", result.passed)
    """
    return TracedOperation(
        f"{stream}_execution",
        kind=SpanKind.INTERNAL,
        stream=stream,
        iteration_id=iteration_id,
    )


def trace_webhook_delivery(webhook_id: str, url: str):
    """
    Create a traced context for webhook delivery.

    Args:
        webhook_id: Webhook configuration ID
        url: Target URL

    Returns:
        TracedOperation context manager
    """
    return TracedOperation(
        "webhook_delivery",
        kind=SpanKind.CLIENT,
        webhook_id=webhook_id,
        url=url,
    )


def trace_gate_check(iteration_id: str):
    """
    Create a traced context for deployment gate check.

    Args:
        iteration_id: Execution iteration ID

    Returns:
        TracedOperation context manager
    """
    return TracedOperation(
        "deployment_gate_check",
        kind=SpanKind.INTERNAL,
        iteration_id=iteration_id,
    )
