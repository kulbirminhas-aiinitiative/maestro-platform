#!/usr/bin/env python3
"""
Approval Audit: Audit trail for approval decisions.

Tracks all approval decisions for compliance reporting.
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from .approval_engine import ApprovalRequest, ApprovalStatus

logger = logging.getLogger(__name__)


@dataclass
class ApprovalAuditEntry:
    """An approval audit trail entry."""
    id: str
    request_id: str
    event_type: str  # created, approved, rejected, expired, cancelled
    actor: str
    resource: str
    action: str
    decision: Optional[str] = None
    comment: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ApprovalAuditor:
    """Audit logger for approval decisions."""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir) if storage_dir else \
            Path.home() / '.maestro' / 'approval_audit'
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._entry_counter = 0
        self._entries: List[ApprovalAuditEntry] = []

    def log_request_created(self, request: ApprovalRequest) -> ApprovalAuditEntry:
        """Log approval request creation."""
        return self._log_event(
            request_id=request.id,
            event_type='created',
            actor=request.requester_id,
            resource=request.resource,
            action=request.action,
            metadata={'approval_type': request.approval_type.value}
        )

    def log_decision(
        self,
        request: ApprovalRequest,
        decision: str,
        decider: str,
        comment: Optional[str] = None
    ) -> ApprovalAuditEntry:
        """Log approval/rejection decision."""
        return self._log_event(
            request_id=request.id,
            event_type=decision,
            actor=decider,
            resource=request.resource,
            action=request.action,
            decision=decision,
            comment=comment
        )

    def log_status_change(
        self,
        request: ApprovalRequest,
        new_status: str,
        actor: str = 'system'
    ) -> ApprovalAuditEntry:
        """Log status change (expired, cancelled)."""
        return self._log_event(
            request_id=request.id,
            event_type=new_status,
            actor=actor,
            resource=request.resource,
            action=request.action
        )

    def _log_event(
        self,
        request_id: str,
        event_type: str,
        actor: str,
        resource: str,
        action: str,
        decision: Optional[str] = None,
        comment: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> ApprovalAuditEntry:
        """Create an audit entry."""
        self._entry_counter += 1
        entry_id = f"APR-AUD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._entry_counter:04d}"

        entry = ApprovalAuditEntry(
            id=entry_id,
            request_id=request_id,
            event_type=event_type,
            actor=actor,
            resource=resource,
            action=action,
            decision=decision,
            comment=comment,
            metadata=metadata or {}
        )

        self._entries.append(entry)
        self._persist_entry(entry)

        logger.info(f"Audit: {event_type} for {request_id} by {actor}")

        return entry

    def query(
        self,
        request_id: Optional[str] = None,
        actor: Optional[str] = None,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[ApprovalAuditEntry]:
        """Query audit entries."""
        results = list(self._entries)

        if request_id:
            results = [e for e in results if e.request_id == request_id]
        if actor:
            results = [e for e in results if e.actor == actor]
        if event_type:
            results = [e for e in results if e.event_type == event_type]

        return sorted(results, key=lambda e: e.timestamp, reverse=True)[:limit]

    def get_request_history(self, request_id: str) -> List[ApprovalAuditEntry]:
        """Get full audit history for a request."""
        return [e for e in self._entries if e.request_id == request_id]

    def _persist_entry(self, entry: ApprovalAuditEntry):
        """Persist entry to storage."""
        date_str = entry.timestamp[:10]
        file_path = self.storage_dir / f"approval_{date_str}.jsonl"

        with open(file_path, 'a') as f:
            f.write(json.dumps(entry.to_dict()) + '\n')


def get_approval_auditor(**kwargs) -> ApprovalAuditor:
    """Get approval auditor instance."""
    return ApprovalAuditor(**kwargs)
