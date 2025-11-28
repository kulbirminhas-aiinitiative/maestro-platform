"""Integration tests for API health endpoints."""

import pytest
from httpx import AsyncClient
from src.backend.api.main import app


@pytest.mark.asyncio
async def test_health_endpoint_returns_200():
    """Health endpoint should return 200 OK."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_endpoint_structure():
    """Health endpoint should return proper structure."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        data = response.json()

        assert "status" in data
        assert "dependencies" in data
        assert "circuit_breakers" in data


@pytest.mark.asyncio
async def test_root_endpoint():
    """Root endpoint should return service info."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/")
        assert response.status_code == 200

        data = response.json()
        assert data["service"] == "Event Sourcing SaaS API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"


@pytest.mark.asyncio
async def test_metrics_endpoint_exists():
    """Metrics endpoint should exist."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/metrics")
        # Prometheus metrics endpoint returns 200
        assert response.status_code == 200
