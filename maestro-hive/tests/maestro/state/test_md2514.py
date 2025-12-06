"""
Tests for MD-2514: Workflow State Persistence

Tests AC-1 through AC-4:
- AC-1: State serialization with complex objects
- AC-2: Checkpoint creation with atomic writes and versioning
- AC-3: State recovery with automatic checkpoint detection
- AC-4: State diff and merge for concurrent branches
"""

import os
import tempfile
import pytest
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any

# Import modules under test
from maestro_hive.maestro.state.serializer import (
    StateSerializer,
    StateEncoder,
    SerializationError,
    DeserializationError,
)
from maestro_hive.maestro.state.checkpoint import (
    CheckpointManager,
    Checkpoint,
    WorkflowState,
    StateMetadata,
    CheckpointNotFoundError,
    ChecksumValidationError,
)
from maestro_hive.maestro.state.recovery import (
    StateRecovery,
    RecoveryResult,
    NoCheckpointAvailable,
)
from maestro_hive.maestro.state.diff import (
    StateDiff,
    StateDiffResult,
    DiffEntry,
    DiffOperation,
    Conflict,
    ConflictResolution,
    MergeResult,
)


# ============================================================
# Test Fixtures
# ============================================================

@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as td:
        yield td


@pytest.fixture
def serializer():
    """Create serializer instance."""
    return StateSerializer()


@pytest.fixture
def checkpoint_manager(temp_dir):
    """Create checkpoint manager with temp storage."""
    return CheckpointManager(
        storage_path=temp_dir,
        max_checkpoints=5,
    )


@pytest.fixture
def sample_state():
    """Create sample workflow state."""
    return WorkflowState(
        workflow_id="wf-test-001",
        phase="implementation",
        step=3,
        data={
            "config": {"timeout": 30, "retries": 3},
            "progress": {"completed": 5, "total": 10},
            "artifacts": ["file1.py", "file2.py"],
        },
        metadata=StateMetadata(
            executor_version="2.1",
            serialization_format="json",
        ),
    )


# ============================================================
# AC-1: State Serialization Tests
# ============================================================

class TestAC1Serialization:
    """Tests for AC-1: State serialization with complex objects."""

    def test_serialize_primitives(self, serializer):
        """Test serialization of primitive types."""
        data = {
            "string": "hello",
            "int": 42,
            "float": 3.14,
            "bool": True,
            "null": None,
        }
        bytes_data = serializer.serialize(data)
        result = serializer.deserialize(bytes_data)

        assert result == data

    def test_serialize_collections(self, serializer):
        """Test serialization of collections."""
        data = {
            "list": [1, 2, 3],
            "nested_list": [[1, 2], [3, 4]],
            "dict": {"a": 1, "b": 2},
            "nested_dict": {"outer": {"inner": "value"}},
        }
        bytes_data = serializer.serialize(data)
        result = serializer.deserialize(bytes_data)

        assert result == data

    def test_serialize_datetime(self, serializer):
        """Test serialization of datetime objects."""
        now = datetime(2025, 12, 6, 17, 30, 0)
        data = {"timestamp": now}

        bytes_data = serializer.serialize(data)
        result = serializer.deserialize(bytes_data)

        assert result["timestamp"] == now

    def test_serialize_timedelta(self, serializer):
        """Test serialization of timedelta objects."""
        delta = timedelta(hours=2, minutes=30)
        data = {"duration": delta}

        bytes_data = serializer.serialize(data)
        result = serializer.deserialize(bytes_data)

        assert result["duration"] == delta

    def test_serialize_set(self, serializer):
        """Test serialization of set objects."""
        data = {"items": {1, 2, 3}}

        bytes_data = serializer.serialize(data)
        result = serializer.deserialize(bytes_data)

        assert result["items"] == {1, 2, 3}

    def test_serialize_bytes(self, serializer):
        """Test serialization of bytes objects."""
        data = {"binary": b"hello"}

        bytes_data = serializer.serialize(data)
        result = serializer.deserialize(bytes_data)

        assert result["binary"] == b"hello"

    def test_serialize_enum(self, serializer):
        """Test serialization of Enum values."""
        class Status(Enum):
            PENDING = "pending"
            COMPLETE = "complete"

        serializer.register_type(Status)
        data = {"status": Status.COMPLETE}

        bytes_data = serializer.serialize(data)
        result = serializer.deserialize(bytes_data)

        assert result["status"] == Status.COMPLETE

    def test_compute_checksum(self, serializer):
        """Test checksum computation."""
        data = {"test": "data"}
        bytes_data = serializer.serialize(data)

        checksum = serializer.compute_checksum(bytes_data)

        assert len(checksum) == 64  # SHA-256 hex digest
        assert all(c in "0123456789abcdef" for c in checksum)

    def test_verify_checksum(self, serializer):
        """Test checksum verification."""
        data = {"test": "data"}
        bytes_data, checksum = serializer.serialize_with_checksum(data)

        assert serializer.verify_checksum(bytes_data, checksum)
        assert not serializer.verify_checksum(bytes_data, "invalid")


