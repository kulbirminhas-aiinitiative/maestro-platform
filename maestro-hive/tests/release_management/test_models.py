"""Tests for Release Management models."""

import pytest
from datetime import datetime

from maestro_hive.release_management.models import (
    Environment,
    EnvironmentConfig,
    EnvironmentTier,
    EnvironmentStatus,
    Branch,
    BranchType,
    ProtectionRules,
    MergeStrategy,
    MergeResult,
    Pipeline,
    PipelineStage,
    PipelineStatus,
    PipelineRun,
    DeploymentGate,
    GateType,
    PromotionResult,
    RollbackResult,
)


class TestEnvironmentTier:
    """Tests for EnvironmentTier enum."""

    def test_tier_values(self):
        """Test environment tier values."""
        assert EnvironmentTier.DEVELOPMENT.value == "development"
        assert EnvironmentTier.TEST.value == "test"
        assert EnvironmentTier.PRE_PROD.value == "pre_prod"
        assert EnvironmentTier.PRODUCTION.value == "production"

    def test_can_promote_to_valid_paths(self):
        """Test valid promotion paths."""
        # Dev -> Test
        assert EnvironmentTier.DEVELOPMENT.can_promote_to(EnvironmentTier.TEST)
        # Test -> Pre-Prod
        assert EnvironmentTier.TEST.can_promote_to(EnvironmentTier.PRE_PROD)
        # Pre-Prod -> Production
        assert EnvironmentTier.PRE_PROD.can_promote_to(EnvironmentTier.PRODUCTION)

    def test_can_promote_to_invalid_paths(self):
        """Test invalid promotion paths."""
        # Dev -> Pre-Prod (skip)
        assert not EnvironmentTier.DEVELOPMENT.can_promote_to(EnvironmentTier.PRE_PROD)
        # Dev -> Production (skip)
        assert not EnvironmentTier.DEVELOPMENT.can_promote_to(EnvironmentTier.PRODUCTION)
        # Test -> Production (skip)
        assert not EnvironmentTier.TEST.can_promote_to(EnvironmentTier.PRODUCTION)
        # Production -> any (can't promote from production)
        assert not EnvironmentTier.PRODUCTION.can_promote_to(EnvironmentTier.DEVELOPMENT)

    def test_cannot_promote_to_same_tier(self):
        """Test cannot promote to same tier."""
        assert not EnvironmentTier.DEVELOPMENT.can_promote_to(EnvironmentTier.DEVELOPMENT)
        assert not EnvironmentTier.TEST.can_promote_to(EnvironmentTier.TEST)


