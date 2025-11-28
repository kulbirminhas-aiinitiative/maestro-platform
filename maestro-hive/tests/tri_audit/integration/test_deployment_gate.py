"""
Tri-Modal Test Suite: Deployment Gate Tests (TRI-301 to TRI-320)
Test Count: 20 test cases

Tests deployment gate enforcement, override handling, CI/CD integration,
and audit trail for the tri-modal audit system.

This is the CRITICAL deployment protection layer that ensures only
validated code reaches production.
"""

import pytest
import json
import time
import subprocess
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, List, Optional
from pathlib import Path
import tempfile
import os


# ============================================================================
# Core Data Models
# ============================================================================

class GateStatus(str, Enum):
    """Deployment gate status"""
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    PENDING = "PENDING"


class TriModalVerdict(str, Enum):
    """Tri-modal audit verdicts"""
    ALL_PASS = "ALL_PASS"
    DESIGN_GAP = "DESIGN_GAP"
    ARCHITECTURAL_EROSION = "ARCHITECTURAL_EROSION"
    PROCESS_ISSUE = "PROCESS_ISSUE"
    SYSTEMIC_FAILURE = "SYSTEMIC_FAILURE"
    MIXED_FAILURE = "MIXED_FAILURE"


@dataclass
class GateResult:
    """Result of a deployment gate check"""
    status: GateStatus
    deploy_allowed: bool
    message: str = ""
    verdict: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OverrideRequest:
    """Request to override a gate decision"""
    iteration_id: str
    requester: str
    justification: str
    verdict: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    approved: bool = False
    approver: Optional[str] = None
    expiration: Optional[str] = None


@dataclass
class GateAuditEntry:
    """Audit trail entry for gate check"""
    iteration_id: str
    timestamp: str
    gate_status: GateStatus
    verdict: str
    deploy_allowed: bool
    trigger_user: str
    override_used: bool = False
    override_approver: Optional[str] = None
    ci_cd_system: Optional[str] = None
    project: str = ""
    version: str = ""
    commit_sha: Optional[str] = None


# ============================================================================
# Deployment Gate Implementation
# ============================================================================

class DeploymentGate:
    """
    Deployment gate that enforces tri-modal audit verdicts.

    Only ALL_PASS verdicts allow deployment to production.
    All other verdicts require override approval.
    """

    def __init__(self, audit_logger=None, override_manager=None):
        self.audit_logger = audit_logger or GateAuditLogger()
        self.override_manager = override_manager or OverrideManager()

    def check(self, verdict: str, iteration_id: str = "test-iter",
              trigger_user: str = "system", project: str = "test-project",
              version: str = "1.0.0", commit_sha: Optional[str] = None) -> GateResult:
        """
        Check if deployment is allowed based on verdict.

        Logic:
        - ALL_PASS: Deploy allowed
        - DESIGN_GAP, PROCESS_ISSUE: Warning, deploy with caution
        - ARCHITECTURAL_EROSION, SYSTEMIC_FAILURE, MIXED_FAILURE: Deploy blocked
        """
        result = self._evaluate_verdict(verdict)
        result.verdict = verdict

        # Log to audit trail
        self.audit_logger.log_gate_check(
            iteration_id=iteration_id,
            gate_status=result.status,
            verdict=verdict,
            deploy_allowed=result.deploy_allowed,
            trigger_user=trigger_user,
            project=project,
            version=version,
            commit_sha=commit_sha
        )

        return result

    def _evaluate_verdict(self, verdict: str) -> GateResult:
        """Evaluate verdict and return gate result"""
        if verdict == TriModalVerdict.ALL_PASS.value:
            return GateResult(
                status=GateStatus.PASS,
                deploy_allowed=True,
                message="All audits passed. Deployment approved."
            )

        elif verdict in [TriModalVerdict.DESIGN_GAP.value,
                         TriModalVerdict.PROCESS_ISSUE.value]:
            return GateResult(
                status=GateStatus.WARN,
                deploy_allowed=True,
                message="Deploy with caution. Review findings before proceeding."
            )

        else:  # ARCHITECTURAL_EROSION, SYSTEMIC_FAILURE, MIXED_FAILURE
            return GateResult(
                status=GateStatus.FAIL,
                deploy_allowed=False,
                message="Deployment blocked. Fix issues or request override."
            )

    def check_with_override(self, verdict: str, iteration_id: str,
                           trigger_user: str = "system") -> GateResult:
        """Check gate with override support"""
        result = self.check(verdict, iteration_id, trigger_user)

        # Check if override exists and is valid
        if not result.deploy_allowed:
            override = self.override_manager.get_override(iteration_id)
            if override and override.approved and not self._is_expired(override):
                result.deploy_allowed = True
                result.status = GateStatus.PASS
                result.message += f" [OVERRIDE APPLIED by {override.approver}]"
                result.details["override"] = {
                    "approver": override.approver,
                    "justification": override.justification,
                    "timestamp": override.timestamp
                }

                # Log override usage
                self.audit_logger.log_override_usage(
                    iteration_id=iteration_id,
                    override_approver=override.approver,
                    trigger_user=trigger_user
                )

        return result

    def _is_expired(self, override: OverrideRequest) -> bool:
        """Check if override has expired"""
        if not override.expiration:
            return False

        expiration_time = datetime.fromisoformat(override.expiration.replace("Z", ""))
        return datetime.utcnow() > expiration_time

    def enforce(self, verdict: str, iteration_id: str = "test-iter") -> None:
        """
        Enforce gate decision - raises exception if deployment blocked.

        This is the final enforcement point before deployment.
        """
        result = self.check_with_override(verdict, iteration_id)

        if not result.deploy_allowed:
            raise DeploymentBlockedException(
                f"Deployment blocked: {result.message}\n"
                f"Verdict: {verdict}\n"
                f"Status: {result.status.value}"
            )


