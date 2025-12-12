"""
Tests for Quarantine Manager - MD-3123 (Agent Isolation)

JIRA Acceptance Criteria:
- AC-1: Quarantine Agent - Block all operations for quarantined agents
- AC-2: Automatic Triggers - Quarantine triggered by Auditor sybil detection
- AC-3: Review Workflow - Appeal and release process
- AC-4: Audit Logging - All quarantine actions logged
"""

import asyncio
from datetime import datetime, timedelta
from typing import List
from unittest.mock import MagicMock

import pytest

from maestro_hive.governance.quarantine import (
    QuarantineAction,
    QuarantineEntry,
    QuarantineError,
    QuarantineManager,
    QuarantineReason,
    QuarantineStatus,
    ReviewDecision,
    create_quarantine_manager,
)


# ============================================================
# AC-1: Quarantine Agent Tests
# ============================================================

class TestAC1_QuarantineAgent:
    """
    AC-1: QuarantineManager can place an agent in quarantine,
    blocking all its operations.
    """

    @pytest.fixture
    def manager(self):
        return QuarantineManager(grace_period_seconds=0)  # No grace period for testing

    @pytest.mark.asyncio
    async def test_quarantine_agent_ac1(self, manager):
        """
        AC-1 CRITICAL TEST: Quarantine blocks agent operations.
        """
        # Quarantine an agent
        entry = await manager.quarantine(
            agent_id="agent_001",
            reason=QuarantineReason.MANUAL_QUARANTINE,
            performed_by="admin",
            immediate=True
        )

        assert entry is not None
        assert entry.status == QuarantineStatus.ACTIVE
        assert entry.agent_id == "agent_001"
        assert entry.reason == QuarantineReason.MANUAL_QUARANTINE

        # Check quarantine status
        assert manager.is_quarantined("agent_001") is True

    @pytest.mark.asyncio
    async def test_quarantined_agent_gets_error_ac1(self, manager):
        """
        AC-1 CRITICAL TEST: Quarantined agents receive QuarantineError.
        """
        await manager.quarantine(
            agent_id="agent_002",
            reason=QuarantineReason.SYBIL_DETECTED,
            immediate=True
        )

        # Should raise QuarantineError
        with pytest.raises(QuarantineError) as exc_info:
            manager.check_operation("agent_002", "publish")

        assert exc_info.value.agent_id == "agent_002"
        assert "publish" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_non_quarantined_agent_allowed(self, manager):
        """Test that non-quarantined agents can operate freely."""
        # Should not raise
        manager.check_operation("agent_003", "publish")

    @pytest.mark.asyncio
    async def test_quarantine_state_persisted(self, manager):
        """Test that quarantine state is persisted."""
        await manager.quarantine(
            agent_id="agent_004",
            reason=QuarantineReason.POLICY_VIOLATION,
            immediate=True
        )

        # Check entry exists
        entry = manager.get_quarantine_entry("agent_004")
        assert entry is not None
        assert entry.status == QuarantineStatus.ACTIVE

        # Check in quarantined list
        quarantined = manager.get_quarantined_agents()
        assert len(quarantined) >= 1
        agent_ids = [e.agent_id for e in quarantined]
        assert "agent_004" in agent_ids

    @pytest.mark.asyncio
    async def test_grace_period_respected(self):
        """Test that grace period delays quarantine enforcement."""
        manager = QuarantineManager(grace_period_seconds=60)

        entry = await manager.quarantine(
            agent_id="agent_005",
            reason=QuarantineReason.SYBIL_DETECTED,
            immediate=False  # Use grace period
        )

        assert entry.grace_period_ends is not None

        # During grace period, should NOT be quarantined
        assert manager.is_quarantined("agent_005") is False

        # Should not raise during grace period
        manager.check_operation("agent_005", "publish")

    @pytest.mark.asyncio
    async def test_immediate_quarantine_skips_grace(self, manager):
        """Test that immediate=True skips grace period."""
        entry = await manager.quarantine(
            agent_id="agent_006",
            reason=QuarantineReason.SYBIL_DETECTED,
            immediate=True
        )

        assert entry.grace_period_ends is None
        assert manager.is_quarantined("agent_006") is True

    @pytest.mark.asyncio
    async def test_repeated_quarantine_increments_violations(self, manager):
        """Test that repeated quarantine increments violation count."""
        await manager.quarantine("agent_007", QuarantineReason.SYBIL_DETECTED, immediate=True)
        entry1 = manager.get_quarantine_entry("agent_007")
        assert entry1.violation_count == 1

        await manager.quarantine("agent_007", QuarantineReason.POLICY_VIOLATION, immediate=True)
        entry2 = manager.get_quarantine_entry("agent_007")
        assert entry2.violation_count == 2


