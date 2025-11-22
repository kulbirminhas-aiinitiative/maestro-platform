"""
Distributed tracing for UTCP services using OpenTelemetry.

Provides end-to-end request tracing across the service mesh,
enabling performance analysis and bottleneck detection.
"""

import time
from typing import Any, Callable, Dict, Optional
from contextlib import asynccontextmanager
from functools import wraps

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
)
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import Status, StatusCode
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

from maestro_core_logging import get_logger

logger = get_logger(__name__)

# Global tracer
_tracer: Optional[trace.Tracer] = None
_propagator = TraceContextTextMapPropagator()


def configure_tracing(
    service_name: str,
    environment: str = "development",
    enable_console: bool = False,
    jaeger_endpoint: Optional[str] = None
):
    """
    Configure OpenTelemetry tracing for the service.

    Args:
        service_name: Name of the service
        environment: Deployment environment
        enable_console: Enable console exporter for debugging
        jaeger_endpoint: Jaeger collector endpoint

    Example:
        >>> configure_tracing(
        >>>     service_name="workflow-engine",
        >>>     environment="production",
        >>>     jaeger_endpoint="http://jaeger:14268/api/traces"
        >>> )
    """
    global _tracer

    # Create resource with service information
    resource = Resource.create({
        "service.name": service_name,
        "service.namespace": "maestro-utcp",
        "deployment.environment": environment,
    })

    # Create tracer provider
    provider = TracerProvider(resource=resource)

    # Add console exporter if enabled
    if enable_console:
        console_exporter = ConsoleSpanExporter()
        console_processor = BatchSpanProcessor(console_exporter)
        provider.add_span_processor(console_processor)

    # Add Jaeger exporter if endpoint provided
    if jaeger_endpoint:
        try:
            from opentelemetry.exporter.jaeger.thrift import JaegerExporter

            jaeger_exporter = JaegerExporter(
                collector_endpoint=jaeger_endpoint,
            )
            jaeger_processor = BatchSpanProcessor(jaeger_exporter)
            provider.add_span_processor(jaeger_processor)

            logger.info(
                "Jaeger tracing configured",
                service=service_name,
                endpoint=jaeger_endpoint
            )
        except ImportError:
            logger.warning(
                "Jaeger exporter not available, install opentelemetry-exporter-jaeger"
            )

    # Set as global tracer provider
    trace.set_tracer_provider(provider)
    _tracer = trace.get_tracer(service_name)

    logger.info("OpenTelemetry tracing configured", service=service_name)


def get_tracer() -> trace.Tracer:
    """
    Get the global tracer instance.

    Returns:
        Tracer instance

    Raises:
        RuntimeError: If tracing not configured
    """
    if _tracer is None:
        raise RuntimeError(
            "Tracing not configured. Call configure_tracing() first."
        )
    return _tracer


@asynccontextmanager
async def trace_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    set_status_on_exception: bool = True
):
    """
    Create a traced span context.

    Args:
        name: Span name
        attributes: Additional span attributes
        set_status_on_exception: Set error status on exception

    Example:
        >>> async with trace_span("call_service", {"service": "workflow-engine"}):
        >>>     result = await call_service()
    """
    tracer = get_tracer()

    with tracer.start_as_current_span(name) as span:
        # Add attributes
        if attributes:
            for key, value in attributes.items():
                span.set_attribute(key, str(value))

        # Add standard attributes
        span.set_attribute("maestro.timestamp", time.time())

        try:
            yield span
        except Exception as e:
            if set_status_on_exception:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
            raise


