"""
Tests for Rollback Mechanism - MD-2527

Tests all acceptance criteria:
- AC-1: State checkpoint before each phase
- AC-2: Rollback execution on failure
- AC-3: Artifact cleanup on rollback
- AC-4: Recovery notification system
"""

import json
import os
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from maestro_hive.maestro.rollback import (
    CheckpointStore,
    PhaseCheckpoint,
    RollbackExecutor,
    RollbackManager,
    RecoveryNotificationService,
)
from maestro_hive.maestro.rollback.manager import RollbackResult
from maestro_hive.maestro.rollback.notifications import NotificationLevel


class TestPhaseCheckpoint:
    """Tests for PhaseCheckpoint dataclass (AC-1)."""

    def test_checkpoint_creation(self):
        """Test checkpoint can be created with required fields."""
        checkpoint = PhaseCheckpoint(
            checkpoint_id="ckpt-01-abc123",
            execution_id="exec-001",
            phase_name="design",
            phase_index=1,
            timestamp=datetime.utcnow(),
            state={"key": "value"},
        )

        assert checkpoint.checkpoint_id == "ckpt-01-abc123"
        assert checkpoint.execution_id == "exec-001"
        assert checkpoint.phase_name == "design"
        assert checkpoint.phase_index == 1
        assert checkpoint.state == {"key": "value"}

    def test_checkpoint_checksum_generated(self):
        """Test checksum is automatically generated."""
        checkpoint = PhaseCheckpoint(
            checkpoint_id="ckpt-01-abc123",
            execution_id="exec-001",
            phase_name="design",
            phase_index=1,
            timestamp=datetime.utcnow(),
            state={"key": "value"},
        )

        assert checkpoint.checksum is not None
        assert len(checkpoint.checksum) == 64  # SHA-256 hex

    def test_checkpoint_integrity_verification(self):
        """Test integrity verification passes for valid checkpoint."""
        checkpoint = PhaseCheckpoint(
            checkpoint_id="ckpt-01-abc123",
            execution_id="exec-001",
            phase_name="design",
            phase_index=1,
            timestamp=datetime.utcnow(),
            state={"key": "value"},
        )

        assert checkpoint.verify_integrity() is True

    def test_checkpoint_integrity_fails_on_tampering(self):
        """Test integrity verification fails if data is modified."""
        checkpoint = PhaseCheckpoint(
            checkpoint_id="ckpt-01-abc123",
            execution_id="exec-001",
            phase_name="design",
            phase_index=1,
            timestamp=datetime.utcnow(),
            state={"key": "value"},
        )

        # Tamper with data
        checkpoint.state["key"] = "tampered"

        assert checkpoint.verify_integrity() is False

    def test_checkpoint_to_dict(self):
        """Test checkpoint serialization to dict."""
        timestamp = datetime.utcnow()
        checkpoint = PhaseCheckpoint(
            checkpoint_id="ckpt-01-abc123",
            execution_id="exec-001",
            phase_name="design",
            phase_index=1,
            timestamp=timestamp,
            state={"key": "value"},
            artifacts_created=["artifact1.json"],
        )

        data = checkpoint.to_dict()

        assert data["checkpoint_id"] == "ckpt-01-abc123"
        assert data["timestamp"] == timestamp.isoformat()
        assert data["artifacts_created"] == ["artifact1.json"]

    def test_checkpoint_from_dict(self):
        """Test checkpoint deserialization from dict."""
        timestamp = datetime.utcnow()
        data = {
            "checkpoint_id": "ckpt-01-abc123",
            "execution_id": "exec-001",
            "phase_name": "design",
            "phase_index": 1,
            "timestamp": timestamp.isoformat(),
            "state": {"key": "value"},
            "artifacts_created": ["artifact1.json"],
            "confluence_pages": [],
            "jira_comments": [],
            "files_created": [],
            "checksum": None,
        }

        checkpoint = PhaseCheckpoint.from_dict(data)

        assert checkpoint.checkpoint_id == "ckpt-01-abc123"
        assert checkpoint.artifacts_created == ["artifact1.json"]


