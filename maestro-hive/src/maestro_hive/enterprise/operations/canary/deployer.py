"""
Canary Deployer Implementation.

Provides canary deployment with configurable traffic splitting
and automatic rollback based on health criteria.
"""

import uuid
import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, Callable

from ..rollback.health_check import HealthChecker, HealthStatus
from .analyzer import CanaryAnalyzer, HealthCriteria, AnalysisResult


class CanaryStatus(str, Enum):
    """Canary deployment status."""
    PENDING = "pending"
    DEPLOYING = "deploying"
    ANALYZING = "analyzing"
    PROGRESSING = "progressing"
    PROMOTING = "promoting"
    ROLLING_BACK = "rolling_back"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TrafficSplit:
    """Traffic split configuration."""
    stable_weight: int = 95
    canary_weight: int = 5

    def __post_init__(self):
        if self.stable_weight + self.canary_weight != 100:
            raise ValueError("Traffic weights must sum to 100")

    def to_dict(self) -> dict[str, Any]:
        return {
            "stable_weight": self.stable_weight,
            "canary_weight": self.canary_weight,
        }


@dataclass
class CanaryConfig:
    """Canary deployment configuration."""
    initial_weight: int = 5
    increment_step: int = 10
    max_weight: int = 50
    observation_period: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    auto_promote_threshold: int = 100
    health_criteria: HealthCriteria = field(default_factory=HealthCriteria)

    def to_dict(self) -> dict[str, Any]:
        return {
            "initial_weight": self.initial_weight,
            "increment_step": self.increment_step,
            "max_weight": self.max_weight,
            "observation_period_seconds": self.observation_period.total_seconds(),
            "auto_promote_threshold": self.auto_promote_threshold,
            "health_criteria": self.health_criteria.to_dict(),
        }


@dataclass
class CanaryDeployment:
    """Canary deployment state."""
    id: str
    service: str
    stable_version: str
    canary_version: str
    status: CanaryStatus
    config: CanaryConfig
    traffic_split: TrafficSplit
    created_at: datetime
    updated_at: datetime
    analysis_results: list[AnalysisResult] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "service": self.service,
            "stable_version": self.stable_version,
            "canary_version": self.canary_version,
            "status": self.status.value,
            "config": self.config.to_dict(),
            "traffic_split": self.traffic_split.to_dict(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "analysis_results": [r.to_dict() for r in self.analysis_results],
            "events": self.events,
            "error": self.error,
        }

    def add_event(self, event_type: str, details: dict[str, Any] = None) -> None:
        """Add event to deployment history."""
        self.events.append({
            "type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "details": details or {},
        })
        self.updated_at = datetime.utcnow()


