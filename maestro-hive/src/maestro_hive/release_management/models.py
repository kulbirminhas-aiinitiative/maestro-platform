"""
Data models for Release Management.

This module defines all data classes and enumerations used across the
release management components.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class EnvironmentTier(Enum):
    """Defines the environment tiers in the deployment pipeline."""
    DEVELOPMENT = "development"
    TEST = "test"
    PRE_PROD = "pre_prod"
    PRODUCTION = "production"

    def can_promote_to(self, target: "EnvironmentTier") -> bool:
        """Check if promotion to target tier is allowed."""
        promotion_order = [
            EnvironmentTier.DEVELOPMENT,
            EnvironmentTier.TEST,
            EnvironmentTier.PRE_PROD,
            EnvironmentTier.PRODUCTION,
        ]
        try:
            current_idx = promotion_order.index(self)
            target_idx = promotion_order.index(target)
            return target_idx == current_idx + 1
        except ValueError:
            return False


class EnvironmentStatus(Enum):
    """Status of an environment."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    DEPLOYING = "deploying"
    MAINTENANCE = "maintenance"


class BranchType(Enum):
    """Types of branches in the branching strategy."""
    MAIN = "main"
    DEVELOP = "develop"
    STABLE_DEMO = "stable_demo"
    WORKING_BETA = "working_beta"
    FEATURE = "feature"
    RELEASE = "release"
    HOTFIX = "hotfix"


class MergeStrategy(Enum):
    """Git merge strategies."""
    MERGE = "merge"
    SQUASH = "squash"
    REBASE = "rebase"
    FAST_FORWARD = "fast_forward"


class GateType(Enum):
    """Types of deployment gates."""
    MANUAL = "manual"
    AUTOMATED = "automated"
    SCHEDULED = "scheduled"
    APPROVAL = "approval"


