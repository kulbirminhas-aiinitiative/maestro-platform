"""
Tests for Maestro-Hive OpenTelemetry Tracing Module
Epic: MD-1901 - Maestro-Hive Observability Integration
Task: MD-1905 - Integrate OpenTelemetry tracing
"""

import os
from unittest.mock import patch

import pytest

from observability.tracing import (
    TracedOperation,
    TracingConfig,
    add_span_attributes,
    add_span_event,
    configure_tracing,
    get_current_span,
    get_trace_context,
    get_tracer,
    record_exception,
    trace_audit_execution,
    trace_function,
    trace_gate_check,
    trace_stream_execution,
    trace_webhook_delivery,
)


class TestTracingConfig:
    """Tests for TracingConfig dataclass."""

    def test_default_config(self):
        """Should create config with default values."""
        config = TracingConfig()
        assert config.service_name == "maestro-hive"
        assert config.sample_rate == 1.0
        assert config.enabled is True

    def test_custom_config(self):
        """Should create config with custom values."""
        config = TracingConfig(
            service_name="custom-service",
            environment="staging",
            otlp_endpoint="http://jaeger:4317",
            sample_rate=0.5,
        )
        assert config.service_name == "custom-service"
        assert config.environment == "staging"
        assert config.otlp_endpoint == "http://jaeger:4317"
        assert config.sample_rate == 0.5

    @patch.dict(os.environ, {"HIVE_ENV": "production"})
    def test_environment_from_env(self):
        """Should read environment from HIVE_ENV."""
        config = TracingConfig()
        assert config.environment == "production"

    @patch.dict(os.environ, {"OTEL_EXPORTER_OTLP_ENDPOINT": "http://collector:4317"})
    def test_otlp_endpoint_from_env(self):
        """Should read OTLP endpoint from environment."""
        config = TracingConfig()
        assert config.otlp_endpoint == "http://collector:4317"

    @patch.dict(os.environ, {"OTEL_TRACING_ENABLED": "false"})
    def test_disabled_from_env(self):
        """Should read enabled state from environment."""
        config = TracingConfig()
        assert config.enabled is False


class TestTracingConfiguration:
    """Tests for tracing configuration."""

    def test_configure_tracing_default(self):
        """Should configure tracing with defaults."""
        configure_tracing()
        tracer = get_tracer("test")
        assert tracer is not None

    def test_configure_tracing_custom(self):
        """Should configure tracing with custom config."""
        config = TracingConfig(
            service_name="test-service",
            enable_console_export=False,
        )
        configure_tracing(config)
        tracer = get_tracer("test")
        assert tracer is not None

    def test_configure_tracing_disabled(self):
        """Should handle disabled tracing."""
        config = TracingConfig(enabled=False)
        configure_tracing(config)
        # Should not raise any exceptions


class TestTracerRetrieval:
    """Tests for tracer retrieval."""

    def test_get_tracer(self):
        """Should get tracer instance."""
        tracer = get_tracer("test_module")
        assert tracer is not None

    def test_get_tracer_default_name(self):
        """Should use default name."""
        tracer = get_tracer()
        assert tracer is not None

    def test_get_current_span(self):
        """Should get current span."""
        span = get_current_span()
        assert span is not None


class TestTraceContext:
    """Tests for trace context propagation."""

    def test_get_trace_context_outside_span(self):
        """Should return empty context outside span."""
        context = get_trace_context()
        # May be empty or have values depending on if there's an active span
        assert isinstance(context, dict)


