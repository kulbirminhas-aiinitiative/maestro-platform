"""Integration tests for API health and metrics endpoints."""

import pytest
from src.api.app import app


@pytest.fixture
def client():
    """Flask test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_health_endpoint_returns_200(client):
    """Health endpoint should return 200 or 503"""
    response = client.get('/health')
    assert response.status_code in [200, 503]


def test_health_endpoint_structure(client):
    """Health endpoint should return proper structure"""
    response = client.get('/health')
    data = response.json

    assert 'status' in data
    assert data['status'] in ['healthy', 'degraded']
    assert 'service' in data
    assert data['service'] == 'analytics-api'
    assert 'version' in data
    assert 'dependencies' in data


def test_health_dependencies_structure(client):
    """Health endpoint should report dependency status"""
    response = client.get('/health')
    data = response.json

    dependencies = data['dependencies']
    assert 'postgresql' in dependencies
    assert 'redis' in dependencies

    for dep_name, dep_info in dependencies.items():
        assert 'status' in dep_info
        assert 'required' in dep_info


def test_metrics_endpoint_exists(client):
    """Metrics endpoint should exist and return Prometheus format"""
    response = client.get('/metrics')
    assert response.status_code == 200
    # Should contain prometheus format
    assert b"http_requests_total" in response.data


def test_metrics_endpoint_content_type(client):
    """Metrics endpoint should return correct content type"""
    response = client.get('/metrics')
    assert response.content_type.startswith('text/plain')
