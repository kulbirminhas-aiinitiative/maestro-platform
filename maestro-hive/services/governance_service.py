"""
Governance Service (MD-2122)

Enforces documentation and governance rules at phase gates.
Validates that required documents exist and approvals are obtained
before phase transitions.
"""

import logging
import yaml
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from threading import Lock

logger = logging.getLogger(__name__)


class ValidationResult(Enum):
    """Result of a validation check"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"


@dataclass
class DocumentRequirement:
    """A required document for a phase"""
    doc_type: str
    name: str
    template: Optional[str] = None
    required: bool = True


@dataclass
class ApprovalRequirement:
    """A required approval for a phase"""
    role: str
    required: bool = True


@dataclass
class ValidationRule:
    """A validation rule for a phase"""
    rule_id: str
    description: str
    threshold: Optional[float] = None
    custom_validator: Optional[Callable[[Dict[str, Any]], bool]] = None


@dataclass
class PhaseGate:
    """Configuration for a phase gate"""
    phase: str
    display_name: str
    required_documents: List[DocumentRequirement] = field(default_factory=list)
    required_approvals: List[ApprovalRequirement] = field(default_factory=list)
    validation_rules: List[ValidationRule] = field(default_factory=list)


@dataclass
class GovernanceCheckResult:
    """Result of a governance check"""
    phase: str
    passed: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)
    document_checks: Dict[str, ValidationResult] = field(default_factory=dict)
    approval_checks: Dict[str, ValidationResult] = field(default_factory=dict)
    rule_checks: Dict[str, ValidationResult] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'phase': self.phase,
            'passed': self.passed,
            'timestamp': self.timestamp.isoformat(),
            'document_checks': {k: v.value for k, v in self.document_checks.items()},
            'approval_checks': {k: v.value for k, v in self.approval_checks.items()},
            'rule_checks': {k: v.value for k, v in self.rule_checks.items()},
            'errors': self.errors,
            'warnings': self.warnings
        }


@dataclass
class AuditEntry:
    """An entry in the governance audit trail"""
    workflow_id: str
    phase: str
    action: str  # 'check', 'approve', 'reject', 'override'
    actor: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    result: Optional[GovernanceCheckResult] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'workflow_id': self.workflow_id,
            'phase': self.phase,
            'action': self.action,
            'actor': self.actor,
            'timestamp': self.timestamp.isoformat(),
            'result': self.result.to_dict() if self.result else None,
            'metadata': self.metadata
        }


@dataclass
class Approval:
    """A recorded approval"""
    workflow_id: str
    phase: str
    role: str
    approver: str
    approved_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    notes: str = ""


class GovernanceService:
    """
    Service for enforcing governance rules at phase gates.

    Features:
    - Load governance protocol from YAML
    - Validate phase transitions
    - Track approvals
    - Maintain audit trail
    """

    def __init__(
        self,
        protocol_path: Optional[str] = None,
        approval_expiry_hours: int = 72
    ):
        """
        Initialize the governance service.

        Args:
            protocol_path: Path to governance protocol YAML
            approval_expiry_hours: Hours until approvals expire
        """
        self._protocol: Dict[str, Any] = {}
        self._phase_gates: Dict[str, PhaseGate] = {}
        self._approvals: Dict[str, List[Approval]] = {}  # workflow_id -> approvals
        self._audit_trail: List[AuditEntry] = []
        self._custom_validators: Dict[str, Callable] = {}
        self._lock = Lock()
        self._approval_expiry_hours = approval_expiry_hours

        # Load protocol if path provided
        if protocol_path:
            self.load_protocol(protocol_path)
        else:
            # Try default path
            default_path = Path(__file__).parent.parent / "config" / "governance_protocol.yaml"
            if default_path.exists():
                self.load_protocol(str(default_path))

        logger.info("GovernanceService initialized")

    def load_protocol(self, path: str) -> None:
        """
        Load governance protocol from YAML file.

        Args:
            path: Path to YAML file
        """
        try:
            with open(path, 'r') as f:
                self._protocol = yaml.safe_load(f)

            # Parse phase gates
            for phase_name, phase_config in self._protocol.get('phases', {}).items():
                gate = PhaseGate(
                    phase=phase_name,
                    display_name=phase_config.get('display_name', phase_name),
                    required_documents=[
                        DocumentRequirement(
                            doc_type=doc.get('type', ''),
                            name=doc.get('name', ''),
                            template=doc.get('template'),
                            required=doc.get('required', True)
                        )
                        for doc in phase_config.get('required_documents', [])
                    ],
                    required_approvals=[
                        ApprovalRequirement(
                            role=appr.get('role', ''),
                            required=appr.get('required', True)
                        )
                        for appr in phase_config.get('required_approvals', [])
                    ],
                    validation_rules=[
                        ValidationRule(
                            rule_id=rule.get('rule', ''),
                            description=rule.get('description', ''),
                            threshold=rule.get('threshold')
                        )
                        for rule in phase_config.get('validation_rules', [])
                    ]
                )
                self._phase_gates[phase_name] = gate

            logger.info(f"Loaded governance protocol with {len(self._phase_gates)} phases")

        except Exception as e:
            logger.error(f"Failed to load governance protocol: {e}")
            raise

    def register_validator(
        self,
        rule_id: str,
        validator: Callable[[Dict[str, Any]], bool]
    ) -> None:
        """
        Register a custom validation function.

        Args:
            rule_id: Rule identifier
            validator: Function that takes context and returns bool
        """
        self._custom_validators[rule_id] = validator
        logger.debug(f"Registered validator for rule: {rule_id}")

    def check_phase_gate(
        self,
        workflow_id: str,
        phase: str,
        context: Dict[str, Any],
        actor: str = "system"
    ) -> GovernanceCheckResult:
        """
        Check if a phase gate passes governance.

        Args:
            workflow_id: Workflow ID
            phase: Phase to check
            context: Context with documents, approvals, etc.
            actor: Actor performing the check

        Returns:
            GovernanceCheckResult with pass/fail and details
        """
        result = GovernanceCheckResult(phase=phase, passed=True)

        gate = self._phase_gates.get(phase)
        if not gate:
            # No gate defined, pass by default
            result.warnings.append(f"No governance gate defined for phase: {phase}")
            self._record_audit(workflow_id, phase, 'check', actor, result)
            return result

        # Check required documents
        documents = context.get('documents', {})
        for doc_req in gate.required_documents:
            if doc_req.required:
                if doc_req.doc_type in documents:
                    result.document_checks[doc_req.doc_type] = ValidationResult.PASSED
                else:
                    result.document_checks[doc_req.doc_type] = ValidationResult.FAILED
                    result.errors.append(f"Missing required document: {doc_req.name}")
                    result.passed = False
            else:
                if doc_req.doc_type in documents:
                    result.document_checks[doc_req.doc_type] = ValidationResult.PASSED
                else:
                    result.document_checks[doc_req.doc_type] = ValidationResult.SKIPPED

        # Check required approvals
        approvals = self._get_valid_approvals(workflow_id, phase)
        approval_roles = {a.role for a in approvals}

        for appr_req in gate.required_approvals:
            if appr_req.required:
                if appr_req.role in approval_roles:
                    result.approval_checks[appr_req.role] = ValidationResult.PASSED
                else:
                    result.approval_checks[appr_req.role] = ValidationResult.PENDING
                    result.errors.append(f"Missing approval from: {appr_req.role}")
                    result.passed = False
            else:
                if appr_req.role in approval_roles:
                    result.approval_checks[appr_req.role] = ValidationResult.PASSED
                else:
                    result.approval_checks[appr_req.role] = ValidationResult.SKIPPED

        # Check validation rules
        for rule in gate.validation_rules:
            validator = self._custom_validators.get(rule.rule_id)
            if validator:
                try:
                    if validator(context):
                        result.rule_checks[rule.rule_id] = ValidationResult.PASSED
                    else:
                        result.rule_checks[rule.rule_id] = ValidationResult.FAILED
                        result.errors.append(f"Validation failed: {rule.description}")
                        result.passed = False
                except Exception as e:
                    result.rule_checks[rule.rule_id] = ValidationResult.FAILED
                    result.errors.append(f"Validation error: {str(e)}")
                    result.passed = False
            else:
                # No validator registered, skip
                result.rule_checks[rule.rule_id] = ValidationResult.SKIPPED
                result.warnings.append(f"No validator for rule: {rule.rule_id}")

        # Record in audit trail
        self._record_audit(workflow_id, phase, 'check', actor, result)

        return result

    def record_approval(
        self,
        workflow_id: str,
        phase: str,
        role: str,
        approver: str,
        notes: str = ""
    ) -> Approval:
        """
        Record an approval for a phase.

        Args:
            workflow_id: Workflow ID
            phase: Phase being approved
            role: Role of the approver
            approver: Approver identifier
            notes: Optional notes

        Returns:
            The recorded Approval
        """
        with self._lock:
            approval = Approval(
                workflow_id=workflow_id,
                phase=phase,
                role=role,
                approver=approver,
                expires_at=datetime.utcnow() + timedelta(hours=self._approval_expiry_hours),
                notes=notes
            )

            if workflow_id not in self._approvals:
                self._approvals[workflow_id] = []
            self._approvals[workflow_id].append(approval)

            # Record in audit trail
            self._record_audit(
                workflow_id, phase, 'approve', approver,
                metadata={'role': role, 'notes': notes}
            )

            logger.info(f"Recorded approval for {workflow_id}/{phase} by {role}")
            return approval

    def revoke_approval(
        self,
        workflow_id: str,
        phase: str,
        role: str,
        actor: str
    ) -> bool:
        """
        Revoke an approval.

        Args:
            workflow_id: Workflow ID
            phase: Phase
            role: Role to revoke
            actor: Actor revoking

        Returns:
            True if approval was revoked
        """
        with self._lock:
            if workflow_id not in self._approvals:
                return False

            initial_count = len(self._approvals[workflow_id])
            self._approvals[workflow_id] = [
                a for a in self._approvals[workflow_id]
                if not (a.phase == phase and a.role == role)
            ]

            if len(self._approvals[workflow_id]) < initial_count:
                self._record_audit(
                    workflow_id, phase, 'reject', actor,
                    metadata={'role': role}
                )
                return True
            return False

    def _get_valid_approvals(self, workflow_id: str, phase: str) -> List[Approval]:
        """Get non-expired approvals for a workflow/phase"""
        with self._lock:
            if workflow_id not in self._approvals:
                return []

            now = datetime.utcnow()
            return [
                a for a in self._approvals[workflow_id]
                if a.phase == phase and (a.expires_at is None or a.expires_at > now)
            ]

    def _record_audit(
        self,
        workflow_id: str,
        phase: str,
        action: str,
        actor: str,
        result: Optional[GovernanceCheckResult] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record an audit entry"""
        with self._lock:
            entry = AuditEntry(
                workflow_id=workflow_id,
                phase=phase,
                action=action,
                actor=actor,
                result=result,
                metadata=metadata or {}
            )
            self._audit_trail.append(entry)

    def get_audit_trail(
        self,
        workflow_id: Optional[str] = None,
        phase: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditEntry]:
        """
        Get audit trail entries.

        Args:
            workflow_id: Filter by workflow
            phase: Filter by phase
            limit: Maximum entries

        Returns:
            List of audit entries
        """
        with self._lock:
            entries = self._audit_trail.copy()

        if workflow_id:
            entries = [e for e in entries if e.workflow_id == workflow_id]
        if phase:
            entries = [e for e in entries if e.phase == phase]

        return entries[-limit:]

    def get_phase_requirements(self, phase: str) -> Optional[PhaseGate]:
        """Get requirements for a phase"""
        return self._phase_gates.get(phase)

    def get_all_phases(self) -> List[str]:
        """Get all defined phases"""
        return list(self._phase_gates.keys())

    def get_protocol_info(self) -> Dict[str, Any]:
        """Get protocol metadata"""
        return {
            'version': self._protocol.get('version', 'unknown'),
            'name': self._protocol.get('name', 'unknown'),
            'phases': list(self._phase_gates.keys()),
            'roles': list(self._protocol.get('roles', {}).keys())
        }

    def clear_workflow_data(self, workflow_id: str) -> None:
        """Clear all data for a workflow"""
        with self._lock:
            if workflow_id in self._approvals:
                del self._approvals[workflow_id]


# Singleton instance
_service: Optional[GovernanceService] = None


def get_governance_service() -> GovernanceService:
    """Get the default governance service instance"""
    global _service
    if _service is None:
        _service = GovernanceService()
    return _service


def reset_governance_service() -> None:
    """Reset the governance service (for testing)"""
    global _service
    _service = None
