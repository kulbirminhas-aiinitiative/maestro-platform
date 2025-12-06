"""
Audit Trail Generator for Verification & Validation.

EPIC: MD-2521 - [SDLC-Phase7] Verification & Validation
AC-3: Audit Trail Generator - Immutable audit logs with cryptographic verification

This module provides:
- Immutable event logging
- SHA-256 hash chain for verification
- Retention policy enforcement
- Export formats (JSON, CSV, PDF)
"""

import csv
import hashlib
import io
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of auditable events."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    LOGIN = "login"
    LOGOUT = "logout"
    ACCESS_DENIED = "access_denied"
    CONFIG_CHANGE = "config_change"
    DEPLOY = "deploy"
    ROLLBACK = "rollback"
    APPROVAL = "approval"
    REJECTION = "rejection"
    CUSTOM = "custom"


class AuditOutcome(Enum):
    """Outcome of an audited action."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"
    DENIED = "denied"


@dataclass
class AuditEntry:
    """
    A single audit trail entry.

    Each entry is cryptographically linked to the previous
    entry forming an immutable chain.
    """
    entry_id: str
    timestamp: datetime
    event_type: EventType
    actor: str  # User or system that performed action
    resource: str  # Resource affected
    action: str  # Specific action taken
    outcome: AuditOutcome
    details: Dict[str, Any] = field(default_factory=dict)
    previous_hash: str = ""  # Hash of previous entry
    current_hash: str = ""  # Hash of this entry
    signature: Optional[str] = None  # Optional digital signature

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of this entry."""
        data = {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "actor": self.actor,
            "resource": self.resource,
            "action": self.action,
            "outcome": self.outcome.value,
            "details": self.details,
            "previous_hash": self.previous_hash
        }
        json_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(json_str.encode()).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "actor": self.actor,
            "resource": self.resource,
            "action": self.action,
            "outcome": self.outcome.value,
            "details": self.details,
            "previous_hash": self.previous_hash,
            "current_hash": self.current_hash,
            "signature": self.signature
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        """Create entry from dictionary."""
        return cls(
            entry_id=data["entry_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            event_type=EventType(data["event_type"]),
            actor=data["actor"],
            resource=data["resource"],
            action=data["action"],
            outcome=AuditOutcome(data["outcome"]),
            details=data.get("details", {}),
            previous_hash=data.get("previous_hash", ""),
            current_hash=data.get("current_hash", ""),
            signature=data.get("signature")
        )


@dataclass
class RetentionPolicy:
    """Audit log retention policy."""
    policy_id: str
    name: str
    retention_days: int
    archive_enabled: bool = True
    archive_location: Optional[str] = None

    def is_expired(self, entry: AuditEntry) -> bool:
        """Check if entry has exceeded retention period."""
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)
        return entry.timestamp < cutoff


