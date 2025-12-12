#!/usr/bin/env python3
"""
Test suite for approval_queue.py

Tests the Approval Queue Manager for pending human-in-the-loop decisions.
Related EPIC: MD-3023 - Human-in-the-Loop Approval System
"""

import pytest
from datetime import datetime, timedelta

from maestro_hive.oversight.approval_workflow import (
    ApprovalType,
    ApprovalStatus,
    Priority,
    ApprovalRequest,
    ApprovalWorkflow,
)
from maestro_hive.oversight.approval_queue import (
    QueueStats,
    QueueEntry,
    ApprovalQueue,
    get_approval_queue,
)


class TestQueueStats:
    """Tests for QueueStats dataclass."""

    def test_queue_stats_creation(self):
        """Test creating queue statistics."""
        stats = QueueStats(
            total_pending=10,
            by_priority={"LOW": 2, "NORMAL": 5, "HIGH": 2, "CRITICAL": 1},
            by_type={"decision": 6, "critical": 3, "compliance": 1},
            overdue_count=2,
            average_wait_seconds=300.5,
            oldest_request_age_seconds=1200,
        )
        assert stats.total_pending == 10
        assert stats.by_priority["NORMAL"] == 5
        assert stats.overdue_count == 2
        assert stats.average_wait_seconds == 300.5

    def test_queue_stats_to_dict(self):
        """Test serialization to dictionary."""
        stats = QueueStats(
            total_pending=5,
            by_priority={"LOW": 1, "NORMAL": 2, "HIGH": 1, "CRITICAL": 1},
            by_type={"decision": 3, "critical": 2},
            overdue_count=0,
            average_wait_seconds=120.0,
            oldest_request_age_seconds=300,
        )
        data = stats.to_dict()
        assert data["total_pending"] == 5
        assert data["overdue_count"] == 0
        assert "timestamp" in data


class TestQueueEntry:
    """Tests for QueueEntry dataclass."""

    def test_queue_entry_creation(self):
        """Test creating a queue entry."""
        deadline = datetime.utcnow() + timedelta(hours=1)
        entry = QueueEntry(
            request_id="apr_test123",
            enqueued_at=datetime.utcnow(),
            priority=Priority.HIGH,
            assigned_to=["approver1", "approver2"],
            request_type=ApprovalType.DECISION,
            deadline=deadline,
        )
        assert entry.request_id == "apr_test123"
        assert entry.priority == Priority.HIGH
        assert len(entry.assigned_to) == 2
        assert entry.request_type == ApprovalType.DECISION


