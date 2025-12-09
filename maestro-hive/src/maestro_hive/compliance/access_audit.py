#!/usr/bin/env python3
"""
Access Audit: Access logging and audit trail for RBAC.

Logs all access checks for compliance auditing and reporting.
"""

import json
import logging
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from .rbac_engine import RBACEngine, AccessCheckResult

logger = logging.getLogger(__name__)


@dataclass
class AccessAuditEntry:
    """An access audit log entry."""
    id: str
    principal_id: str
    resource: str
    action: str
    allowed: bool
    roles: List[str]
    permissions: List[str]
    reason: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    duration_ms: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AccessAuditor:
    """Audit logger for access control events."""

    def __init__(
        self,
        storage_dir: Optional[str] = None,
        rbac_engine: Optional[RBACEngine] = None
    ):
        self.storage_dir = Path(storage_dir) if storage_dir else \
            Path.home() / '.maestro' / 'access_audit'
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.rbac_engine = rbac_engine
        self._entry_counter = 0
        self._entries: List[AccessAuditEntry] = []

        # Register as audit callback if rbac_engine provided
        if rbac_engine:
            rbac_engine.audit_callback = self.log_access_check

    def log_access_check(self, result: AccessCheckResult) -> AccessAuditEntry:
        """Log an access check result."""
        self._entry_counter += 1
        entry_id = f"ACC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._entry_counter:06d}"

        entry = AccessAuditEntry(
            id=entry_id,
            principal_id=result.principal_id,
            resource=result.resource,
            action=result.action,
            allowed=result.allowed,
            roles=result.matched_roles,
            permissions=result.matched_permissions,
            reason=result.reason,
            duration_ms=result.duration_ms
        )

        self._entries.append(entry)
        self._persist_entry(entry)

        return entry

    def log_access(
        self,
        principal_id: str,
        resource: str,
        action: str,
        allowed: bool,
        reason: str = "",
        **metadata
    ) -> AccessAuditEntry:
        """Log an access event directly."""
        self._entry_counter += 1
        entry_id = f"ACC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._entry_counter:06d}"

        entry = AccessAuditEntry(
            id=entry_id,
            principal_id=principal_id,
            resource=resource,
            action=action,
            allowed=allowed,
            roles=[],
            permissions=[],
            reason=reason,
            context=metadata
        )

        self._entries.append(entry)
        self._persist_entry(entry)

        return entry

    def query(
        self,
        principal_id: Optional[str] = None,
        resource: Optional[str] = None,
        allowed: Optional[bool] = None,
        since: Optional[str] = None,
        limit: int = 100
    ) -> List[AccessAuditEntry]:
        """Query access audit logs."""
        results = list(self._entries)

        if principal_id:
            results = [e for e in results if e.principal_id == principal_id]
        if resource:
            results = [e for e in results if resource in e.resource]
        if allowed is not None:
            results = [e for e in results if e.allowed == allowed]

        return sorted(results, key=lambda e: e.timestamp, reverse=True)[:limit]

    def get_user_access_report(self, principal_id: str) -> Dict[str, Any]:
        """Generate access report for a user."""
        entries = self.query(principal_id=principal_id, limit=1000)

        return {
            'principal_id': principal_id,
            'total_access_checks': len(entries),
            'allowed_count': sum(1 for e in entries if e.allowed),
            'denied_count': sum(1 for e in entries if not e.allowed),
            'resources_accessed': list(set(e.resource for e in entries if e.allowed)),
            'recent_denials': [e.to_dict() for e in entries if not e.allowed][:10]
        }

    def _persist_entry(self, entry: AccessAuditEntry):
        """Persist entry to storage."""
        date_str = entry.timestamp[:10]
        file_path = self.storage_dir / f"access_{date_str}.jsonl"

        with open(file_path, 'a') as f:
            f.write(json.dumps(entry.to_dict()) + '\n')


def get_access_auditor(**kwargs) -> AccessAuditor:
    """Get access auditor instance."""
    return AccessAuditor(**kwargs)
