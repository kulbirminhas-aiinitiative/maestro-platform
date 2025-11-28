"""
Test suite for Health Check API

Author: Marcus (Backend Developer)
"""

import pytest
from fastapi.testclient import TestClient
from health_api import app, _startup_time
from datetime import datetime


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


class TestHealthEndpoint:
    """Tests for /health endpoint"""

    def test_health_check_returns_200(self, client):
        """Test that health check returns 200 OK"""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_response_structure(self, client):
        """Test health check response has correct structure"""
        response = client.get("/health")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "service" in data
        assert "version" in data

    def test_health_check_status_is_healthy(self, client):
        """Test that status is healthy"""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_check_timestamp_is_valid(self, client):
        """Test timestamp is valid ISO format"""
        response = client.get("/health")
        data = response.json()
        # Should not raise exception
        datetime.fromisoformat(data["timestamp"])


class TestDetailedHealthEndpoint:
    """Tests for /health/detailed endpoint"""

    def test_detailed_health_returns_200(self, client):
        """Test that detailed health check returns 200"""
        response = client.get("/health/detailed")
        assert response.status_code == 200

    def test_detailed_health_response_structure(self, client):
        """Test detailed health response structure"""
        response = client.get("/health/detailed")
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "service" in data
        assert "version" in data
        assert "uptime_seconds" in data
        assert "system" in data

    def test_detailed_health_system_info(self, client):
        """Test system info is present"""
        response = client.get("/health/detailed")
        data = response.json()
        system = data["system"]

        assert "platform" in system
        assert "python_version" in system
        assert "hostname" in system
        assert "processor" in system
        assert "pid" in system

    def test_detailed_health_uptime_is_positive(self, client):
        """Test uptime is a positive number"""
        response = client.get("/health/detailed")
        data = response.json()
        assert data["uptime_seconds"] >= 0


class TestReadinessEndpoint:
    """Tests for /ready endpoint"""

    def test_readiness_returns_200(self, client):
        """Test readiness probe returns 200"""
        response = client.get("/ready")
        assert response.status_code == 200

    def test_readiness_returns_ready_true(self, client):
        """Test readiness returns ready=True"""
        response = client.get("/ready")
        data = response.json()
        assert data["ready"] is True


class TestLivenessEndpoint:
    """Tests for /live endpoint"""

    def test_liveness_returns_200(self, client):
        """Test liveness probe returns 200"""
        response = client.get("/live")
        assert response.status_code == 200

    def test_liveness_returns_alive_true(self, client):
        """Test liveness returns alive=True"""
        response = client.get("/live")
        data = response.json()
        assert data["alive"] is True


class TestAPIDocumentation:
    """Tests for API documentation endpoints"""

    def test_openapi_schema_available(self, client):
        """Test OpenAPI schema is available"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data

    def test_docs_available(self, client):
        """Test Swagger UI docs are available"""
        response = client.get("/docs")
        assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