class PipelineStatus(Enum):
    """Status of a pipeline run."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_APPROVAL = "waiting_approval"


@dataclass
class EnvironmentConfig:
    """Configuration for an environment."""
    cpu: str = "1000m"
    memory: str = "1Gi"
    replicas: int = 1
    auto_deploy: bool = False
    require_approval: bool = False
    approvers: List[str] = field(default_factory=list)
    data_source: str = "synthetic"
    mask_pii: bool = True
    refresh_daily: bool = False
    max_age_days: Optional[int] = None
    custom_config: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> bool:
        """Validate configuration values."""
        if self.replicas < 1:
            logger.error("Replicas must be at least 1")
            return False
        if self.require_approval and not self.approvers:
            logger.error("Approvers required when approval is enabled")
            return False
        return True


@dataclass
class Environment:
    """Represents a deployment environment."""
    name: str
    tier: EnvironmentTier
    config: EnvironmentConfig
    status: EnvironmentStatus = EnvironmentStatus.HEALTHY
    current_version: Optional[str] = None
    deployed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_healthy(self) -> bool:
        """Check if environment is healthy."""
        return self.status == EnvironmentStatus.HEALTHY

    def can_accept_deployment(self) -> bool:
        """Check if environment can accept a new deployment."""
        return self.status in [EnvironmentStatus.HEALTHY, EnvironmentStatus.DEGRADED]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "tier": self.tier.value,
            "status": self.status.value,
            "current_version": self.current_version,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
            "config": {
                "cpu": self.config.cpu,
                "memory": self.config.memory,
                "replicas": self.config.replicas,
            },
        }


@dataclass
class ProtectionRules:
    """Branch protection rules."""
    require_reviews: int = 1
    require_ci: bool = True
    require_signed: bool = False
    prevent_force_push: bool = True
    restrict_push: List[str] = field(default_factory=list)
    require_linear_history: bool = False
    allow_deletions: bool = False
    require_status_checks: List[str] = field(default_factory=list)

    def is_strict(self) -> bool:
        """Check if protection rules are strict."""
        return (
            self.require_reviews >= 2 and
            self.require_ci and
            self.prevent_force_push and
            self.require_linear_history
        )


@dataclass
class Branch:
    """Represents a Git branch."""
    name: str
    branch_type: BranchType
    source_branch: Optional[str] = None
    protection_rules: Optional[ProtectionRules] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_commit: Optional[str] = None
    last_commit_at: Optional[datetime] = None
    is_protected: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_full_name(self) -> str:
        """Get full branch name with type prefix."""
        if self.branch_type == BranchType.FEATURE:
            return f"feature/{self.name}"
        elif self.branch_type == BranchType.RELEASE:
            return f"release/{self.name}"
        elif self.branch_type == BranchType.HOTFIX:
            return f"hotfix/{self.name}"
        return self.name


@dataclass
class MergeResult:
    """Result of a merge operation."""
    success: bool
    source_branch: str
    target_branch: str
    commit_sha: Optional[str] = None
    strategy_used: MergeStrategy = MergeStrategy.MERGE
    conflicts: List[str] = field(default_factory=list)
    error: Optional[str] = None
    merged_at: Optional[datetime] = None


@dataclass
class PipelineStage:
    """A stage in a CI/CD pipeline."""
    name: str
    order: int
    timeout_minutes: int = 30
    allow_failure: bool = False
    dependencies: List[str] = field(default_factory=list)
    environment_variables: Dict[str, str] = field(default_factory=dict)
    scripts: List[str] = field(default_factory=list)
    artifacts: List[str] = field(default_factory=list)


@dataclass
class DeploymentGate:
    """A deployment gate in a pipeline."""
    name: str
    gate_type: GateType
    approvers: List[str] = field(default_factory=list)
    timeout_hours: int = 24
    conditions: Dict[str, Any] = field(default_factory=dict)
    auto_approve_conditions: Dict[str, Any] = field(default_factory=dict)

    def requires_manual_approval(self) -> bool:
        """Check if gate requires manual approval."""
        return self.gate_type in [GateType.MANUAL, GateType.APPROVAL]


@dataclass
class Pipeline:
    """CI/CD pipeline configuration."""
    id: str
    name: str
    environment: str
    stages: List[PipelineStage] = field(default_factory=list)
    gates: List[DeploymentGate] = field(default_factory=list)
    triggers: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def get_stage(self, name: str) -> Optional[PipelineStage]:
        """Get stage by name."""
        for stage in self.stages:
            if stage.name == name:
                return stage
        return None

    def add_gate_after_stage(self, stage_name: str, gate: DeploymentGate) -> bool:
        """Add a gate after a specific stage."""
        for i, stage in enumerate(self.stages):
            if stage.name == stage_name:
                self.gates.append(gate)
                logger.info(f"Added gate '{gate.name}' after stage '{stage_name}'")
                return True
        logger.warning(f"Stage '{stage_name}' not found in pipeline")
        return False


@dataclass
class PipelineRun:
    """A single run of a pipeline."""
    id: str
    pipeline_id: str
    status: PipelineStatus = PipelineStatus.PENDING
    version: Optional[str] = None
    trigger: str = "manual"
    current_stage: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    artifacts: List[str] = field(default_factory=list)
    logs_url: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def duration_seconds(self) -> Optional[float]:
        """Get run duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class PromotionResult:
    """Result of an environment promotion."""
    success: bool
    from_environment: str
    to_environment: str
    version: str
    deployment_id: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    tests_passed: Optional[int] = None
    tests_failed: Optional[int] = None
    approval_required: bool = False
    approved_by: Optional[str] = None
    error: Optional[str] = None
    rollback_available: bool = True


@dataclass
class RollbackResult:
    """Result of a rollback operation."""
    success: bool
    environment: str
    from_version: str
    to_version: str
    rollback_id: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    reason: Optional[str] = None
    error: Optional[str] = None
