"""
Human Approval Gate for Persona Evolution.

EPIC: MD-2556
AC-2: Human approval required before persona changes applied.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from .models import ImprovementSuggestion, SuggestionStatus

logger = logging.getLogger(__name__)


class ApprovalDecision(Enum):
    """Approval decision types."""
    APPROVED = "approved"
    REJECTED = "rejected"
    DEFERRED = "deferred"


@dataclass
class ApprovalRequest:
    """
    A request for human approval.

    AC-2: Human approval required before persona changes applied.
    """
    request_id: str
    suggestion: ImprovementSuggestion
    requested_at: datetime = field(default_factory=datetime.utcnow)
    requested_by: str = "system"
    priority: int = 0  # Higher = more urgent
    notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    decision: Optional[ApprovalDecision] = None
    review_notes: Optional[str] = None

    def approve(self, reviewer: str, notes: Optional[str] = None) -> None:
        """Approve this request."""
        self.reviewed_by = reviewer
        self.reviewed_at = datetime.utcnow()
        self.decision = ApprovalDecision.APPROVED
        self.review_notes = notes
        self.suggestion.approve(reviewer)

    def reject(self, reviewer: str, reason: str) -> None:
        """Reject this request."""
        self.reviewed_by = reviewer
        self.reviewed_at = datetime.utcnow()
        self.decision = ApprovalDecision.REJECTED
        self.review_notes = reason
        self.suggestion.reject(reason)

    def defer(self, reviewer: str, notes: Optional[str] = None) -> None:
        """Defer this request for later review."""
        self.reviewed_by = reviewer
        self.reviewed_at = datetime.utcnow()
        self.decision = ApprovalDecision.DEFERRED
        self.review_notes = notes

    @property
    def is_pending(self) -> bool:
        """Check if request is still pending."""
        return self.decision is None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "request_id": self.request_id,
            "suggestion": self.suggestion.to_dict(),
            "requested_at": self.requested_at.isoformat(),
            "requested_by": self.requested_by,
            "priority": self.priority,
            "notes": self.notes,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "decision": self.decision.value if self.decision else None,
            "review_notes": self.review_notes,
        }


class ApprovalGate:
    """
    Gate for human approval of persona changes.

    AC-2: Human approval required before persona changes applied.

    All persona modifications must pass through this gate for human review.
    No automatic changes are applied without explicit approval.
    """

    def __init__(
        self,
        on_approval: Optional[Callable[[ApprovalRequest], None]] = None,
        on_rejection: Optional[Callable[[ApprovalRequest], None]] = None,
        auto_approve_threshold: Optional[float] = None,  # None = always require approval
    ):
        """
        Initialize the approval gate.

        Args:
            on_approval: Callback when request is approved
            on_rejection: Callback when request is rejected
            auto_approve_threshold: Confidence threshold for auto-approval (None = disabled)
        """
        self._pending: Dict[str, ApprovalRequest] = {}
        self._history: List[ApprovalRequest] = []
        self._on_approval = on_approval
        self._on_rejection = on_rejection
        self._auto_approve_threshold = auto_approve_threshold

        # Statistics
        self._total_requests = 0
        self._approved_count = 0
        self._rejected_count = 0

        logger.info("ApprovalGate initialized (human approval required for all changes)")

    def submit(
        self,
        suggestion: ImprovementSuggestion,
        requested_by: str = "system",
        priority: int = 0,
        notes: Optional[str] = None,
    ) -> ApprovalRequest:
        """
        Submit a suggestion for approval.

        Args:
            suggestion: The improvement suggestion
            requested_by: Who requested this change
            priority: Priority level (higher = more urgent)
            notes: Additional notes

        Returns:
            The approval request
        """
        request_id = f"apr_{suggestion.suggestion_id}"

        request = ApprovalRequest(
            request_id=request_id,
            suggestion=suggestion,
            requested_by=requested_by,
            priority=priority,
            notes=notes,
        )

        self._pending[request_id] = request
        self._total_requests += 1

        logger.info(
            f"Submitted approval request {request_id} for suggestion {suggestion.suggestion_id}"
        )

        # Check for auto-approval (if enabled and confidence is high enough)
        if (
            self._auto_approve_threshold is not None
            and suggestion.confidence >= self._auto_approve_threshold
        ):
            logger.info(f"Auto-approving request {request_id} (confidence: {suggestion.confidence})")
            self.approve(request_id, "auto-approval-system", "Auto-approved due to high confidence")

        return request

    def approve(
        self,
        request_id: str,
        reviewer: str,
        notes: Optional[str] = None,
    ) -> ApprovalRequest:
        """
        Approve a request.

        Args:
            request_id: ID of the request to approve
            reviewer: Who is approving
            notes: Approval notes

        Returns:
            The approved request

        Raises:
            ValueError: If request not found or already reviewed
        """
        if request_id not in self._pending:
            raise ValueError(f"Request {request_id} not found or already reviewed")

        request = self._pending.pop(request_id)
        request.approve(reviewer, notes)

        self._history.append(request)
        self._approved_count += 1

        logger.info(f"Request {request_id} approved by {reviewer}")

        if self._on_approval:
            try:
                self._on_approval(request)
            except Exception as e:
                logger.error(f"Approval callback failed: {e}")

        return request

    def reject(
        self,
        request_id: str,
        reviewer: str,
        reason: str,
    ) -> ApprovalRequest:
        """
        Reject a request.

        Args:
            request_id: ID of the request to reject
            reviewer: Who is rejecting
            reason: Reason for rejection

        Returns:
            The rejected request

        Raises:
            ValueError: If request not found or already reviewed
        """
        if request_id not in self._pending:
            raise ValueError(f"Request {request_id} not found or already reviewed")

        request = self._pending.pop(request_id)
        request.reject(reviewer, reason)

        self._history.append(request)
        self._rejected_count += 1

        logger.info(f"Request {request_id} rejected by {reviewer}: {reason}")

        if self._on_rejection:
            try:
                self._on_rejection(request)
            except Exception as e:
                logger.error(f"Rejection callback failed: {e}")

        return request

    def defer(
        self,
        request_id: str,
        reviewer: str,
        notes: Optional[str] = None,
    ) -> ApprovalRequest:
        """
        Defer a request for later review.

        Args:
            request_id: ID of the request to defer
            reviewer: Who is deferring
            notes: Notes about why deferred

        Returns:
            The deferred request
        """
        if request_id not in self._pending:
            raise ValueError(f"Request {request_id} not found")

        request = self._pending[request_id]
        request.defer(reviewer, notes)

        logger.info(f"Request {request_id} deferred by {reviewer}")

        return request

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get a request by ID."""
        return self._pending.get(request_id)

    def get_pending(
        self,
        persona_id: Optional[str] = None,
    ) -> List[ApprovalRequest]:
        """
        Get all pending requests.

        Args:
            persona_id: Filter by persona (optional)

        Returns:
            List of pending requests, sorted by priority
        """
        requests = list(self._pending.values())

        if persona_id:
            requests = [r for r in requests if r.suggestion.persona_id == persona_id]

        # Sort by priority (descending) then by requested_at (ascending)
        requests.sort(key=lambda r: (-r.priority, r.requested_at))

        return requests

    def get_history(
        self,
        persona_id: Optional[str] = None,
        decision: Optional[ApprovalDecision] = None,
        limit: int = 100,
    ) -> List[ApprovalRequest]:
        """
        Get approval history.

        Args:
            persona_id: Filter by persona
            decision: Filter by decision type
            limit: Maximum results

        Returns:
            List of historical requests
        """
        history = self._history.copy()

        if persona_id:
            history = [r for r in history if r.suggestion.persona_id == persona_id]

        if decision:
            history = [r for r in history if r.decision == decision]

        # Sort by reviewed_at descending
        history.sort(key=lambda r: r.reviewed_at or r.requested_at, reverse=True)

        return history[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get approval gate statistics."""
        return {
            "total_requests": self._total_requests,
            "pending_count": len(self._pending),
            "approved_count": self._approved_count,
            "rejected_count": self._rejected_count,
            "approval_rate": (
                self._approved_count / (self._approved_count + self._rejected_count)
                if (self._approved_count + self._rejected_count) > 0
                else 0.0
            ),
        }

    def clear_pending(self, persona_id: Optional[str] = None) -> int:
        """Clear pending requests."""
        if persona_id:
            to_remove = [
                k for k, v in self._pending.items()
                if v.suggestion.persona_id == persona_id
            ]
            for key in to_remove:
                del self._pending[key]
            return len(to_remove)
        else:
            count = len(self._pending)
            self._pending = {}
            return count
