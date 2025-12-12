"""
Tests for Auditor Service - MD-3117 (Asynchronous Governance)

JIRA Acceptance Criteria:
- AC-1: Coverage Verification - If test doesn't increase coverage, no reputation awarded
- AC-2: Async Processing - Does not block main agent execution loop
- AC-3: Sybil Detection - Flags if 2+ agents edit same file within 100ms
- AC-4: Logging - All decisions written to immutable audit log
"""

import asyncio
import hashlib
import time
from pathlib import Path
from typing import List, Tuple
from unittest.mock import MagicMock

import pytest

from maestro_hive.governance.auditor import (
    AuditDecision,
    AuditLogEntry,
    AuditReason,
    AuditorService,
    CoverageReport,
    CoverageVerifier,
    FileEditEvent,
    ImmutableAuditLog,
    SybilDetector,
    create_auditor_service,
)


# ============================================================
# AC-1: Coverage Verification Tests
# ============================================================

class TestAC1_CoverageVerification:
    """
    AC-1: If an agent adds a test that doesn't increase coverage,
    no reputation is awarded.
    """

    @pytest.fixture
    def coverage_verifier(self):
        return CoverageVerifier()

    @pytest.fixture
    def auditor_with_reputation_tracking(self):
        """Auditor with reputation callback to track awards."""
        reputation_awards: List[Tuple[str, int]] = []

        def track_reputation(agent_id: str, amount: int):
            reputation_awards.append((agent_id, amount))

        auditor = AuditorService(reputation_callback=track_reputation)
        auditor._reputation_awards = reputation_awards  # Attach for test access
        return auditor

    @pytest.mark.asyncio
    async def test_reputation_awarded_when_coverage_increases(
        self, auditor_with_reputation_tracking
    ):
        """Test that reputation IS awarded when coverage increases."""
        auditor = auditor_with_reputation_tracking
        await auditor.start()

        try:
            # Agent submits test that increases coverage
            reputation_awarded, entry = await auditor.audit_coverage_direct(
                agent_id="agent_001",
                test_file="tests/test_feature.py",
                coverage_before=75.0,
                coverage_after=80.0  # +5% increase
            )

            assert reputation_awarded is True
            assert entry.decision == AuditDecision.APPROVED
            assert entry.reason == AuditReason.COVERAGE_INCREASED
            assert entry.metadata["delta"] == 5.0

        finally:
            await auditor.stop()

    @pytest.mark.asyncio
    async def test_no_reputation_when_coverage_not_increased_ac1(
        self, auditor_with_reputation_tracking
    ):
        """
        AC-1 CRITICAL TEST: No reputation awarded if coverage doesn't increase.
        """
        auditor = auditor_with_reputation_tracking
        await auditor.start()

        try:
            # Agent submits test that doesn't increase coverage
            reputation_awarded, entry = await auditor.audit_coverage_direct(
                agent_id="agent_002",
                test_file="tests/test_useless.py",
                coverage_before=80.0,
                coverage_after=80.0  # No change
            )

            # AC-1: No reputation should be awarded
            assert reputation_awarded is False
            assert entry.decision == AuditDecision.REJECTED
            assert entry.reason == AuditReason.COVERAGE_NOT_INCREASED
            assert entry.metadata["delta"] == 0.0

        finally:
            await auditor.stop()

    @pytest.mark.asyncio
    async def test_no_reputation_when_coverage_decreases(
        self, auditor_with_reputation_tracking
    ):
        """Test that reputation is NOT awarded when coverage decreases."""
        auditor = auditor_with_reputation_tracking
        await auditor.start()

        try:
            reputation_awarded, entry = await auditor.audit_coverage_direct(
                agent_id="agent_003",
                test_file="tests/test_bad.py",
                coverage_before=80.0,
                coverage_after=75.0  # -5% decrease
            )

            assert reputation_awarded is False
            assert entry.decision == AuditDecision.REJECTED
            assert entry.metadata["delta"] == -5.0

        finally:
            await auditor.stop()

    @pytest.mark.asyncio
    async def test_coverage_verifier_tracks_history(self, coverage_verifier):
        """Test that coverage verification history is tracked per agent."""
        # First verification
        increased1, report1 = await coverage_verifier.verify_coverage_increase(
            agent_id="agent_a",
            test_file="test1.py",
            coverage_before=50.0,
            coverage_after=60.0
        )
        assert increased1 is True
        assert report1.delta == 10.0

        # Second verification for same agent
        increased2, report2 = await coverage_verifier.verify_coverage_increase(
            agent_id="agent_a",
            test_file="test2.py",
            coverage_before=60.0,
            coverage_after=60.0
        )
        assert increased2 is False

        # Check history
        history = coverage_verifier.get_agent_coverage_history("agent_a")
        assert len(history) == 2
        assert history[0].increased is True
        assert history[1].increased is False


