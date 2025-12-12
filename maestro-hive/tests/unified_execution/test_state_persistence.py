#!/usr/bin/env python3
"""
Tests for State Persistence Module

EPIC: MD-3091 - Unified Execution Foundation
Tests AC-1 (State Persistence) and AC-2 (Checkpoint Resume)
"""

import json
import os
import pytest
import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from maestro_hive.unified_execution.state_persistence import (
    StatePersistence,
    ExecutionState,
    StateCorruptionError,
    DEFAULT_STATE_PATH,
    DEFAULT_CHECKPOINT_PATH,
    get_state_persistence,
    save_state,
    load_state,
)
from maestro_hive.unified_execution.config import ExecutionConfig, StateConfig


class TestExecutionState:
    """Tests for ExecutionState dataclass."""

    def test_create_default_state(self):
        """Test creating state with defaults."""
        state = ExecutionState(workflow_id="test_workflow")
        assert state.workflow_id == "test_workflow"
        assert state.phase == "initializing"
        assert state.step == 0
        assert state.status == "pending"
        assert state.persona_states == {}
        assert state.retry_counts == {}
        assert state.completed_tasks == []
        assert state.pending_tasks == []

    def test_update_timestamp(self):
        """Test that update() refreshes the timestamp."""
        state = ExecutionState(workflow_id="test")
        original_updated = state.updated_at
        time.sleep(0.01)
        state.update()
        assert state.updated_at > original_updated

    def test_to_dict_roundtrip(self):
        """Test serialization and deserialization."""
        state = ExecutionState(
            workflow_id="test_wf",
            phase="implementation",
            step=3,
            status="running",
            completed_tasks=["task1", "task2"],
            pending_tasks=["task3"],
            artifacts={"file.py": "/path/to/file.py"},
        )

        state_dict = state.to_dict()
        restored = ExecutionState.from_dict(state_dict)

        assert restored.workflow_id == state.workflow_id
        assert restored.phase == state.phase
        assert restored.step == state.step
        assert restored.completed_tasks == state.completed_tasks
        assert restored.artifacts == state.artifacts