# ============================================================
# AC-2: Automatic Triggers Tests
# ============================================================

class TestAC2_AutomaticTriggers:
    """
    AC-2: Quarantine is automatically triggered by Auditor sybil detection.
    """

    @pytest.mark.asyncio
    async def test_sybil_detection_triggers_quarantine_ac2(self):
        """
        AC-2 CRITICAL TEST: Quarantine triggered after sybil threshold.
        """
        manager = QuarantineManager(sybil_threshold=3, grace_period_seconds=0)

        # First two flags - no quarantine
        result1 = await manager.on_sybil_detected(
            agent_id="sybil_agent",
            file_path="src/file.py",
            conflicting_agents=["agent_a"]
        )
        assert result1 is None
        assert manager.is_quarantined("sybil_agent") is False

        result2 = await manager.on_sybil_detected(
            agent_id="sybil_agent",
            file_path="src/file2.py",
            conflicting_agents=["agent_b"]
        )
        assert result2 is None
        assert manager.is_quarantined("sybil_agent") is False

        # Third flag - should trigger quarantine
        result3 = await manager.on_sybil_detected(
            agent_id="sybil_agent",
            file_path="src/file3.py",
            conflicting_agents=["agent_c"]
        )

        # AC-2: Should be quarantined after threshold
        assert result3 is not None
        assert result3.status == QuarantineStatus.ACTIVE
        assert result3.reason == QuarantineReason.SYBIL_DETECTED
        assert manager.is_quarantined("sybil_agent") is True

    @pytest.mark.asyncio
    async def test_configurable_sybil_threshold_ac2(self):
        """
        AC-2 TEST: Sybil threshold is configurable.
        """
        # Higher threshold
        manager = QuarantineManager(sybil_threshold=5, grace_period_seconds=0)

        for i in range(4):
            result = await manager.on_sybil_detected(
                agent_id="high_threshold_agent",
                file_path=f"src/file{i}.py",
                conflicting_agents=["other"]
            )
            assert result is None

        # 5th flag should trigger
        result = await manager.on_sybil_detected(
            agent_id="high_threshold_agent",
            file_path="src/file5.py",
            conflicting_agents=["other"]
        )
        assert result is not None
        assert manager.is_quarantined("high_threshold_agent") is True

    @pytest.mark.asyncio
    async def test_policy_violation_trigger(self):
        """Test policy violation auto-quarantine."""
        manager = QuarantineManager(grace_period_seconds=0)

        entry = await manager.on_policy_violation(
            agent_id="violator_agent",
            violation_type="unauthorized_access",
            details={"resource": "/admin/secrets"}
        )

        assert entry is not None
        assert entry.reason == QuarantineReason.POLICY_VIOLATION
        assert manager.is_quarantined("violator_agent") is True

    @pytest.mark.asyncio
    async def test_low_reputation_trigger(self):
        """Test low reputation auto-quarantine."""
        manager = QuarantineManager(grace_period_seconds=0)

        entry = await manager.on_low_reputation(
            agent_id="low_rep_agent",
            current_reputation=-50,
            threshold=0
        )

        assert entry is not None
        assert entry.reason == QuarantineReason.REPUTATION_TOO_LOW
        assert entry.metadata["reputation"] == -50


# ============================================================
# AC-3: Review Workflow Tests
# ============================================================

