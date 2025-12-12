"""
Environment Promotion Gates Implementation.

Provides approval-based promotion workflows with quality gates,
approval tracking, and promotion history.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Approval request status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class GateStatus(Enum):
    """Quality gate status."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"


@dataclass
class QualityGate:
    """Quality gate definition."""

    name: str
    check_func: Optional[Callable[[], bool]] = None
    min_test_coverage: float = 0.0
    max_critical_issues: int = 0
    required_checks: List[str] = field(default_factory=list)
    manual_approval: bool = False
    required_approvers: List[str] = field(default_factory=list)
    timeout_hours: int = 24

    def evaluate(self, metrics: Dict[str, Any]) -> GateStatus:
        """
        Evaluate quality gate against metrics.

        Args:
            metrics: Dictionary of metric values

        Returns:
            Gate status
        """
        # Check test coverage
        if self.min_test_coverage > 0:
            coverage = metrics.get("test_coverage", 0)
            if coverage < self.min_test_coverage:
                logger.warning(
                    f"Quality gate '{self.name}' failed: coverage {coverage}% "
                    f"< required {self.min_test_coverage}%"
                )
                return GateStatus.FAILED

        # Check critical issues
        critical_issues = metrics.get("critical_issues", 0)
        if critical_issues > self.max_critical_issues:
            logger.warning(
                f"Quality gate '{self.name}' failed: {critical_issues} critical issues "
                f"> max {self.max_critical_issues}"
            )
            return GateStatus.FAILED

        # Check required checks
        passed_checks = metrics.get("passed_checks", [])
        for required in self.required_checks:
            if required not in passed_checks:
                logger.warning(
                    f"Quality gate '{self.name}' failed: required check '{required}' not passed"
                )
                return GateStatus.FAILED

        # Run custom check function if provided
        if self.check_func:
            try:
                if not self.check_func():
                    return GateStatus.FAILED
            except Exception as e:
                logger.error(f"Quality gate check function failed: {e}")
                return GateStatus.FAILED

        # Manual approval required
        if self.manual_approval:
            approved = metrics.get("manual_approved", False)
            if not approved:
                return GateStatus.PENDING

        logger.info(f"Quality gate '{self.name}' passed")
        return GateStatus.PASSED


@dataclass
class ApprovalRequest:
    """Approval request for promotion."""

    id: str
    release_version: str
    target_environment: str
    requester: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    approvers: List[str] = field(default_factory=list)
    approved_by: List[str] = field(default_factory=list)
    rejected_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    decided_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    def approve(self, approver: str) -> bool:
        """
        Approve the request.

        Args:
            approver: Approver identifier

        Returns:
            True if approval results in full approval
        """
        if self.status != ApprovalStatus.PENDING:
            return False

        if approver not in self.approved_by:
            self.approved_by.append(approver)

        # Check if all required approvers have approved
        if not self.approvers or all(a in self.approved_by for a in self.approvers):
            self.status = ApprovalStatus.APPROVED
            self.decided_at = datetime.utcnow()
            logger.info(f"Approval request {self.id} approved")
            return True

        return False

    def reject(self, rejector: str, reason: str) -> None:
        """
        Reject the request.

        Args:
            rejector: Rejector identifier
            reason: Rejection reason
        """
        if self.status == ApprovalStatus.PENDING:
            self.status = ApprovalStatus.REJECTED
            self.rejected_by = rejector
            self.rejection_reason = reason
            self.decided_at = datetime.utcnow()
            logger.info(f"Approval request {self.id} rejected: {reason}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "release_version": self.release_version,
            "target_environment": self.target_environment,
            "requester": self.requester,
            "status": self.status.value,
            "approvers": self.approvers,
            "approved_by": self.approved_by,
            "rejected_by": self.rejected_by,
            "rejection_reason": self.rejection_reason,
            "created_at": self.created_at.isoformat(),
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
        }


@dataclass
class PromotionRecord:
    """Record of a promotion execution."""

    id: str
    release_version: str
    source_environment: str
    target_environment: str
    status: str
    initiated_by: str
    approval_request_id: Optional[str] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    gate_results: Dict[str, GateStatus] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "release_version": self.release_version,
            "source_environment": self.source_environment,
            "target_environment": self.target_environment,
            "status": self.status,
            "initiated_by": self.initiated_by,
            "approval_request_id": self.approval_request_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "gate_results": {k: v.value for k, v in self.gate_results.items()},
        }