# ============================================================
# AC-2: Async Processing Tests
# ============================================================

class TestAC2_AsyncProcessing:
    """
    AC-2: Does not block the main agent execution loop.
    Auditing happens asynchronously in background.
    """

    @pytest.mark.asyncio
    async def test_submit_coverage_check_returns_immediately_ac2(self):
        """
        AC-2 CRITICAL TEST: Coverage check submission doesn't block.
        """
        auditor = AuditorService()
        await auditor.start()

        try:
            start_time = time.time()

            # Submit multiple checks - should return immediately
            for i in range(100):
                await auditor.submit_coverage_check(
                    agent_id=f"agent_{i}",
                    test_file=f"test_{i}.py",
                    coverage_before=50.0,
                    coverage_after=51.0
                )

            elapsed = time.time() - start_time

            # AC-2: Should complete in < 100ms (non-blocking)
            assert elapsed < 0.1, f"Submission took {elapsed}s - should be non-blocking"

            # Queue should have tasks
            assert auditor._task_queue.qsize() > 0

        finally:
            await auditor.stop()

    @pytest.mark.asyncio
    async def test_submit_file_edit_returns_immediately_ac2(self):
        """
        AC-2 CRITICAL TEST: File edit submission doesn't block.
        """
        auditor = AuditorService()
        await auditor.start()

        try:
            start_time = time.time()

            # Submit multiple edits - should return immediately
            for i in range(100):
                await auditor.submit_file_edit(
                    agent_id=f"agent_{i}",
                    file_path=f"src/file_{i}.py",
                    content_hash=f"hash_{i}"
                )

            elapsed = time.time() - start_time

            # AC-2: Should complete in < 100ms (non-blocking)
            assert elapsed < 0.1, f"Submission took {elapsed}s - should be non-blocking"

        finally:
            await auditor.stop()

    @pytest.mark.asyncio
    async def test_async_processor_runs_in_background(self):
        """Test that async processor handles tasks in background."""
        auditor = AuditorService()
        await auditor.start()

        try:
            # Submit a task
            await auditor.submit_coverage_check(
                agent_id="agent_bg",
                test_file="test_bg.py",
                coverage_before=50.0,
                coverage_after=55.0
            )

            # Wait for processing
            await asyncio.sleep(0.2)

            # Check that task was processed (audit log has entry)
            entries = auditor.audit_log.get_entries(agent_id="agent_bg")
            assert len(entries) >= 1

        finally:
            await auditor.stop()

    @pytest.mark.asyncio
    async def test_main_loop_not_blocked_during_audit(self):
        """Test that main code execution continues while auditing."""
        auditor = AuditorService()
        await auditor.start()

        results = []

        async def main_work():
            """Simulated main agent work."""
            for i in range(5):
                results.append(f"work_{i}")
                await asyncio.sleep(0.01)

        try:
            # Start main work
            main_task = asyncio.create_task(main_work())

            # Submit audit tasks simultaneously
            for i in range(10):
                await auditor.submit_coverage_check(
                    agent_id=f"agent_{i}",
                    test_file=f"test_{i}.py",
                    coverage_before=50.0,
                    coverage_after=55.0
                )

            # Wait for main work to complete
            await main_task

            # Main work should have completed (AC-2)
            assert len(results) == 5
            assert results == ["work_0", "work_1", "work_2", "work_3", "work_4"]

        finally:
            await auditor.stop()