class DeploymentBlockedException(Exception):
    """Raised when deployment is blocked by gate"""
    pass


# ============================================================================
# Override Manager
# ============================================================================

class OverrideManager:
    """Manages deployment gate overrides with approval workflow"""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path(tempfile.gettempdir()) / "gate_overrides"
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.notification_callbacks: List[callable] = []

    def request_override(self, iteration_id: str, requester: str,
                        justification: str, verdict: str,
                        duration_hours: int = 24) -> OverrideRequest:
        """Request override for non-PASS verdict"""
        if not justification or len(justification) < 10:
            raise ValueError("Override justification must be at least 10 characters")

        expiration = (datetime.utcnow() + timedelta(hours=duration_hours)).isoformat() + "Z"

        override = OverrideRequest(
            iteration_id=iteration_id,
            requester=requester,
            justification=justification,
            verdict=verdict,
            approved=False,
            expiration=expiration
        )

        self._save_override(override)
        return override

    def approve_override(self, iteration_id: str, approver: str) -> OverrideRequest:
        """Approve override request"""
        override = self.get_override(iteration_id)
        if not override:
            raise ValueError(f"No override found for iteration {iteration_id}")

        override.approved = True
        override.approver = approver
        self._save_override(override)

        # Send notifications
        self._notify_override_approved(override)

        return override

    def get_override(self, iteration_id: str) -> Optional[OverrideRequest]:
        """Get override for iteration"""
        override_file = self.storage_path / f"{iteration_id}.json"
        if not override_file.exists():
            return None

        with open(override_file) as f:
            data = json.load(f)

        return OverrideRequest(**data)

    def _save_override(self, override: OverrideRequest):
        """Save override to storage"""
        override_file = self.storage_path / f"{override.iteration_id}.json"
        with open(override_file, "w") as f:
            json.dump(asdict(override), f, indent=2)

    def add_notification_callback(self, callback: callable):
        """Add notification callback for override events"""
        self.notification_callbacks.append(callback)

    def _notify_override_approved(self, override: OverrideRequest):
        """Send notifications for approved override"""
        for callback in self.notification_callbacks:
            try:
                callback(override)
            except Exception as e:
                print(f"Notification callback failed: {e}")


# ============================================================================
# Gate Audit Logger
# ============================================================================

