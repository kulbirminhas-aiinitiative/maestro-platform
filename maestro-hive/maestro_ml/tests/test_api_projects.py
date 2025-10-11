"""
Test cases for Project API endpoints
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_endpoint(client: AsyncClient):
    """Test the root health check endpoint"""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "app" in data
    assert "version" in data
    assert "status" in data
    assert data["status"] == "running"


@pytest.mark.asyncio
async def test_create_project(client: AsyncClient):
    """Test creating a new project"""
    project_data = {
        "name": "test-fraud-detection",
        "problem_class": "classification",
        "complexity_score": 7,
        "team_size": 2,
        "metadata": {
            "description": "Test fraud detection model",
            "dataset_size_gb": 50
        }
    }

    response = await client.post("/api/v1/projects", json=project_data)
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == project_data["name"]
    assert data["problem_class"] == project_data["problem_class"]
    assert data["complexity_score"] == project_data["complexity_score"]
    assert data["team_size"] == project_data["team_size"]
    assert "id" in data
    assert "start_date" in data


@pytest.mark.asyncio
async def test_get_project(client: AsyncClient):
    """Test retrieving a project by ID"""
    # First create a project
    project_data = {
        "name": "test-recommendation-engine",
        "problem_class": "recommendation",
        "complexity_score": 8,
        "team_size": 3
    }

    create_response = await client.post("/api/v1/projects", json=project_data)
    assert create_response.status_code == 200
    created_project = create_response.json()
    project_id = created_project["id"]

    # Now get the project
    get_response = await client.get(f"/api/v1/projects/{project_id}")
    assert get_response.status_code == 200

    retrieved_project = get_response.json()
    assert retrieved_project["id"] == project_id
    assert retrieved_project["name"] == project_data["name"]


@pytest.mark.asyncio
async def test_get_nonexistent_project(client: AsyncClient):
    """Test retrieving a project that doesn't exist"""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.get(f"/api/v1/projects/{fake_id}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_project_success_metrics(client: AsyncClient):
    """Test updating project with success metrics"""
    # Create project
    project_data = {
        "name": "test-churn-prediction",
        "problem_class": "classification",
        "complexity_score": 6,
        "team_size": 2
    }

    create_response = await client.post("/api/v1/projects", json=project_data)
    project_id = create_response.json()["id"]

    # Update with success metrics
    update_data = {
        "model_accuracy": 0.92,
        "business_impact_usd": 150000.0,
        "deployment_days": 45
    }

    update_response = await client.patch(
        f"/api/v1/projects/{project_id}/success",
        json=update_data
    )
    assert update_response.status_code == 200

    updated_project = update_response.json()
    assert updated_project["model_performance"] == update_data["model_accuracy"]
    assert updated_project["business_impact"] == update_data["business_impact_usd"]
