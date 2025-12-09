#!/usr/bin/env python3
"""
Exception Handler: Policy exception workflow management.

Handles requests for policy exceptions with approval tracking.
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from .approval_engine import ApprovalEngine, ApprovalRequest, ApprovalStatus

logger = logging.getLogger(__name__)


@dataclass
class PolicyException:
    """A policy exception request."""
    id: str
    policy_id: str
    resource: str
    action: str
    requester_id: str
    reason: str
    risk_assessment: str
    duration_days: int
    approval_request_id: Optional[str] = None
    status: str = "pending"  # pending, approved, rejected, expired
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_active(self) -> bool:
        """Check if exception is currently active."""
        if self.status != 'approved':
            return False
        if self.expires_at:
            expires = datetime.fromisoformat(self.expires_at.replace('Z', '+00:00').replace('+00:00', ''))
            if datetime.utcnow() > expires:
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExceptionHandler:
    """Handles policy exception workflows."""

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        approval_engine: Optional[ApprovalEngine] = None
    ):
        self.storage_dir = Path(storage_dir) if storage_dir else \
            Path.home() / '.maestro' / 'exceptions'
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.approval_engine = approval_engine or ApprovalEngine()
        self._exceptions: Dict[str, PolicyException] = {}
        self._exception_counter = 0

    def request_exception(
        self,
        policy_id: str,
        resource: str,
        action: str,
        requester_id: str,
        reason: str,
        risk_assessment: str,
        duration_days: int = 30
    ) -> PolicyException:
        """Request a policy exception."""
        self._exception_counter += 1
        exception_id = f"EXC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._exception_counter:04d}"

        exception = PolicyException(
            id=exception_id,
            policy_id=policy_id,
            resource=resource,
            action=action,
            requester_id=requester_id,
            reason=reason,
            risk_assessment=risk_assessment,
            duration_days=duration_days
        )

        self._exceptions[exception_id] = exception
        self._save_exception(exception)

        logger.info(f"Exception requested: {exception_id} for {resource}/{action}")

        return exception

    def approve_exception(
        self,
        exception_id: str,
        approver_id: str,
        duration_days: Optional[int] = None
    ) -> Optional[PolicyException]:
        """Approve a policy exception."""
        exception = self._exceptions.get(exception_id)
        if not exception or exception.status != 'pending':
            return None

        days = duration_days or exception.duration_days
        expires_at = (datetime.utcnow() + timedelta(days=days)).isoformat()

        exception.status = 'approved'
        exception.approved_by = approver_id
        exception.approved_at = datetime.utcnow().isoformat()
        exception.expires_at = expires_at

        self._save_exception(exception)

        logger.info(f"Exception approved: {exception_id} by {approver_id}")

        return exception

    def reject_exception(
        self,
        exception_id: str,
        rejector_id: str,
        reason: Optional[str] = None
    ) -> Optional[PolicyException]:
        """Reject a policy exception."""
        exception = self._exceptions.get(exception_id)
        if not exception or exception.status != 'pending':
            return None

        exception.status = 'rejected'
        exception.metadata['rejected_by'] = rejector_id
        exception.metadata['rejection_reason'] = reason

        self._save_exception(exception)

        return exception

    def check_exception(
        self,
        policy_id: str,
        resource: str,
        action: str
    ) -> Optional[PolicyException]:
        """Check if an active exception exists."""
        for exception in self._exceptions.values():
            if (exception.policy_id == policy_id and
                exception.resource == resource and
                exception.action == action and
                exception.is_active()):
                return exception
        return None

    def get_exceptions(
        self,
        status: Optional[str] = None,
        requester_id: Optional[str] = None
    ) -> List[PolicyException]:
        """Get exceptions with filters."""
        exceptions = list(self._exceptions.values())

        if status:
            exceptions = [e for e in exceptions if e.status == status]
        if requester_id:
            exceptions = [e for e in exceptions if e.requester_id == requester_id]

        return sorted(exceptions, key=lambda e: e.created_at, reverse=True)

    def _save_exception(self, exception: PolicyException):
        """Save exception to storage."""
        file_path = self.storage_dir / f"{exception.id}.json"
        with open(file_path, 'w') as f:
            json.dump(exception.to_dict(), f, indent=2)


def get_exception_handler(**kwargs) -> ExceptionHandler:
    """Get exception handler instance."""
    return ExceptionHandler(**kwargs)