class GateAuditLogger:
    """Logs all gate checks and overrides for audit trail"""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or Path(tempfile.gettempdir()) / "gate_audit_logs"
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def log_gate_check(self, iteration_id: str, gate_status: GateStatus,
                      verdict: str, deploy_allowed: bool, trigger_user: str,
                      project: str = "", version: str = "",
                      commit_sha: Optional[str] = None,
                      ci_cd_system: Optional[str] = None):
        """Log gate check to audit trail"""
        entry = GateAuditEntry(
            iteration_id=iteration_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            gate_status=gate_status,
            verdict=verdict,
            deploy_allowed=deploy_allowed,
            trigger_user=trigger_user,
            project=project,
            version=version,
            commit_sha=commit_sha,
            ci_cd_system=ci_cd_system
        )

        self._save_entry(entry)

    def log_override_usage(self, iteration_id: str, override_approver: str,
                          trigger_user: str):
        """Log override usage"""
        entry = GateAuditEntry(
            iteration_id=iteration_id,
            timestamp=datetime.utcnow().isoformat() + "Z",
            gate_status=GateStatus.PASS,
            verdict="OVERRIDE",
            deploy_allowed=True,
            trigger_user=trigger_user,
            override_used=True,
            override_approver=override_approver
        )

        self._save_entry(entry)

    def get_audit_trail(self, iteration_id: Optional[str] = None) -> List[GateAuditEntry]:
        """Get audit trail entries"""
        entries = []

        for entry_file in sorted(self.storage_path.glob("*.json")):
            with open(entry_file) as f:
                data = json.load(f)

            entry = GateAuditEntry(**data)

            if iteration_id is None or entry.iteration_id == iteration_id:
                entries.append(entry)

        return sorted(entries, key=lambda e: e.timestamp)

    def get_pass_rate(self, days: int = 30) -> float:
        """Calculate gate pass rate over time"""
        entries = self.get_audit_trail()
        if not entries:
            return 0.0

        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        recent_entries = [e for e in entries if e.timestamp >= cutoff]

        if not recent_entries:
            return 0.0

        passed = sum(1 for e in recent_entries if e.deploy_allowed)
        return passed / len(recent_entries)

    def get_override_count(self, days: int = 30) -> int:
        """Get number of overrides used in time period"""
        entries = self.get_audit_trail()
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        return sum(1 for e in entries
                  if e.timestamp >= cutoff and e.override_used)

    def _save_entry(self, entry: GateAuditEntry):
        """Save audit entry"""
        timestamp_safe = entry.timestamp.replace(":", "-").replace("Z", "")
        entry_file = self.storage_path / f"{entry.iteration_id}_{timestamp_safe}.json"

        with open(entry_file, "w") as f:
            json.dump(asdict(entry), f, indent=2)


# ============================================================================
# CI/CD Integration
# ============================================================================

class CICDIntegration:
    """CI/CD integration for deployment gates"""

    def __init__(self, gate: DeploymentGate):
        self.gate = gate

    def check_gate_exit_code(self, verdict: str, iteration_id: str) -> int:
        """Return exit code for CI/CD: 0 = pass, 1 = fail"""
        try:
            self.gate.enforce(verdict, iteration_id)
            return 0
        except DeploymentBlockedException:
            return 1

    def get_json_output(self, verdict: str, iteration_id: str) -> Dict[str, Any]:
        """Get JSON output for CI/CD automation"""
        result = self.gate.check_with_override(verdict, iteration_id)

        return {
            "iteration_id": iteration_id,
            "verdict": verdict,
            "gate_status": result.status.value,
            "deploy_allowed": result.deploy_allowed,
            "message": result.message,
            "timestamp": result.timestamp,
            "details": result.details
        }

    def github_actions_output(self, verdict: str, iteration_id: str) -> str:
        """Format output for GitHub Actions"""
        result = self.gate.check_with_override(verdict, iteration_id)

        # GitHub Actions output format
        output = f"::set-output name=deploy_allowed::{str(result.deploy_allowed).lower()}\n"
        output += f"::set-output name=gate_status::{result.status.value}\n"
        output += f"::set-output name=verdict::{verdict}\n"

        if not result.deploy_allowed:
            output += f"::error::Deployment blocked - {result.message}\n"
        elif result.status == GateStatus.WARN:
            output += f"::warning::{result.message}\n"

        return output

    def gitlab_ci_output(self, verdict: str, iteration_id: str) -> Dict[str, Any]:
        """Format output for GitLab CI"""
        result = self.gate.check_with_override(verdict, iteration_id)

        return {
            "deploy_allowed": result.deploy_allowed,
            "gate_status": result.status.value,
            "verdict": verdict,
            "message": result.message,
            "gitlab_status": "success" if result.deploy_allowed else "failed"
        }

    def jenkins_output(self, verdict: str, iteration_id: str) -> Dict[str, Any]:
        """Format output for Jenkins"""
        result = self.gate.check_with_override(verdict, iteration_id)

        return {
            "result": "SUCCESS" if result.deploy_allowed else "FAILURE",
            "deploy_allowed": result.deploy_allowed,
            "gate_status": result.status.value,
            "verdict": verdict,
            "message": result.message,
            "build_status": "STABLE" if result.deploy_allowed else "UNSTABLE"
        }


