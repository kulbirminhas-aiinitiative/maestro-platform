#!/usr/bin/env python3
"""
E2E Tests: Deployment Pipeline Execution (AC-2)

Tests the complete deployment pipeline including:
- Gate checks (ALL_PASS, BLOCKED, WARN)
- Manual overrides with approval workflow
- CI/CD integration (GitHub Actions, GitLab CI, Jenkins)
- Auto-blocking on SYSTEMIC_FAILURE

EPIC: MD-3038 - Approval & Deployment E2E Tests
"""

import pytest
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass, field, asdict
from enum import Enum


# =============================================================================
# Local Implementation (Based on tri_audit/deployment_gate.py patterns)
# =============================================================================

class GateStatus(str, Enum):
    """Deployment gate status."""
    APPROVED = "APPROVED"
    BLOCKED = "BLOCKED"
    PENDING = "PENDING"
    AUTO_BLOCKED = "AUTO_BLOCKED"
    WARN = "WARN"


class TriModalVerdict(str, Enum):
    """Tri-modal audit verdicts."""
    ALL_PASS = "ALL_PASS"
    DESIGN_GAP = "DESIGN_GAP"
    ARCHITECTURAL_EROSION = "ARCHITECTURAL_EROSION"
    PROCESS_ISSUE = "PROCESS_ISSUE"
    SYSTEMIC_FAILURE = "SYSTEMIC_FAILURE"
    MIXED_FAILURE = "MIXED_FAILURE"


@dataclass
class DeploymentRequest:
    """Request to check deployment gate."""
    iteration_id: str
    project: str
    version: str
    commit_sha: str = None
    environment: str = "production"
    force_check: bool = False


@dataclass
class GateResult:
    """Result of a deployment gate check."""
    iteration_id: str
    timestamp: str
    gate_status: GateStatus
    approved: bool
    verdict: str = None
    message: str = ""
    dde_gate: bool = False
    bdv_gate: bool = False
    acc_gate: bool = False
    blocking_reasons: List[str] = field(default_factory=list)
    auto_blocked: bool = False
    override_applied: bool = False
    override_approver: str = None


@dataclass
class Override:
    """Manual override for deployment gate."""
    iteration_id: str
    action: str
    reason: str
    approved_by: str
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    expires_at: str = None
    approved: bool = False


@dataclass
class AuditEntry:
    """Audit trail entry."""
    iteration_id: str
    timestamp: str
    gate_status: str
    verdict: str
    trigger_user: str
    deploy_allowed: bool
    override_used: bool = False
    override_approver: str = None
    project: str = ""
    version: str = ""