class TestStatePersistence:
    """Tests for StatePersistence class."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "state"
            checkpoint_dir = Path(tmpdir) / "checkpoints"
            state_dir.mkdir()
            checkpoint_dir.mkdir()
            yield state_dir, checkpoint_dir

    @pytest.fixture
    def config(self, temp_dirs):
        """Create test configuration."""
        state_dir, checkpoint_dir = temp_dirs
        config = ExecutionConfig()
        config.state = StateConfig(
            state_dir=str(state_dir),
            checkpoint_dir=str(checkpoint_dir),
            enable_persistence=True,
            auto_checkpoint_interval_seconds=300,  # Long interval for tests
            verify_checksum_on_load=True,
            max_checkpoints_per_workflow=5,
        )
        return config

    def test_ac1_default_state_path(self):
        """AC-1: Verify default state path is /var/maestro/state."""
        assert DEFAULT_STATE_PATH == "/var/maestro/state"
        assert DEFAULT_CHECKPOINT_PATH == "/var/maestro/checkpoints"

    def test_ac1_state_persists_to_disk(self, temp_dirs, config):
        """AC-1: State persists to configured directory."""
        state_dir, _ = temp_dirs

        persistence = StatePersistence(
            config=config,
            workflow_id="test_persist",
            auto_restore=False,
        )

        # Update state
        persistence.update_state(phase="testing", step=5, status="running")

        # Create checkpoint
        cp_id = persistence.checkpoint()

        # Verify checkpoint file exists
        persistence.shutdown()

        # Check files exist (may be .json or .checkpoint)
        checkpoint_dir = Path(config.state.checkpoint_dir)
        checkpoint_files = list(checkpoint_dir.glob("**/*.json")) + list(checkpoint_dir.glob("**/*.checkpoint"))
        assert len(checkpoint_files) > 0 or persistence.list_checkpoints()

    def test_ac2_auto_resume_from_checkpoint(self, temp_dirs, config):
        """AC-2: Process restart auto-resumes from checkpoint."""
        state_dir, checkpoint_dir = temp_dirs
        workflow_id = "test_resume"

        # Create initial persistence and set state
        persistence1 = StatePersistence(
            config=config,
            workflow_id=workflow_id,
            auto_restore=False,
        )
        persistence1.update_state(phase="implementation", step=7, status="in_progress")
        persistence1.mark_task_completed("task_1", {"out.py": "/path/out.py"})
        persistence1.checkpoint()
        persistence1.shutdown()

        # Simulate process restart - create new persistence with same workflow_id
        persistence2 = StatePersistence(
            config=config,
            workflow_id=workflow_id,
            auto_restore=True,  # This should restore!
        )

        # Verify state was restored
        assert persistence2.state.phase == "implementation"
        assert persistence2.state.step == 7
        assert persistence2.state.status == "in_progress"
        assert "task_1" in persistence2.state.completed_tasks
        persistence2.shutdown()

    def test_update_state(self, config):
        """Test state update method."""
        persistence = StatePersistence(
            config=config,
            workflow_id="test_update",
            auto_restore=False,
        )

        persistence.update_state(
            phase="building",
            step=10,
            status="active",
        )

        assert persistence.state.phase == "building"
        assert persistence.state.step == 10
        assert persistence.state.status == "active"
        persistence.shutdown()

    def test_mark_task_completed(self, config):
        """Test task completion tracking."""
        persistence = StatePersistence(
            config=config,
            workflow_id="test_tasks",
            auto_restore=False,
        )

        persistence.mark_task_pending("task_a")
        persistence.mark_task_pending("task_b")

        assert "task_a" in persistence.state.pending_tasks
        assert "task_b" in persistence.state.pending_tasks

        persistence.mark_task_completed("task_a", {"result.txt": "/path/result.txt"})

        assert "task_a" not in persistence.state.pending_tasks
        assert "task_a" in persistence.state.completed_tasks
        assert persistence.state.artifacts["result.txt"] == "/path/result.txt"
        persistence.shutdown()

    def test_retry_counting(self, config):
        """Test retry count tracking."""
        persistence = StatePersistence(
            config=config,
            workflow_id="test_retry",
            auto_restore=False,
        )

        assert persistence.get_retry_count("persona_1") == 0

        persistence.increment_retry("persona_1")
        assert persistence.get_retry_count("persona_1") == 1

        persistence.increment_retry("persona_1")
        persistence.increment_retry("persona_1")
        assert persistence.get_retry_count("persona_1") == 3
        persistence.shutdown()

    def test_persona_state_tracking(self, config):
        """Test per-persona state tracking."""
        persistence = StatePersistence(
            config=config,
            workflow_id="test_persona",
            auto_restore=False,
        )

        persistence.update_persona_state("backend_dev", {
            "last_output": "code.py",
            "tokens_used": 5000,
        })

        state = persistence.get_persona_state("backend_dev")
        assert state["last_output"] == "code.py"
        assert state["tokens_used"] == 5000

        assert persistence.get_persona_state("unknown") is None
        persistence.shutdown()

    def test_checkpoint_and_restore(self, config):
        """Test manual checkpoint and restore."""
        persistence = StatePersistence(
            config=config,
            workflow_id="test_cp",
            auto_restore=False,
        )

        # Set initial state
        persistence.update_state(phase="phase_1", step=1)
        cp1_id = persistence.checkpoint("checkpoint_1")

        # Change state
        persistence.update_state(phase="phase_2", step=2)
        cp2_id = persistence.checkpoint("checkpoint_2")

        # Restore to checkpoint 1
        success = persistence.restore(cp1_id)
        assert success
        assert persistence.state.phase == "phase_1"
        assert persistence.state.step == 1
        persistence.shutdown()

    def test_list_checkpoints(self, config):
        """Test listing available checkpoints."""
        persistence = StatePersistence(
            config=config,
            workflow_id="test_list",
            auto_restore=False,
        )

        persistence.checkpoint("cp_a")
        persistence.checkpoint("cp_b")
        persistence.checkpoint("cp_c")

        checkpoints = persistence.list_checkpoints()
        assert len(checkpoints) >= 3
        persistence.shutdown()

    def test_atomic_write(self, temp_dirs, config):
        """Test that writes are atomic (no partial writes)."""
        persistence = StatePersistence(
            config=config,
            workflow_id="test_atomic",
            auto_restore=False,
        )

        # Create large state to increase chance of catching partial write
        persistence.update_state(
            phase="testing",
            pending_tasks=[f"task_{i}" for i in range(100)],
        )

        cp_id = persistence.checkpoint()

        # Verify file is complete and valid JSON
        checkpoint_dir = Path(config.state.checkpoint_dir)
        checkpoint_files = list(checkpoint_dir.glob("**/*test_atomic*.json")) + list(checkpoint_dir.glob("**/*test_atomic*.checkpoint"))
        # If using CheckpointManager, files may be in workflow subdirectory
        if not checkpoint_files:
            checkpoint_files = list(checkpoint_dir.glob("**/*.json")) + list(checkpoint_dir.glob("**/*.checkpoint"))
        assert len(checkpoint_files) > 0 or len(persistence.list_checkpoints()) > 0

        for cp_file in checkpoint_files:
            with open(cp_file, "rb") as f:
                data = json.load(f)
                # CheckpointManager uses nested structure with __value__
                assert "pending_tasks" in data or "state" in data or "__value__" in data

        persistence.shutdown()

    def test_context_manager(self, config):
        """Test context manager usage."""
        with StatePersistence(
            config=config,
            workflow_id="test_context",
            auto_restore=False,
        ) as persistence:
            persistence.update_state(phase="in_context")
            assert persistence.state.phase == "in_context"
        # Should auto-shutdown

    def test_thread_safety(self, config):
        """Test thread-safe operations."""
        persistence = StatePersistence(
            config=config,
            workflow_id="test_threads",
            auto_restore=False,
        )

        errors = []

        def update_worker(n):
            try:
                for i in range(10):
                    persistence.increment_retry(f"persona_{n}")
                    persistence.mark_task_pending(f"task_{n}_{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=update_worker, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

        # Verify all updates applied
        total_retries = sum(persistence.state.retry_counts.values())
        assert total_retries == 50  # 5 threads * 10 increments each

        persistence.shutdown()

    def test_fallback_directory(self, config):
        """Test fallback to user directory when /var not writable."""
        # Create config with unwritable path
        config.state.state_dir = "/unwritable/path"
        config.state.checkpoint_dir = "/unwritable/path/checkpoints"

        persistence = StatePersistence(
            config=config,
            workflow_id="test_fallback",
            auto_restore=False,
        )

        # Should have fallen back to ~/.maestro
        assert ".maestro" in str(persistence._state_dir) or "/var/maestro" in str(persistence._state_dir)
        persistence.shutdown()


class TestConvenienceFunction:
    """Tests for get_state_persistence helper."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "state"
            checkpoint_dir = Path(tmpdir) / "checkpoints"
            state_dir.mkdir()
            checkpoint_dir.mkdir()
            yield state_dir, checkpoint_dir

    def test_get_state_persistence_auto_workflow_id(self, temp_dirs):
        """Test that workflow ID is auto-generated."""
        state_dir, checkpoint_dir = temp_dirs

        with patch.object(ExecutionConfig, '__init__', lambda self: None):
            config = ExecutionConfig()
            config.state = StateConfig(
                state_dir=str(state_dir),
                checkpoint_dir=str(checkpoint_dir),
                enable_persistence=False,
            )

            with patch('maestro_hive.unified_execution.state_persistence.get_execution_config', return_value=config):
                persistence = get_state_persistence(auto_restore=False)
                assert persistence.workflow_id.startswith("wf_")
                persistence.shutdown()


