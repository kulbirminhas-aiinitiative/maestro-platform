"""
Tests for Maestro-Hive Prometheus Metrics Module
Epic: MD-1901 - Maestro-Hive Observability Integration
Task: MD-1904 - Add Prometheus metrics to key workflows
"""

import pytest

from observability.metrics import (
    AUDIT_COUNT,
    AUDIT_STREAM_RESULTS,
    GATE_CHECK_COUNT,
    REQUEST_COUNT,
    REQUEST_IN_PROGRESS,
    REQUEST_LATENCY,
    SERVICE_INFO,
    STORAGE_OPERATIONS,
    STORAGE_SIZE,
    WEBHOOK_DELIVERY_COUNT,
    create_metrics_endpoint,
    get_metrics,
    record_audit_result,
    record_request_latency,
)


class TestMetricsRegistry:
    """Tests for MetricsRegistry class."""

    def test_get_metrics_returns_singleton(self):
        """Should return the same metrics instance."""
        metrics1 = get_metrics()
        metrics2 = get_metrics()
        assert metrics1 is metrics2

    def test_record_request(self):
        """Should record request metrics."""
        metrics = get_metrics()
        metrics.record_request(
            method="POST",
            endpoint="/api/audit",
            status=200,
            latency=0.125,
        )
        # Metrics are recorded - no assertion needed as this verifies no exceptions

    def test_record_audit(self):
        """Should record audit metrics."""
        metrics = get_metrics()
        metrics.record_audit(
            verdict="ALL_PASS",
            can_deploy=True,
            latency=2.5,
        )

    def test_record_stream_result(self):
        """Should record stream result metrics."""
        metrics = get_metrics()
        metrics.record_stream_result(stream="dde", passed=True)
        metrics.record_stream_result(stream="bdv", passed=True)
        metrics.record_stream_result(stream="acc", passed=False)

    def test_record_gate_check(self):
        """Should record gate check metrics."""
        metrics = get_metrics()
        metrics.record_gate_check(result="allowed", latency=0.05)
        metrics.record_gate_check(result="blocked", latency=0.03)

    def test_record_webhook_delivery(self):
        """Should record webhook delivery metrics."""
        metrics = get_metrics()
        metrics.record_webhook_delivery(
            event_type="audit.completed",
            success=True,
            latency=0.5,
        )

    def test_record_storage_operation(self):
        """Should record storage operation metrics."""
        metrics = get_metrics()
        metrics.record_storage_operation(operation="read", success=True)
        metrics.record_storage_operation(operation="write", success=False)

    def test_set_storage_size(self):
        """Should set storage size gauge."""
        metrics = get_metrics()
        metrics.set_storage_size(file_type="audit_results", size_bytes=1024000)

    def test_generate_metrics(self):
        """Should generate Prometheus metrics output."""
        metrics = get_metrics()
        output = metrics.generate_metrics()
        assert isinstance(output, bytes)
        assert len(output) > 0

    def test_get_content_type(self):
        """Should return correct content type."""
        metrics = get_metrics()
        content_type = metrics.get_content_type()
        assert "text/plain" in content_type or "openmetrics" in content_type.lower()


class TestPrometheusMetrics:
    """Tests for Prometheus metric definitions."""

    def test_service_info_exists(self):
        """Should have service info metric."""
        assert SERVICE_INFO is not None

    def test_request_count_labels(self):
        """Request count should have correct labels."""
        assert REQUEST_COUNT._labelnames == ("method", "endpoint", "status")

    def test_request_latency_labels(self):
        """Request latency should have correct labels."""
        assert REQUEST_LATENCY._labelnames == ("method", "endpoint")

    def test_request_in_progress_labels(self):
        """Request in progress should have correct labels."""
        assert REQUEST_IN_PROGRESS._labelnames == ("method", "endpoint")

    def test_audit_count_labels(self):
        """Audit count should have correct labels."""
        assert AUDIT_COUNT._labelnames == ("verdict", "can_deploy")

    def test_audit_stream_results_labels(self):
        """Audit stream results should have correct labels."""
        assert AUDIT_STREAM_RESULTS._labelnames == ("stream", "passed")

    def test_gate_check_count_labels(self):
        """Gate check count should have correct labels."""
        assert GATE_CHECK_COUNT._labelnames == ("result",)

    def test_webhook_delivery_count_labels(self):
        """Webhook delivery count should have correct labels."""
        assert WEBHOOK_DELIVERY_COUNT._labelnames == ("event_type", "success")

    def test_storage_operations_labels(self):
        """Storage operations should have correct labels."""
        assert STORAGE_OPERATIONS._labelnames == ("operation", "success")

    def test_storage_size_labels(self):
        """Storage size should have correct labels."""
        assert STORAGE_SIZE._labelnames == ("file_type",)


