"""Tests for ProgressTracker."""

import asyncio
import pytest
from datetime import datetime

from maestro_hive.mission.progress_tracker import (
    ProgressTracker,
    ProgressReport,
    TaskStatus,
    ProgressUpdate,
)


class TestTaskStatus:
    """Tests for TaskStatus enum."""

    def test_all_statuses_defined(self):
        """Test all expected statuses are defined."""
        statuses = [s.value for s in TaskStatus]
        assert "pending" in statuses
        assert "in_progress" in statuses
        assert "completed" in statuses
        assert "failed" in statuses
        assert "skipped" in statuses


class TestProgressUpdate:
    """Tests for ProgressUpdate dataclass."""

    def test_create_update(self):
        """Test creating a progress update."""
        update = ProgressUpdate(
            timestamp=datetime.utcnow(),
            task_id="task-123",
            status=TaskStatus.IN_PROGRESS,
            progress=0.5,
            message="Processing..."
        )

        assert update.task_id == "task-123"
        assert update.status == TaskStatus.IN_PROGRESS
        assert update.progress == 0.5
        assert update.message == "Processing..."


class TestProgressReport:
    """Tests for ProgressReport dataclass."""

    def test_create_report(self):
        """Test creating a progress report."""
        report = ProgressReport(
            total_tasks=10,
            completed=5,
            pending=3,
            in_progress=2,
            failed=0,
            percentage=50.0
        )

        assert report.total_tasks == 10
        assert report.completed == 5
        assert report.percentage == 50.0


class TestProgressTracker:
    """Tests for ProgressTracker class."""

    @pytest.fixture
    def tracker(self):
        """Create a ProgressTracker instance."""
        return ProgressTracker(
            execution_id="exec-123",
            update_interval=100,
            batch_size=10
        )

    def test_initialization(self, tracker):
        """Test tracker initialization."""
        assert tracker.execution_id == "exec-123"
        assert tracker.update_interval == 100
        assert tracker.batch_size == 10

    @pytest.mark.asyncio
    async def test_track_task_pending(self, tracker):
        """Test tracking a pending task."""
        await tracker.track_task("task-1", TaskStatus.PENDING)

        status = await tracker.get_task_status("task-1")
        assert status == TaskStatus.PENDING

    @pytest.mark.asyncio
    async def test_track_task_in_progress(self, tracker):
        """Test tracking task in progress."""
        await tracker.track_task(
            "task-1",
            TaskStatus.IN_PROGRESS,
            progress=0.5,
            message="Working..."
        )

        status = await tracker.get_task_status("task-1")
        assert status == TaskStatus.IN_PROGRESS

        details = await tracker.get_task_details("task-1")
        assert details["progress"] == 0.5
        assert details["message"] == "Working..."

    @pytest.mark.asyncio
    async def test_track_task_completed(self, tracker):
        """Test tracking completed task."""
        await tracker.track_task("task-1", TaskStatus.COMPLETED, progress=1.0)

        status = await tracker.get_task_status("task-1")
        assert status == TaskStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_get_progress(self, tracker):
        """Test getting progress report."""
        await tracker.track_task("task-1", TaskStatus.COMPLETED)
        await tracker.track_task("task-2", TaskStatus.IN_PROGRESS)
        await tracker.track_task("task-3", TaskStatus.PENDING)
        await tracker.track_task("task-4", TaskStatus.FAILED)

        report = await tracker.get_progress()

        assert report.total_tasks == 4
        assert report.completed == 1
        assert report.in_progress == 1
        assert report.pending == 1
        assert report.failed == 1
        assert report.percentage == 25.0

    @pytest.mark.asyncio
    async def test_get_progress_empty(self, tracker):
        """Test getting progress with no tasks."""
        report = await tracker.get_progress()

        assert report.total_tasks == 0
        assert report.percentage == 0.0

    @pytest.mark.asyncio
    async def test_get_task_status_not_found(self, tracker):
        """Test getting status of non-existent task."""
        status = await tracker.get_task_status("nonexistent")
        assert status is None

    @pytest.mark.asyncio
    async def test_get_task_details_not_found(self, tracker):
        """Test getting details of non-existent task."""
        details = await tracker.get_task_details("nonexistent")
        assert details is None

    @pytest.mark.asyncio
    async def test_update_handler(self, tracker):
        """Test update handler registration."""
        updates = []

        def handler(update):
            updates.append(update)

        tracker.on_update(handler)
        await tracker.track_task("task-1", TaskStatus.IN_PROGRESS)

        assert len(updates) == 1
        assert updates[0].task_id == "task-1"

    @pytest.mark.asyncio
    async def test_async_update_handler(self, tracker):
        """Test async update handler."""
        updates = []

        async def handler(update):
            updates.append(update)

        tracker.on_update(handler)
        await tracker.track_task("task-1", TaskStatus.IN_PROGRESS)

        assert len(updates) == 1

    @pytest.mark.asyncio
    async def test_batch_handler(self, tracker):
        """Test batch handler."""
        batches = []

        def batch_handler(batch):
            batches.append(batch)

        tracker.on_batch_update(batch_handler)

        # Track multiple tasks
        for i in range(15):
            await tracker.track_task(f"task-{i}", TaskStatus.COMPLETED)

        # Flush any remaining
        await tracker._flush_batch()

        assert len(batches) > 0

    @pytest.mark.asyncio
    async def test_subscribe(self, tracker):
        """Test subscription queue."""
        queue = await tracker.subscribe()

        await tracker.track_task("task-1", TaskStatus.IN_PROGRESS)

        update = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert update.task_id == "task-1"

        await tracker.unsubscribe(queue)

    @pytest.mark.asyncio
    async def test_reset(self, tracker):
        """Test tracker reset."""
        await tracker.track_task("task-1", TaskStatus.COMPLETED)
        await tracker.track_task("task-2", TaskStatus.IN_PROGRESS)

        await tracker.reset()

        report = await tracker.get_progress()
        assert report.total_tasks == 0

    @pytest.mark.asyncio
    async def test_estimated_remaining(self, tracker):
        """Test estimated remaining time calculation."""
        # Track some completed tasks
        await tracker.track_task("task-1", TaskStatus.COMPLETED)
        await asyncio.sleep(0.1)
        await tracker.track_task("task-2", TaskStatus.COMPLETED)
        await tracker.track_task("task-3", TaskStatus.PENDING)

        report = await tracker.get_progress()

        # Should have an estimate if we have completed tasks
        assert report.estimated_remaining is not None or report.pending == 0

    @pytest.mark.asyncio
    async def test_current_tasks_in_report(self, tracker):
        """Test current tasks appear in progress report."""
        await tracker.track_task("task-1", TaskStatus.IN_PROGRESS)
        await tracker.track_task("task-2", TaskStatus.IN_PROGRESS)
        await tracker.track_task("task-3", TaskStatus.COMPLETED)

        report = await tracker.get_progress()

        assert "task-1" in report.current_tasks
        assert "task-2" in report.current_tasks
        assert "task-3" not in report.current_tasks

    @pytest.mark.asyncio
    async def test_task_metadata(self, tracker):
        """Test task metadata storage."""
        await tracker.track_task(
            "task-1",
            TaskStatus.IN_PROGRESS,
            metadata={"priority": "high", "retries": 2}
        )

        details = await tracker.get_task_details("task-1")
        assert details["metadata"]["priority"] == "high"
        assert details["metadata"]["retries"] == 2