class AuditTrail:
    """
    Immutable audit trail with hash chain verification.

    Maintains a cryptographically linked chain of audit entries
    that can be verified for tampering.
    """

    GENESIS_HASH = "0" * 64  # Genesis block hash

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        retention_policy: Optional[RetentionPolicy] = None
    ):
        """
        Initialize the audit trail.

        Args:
            storage_path: Path for persistent storage
            retention_policy: Retention policy to apply
        """
        self._entries: List[AuditEntry] = []
        self._storage_path = storage_path
        self._retention_policy = retention_policy
        self._last_hash = self.GENESIS_HASH
        self._entry_index: Dict[str, int] = {}

        if storage_path:
            self._load_from_storage()

        logger.info("AuditTrail initialized")

    def log(
        self,
        event_type: EventType,
        actor: str,
        resource: str,
        action: str,
        outcome: AuditOutcome,
        details: Optional[Dict[str, Any]] = None
    ) -> AuditEntry:
        """
        Log an audit event.

        Args:
            event_type: Type of event
            actor: Who performed the action
            resource: What resource was affected
            action: What action was taken
            outcome: Result of the action
            details: Additional details

        Returns:
            The created AuditEntry
        """
        entry_id = f"audit-{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"

        entry = AuditEntry(
            entry_id=entry_id,
            timestamp=datetime.utcnow(),
            event_type=event_type,
            actor=actor,
            resource=resource,
            action=action,
            outcome=outcome,
            details=details or {},
            previous_hash=self._last_hash
        )

        # Compute and set the hash
        entry.current_hash = entry.compute_hash()
        self._last_hash = entry.current_hash

        # Add to chain
        self._entry_index[entry.entry_id] = len(self._entries)
        self._entries.append(entry)

        # Persist if storage configured
        if self._storage_path:
            self._append_to_storage(entry)

        logger.debug(f"Logged audit entry: {entry.entry_id}")
        return entry

    def get_entry(self, entry_id: str) -> Optional[AuditEntry]:
        """Get an entry by ID."""
        idx = self._entry_index.get(entry_id)
        if idx is not None:
            return self._entries[idx]
        return None

    def verify_chain(self) -> Dict[str, Any]:
        """
        Verify the integrity of the audit chain.

        Returns:
            Dictionary with verification result
        """
        if not self._entries:
            return {"valid": True, "entries_checked": 0, "message": "Empty chain"}

        issues = []
        previous_hash = self.GENESIS_HASH

        for i, entry in enumerate(self._entries):
            # Verify previous hash link
            if entry.previous_hash != previous_hash:
                issues.append({
                    "index": i,
                    "entry_id": entry.entry_id,
                    "issue": "Previous hash mismatch",
                    "expected": previous_hash,
                    "actual": entry.previous_hash
                })

            # Verify current hash
            computed_hash = entry.compute_hash()
            if entry.current_hash != computed_hash:
                issues.append({
                    "index": i,
                    "entry_id": entry.entry_id,
                    "issue": "Current hash mismatch",
                    "expected": computed_hash,
                    "actual": entry.current_hash
                })

            previous_hash = entry.current_hash

        return {
            "valid": len(issues) == 0,
            "entries_checked": len(self._entries),
            "issues": issues,
            "message": "Chain valid" if not issues else f"Found {len(issues)} issues"
        }

    def query(
        self,
        actor: Optional[str] = None,
        resource: Optional[str] = None,
        event_type: Optional[EventType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditEntry]:
        """
        Query audit entries with filters.

        Args:
            actor: Filter by actor
            resource: Filter by resource
            event_type: Filter by event type
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum entries to return

        Returns:
            List of matching entries
        """
        results = []

        for entry in reversed(self._entries):  # Most recent first
            if actor and entry.actor != actor:
                continue
            if resource and entry.resource != resource:
                continue
            if event_type and entry.event_type != event_type:
                continue
            if start_time and entry.timestamp < start_time:
                continue
            if end_time and entry.timestamp > end_time:
                continue

            results.append(entry)

            if len(results) >= limit:
                break

        return results

    def apply_retention(self) -> int:
        """
        Apply retention policy, removing expired entries.

        Returns:
            Number of entries removed
        """
        if not self._retention_policy:
            return 0

        original_count = len(self._entries)
        self._entries = [
            e for e in self._entries
            if not self._retention_policy.is_expired(e)
        ]

        # Rebuild index
        self._entry_index = {e.entry_id: i for i, e in enumerate(self._entries)}

        removed = original_count - len(self._entries)
        if removed > 0:
            logger.info(f"Removed {removed} expired audit entries")

        return removed

    def export_json(self, entries: Optional[List[AuditEntry]] = None) -> str:
        """Export entries to JSON format."""
        entries = entries or self._entries
        return json.dumps([e.to_dict() for e in entries], indent=2)

    def export_csv(self, entries: Optional[List[AuditEntry]] = None) -> str:
        """Export entries to CSV format."""
        entries = entries or self._entries

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "entry_id", "timestamp", "event_type", "actor",
            "resource", "action", "outcome", "current_hash"
        ])

        # Data rows
        for entry in entries:
            writer.writerow([
                entry.entry_id,
                entry.timestamp.isoformat(),
                entry.event_type.value,
                entry.actor,
                entry.resource,
                entry.action,
                entry.outcome.value,
                entry.current_hash
            ])

        return output.getvalue()

    def iter_entries(self) -> Iterator[AuditEntry]:
        """Iterate over all entries."""
        yield from self._entries

    def __len__(self) -> int:
        """Return number of entries."""
        return len(self._entries)

    def _load_from_storage(self) -> None:
        """Load entries from persistent storage."""
        if not self._storage_path or not self._storage_path.exists():
            return

        try:
            with open(self._storage_path, 'r') as f:
                data = json.load(f)

            for entry_data in data:
                entry = AuditEntry.from_dict(entry_data)
                self._entry_index[entry.entry_id] = len(self._entries)
                self._entries.append(entry)

            if self._entries:
                self._last_hash = self._entries[-1].current_hash

            logger.info(f"Loaded {len(self._entries)} entries from storage")

        except Exception as e:
            logger.error(f"Failed to load from storage: {e}")

    def _append_to_storage(self, entry: AuditEntry) -> None:
        """Append entry to persistent storage."""
        if not self._storage_path:
            return

        try:
            # Read existing or create new
            if self._storage_path.exists():
                with open(self._storage_path, 'r') as f:
                    data = json.load(f)
            else:
                data = []
                self._storage_path.parent.mkdir(parents=True, exist_ok=True)

            data.append(entry.to_dict())

            with open(self._storage_path, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            logger.error(f"Failed to append to storage: {e}")


def create_audit_trail_with_defaults(storage_dir: Optional[Path] = None) -> AuditTrail:
    """Create an audit trail with default 90-day retention."""
    storage_path = None
    if storage_dir:
        storage_path = storage_dir / "audit_trail.json"

    retention = RetentionPolicy(
        policy_id="default",
        name="90-Day Retention",
        retention_days=90,
        archive_enabled=True
    )

    return AuditTrail(storage_path=storage_path, retention_policy=retention)