class TestApprovalQueue:
    """Tests for ApprovalQueue class."""

    @pytest.fixture(autouse=True)
    def reset_singletons(self):
        """Reset singletons before each test."""
        ApprovalWorkflow._instance = None
        ApprovalQueue._instance = None
        import maestro_hive.oversight.approval_workflow as wf_module
        import maestro_hive.oversight.approval_queue as q_module
        wf_module._workflow_instance = None
        q_module._queue_instance = None
        yield
        ApprovalWorkflow._instance = None
        ApprovalQueue._instance = None
        wf_module._workflow_instance = None
        q_module._queue_instance = None

    @pytest.fixture
    def queue(self):
        """Create a fresh queue instance."""
        return ApprovalQueue()

    @pytest.fixture
    def workflow(self):
        """Create a fresh workflow instance."""
        return ApprovalWorkflow()

    @pytest.fixture
    def sample_request(self, workflow):
        """Create a sample approval request."""
        return workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={"action": "test"},
            assigned_to=["approver1"],
            priority=Priority.NORMAL,
        )

    def test_singleton_pattern(self):
        """Test that ApprovalQueue follows singleton pattern."""
        q1 = ApprovalQueue()
        q2 = ApprovalQueue()
        assert q1 is q2

    def test_enqueue(self, queue, sample_request):
        """Test enqueueing a request."""
        result = queue.enqueue(sample_request)
        assert result is True
        pending = queue.get_pending()
        assert len(pending) == 1
        assert pending[0].id == sample_request.id

    def test_enqueue_duplicate(self, queue, sample_request):
        """Test enqueueing duplicate request fails."""
        queue.enqueue(sample_request)
        result = queue.enqueue(sample_request)
        assert result is False

    def test_enqueue_non_pending(self, workflow, queue):
        """Test enqueueing non-pending request fails."""
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        workflow.process_approval(
            request_id=request.id,
            decision=ApprovalType.DECISION,  # Wrong enum, will fail
            approver_id="approver1",
        )
        # Actually let's use the correct approach
        from maestro_hive.oversight.approval_workflow import ApprovalDecision
        workflow.process_approval(
            request_id=request.id,
            decision=ApprovalDecision.APPROVED,
            approver_id="approver1",
        )
        # Now try to enqueue the approved request
        result = queue.enqueue(request)
        assert result is False

    def test_dequeue(self, queue, sample_request):
        """Test dequeueing a request."""
        queue.enqueue(sample_request)
        result = queue.dequeue(sample_request.id)
        assert result is not None
        assert result.id == sample_request.id
        # Verify it's no longer in queue
        pending = queue.get_pending()
        assert len(pending) == 0

    def test_dequeue_not_found(self, queue):
        """Test dequeueing non-existent request."""
        result = queue.dequeue("apr_nonexistent")
        assert result is None

    def test_get_pending(self, workflow, queue):
        """Test getting pending requests."""
        r1 = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
            priority=Priority.LOW,
        )
        r2 = workflow.create_request(
            request_type=ApprovalType.CRITICAL,
            context={},
            assigned_to=["approver1"],
            priority=Priority.CRITICAL,
        )
        queue.enqueue(r1)
        queue.enqueue(r2)
        pending = queue.get_pending()
        assert len(pending) == 2
        # Critical should come first
        assert pending[0].priority == Priority.CRITICAL

    def test_get_pending_by_approver(self, workflow, queue):
        """Test getting pending requests for specific approver."""
        r1 = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        r2 = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver2"],
        )
        queue.enqueue(r1)
        queue.enqueue(r2)
        pending = queue.get_pending(approver_id="approver1")
        assert len(pending) == 1
        assert "approver1" in pending[0].assigned_to

    def test_get_pending_limit(self, workflow, queue):
        """Test get_pending respects limit parameter."""
        for i in range(5):
            request = workflow.create_request(
                request_type=ApprovalType.DECISION,
                context={"i": i},
                assigned_to=["approver1"],
            )
            queue.enqueue(request)
        pending = queue.get_pending(limit=3)
        assert len(pending) == 3

    def test_get_by_priority(self, workflow, queue):
        """Test getting requests by priority."""
        r1 = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
            priority=Priority.LOW,
        )
        r2 = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
            priority=Priority.HIGH,
        )
        r3 = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
            priority=Priority.HIGH,
        )
        queue.enqueue(r1)
        queue.enqueue(r2)
        queue.enqueue(r3)
        high_priority = queue.get_by_priority(Priority.HIGH)
        assert len(high_priority) == 2

    def test_get_by_type(self, workflow, queue):
        """Test getting requests by type."""
        r1 = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        r2 = workflow.create_request(
            request_type=ApprovalType.CRITICAL,
            context={},
            assigned_to=["approver1"],
        )
        r3 = workflow.create_request(
            request_type=ApprovalType.COMPLIANCE,
            context={},
            assigned_to=["approver1"],
        )
        queue.enqueue(r1)
        queue.enqueue(r2)
        queue.enqueue(r3)
        decisions = queue.get_by_type(ApprovalType.DECISION)
        assert len(decisions) == 1
        critical = queue.get_by_type(ApprovalType.CRITICAL)
        assert len(critical) == 1

    def test_prioritize(self, workflow, queue):
        """Test changing request priority."""
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
            priority=Priority.LOW,
        )
        queue.enqueue(request)
        result = queue.prioritize(request.id, Priority.CRITICAL)
        assert result is True
        assert request.priority == Priority.CRITICAL

    def test_prioritize_not_found(self, queue):
        """Test prioritizing non-existent request."""
        result = queue.prioritize("apr_nonexistent", Priority.HIGH)
        assert result is False

    def test_get_overdue(self, workflow, queue):
        """Test getting overdue requests."""
        # Create a request with 1 second timeout that's already past
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
            timeout_seconds=1,
        )
        # Manually set created_at to past
        request.created_at = datetime.utcnow() - timedelta(seconds=10)
        queue.enqueue(request)
        overdue = queue.get_overdue()
        assert len(overdue) == 1
        assert overdue[0].id == request.id

    def test_get_expiring_soon(self, workflow, queue):
        """Test getting soon-to-expire requests."""
        # Request with 10 minutes left
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
            timeout_seconds=600,
        )
        queue.enqueue(request)
        expiring = queue.get_expiring_soon(within_seconds=900)
        assert len(expiring) == 1

    def test_get_stats(self, workflow, queue):
        """Test getting queue statistics."""
        r1 = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
            priority=Priority.LOW,
        )
        r2 = workflow.create_request(
            request_type=ApprovalType.CRITICAL,
            context={},
            assigned_to=["approver1"],
            priority=Priority.CRITICAL,
        )
        queue.enqueue(r1)
        queue.enqueue(r2)
        stats = queue.get_stats()
        assert stats.total_pending == 2
        assert stats.by_priority["LOW"] == 1
        assert stats.by_priority["CRITICAL"] == 1
        assert stats.by_type["decision"] == 1
        assert stats.by_type["critical"] == 1

    def test_get_stats_empty_queue(self, queue):
        """Test getting stats for empty queue."""
        stats = queue.get_stats()
        assert stats.total_pending == 0
        assert stats.average_wait_seconds == 0
        assert stats.oldest_request_age_seconds == 0

    def test_get_approver_load(self, workflow, queue):
        """Test getting approver load distribution."""
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
        r3 = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver2"],
        )
        queue.enqueue(r1)
        queue.enqueue(r2)
        queue.enqueue(r3)
        load = queue.get_approver_load()
        assert load["approver1"] == 2
        assert load["approver2"] == 1

    def test_reassign(self, workflow, queue):
        """Test reassigning a request to different approvers."""
        request = workflow.create_request(
            request_type=ApprovalType.DECISION,
            context={},
            assigned_to=["approver1"],
        )
        queue.enqueue(request)
        result = queue.reassign(request.id, ["approver2", "approver3"])
        assert result is True
        assert "approver2" in request.assigned_to
        assert "approver3" in request.assigned_to
        assert "approver1" not in request.assigned_to

    def test_reassign_not_found(self, queue):
        """Test reassigning non-existent request."""
        result = queue.reassign("apr_nonexistent", ["approver2"])
        assert result is False

    def test_clear_completed(self, workflow, queue):
        """Test clearing completed requests from queue."""
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
        # Approve one request
        from maestro_hive.oversight.approval_workflow import ApprovalDecision
        workflow.process_approval(
            request_id=r1.id,
            decision=ApprovalDecision.APPROVED,
            approver_id="approver1",
        )
        removed = queue.clear_completed()
        assert removed == 1
        pending = queue.get_pending()
        assert len(pending) == 1
        assert pending[0].id == r2.id


class TestGetApprovalQueue:
    """Tests for get_approval_queue convenience function."""

    @pytest.fixture(autouse=True)
    def reset_singletons(self):
        """Reset singletons before each test."""
        ApprovalWorkflow._instance = None
        ApprovalQueue._instance = None
        import maestro_hive.oversight.approval_queue as q_module
        q_module._queue_instance = None
        yield
        ApprovalQueue._instance = None
        q_module._queue_instance = None

    def test_get_approval_queue_singleton(self):
        """Test get_approval_queue returns singleton."""
        q1 = get_approval_queue()
        q2 = get_approval_queue()
        assert q1 is q2