class TestAC3_ReviewWorkflow:
    """
    AC-3: Quarantined agents can be reviewed and released.
    """

    @pytest.fixture
    def manager_with_quarantined_agent(self):
        manager = QuarantineManager(grace_period_seconds=0, max_reviews=3)

        async def setup():
            await manager.quarantine(
                agent_id="review_agent",
                reason=QuarantineReason.SYBIL_DETECTED,
                immediate=True
            )
            return manager

        return asyncio.get_event_loop().run_until_complete(setup())

    @pytest.mark.asyncio
    async def test_request_review_ac3(self, manager_with_quarantined_agent):
        """
        AC-3 CRITICAL TEST: Quarantined agent can request review.
        """
        manager = manager_with_quarantined_agent

        result = await manager.request_review(
            agent_id="review_agent",
            notes="I promise to behave"
        )

        assert result is True

        entry = manager.get_quarantine_entry("review_agent")
        assert entry.status == QuarantineStatus.PENDING_REVIEW
        assert entry.review_requested_at is not None
        assert entry.review_notes == "I promise to behave"

    @pytest.mark.asyncio
    async def test_approve_release_ac3(self, manager_with_quarantined_agent):
        """
        AC-3 CRITICAL TEST: Authorized release approval.
        """
        manager = manager_with_quarantined_agent

        await manager.request_review("review_agent", "Please review")

        # Approve release
        result = await manager.approve_release(
            agent_id="review_agent",
            reviewer_id="admin_001",
            notes="Behavior improved"
        )

        assert result is True

        entry = manager.get_quarantine_entry("review_agent")
        assert entry.status == QuarantineStatus.RELEASED
        assert entry.released_by == "admin_001"
        assert entry.released_at is not None

        # Should no longer be quarantined
        assert manager.is_quarantined("review_agent") is False

    @pytest.mark.asyncio
    async def test_reject_release_ac3(self, manager_with_quarantined_agent):
        """
        AC-3 TEST: Reject release keeps agent quarantined.
        """
        manager = manager_with_quarantined_agent

        await manager.request_review("review_agent", "Please review")

        # Reject release
        result = await manager.reject_release(
            agent_id="review_agent",
            reviewer_id="admin_001",
            notes="Still suspicious"
        )

        assert result is True

        entry = manager.get_quarantine_entry("review_agent")
        assert entry.status == QuarantineStatus.ACTIVE  # Back to active
        assert manager.is_quarantined("review_agent") is True

    @pytest.mark.asyncio
    async def test_max_reviews_escalates_to_ban_ac3(self):
        """
        AC-3 CRITICAL TEST: Exceeded max reviews escalates to permanent ban.
        """
        manager = QuarantineManager(grace_period_seconds=0, max_reviews=2)

        await manager.quarantine("persistent_agent", QuarantineReason.SYBIL_DETECTED, immediate=True)

        # First review - request and reject
        await manager.request_review("persistent_agent", "Attempt 1")
        await manager.reject_release("persistent_agent", "admin", "No")

        # Second review - request and reject
        await manager.request_review("persistent_agent", "Attempt 2")
        await manager.reject_release("persistent_agent", "admin", "Still no")

        # Third attempt should fail (max reached)
        result = await manager.request_review("persistent_agent", "Attempt 3")
        assert result is False

        # Should still be quarantined (max reviews reached means permanent)
        assert manager.is_quarantined("persistent_agent") is True

    @pytest.mark.asyncio
    async def test_escalate_to_permanent_ban_ac3(self, manager_with_quarantined_agent):
        """
        AC-3 TEST: Explicit escalation to permanent ban.
        """
        manager = manager_with_quarantined_agent

        await manager.request_review("review_agent")

        # Explicitly escalate to ban
        result = await manager.reject_release(
            agent_id="review_agent",
            reviewer_id="security_admin",
            notes="Malicious activity confirmed",
            escalate_to_ban=True
        )

        assert result is True

        entry = manager.get_quarantine_entry("review_agent")
        assert entry.status == QuarantineStatus.PERMANENTLY_BANNED

        # Should still be quarantined (permanently)
        assert manager.is_quarantined("review_agent") is True

    @pytest.mark.asyncio
    async def test_cannot_release_permanently_banned_ac3(self):
        """
        AC-3 TEST: Permanently banned agents cannot be released.
        """
        manager = QuarantineManager(grace_period_seconds=0)

        await manager.quarantine("banned_agent", QuarantineReason.SYBIL_DETECTED, immediate=True)
        await manager.request_review("banned_agent")
        await manager.reject_release("banned_agent", "admin", escalate_to_ban=True)

        # Try to release
        result = await manager.approve_release("banned_agent", "super_admin")
        assert result is False  # Cannot release permanently banned

        # Try to request review
        result = await manager.request_review("banned_agent")
        assert result is False  # Cannot request review when banned


# ============================================================
# AC-4: Audit Logging Tests
# ============================================================

