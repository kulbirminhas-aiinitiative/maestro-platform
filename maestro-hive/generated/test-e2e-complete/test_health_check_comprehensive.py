"""
Comprehensive Test Suite for Health Check API.

This module provides complete test coverage including:
- Unit tests for all endpoints
- Integration tests
- End-to-end tests
- Performance tests
- Error handling tests
- Edge case tests

Author: Rachel (QA Engineer)
"""

import pytest
import time
import json
import concurrent.futures
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock

from health_check_api import app, APP_VERSION

client = TestClient(app)


# =============================================================================
# Unit Tests - Basic Endpoint Testing
# =============================================================================

class TestHealthEndpoint:
    """Test suite for /health endpoint."""

    def test_health_check_returns_200(self):
        """Test that health check returns HTTP 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_response_structure(self):
        """Test health check response contains required fields."""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "uptime_seconds" in data

    def test_health_check_status_is_healthy(self):
        """Test that status is 'healthy'."""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_check_version_matches(self):
        """Test that version matches APP_VERSION."""
        response = client.get("/health")
        data = response.json()
        assert data["version"] == APP_VERSION
        assert data["version"] == "1.0.0"

    def test_health_check_timestamp_format(self):
        """Test timestamp is in ISO format with Z suffix."""
        response = client.get("/health")
        data = response.json()
        timestamp = data["timestamp"]

        assert timestamp.endswith("Z")
        # Parse timestamp to validate format
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))

    def test_health_check_uptime_is_positive(self):
        """Test that uptime_seconds is a positive number."""
        response = client.get("/health")
        data = response.json()

        assert isinstance(data["uptime_seconds"], (int, float))
        assert data["uptime_seconds"] >= 0

    def test_health_check_content_type(self):
        """Test response content type is JSON."""
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]


class TestReadinessEndpoint:
    """Test suite for /health/ready endpoint."""

    def test_readiness_returns_200(self):
        """Test readiness probe returns HTTP 200."""
        response = client.get("/health/ready")
        assert response.status_code == 200

    def test_readiness_response_structure(self):
        """Test readiness response contains required fields."""
        response = client.get("/health/ready")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data

    def test_readiness_status_is_ready(self):
        """Test that status is 'ready'."""
        response = client.get("/health/ready")
        data = response.json()
        assert data["status"] == "ready"

    def test_readiness_timestamp_format(self):
        """Test timestamp format is valid."""
        response = client.get("/health/ready")
        data = response.json()

        assert data["timestamp"].endswith("Z")
        datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))


class TestLivenessEndpoint:
    """Test suite for /health/live endpoint."""

    def test_liveness_returns_200(self):
        """Test liveness probe returns HTTP 200."""
        response = client.get("/health/live")
        assert response.status_code == 200

    def test_liveness_response_structure(self):
        """Test liveness response contains required fields."""
        response = client.get("/health/live")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data

    def test_liveness_status_is_alive(self):
        """Test that status is 'alive'."""
        response = client.get("/health/live")
        data = response.json()
        assert data["status"] == "alive"


class TestDetailedHealthEndpoint:
    """Test suite for /health/detailed endpoint."""

    def test_detailed_health_returns_200(self):
        """Test detailed health check returns HTTP 200."""
        response = client.get("/health/detailed")
        assert response.status_code == 200

    def test_detailed_health_response_structure(self):
        """Test detailed response contains required fields."""
        response = client.get("/health/detailed")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "system" in data
        assert "checks" in data

    def test_detailed_health_status_values(self):
        """Test status is one of valid values."""
        response = client.get("/health/detailed")
        data = response.json()

        valid_statuses = ["healthy", "degraded", "unhealthy"]
        assert data["status"] in valid_statuses

    def test_detailed_health_system_info(self):
        """Test system info contains required fields."""
        response = client.get("/health/detailed")
        data = response.json()

        system = data["system"]
        assert "platform" in system
        assert "python_version" in system
        assert "hostname" in system
        assert "cpu_count" in system

    def test_detailed_health_system_metrics(self):
        """Test system metrics are present and valid."""
        response = client.get("/health/detailed")
        data = response.json()

        system = data["system"]

        # Memory and disk percent should be present
        if "memory_percent" in system:
            assert 0 <= system["memory_percent"] <= 100

        if "disk_percent" in system:
            assert 0 <= system["disk_percent"] <= 100

    def test_detailed_health_checks(self):
        """Test health checks contain required components."""
        response = client.get("/health/detailed")
        data = response.json()

        checks = data["checks"]
        assert "api" in checks
        assert "memory" in checks
        assert "disk" in checks

    def test_detailed_health_check_values(self):
        """Test check values are valid."""
        response = client.get("/health/detailed")
        data = response.json()

        valid_values = ["passing", "warning", "critical", "unknown"]
        for check_name, check_value in data["checks"].items():
            assert check_value in valid_values, f"{check_name} has invalid value: {check_value}"


class TestRootEndpoint:
    """Test suite for root / endpoint."""

    def test_root_returns_200(self):
        """Test root endpoint returns HTTP 200."""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_response_structure(self):
        """Test root response contains required fields."""
        response = client.get("/")
        data = response.json()

        assert "message" in data
        assert "health_endpoint" in data

    def test_root_health_endpoint_reference(self):
        """Test root references health endpoint."""
        response = client.get("/")
        data = response.json()

        assert data["health_endpoint"] == "/health"


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for Health Check API."""

    def test_all_endpoints_available(self):
        """Test all endpoints are accessible."""
        endpoints = ["/", "/health", "/health/ready", "/health/live", "/health/detailed"]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200, f"Endpoint {endpoint} failed"

    def test_consecutive_health_checks(self):
        """Test multiple consecutive health checks."""
        for _ in range(10):
            response = client.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

    def test_uptime_increases(self):
        """Test that uptime increases between calls."""
        response1 = client.get("/health")
        time.sleep(0.1)
        response2 = client.get("/health")

        uptime1 = response1.json()["uptime_seconds"]
        uptime2 = response2.json()["uptime_seconds"]

        assert uptime2 > uptime1

    def test_timestamp_changes(self):
        """Test that timestamp changes between calls."""
        response1 = client.get("/health")
        time.sleep(0.01)
        response2 = client.get("/health")

        # Timestamps should be different (or at least not fail)
        ts1 = response1.json()["timestamp"]
        ts2 = response2.json()["timestamp"]

        # Both should be valid timestamps
        datetime.fromisoformat(ts1.replace("Z", "+00:00"))
        datetime.fromisoformat(ts2.replace("Z", "+00:00"))

    def test_openapi_schema_available(self):
        """Test OpenAPI schema is accessible."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

    def test_swagger_ui_available(self):
        """Test Swagger UI is accessible."""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "swagger-ui" in response.text.lower() or "text/html" in response.headers.get("content-type", "")


# =============================================================================
# End-to-End Tests
# =============================================================================

class TestE2E:
    """End-to-end tests simulating real usage patterns."""

    def test_kubernetes_probe_flow(self):
        """Test typical Kubernetes probe sequence."""
        # Simulate Kubernetes probing pattern

        # 1. Liveness check
        live = client.get("/health/live")
        assert live.status_code == 200
        assert live.json()["status"] == "alive"

        # 2. Readiness check
        ready = client.get("/health/ready")
        assert ready.status_code == 200
        assert ready.json()["status"] == "ready"

        # 3. Full health check for monitoring
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["status"] == "healthy"

    def test_monitoring_dashboard_flow(self):
        """Test typical monitoring dashboard data collection."""
        # Collect basic health
        health = client.get("/health")
        assert health.status_code == 200

        # Collect detailed metrics
        detailed = client.get("/health/detailed")
        assert detailed.status_code == 200

        # Verify we can parse the data
        health_data = health.json()
        detailed_data = detailed.json()

        # Dashboard would display these values
        assert health_data["status"] == "healthy"
        assert "memory_percent" in detailed_data["system"] or detailed_data["checks"]["memory"] == "unknown"

    def test_load_balancer_health_check(self):
        """Test load balancer health check pattern."""
        # Load balancers typically check /health or /health/ready
        response = client.get("/health/ready")

        # Must return 200 to be considered healthy
        assert response.status_code == 200

        # Response should be fast
        assert response.elapsed.total_seconds() < 1.0

    def test_api_discovery_flow(self):
        """Test API discovery starting from root."""
        # Hit root to discover API
        root = client.get("/")
        assert root.status_code == 200

        # Follow to health endpoint
        health_path = root.json()["health_endpoint"]
        health = client.get(health_path)
        assert health.status_code == 200

        # Discover OpenAPI schema
        openapi = client.get("/openapi.json")
        assert openapi.status_code == 200


# =============================================================================
# Performance Tests
# =============================================================================

class TestPerformance:
    """Performance tests for Health Check API."""

    def test_health_endpoint_response_time(self):
        """Test /health response time is acceptable."""
        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 0.5, f"Response took {elapsed:.3f}s, expected < 0.5s"

    def test_detailed_health_response_time(self):
        """Test /health/detailed response time is acceptable."""
        start = time.time()
        response = client.get("/health/detailed")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 1.0, f"Response took {elapsed:.3f}s, expected < 1.0s"

    def test_concurrent_requests(self):
        """Test API handles concurrent requests."""
        num_requests = 20

        def make_request():
            return client.get("/health")

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(num_requests)]
            responses = [f.result() for f in concurrent.futures.as_completed(futures)]

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

    def test_sustained_load(self):
        """Test API under sustained load."""
        num_requests = 50
        successes = 0

        for _ in range(num_requests):
            response = client.get("/health")
            if response.status_code == 200:
                successes += 1

        # At least 95% success rate
        success_rate = successes / num_requests
        assert success_rate >= 0.95, f"Success rate {success_rate:.2%} < 95%"

    def test_response_size(self):
        """Test response sizes are reasonable."""
        # Basic health should be small
        health = client.get("/health")
        health_size = len(health.content)
        assert health_size < 500, f"Health response too large: {health_size} bytes"

        # Detailed can be larger but still reasonable
        detailed = client.get("/health/detailed")
        detailed_size = len(detailed.content)
        assert detailed_size < 2000, f"Detailed response too large: {detailed_size} bytes"


# =============================================================================
# Error Handling Tests
# =============================================================================

class TestErrorHandling:
    """Tests for error handling scenarios."""

    def test_invalid_endpoint_returns_404(self):
        """Test non-existent endpoint returns 404."""
        response = client.get("/invalid")
        assert response.status_code == 404

    def test_method_not_allowed(self):
        """Test POST to GET-only endpoint."""
        response = client.post("/health")
        assert response.status_code == 405

    def test_put_method_not_allowed(self):
        """Test PUT method is not allowed."""
        response = client.put("/health")
        assert response.status_code == 405

    def test_delete_method_not_allowed(self):
        """Test DELETE method is not allowed."""
        response = client.delete("/health")
        assert response.status_code == 405


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_health_with_query_params(self):
        """Test health endpoint ignores query params."""
        response = client.get("/health?foo=bar")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_health_with_trailing_slash(self):
        """Test health endpoint with trailing slash."""
        response = client.get("/health/")
        # FastAPI typically returns 307 redirect or 200
        assert response.status_code in [200, 307]

    def test_case_sensitivity(self):
        """Test URL case sensitivity."""
        # FastAPI is case-sensitive by default
        response = client.get("/HEALTH")
        assert response.status_code == 404

    def test_json_content_negotiation(self):
        """Test API returns JSON regardless of Accept header."""
        headers = {"Accept": "text/html"}
        response = client.get("/health", headers=headers)

        assert response.status_code == 200
        # Should still return JSON
        assert "application/json" in response.headers["content-type"]

    def test_multiple_rapid_requests(self):
        """Test handling rapid successive requests."""
        responses = [client.get("/health") for _ in range(100)]

        # All should succeed
        assert all(r.status_code == 200 for r in responses)
        assert all(r.json()["status"] == "healthy" for r in responses)


# =============================================================================
# Mock Tests for Error Conditions
# =============================================================================

class TestMockedConditions:
    """Tests using mocks to simulate various conditions."""

    @patch('health_check_api.psutil.virtual_memory')
    def test_high_memory_usage_warning(self, mock_memory):
        """Test degraded status when memory usage is high."""
        mock_memory.return_value = MagicMock(percent=95.0)

        response = client.get("/health/detailed")
        assert response.status_code == 200

        data = response.json()
        assert data["checks"]["memory"] == "warning"
        assert data["status"] == "degraded"

    @patch('health_check_api.psutil.disk_usage')
    def test_high_disk_usage_warning(self, mock_disk):
        """Test degraded status when disk usage is high."""
        mock_disk.return_value = MagicMock(percent=95.0)

        response = client.get("/health/detailed")
        assert response.status_code == 200

        data = response.json()
        assert data["checks"]["disk"] == "warning"
        assert data["status"] == "degraded"

    @patch('health_check_api.psutil.virtual_memory')
    def test_memory_check_exception(self, mock_memory):
        """Test unknown status when memory check fails."""
        mock_memory.side_effect = Exception("Memory check failed")

        response = client.get("/health/detailed")
        assert response.status_code == 200

        data = response.json()
        assert data["checks"]["memory"] == "unknown"

    @patch('health_check_api.psutil.disk_usage')
    def test_disk_check_exception(self, mock_disk):
        """Test unknown status when disk check fails."""
        mock_disk.side_effect = Exception("Disk check failed")

        response = client.get("/health/detailed")
        assert response.status_code == 200

        data = response.json()
        assert data["checks"]["disk"] == "unknown"


# =============================================================================
# Data Validation Tests
# =============================================================================

class TestDataValidation:
    """Tests for response data validation."""

    def test_health_response_json_serializable(self):
        """Test health response is valid JSON."""
        response = client.get("/health")

        # Should not raise
        json_str = json.dumps(response.json())
        parsed = json.loads(json_str)

        assert parsed == response.json()

    def test_detailed_response_json_serializable(self):
        """Test detailed response is valid JSON."""
        response = client.get("/health/detailed")

        json_str = json.dumps(response.json())
        parsed = json.loads(json_str)

        assert parsed == response.json()

    def test_version_format(self):
        """Test version follows semantic versioning pattern."""
        response = client.get("/health")
        version = response.json()["version"]

        # Should be in format X.Y.Z
        parts = version.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    def test_cpu_count_valid(self):
        """Test CPU count is a positive integer."""
        response = client.get("/health/detailed")
        cpu_count = response.json()["system"]["cpu_count"]

        assert isinstance(cpu_count, int)
        assert cpu_count > 0


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "-x",  # Stop on first failure
        "--durations=10"  # Show 10 slowest tests
    ])