# ============================================================
# AC-2: Checkpoint Creation Tests
# ============================================================

class TestAC2Checkpoint:
    """Tests for AC-2: Checkpoint creation with atomic writes."""

    def test_create_checkpoint(self, checkpoint_manager, sample_state):
        """Test basic checkpoint creation."""
        checkpoint = checkpoint_manager.create_checkpoint(
            workflow_id=sample_state.workflow_id,
            state=sample_state,
        )

        assert checkpoint.workflow_id == sample_state.workflow_id
        assert checkpoint.version == 1
        assert checkpoint.state.phase == "implementation"
        assert checkpoint.checkpoint_id is not None

    def test_checkpoint_versioning(self, checkpoint_manager, sample_state):
        """Test checkpoint version incrementing."""
        cp1 = checkpoint_manager.create_checkpoint(
            workflow_id=sample_state.workflow_id,
            state=sample_state,
        )

        sample_state.step = 4
        cp2 = checkpoint_manager.create_checkpoint(
            workflow_id=sample_state.workflow_id,
            state=sample_state,
        )

        assert cp1.version == 1
        assert cp2.version == 2

    def test_get_checkpoint(self, checkpoint_manager, sample_state):
        """Test checkpoint retrieval."""
        created = checkpoint_manager.create_checkpoint(
            workflow_id=sample_state.workflow_id,
            state=sample_state,
        )

        retrieved = checkpoint_manager.get_checkpoint(
            checkpoint_id=created.checkpoint_id,
            workflow_id=sample_state.workflow_id,
        )

        assert retrieved.checkpoint_id == created.checkpoint_id
        assert retrieved.state.phase == sample_state.phase

    def test_list_checkpoints(self, checkpoint_manager, sample_state):
        """Test listing checkpoints."""
        # Create multiple checkpoints
        for i in range(3):
            sample_state.step = i
            checkpoint_manager.create_checkpoint(
                workflow_id=sample_state.workflow_id,
                state=sample_state,
            )

        checkpoints = checkpoint_manager.list_checkpoints(
            sample_state.workflow_id
        )

        assert len(checkpoints) == 3
        assert checkpoints[0].version == 1
        assert checkpoints[2].version == 3

    def test_checkpoint_retention(self, checkpoint_manager, sample_state):
        """Test checkpoint retention policy."""
        # Create more than max_checkpoints (5)
        for i in range(7):
            sample_state.step = i
            checkpoint_manager.create_checkpoint(
                workflow_id=sample_state.workflow_id,
                state=sample_state,
            )

        checkpoints = checkpoint_manager.list_checkpoints(
            sample_state.workflow_id
        )

        # Should only keep 5
        assert len(checkpoints) == 5
        # Should keep latest versions
        assert checkpoints[0].version == 3  # Oldest kept
        assert checkpoints[4].version == 7  # Latest

    def test_checkpoint_checksum(self, checkpoint_manager, sample_state):
        """Test checkpoint checksum validation."""
        created = checkpoint_manager.create_checkpoint(
            workflow_id=sample_state.workflow_id,
            state=sample_state,
        )

        assert created.state.checksum is not None
        assert len(created.state.checksum) == 64

    def test_delete_checkpoint(self, checkpoint_manager, sample_state):
        """Test checkpoint deletion."""
        created = checkpoint_manager.create_checkpoint(
            workflow_id=sample_state.workflow_id,
            state=sample_state,
        )

        result = checkpoint_manager.delete_checkpoint(created.checkpoint_id)
        assert result is True

        with pytest.raises(CheckpointNotFoundError):
            checkpoint_manager.get_checkpoint(
                created.checkpoint_id,
                sample_state.workflow_id,
            )


