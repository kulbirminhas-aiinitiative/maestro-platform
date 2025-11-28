"""
Unit Tests for Health Check API

Tests all endpoints and error handling for the health check API.
"""

import json
import unittest
from unittest.mock import patch, MagicMock
from io import BytesIO

from health_check_api import (
    HealthCheckHandler,
    HealthStatus,
    create_server
)


class MockRequest:
    """Mock HTTP request for testing."""
    def __init__(self, path: str):
        self.path = path


class TestHealthCheckHandler(unittest.TestCase):
    """Test cases for HealthCheckHandler."""

    def setUp(self):
        """Set up test fixtures."""
        self.handler = self._create_handler("/health")

    def _create_handler(self, path: str):
        """Create a handler with mocked request/response."""
        handler = HealthCheckHandler.__new__(HealthCheckHandler)
        handler.path = path
        handler.requestline = f"GET {path} HTTP/1.1"
        handler.client_address = ("127.0.0.1", 8000)
        handler.request_version = "HTTP/1.1"
        handler.wfile = BytesIO()
        handler.headers = {}
        handler._headers_buffer = []
        return handler

    def _mock_send_methods(self, handler):
        """Mock HTTP response methods."""
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

    def test_health_status_constants(self):
        """Test health status constants are defined correctly."""
        self.assertEqual(HealthStatus.HEALTHY, "healthy")
        self.assertEqual(HealthStatus.DEGRADED, "degraded")
        self.assertEqual(HealthStatus.UNHEALTHY, "unhealthy")

    def test_health_check_endpoint(self):
        """Test main /health endpoint returns comprehensive data."""
        handler = self._create_handler("/health")
        self._mock_send_methods(handler)

        handler.do_GET()

        handler.send_response.assert_called_with(200)
        response = handler.wfile.getvalue().decode('utf-8')
        data = json.loads(response)

        self.assertEqual(data["status"], HealthStatus.HEALTHY)
        self.assertIn("timestamp", data)
        self.assertIn("service", data)
        self.assertIn("system", data)
        self.assertIn("checks", data)
        self.assertEqual(data["service"]["name"], "health-check-api")
        self.assertEqual(data["service"]["version"], "1.0.0")

    def test_liveness_endpoint(self):
        """Test /health/live endpoint returns minimal response."""
        handler = self._create_handler("/health/live")
        self._mock_send_methods(handler)

        handler.do_GET()

        handler.send_response.assert_called_with(200)
        response = handler.wfile.getvalue().decode('utf-8')
        data = json.loads(response)

        self.assertEqual(data["status"], HealthStatus.HEALTHY)
        self.assertIn("timestamp", data)
        self.assertNotIn("service", data)

    def test_readiness_endpoint(self):
        """Test /health/ready endpoint returns readiness status."""
        handler = self._create_handler("/health/ready")
        self._mock_send_methods(handler)

        handler.do_GET()

        handler.send_response.assert_called_with(200)
        response = handler.wfile.getvalue().decode('utf-8')
        data = json.loads(response)

        self.assertEqual(data["status"], HealthStatus.HEALTHY)
        self.assertTrue(data["ready"])
        self.assertIn("timestamp", data)

    def test_not_found_endpoint(self):
        """Test unknown endpoints return 404."""
        handler = self._create_handler("/unknown")
        self._mock_send_methods(handler)

        handler.do_GET()

        handler.send_response.assert_called_with(404)
        response = handler.wfile.getvalue().decode('utf-8')
        data = json.loads(response)

        self.assertEqual(data["error"], "Not Found")
        self.assertIn("available_endpoints", data)

    def test_memory_check(self):
        """Test memory check returns valid data."""
        handler = self._create_handler("/health")
        result = handler._check_memory()

        self.assertIn("status", result)
        self.assertEqual(result["status"], HealthStatus.HEALTHY)

    def test_disk_check(self):
        """Test disk check returns valid data."""
        handler = self._create_handler("/health")
        result = handler._check_disk()

        self.assertIn("status", result)
        self.assertIn(result["status"], [
            HealthStatus.HEALTHY,
            HealthStatus.DEGRADED,
            HealthStatus.UNHEALTHY
        ])

    def test_health_data_structure(self):
        """Test health data has required structure."""
        handler = self._create_handler("/health")
        data = handler._get_health_data()

        # Required top-level fields
        required_fields = ["status", "timestamp", "service", "system", "checks"]
        for field in required_fields:
            self.assertIn(field, data)

        # Service info
        self.assertIn("name", data["service"])
        self.assertIn("version", data["service"])
        self.assertIn("environment", data["service"])

        # System info
        self.assertIn("hostname", data["system"])
        self.assertIn("platform", data["system"])
        self.assertIn("python_version", data["system"])
        self.assertIn("uptime_seconds", data["system"])

    def test_readiness_check_default(self):
        """Test default readiness check returns True."""
        handler = self._create_handler("/health/ready")
        self.assertTrue(handler._check_readiness())

    def test_json_response_headers(self):
        """Test JSON response has correct headers."""
        handler = self._create_handler("/health")
        self._mock_send_methods(handler)

        handler._send_json_response(200, {"test": "data"})

        # Verify Content-Type header was set
        calls = handler.send_header.call_args_list
        content_type_set = any(
            call[0] == ("Content-Type", "application/json")
            for call in calls
        )
        self.assertTrue(content_type_set)

    def test_create_server(self):
        """Test server creation with custom host and port."""
        server = create_server("127.0.0.1", 9999)

        self.assertEqual(server.server_address, ("127.0.0.1", 9999))
        server.server_close()

    @patch.dict('os.environ', {'ENVIRONMENT': 'production'})
    def test_environment_variable(self):
        """Test environment variable is read correctly."""
        handler = self._create_handler("/health")
        data = handler._get_health_data()

        self.assertEqual(data["service"]["environment"], "production")


class TestHealthCheckIntegration(unittest.TestCase):
    """Integration tests for the health check API."""

    def test_server_startup(self):
        """Test server can start and stop cleanly."""
        server = create_server("127.0.0.1", 0)  # Port 0 = random available port
        self.assertIsNotNone(server)
        server.server_close()

    def test_uptime_calculation(self):
        """Test uptime is calculated correctly."""
        handler = HealthCheckHandler.__new__(HealthCheckHandler)
        handler.path = "/health"

        # Uptime should be positive
        data = handler._get_health_data()
        self.assertGreaterEqual(data["system"]["uptime_seconds"], 0)


if __name__ == "__main__":
    unittest.main()
