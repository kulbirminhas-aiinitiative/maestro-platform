"""
Unit tests for Health Check API.
"""

import pytest
from fastapi.testclient import TestClient
from health_check_api import app

client = TestClient(app)


def test_health_check():
    """Test basic health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["version"] == "1.0.0"
    assert "uptime_seconds" in data


def test_readiness_check():
    """Test readiness probe endpoint."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "timestamp" in data


def test_liveness_check():
    """Test liveness probe endpoint."""
    response = client.get("/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "timestamp" in data


def test_detailed_health_check():
    """Test detailed health check endpoint."""
    response = client.get("/health/detailed")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    assert "timestamp" in data
    assert "version" in data
    assert "system" in data
    assert "checks" in data
    assert "platform" in data["system"]
    assert "api" in data["checks"]


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "health_endpoint" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
