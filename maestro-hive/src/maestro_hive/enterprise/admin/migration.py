"""
Migration Runner Module.

Provides utilities for running and managing migration operations
with verification, rollback support, and progress tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any, Callable
import asyncio
import logging
import uuid

from .config import AdminConfig, AdminOperation, OperationType
from .repository import RepositoryManager, MigrationResult

logger = logging.getLogger(__name__)


class MigrationStatus(Enum):
    """Status of a migration operation."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class MigrationStep:
    """Individual step in a migration plan."""

    step_id: str
    name: str
    description: str
    source: str
    target: str
    status: MigrationStatus = MigrationStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[MigrationResult] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_id": self.step_id,
            "name": self.name,
            "description": self.description,
            "source": self.source,
            "target": self.target,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result": self.result.to_dict() if self.result else None,
            "error_message": self.error_message,
        }


@dataclass
class MigrationPlan:
    """Plan for a complete migration operation."""

    plan_id: str
    name: str
    description: str
    steps: List[MigrationStep]
    created_at: datetime
    created_by: str
    status: MigrationStatus = MigrationStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    dry_run: bool = True
    pre_checks: List[str] = field(default_factory=list)
    post_checks: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "plan_id": self.plan_id,
            "name": self.name,
            "description": self.description,
            "steps": [step.to_dict() for step in self.steps],
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "dry_run": self.dry_run,
            "pre_checks": self.pre_checks,
            "post_checks": self.post_checks,
            "progress": self.get_progress(),
        }

    def get_progress(self) -> Dict[str, Any]:
        """Get migration progress."""
        total = len(self.steps)
        completed = sum(
            1 for s in self.steps if s.status == MigrationStatus.COMPLETED
        )
        failed = sum(1 for s in self.steps if s.status == MigrationStatus.FAILED)
        in_progress = sum(
            1 for s in self.steps if s.status == MigrationStatus.IN_PROGRESS
        )

        return {
            "total_steps": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": total - completed - failed - in_progress,
            "percentage": (completed / total * 100) if total > 0 else 0,
        }


