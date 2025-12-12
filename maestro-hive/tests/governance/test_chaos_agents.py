"""
Tests for Chaos Agents (Loki & Janitor) - MD-3119

Acceptance Criteria:
- AC-1: Loki successfully kills a worker process without bringing down the whole system
- AC-2: Janitor successfully identifies and deletes an orphaned .tmp file
- AC-3: Safety - Loki never kills the Database or the Enforcer
- AC-4: Reporting - Both agents report their actions to the Audit Log
"""

import os
import signal
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from typing import List, Optional

import pytest

from maestro_hive.governance.chaos_agents import (
    ChaosActionType,
    ChaosEvent,
    ChaosManager,
    JanitorAgent,
    LokiAgent,
)


class TestLokiAgent:
    """Tests for LokiAgent - Chaos Engineering functionality."""

    def test_loki_instantiation(self):
        """Test that LokiAgent can be instantiated with defaults."""
        agent = LokiAgent()
        assert agent is not None
        assert agent._dry_run is True  # Default is dry run

    def test_loki_kills_worker_safely_ac1(self):
        """
        AC-1: Loki successfully kills a worker process without bringing down
        the whole system.

        Test that Loki can target and kill a worker process gracefully.
        """
        # Create mock for audit callback
        audit_events: List[ChaosEvent] = []

        def capture_audit(event: ChaosEvent):
            audit_events.append(event)

        agent = LokiAgent(dry_run=False)
        agent.on_chaos_event(capture_audit)

        # Mock os.kill to simulate process killing
        with patch("os.kill") as mock_kill:
            mock_kill.return_value = None  # Successful kill

            # Create a worker dict
            worker = {"id": "w1", "pid": 12345, "name": "test_worker"}

            # Run with workers
            events = agent.run([worker], kill_probability=1.0, latency_probability=0, exhaustion_probability=0)

            # Verify the kill was attempted
            mock_kill.assert_called_once_with(12345, signal.SIGTERM)

            # Verify events were created
            assert len(events) >= 1
            kill_event = events[0]
            assert kill_event.action_type == ChaosActionType.KILL_RANDOM_WORKER
            assert "test_worker" in kill_event.target
            assert kill_event.result == "killed"

        # Verify audit callback was called (AC-4)
        assert len(audit_events) >= 1

    def test_loki_protects_critical_services_ac3(self):
        """
        AC-3: Safety - Loki never kills the Database or the Enforcer.

        Test that protected targets cannot be killed.
        """
        agent = LokiAgent(dry_run=False)

        # Verify database and enforcer are in protected list
        assert "database" in agent._protected_targets
        assert "enforcer" in agent._protected_targets
        assert "governance_agent" in agent._protected_targets
        assert "audit_service" in agent._protected_targets

    def test_loki_refuses_to_kill_protected_target(self):
        """Test that Loki skips protected targets."""
        agent = LokiAgent(dry_run=False)

        # These should be protected
        protected_workers = [
            {"id": "w1", "pid": 1001, "name": "database"},
            {"id": "w2", "pid": 1002, "name": "enforcer"},
            {"id": "w3", "pid": 1003, "name": "governance_agent"},
            {"id": "w4", "pid": 1004, "name": "audit_service"},
        ]

        with patch("os.kill") as mock_kill:
            # Run chaos with 100% kill probability
            events = agent.run(protected_workers, kill_probability=1.0, latency_probability=0, exhaustion_probability=0)

            # Should NOT have killed any protected targets
            mock_kill.assert_not_called()
            assert len(events) == 0

    def test_loki_max_disruptions_limit(self):
        """Test that Loki respects max disruptions per run."""
        agent = LokiAgent(dry_run=True, max_disruptions=2)

        workers = [
            {"id": "w1", "pid": 1001, "name": "worker1"},
            {"id": "w2", "pid": 1002, "name": "worker2"},
            {"id": "w3", "pid": 1003, "name": "worker3"},
            {"id": "w4", "pid": 1004, "name": "worker4"},
            {"id": "w5", "pid": 1005, "name": "worker5"},
        ]

        # Run with 100% kill probability
        events = agent.run(workers, kill_probability=1.0, latency_probability=0, exhaustion_probability=0)

        # Should not exceed max_disruptions
        assert len(events) <= 2

    def test_loki_dry_run_no_actual_kill(self):
        """Test that dry run mode doesn't actually kill processes."""
        agent = LokiAgent(dry_run=True)

        with patch("os.kill") as mock_kill:
            worker = {"id": "w1", "pid": 12345, "name": "test_worker"}
            events = agent.run([worker], kill_probability=1.0, latency_probability=0, exhaustion_probability=0)

            # In dry run, os.kill should NOT be called
            mock_kill.assert_not_called()

            # But event should still be created
            assert len(events) >= 1
            assert events[0].result == "dry_run"


