"""End-to-end tests for complete analytics workflow."""

import pytest
from src.api.app import app


@pytest.fixture
def client():
    """Flask test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_service_startup_and_health(client):
    """Test that service starts up and health check works"""
    # Check health endpoint
    response = client.get('/health')
    assert response.status_code in [200, 503]
    assert response.json['status'] in ['healthy', 'degraded']

    # Check metrics endpoint
    metrics_response = client.get('/metrics')
    assert metrics_response.status_code == 200


def test_api_endpoints_exist(client):
    """Test that API endpoints exist"""
    endpoints = [
        '/health',
        '/metrics',
        '/api/stats',
    ]

    for endpoint in endpoints:
        response = client.get(endpoint)
        # Should not return 404
        assert response.status_code != 404


def test_metrics_endpoint_format(client):
    """Test that metrics endpoint returns Prometheus format"""
    response = client.get('/metrics')
    assert response.status_code == 200

    content = response.data.decode()
    # Check for expected metrics
    assert "http_requests_total" in content
    assert "http_request_duration_seconds" in content


def test_health_check_tracks_dependencies(client):
    """Test that health check tracks all dependencies"""
    response = client.get('/health')
    data = response.json

    assert 'dependencies' in data
    dependencies = data['dependencies']

    # Should track PostgreSQL and Redis
    expected_deps = ['postgresql', 'redis']
    for dep in expected_deps:
        assert dep in dependencies
        assert 'status' in dependencies[dep]
        assert 'required' in dependencies[dep]
