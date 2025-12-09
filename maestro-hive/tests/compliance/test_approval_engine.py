#!/usr/bin/env python3
"""Tests for approval_engine module."""

import pytest
import tempfile
from datetime import datetime, timedelta

from maestro_hive.compliance.approval_engine import (
    ApprovalEngine,
    ApprovalRequest,
    ApprovalType,
    ApprovalStatus,
    ApprovalDecision,
    get_approval_engine
)


class TestApprovalEngine:
    """Tests for ApprovalEngine class."""

    def test_engine_initialization(self):
        """Test engine initializes correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = ApprovalEngine(storage_dir=tmpdir)
            assert engine.storage_dir.exists()

    def test_create_single_approval_request(self):
        """Test creating single approval request."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = ApprovalEngine(storage_dir=tmpdir)

            request = engine.create_request(
                requester_id='user-1',
                resource='production-deploy',
                action='deploy',
                approval_type=ApprovalType.SINGLE,
                required_approvers=['manager-1']
            )

            assert request.requester_id == 'user-1'
            assert request.resource == 'production-deploy'
            assert request.approval_type == ApprovalType.SINGLE
            assert request.status == ApprovalStatus.PENDING

    def test_single_approval_workflow(self):
        """Test single approval workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = ApprovalEngine(storage_dir=tmpdir)

            # Create request
            request = engine.create_request(
                requester_id='dev-1',
                resource='feature-branch',
                action='merge',
                approval_type=ApprovalType.SINGLE,
                required_approvers=['lead-1', 'lead-2']
            )

            # Single approval should be enough
            decision = engine.approve(
                request_id=request.id,
                approver_id='lead-1',
                comment='LGTM'
            )

            assert decision.approved is True

            # Check request status
            updated = engine.get_request(request.id)
            assert updated.status == ApprovalStatus.APPROVED

    def test_all_approval_workflow(self):
        """Test approval requiring all approvers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = ApprovalEngine(storage_dir=tmpdir)

            request = engine.create_request(
                requester_id='user-1',
                resource='critical-change',
                action='execute',
                approval_type=ApprovalType.ALL,
                required_approvers=['approver-1', 'approver-2', 'approver-3']
            )

            # First approval - still pending
            engine.approve(request_id=request.id, approver_id='approver-1')
            assert engine.get_request(request.id).status == ApprovalStatus.PENDING

            # Second approval - still pending
            engine.approve(request_id=request.id, approver_id='approver-2')
            assert engine.get_request(request.id).status == ApprovalStatus.PENDING

            # Third approval - now approved
            engine.approve(request_id=request.id, approver_id='approver-3')
            assert engine.get_request(request.id).status == ApprovalStatus.APPROVED

    def test_majority_approval_workflow(self):
        """Test majority approval workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = ApprovalEngine(storage_dir=tmpdir)

            request = engine.create_request(
                requester_id='user-1',
                resource='policy-change',
                action='update',
                approval_type=ApprovalType.MAJORITY,
                required_approvers=['v1', 'v2', 'v3', 'v4', 'v5']  # 5 voters, need 3
            )

            # First two approvals - not majority yet
            engine.approve(request_id=request.id, approver_id='v1')
            engine.approve(request_id=request.id, approver_id='v2')
            assert engine.get_request(request.id).status == ApprovalStatus.PENDING

            # Third approval - majority reached
            engine.approve(request_id=request.id, approver_id='v3')
            assert engine.get_request(request.id).status == ApprovalStatus.APPROVED

    def test_sequential_approval_workflow(self):
        """Test sequential approval workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = ApprovalEngine(storage_dir=tmpdir)

            request = engine.create_request(
                requester_id='user-1',
                resource='expense-report',
                action='submit',
                approval_type=ApprovalType.SEQUENTIAL,
                required_approvers=['manager', 'finance', 'cfo']  # Must approve in order
            )

            # Wrong order should fail
            with pytest.raises(ValueError):
                engine.approve(request_id=request.id, approver_id='finance')

            # Correct order
            engine.approve(request_id=request.id, approver_id='manager')
            engine.approve(request_id=request.id, approver_id='finance')
            engine.approve(request_id=request.id, approver_id='cfo')

            assert engine.get_request(request.id).status == ApprovalStatus.APPROVED

    def test_rejection(self):
        """Test rejection of request."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = ApprovalEngine(storage_dir=tmpdir)

            request = engine.create_request(
                requester_id='user-1',
                resource='risky-change',
                action='deploy',
                approval_type=ApprovalType.SINGLE,
                required_approvers=['approver-1']
            )

            decision = engine.reject(
                request_id=request.id,
                approver_id='approver-1',
                reason='Too risky without testing'
            )

            assert decision.approved is False
            assert engine.get_request(request.id).status == ApprovalStatus.REJECTED

    def test_request_expiration(self):
        """Test request expiration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = ApprovalEngine(storage_dir=tmpdir)

            # Create request with short expiration
            request = engine.create_request(
                requester_id='user-1',
                resource='temp-access',
                action='grant',
                approval_type=ApprovalType.SINGLE,
                required_approvers=['approver-1'],
                expires_in_hours=0  # Immediate expiration for test
            )

            # Check if expired
            engine.check_expirations()
            updated = engine.get_request(request.id)
            assert updated.status == ApprovalStatus.EXPIRED

    def test_cancel_request(self):
        """Test cancelling a request."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = ApprovalEngine(storage_dir=tmpdir)

            request = engine.create_request(
                requester_id='user-1',
                resource='change',
                action='apply',
                approval_type=ApprovalType.SINGLE,
                required_approvers=['approver-1']
            )

            engine.cancel(request_id=request.id, cancelled_by='user-1')

            assert engine.get_request(request.id).status == ApprovalStatus.CANCELLED

    def test_unauthorized_approver(self):
        """Test unauthorized approver cannot approve."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = ApprovalEngine(storage_dir=tmpdir)

            request = engine.create_request(
                requester_id='user-1',
                resource='secure-resource',
                action='access',
                approval_type=ApprovalType.SINGLE,
                required_approvers=['authorized-approver']
            )

            # Unauthorized approver should fail
            with pytest.raises(ValueError):
                engine.approve(request_id=request.id, approver_id='unauthorized-user')

    def test_query_pending_requests(self):
        """Test querying pending requests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            engine = ApprovalEngine(storage_dir=tmpdir)

            # Create multiple requests
            engine.create_request(
                requester_id='user-1',
                resource='r1',
                action='a1',
                approval_type=ApprovalType.SINGLE,
                required_approvers=['approver-1']
            )
            engine.create_request(
                requester_id='user-2',
                resource='r2',
                action='a2',
                approval_type=ApprovalType.SINGLE,
                required_approvers=['approver-1']
            )

            pending = engine.query(status=ApprovalStatus.PENDING)
            assert len(pending) == 2

    def test_get_approval_engine_factory(self):
        """Test factory function."""
        engine = get_approval_engine()
        assert isinstance(engine, ApprovalEngine)


class TestApprovalRequest:
    """Tests for ApprovalRequest dataclass."""

    def test_request_creation(self):
        """Test request creation."""
        request = ApprovalRequest(
            id='REQ-001',
            requester_id='user-1',
            resource='document',
            action='publish',
            approval_type=ApprovalType.SINGLE,
            required_approvers=['approver-1'],
            status=ApprovalStatus.PENDING,
            created_at='2024-01-01T00:00:00',
            expires_at='2024-01-02T00:00:00'
        )
        assert request.id == 'REQ-001'
        assert request.status == ApprovalStatus.PENDING

    def test_request_to_dict(self):
        """Test request serialization."""
        request = ApprovalRequest(
            id='REQ-002',
            requester_id='user-1',
            resource='config',
            action='update',
            approval_type=ApprovalType.ALL,
            required_approvers=['a1', 'a2'],
            status=ApprovalStatus.PENDING,
            created_at='2024-01-01T00:00:00',
            expires_at='2024-01-02T00:00:00'
        )
        data = request.to_dict()
        assert data['id'] == 'REQ-002'
        assert data['approval_type'] == 'all'


class TestApprovalDecision:
    """Tests for ApprovalDecision dataclass."""

    def test_approved_decision(self):
        """Test approved decision."""
        decision = ApprovalDecision(
            request_id='REQ-001',
            approver_id='approver-1',
            approved=True,
            comment='Approved',
            timestamp='2024-01-01T00:00:00'
        )
        assert decision.approved is True

    def test_rejected_decision(self):
        """Test rejected decision."""
        decision = ApprovalDecision(
            request_id='REQ-001',
            approver_id='approver-1',
            approved=False,
            reason='Security concerns',
            timestamp='2024-01-01T00:00:00'
        )
        assert decision.approved is False
        assert 'Security' in decision.reason