# ============================================================
# AC-3: Sybil Detection Tests
# ============================================================

class TestAC3_SybilDetection:
    """
    AC-3: Flags if 2+ agents try to edit the same file within 100ms.
    """

    @pytest.fixture
    def sybil_detector(self):
        return SybilDetector()

    @pytest.mark.asyncio
    async def test_sybil_detected_concurrent_edits_ac3(self, sybil_detector):
        """
        AC-3 CRITICAL TEST: Flag when 2+ agents edit same file within 100ms.
        """
        file_path = "src/shared_file.py"

        # Agent 1 edits file
        event1 = FileEditEvent.create(
            agent_id="agent_1",
            file_path=file_path,
            content_hash="hash_1"
        )
        sybil1 = await sybil_detector.record_edit(event1)
        assert sybil1 is False  # First edit, no sybil

        # Agent 2 edits SAME file within 100ms
        event2 = FileEditEvent(
            agent_id="agent_2",
            file_path=file_path,
            timestamp_ms=event1.timestamp_ms + 50,  # 50ms later (within window)
            edit_hash="hash_2"
        )
        sybil2 = await sybil_detector.record_edit(event2)

        # AC-3: Should detect sybil activity
        assert sybil2 is True

        # Check flagged events
        flagged = sybil_detector.get_flagged_events()
        assert len(flagged) >= 1
        assert file_path in [f["file_path"] for f in flagged]

    @pytest.mark.asyncio
    async def test_no_sybil_when_different_files(self, sybil_detector):
        """Test no sybil when agents edit different files."""
        event1 = FileEditEvent.create(
            agent_id="agent_1",
            file_path="src/file_a.py",
            content_hash="hash_1"
        )
        sybil1 = await sybil_detector.record_edit(event1)

        event2 = FileEditEvent(
            agent_id="agent_2",
            file_path="src/file_b.py",  # Different file
            timestamp_ms=event1.timestamp_ms + 50,
            edit_hash="hash_2"
        )
        sybil2 = await sybil_detector.record_edit(event2)

        assert sybil1 is False
        assert sybil2 is False

    @pytest.mark.asyncio
    async def test_no_sybil_when_outside_window(self, sybil_detector):
        """Test no sybil when edits are > 100ms apart."""
        file_path = "src/shared_file.py"

        event1 = FileEditEvent.create(
            agent_id="agent_1",
            file_path=file_path,
            content_hash="hash_1"
        )
        await sybil_detector.record_edit(event1)

        # Agent 2 edits SAME file but AFTER 100ms window
        event2 = FileEditEvent(
            agent_id="agent_2",
            file_path=file_path,
            timestamp_ms=event1.timestamp_ms + 150,  # 150ms later (outside window)
            edit_hash="hash_2"
        )
        sybil2 = await sybil_detector.record_edit(event2)

        assert sybil2 is False  # Outside detection window

    @pytest.mark.asyncio
    async def test_same_agent_no_sybil(self, sybil_detector):
        """Test no sybil when same agent edits file multiple times."""
        file_path = "src/my_file.py"

        event1 = FileEditEvent.create(
            agent_id="agent_1",
            file_path=file_path,
            content_hash="hash_1"
        )
        await sybil_detector.record_edit(event1)

        # Same agent edits again
        event2 = FileEditEvent(
            agent_id="agent_1",  # Same agent
            file_path=file_path,
            timestamp_ms=event1.timestamp_ms + 50,
            edit_hash="hash_2"
        )
        sybil2 = await sybil_detector.record_edit(event2)

        assert sybil2 is False  # Same agent, not sybil

    @pytest.mark.asyncio
    async def test_three_agents_sybil_detection(self, sybil_detector):
        """Test sybil detection with 3+ agents."""
        file_path = "src/contested_file.py"
        base_time = time.time() * 1000

        # Agent 1 edits
        event1 = FileEditEvent(
            agent_id="agent_1",
            file_path=file_path,
            timestamp_ms=base_time,
            edit_hash="hash_1"
        )
        sybil1 = await sybil_detector.record_edit(event1)

        # Agent 2 edits within window
        event2 = FileEditEvent(
            agent_id="agent_2",
            file_path=file_path,
            timestamp_ms=base_time + 30,
            edit_hash="hash_2"
        )
        sybil2 = await sybil_detector.record_edit(event2)

        # Agent 3 edits within window
        event3 = FileEditEvent(
            agent_id="agent_3",
            file_path=file_path,
            timestamp_ms=base_time + 60,
            edit_hash="hash_3"
        )
        sybil3 = await sybil_detector.record_edit(event3)

        assert sybil1 is False
        assert sybil2 is True  # 2 agents
        assert sybil3 is True  # 3 agents

    @pytest.mark.asyncio
    async def test_sybil_via_auditor_service_ac3(self):
        """Test sybil detection through AuditorService."""
        auditor = AuditorService()
        await auditor.start()

        try:
            file_path = "src/target.py"

            # Agent 1 edits
            sybil1, entry1 = await auditor.check_sybil_direct(
                agent_id="agent_1",
                file_path=file_path,
                content_hash="hash_1"
            )
            assert sybil1 is False
            assert entry1.decision == AuditDecision.APPROVED

            # Agent 2 edits same file immediately
            sybil2, entry2 = await auditor.check_sybil_direct(
                agent_id="agent_2",
                file_path=file_path,
                content_hash="hash_2"
            )

            # AC-3: Should flag sybil activity
            assert sybil2 is True
            assert entry2.decision == AuditDecision.FLAGGED
            assert entry2.reason == AuditReason.SYBIL_DETECTED

        finally:
            await auditor.stop()


