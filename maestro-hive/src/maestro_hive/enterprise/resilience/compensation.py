"""
Compensation and Rollback Logic.

Implements the Saga pattern for distributed transactions.
"""

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Callable, Any, Dict, List, Awaitable
from enum import Enum
import uuid
import traceback


class CompensationStatus(Enum):
    """Compensation action status."""
    PENDING = "pending"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class CompensationAction:
    """Compensation action definition."""
    id: str
    name: str
    action: Callable[[], Awaitable[Any]]
    status: CompensationStatus = CompensationStatus.PENDING
    error: Optional[str] = None
    executed_at: Optional[datetime] = None
    result: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompensationResult:
    """Result of compensation execution."""
    saga_id: str
    success: bool
    actions_executed: int
    actions_failed: int
    actions_skipped: int
    errors: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    duration_ms: int = 0


class CompensationManager:
    """
    Manages compensation actions for rollback.

    Compensation actions are executed in reverse order
    when a transaction fails, undoing previous operations.
    """

    def __init__(self):
        """Initialize compensation manager."""
        self._compensation_stack: List[CompensationAction] = []
        self._executed_actions: List[CompensationAction] = []

    def register(
        self,
        name: str,
        action: Callable[[], Awaitable[Any]],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Register compensation action.

        Actions are executed in LIFO order during compensation.

        Args:
            name: Action name for logging
            action: Async function to execute for compensation
            metadata: Additional action metadata

        Returns:
            Action ID
        """
        action_id = str(uuid.uuid4())
        compensation = CompensationAction(
            id=action_id,
            name=name,
            action=action,
            metadata=metadata or {},
        )
        self._compensation_stack.append(compensation)
        return action_id

    def clear(self) -> None:
        """Clear all registered compensations (on success)."""
        self._compensation_stack.clear()

    async def compensate(
        self,
        stop_on_error: bool = False,
    ) -> CompensationResult:
        """
        Execute all compensation actions in reverse order.

        Args:
            stop_on_error: Stop if any compensation fails

        Returns:
            CompensationResult with execution details
        """
        saga_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        errors = []
        executed = 0
        failed = 0
        skipped = 0

        # Execute in reverse order (LIFO)
        while self._compensation_stack:
            action = self._compensation_stack.pop()

            if stop_on_error and failed > 0:
                action.status = CompensationStatus.SKIPPED
                skipped += 1
                continue

            action.status = CompensationStatus.EXECUTING

            try:
                result = await action.action()
                action.status = CompensationStatus.COMPLETED
                action.result = result
                action.executed_at = datetime.utcnow()
                executed += 1

            except Exception as e:
                action.status = CompensationStatus.FAILED
                action.error = str(e)
                action.executed_at = datetime.utcnow()
                failed += 1
                errors.append(f"{action.name}: {e}")

            self._executed_actions.append(action)

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds() * 1000

        return CompensationResult(
            saga_id=saga_id,
            success=failed == 0,
            actions_executed=executed,
            actions_failed=failed,
            actions_skipped=skipped,
            errors=errors,
            started_at=start_time,
            completed_at=end_time,
            duration_ms=int(duration),
        )

    def get_pending_actions(self) -> List[CompensationAction]:
        """Get pending compensation actions."""
        return list(self._compensation_stack)

    def get_executed_actions(self) -> List[CompensationAction]:
        """Get executed compensation actions."""
        return list(self._executed_actions)


class SagaStep:
    """Step in a Saga transaction."""

    def __init__(
        self,
        name: str,
        action: Callable[..., Awaitable[Any]],
        compensation: Callable[..., Awaitable[Any]],
    ):
        """
        Initialize saga step.

        Args:
            name: Step name
            action: Forward action
            compensation: Compensation action
        """
        self.name = name
        self.action = action
        self.compensation = compensation
        self.result: Any = None
        self.error: Optional[str] = None
        self.status: CompensationStatus = CompensationStatus.PENDING


@dataclass
class SagaResult:
    """Result of Saga execution."""
    saga_id: str
    success: bool
    completed_steps: List[str]
    failed_step: Optional[str]
    compensation_result: Optional[CompensationResult]
    step_results: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class Saga:
    """
    Saga pattern implementation for distributed transactions.

    Executes a sequence of steps, with automatic compensation
    (rollback) if any step fails.
    """

    def __init__(self, name: str):
        """
        Initialize saga.

        Args:
            name: Saga name
        """
        self.name = name
        self.saga_id = str(uuid.uuid4())
        self._steps: List[SagaStep] = []
        self._completed_steps: List[SagaStep] = []
        self._context: Dict[str, Any] = {}

    def add_step(
        self,
        name: str,
        action: Callable[..., Awaitable[Any]],
        compensation: Callable[..., Awaitable[Any]],
    ) -> "Saga":
        """
        Add step to saga.

        Args:
            name: Step name
            action: Forward action (receives context dict)
            compensation: Compensation action (receives context dict)

        Returns:
            Self for chaining
        """
        step = SagaStep(name, action, compensation)
        self._steps.append(step)
        return self

    def set_context(self, key: str, value: Any) -> "Saga":
        """
        Set context value.

        Args:
            key: Context key
            value: Context value

        Returns:
            Self for chaining
        """
        self._context[key] = value
        return self

    async def execute(self) -> SagaResult:
        """
        Execute saga with automatic compensation on failure.

        Returns:
            SagaResult with execution details
        """
        start_time = datetime.utcnow()
        step_results = {}
        failed_step = None
        compensation_result = None
        error = None

        try:
            # Execute steps in order
            for step in self._steps:
                step.status = CompensationStatus.EXECUTING

                try:
                    # Execute action with context
                    result = await step.action(self._context)
                    step.result = result
                    step.status = CompensationStatus.COMPLETED
                    step_results[step.name] = result

                    # Store result in context for next steps
                    self._context[f"{step.name}_result"] = result
                    self._completed_steps.append(step)

                except Exception as e:
                    step.status = CompensationStatus.FAILED
                    step.error = str(e)
                    failed_step = step.name
                    error = f"Step '{step.name}' failed: {e}"

                    # Compensate completed steps
                    compensation_result = await self._compensate()
                    break

        except Exception as e:
            error = f"Saga execution error: {e}"
            compensation_result = await self._compensate()

        end_time = datetime.utcnow()

        return SagaResult(
            saga_id=self.saga_id,
            success=failed_step is None,
            completed_steps=[s.name for s in self._completed_steps],
            failed_step=failed_step,
            compensation_result=compensation_result,
            step_results=step_results,
            error=error,
            started_at=start_time,
            completed_at=end_time,
        )

    async def _compensate(self) -> CompensationResult:
        """Compensate completed steps in reverse order."""
        saga_id = f"{self.saga_id}-compensation"
        start_time = datetime.utcnow()
        errors = []
        executed = 0
        failed = 0

        # Compensate in reverse order
        for step in reversed(self._completed_steps):
            try:
                await step.compensation(self._context)
                executed += 1
            except Exception as e:
                failed += 1
                errors.append(f"{step.name}: {e}")

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds() * 1000

        return CompensationResult(
            saga_id=saga_id,
            success=failed == 0,
            actions_executed=executed,
            actions_failed=failed,
            actions_skipped=0,
            errors=errors,
            started_at=start_time,
            completed_at=end_time,
            duration_ms=int(duration),
        )

    def get_context(self) -> Dict[str, Any]:
        """Get saga context."""
        return self._context.copy()


# Example Saga factory
def create_workflow_creation_saga(
    workflow_data: Dict[str, Any],
) -> Saga:
    """
    Create saga for workflow creation with JIRA sync.

    Args:
        workflow_data: Workflow creation data

    Returns:
        Configured Saga
    """
    saga = Saga("create_workflow_with_jira")
    saga.set_context("workflow_data", workflow_data)

    async def create_workflow(ctx):
        # Create workflow in database
        return {"workflow_id": "wf-123"}

    async def compensate_workflow(ctx):
        # Delete created workflow
        pass

    async def create_jira_issue(ctx):
        # Create JIRA issue
        return {"jira_key": "PROJ-456"}

    async def compensate_jira(ctx):
        # Delete JIRA issue
        pass

    async def link_workflow_jira(ctx):
        # Create link between workflow and JIRA
        pass

    async def compensate_link(ctx):
        # Remove link
        pass

    saga.add_step("create_workflow", create_workflow, compensate_workflow)
    saga.add_step("create_jira_issue", create_jira_issue, compensate_jira)
    saga.add_step("link_workflow_jira", link_workflow_jira, compensate_link)

    return saga
