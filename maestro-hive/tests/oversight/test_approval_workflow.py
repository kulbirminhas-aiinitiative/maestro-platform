#!/usr/bin/env python3
"""
Test suite for approval_workflow.py

Tests the Human-in-the-Loop Approval Workflow Engine.
Related EPIC: MD-3023 - Human-in-the-Loop Approval System
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
import time

from maestro_hive.oversight.approval_workflow import (
    ApprovalType,
    ApprovalStatus,
    Priority,
    ApprovalDecision,
    ApprovalRequest,
    ApprovalResult,
    SuspendedWorkflow,
    ApprovalWorkflow,
    get_approval_workflow,
    create_approval_request,
)


class TestApprovalType:
    """Tests for ApprovalType enum."""

    def test_approval_types_exist(self):
        """Verify all approval types are defined."""
        assert ApprovalType.DECISION.value == "decision"
        assert ApprovalType.OVERRIDE.value == "override"
        assert ApprovalType.CRITICAL.value == "critical"
        assert ApprovalType.COMPLIANCE.value == "compliance"

    def test_approval_type_count(self):
        """Verify expected number of approval types."""
        assert len(ApprovalType) == 4


class TestApprovalStatus:
    """Tests for ApprovalStatus enum."""

    def test_approval_statuses_exist(self):
        """Verify all approval statuses are defined."""
        assert ApprovalStatus.PENDING.value == "pending"
        assert ApprovalStatus.APPROVED.value == "approved"
        assert ApprovalStatus.REJECTED.value == "rejected"
        assert ApprovalStatus.ESCALATED.value == "escalated"
        assert ApprovalStatus.CANCELLED.value == "cancelled"
        assert ApprovalStatus.EXPIRED.value == "expired"

    def test_approval_status_count(self):
        """Verify expected number of statuses."""
        assert len(ApprovalStatus) == 6


class TestPriority:
    """Tests for Priority enum."""

    def test_priority_values(self):
        """Verify priority ordering."""
        assert Priority.LOW.value == 1
        assert Priority.NORMAL.value == 2
        assert Priority.HIGH.value == 3
        assert Priority.CRITICAL.value == 4

    def test_priority_ordering(self):
        """Verify priorities can be compared."""
        assert Priority.LOW.value < Priority.NORMAL.value
        assert Priority.NORMAL.value < Priority.HIGH.value
        assert Priority.HIGH.value < Priority.CRITICAL.value


class TestApprovalDecision:
    """Tests for ApprovalDecision enum."""

    def test_decisions_exist(self):
        """Verify all decision types are defined."""
        assert ApprovalDecision.APPROVED.value == "approved"
        assert ApprovalDecision.REJECTED.value == "rejected"


class TestApprovalRequest:
    """Tests for ApprovalRequest dataclass."""

    @pytest.fixture
    def sample_request(self):
        """Create a sample approval request."""
        return ApprovalRequest(
            id="apr_test123",
            workflow_id="wf_abc",
            request_type=ApprovalType.DECISION,
            context={"action": "deploy", "environment": "prod"},
            requester="test_user",
            assigned_to=["approver1", "approver2"],
            priority=Priority.HIGH,
            timeout_seconds=1800,
        )

    def test_request_creation(self, sample_request):
        """Test creating an approval request."""
        assert sample_request.id == "apr_test123"
        assert sample_request.workflow_id == "wf_abc"
        assert sample_request.request_type == ApprovalType.DECISION
        assert sample_request.status == ApprovalStatus.PENDING
        assert sample_request.priority == Priority.HIGH
        assert sample_request.timeout_seconds == 1800
        assert len(sample_request.assigned_to) == 2

    def test_request_defaults(self):
        """Test default values for approval request."""
        request = ApprovalRequest(
            id="apr_test",
            workflow_id="wf_test",
            request_type=ApprovalType.DECISION,
            context={},
            requester="system",
            assigned_to=["approver"],
        )
        assert request.priority == Priority.NORMAL
        assert request.timeout_seconds == 3600
        assert request.status == ApprovalStatus.PENDING
        assert request.decision is None
        assert request.decided_by is None
        assert request.escalation_level == 0

    def test_to_dict(self, sample_request):
        """Test serialization to dictionary."""
        data = sample_request.to_dict()
        assert data["id"] == "apr_test123"
        assert data["workflow_id"] == "wf_abc"
        assert data["request_type"] == "decision"
        assert data["priority"] == 3  # HIGH
        assert data["status"] == "pending"
        assert data["context"]["action"] == "deploy"

    def test_from_dict(self, sample_request):
        """Test deserialization from dictionary."""
        data = sample_request.to_dict()
        restored = ApprovalRequest.from_dict(data)
        assert restored.id == sample_request.id
        assert restored.workflow_id == sample_request.workflow_id
        assert restored.request_type == sample_request.request_type
        assert restored.priority == sample_request.priority

    def test_is_overdue_not_expired(self, sample_request):
        """Test is_overdue returns False for fresh request."""
        assert sample_request.is_overdue() is False

    def test_is_overdue_expired(self):
        """Test is_overdue returns True for expired request."""
        request = ApprovalRequest(
            id="apr_old",
            workflow_id="wf_old",
            request_type=ApprovalType.DECISION,
            context={},
            requester="system",
            assigned_to=["approver"],
            timeout_seconds=1,
            created_at=datetime.utcnow() - timedelta(seconds=10),
        )
        assert request.is_overdue() is True

    def test_is_overdue_non_pending(self, sample_request):
        """Test is_overdue returns False for non-pending requests."""
        sample_request.status = ApprovalStatus.APPROVED
        assert sample_request.is_overdue() is False

    def test_time_remaining_seconds(self, sample_request):
        """Test time remaining calculation."""
        remaining = sample_request.time_remaining_seconds()
        assert remaining > 0
        assert remaining <= sample_request.timeout_seconds

    def test_time_remaining_expired(self):
        """Test time remaining for expired request."""
        request = ApprovalRequest(
            id="apr_old",
            workflow_id="wf_old",
            request_type=ApprovalType.DECISION,
            context={},
            requester="system",
            assigned_to=["approver"],
            timeout_seconds=1,
            created_at=datetime.utcnow() - timedelta(seconds=10),
        )
        assert request.time_remaining_seconds() == 0


class TestApprovalResult:
    """Tests for ApprovalResult dataclass."""

    def test_result_creation(self):
        """Test creating an approval result."""
        result = ApprovalResult(
            request_id="apr_test",
            success=True,
            decision=ApprovalDecision.APPROVED,
            workflow_resumed=True,
            message="Approved successfully",
        )
        assert result.request_id == "apr_test"
        assert result.success is True
        assert result.decision == ApprovalDecision.APPROVED
        assert result.workflow_resumed is True
        assert result.timestamp is not None


class TestSuspendedWorkflow:
    """Tests for SuspendedWorkflow dataclass."""

    def test_suspended_workflow_creation(self):
        """Test creating a suspended workflow."""
        suspended = SuspendedWorkflow(
            workflow_id="wf_test",
            request_id="apr_test",
            suspended_at=datetime.utcnow(),
            state={"step": 3, "data": "test"},
        )
        assert suspended.workflow_id == "wf_test"
        assert suspended.request_id == "apr_test"
        assert suspended.state["step"] == 3
        assert suspended.resume_callback is None


class TestApprovalWorkflow:
    """Tests for ApprovalWorkflow class."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        ApprovalWorkflow._instance = None
        yield
        ApprovalWorkflow._instance = None

    @pytest.fixture
    def workflow(self):
        """Create a fresh workflow instance."""
        return ApprovalWorkflow()

    def test_singleton_pattern(self):
        """Test that ApprovalWorkflow follows singleton pattern."""
        wf1 = ApprovalWorkflow()
        wf2 = ApprovalWorkflow()
        assert wf1 is wf2

    def test_create_request(self, workflow):
        """Test creating an approval request."""
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={"action": "test"},
            assigned_to=["approver1"],
            requester="test_user",
        )
        assert request.id.startswith("apr_")
        assert request.workflow_id.startswith("wf_")
        assert request.status == ApprovalStatus.PENDING
        assert "approver1" in request.assigned_to

    def test_create_request_with_workflow_id(self, workflow):
        """Test creating request with specific workflow ID."""
        request = workflow.create_request(
            request_type=ApprovalType.CRITICAL,
            context={"critical": True},
            assigned_to=["approver1"],
            workflow_id="wf_custom_123",
        )
        assert request.workflow_id == "wf_custom_123"

    def test_create_request_with_priority(self, workflow):
        """Test creating request with specific priority."""
        request = workflow.create_request(
            request_type=ApprovalType.CRITICAL,
            context={},
            assigned_to=["approver1"],
            priority=Priority.CRITICAL,
        )
        assert request.priority == Priority.CRITICAL

    def test_get_request(self, workflow):
        """Test retrieving a request by ID."""
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        retrieved = workflow.get_request(request.id)
        assert retrieved is not None
        assert retrieved.id == request.id

    def test_get_request_not_found(self, workflow):
        """Test retrieving non-existent request."""
        result = workflow.get_request("apr_nonexistent")
        assert result is None

    def test_process_approval_approved(self, workflow):
        """Test approving a request."""
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        result = workflow.process_approval(
            request_id=request.id,
            decision=ApprovalDecision.APPROVED,
            approver_id="approver1",
            comments="Looks good",
        )
        assert result.success is True
        assert result.decision == ApprovalDecision.APPROVED
        assert request.status == ApprovalStatus.APPROVED
        assert request.decided_by == "approver1"
        assert request.comments == "Looks good"

    def test_process_approval_rejected(self, workflow):
        """Test rejecting a request."""
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        result = workflow.process_approval(
            request_id=request.id,
            decision=ApprovalDecision.REJECTED,
            approver_id="approver1",
            comments="Not approved",
        )
        assert result.success is True
        assert result.decision == ApprovalDecision.REJECTED
        assert request.status == ApprovalStatus.REJECTED

    def test_process_approval_not_found(self, workflow):
        """Test approval for non-existent request."""
        result = workflow.process_approval(
            request_id="apr_nonexistent",
            decision=ApprovalDecision.APPROVED,
            approver_id="approver1",
        )
        assert result.success is False
        assert "not found" in result.message.lower()

    def test_process_approval_not_pending(self, workflow):
        """Test approval for already-processed request."""
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
        # Try to approve again
        result = workflow.process_approval(
            request_id=request.id,
            decision=ApprovalDecision.REJECTED,
            approver_id="approver1",
        )
        assert result.success is False
        assert "not pending" in result.message.lower()

    def test_process_approval_unauthorized(self, workflow):
        """Test approval by unauthorized approver."""
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        result = workflow.process_approval(
            request_id=request.id,
            decision=ApprovalDecision.APPROVED,
            approver_id="unauthorized_user",
        )
        assert result.success is False
        assert "not authorized" in result.message.lower()

    def test_suspend_workflow(self, workflow):
        """Test suspending a workflow."""
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        result = workflow.suspend_workflow(
            workflow_id=request.workflow_id,
            request_id=request.id,
            state={"step": 5, "data": "preserved"},
        )
        assert result is True

    def test_suspend_workflow_invalid_request(self, workflow):
        """Test suspending with invalid request ID."""
        result = workflow.suspend_workflow(
            workflow_id="wf_test",
            request_id="apr_nonexistent",
            state={},
        )
        assert result is False

    def test_resume_workflow(self, workflow):
        """Test resuming a suspended workflow."""
        callback_called = {"value": False}

        def resume_callback(approval, state):
            callback_called["value"] = True

        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        workflow.suspend_workflow(
            workflow_id=request.workflow_id,
            request_id=request.id,
            state={"step": 5},
            resume_callback=resume_callback,
        )
        result = workflow.process_approval(
            request_id=request.id,
            decision=ApprovalDecision.APPROVED,
            approver_id="approver1",
        )
        assert result.workflow_resumed is True
        assert callback_called["value"] is True

    def test_resume_workflow_not_suspended(self, workflow):
        """Test resuming non-suspended workflow."""
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        result = workflow.resume_workflow(request.workflow_id, request)
        assert result is False

    def test_cancel_request(self, workflow):
        """Test cancelling a request."""
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        result = workflow.cancel_request(request.id, "No longer needed")
        assert result is True
        assert request.status == ApprovalStatus.CANCELLED
        assert request.comments == "No longer needed"

    def test_cancel_request_not_found(self, workflow):
        """Test cancelling non-existent request."""
        result = workflow.cancel_request("apr_nonexistent")
        assert result is False

    def test_cancel_request_not_pending(self, workflow):
        """Test cancelling already-processed request."""
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
        result = workflow.cancel_request(request.id)
        assert result is False

    def test_get_pending_requests(self, workflow):
        """Test getting pending requests."""
        workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        workflow.create_request(
            request_type=ApprovalType.CRITICAL,
            context={},
            assigned_to=["approver1", "approver2"],
        )
        pending = workflow.get_pending_requests()
        assert len(pending) == 2

    def test_get_pending_requests_by_approver(self, workflow):
        """Test getting pending requests for specific approver."""
        workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        workflow.create_request(
            request_type=ApprovalType.CRITICAL,
            context={},
            assigned_to=["approver2"],
        )
        pending = workflow.get_pending_requests(approver_id="approver1")
        assert len(pending) == 1

    def test_get_workflow_requests(self, workflow):
        """Test getting all requests for a workflow."""
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        requests = workflow.get_workflow_requests(request.workflow_id)
        assert len(requests) == 1
        assert requests[0].id == request.id

    def test_get_stats(self, workflow):
        """Test getting workflow statistics."""
        workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        request2 = workflow.create_request(
            request_type=ApprovalType.CRITICAL,
            context={},
            assigned_to=["approver1"],
        )
        workflow.process_approval(
            request_id=request2.id,
            decision=ApprovalDecision.APPROVED,
            approver_id="approver1",
        )
        stats = workflow.get_stats()
        assert stats["total_requests"] == 2
        assert stats["pending"] == 1
        assert stats["approved"] == 1
        assert stats["rejected"] == 0

    def test_get_audit_log(self, workflow):
        """Test getting audit log entries."""
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
        log = workflow.get_audit_log()
        assert len(log) >= 2  # At least create and approve events

    def test_get_audit_log_by_request(self, workflow):
        """Test getting audit log for specific request."""
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        workflow.create_request(
            request_type=ApprovalType.CRITICAL,
            context={},
            assigned_to=["approver2"],
        )
        log = workflow.get_audit_log(request_id=request.id)
        assert len(log) >= 1


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        ApprovalWorkflow._instance = None
        import maestro_hive.oversight.approval_workflow as module
        module._workflow_instance = None
        yield
        ApprovalWorkflow._instance = None
        module._workflow_instance = None

    def test_get_approval_workflow(self):
        """Test get_approval_workflow returns singleton."""
        wf1 = get_approval_workflow()
        wf2 = get_approval_workflow()
        assert wf1 is wf2

    def test_create_approval_request(self):
        """Test create_approval_request convenience function."""
        request = create_approval_request(
            request_type=ApprovalType.DECISION,
            context={"test": True},
            assigned_to=["approver1"],
        )
        assert request.id.startswith("apr_")
        assert request.status == ApprovalStatus.PENDING
