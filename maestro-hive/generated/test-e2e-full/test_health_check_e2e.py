"""
End-to-End Tests for Health Check API

Comprehensive E2E test suite that tests the actual HTTP server
with real network requests.

Author: Rachel - QA Engineer
Date: 2025-11-22
"""

import json
import time
import unittest
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer

from health_check_api import HealthCheckHandler, create_server


class TestHealthCheckE2E(unittest.TestCase):
    """End-to-end tests for the Health Check API."""

    @classmethod
    def setUpClass(cls):
        """Start the test server before running tests."""
        cls.host = "127.0.0.1"
        cls.port = 0  # Let OS assign available port
        cls.server = create_server(cls.host, cls.port)
        cls.port = cls.server.server_address[1]  # Get assigned port
        cls.base_url = f"http://{cls.host}:{cls.port}"

        # Start server in background thread
        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()

        # Give server time to start
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        """Shutdown the test server."""
        cls.server.shutdown()
        cls.server.server_close()

    def _make_request(self, path: str, method: str = "GET"):
        """Make HTTP request and return response data."""
        url = f"{self.base_url}{path}"
        request = urllib.request.Request(url, method=method)

        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                return {
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "body": json.loads(response.read().decode("utf-8"))
                }
        except urllib.error.HTTPError as e:
            return {
                "status_code": e.code,
                "headers": dict(e.headers),
                "body": json.loads(e.read().decode("utf-8"))
            }

    # ==================== /health endpoint tests ====================

    def test_health_endpoint_returns_200(self):
        """Test /health returns 200 status code."""
        response = self._make_request("/health")
        self.assertEqual(response["status_code"], 200)

    def test_health_endpoint_returns_json(self):
        """Test /health returns valid JSON with correct content type."""
        response = self._make_request("/health")
        self.assertEqual(
            response["headers"]["Content-Type"],
            "application/json"
        )

    def test_health_endpoint_has_required_fields(self):
        """Test /health response contains all required fields."""
        response = self._make_request("/health")
        body = response["body"]

        required_fields = ["status", "timestamp", "service", "system", "checks"]
        for field in required_fields:
            self.assertIn(field, body, f"Missing required field: {field}")

    def test_health_endpoint_service_info(self):
        """Test /health returns correct service information."""
        response = self._make_request("/health")
        service = response["body"]["service"]

        self.assertEqual(service["name"], "health-check-api")
        self.assertEqual(service["version"], "1.0.0")
        self.assertIn("environment", service)

    def test_health_endpoint_system_info(self):
        """Test /health returns system information."""
        response = self._make_request("/health")
        system = response["body"]["system"]

        self.assertIn("hostname", system)
        self.assertIn("platform", system)
        self.assertIn("python_version", system)
        self.assertIn("uptime_seconds", system)
        self.assertGreaterEqual(system["uptime_seconds"], 0)

    def test_health_endpoint_checks(self):
        """Test /health returns memory and disk checks."""
        response = self._make_request("/health")
        checks = response["body"]["checks"]

        self.assertIn("memory", checks)
        self.assertIn("disk", checks)
        self.assertIn("status", checks["memory"])
        self.assertIn("status", checks["disk"])

    def test_health_endpoint_status_values(self):
        """Test /health returns valid status values."""
        response = self._make_request("/health")
        valid_statuses = ["healthy", "degraded", "unhealthy"]

        self.assertIn(response["body"]["status"], valid_statuses)

    def test_health_endpoint_timestamp_format(self):
        """Test /health returns ISO 8601 timestamp."""
        response = self._make_request("/health")
        timestamp = response["body"]["timestamp"]

        # Should be ISO 8601 format with timezone
        self.assertIn("T", timestamp)
        self.assertTrue(
            timestamp.endswith("Z") or "+" in timestamp or "-" in timestamp[-6:]
        )

    def test_health_endpoint_cache_control(self):
        """Test /health has no-cache headers."""
        response = self._make_request("/health")
        cache_control = response["headers"].get("Cache-Control", "")

        self.assertIn("no-cache", cache_control)

    # ==================== /health/live endpoint tests ====================

    def test_liveness_endpoint_returns_200(self):
        """Test /health/live returns 200 status code."""
        response = self._make_request("/health/live")
        self.assertEqual(response["status_code"], 200)

    def test_liveness_endpoint_minimal_response(self):
        """Test /health/live returns minimal response (no service/system info)."""
        response = self._make_request("/health/live")
        body = response["body"]

        self.assertIn("status", body)
        self.assertIn("timestamp", body)
        self.assertNotIn("service", body)
        self.assertNotIn("system", body)
        self.assertNotIn("checks", body)

    def test_liveness_endpoint_healthy_status(self):
        """Test /health/live returns healthy status."""
        response = self._make_request("/health/live")
        self.assertEqual(response["body"]["status"], "healthy")

    # ==================== /health/ready endpoint tests ====================

    def test_readiness_endpoint_returns_200(self):
        """Test /health/ready returns 200 when ready."""
        response = self._make_request("/health/ready")
        self.assertEqual(response["status_code"], 200)

    def test_readiness_endpoint_has_ready_field(self):
        """Test /health/ready includes ready boolean field."""
        response = self._make_request("/health/ready")
        self.assertIn("ready", response["body"])
        self.assertIsInstance(response["body"]["ready"], bool)

    def test_readiness_endpoint_ready_true(self):
        """Test /health/ready returns ready=true when service is ready."""
        response = self._make_request("/health/ready")
        self.assertTrue(response["body"]["ready"])

    def test_readiness_endpoint_status_matches_ready(self):
        """Test /health/ready status matches ready state."""
        response = self._make_request("/health/ready")
        body = response["body"]

        if body["ready"]:
            self.assertEqual(body["status"], "healthy")
        else:
            self.assertEqual(body["status"], "unhealthy")

    # ==================== Error handling tests ====================

    def test_404_for_unknown_endpoint(self):
        """Test unknown endpoints return 404."""
        response = self._make_request("/unknown")
        self.assertEqual(response["status_code"], 404)

    def test_404_response_format(self):
        """Test 404 response has correct format."""
        response = self._make_request("/unknown")
        body = response["body"]

        self.assertEqual(body["error"], "Not Found")
        self.assertIn("message", body)
        self.assertIn("available_endpoints", body)

    def test_404_lists_available_endpoints(self):
        """Test 404 response lists all available endpoints."""
        response = self._make_request("/unknown")
        endpoints = response["body"]["available_endpoints"]

        expected = ["/health", "/health/live", "/health/ready"]
        for endpoint in expected:
            self.assertIn(endpoint, endpoints)

    def test_root_endpoint_returns_404(self):
        """Test root / endpoint returns 404."""
        response = self._make_request("/")
        self.assertEqual(response["status_code"], 404)

    def test_trailing_slash_returns_404(self):
        """Test /health/ (with trailing slash) returns 404."""
        response = self._make_request("/health/")
        self.assertEqual(response["status_code"], 404)

    # ==================== Response consistency tests ====================

    def test_multiple_health_requests(self):
        """Test multiple requests return consistent structure."""
        for _ in range(3):
            response = self._make_request("/health")
            self.assertEqual(response["status_code"], 200)
            self.assertIn("status", response["body"])
            self.assertIn("timestamp", response["body"])

    def test_uptime_increases(self):
        """Test uptime increases between requests."""
        response1 = self._make_request("/health")
        uptime1 = response1["body"]["system"]["uptime_seconds"]

        time.sleep(0.1)

        response2 = self._make_request("/health")
        uptime2 = response2["body"]["system"]["uptime_seconds"]

        self.assertGreater(uptime2, uptime1)

    def test_timestamps_increase(self):
        """Test timestamps increase between requests."""
        response1 = self._make_request("/health")
        ts1 = response1["body"]["timestamp"]

        time.sleep(0.01)

        response2 = self._make_request("/health")
        ts2 = response2["body"]["timestamp"]

        self.assertGreater(ts2, ts1)

    # ==================== Schema validation tests ====================

    def test_health_response_types(self):
        """Test /health response field types match schema."""
        response = self._make_request("/health")
        body = response["body"]

        self.assertIsInstance(body["status"], str)
        self.assertIsInstance(body["timestamp"], str)
        self.assertIsInstance(body["service"], dict)
        self.assertIsInstance(body["system"], dict)
        self.assertIsInstance(body["checks"], dict)

    def test_system_info_types(self):
        """Test system info field types."""
        response = self._make_request("/health")
        system = response["body"]["system"]

        self.assertIsInstance(system["hostname"], str)
        self.assertIsInstance(system["platform"], str)
        self.assertIsInstance(system["python_version"], str)
        self.assertIsInstance(system["uptime_seconds"], (int, float))

    def test_service_info_types(self):
        """Test service info field types."""
        response = self._make_request("/health")
        service = response["body"]["service"]

        self.assertIsInstance(service["name"], str)
        self.assertIsInstance(service["version"], str)
        self.assertIsInstance(service["environment"], str)