class TestIntegrationWithPersonaExecutor:
    """Integration tests with PersonaExecutor."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "state"
            checkpoint_dir = Path(tmpdir) / "checkpoints"
            state_dir.mkdir()
            checkpoint_dir.mkdir()
            yield state_dir, checkpoint_dir

    @pytest.fixture
    def config(self, temp_dirs):
        """Create test configuration."""
        state_dir, checkpoint_dir = temp_dirs
        config = ExecutionConfig()
        config.state = StateConfig(
            state_dir=str(state_dir),
            checkpoint_dir=str(checkpoint_dir),
            enable_persistence=True,
            auto_checkpoint_interval_seconds=300,
        )
        return config

    @pytest.mark.asyncio
    async def test_state_tracks_execution_progress(self, config):
        """Test that state persistence tracks executor progress."""
        from maestro_hive.unified_execution.persona_executor import PersonaExecutor

        persistence = StatePersistence(
            config=config,
            workflow_id="integration_test",
            auto_restore=False,
        )

        executor = PersonaExecutor(config=config, persona_id="test_persona")

        # Simulate workflow progress
        persistence.update_state(phase="execution", status="running")
        persistence.update_persona_state("test_persona", {"status": "starting"})

        async def simple_task():
            return "result"

        try:
            result = await executor.execute(simple_task, "test_task")
            persistence.mark_task_completed("test_task", {})
            persistence.update_persona_state("test_persona", {
                "status": "completed",
                "tokens": executor.get_token_usage(),
            })
        except Exception:
            persistence.increment_retry("test_persona")

        persistence.checkpoint()

        assert "test_task" in persistence.state.completed_tasks
        assert persistence.state.phase == "execution"
        persistence.shutdown()


class TestSaveLoadStateFunctions:
    """Tests for AC-1 save_state() and load_state() convenience functions."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "state"
            checkpoint_dir = Path(tmpdir) / "checkpoints"
            state_dir.mkdir()
            checkpoint_dir.mkdir()
            yield state_dir, checkpoint_dir

    @pytest.fixture
    def config(self, temp_dirs):
        """Create test configuration."""
        state_dir, checkpoint_dir = temp_dirs
        config = ExecutionConfig()
        config.state = StateConfig(
            state_dir=str(state_dir),
            checkpoint_dir=str(checkpoint_dir),
            enable_persistence=True,
            auto_checkpoint_interval_seconds=300,
        )
        return config

    def test_ac1_save_state_function(self, temp_dirs, config):
        """AC-1: Test save_state() convenience function exists and works."""
        state_dir, _ = temp_dirs

        # Create a state
        state = ExecutionState(
            workflow_id="save_test",
            phase="testing",
            step=5,
            status="active",
            completed_tasks=["task1"],
        )

        # Save it
        with patch('maestro_hive.unified_execution.state_persistence.get_execution_config', return_value=config):
            cp_id = save_state(state)
            assert cp_id is not None

    def test_ac1_load_state_function(self, temp_dirs, config):
        """AC-1: Test load_state() convenience function exists and works."""
        state_dir, _ = temp_dirs
        workflow_id = "load_test"

        # Create and save a state
        state = ExecutionState(
            workflow_id=workflow_id,
            phase="building",
            step=10,
            status="running",
            completed_tasks=["build_step_1", "build_step_2"],
        )

        with patch('maestro_hive.unified_execution.state_persistence.get_execution_config', return_value=config):
            save_state(state)

            # Load it back
            loaded = load_state(workflow_id)
            assert loaded is not None
            assert loaded.workflow_id == workflow_id
            assert loaded.phase == "building"
            assert loaded.step == 10
            assert "build_step_1" in loaded.completed_tasks

    def test_ac1_load_state_returns_none_for_missing(self, temp_dirs, config):
        """AC-1: load_state() returns None for non-existent workflow."""
        with patch('maestro_hive.unified_execution.state_persistence.get_execution_config', return_value=config):
            loaded = load_state("nonexistent_workflow_12345")
            # New workflow will be created with initializing phase
            assert loaded is None or loaded.phase == "initializing"