def trace_function(
    span_name: Optional[str] = None,
    attributes: Optional[Dict[str, Any]] = None
):
    """
    Decorator to trace function execution.

    Args:
        span_name: Custom span name (defaults to function name)
        attributes: Additional span attributes

    Example:
        >>> @trace_function(span_name="process_workflow")
        >>> async def process_workflow(workflow_id: str):
        >>>     # Function implementation
        >>>     pass
    """

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            name = span_name or f"{func.__module__}.{func.__name__}"
            func_attributes = attributes or {}

            # Add function info
            func_attributes["function.name"] = func.__name__
            func_attributes["function.module"] = func.__module__

            async with trace_span(name, func_attributes):
                return await func(*args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            name = span_name or f"{func.__module__}.{func.__name__}"
            func_attributes = attributes or {}

            func_attributes["function.name"] = func.__name__
            func_attributes["function.module"] = func.__module__

            tracer = get_tracer()
            with tracer.start_as_current_span(name) as span:
                for key, value in func_attributes.items():
                    span.set_attribute(key, str(value))

                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


class UTCPTracer:
    """
    Specialized tracer for UTCP tool calls.

    Provides automatic tracing for UTCP service discovery,
    tool calls, and orchestration.

    Example:
        >>> tracer = UTCPTracer("workflow-engine")
        >>>
        >>> async with tracer.trace_tool_call("create_workflow", tool_input):
        >>>     result = await execute_tool()
    """

    def __init__(self, service_name: str):
        """
        Initialize UTCP tracer.

        Args:
            service_name: Name of the UTCP service
        """
        self.service_name = service_name
        self.tracer = get_tracer()

    @asynccontextmanager
    async def trace_tool_call(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        service_url: Optional[str] = None
    ):
        """
        Trace a UTCP tool call.

        Args:
            tool_name: Name of the tool being called
            tool_input: Tool input parameters
            service_url: Target service URL

        Yields:
            Span for the tool call
        """
        span_name = f"utcp.tool_call.{tool_name}"

        with self.tracer.start_as_current_span(span_name) as span:
            # Add UTCP-specific attributes
            span.set_attribute("utcp.tool_name", tool_name)
            span.set_attribute("utcp.service_name", self.service_name)
            span.set_attribute("utcp.input_keys", list(tool_input.keys()))

            if service_url:
                span.set_attribute("utcp.service_url", service_url)

            start_time = time.time()

            try:
                yield span

                # Record success metrics
                duration = time.time() - start_time
                span.set_attribute("utcp.call_duration_ms", duration * 1000)
                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                # Record failure
                duration = time.time() - start_time
                span.set_attribute("utcp.call_duration_ms", duration * 1000)
                span.set_attribute("utcp.error", str(e))
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    @asynccontextmanager
    async def trace_service_discovery(self, service_url: str):
        """
        Trace service discovery operation.

        Args:
            service_url: URL being discovered

        Yields:
            Span for service discovery
        """
        with self.tracer.start_as_current_span("utcp.service_discovery") as span:
            span.set_attribute("utcp.discovery_url", service_url)
            span.set_attribute("utcp.discovery_service", self.service_name)

            start_time = time.time()

            try:
                yield span

                duration = time.time() - start_time
                span.set_attribute("utcp.discovery_duration_ms", duration * 1000)
                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                duration = time.time() - start_time
                span.set_attribute("utcp.discovery_duration_ms", duration * 1000)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    @asynccontextmanager
    async def trace_orchestration(
        self,
        requirement: str,
        available_tools: int
    ):
        """
        Trace Claude orchestration operation.

        Args:
            requirement: User requirement being orchestrated
            available_tools: Number of available tools

        Yields:
            Span for orchestration
        """
        with self.tracer.start_as_current_span("utcp.orchestration") as span:
            span.set_attribute("utcp.requirement_length", len(requirement))
            span.set_attribute("utcp.available_tools", available_tools)
            span.set_attribute("utcp.orchestrator", "claude")

            start_time = time.time()
            tool_calls_made = 0

            try:
                # Span will be updated during orchestration
                span.set_attribute("utcp.tool_calls_made", tool_calls_made)
                yield span

                duration = time.time() - start_time
                span.set_attribute("utcp.orchestration_duration_ms", duration * 1000)
                span.set_status(Status(StatusCode.OK))

            except Exception as e:
                duration = time.time() - start_time
                span.set_attribute("utcp.orchestration_duration_ms", duration * 1000)
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise


def inject_trace_context(headers: Dict[str, str]) -> Dict[str, str]:
    """
    Inject trace context into HTTP headers for propagation.

    Args:
        headers: Existing headers dictionary

    Returns:
        Headers with trace context injected
    """
    _propagator.inject(headers)
    return headers


def extract_trace_context(headers: Dict[str, str]) -> trace.Context:
    """
    Extract trace context from HTTP headers.

    Args:
        headers: HTTP headers containing trace context

    Returns:
        Trace context
    """
    return _propagator.extract(headers)