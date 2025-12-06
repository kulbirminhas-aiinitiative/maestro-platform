"""
Tests for tri_audit/deployment_gate.py (MD-2079, MD-2080)

Tests deployment gate functionality:
- Gate status checking
- Auto-block on SYSTEMIC_FAILURE
- Manual override handling
- CI/CD helper functions
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from tri_audit.deployment_gate import (
    GateStatus,
    BlockReason,
    DeploymentRequest,
    DeploymentGateResponse,
    ManualOverride,
    check_auto_block,
    get_blocking_reasons,
    check_manual_override,
    run_deployment_gate_check,
    check_can_deploy,
    get_blocking_summary,
    _manual_overrides
)

from tri_audit.tri_audit import TriModalVerdict, TriAuditResult


@pytest.fixture(autouse=True)
def clear_overrides():
    """Clear manual overrides before each test."""
    _manual_overrides.clear()
    yield
    _manual_overrides.clear()


class TestCheckAutoBlock:
    """Tests for auto-block functionality (MD-2080)."""

    def test_systemic_failure_triggers_auto_block(self):
        """SYSTEMIC_FAILURE should trigger auto-block."""
        assert check_auto_block(TriModalVerdict.SYSTEMIC_FAILURE) is True

    def test_all_pass_no_auto_block(self):
        """ALL_PASS should not trigger auto-block."""
        assert check_auto_block(TriModalVerdict.ALL_PASS) is False

    def test_design_gap_no_auto_block(self):
        """DESIGN_GAP should not trigger auto-block."""
        assert check_auto_block(TriModalVerdict.DESIGN_GAP) is False

    def test_architectural_erosion_no_auto_block(self):
        """ARCHITECTURAL_EROSION should not trigger auto-block."""
        assert check_auto_block(TriModalVerdict.ARCHITECTURAL_EROSION) is False

    def test_process_issue_no_auto_block(self):
        """PROCESS_ISSUE should not trigger auto-block."""
        assert check_auto_block(TriModalVerdict.PROCESS_ISSUE) is False

    def test_mixed_failure_no_auto_block(self):
        """MIXED_FAILURE should not trigger auto-block."""
        assert check_auto_block(TriModalVerdict.MIXED_FAILURE) is False

    def test_none_verdict_no_auto_block(self):
        """None verdict should not trigger auto-block."""
        assert check_auto_block(None) is False


class TestGetBlockingReasons:
    """Tests for blocking reason generation."""

    def test_all_pass_no_blocking_reasons(self):
        """All passing should have no blocking reasons."""
        reasons = get_blocking_reasons(True, True, True, TriModalVerdict.ALL_PASS)
        assert len(reasons) == 0

    def test_dde_failed_reason(self):
        """DDE failure should add reason."""
        reasons = get_blocking_reasons(False, True, True)
        assert any("DDE" in r for r in reasons)

    def test_bdv_failed_reason(self):
        """BDV failure should add reason."""
        reasons = get_blocking_reasons(True, False, True)
        assert any("BDV" in r for r in reasons)

    def test_acc_failed_reason(self):
        """ACC failure should add reason."""
        reasons = get_blocking_reasons(True, True, False)
        assert any("ACC" in r for r in reasons)

    def test_systemic_failure_adds_reason(self):
        """SYSTEMIC_FAILURE adds auto-block reason."""
        reasons = get_blocking_reasons(False, False, False, TriModalVerdict.SYSTEMIC_FAILURE)
        assert any("SYSTEMIC" in r and "auto-blocked" in r for r in reasons)

    def test_multiple_failures(self):
        """Multiple failures should have multiple reasons."""
        reasons = get_blocking_reasons(False, False, False)
        assert len(reasons) >= 3  # At least DDE, BDV, ACC


class TestManualOverride:
    """Tests for manual override functionality."""

    def test_no_override_returns_none(self):
        """No override should return None."""
        result = check_manual_override("iter-123")
        assert result is None

    def test_override_is_returned(self):
        """Set override should be returned."""
        _manual_overrides["iter-123"] = {
            "action": "approve",
            "reason": "Test",
            "approved_by": "test@test.com"
        }

        result = check_manual_override("iter-123")
        assert result is not None
        assert result["action"] == "approve"

    def test_expired_override_returns_none(self):
        """Expired override should return None."""
        past_time = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
        _manual_overrides["iter-123"] = {
            "action": "approve",
            "reason": "Test",
            "approved_by": "test@test.com",
            "expires_at": past_time
        }

        result = check_manual_override("iter-123")
        assert result is None
        assert "iter-123" not in _manual_overrides

    def test_non_expired_override_returns(self):
        """Non-expired override should be returned."""
        future_time = (datetime.utcnow() + timedelta(hours=1)).isoformat() + "Z"
        _manual_overrides["iter-123"] = {
            "action": "approve",
            "reason": "Test",
            "approved_by": "test@test.com",
            "expires_at": future_time
        }

        result = check_manual_override("iter-123")
        assert result is not None


class TestRunDeploymentGateCheck:
    """Tests for main deployment gate check."""

    @patch('tri_audit.deployment_gate.tri_modal_audit')
    @patch('tri_audit.deployment_gate.get_audit_result')
    @patch('tri_audit.deployment_gate.save_audit_result')
    def test_approved_deployment(self, mock_save, mock_get, mock_audit):
        """Test approved deployment."""
        mock_get.return_value = None
        mock_audit.return_value = TriAuditResult(
            iteration_id="iter-123",
            verdict=TriModalVerdict.ALL_PASS,
            timestamp=datetime.utcnow().isoformat() + "Z",
            dde_passed=True,
            bdv_passed=True,
            acc_passed=True,
            can_deploy=True,
            diagnosis="All pass",
            recommendations=[],
            dde_details={},
            bdv_details={},
            acc_details={}
        )

        request = DeploymentRequest(
            iteration_id="iter-123",
            project="test",
            version="1.0.0"
        )

        result = run_deployment_gate_check(request)

        assert result.approved is True
        assert result.gate_status == GateStatus.APPROVED
        assert result.dde_gate is True
        assert result.bdv_gate is True
        assert result.acc_gate is True

    @patch('tri_audit.deployment_gate.tri_modal_audit')
    @patch('tri_audit.deployment_gate.get_audit_result')
    @patch('tri_audit.deployment_gate.save_audit_result')
    def test_blocked_deployment(self, mock_save, mock_get, mock_audit):
        """Test blocked deployment."""
        mock_get.return_value = None
        mock_audit.return_value = TriAuditResult(
            iteration_id="iter-123",
            verdict=TriModalVerdict.DESIGN_GAP,
            timestamp=datetime.utcnow().isoformat() + "Z",
            dde_passed=True,
            bdv_passed=False,
            acc_passed=True,
            can_deploy=False,
            diagnosis="Design gap",
            recommendations=["Fix BDV"],
            dde_details={},
            bdv_details={},
            acc_details={}
        )

        request = DeploymentRequest(
            iteration_id="iter-123",
            project="test",
            version="1.0.0"
        )

        result = run_deployment_gate_check(request)

        assert result.approved is False
        assert result.gate_status == GateStatus.BLOCKED
        assert result.bdv_gate is False
        assert len(result.blocking_reasons) > 0

    @patch('tri_audit.deployment_gate.tri_modal_audit')
    @patch('tri_audit.deployment_gate.get_audit_result')
    @patch('tri_audit.deployment_gate.save_audit_result')
    def test_auto_blocked_systemic_failure(self, mock_save, mock_get, mock_audit):
        """Test auto-block on SYSTEMIC_FAILURE (MD-2080)."""
        mock_get.return_value = None
        mock_audit.return_value = TriAuditResult(
            iteration_id="iter-123",
            verdict=TriModalVerdict.SYSTEMIC_FAILURE,
            timestamp=datetime.utcnow().isoformat() + "Z",
            dde_passed=False,
            bdv_passed=False,
            acc_passed=False,
            can_deploy=False,
            diagnosis="Systemic failure",
            recommendations=["HALT"],
            dde_details={},
            bdv_details={},
            acc_details={}
        )

        request = DeploymentRequest(
            iteration_id="iter-123",
            project="test",
            version="1.0.0"
        )

        result = run_deployment_gate_check(request)

        assert result.approved is False
        assert result.gate_status == GateStatus.AUTO_BLOCKED
        assert result.auto_blocked is True

    def test_manual_override_approve(self):
        """Test manual override approves deployment."""
        _manual_overrides["iter-123"] = {
            "action": "approve",
            "reason": "Emergency hotfix",
            "approved_by": "admin@test.com"
        }

        request = DeploymentRequest(
            iteration_id="iter-123",
            project="test",
            version="1.0.0"
        )

        result = run_deployment_gate_check(request)

        assert result.approved is True
        assert result.gate_status == GateStatus.APPROVED
        assert "manual_override" in result.verdict

    def test_manual_override_block(self):
        """Test manual override blocks deployment."""
        _manual_overrides["iter-123"] = {
            "action": "block",
            "reason": "Security review needed",
            "approved_by": "security@test.com"
        }

        request = DeploymentRequest(
            iteration_id="iter-123",
            project="test",
            version="1.0.0"
        )

        result = run_deployment_gate_check(request)

        assert result.approved is False
        assert result.gate_status == GateStatus.BLOCKED


class TestCICDHelperFunctions:
    """Tests for CI/CD helper functions."""

    @patch('tri_audit.deployment_gate.tri_modal_audit')
    @patch('tri_audit.deployment_gate.get_audit_result')
    @patch('tri_audit.deployment_gate.save_audit_result')
    def test_check_can_deploy_true(self, mock_save, mock_get, mock_audit):
        """Test check_can_deploy returns True when approved."""
        mock_get.return_value = None
        mock_audit.return_value = TriAuditResult(
            iteration_id="iter-123",
            verdict=TriModalVerdict.ALL_PASS,
            timestamp=datetime.utcnow().isoformat() + "Z",
            dde_passed=True,
            bdv_passed=True,
            acc_passed=True,
            can_deploy=True,
            diagnosis="All pass",
            recommendations=[],
            dde_details={},
            bdv_details={},
            acc_details={}
        )

        result = check_can_deploy("iter-123", "test", "1.0.0")
        assert result is True

    @patch('tri_audit.deployment_gate.tri_modal_audit')
    @patch('tri_audit.deployment_gate.get_audit_result')
    @patch('tri_audit.deployment_gate.save_audit_result')
    def test_check_can_deploy_false(self, mock_save, mock_get, mock_audit):
        """Test check_can_deploy returns False when blocked."""
        mock_get.return_value = None
        mock_audit.return_value = TriAuditResult(
            iteration_id="iter-123",
            verdict=TriModalVerdict.SYSTEMIC_FAILURE,
            timestamp=datetime.utcnow().isoformat() + "Z",
            dde_passed=False,
            bdv_passed=False,
            acc_passed=False,
            can_deploy=False,
            diagnosis="Failure",
            recommendations=[],
            dde_details={},
            bdv_details={},
            acc_details={}
        )

        result = check_can_deploy("iter-123", "test", "1.0.0")
        assert result is False

    @patch('tri_audit.deployment_gate.tri_modal_audit')
    @patch('tri_audit.deployment_gate.get_audit_result')
    @patch('tri_audit.deployment_gate.save_audit_result')
    def test_get_blocking_summary_approved(self, mock_save, mock_get, mock_audit):
        """Test blocking summary for approved deployment."""
        mock_get.return_value = None
        mock_audit.return_value = TriAuditResult(
            iteration_id="iter-123",
            verdict=TriModalVerdict.ALL_PASS,
            timestamp=datetime.utcnow().isoformat() + "Z",
            dde_passed=True,
            bdv_passed=True,
            acc_passed=True,
            can_deploy=True,
            diagnosis="All pass",
            recommendations=[],
            dde_details={},
            bdv_details={},
            acc_details={}
        )

        summary = get_blocking_summary("iter-123")
        assert "APPROVED" in summary
        assert "✅" in summary

    @patch('tri_audit.deployment_gate.tri_modal_audit')
    @patch('tri_audit.deployment_gate.get_audit_result')
    @patch('tri_audit.deployment_gate.save_audit_result')
    def test_get_blocking_summary_blocked(self, mock_save, mock_get, mock_audit):
        """Test blocking summary for blocked deployment."""
        mock_get.return_value = None
        mock_audit.return_value = TriAuditResult(
            iteration_id="iter-123",
            verdict=TriModalVerdict.DESIGN_GAP,
            timestamp=datetime.utcnow().isoformat() + "Z",
            dde_passed=True,
            bdv_passed=False,
            acc_passed=True,
            can_deploy=False,
            diagnosis="Design gap detected",
            recommendations=["Review BDV scenarios"],
            dde_details={},
            bdv_details={},
            acc_details={}
        )

        summary = get_blocking_summary("iter-123")
        assert "BLOCKED" in summary
        assert "❌" in summary
        assert "Reasons:" in summary


class TestGateStatus:
    """Tests for GateStatus enum."""

    def test_all_statuses_exist(self):
        """All expected statuses should exist."""
        assert GateStatus.APPROVED.value == "APPROVED"
        assert GateStatus.BLOCKED.value == "BLOCKED"
        assert GateStatus.PENDING.value == "PENDING"
        assert GateStatus.AUTO_BLOCKED.value == "AUTO_BLOCKED"


class TestDeploymentRequest:
    """Tests for DeploymentRequest model."""

    def test_required_fields(self):
        """Test required fields validation."""
        request = DeploymentRequest(
            iteration_id="iter-123",
            project="test",
            version="1.0.0"
        )
        assert request.iteration_id == "iter-123"
        assert request.environment == "production"  # default

    def test_optional_fields(self):
        """Test optional fields."""
        request = DeploymentRequest(
            iteration_id="iter-123",
            project="test",
            version="1.0.0",
            commit_sha="abc123",
            environment="staging",
            force_check=True
        )
        assert request.commit_sha == "abc123"
        assert request.environment == "staging"
        assert request.force_check is True
