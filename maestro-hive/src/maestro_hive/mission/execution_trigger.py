"""
Execution Trigger for Starting Missions.
EPIC: MD-3024 - Mission to Execution Handoff

Triggers mission execution by integrating with the TaskQueue
and team execution infrastructure.
"""

import asyncio
import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, AsyncGenerator, Callable, Awaitable

from .handoff_coordinator import MissionContext

logger = logging.getLogger(__name__)


class ExecutionStatus(Enum):
    """Execution lifecycle status."""
    QUEUED = "queued"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class ExecutionPriority(Enum):
    """Execution priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


@dataclass
class TriggerConfig:
    """Configuration for execution trigger."""
    async_execution: bool = True
    max_concurrent: int = 5
    queue_timeout_seconds: int = 60
    execution_timeout_seconds: int = 3600
    enable_tracing: bool = True
    priority: ExecutionPriority = ExecutionPriority.NORMAL
    retry_on_failure: bool = True
    max_retries: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionHandle:
    """Handle to a triggered execution."""
    execution_id: str
    mission_id: str
    status: ExecutionStatus
    queue_position: Optional[int] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    task_id: Optional[str] = None

    def is_active(self) -> bool:
        """Check if execution is still active."""
        return self.status in (
            ExecutionStatus.QUEUED,
            ExecutionStatus.STARTING,
            ExecutionStatus.RUNNING,
            ExecutionStatus.PAUSED,
        )


@dataclass
class ExecutionUpdate:
    """Update about execution progress."""
    execution_id: str
    status: ExecutionStatus
    progress: float = 0.0
    message: str = ""
    current_phase: str = ""
    artifacts_produced: int = 0
    error: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def completed(self) -> bool:
        """Check if execution is complete."""
        return self.status in (
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.ABORTED,
        )


@dataclass
class ExecutionResult:
    """Result of completed execution."""
    execution_id: str
    mission_id: str
    status: ExecutionStatus
    outputs: Dict[str, Any] = field(default_factory=dict)
    artifacts: list = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def duration_seconds(self) -> float:
        """Calculate execution duration."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0

    @property
    def success(self) -> bool:
        """Check if execution succeeded."""
        return self.status == ExecutionStatus.COMPLETED