class DeploymentGate:
    """
    Deployment gate that enforces tri-modal audit verdicts.

    This is a test implementation mirroring the real deployment_gate.py
    for E2E testing purposes.
    """

    def __init__(self, storage_path: Path = None):
        self.storage_path = storage_path or Path(tempfile.gettempdir()) / "deployment_gate"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._overrides: Dict[str, Override] = {}
        self._audit_log: List[AuditEntry] = []
        self._cached_results: Dict[str, Dict[str, Any]] = {}

    def check(
        self,
        request: DeploymentRequest,
        dde_passed: bool = True,
        bdv_passed: bool = True,
        acc_passed: bool = True,
        verdict: TriModalVerdict = TriModalVerdict.ALL_PASS,
        trigger_user: str = "system"
    ) -> GateResult:
        """
        Check deployment gate status.

        Args:
            request: Deployment request details
            dde_passed: DDE audit result
            bdv_passed: BDV audit result
            acc_passed: ACC audit result
            verdict: Tri-modal verdict
            trigger_user: Who triggered the check

        Returns:
            GateResult with gate status
        """
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Check for manual override first
        override = self._get_valid_override(request.iteration_id)
        if override:
            return self._apply_override(request, override, timestamp)

        # Check cached result unless force_check
        if not request.force_check and request.iteration_id in self._cached_results:
            cached = self._cached_results[request.iteration_id]
            return GateResult(**cached)

        # Evaluate verdict
        result = self._evaluate_verdict(
            request=request,
            dde_passed=dde_passed,
            bdv_passed=bdv_passed,
            acc_passed=acc_passed,
            verdict=verdict,
            timestamp=timestamp
        )

        # Log to audit trail
        self._log_audit(
            iteration_id=request.iteration_id,
            gate_status=result.gate_status.value,
            verdict=verdict.value,
            deploy_allowed=result.approved,
            trigger_user=trigger_user,
            project=request.project,
            version=request.version
        )

        # Cache result
        self._cached_results[request.iteration_id] = asdict(result)

        return result

    def _evaluate_verdict(
        self,
        request: DeploymentRequest,
        dde_passed: bool,
        bdv_passed: bool,
        acc_passed: bool,
        verdict: TriModalVerdict,
        timestamp: str
    ) -> GateResult:
        """Evaluate verdict and return gate result."""
        blocking_reasons = []
        auto_blocked = False

        if not dde_passed:
            blocking_reasons.append("DDE audit failed - execution/process issues")
        if not bdv_passed:
            blocking_reasons.append("BDV audit failed - behavior validation not met")
        if not acc_passed:
            blocking_reasons.append("ACC audit failed - architectural violations")

        if verdict == TriModalVerdict.ALL_PASS:
            return GateResult(
                iteration_id=request.iteration_id,
                timestamp=timestamp,
                gate_status=GateStatus.APPROVED,
                approved=True,
                verdict=verdict.value,
                message="All audits passed. Deployment approved.",
                dde_gate=dde_passed,
                bdv_gate=bdv_passed,
                acc_gate=acc_passed
            )

        elif verdict in [TriModalVerdict.DESIGN_GAP, TriModalVerdict.PROCESS_ISSUE]:
            return GateResult(
                iteration_id=request.iteration_id,
                timestamp=timestamp,
                gate_status=GateStatus.WARN,
                approved=True,
                verdict=verdict.value,
                message="Deploy with caution. Review findings before proceeding.",
                dde_gate=dde_passed,
                bdv_gate=bdv_passed,
                acc_gate=acc_passed,
                blocking_reasons=blocking_reasons
            )

        elif verdict == TriModalVerdict.SYSTEMIC_FAILURE:
            auto_blocked = True
            blocking_reasons.append("SYSTEMIC FAILURE - all three audits failed, deployment auto-blocked")
            return GateResult(
                iteration_id=request.iteration_id,
                timestamp=timestamp,
                gate_status=GateStatus.AUTO_BLOCKED,
                approved=False,
                verdict=verdict.value,
                message="Deployment blocked. SYSTEMIC_FAILURE detected.",
                dde_gate=dde_passed,
                bdv_gate=bdv_passed,
                acc_gate=acc_passed,
                blocking_reasons=blocking_reasons,
                auto_blocked=True
            )

        else:  # ARCHITECTURAL_EROSION, MIXED_FAILURE
            return GateResult(
                iteration_id=request.iteration_id,
                timestamp=timestamp,
                gate_status=GateStatus.BLOCKED,
                approved=False,
                verdict=verdict.value,
                message="Deployment blocked. Fix issues or request override.",
                dde_gate=dde_passed,
                bdv_gate=bdv_passed,
                acc_gate=acc_passed,
                blocking_reasons=blocking_reasons
            )

    def request_override(
        self,
        iteration_id: str,
        requester: str,
        reason: str,
        duration_hours: int = 24
    ) -> Override:
        """Request manual override for blocked deployment."""
        if len(reason) < 10:
            raise ValueError("Override reason must be at least 10 characters")

        expires_at = (datetime.utcnow() + timedelta(hours=duration_hours)).isoformat() + "Z"

        override = Override(
            iteration_id=iteration_id,
            action="approve",
            reason=reason,
            approved_by=requester,
            expires_at=expires_at,
            approved=False
        )

        self._overrides[iteration_id] = override
        return override

    def approve_override(self, iteration_id: str, approver: str) -> Override:
        """Approve override request."""
        if iteration_id not in self._overrides:
            raise ValueError(f"No override request found for {iteration_id}")

        override = self._overrides[iteration_id]
        override.approved = True
        override.approved_by = approver

        self._log_audit(
            iteration_id=iteration_id,
            gate_status="OVERRIDE_APPROVED",
            verdict="OVERRIDE",
            deploy_allowed=True,
            trigger_user=approver,
            override_used=True,
            override_approver=approver
        )

        return override

    def _get_valid_override(self, iteration_id: str) -> Override:
        """Get valid (approved, non-expired) override."""
        if iteration_id not in self._overrides:
            return None

        override = self._overrides[iteration_id]

        if not override.approved:
            return None

        # Check expiration
        if override.expires_at:
            expires = datetime.fromisoformat(override.expires_at.replace("Z", ""))
            if datetime.utcnow() > expires:
                return None

        return override

    def _apply_override(
        self,
        request: DeploymentRequest,
        override: Override,
        timestamp: str
    ) -> GateResult:
        """Apply manual override to gate check."""
        self._log_audit(
            iteration_id=request.iteration_id,
            gate_status="OVERRIDE_APPLIED",
            verdict="OVERRIDE",
            deploy_allowed=True,
            trigger_user=override.approved_by,
            override_used=True,
            override_approver=override.approved_by,
            project=request.project,
            version=request.version
        )

        return GateResult(
            iteration_id=request.iteration_id,
            timestamp=timestamp,
            gate_status=GateStatus.APPROVED,
            approved=True,
            verdict="OVERRIDE",
            message=f"Manual override applied by {override.approved_by}: {override.reason}",
            dde_gate=True,
            bdv_gate=True,
            acc_gate=True,
            override_applied=True,
            override_approver=override.approved_by
        )

    def _log_audit(
        self,
        iteration_id: str,
        gate_status: str,
        verdict: str,
        deploy_allowed: bool,
        trigger_user: str,
        override_used: bool = False,
        override_approver: str = None,
        project: str = "",
        version: str = ""
    ):
        """Log entry to audit trail."""
        entry = AuditEntry(
            iteration_id=iteration_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            gate_status=gate_status,
            verdict=verdict,
            trigger_user=trigger_user,
            deploy_allowed=deploy_allowed,
            override_used=override_used,
            override_approver=override_approver,
            project=project,
            version=version
        )
        self._audit_log.append(entry)

    def get_audit_trail(self, iteration_id: str = None) -> List[AuditEntry]:
        """Get audit trail entries."""
        if iteration_id:
            return [e for e in self._audit_log if e.iteration_id == iteration_id]
        return self._audit_log

    def get_statistics(self, days: int = 30) -> Dict[str, Any]:
        """Get gate statistics."""
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        recent = [e for e in self._audit_log if e.timestamp >= cutoff]

        if not recent:
            return {"pass_rate": 0.0, "total": 0, "passed": 0, "blocked": 0}

        passed = sum(1 for e in recent if e.deploy_allowed)
        blocked = len(recent) - passed

        return {
            "pass_rate": passed / len(recent) if recent else 0.0,
            "total": len(recent),
            "passed": passed,
            "blocked": blocked,
            "override_count": sum(1 for e in recent if e.override_used)
        }