class TestJanitorAgent:
    """Tests for JanitorAgent - Anti-Entropy functionality."""

    def test_janitor_instantiation(self):
        """Test that JanitorAgent can be instantiated with defaults."""
        agent = JanitorAgent()
        assert agent is not None
        assert agent._dry_run is True  # Default is dry run

    def test_janitor_deletes_tmp_file_ac2(self):
        """
        AC-2: Janitor successfully identifies and deletes an orphaned .tmp file.

        Test that Janitor can find and delete .tmp files.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create orphan .tmp files
            tmp_file1 = Path(tmpdir) / "orphan1.tmp"
            tmp_file2 = Path(tmpdir) / "orphan2.tmp"
            tmp_file1.touch()
            tmp_file2.touch()

            # Also create a .temp file
            temp_file = Path(tmpdir) / "orphan3.temp"
            temp_file.touch()

            # Verify files exist
            assert tmp_file1.exists()
            assert tmp_file2.exists()
            assert temp_file.exists()

            # Create Janitor with dry_run=False
            audit_events: List[ChaosEvent] = []

            def capture_audit(event: ChaosEvent):
                audit_events.append(event)

            agent = JanitorAgent(dry_run=False, cleanup_dirs=[tmpdir])
            agent.on_janitor_event(capture_audit)

            # Run cleanup
            events = agent.run()

            # Find the cleanup event for our directory
            cleanup_event = None
            for event in events:
                if event.action_type == ChaosActionType.CLEANUP_ORPHAN_FILES and event.target == tmpdir:
                    cleanup_event = event
                    break

            # Verify files were deleted
            assert not tmp_file1.exists(), "orphan1.tmp should be deleted"
            assert not tmp_file2.exists(), "orphan2.tmp should be deleted"
            assert not temp_file.exists(), "orphan3.temp should be deleted"

            # Verify event was created
            assert cleanup_event is not None
            assert cleanup_event.action_type == ChaosActionType.CLEANUP_ORPHAN_FILES
            assert "cleaned" in cleanup_event.result.lower()

    def test_janitor_dry_run_no_delete(self):
        """Test that dry run mode doesn't actually delete files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create orphan .tmp file
            tmp_file = Path(tmpdir) / "orphan.tmp"
            tmp_file.touch()

            # Create Janitor with dry_run=True (default)
            agent = JanitorAgent(dry_run=True, cleanup_dirs=[tmpdir])

            # Run cleanup
            events = agent.run()

            # File should still exist
            assert tmp_file.exists(), "File should NOT be deleted in dry run"

            # But events should report what was found
            cleanup_events = [e for e in events if e.action_type == ChaosActionType.CLEANUP_ORPHAN_FILES]
            assert len(cleanup_events) > 0

    def test_janitor_archive_old_logs(self):
        """Test that Janitor can archive old logs."""
        agent = JanitorAgent(dry_run=True)

        # Run will call _archive_old_logs internally
        events = agent.run()

        # Find archive event
        archive_events = [e for e in events if e.action_type == ChaosActionType.ARCHIVE_OLD_LOGS]
        assert len(archive_events) > 0


class TestChaosManager:
    """Tests for ChaosManager - Orchestration of Loki & Janitor."""

    def test_chaos_manager_instantiation(self):
        """Test that ChaosManager can be instantiated."""
        manager = ChaosManager()
        assert manager is not None
        assert manager.loki is not None
        assert manager.janitor is not None

    def test_chaos_manager_runs_both_agents(self):
        """Test that ChaosManager can orchestrate both agents."""
        audit_events: List[ChaosEvent] = []

        def capture_audit(event: ChaosEvent):
            audit_events.append(event)

        loki = LokiAgent(dry_run=True)
        janitor = JanitorAgent(dry_run=True)

        loki.on_chaos_event(capture_audit)
        janitor.on_janitor_event(capture_audit)

        manager = ChaosManager(loki=loki, janitor=janitor)

        # Run chaos test with workers
        workers = [{"id": "w1", "pid": 1001, "name": "test_worker"}]
        results = manager.run_chaos_test(workers)

        # Should get results from both agents
        assert "loki_events" in results
        assert "janitor_events" in results
        assert isinstance(results["loki_events"], list)
        assert isinstance(results["janitor_events"], list)