# ============================================================
# AC-3: State Recovery Tests
# ============================================================

class TestAC3Recovery:
    """Tests for AC-3: State recovery with automatic detection."""

    def test_can_recover(self, temp_dir, sample_state):
        """Test recovery check."""
        manager = CheckpointManager(storage_path=temp_dir)
        recovery = StateRecovery(checkpoint_manager=manager)

        # No checkpoints yet
        assert not recovery.can_recover(sample_state.workflow_id)

        # Create checkpoint
        manager.create_checkpoint(
            workflow_id=sample_state.workflow_id,
            state=sample_state,
        )

        assert recovery.can_recover(sample_state.workflow_id)

    def test_recover_latest(self, temp_dir, sample_state):
        """Test recovering latest checkpoint."""
        manager = CheckpointManager(storage_path=temp_dir)
        recovery = StateRecovery(checkpoint_manager=manager)

        # Create multiple checkpoints
        for i in range(3):
            sample_state.step = i + 1
            manager.create_checkpoint(
                workflow_id=sample_state.workflow_id,
                state=sample_state,
            )

        result = recovery.recover(sample_state.workflow_id)

        assert result.success
        assert result.recovered_state is not None
        assert result.recovered_state.step == 3  # Latest

    def test_recover_specific_version(self, temp_dir, sample_state):
        """Test recovering specific version."""
        manager = CheckpointManager(storage_path=temp_dir)
        recovery = StateRecovery(checkpoint_manager=manager)

        # Create multiple checkpoints
        for i in range(3):
            sample_state.step = i + 1
            manager.create_checkpoint(
                workflow_id=sample_state.workflow_id,
                state=sample_state,
            )

        result = recovery.recover(sample_state.workflow_id, version=2)

        assert result.success
        assert result.recovered_state.step == 2

    def test_recovery_dry_run(self, temp_dir, sample_state):
        """Test dry-run recovery."""
        manager = CheckpointManager(storage_path=temp_dir)
        recovery = StateRecovery(checkpoint_manager=manager)

        manager.create_checkpoint(
            workflow_id=sample_state.workflow_id,
            state=sample_state,
        )

        callback_called = []
        recovery.register_callback(lambda s: callback_called.append(s))

        # Dry run should not trigger callbacks
        result = recovery.recover(sample_state.workflow_id, dry_run=True)

        assert result.success
        assert len(callback_called) == 0

    def test_recovery_callback(self, temp_dir, sample_state):
        """Test recovery callbacks."""
        manager = CheckpointManager(storage_path=temp_dir)
        recovery = StateRecovery(checkpoint_manager=manager)

        manager.create_checkpoint(
            workflow_id=sample_state.workflow_id,
            state=sample_state,
        )

        callback_called = []
        recovery.register_callback(lambda s: callback_called.append(s))

        result = recovery.recover(sample_state.workflow_id)

        assert result.success
        assert len(callback_called) == 1

    def test_find_recoverable_workflows(self, temp_dir):
        """Test finding all recoverable workflows."""
        manager = CheckpointManager(storage_path=temp_dir)
        recovery = StateRecovery(checkpoint_manager=manager)

        # Create checkpoints for multiple workflows
        for wf_id in ["wf-1", "wf-2", "wf-3"]:
            state = WorkflowState(
                workflow_id=wf_id,
                phase="test",
                step=1,
                data={},
            )
            manager.create_checkpoint(workflow_id=wf_id, state=state)

        recoverable = recovery.find_recoverable_workflows()

        assert len(recoverable) == 3
        assert set(recoverable) == {"wf-1", "wf-2", "wf-3"}