class ExecutionTrigger:
    """
    Triggers mission execution.

    Integrates with TaskQueue to submit missions for execution
    and provides monitoring capabilities.

    Example:
        trigger = ExecutionTrigger()
        handle = await trigger.trigger_execution(context)
        async for update in trigger.monitor_execution(handle):
            print(f"Progress: {update.progress}%")
    """

    def __init__(
        self,
        task_queue: Optional[Any] = None,
        config: Optional[TriggerConfig] = None,
    ):
        """
        Initialize trigger.

        Args:
            task_queue: Optional TaskQueue for execution
            config: Trigger configuration
        """
        self.config = config or TriggerConfig()
        self._task_queue = task_queue
        self._executions: Dict[str, ExecutionHandle] = {}
        self._results: Dict[str, ExecutionResult] = {}
        self._update_callbacks: Dict[str, list] = {}
        self._lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        logger.info(f"ExecutionTrigger initialized: max_concurrent={self.config.max_concurrent}")

    async def trigger_execution(
        self,
        context: MissionContext,
        config: Optional[TriggerConfig] = None,
    ) -> ExecutionHandle:
        """
        Trigger mission execution.

        Args:
            context: Mission context to execute
            config: Override trigger configuration

        Returns:
            ExecutionHandle for tracking
        """
        config = config or self.config
        execution_id = f"exec-{uuid.uuid4().hex[:12]}"

        handle = ExecutionHandle(
            execution_id=execution_id,
            mission_id=context.mission_id,
            status=ExecutionStatus.QUEUED,
        )

        async with self._lock:
            self._executions[execution_id] = handle

        logger.info(f"Triggered execution {execution_id} for mission {context.mission_id}")

        # Submit to queue if available
        if self._task_queue:
            try:
                task_id = await self._task_queue.submit(
                    self._execute_mission,
                    context,
                    name=f"mission-{context.mission_id}",
                    metadata={"execution_id": execution_id},
                )
                handle.task_id = task_id
                logger.debug(f"Submitted to queue: task_id={task_id}")
            except Exception as e:
                handle.status = ExecutionStatus.FAILED
                logger.error(f"Failed to submit to queue: {e}")
                raise

        # If async execution, start background task
        if config.async_execution and not self._task_queue:
            asyncio.create_task(self._execute_async(execution_id, context))

        return handle

    async def _execute_async(
        self,
        execution_id: str,
        context: MissionContext,
    ) -> None:
        """Execute mission asynchronously."""
        async with self._semaphore:
            handle = self._executions.get(execution_id)
            if not handle:
                return

            try:
                handle.status = ExecutionStatus.STARTING
                handle.started_at = datetime.utcnow()

                await self._emit_update(execution_id, ExecutionUpdate(
                    execution_id=execution_id,
                    status=ExecutionStatus.STARTING,
                    progress=5.0,
                    message="Initializing execution",
                ))

                # Simulate execution phases
                handle.status = ExecutionStatus.RUNNING

                await self._emit_update(execution_id, ExecutionUpdate(
                    execution_id=execution_id,
                    status=ExecutionStatus.RUNNING,
                    progress=20.0,
                    message="Executing mission",
                    current_phase="initialization",
                ))

                # Simulate work
                for phase, progress in [
                    ("planning", 40.0),
                    ("execution", 70.0),
                    ("finalization", 90.0),
                ]:
                    await asyncio.sleep(0.1)  # Simulate work
                    await self._emit_update(execution_id, ExecutionUpdate(
                        execution_id=execution_id,
                        status=ExecutionStatus.RUNNING,
                        progress=progress,
                        message=f"Phase: {phase}",
                        current_phase=phase,
                    ))

                # Complete
                handle.status = ExecutionStatus.COMPLETED

                result = ExecutionResult(
                    execution_id=execution_id,
                    mission_id=context.mission_id,
                    status=ExecutionStatus.COMPLETED,
                    outputs={"objectives_completed": len(context.objectives)},
                    metrics={
                        "duration_seconds": (datetime.utcnow() - handle.started_at).total_seconds(),
                        "phases_executed": 3,
                    },
                    started_at=handle.started_at,
                    completed_at=datetime.utcnow(),
                )

                async with self._lock:
                    self._results[execution_id] = result

                await self._emit_update(execution_id, ExecutionUpdate(
                    execution_id=execution_id,
                    status=ExecutionStatus.COMPLETED,
                    progress=100.0,
                    message="Execution completed",
                ))

                logger.info(f"Execution {execution_id} completed")

            except Exception as e:
                handle.status = ExecutionStatus.FAILED

                result = ExecutionResult(
                    execution_id=execution_id,
                    mission_id=context.mission_id,
                    status=ExecutionStatus.FAILED,
                    error=str(e),
                    started_at=handle.started_at,
                    completed_at=datetime.utcnow(),
                )

                async with self._lock:
                    self._results[execution_id] = result

                await self._emit_update(execution_id, ExecutionUpdate(
                    execution_id=execution_id,
                    status=ExecutionStatus.FAILED,
                    error=str(e),
                ))

                logger.error(f"Execution {execution_id} failed: {e}")

    async def _execute_mission(
        self,
        context: MissionContext,
    ) -> Dict[str, Any]:
        """Execute mission (called by TaskQueue)."""
        logger.info(f"Executing mission {context.mission_id}")

        # Simulate execution
        await asyncio.sleep(0.5)

        return {
            "mission_id": context.mission_id,
            "status": "completed",
            "objectives_completed": len(context.objectives),
        }

    async def monitor_execution(
        self,
        handle: ExecutionHandle,
    ) -> AsyncGenerator[ExecutionUpdate, None]:
        """
        Stream execution updates.

        Args:
            handle: Execution to monitor

        Yields:
            ExecutionUpdate with progress information
        """
        execution_id = handle.execution_id

        # Create update queue for this monitor
        update_queue: asyncio.Queue = asyncio.Queue()

        async with self._lock:
            if execution_id not in self._update_callbacks:
                self._update_callbacks[execution_id] = []
            self._update_callbacks[execution_id].append(update_queue.put)

        try:
            # Yield initial status
            yield ExecutionUpdate(
                execution_id=execution_id,
                status=handle.status,
                progress=0.0 if handle.status == ExecutionStatus.QUEUED else 5.0,
                message="Monitoring started",
            )

            # Stream updates
            while True:
                try:
                    update = await asyncio.wait_for(update_queue.get(), timeout=30.0)
                    yield update

                    if update.completed:
                        break

                except asyncio.TimeoutError:
                    # Check if still active
                    current = self._executions.get(execution_id)
                    if not current or not current.is_active():
                        break

                    # Yield heartbeat
                    yield ExecutionUpdate(
                        execution_id=execution_id,
                        status=current.status,
                        message="Heartbeat",
                    )

        finally:
            # Cleanup callback
            async with self._lock:
                if execution_id in self._update_callbacks:
                    callbacks = self._update_callbacks[execution_id]
                    if update_queue.put in callbacks:
                        callbacks.remove(update_queue.put)
                    if not callbacks:
                        del self._update_callbacks[execution_id]

    async def _emit_update(
        self,
        execution_id: str,
        update: ExecutionUpdate,
    ) -> None:
        """Emit update to all monitors."""
        async with self._lock:
            callbacks = self._update_callbacks.get(execution_id, [])

        for callback in callbacks:
            try:
                await callback(update)
            except Exception as e:
                logger.warning(f"Failed to emit update: {e}")

    async def get_status(
        self,
        execution_id: str,
    ) -> Optional[ExecutionHandle]:
        """
        Get execution status.

        Args:
            execution_id: Execution to check

        Returns:
            ExecutionHandle or None
        """
        async with self._lock:
            return self._executions.get(execution_id)

    async def get_result(
        self,
        execution_id: str,
    ) -> Optional[ExecutionResult]:
        """
        Get execution result.

        Args:
            execution_id: Execution to get result for

        Returns:
            ExecutionResult or None if not complete
        """
        async with self._lock:
            return self._results.get(execution_id)

    async def abort_execution(
        self,
        handle: ExecutionHandle,
    ) -> bool:
        """
        Abort a running execution.

        Args:
            handle: Execution to abort

        Returns:
            True if aborted, False if not abortable
        """
        execution_id = handle.execution_id

        async with self._lock:
            current = self._executions.get(execution_id)
            if not current:
                return False

            if current.is_active():
                current.status = ExecutionStatus.ABORTED

                # Cancel queue task if present
                if self._task_queue and current.task_id:
                    await self._task_queue.cancel(current.task_id)

                await self._emit_update(execution_id, ExecutionUpdate(
                    execution_id=execution_id,
                    status=ExecutionStatus.ABORTED,
                    message="Execution aborted",
                ))

                logger.info(f"Execution {execution_id} aborted")
                return True

            return False

    async def list_active(self) -> list:
        """List all active executions."""
        async with self._lock:
            return [h for h in self._executions.values() if h.is_active()]

    def get_metrics(self) -> Dict[str, Any]:
        """Get trigger metrics."""
        total = len(self._executions)
        completed = len(self._results)
        active = sum(1 for h in self._executions.values() if h.is_active())

        status_counts = {}
        for handle in self._executions.values():
            status = handle.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_executions": total,
            "completed": completed,
            "active": active,
            "by_status": status_counts,
            "concurrent_limit": self.config.max_concurrent,
        }


# Convenience function
def create_trigger(
    task_queue: Optional[Any] = None,
    config: Optional[TriggerConfig] = None,
) -> ExecutionTrigger:
    """
    Create an execution trigger.

    Args:
        task_queue: Optional TaskQueue
        config: Optional configuration

    Returns:
        Configured ExecutionTrigger
    """
    return ExecutionTrigger(task_queue=task_queue, config=config)
