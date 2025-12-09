"""
Critical Decision Service
AC-6: Implement human approval for critical decisions
EU AI Act Article 14 - Human oversight for high-risk decisions
EPIC: MD-2158
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from .compliance_logger import ComplianceLogger, ComplianceContext


class DecisionRiskLevel(Enum):
    """Risk level of a decision."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ApprovalStatus(Enum):
    """Status of a decision approval."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    AUTO_APPROVED = "auto_approved"


@dataclass
class CriticalDecision:
    """Critical decision requiring human approval."""
    id: str
    decision_type: str
    description: str
    risk_level: DecisionRiskLevel
    context: Dict[str, Any]
    required_approvers: int
    expires_at: datetime
    status: ApprovalStatus
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
    ai_recommendation: Optional[str] = None
    ai_confidence: float = 0.0


@dataclass
class DecisionApproval:
    """Approval record for a decision."""
    id: str
    decision_id: str
    approved: bool
    comments: str
    approver_id: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    audit_log_id: str = ""


class CriticalDecisionService:
    """
    Critical Decision Service
    Requires human approval for high-risk AI decisions.
    EU AI Act Article 14 compliant human oversight mechanism.
    """

    # Required approvers by risk level
    RISK_APPROVERS = {
        DecisionRiskLevel.LOW: 1,
        DecisionRiskLevel.MEDIUM: 1,
        DecisionRiskLevel.HIGH: 2,
        DecisionRiskLevel.CRITICAL: 3,
    }

    # Expiry hours by risk level
    RISK_EXPIRY_HOURS = {
        DecisionRiskLevel.LOW: 72,
        DecisionRiskLevel.MEDIUM: 48,
        DecisionRiskLevel.HIGH: 24,
        DecisionRiskLevel.CRITICAL: 8,
    }

    def __init__(
        self,
        logger: ComplianceLogger,
        expiry_hours: int = 48,
        db_client: Optional[Any] = None
    ):
        """
        Initialize critical decision service.

        Args:
            logger: Compliance logger for audit trail
            expiry_hours: Default expiry hours for decisions
            db_client: Optional database client
        """
        self._logger = logger
        self._default_expiry_hours = expiry_hours
        self._db = db_client
        self._decisions: Dict[str, CriticalDecision] = {}
        self._approvals: Dict[str, List[DecisionApproval]] = {}

    def _generate_decision_id(self) -> str:
        """Generate unique decision ID."""
        return f"dec_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def _generate_approval_id(self) -> str:
        """Generate unique approval ID."""
        return f"appr_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    async def create_decision(
        self,
        decision_type: str,
        description: str,
        risk_level: DecisionRiskLevel,
        context: Dict[str, Any],
        ai_recommendation: Optional[str] = None,
        ai_confidence: float = 0.0,
        expiry_hours: Optional[int] = None
    ) -> CriticalDecision:
        """
        Create a critical decision requiring approval.

        Args:
            decision_type: Type of decision
            description: Description of the decision
            risk_level: Risk level
            context: Decision context
            ai_recommendation: AI's recommendation
            ai_confidence: AI's confidence score
            expiry_hours: Custom expiry hours

        Returns:
            Created CriticalDecision
        """
        decision_id = self._generate_decision_id()

        # Determine required approvers and expiry
        required_approvers = self.RISK_APPROVERS[risk_level]
        hours = expiry_hours or self.RISK_EXPIRY_HOURS.get(risk_level, self._default_expiry_hours)
        expires_at = datetime.utcnow() + timedelta(hours=hours)

        decision = CriticalDecision(
            id=decision_id,
            decision_type=decision_type,
            description=description,
            risk_level=risk_level,
            context=context,
            required_approvers=required_approvers,
            expires_at=expires_at,
            status=ApprovalStatus.PENDING,
            ai_recommendation=ai_recommendation,
            ai_confidence=ai_confidence,
        )

        # Store decision and initialize approvals list
        self._decisions[decision_id] = decision
        self._approvals[decision_id] = []

        return decision

    async def submit_approval(
        self,
        decision_id: str,
        approver_id: str,
        approved: bool,
        comments: str,
        context: Optional[ComplianceContext] = None
    ) -> Optional[DecisionApproval]:
        """
        Submit an approval or rejection for a decision.

        Args:
            decision_id: Decision to approve/reject
            approver_id: User submitting approval
            approved: True for approval, False for rejection
            comments: Approval comments
            context: Optional compliance context

        Returns:
            Created DecisionApproval or None if invalid
        """
        decision = self._decisions.get(decision_id)
        if not decision:
            return None

        # Check if already resolved
        if decision.status in [ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.EXPIRED]:
            return None

        # Check if expired
        if datetime.utcnow() > decision.expires_at:
            decision.status = ApprovalStatus.EXPIRED
            decision.resolved_at = datetime.utcnow()
            return None

        # Check if approver already voted
        existing_approvals = self._approvals.get(decision_id, [])
        for existing in existing_approvals:
            if existing.approver_id == approver_id:
                return None  # Already voted

        # Create approval record
        approval_id = self._generate_approval_id()
        approval = DecisionApproval(
            id=approval_id,
            decision_id=decision_id,
            approved=approved,
            comments=comments,
            approver_id=approver_id,
        )

        # Log to audit
        audit_entry = await self._logger.log_approval(
            approver_id,
            decision_id,
            approved,
            comments,
            decision.risk_level.value,
            context
        )
        approval.audit_log_id = audit_entry.id

        # Store approval
        existing_approvals.append(approval)
        self._approvals[decision_id] = existing_approvals

        # Check if decision is now resolved
        self._check_decision_resolution(decision)

        return approval

    def _check_decision_resolution(self, decision: CriticalDecision) -> None:
        """Check if a decision has been resolved based on approvals."""
        approvals = self._approvals.get(decision.id, [])

        # Count approvals and rejections
        approval_count = sum(1 for a in approvals if a.approved)
        rejection_count = sum(1 for a in approvals if not a.approved)

        # Any rejection rejects the decision
        if rejection_count > 0:
            decision.status = ApprovalStatus.REJECTED
            decision.resolved_at = datetime.utcnow()
            return

        # Check if enough approvals
        if approval_count >= decision.required_approvers:
            decision.status = ApprovalStatus.APPROVED
            decision.resolved_at = datetime.utcnow()

    def get_decision_status(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a decision."""
        decision = self._decisions.get(decision_id)
        if not decision:
            return None

        approvals = self._approvals.get(decision_id, [])
        approval_count = sum(1 for a in approvals if a.approved)

        return {
            "decision_id": decision.id,
            "decision_type": decision.decision_type,
            "description": decision.description,
            "risk_level": decision.risk_level.value,
            "status": decision.status.value,
            "required_approvers": decision.required_approvers,
            "current_approvals": approval_count,
            "expires_at": decision.expires_at.isoformat(),
            "is_expired": datetime.utcnow() > decision.expires_at,
            "ai_recommendation": decision.ai_recommendation,
            "ai_confidence": decision.ai_confidence,
        }

    def get_pending_decisions(
        self,
        risk_level: Optional[DecisionRiskLevel] = None,
        approver_id: Optional[str] = None
    ) -> List[CriticalDecision]:
        """
        Get pending decisions.

        Args:
            risk_level: Optional filter by risk level
            approver_id: Optional filter out decisions already approved by user

        Returns:
            List of pending decisions
        """
        pending = []
        now = datetime.utcnow()

        for decision in self._decisions.values():
            # Skip if not pending
            if decision.status != ApprovalStatus.PENDING:
                continue

            # Skip if expired
            if now > decision.expires_at:
                decision.status = ApprovalStatus.EXPIRED
                decision.resolved_at = now
                continue

            # Filter by risk level
            if risk_level is not None and decision.risk_level != risk_level:
                continue

            # Filter out if approver already voted
            if approver_id:
                approvals = self._approvals.get(decision.id, [])
                if any(a.approver_id == approver_id for a in approvals):
                    continue

            pending.append(decision)

        # Sort by risk level (critical first) then by expiry
        risk_order = {
            DecisionRiskLevel.CRITICAL: 0,
            DecisionRiskLevel.HIGH: 1,
            DecisionRiskLevel.MEDIUM: 2,
            DecisionRiskLevel.LOW: 3,
        }
        pending.sort(key=lambda d: (risk_order[d.risk_level], d.expires_at))
        return pending

    def get_approvals(self, decision_id: str) -> List[DecisionApproval]:
        """Get all approvals for a decision."""
        return self._approvals.get(decision_id, [])

    def get_decision(self, decision_id: str) -> Optional[CriticalDecision]:
        """Get a specific decision by ID."""
        return self._decisions.get(decision_id)

    def process_expired_decisions(self) -> int:
        """
        Process and mark expired decisions.

        Returns:
            Number of decisions expired
        """
        expired_count = 0
        now = datetime.utcnow()

        for decision in self._decisions.values():
            if decision.status == ApprovalStatus.PENDING and now > decision.expires_at:
                decision.status = ApprovalStatus.EXPIRED
                decision.resolved_at = now
                expired_count += 1

        return expired_count

    def get_statistics(self) -> Dict[str, Any]:
        """Get decision statistics."""
        by_status = {status.value: 0 for status in ApprovalStatus}
        by_risk = {risk.value: 0 for risk in DecisionRiskLevel}

        for decision in self._decisions.values():
            by_status[decision.status.value] += 1
            by_risk[decision.risk_level.value] += 1

        total_approvals = sum(len(approvals) for approvals in self._approvals.values())

        return {
            "total_decisions": len(self._decisions),
            "by_status": by_status,
            "by_risk_level": by_risk,
            "total_approvals": total_approvals,
            "risk_approvers_config": {k.value: v for k, v in self.RISK_APPROVERS.items()},
            "risk_expiry_config": {k.value: v for k, v in self.RISK_EXPIRY_HOURS.items()},
        }
