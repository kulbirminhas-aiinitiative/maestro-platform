"""
Environment Promotion Policies.

Controls promotion between environments with approval workflows.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional


class ApprovalStatus(str, Enum):
    """Approval status."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


@dataclass
class ApprovalRequirement:
    """Requirement for promotion approval."""
    role: str
    count: int = 1
    mandatory: bool = True
    timeout_hours: int = 24

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "role": self.role,
            "count": self.count,
            "mandatory": self.mandatory,
            "timeout_hours": self.timeout_hours
        }


@dataclass
class Approval:
    """Single approval record."""
    id: str
    approver: str
    role: str
    status: ApprovalStatus
    created_at: datetime
    decided_at: Optional[datetime] = None
    comment: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "approver": self.approver,
            "role": self.role,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "comment": self.comment
        }


@dataclass
class PromotionPolicy:
    """Policy governing environment promotions."""
    environment: str
    approval_required: bool = False
    requirements: list[ApprovalRequirement] = field(default_factory=list)
    allowed_source_environments: list[str] = field(default_factory=list)
    freeze_windows: list[dict[str, str]] = field(default_factory=list)
    auto_promote_on_success: bool = False

    def add_requirement(self, requirement: ApprovalRequirement) -> None:
        """Add approval requirement."""
        self.requirements.append(requirement)

    def add_freeze_window(self, start: str, end: str, reason: str = "") -> None:
        """Add deployment freeze window."""
        self.freeze_windows.append({
            "start": start,
            "end": end,
            "reason": reason
        })

    def is_frozen(self, at_time: Optional[datetime] = None) -> bool:
        """Check if environment is in freeze window."""
        check_time = at_time or datetime.utcnow()
        for window in self.freeze_windows:
            start = datetime.fromisoformat(window["start"])
            end = datetime.fromisoformat(window["end"])
            if start <= check_time <= end:
                return True
        return False

    def validate_source(self, source: str) -> bool:
        """Validate promotion source environment."""
        if not self.allowed_source_environments:
            return True
        return source in self.allowed_source_environments

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "environment": self.environment,
            "approval_required": self.approval_required,
            "requirements": [r.to_dict() for r in self.requirements],
            "allowed_source_environments": self.allowed_source_environments,
            "freeze_windows": self.freeze_windows,
            "auto_promote_on_success": self.auto_promote_on_success
        }


class PromotionWorkflow:
    """Manages promotion workflow with approvals."""

    def __init__(self, policy: PromotionPolicy):
        self.policy = policy
        self._approvals: dict[str, list[Approval]] = {}

    async def request_promotion(
        self,
        promotion_id: str,
        requested_by: str
    ) -> dict[str, Any]:
        """Request promotion, initiating approval workflow."""
        self._approvals[promotion_id] = []

        if not self.policy.approval_required:
            return {
                "status": "approved",
                "message": "No approval required",
                "can_proceed": True
            }

        return {
            "status": "pending_approval",
            "requirements": [r.to_dict() for r in self.policy.requirements],
            "can_proceed": False
        }

    async def approve(
        self,
        promotion_id: str,
        approver: str,
        role: str,
        comment: str = ""
    ) -> Approval:
        """Record approval."""
        import uuid
        approval = Approval(
            id=str(uuid.uuid4()),
            approver=approver,
            role=role,
            status=ApprovalStatus.APPROVED,
            created_at=datetime.utcnow(),
            decided_at=datetime.utcnow(),
            comment=comment
        )

        if promotion_id not in self._approvals:
            self._approvals[promotion_id] = []
        self._approvals[promotion_id].append(approval)

        return approval

    async def reject(
        self,
        promotion_id: str,
        rejector: str,
        role: str,
        reason: str
    ) -> Approval:
        """Record rejection."""
        import uuid
        approval = Approval(
            id=str(uuid.uuid4()),
            approver=rejector,
            role=role,
            status=ApprovalStatus.REJECTED,
            created_at=datetime.utcnow(),
            decided_at=datetime.utcnow(),
            comment=reason
        )

        if promotion_id not in self._approvals:
            self._approvals[promotion_id] = []
        self._approvals[promotion_id].append(approval)

        return approval

    def check_requirements(self, promotion_id: str) -> dict[str, Any]:
        """Check if all approval requirements are met."""
        approvals = self._approvals.get(promotion_id, [])

        # Check for any rejections
        rejections = [a for a in approvals if a.status == ApprovalStatus.REJECTED]
        if rejections:
            return {
                "met": False,
                "status": "rejected",
                "reason": rejections[0].comment
            }

        # Check all requirements
        for requirement in self.policy.requirements:
            approved_count = sum(
                1 for a in approvals
                if a.role == requirement.role and a.status == ApprovalStatus.APPROVED
            )
            if approved_count < requirement.count:
                if requirement.mandatory:
                    return {
                        "met": False,
                        "status": "pending",
                        "missing": {
                            "role": requirement.role,
                            "needed": requirement.count - approved_count
                        }
                    }

        return {"met": True, "status": "approved"}