# ============================================================
# AC-4: State Diff and Merge Tests
# ============================================================

class TestAC4DiffMerge:
    """Tests for AC-4: State diff and merge."""

    def test_diff_no_changes(self):
        """Test diff with identical states."""
        state_a = WorkflowState(
            workflow_id="wf-1",
            phase="test",
            step=1,
            data={"key": "value"},
        )
        state_b = WorkflowState(
            workflow_id="wf-1",
            phase="test",
            step=1,
            data={"key": "value"},
        )

        diff = StateDiff()
        result = diff.diff(state_a, state_b)

        assert not result.has_changes
        assert result.added_count == 0
        assert result.removed_count == 0
        assert result.modified_count == 0

    def test_diff_added(self):
        """Test diff with added fields."""
        state_a = WorkflowState(
            workflow_id="wf-1",
            phase="test",
            step=1,
            data={"key": "value"},
        )
        state_b = WorkflowState(
            workflow_id="wf-1",
            phase="test",
            step=1,
            data={"key": "value", "new_key": "new_value"},
        )

        diff = StateDiff()
        result = diff.diff(state_a, state_b)

        assert result.has_changes
        assert result.added_count == 1

    def test_diff_removed(self):
        """Test diff with removed fields."""
        state_a = WorkflowState(
            workflow_id="wf-1",
            phase="test",
            step=1,
            data={"key": "value", "old_key": "old_value"},
        )
        state_b = WorkflowState(
            workflow_id="wf-1",
            phase="test",
            step=1,
            data={"key": "value"},
        )

        diff = StateDiff()
        result = diff.diff(state_a, state_b)

        assert result.has_changes
        assert result.removed_count == 1

    def test_diff_modified(self):
        """Test diff with modified fields."""
        state_a = WorkflowState(
            workflow_id="wf-1",
            phase="test",
            step=1,
            data={"key": "old_value"},
        )
        state_b = WorkflowState(
            workflow_id="wf-1",
            phase="test",
            step=1,
            data={"key": "new_value"},
        )

        diff = StateDiff()
        result = diff.diff(state_a, state_b)

        assert result.has_changes
        assert result.modified_count == 1

    def test_diff_nested(self):
        """Test diff with nested changes."""
        state_a = WorkflowState(
            workflow_id="wf-1",
            phase="test",
            step=1,
            data={"outer": {"inner": "old"}},
        )
        state_b = WorkflowState(
            workflow_id="wf-1",
            phase="test",
            step=1,
            data={"outer": {"inner": "new"}},
        )

        diff = StateDiff()
        result = diff.diff(state_a, state_b)

        assert result.has_changes
        assert result.modified_count == 1
        assert any(e.path == "outer.inner" for e in result.entries)

    def test_merge_no_conflicts(self):
        """Test three-way merge without conflicts."""
        base = WorkflowState(
            workflow_id="wf-1",
            phase="test",
            step=1,
            data={"shared": "value"},
        )
        state_a = WorkflowState(
            workflow_id="wf-1",
            phase="test",
            step=1,
            data={"shared": "value", "left": "left_val"},
        )
        state_b = WorkflowState(
            workflow_id="wf-1",
            phase="test",
            step=1,
            data={"shared": "value", "right": "right_val"},
        )

        diff = StateDiff()
        result = diff.merge(base, state_a, state_b)

        assert result.success
        assert result.merged_state is not None
        assert result.merged_state.data["left"] == "left_val"
        assert result.merged_state.data["right"] == "right_val"
        assert result.unresolved_conflicts == 0

    def test_merge_with_conflicts(self):
        """Test three-way merge with conflicts."""
        base = WorkflowState(
            workflow_id="wf-1",
            phase="test",
            step=1,
            data={"key": "base_value"},
        )
        state_a = WorkflowState(
            workflow_id="wf-1",
            phase="test",
            step=1,
            data={"key": "left_value"},
        )
        state_b = WorkflowState(
            workflow_id="wf-1",
            phase="test",
            step=1,
            data={"key": "right_value"},
        )

        diff = StateDiff()
        result = diff.merge(base, state_a, state_b)

        # Without resolver, should have unresolved conflict
        assert not result.success
        assert result.unresolved_conflicts == 1
        assert len(result.conflicts) == 1

    def test_merge_with_resolver(self):
        """Test merge with conflict resolver."""
        base = WorkflowState(
            workflow_id="wf-1",
            phase="test",
            step=1,
            data={"key": "base_value"},
        )
        state_a = WorkflowState(
            workflow_id="wf-1",
            phase="test",
            step=1,
            data={"key": "left_value"},
        )
        state_b = WorkflowState(
            workflow_id="wf-1",
            phase="test",
            step=1,
            data={"key": "right_value"},
        )

        resolver = StateDiff.create_resolver(ConflictResolution.KEEP_RIGHT)
        diff = StateDiff(conflict_resolver=resolver)
        result = diff.merge(base, state_a, state_b)

        assert result.success
        assert result.resolved_conflicts == 1
        assert result.merged_state.data["key"] == "right_value"

    def test_create_resolvers(self):
        """Test different conflict resolution strategies."""
        conflict = Conflict(
            path="test",
            base_value="base",
            left_value="left",
            right_value="right",
        )

        left_resolver = StateDiff.create_resolver(ConflictResolution.KEEP_LEFT)
        assert left_resolver(conflict) == "left"

        right_resolver = StateDiff.create_resolver(ConflictResolution.KEEP_RIGHT)
        assert right_resolver(conflict) == "right"

        both_resolver = StateDiff.create_resolver(ConflictResolution.KEEP_BOTH)
        result = both_resolver(conflict)
        assert result == {"left": "left", "right": "right"}