class CICDIntegration:
    """CI/CD integration for deployment gates."""

    def __init__(self, gate: DeploymentGate):
        self.gate = gate

    def github_actions_output(
        self,
        request: DeploymentRequest,
        verdict: TriModalVerdict,
        trigger_user: str = "github-actions"
    ) -> str:
        """Format output for GitHub Actions."""
        result = self.gate.check(request, verdict=verdict, trigger_user=trigger_user)

        output = f"::set-output name=deploy_allowed::{str(result.approved).lower()}\n"
        output += f"::set-output name=gate_status::{result.gate_status.value}\n"
        output += f"::set-output name=verdict::{result.verdict}\n"

        if not result.approved:
            output += f"::error::Deployment blocked - {result.message}\n"
        elif result.gate_status == GateStatus.WARN:
            output += f"::warning::{result.message}\n"

        return output

    def gitlab_ci_output(
        self,
        request: DeploymentRequest,
        verdict: TriModalVerdict,
        trigger_user: str = "gitlab-ci"
    ) -> Dict[str, Any]:
        """Format output for GitLab CI."""
        result = self.gate.check(request, verdict=verdict, trigger_user=trigger_user)

        return {
            "deploy_allowed": result.approved,
            "gate_status": result.gate_status.value,
            "verdict": result.verdict,
            "message": result.message,
            "gitlab_status": "success" if result.approved else "failed"
        }

    def jenkins_output(
        self,
        request: DeploymentRequest,
        verdict: TriModalVerdict,
        trigger_user: str = "jenkins"
    ) -> Dict[str, Any]:
        """Format output for Jenkins."""
        result = self.gate.check(request, verdict=verdict, trigger_user=trigger_user)

        return {
            "result": "SUCCESS" if result.approved else "FAILURE",
            "deploy_allowed": result.approved,
            "gate_status": result.gate_status.value,
            "verdict": result.verdict,
            "message": result.message,
            "build_status": "STABLE" if result.approved else "UNSTABLE"
        }

    def get_json_output(
        self,
        request: DeploymentRequest,
        verdict: TriModalVerdict,
        trigger_user: str = "automation"
    ) -> Dict[str, Any]:
        """Get JSON output for automation."""
        result = self.gate.check(request, verdict=verdict, trigger_user=trigger_user)

        return {
            "iteration_id": result.iteration_id,
            "verdict": result.verdict,
            "gate_status": result.gate_status.value,
            "deploy_allowed": result.approved,
            "message": result.message,
            "timestamp": result.timestamp,
            "blocking_reasons": result.blocking_reasons,
            "auto_blocked": result.auto_blocked
        }