class TestAC4_AuditLogging:
    """
    AC-4: All quarantine actions are logged to the immutable audit log.
    """

    @pytest.fixture
    def manager_with_audit(self):
        actions: List[QuarantineAction] = []

        def capture_audit(action: QuarantineAction):
            actions.append(action)

        manager = QuarantineManager(
            grace_period_seconds=0,
            audit_callback=capture_audit
        )
        manager._captured_actions = actions
        return manager

    @pytest.mark.asyncio
    async def test_quarantine_logged_ac4(self, manager_with_audit):
        """
        AC-4 CRITICAL TEST: Quarantine entry is logged.
        """
        manager = manager_with_audit

        await manager.quarantine(
            agent_id="logged_agent",
            reason=QuarantineReason.SYBIL_DETECTED,
            performed_by="system",
            immediate=True
        )

        # Check audit callback was called
        assert len(manager._captured_actions) >= 1

        action = manager._captured_actions[-1]
        assert action.agent_id == "logged_agent"
        assert action.action_type == "quarantine"
        assert action.performed_by == "system"

    @pytest.mark.asyncio
    async def test_review_request_logged_ac4(self, manager_with_audit):
        """
        AC-4 TEST: Review request is logged.
        """
        manager = manager_with_audit

        await manager.quarantine("log_review_agent", QuarantineReason.MANUAL_QUARANTINE, immediate=True)
        await manager.request_review("log_review_agent", "Please review")

        # Find review request action
        review_actions = [a for a in manager._captured_actions if a.action_type == "review_request"]
        assert len(review_actions) >= 1

        action = review_actions[-1]
        assert action.agent_id == "log_review_agent"
        assert action.action_type == "review_request"

    @pytest.mark.asyncio
    async def test_release_approval_logged_ac4(self, manager_with_audit):
        """
        AC-4 TEST: Release approval is logged.
        """
        manager = manager_with_audit

        await manager.quarantine("release_log_agent", QuarantineReason.MANUAL_QUARANTINE, immediate=True)
        await manager.request_review("release_log_agent")
        await manager.approve_release("release_log_agent", "admin_approver", "Released")

        # Find release action
        release_actions = [a for a in manager._captured_actions if a.action_type == "release_approved"]
        assert len(release_actions) >= 1

        action = release_actions[-1]
        assert action.agent_id == "release_log_agent"
        assert action.performed_by == "admin_approver"

    @pytest.mark.asyncio
    async def test_release_rejection_logged_ac4(self, manager_with_audit):
        """
        AC-4 TEST: Release rejection is logged.
        """
        manager = manager_with_audit

        await manager.quarantine("reject_log_agent", QuarantineReason.MANUAL_QUARANTINE, immediate=True)
        await manager.request_review("reject_log_agent")
        await manager.reject_release("reject_log_agent", "admin_rejecter", "Denied")

        # Find rejection action
        reject_actions = [a for a in manager._captured_actions if a.action_type == "release_rejected"]
        assert len(reject_actions) >= 1

        action = reject_actions[-1]
        assert action.agent_id == "reject_log_agent"
        assert action.performed_by == "admin_rejecter"

    @pytest.mark.asyncio
    async def test_action_history_queryable_ac4(self, manager_with_audit):
        """
        AC-4 TEST: Action history can be queried.
        """
        manager = manager_with_audit

        await manager.quarantine("history_agent", QuarantineReason.SYBIL_DETECTED, immediate=True)
        await manager.request_review("history_agent")
        await manager.approve_release("history_agent", "admin")

        # Query history for this agent
        history = manager.get_action_history(agent_id="history_agent")

        assert len(history) >= 3  # quarantine, review_request, release_approved
        action_types = [a.action_type for a in history]
        assert "quarantine" in action_types
        assert "review_request" in action_types
        assert "release_approved" in action_types


# ============================================================
# Integration Tests
# ============================================================

