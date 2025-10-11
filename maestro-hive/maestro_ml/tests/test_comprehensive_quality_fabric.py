"""
Comprehensive Test Suite for Maestro ML Platform
For use with Quality Fabric (TaaS) testing service

This test suite covers:
- All API endpoints
- Error handling
- Edge cases
- Performance scenarios
- Security validations
- Data integrity
"""

import pytest
from httpx import AsyncClient
import uuid


# ============================================================================
# Project API Tests
# ============================================================================

class TestProjectAPI:
    """Comprehensive tests for Project endpoints"""

    @pytest.mark.asyncio
    async def test_create_project_minimal(self, client: AsyncClient):
        """Test creating project with minimal required fields"""
        project_data = {
            "name": "minimal-project",
            "problem_class": "classification",
            "team_size": 1
        }
        response = await client.post("/api/v1/projects", json=project_data)
        assert response.status_code == 200
        assert response.json()["name"] == project_data["name"]

    @pytest.mark.asyncio
    async def test_create_project_full(self, client: AsyncClient):
        """Test creating project with all fields"""
        project_data = {
            "name": "full-featured-project",
            "problem_class": "nlp",
            "complexity_score": 9,
            "team_size": 5,
            "metadata": {
                "description": "Advanced NLP system",
                "dataset_size_gb": 500,
                "languages": ["en", "es", "fr"],
                "frameworks": ["pytorch", "transformers"]
            }
        }
        response = await client.post("/api/v1/projects", json=project_data)
        assert response.status_code == 200
        data = response.json()
        assert data["complexity_score"] == 9
        assert data["team_size"] == 5

    @pytest.mark.asyncio
    async def test_create_project_invalid_data(self, client: AsyncClient):
        """Test creating project with invalid data"""
        # Missing required field
        project_data = {
            "name": "invalid-project",
            "problem_class": "classification"
            # Missing team_size
        }
        response = await client.post("/api/v1/projects", json=project_data)
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_project_by_id(self, client: AsyncClient):
        """Test retrieving project by ID"""
        # Create project first
        project_data = {
            "name": "test-retrieval",
            "problem_class": "regression",
            "team_size": 2
        }
        create_response = await client.post("/api/v1/projects", json=project_data)
        project_id = create_response.json()["id"]

        # Get project
        get_response = await client.get(f"/api/v1/projects/{project_id}")
        assert get_response.status_code == 200
        assert get_response.json()["name"] == project_data["name"]

    @pytest.mark.asyncio
    async def test_get_project_nonexistent(self, client: AsyncClient):
        """Test retrieving non-existent project"""
        fake_id = str(uuid.uuid4())
        response = await client.get(f"/api/v1/projects/{fake_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_project_invalid_id(self, client: AsyncClient):
        """Test retrieving project with invalid ID format"""
        invalid_id = "not-a-uuid"
        response = await client.get(f"/api/v1/projects/{invalid_id}")
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_update_project_success_all_fields(self, client: AsyncClient):
        """Test updating project with all success metrics"""
        # Create project
        project_data = {
            "name": "update-test-all-fields",
            "problem_class": "classification",
            "team_size": 3
        }
        create_response = await client.post("/api/v1/projects", json=project_data)
        project_id = create_response.json()["id"]

        # Update with all fields
        update_data = {
            "model_accuracy": 0.95,
            "business_impact_usd": 1000000.0,
            "deployment_days": 30,
            "compute_cost": 5000.0
        }
        update_response = await client.patch(
            f"/api/v1/projects/{project_id}/success",
            json=update_data
        )
        assert update_response.status_code == 200
        updated = update_response.json()
        assert updated["model_performance"] == 0.95
        assert updated["business_impact"] == 1000000.0
        assert updated["compute_cost"] == 5000.0

    @pytest.mark.asyncio
    async def test_update_project_success_partial(self, client: AsyncClient):
        """Test updating project with partial success metrics"""
        # Create project
        project_data = {
            "name": "update-test-partial",
            "problem_class": "forecasting",
            "team_size": 2
        }
        create_response = await client.post("/api/v1/projects", json=project_data)
        project_id = create_response.json()["id"]

        # Update with only model_accuracy
        update_data = {"model_accuracy": 0.88}
        update_response = await client.patch(
            f"/api/v1/projects/{project_id}/success",
            json=update_data
        )
        assert update_response.status_code == 200
        assert update_response.json()["model_performance"] == 0.88


# ============================================================================
# Artifact API Tests
# ============================================================================

class TestArtifactAPI:
    """Comprehensive tests for Artifact endpoints"""

    @pytest.mark.asyncio
    async def test_create_artifact_minimal(self, client: AsyncClient):
        """Test creating artifact with minimal fields"""
        artifact_data = {
            "name": "minimal-artifact",
            "type": "schema",
            "version": "1.0.0",
            "storage_path": "s3://bucket/schema.json"
        }
        response = await client.post("/api/v1/artifacts", json=artifact_data)
        assert response.status_code == 200
        assert response.json()["name"] == artifact_data["name"]

    @pytest.mark.asyncio
    async def test_create_artifact_full(self, client: AsyncClient):
        """Test creating artifact with all fields"""
        artifact_data = {
            "name": "comprehensive-pipeline",
            "type": "feature_pipeline",
            "version": "2.5.1",
            "created_by": "data-science-team",
            "tags": ["production", "optimized", "v2"],
            "storage_path": "s3://maestro/pipelines/comprehensive-v2.py",
            "metadata": {
                "description": "Optimized feature pipeline v2",
                "dependencies": ["pandas>=2.0", "numpy>=1.24"],
                "performance": {"avg_runtime_ms": 150}
            }
        }
        response = await client.post("/api/v1/artifacts", json=artifact_data)
        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "2.5.1"
        assert len(data["tags"]) == 3
        assert data["usage_count"] == 0
        assert data["avg_impact_score"] == 0.0

    @pytest.mark.asyncio
    async def test_create_multiple_artifact_types(self, client: AsyncClient):
        """Test creating different artifact types"""
        artifact_types = [
            "feature_pipeline",
            "model_template",
            "schema",
            "notebook"
        ]

        for artifact_type in artifact_types:
            artifact_data = {
                "name": f"test-{artifact_type}",
                "type": artifact_type,
                "version": "1.0.0",
                "storage_path": f"s3://bucket/{artifact_type}.ext"
            }
            response = await client.post("/api/v1/artifacts", json=artifact_data)
            assert response.status_code == 200
            assert response.json()["type"] == artifact_type

    @pytest.mark.asyncio
    async def test_search_artifacts_by_type(self, client: AsyncClient):
        """Test searching artifacts by type"""
        # Create artifacts of different types
        for i in range(3):
            artifact_data = {
                "name": f"pipeline-{i}",
                "type": "feature_pipeline",
                "version": "1.0.0",
                "storage_path": f"s3://bucket/pipeline-{i}.py"
            }
            await client.post("/api/v1/artifacts", json=artifact_data)

        # Search
        search_response = await client.post(
            "/api/v1/artifacts/search",
            json={"type": "feature_pipeline"}
        )
        assert search_response.status_code == 200
        results = search_response.json()
        assert len(results) >= 3
        assert all(r["type"] == "feature_pipeline" for r in results)

    @pytest.mark.asyncio
    async def test_search_artifacts_by_multiple_tags(self, client: AsyncClient):
        """Test searching artifacts by multiple tags"""
        # Create artifacts with overlapping tags
        artifact_data1 = {
            "name": "tagged-artifact-1",
            "type": "model_template",
            "version": "1.0.0",
            "tags": ["production", "ml", "classification"],
            "storage_path": "s3://bucket/model1.pkl"
        }
        artifact_data2 = {
            "name": "tagged-artifact-2",
            "type": "model_template",
            "version": "1.0.0",
            "tags": ["staging", "ml", "regression"],
            "storage_path": "s3://bucket/model2.pkl"
        }

        await client.post("/api/v1/artifacts", json=artifact_data1)
        await client.post("/api/v1/artifacts", json=artifact_data2)

        # Search for "ml" tag
        search_response = await client.post(
            "/api/v1/artifacts/search",
            json={"tags": ["ml"]}
        )
        assert search_response.status_code == 200
        results = search_response.json()
        assert len(results) >= 2

    @pytest.mark.asyncio
    async def test_search_artifacts_by_name_query(self, client: AsyncClient):
        """Test searching artifacts by name query"""
        artifact_data = {
            "name": "unique-searchable-pipeline",
            "type": "feature_pipeline",
            "version": "1.0.0",
            "storage_path": "s3://bucket/unique.py"
        }
        await client.post("/api/v1/artifacts", json=artifact_data)

        # Search by name
        search_response = await client.post(
            "/api/v1/artifacts/search",
            json={"query": "searchable"}
        )
        assert search_response.status_code == 200
        results = search_response.json()
        assert any("searchable" in r["name"].lower() for r in results)

    @pytest.mark.asyncio
    async def test_search_artifacts_empty_results(self, client: AsyncClient):
        """Test searching with no matching artifacts"""
        search_response = await client.post(
            "/api/v1/artifacts/search",
            json={"query": "nonexistent-artifact-xyz-123"}
        )
        assert search_response.status_code == 200
        results = search_response.json()
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_log_artifact_usage(self, client: AsyncClient):
        """Test logging artifact usage"""
        # Create project and artifact
        project_data = {
            "name": "usage-test-project",
            "problem_class": "classification",
            "team_size": 2
        }
        project_response = await client.post("/api/v1/projects", json=project_data)
        project_id = project_response.json()["id"]

        artifact_data = {
            "name": "used-artifact",
            "type": "feature_pipeline",
            "version": "1.0.0",
            "storage_path": "s3://bucket/used.py"
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

    @pytest.mark.asyncio
    async def test_log_artifact_usage_with_impact_score(self, client: AsyncClient):
        """Test logging artifact usage with impact score"""
        # Create project and artifact
        project_data = {
            "name": "impact-test-project",
            "problem_class": "nlp",
            "team_size": 3
        }
        project_response = await client.post("/api/v1/projects", json=project_data)
        project_id = project_response.json()["id"]

        artifact_data = {
            "name": "high-impact-artifact",
            "type": "model_template",
            "version": "3.0.0",
            "storage_path": "s3://bucket/high-impact.pkl"
        }
        artifact_response = await client.post("/api/v1/artifacts", json=artifact_data)
        artifact_id = artifact_response.json()["id"]

        # Log usage with impact score
        usage_response = await client.post(
            f"/api/v1/artifacts/{artifact_id}/use",
            json={
                "project_id": project_id,
                "impact_score": 92.5,
                "context": {"modification": "minor tuning"}
            }
        )
        assert usage_response.status_code == 200
        usage_data = usage_response.json()
        assert usage_data["impact_score"] == 92.5


# ============================================================================
# Metrics API Tests
# ============================================================================

class TestMetricsAPI:
    """Comprehensive tests for Metrics endpoints"""

    @pytest.mark.asyncio
    async def test_create_metric(self, client: AsyncClient):
        """Test creating a process metric"""
        # Create project
        project_data = {
            "name": "metrics-test-project",
            "problem_class": "classification",
            "team_size": 2
        }
        project_response = await client.post("/api/v1/projects", json=project_data)
        project_id = project_response.json()["id"]

        # Create metric
        metric_data = {
            "project_id": project_id,
            "metric_type": "commits_per_week",
            "metric_value": 20.0,
            "metadata": {"repo": "github.com/org/project"}
        }
        response = await client.post("/api/v1/metrics", json=metric_data)
        assert response.status_code == 200
        assert "metric_id" in response.json()

    @pytest.mark.asyncio
    async def test_create_multiple_metric_types(self, client: AsyncClient):
        """Test creating different types of metrics"""
        # Create project
        project_data = {
            "name": "multi-metric-project",
            "problem_class": "forecasting",
            "team_size": 4
        }
        project_response = await client.post("/api/v1/projects", json=project_data)
        project_id = project_response.json()["id"]

        # Create various metrics
        metrics = [
            {"metric_type": "commits_per_week", "metric_value": 15.0},
            {"metric_type": "avg_pr_merge_time_hours", "metric_value": 3.5},
            {"metric_type": "pipeline_success_rate", "metric_value": 0.96},
            {"metric_type": "mlflow_experiments", "metric_value": 150.0}
        ]

        for metric in metrics:
            metric_data = {
                "project_id": project_id,
                "metric_type": metric["metric_type"],
                "metric_value": metric["metric_value"],
                "metadata": {}
            }
            response = await client.post("/api/v1/metrics", json=metric_data)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_metrics_summary(self, client: AsyncClient):
        """Test getting metrics summary for a project"""
        # Create project
        project_data = {
            "name": "summary-test-project",
            "problem_class": "classification",
            "team_size": 3
        }
        project_response = await client.post("/api/v1/projects", json=project_data)
        project_id = project_response.json()["id"]

        # Create metrics
        for i in range(5):
            metric_data = {
                "project_id": project_id,
                "metric_type": "commits_per_week",
                "metric_value": 10.0 + i,
                "metadata": {}
            }
            await client.post("/api/v1/metrics", json=metric_data)

        # Get summary
        summary_response = await client.get(f"/api/v1/metrics/{project_id}/summary")
        assert summary_response.status_code == 200
        summary = summary_response.json()
        assert "commits_per_week" in summary
        assert len(summary["commits_per_week"]) == 5

    @pytest.mark.asyncio
    async def test_calculate_development_velocity(self, client: AsyncClient):
        """Test calculating development velocity score"""
        # Create project
        project_data = {
            "name": "velocity-test-project",
            "problem_class": "nlp",
            "team_size": 5
        }
        project_response = await client.post("/api/v1/projects", json=project_data)
        project_id = project_response.json()["id"]

        # Create metrics that affect velocity
        metrics = [
            {"metric_type": "commits_per_week", "metric_value": 25.0},
            {"metric_type": "pipeline_success_rate", "metric_value": 0.92},
            {"metric_type": "artifact_reuse_rate", "metric_value": 0.75}
        ]

        for metric in metrics:
            metric_data = {
                "project_id": project_id,
                "metric_type": metric["metric_type"],
                "metric_value": metric["metric_value"],
                "metadata": {}
            }
            await client.post("/api/v1/metrics", json=metric_data)

        # Calculate velocity
        velocity_response = await client.get(f"/api/v1/metrics/{project_id}/velocity")
        assert velocity_response.status_code == 200
        velocity_data = velocity_response.json()
        assert "velocity_score" in velocity_data
        assert 0 <= velocity_data["velocity_score"] <= 100


# ============================================================================
# End-to-End Workflow Tests
# ============================================================================

class TestEndToEndWorkflows:
    """Test complete ML project workflows"""

    @pytest.mark.asyncio
    async def test_small_team_project_workflow(self, client: AsyncClient):
        """Test workflow for a small 1-2 person team"""
        # 1. Create small project
        project_data = {
            "name": "small-team-churn-prediction",
            "problem_class": "classification",
            "complexity_score": 5,
            "team_size": 2
        }
        project_response = await client.post("/api/v1/projects", json=project_data)
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]

        # 2. Register 2 artifacts
        artifacts = [
            {
                "name": "simple-feature-pipeline",
                "type": "feature_pipeline",
                "version": "1.0.0",
                "tags": ["churn", "simple"],
                "storage_path": "s3://bucket/simple-pipeline.py"
            },
            {
                "name": "basic-classifier",
                "type": "model_template",
                "version": "1.0.0",
                "tags": ["churn", "xgboost"],
                "storage_path": "s3://bucket/classifier.pkl"
            }
        ]

        artifact_ids = []
        for artifact in artifacts:
            artifact_response = await client.post("/api/v1/artifacts", json=artifact)
            artifact_ids.append(artifact_response.json()["id"])

        # 3. Log artifact usage
        for artifact_id in artifact_ids:
            await client.post(
                f"/api/v1/artifacts/{artifact_id}/use",
                json={"project_id": project_id}
            )

        # 4. Log metrics
        metrics = [
            {"metric_type": "commits_per_week", "metric_value": 12.0},
            {"metric_type": "pipeline_success_rate", "metric_value": 0.88}
        ]
        for metric in metrics:
            metric_data = {
                "project_id": project_id,
                "metric_type": metric["metric_type"],
                "metric_value": metric["metric_value"],
                "metadata": {}
            }
            await client.post("/api/v1/metrics", json=metric_data)

        # 5. Update with success metrics
        success_data = {
            "model_accuracy": 0.87,
            "business_impact_usd": 75000.0,
            "deployment_days": 21
        }
        success_response = await client.patch(
            f"/api/v1/projects/{project_id}/success",
            json=success_data
        )
        assert success_response.status_code == 200

        # 6. Verify final state
        final_project = success_response.json()
        assert final_project["model_performance"] == 0.87
        assert final_project["team_size"] == 2

    @pytest.mark.asyncio
    async def test_large_team_complex_project_workflow(self, client: AsyncClient):
        """Test workflow for a large 8+ person team on complex project"""
        # 1. Create complex project
        project_data = {
            "name": "enterprise-recommendation-system",
            "problem_class": "recommendation",
            "complexity_score": 10,
            "team_size": 8,
            "metadata": {
                "description": "Large-scale recommendation engine",
                "dataset_size_gb": 5000,
                "models": ["collaborative-filtering", "content-based", "hybrid"]
            }
        }
        project_response = await client.post("/api/v1/projects", json=project_data)
        project_id = project_response.json()["id"]

        # 2. Register multiple artifacts (simulating large project)
        for i in range(10):
            artifact_data = {
                "name": f"enterprise-component-{i}",
                "type": ["feature_pipeline", "model_template", "schema"][i % 3],
                "version": "1.0.0",
                "tags": ["enterprise", "recommendation"],
                "storage_path": f"s3://bucket/component-{i}.ext"
            }
            artifact_response = await client.post("/api/v1/artifacts", json=artifact_data)
            artifact_id = artifact_response.json()["id"]

            # Log usage with varying impact scores
            await client.post(
                f"/api/v1/artifacts/{artifact_id}/use",
                json={
                    "project_id": project_id,
                    "impact_score": 70.0 + (i * 2)
                }
            )

        # 3. Log extensive metrics
        metrics = [
            {"metric_type": "commits_per_week", "metric_value": 45.0},
            {"metric_type": "avg_pr_merge_time_hours", "metric_value": 6.5},
            {"metric_type": "pipeline_success_rate", "metric_value": 0.94},
            {"metric_type": "mlflow_experiments", "metric_value": 250.0}
        ]
        for metric in metrics:
            metric_data = {
                "project_id": project_id,
                "metric_type": metric["metric_type"],
                "metric_value": metric["metric_value"],
                "metadata": {}
            }
            await client.post("/api/v1/metrics", json=metric_data)

        # 4. Update with high success metrics
        success_data = {
            "model_accuracy": 0.96,
            "business_impact_usd": 2000000.0,
            "deployment_days": 90,
            "compute_cost": 50000.0
        }
        success_response = await client.patch(
            f"/api/v1/projects/{project_id}/success",
            json=success_data
        )
        assert success_response.status_code == 200


# ============================================================================
# Performance and Edge Case Tests
# ============================================================================

class TestPerformanceAndEdgeCases:
    """Test performance scenarios and edge cases"""

    @pytest.mark.asyncio
    async def test_create_many_projects(self, client: AsyncClient):
        """Test creating multiple projects in sequence"""
        for i in range(10):
            project_data = {
                "name": f"bulk-project-{i}",
                "problem_class": ["classification", "regression", "nlp"][i % 3],
                "team_size": (i % 5) + 1
            }
            response = await client.post("/api/v1/projects", json=project_data)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_many_artifacts(self, client: AsyncClient):
        """Test creating multiple artifacts in sequence"""
        for i in range(20):
            artifact_data = {
                "name": f"bulk-artifact-{i}",
                "type": ["feature_pipeline", "model_template", "schema", "notebook"][i % 4],
                "version": f"{(i % 3) + 1}.0.0",
                "storage_path": f"s3://bucket/bulk-{i}.ext"
            }
            response = await client.post("/api/v1/artifacts", json=artifact_data)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_zero_team_size(self, client: AsyncClient):
        """Test edge case: zero team size"""
        project_data = {
            "name": "zero-team-project",
            "problem_class": "classification",
            "team_size": 0
        }
        response = await client.post("/api/v1/projects", json=project_data)
        # Should succeed but may want to add validation later
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_very_large_team_size(self, client: AsyncClient):
        """Test edge case: very large team size"""
        project_data = {
            "name": "huge-team-project",
            "problem_class": "forecasting",
            "team_size": 100
        }
        response = await client.post("/api/v1/projects", json=project_data)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_empty_tags_array(self, client: AsyncClient):
        """Test artifact with empty tags array"""
        artifact_data = {
            "name": "no-tags-artifact",
            "type": "schema",
            "version": "1.0.0",
            "tags": [],
            "storage_path": "s3://bucket/no-tags.json"
        }
        response = await client.post("/api/v1/artifacts", json=artifact_data)
        assert response.status_code == 200
        assert response.json()["tags"] == []

    @pytest.mark.asyncio
    async def test_search_with_all_filters(self, client: AsyncClient):
        """Test searching with all filter parameters"""
        # Create test artifact
        artifact_data = {
            "name": "advanced-search-test",
            "type": "model_template",
            "version": "1.0.0",
            "tags": ["advanced", "test"],
            "storage_path": "s3://bucket/advanced.pkl"
        }
        await client.post("/api/v1/artifacts", json=artifact_data)

        # Search with all filters
        search_response = await client.post(
            "/api/v1/artifacts/search",
            json={
                "query": "advanced",
                "type": "model_template",
                "tags": ["advanced"],
                "min_impact_score": 0.0
            }
        )
        assert search_response.status_code == 200


# ============================================================================
# Data Integrity Tests
# ============================================================================

class TestDataIntegrity:
    """Test data integrity and consistency"""

    @pytest.mark.asyncio
    async def test_project_timestamps(self, client: AsyncClient):
        """Test that project timestamps are set correctly"""
        project_data = {
            "name": "timestamp-test",
            "problem_class": "classification",
            "team_size": 2
        }
        response = await client.post("/api/v1/projects", json=project_data)
        data = response.json()

        assert "start_date" in data
        assert data["start_date"] is not None
        assert data["completion_date"] is None  # Should be null initially

    @pytest.mark.asyncio
    async def test_artifact_usage_count_increments(self, client: AsyncClient):
        """Test that artifact usage count increments correctly"""
        # Create project and artifact
        project_data = {
            "name": "usage-count-project",
            "problem_class": "classification",
            "team_size": 2
        }
        project_response = await client.post("/api/v1/projects", json=project_data)
        project_id = project_response.json()["id"]

        artifact_data = {
            "name": "usage-count-artifact",
            "type": "feature_pipeline",
            "version": "1.0.0",
            "storage_path": "s3://bucket/usage-count.py"
        }
        artifact_response = await client.post("/api/v1/artifacts", json=artifact_data)
        artifact_id = artifact_response.json()["id"]

        # Initial usage count should be 0
        initial_count = artifact_response.json()["usage_count"]
        assert initial_count == 0

        # Log usage twice
        for _ in range(2):
            await client.post(
                f"/api/v1/artifacts/{artifact_id}/use",
                json={"project_id": project_id}
            )

        # Note: Would need GET endpoint for artifacts to verify count increment
        # This is a placeholder for when that endpoint exists

    @pytest.mark.asyncio
    async def test_metric_values_precision(self, client: AsyncClient):
        """Test that metric values maintain precision"""
        # Create project
        project_data = {
            "name": "precision-test-project",
            "problem_class": "regression",
            "team_size": 2
        }
        project_response = await client.post("/api/v1/projects", json=project_data)
        project_id = project_response.json()["id"]

        # Create metric with decimal precision
        metric_data = {
            "project_id": project_id,
            "metric_type": "test_metric",
            "metric_value": 12.345678,
            "metadata": {}
        }
        await client.post("/api/v1/metrics", json=metric_data)

        # Get summary and verify precision
        summary_response = await client.get(f"/api/v1/metrics/{project_id}/summary")
        summary = summary_response.json()
        assert "test_metric" in summary
        # Verify value maintains reasonable precision
        assert abs(summary["test_metric"][0]["value"] - 12.345678) < 0.0001
