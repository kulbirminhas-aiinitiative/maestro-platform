"""
OpenTelemetry Distributed Tracing Configuration

Provides distributed tracing instrumentation for the Maestro ML platform.
Exports traces to Jaeger for visualization and analysis.
"""

import os
from typing import Optional
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from fastapi import FastAPI


class TracingManager:
    """Manages OpenTelemetry tracing configuration and instrumentation."""

    def __init__(
        self,
        service_name: str = "maestro-ml-api",
        service_version: str = "1.0.0",
        jaeger_host: str = "jaeger.observability.svc.cluster.local",
        jaeger_port: int = 6831,
        enabled: bool = True
    ):
        """
        Initialize tracing manager.

        Args:
            service_name: Name of the service
            service_version: Version of the service
            jaeger_host: Jaeger agent hostname
            jaeger_port: Jaeger agent port (UDP)
            enabled: Whether tracing is enabled
        """
        self.service_name = service_name
        self.service_version = service_version
        self.jaeger_host = jaeger_host
        self.jaeger_port = jaeger_port
        self.enabled = enabled
        self._tracer_provider: Optional[TracerProvider] = None

    def setup_tracing(self) -> Optional[TracerProvider]:
        """
        Configure OpenTelemetry tracing with Jaeger exporter.

        Returns:
            TracerProvider instance if enabled, None otherwise
        """
        if not self.enabled:
            return None

        # Create resource with service information
        resource = Resource(attributes={
            SERVICE_NAME: self.service_name,
            SERVICE_VERSION: self.service_version,
            "deployment.environment": os.getenv("ENVIRONMENT", "development"),
            "service.namespace": "ml-platform"
        })

        # Create tracer provider
        self._tracer_provider = TracerProvider(resource=resource)

        # Configure Jaeger exporter
        jaeger_exporter = JaegerExporter(
            agent_host_name=self.jaeger_host,
            agent_port=self.jaeger_port,
        )

        # Add batch span processor
        span_processor = BatchSpanProcessor(jaeger_exporter)
        self._tracer_provider.add_span_processor(span_processor)

        # Set global tracer provider
        trace.set_tracer_provider(self._tracer_provider)

        return self._tracer_provider

    def instrument_fastapi(self, app: FastAPI):
        """
        Instrument FastAPI application with automatic tracing.

        Args:
            app: FastAPI application instance
        """
        if not self.enabled:
            return

        FastAPIInstrumentor.instrument_app(
            app,
            tracer_provider=self._tracer_provider,
            excluded_urls="health,metrics"  # Don't trace health/metrics endpoints
        )

    def instrument_sqlalchemy(self, engine):
        """
        Instrument SQLAlchemy for database query tracing.

        Args:
            engine: SQLAlchemy engine instance
        """
        if not self.enabled:
            return

        SQLAlchemyInstrumentor().instrument(
            engine=engine,
            tracer_provider=self._tracer_provider,
        )

    def instrument_httpx(self):
        """Instrument HTTPX for HTTP client tracing."""
        if not self.enabled:
            return

        HTTPXClientInstrumentor().instrument(
            tracer_provider=self._tracer_provider
        )

    def instrument_redis(self):
        """Instrument Redis for cache tracing."""
        if not self.enabled:
            return

        RedisInstrumentor().instrument(
            tracer_provider=self._tracer_provider
        )

    def get_tracer(self, name: str = __name__) -> trace.Tracer:
        """
        Get a tracer instance for manual instrumentation.

        Args:
            name: Name for the tracer

        Returns:
            Tracer instance
        """
        return trace.get_tracer(name)


def configure_tracing(
    app: FastAPI,
    service_name: str = "maestro-ml-api",
    jaeger_host: Optional[str] = None
) -> TracingManager:
    """
    Configure distributed tracing for the application.

    Args:
        app: FastAPI application
        service_name: Service name for traces
        jaeger_host: Jaeger agent host (defaults to env or cluster DNS)

    Returns:
        TracingManager instance
    """
    # Get configuration from environment
    enabled = os.getenv("TRACING_ENABLED", "true").lower() == "true"
    jaeger_host = jaeger_host or os.getenv(
        "JAEGER_AGENT_HOST",
        "jaeger.observability.svc.cluster.local"
    )
    jaeger_port = int(os.getenv("JAEGER_AGENT_PORT", "6831"))

    # Create tracing manager
    tracing_manager = TracingManager(
        service_name=service_name,
        jaeger_host=jaeger_host,
        jaeger_port=jaeger_port,
        enabled=enabled
    )

    # Setup tracing
    tracing_manager.setup_tracing()

    # Instrument FastAPI
    tracing_manager.instrument_fastapi(app)

    # Instrument HTTP clients
    tracing_manager.instrument_httpx()

    # Instrument Redis (if available)
    try:
        tracing_manager.instrument_redis()
    except Exception:
        pass  # Redis not available

    return tracing_manager


# Context manager for custom spans
class trace_span:
    """Context manager for creating custom trace spans."""

    def __init__(self, name: str, attributes: Optional[dict] = None):
        """
        Initialize span context manager.

        Args:
            name: Span name
            attributes: Optional span attributes
        """
        self.name = name
        self.attributes = attributes or {}
        self.span = None

    def __enter__(self):
        tracer = trace.get_tracer(__name__)
        self.span = tracer.start_span(self.name)

        # Set attributes
        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)

        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Record exception in span
            self.span.record_exception(exc_val)
            self.span.set_status(
                trace.Status(trace.StatusCode.ERROR, str(exc_val))
            )

        self.span.end()
        return False


# Decorator for tracing functions
def traced(span_name: Optional[str] = None, attributes: Optional[dict] = None):
    """
    Decorator to trace function execution.

    Args:
        span_name: Custom span name (defaults to function name)
        attributes: Additional span attributes

    Example:
        @traced("process_model")
        async def process_model(model_id: str):
            ...
    """
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            name = span_name or func.__name__
            attrs = attributes or {}

            with trace_span(name, attrs):
                return await func(*args, **kwargs)

        def sync_wrapper(*args, **kwargs):
            name = span_name or func.__name__
            attrs = attributes or {}

            with trace_span(name, attrs):
                return func(*args, **kwargs)

        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
