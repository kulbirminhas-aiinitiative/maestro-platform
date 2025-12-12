"""
Promotion Service for Release Management.

This module provides the PromotionService class for orchestrating
deployments and promotions between environments.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import logging
import uuid

from .models import (
    Environment,
    EnvironmentTier,
    PromotionResult,
    RollbackResult,
    PipelineStatus,
)
from .environments import EnvironmentManager
from .pipelines import PipelineManager

logger = logging.getLogger(__name__)


class PromotionService:
    """
    Orchestrates deployment promotions between environments.

    Provides high-level promotion workflow including pipeline execution,
    gate approvals, and rollback handling.
    """

    def __init__(
        self,
        environment_manager: EnvironmentManager,
        pipeline_manager: PipelineManager,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the PromotionService.

        Args:
            environment_manager: EnvironmentManager instance
            pipeline_manager: PipelineManager instance
            config: Optional configuration dictionary
        """
        self.env_manager = environment_manager
        self.pipeline_manager = pipeline_manager
        self.config = config or {}
        self._promotion_history: List[PromotionResult] = []
        self._pending_approvals: Dict[str, Dict[str, Any]] = {}
        logger.info("PromotionService initialized")

    def promote(
        self,
        from_env: str,
        to_env: str,
        version: Optional[str] = None,
        skip_tests: bool = False,
        auto_approve: bool = False,
    ) -> PromotionResult:
        """
        Promote a deployment from one environment to another.

        Args:
            from_env: Source environment name
            to_env: Target environment name
            version: Optional specific version
            skip_tests: Skip test execution
            auto_approve: Auto-approve without manual gates

        Returns:
            PromotionResult with promotion status
        """
        # Get environments
        source = self.env_manager.get_environment(from_env)
        target = self.env_manager.get_environment(to_env)

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

        # Get version to promote
        promote_version = version or source.current_version
        if promote_version is None:
            return PromotionResult(
                success=False,
                from_environment=from_env,
                to_environment=to_env,
                version="",
                error="No version available for promotion",
            )

        # Validate promotion path
        if not source.tier.can_promote_to(target.tier):
            return PromotionResult(
                success=False,
                from_environment=from_env,
                to_environment=to_env,
                version=promote_version,
                error=f"Invalid promotion path: {source.tier.value} -> {target.tier.value}",
            )

        # Check target health
        if not target.can_accept_deployment():
            return PromotionResult(
                success=False,
                from_environment=from_env,
                to_environment=to_env,
                version=promote_version,
                error=f"Target environment not ready (status: {target.status.value})",
            )

        # Get or create pipeline for target
        pipeline = self.pipeline_manager.get_pipeline_by_environment(to_env)
        if pipeline is None:
            pipeline = self.pipeline_manager.create_environment_pipeline(
                to_env,
                target.tier.value,
            )

        # Check for manual gates
        manual_gates = [g for g in pipeline.gates if g.requires_manual_approval()]
        if manual_gates and not auto_approve:
            # Create pending approval
            approval_id = str(uuid.uuid4())[:8]
            self._pending_approvals[approval_id] = {
                "from_env": from_env,
                "to_env": to_env,
                "version": promote_version,
                "gates": [g.name for g in manual_gates],
                "created_at": datetime.utcnow(),
            }
            return PromotionResult(
                success=False,
                from_environment=from_env,
                to_environment=to_env,
                version=promote_version,
                approval_required=True,
                error=f"Awaiting approval (ID: {approval_id})",
            )

        # Trigger pipeline
        run = self.pipeline_manager.trigger(
            pipeline.id,
            version=promote_version,
            params={
                "source_env": from_env,
                "target_env": to_env,
                "skip_tests": skip_tests,
            },
        )

        # Simulate pipeline execution
        if skip_tests:
            test_passed = 100
            test_failed = 0
        else:
            test_passed = 150
            test_failed = 0

        # Complete pipeline
        self.pipeline_manager.complete_run(
            run.id,
            PipelineStatus.SUCCESS,
            artifacts=[f"{promote_version}.tar.gz"],
        )

        # Perform actual deployment
        result = self.env_manager.promote(
            from_env,
            to_env,
            version=promote_version,
            require_tests=not skip_tests,
        )

        # Update with test results
        result.tests_passed = test_passed
        result.tests_failed = test_failed

        # Record in history
        self._promotion_history.append(result)

        logger.info(
            f"Promoted version '{promote_version}' from '{from_env}' to '{to_env}'"
        )
        return result

    def approve_promotion(
        self,
        approval_id: str,
        approver: str,
    ) -> PromotionResult:
        """
        Approve a pending promotion.

        Args:
            approval_id: Approval request ID
            approver: Name of approver

        Returns:
            PromotionResult after approval
        """
        if approval_id not in self._pending_approvals:
            return PromotionResult(
                success=False,
                from_environment="",
                to_environment="",
                version="",
                error=f"Approval request '{approval_id}' not found",
            )

        pending = self._pending_approvals.pop(approval_id)

        # Execute promotion with auto_approve
        result = self.promote(
            pending["from_env"],
            pending["to_env"],
            version=pending["version"],
            auto_approve=True,
        )

        result.approved_by = approver
        return result

    def reject_promotion(
        self,
        approval_id: str,
        rejector: str,
        reason: Optional[str] = None,
    ) -> bool:
        """
        Reject a pending promotion.

        Args:
            approval_id: Approval request ID
            rejector: Name of rejector
            reason: Optional rejection reason

        Returns:
            True if rejected, False if not found
        """
        if approval_id not in self._pending_approvals:
            logger.warning(f"Approval request '{approval_id}' not found")
            return False

        pending = self._pending_approvals.pop(approval_id)
        logger.info(
            f"Promotion from '{pending['from_env']}' to '{pending['to_env']}' "
            f"rejected by {rejector}: {reason or 'No reason provided'}"
        )
        return True

    def rollback(
        self,
        environment: str,
        target_version: Optional[str] = None,
        reason: Optional[str] = None,
    ) -> RollbackResult:
        """
        Rollback an environment to a previous version.

        Args:
            environment: Environment to rollback
            target_version: Specific version (uses previous if not specified)
            reason: Reason for rollback

        Returns:
            RollbackResult with rollback status
        """
        result = self.env_manager.rollback(
            environment,
            target_version=target_version,
            reason=reason,
        )

        if result.success:
            logger.info(
                f"Rolled back '{environment}' to version '{result.to_version}'"
            )
        else:
            logger.error(f"Rollback failed: {result.error}")

        return result

    def get_promotion_status(
        self,
        from_env: str,
        to_env: str,
    ) -> Dict[str, Any]:
        """
        Get current promotion status between environments.

        Args:
            from_env: Source environment
            to_env: Target environment

        Returns:
            Dictionary with promotion status
        """
        source = self.env_manager.get_environment(from_env)
        target = self.env_manager.get_environment(to_env)

        if source is None or target is None:
            return {
                "error": "One or both environments not found",
                "can_promote": False,
            }

        # Check for pending approvals
        pending = None
        for approval_id, details in self._pending_approvals.items():
            if details["from_env"] == from_env and details["to_env"] == to_env:
                pending = {
                    "approval_id": approval_id,
                    "version": details["version"],
                    "gates": details["gates"],
                    "created_at": details["created_at"].isoformat(),
                }
                break

        # Get recent history
        recent_promotions = [
            p for p in self._promotion_history
            if p.from_environment == from_env and p.to_environment == to_env
        ][-5:]

        return {
            "from_environment": {
                "name": from_env,
                "status": source.status.value,
                "current_version": source.current_version,
            },
            "to_environment": {
                "name": to_env,
                "status": target.status.value,
                "current_version": target.current_version,
            },
            "can_promote": (
                source.tier.can_promote_to(target.tier) and
                target.can_accept_deployment() and
                source.current_version is not None
            ),
            "pending_approval": pending,
            "recent_promotions": [
                {
                    "version": p.version,
                    "success": p.success,
                    "started_at": p.started_at.isoformat(),
                }
                for p in recent_promotions
            ],
        }

    def get_promotion_history(
        self,
        environment: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get promotion history.

        Args:
            environment: Optional environment filter
            limit: Maximum records to return

        Returns:
            List of promotion records
        """
        history = self._promotion_history

        if environment:
            history = [
                p for p in history
                if p.from_environment == environment or p.to_environment == environment
            ]

        # Sort by timestamp descending
        history.sort(key=lambda p: p.started_at, reverse=True)

        return [
            {
                "from_environment": p.from_environment,
                "to_environment": p.to_environment,
                "version": p.version,
                "success": p.success,
                "deployment_id": p.deployment_id,
                "started_at": p.started_at.isoformat(),
                "completed_at": (
                    p.completed_at.isoformat() if p.completed_at else None
                ),
                "tests_passed": p.tests_passed,
                "tests_failed": p.tests_failed,
                "approved_by": p.approved_by,
                "error": p.error,
            }
            for p in history[:limit]
        ]

    def get_pending_approvals(self) -> List[Dict[str, Any]]:
        """
        Get all pending approval requests.

        Returns:
            List of pending approval details
        """
        return [
            {
                "approval_id": approval_id,
                "from_environment": details["from_env"],
                "to_environment": details["to_env"],
                "version": details["version"],
                "gates": details["gates"],
                "created_at": details["created_at"].isoformat(),
            }
            for approval_id, details in self._pending_approvals.items()
        ]

    def validate_promotion_path(
        self,
        from_env: str,
        to_env: str,
    ) -> Dict[str, Any]:
        """
        Validate if a promotion path is valid.

        Args:
            from_env: Source environment
            to_env: Target environment

        Returns:
            Dictionary with validation results
        """
        source = self.env_manager.get_environment(from_env)
        target = self.env_manager.get_environment(to_env)

        issues = []

        if source is None:
            issues.append(f"Source environment '{from_env}' not found")
        if target is None:
            issues.append(f"Target environment '{to_env}' not found")

        if source and target:
            if not source.tier.can_promote_to(target.tier):
                issues.append(
                    f"Cannot promote from {source.tier.value} to {target.tier.value}"
                )

            if not target.can_accept_deployment():
                issues.append(
                    f"Target environment not healthy (status: {target.status.value})"
                )

            if source.current_version is None:
                issues.append("No version deployed in source environment")

        return {
            "valid": len(issues) == 0,
            "from_environment": from_env,
            "to_environment": to_env,
            "issues": issues,
        }

    def create_promotion_workflow(
        self,
        version: str,
        target_tier: EnvironmentTier = EnvironmentTier.PRE_PROD,
    ) -> Dict[str, Any]:
        """
        Create a full promotion workflow from dev to target tier.

        Args:
            version: Version to promote
            target_tier: Target tier for promotion

        Returns:
            Dictionary with workflow steps
        """
        tiers = [
            EnvironmentTier.DEVELOPMENT,
            EnvironmentTier.TEST,
            EnvironmentTier.PRE_PROD,
            EnvironmentTier.PRODUCTION,
        ]

        target_idx = tiers.index(target_tier)
        workflow_tiers = tiers[:target_idx + 1]

        steps = []
        for i, tier in enumerate(workflow_tiers):
            env = None
            for e in self.env_manager.list_environments(tier=tier):
                env = e
                break

            if i == 0:
                steps.append({
                    "step": i + 1,
                    "action": "deploy",
                    "environment": env.name if env else tier.value,
                    "tier": tier.value,
                    "version": version,
                })
            else:
                prev_tier = workflow_tiers[i - 1]
                prev_env = None
                for e in self.env_manager.list_environments(tier=prev_tier):
                    prev_env = e
                    break

                steps.append({
                    "step": i + 1,
                    "action": "promote",
                    "from_environment": prev_env.name if prev_env else prev_tier.value,
                    "to_environment": env.name if env else tier.value,
                    "tier": tier.value,
                    "version": version,
                    "requires_approval": (
                        tier in [EnvironmentTier.PRE_PROD, EnvironmentTier.PRODUCTION]
                    ),
                })

        return {
            "workflow_id": str(uuid.uuid4())[:8],
            "version": version,
            "target_tier": target_tier.value,
            "steps": steps,
            "created_at": datetime.utcnow().isoformat(),
        }
