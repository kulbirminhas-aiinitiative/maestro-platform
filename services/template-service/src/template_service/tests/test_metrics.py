"""
Unit tests for metrics module
Tests the Prometheus metrics singleton pattern and metric recording functions
"""

import pytest
from prometheus_client import REGISTRY
from metrics import (
    get_metrics,
    record_request,
    observe_duration,
    set_active_services,
    increment_port_conflicts,
    increment_asset_violations,
    record_template_operation,
    record_template_search,
    record_template_download,
    observe_db_operation,
    record_cache_operation,
)


class TestMetricsInitialization:
    """Test metrics module initialization"""

    def test_get_metrics_returns_dict(self):
        """Test that get_metrics returns a dictionary"""
        metrics = get_metrics()
        assert isinstance(metrics, dict)

    def test_get_metrics_is_singleton(self):
        """Test that get_metrics returns the same instance"""
        metrics1 = get_metrics()
        metrics2 = get_metrics()
        assert metrics1 is metrics2

    def test_metrics_contains_expected_keys(self):
        """Test that metrics dict contains expected metric keys"""
        metrics = get_metrics()
        expected_keys = [
            'registry_requests',
            'registry_duration',
            'active_services',
            'port_conflicts',
            'asset_violations',
            'template_operations',
            'template_searches',
            'template_downloads',
            'db_operations',
            'cache_operations'
        ]

        for key in expected_keys:
            assert key in metrics, f"Expected key '{key}' not found in metrics"


class TestMetricsRecording:
    """Test metric recording functions"""

    def test_record_request(self):
        """Test recording HTTP requests"""
        # Should not raise exception
        record_request("GET", "/api/v1/templates", 200)
        record_request("POST", "/api/v1/templates", 201)
        record_request("GET", "/api/v1/templates/test", 404)
        record_request("DELETE", "/api/v1/templates/test", 500)

    def test_observe_duration(self):
        """Test observing request duration"""
        # Should not raise exception
        observe_duration("GET", "/health", 0.05)
        observe_duration("GET", "/api/v1/templates", 0.15)
        observe_duration("POST", "/api/v1/templates", 0.25)

    def test_set_active_services(self):
        """Test setting active services gauge"""
        # Should not raise exception
        set_active_services(0)
        set_active_services(5)
        set_active_services(10)

    def test_increment_port_conflicts(self):
        """Test incrementing port conflicts counter"""
        # Should not raise exception
        increment_port_conflicts()
        increment_port_conflicts()

    def test_increment_asset_violations(self):
        """Test incrementing asset violations counter"""
        # Should not raise exception
        increment_asset_violations()
        increment_asset_violations()

    def test_record_template_operation(self):
        """Test recording template operations"""
        # Should not raise exception
        record_template_operation("search", "success")
        record_template_operation("download", "success")
        record_template_operation("upload", "failed")

    def test_record_template_search(self):
        """Test recording template searches"""
        # Should not raise exception
        record_template_search()
        record_template_search("iot", "python")
        record_template_search("backend", "javascript")

    def test_record_template_download(self):
        """Test recording template downloads"""
        # Should not raise exception
        record_template_download("jwt-auth-v1", "security_specialist")
        record_template_download("graphql-api-v1", "backend_developer")

    def test_observe_db_operation(self):
        """Test observing database operation duration"""
        # Should not raise exception
        observe_db_operation("SELECT", 0.05)
        observe_db_operation("INSERT", 0.10)
        observe_db_operation("UPDATE", 0.08)

    def test_record_cache_operation(self):
        """Test recording cache operations"""
        # Should not raise exception
        record_cache_operation("get", "hit")
        record_cache_operation("get", "miss")
        record_cache_operation("set", "success")


