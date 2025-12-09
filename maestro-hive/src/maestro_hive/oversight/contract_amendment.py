"""
Contract Amendment Service
AC-4: Allow contract amendment/renegotiation
EU AI Act Article 14 - Human control over AI contracts
EPIC: MD-2158
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .compliance_logger import ComplianceLogger, ComplianceContext


class AmendmentStatus(Enum):
    """Contract amendment status."""
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    APPLIED = "applied"


@dataclass
class ContractChange:
    """Single change in a contract amendment."""
    field: str
    old_value: Any
    new_value: Any
    change_type: str  # add, modify, remove

    def to_dict(self) -> Dict[str, Any]:
        return {
            "field": self.field,
            "old_value": str(self.old_value),
            "new_value": str(self.new_value),
            "change_type": self.change_type,
        }


@dataclass
class ContractAmendmentRequest:
    """Request to amend a contract."""
    contract_id: str
    amendments: List[ContractChange]
    requester_id: str
    reason: str
    context: Optional[ComplianceContext] = None


@dataclass
class ContractAmendment:
    """Contract amendment record."""
    id: str
    contract_id: str
    amendments: List[ContractChange]
    requester_id: str
    reason: str
    status: AmendmentStatus
    approver_id: Optional[str] = None
    approval_comments: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    approved_at: Optional[datetime] = None
    applied_at: Optional[datetime] = None
    audit_log_id: str = ""


class ContractAmendmentService:
    """
    Contract Amendment Service
    Allows human review and modification of AI-generated contracts.
    EU AI Act Article 14 compliant human control mechanism.
    """

    def __init__(
        self,
        logger: ComplianceLogger,
        db_client: Optional[Any] = None
    ):
        """
        Initialize contract amendment service.

        Args:
            logger: Compliance logger for audit trail
            db_client: Optional database client
        """
        self._logger = logger
        self._db = db_client
        self._amendments: Dict[str, ContractAmendment] = {}
        self._contracts: Dict[str, Dict[str, Any]] = {}

    def _generate_amendment_id(self) -> str:
        """Generate unique amendment ID."""
        return f"amend_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def register_contract(self, contract_id: str, contract_data: Dict[str, Any]) -> None:
        """Register a contract for amendment tracking."""
        self._contracts[contract_id] = contract_data

    async def create_amendment(self, request: ContractAmendmentRequest) -> ContractAmendment:
        """
        Create a new contract amendment request.

        Args:
            request: Amendment request details

        Returns:
            Created ContractAmendment
        """
        amendment_id = self._generate_amendment_id()

        amendment = ContractAmendment(
            id=amendment_id,
            contract_id=request.contract_id,
            amendments=request.amendments,
            requester_id=request.requester_id,
            reason=request.reason,
            status=AmendmentStatus.DRAFT,
        )

        # Log to audit
        audit_entry = await self._logger.log_amendment(
            request.requester_id,
            request.contract_id,
            len(request.amendments),
            request.reason,
            AmendmentStatus.DRAFT.value,
            request.context
        )
        amendment.audit_log_id = audit_entry.id

        # Store amendment
        self._amendments[amendment_id] = amendment

        return amendment

    async def submit_for_approval(self, amendment_id: str) -> bool:
        """
        Submit amendment for approval.

        Args:
            amendment_id: Amendment to submit

        Returns:
            True if submitted, False if not found or wrong status
        """
        amendment = self._amendments.get(amendment_id)
        if not amendment:
            return False

        if amendment.status != AmendmentStatus.DRAFT:
            return False

        amendment.status = AmendmentStatus.PENDING_APPROVAL

        return True

    async def approve_amendment(
        self,
        amendment_id: str,
        approver_id: str,
        comments: Optional[str] = None
    ) -> bool:
        """
        Approve a contract amendment.

        Args:
            amendment_id: Amendment to approve
            approver_id: User approving
            comments: Optional approval comments

        Returns:
            True if approved, False if not found or wrong status
        """
        amendment = self._amendments.get(amendment_id)
        if not amendment:
            return False

        if amendment.status != AmendmentStatus.PENDING_APPROVAL:
            return False

        amendment.status = AmendmentStatus.APPROVED
        amendment.approver_id = approver_id
        amendment.approval_comments = comments
        amendment.approved_at = datetime.utcnow()

        # Log approval
        from .compliance_logger import OversightActionType
        await self._logger.log_action(
            OversightActionType.APPROVE,
            approver_id,
            amendment.contract_id,
            {
                "action_type": "contract_amendment_approval",
                "amendment_id": amendment_id,
                "comments": comments,
            }
        )

        return True

    async def reject_amendment(
        self,
        amendment_id: str,
        rejector_id: str,
        reason: str
    ) -> bool:
        """
        Reject a contract amendment.

        Args:
            amendment_id: Amendment to reject
            rejector_id: User rejecting
            reason: Rejection reason

        Returns:
            True if rejected, False if not found or wrong status
        """
        amendment = self._amendments.get(amendment_id)
        if not amendment:
            return False

        if amendment.status != AmendmentStatus.PENDING_APPROVAL:
            return False

        amendment.status = AmendmentStatus.REJECTED
        amendment.approver_id = rejector_id
        amendment.approval_comments = reason

        # Log rejection
        from .compliance_logger import OversightActionType
        await self._logger.log_action(
            OversightActionType.REJECT,
            rejector_id,
            amendment.contract_id,
            {
                "action_type": "contract_amendment_rejection",
                "amendment_id": amendment_id,
                "reason": reason,
            }
        )

        return True

    async def apply_amendment(self, amendment_id: str) -> bool:
        """
        Apply an approved amendment to the contract.

        Args:
            amendment_id: Amendment to apply

        Returns:
            True if applied, False if not found or not approved
        """
        amendment = self._amendments.get(amendment_id)
        if not amendment:
            return False

        if amendment.status != AmendmentStatus.APPROVED:
            return False

        # Apply changes to contract if registered
        contract = self._contracts.get(amendment.contract_id)
        if contract:
            for change in amendment.amendments:
                if change.change_type == "remove":
                    contract.pop(change.field, None)
                else:
                    contract[change.field] = change.new_value

        amendment.status = AmendmentStatus.APPLIED
        amendment.applied_at = datetime.utcnow()

        return True

    def get_pending_amendments(
        self,
        contract_id: Optional[str] = None
    ) -> List[ContractAmendment]:
        """
        Get pending amendments.

        Args:
            contract_id: Optional filter by contract

        Returns:
            List of pending amendments
        """
        pending = []
        for amendment in self._amendments.values():
            if amendment.status == AmendmentStatus.PENDING_APPROVAL:
                if contract_id is None or amendment.contract_id == contract_id:
                    pending.append(amendment)
        return pending

    def get_amendment(self, amendment_id: str) -> Optional[ContractAmendment]:
        """Get a specific amendment by ID."""
        return self._amendments.get(amendment_id)

    def get_contract_history(self, contract_id: str) -> List[ContractAmendment]:
        """Get amendment history for a contract."""
        return [a for a in self._amendments.values() if a.contract_id == contract_id]

    def get_statistics(self) -> Dict[str, Any]:
        """Get amendment statistics."""
        by_status = {status.value: 0 for status in AmendmentStatus}

        for amendment in self._amendments.values():
            by_status[amendment.status.value] += 1

        return {
            "total_amendments": len(self._amendments),
            "by_status": by_status,
            "contracts_tracked": len(self._contracts),
        }