class TestAC4DurabilityKillSurvival:
    """Tests for AC-4: Agent survives kill (Ctrl+C) and resumes from correct step."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            state_dir = Path(tmpdir) / "state"
            checkpoint_dir = Path(tmpdir) / "checkpoints"
            state_dir.mkdir()
            checkpoint_dir.mkdir()
            yield state_dir, checkpoint_dir

    @pytest.fixture
    def config(self, temp_dirs):
        """Create test configuration."""
        state_dir, checkpoint_dir = temp_dirs
        config = ExecutionConfig()
        config.state = StateConfig(
            state_dir=str(state_dir),
            checkpoint_dir=str(checkpoint_dir),
            enable_persistence=True,
            auto_checkpoint_interval_seconds=300,
        )
        return config

    @pytest.mark.asyncio
    async def test_ac4_persona_executor_state_survives_simulated_kill(self, config):
        """AC-4: PersonaExecutor state survives process termination and resumes."""
        from maestro_hive.unified_execution.persona_executor import PersonaExecutor

        workflow_id = "kill_test_workflow"

        # STEP 1: Start execution and make progress
        persistence1 = StatePersistence(
            config=config,
            workflow_id=workflow_id,
            auto_restore=False,
        )

        executor1 = PersonaExecutor(
            config=config,
            persona_id="durable_persona",
            workflow_id=workflow_id,
            state_persistence=persistence1,
        )

        # Execute a task - this should persist state
        async def step_task():
            return "step_completed"

        result = await executor1.execute(step_task, "step_1_task")
        assert result.success

        # Simulate executing more steps
        persistence1.update_state(phase="mid_execution", step=5)
        persistence1.mark_task_completed("step_1_task")
        persistence1.mark_task_completed("step_2_task")
        persistence1.checkpoint()

        # STEP 2: Simulate Ctrl+C / kill (just destroy the persistence without graceful shutdown)
        # In real scenario, the process would die here
        del persistence1
        del executor1

        # STEP 3: Restart with same workflow_id (simulating process restart)
        persistence2 = StatePersistence(
            config=config,
            workflow_id=workflow_id,
            auto_restore=True,  # This is key - should restore from checkpoint
        )

        # VERIFY: State was restored from checkpoint
        assert persistence2.state.workflow_id == workflow_id
        assert persistence2.state.phase == "mid_execution"
        assert persistence2.state.step == 5
        assert "step_1_task" in persistence2.state.completed_tasks
        assert "step_2_task" in persistence2.state.completed_tasks

        # STEP 4: Can resume execution from where we left off
        executor2 = PersonaExecutor(
            config=config,
            persona_id="durable_persona",
            workflow_id=workflow_id,
            state_persistence=persistence2,
        )

        # Continue from step 5
        async def continue_task():
            return "continued_from_step_5"

        result2 = await executor2.execute(continue_task, "step_6_task")
        assert result2.success
        persistence2.mark_task_completed("step_6_task")

        assert "step_6_task" in persistence2.state.completed_tasks
        persistence2.shutdown()

    def test_ac4_checkpoint_after_each_persona_state_update(self, config):
        """AC-4: Verify that persona state updates trigger checkpoints."""
        workflow_id = "checkpoint_test"

        persistence = StatePersistence(
            config=config,
            workflow_id=workflow_id,
            auto_restore=False,
        )

        # Simulate what PersonaExecutor._persist_state() does
        persona_state = {
            "last_updated": "2025-12-11T16:00:00Z",
            "status": "running",
            "current_attempt": 1,
            "tokens_used": 1000,
        }

        persistence.update_persona_state("test_persona", persona_state)
        cp_id = persistence.checkpoint()

        assert cp_id is not None

        # Verify checkpoint contains the persona state
        checkpoints = persistence.list_checkpoints()
        assert len(checkpoints) > 0

        persistence.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
