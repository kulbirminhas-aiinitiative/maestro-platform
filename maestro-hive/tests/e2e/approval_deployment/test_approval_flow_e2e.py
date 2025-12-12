#!/usr/bin/env python3
"""
E2E Tests: Approval Request Flow (AC-1)

Tests the complete approval request lifecycle:
- Request creation -> Review -> Approve/Reject
- Multiple approval types (SINGLE, ALL, MAJORITY, SEQUENTIAL)
- Timeout, escalation, and delegation scenarios

EPIC: MD-3038 - Approval & Deployment E2E Tests
"""

import pytest
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
from unittest.mock import MagicMock

from maestro_hive.compliance.approval_engine import (
    ApprovalEngine,
    ApprovalRequest,
    ApprovalRule,
    ApprovalType,
    ApprovalStatus,
    Approver,
    ApprovalDecision,
    get_approval_engine,
)
from maestro_hive.oversight.approval_workflow import (
    ApprovalWorkflow,
    ApprovalType as WorkflowApprovalType,
    ApprovalStatus as WorkflowApprovalStatus,
    ApprovalDecision as WorkflowApprovalDecision,
    Priority,
    get_approval_workflow,
    create_approval_request,
)


class TestApprovalRequestFlowE2E:
    """E2E Tests for Approval Request Flow (AC-1)"""

    @pytest.fixture
    def temp_storage(self, tmp_path):
        """Create temporary storage directory."""
        storage_dir = tmp_path / "approvals"
        storage_dir.mkdir(parents=True, exist_ok=True)
        return str(storage_dir)

    @pytest.fixture
    def approval_engine(self, temp_storage):
        """Create a fresh approval engine for each test."""
        notifications = []
        audits = []

        def notification_callback(request, approver_id):
            notifications.append({
                "request_id": request.id,
                "approver_id": approver_id,
                "timestamp": datetime.utcnow().isoformat()
            })

        def audit_callback(request):
            audits.append({
                "request_id": request.id,
                "status": request.status.value,
                "timestamp": datetime.utcnow().isoformat()
            })

        engine = ApprovalEngine(
            storage_dir=temp_storage,
            notification_callback=notification_callback,
            audit_callback=audit_callback
        )
        engine._notifications = notifications
        engine._audits = audits
        return engine

    @pytest.fixture
    def workflow_engine(self):
        """Create a fresh workflow engine for each test."""
        ApprovalWorkflow._instance = None
        import maestro_hive.oversight.approval_workflow as module
        module._workflow_instance = None
        return ApprovalWorkflow()

    # =========================================================================
    # Test: Single Approver Approval Flow
    # =========================================================================
    def test_e2e_single_approver_approval_flow(self, approval_engine):
        """
        E2E-APR-001: Complete single approver approval flow.

        Flow: Create Request -> Notification Sent -> Approver Reviews -> Approve
        """
        # Step 1: Create approval rule
        rule = ApprovalRule(
            id="deployment-rule",
            name="Deployment Approval",
            description="Requires approval for deployment",
            resource_pattern="deploy/*",
            action_pattern="execute",
            approval_type=ApprovalType.SINGLE,
            required_approvers=["lead-dev", "ops-lead"],
            timeout_hours=24
        )
        approval_engine.add_rule(rule)

        # Step 2: Check if approval required
        matched_rule = approval_engine.requires_approval(
            resource="deploy/production",
            action="execute",
            context={}
        )
        assert matched_rule is not None
        assert matched_rule.id == "deployment-rule"

        # Step 3: Create approval request
        request = approval_engine.create_request(
            requester_id="developer-001",
            resource="deploy/production",
            action="execute",
            rule=matched_rule,
            context={"version": "2.1.0", "commit": "abc123"}
        )

        assert request.status == ApprovalStatus.PENDING
        assert request.approval_type == ApprovalType.SINGLE
        assert len(request.required_approvers) == 2

        # Step 4: Verify notifications sent
        assert len(approval_engine._notifications) == 2

        # Step 5: First approver approves (single approval type - done)
        approved_request = approval_engine.decide(
            request_id=request.id,
            approver_id="lead-dev",
            approved=True,
            comment="LGTM - code reviewed and tested"
        )

        assert approved_request.status == ApprovalStatus.APPROVED
        assert approved_request.completed_at is not None
        assert len(approved_request.decisions) == 1
        assert approved_request.decisions[0].approver_id == "lead-dev"

    # =========================================================================
    # Test: Multi-Approver (ALL) Approval Flow
    # =========================================================================
    def test_e2e_multi_approver_all_approval_flow(self, approval_engine):
        """
        E2E-APR-002: Multi-approver flow where ALL must approve.

        Flow: Create Request -> All Approvers Review -> All Approve -> Complete
        """
        # Step 1: Create rule requiring all approvers
        rule = ApprovalRule(
            id="critical-change-rule",
            name="Critical Change Approval",
            description="All approvers must approve",
            resource_pattern="config/critical/*",
            action_pattern="modify",
            approval_type=ApprovalType.ALL,
            required_approvers=["security-lead", "tech-lead", "product-owner"],
            timeout_hours=48
        )
        approval_engine.add_rule(rule)

        # Step 2: Create request
        request = approval_engine.create_request(
            requester_id="developer-002",
            resource="config/critical/auth",
            action="modify",
            rule=rule,
            context={"change": "Enable MFA"}
        )

        assert request.approval_type == ApprovalType.ALL

        # Step 3: First approver approves (not complete yet)
        request = approval_engine.decide(request.id, "security-lead", True, "Security OK")
        assert request.status == ApprovalStatus.PENDING

        # Step 4: Second approver approves (still not complete)
        request = approval_engine.decide(request.id, "tech-lead", True, "Tech OK")
        assert request.status == ApprovalStatus.PENDING

        # Step 5: Third approver approves (now complete)
        request = approval_engine.decide(request.id, "product-owner", True, "Product OK")
        assert request.status == ApprovalStatus.APPROVED
        assert len(request.decisions) == 3

    # =========================================================================
    # Test: Majority Approval Flow
    # =========================================================================
    def test_e2e_majority_approval_flow(self, approval_engine):
        """
        E2E-APR-003: Majority approval flow.

        Flow: Create Request -> Majority (2/3) Approve -> Complete
        """
        rule = ApprovalRule(
            id="feature-flag-rule",
            name="Feature Flag Approval",
            description="Majority must approve",
            resource_pattern="feature-flags/*",
            action_pattern="enable",
            approval_type=ApprovalType.MAJORITY,
            required_approvers=["dev-1", "dev-2", "dev-3"],
            timeout_hours=24
        )
        approval_engine.add_rule(rule)

        request = approval_engine.create_request(
            requester_id="pm-001",
            resource="feature-flags/dark-mode",
            action="enable",
            rule=rule
        )

        # First approver approves (1/3 - not majority)
        request = approval_engine.decide(request.id, "dev-1", True)
        assert request.status == ApprovalStatus.PENDING

        # Second approver approves (2/3 - majority achieved)
        request = approval_engine.decide(request.id, "dev-2", True)
        assert request.status == ApprovalStatus.APPROVED

    # =========================================================================
    # Test: Sequential Approval Flow
    # =========================================================================
    def test_e2e_sequential_approval_flow(self, approval_engine):
        """
        E2E-APR-004: Sequential approval flow.

        Flow: Create Request -> Approvers in Order -> Complete
        """
        rule = ApprovalRule(
            id="budget-approval-rule",
            name="Budget Approval",
            description="Sequential approval chain",
            resource_pattern="budget/*",
            action_pattern="increase",
            approval_type=ApprovalType.SEQUENTIAL,
            required_approvers=["manager", "director", "cfo"],
            timeout_hours=72
        )
        approval_engine.add_rule(rule)

        request = approval_engine.create_request(
            requester_id="finance-analyst",
            resource="budget/engineering",
            action="increase",
            rule=rule,
            context={"amount": 50000}
        )

        assert request.current_stage == 0

        # Manager approves first
        request = approval_engine.decide(request.id, "manager", True)
        assert request.status == ApprovalStatus.PENDING
        assert request.current_stage == 1

        # Director approves second
        request = approval_engine.decide(request.id, "director", True)
        assert request.status == ApprovalStatus.PENDING
        assert request.current_stage == 2

        # CFO approves last
        request = approval_engine.decide(request.id, "cfo", True)
        assert request.status == ApprovalStatus.APPROVED

    # =========================================================================
    # Test: Rejection Scenarios
    # =========================================================================
    def test_e2e_rejection_scenarios(self, approval_engine):
        """
        E2E-APR-005: Approval rejection scenarios.

        Tests rejection in different approval types.
        """
        # Test ALL type - one rejection blocks
        rule_all = ApprovalRule(
            id="rule-all",
            name="All Required",
            description="Test",
            resource_pattern="test/all/*",
            action_pattern="*",
            approval_type=ApprovalType.ALL,
            required_approvers=["a", "b", "c"]
        )
        approval_engine.add_rule(rule_all)

        request = approval_engine.create_request(
            requester_id="user",
            resource="test/all/item",
            action="do",
            rule=rule_all
        )

        # First approves
        approval_engine.decide(request.id, "a", True)

        # Second rejects - should block entire request
        request = approval_engine.decide(request.id, "b", False, "Does not meet requirements")
        assert request.status == ApprovalStatus.REJECTED

        # Test MAJORITY type - majority rejection blocks
        rule_majority = ApprovalRule(
            id="rule-majority",
            name="Majority Required",
            description="Test",
            resource_pattern="test/majority/*",
            action_pattern="*",
            approval_type=ApprovalType.MAJORITY,
            required_approvers=["x", "y", "z"]
        )
        approval_engine.add_rule(rule_majority)

        request2 = approval_engine.create_request(
            requester_id="user",
            resource="test/majority/item",
            action="do",
            rule=rule_majority
        )

        # Two rejections block (majority rejected)
        approval_engine.decide(request2.id, "x", False)
        request2 = approval_engine.decide(request2.id, "y", False)
        assert request2.status == ApprovalStatus.REJECTED

    # =========================================================================
    # Test: Cancellation Scenarios
    # =========================================================================
    def test_e2e_cancellation_scenarios(self, approval_engine):
        """
        E2E-APR-006: Request cancellation by requester.
        """
        rule = ApprovalRule(
            id="cancel-test-rule",
            name="Cancellation Test",
            description="Test",
            resource_pattern="cancel/*",
            action_pattern="*",
            approval_type=ApprovalType.SINGLE,
            required_approvers=["approver"]
        )
        approval_engine.add_rule(rule)

        request = approval_engine.create_request(
            requester_id="user",
            resource="cancel/item",
            action="do",
            rule=rule
        )

        # Cancel the request
        cancelled = approval_engine.cancel_request(
            request_id=request.id,
            cancelled_by="user",
            reason="No longer needed"
        )

        assert cancelled.status == ApprovalStatus.CANCELLED
        assert cancelled.metadata["cancelled_by"] == "user"
        assert cancelled.metadata["cancel_reason"] == "No longer needed"

        # Cannot approve cancelled request
        with pytest.raises(ValueError) as exc_info:
            approval_engine.decide(request.id, "approver", True)
        assert "already completed" in str(exc_info.value).lower()

    # =========================================================================
    # Test: Timeout and Expiration
    # =========================================================================
    def test_e2e_timeout_and_expiration(self, approval_engine):
        """
        E2E-APR-007: Request timeout and expiration handling.
        """
        rule = ApprovalRule(
            id="expire-test-rule",
            name="Expiration Test",
            description="Test",
            resource_pattern="expire/*",
            action_pattern="*",
            approval_type=ApprovalType.SINGLE,
            required_approvers=["approver"],
            timeout_hours=1  # 1 hour timeout
        )
        approval_engine.add_rule(rule)

        request = approval_engine.create_request(
            requester_id="user",
            resource="expire/item",
            action="do",
            rule=rule
        )

        # Manually expire the request
        request.expires_at = (datetime.utcnow() - timedelta(hours=1)).isoformat()

        # Check expiration
        assert request.is_expired() is True

        # Trying to approve expired request should fail
        with pytest.raises(ValueError) as exc_info:
            approval_engine.decide(request.id, "approver", True)
        assert "expired" in str(exc_info.value).lower()

    # =========================================================================
    # Test: Delegate Approval
    # =========================================================================
    def test_e2e_delegate_approval(self, approval_engine):
        """
        E2E-APR-008: Approval by delegate.
        """
        # Register approver with delegate
        approver = Approver(
            id="manager",
            name="Manager",
            email="manager@example.com",
            delegate="assistant-manager"
        )
        approval_engine.register_approver(approver)

        rule = ApprovalRule(
            id="delegate-test-rule",
            name="Delegate Test",
            description="Test",
            resource_pattern="delegate/*",
            action_pattern="*",
            approval_type=ApprovalType.SINGLE,
            required_approvers=["manager"]
        )
        approval_engine.add_rule(rule)

        request = approval_engine.create_request(
            requester_id="user",
            resource="delegate/item",
            action="do",
            rule=rule
        )

        # Delegate approves on behalf of manager
        request = approval_engine.decide(
            request.id,
            "assistant-manager",
            True,
            "Approved on behalf of manager"
        )

        assert request.status == ApprovalStatus.APPROVED
        assert request.decisions[0].approver_id == "assistant-manager"

    # =========================================================================
    # Test: Workflow Engine Integration
    # =========================================================================
    def test_e2e_workflow_engine_approval_flow(self, workflow_engine):
        """
        E2E-APR-009: Complete workflow using oversight approval workflow.
        """
        # Create approval request
        request = workflow_engine.create_request(
            request_type=WorkflowApprovalType.DECISION,
            context={"action": "deploy", "environment": "production"},
            assigned_to=["approver1", "approver2"],
            requester="developer",
            priority=Priority.HIGH,
            timeout_seconds=3600
        )

        assert request.status == WorkflowApprovalStatus.PENDING
        assert request.priority == Priority.HIGH

        # Process approval
        result = workflow_engine.process_approval(
            request_id=request.id,
            decision=WorkflowApprovalDecision.APPROVED,
            approver_id="approver1",
            comments="Approved for deployment"
        )

        assert result.success is True
        assert result.decision == WorkflowApprovalDecision.APPROVED
        assert request.status == WorkflowApprovalStatus.APPROVED

    # =========================================================================
    # Test: Audit Trail Verification
    # =========================================================================
    def test_e2e_audit_trail_verification(self, approval_engine):
        """
        E2E-APR-010: Complete audit trail for approval workflow.
        """
        rule = ApprovalRule(
            id="audit-test-rule",
            name="Audit Test",
            description="Test",
            resource_pattern="audit/*",
            action_pattern="*",
            approval_type=ApprovalType.SINGLE,
            required_approvers=["auditor"]
        )
        approval_engine.add_rule(rule)

        # Create request - should trigger audit
        request = approval_engine.create_request(
            requester_id="user",
            resource="audit/item",
            action="do",
            rule=rule
        )

        initial_audit_count = len(approval_engine._audits)
        assert initial_audit_count >= 1

        # Approve - should trigger audit
        approval_engine.decide(request.id, "auditor", True)

        final_audit_count = len(approval_engine._audits)
        assert final_audit_count > initial_audit_count

        # Verify audit entries contain expected data
        audit_entries = [a for a in approval_engine._audits if a["request_id"] == request.id]
        assert len(audit_entries) >= 2

        # Verify status progression in audit
        statuses = [a["status"] for a in audit_entries]
        assert "pending" in statuses
        assert "approved" in statuses


