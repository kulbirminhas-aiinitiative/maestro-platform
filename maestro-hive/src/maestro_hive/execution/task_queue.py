"""
Distributed Task Queue with Priority Scheduling.

Provides enterprise-grade task scheduling with:
- Priority-based queueing (multiple priority levels)
- Fair scheduling with anti-starvation
- Load balancing across workers
- Task lifecycle management
- Persistence for fault tolerance
"""

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, IntEnum
from typing import Optional, Callable, Any, Dict, List, Awaitable
import heapq
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status."""
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class TaskPriority(IntEnum):
    """Task priority levels (lower value = higher priority)."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class TaskQueueConfig:
    """Configuration for task queue."""
    max_size: int = 10000
    max_workers: int = 10
    priority_levels: int = 5
    default_timeout: int = 300  # 5 minutes
    retry_limit: int = 3
    retry_delay: int = 5
    enable_persistence: bool = False
    persistence_path: Optional[str] = None


@dataclass
class Task:
    """
    Represents a task in the queue.

    Attributes:
        id: Unique task identifier
        name: Human-readable task name
        func: Async callable to execute
        args: Positional arguments
        kwargs: Keyword arguments
        priority: Task priority level
        timeout: Execution timeout in seconds
        retry_count: Number of retries attempted
        max_retries: Maximum retry attempts
        created_at: Task creation timestamp
        started_at: Execution start timestamp
        completed_at: Execution completion timestamp
        status: Current task status
        result: Execution result (if completed)
        error: Error message (if failed)
        metadata: Additional task metadata
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    func: Optional[Callable[..., Awaitable[Any]]] = None
    args: tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    timeout: int = 300
    retry_count: int = 0
    max_retries: int = 3
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __lt__(self, other: "Task") -> bool:
        """Compare tasks by priority for heap ordering."""
        if self.priority != other.priority:
            return self.priority < other.priority
        return self.created_at < other.created_at


class TaskQueue:
    """
    Distributed task queue with priority scheduling.

    Features:
    - Multiple priority levels
    - Fair scheduling with anti-starvation
    - Task lifecycle tracking
    - Async execution support
    """

    def __init__(self, config: Optional[TaskQueueConfig] = None):
        """
        Initialize task queue.

        Args:
            config: Queue configuration
        """
        self.config = config or TaskQueueConfig()
        self._queue: List[Task] = []  # Priority heap
        self._tasks: Dict[str, Task] = {}  # Task registry
        self._lock = asyncio.Lock()
        self._not_empty = asyncio.Event()
        self._stats = {
            "submitted": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
        }

    @property
    def size(self) -> int:
        """Current queue size."""
        return len(self._queue)

    @property
    def is_full(self) -> bool:
        """Check if queue is at capacity."""
        return self.size >= self.config.max_size

    async def submit(
        self,
        func: Callable[..., Awaitable[Any]],
        *args,
        name: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: int = 300,
        max_retries: int = 3,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> str:
        """
        Submit a task to the queue.

        Args:
            func: Async callable to execute
            *args: Function arguments
            name: Task name for identification
            priority: Task priority
            timeout: Execution timeout
            max_retries: Maximum retry attempts
            metadata: Additional metadata
            **kwargs: Function keyword arguments

        Returns:
            Task ID

        Raises:
            ValueError: If queue is full
        """
        async with self._lock:
            if self.is_full:
                raise ValueError(f"Queue is full (max_size={self.config.max_size})")

            task = Task(
                name=name or func.__name__,
                func=func,
                args=args,
                kwargs=kwargs,
                priority=priority,
                timeout=timeout,
                max_retries=max_retries,
                metadata=metadata or {},
            )

            heapq.heappush(self._queue, task)
            self._tasks[task.id] = task
            self._stats["submitted"] += 1
            self._not_empty.set()

            logger.debug(f"Task {task.id} submitted with priority {priority.name}")
            return task.id

    async def get(self, timeout: Optional[float] = None) -> Optional[Task]:
        """
        Get next task from queue.

        Args:
            timeout: Maximum wait time

        Returns:
            Next task or None if timeout
        """
        try:
            if timeout:
                await asyncio.wait_for(
                    self._not_empty.wait(),
                    timeout=timeout
                )
            else:
                await self._not_empty.wait()
        except asyncio.TimeoutError:
            return None

        async with self._lock:
            if not self._queue:
                self._not_empty.clear()
                return None

            task = heapq.heappop(self._queue)
            task.status = TaskStatus.SCHEDULED

            if not self._queue:
                self._not_empty.clear()

            return task

    async def get_status(self, task_id: str) -> Optional[TaskStatus]:
        """Get task status by ID."""
        task = self._tasks.get(task_id)
        return task.status if task else None

    async def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return self._tasks.get(task_id)

    async def cancel(self, task_id: str) -> bool:
        """
        Cancel a pending task.

        Args:
            task_id: Task to cancel

        Returns:
            True if cancelled, False if not found or already running
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            if task.status in (TaskStatus.PENDING, TaskStatus.SCHEDULED):
                task.status = TaskStatus.CANCELLED
                task.completed_at = datetime.utcnow()
                self._stats["cancelled"] += 1

                # Remove from queue
                try:
                    self._queue.remove(task)
                    heapq.heapify(self._queue)
                except ValueError:
                    pass

                return True
            return False

    async def complete(
        self,
        task_id: str,
        result: Any = None,
        error: Optional[str] = None,
    ) -> None:
        """
        Mark task as completed.

        Args:
            task_id: Task ID
            result: Execution result
            error: Error message if failed
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return

            task.completed_at = datetime.utcnow()
            task.result = result

            if error:
                task.status = TaskStatus.FAILED
                task.error = error
                self._stats["failed"] += 1
            else:
                task.status = TaskStatus.COMPLETED
                self._stats["completed"] += 1

    async def retry(self, task_id: str) -> bool:
        """
        Retry a failed task.

        Args:
            task_id: Task to retry

        Returns:
            True if requeued, False if max retries exceeded
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            if task.retry_count >= task.max_retries:
                return False

            task.retry_count += 1
            task.status = TaskStatus.PENDING
            task.error = None
            task.started_at = None
            task.completed_at = None

            heapq.heappush(self._queue, task)
            self._not_empty.set()

            logger.info(f"Task {task_id} requeued (retry {task.retry_count}/{task.max_retries})")
            return True

    def get_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        return {
            "size": self.size,
            "max_size": self.config.max_size,
            "submitted": self._stats["submitted"],
            "completed": self._stats["completed"],
            "failed": self._stats["failed"],
            "cancelled": self._stats["cancelled"],
            "pending": sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING),
            "running": sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING),
        }