# ============================================================================
# CLI Tool
# ============================================================================

class GateCLI:
    """Command-line interface for deployment gate"""

    def __init__(self, gate: DeploymentGate):
        self.gate = gate

    def check(self, verdict: str, iteration_id: str, json_output: bool = False) -> int:
        """
        Check deployment gate from CLI

        Returns exit code: 0 = pass, 1 = fail
        """
        try:
            result = self.gate.check_with_override(verdict, iteration_id)

            if json_output:
                output = {
                    "status": result.status.value,
                    "deploy_allowed": result.deploy_allowed,
                    "message": result.message,
                    "verdict": verdict
                }
                print(json.dumps(output, indent=2))
            else:
                print(f"Gate Status: {result.status.value}")
                print(f"Deploy Allowed: {result.deploy_allowed}")
                print(f"Message: {result.message}")

            return 0 if result.deploy_allowed else 1

        except Exception as e:
            if json_output:
                print(json.dumps({"error": str(e)}, indent=2))
            else:
                print(f"Error: {e}")
            return 1


# ============================================================================
# Test Suite: Gate Enforcement (TRI-301 to TRI-305)
# ============================================================================

@pytest.mark.integration
@pytest.mark.tri_audit
class TestGateEnforcement:
    """Test Suite: Deployment Gate Enforcement"""

    def test_tri_301_all_pass_allows_deployment(self):
        """TRI-301: Only ALL_PASS verdict allows deployment"""
        gate = DeploymentGate()
        result = gate.check(TriModalVerdict.ALL_PASS.value, "test-iter-301")

        assert result.status == GateStatus.PASS
        assert result.deploy_allowed is True
        assert "approved" in result.message.lower()

    def test_tri_302_fail_verdicts_block_deployment(self):
        """TRI-302: FAIL verdicts block deployment (raise exception)"""
        gate = DeploymentGate()

        # Test verdicts that should block
        blocking_verdicts = [
            TriModalVerdict.SYSTEMIC_FAILURE.value,
            TriModalVerdict.ARCHITECTURAL_EROSION.value,
            TriModalVerdict.MIXED_FAILURE.value
        ]

        for verdict in blocking_verdicts:
            with pytest.raises(DeploymentBlockedException):
                gate.enforce(verdict, f"test-iter-302-{verdict}")

    def test_tri_303_warn_verdicts_allow_with_warning(self):
        """TRI-303: WARN verdicts allow deployment with warning"""
        gate = DeploymentGate()

        # DESIGN_GAP and PROCESS_ISSUE are warnings
        warn_verdicts = [
            TriModalVerdict.DESIGN_GAP.value,
            TriModalVerdict.PROCESS_ISSUE.value
        ]

        for verdict in warn_verdicts:
            result = gate.check(verdict, f"test-iter-303-{verdict}")
            assert result.status == GateStatus.WARN
            assert result.deploy_allowed is True
            assert "caution" in result.message.lower()

    def test_tri_304_gate_status_values(self):
        """TRI-304: Gate status: PASS, FAIL, WARN"""
        gate = DeploymentGate()

        # Test all status types
        test_cases = [
            (TriModalVerdict.ALL_PASS.value, GateStatus.PASS),
            (TriModalVerdict.DESIGN_GAP.value, GateStatus.WARN),
            (TriModalVerdict.SYSTEMIC_FAILURE.value, GateStatus.FAIL)
        ]

        for verdict, expected_status in test_cases:
            result = gate.check(verdict, f"test-iter-304-{verdict}")
            assert result.status == expected_status

    def test_tri_305_gate_execution_logs_audit_trail(self):
        """TRI-305: Gate execution logs and audit trail"""
        # Use unique storage for this test
        import tempfile
        test_storage = Path(tempfile.mkdtemp()) / "gate_audit_logs_305"
        logger = GateAuditLogger(storage_path=test_storage)
        gate = DeploymentGate(audit_logger=logger)

        # Execute gate check
        gate.check(
            TriModalVerdict.ALL_PASS.value,
            iteration_id="test-iter-305",
            trigger_user="test-user",
            project="test-project",
            version="1.0.0"
        )

        # Verify audit trail
        entries = logger.get_audit_trail("test-iter-305")
        assert len(entries) == 1, f"Expected 1 entry, got {len(entries)}"
        assert entries[0].iteration_id == "test-iter-305"
        assert entries[0].trigger_user == "test-user"
        assert entries[0].verdict == TriModalVerdict.ALL_PASS.value


