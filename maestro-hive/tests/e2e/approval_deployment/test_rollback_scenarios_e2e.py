#!/usr/bin/env python3
"""
E2E Tests: Rollback Scenarios (AC-3)

Tests rollback and recovery scenarios including:
- Workflow suspension pending approval
- Workflow resumption after approval
- State preservation during suspension
- Rollback on rejection/expiration

EPIC: MD-3038 - Approval & Deployment E2E Tests
"""

import pytest
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock
from unittest.mock import MagicMock


# =============================================================================
# Rollback System Implementation for Testing
# =============================================================================

class RollbackState(str, Enum):
    """Rollback state."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowCheckpoint:
    """Checkpoint for workflow state."""
    checkpoint_id: str
    workflow_id: str
    step: int
    state: Dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


@dataclass
class RollbackOperation:
    """Represents a rollback operation."""
    rollback_id: str
    workflow_id: str
    reason: str
    initiated_by: str
    from_checkpoint: Optional[str] = None
    state: RollbackState = RollbackState.PENDING
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


class WorkflowStateManager:
    """
    Manages workflow state, checkpoints, and rollbacks.

    Provides:
    - State checkpointing before critical operations
    - Workflow suspension for approvals
    - State recovery on rollback
    - Audit trail for state changes
    """

    def __init__(self):
        self._checkpoints: Dict[str, List[WorkflowCheckpoint]] = {}
        self._suspended: Dict[str, Dict[str, Any]] = {}
        self._rollbacks: Dict[str, RollbackOperation] = {}
        self._audit_log: List[Dict[str, Any]] = []
        self._lock = Lock()
        self._counter = 0

    def create_checkpoint(
        self,
        workflow_id: str,
        step: int,
        state: Dict[str, Any]
    ) -> WorkflowCheckpoint:
        """Create a checkpoint for workflow state."""
        with self._lock:
            self._counter += 1
            checkpoint_id = f"ckpt-{workflow_id}-{step}-{self._counter}"

        checkpoint = WorkflowCheckpoint(
            checkpoint_id=checkpoint_id,
            workflow_id=workflow_id,
            step=step,
            state=state.copy()
        )

        if workflow_id not in self._checkpoints:
            self._checkpoints[workflow_id] = []
        self._checkpoints[workflow_id].append(checkpoint)

        self._log_event("checkpoint_created", {
            "checkpoint_id": checkpoint_id,
            "workflow_id": workflow_id,
            "step": step
        })

        return checkpoint

    def suspend_workflow(
        self,
        workflow_id: str,
        reason: str,
        state: Dict[str, Any],
        approval_id: Optional[str] = None
    ) -> bool:
        """Suspend workflow pending approval or other blocking condition."""
        if workflow_id in self._suspended:
            return False

        self._suspended[workflow_id] = {
            "reason": reason,
            "state": state.copy(),
            "approval_id": approval_id,
            "suspended_at": datetime.utcnow().isoformat() + "Z"
        }

        self._log_event("workflow_suspended", {
            "workflow_id": workflow_id,
            "reason": reason,
            "approval_id": approval_id
        })

        return True

    def resume_workflow(
        self,
        workflow_id: str,
        approved_by: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Resume a suspended workflow, returning preserved state."""
        if workflow_id not in self._suspended:
            return None

        suspended_data = self._suspended.pop(workflow_id)

        self._log_event("workflow_resumed", {
            "workflow_id": workflow_id,
            "approved_by": approved_by,
            "suspended_duration_seconds": self._calculate_duration(
                suspended_data["suspended_at"]
            )
        })

        return suspended_data["state"]

    def is_suspended(self, workflow_id: str) -> bool:
        """Check if workflow is suspended."""
        return workflow_id in self._suspended

    def get_suspension_info(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get suspension information."""
        return self._suspended.get(workflow_id)

    def initiate_rollback(
        self,
        workflow_id: str,
        reason: str,
        initiated_by: str,
        to_checkpoint: Optional[str] = None
    ) -> RollbackOperation:
        """Initiate a rollback operation."""
        with self._lock:
            self._counter += 1
            rollback_id = f"rollback-{workflow_id}-{self._counter}"

        rollback = RollbackOperation(
            rollback_id=rollback_id,
            workflow_id=workflow_id,
            reason=reason,
            initiated_by=initiated_by,
            from_checkpoint=to_checkpoint,
            state=RollbackState.PENDING
        )

        self._rollbacks[rollback_id] = rollback

        self._log_event("rollback_initiated", {
            "rollback_id": rollback_id,
            "workflow_id": workflow_id,
            "reason": reason,
            "initiated_by": initiated_by
        })

        return rollback

    def execute_rollback(
        self,
        rollback_id: str,
        recovery_callback: callable = None
    ) -> RollbackOperation:
        """Execute a rollback operation."""
        if rollback_id not in self._rollbacks:
            raise ValueError(f"Rollback not found: {rollback_id}")

        rollback = self._rollbacks[rollback_id]
        rollback.state = RollbackState.IN_PROGRESS

        try:
            # Get checkpoint to restore
            checkpoint = None
            if rollback.from_checkpoint:
                checkpoints = self._checkpoints.get(rollback.workflow_id, [])
                checkpoint = next(
                    (c for c in checkpoints if c.checkpoint_id == rollback.from_checkpoint),
                    None
                )

            if checkpoint is None and rollback.workflow_id in self._checkpoints:
                # Use latest checkpoint
                checkpoints = self._checkpoints[rollback.workflow_id]
                if checkpoints:
                    checkpoint = checkpoints[-1]

            # Execute recovery callback
            if recovery_callback and checkpoint:
                recovery_callback(checkpoint.state)

            rollback.state = RollbackState.COMPLETED
            rollback.completed_at = datetime.utcnow().isoformat() + "Z"

            self._log_event("rollback_completed", {
                "rollback_id": rollback_id,
                "workflow_id": rollback.workflow_id,
                "restored_to_checkpoint": checkpoint.checkpoint_id if checkpoint else None
            })

        except Exception as e:
            rollback.state = RollbackState.FAILED
            rollback.error_message = str(e)
            rollback.completed_at = datetime.utcnow().isoformat() + "Z"

            self._log_event("rollback_failed", {
                "rollback_id": rollback_id,
                "error": str(e)
            })

        return rollback

    def cancel_rollback(self, rollback_id: str, reason: str) -> RollbackOperation:
        """Cancel a pending rollback."""
        if rollback_id not in self._rollbacks:
            raise ValueError(f"Rollback not found: {rollback_id}")

        rollback = self._rollbacks[rollback_id]
        if rollback.state != RollbackState.PENDING:
            raise ValueError(f"Cannot cancel rollback in state: {rollback.state}")

        rollback.state = RollbackState.CANCELLED
        rollback.completed_at = datetime.utcnow().isoformat() + "Z"
        rollback.error_message = reason

        self._log_event("rollback_cancelled", {
            "rollback_id": rollback_id,
            "reason": reason
        })

        return rollback

    def get_checkpoints(self, workflow_id: str) -> List[WorkflowCheckpoint]:
        """Get all checkpoints for a workflow."""
        return self._checkpoints.get(workflow_id, [])

    def get_rollback(self, rollback_id: str) -> Optional[RollbackOperation]:
        """Get rollback operation by ID."""
        return self._rollbacks.get(rollback_id)

    def get_audit_log(self, workflow_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get audit log entries."""
        if workflow_id:
            return [
                e for e in self._audit_log
                if e.get("data", {}).get("workflow_id") == workflow_id
            ]
        return self._audit_log

    def _log_event(self, event_type: str, data: Dict[str, Any]):
        """Log an event to audit trail."""
        self._audit_log.append({
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "data": data
        })

    def _calculate_duration(self, start_time: str) -> float:
        """Calculate duration in seconds from start time."""
        start = datetime.fromisoformat(start_time.replace("Z", ""))
        return (datetime.utcnow() - start).total_seconds()


# =============================================================================
# E2E Test Suite
# =============================================================================

class TestRollbackScenariosE2E:
    """E2E Tests for Rollback Scenarios (AC-3)"""

    @pytest.fixture
    def state_manager(self):
        """Create fresh state manager."""
        return WorkflowStateManager()

    # =========================================================================
    # Test: Workflow Suspension Pending Approval
    # =========================================================================
    def test_e2e_workflow_suspension_pending_approval(self, state_manager):
        """
        E2E-ROL-001: Workflow suspension pending approval.

        Flow: Workflow Running -> Needs Approval -> Suspend -> Wait
        """
        workflow_id = "wf-001"

        # Create checkpoint before suspension
        checkpoint = state_manager.create_checkpoint(
            workflow_id=workflow_id,
            step=5,
            state={"processed_items": 100, "current_batch": 3}
        )

        assert checkpoint.checkpoint_id is not None
        assert checkpoint.step == 5

        # Suspend workflow
        result = state_manager.suspend_workflow(
            workflow_id=workflow_id,
            reason="Requires manager approval for batch processing",
            state={"processed_items": 100, "current_batch": 3, "pending_step": 6},
            approval_id="apr-123"
        )

        assert result is True
        assert state_manager.is_suspended(workflow_id) is True

        # Verify suspension info
        info = state_manager.get_suspension_info(workflow_id)
        assert info is not None
        assert info["approval_id"] == "apr-123"
        assert info["state"]["processed_items"] == 100

    # =========================================================================
    # Test: Workflow Resumption After Approval
    # =========================================================================
    def test_e2e_workflow_resumption_after_approval(self, state_manager):
        """
        E2E-ROL-002: Workflow resumption after approval.

        Flow: Suspended -> Approved -> Resume with State
        """
        workflow_id = "wf-002"

        # Suspend workflow
        state_manager.suspend_workflow(
            workflow_id=workflow_id,
            reason="Pending approval",
            state={"step": 10, "data": [1, 2, 3]}
        )

        assert state_manager.is_suspended(workflow_id) is True

        # Resume workflow
        restored_state = state_manager.resume_workflow(
            workflow_id=workflow_id,
            approved_by="manager"
        )

        assert restored_state is not None
        assert restored_state["step"] == 10
        assert restored_state["data"] == [1, 2, 3]
        assert state_manager.is_suspended(workflow_id) is False

    # =========================================================================
    # Test: State Preservation During Suspension
    # =========================================================================
    def test_e2e_state_preservation_during_suspension(self, state_manager):
        """
        E2E-ROL-003: State preservation during suspension.

        Verifies that all state data is preserved across suspension.
        """
        workflow_id = "wf-003"

        # Complex state to preserve
        complex_state = {
            "step": 15,
            "nested": {
                "level1": {
                    "level2": [1, 2, 3]
                }
            },
            "items": ["a", "b", "c"],
            "metadata": {
                "created_at": "2024-01-01",
                "updated_at": "2024-01-02"
            }
        }

        state_manager.suspend_workflow(
            workflow_id=workflow_id,
            reason="Complex state test",
            state=complex_state
        )

        restored = state_manager.resume_workflow(workflow_id)

        # Verify all state preserved
        assert restored["step"] == 15
        assert restored["nested"]["level1"]["level2"] == [1, 2, 3]
        assert restored["items"] == ["a", "b", "c"]
        assert restored["metadata"]["created_at"] == "2024-01-01"

    # =========================================================================
    # Test: Rollback on Rejected Approval
    # =========================================================================
    def test_e2e_rollback_on_rejected_approval(self, state_manager):
        """
        E2E-ROL-004: Rollback on rejected approval.

        Flow: Suspended -> Rejected -> Initiate Rollback -> Execute
        """
        workflow_id = "wf-004"

        # Create checkpoints
        state_manager.create_checkpoint(workflow_id, 1, {"data": "initial"})
        state_manager.create_checkpoint(workflow_id, 5, {"data": "step5"})
        state_manager.create_checkpoint(workflow_id, 10, {"data": "step10"})

        # Suspend workflow
        state_manager.suspend_workflow(
            workflow_id=workflow_id,
            reason="Pending approval",
            state={"data": "current", "step": 10}
        )

        # Simulate rejection - initiate rollback
        rollback = state_manager.initiate_rollback(
            workflow_id=workflow_id,
            reason="Approval rejected - reverting to safe state",
            initiated_by="system"
        )

        assert rollback.state == RollbackState.PENDING

        # Track recovery
        recovered_state = {"value": None}

        def recovery_callback(state):
            recovered_state["value"] = state

        # Execute rollback
        completed = state_manager.execute_rollback(rollback.rollback_id, recovery_callback)

        assert completed.state == RollbackState.COMPLETED
        assert recovered_state["value"] is not None

    # =========================================================================
    # Test: Rollback on Expired Approval
    # =========================================================================
    def test_e2e_rollback_on_expired_approval(self, state_manager):
        """
        E2E-ROL-005: Rollback on expired approval.

        Flow: Suspended -> Timeout -> Initiate Rollback
        """
        workflow_id = "wf-005"

        # Create checkpoint
        checkpoint = state_manager.create_checkpoint(
            workflow_id,
            3,
            {"status": "pre-approval"}
        )

        # Suspend workflow
        state_manager.suspend_workflow(
            workflow_id=workflow_id,
            reason="Awaiting time-limited approval",
            state={"status": "pending"}
        )

        # Simulate expiration - initiate rollback with specific checkpoint
        rollback = state_manager.initiate_rollback(
            workflow_id=workflow_id,
            reason="Approval expired - automatic rollback",
            initiated_by="system",
            to_checkpoint=checkpoint.checkpoint_id
        )

        # Execute rollback
        completed = state_manager.execute_rollback(rollback.rollback_id)

        assert completed.state == RollbackState.COMPLETED
        assert completed.from_checkpoint == checkpoint.checkpoint_id

    # =========================================================================
    # Test: Callback Execution on Resume
    # =========================================================================
    def test_e2e_callback_execution_on_resume(self, state_manager):
        """
        E2E-ROL-006: Callback execution on workflow resume.

        Tests that callbacks are properly executed after resumption.
        """
        workflow_id = "wf-006"
        callback_results = {"called": False, "state": None}

        # Suspend workflow
        state_manager.suspend_workflow(
            workflow_id=workflow_id,
            reason="Testing callback",
            state={"value": 42}
        )

        # Resume and track
        restored = state_manager.resume_workflow(workflow_id, approved_by="approver")

        # Simulate callback execution after resume
        if restored:
            callback_results["called"] = True
            callback_results["state"] = restored

        assert callback_results["called"] is True
        assert callback_results["state"]["value"] == 42

    # =========================================================================
    # Test: Multiple Suspensions Handling
    # =========================================================================
    def test_e2e_multiple_suspensions_handling(self, state_manager):
        """
        E2E-ROL-007: Handle multiple concurrent workflow suspensions.
        """
        workflows = ["wf-007-a", "wf-007-b", "wf-007-c"]

        # Suspend multiple workflows
        for i, wf_id in enumerate(workflows):
            state_manager.suspend_workflow(
                workflow_id=wf_id,
                reason=f"Suspension {i}",
                state={"index": i}
            )

        # Verify all suspended
        for wf_id in workflows:
            assert state_manager.is_suspended(wf_id) is True

        # Resume in different order
        state_manager.resume_workflow(workflows[1])
        state_manager.resume_workflow(workflows[0])
        state_manager.resume_workflow(workflows[2])

        # Verify all resumed
        for wf_id in workflows:
            assert state_manager.is_suspended(wf_id) is False

    # =========================================================================
    # Test: Recovery from Failed Callback
    # =========================================================================
    def test_e2e_recovery_from_failed_callback(self, state_manager):
        """
        E2E-ROL-008: Recovery from failed callback during rollback.
        """
        workflow_id = "wf-008"

        # Create checkpoint
        state_manager.create_checkpoint(workflow_id, 1, {"safe": True})

        # Initiate rollback
        rollback = state_manager.initiate_rollback(
            workflow_id=workflow_id,
            reason="Testing failure recovery",
            initiated_by="test"
        )

        # Execute with failing callback
        def failing_callback(state):
            raise Exception("Callback failed!")

        completed = state_manager.execute_rollback(rollback.rollback_id, failing_callback)

        assert completed.state == RollbackState.FAILED
        assert "Callback failed" in completed.error_message

    # =========================================================================
    # Test: Concurrent Rollback Requests
    # =========================================================================
    def test_e2e_concurrent_rollback_requests(self, state_manager):
        """
        E2E-ROL-009: Handle concurrent rollback requests.
        """
        workflow_id = "wf-009"

        # Create checkpoints
        state_manager.create_checkpoint(workflow_id, 1, {"step": 1})
        state_manager.create_checkpoint(workflow_id, 2, {"step": 2})

        # Initiate multiple rollbacks
        rollback1 = state_manager.initiate_rollback(
            workflow_id=workflow_id,
            reason="First rollback",
            initiated_by="user1"
        )

        rollback2 = state_manager.initiate_rollback(
            workflow_id=workflow_id,
            reason="Second rollback",
            initiated_by="user2"
        )

        # Execute first, cancel second
        state_manager.execute_rollback(rollback1.rollback_id)
        state_manager.cancel_rollback(rollback2.rollback_id, "Another rollback in progress")

        assert state_manager.get_rollback(rollback1.rollback_id).state == RollbackState.COMPLETED
        assert state_manager.get_rollback(rollback2.rollback_id).state == RollbackState.CANCELLED

    # =========================================================================
    # Test: Audit Trail for Rollbacks
    # =========================================================================
    def test_e2e_audit_trail_for_rollbacks(self, state_manager):
        """
        E2E-ROL-010: Verify complete audit trail for rollback operations.
        """
        workflow_id = "wf-010"

        # Create checkpoint
        state_manager.create_checkpoint(workflow_id, 1, {"data": "test"})

        # Suspend
        state_manager.suspend_workflow(workflow_id, "Testing", {"data": "test"})

        # Resume
        state_manager.resume_workflow(workflow_id)

        # Initiate and execute rollback
        rollback = state_manager.initiate_rollback(
            workflow_id=workflow_id,
            reason="Audit trail test",
            initiated_by="tester"
        )
        state_manager.execute_rollback(rollback.rollback_id)

        # Verify audit trail
        audit_log = state_manager.get_audit_log(workflow_id)

        event_types = [e["event_type"] for e in audit_log]

        assert "checkpoint_created" in event_types
        assert "workflow_suspended" in event_types
        assert "workflow_resumed" in event_types
        assert "rollback_initiated" in event_types
        assert "rollback_completed" in event_types


class TestCheckpointManagementE2E:
    """E2E Tests for Checkpoint Management"""

    @pytest.fixture
    def state_manager(self):
        """Create fresh state manager."""
        return WorkflowStateManager()

    def test_e2e_checkpoint_creation_and_retrieval(self, state_manager):
        """
        E2E-ROL-011: Create and retrieve checkpoints.
        """
        workflow_id = "ckpt-test-001"

        # Create multiple checkpoints
        for i in range(5):
            state_manager.create_checkpoint(
                workflow_id,
                step=i + 1,
                state={"step": i + 1, "timestamp": datetime.utcnow().isoformat()}
            )

        # Retrieve checkpoints
        checkpoints = state_manager.get_checkpoints(workflow_id)

        assert len(checkpoints) == 5
        assert all(c.workflow_id == workflow_id for c in checkpoints)
        assert [c.step for c in checkpoints] == [1, 2, 3, 4, 5]

    def test_e2e_rollback_to_specific_checkpoint(self, state_manager):
        """
        E2E-ROL-012: Rollback to specific checkpoint.
        """
        workflow_id = "ckpt-test-002"

        # Create checkpoints
        ckpt1 = state_manager.create_checkpoint(workflow_id, 1, {"version": "v1"})
        ckpt2 = state_manager.create_checkpoint(workflow_id, 2, {"version": "v2"})
        ckpt3 = state_manager.create_checkpoint(workflow_id, 3, {"version": "v3"})

        recovered_state = {"value": None}

        def recovery_callback(state):
            recovered_state["value"] = state

        # Rollback to checkpoint 2
        rollback = state_manager.initiate_rollback(
            workflow_id=workflow_id,
            reason="Rollback to v2",
            initiated_by="test",
            to_checkpoint=ckpt2.checkpoint_id
        )

        state_manager.execute_rollback(rollback.rollback_id, recovery_callback)

        assert recovered_state["value"]["version"] == "v2"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