class TestHealthCheckConcurrency(unittest.TestCase):
    """Concurrency tests for the Health Check API."""

    @classmethod
    def setUpClass(cls):
        """Start the test server."""
        cls.host = "127.0.0.1"
        cls.server = create_server(cls.host, 0)
        cls.port = cls.server.server_address[1]
        cls.base_url = f"http://{cls.host}:{cls.port}"

        cls.server_thread = threading.Thread(target=cls.server.serve_forever)
        cls.server_thread.daemon = True
        cls.server_thread.start()
        time.sleep(0.1)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()

    def test_concurrent_requests(self):
        """Test server handles concurrent requests."""
        results = []
        errors = []

        def make_request():
            try:
                url = f"{self.base_url}/health"
                with urllib.request.urlopen(url, timeout=5) as response:
                    results.append(response.status)
            except Exception as e:
                errors.append(str(e))

        # Create 10 concurrent requests
        threads = []
        for _ in range(10):
            t = threading.Thread(target=make_request)
            threads.append(t)
            t.start()

        # Wait for all to complete
        for t in threads:
            t.join(timeout=10)

        # All should succeed
        self.assertEqual(len(errors), 0, f"Errors: {errors}")
        self.assertEqual(len(results), 10)
        self.assertTrue(all(r == 200 for r in results))


if __name__ == "__main__":
    unittest.main()
