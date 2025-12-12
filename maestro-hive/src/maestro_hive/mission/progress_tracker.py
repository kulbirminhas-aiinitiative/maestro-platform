"""
Progress Tracker for real-time mission execution monitoring.

Provides event-driven progress updates with WebSocket support for
real-time status propagation to clients.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of a tracked task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ProgressUpdate:
    """A progress update event."""
    timestamp: datetime
    task_id: str
    status: TaskStatus
    progress: float  # 0.0 to 1.0
    message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProgressReport:
    """Summary report of execution progress."""
    total_tasks: int
    completed: int
    pending: int
    in_progress: int
    failed: int
    percentage: float
    estimated_remaining: Optional[float] = None  # Seconds
    current_tasks: List[str] = field(default_factory=list)


class ProgressTracker:
    """
    Real-time progress tracking for mission execution.

    Features:
    - Event-driven updates via callbacks
    - WebSocket-ready update streaming
    - Batch update support for efficiency
    - Progress persistence support

    Example:
        >>> tracker = ProgressTracker("execution-123")
        >>> tracker.on_update(lambda u: print(f"Task {u.task_id}: {u.status}"))
        >>> await tracker.track_task("task-1", TaskStatus.IN_PROGRESS)
        >>> report = await tracker.get_progress()
    """

    def __init__(
        self,
        execution_id: str,
        update_interval: int = 1000,
        batch_size: int = 50,
        persistence: Optional[str] = None,
        ttl: int = 86400
    ):
        """
        Initialize the progress tracker.

        Args:
            execution_id: ID of the execution to track
            update_interval: Minimum interval between updates (ms)
            batch_size: Maximum updates to batch together
            persistence: Persistence backend ('redis', 'memory', or None)
            ttl: Time-to-live for persisted data in seconds
        """
        self.execution_id = execution_id
        self.update_interval = update_interval
        self.batch_size = batch_size
        self.persistence = persistence
        self.ttl = ttl

        self._tasks: Dict[str, TaskStatus] = {}
        self._task_progress: Dict[str, float] = {}
        self._task_messages: Dict[str, str] = {}
        self._task_metadata: Dict[str, Dict[str, Any]] = {}
        self._update_handlers: List[Callable[[ProgressUpdate], Any]] = []
        self._batch_handlers: List[Callable[[List[ProgressUpdate]], Any]] = []
        self._update_queue: List[ProgressUpdate] = []
        self._last_flush: datetime = datetime.utcnow()
        self._lock = asyncio.Lock()
        self._subscribers: Set[asyncio.Queue] = set()
        self._start_time: Optional[datetime] = None
        self._task_durations: Dict[str, float] = {}

        logger.info(f"ProgressTracker initialized for execution {execution_id}")

    async def track_task(
        self,
        task_id: str,
        status: TaskStatus,
        progress: float = 0.0,
        message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update tracking status for a task.

        Args:
            task_id: ID of the task to track
            status: New status of the task
            progress: Task progress (0.0 to 1.0)
            message: Optional status message
            metadata: Optional additional metadata
        """
        if self._start_time is None:
            self._start_time = datetime.utcnow()

        async with self._lock:
            previous_status = self._tasks.get(task_id)
            self._tasks[task_id] = status
            self._task_progress[task_id] = progress

            if message:
                self._task_messages[task_id] = message
            if metadata:
                self._task_metadata[task_id] = metadata

            # Track duration for completed tasks
            if status == TaskStatus.COMPLETED and task_id not in self._task_durations:
                # Calculate average duration
                completed_count = sum(1 for s in self._tasks.values() if s == TaskStatus.COMPLETED)
                if completed_count > 0 and self._start_time:
                    elapsed = (datetime.utcnow() - self._start_time).total_seconds()
                    self._task_durations[task_id] = elapsed / completed_count

        update = ProgressUpdate(
            timestamp=datetime.utcnow(),
            task_id=task_id,
            status=status,
            progress=progress,
            message=message,
            metadata=metadata or {}
        )

        # Queue update for batching
        self._update_queue.append(update)

        # Emit individual update
        await self._emit_update(update)

        # Check if we should flush batch
        if len(self._update_queue) >= self.batch_size or self._should_flush():
            await self._flush_batch()

        # Persist if enabled
        if self.persistence:
            await self._persist_update(update)

        logger.debug(f"Task {task_id} tracked: {status.value} ({progress:.1%})")

    async def get_progress(self) -> ProgressReport:
        """
        Get current execution progress report.

        Returns:
            ProgressReport with task counts and percentage
        """
        async with self._lock:
            total = len(self._tasks)
            completed = sum(1 for s in self._tasks.values() if s == TaskStatus.COMPLETED)
            pending = sum(1 for s in self._tasks.values() if s == TaskStatus.PENDING)
            in_progress = sum(1 for s in self._tasks.values() if s == TaskStatus.IN_PROGRESS)
            failed = sum(1 for s in self._tasks.values() if s == TaskStatus.FAILED)

            percentage = (completed / total * 100) if total > 0 else 0.0

            current_tasks = [
                task_id for task_id, status in self._tasks.items()
                if status == TaskStatus.IN_PROGRESS
            ]

            # Estimate remaining time
            estimated_remaining = None
            if completed > 0 and self._start_time and pending + in_progress > 0:
                elapsed = (datetime.utcnow() - self._start_time).total_seconds()
                avg_time_per_task = elapsed / completed
                estimated_remaining = avg_time_per_task * (pending + in_progress)

        return ProgressReport(
            total_tasks=total,
            completed=completed,
            pending=pending,
            in_progress=in_progress,
            failed=failed,
            percentage=percentage,
            estimated_remaining=estimated_remaining,
            current_tasks=current_tasks
        )

    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get status of a specific task.

        Args:
            task_id: ID of the task

        Returns:
            TaskStatus if task exists, None otherwise
        """
        return self._tasks.get(task_id)

    async def get_task_details(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a task.

        Args:
            task_id: ID of the task

        Returns:
            Dictionary with task details or None
        """
        if task_id not in self._tasks:
            return None

        return {
            "task_id": task_id,
            "status": self._tasks[task_id].value,
            "progress": self._task_progress.get(task_id, 0.0),
            "message": self._task_messages.get(task_id),
            "metadata": self._task_metadata.get(task_id, {})
        }

    def on_update(self, handler: Callable[[ProgressUpdate], Any]) -> None:
        """
        Register a handler for individual progress updates.

        Args:
            handler: Callback function receiving ProgressUpdate
        """
        self._update_handlers.append(handler)

    def on_batch_update(self, handler: Callable[[List[ProgressUpdate]], Any]) -> None:
        """
        Register a handler for batched progress updates.

        Args:
            handler: Callback function receiving list of updates
        """
        self._batch_handlers.append(handler)

    async def subscribe(self) -> asyncio.Queue:
        """
        Subscribe to progress updates via async queue.

        Returns:
            AsyncIO Queue that will receive updates

        Example:
            >>> queue = await tracker.subscribe()
            >>> update = await queue.get()
        """
        queue: asyncio.Queue = asyncio.Queue()
        self._subscribers.add(queue)
        logger.debug(f"New subscriber added. Total: {len(self._subscribers)}")
        return queue

    async def unsubscribe(self, queue: asyncio.Queue) -> None:
        """
        Unsubscribe from progress updates.

        Args:
            queue: Queue returned from subscribe()
        """
        self._subscribers.discard(queue)
        logger.debug(f"Subscriber removed. Total: {len(self._subscribers)}")

    async def reset(self) -> None:
        """Reset the tracker state."""
        async with self._lock:
            self._tasks.clear()
            self._task_progress.clear()
            self._task_messages.clear()
            self._task_metadata.clear()
            self._update_queue.clear()
            self._task_durations.clear()
            self._start_time = None

        logger.info(f"ProgressTracker reset for execution {self.execution_id}")

    async def _emit_update(self, update: ProgressUpdate) -> None:
        """Emit update to all handlers and subscribers."""
        # Call individual update handlers
        for handler in self._update_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(update)
                else:
                    handler(update)
            except Exception as e:
                logger.error(f"Error in update handler: {e}")

        # Send to subscribers
        for queue in self._subscribers:
            try:
                await queue.put(update)
            except Exception as e:
                logger.error(f"Error sending to subscriber: {e}")

    async def _flush_batch(self) -> None:
        """Flush queued updates as a batch."""
        if not self._update_queue:
            return

        batch = self._update_queue.copy()
        self._update_queue.clear()
        self._last_flush = datetime.utcnow()

        # Call batch handlers
        for handler in self._batch_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(batch)
                else:
                    handler(batch)
            except Exception as e:
                logger.error(f"Error in batch handler: {e}")

        logger.debug(f"Flushed batch of {len(batch)} updates")

    def _should_flush(self) -> bool:
        """Check if batch should be flushed based on interval."""
        elapsed_ms = (datetime.utcnow() - self._last_flush).total_seconds() * 1000
        return elapsed_ms >= self.update_interval

    async def _persist_update(self, update: ProgressUpdate) -> None:
        """Persist update to configured backend."""
        if self.persistence == "redis":
            await self._persist_to_redis(update)
        elif self.persistence == "memory":
            pass  # Already in memory

    async def _persist_to_redis(self, update: ProgressUpdate) -> None:
        """Persist update to Redis (stub for integration)."""
        # In production, this would connect to Redis
        logger.debug(f"Would persist to Redis: {update.task_id}")