# ============================================================================
# Test Suite: Override Handling (TRI-306 to TRI-310)
# ============================================================================

@pytest.mark.integration
@pytest.mark.tri_audit
class TestOverrideHandling:
    """Test Suite: Override Handling"""

    def test_tri_306_manual_override_for_non_pass(self):
        """TRI-306: Manual override for non-PASS verdicts"""
        # Use unique storage for this test
        import tempfile
        override_storage = Path(tempfile.mkdtemp()) / "gate_overrides_306"
        manager = OverrideManager(storage_path=override_storage)
        gate = DeploymentGate(override_manager=manager)

        # Initially blocked
        with pytest.raises(DeploymentBlockedException):
            gate.enforce(TriModalVerdict.SYSTEMIC_FAILURE.value, "test-iter-306")

        # Request and approve override
        manager.request_override(
            "test-iter-306",
            "dev-user",
            "Emergency hotfix required for production issue",
            TriModalVerdict.SYSTEMIC_FAILURE.value
        )
        manager.approve_override("test-iter-306", "manager-user")

        # Now should pass
        result = gate.check_with_override(
            TriModalVerdict.SYSTEMIC_FAILURE.value,
            "test-iter-306"
        )
        assert result.deploy_allowed is True
        assert "OVERRIDE APPLIED" in result.message

    def test_tri_307_override_requires_justification_and_approval(self):
        """TRI-307: Override requires justification and approval"""
        manager = OverrideManager()

        # Justification too short
        with pytest.raises(ValueError):
            manager.request_override(
                "test-iter-307",
                "dev-user",
                "urgent",  # Too short
                TriModalVerdict.SYSTEMIC_FAILURE.value
            )

        # Valid justification
        override = manager.request_override(
            "test-iter-307",
            "dev-user",
            "Emergency production fix required for customer-facing bug",
            TriModalVerdict.SYSTEMIC_FAILURE.value
        )

        assert override.approved is False
        assert override.approver is None

        # Approval required
        approved_override = manager.approve_override("test-iter-307", "manager")
        assert approved_override.approved is True
        assert approved_override.approver == "manager"

    def test_tri_308_override_recorded_in_audit_trail(self):
        """TRI-308: Override recorded in audit trail"""
        logger = GateAuditLogger()
        manager = OverrideManager()
        gate = DeploymentGate(audit_logger=logger, override_manager=manager)

        # Request and approve override
        manager.request_override(
            "test-iter-308",
            "dev-user",
            "Emergency hotfix required",
            TriModalVerdict.SYSTEMIC_FAILURE.value
        )
        manager.approve_override("test-iter-308", "manager-user")

        # Use override
        gate.check_with_override(
            TriModalVerdict.SYSTEMIC_FAILURE.value,
            "test-iter-308",
            trigger_user="deploy-user"
        )

        # Verify audit trail
        entries = logger.get_audit_trail("test-iter-308")
        override_entries = [e for e in entries if e.override_used]

        assert len(override_entries) >= 1
        assert override_entries[0].override_approver == "manager-user"
        assert override_entries[0].deploy_allowed is True

    def test_tri_309_override_expiration(self):
        """TRI-309: Override expiration (time-limited)"""
        manager = OverrideManager()
        gate = DeploymentGate(override_manager=manager)

        # Create override with 1 hour expiration
        override = manager.request_override(
            "test-iter-309",
            "dev-user",
            "Emergency production fix required",
            TriModalVerdict.SYSTEMIC_FAILURE.value,
            duration_hours=1
        )
        manager.approve_override("test-iter-309", "manager")

        # Should work now
        result = gate.check_with_override(
            TriModalVerdict.SYSTEMIC_FAILURE.value,
            "test-iter-309"
        )
        assert result.deploy_allowed is True

        # Manually expire override
        override = manager.get_override("test-iter-309")
        override.expiration = (datetime.utcnow() - timedelta(hours=2)).isoformat() + "Z"
        manager._save_override(override)

        # Should be blocked now
        result = gate.check_with_override(
            TriModalVerdict.SYSTEMIC_FAILURE.value,
            "test-iter-309"
        )
        assert result.deploy_allowed is False

    def test_tri_310_override_notification(self):
        """TRI-310: Override notification (webhook, email)"""
        manager = OverrideManager()

        # Track notifications
        notifications = []

        def notification_callback(override: OverrideRequest):
            notifications.append({
                "iteration_id": override.iteration_id,
                "approver": override.approver,
                "timestamp": override.timestamp
            })

        manager.add_notification_callback(notification_callback)

        # Request and approve override
        manager.request_override(
            "test-iter-310",
            "dev-user",
            "Emergency production fix required",
            TriModalVerdict.SYSTEMIC_FAILURE.value
        )
        manager.approve_override("test-iter-310", "manager-user")

        # Verify notification sent
        assert len(notifications) == 1
        assert notifications[0]["iteration_id"] == "test-iter-310"
        assert notifications[0]["approver"] == "manager-user"