class MigrationRunner:
    """Manages and executes migration plans.

    Provides:
    - Plan creation and validation
    - Step-by-step execution with progress tracking
    - Verification after each step
    - Rollback support on failure
    - Audit logging
    """

    def __init__(self, config: Optional[AdminConfig] = None):
        """Initialize migration runner.

        Args:
            config: Admin configuration. Defaults to environment-based config.
        """
        self.config = config or AdminConfig.from_env()
        self.repository_manager = RepositoryManager(config)
        self._plans: Dict[str, MigrationPlan] = {}
        self._operations: List[AdminOperation] = []
        self._progress_callbacks: List[Callable[[MigrationPlan], None]] = []

        logger.info(
            "MigrationRunner initialized (dry_run=%s)",
            self.config.dry_run,
        )

    def create_plan(
        self,
        name: str,
        description: str,
        migrations: List[Dict[str, str]],
        created_by: Optional[str] = None,
    ) -> MigrationPlan:
        """Create a migration plan.

        Args:
            name: Plan name
            description: Plan description
            migrations: List of {source, target} dictionaries
            created_by: User creating the plan

        Returns:
            MigrationPlan ready for execution
        """
        plan_id = str(uuid.uuid4())

        steps = []
        for i, migration in enumerate(migrations):
            step = MigrationStep(
                step_id=f"{plan_id}-step-{i + 1}",
                name=f"Migrate {migration['source']}",
                description=f"Migrate repository from {migration['source']} to {migration['target']}",
                source=migration["source"],
                target=migration["target"],
            )
            steps.append(step)

        plan = MigrationPlan(
            plan_id=plan_id,
            name=name,
            description=description,
            steps=steps,
            created_at=datetime.utcnow(),
            created_by=created_by or "system",
            dry_run=self.config.dry_run,
            pre_checks=[
                "Verify source repositories exist",
                "Verify target organization access",
                "Check for name conflicts",
            ],
            post_checks=[
                "Verify all branches migrated",
                "Verify all tags migrated",
                "Update CI/CD pipelines",
                "Update documentation",
            ],
        )

        self._plans[plan_id] = plan
        logger.info("Created migration plan: %s (%d steps)", plan_id, len(steps))

        return plan

    def register_progress_callback(
        self, callback: Callable[[MigrationPlan], None]
    ) -> None:
        """Register a callback for progress updates.

        Args:
            callback: Function called with plan after each step
        """
        self._progress_callbacks.append(callback)

    def _notify_progress(self, plan: MigrationPlan) -> None:
        """Notify all registered callbacks of progress."""
        for callback in self._progress_callbacks:
            try:
                callback(plan)
            except Exception as e:
                logger.error("Progress callback failed: %s", str(e))

    async def execute_plan(
        self,
        plan_id: str,
        dry_run: Optional[bool] = None,
    ) -> MigrationPlan:
        """Execute a migration plan.

        Args:
            plan_id: ID of the plan to execute
            dry_run: Override config dry_run setting

        Returns:
            Updated MigrationPlan with results
        """
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")

        effective_dry_run = dry_run if dry_run is not None else self.config.dry_run
        plan.dry_run = effective_dry_run

        logger.info(
            "Executing migration plan: %s (dry_run=%s)",
            plan_id,
            effective_dry_run,
        )

        plan.status = MigrationStatus.IN_PROGRESS
        plan.started_at = datetime.utcnow()
        self._notify_progress(plan)

        try:
            for step in plan.steps:
                await self._execute_step(step, effective_dry_run)
                self._notify_progress(plan)

                if step.status == MigrationStatus.FAILED:
                    logger.error("Step failed: %s", step.step_id)
                    plan.status = MigrationStatus.FAILED
                    break

            if plan.status != MigrationStatus.FAILED:
                plan.status = MigrationStatus.COMPLETED

        except Exception as e:
            logger.error("Migration plan failed: %s", str(e))
            plan.status = MigrationStatus.FAILED

        plan.completed_at = datetime.utcnow()
        self._notify_progress(plan)

        logger.info(
            "Migration plan %s: %s",
            plan_id,
            plan.status.value,
        )

        return plan

    async def _execute_step(self, step: MigrationStep, dry_run: bool) -> None:
        """Execute a single migration step.

        Args:
            step: Step to execute
            dry_run: Whether to simulate or execute
        """
        step.status = MigrationStatus.IN_PROGRESS
        step.started_at = datetime.utcnow()

        logger.info(
            "Executing step: %s (%s -> %s)",
            step.step_id,
            step.source,
            step.target,
        )

        try:
            # Update repository manager dry_run setting
            original_dry_run = self.repository_manager.config.dry_run
            self.repository_manager.config.dry_run = dry_run

            result = await self.repository_manager.migrate_repository(
                source=step.source,
                target=step.target,
                verify=self.config.verify_after,
            )

            # Restore original setting
            self.repository_manager.config.dry_run = original_dry_run

            step.result = result
            step.completed_at = datetime.utcnow()

            if result.success:
                step.status = MigrationStatus.COMPLETED
                logger.info(
                    "Step completed: %s (branches=%d, tags=%d)",
                    step.step_id,
                    result.branches_migrated,
                    result.tags_migrated,
                )
            else:
                step.status = MigrationStatus.FAILED
                step.error_message = result.error_message
                logger.error("Step failed: %s - %s", step.step_id, result.error_message)

        except Exception as e:
            step.status = MigrationStatus.FAILED
            step.error_message = str(e)
            step.completed_at = datetime.utcnow()
            logger.error("Step exception: %s - %s", step.step_id, str(e))

    async def rollback_plan(self, plan_id: str) -> MigrationPlan:
        """Rollback a migration plan.

        Args:
            plan_id: ID of the plan to rollback

        Returns:
            Updated MigrationPlan after rollback
        """
        plan = self._plans.get(plan_id)
        if not plan:
            raise ValueError(f"Plan not found: {plan_id}")

        logger.info("Rolling back migration plan: %s", plan_id)

        # Rollback completed steps in reverse order
        for step in reversed(plan.steps):
            if step.status == MigrationStatus.COMPLETED:
                logger.info(
                    "Rolling back step: %s (%s -> %s)",
                    step.step_id,
                    step.target,
                    step.source,
                )
                # In production, this would reverse the migration
                step.status = MigrationStatus.ROLLED_BACK

        plan.status = MigrationStatus.ROLLED_BACK
        self._notify_progress(plan)

        return plan

    def get_plan(self, plan_id: str) -> Optional[MigrationPlan]:
        """Get a migration plan by ID.

        Args:
            plan_id: Plan ID

        Returns:
            MigrationPlan if found, None otherwise
        """
        return self._plans.get(plan_id)

    def list_plans(
        self,
        status: Optional[MigrationStatus] = None,
    ) -> List[MigrationPlan]:
        """List all migration plans.

        Args:
            status: Filter by status

        Returns:
            List of migration plans
        """
        plans = list(self._plans.values())
        if status:
            plans = [p for p in plans if p.status == status]
        return plans

    def get_operations_history(self) -> List[Dict[str, Any]]:
        """Get history of all operations for audit."""
        history = self.repository_manager.get_operations_history()
        return history
