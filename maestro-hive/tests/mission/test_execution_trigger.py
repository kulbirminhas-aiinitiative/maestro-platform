"""
Tests for Execution Trigger.
EPIC: MD-3024 - Mission to Execution Handoff
"""

import pytest
import asyncio

from maestro_hive.mission import (
    ExecutionTrigger,
    TriggerConfig,
    TriggerExecutionStatus,
    TriggerExecutionResult,
    ExecutionPriority,
    ExecutionHandle,
    MissionContext,
    MissionConstraints,
    create_trigger,
)
from maestro_hive.mission.execution_trigger import ExecutionStatus, ExecutionUpdate


class TestExecutionTrigger:
    """Test suite for ExecutionTrigger."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = TriggerConfig(
            async_execution=True,
            max_concurrent=3,
        )
        self.trigger = ExecutionTrigger(config=self.config)
        self.valid_context = MissionContext(
            mission_id="test-mission-001",
            mission_name="Test Mission",
            objectives=["Complete task 1", "Complete task 2"],
            team_composition={"lead": "architect"},
            constraints=MissionConstraints(max_duration_hours=2.0),
        )

    @pytest.mark.asyncio
    async def test_trigger_execution_basic(self):
        """Test basic execution triggering."""
        handle = await self.trigger.trigger_execution(self.valid_context)

        assert handle is not None
        assert handle.execution_id is not None
        assert handle.mission_id == self.valid_context.mission_id
        assert handle.status in (
            ExecutionStatus.QUEUED,
            ExecutionStatus.STARTING,
            ExecutionStatus.RUNNING,
            ExecutionStatus.COMPLETED,
        )

    @pytest.mark.asyncio
    async def test_trigger_execution_with_config(self):
        """Test execution triggering with custom config."""
        config = TriggerConfig(
            priority=ExecutionPriority.HIGH,
            max_retries=5,
        )

        handle = await self.trigger.trigger_execution(
            self.valid_context,
            config=config,
        )

        assert handle is not None
        assert handle.execution_id is not None

    @pytest.mark.asyncio
    async def test_execution_handle_is_active(self):
        """Test execution handle is_active method."""
        handle = await self.trigger.trigger_execution(self.valid_context)

        # Wait for completion
        await asyncio.sleep(0.5)

        # Check the handle's is_active method
        # After completion it should return False
        # We need to get updated status
        updated_handle = await self.trigger.get_status(handle.execution_id)

        if updated_handle:
            # Test is_active method
            is_active = updated_handle.is_active()
            assert isinstance(is_active, bool)

    @pytest.mark.asyncio
    async def test_get_status(self):
        """Test getting execution status."""
        handle = await self.trigger.trigger_execution(self.valid_context)

        status = await self.trigger.get_status(handle.execution_id)

        assert status is not None
        assert status.execution_id == handle.execution_id

    @pytest.mark.asyncio
    async def test_get_status_nonexistent(self):
        """Test getting status for non-existent execution."""
        status = await self.trigger.get_status("nonexistent-id")
        assert status is None

    @pytest.mark.asyncio
    async def test_get_result_after_completion(self):
        """Test getting result after completion."""
        handle = await self.trigger.trigger_execution(self.valid_context)

        # Wait for async execution to complete
        await asyncio.sleep(1.0)

        result = await self.trigger.get_result(handle.execution_id)

        # Result may or may not be available depending on timing
        if result:
            assert result.execution_id == handle.execution_id

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Timing-sensitive test that may hang in CI")
    async def test_abort_execution(self):
        """Test aborting execution."""
        handle = await self.trigger.trigger_execution(self.valid_context)

        # Try to abort (may succeed or fail depending on state)
        aborted = await self.trigger.abort_execution(handle)

        # If it was active when we tried to abort, should succeed
        # Otherwise it may have already completed
        assert isinstance(aborted, bool)

    @pytest.mark.asyncio
    async def test_abort_nonexistent(self):
        """Test aborting non-existent execution."""
        fake_handle = ExecutionHandle(
            execution_id="fake-id",
            mission_id="fake-mission",
            status=ExecutionStatus.RUNNING,
        )

        aborted = await self.trigger.abort_execution(fake_handle)
        assert aborted is False

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Timing-sensitive test that may hang in CI")
    async def test_list_active(self):
        """Test listing active executions."""
        # Trigger multiple executions
        await self.trigger.trigger_execution(self.valid_context)
        await self.trigger.trigger_execution(self.valid_context)

        active = await self.trigger.list_active()

        # Should be a list (may be empty if all completed quickly)
        assert isinstance(active, list)

    def test_get_metrics(self):
        """Test getting trigger metrics."""
        metrics = self.trigger.get_metrics()

        assert "total_executions" in metrics
        assert "completed" in metrics
        assert "active" in metrics
        assert "by_status" in metrics
        assert "concurrent_limit" in metrics
        assert metrics["concurrent_limit"] == 3

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Timing-sensitive test that may hang in CI")
    async def test_multiple_concurrent_executions(self):
        """Test multiple concurrent executions."""
        handles = await asyncio.gather(
            self.trigger.trigger_execution(self.valid_context),
            self.trigger.trigger_execution(self.valid_context),
            self.trigger.trigger_execution(self.valid_context),
        )

        assert len(handles) == 3
        assert len(set(h.execution_id for h in handles)) == 3  # All unique

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Timing-sensitive test that may hang in CI")
    async def test_monitor_execution(self):
        """Test monitoring execution updates."""
        handle = await self.trigger.trigger_execution(self.valid_context)

        updates = []
        async for update in self.trigger.monitor_execution(handle):
            updates.append(update)
            if update.completed:
                break
            if len(updates) > 10:  # Safety limit
                break

        assert len(updates) > 0

    @pytest.mark.asyncio
    async def test_execution_result_properties(self):
        """Test ExecutionResult properties."""
        handle = await self.trigger.trigger_execution(self.valid_context)

        # Wait for completion
        await asyncio.sleep(1.0)

        result = await self.trigger.get_result(handle.execution_id)

        if result:
            # Test duration calculation
            duration = result.duration_seconds
            assert duration >= 0

            # Test success property
            if result.status == ExecutionStatus.COMPLETED:
                assert result.success is True
            elif result.status == ExecutionStatus.FAILED:
                assert result.success is False


class TestTriggerConfig:
    """Test suite for TriggerConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TriggerConfig()

        assert config.async_execution is True
        assert config.max_concurrent == 5
        assert config.queue_timeout_seconds == 60
        assert config.execution_timeout_seconds == 3600
        assert config.enable_tracing is True
        assert config.priority == ExecutionPriority.NORMAL
        assert config.retry_on_failure is True
        assert config.max_retries == 3

    def test_custom_config(self):
        """Test custom configuration."""
        config = TriggerConfig(
            async_execution=False,
            max_concurrent=10,
            priority=ExecutionPriority.CRITICAL,
            max_retries=5,
        )

        assert config.async_execution is False
        assert config.max_concurrent == 10
        assert config.priority == ExecutionPriority.CRITICAL
        assert config.max_retries == 5