class TestCheckpointStore:
    """Tests for CheckpointStore (AC-1)."""

    @pytest.fixture
    def temp_checkpoint_dir(self):
        """Create temporary checkpoint directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def store(self, temp_checkpoint_dir):
        """Create checkpoint store with temp directory."""
        return CheckpointStore(temp_checkpoint_dir)

    def test_store_initialization(self, store, temp_checkpoint_dir):
        """Test store creates checkpoint directory."""
        assert Path(temp_checkpoint_dir).exists()

    def test_save_checkpoint(self, store):
        """Test checkpoint can be saved."""
        checkpoint = PhaseCheckpoint(
            checkpoint_id="ckpt-01-abc123",
            execution_id="exec-001",
            phase_name="design",
            phase_index=1,
            timestamp=datetime.utcnow(),
            state={"key": "value"},
        )

        path = store.save(checkpoint)

        assert Path(path).exists()
        assert "ckpt-01-abc123.json" in path

    def test_load_checkpoint(self, store):
        """Test checkpoint can be loaded."""
        checkpoint = PhaseCheckpoint(
            checkpoint_id="ckpt-01-abc123",
            execution_id="exec-001",
            phase_name="design",
            phase_index=1,
            timestamp=datetime.utcnow(),
            state={"key": "value"},
        )
        store.save(checkpoint)

        loaded = store.load("exec-001", "ckpt-01-abc123")

        assert loaded is not None
        assert loaded.checkpoint_id == "ckpt-01-abc123"
        assert loaded.verify_integrity() is True

    def test_load_nonexistent_checkpoint(self, store):
        """Test loading nonexistent checkpoint returns None."""
        loaded = store.load("exec-001", "nonexistent")

        assert loaded is None

    def test_list_checkpoints(self, store):
        """Test listing checkpoints returns sorted by phase index."""
        for i in range(3):
            checkpoint = PhaseCheckpoint(
                checkpoint_id=f"ckpt-{i:02d}-abc",
                execution_id="exec-001",
                phase_name=f"phase-{i}",
                phase_index=i,
                timestamp=datetime.utcnow(),
                state={"phase": i},
            )
            store.save(checkpoint)

        checkpoints = store.list_checkpoints("exec-001")

        assert len(checkpoints) == 3
        assert checkpoints[0].phase_index == 0
        assert checkpoints[1].phase_index == 1
        assert checkpoints[2].phase_index == 2

    def test_get_latest_checkpoint(self, store):
        """Test getting latest checkpoint."""
        for i in range(3):
            checkpoint = PhaseCheckpoint(
                checkpoint_id=f"ckpt-{i:02d}-abc",
                execution_id="exec-001",
                phase_name=f"phase-{i}",
                phase_index=i,
                timestamp=datetime.utcnow(),
                state={"phase": i},
            )
            store.save(checkpoint)

        latest = store.get_latest_checkpoint("exec-001")

        assert latest is not None
        assert latest.phase_index == 2

    def test_delete_checkpoint(self, store):
        """Test checkpoint can be deleted."""
        checkpoint = PhaseCheckpoint(
            checkpoint_id="ckpt-01-abc123",
            execution_id="exec-001",
            phase_name="design",
            phase_index=1,
            timestamp=datetime.utcnow(),
            state={"key": "value"},
        )
        store.save(checkpoint)

        result = store.delete_checkpoint("exec-001", "ckpt-01-abc123")

        assert result is True
        assert store.load("exec-001", "ckpt-01-abc123") is None

    def test_cleanup_execution(self, store):
        """Test cleanup removes all checkpoints for execution."""
        for i in range(3):
            checkpoint = PhaseCheckpoint(
                checkpoint_id=f"ckpt-{i:02d}-abc",
                execution_id="exec-001",
                phase_name=f"phase-{i}",
                phase_index=i,
                timestamp=datetime.utcnow(),
                state={"phase": i},
            )
            store.save(checkpoint)

        count = store.cleanup_execution("exec-001")

        assert count == 3
        assert len(store.list_checkpoints("exec-001")) == 0


class TestRollbackExecutor:
    """Tests for RollbackExecutor (AC-3)."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def executor(self):
        """Create rollback executor."""
        return RollbackExecutor()

    def test_cleanup_file(self, executor, temp_dir):
        """Test file cleanup."""
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("test content")

        result = executor.cleanup_file(str(test_file))

        assert result.success is True
        assert not test_file.exists()

    def test_cleanup_directory(self, executor, temp_dir):
        """Test directory cleanup."""
        test_dir = Path(temp_dir) / "subdir"
        test_dir.mkdir()
        (test_dir / "file.txt").write_text("content")

        result = executor.cleanup_file(str(test_dir))

        assert result.success is True
        assert not test_dir.exists()

    def test_cleanup_nonexistent_file(self, executor):
        """Test cleanup of nonexistent file succeeds."""
        result = executor.cleanup_file("/nonexistent/path/file.txt")

        assert result.success is True  # Missing files are success

    def test_cleanup_checkpoint_artifacts(self, executor, temp_dir):
        """Test cleanup of all checkpoint artifacts."""
        # Create test files
        file1 = Path(temp_dir) / "artifact1.txt"
        file2 = Path(temp_dir) / "artifact2.txt"
        file1.write_text("content1")
        file2.write_text("content2")

        checkpoint = MagicMock()
        checkpoint.files_created = [str(file1), str(file2)]
        checkpoint.confluence_pages = []
        checkpoint.jira_comments = []
        checkpoint.artifacts_created = []

        result = executor.cleanup_checkpoint_artifacts(checkpoint)

        assert len(result["cleaned"]) == 2
        assert len(result["failed"]) == 0
        assert not file1.exists()
        assert not file2.exists()

    def test_dry_run_mode(self, executor, temp_dir):
        """Test dry run doesn't actually delete."""
        dry_executor = RollbackExecutor(dry_run=True)
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_text("test content")

        result = dry_executor.cleanup_file(str(test_file))

        assert result.success is True
        assert test_file.exists()  # File should still exist

    def test_custom_cleanup_handler(self, executor):
        """Test custom cleanup handler registration and execution."""
        cleanup_called = []

        def custom_handler(artifact_id: str) -> bool:
            cleanup_called.append(artifact_id)
            return True

        executor.register_cleanup_handler("database", custom_handler)

        result = executor.cleanup_artifact("database:record-123")

        assert result.success is True
        assert "record-123" in cleanup_called


