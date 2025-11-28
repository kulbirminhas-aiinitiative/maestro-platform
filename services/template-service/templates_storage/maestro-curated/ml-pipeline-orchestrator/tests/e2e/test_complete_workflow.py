"""End-to-end tests for complete ML pipeline workflows."""

import pytest
from httpx import AsyncClient
from src.ml_pipeline.api import app


@pytest.mark.asyncio
async def test_service_startup_and_health():
    """Test that service starts up and health check works"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Check root endpoint
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json()["status"] == "operational"

        # Check health endpoint
        health_response = await client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json()["status"] in ["healthy", "degraded"]

        # Check metrics endpoint
        metrics_response = await client.get("/metrics")
        assert metrics_response.status_code == 200


@pytest.mark.asyncio
async def test_api_documentation_accessible():
    """Test that API documentation is accessible"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # OpenAPI schema
        response = await client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()
        assert schema["info"]["title"] == "ML Pipeline Orchestration API"
        assert schema["info"]["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_workflow_endpoints_exist():
    """Test that workflow management endpoints exist"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # List workflows (should be empty initially)
        response = await client.get("/workflows")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

        # List executions (should be empty initially)
        response = await client.get("/executions")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_stages_endpoint():
    """Test that available stages can be listed"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/stages")
        assert response.status_code == 200

        stages = response.json()
        assert isinstance(stages, list)
        assert "data_ingestion" in stages
        assert "model_training" in stages


@pytest.mark.asyncio
async def test_metrics_endpoint_format():
    """Test that metrics endpoint returns Prometheus format"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/metrics")
        assert response.status_code == 200

        content = response.content.decode()
        # Check for expected metrics
        assert "http_requests_total" in content
        assert "http_request_duration_seconds" in content
        assert "workflow_executions_total" in content