class TestAuditIntegration:
    """Tests for Audit Log integration - AC-4."""

    def test_loki_reports_to_audit_ac4(self):
        """
        AC-4: Loki reports actions to Audit Log.
        """
        audit_events: List[ChaosEvent] = []

        def capture_audit(event: ChaosEvent):
            audit_events.append(event)

        agent = LokiAgent(dry_run=True)
        agent.on_chaos_event(capture_audit)

        # Run chaos
        workers = [{"id": "w1", "pid": 12345, "name": "test_worker"}]
        agent.run(workers, kill_probability=1.0, latency_probability=0, exhaustion_probability=0)

        # Verify audit was called
        assert len(audit_events) >= 1
        assert audit_events[0].agent == "loki"

    def test_janitor_reports_to_audit_ac4(self):
        """
        AC-4: Janitor reports actions to Audit Log.
        """
        audit_events: List[ChaosEvent] = []

        def capture_audit(event: ChaosEvent):
            audit_events.append(event)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a .tmp file to find
            tmp_file = Path(tmpdir) / "test.tmp"
            tmp_file.touch()

            agent = JanitorAgent(dry_run=True, cleanup_dirs=[tmpdir])
            agent.on_janitor_event(capture_audit)

            # Run cleanup
            agent.run()

        # Verify audit was called
        assert len(audit_events) >= 1
        assert audit_events[0].agent == "janitor"


class TestChaosEvent:
    """Tests for ChaosEvent data model."""

    def test_chaos_event_creation(self):
        """Test that ChaosEvent can be created with all fields."""
        from datetime import datetime

        event = ChaosEvent(
            event_id="test-123",
            action_type=ChaosActionType.KILL_RANDOM_WORKER,
            agent="loki",
            timestamp=datetime.utcnow(),
            target="test_worker",
            result="killed",
            metadata={"pid": 12345}
        )

        assert event.event_id == "test-123"
        assert event.action_type == ChaosActionType.KILL_RANDOM_WORKER
        assert event.agent == "loki"
        assert event.target == "test_worker"
        assert event.result == "killed"
        assert event.metadata["pid"] == 12345

    def test_chaos_event_to_dict(self):
        """Test serialization to dictionary."""
        from datetime import datetime

        event = ChaosEvent(
            event_id="test-123",
            action_type=ChaosActionType.CLEANUP_ORPHAN_FILES,
            agent="janitor",
            target="/tmp",
            result="cleaned",
        )

        d = event.to_dict()
        assert d["event_id"] == "test-123"
        assert d["action_type"] == "cleanup_orphan_files"
        assert d["agent"] == "janitor"
        assert d["target"] == "/tmp"
        assert d["result"] == "cleaned"


class TestChaosActionType:
    """Tests for ChaosActionType enum."""

    def test_all_action_types_exist(self):
        """Test that all expected action types are defined."""
        assert hasattr(ChaosActionType, "KILL_RANDOM_WORKER")
        assert hasattr(ChaosActionType, "INJECT_LATENCY")
        assert hasattr(ChaosActionType, "SIMULATE_RESOURCE_EXHAUSTION")
        assert hasattr(ChaosActionType, "ARCHIVE_OLD_LOGS")
        assert hasattr(ChaosActionType, "REMOVE_DEAD_CODE")
        assert hasattr(ChaosActionType, "VALIDATE_DOCUMENTATION")
        assert hasattr(ChaosActionType, "CLEANUP_ORPHAN_FILES")

    def test_action_type_values(self):
        """Test enum values."""
        assert ChaosActionType.KILL_RANDOM_WORKER.value == "kill_random_worker"
        assert ChaosActionType.CLEANUP_ORPHAN_FILES.value == "cleanup_orphan_files"