# ============================================================
# Integration Tests
# ============================================================

class TestIntegration:
    """Integration tests for complete workflows."""

    def test_checkpoint_and_recovery_workflow(self, temp_dir):
        """Test complete checkpoint and recovery workflow."""
        # Setup
        manager = CheckpointManager(storage_path=temp_dir)
        recovery = StateRecovery(checkpoint_manager=manager)

        # Create workflow state
        state = WorkflowState(
            workflow_id="wf-integration",
            phase="implementation",
            step=1,
            data={
                "config": {"timeout": 30},
                "progress": {"completed": 0, "total": 10},
            },
        )

        # Simulate workflow execution with checkpoints
        for step in range(1, 6):
            state.step = step
            state.data["progress"]["completed"] = step
            manager.create_checkpoint(
                workflow_id=state.workflow_id,
                state=state,
            )

        # Simulate failure and recovery
        recovered = recovery.recover(state.workflow_id)

        assert recovered.success
        assert recovered.recovered_state.step == 5
        assert recovered.recovered_state.data["progress"]["completed"] == 5

    def test_branch_and_merge_workflow(self, temp_dir):
        """Test branch and merge workflow."""
        # Create base state
        base = WorkflowState(
            workflow_id="wf-branch",
            phase="test",
            step=1,
            data={"feature_a": False, "feature_b": False},
        )

        # Simulate two branches
        branch_a = WorkflowState(
            workflow_id="wf-branch",
            phase="test",
            step=2,
            data={"feature_a": True, "feature_b": False, "branch_a_data": "value"},
        )

        branch_b = WorkflowState(
            workflow_id="wf-branch",
            phase="test",
            step=3,
            data={"feature_a": False, "feature_b": True, "branch_b_data": "value"},
        )

        # Merge branches
        diff = StateDiff()
        result = diff.merge(base, branch_a, branch_b)

        assert result.success
        assert result.merged_state.data["feature_a"] is True
        assert result.merged_state.data["feature_b"] is True
        assert result.merged_state.data["branch_a_data"] == "value"
        assert result.merged_state.data["branch_b_data"] == "value"