# ============================================================================
# Test Suite: CI/CD Integration (TRI-311 to TRI-315)
# ============================================================================

@pytest.mark.integration
@pytest.mark.tri_audit
class TestCICDIntegration:
    """Test Suite: CI/CD Integration"""

    def test_tri_311_github_actions_integration(self):
        """TRI-311: GitHub Actions integration (exit code)"""
        gate = DeploymentGate()
        cicd = CICDIntegration(gate)

        # Test pass case
        exit_code = cicd.check_gate_exit_code(
            TriModalVerdict.ALL_PASS.value,
            "test-iter-311"
        )
        assert exit_code == 0

        # Test fail case
        exit_code = cicd.check_gate_exit_code(
            TriModalVerdict.SYSTEMIC_FAILURE.value,
            "test-iter-311-fail"
        )
        assert exit_code == 1

        # Test GitHub Actions output format
        output = cicd.github_actions_output(
            TriModalVerdict.ALL_PASS.value,
            "test-iter-311-output"
        )
        assert "::set-output" in output
        assert "deploy_allowed" in output

    def test_tri_312_gitlab_ci_integration(self):
        """TRI-312: GitLab CI integration"""
        gate = DeploymentGate()
        cicd = CICDIntegration(gate)

        # Test GitLab CI output
        output = cicd.gitlab_ci_output(
            TriModalVerdict.ALL_PASS.value,
            "test-iter-312"
        )

        assert output["gitlab_status"] == "success"
        assert output["deploy_allowed"] is True

        # Test failure case
        output = cicd.gitlab_ci_output(
            TriModalVerdict.SYSTEMIC_FAILURE.value,
            "test-iter-312-fail"
        )
        assert output["gitlab_status"] == "failed"
        assert output["deploy_allowed"] is False

    def test_tri_313_jenkins_integration(self):
        """TRI-313: Jenkins integration"""
        gate = DeploymentGate()
        cicd = CICDIntegration(gate)

        # Test Jenkins output
        output = cicd.jenkins_output(
            TriModalVerdict.ALL_PASS.value,
            "test-iter-313"
        )

        assert output["result"] == "SUCCESS"
        assert output["build_status"] == "STABLE"

        # Test failure case
        output = cicd.jenkins_output(
            TriModalVerdict.SYSTEMIC_FAILURE.value,
            "test-iter-313-fail"
        )
        assert output["result"] == "FAILURE"
        assert output["build_status"] == "UNSTABLE"

    def test_tri_314_cli_tool_check(self):
        """TRI-314: CLI tool: tri-audit gate --check"""
        gate = DeploymentGate()
        cli = GateCLI(gate)

        # Test pass case
        exit_code = cli.check(
            TriModalVerdict.ALL_PASS.value,
            "test-iter-314",
            json_output=False
        )
        assert exit_code == 0

        # Test fail case
        exit_code = cli.check(
            TriModalVerdict.SYSTEMIC_FAILURE.value,
            "test-iter-314-fail",
            json_output=False
        )
        assert exit_code == 1

    def test_tri_315_json_output_for_automation(self):
        """TRI-315: JSON output for automation"""
        gate = DeploymentGate()
        cicd = CICDIntegration(gate)

        # Get JSON output
        output = cicd.get_json_output(
            TriModalVerdict.ALL_PASS.value,
            "test-iter-315"
        )

        # Verify JSON structure
        assert "iteration_id" in output
        assert "verdict" in output
        assert "gate_status" in output
        assert "deploy_allowed" in output
        assert "timestamp" in output

        # Verify values
        assert output["deploy_allowed"] is True
        assert output["verdict"] == TriModalVerdict.ALL_PASS.value

        # Verify it's JSON serializable
        json_str = json.dumps(output)
        parsed = json.loads(json_str)
        assert parsed["deploy_allowed"] is True