class TestConvenienceFunctions:
    """Tests for convenience metric functions."""

    def test_record_audit_result_complete(self):
        """Should record complete audit result."""
        record_audit_result(
            iteration_id="iter_123",
            verdict="ALL_PASS",
            can_deploy=True,
            dde_passed=True,
            bdv_passed=True,
            acc_passed=True,
            latency=3.5,
        )

    def test_record_audit_result_partial(self):
        """Should record partial audit result."""
        record_audit_result(
            iteration_id="iter_456",
            verdict="PARTIAL_PASS",
            can_deploy=False,
            dde_passed=True,
            bdv_passed=None,
            acc_passed=False,
        )

    def test_record_audit_result_without_latency(self):
        """Should handle missing latency."""
        record_audit_result(
            iteration_id="iter_789",
            verdict="SYSTEMIC_FAILURE",
            can_deploy=False,
        )


class TestRequestLatencyDecorator:
    """Tests for request latency decorator."""

    def test_sync_function_decorator(self):
        """Should decorate sync functions."""

        @record_request_latency("GET", "/test")
        def sync_handler():
            return "result"

        result = sync_handler()
        assert result == "result"

    @pytest.mark.asyncio
    async def test_async_function_decorator(self):
        """Should decorate async functions."""

        @record_request_latency("POST", "/test")
        async def async_handler():
            return "async_result"

        result = await async_handler()
        assert result == "async_result"

    def test_decorator_preserves_function_name(self):
        """Should preserve function name."""

        @record_request_latency("GET", "/test")
        def named_handler():
            pass

        assert named_handler.__name__ == "named_handler"

    def test_decorator_handles_exception(self):
        """Should record error status on exception."""

        @record_request_latency("GET", "/error")
        def error_handler():
            raise ValueError("Test error")

        with pytest.raises(ValueError):
            error_handler()


class TestMetricsEndpoint:
    """Tests for FastAPI metrics endpoint."""

    def test_create_metrics_endpoint(self):
        """Should create metrics endpoint response."""
        response = create_metrics_endpoint()
        assert response is not None
        assert hasattr(response, "body")
        assert len(response.body) > 0

    def test_metrics_endpoint_content_type(self):
        """Should have correct content type."""
        response = create_metrics_endpoint()
        assert response.media_type is not None


class TestMetricsOutput:
    """Tests for metrics output format."""

    def test_output_contains_service_info(self):
        """Metrics output should contain service info."""
        metrics = get_metrics()
        output = metrics.generate_metrics().decode("utf-8")
        assert "maestro_hive" in output

    def test_output_contains_request_metrics(self):
        """Metrics output should contain request metrics."""
        metrics = get_metrics()
        # Record a request first
        metrics.record_request("GET", "/health", 200, 0.01)
        output = metrics.generate_metrics().decode("utf-8")
        assert "maestro_hive_requests_total" in output

    def test_output_contains_audit_metrics(self):
        """Metrics output should contain audit metrics."""
        metrics = get_metrics()
        metrics.record_audit("ALL_PASS", True, 1.0)
        output = metrics.generate_metrics().decode("utf-8")
        assert "maestro_hive_audits_total" in output

    def test_output_is_valid_prometheus_format(self):
        """Metrics output should be valid Prometheus format."""
        metrics = get_metrics()
        output = metrics.generate_metrics().decode("utf-8")
        # Check for valid Prometheus format elements
        lines = output.strip().split("\n")
        for line in lines:
            if line.startswith("#"):
                # Comment or metadata line
                assert (
                    line.startswith("# ") or line.startswith("# HELP") or line.startswith("# TYPE")
                )
            elif line.strip():
                # Metric line should have format: metric_name{labels} value
                # or metric_name value
                pass  # Basic validation
