#!/usr/bin/env python3
"""
Phase Gate Bypass Manager

Manages bypasses for phase gate quality requirements with:
- ADR (Architecture Decision Record) backed approval process
- Full audit trail in JSONL format
- Bypass metrics tracking and alerting
- Policy-based bypass rules from YAML configuration

Version: 1.0.0
Created: 2025-10-12
"""

import logging
import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum

try:
    from policy_loader import get_policy_loader, PolicyLoader
    POLICY_LOADER_AVAILABLE = True
except ImportError:
    POLICY_LOADER_AVAILABLE = False
    logging.warning("PolicyLoader not available for bypass rules")

logger = logging.getLogger(__name__)


class BypassStatus(str, Enum):
    """Status of a bypass request"""
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    REVOKED = "revoked"


class RiskLevel(str, Enum):
    """Risk level assessment"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class BypassRequest:
    """Represents a request to bypass a quality gate"""
    bypass_id: str
    workflow_id: str
    phase: str
    gate_name: str
    status: BypassStatus

    # Context
    current_value: float
    required_threshold: float
    justification: str

    # Risk assessment
    technical_risk: RiskLevel
    business_risk: RiskLevel
    security_risk: RiskLevel
    risk_description: str

    # Bypass details
    bypass_duration: str  # "temporary" or "permanent"
    expiration_date: Optional[str] = None
    remediation_plan: Optional[str] = None
    compensating_controls: List[str] = field(default_factory=list)

    # Audit trail
    requested_by: str = "system"
    request_date: str = field(default_factory=lambda: datetime.now().isoformat())
    approved_by: Optional[str] = None
    approval_date: Optional[str] = None
    applied_date: Optional[str] = None

    # Documentation
    adr_path: Optional[str] = None
    related_docs: List[str] = field(default_factory=list)

    # Follow-up
    follow_up_required: bool = False
    follow_up_tasks: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class BypassMetrics:
    """Metrics for bypass tracking"""
    total_bypasses: int = 0
    approved_bypasses: int = 0
    rejected_bypasses: int = 0
    active_bypasses: int = 0
    expired_bypasses: int = 0
    bypass_rate: float = 0.0  # Ratio of bypasses to total gate evaluations

    # By gate
    bypasses_by_gate: Dict[str, int] = field(default_factory=dict)

    # By phase
    bypasses_by_phase: Dict[str, int] = field(default_factory=dict)

    # Time range
    time_window_days: int = 30
    last_updated: str = field(default_factory=lambda: datetime.now().isoformat())


class PhaseGateBypassManager:
    """
    Manages phase gate bypasses with ADR backing and audit trail.

    Key Features:
    - Policy-based bypass rules from YAML
    - ADR template enforcement
    - JSONL audit trail
    - Bypass metrics tracking
    - Alerting on high bypass rates
    """

    def __init__(self,
                 audit_log_path: Optional[Path] = None,
                 policy_loader: Optional[PolicyLoader] = None):
        """
        Initialize bypass manager.

        Args:
            audit_log_path: Path to JSONL audit log file
            policy_loader: PolicyLoader instance for bypass rules
        """
        # Audit trail
        self.audit_log_path = audit_log_path or Path("logs/phase_gate_bypasses.jsonl")
        self.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

        # Policy loader
        if POLICY_LOADER_AVAILABLE:
            self.policy_loader = policy_loader or get_policy_loader()
            logger.info("PolicyLoader enabled for bypass rules")
        else:
            self.policy_loader = None
            logger.warning("PolicyLoader not available, using default bypass rules")

        # Metrics
        self.metrics = BypassMetrics()
        self._load_metrics()

        # Alert thresholds
        self.bypass_rate_alert_threshold = 0.10  # 10%
        self.bypass_rate_critical_threshold = 0.20  # 20%

        logger.info(f"PhaseGateBypassManager initialized, audit log: {self.audit_log_path}")

    def can_bypass_gate(self, gate_name: str, phase: str) -> bool:
        """
        Check if a gate can be bypassed according to policy.

        Args:
            gate_name: Name of the quality gate
            phase: SDLC phase

        Returns:
            True if gate can be bypassed (with ADR approval), False if non-bypassable
        """
        if not self.policy_loader:
            # Default: most gates can be bypassed except security and build
            non_bypassable = ["security", "build_success", "security_vulnerabilities"]
            return gate_name not in non_bypassable

        try:
            return self.policy_loader.can_bypass_gate(gate_name, phase)
        except Exception as e:
            logger.error(f"Error checking bypass rules: {e}")
            return False

    def get_bypass_requirements(self, gate_name: str, phase: str) -> Dict[str, Any]:
        """
        Get bypass requirements for a gate from policy.

        Returns:
            Dictionary with requires_adr, approval_level, etc.
        """
        if not self.policy_loader:
            return {
                "requires_adr": True,
                "approval_level": "tech_lead",
                "requires_approval": True
            }

        try:
            override_policies = self.policy_loader.get_override_policies()

            # Find matching override rule
            for rule in override_policies.get('allowed_overrides', []):
                if rule.get('gate') == gate_name:
                    return {
                        "requires_adr": override_policies.get('adr_required', True),
                        "approval_level": rule.get('approval_level', 'tech_lead'),
                        "requires_approval": override_policies.get('approval_required', True),
                        "condition": rule.get('condition', '')
                    }

            # Default requirements
            return {
                "requires_adr": True,
                "approval_level": "tech_lead",
                "requires_approval": True
            }

        except Exception as e:
            logger.error(f"Error getting bypass requirements: {e}")
            return {
                "requires_adr": True,
                "approval_level": "tech_lead",
                "requires_approval": True
            }

    def create_bypass_request(self,
                             workflow_id: str,
                             phase: str,
                             gate_name: str,
                             current_value: float,
                             required_threshold: float,
                             justification: str,
                             technical_risk: RiskLevel = RiskLevel.MEDIUM,
                             business_risk: RiskLevel = RiskLevel.MEDIUM,
                             security_risk: RiskLevel = RiskLevel.LOW,
                             risk_description: str = "",
                             bypass_duration: str = "temporary",
                             remediation_plan: Optional[str] = None,
                             requested_by: str = "system") -> BypassRequest:
        """
        Create a new bypass request.

        Args:
            workflow_id: Workflow identifier
            phase: SDLC phase
            gate_name: Quality gate name
            current_value: Current metric value
            required_threshold: Required threshold value
            justification: Justification for bypass
            technical_risk: Technical risk level
            business_risk: Business risk level
            security_risk: Security risk level
            risk_description: Description of risks
            bypass_duration: "temporary" or "permanent"
            remediation_plan: Plan to address the issue
            requested_by: Person requesting bypass

        Returns:
            BypassRequest object
        """
        bypass_id = f"bypass-{uuid.uuid4()}"

        request = BypassRequest(
            bypass_id=bypass_id,
            workflow_id=workflow_id,
            phase=phase,
            gate_name=gate_name,
            status=BypassStatus.PROPOSED,
            current_value=current_value,
            required_threshold=required_threshold,
            justification=justification,
            technical_risk=technical_risk,
            business_risk=business_risk,
            security_risk=security_risk,
            risk_description=risk_description,
            bypass_duration=bypass_duration,
            remediation_plan=remediation_plan,
            requested_by=requested_by
        )

        # Log to audit trail
        self._log_audit_event("bypass_requested", request)

        logger.info(f"Bypass request created: {bypass_id} for {gate_name} in {phase}")

        return request

    def approve_bypass(self,
                      bypass_request: BypassRequest,
                      approved_by: str,
                      adr_path: Optional[str] = None,
                      expiration_date: Optional[str] = None,
                      compensating_controls: Optional[List[str]] = None) -> BypassRequest:
        """
        Approve a bypass request.

        Args:
            bypass_request: The bypass request to approve
            approved_by: Person approving the bypass
            adr_path: Path to ADR document
            expiration_date: Expiration date for temporary bypasses (ISO format)
            compensating_controls: List of compensating controls

        Returns:
            Updated BypassRequest
        """
        # Check if bypass is allowed
        if not self.can_bypass_gate(bypass_request.gate_name, bypass_request.phase):
            logger.error(f"Gate {bypass_request.gate_name} is non-bypassable")
            return self.reject_bypass(bypass_request, approved_by, "Gate is non-bypassable per policy")

        # Check requirements
        requirements = self.get_bypass_requirements(bypass_request.gate_name, bypass_request.phase)
        if requirements.get('requires_adr') and not adr_path:
            logger.warning(f"ADR required but not provided for {bypass_request.bypass_id}")

        # Update request
        bypass_request.status = BypassStatus.APPROVED
        bypass_request.approved_by = approved_by
        bypass_request.approval_date = datetime.now().isoformat()
        bypass_request.applied_date = datetime.now().isoformat()

        if adr_path:
            bypass_request.adr_path = adr_path

        if expiration_date:
            bypass_request.expiration_date = expiration_date

        if compensating_controls:
            bypass_request.compensating_controls = compensating_controls

        # Log to audit trail
        self._log_audit_event("bypass_approved", bypass_request)

        # Update metrics
        self.metrics.approved_bypasses += 1
        self.metrics.active_bypasses += 1
        self.metrics.bypasses_by_gate[bypass_request.gate_name] = \
            self.metrics.bypasses_by_gate.get(bypass_request.gate_name, 0) + 1
        self.metrics.bypasses_by_phase[bypass_request.phase] = \
            self.metrics.bypasses_by_phase.get(bypass_request.phase, 0) + 1

        self._save_metrics()
        self._check_bypass_rate_alerts()

        logger.info(f"Bypass approved: {bypass_request.bypass_id} by {approved_by}")

        return bypass_request

    def reject_bypass(self,
                     bypass_request: BypassRequest,
                     rejected_by: str,
                     reason: str) -> BypassRequest:
        """
        Reject a bypass request.

        Args:
            bypass_request: The bypass request to reject
            rejected_by: Person rejecting the bypass
            reason: Reason for rejection

        Returns:
            Updated BypassRequest
        """
        bypass_request.status = BypassStatus.REJECTED
        bypass_request.approved_by = rejected_by
        bypass_request.approval_date = datetime.now().isoformat()
        bypass_request.justification += f"\n\nREJECTED: {reason}"

        # Log to audit trail
        self._log_audit_event("bypass_rejected", bypass_request, {"reason": reason})

        # Update metrics
        self.metrics.rejected_bypasses += 1

        self._save_metrics()

        logger.info(f"Bypass rejected: {bypass_request.bypass_id} by {rejected_by}")

        return bypass_request

    def revoke_bypass(self, bypass_request: BypassRequest, revoked_by: str, reason: str) -> BypassRequest:
        """
        Revoke an active bypass.

        Args:
            bypass_request: The bypass to revoke
            revoked_by: Person revoking the bypass
            reason: Reason for revocation

        Returns:
            Updated BypassRequest
        """
        if bypass_request.status != BypassStatus.APPROVED:
            logger.warning(f"Cannot revoke bypass {bypass_request.bypass_id} - not approved")
            return bypass_request

        bypass_request.status = BypassStatus.REVOKED

        # Log to audit trail
        self._log_audit_event("bypass_revoked", bypass_request, {
            "revoked_by": revoked_by,
            "reason": reason
        })

        # Update metrics
        self.metrics.active_bypasses = max(0, self.metrics.active_bypasses - 1)

        self._save_metrics()

        logger.info(f"Bypass revoked: {bypass_request.bypass_id} by {revoked_by}")

        return bypass_request

    def _log_audit_event(self, event_type: str, bypass_request: BypassRequest, extra_data: Optional[Dict] = None):
        """
        Log an audit event to JSONL file.

        Args:
            event_type: Type of event (bypass_requested, bypass_approved, etc.)
            bypass_request: The bypass request
            extra_data: Additional event data
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "event_type": event_type,
            "bypass_id": bypass_request.bypass_id,
            "workflow_id": bypass_request.workflow_id,
            "phase": bypass_request.phase,
            "gate_name": bypass_request.gate_name,
            "status": bypass_request.status.value,
            "requested_by": bypass_request.requested_by,
            "approved_by": bypass_request.approved_by,
            "bypass_data": asdict(bypass_request)
        }

        if extra_data:
            event.update(extra_data)

        # Append to JSONL file
        with open(self.audit_log_path, 'a') as f:
            f.write(json.dumps(event) + '\n')

        logger.debug(f"Audit event logged: {event_type} for {bypass_request.bypass_id}")

    def _load_metrics(self):
        """Load metrics from audit log"""
        if not self.audit_log_path.exists():
            return

        try:
            with open(self.audit_log_path, 'r') as f:
                for line in f:
                    event = json.loads(line.strip())
                    self.metrics.total_bypasses += 1

                    if event.get('event_type') == 'bypass_approved':
                        self.metrics.approved_bypasses += 1
                    elif event.get('event_type') == 'bypass_rejected':
                        self.metrics.rejected_bypasses += 1

            logger.info(f"Loaded metrics: {self.metrics.total_bypasses} total bypasses")

        except Exception as e:
            logger.error(f"Error loading metrics: {e}")

    def _save_metrics(self):
        """Save current metrics"""
        self.metrics.last_updated = datetime.now().isoformat()
        self.metrics.bypass_rate = (self.metrics.approved_bypasses /
                                   max(self.metrics.total_bypasses, 1))

    def _check_bypass_rate_alerts(self):
        """Check if bypass rate exceeds alert thresholds"""
        if self.metrics.bypass_rate >= self.bypass_rate_critical_threshold:
            logger.critical(
                f"🚨 CRITICAL: Bypass rate is {self.metrics.bypass_rate:.1%} "
                f"(threshold: {self.bypass_rate_critical_threshold:.0%})"
            )
        elif self.metrics.bypass_rate >= self.bypass_rate_alert_threshold:
            logger.warning(
                f"⚠️  WARNING: Bypass rate is {self.metrics.bypass_rate:.1%} "
                f"(threshold: {self.bypass_rate_alert_threshold:.0%})"
            )

    def get_metrics(self) -> BypassMetrics:
        """Get current bypass metrics"""
        return self.metrics

    def get_recent_bypasses(self, days: int = 30) -> List[BypassRequest]:
        """
        Get recent bypass requests from audit log.

        Args:
            days: Number of days to look back

        Returns:
            List of BypassRequest objects
        """
        if not self.audit_log_path.exists():
            return []

        bypasses = []
        cutoff_date = datetime.now().timestamp() - (days * 24 * 3600)

        try:
            with open(self.audit_log_path, 'r') as f:
                for line in f:
                    event = json.loads(line.strip())

                    # Check if event is recent
                    event_date = datetime.fromisoformat(event['timestamp']).timestamp()
                    if event_date < cutoff_date:
                        continue

                    # Only include approved bypasses
                    if event.get('event_type') == 'bypass_approved':
                        bypass_data = event.get('bypass_data', {})
                        if bypass_data:
                            # Reconstruct BypassRequest
                            bypass = BypassRequest(**bypass_data)
                            bypasses.append(bypass)

        except Exception as e:
            logger.error(f"Error loading recent bypasses: {e}")

        return bypasses


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    manager = PhaseGateBypassManager()

    # Create a bypass request
    request = manager.create_bypass_request(
        workflow_id="wf-test-001",
        phase="implementation",
        gate_name="test_coverage",
        current_value=0.68,
        required_threshold=0.80,
        justification="Legacy code needs testing, but customer-critical bug fix required",
        technical_risk=RiskLevel.LOW,
        business_risk=RiskLevel.MEDIUM,
        security_risk=RiskLevel.LOW,
        risk_description="Bug fix code has 100% coverage, only legacy utilities lack tests",
        bypass_duration="temporary",
        remediation_plan="Add tests for legacy utilities by 2025-10-19",
        requested_by="jane.developer"
    )

    print(f"\n✓ Bypass request created: {request.bypass_id}")
    print(f"  Gate: {request.gate_name}")
    print(f"  Status: {request.status.value}")

    # Check if bypass is allowed
    can_bypass = manager.can_bypass_gate(request.gate_name, request.phase)
    print(f"  Can bypass: {can_bypass}")

    # Get requirements
    requirements = manager.get_bypass_requirements(request.gate_name, request.phase)
    print(f"  Requirements: {requirements}")

    # Approve bypass
    approved = manager.approve_bypass(
        request,
        approved_by="john.techlead",
        adr_path="docs/adr/ADR-0123_test_coverage_bypass.md",
        expiration_date="2025-10-19",
        compensating_controls=[
            "Manual testing completed",
            "Smoke tests pass",
            "Monitoring in place"
        ]
    )

    print(f"\n✓ Bypass approved: {approved.bypass_id}")
    print(f"  Status: {approved.status.value}")
    print(f"  Approved by: {approved.approved_by}")
    print(f"  ADR: {approved.adr_path}")

    # Get metrics
    metrics = manager.get_metrics()
    print(f"\n📊 Metrics:")
    print(f"  Total bypasses: {metrics.total_bypasses}")
    print(f"  Approved: {metrics.approved_bypasses}")
    print(f"  Rejected: {metrics.rejected_bypasses}")
    print(f"  Active: {metrics.active_bypasses}")
    print(f"  Bypass rate: {metrics.bypass_rate:.1%}")

    print(f"\n✓ Audit log: {manager.audit_log_path}")