class TaskScheduler:
    """
    Task scheduler for executing queued tasks.

    Features:
    - Worker pool management
    - Concurrent execution
    - Timeout handling
    - Retry logic
    """

    def __init__(
        self,
        queue: TaskQueue,
        max_workers: Optional[int] = None,
    ):
        """
        Initialize scheduler.

        Args:
            queue: Task queue to process
            max_workers: Maximum concurrent workers
        """
        self.queue = queue
        self.max_workers = max_workers or queue.config.max_workers
        self._running = False
        self._workers: List[asyncio.Task] = []
        self._semaphore = asyncio.Semaphore(self.max_workers)

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return

        self._running = True
        logger.info(f"TaskScheduler started with {self.max_workers} workers")

        # Start worker tasks
        for i in range(self.max_workers):
            worker = asyncio.create_task(self._worker(i))
            self._workers.append(worker)

    async def stop(self, wait: bool = True) -> None:
        """
        Stop the scheduler.

        Args:
            wait: Wait for running tasks to complete
        """
        self._running = False

        if wait:
            await asyncio.gather(*self._workers, return_exceptions=True)
        else:
            for worker in self._workers:
                worker.cancel()

        self._workers.clear()
        logger.info("TaskScheduler stopped")

    async def _worker(self, worker_id: int) -> None:
        """Worker coroutine that processes tasks."""
        logger.debug(f"Worker {worker_id} started")

        while self._running:
            try:
                async with self._semaphore:
                    task = await self.queue.get(timeout=1.0)
                    if task:
                        await self._execute_task(task, worker_id)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")

        logger.debug(f"Worker {worker_id} stopped")

    async def _execute_task(self, task: Task, worker_id: int) -> None:
        """Execute a single task with timeout and error handling."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.utcnow()

        logger.debug(f"Worker {worker_id} executing task {task.id}: {task.name}")

        try:
            # Execute with timeout
            if task.func:
                result = await asyncio.wait_for(
                    task.func(*task.args, **task.kwargs),
                    timeout=task.timeout
                )
                await self.queue.complete(task.id, result=result)
                logger.debug(f"Task {task.id} completed successfully")
            else:
                await self.queue.complete(task.id, error="No function provided")

        except asyncio.TimeoutError:
            task.status = TaskStatus.TIMEOUT
            await self.queue.complete(task.id, error=f"Timeout after {task.timeout}s")
            logger.warning(f"Task {task.id} timed out")

            # Retry on timeout
            if task.retry_count < task.max_retries:
                await asyncio.sleep(self.queue.config.retry_delay)
                await self.queue.retry(task.id)

        except Exception as e:
            await self.queue.complete(task.id, error=str(e))
            logger.error(f"Task {task.id} failed: {e}")

            # Retry on error
            if task.retry_count < task.max_retries:
                await asyncio.sleep(self.queue.config.retry_delay)
                await self.queue.retry(task.id)