# ============================================================
# AC-4: Immutable Audit Logging Tests
# ============================================================

class TestAC4_ImmutableAuditLog:
    """
    AC-4: All decisions are written to the immutable audit log.
    """

    @pytest.fixture
    def audit_log(self):
        return ImmutableAuditLog()

    @pytest.mark.asyncio
    async def test_all_decisions_logged_ac4(self):
        """
        AC-4 CRITICAL TEST: All audit decisions must be logged.
        """
        auditor = AuditorService()
        await auditor.start()

        try:
            # Coverage check (should log)
            await auditor.audit_coverage_direct(
                agent_id="agent_cov",
                test_file="test.py",
                coverage_before=50.0,
                coverage_after=55.0
            )

            # Sybil check (should log)
            await auditor.check_sybil_direct(
                agent_id="agent_sybil",
                file_path="src/file.py",
                content_hash="hash"
            )

            # Verify all decisions logged
            entries = auditor.audit_log.get_entries()
            assert len(entries) >= 2

            # Check agents are logged
            agent_ids = [e.agent_id for e in entries]
            assert "agent_cov" in agent_ids
            assert "agent_sybil" in agent_ids

        finally:
            await auditor.stop()

    @pytest.mark.asyncio
    async def test_audit_log_hash_chain_integrity(self, audit_log):
        """Test that audit log maintains hash chain integrity."""
        # Add entries
        entry1 = await audit_log.append(
            agent_id="agent_1",
            action="test_action",
            decision=AuditDecision.APPROVED,
            reason=AuditReason.VALID_CONTRIBUTION
        )

        entry2 = await audit_log.append(
            agent_id="agent_2",
            action="test_action",
            decision=AuditDecision.REJECTED,
            reason=AuditReason.COVERAGE_NOT_INCREASED
        )

        # Verify chain
        assert audit_log.verify_chain() is True

        # Entry 2 should link to entry 1
        assert entry2.previous_hash == entry1.entry_hash

        # Entry 1 should link to genesis
        assert entry1.previous_hash == ImmutableAuditLog.GENESIS_HASH

    @pytest.mark.asyncio
    async def test_audit_log_tamper_detection_ac4(self, audit_log):
        """Test that tampering with audit log is detected."""
        # Add entries
        await audit_log.append(
            agent_id="agent_1",
            action="action_1",
            decision=AuditDecision.APPROVED,
            reason=AuditReason.VALID_CONTRIBUTION
        )

        await audit_log.append(
            agent_id="agent_2",
            action="action_2",
            decision=AuditDecision.APPROVED,
            reason=AuditReason.COVERAGE_INCREASED
        )

        # Verify chain is valid
        assert audit_log.verify_chain() is True

        # Tamper with first entry
        audit_log._entries[0].agent_id = "tampered_agent"

        # Chain should now be invalid
        assert audit_log.verify_chain() is False

    @pytest.mark.asyncio
    async def test_audit_log_entries_contain_metadata(self, audit_log):
        """Test that audit entries contain full metadata."""
        entry = await audit_log.append(
            agent_id="agent_meta",
            action="coverage_check",
            decision=AuditDecision.APPROVED,
            reason=AuditReason.COVERAGE_INCREASED,
            metadata={
                "test_file": "test_feature.py",
                "coverage_before": 50.0,
                "coverage_after": 60.0,
                "delta": 10.0
            }
        )

        assert entry.metadata["test_file"] == "test_feature.py"
        assert entry.metadata["delta"] == 10.0

    @pytest.mark.asyncio
    async def test_audit_log_serialization(self, audit_log):
        """Test that audit entries can be serialized."""
        entry = await audit_log.append(
            agent_id="agent_serial",
            action="test_action",
            decision=AuditDecision.FLAGGED,
            reason=AuditReason.SYBIL_DETECTED,
            metadata={"file": "contested.py"}
        )

        # Serialize
        data = entry.to_dict()

        assert data["agent_id"] == "agent_serial"
        assert data["decision"] == "flagged"
        assert data["reason"] == "sybil_detected"
        assert "entry_hash" in data
        assert "previous_hash" in data

    @pytest.mark.asyncio
    async def test_audit_log_stats(self, audit_log):
        """Test audit log statistics."""
        await audit_log.append("a1", "act", AuditDecision.APPROVED, AuditReason.VALID_CONTRIBUTION)
        await audit_log.append("a2", "act", AuditDecision.APPROVED, AuditReason.COVERAGE_INCREASED)
        await audit_log.append("a3", "act", AuditDecision.REJECTED, AuditReason.COVERAGE_NOT_INCREASED)
        await audit_log.append("a4", "act", AuditDecision.FLAGGED, AuditReason.SYBIL_DETECTED)

        stats = audit_log.get_stats()

        assert stats["total_entries"] == 4
        assert stats["by_decision"]["approved"] == 2
        assert stats["by_decision"]["rejected"] == 1
        assert stats["by_decision"]["flagged"] == 1
        assert stats["chain_valid"] is True