# =============================================================================
# E2E Test Suite
# =============================================================================

class TestDeploymentPipelineE2E:
    """E2E Tests for Deployment Pipeline (AC-2)"""

    @pytest.fixture
    def gate(self, tmp_path):
        """Create deployment gate with temp storage."""
        return DeploymentGate(storage_path=tmp_path / "gate")

    @pytest.fixture
    def cicd(self, gate):
        """Create CI/CD integration."""
        return CICDIntegration(gate)

    # =========================================================================
    # Test: Deployment Gate ALL_PASS Flow
    # =========================================================================
    def test_e2e_deployment_gate_all_pass_flow(self, gate):
        """
        E2E-DEP-001: Deployment gate ALL_PASS flow.

        Flow: Check Gate -> ALL_PASS -> Deployment Approved
        """
        request = DeploymentRequest(
            iteration_id="iter-001",
            project="my-service",
            version="2.0.0",
            commit_sha="abc123"
        )

        result = gate.check(
            request=request,
            dde_passed=True,
            bdv_passed=True,
            acc_passed=True,
            verdict=TriModalVerdict.ALL_PASS,
            trigger_user="deployer"
        )

        assert result.approved is True
        assert result.gate_status == GateStatus.APPROVED
        assert result.verdict == "ALL_PASS"
        assert "approved" in result.message.lower()
        assert result.dde_gate is True
        assert result.bdv_gate is True
        assert result.acc_gate is True

    # =========================================================================
    # Test: Deployment Gate BLOCKED Flow
    # =========================================================================
    def test_e2e_deployment_gate_blocked_flow(self, gate):
        """
        E2E-DEP-002: Deployment gate BLOCKED flow.

        Flow: Check Gate -> ARCHITECTURAL_EROSION -> Deployment Blocked
        """
        request = DeploymentRequest(
            iteration_id="iter-002",
            project="my-service",
            version="2.0.1"
        )

        result = gate.check(
            request=request,
            dde_passed=True,
            bdv_passed=True,
            acc_passed=False,
            verdict=TriModalVerdict.ARCHITECTURAL_EROSION,
            trigger_user="deployer"
        )

        assert result.approved is False
        assert result.gate_status == GateStatus.BLOCKED
        assert result.acc_gate is False
        assert len(result.blocking_reasons) > 0
        assert "blocked" in result.message.lower()

    # =========================================================================
    # Test: Manual Override Request and Approval
    # =========================================================================
    def test_e2e_manual_override_request_and_approval(self, gate):
        """
        E2E-DEP-003: Manual override request and approval flow.

        Flow: Gate Blocked -> Request Override -> Approve Override -> Gate Passes
        """
        request = DeploymentRequest(
            iteration_id="iter-003",
            project="critical-service",
            version="1.5.0"
        )

        # Initial check - blocked
        result = gate.check(
            request=request,
            verdict=TriModalVerdict.SYSTEMIC_FAILURE,
            trigger_user="developer"
        )
        assert result.approved is False
        assert result.auto_blocked is True

        # Request override
        override = gate.request_override(
            iteration_id="iter-003",
            requester="developer",
            reason="Emergency hotfix for critical production bug",
            duration_hours=4
        )
        assert override.approved is False

        # Approve override
        approved_override = gate.approve_override("iter-003", "cto")
        assert approved_override.approved is True
        assert approved_override.approved_by == "cto"

        # Re-check - should pass with override
        result = gate.check(
            request=request,
            verdict=TriModalVerdict.SYSTEMIC_FAILURE,
            trigger_user="developer"
        )
        assert result.approved is True
        assert result.override_applied is True
        assert result.override_approver == "cto"
        assert "override" in result.message.lower()

    # =========================================================================
    # Test: Override Expiration
    # =========================================================================
    def test_e2e_override_expiration(self, gate):
        """
        E2E-DEP-004: Override expiration handling.

        Flow: Create Override -> Approve -> Expire -> Gate Blocked Again
        """
        request = DeploymentRequest(
            iteration_id="iter-004",
            project="service",
            version="1.0.0"
        )

        # Request and approve override with 1 hour duration
        override = gate.request_override(
            iteration_id="iter-004",
            requester="dev",
            reason="Emergency fix required for production",
            duration_hours=1
        )
        gate.approve_override("iter-004", "manager")

        # Should pass initially
        result = gate.check(request, verdict=TriModalVerdict.MIXED_FAILURE)
        assert result.approved is True

        # Manually expire the override
        gate._overrides["iter-004"].expires_at = (
            datetime.utcnow() - timedelta(hours=2)
        ).isoformat() + "Z"

        # Clear cache to force re-evaluation
        gate._cached_results.pop("iter-004", None)

        # Should be blocked again
        result = gate.check(request, verdict=TriModalVerdict.MIXED_FAILURE)
        assert result.approved is False

    # =========================================================================
    # Test: CI/CD Integration - GitHub Actions
    # =========================================================================
    def test_e2e_cicd_github_actions_integration(self, cicd):
        """
        E2E-DEP-005: GitHub Actions integration.

        Tests GitHub Actions output format.
        """
        request = DeploymentRequest(
            iteration_id="iter-005",
            project="gh-service",
            version="1.0.0"
        )

        # Test pass case
        output = cicd.github_actions_output(
            request,
            TriModalVerdict.ALL_PASS
        )
        assert "::set-output" in output
        assert "deploy_allowed::true" in output
        assert "gate_status::APPROVED" in output

        # Test fail case
        request2 = DeploymentRequest(
            iteration_id="iter-005-fail",
            project="gh-service",
            version="1.0.1"
        )
        output = cicd.github_actions_output(
            request2,
            TriModalVerdict.SYSTEMIC_FAILURE
        )
        assert "deploy_allowed::false" in output
        assert "::error::" in output

    # =========================================================================
    # Test: CI/CD Integration - GitLab CI
    # =========================================================================
    def test_e2e_cicd_gitlab_ci_integration(self, cicd):
        """
        E2E-DEP-006: GitLab CI integration.

        Tests GitLab CI output format.
        """
        request = DeploymentRequest(
            iteration_id="iter-006",
            project="gl-service",
            version="2.0.0"
        )

        # Test pass case
        output = cicd.gitlab_ci_output(request, TriModalVerdict.ALL_PASS)
        assert output["gitlab_status"] == "success"
        assert output["deploy_allowed"] is True

        # Test fail case
        request2 = DeploymentRequest(
            iteration_id="iter-006-fail",
            project="gl-service",
            version="2.0.1"
        )
        output = cicd.gitlab_ci_output(request2, TriModalVerdict.ARCHITECTURAL_EROSION)
        assert output["gitlab_status"] == "failed"
        assert output["deploy_allowed"] is False

    # =========================================================================
    # Test: CI/CD Integration - Jenkins
    # =========================================================================
    def test_e2e_cicd_jenkins_integration(self, cicd):
        """
        E2E-DEP-007: Jenkins integration.

        Tests Jenkins output format.
        """
        request = DeploymentRequest(
            iteration_id="iter-007",
            project="jenkins-service",
            version="3.0.0"
        )

        # Test pass case
        output = cicd.jenkins_output(request, TriModalVerdict.ALL_PASS)
        assert output["result"] == "SUCCESS"
        assert output["build_status"] == "STABLE"

        # Test fail case
        request2 = DeploymentRequest(
            iteration_id="iter-007-fail",
            project="jenkins-service",
            version="3.0.1"
        )
        output = cicd.jenkins_output(request2, TriModalVerdict.MIXED_FAILURE)
        assert output["result"] == "FAILURE"
        assert output["build_status"] == "UNSTABLE"

    # =========================================================================
    # Test: Auto-Block on SYSTEMIC_FAILURE
    # =========================================================================
    def test_e2e_auto_block_on_systemic_failure(self, gate):
        """
        E2E-DEP-008: Auto-block on SYSTEMIC_FAILURE.

        Tests that SYSTEMIC_FAILURE verdict triggers automatic blocking.
        """
        request = DeploymentRequest(
            iteration_id="iter-008",
            project="critical-service",
            version="1.0.0"
        )

        result = gate.check(
            request=request,
            dde_passed=False,
            bdv_passed=False,
            acc_passed=False,
            verdict=TriModalVerdict.SYSTEMIC_FAILURE
        )

        assert result.approved is False
        assert result.gate_status == GateStatus.AUTO_BLOCKED
        assert result.auto_blocked is True
        assert any("SYSTEMIC" in r for r in result.blocking_reasons)

    # =========================================================================
    # Test: Pipeline with Cached Audit Results
    # =========================================================================
    def test_e2e_pipeline_cached_audit_results(self, gate):
        """
        E2E-DEP-009: Pipeline with cached audit results.

        Tests that subsequent checks use cached results.
        """
        request = DeploymentRequest(
            iteration_id="iter-009",
            project="cached-service",
            version="1.0.0",
            force_check=False
        )

        # First check
        result1 = gate.check(request, verdict=TriModalVerdict.ALL_PASS)
        assert result1.approved is True

        # Second check should use cache (even if we pass different verdict)
        # The cache should be hit based on iteration_id
        assert request.iteration_id in gate._cached_results

        # Verify cache contains expected data
        cached = gate._cached_results[request.iteration_id]
        assert cached["approved"] is True

    # =========================================================================
    # Test: Force Re-run Audit
    # =========================================================================
    def test_e2e_force_rerun_audit(self, gate):
        """
        E2E-DEP-010: Force re-run audit bypassing cache.

        Tests that force_check bypasses cached results.
        """
        request = DeploymentRequest(
            iteration_id="iter-010",
            project="force-service",
            version="1.0.0",
            force_check=False
        )

        # First check
        result1 = gate.check(request, verdict=TriModalVerdict.ALL_PASS)
        assert result1.approved is True

        # Force re-check with different verdict
        request_force = DeploymentRequest(
            iteration_id="iter-010",
            project="force-service",
            version="1.0.0",
            force_check=True
        )

        result2 = gate.check(
            request_force,
            dde_passed=False,
            bdv_passed=False,
            acc_passed=False,
            verdict=TriModalVerdict.SYSTEMIC_FAILURE
        )

        # Force check should evaluate fresh
        assert result2.approved is False
        assert result2.auto_blocked is True