class TestRollbackManager:
    """Tests for RollbackManager (AC-2)."""

    @pytest.fixture
    def temp_checkpoint_dir(self):
        """Create temporary checkpoint directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def manager(self, temp_checkpoint_dir):
        """Create rollback manager."""
        return RollbackManager(
            checkpoint_dir=temp_checkpoint_dir,
            enable_notifications=False,
        )

    def test_create_checkpoint(self, manager):
        """Test checkpoint creation through manager."""
        checkpoint = manager.create_checkpoint(
            execution_id="exec-001",
            phase_name="design",
            phase_index=1,
            state={"key": "value"},
        )

        assert checkpoint.execution_id == "exec-001"
        assert checkpoint.phase_name == "design"
        assert checkpoint.checkpoint_id.startswith("ckpt-01-")

    def test_rollback_to_checkpoint(self, manager, temp_checkpoint_dir):
        """Test rollback to specific checkpoint."""
        # Create checkpoints
        ckpt1 = manager.create_checkpoint(
            execution_id="exec-001",
            phase_name="requirements",
            phase_index=0,
            state={"phase": 0},
        )
        ckpt2 = manager.create_checkpoint(
            execution_id="exec-001",
            phase_name="design",
            phase_index=1,
            state={"phase": 1},
        )
        ckpt3 = manager.create_checkpoint(
            execution_id="exec-001",
            phase_name="implementation",
            phase_index=2,
            state={"phase": 2},
        )

        # Rollback to checkpoint 1
        report = manager.rollback_to_checkpoint("exec-001", ckpt1.checkpoint_id)

        assert report.result == RollbackResult.SUCCESS
        assert report.checkpoint_id == ckpt1.checkpoint_id

        # Verify checkpoints 2 and 3 are deleted
        checkpoints = manager.checkpoint_store.list_checkpoints("exec-001")
        assert len(checkpoints) == 1
        assert checkpoints[0].checkpoint_id == ckpt1.checkpoint_id

    def test_rollback_to_nonexistent_checkpoint(self, manager):
        """Test rollback to nonexistent checkpoint."""
        report = manager.rollback_to_checkpoint("exec-001", "nonexistent")

        assert report.result == RollbackResult.NO_CHECKPOINT

    def test_rollback_to_latest(self, manager):
        """Test rollback to latest checkpoint."""
        # Create checkpoints
        ckpt1 = manager.create_checkpoint(
            execution_id="exec-001",
            phase_name="requirements",
            phase_index=0,
            state={"phase": 0},
        )
        ckpt2 = manager.create_checkpoint(
            execution_id="exec-001",
            phase_name="design",
            phase_index=1,
            state={"phase": 1},
        )

        report = manager.rollback_to_latest("exec-001")

        assert report.result == RollbackResult.SUCCESS

    def test_get_recovery_state(self, manager):
        """Test getting state from checkpoint."""
        manager.create_checkpoint(
            execution_id="exec-001",
            phase_name="requirements",
            phase_index=0,
            state={"key": "value", "count": 42},
        )

        state = manager.get_recovery_state("exec-001")

        assert state == {"key": "value", "count": 42}

    def test_register_phase_handler(self, manager):
        """Test registering custom phase handler."""
        handler_calls = []

        def custom_handler(checkpoint):
            handler_calls.append(checkpoint.phase_name)
            return True

        manager.register_phase_handler("design", custom_handler)

        # Create checkpoints
        manager.create_checkpoint(
            execution_id="exec-001",
            phase_name="requirements",
            phase_index=0,
            state={},
        )
        manager.create_checkpoint(
            execution_id="exec-001",
            phase_name="design",
            phase_index=1,
            state={},
        )

        # Rollback - should call handler for design phase
        checkpoints = manager.checkpoint_store.list_checkpoints("exec-001")
        report = manager.rollback_to_checkpoint("exec-001", checkpoints[0].checkpoint_id)

        assert "design" in handler_calls


class TestRecoveryNotificationService:
    """Tests for RecoveryNotificationService (AC-4)."""

    @pytest.fixture
    def service(self):
        """Create notification service without webhook."""
        return RecoveryNotificationService(enabled=True)

    def test_notify_logs_message(self, service, caplog):
        """Test notification logs message."""
        with caplog.at_level("INFO"):
            service.notify(
                level=NotificationLevel.INFO,
                title="Test",
                message="Test message",
            )

        assert "Test message" in caplog.text

    def test_notify_stores_in_history(self, service):
        """Test notification stored in history."""
        service.notify(
            level=NotificationLevel.WARNING,
            title="Test",
            message="Test message",
        )

        history = service.get_notification_history()

        assert len(history) == 1
        assert history[0]["title"] == "Test"
        assert history[0]["level"] == "warning"

    def test_notify_rollback_started(self, service):
        """Test rollback started notification."""
        result = service.notify_rollback_started(
            execution_id="exec-001",
            phase_name="design",
            reason="Test failure",
        )

        assert result is True
        history = service.get_notification_history()
        assert "Rollback Started" in history[0]["title"]

    def test_notify_rollback_completed(self, service):
        """Test rollback completed notification."""
        result = service.notify_rollback_completed(
            execution_id="exec-001",
            success=True,
            artifacts_cleaned=5,
            artifacts_failed=0,
            duration_ms=150.5,
        )

        assert result is True
        history = service.get_notification_history()
        assert "Rollback Completed" in history[0]["title"]

    def test_min_level_filtering(self):
        """Test notifications below min level are not sent to webhook."""
        service = RecoveryNotificationService(
            enabled=True,
            min_level=NotificationLevel.ERROR,
        )

        # INFO should still be logged but not trigger webhook logic
        result = service.notify(
            level=NotificationLevel.INFO,
            title="Test",
            message="Test message",
        )

        assert result is True  # Should succeed (just skip webhook)

    def test_notification_to_slack_payload(self):
        """Test Slack payload generation."""
        from maestro_hive.maestro.rollback.notifications import Notification

        notification = Notification(
            level=NotificationLevel.ERROR,
            title="Test Alert",
            message="Something went wrong",
            details={"key": "value"},
        )

        payload = notification.to_slack_payload()

        assert "attachments" in payload
        assert payload["attachments"][0]["color"] == "#ff6600"  # ERROR color

    def test_notification_to_teams_payload(self):
        """Test Teams payload generation."""
        from maestro_hive.maestro.rollback.notifications import Notification

        notification = Notification(
            level=NotificationLevel.WARNING,
            title="Test Alert",
            message="Warning message",
            details={"execution_id": "exec-001"},
        )

        payload = notification.to_teams_payload()

        assert payload["@type"] == "MessageCard"
        assert "Test Alert" in payload["sections"][0]["activityTitle"]

    def test_custom_handler(self):
        """Test custom notification handler."""
        # Use min_level INFO to ensure handler is called
        service = RecoveryNotificationService(
            enabled=True,
            min_level=NotificationLevel.INFO,
        )
        received = []

        def handler(notification):
            received.append(notification)

        service.add_handler(handler)
        service.notify(
            level=NotificationLevel.WARNING,
            title="Test",
            message="Test message",
        )

        assert len(received) == 1
        assert received[0].title == "Test"

    @patch("urllib.request.urlopen")
    def test_webhook_sending(self, mock_urlopen):
        """Test webhook is called when configured."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        service = RecoveryNotificationService(
            webhook_url="https://example.com/webhook",
            webhook_type="slack",
            enabled=True,
        )

        service.notify(
            level=NotificationLevel.ERROR,
            title="Test",
            message="Test message",
        )

        mock_urlopen.assert_called_once()


