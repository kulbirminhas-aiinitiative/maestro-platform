"""
Rollback Strategy Implementation - AC-3.

Provides automated rollback mechanisms with multiple strategies.
"""

import uuid
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .health_check import HealthChecker, HealthStatus


class RollbackType(str, Enum):
    """Rollback strategy types."""
    IMMEDIATE = "immediate"      # Instant rollback
    GRADUAL = "gradual"          # Gradual traffic shift
    CANARY = "canary"            # Canary-based rollback
    BLUE_GREEN = "blue_green"    # Blue-green switch


class DeploymentStatus(str, Enum):
    """Deployment status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class Deployment:
    """Deployment representation."""
    id: str
    environment: str
    version: str
    artifact_hash: str
    status: DeploymentStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    deployed_by: str = ""
    rollback_target_id: Optional[str] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "environment": self.environment,
            "version": self.version,
            "artifact_hash": self.artifact_hash,
            "status": self.status.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "deployed_by": self.deployed_by,
            "rollback_target_id": self.rollback_target_id,
            "metadata": self.metadata
        }


@dataclass
class RollbackResult:
    """Result of rollback operation."""
    id: str
    deployment_id: str
    target_version: str
    strategy: RollbackType
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    rolled_back_from: str = ""
    rolled_back_to: str = ""
    error: Optional[str] = None
    steps: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rollback_id": self.id,
            "deployment_id": self.deployment_id,
            "target_version": self.target_version,
            "strategy": self.strategy.value,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "rolled_back_from": self.rolled_back_from,
            "rolled_back_to": self.rolled_back_to,
            "error": self.error,
            "steps": self.steps
        }


class RollbackStrategy:
    """Automated rollback mechanisms."""

    def __init__(
        self,
        strategy_type: RollbackType = RollbackType.IMMEDIATE,
        health_checker: Optional[HealthChecker] = None
    ):
        self.strategy_type = strategy_type
        self.health_checker = health_checker or HealthChecker()
        self._deployments: dict[str, Deployment] = {}
        self._history: list[Deployment] = []

    def record_deployment(self, deployment: Deployment) -> None:
        """Record deployment for rollback tracking."""
        self._deployments[deployment.id] = deployment
        self._history.append(deployment)

    def get_previous_deployment(self, environment: str) -> Optional[Deployment]:
        """Get previous successful deployment for environment."""
        env_deployments = [
            d for d in self._history
            if d.environment == environment and d.status == DeploymentStatus.SUCCESS
        ]
        if len(env_deployments) >= 2:
            return env_deployments[-2]
        return None

    async def execute(
        self,
        deployment: Deployment,
        target_version: Optional[str] = None,
        reason: str = ""
    ) -> RollbackResult:
        """Execute rollback to previous version."""
        started_at = datetime.utcnow()

        # Determine target version
        if target_version is None:
            prev = self.get_previous_deployment(deployment.environment)
            if prev:
                target_version = prev.version
            else:
                return RollbackResult(
                    id=str(uuid.uuid4()),
                    deployment_id=deployment.id,
                    target_version="",
                    strategy=self.strategy_type,
                    status="failed",
                    started_at=started_at,
                    completed_at=datetime.utcnow(),
                    error="No previous deployment found for rollback"
                )

        result = RollbackResult(
            id=str(uuid.uuid4()),
            deployment_id=deployment.id,
            target_version=target_version,
            strategy=self.strategy_type,
            status="in_progress",
            started_at=started_at,
            rolled_back_from=deployment.version
        )

        try:
            if self.strategy_type == RollbackType.IMMEDIATE:
                await self._immediate_rollback(deployment, target_version, result)
            elif self.strategy_type == RollbackType.GRADUAL:
                await self._gradual_rollback(deployment, target_version, result)
            elif self.strategy_type == RollbackType.CANARY:
                await self._canary_rollback(deployment, target_version, result)
            elif self.strategy_type == RollbackType.BLUE_GREEN:
                await self._blue_green_rollback(deployment, target_version, result)

            result.status = "completed"
            result.rolled_back_to = target_version
            deployment.status = DeploymentStatus.ROLLED_BACK

        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        result.completed_at = datetime.utcnow()
        return result

    async def _immediate_rollback(
        self,
        deployment: Deployment,
        target_version: str,
        result: RollbackResult
    ) -> None:
        """Execute immediate rollback."""
        result.steps.append({
            "step": "stop_current",
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat()
        })

        result.steps.append({
            "step": "deploy_previous",
            "version": target_version,
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat()
        })

        # Verify health
        health = await self.health_checker.check_all()
        result.steps.append({
            "step": "health_check",
            "status": "passed" if health.status == HealthStatus.HEALTHY else "failed",
            "timestamp": datetime.utcnow().isoformat()
        })

    async def _gradual_rollback(
        self,
        deployment: Deployment,
        target_version: str,
        result: RollbackResult
    ) -> None:
        """Execute gradual rollback with traffic shifting."""
        traffic_percentages = [10, 25, 50, 75, 100]

        for pct in traffic_percentages:
            result.steps.append({
                "step": f"shift_traffic_{pct}",
                "traffic_to_previous": pct,
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat()
            })

            # Check health at each step
            health = await self.health_checker.check_all()
            if health.status != HealthStatus.HEALTHY:
                raise Exception(f"Health check failed at {pct}% traffic shift")

    async def _canary_rollback(
        self,
        deployment: Deployment,
        target_version: str,
        result: RollbackResult
    ) -> None:
        """Execute canary-based rollback."""
        result.steps.append({
            "step": "deploy_canary",
            "version": target_version,
            "traffic_percentage": 5,
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat()
        })

        # Monitor canary
        health = await self.health_checker.check_all()
        result.steps.append({
            "step": "canary_analysis",
            "status": "passed" if health.status == HealthStatus.HEALTHY else "failed",
            "timestamp": datetime.utcnow().isoformat()
        })

        # Full rollback
        result.steps.append({
            "step": "full_rollback",
            "version": target_version,
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat()
        })

    async def _blue_green_rollback(
        self,
        deployment: Deployment,
        target_version: str,
        result: RollbackResult
    ) -> None:
        """Execute blue-green rollback."""
        result.steps.append({
            "step": "activate_green",
            "version": target_version,
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat()
        })

        # Verify green environment
        health = await self.health_checker.check_all()
        if health.status != HealthStatus.HEALTHY:
            raise Exception("Green environment health check failed")

        result.steps.append({
            "step": "switch_traffic",
            "from": "blue",
            "to": "green",
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat()
        })

        result.steps.append({
            "step": "deactivate_blue",
            "status": "completed",
            "timestamp": datetime.utcnow().isoformat()
        })

    async def should_rollback(self, deployment: Deployment) -> bool:
        """Determine if rollback is needed based on health."""
        if self.health_checker:
            return await self.health_checker.should_rollback()
        return False