# ============================================================
# Integration Tests
# ============================================================

class TestAuditorServiceIntegration:
    """Integration tests for full AuditorService workflow."""

    @pytest.mark.asyncio
    async def test_full_audit_workflow(self):
        """Test complete audit workflow with all components."""
        reputation_awards = []

        def track_rep(agent_id, amount):
            reputation_awards.append((agent_id, amount))

        auditor = create_auditor_service(reputation_callback=track_rep)
        await auditor.start()

        try:
            # Good agent: increases coverage
            good_awarded, good_entry = await auditor.audit_coverage_direct(
                agent_id="good_agent",
                test_file="test_good.py",
                coverage_before=50.0,
                coverage_after=60.0
            )

            # Bad agent: no coverage increase
            bad_awarded, bad_entry = await auditor.audit_coverage_direct(
                agent_id="bad_agent",
                test_file="test_bad.py",
                coverage_before=60.0,
                coverage_after=60.0
            )

            # Verify results
            assert good_awarded is True
            assert bad_awarded is False

            # Check audit log has both entries
            assert len(auditor.audit_log.get_entries()) >= 2

            # Check chain integrity
            assert auditor.audit_log.verify_chain() is True

        finally:
            await auditor.stop()

    @pytest.mark.asyncio
    async def test_sybil_attack_scenario(self):
        """Test a simulated sybil attack scenario."""
        auditor = AuditorService()
        await auditor.start()

        try:
            file_path = "src/valuable_file.py"

            # Multiple "agents" (possibly same attacker) edit same file rapidly
            results = []
            for i in range(5):
                sybil, entry = await auditor.check_sybil_direct(
                    agent_id=f"suspicious_agent_{i}",
                    file_path=file_path,
                    content_hash=f"hash_{i}"
                )
                results.append((sybil, entry.decision))

            # First should pass, rest should be flagged
            assert results[0][0] is False
            assert all(r[0] is True for r in results[1:])

            # Check flagged events
            flagged = auditor.sybil_detector.get_flagged_events()
            assert len(flagged) >= 1

        finally:
            await auditor.stop()

    @pytest.mark.asyncio
    async def test_auditor_stats(self):
        """Test comprehensive auditor statistics."""
        auditor = AuditorService()
        await auditor.start()

        try:
            # Generate some activity
            await auditor.audit_coverage_direct("a1", "t1.py", 50, 55)
            await auditor.audit_coverage_direct("a2", "t2.py", 55, 55)
            await auditor.check_sybil_direct("a3", "f1.py", "h1")

            stats = auditor.get_stats()

            assert "audit_log" in stats
            assert "sybil_detector" in stats
            assert "coverage_verifier" in stats
            assert stats["audit_log"]["total_entries"] >= 3

        finally:
            await auditor.stop()


