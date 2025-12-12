"""Tests for PromotionService."""

import pytest
from datetime import datetime

from maestro_hive.release_management.promotion import PromotionService
from maestro_hive.release_management.environments import EnvironmentManager
from maestro_hive.release_management.pipelines import PipelineManager
from maestro_hive.release_management.models import (
    EnvironmentTier,
    DeploymentGate,
    GateType,
)


class TestPromotionService:
    """Tests for PromotionService class."""

    @pytest.fixture
    def env_manager(self):
        """Create an EnvironmentManager with default environments."""
        manager = EnvironmentManager()
        manager.create_environment("dev", EnvironmentTier.DEVELOPMENT)
        manager.create_environment("test", EnvironmentTier.TEST)
        manager.create_environment("preprod", EnvironmentTier.PRE_PROD)
        manager.deploy("dev", "1.0.0")
        return manager

    @pytest.fixture
    def pipeline_manager(self):
        """Create a PipelineManager."""
        return PipelineManager()

    @pytest.fixture
    def service(self, env_manager, pipeline_manager):
        """Create a PromotionService."""
        return PromotionService(env_manager, pipeline_manager)

    def test_init(self, service):
        """Test service initialization."""
        assert service is not None
        assert len(service._promotion_history) == 0
        assert len(service._pending_approvals) == 0

    def test_promote_success(self, service):
        """Test successful promotion."""
        result = service.promote("dev", "test")

        assert result.success is True
        assert result.from_environment == "dev"
        assert result.to_environment == "test"
        assert result.version == "1.0.0"

    def test_promote_with_version(self, service):
        """Test promotion with specific version."""
        result = service.promote("dev", "test", version="2.0.0")

        assert result.success is True
        assert result.version == "2.0.0"

    def test_promote_source_not_found(self, service):
        """Test promotion with non-existent source."""
        result = service.promote("nonexistent", "test")

        assert result.success is False
        assert "not found" in result.error

    def test_promote_target_not_found(self, service):
        """Test promotion with non-existent target."""
        result = service.promote("dev", "nonexistent")

        assert result.success is False
        assert "not found" in result.error

    def test_promote_no_version(self, service, env_manager):
        """Test promotion when no version deployed."""
        env_manager.create_environment("dev2", EnvironmentTier.DEVELOPMENT)

        result = service.promote("dev2", "test")

        assert result.success is False
        assert "No version" in result.error

    def test_promote_invalid_path(self, service):
        """Test promotion via invalid path."""
        # dev -> preprod is not valid (skips test)
        result = service.promote("dev", "preprod")

        assert result.success is False
        assert "Invalid promotion path" in result.error

    def test_promote_skip_tests(self, service):
        """Test promotion skipping tests."""
        result = service.promote("dev", "test", skip_tests=True)

        assert result.success is True
        assert result.tests_passed == 100
        assert result.tests_failed == 0

    def test_promote_with_manual_gate(self, service, pipeline_manager):
        """Test promotion requiring manual approval."""
        # Create pipeline with manual gate
        pipeline = pipeline_manager.configure_pipeline(environment="test")
        gate = DeploymentGate(
            name="qa-approval",
            gate_type=GateType.MANUAL,
            approvers=["qa-lead"],
        )
        pipeline_manager.add_gate(pipeline.id, gate)

        result = service.promote("dev", "test")

        assert result.success is False
        assert result.approval_required is True
        assert "Awaiting approval" in result.error

    def test_promote_auto_approve(self, service, pipeline_manager):
        """Test promotion with auto-approve bypassing gates."""
        # Create pipeline with manual gate
        pipeline = pipeline_manager.configure_pipeline(environment="test")
        gate = DeploymentGate(
            name="qa-approval",
            gate_type=GateType.MANUAL,
            approvers=["qa-lead"],
        )
        pipeline_manager.add_gate(pipeline.id, gate)

        result = service.promote("dev", "test", auto_approve=True)

        assert result.success is True

    def test_approve_promotion(self, service, pipeline_manager):
        """Test approving a pending promotion."""
        # Create pipeline with manual gate
        pipeline = pipeline_manager.configure_pipeline(environment="test")
        gate = DeploymentGate(
            name="qa-approval",
            gate_type=GateType.MANUAL,
            approvers=["qa-lead"],
        )
        pipeline_manager.add_gate(pipeline.id, gate)

        # Trigger promotion (will be pending)
        pending_result = service.promote("dev", "test")
        approval_id = pending_result.error.split("ID: ")[1].strip(")")

        # Approve
        result = service.approve_promotion(approval_id, "qa-lead")

        assert result.success is True
        assert result.approved_by == "qa-lead"

    def test_approve_nonexistent(self, service):
        """Test approving non-existent approval."""
        result = service.approve_promotion("nonexistent", "approver")

        assert result.success is False
        assert "not found" in result.error

    def test_reject_promotion(self, service, pipeline_manager):
        """Test rejecting a pending promotion."""
        # Create pipeline with manual gate
        pipeline = pipeline_manager.configure_pipeline(environment="test")
        gate = DeploymentGate(
            name="qa-approval",
            gate_type=GateType.MANUAL,
            approvers=["qa-lead"],
        )
        pipeline_manager.add_gate(pipeline.id, gate)

        # Trigger promotion (will be pending)
        pending_result = service.promote("dev", "test")
        approval_id = pending_result.error.split("ID: ")[1].strip(")")

        # Reject
        result = service.reject_promotion(
            approval_id,
            "qa-lead",
            reason="Quality issues found",
        )

        assert result is True

    def test_reject_nonexistent(self, service):
        """Test rejecting non-existent approval."""
        result = service.reject_promotion("nonexistent", "rejector")
        assert result is False

    def test_rollback(self, service, env_manager):
        """Test rollback operation."""
        # Deploy multiple versions
        env_manager.deploy("test", "1.0.0")
        env_manager.deploy("test", "1.1.0")

        result = service.rollback("test")

        assert result.success is True
        assert result.to_version == "1.0.0"

    def test_rollback_with_version(self, service, env_manager):
        """Test rollback to specific version."""
        env_manager.deploy("test", "1.0.0")
        env_manager.deploy("test", "1.1.0")
        env_manager.deploy("test", "1.2.0")

        result = service.rollback("test", target_version="1.0.0")

        assert result.success is True
        assert result.to_version == "1.0.0"

    def test_rollback_with_reason(self, service, env_manager):
        """Test rollback with reason."""
        env_manager.deploy("test", "1.0.0")
        env_manager.deploy("test", "1.1.0")

        result = service.rollback("test", reason="Critical bug found")

        assert result.success is True
        assert result.reason == "Critical bug found"

    def test_get_promotion_status(self, service):
        """Test getting promotion status."""
        status = service.get_promotion_status("dev", "test")

        assert status["from_environment"]["name"] == "dev"
        assert status["to_environment"]["name"] == "test"
        assert status["can_promote"] is True

    def test_get_promotion_status_invalid_envs(self, service):
        """Test promotion status with invalid environments."""
        status = service.get_promotion_status("nonexistent", "test")

        assert "error" in status
        assert status["can_promote"] is False

    def test_get_promotion_status_with_pending(self, service, pipeline_manager):
        """Test promotion status with pending approval."""
        # Create pipeline with manual gate
        pipeline = pipeline_manager.configure_pipeline(environment="test")
        gate = DeploymentGate(
            name="qa-approval",
            gate_type=GateType.MANUAL,
            approvers=["qa-lead"],
        )
        pipeline_manager.add_gate(pipeline.id, gate)

        # Create pending approval
        service.promote("dev", "test")

        status = service.get_promotion_status("dev", "test")

        assert status["pending_approval"] is not None
        assert "approval_id" in status["pending_approval"]

    def test_get_promotion_history(self, service):
        """Test getting promotion history."""
        # Perform some promotions
        service.promote("dev", "test", auto_approve=True)
        service.promote("dev", "test", version="1.1.0", auto_approve=True)

        history = service.get_promotion_history()

        assert len(history) == 2

    def test_get_promotion_history_filtered(self, service, env_manager):
        """Test promotion history filtered by environment."""
        env_manager.deploy("test", "1.0.0")

        service.promote("dev", "test", auto_approve=True)
        service.promote("test", "preprod", auto_approve=True)

        history = service.get_promotion_history(environment="test")

        # Should include both (test as source and target)
        assert len(history) == 2

    def test_get_promotion_history_limit(self, service):
        """Test promotion history with limit."""
        for i in range(10):
            service.promote("dev", "test", version=f"1.0.{i}", auto_approve=True)

        history = service.get_promotion_history(limit=5)

        assert len(history) == 5

    def test_get_pending_approvals(self, service, pipeline_manager):
        """Test getting all pending approvals."""
        # Create pipelines with manual gates
        for env in ["test", "preprod"]:
            pipeline = pipeline_manager.configure_pipeline(environment=env)
            gate = DeploymentGate(
                name="approval",
                gate_type=GateType.MANUAL,
                approvers=["lead"],
            )
            pipeline_manager.add_gate(pipeline.id, gate)

        service.promote("dev", "test")

        pending = service.get_pending_approvals()

        assert len(pending) == 1
        assert pending[0]["to_environment"] == "test"

    def test_validate_promotion_path_valid(self, service):
        """Test validating valid promotion path."""
        validation = service.validate_promotion_path("dev", "test")

        assert validation["valid"] is True
        assert len(validation["issues"]) == 0

    def test_validate_promotion_path_invalid(self, service):
        """Test validating invalid promotion path."""
        validation = service.validate_promotion_path("dev", "preprod")

        assert validation["valid"] is False
        assert len(validation["issues"]) > 0

    def test_validate_promotion_path_no_version(self, service, env_manager):
        """Test validation when no version deployed."""
        env_manager.create_environment("dev2", EnvironmentTier.DEVELOPMENT)

        validation = service.validate_promotion_path("dev2", "test")

        assert validation["valid"] is False
        assert any("No version" in issue for issue in validation["issues"])

    def test_create_promotion_workflow(self, service):
        """Test creating promotion workflow."""
        workflow = service.create_promotion_workflow(
            version="1.0.0",
            target_tier=EnvironmentTier.PRE_PROD,
        )

        assert workflow["version"] == "1.0.0"
        assert workflow["target_tier"] == "pre_prod"
        assert len(workflow["steps"]) == 3  # dev -> test -> preprod

    def test_create_promotion_workflow_to_test(self, service):
        """Test creating workflow to test tier."""
        workflow = service.create_promotion_workflow(
            version="1.0.0",
            target_tier=EnvironmentTier.TEST,
        )

        assert len(workflow["steps"]) == 2  # dev -> test

    def test_workflow_steps_structure(self, service):
        """Test workflow steps have correct structure."""
        workflow = service.create_promotion_workflow(
            version="1.0.0",
            target_tier=EnvironmentTier.PRE_PROD,
        )

        # First step is deploy
        assert workflow["steps"][0]["action"] == "deploy"
        assert workflow["steps"][0]["tier"] == "development"

        # Subsequent steps are promote
        for step in workflow["steps"][1:]:
            assert step["action"] == "promote"
            assert "from_environment" in step
            assert "to_environment" in step

    def test_workflow_approval_requirements(self, service):
        """Test workflow identifies approval requirements."""
        workflow = service.create_promotion_workflow(
            version="1.0.0",
            target_tier=EnvironmentTier.PRE_PROD,
        )

        # Pre-prod step should require approval
        preprod_step = [s for s in workflow["steps"] if s["tier"] == "pre_prod"][0]
        assert preprod_step["requires_approval"] is True

    def test_promotion_records_in_history(self, service):
        """Test that promotions are recorded in history."""
        initial_count = len(service._promotion_history)

        service.promote("dev", "test", auto_approve=True)

        assert len(service._promotion_history) == initial_count + 1

    def test_promotion_result_has_deployment_id(self, service):
        """Test promotion result includes deployment ID."""
        result = service.promote("dev", "test", auto_approve=True)

        assert result.success is True
        assert result.deployment_id is not None

    def test_promotion_test_results(self, service):
        """Test promotion includes test results."""
        result = service.promote("dev", "test", auto_approve=True)

        assert result.tests_passed is not None
        assert result.tests_failed is not None
        assert result.tests_failed == 0