@dataclass
class ReadinessResult:
    """Result of promotion readiness check."""

    ready: bool
    gate_results: Dict[str, GateStatus] = field(default_factory=dict)
    blocking_issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    requires_approval: bool = False
    approval_request: Optional[ApprovalRequest] = None


@dataclass
class PromotionResult:
    """Result of promotion execution."""

    success: bool
    promotion_record: PromotionRecord
    error_message: Optional[str] = None


class PromotionGates:
    """Environment promotion and approval workflow."""

    def __init__(self):
        """Initialize promotion gates."""
        self._quality_gates: Dict[str, Dict[str, QualityGate]] = {}
        self._approval_requests: Dict[str, ApprovalRequest] = {}
        self._promotion_history: List[PromotionRecord] = []
        self._id_counter = 0

        # Initialize default gates
        self._initialize_default_gates()
        logger.info("PromotionGates initialized")

    def _initialize_default_gates(self) -> None:
        """Initialize default quality gates."""
        # Dev to Test gate
        self._quality_gates["dev_to_test"] = {
            "basic_tests": QualityGate(
                name="basic_tests",
                min_test_coverage=60.0,
                required_checks=["unit_tests"],
                manual_approval=False,
            )
        }

        # Test to Pre-Prod gate
        self._quality_gates["test_to_preprod"] = {
            "quality_assurance": QualityGate(
                name="quality_assurance",
                min_test_coverage=80.0,
                max_critical_issues=0,
                required_checks=["unit_tests", "integration_tests", "security_scan"],
                manual_approval=False,
            )
        }

        # Pre-Prod to Prod gate
        self._quality_gates["preprod_to_prod"] = {
            "production_readiness": QualityGate(
                name="production_readiness",
                min_test_coverage=85.0,
                max_critical_issues=0,
                required_checks=["unit_tests", "integration_tests",
                                 "security_scan", "performance_tests"],
                manual_approval=True,
                required_approvers=["tech_lead", "product_owner"],
            )
        }

    def _generate_id(self) -> str:
        """Generate unique ID."""
        self._id_counter += 1
        return f"promo_{self._id_counter:06d}"

    def add_quality_gate(
        self,
        promotion_path: str,
        gate: QualityGate,
    ) -> None:
        """
        Add quality gate for promotion path.

        Args:
            promotion_path: Promotion path (e.g., 'test_to_preprod')
            gate: Quality gate to add
        """
        if promotion_path not in self._quality_gates:
            self._quality_gates[promotion_path] = {}

        self._quality_gates[promotion_path][gate.name] = gate
        logger.info(f"Quality gate added: {gate.name} for {promotion_path}")

    def get_quality_gates(self, promotion_path: str) -> Dict[str, QualityGate]:
        """
        Get quality gates for promotion path.

        Args:
            promotion_path: Promotion path

        Returns:
            Dictionary of quality gates
        """
        return self._quality_gates.get(promotion_path, {})

    def check_promotion_readiness(
        self,
        release_version: str,
        source_env: str,
        target_env: str,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> ReadinessResult:
        """
        Check if release is ready for promotion.

        Args:
            release_version: Version to promote
            source_env: Source environment
            target_env: Target environment
            metrics: Optional metrics for evaluation

        Returns:
            Readiness result
        """
        promotion_path = f"{source_env}_to_{target_env}"
        gates = self._quality_gates.get(promotion_path, {})
        metrics = metrics or {}

        gate_results = {}
        blocking_issues = []
        warnings = []
        requires_approval = False

        for gate_name, gate in gates.items():
            result = gate.evaluate(metrics)
            gate_results[gate_name] = result

            if result == GateStatus.FAILED:
                blocking_issues.append(f"Quality gate '{gate_name}' failed")
            elif result == GateStatus.PENDING:
                if gate.manual_approval:
                    requires_approval = True
                    blocking_issues.append(f"Manual approval required for '{gate_name}'")

        ready = len(blocking_issues) == 0 and not requires_approval

        return ReadinessResult(
            ready=ready,
            gate_results=gate_results,
            blocking_issues=blocking_issues,
            warnings=warnings,
            requires_approval=requires_approval,
        )

    def request_approval(
        self,
        release_version: str,
        target_env: str,
        requester: str,
        approvers: Optional[List[str]] = None,
    ) -> ApprovalRequest:
        """
        Request approval for promotion.

        Args:
            release_version: Version to promote
            target_env: Target environment
            requester: Person requesting approval
            approvers: List of required approvers

        Returns:
            Created approval request
        """
        request_id = self._generate_id()

        request = ApprovalRequest(
            id=request_id,
            release_version=release_version,
            target_environment=target_env,
            requester=requester,
            approvers=approvers or [],
        )

        self._approval_requests[request_id] = request
        logger.info(
            f"Approval request created: {request_id} for {release_version} -> {target_env}"
        )
        return request

    def get_approval_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """
        Get approval request by ID.

        Args:
            request_id: Approval request ID

        Returns:
            Approval request or None
        """
        return self._approval_requests.get(request_id)

    def list_pending_approvals(
        self,
        target_env: Optional[str] = None,
    ) -> List[ApprovalRequest]:
        """
        List pending approval requests.

        Args:
            target_env: Optional filter by target environment

        Returns:
            List of pending approval requests
        """
        pending = [
            r for r in self._approval_requests.values()
            if r.status == ApprovalStatus.PENDING
        ]

        if target_env:
            pending = [r for r in pending if r.target_environment == target_env]

        return pending

    def approve(
        self,
        request_id: str,
        approver: str,
    ) -> bool:
        """
        Approve a promotion request.

        Args:
            request_id: Approval request ID
            approver: Approver identifier

        Returns:
            True if fully approved
        """
        request = self._approval_requests.get(request_id)
        if not request:
            logger.error(f"Approval request not found: {request_id}")
            return False

        return request.approve(approver)

    def reject(
        self,
        request_id: str,
        rejector: str,
        reason: str,
    ) -> bool:
        """
        Reject a promotion request.

        Args:
            request_id: Approval request ID
            rejector: Rejector identifier
            reason: Rejection reason

        Returns:
            True if rejection successful
        """
        request = self._approval_requests.get(request_id)
        if not request:
            logger.error(f"Approval request not found: {request_id}")
            return False

        request.reject(rejector, reason)
        return True

    def promote(
        self,
        release_version: str,
        source_env: str,
        target_env: str,
        initiated_by: str,
        approval_request_id: Optional[str] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> PromotionResult:
        """
        Execute environment promotion.

        Args:
            release_version: Version to promote
            source_env: Source environment
            target_env: Target environment
            initiated_by: Person initiating promotion
            approval_request_id: Optional approval request ID
            metrics: Optional metrics for gate evaluation

        Returns:
            Promotion result
        """
        promotion_id = self._generate_id()

        record = PromotionRecord(
            id=promotion_id,
            release_version=release_version,
            source_environment=source_env,
            target_environment=target_env,
            status="in_progress",
            initiated_by=initiated_by,
            approval_request_id=approval_request_id,
        )

        # Check readiness
        readiness = self.check_promotion_readiness(
            release_version, source_env, target_env, metrics
        )

        record.gate_results = readiness.gate_results

        if not readiness.ready:
            record.status = "failed"
            record.completed_at = datetime.utcnow()
            record.error_message = "; ".join(readiness.blocking_issues)
            self._promotion_history.append(record)

            logger.error(f"Promotion failed: {record.error_message}")
            return PromotionResult(
                success=False,
                promotion_record=record,
                error_message=record.error_message,
            )

        # Execute promotion (placeholder for actual deployment logic)
        record.status = "completed"
        record.completed_at = datetime.utcnow()
        self._promotion_history.append(record)

        logger.info(
            f"Promotion completed: {release_version} from {source_env} to {target_env}"
        )

        return PromotionResult(
            success=True,
            promotion_record=record,
        )

    def get_promotion_history(
        self,
        environment: Optional[str] = None,
        limit: int = 50,
    ) -> List[PromotionRecord]:
        """
        Get promotion history.

        Args:
            environment: Optional filter by target environment
            limit: Maximum records to return

        Returns:
            List of promotion records
        """
        history = self._promotion_history.copy()

        if environment:
            history = [r for r in history if r.target_environment == environment]

        return history[-limit:]

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary."""
        return {
            "quality_gates": {
                path: {name: {"name": gate.name, "manual_approval": gate.manual_approval}
                       for name, gate in gates.items()}
                for path, gates in self._quality_gates.items()
            },
            "pending_approvals": len(self.list_pending_approvals()),
            "promotion_history_count": len(self._promotion_history),
        }