class CanaryDeployer:
    """Canary deployment with traffic splitting."""

    def __init__(
        self,
        health_checker: Optional[HealthChecker] = None,
        analyzer: Optional[CanaryAnalyzer] = None,
    ):
        self.health_checker = health_checker or HealthChecker()
        self.analyzer = analyzer or CanaryAnalyzer()
        self._deployments: dict[str, CanaryDeployment] = {}
        self._active_by_service: dict[str, str] = {}
        self._callbacks: dict[str, Callable] = {}

    async def start_canary(
        self,
        service: str,
        stable_version: str,
        canary_version: str,
        config: Optional[CanaryConfig] = None,
    ) -> CanaryDeployment:
        """Start a canary deployment."""
        config = config or CanaryConfig()

        # Check for existing canary
        if service in self._active_by_service:
            existing_id = self._active_by_service[service]
            existing = self._deployments.get(existing_id)
            if existing and existing.status not in (CanaryStatus.COMPLETED, CanaryStatus.FAILED):
                raise ValueError(f"Active canary deployment exists for {service}: {existing_id}")

        deployment = CanaryDeployment(
            id=str(uuid.uuid4()),
            service=service,
            stable_version=stable_version,
            canary_version=canary_version,
            status=CanaryStatus.PENDING,
            config=config,
            traffic_split=TrafficSplit(
                stable_weight=100 - config.initial_weight,
                canary_weight=config.initial_weight,
            ),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        deployment.add_event("created", {
            "stable_version": stable_version,
            "canary_version": canary_version,
            "initial_weight": config.initial_weight,
        })

        self._deployments[deployment.id] = deployment
        self._active_by_service[service] = deployment.id

        # Start deployment
        deployment.status = CanaryStatus.DEPLOYING
        deployment.add_event("deploying")

        # Deploy canary (simulated)
        await self._deploy_canary_instance(deployment)

        deployment.status = CanaryStatus.ANALYZING
        deployment.add_event("analyzing_started", {
            "traffic_split": deployment.traffic_split.to_dict(),
        })

        return deployment

    async def _deploy_canary_instance(self, deployment: CanaryDeployment) -> None:
        """Deploy canary instance (placeholder for actual deployment)."""
        await asyncio.sleep(0.01)  # Simulated deployment
        deployment.add_event("canary_deployed", {
            "version": deployment.canary_version,
        })

    async def analyze(self, deployment_id: str) -> AnalysisResult:
        """Run canary analysis."""
        deployment = self._get_deployment(deployment_id)

        if deployment.status != CanaryStatus.ANALYZING:
            raise ValueError(f"Cannot analyze: deployment status is {deployment.status}")

        # Run analysis
        result = await self.analyzer.analyze(
            service=deployment.service,
            stable_version=deployment.stable_version,
            canary_version=deployment.canary_version,
            criteria=deployment.config.health_criteria,
        )

        deployment.analysis_results.append(result)
        deployment.add_event("analysis_completed", result.to_dict())

        return result

    async def progress(self, deployment_id: str, weight_increase: Optional[int] = None) -> CanaryDeployment:
        """Increase canary traffic weight."""
        deployment = self._get_deployment(deployment_id)

        if deployment.status not in (CanaryStatus.ANALYZING, CanaryStatus.PROGRESSING):
            raise ValueError(f"Cannot progress: deployment status is {deployment.status}")

        # Default to config increment
        increase = weight_increase or deployment.config.increment_step
        new_canary_weight = min(
            deployment.traffic_split.canary_weight + increase,
            deployment.config.max_weight,
        )

        deployment.status = CanaryStatus.PROGRESSING
        deployment.traffic_split = TrafficSplit(
            stable_weight=100 - new_canary_weight,
            canary_weight=new_canary_weight,
        )

        deployment.add_event("traffic_increased", {
            "new_canary_weight": new_canary_weight,
            "previous_weight": new_canary_weight - increase,
        })

        # Back to analyzing
        deployment.status = CanaryStatus.ANALYZING

        return deployment

    async def promote(self, deployment_id: str) -> CanaryDeployment:
        """Promote canary to stable."""
        deployment = self._get_deployment(deployment_id)

        if deployment.status not in (CanaryStatus.ANALYZING, CanaryStatus.PROGRESSING):
            raise ValueError(f"Cannot promote: deployment status is {deployment.status}")

        deployment.status = CanaryStatus.PROMOTING
        deployment.add_event("promoting_started")

        # Shift all traffic to canary
        deployment.traffic_split = TrafficSplit(
            stable_weight=0,
            canary_weight=100,
        )

        # Scale down stable
        await self._scale_down_stable(deployment)

        deployment.status = CanaryStatus.COMPLETED
        deployment.add_event("promoted", {
            "new_stable_version": deployment.canary_version,
        })

        # Clear active
        if self._active_by_service.get(deployment.service) == deployment.id:
            del self._active_by_service[deployment.service]

        return deployment

    async def _scale_down_stable(self, deployment: CanaryDeployment) -> None:
        """Scale down stable instances (placeholder)."""
        await asyncio.sleep(0.01)
        deployment.add_event("stable_scaled_down")

    async def rollback(self, deployment_id: str, reason: str = "") -> CanaryDeployment:
        """Rollback canary deployment."""
        deployment = self._get_deployment(deployment_id)

        if deployment.status == CanaryStatus.COMPLETED:
            raise ValueError("Cannot rollback completed deployment")

        deployment.status = CanaryStatus.ROLLING_BACK
        deployment.add_event("rolling_back", {"reason": reason})

        # Shift all traffic to stable
        deployment.traffic_split = TrafficSplit(
            stable_weight=100,
            canary_weight=0,
        )

        # Remove canary instances
        await self._remove_canary_instances(deployment)

        deployment.status = CanaryStatus.FAILED
        deployment.error = reason or "Manual rollback"
        deployment.add_event("rolled_back", {"reason": reason})

        # Clear active
        if self._active_by_service.get(deployment.service) == deployment.id:
            del self._active_by_service[deployment.service]

        return deployment

    async def _remove_canary_instances(self, deployment: CanaryDeployment) -> None:
        """Remove canary instances (placeholder)."""
        await asyncio.sleep(0.01)
        deployment.add_event("canary_instances_removed")

    async def auto_rollback_check(self, deployment_id: str) -> bool:
        """Check if auto-rollback should be triggered."""
        deployment = self._get_deployment(deployment_id)

        if not deployment.analysis_results:
            return False

        latest = deployment.analysis_results[-1]
        if not latest.passed:
            await self.rollback(deployment_id, f"Auto-rollback: {latest.reason}")
            return True

        return False

    def get_deployment(self, deployment_id: str) -> Optional[CanaryDeployment]:
        """Get deployment by ID."""
        return self._deployments.get(deployment_id)

    def _get_deployment(self, deployment_id: str) -> CanaryDeployment:
        """Get deployment by ID, raising if not found."""
        deployment = self._deployments.get(deployment_id)
        if not deployment:
            raise ValueError(f"Deployment not found: {deployment_id}")
        return deployment

    def get_active_deployment(self, service: str) -> Optional[CanaryDeployment]:
        """Get active deployment for service."""
        deployment_id = self._active_by_service.get(service)
        if deployment_id:
            return self._deployments.get(deployment_id)
        return None

    def list_deployments(self, service: Optional[str] = None) -> list[CanaryDeployment]:
        """List all deployments, optionally filtered by service."""
        deployments = list(self._deployments.values())
        if service:
            deployments = [d for d in deployments if d.service == service]
        return sorted(deployments, key=lambda d: d.created_at, reverse=True)

    def get_status(self, deployment_id: str) -> dict[str, Any]:
        """Get deployment status summary."""
        deployment = self._get_deployment(deployment_id)
        return {
            "id": deployment.id,
            "service": deployment.service,
            "status": deployment.status.value,
            "stable_version": deployment.stable_version,
            "canary_version": deployment.canary_version,
            "traffic_split": deployment.traffic_split.to_dict(),
            "analysis_count": len(deployment.analysis_results),
            "last_analysis_passed": deployment.analysis_results[-1].passed if deployment.analysis_results else None,
            "created_at": deployment.created_at.isoformat(),
            "updated_at": deployment.updated_at.isoformat(),
        }