class TestApprovalWorkflowSuspensionE2E:
    """E2E Tests for Workflow Suspension and Resumption"""

    @pytest.fixture
    def workflow_engine(self):
        """Create a fresh workflow engine."""
        ApprovalWorkflow._instance = None
        import maestro_hive.oversight.approval_workflow as module
        module._workflow_instance = None
        return ApprovalWorkflow()

    def test_e2e_workflow_suspension_and_resumption(self, workflow_engine):
        """
        E2E-APR-011: Suspend workflow pending approval, resume after.
        """
        callback_executed = {"value": False, "state": None}

        def resume_callback(approval_result, state):
            callback_executed["value"] = True
            callback_executed["state"] = state

        # Create approval request
        request = workflow_engine.create_request(
            request_type=WorkflowApprovalType.CRITICAL,
            context={"operation": "data-migration"},
            assigned_to=["dba", "architect"],
            requester="system"
        )

        # Suspend workflow
        workflow_engine.suspend_workflow(
            workflow_id=request.workflow_id,
            request_id=request.id,
            state={"step": 5, "progress": 50},
            resume_callback=resume_callback
        )

        # Approve request
        result = workflow_engine.process_approval(
            request_id=request.id,
            decision=WorkflowApprovalDecision.APPROVED,
            approver_id="dba",
            comments="Migration plan approved"
        )

        assert result.success is True
        assert result.workflow_resumed is True
        assert callback_executed["value"] is True
        assert callback_executed["state"]["step"] == 5

    def test_e2e_multiple_pending_approvals(self, workflow_engine):
        """
        E2E-APR-012: Handle multiple pending approvals.
        """
        # Create multiple requests
        requests = []
        for i in range(3):
            request = workflow_engine.create_request(
                request_type=WorkflowApprovalType.DECISION,
                context={"task": f"task-{i}"},
                assigned_to=["approver"],
                requester=f"user-{i}"
            )
            requests.append(request)

        # Get pending requests
        pending = workflow_engine.get_pending_requests()
        assert len(pending) >= 3

        # Approve first request
        workflow_engine.process_approval(
            request_id=requests[0].id,
            decision=WorkflowApprovalDecision.APPROVED,
            approver_id="approver"
        )

        # Verify pending count decreased
        pending = workflow_engine.get_pending_requests()
        assert len(pending) >= 2

        # Reject second request
        workflow_engine.process_approval(
            request_id=requests[1].id,
            decision=WorkflowApprovalDecision.REJECTED,
            approver_id="approver"
        )

        # Cancel third request
        workflow_engine.cancel_request(requests[2].id, "No longer needed")

        # Verify stats
        stats = workflow_engine.get_stats()
        assert stats["approved"] >= 1
        assert stats["rejected"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