class TestQuarantineIntegration:
    """Integration tests for full quarantine workflow."""

    @pytest.mark.asyncio
    async def test_full_quarantine_lifecycle(self):
        """Test complete quarantine lifecycle."""
        audit_log: List[QuarantineAction] = []
        manager = QuarantineManager(
            grace_period_seconds=0,
            sybil_threshold=2,
            max_reviews=2,
            audit_callback=lambda a: audit_log.append(a)
        )

        # Step 1: Sybil detection (first flag)
        await manager.on_sybil_detected("lifecycle_agent", "file1.py", ["other1"])
        assert manager.is_quarantined("lifecycle_agent") is False

        # Step 2: Second sybil flag - triggers quarantine
        await manager.on_sybil_detected("lifecycle_agent", "file2.py", ["other2"])
        assert manager.is_quarantined("lifecycle_agent") is True

        # Step 3: Operation blocked
        with pytest.raises(QuarantineError):
            manager.check_operation("lifecycle_agent", "edit")

        # Step 4: Request review
        await manager.request_review("lifecycle_agent", "I was hacked")
        entry = manager.get_quarantine_entry("lifecycle_agent")
        assert entry.status == QuarantineStatus.PENDING_REVIEW

        # Step 5: Release approved
        await manager.approve_release("lifecycle_agent", "security_team", "Identity verified")

        # Step 6: Agent can operate again
        manager.check_operation("lifecycle_agent", "edit")  # Should not raise

        # Verify audit trail - expect 3 actions: quarantine, review_request, release_approved
        assert len(audit_log) >= 3
        action_types = [a.action_type for a in audit_log]
        assert "quarantine" in action_types
        assert "review_request" in action_types
        assert "release_approved" in action_types

    @pytest.mark.asyncio
    async def test_permanent_ban_flow(self):
        """Test flow leading to permanent ban."""
        manager = QuarantineManager(
            grace_period_seconds=0,
            max_reviews=1
        )

        await manager.quarantine("ban_flow_agent", QuarantineReason.SYBIL_DETECTED, immediate=True)

        # First review rejected
        await manager.request_review("ban_flow_agent")
        await manager.reject_release("ban_flow_agent", "admin", "Suspicious")

        # Second review attempt fails (max reached)
        result = await manager.request_review("ban_flow_agent")
        assert result is False

        # Agent is effectively permanently quarantined
        assert manager.is_quarantined("ban_flow_agent") is True


# ============================================================
# Edge Cases
# ============================================================

class TestEdgeCases:
    """Edge case tests."""

    @pytest.mark.asyncio
    async def test_review_non_quarantined_agent(self):
        """Test review request for non-quarantined agent."""
        manager = QuarantineManager()
        result = await manager.request_review("non_existent_agent")
        assert result is False

    @pytest.mark.asyncio
    async def test_release_non_quarantined_agent(self):
        """Test release for non-quarantined agent."""
        manager = QuarantineManager()
        result = await manager.approve_release("non_existent_agent", "admin")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_pending_reviews(self):
        """Test getting agents pending review."""
        manager = QuarantineManager(grace_period_seconds=0)

        await manager.quarantine("pending1", QuarantineReason.MANUAL_QUARANTINE, immediate=True)
        await manager.quarantine("pending2", QuarantineReason.MANUAL_QUARANTINE, immediate=True)

        await manager.request_review("pending1")

        pending = manager.get_pending_reviews()
        assert len(pending) == 1
        assert pending[0].agent_id == "pending1"

    @pytest.mark.asyncio
    async def test_stats(self):
        """Test quarantine statistics."""
        manager = QuarantineManager(grace_period_seconds=0, sybil_threshold=3)

        await manager.quarantine("stat_agent1", QuarantineReason.SYBIL_DETECTED, immediate=True)
        await manager.quarantine("stat_agent2", QuarantineReason.POLICY_VIOLATION, immediate=True)
        await manager.request_review("stat_agent1")

        stats = manager.get_stats()

        assert stats["total_quarantined"] == 2
        assert stats["sybil_threshold"] == 3
        assert stats["by_status"]["active"] == 1
        assert stats["by_status"]["pending_review"] == 1


# ============================================================
# Factory Function Tests
# ============================================================

class TestFactoryFunction:
    """Test create_quarantine_manager factory."""

    def test_create_quarantine_manager_default(self):
        """Test creating manager with defaults."""
        manager = create_quarantine_manager()
        assert manager is not None
        assert manager._sybil_threshold == QuarantineManager.DEFAULT_SYBIL_THRESHOLD
        assert manager._max_reviews == QuarantineManager.DEFAULT_MAX_REVIEWS

    def test_create_quarantine_manager_custom(self):
        """Test creating manager with custom settings."""
        callback = MagicMock()
        manager = create_quarantine_manager(
            grace_period_seconds=120,
            sybil_threshold=5,
            max_reviews=2,
            audit_callback=callback
        )
        assert manager._sybil_threshold == 5
        assert manager._max_reviews == 2
        assert manager._audit_callback == callback
