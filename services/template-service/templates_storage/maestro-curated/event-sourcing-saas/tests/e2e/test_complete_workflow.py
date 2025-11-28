"""End-to-end tests for complete workflows."""

import pytest
from httpx import AsyncClient
from src.backend.api.main import app


@pytest.mark.asyncio
async def test_service_startup_and_health():
    """Test that service starts up and health check works."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Check root endpoint
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "running"

        # Check health endpoint
        health_response = await client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json()["status"] in ["healthy", "degraded"]

        # Check metrics endpoint
        metrics_response = await client.get("/metrics")
        assert metrics_response.status_code == 200


@pytest.mark.asyncio
async def test_api_documentation_accessible():
    """Test that API documentation is accessible."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # OpenAPI schema
        response = await client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert schema["info"]["title"] == "Event Sourcing SaaS API"
        assert schema["info"]["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_cors_headers_present():
    """Test that CORS headers are properly set."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.options(
            "/health",
            headers={"Origin": "http://example.com"}
        )

        assert "access-control-allow-origin" in response.headers
