"""
Audit Logger (AC-5)

Implements immutable audit logging as defined in policy.yaml Section 10.
AC-5: All governance actions are logged to audit.log and broadcast to the Event Bus.

This provides forensic capabilities and compliance evidence for all
governance-related actions in the system.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class AuditAction(Enum):
    """Types of audited actions."""

    # Enforcer actions
    TOOL_BLOCKED = "tool_blocked"
    TOOL_ALLOWED = "tool_allowed"
    PATH_BLOCKED = "path_blocked"
    POLICY_CHECK = "policy_check"

    # Reputation actions
    REPUTATION_CHANGE = "reputation_change"
    ROLE_PROMOTION = "role_promotion"
    ROLE_DEMOTION = "role_demotion"
    AGENT_DECOMMISSION = "agent_decommission"

    # Lock actions
    LOCK_ACQUIRED = "lock_acquired"
    LOCK_RELEASED = "lock_released"
    LOCK_EXPIRED = "lock_expired"
    LOCK_FORCED = "lock_forced"

    # Appeal actions
    APPEAL_SUBMITTED = "appeal_submitted"
    APPEAL_APPROVED = "appeal_approved"
    APPEAL_DENIED = "appeal_denied"

    # Emergency override
    OVERRIDE_INITIATED = "override_initiated"
    OVERRIDE_APPROVED = "override_approved"
    OVERRIDE_EXPIRED = "override_expired"

    # Chaos events
    CHAOS_EVENT = "chaos_event"
    JANITOR_ACTION = "janitor_action"


@dataclass
class AuditEntry:
    """
    An immutable audit log entry.

    Attributes:
        entry_id: Unique identifier for this entry
        timestamp: When the action occurred
        action: Type of action
        agent_id: Agent involved
        target_resource: Resource affected (file path, etc.)
        result: Result of the action (allowed/denied/etc.)
        policy_version: Policy version at time of action
        details: Additional context
    """

    entry_id: str
    timestamp: datetime
    action: AuditAction
    agent_id: str
    target_resource: str = ""
    result: str = ""
    policy_version: str = "2.0.0"
    reputation_at_time: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for JSON storage."""
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "action": self.action.value,
            "agent_id": self.agent_id,
            "target_resource": self.target_resource,
            "result": self.result,
            "policy_version": self.policy_version,
            "reputation_at_time": self.reputation_at_time,
            "details": self.details,
        }

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AuditEntry":
        """Deserialize from dictionary."""
        return cls(
            entry_id=data["entry_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            action=AuditAction(data["action"]),
            agent_id=data["agent_id"],
            target_resource=data.get("target_resource", ""),
            result=data.get("result", ""),
            policy_version=data.get("policy_version", ""),
            reputation_at_time=data.get("reputation_at_time"),
            details=data.get("details", {}),
        )


class AuditLogger:
    """
    Audit Logger - Immutable Governance Action Logging.

    AC-5 Implementation: Logs all governance actions to audit.log
    and broadcasts to the Event Bus.

    From policy.yaml Section 10:
    - log_all_actions: true
    - log_all_policy_checks: true
    - log_format: structured_json
    - immutable_log: append_only_file

    Features:
    - Append-only file logging
    - Event Bus integration
    - Query support for forensics
    - Retention management
    """

    def __init__(
        self,
        log_path: Optional[str] = None,
        event_bus: Optional[Any] = None,
        retention_days: int = 90,
    ):
        """
        Initialize the audit logger.

        Args:
            log_path: Path to audit log file
            event_bus: Event bus for broadcasting
            retention_days: Days to retain logs
        """
        self._log_path = log_path or "/tmp/governance_audit.log"
        self._event_bus = event_bus
        self._retention_days = retention_days
        self._lock = threading.Lock()
        self._entry_counter = 0
        self._in_memory_log: List[AuditEntry] = []

        # Callbacks for external integrations
        self._on_entry: List[Callable[[AuditEntry], None]] = []

        # Event bus topics from policy.yaml
        self._topics = {
            "violations": "governance.violation",
            "reputation": "governance.reputation_change",
            "role_changes": "governance.role_change",
            "appeals": "governance.appeal",
            "overrides": "governance.emergency_override",
        }

        # Ensure log directory exists
        log_dir = Path(self._log_path).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"AuditLogger initialized (path={self._log_path})")

    def log(
        self,
        action: AuditAction,
        agent_id: str,
        target_resource: str = "",
        result: str = "",
        reputation_at_time: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """
        Log an audit entry.

        AC-5: All governance actions logged to audit.log and Event Bus.

        Args:
            action: Type of action
            agent_id: Agent involved
            target_resource: Resource affected
            result: Result of action
            reputation_at_time: Agent's reputation at time of action
            details: Additional context

        Returns:
            The created AuditEntry
        """
        with self._lock:
            self._entry_counter += 1
            entry_id = f"audit_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{self._entry_counter:06d}"

            entry = AuditEntry(
                entry_id=entry_id,
                timestamp=datetime.utcnow(),
                action=action,
                agent_id=agent_id,
                target_resource=target_resource,
                result=result,
                reputation_at_time=reputation_at_time,
                details=details or {},
            )

            # Store in memory
            self._in_memory_log.append(entry)

            # Append to file (immutable)
            self._append_to_file(entry)

            # Broadcast to Event Bus
            self._broadcast(entry)

            # Notify callbacks
            for callback in self._on_entry:
                try:
                    callback(entry)
                except Exception as e:
                    logger.error(f"Audit callback error: {e}")

            return entry

    def log_violation(
        self,
        agent_id: str,
        tool_name: str,
        target: str,
        violation_type: str,
        message: str,
    ) -> AuditEntry:
        """Convenience method for logging policy violations."""
        return self.log(
            action=AuditAction.TOOL_BLOCKED,
            agent_id=agent_id,
            target_resource=target,
            result="blocked",
            details={
                "tool_name": tool_name,
                "violation_type": violation_type,
                "message": message,
            },
        )

    def log_reputation_change(
        self,
        agent_id: str,
        event: str,
        old_score: int,
        new_score: int,
        delta: int,
    ) -> AuditEntry:
        """Convenience method for logging reputation changes."""
        return self.log(
            action=AuditAction.REPUTATION_CHANGE,
            agent_id=agent_id,
            result=f"{old_score} -> {new_score}",
            reputation_at_time=new_score,
            details={
                "event": event,
                "old_score": old_score,
                "new_score": new_score,
                "delta": delta,
            },
        )

    def log_lock_event(
        self,
        action: AuditAction,
        agent_id: str,
        path: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEntry:
        """Convenience method for logging lock events."""
        return self.log(
            action=action,
            agent_id=agent_id,
            target_resource=path,
            result=action.value.split("_")[-1],  # "acquired", "released", etc.
            details=details or {},
        )

    def _append_to_file(self, entry: AuditEntry) -> None:
        """Append entry to log file (append-only)."""
        try:
            with open(self._log_path, "a") as f:
                f.write(entry.to_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")

    def _broadcast(self, entry: AuditEntry) -> None:
        """Broadcast entry to Event Bus."""
        if self._event_bus is None:
            return

        # Determine topic based on action
        topic = None
        if entry.action in (AuditAction.TOOL_BLOCKED, AuditAction.PATH_BLOCKED):
            topic = self._topics["violations"]
        elif entry.action == AuditAction.REPUTATION_CHANGE:
            topic = self._topics["reputation"]
        elif entry.action in (AuditAction.ROLE_PROMOTION, AuditAction.ROLE_DEMOTION):
            topic = self._topics["role_changes"]
        elif entry.action in (AuditAction.APPEAL_SUBMITTED, AuditAction.APPEAL_APPROVED, AuditAction.APPEAL_DENIED):
            topic = self._topics["appeals"]
        elif entry.action in (AuditAction.OVERRIDE_INITIATED, AuditAction.OVERRIDE_APPROVED):
            topic = self._topics["overrides"]

        if topic:
            try:
                self._event_bus.publish(topic, entry.to_dict())
                logger.debug(f"Broadcast audit entry to {topic}")
            except Exception as e:
                logger.error(f"Failed to broadcast audit entry: {e}")

    def query(
        self,
        agent_id: Optional[str] = None,
        action: Optional[AuditAction] = None,
        target_resource: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[AuditEntry]:
        """
        Query audit log entries.

        Args:
            agent_id: Filter by agent
            action: Filter by action type
            target_resource: Filter by resource (substring match)
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum entries to return

        Returns:
            List of matching entries
        """
        with self._lock:
            results = self._in_memory_log.copy()

        if agent_id:
            results = [e for e in results if e.agent_id == agent_id]

        if action:
            results = [e for e in results if e.action == action]

        if target_resource:
            results = [e for e in results if target_resource in e.target_resource]

        if start_time:
            results = [e for e in results if e.timestamp >= start_time]

        if end_time:
            results = [e for e in results if e.timestamp <= end_time]

        return results[-limit:]

    def get_agent_history(self, agent_id: str, limit: int = 50) -> List[AuditEntry]:
        """Get audit history for a specific agent."""
        return self.query(agent_id=agent_id, limit=limit)

    def get_violations(self, limit: int = 50) -> List[AuditEntry]:
        """Get recent policy violations."""
        with self._lock:
            violations = [
                e for e in self._in_memory_log
                if e.action in (AuditAction.TOOL_BLOCKED, AuditAction.PATH_BLOCKED)
            ]
        return violations[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        """Get audit statistics."""
        with self._lock:
            entries = self._in_memory_log

        by_action = {}
        by_agent = {}
        violations = 0

        for entry in entries:
            # Count by action
            action_name = entry.action.value
            by_action[action_name] = by_action.get(action_name, 0) + 1

            # Count by agent
            by_agent[entry.agent_id] = by_agent.get(entry.agent_id, 0) + 1

            # Count violations
            if entry.action in (AuditAction.TOOL_BLOCKED, AuditAction.PATH_BLOCKED):
                violations += 1

        return {
            "total_entries": len(entries),
            "by_action": by_action,
            "by_agent": by_agent,
            "violations": violations,
            "log_path": self._log_path,
        }

    def on_entry(self, callback: Callable[[AuditEntry], None]) -> None:
        """Register callback for new audit entries."""
        self._on_entry.append(callback)

    def set_event_bus(self, event_bus: Any) -> None:
        """Set the event bus for broadcasting."""
        self._event_bus = event_bus

    def export_to_file(self, path: str) -> int:
        """Export all entries to a file."""
        with self._lock:
            with open(path, "w") as f:
                for entry in self._in_memory_log:
                    f.write(entry.to_json() + "\n")
            return len(self._in_memory_log)

    def load_from_file(self) -> int:
        """Load entries from the log file into memory."""
        if not os.path.exists(self._log_path):
            return 0

        count = 0
        with self._lock:
            with open(self._log_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            data = json.loads(line)
                            entry = AuditEntry.from_dict(data)
                            self._in_memory_log.append(entry)
                            count += 1
                        except Exception as e:
                            logger.warning(f"Failed to parse audit entry: {e}")

        logger.info(f"Loaded {count} audit entries from {self._log_path}")
        return count
