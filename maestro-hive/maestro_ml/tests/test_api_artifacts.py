"""
Test cases for Artifact API endpoints
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_artifact(client: AsyncClient):
    """Test creating a new artifact"""
    artifact_data = {
        "name": "feature-pipeline-transactions",
        "type": "feature_pipeline",
        "version": "1.0.0",
        "created_by": "data-team",
        "tags": ["transactions", "fraud", "preprocessing"],
        "storage_path": "s3://maestro-artifacts/pipelines/transactions-v1.py",
        "metadata": {
            "description": "Transaction feature engineering pipeline",
            "input_schema": "raw_transactions",
            "output_schema": "features_v1"
        }
    }

    response = await client.post("/api/v1/artifacts", json=artifact_data)
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == artifact_data["name"]
    assert data["type"] == artifact_data["type"]
    assert data["version"] == artifact_data["version"]
    assert data["tags"] == artifact_data["tags"]
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_search_artifacts_by_type(client: AsyncClient):
    """Test searching artifacts by type"""
    # Create multiple artifacts
    artifacts = [
        {
            "name": "xgboost-fraud-model",
            "type": "model_template",
            "version": "2.0.0",
            "created_by": "ml-team",
            "tags": ["xgboost", "fraud"],
            "storage_path": "s3://maestro-artifacts/models/xgboost-fraud.pkl"
        },
        {
            "name": "feature-pipeline-user-behavior",
            "type": "feature_pipeline",
            "version": "1.5.0",
            "created_by": "data-team",
            "tags": ["user", "behavior"],
            "storage_path": "s3://maestro-artifacts/pipelines/user-behavior-v1.py"
        }
    ]

    for artifact_data in artifacts:
        response = await client.post("/api/v1/artifacts", json=artifact_data)
        assert response.status_code == 200

    # Search for feature_pipeline type
    search_response = await client.post(
        "/api/v1/artifacts/search",
        json={"type": "feature_pipeline"}
    )
    assert search_response.status_code == 200

    results = search_response.json()
    assert len(results) >= 1
    assert all(r["type"] == "feature_pipeline" for r in results)


@pytest.mark.asyncio
async def test_search_artifacts_by_tags(client: AsyncClient):
    """Test searching artifacts by tags"""
    # Create artifact with specific tags
    artifact_data = {
        "name": "lightgbm-churn-model",
        "type": "model_template",
        "version": "1.0.0",
        "created_by": "ml-team",
        "tags": ["lightgbm", "churn", "classification"],
        "storage_path": "s3://maestro-artifacts/models/lightgbm-churn.pkl"
    }

    await client.post("/api/v1/artifacts", json=artifact_data)

    # Search by tags
    search_response = await client.post(
        "/api/v1/artifacts/search",
        json={"tags": ["churn"]}
    )
    assert search_response.status_code == 200

    results = search_response.json()
    assert len(results) >= 1
    assert any("churn" in r["tags"] for r in results)


@pytest.mark.asyncio
async def test_log_artifact_usage(client: AsyncClient):
    """Test logging artifact usage in a project"""
    # Create a project
    project_data = {
        "name": "test-project-with-artifacts",
        "problem_class": "classification",
        "complexity_score": 5,
        "team_size": 2
    }
    project_response = await client.post("/api/v1/projects", json=project_data)
    project_id = project_response.json()["id"]

    # Create an artifact
    artifact_data = {
        "name": "test-artifact-usage",
        "type": "schema",
        "version": "1.0.0",
        "created_by": "test-team",
        "tags": ["test"],
        "storage_path": "s3://test/schema.json"
    }
    artifact_response = await client.post("/api/v1/artifacts", json=artifact_data)
    artifact_id = artifact_response.json()["id"]

    # Log usage
    usage_response = await client.post(
        f"/api/v1/artifacts/{artifact_id}/use",
        json={"project_id": project_id}
    )
    assert usage_response.status_code == 200

    usage_data = usage_response.json()
    assert usage_data["artifact_id"] == artifact_id
    assert usage_data["project_id"] == project_id
    assert "used_at" in usage_data