# ============================================================================
# Test Suite: Audit Trail (TRI-316 to TRI-320)
# ============================================================================

@pytest.mark.integration
@pytest.mark.tri_audit
class TestAuditTrail:
    """Test Suite: Audit Trail"""

    def test_tri_316_record_all_gate_checks(self):
        """TRI-316: Record all gate checks (pass/fail/override)"""
        logger = GateAuditLogger()
        gate = DeploymentGate(audit_logger=logger)

        # Execute multiple gate checks
        gate.check(TriModalVerdict.ALL_PASS.value, "iter-316-1", "user1")
        gate.check(TriModalVerdict.SYSTEMIC_FAILURE.value, "iter-316-2", "user2")
        gate.check(TriModalVerdict.DESIGN_GAP.value, "iter-316-3", "user3")

        # Verify all recorded
        entries = logger.get_audit_trail()
        assert len(entries) >= 3

        # Verify different verdicts recorded
        verdicts = {e.verdict for e in entries if e.iteration_id.startswith("iter-316")}
        assert TriModalVerdict.ALL_PASS.value in verdicts
        assert TriModalVerdict.SYSTEMIC_FAILURE.value in verdicts

    def test_tri_317_track_who_triggered_deployment(self):
        """TRI-317: Track who triggered deployment"""
        # Use unique storage for this test
        import tempfile
        test_storage = Path(tempfile.mkdtemp()) / "gate_audit_logs_317"
        logger = GateAuditLogger(storage_path=test_storage)
        gate = DeploymentGate(audit_logger=logger)

        # Trigger gate check
        gate.check(
            TriModalVerdict.ALL_PASS.value,
            iteration_id="test-iter-317",
            trigger_user="alice@example.com",
            project="my-service",
            version="2.1.0",
            commit_sha="abc123def456"
        )

        # Verify tracking
        entries = logger.get_audit_trail("test-iter-317")
        assert len(entries) == 1, f"Expected 1 entry, got {len(entries)}"
        assert entries[0].trigger_user == "alice@example.com"
        assert entries[0].project == "my-service"
        assert entries[0].version == "2.1.0"
        assert entries[0].commit_sha == "abc123def456"

    def test_tri_318_track_override_approvers(self):
        """TRI-318: Track override approvers"""
        logger = GateAuditLogger()
        manager = OverrideManager()
        gate = DeploymentGate(audit_logger=logger, override_manager=manager)

        # Request and approve override
        manager.request_override(
            "test-iter-318",
            "dev-user",
            "Emergency hotfix for critical bug",
            TriModalVerdict.SYSTEMIC_FAILURE.value
        )
        manager.approve_override("test-iter-318", "director@example.com")

        # Use override
        gate.check_with_override(
            TriModalVerdict.SYSTEMIC_FAILURE.value,
            "test-iter-318",
            "deployer@example.com"
        )

        # Verify override approver tracked
        entries = logger.get_audit_trail("test-iter-318")
        override_entry = next((e for e in entries if e.override_used), None)

        assert override_entry is not None
        assert override_entry.override_approver == "director@example.com"
        assert override_entry.trigger_user == "deployer@example.com"

    def test_tri_319_historical_gate_metrics(self):
        """TRI-319: Historical gate metrics (pass rate over time)"""
        # Use unique storage path for this test
        import tempfile
        test_storage = Path(tempfile.mkdtemp()) / "gate_audit_logs_319"
        logger = GateAuditLogger(storage_path=test_storage)
        gate = DeploymentGate(audit_logger=logger)

        # Simulate multiple checks
        for i in range(10):
            verdict = TriModalVerdict.ALL_PASS.value if i < 7 else TriModalVerdict.SYSTEMIC_FAILURE.value
            gate.check(verdict, f"iter-319-{i}")

        # Calculate pass rate
        pass_rate = logger.get_pass_rate(days=30)

        # Should be 70% (7 out of 10 passed)
        assert 0.69 <= pass_rate <= 0.71, f"Expected pass rate ~0.7, got {pass_rate}"

    def test_tri_320_compliance_reporting(self):
        """TRI-320: Compliance reporting (gates skipped, overrides used)"""
        logger = GateAuditLogger()
        manager = OverrideManager()
        gate = DeploymentGate(audit_logger=logger, override_manager=manager)

        # Execute normal checks
        gate.check(TriModalVerdict.ALL_PASS.value, "iter-320-1")
        gate.check(TriModalVerdict.ALL_PASS.value, "iter-320-2")

        # Execute with overrides
        for i in range(3, 6):
            manager.request_override(
                f"iter-320-{i}",
                "dev-user",
                f"Emergency hotfix {i}",
                TriModalVerdict.SYSTEMIC_FAILURE.value
            )
            manager.approve_override(f"iter-320-{i}", "manager")
            gate.check_with_override(
                TriModalVerdict.SYSTEMIC_FAILURE.value,
                f"iter-320-{i}"
            )

        # Get compliance metrics
        override_count = logger.get_override_count(days=30)
        total_entries = len([e for e in logger.get_audit_trail()
                           if e.iteration_id.startswith("iter-320")])

        # Verify override tracking
        assert override_count >= 3
        assert total_entries >= 5