class TestEnvironmentConfig:
    """Tests for EnvironmentConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = EnvironmentConfig()
        assert config.cpu == "1000m"
        assert config.memory == "1Gi"
        assert config.replicas == 1
        assert config.auto_deploy is False
        assert config.require_approval is False
        assert config.data_source == "synthetic"
        assert config.mask_pii is True  # Default is True for security

    def test_custom_values(self):
        """Test custom configuration values."""
        config = EnvironmentConfig(
            cpu="2000m",
            memory="4Gi",
            replicas=3,
            auto_deploy=True,
            require_approval=True,
            approvers=["qa-lead"],
            data_source="production_snapshot",
            mask_pii=True,
        )
        assert config.cpu == "2000m"
        assert config.replicas == 3
        assert config.approvers == ["qa-lead"]

    def test_validate_valid_config(self):
        """Test validation passes for valid config."""
        config = EnvironmentConfig(replicas=2)
        assert config.validate() is True

    def test_validate_invalid_replicas(self):
        """Test validation fails for invalid replicas."""
        config = EnvironmentConfig(replicas=0)
        assert config.validate() is False

        config = EnvironmentConfig(replicas=-1)
        assert config.validate() is False


class TestEnvironment:
    """Tests for Environment dataclass."""

    def test_environment_creation(self):
        """Test environment creation."""
        config = EnvironmentConfig()
        env = Environment(
            name="dev-1",
            tier=EnvironmentTier.DEVELOPMENT,
            config=config,
        )
        assert env.name == "dev-1"
        assert env.tier == EnvironmentTier.DEVELOPMENT
        assert env.status == EnvironmentStatus.HEALTHY

    def test_is_healthy(self):
        """Test is_healthy method."""
        env = Environment(
            name="test",
            tier=EnvironmentTier.TEST,
            config=EnvironmentConfig(),
            status=EnvironmentStatus.HEALTHY,
        )
        assert env.is_healthy() is True

        env.status = EnvironmentStatus.DEGRADED
        assert env.is_healthy() is False

    def test_can_accept_deployment(self):
        """Test can_accept_deployment method."""
        env = Environment(
            name="test",
            tier=EnvironmentTier.TEST,
            config=EnvironmentConfig(),
            status=EnvironmentStatus.HEALTHY,
        )
        assert env.can_accept_deployment() is True

        env.status = EnvironmentStatus.DEPLOYING
        assert env.can_accept_deployment() is False

        env.status = EnvironmentStatus.UNHEALTHY
        assert env.can_accept_deployment() is False


class TestBranchType:
    """Tests for BranchType enum."""

    def test_branch_type_values(self):
        """Test branch type values."""
        assert BranchType.MAIN.value == "main"
        assert BranchType.DEVELOP.value == "develop"
        assert BranchType.FEATURE.value == "feature"
        assert BranchType.RELEASE.value == "release"
        assert BranchType.HOTFIX.value == "hotfix"
        assert BranchType.STABLE_DEMO.value == "stable_demo"
        assert BranchType.WORKING_BETA.value == "working_beta"


class TestProtectionRules:
    """Tests for ProtectionRules dataclass."""

    def test_default_values(self):
        """Test default protection rules."""
        rules = ProtectionRules()
        assert rules.require_reviews == 1
        assert rules.require_ci is True
        assert rules.require_signed is False
        assert rules.prevent_force_push is True

    def test_custom_rules(self):
        """Test custom protection rules."""
        rules = ProtectionRules(
            require_reviews=2,
            require_ci=True,
            require_signed=True,
            prevent_force_push=True,
            require_linear_history=True,
        )
        assert rules.require_reviews == 2
        assert rules.require_linear_history is True


class TestBranch:
    """Tests for Branch dataclass."""

    def test_branch_creation(self):
        """Test branch creation."""
        branch = Branch(
            name="feature/test",
            branch_type=BranchType.FEATURE,
            source_branch="develop",
        )
        assert branch.name == "feature/test"
        assert branch.branch_type == BranchType.FEATURE
        assert branch.is_protected is False

    def test_protected_branch(self):
        """Test protected branch creation."""
        rules = ProtectionRules(require_reviews=2)
        branch = Branch(
            name="main",
            branch_type=BranchType.MAIN,
            is_protected=True,
            protection_rules=rules,
        )
        assert branch.is_protected is True
        assert branch.protection_rules.require_reviews == 2


class TestPipelineStage:
    """Tests for PipelineStage dataclass."""

    def test_stage_creation(self):
        """Test stage creation."""
        stage = PipelineStage(
            name="build",
            order=1,
            scripts=["npm install", "npm run build"],
        )
        assert stage.name == "build"
        assert stage.order == 1
        assert len(stage.scripts) == 2

    def test_stage_with_dependencies(self):
        """Test stage with dependencies."""
        stage = PipelineStage(
            name="test",
            order=2,
            dependencies=["build"],
            scripts=["npm test"],
        )
        assert stage.dependencies == ["build"]


class TestDeploymentGate:
    """Tests for DeploymentGate dataclass."""

    def test_manual_gate(self):
        """Test manual gate creation."""
        gate = DeploymentGate(
            name="qa-approval",
            gate_type=GateType.MANUAL,
            approvers=["qa-lead"],
            timeout_hours=24,
        )
        assert gate.name == "qa-approval"
        assert gate.gate_type == GateType.MANUAL
        assert gate.requires_manual_approval() is True

    def test_automated_gate(self):
        """Test automated gate creation."""
        gate = DeploymentGate(
            name="security-scan",
            gate_type=GateType.AUTOMATED,
            conditions={"no_critical_vulnerabilities": True},
        )
        assert gate.gate_type == GateType.AUTOMATED
        assert gate.requires_manual_approval() is False


class TestPipeline:
    """Tests for Pipeline dataclass."""

    def test_pipeline_creation(self):
        """Test pipeline creation."""
        stages = [
            PipelineStage(name="build", order=1),
            PipelineStage(name="test", order=2),
        ]
        pipeline = Pipeline(
            id="pipe-123",
            name="dev-pipeline",
            environment="dev",
            stages=stages,
        )
        assert pipeline.id == "pipe-123"
        assert len(pipeline.stages) == 2


class TestPipelineRun:
    """Tests for PipelineRun dataclass."""

    def test_run_creation(self):
        """Test pipeline run creation."""
        run = PipelineRun(
            id="run-123",
            pipeline_id="pipe-123",
            status=PipelineStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        assert run.id == "run-123"
        assert run.status == PipelineStatus.RUNNING

    def test_duration_calculation(self):
        """Test duration calculation."""
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 12, 5, 0)
        run = PipelineRun(
            id="run-123",
            pipeline_id="pipe-123",
            status=PipelineStatus.SUCCESS,
            started_at=start,
            completed_at=end,
        )
        assert run.duration_seconds() == 300  # 5 minutes

    def test_duration_no_completion(self):
        """Test duration with no completion time."""
        run = PipelineRun(
            id="run-123",
            pipeline_id="pipe-123",
            status=PipelineStatus.RUNNING,
            started_at=datetime.utcnow(),
        )
        assert run.duration_seconds() is None


class TestPromotionResult:
    """Tests for PromotionResult dataclass."""

    def test_successful_promotion(self):
        """Test successful promotion result."""
        result = PromotionResult(
            success=True,
            from_environment="dev",
            to_environment="test",
            version="1.0.0",
            deployment_id="deploy-123",
            tests_passed=100,
            tests_failed=0,
        )
        assert result.success is True
        assert result.tests_passed == 100

    def test_failed_promotion(self):
        """Test failed promotion result."""
        result = PromotionResult(
            success=False,
            from_environment="dev",
            to_environment="test",
            version="1.0.0",
            error="Target environment unhealthy",
        )
        assert result.success is False
        assert result.error == "Target environment unhealthy"


class TestRollbackResult:
    """Tests for RollbackResult dataclass."""

    def test_successful_rollback(self):
        """Test successful rollback result."""
        result = RollbackResult(
            success=True,
            environment="test",
            from_version="1.1.0",
            to_version="1.0.0",
            rollback_id="rb-123",
            reason="Regression found",
        )
        assert result.success is True
        assert result.reason == "Regression found"

    def test_failed_rollback(self):
        """Test failed rollback result."""
        result = RollbackResult(
            success=False,
            environment="test",
            from_version="1.1.0",
            to_version="1.0.0",
            error="No previous version available",
        )
        assert result.success is False
        assert result.error == "No previous version available"