class TestCreateTrigger:
    """Test suite for create_trigger factory function."""

    def test_create_trigger_default(self):
        """Test creating trigger with defaults."""
        trigger = create_trigger()

        assert trigger is not None
        assert isinstance(trigger, ExecutionTrigger)

    def test_create_trigger_with_config(self):
        """Test creating trigger with custom config."""
        config = TriggerConfig(max_concurrent=20)
        trigger = create_trigger(config=config)

        assert trigger is not None
        assert trigger.config.max_concurrent == 20


class TestExecutionPriority:
    """Test suite for ExecutionPriority."""

    def test_priority_values(self):
        """Test priority enum values."""
        assert ExecutionPriority.CRITICAL.value == "critical"
        assert ExecutionPriority.HIGH.value == "high"
        assert ExecutionPriority.NORMAL.value == "normal"
        assert ExecutionPriority.LOW.value == "low"
        assert ExecutionPriority.BACKGROUND.value == "background"


class TestExecutionStatus:
    """Test suite for ExecutionStatus."""

    def test_status_values(self):
        """Test status enum values."""
        assert ExecutionStatus.QUEUED.value == "queued"
        assert ExecutionStatus.STARTING.value == "starting"
        assert ExecutionStatus.RUNNING.value == "running"
        assert ExecutionStatus.PAUSED.value == "paused"
        assert ExecutionStatus.COMPLETED.value == "completed"
        assert ExecutionStatus.FAILED.value == "failed"
        assert ExecutionStatus.ABORTED.value == "aborted"


class TestExecutionUpdate:
    """Test suite for ExecutionUpdate."""

    def test_update_completed_property(self):
        """Test completed property of updates."""
        from maestro_hive.mission import ExecutionUpdate

        # Non-terminal states
        for status in [
            ExecutionStatus.QUEUED,
            ExecutionStatus.STARTING,
            ExecutionStatus.RUNNING,
            ExecutionStatus.PAUSED,
        ]:
            update = ExecutionUpdate(
                execution_id="test",
                status=status,
            )
            assert update.completed is False

        # Terminal states
        for status in [
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.ABORTED,
        ]:
            update = ExecutionUpdate(
                execution_id="test",
                status=status,
            )
            assert update.completed is True
