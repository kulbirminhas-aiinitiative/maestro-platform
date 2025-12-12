"""Tests for PipelineManager."""

import pytest
from datetime import datetime

from maestro_hive.release_management.pipelines import PipelineManager
from maestro_hive.release_management.models import (
    PipelineStage,
    PipelineStatus,
    DeploymentGate,
    GateType,
)


class TestPipelineManager:
    """Tests for PipelineManager class."""

    @pytest.fixture
    def manager(self):
        """Create a fresh PipelineManager instance."""
        return PipelineManager()

    def test_init(self, manager):
        """Test manager initialization."""
        assert manager is not None
        assert len(manager._pipelines) == 0
        assert len(manager._default_stages) == 5

    def test_default_stages(self, manager):
        """Test default pipeline stages."""
        stage_names = [s.name for s in manager._default_stages]
        assert "build" in stage_names
        assert "unit-tests" in stage_names
        assert "integration-tests" in stage_names
        assert "security-scan" in stage_names
        assert "deploy" in stage_names

    def test_configure_pipeline(self, manager):
        """Test configuring a new pipeline."""
        pipeline = manager.configure_pipeline(
            environment="dev",
            name="dev-pipeline",
        )

        assert pipeline.id is not None
        assert pipeline.name == "dev-pipeline"
        assert pipeline.environment == "dev"
        assert len(pipeline.stages) == 5

    def test_configure_pipeline_default_name(self, manager):
        """Test pipeline with default name."""
        pipeline = manager.configure_pipeline(environment="test")
        assert pipeline.name == "test-pipeline"

    def test_configure_pipeline_with_stages(self, manager):
        """Test configuring pipeline with specific stages."""
        pipeline = manager.configure_pipeline(
            environment="dev",
            stages=["build", "deploy"],
        )

        assert len(pipeline.stages) == 2
        stage_names = [s.name for s in pipeline.stages]
        assert "build" in stage_names
        assert "deploy" in stage_names

    def test_configure_pipeline_with_custom_stages(self, manager):
        """Test configuring pipeline with custom stages."""
        custom_stages = [
            PipelineStage(name="custom-build", order=1),
            PipelineStage(name="custom-test", order=2),
        ]
        pipeline = manager.configure_pipeline(
            environment="dev",
            custom_stages=custom_stages,
        )

        assert len(pipeline.stages) == 2
        assert pipeline.stages[0].name == "custom-build"

    def test_get_pipeline(self, manager):
        """Test getting a pipeline by ID."""
        pipeline = manager.configure_pipeline(environment="dev")

        result = manager.get_pipeline(pipeline.id)
        assert result is not None
        assert result.id == pipeline.id

    def test_get_pipeline_not_found(self, manager):
        """Test getting non-existent pipeline."""
        result = manager.get_pipeline("nonexistent")
        assert result is None

    def test_get_pipeline_by_environment(self, manager):
        """Test getting pipeline by environment."""
        manager.configure_pipeline(environment="dev")

        result = manager.get_pipeline_by_environment("dev")
        assert result is not None
        assert result.environment == "dev"

    def test_get_pipeline_by_environment_not_found(self, manager):
        """Test getting pipeline for non-existent environment."""
        result = manager.get_pipeline_by_environment("nonexistent")
        assert result is None

    def test_list_pipelines(self, manager):
        """Test listing all pipelines."""
        manager.configure_pipeline(environment="dev")
        manager.configure_pipeline(environment="test")

        pipelines = manager.list_pipelines()
        assert len(pipelines) == 2

    def test_list_pipelines_by_environment(self, manager):
        """Test listing pipelines filtered by environment."""
        manager.configure_pipeline(environment="dev")
        manager.configure_pipeline(environment="test")

        pipelines = manager.list_pipelines(environment="dev")
        assert len(pipelines) == 1
        assert pipelines[0].environment == "dev"

    def test_update_pipeline_stages(self, manager):
        """Test updating pipeline stages."""
        pipeline = manager.configure_pipeline(environment="dev")

        new_stages = [PipelineStage(name="new-stage", order=1)]
        result = manager.update_pipeline(pipeline.id, stages=new_stages)

        assert result is not None
        assert len(result.stages) == 1
        assert result.stages[0].name == "new-stage"

    def test_update_pipeline_variables(self, manager):
        """Test updating pipeline variables."""
        pipeline = manager.configure_pipeline(environment="dev")

        result = manager.update_pipeline(
            pipeline.id,
            variables={"NODE_ENV": "development"},
        )

        assert result is not None
        assert result.variables["NODE_ENV"] == "development"

    def test_update_pipeline_not_found(self, manager):
        """Test updating non-existent pipeline."""
        result = manager.update_pipeline("nonexistent", variables={})
        assert result is None

    def test_delete_pipeline(self, manager):
        """Test deleting a pipeline."""
        pipeline = manager.configure_pipeline(environment="dev")

        result = manager.delete_pipeline(pipeline.id)
        assert result is True
        assert manager.get_pipeline(pipeline.id) is None

    def test_delete_pipeline_not_found(self, manager):
        """Test deleting non-existent pipeline."""
        result = manager.delete_pipeline("nonexistent")
        assert result is False

    def test_add_gate(self, manager):
        """Test adding a deployment gate."""
        pipeline = manager.configure_pipeline(environment="dev")

        gate = DeploymentGate(
            name="qa-approval",
            gate_type=GateType.MANUAL,
            approvers=["qa-lead"],
        )
        result = manager.add_gate(pipeline.id, gate)

        assert result is True
        assert len(pipeline.gates) == 1
        assert pipeline.gates[0].name == "qa-approval"

    def test_add_gate_not_found(self, manager):
        """Test adding gate to non-existent pipeline."""
        gate = DeploymentGate(name="test", gate_type=GateType.AUTOMATED)
        result = manager.add_gate("nonexistent", gate)
        assert result is False

    def test_remove_gate(self, manager):
        """Test removing a deployment gate."""
        pipeline = manager.configure_pipeline(environment="dev")
        gate = DeploymentGate(name="qa-approval", gate_type=GateType.MANUAL)
        manager.add_gate(pipeline.id, gate)

        result = manager.remove_gate(pipeline.id, "qa-approval")

        assert result is True
        assert len(pipeline.gates) == 0

    def test_remove_gate_not_found(self, manager):
        """Test removing non-existent gate."""
        pipeline = manager.configure_pipeline(environment="dev")

        result = manager.remove_gate(pipeline.id, "nonexistent")
        assert result is False

    def test_trigger_pipeline(self, manager):
        """Test triggering a pipeline run."""
        pipeline = manager.configure_pipeline(environment="dev")

        run = manager.trigger(pipeline.id)

        assert run.id is not None
        assert run.pipeline_id == pipeline.id
        assert run.status == PipelineStatus.RUNNING
        assert run.current_stage == "build"

    def test_trigger_pipeline_with_version(self, manager):
        """Test triggering pipeline with version."""
        pipeline = manager.configure_pipeline(environment="dev")

        run = manager.trigger(pipeline.id, version="1.0.0")

        assert run.version == "1.0.0"

    def test_trigger_pipeline_with_params(self, manager):
        """Test triggering pipeline with parameters."""
        pipeline = manager.configure_pipeline(environment="dev")

        run = manager.trigger(
            pipeline.id,
            params={"skip_tests": True},
        )

        assert run.metadata["skip_tests"] is True

    def test_trigger_nonexistent_pipeline(self, manager):
        """Test triggering non-existent pipeline."""
        run = manager.trigger("nonexistent")

        assert run.status == PipelineStatus.FAILED
        assert "not found" in run.error

    def test_get_run(self, manager):
        """Test getting a pipeline run."""
        pipeline = manager.configure_pipeline(environment="dev")
        run = manager.trigger(pipeline.id)

        result = manager.get_run(run.id)
        assert result is not None
        assert result.id == run.id

    def test_get_run_not_found(self, manager):
        """Test getting non-existent run."""
        result = manager.get_run("nonexistent")
        assert result is None

    def test_get_status(self, manager):
        """Test getting pipeline run status."""
        pipeline = manager.configure_pipeline(environment="dev")
        run = manager.trigger(pipeline.id)

        status = manager.get_status(run.id)
        assert status == PipelineStatus.RUNNING

    def test_get_status_not_found(self, manager):
        """Test getting status for non-existent run."""
        status = manager.get_status("nonexistent")
        assert status == PipelineStatus.FAILED

    def test_complete_run_success(self, manager):
        """Test completing a run successfully."""
        pipeline = manager.configure_pipeline(environment="dev")
        run = manager.trigger(pipeline.id)

        result = manager.complete_run(
            run.id,
            PipelineStatus.SUCCESS,
            artifacts=["build.tar.gz"],
        )

        assert result is not None
        assert result.status == PipelineStatus.SUCCESS
        assert result.completed_at is not None
        assert "build.tar.gz" in result.artifacts

    def test_complete_run_failure(self, manager):
        """Test completing a run with failure."""
        pipeline = manager.configure_pipeline(environment="dev")
        run = manager.trigger(pipeline.id)

        result = manager.complete_run(
            run.id,
            PipelineStatus.FAILED,
            error="Build failed",
        )

        assert result.status == PipelineStatus.FAILED
        assert result.error == "Build failed"

    def test_complete_run_not_found(self, manager):
        """Test completing non-existent run."""
        result = manager.complete_run("nonexistent", PipelineStatus.SUCCESS)
        assert result is None

    def test_cancel_run(self, manager):
        """Test cancelling a pipeline run."""
        pipeline = manager.configure_pipeline(environment="dev")
        run = manager.trigger(pipeline.id)

        result = manager.cancel_run(run.id)

        assert result is True
        assert run.status == PipelineStatus.CANCELLED
        assert run.completed_at is not None

    def test_cancel_completed_run(self, manager):
        """Test cancelling already completed run fails."""
        pipeline = manager.configure_pipeline(environment="dev")
        run = manager.trigger(pipeline.id)
        manager.complete_run(run.id, PipelineStatus.SUCCESS)

        result = manager.cancel_run(run.id)
        assert result is False

    def test_cancel_run_not_found(self, manager):
        """Test cancelling non-existent run."""
        result = manager.cancel_run("nonexistent")
        assert result is False

    def test_list_runs(self, manager):
        """Test listing pipeline runs."""
        pipeline = manager.configure_pipeline(environment="dev")
        manager.trigger(pipeline.id)
        manager.trigger(pipeline.id)

        runs = manager.list_runs()
        assert len(runs) == 2

    def test_list_runs_by_pipeline(self, manager):
        """Test listing runs filtered by pipeline."""
        pipe1 = manager.configure_pipeline(environment="dev")
        pipe2 = manager.configure_pipeline(environment="test")
        manager.trigger(pipe1.id)
        manager.trigger(pipe1.id)
        manager.trigger(pipe2.id)

        runs = manager.list_runs(pipeline_id=pipe1.id)
        assert len(runs) == 2

    def test_list_runs_by_status(self, manager):
        """Test listing runs filtered by status."""
        pipeline = manager.configure_pipeline(environment="dev")
        run1 = manager.trigger(pipeline.id)
        run2 = manager.trigger(pipeline.id)
        manager.complete_run(run1.id, PipelineStatus.SUCCESS)

        running = manager.list_runs(status=PipelineStatus.RUNNING)
        assert len(running) == 1

    def test_list_runs_with_limit(self, manager):
        """Test listing runs with limit."""
        pipeline = manager.configure_pipeline(environment="dev")
        for _ in range(10):
            manager.trigger(pipeline.id)

        runs = manager.list_runs(limit=5)
        assert len(runs) == 5

    def test_add_stage(self, manager):
        """Test adding a stage to pipeline."""
        pipeline = manager.configure_pipeline(
            environment="dev",
            stages=["build"],
        )

        stage = PipelineStage(name="new-stage", order=2)
        result = manager.add_stage(pipeline.id, stage)

        assert result is True
        assert len(pipeline.stages) == 2

    def test_add_stage_at_position(self, manager):
        """Test adding stage at specific position."""
        pipeline = manager.configure_pipeline(
            environment="dev",
            stages=["build", "deploy"],
        )

        stage = PipelineStage(name="test", order=2)
        manager.add_stage(pipeline.id, stage, position=1)

        assert pipeline.stages[1].name == "test"

    def test_add_stage_not_found(self, manager):
        """Test adding stage to non-existent pipeline."""
        stage = PipelineStage(name="test", order=1)
        result = manager.add_stage("nonexistent", stage)
        assert result is False

    def test_remove_stage(self, manager):
        """Test removing a stage from pipeline."""
        pipeline = manager.configure_pipeline(environment="dev")
        original_count = len(pipeline.stages)

        result = manager.remove_stage(pipeline.id, "security-scan")

        assert result is True
        assert len(pipeline.stages) == original_count - 1

    def test_remove_stage_not_found(self, manager):
        """Test removing non-existent stage."""
        pipeline = manager.configure_pipeline(environment="dev")

        result = manager.remove_stage(pipeline.id, "nonexistent")
        assert result is False

    def test_create_environment_pipeline_development(self, manager):
        """Test creating pipeline for development tier."""
        pipeline = manager.create_environment_pipeline("dev", "development")

        assert pipeline.environment == "dev"
        stage_names = [s.name for s in pipeline.stages]
        assert "build" in stage_names
        assert "unit-tests" in stage_names
        assert "deploy" in stage_names
        assert len(pipeline.gates) == 0

    def test_create_environment_pipeline_test(self, manager):
        """Test creating pipeline for test tier."""
        pipeline = manager.create_environment_pipeline("test", "test")

        stage_names = [s.name for s in pipeline.stages]
        assert "integration-tests" in stage_names
        assert len(pipeline.gates) == 1
        assert pipeline.gates[0].gate_type == GateType.AUTOMATED

    def test_create_environment_pipeline_preprod(self, manager):
        """Test creating pipeline for pre-prod tier."""
        pipeline = manager.create_environment_pipeline("preprod", "pre_prod")

        stage_names = [s.name for s in pipeline.stages]
        assert "security-scan" in stage_names
        assert len(pipeline.gates) == 2
        # Should have manual and approval gates
        gate_types = [g.gate_type for g in pipeline.gates]
        assert GateType.MANUAL in gate_types
        assert GateType.APPROVAL in gate_types

    def test_get_pipeline_metrics(self, manager):
        """Test getting pipeline metrics."""
        pipeline = manager.configure_pipeline(environment="dev")
        run1 = manager.trigger(pipeline.id)
        run2 = manager.trigger(pipeline.id)
        manager.complete_run(run1.id, PipelineStatus.SUCCESS)
        manager.complete_run(run2.id, PipelineStatus.FAILED)

        metrics = manager.get_pipeline_metrics(pipeline.id)

        assert metrics["pipeline_id"] == pipeline.id
        assert metrics["total_runs"] == 2
        assert metrics["successful_runs"] == 1
        assert metrics["failed_runs"] == 1
        assert metrics["success_rate"] == 0.5

    def test_get_pipeline_metrics_not_found(self, manager):
        """Test metrics for non-existent pipeline."""
        metrics = manager.get_pipeline_metrics("nonexistent")
        assert "error" in metrics
