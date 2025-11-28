"""Integration tests for API health and metrics endpoints."""

import pytest
from httpx import AsyncClient
from src.ml_pipeline.api import app


@pytest.mark.asyncio
async def test_health_endpoint_returns_200():
    """Health endpoint should return 200 OK"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint_structure():
    """Health endpoint should return proper structure"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        data = response.json()

        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]
        assert "service" in data
        assert data["service"] == "ML Pipeline Orchestration"
        assert "version" in data
        assert "dependencies" in data
        assert "metrics" in data


@pytest.mark.asyncio
async def test_health_dependencies_structure():
    """Health endpoint should report dependency status"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        data = response.json()

        dependencies = data["dependencies"]
        assert "database" in dependencies
        assert "redis" in dependencies

        for dep_name, dep_info in dependencies.items():
            assert "status" in dep_info
            assert "required" in dep_info


@pytest.mark.asyncio
async def test_root_endpoint():
    """Root endpoint should return service info"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "ML Pipeline Orchestration"
        assert data["version"] == "1.0.0"
        assert data["status"] == "operational"


@pytest.mark.asyncio
async def test_metrics_endpoint_exists():
    """Metrics endpoint should exist"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/metrics")
        # Prometheus metrics endpoint returns 200
        assert response.status_code == 200
        # Should contain prometheus format
        assert b"http_requests_total" in response.content


@pytest.mark.asyncio
async def test_cors_headers():
    """CORS headers should be present"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.options(
            "/health",
            headers={"Origin": "http://example.com"}
        )
        assert "access-control-allow-origin" in response.headers
