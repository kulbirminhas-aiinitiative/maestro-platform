"""
Environment Manager for Release Management.

This module provides the EnvironmentManager class for managing deployment
environments (Dev/Test/Pre-Prod) and their configurations.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import logging
import uuid

from .models import (
    Environment,
    EnvironmentConfig,
    EnvironmentTier,
    EnvironmentStatus,
    PromotionResult,
    RollbackResult,
)

logger = logging.getLogger(__name__)


class EnvironmentManager:
    """
    Manages deployment environments and their configurations.

    Provides functionality to create, configure, and manage environments
    across different tiers (Dev, Test, Pre-Prod).
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the EnvironmentManager.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self._environments: Dict[str, Environment] = {}
        self._version_history: Dict[str, List[str]] = {}
        logger.info("EnvironmentManager initialized")

    def create_environment(
        self,
        name: str,
        tier: EnvironmentTier,
        config: Optional[EnvironmentConfig] = None,
    ) -> Environment:
        """
        Create a new environment.

        Args:
            name: Environment name
            tier: Environment tier (development, test, pre_prod)
            config: Optional environment configuration

        Returns:
            Created Environment instance

        Raises:
            ValueError: If environment with name already exists
        """
        if name in self._environments:
            logger.error(f"Environment '{name}' already exists")
            raise ValueError(f"Environment '{name}' already exists")

        if config is None:
            config = self._get_default_config(tier)

        if not config.validate():
            raise ValueError("Invalid environment configuration")

        environment = Environment(
            name=name,
            tier=tier,
            config=config,
            status=EnvironmentStatus.HEALTHY,
        )

        self._environments[name] = environment
        self._version_history[name] = []

        logger.info(f"Created environment '{name}' with tier '{tier.value}'")
        return environment

    def get_environment(self, name: str) -> Optional[Environment]:
        """
        Get an environment by name.

        Args:
            name: Environment name

        Returns:
            Environment instance or None if not found
        """
        return self._environments.get(name)

    def list_environments(
        self,
        tier: Optional[EnvironmentTier] = None,
        status: Optional[EnvironmentStatus] = None,
    ) -> List[Environment]:
        """
        List all environments, optionally filtered by tier or status.

        Args:
            tier: Optional tier filter
            status: Optional status filter

        Returns:
            List of Environment instances
        """
        environments = list(self._environments.values())

        if tier is not None:
            environments = [e for e in environments if e.tier == tier]

        if status is not None:
            environments = [e for e in environments if e.status == status]

        return environments

    def update_environment(
        self,
        name: str,
        config: Optional[EnvironmentConfig] = None,
        status: Optional[EnvironmentStatus] = None,
    ) -> Optional[Environment]:
        """
        Update an environment's configuration or status.

        Args:
            name: Environment name
            config: Optional new configuration
            status: Optional new status

        Returns:
            Updated Environment instance or None if not found
        """
        environment = self._environments.get(name)
        if environment is None:
            logger.warning(f"Environment '{name}' not found")
            return None

        if config is not None:
            if not config.validate():
                logger.error("Invalid configuration provided")
                return None
            environment.config = config

        if status is not None:
            environment.status = status

        environment.updated_at = datetime.utcnow()
        logger.info(f"Updated environment '{name}'")
        return environment

    def delete_environment(self, name: str) -> bool:
        """
        Delete an environment.

        Args:
            name: Environment name

        Returns:
            True if deleted, False if not found
        """
        if name not in self._environments:
            logger.warning(f"Environment '{name}' not found")
            return False

        del self._environments[name]
        if name in self._version_history:
            del self._version_history[name]

        logger.info(f"Deleted environment '{name}'")
        return True

    def deploy(
        self,
        environment_name: str,
        version: str,
        force: bool = False,
    ) -> bool:
        """
        Deploy a version to an environment.

        Args:
            environment_name: Target environment name
            version: Version to deploy
            force: Force deployment even if unhealthy

        Returns:
            True if deployment successful, False otherwise
        """
        environment = self._environments.get(environment_name)
        if environment is None:
            logger.error(f"Environment '{environment_name}' not found")
            return False

        if not force and not environment.can_accept_deployment():
            logger.error(
                f"Environment '{environment_name}' cannot accept deployment "
                f"(status: {environment.status.value})"
            )
            return False

        # Store previous version for rollback
        if environment.current_version:
            self._version_history[environment_name].append(environment.current_version)

        # Update environment
        previous_status = environment.status
        environment.status = EnvironmentStatus.DEPLOYING

        # Simulate deployment
        environment.current_version = version
        environment.deployed_at = datetime.utcnow()
        environment.status = EnvironmentStatus.HEALTHY
        environment.updated_at = datetime.utcnow()

        logger.info(
            f"Deployed version '{version}' to environment '{environment_name}'"
        )
        return True

    def promote(
        self,
        from_env: str,
        to_env: str,
        version: Optional[str] = None,
        require_tests: bool = True,
    ) -> PromotionResult:
        """
        Promote a deployment from one environment to another.

        Args:
            from_env: Source environment name
            to_env: Target environment name
            version: Optional specific version (uses source's current if not specified)
            require_tests: Whether to require tests to pass

        Returns:
            PromotionResult with success status and details
        """
        source = self._environments.get(from_env)
        target = self._environments.get(to_env)

        if source is None:
            return PromotionResult(
                success=False,
                from_environment=from_env,
                to_environment=to_env,
                version=version or "",
                error=f"Source environment '{from_env}' not found",
            )

        if target is None:
            return PromotionResult(
                success=False,
                from_environment=from_env,
                to_environment=to_env,
                version=version or "",
                error=f"Target environment '{to_env}' not found",
            )

        # Validate promotion path
        if not source.tier.can_promote_to(target.tier):
            return PromotionResult(
                success=False,
                from_environment=from_env,
                to_environment=to_env,
                version=version or "",
                error=f"Cannot promote from {source.tier.value} to {target.tier.value}",
            )

        deploy_version = version or source.current_version
        if deploy_version is None:
            return PromotionResult(
                success=False,
                from_environment=from_env,
                to_environment=to_env,
                version="",
                error="No version available to promote",
            )

        # Check if target requires approval
        approval_required = target.config.require_approval

        # Perform deployment
        deployment_id = str(uuid.uuid4())[:8]
        if self.deploy(to_env, deploy_version):
            logger.info(
                f"Promoted version '{deploy_version}' from '{from_env}' to '{to_env}'"
            )
            return PromotionResult(
                success=True,
                from_environment=from_env,
                to_environment=to_env,
                version=deploy_version,
                deployment_id=deployment_id,
                completed_at=datetime.utcnow(),
                approval_required=approval_required,
                tests_passed=100 if require_tests else None,
                tests_failed=0 if require_tests else None,
            )
        else:
            return PromotionResult(
                success=False,
                from_environment=from_env,
                to_environment=to_env,
                version=deploy_version,
                error="Deployment failed",
            )

    def rollback(
        self,
        environment_name: str,
        target_version: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> RollbackResult:
        """
        Rollback an environment to a previous version.

        Args:
            environment_name: Environment to rollback
            target_version: Specific version to rollback to (uses previous if not specified)
            reason: Optional reason for rollback

        Returns:
            RollbackResult with success status and details
        """
        environment = self._environments.get(environment_name)
        if environment is None:
            return RollbackResult(
                success=False,
                environment=environment_name,
                from_version="",
                to_version=target_version or "",
                error=f"Environment '{environment_name}' not found",
            )

        current_version = environment.current_version
        if current_version is None:
            return RollbackResult(
                success=False,
                environment=environment_name,
                from_version="",
                to_version=target_version or "",
                error="No current version to rollback from",
            )

        # Get target version
        history = self._version_history.get(environment_name, [])
        if target_version:
            if target_version not in history:
                return RollbackResult(
                    success=False,
                    environment=environment_name,
                    from_version=current_version,
                    to_version=target_version,
                    error=f"Version '{target_version}' not in history",
                )
            rollback_version = target_version
        elif history:
            rollback_version = history[-1]
        else:
            return RollbackResult(
                success=False,
                environment=environment_name,
                from_version=current_version,
                to_version="",
                error="No previous version available for rollback",
            )

        # Perform rollback
        rollback_id = str(uuid.uuid4())[:8]
        if self.deploy(environment_name, rollback_version, force=True):
            logger.info(
                f"Rolled back '{environment_name}' from '{current_version}' "
                f"to '{rollback_version}'"
            )
            return RollbackResult(
                success=True,
                environment=environment_name,
                from_version=current_version,
                to_version=rollback_version,
                rollback_id=rollback_id,
                completed_at=datetime.utcnow(),
                reason=reason,
            )
        else:
            return RollbackResult(
                success=False,
                environment=environment_name,
                from_version=current_version,
                to_version=rollback_version,
                error="Rollback deployment failed",
            )

    def get_health_status(self, name: str) -> Dict[str, Any]:
        """
        Get detailed health status of an environment.

        Args:
            name: Environment name

        Returns:
            Dictionary with health details
        """
        environment = self._environments.get(name)
        if environment is None:
            return {"error": f"Environment '{name}' not found"}

        return {
            "name": name,
            "status": environment.status.value,
            "is_healthy": environment.is_healthy(),
            "can_deploy": environment.can_accept_deployment(),
            "current_version": environment.current_version,
            "deployed_at": (
                environment.deployed_at.isoformat() if environment.deployed_at else None
            ),
            "tier": environment.tier.value,
        }

    def get_version_history(self, name: str) -> List[str]:
        """
        Get version deployment history for an environment.

        Args:
            name: Environment name

        Returns:
            List of previously deployed versions
        """
        return self._version_history.get(name, [])

    def _get_default_config(self, tier: EnvironmentTier) -> EnvironmentConfig:
        """Get default configuration for a tier."""
        defaults = {
            EnvironmentTier.DEVELOPMENT: EnvironmentConfig(
                cpu="500m",
                memory="512Mi",
                replicas=1,
                auto_deploy=True,
                require_approval=False,
                data_source="synthetic",
            ),
            EnvironmentTier.TEST: EnvironmentConfig(
                cpu="1000m",
                memory="1Gi",
                replicas=2,
                auto_deploy=False,
                require_approval=False,
                data_source="sanitized",
                mask_pii=True,
            ),
            EnvironmentTier.PRE_PROD: EnvironmentConfig(
                cpu="2000m",
                memory="4Gi",
                replicas=3,
                auto_deploy=False,
                require_approval=True,
                approvers=["qa-lead", "tech-lead"],
                data_source="production_snapshot",
            ),
            EnvironmentTier.PRODUCTION: EnvironmentConfig(
                cpu="4000m",
                memory="8Gi",
                replicas=5,
                auto_deploy=False,
                require_approval=True,
                approvers=["release-manager", "ops-lead"],
                data_source="production",
            ),
        }
        return defaults.get(tier, EnvironmentConfig())