# ============================================================
# Edge Cases
# ============================================================

class TestEdgeCases:
    """Edge case tests."""

    @pytest.mark.asyncio
    async def test_zero_coverage_increase(self):
        """Test exact zero coverage change."""
        verifier = CoverageVerifier()
        increased, report = await verifier.verify_coverage_increase(
            agent_id="agent",
            test_file="test.py",
            coverage_before=75.0,
            coverage_after=75.0
        )
        assert increased is False
        assert report.delta == 0.0

    @pytest.mark.asyncio
    async def test_tiny_coverage_increase(self):
        """Test very small coverage increase."""
        verifier = CoverageVerifier()
        increased, report = await verifier.verify_coverage_increase(
            agent_id="agent",
            test_file="test.py",
            coverage_before=75.0,
            coverage_after=75.001
        )
        assert increased is True
        assert report.delta > 0

    @pytest.mark.asyncio
    async def test_audit_log_empty_chain_valid(self):
        """Test that empty audit log has valid chain."""
        log = ImmutableAuditLog()
        assert log.verify_chain() is True

    @pytest.mark.asyncio
    async def test_sybil_detector_cleanup(self):
        """Test that sybil detector cleans up old entries."""
        detector = SybilDetector()

        # Add many edits to trigger cleanup
        for i in range(1500):
            event = FileEditEvent.create(
                agent_id=f"agent_{i % 10}",
                file_path="src/file.py",
                content_hash=f"hash_{i}"
            )
            await detector.record_edit(event)

        # Should have cleaned up (max 500 after cleanup)
        assert len(detector._edit_history["src/file.py"]) <= 1000


# ============================================================
# Factory Function Tests
# ============================================================

class TestFactoryFunction:
    """Test create_auditor_service factory."""

    def test_create_auditor_service_default(self):
        """Test creating auditor with defaults."""
        auditor = create_auditor_service()
        assert auditor is not None
        assert auditor.audit_log is not None
        assert auditor.sybil_detector is not None
        assert auditor.coverage_verifier is not None

    def test_create_auditor_service_with_callback(self):
        """Test creating auditor with reputation callback."""
        callback = MagicMock()
        auditor = create_auditor_service(reputation_callback=callback)
        assert auditor._reputation_callback == callback
