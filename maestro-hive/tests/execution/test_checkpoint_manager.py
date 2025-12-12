#!/usr/bin/env python3
"""
Unit tests for CheckpointManager

Tests checkpoint lifecycle including:
- Checkpoint listing and retrieval
- Rotation and cleanup
- Archival
- Validation
- Storage statistics
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from maestro_hive.execution.checkpoint_manager import (
    CheckpointManager,
    CheckpointInfo
)


class TestCheckpointManager:
    """Tests for CheckpointManager class"""

    @pytest.fixture
    def temp_checkpoint_dir(self):
        """Create temporary checkpoint directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def manager(self, temp_checkpoint_dir):
        """Create CheckpointManager with temporary directory"""
        return CheckpointManager(
            checkpoint_dir=temp_checkpoint_dir,
            max_checkpoints_per_workflow=3,
            max_age_days=7
        )

    @pytest.fixture
    def sample_checkpoint(self):
        """Sample checkpoint data"""
        return {
            "workflow_id": "wf-test-001",
            "checkpoint_metadata": {
                "version": 1,
                "created_at": datetime.utcnow().isoformat()
            },
            "phase_results": {
                "design": {"status": "completed"}
            }
        }

    def create_checkpoint_file(self, manager, workflow_id, phase, data=None, age_days=0):
        """Helper to create a checkpoint file"""
        workflow_dir = manager.checkpoint_dir / workflow_id
        workflow_dir.mkdir(parents=True, exist_ok=True)

        checkpoint_path = workflow_dir / f"checkpoint_{phase}.json"

        checkpoint_data = data or {
            "workflow_id": workflow_id,
            "checkpoint_metadata": {
                "version": 1,
                "created_at": (datetime.utcnow() - timedelta(days=age_days)).isoformat()
            }
        }

        with open(checkpoint_path, "w") as f:
            json.dump(checkpoint_data, f)

        return checkpoint_path

    def test_manager_initialization(self, temp_checkpoint_dir):
        """Test manager initializes correctly"""
        manager = CheckpointManager(
            checkpoint_dir=temp_checkpoint_dir,
            max_checkpoints_per_workflow=5,
            max_age_days=14
        )

        assert manager.checkpoint_dir == temp_checkpoint_dir
        assert manager.max_checkpoints == 5
        assert manager.max_age_days == 14
        assert temp_checkpoint_dir.exists()

    def test_list_workflows_empty(self, manager):
        """Test list_workflows returns empty for empty directory"""
        workflows = manager.list_workflows()
        assert workflows == []

    def test_list_workflows_with_checkpoints(self, manager):
        """Test list_workflows returns workflow IDs"""
        # Create some workflow directories
        (manager.checkpoint_dir / "wf-001").mkdir()
        (manager.checkpoint_dir / "wf-002").mkdir()
        (manager.checkpoint_dir / "not-a-workflow").mkdir()  # Should be excluded

        workflows = manager.list_workflows()

        assert len(workflows) == 2
        assert "wf-001" in workflows
        assert "wf-002" in workflows
        assert "not-a-workflow" not in workflows

    def test_list_checkpoints(self, manager):
        """Test list_checkpoints returns checkpoint info"""
        workflow_id = "wf-test-001"

        # Create checkpoints
        self.create_checkpoint_file(manager, workflow_id, "requirements")
        self.create_checkpoint_file(manager, workflow_id, "design")

        checkpoints = manager.list_checkpoints(workflow_id)

        assert len(checkpoints) == 2
        assert all(isinstance(cp, CheckpointInfo) for cp in checkpoints)

    def test_list_checkpoints_sorted_by_time(self, manager):
        """Test checkpoints are sorted newest first"""
        workflow_id = "wf-test-001"

        # Create checkpoints with different ages
        self.create_checkpoint_file(manager, workflow_id, "old", age_days=5)
        self.create_checkpoint_file(manager, workflow_id, "new", age_days=0)
        self.create_checkpoint_file(manager, workflow_id, "mid", age_days=2)

        checkpoints = manager.list_checkpoints(workflow_id)

        # Newest should be first
        assert checkpoints[0].phase == "new"
        assert checkpoints[-1].phase == "old"

    def test_get_latest_checkpoint(self, manager):
        """Test get_latest_checkpoint returns most recent"""
        workflow_id = "wf-test-001"

        self.create_checkpoint_file(manager, workflow_id, "old", age_days=5)
        self.create_checkpoint_file(manager, workflow_id, "latest", age_days=0)

        latest = manager.get_latest_checkpoint(workflow_id)

        assert latest is not None
        assert latest.phase == "latest"

    def test_get_latest_checkpoint_none(self, manager):
        """Test get_latest_checkpoint returns None for missing workflow"""
        assert manager.get_latest_checkpoint("nonexistent") is None

    def test_get_checkpoint_for_phase(self, manager):
        """Test get_checkpoint_for_phase finds specific phase"""
        workflow_id = "wf-test-001"

        self.create_checkpoint_file(manager, workflow_id, "design")
        self.create_checkpoint_file(manager, workflow_id, "implementation")

        checkpoint = manager.get_checkpoint_for_phase(workflow_id, "design")

        assert checkpoint is not None
        assert checkpoint.phase == "design"

    def test_rotate_checkpoints(self, manager):
        """Test rotation keeps only max checkpoints"""
        workflow_id = "wf-test-001"

        # Create more checkpoints than max (3)
        for i in range(5):
            self.create_checkpoint_file(manager, workflow_id, f"phase_{i}", age_days=i)

        deleted = manager.rotate_checkpoints(workflow_id)

        assert deleted == 2  # 5 - 3 = 2 deleted

        remaining = manager.list_checkpoints(workflow_id)
        assert len(remaining) == 3

    def test_rotate_checkpoints_no_action_needed(self, manager):
        """Test rotation does nothing when under max"""
        workflow_id = "wf-test-001"

        self.create_checkpoint_file(manager, workflow_id, "phase_1")
        self.create_checkpoint_file(manager, workflow_id, "phase_2")

        deleted = manager.rotate_checkpoints(workflow_id)

        assert deleted == 0

    def test_cleanup_old_checkpoints(self, manager):
        """Test cleanup removes old checkpoints"""
        workflow_id = "wf-test-001"

        # Create old and new checkpoints
        self.create_checkpoint_file(manager, workflow_id, "old", age_days=30)
        self.create_checkpoint_file(manager, workflow_id, "new", age_days=1)

        workflows, deleted = manager.cleanup_old_checkpoints()

        assert deleted >= 1  # At least the old one

        remaining = manager.list_checkpoints(workflow_id)
        phases = [cp.phase for cp in remaining]
        assert "old" not in phases
        assert "new" in phases

    def test_validate_checkpoint_valid(self, manager):
        """Test validation passes for valid checkpoint"""
        workflow_id = "wf-test-001"
        path = self.create_checkpoint_file(manager, workflow_id, "design")

        is_valid, error = manager.validate_checkpoint(path)

        assert is_valid is True
        assert error is None

    def test_validate_checkpoint_missing(self, manager):
        """Test validation fails for missing file"""
        is_valid, error = manager.validate_checkpoint(Path("/nonexistent/file.json"))

        assert is_valid is False
        assert "does not exist" in error

    def test_validate_checkpoint_invalid_json(self, manager, temp_checkpoint_dir):
        """Test validation fails for invalid JSON"""
        bad_file = temp_checkpoint_dir / "bad.json"
        bad_file.write_text("not valid json {{{")

        is_valid, error = manager.validate_checkpoint(bad_file)

        assert is_valid is False
        assert "Invalid JSON" in error

    def test_get_storage_stats(self, manager):
        """Test storage stats are calculated correctly"""
        # Create some checkpoints
        self.create_checkpoint_file(manager, "wf-001", "design")
        self.create_checkpoint_file(manager, "wf-001", "impl")
        self.create_checkpoint_file(manager, "wf-002", "design")

        stats = manager.get_storage_stats()

        assert stats["total_workflows"] == 2
        assert stats["total_checkpoints"] == 3
        assert stats["total_size_bytes"] > 0
        assert stats["max_checkpoints_per_workflow"] == 3
        assert stats["max_age_days"] == 7

    def test_archive_workflow(self, manager):
        """Test workflow archival creates zip file"""
        workflow_id = "wf-test-001"
        self.create_checkpoint_file(manager, workflow_id, "design")

        archive_path = manager.archive_workflow(workflow_id)

        assert archive_path is not None
        assert archive_path.exists()
        assert archive_path.suffix == ".zip"

    def test_archive_workflow_nonexistent(self, manager):
        """Test archiving nonexistent workflow returns None"""
        archive_path = manager.archive_workflow("nonexistent")
        assert archive_path is None

    def test_delete_workflow_checkpoints(self, manager):
        """Test deleting all workflow checkpoints"""
        workflow_id = "wf-test-001"
        self.create_checkpoint_file(manager, workflow_id, "design")
        self.create_checkpoint_file(manager, workflow_id, "impl")

        result = manager.delete_workflow_checkpoints(workflow_id)

        assert result is True
        assert not (manager.checkpoint_dir / workflow_id).exists()

    def test_delete_workflow_checkpoints_nonexistent(self, manager):
        """Test deleting nonexistent workflow returns True"""
        result = manager.delete_workflow_checkpoints("nonexistent")
        assert result is True


class TestCheckpointInfo:
    """Tests for CheckpointInfo dataclass"""

    def test_age_hours_calculation(self):
        """Test age_hours property calculates correctly"""
        info = CheckpointInfo(
            path=Path("/test/path"),
            workflow_id="wf-001",
            phase="design",
            created_at=datetime.utcnow() - timedelta(hours=5),
            size_bytes=1000
        )

        assert 4.9 < info.age_hours < 5.1  # Allow small variance

    def test_checkpoint_info_defaults(self):
        """Test CheckpointInfo has correct defaults"""
        info = CheckpointInfo(
            path=Path("/test/path"),
            workflow_id="wf-001",
            phase="design",
            created_at=datetime.utcnow(),
            size_bytes=1000
        )

        assert info.is_synthetic is False
        assert info.version == 1