class TestMetricsValidation:
    """Test metrics validation and error handling"""

    def test_record_request_with_various_status_codes(self):
        """Test recording requests with different status codes"""
        for status in [200, 201, 204, 301, 302, 400, 401, 403, 404, 500, 502, 503]:
            record_request("GET", "/test", status)

    def test_observe_duration_with_various_durations(self):
        """Test observing various duration values"""
        durations = [0.001, 0.01, 0.1, 0.5, 1.0, 5.0, 10.0]
        for duration in durations:
            observe_duration("GET", "/test", duration)

    def test_set_active_services_with_edge_values(self):
        """Test setting active services with edge values"""
        set_active_services(0)
        set_active_services(1)
        set_active_services(100)
        set_active_services(1000)

    def test_template_operations_with_various_statuses(self):
        """Test template operations with different statuses"""
        operations = ["search", "download", "upload", "delete", "update"]
        statuses = ["success", "failed", "pending"]

        for operation in operations:
            for status in statuses:
                record_template_operation(operation, status)


class TestMetricsIntegration:
    """Test metrics integration scenarios"""

    def test_typical_api_request_flow(self):
        """Test typical API request metric recording flow"""
        import time

        # Simulate API request
        start_time = time.time()

        # Request arrives
        method = "GET"
        endpoint = "/api/v1/templates"

        # Process request (simulated)
        time.sleep(0.01)

        # Record metrics
        duration = time.time() - start_time
        status_code = 200

        record_request(method, endpoint, status_code)
        observe_duration(method, endpoint, duration)

        # Success - no exceptions raised

    def test_template_search_flow(self):
        """Test template search metric recording flow"""
        import time

        start_time = time.time()

        # User searches for templates
        category = "backend"
        language = "python"
        record_template_search(category, language)

        # Operation completes
        duration = time.time() - start_time
        observe_duration("GET", "/api/v1/templates/search", duration)
        record_template_operation("search", "success")

    def test_database_query_flow(self):
        """Test database query metric recording flow"""
        import time

        start_time = time.time()

        # Simulate database query
        time.sleep(0.005)

        # Record duration
        duration = time.time() - start_time
        observe_db_operation("SELECT", duration)

    def test_cache_hit_and_miss_flow(self):
        """Test cache operation metric recording flow"""
        # Cache miss
        record_cache_operation("get", "miss")

        # Load from database
        observe_db_operation("SELECT", 0.05)

        # Cache set
        record_cache_operation("set", "success")

        # Cache hit
        record_cache_operation("get", "hit")


class TestMetricsPrometheusRegistry:
    """Test Prometheus registry integration"""

    def test_metrics_are_registered_in_prometheus(self):
        """Test that metrics are registered in Prometheus registry"""
        metrics = get_metrics()

        # Check that metrics are registered
        collector_names = [collector._name for collector in REGISTRY._collector_to_names.keys()
                          if hasattr(collector, '_name')]

        # At least some metrics should be registered
        assert len(collector_names) > 0

    def test_metrics_can_be_generated(self):
        """Test that metrics can be generated for export"""
        from prometheus_client import generate_latest

        # Generate metrics
        output = generate_latest(REGISTRY)

        # Should produce some output
        assert output is not None
        assert len(output) > 0

    def test_multiple_metric_recordings(self):
        """Test recording multiple metrics in sequence"""
        # Record various metrics
        for i in range(10):
            record_request("GET", "/test", 200)
            observe_duration("GET", "/test", 0.1)
            record_template_operation("search", "success")
            record_cache_operation("get", "hit")

        # All should succeed without error


# Benchmark tests
class TestMetricsPerformance:
    """Test metrics performance characteristics"""

    def test_metric_recording_is_fast(self):
        """Test that metric recording is fast enough"""
        import time

        start = time.time()

        # Record 1000 metrics
        for i in range(1000):
            record_request("GET", "/test", 200)

        duration = time.time() - start

        # Should complete in less than 1 second
        assert duration < 1.0, f"Metric recording too slow: {duration}s for 1000 recordings"

    def test_get_metrics_is_cached(self):
        """Test that get_metrics is properly cached"""
        import time

        # First call (initialization)
        start1 = time.time()
        get_metrics()
        duration1 = time.time() - start1

        # Subsequent calls (cached)
        start2 = time.time()
        for _ in range(100):
            get_metrics()
        duration2 = time.time() - start2

        # Cached calls should be much faster
        assert duration2 < duration1, "get_metrics not properly cached"