class TestIntegration:
    """Integration tests for complete rollback flow."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_full_rollback_flow(self, temp_dir):
        """Test complete rollback scenario."""
        # Setup
        checkpoint_dir = Path(temp_dir) / "checkpoints"
        artifacts_dir = Path(temp_dir) / "artifacts"
        artifacts_dir.mkdir()

        manager = RollbackManager(
            checkpoint_dir=str(checkpoint_dir),
            enable_notifications=False,
        )

        # Create artifacts for each phase
        artifact1 = artifacts_dir / "phase1_artifact.json"
        artifact2 = artifacts_dir / "phase2_artifact.json"
        artifact3 = artifacts_dir / "phase3_artifact.json"
        artifact1.write_text('{"phase": 1}')
        artifact2.write_text('{"phase": 2}')
        artifact3.write_text('{"phase": 3}')

        # Create checkpoints with artifacts
        ckpt1 = manager.create_checkpoint(
            execution_id="exec-001",
            phase_name="requirements",
            phase_index=0,
            state={"phase": 0},
            files_created=[str(artifact1)],
        )
        ckpt2 = manager.create_checkpoint(
            execution_id="exec-001",
            phase_name="design",
            phase_index=1,
            state={"phase": 1},
            files_created=[str(artifact2)],
        )
        ckpt3 = manager.create_checkpoint(
            execution_id="exec-001",
            phase_name="implementation",
            phase_index=2,
            state={"phase": 2},
            files_created=[str(artifact3)],
        )

        # Verify all artifacts exist
        assert artifact1.exists()
        assert artifact2.exists()
        assert artifact3.exists()

        # Simulate failure at phase 3 - rollback to phase 1
        report = manager.rollback_to_checkpoint(
            "exec-001",
            ckpt1.checkpoint_id,
            reason="Phase 3 failed",
        )

        # Verify rollback
        assert report.result == RollbackResult.SUCCESS
        assert artifact1.exists()  # Phase 1 artifact preserved
        assert not artifact2.exists()  # Phase 2 artifact cleaned
        assert not artifact3.exists()  # Phase 3 artifact cleaned

        # Verify checkpoints
        checkpoints = manager.checkpoint_store.list_checkpoints("exec-001")
        assert len(checkpoints) == 1
        assert checkpoints[0].phase_index == 0

        # Verify recovery state
        state = manager.get_recovery_state("exec-001")
        assert state == {"phase": 0}
