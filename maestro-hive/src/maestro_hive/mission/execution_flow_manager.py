"""
Execution Flow Manager for orchestrating mission execution with teams.

Provides lifecycle management for mission execution including start, pause,
resume, and cancel operations with checkpoint and rollback support.
"""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ExecutionState(Enum):
    """Possible states of a mission execution."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExecutionConfig:
    """Configuration for mission execution."""
    timeout: int = 3600  # Maximum execution time in seconds
    max_retries: int = 3  # Maximum retry attempts for failed tasks
    checkpoint_interval: int = 300  # Checkpoint interval in seconds
    enable_rollback: bool = True  # Enable rollback on failure
    max_concurrent_tasks: int = 10  # Maximum parallel tasks
    progress_update_interval: int = 1000  # Progress update frequency in ms


@dataclass
class ExecutionResult:
    """Result of a mission execution."""
    execution_id: str
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    team_size: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    error_message: Optional[str] = None
    outputs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionStatus:
    """Current status of an execution."""
    state: ExecutionState
    progress: float  # 0.0 to 1.0
    current_task: Optional[str] = None
    elapsed_time: float = 0.0
    remaining_tasks: int = 0
    checkpoint_id: Optional[str] = None


class ExecutionError(Exception):
    """Exception raised during execution failures."""
    pass


class ExecutionFlowManager:
    """
    Orchestrates mission execution with teams.

    Provides lifecycle management for mission execution including:
    - Starting execution with teams
    - Pausing and resuming execution
    - Progress tracking and checkpointing
    - Rollback on failure

    Example:
        >>> config = ExecutionConfig(timeout=3600, max_retries=3)
        >>> manager = ExecutionFlowManager("mission-123", team, config)
        >>> result = await manager.start_execution()
        >>> status = await manager.get_status()
    """

    def __init__(
        self,
        mission_id: str,
        team: Any,  # Team type from teams module
        config: Optional[ExecutionConfig] = None
    ):
        """
        Initialize the execution flow manager.

        Args:
            mission_id: Unique identifier for the mission
            team: Team assigned to execute the mission
            config: Optional execution configuration
        """
        self.mission_id = mission_id
        self.team = team
        self.config = config or ExecutionConfig()

        self._execution_id: Optional[str] = None
        self._state = ExecutionState.PENDING
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._tasks: List[Dict[str, Any]] = []
        self._completed_tasks: List[str] = []
        self._failed_tasks: List[str] = []
        self._current_task: Optional[str] = None
        self._checkpoint_id: Optional[str] = None
        self._checkpoints: Dict[str, Dict[str, Any]] = {}
        self._outputs: Dict[str, Any] = {}
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused by default
        self._cancel_requested = False

        logger.info(f"ExecutionFlowManager initialized for mission {mission_id}")

    async def start_execution(self) -> ExecutionResult:
        """
        Start mission execution.

        Returns:
            ExecutionResult with execution_id, status, and start_time

        Raises:
            ExecutionError: If team is not ready or execution fails
        """
        if self._state not in (ExecutionState.PENDING, ExecutionState.CANCELLED):
            raise ExecutionError(f"Cannot start execution in state {self._state}")

        # Validate team is ready
        if not await self._validate_team_ready():
            raise ExecutionError("Team is not ready for execution")

        self._execution_id = str(uuid.uuid4())
        self._start_time = datetime.utcnow()
        self._state = ExecutionState.RUNNING
        self._cancel_requested = False

        logger.info(f"Starting execution {self._execution_id} for mission {self.mission_id}")
        await self._emit_event("execution_started", {
            "execution_id": self._execution_id,
            "mission_id": self.mission_id
        })

        try:
            # Load mission tasks
            self._tasks = await self._load_mission_tasks()

            # Execute tasks with timeout
            async with asyncio.timeout(self.config.timeout):
                await self._execute_tasks()

            self._state = ExecutionState.COMPLETED
            self._end_time = datetime.utcnow()

            logger.info(f"Execution {self._execution_id} completed successfully")
            await self._emit_event("execution_completed", {
                "execution_id": self._execution_id,
                "tasks_completed": len(self._completed_tasks)
            })

        except asyncio.TimeoutError:
            self._state = ExecutionState.FAILED
            self._end_time = datetime.utcnow()
            logger.error(f"Execution {self._execution_id} timed out")
            if self.config.enable_rollback:
                await self._rollback()
            raise ExecutionError("Execution timed out")

        except Exception as e:
            self._state = ExecutionState.FAILED
            self._end_time = datetime.utcnow()
            logger.error(f"Execution {self._execution_id} failed: {e}")
            if self.config.enable_rollback:
                await self._rollback()
            raise ExecutionError(f"Execution failed: {e}")

        return ExecutionResult(
            execution_id=self._execution_id,
            status=self._state.value,
            start_time=self._start_time,
            end_time=self._end_time,
            team_size=self._get_team_size(),
            tasks_completed=len(self._completed_tasks),
            tasks_failed=len(self._failed_tasks),
            outputs=self._outputs
        )

    async def pause_execution(self) -> bool:
        """
        Pause ongoing execution.

        Returns:
            True if paused successfully, False otherwise
        """
        if self._state != ExecutionState.RUNNING:
            logger.warning(f"Cannot pause execution in state {self._state}")
            return False

        self._pause_event.clear()
        self._state = ExecutionState.PAUSED

        # Create checkpoint
        self._checkpoint_id = await self._create_checkpoint()

        logger.info(f"Execution {self._execution_id} paused at checkpoint {self._checkpoint_id}")
        await self._emit_event("execution_paused", {
            "execution_id": self._execution_id,
            "checkpoint_id": self._checkpoint_id
        })

        return True

    async def resume_execution(self) -> bool:
        """
        Resume paused execution.

        Returns:
            True if resumed successfully, False otherwise
        """
        if self._state != ExecutionState.PAUSED:
            logger.warning(f"Cannot resume execution in state {self._state}")
            return False

        self._state = ExecutionState.RUNNING
        self._pause_event.set()

        logger.info(f"Execution {self._execution_id} resumed from checkpoint {self._checkpoint_id}")
        await self._emit_event("execution_resumed", {
            "execution_id": self._execution_id,
            "checkpoint_id": self._checkpoint_id
        })

        return True

    async def cancel_execution(self) -> bool:
        """
        Cancel ongoing execution.

        Returns:
            True if cancelled successfully, False otherwise
        """
        if self._state not in (ExecutionState.RUNNING, ExecutionState.PAUSED):
            logger.warning(f"Cannot cancel execution in state {self._state}")
            return False

        self._cancel_requested = True
        self._pause_event.set()  # Unblock if paused

        self._state = ExecutionState.CANCELLED
        self._end_time = datetime.utcnow()

        if self.config.enable_rollback:
            await self._rollback()

        logger.info(f"Execution {self._execution_id} cancelled")
        await self._emit_event("execution_cancelled", {
            "execution_id": self._execution_id
        })

        return True

    async def get_status(self) -> ExecutionStatus:
        """
        Get current execution status.

        Returns:
            ExecutionStatus with state, progress, and current task
        """
        total_tasks = len(self._tasks)
        completed = len(self._completed_tasks)
        progress = completed / total_tasks if total_tasks > 0 else 0.0

        elapsed = 0.0
        if self._start_time:
            end = self._end_time or datetime.utcnow()
            elapsed = (end - self._start_time).total_seconds()

        return ExecutionStatus(
            state=self._state,
            progress=progress,
            current_task=self._current_task,
            elapsed_time=elapsed,
            remaining_tasks=total_tasks - completed - len(self._failed_tasks),
            checkpoint_id=self._checkpoint_id
        )

    def on_event(self, event_type: str, handler: Callable) -> None:
        """
        Register an event handler.

        Args:
            event_type: Type of event to listen for
            handler: Callback function for the event
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)

    async def _validate_team_ready(self) -> bool:
        """Validate that the team is ready for execution."""
        if self.team is None:
            return False

        # Check team has required members
        if hasattr(self.team, 'members'):
            if not self.team.members:
                return False

        # Check team status if available
        if hasattr(self.team, 'is_ready'):
            return await self.team.is_ready() if asyncio.iscoroutinefunction(self.team.is_ready) else self.team.is_ready()

        return True

    async def _load_mission_tasks(self) -> List[Dict[str, Any]]:
        """Load tasks for the mission."""
        # In a real implementation, this would load from mission definition
        # For now, return sample tasks structure
        return [
            {"id": f"task_{i}", "name": f"Task {i}", "status": "pending"}
            for i in range(5)
        ]

    async def _execute_tasks(self) -> None:
        """Execute all mission tasks."""
        semaphore = asyncio.Semaphore(self.config.max_concurrent_tasks)

        async def execute_with_limit(task: Dict[str, Any]) -> None:
            async with semaphore:
                await self._execute_single_task(task)

        # Execute tasks with concurrency limit
        pending_tasks = [t for t in self._tasks if t["id"] not in self._completed_tasks]

        for task in pending_tasks:
            if self._cancel_requested:
                break

            # Wait if paused
            await self._pause_event.wait()

            await execute_with_limit(task)

            # Create checkpoint if interval elapsed
            if self._should_checkpoint():
                self._checkpoint_id = await self._create_checkpoint()

    async def _execute_single_task(self, task: Dict[str, Any]) -> None:
        """Execute a single task with retry logic."""
        task_id = task["id"]
        self._current_task = task_id

        logger.debug(f"Executing task {task_id}")
        await self._emit_event("task_started", {"task_id": task_id})

        retries = 0
        while retries <= self.config.max_retries:
            try:
                # Execute task (simulated)
                await asyncio.sleep(0.1)  # Simulate work

                self._completed_tasks.append(task_id)
                task["status"] = "completed"

                await self._emit_event("task_completed", {"task_id": task_id})
                return

            except Exception as e:
                retries += 1
                logger.warning(f"Task {task_id} failed (attempt {retries}): {e}")

                if retries > self.config.max_retries:
                    self._failed_tasks.append(task_id)
                    task["status"] = "failed"
                    await self._emit_event("task_failed", {
                        "task_id": task_id,
                        "error": str(e)
                    })
                    raise

                await asyncio.sleep(1)  # Wait before retry

    def _should_checkpoint(self) -> bool:
        """Check if a checkpoint should be created."""
        if not self._start_time or not self._checkpoint_id:
            return True

        # Check interval since last checkpoint
        last_checkpoint = self._checkpoints.get(self._checkpoint_id, {})
        last_time = last_checkpoint.get("timestamp", self._start_time)
        elapsed = (datetime.utcnow() - last_time).total_seconds()

        return elapsed >= self.config.checkpoint_interval

    async def _create_checkpoint(self) -> str:
        """Create an execution checkpoint."""
        checkpoint_id = str(uuid.uuid4())

        self._checkpoints[checkpoint_id] = {
            "timestamp": datetime.utcnow(),
            "completed_tasks": self._completed_tasks.copy(),
            "failed_tasks": self._failed_tasks.copy(),
            "outputs": self._outputs.copy(),
            "current_task": self._current_task
        }

        logger.info(f"Created checkpoint {checkpoint_id}")
        return checkpoint_id

    async def _rollback(self) -> None:
        """Rollback execution to last checkpoint."""
        if not self._checkpoint_id or self._checkpoint_id not in self._checkpoints:
            logger.warning("No checkpoint available for rollback")
            return

        checkpoint = self._checkpoints[self._checkpoint_id]
        logger.info(f"Rolling back to checkpoint {self._checkpoint_id}")

        # Restore state from checkpoint
        # In a real implementation, this would undo task effects
        await self._emit_event("execution_rollback", {
            "checkpoint_id": self._checkpoint_id,
            "tasks_rolled_back": len(self._completed_tasks) - len(checkpoint["completed_tasks"])
        })

    def _get_team_size(self) -> int:
        """Get the size of the assigned team."""
        if hasattr(self.team, 'members'):
            return len(self.team.members)
        if hasattr(self.team, '__len__'):
            return len(self.team)
        return 1

    async def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event to registered handlers."""
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Error in event handler for {event_type}: {e}")
