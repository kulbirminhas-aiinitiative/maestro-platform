"""Tests for ExecutionFlowManager."""

import asyncio
import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from maestro_hive.mission.execution_flow_manager import (
    ExecutionFlowManager,
    ExecutionConfig,
    ExecutionResult,
    ExecutionStatus,
    ExecutionState,
    ExecutionError,
)


class TestExecutionConfig:
    """Tests for ExecutionConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = ExecutionConfig()
        assert config.timeout == 3600
        assert config.max_retries == 3
        assert config.checkpoint_interval == 300
        assert config.enable_rollback is True
        assert config.max_concurrent_tasks == 10

    def test_custom_values(self):
        """Test custom configuration values."""
        config = ExecutionConfig(
            timeout=7200,
            max_retries=5,
            checkpoint_interval=600,
            enable_rollback=False,
            max_concurrent_tasks=20
        )
        assert config.timeout == 7200
        assert config.max_retries == 5
        assert config.checkpoint_interval == 600
        assert config.enable_rollback is False
        assert config.max_concurrent_tasks == 20


class TestExecutionFlowManager:
    """Tests for ExecutionFlowManager class."""

    @pytest.fixture
    def mock_team(self):
        """Create a mock team for testing."""
        team = Mock()
        team.members = [Mock(), Mock()]
        team.is_ready = Mock(return_value=True)
        return team

    @pytest.fixture
    def manager(self, mock_team):
        """Create an ExecutionFlowManager instance."""
        return ExecutionFlowManager(
            mission_id="test-mission-123",
            team=mock_team,
            config=ExecutionConfig(timeout=10)
        )

    def test_initialization(self, manager, mock_team):
        """Test manager initialization."""
        assert manager.mission_id == "test-mission-123"
        assert manager.team == mock_team
        assert manager.config.timeout == 10
        assert manager._state == ExecutionState.PENDING

    @pytest.mark.asyncio
    async def test_start_execution_success(self, manager):
        """Test successful execution start."""
        result = await manager.start_execution()

        assert result.execution_id is not None
        assert result.status == "completed"
        assert result.start_time is not None
        assert result.end_time is not None
        assert result.team_size == 2

    @pytest.mark.asyncio
    async def test_start_execution_team_not_ready(self, manager, mock_team):
        """Test execution fails when team not ready."""
        mock_team.is_ready.return_value = False

        with pytest.raises(ExecutionError, match="not ready"):
            await manager.start_execution()

    @pytest.mark.asyncio
    async def test_start_execution_already_running(self, manager):
        """Test cannot start already running execution."""
        manager._state = ExecutionState.RUNNING

        with pytest.raises(ExecutionError, match="Cannot start"):
            await manager.start_execution()

    @pytest.mark.asyncio
    async def test_pause_execution(self, manager):
        """Test pausing execution."""
        # Start first
        await manager.start_execution()

        # Reset state to simulate running
        manager._state = ExecutionState.RUNNING

        result = await manager.pause_execution()
        assert result is True
        assert manager._state == ExecutionState.PAUSED
        assert manager._checkpoint_id is not None

    @pytest.mark.asyncio
    async def test_pause_not_running(self, manager):
        """Test pause when not running returns False."""
        result = await manager.pause_execution()
        assert result is False

    @pytest.mark.asyncio
    async def test_resume_execution(self, manager):
        """Test resuming execution."""
        manager._state = ExecutionState.PAUSED
        manager._checkpoint_id = "checkpoint-123"

        result = await manager.resume_execution()
        assert result is True
        assert manager._state == ExecutionState.RUNNING

    @pytest.mark.asyncio
    async def test_resume_not_paused(self, manager):
        """Test resume when not paused returns False."""
        result = await manager.resume_execution()
        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_execution(self, manager):
        """Test cancelling execution."""
        manager._state = ExecutionState.RUNNING

        result = await manager.cancel_execution()
        assert result is True
        assert manager._state == ExecutionState.CANCELLED

    @pytest.mark.asyncio
    async def test_cancel_not_running(self, manager):
        """Test cancel when not running returns False."""
        result = await manager.cancel_execution()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_status(self, manager):
        """Test getting execution status."""
        manager._state = ExecutionState.RUNNING
        manager._start_time = datetime.utcnow()
        manager._tasks = [{"id": "t1"}, {"id": "t2"}, {"id": "t3"}]
        manager._completed_tasks = ["t1"]
        manager._current_task = "t2"

        status = await manager.get_status()

        assert status.state == ExecutionState.RUNNING
        assert status.progress == pytest.approx(1/3, rel=0.01)
        assert status.current_task == "t2"
        assert status.remaining_tasks == 2

    @pytest.mark.asyncio
    async def test_event_handler(self, manager):
        """Test event handler registration and triggering."""
        events = []

        def handler(data):
            events.append(data)

        manager.on_event("execution_started", handler)

        await manager.start_execution()

        assert len(events) > 0
        assert "execution_id" in events[0]

    @pytest.mark.asyncio
    async def test_async_event_handler(self, manager):
        """Test async event handler."""
        events = []

        async def async_handler(data):
            events.append(data)

        manager.on_event("execution_started", async_handler)

        await manager.start_execution()

        assert len(events) > 0


class TestExecutionState:
    """Tests for ExecutionState enum."""

    def test_all_states_defined(self):
        """Test all expected states are defined."""
        states = [s.value for s in ExecutionState]
        assert "pending" in states
        assert "running" in states
        assert "paused" in states
        assert "completed" in states
        assert "failed" in states
        assert "cancelled" in states


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_create_result(self):
        """Test creating execution result."""
        result = ExecutionResult(
            execution_id="exec-123",
            status="completed",
            start_time=datetime.utcnow(),
            team_size=3,
            tasks_completed=10
        )

        assert result.execution_id == "exec-123"
        assert result.status == "completed"
        assert result.team_size == 3
        assert result.tasks_completed == 10
        assert result.tasks_failed == 0
        assert result.outputs == {}