# ============================================================================
# Additional Integration Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.tri_audit
class TestDeploymentGateIntegration:
    """Additional integration tests for complete workflows"""

    def test_complete_deployment_workflow_with_override(self):
        """Test complete deployment workflow with override"""
        logger = GateAuditLogger()
        manager = OverrideManager()
        gate = DeploymentGate(audit_logger=logger, override_manager=manager)
        cicd = CICDIntegration(gate)

        iteration_id = "test-complete-workflow"

        # 1. Initial check fails
        result = gate.check(TriModalVerdict.SYSTEMIC_FAILURE.value, iteration_id)
        assert result.deploy_allowed is False

        # 2. Request override
        override = manager.request_override(
            iteration_id,
            "developer@example.com",
            "Critical production bug fix required immediately",
            TriModalVerdict.SYSTEMIC_FAILURE.value
        )
        assert override.approved is False

        # 3. Approve override
        approved = manager.approve_override(iteration_id, "cto@example.com")
        assert approved.approved is True

        # 4. Re-check with override
        result = gate.check_with_override(TriModalVerdict.SYSTEMIC_FAILURE.value, iteration_id)
        assert result.deploy_allowed is True
        assert "OVERRIDE APPLIED" in result.message

        # 5. Verify audit trail
        entries = logger.get_audit_trail(iteration_id)
        assert len(entries) >= 2

        # 6. Check CI/CD output
        json_output = cicd.get_json_output(TriModalVerdict.SYSTEMIC_FAILURE.value, iteration_id)
        assert json_output["deploy_allowed"] is True

    def test_gate_enforcement_prevents_bad_deployments(self):
        """Test that gate enforcement prevents bad deployments"""
        gate = DeploymentGate()

        bad_verdicts = [
            TriModalVerdict.SYSTEMIC_FAILURE.value,
            TriModalVerdict.ARCHITECTURAL_EROSION.value,
            TriModalVerdict.MIXED_FAILURE.value
        ]

        for verdict in bad_verdicts:
            with pytest.raises(DeploymentBlockedException) as exc_info:
                gate.enforce(verdict, f"test-bad-{verdict}")

            assert "blocked" in str(exc_info.value).lower()
            assert verdict in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
