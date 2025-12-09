"""
Environment Lifecycle Manager - AC-2 Implementation.

Manages dev, staging, and production environments.
"""

import uuid
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

from .config import EnvironmentConfig
from .promotion import PromotionPolicy, ApprovalRequirement
from .secrets import SecretManager


class EnvironmentStatus(str, Enum):
    """Environment status."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    DEPLOYING = "deploying"
    MAINTENANCE = "maintenance"
    FAILED = "failed"
    LOCKED = "locked"


class EnvironmentTier(str, Enum):
    """Environment tier/level."""
    DEV = "dev"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class Environment:
    """Environment representation."""
    id: str
    name: str
    tier: EnvironmentTier
    status: EnvironmentStatus
    config: EnvironmentConfig
    current_version: str = ""
    deployed_at: Optional[datetime] = None
    deployed_by: str = ""
    url: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "tier": self.tier.value,
            "status": self.status.value,
            "current_version": self.current_version,
            "deployed_at": self.deployed_at.isoformat() if self.deployed_at else None,
            "deployed_by": self.deployed_by,
            "url": self.url,
            "config": self.config.to_dict(),
            "metadata": self.metadata
        }


@dataclass
class PromotionResult:
    """Result of environment promotion."""
    id: str
    source: str
    target: str
    version: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    approvals: list[dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "promotion_id": self.id,
            "source_environment": self.source,
            "target_environment": self.target,
            "version": self.version,
            "status": self.status,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "approvals": self.approvals,
            "error": self.error
        }


class EnvironmentManager:
    """Manages environment lifecycle."""

    TIER_ORDER = [EnvironmentTier.DEV, EnvironmentTier.STAGING, EnvironmentTier.PRODUCTION]

    def __init__(self, secret_manager: Optional[SecretManager] = None):
        self.secret_manager = secret_manager or SecretManager()
        self._environments: dict[str, Environment] = {}
        self._promotion_policies: dict[str, PromotionPolicy] = {}
        self._promotions: dict[str, PromotionResult] = {}
        self._initialize_default_environments()

    def _initialize_default_environments(self) -> None:
        """Initialize default environment structure."""
        defaults = [
            (EnvironmentTier.DEV, "Development environment"),
            (EnvironmentTier.STAGING, "Staging environment"),
            (EnvironmentTier.PRODUCTION, "Production environment"),
        ]
        for tier, description in defaults:
            config = EnvironmentConfig(name=tier.value)
            config.set("ENVIRONMENT", tier.value)
            config.set("DESCRIPTION", description)

            env = Environment(
                id=str(uuid.uuid4()),
                name=tier.value,
                tier=tier,
                status=EnvironmentStatus.ACTIVE,
                config=config
            )
            self._environments[tier.value] = env

    async def create(self, name: str, config: EnvironmentConfig, tier: EnvironmentTier) -> Environment:
        """Create new environment."""
        if name in self._environments:
            raise ValueError(f"Environment '{name}' already exists")

        env = Environment(
            id=str(uuid.uuid4()),
            name=name,
            tier=tier,
            status=EnvironmentStatus.INACTIVE,
            config=config
        )
        self._environments[name] = env
        return env

    async def get(self, name: str) -> Optional[Environment]:
        """Get environment by name."""
        return self._environments.get(name)

    async def list(self) -> list[Environment]:
        """List all environments."""
        return list(self._environments.values())

    async def update_config(self, name: str, variables: dict[str, str]) -> Environment:
        """Update environment configuration."""
        env = self._environments.get(name)
        if not env:
            raise ValueError(f"Environment '{name}' not found")

        for key, value in variables.items():
            env.config.set(key, value)

        return env

    async def deploy(self, name: str, version: str, deployed_by: str) -> Environment:
        """Deploy version to environment."""
        env = self._environments.get(name)
        if not env:
            raise ValueError(f"Environment '{name}' not found")

        if env.status == EnvironmentStatus.LOCKED:
            raise ValueError(f"Environment '{name}' is locked")

        env.status = EnvironmentStatus.DEPLOYING
        env.current_version = version
        env.deployed_at = datetime.utcnow()
        env.deployed_by = deployed_by
        env.status = EnvironmentStatus.ACTIVE

        return env

    async def promote(
        self,
        source: str,
        target: str,
        approval_by: Optional[str] = None
    ) -> PromotionResult:
        """Promote from source to target environment."""
        source_env = self._environments.get(source)
        target_env = self._environments.get(target)

        if not source_env:
            raise ValueError(f"Source environment '{source}' not found")
        if not target_env:
            raise ValueError(f"Target environment '{target}' not found")

        # Validate tier progression
        source_idx = self.TIER_ORDER.index(source_env.tier)
        target_idx = self.TIER_ORDER.index(target_env.tier)
        if target_idx <= source_idx:
            raise ValueError("Can only promote to higher-tier environments")

        if not source_env.current_version:
            raise ValueError(f"No version deployed to '{source}'")

        # Check promotion policy
        policy = self._promotion_policies.get(target)
        if policy and policy.approval_required and not approval_by:
            result = PromotionResult(
                id=str(uuid.uuid4()),
                source=source,
                target=target,
                version=source_env.current_version,
                status="pending_approval",
                started_at=datetime.utcnow()
            )
            self._promotions[result.id] = result
            return result

        # Execute promotion
        result = PromotionResult(
            id=str(uuid.uuid4()),
            source=source,
            target=target,
            version=source_env.current_version,
            status="in_progress",
            started_at=datetime.utcnow()
        )

        if approval_by:
            result.approvals.append({
                "approved_by": approval_by,
                "approved_at": datetime.utcnow().isoformat()
            })

        try:
            target_env.current_version = source_env.current_version
            target_env.deployed_at = datetime.utcnow()
            target_env.deployed_by = approval_by or "system"
            result.status = "completed"
            result.completed_at = datetime.utcnow()
        except Exception as e:
            result.status = "failed"
            result.error = str(e)

        self._promotions[result.id] = result
        return result

    def set_promotion_policy(self, environment: str, policy: PromotionPolicy) -> None:
        """Set promotion policy for environment."""
        self._promotion_policies[environment] = policy

    async def lock(self, name: str, reason: str = "") -> Environment:
        """Lock environment to prevent changes."""
        env = self._environments.get(name)
        if not env:
            raise ValueError(f"Environment '{name}' not found")

        env.status = EnvironmentStatus.LOCKED
        env.metadata["lock_reason"] = reason
        env.metadata["locked_at"] = datetime.utcnow().isoformat()
        return env

    async def unlock(self, name: str) -> Environment:
        """Unlock environment."""
        env = self._environments.get(name)
        if not env:
            raise ValueError(f"Environment '{name}' not found")

        env.status = EnvironmentStatus.ACTIVE
        env.metadata.pop("lock_reason", None)
        env.metadata.pop("locked_at", None)
        return env

    async def set_maintenance(self, name: str, maintenance: bool) -> Environment:
        """Set environment maintenance mode."""
        env = self._environments.get(name)
        if not env:
            raise ValueError(f"Environment '{name}' not found")

        env.status = EnvironmentStatus.MAINTENANCE if maintenance else EnvironmentStatus.ACTIVE
        return env