class TestTraceFunctionDecorator:
    """Tests for trace_function decorator."""

    def test_sync_function_decorator(self):
        """Should decorate sync functions."""

        @trace_function(name="test_operation")
        def sync_handler():
            return "result"

        result = sync_handler()
        assert result == "result"

    @pytest.mark.asyncio
    async def test_async_function_decorator(self):
        """Should decorate async functions."""

        @trace_function(name="async_test_operation")
        async def async_handler():
            return "async_result"

        result = await async_handler()
        assert result == "async_result"

    def test_decorator_preserves_function_name(self):
        """Should preserve function name."""

        @trace_function()
        def named_handler():
            pass

        assert named_handler.__name__ == "named_handler"

    def test_decorator_with_attributes(self):
        """Should accept additional attributes."""

        @trace_function(name="attributed_op", attributes={"key": "value"})
        def handler_with_attrs():
            return "result"

        result = handler_with_attrs()
        assert result == "result"

    def test_decorator_handles_exception(self):
        """Should record exception on failure."""

        @trace_function(name="error_operation")
        def error_handler():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            error_handler()

    @pytest.mark.asyncio
    async def test_async_decorator_handles_exception(self):
        """Should record exception on async failure."""

        @trace_function(name="async_error_operation")
        async def async_error_handler():
            raise ValueError("Async test error")

        with pytest.raises(ValueError):
            await async_error_handler()


class TestTracedOperation:
    """Tests for TracedOperation context manager."""

    def test_traced_operation_basic(self):
        """Should create traced operation."""
        with TracedOperation("test_operation") as span:
            assert span is not None

    def test_traced_operation_with_attributes(self):
        """Should create traced operation with attributes."""
        with TracedOperation("test_op", iteration_id="abc123", task_id="MD-1234") as span:
            assert span is not None

    def test_traced_operation_on_exception(self):
        """Should handle exceptions in traced operation."""
        with pytest.raises(ValueError):
            with TracedOperation("error_op"):
                raise ValueError("Test error")


class TestSpanManagement:
    """Tests for span attribute and event management."""

    def test_add_span_attributes(self):
        """Should add attributes to current span."""
        # This should not raise even outside a span context
        add_span_attributes(key1="value1", key2="value2")

    def test_add_span_event(self):
        """Should add event to current span."""
        add_span_event("test_event", {"status": "completed"})

    def test_add_span_event_without_attributes(self):
        """Should add event without attributes."""
        add_span_event("simple_event")

    def test_record_exception(self):
        """Should record exception in span."""
        try:
            raise ValueError("Test exception")
        except ValueError as e:
            record_exception(e)

    def test_record_exception_with_attributes(self):
        """Should record exception with attributes."""
        try:
            raise RuntimeError("Runtime error")
        except RuntimeError as e:
            record_exception(e, {"context": "test"})


class TestTrimodalSpecificTracing:
    """Tests for trimodal-specific tracing helpers."""

    def test_trace_audit_execution(self):
        """Should create audit execution trace."""
        with trace_audit_execution("iter_123", "MD-1234") as span:
            assert span is not None

    def test_trace_audit_execution_without_task(self):
        """Should handle missing task ID."""
        with trace_audit_execution("iter_456") as span:
            assert span is not None

    def test_trace_stream_execution_dde(self):
        """Should create DDE stream trace."""
        with trace_stream_execution("dde", "iter_123") as span:
            assert span is not None

    def test_trace_stream_execution_bdv(self):
        """Should create BDV stream trace."""
        with trace_stream_execution("bdv", "iter_123") as span:
            assert span is not None

    def test_trace_stream_execution_acc(self):
        """Should create ACC stream trace."""
        with trace_stream_execution("acc", "iter_123") as span:
            assert span is not None

    def test_trace_webhook_delivery(self):
        """Should create webhook delivery trace."""
        with trace_webhook_delivery("wh_123", "https://example.com/hook") as span:
            assert span is not None

    def test_trace_gate_check(self):
        """Should create gate check trace."""
        with trace_gate_check("iter_123") as span:
            assert span is not None


class TestSpanKinds:
    """Tests for different span kinds."""

    def test_internal_span_kind(self):
        """Should create internal span."""
        from opentelemetry.trace import SpanKind

        with TracedOperation("internal_op", kind=SpanKind.INTERNAL) as span:
            assert span is not None

    def test_client_span_kind(self):
        """Should create client span."""
        from opentelemetry.trace import SpanKind

        with TracedOperation("client_op", kind=SpanKind.CLIENT) as span:
            assert span is not None

    def test_server_span_kind(self):
        """Should create server span."""
        from opentelemetry.trace import SpanKind

        with TracedOperation("server_op", kind=SpanKind.SERVER) as span:
            assert span is not None
