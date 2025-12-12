#!/usr/bin/env python3
"""
Test suite for escalation_handler.py

Tests the Escalation Handler for approval timeout scenarios.
Related EPIC: MD-3023 - Human-in-the-Loop Approval System
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from maestro_hive.oversight.approval_workflow import (
    ApprovalType,
    ApprovalStatus,
    ApprovalDecision,
    Priority,
    ApprovalWorkflow,
)
from maestro_hive.oversight.approval_queue import ApprovalQueue
from maestro_hive.oversight.escalation_handler import (
    EscalationReason,
    EscalationLevel,
    EscalationPath,
    EscalationResult,
    EscalationEvent,
    EscalationHandler,
    get_escalation_handler,
)


class TestEscalationReason:
    """Tests for EscalationReason enum."""

    def test_escalation_reasons_exist(self):
        """Verify all escalation reasons are defined."""
        assert EscalationReason.TIMEOUT.value == "timeout"
        assert EscalationReason.MANUAL.value == "manual"
        assert EscalationReason.PRIORITY_UPGRADE.value == "priority_upgrade"
        assert EscalationReason.APPROVER_UNAVAILABLE.value == "approver_unavailable"
        assert EscalationReason.POLICY.value == "policy"

    def test_escalation_reason_count(self):
        """Verify expected number of reasons."""
        assert len(EscalationReason) == 5


class TestEscalationLevel:
    """Tests for EscalationLevel dataclass."""

    def test_level_creation(self):
        """Test creating an escalation level."""
        level = EscalationLevel(
            level=1,
            role="senior_engineer",
            approvers=["eng1", "eng2"],
            timeout_seconds=1800,
            priority_override=Priority.HIGH,
            notification_channels=["email", "slack"],
        )
        assert level.level == 1
        assert level.role == "senior_engineer"
        assert len(level.approvers) == 2
        assert level.timeout_seconds == 1800
        assert level.priority_override == Priority.HIGH

    def test_level_defaults(self):
        """Test default values for escalation level."""
        level = EscalationLevel(
            level=1,
            role="engineer",
            approvers=[],
        )
        assert level.timeout_seconds == 3600
        assert level.priority_override is None
        assert level.notification_channels == []

    def test_level_to_dict(self):
        """Test serialization to dictionary."""
        level = EscalationLevel(
            level=2,
            role="manager",
            approvers=["mgr1"],
            priority_override=Priority.CRITICAL,
        )
        data = level.to_dict()
        assert data["level"] == 2
        assert data["role"] == "manager"
        assert data["priority_override"] == 4  # CRITICAL value


class TestEscalationPath:
    """Tests for EscalationPath dataclass."""

    def test_path_creation(self):
        """Test creating an escalation path."""
        path = EscalationPath(
            request_type=ApprovalType.CRITICAL,
            levels=[
                EscalationLevel(level=1, role="engineer", approvers=[]),
                EscalationLevel(level=2, role="manager", approvers=[]),
            ],
            final_action="block",
        )
        assert path.request_type == ApprovalType.CRITICAL
        assert len(path.levels) == 2
        assert path.final_action == "block"

    def test_path_default_final_action(self):
        """Test default final action."""
        path = EscalationPath(
            request_type=ApprovalType.DECISION,
            levels=[],
        )
        assert path.final_action == "auto_reject"

    def test_path_to_dict(self):
        """Test serialization to dictionary."""
        path = EscalationPath(
            request_type=ApprovalType.COMPLIANCE,
            levels=[
                EscalationLevel(level=1, role="officer", approvers=[]),
            ],
            final_action="block",
        )
        data = path.to_dict()
        assert data["request_type"] == "compliance"
        assert len(data["levels"]) == 1
        assert data["final_action"] == "block"


class TestEscalationResult:
    """Tests for EscalationResult dataclass."""

    def test_result_creation(self):
        """Test creating an escalation result."""
        result = EscalationResult(
            request_id="apr_test",
            success=True,
            new_level=2,
            new_approvers=["mgr1", "mgr2"],
            reason=EscalationReason.TIMEOUT,
            message="Escalated to level 2",
        )
        assert result.request_id == "apr_test"
        assert result.success is True
        assert result.new_level == 2
        assert len(result.new_approvers) == 2
        assert result.reason == EscalationReason.TIMEOUT
        assert result.timestamp is not None


class TestEscalationEvent:
    """Tests for EscalationEvent dataclass."""

    def test_event_creation(self):
        """Test creating an escalation event."""
        event = EscalationEvent(
            request_id="apr_test",
            from_level=1,
            to_level=2,
            reason=EscalationReason.MANUAL,
            triggered_by="admin_user",
        )
        assert event.request_id == "apr_test"
        assert event.from_level == 1
        assert event.to_level == 2
        assert event.reason == EscalationReason.MANUAL
        assert event.triggered_by == "admin_user"
        assert event.timestamp is not None


class TestEscalationHandler:
    """Tests for EscalationHandler class."""

    @pytest.fixture(autouse=True)
    def reset_singletons(self):
        """Reset singletons before each test."""
        ApprovalWorkflow._instance = None
        ApprovalQueue._instance = None
        EscalationHandler._instance = None
        import maestro_hive.oversight.approval_workflow as wf_module
        import maestro_hive.oversight.approval_queue as q_module
        import maestro_hive.oversight.escalation_handler as e_module
        wf_module._workflow_instance = None
        q_module._queue_instance = None
        e_module._handler_instance = None
        yield
        ApprovalWorkflow._instance = None
        ApprovalQueue._instance = None
        EscalationHandler._instance = None
        wf_module._workflow_instance = None
        q_module._queue_instance = None
        e_module._handler_instance = None

    @pytest.fixture
    def handler(self):
        """Create a fresh handler instance."""
        return EscalationHandler()

    @pytest.fixture
    def workflow(self):
        """Create a fresh workflow instance."""
        return ApprovalWorkflow()

    @pytest.fixture
    def queue(self):
        """Create a fresh queue instance."""
        return ApprovalQueue()

    def test_singleton_pattern(self):
        """Test that EscalationHandler follows singleton pattern."""
        h1 = EscalationHandler()
        h2 = EscalationHandler()
        assert h1 is h2

    def test_default_paths_configured(self, handler):
        """Test that default escalation paths are configured."""
        critical_path = handler.get_escalation_path(ApprovalType.CRITICAL)
        assert critical_path is not None
        assert len(critical_path.levels) == 3
        assert critical_path.final_action == "block"

        compliance_path = handler.get_escalation_path(ApprovalType.COMPLIANCE)
        assert compliance_path is not None
        assert len(compliance_path.levels) == 2

        decision_path = handler.get_escalation_path(ApprovalType.DECISION)
        assert decision_path is not None
        assert decision_path.final_action == "auto_reject"

    def test_configure_escalation_path(self, handler):
        """Test configuring a custom escalation path."""
        result = handler.configure_escalation_path(
            request_type=ApprovalType.OVERRIDE,
            levels=[
                {"role": "supervisor", "timeout": 1800},
                {"role": "director", "timeout": 3600, "priority": 4},
            ],
            final_action="auto_approve",
        )
        assert result is True
        path = handler.get_escalation_path(ApprovalType.OVERRIDE)
        assert path is not None
        assert len(path.levels) == 2
        assert path.final_action == "auto_approve"

    def test_get_escalation_path_not_found(self, handler):
        """Test getting non-existent escalation path."""
        # Override is not configured by default
        path = handler.get_escalation_path(ApprovalType.OVERRIDE)
        assert path is None

    def test_escalate_success(self, handler, workflow, queue):
        """Test successful escalation."""
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        queue.enqueue(request)
        result = handler.escalate(
            request_id=request.id,
            reason=EscalationReason.MANUAL,
            triggered_by="admin",
        )
        assert result.success is True
        assert result.new_level == 1
        assert "team_lead" in result.message.lower()

    def test_escalate_multiple_levels(self, handler, workflow, queue):
        """Test escalating through multiple levels."""
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        queue.enqueue(request)
        # First escalation
        result1 = handler.escalate(request.id)
        assert result1.success is True
        assert result1.new_level == 1
        # Second escalation
        result2 = handler.escalate(request.id)
        assert result2.success is True
        assert result2.new_level == 2

    def test_escalate_request_not_found(self, handler):
        """Test escalating non-existent request."""
        result = handler.escalate(
            request_id="apr_nonexistent",
            reason=EscalationReason.MANUAL,
        )
        assert result.success is False
        assert "not found" in result.message.lower()

    def test_escalate_not_pending(self, handler, workflow, queue):
        """Test escalating non-pending request."""
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        workflow.process_approval(
            request_id=request.id,
            decision=ApprovalDecision.APPROVED,
            approver_id="approver1",
        )
        result = handler.escalate(request.id)
        assert result.success is False
        assert "not pending" in result.message.lower()

    def test_escalate_no_path(self, handler, workflow, queue):
        """Test escalating request with no configured path."""
        request = workflow.create_request(
            request_type=ApprovalType.OVERRIDE,
            context={},
            assigned_to=["approver1"],
        )
        queue.enqueue(request)
        result = handler.escalate(request.id)
        assert result.success is False
        assert "no escalation path" in result.message.lower()

    def test_escalate_priority_override(self, handler, workflow, queue):
        """Test that escalation can override priority."""
        request = workflow.create_request(
            request_type=ApprovalType.CRITICAL,
            context={},
            assigned_to=["approver1"],
            priority=Priority.NORMAL,
        )
        queue.enqueue(request)
        # Escalate to level 2 which has priority override
        handler.escalate(request.id)
        handler.escalate(request.id)
        assert request.priority == Priority.CRITICAL

    def test_escalate_final_action_auto_reject(self, handler, workflow, queue):
        """Test final action: auto_reject."""
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        queue.enqueue(request)
        # Exhaust all levels
        handler.escalate(request.id)  # Level 1
        handler.escalate(request.id)  # Level 2
        result = handler.escalate(request.id)  # Exhausted
        assert result.success is True
        assert "auto-rejected" in result.message.lower()
        assert request.status == ApprovalStatus.REJECTED

    def test_escalate_final_action_block(self, handler, workflow, queue):
        """Test final action: block."""
        request = workflow.create_request(
            request_type=ApprovalType.CRITICAL,
            context={},
            assigned_to=["approver1"],
        )
        queue.enqueue(request)
        # Exhaust all 3 levels
        handler.escalate(request.id)  # Level 1
        handler.escalate(request.id)  # Level 2
        handler.escalate(request.id)  # Level 3
        result = handler.escalate(request.id)  # Exhausted
        assert result.success is True
        assert "blocked" in result.message.lower()
        assert request.status == ApprovalStatus.EXPIRED

    def test_register_notification_handler(self, handler):
        """Test registering a notification handler."""
        mock_handler = MagicMock()
        handler.register_notification_handler("slack", mock_handler)
        # Verify it's registered
        assert "slack" in handler._notification_handlers

    def test_notify_escalation(self, handler, workflow):
        """Test sending escalation notification."""
        mock_handler = MagicMock()
        handler.register_notification_handler("email", mock_handler)
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        result = handler.notify_escalation(
            request_id=request.id,
            target_approver="approver1",
            channel="email",
        )
        assert result is True
        mock_handler.assert_called_once()

    def test_notify_escalation_no_handler(self, handler, workflow):
        """Test notification with no handler registered."""
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        result = handler.notify_escalation(
            request_id=request.id,
            target_approver="approver1",
            channel="pager",  # Not registered
        )
        assert result is False

    def test_check_timeouts(self, handler, workflow, queue):
        """Test automatic timeout checking."""
        # Create request with short timeout
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
            timeout_seconds=1,
        )
        # Set created_at to past
        request.created_at = datetime.utcnow() - timedelta(seconds=10)
        queue.enqueue(request)
        escalated = handler.check_timeouts()
        assert request.id in escalated

    def test_get_escalation_history(self, handler, workflow, queue):
        """Test getting escalation history."""
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        queue.enqueue(request)
        handler.escalate(request.id, reason=EscalationReason.MANUAL)
        handler.escalate(request.id, reason=EscalationReason.TIMEOUT)
        history = handler.get_escalation_history()
        assert len(history) == 2

    def test_get_escalation_history_by_request(self, handler, workflow, queue):
        """Test getting escalation history for specific request."""
        r1 = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        r2 = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        queue.enqueue(r1)
        queue.enqueue(r2)
        handler.escalate(r1.id)
        handler.escalate(r2.id)
        history = handler.get_escalation_history(request_id=r1.id)
        assert len(history) == 1
        assert history[0].request_id == r1.id

    def test_get_stats(self, handler, workflow, queue):
        """Test getting escalation statistics."""
        r1 = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        r2 = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        queue.enqueue(r1)
        queue.enqueue(r2)
        handler.escalate(r1.id, reason=EscalationReason.MANUAL)
        handler.escalate(r1.id, reason=EscalationReason.TIMEOUT)
        handler.escalate(r2.id, reason=EscalationReason.MANUAL)
        stats = handler.get_stats()
        assert stats["total_escalations"] == 3
        assert stats["by_reason"]["manual"] == 2
        assert stats["by_reason"]["timeout"] == 1
        assert stats["configured_paths"] >= 3


class TestGetEscalationHandler:
    """Tests for get_escalation_handler convenience function."""

    @pytest.fixture(autouse=True)
    def reset_singletons(self):
        """Reset singletons before each test."""
        EscalationHandler._instance = None
        import maestro_hive.oversight.escalation_handler as e_module
        e_module._handler_instance = None
        yield
        EscalationHandler._instance = None
        e_module._handler_instance = None

    def test_get_escalation_handler_singleton(self):
        """Test get_escalation_handler returns singleton."""
        h1 = get_escalation_handler()
        h2 = get_escalation_handler()
        assert h1 is h2