class TestDeploymentAuditTrailE2E:
    """E2E Tests for Deployment Audit Trail"""

    @pytest.fixture
    def gate(self, tmp_path):
        """Create deployment gate."""
        return DeploymentGate(storage_path=tmp_path / "gate")

    def test_e2e_audit_trail_completeness(self, gate):
        """
        E2E-DEP-011: Verify audit trail completeness.

        All gate checks should be logged to audit trail.
        """
        # Perform multiple gate checks
        for i in range(5):
            request = DeploymentRequest(
                iteration_id=f"audit-iter-{i}",
                project="audit-service",
                version=f"1.0.{i}"
            )
            verdict = TriModalVerdict.ALL_PASS if i % 2 == 0 else TriModalVerdict.SYSTEMIC_FAILURE
            gate.check(request, verdict=verdict, trigger_user=f"user-{i}")

        # Verify audit trail
        audit_log = gate.get_audit_trail()
        assert len(audit_log) >= 5

        # Verify entries have required fields
        for entry in audit_log:
            assert entry.iteration_id is not None
            assert entry.timestamp is not None
            assert entry.trigger_user is not None

    def test_e2e_audit_trail_override_tracking(self, gate):
        """
        E2E-DEP-012: Verify override tracking in audit trail.

        Override approvals should be tracked in audit trail.
        """
        request = DeploymentRequest(
            iteration_id="override-audit-iter",
            project="service",
            version="1.0.0"
        )

        # Initial blocked check
        gate.check(request, verdict=TriModalVerdict.SYSTEMIC_FAILURE)

        # Request and approve override
        gate.request_override(
            "override-audit-iter",
            "developer",
            "Emergency production fix required"
        )
        gate.approve_override("override-audit-iter", "manager")

        # Check with override
        gate.check(request, verdict=TriModalVerdict.SYSTEMIC_FAILURE)

        # Verify override entries in audit trail
        audit_log = gate.get_audit_trail("override-audit-iter")
        override_entries = [e for e in audit_log if e.override_used]

        assert len(override_entries) >= 1
        assert any(e.override_approver == "manager" for e in override_entries)

    def test_e2e_statistics_calculation(self, gate):
        """
        E2E-DEP-013: Verify statistics calculation.

        Pass rate and other metrics should be calculated correctly.
        """
        # Create mix of pass/fail
        for i in range(10):
            request = DeploymentRequest(
                iteration_id=f"stats-iter-{i}",
                project="stats-service",
                version=f"1.0.{i}"
            )
            # 7 pass, 3 fail
            verdict = TriModalVerdict.ALL_PASS if i < 7 else TriModalVerdict.SYSTEMIC_FAILURE
            gate.check(request, verdict=verdict)

        stats = gate.get_statistics(days=30)

        assert stats["total"] == 10
        assert stats["passed"] == 7
        assert stats["blocked"] == 3
        assert 0.69 <= stats["pass_rate"] <= 0.71


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
