#!/usr/bin/env python3
"""
Audit Logger: Comprehensive audit logging for compliance.

This module provides structured audit logging for AI decisions, user actions,
data access, and configuration changes with support for PII masking and retention.
"""

import json
import re
import os
import gzip
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    AI_DECISION = "ai_decision"
    USER_ACTION = "user_action"
    DATA_ACCESS = "data_access"
    CONFIG_CHANGE = "config_change"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    SYSTEM_EVENT = "system_event"
    ERROR = "error"
    COMPLIANCE = "compliance"


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """
    An audit event record.

    Captures comprehensive information about an auditable action
    in the system with support for correlation and context.
    """
    id: str
    event_type: AuditEventType
    severity: AuditSeverity
    message: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    actor: Optional[str] = None
    actor_type: str = "system"  # user, system, ai, service
    resource: Optional[str] = None
    resource_type: Optional[str] = None
    action: Optional[str] = None
    outcome: str = "success"  # success, failure, partial
    correlation_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    pii_masked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        return data

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditEvent':
        """Create from dictionary."""
        data = dict(data)
        if isinstance(data.get('event_type'), str):
            data['event_type'] = AuditEventType(data['event_type'])
        if isinstance(data.get('severity'), str):
            data['severity'] = AuditSeverity(data['severity'])
        return cls(**data)


class PIIMasker:
    """Masks PII in audit events."""

    # Common PII patterns
    PATTERNS = {
        'email': (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_MASKED]'),
        'phone': (r'\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b', '[PHONE_MASKED]'),
        'ssn': (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_MASKED]'),
        'credit_card': (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '[CC_MASKED]'),
        'ip_address': (r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b', '[IP_MASKED]'),
        'api_key': (r'\b[A-Za-z0-9]{32,}\b', '[KEY_MASKED]'),
        'bearer_token': (r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', 'Bearer [TOKEN_MASKED]'),
        'password': (r'(?i)password["\s:=]+[^\s,}"\']+', 'password=[MASKED]'),
        'secret': (r'(?i)secret["\s:=]+[^\s,}"\']+', 'secret=[MASKED]'),
    }

    def __init__(self, additional_patterns: Optional[Dict[str, tuple]] = None):
        """
        Initialize masker.

        Args:
            additional_patterns: Additional patterns to mask {name: (pattern, replacement)}
        """
        self.patterns = dict(self.PATTERNS)
        if additional_patterns:
            self.patterns.update(additional_patterns)

        # Compile patterns
        self._compiled = {
            name: (re.compile(pattern), replacement)
            for name, (pattern, replacement) in self.patterns.items()
        }

    def mask(self, text: str) -> str:
        """Mask PII in text."""
        result = text
        for name, (pattern, replacement) in self._compiled.items():
            result = pattern.sub(replacement, result)
        return result

    def mask_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively mask PII in a dictionary."""
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self.mask(value)
            elif isinstance(value, dict):
                result[key] = self.mask_dict(value)
            elif isinstance(value, list):
                result[key] = [
                    self.mask_dict(item) if isinstance(item, dict)
                    else self.mask(item) if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                result[key] = value
        return result


class AuditLogger:
    """
    Comprehensive audit logging system.

    Features:
    - Structured JSON logging
    - PII masking
    - Log rotation
    - Retention policies
    - Export capabilities
    """

    _instance: Optional['AuditLogger'] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        log_dir: Optional[str] = None,
        max_size_mb: int = 100,
        backup_count: int = 10,
        pii_masking: bool = True,
        retention_days: int = 90
    ):
        """
        Initialize the audit logger.

        Args:
            log_dir: Directory for audit logs
            max_size_mb: Maximum log file size before rotation
            backup_count: Number of backup files to keep
            pii_masking: Enable PII masking
            retention_days: Days to retain logs
        """
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.log_dir = Path(log_dir) if log_dir else Path.home() / ".maestro" / "audit"
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.backup_count = backup_count
        self.retention_days = retention_days
        self.pii_masking = pii_masking

        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._current_log_file = self.log_dir / "audit.jsonl"
        self._write_lock = threading.RLock()
        self._event_counter = 0
        self._masker = PIIMasker() if pii_masking else None
        self._hooks: List[Callable[[AuditEvent], None]] = []
        self._initialized = True

        # Run cleanup on init
        self._cleanup_old_logs()

        logger.info(f"AuditLogger initialized: {self.log_dir}")

    def log(
        self,
        event_type: AuditEventType,
        message: str,
        severity: AuditSeverity = AuditSeverity.INFO,
        **kwargs
    ) -> str:
        """
        Log an audit event.

        Args:
            event_type: Type of event
            message: Human-readable message
            severity: Event severity
            **kwargs: Additional event fields

        Returns:
            Event ID
        """
        with self._write_lock:
            self._event_counter += 1
            event_id = f"AUD-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._event_counter:06d}"

        event = AuditEvent(
            id=event_id,
            event_type=event_type,
            severity=severity,
            message=message,
            **kwargs
        )

        # Apply PII masking
        if self._masker:
            event.message = self._masker.mask(event.message)
            if event.metadata:
                event.metadata = self._masker.mask_dict(event.metadata)
            if event.context:
                event.context = self._masker.mask_dict(event.context)
            event.pii_masked = True

        # Write to log
        self._write_event(event)

        # Call hooks
        for hook in self._hooks:
            try:
                hook(event)
            except Exception as e:
                logger.error(f"Audit hook error: {e}")

        return event_id

    def log_ai_decision(
        self,
        decision: str,
        reasoning: str,
        model: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        confidence: Optional[float] = None,
        **kwargs
    ) -> str:
        """
        Log an AI decision for compliance.

        Args:
            decision: The decision made
            reasoning: Explanation of reasoning
            model: Model used for decision
            inputs: Input data
            outputs: Output data
            confidence: Confidence score
            **kwargs: Additional fields

        Returns:
            Event ID
        """
        return self.log(
            event_type=AuditEventType.AI_DECISION,
            message=f"AI Decision: {decision}",
            actor=model,
            actor_type="ai",
            metadata={
                "decision": decision,
                "reasoning": reasoning,
                "model": model,
                "confidence": confidence,
                "inputs_summary": str(inputs)[:500],
                "outputs_summary": str(outputs)[:500]
            },
            **kwargs
        )

    def log_user_action(
        self,
        user: str,
        action: str,
        resource: Optional[str] = None,
        outcome: str = "success",
        **kwargs
    ) -> str:
        """
        Log a user action.

        Args:
            user: User identifier
            action: Action performed
            resource: Resource affected
            outcome: Action outcome

        Returns:
            Event ID
        """
        return self.log(
            event_type=AuditEventType.USER_ACTION,
            message=f"User {user} performed {action}",
            actor=user,
            actor_type="user",
            action=action,
            resource=resource,
            outcome=outcome,
            **kwargs
        )

    def log_data_access(
        self,
        accessor: str,
        data_type: str,
        operation: str,
        record_count: int = 1,
        **kwargs
    ) -> str:
        """
        Log data access for compliance.

        Args:
            accessor: Who accessed the data
            data_type: Type of data accessed
            operation: read, write, delete, etc.
            record_count: Number of records affected

        Returns:
            Event ID
        """
        return self.log(
            event_type=AuditEventType.DATA_ACCESS,
            message=f"Data access: {operation} on {data_type}",
            actor=accessor,
            resource_type=data_type,
            action=operation,
            metadata={"record_count": record_count},
            **kwargs
        )

    def query(
        self,
        since: Optional[str] = None,
        until: Optional[str] = None,
        event_type: Optional[AuditEventType] = None,
        severity: Optional[AuditSeverity] = None,
        actor: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """
        Query audit logs.

        Args:
            since: Start time (ISO format or relative like '1h', '1d')
            until: End time
            event_type: Filter by event type
            severity: Filter by severity
            actor: Filter by actor
            correlation_id: Filter by correlation ID
            limit: Maximum results

        Returns:
            List of matching AuditEvents
        """
        events = []

        # Parse time filters
        since_dt = self._parse_time(since) if since else None
        until_dt = self._parse_time(until) if until else None

        # Read from current and backup logs
        log_files = [self._current_log_file]
        log_files.extend(sorted(self.log_dir.glob("audit.jsonl.*"), reverse=True))

        for log_file in log_files:
            if len(events) >= limit:
                break

            if not log_file.exists():
                continue

            try:
                if log_file.suffix == '.gz':
                    with gzip.open(log_file, 'rt') as f:
                        lines = f.readlines()
                else:
                    with open(log_file, 'r') as f:
                        lines = f.readlines()

                for line in reversed(lines):
                    if len(events) >= limit:
                        break

                    try:
                        data = json.loads(line.strip())
                        event = AuditEvent.from_dict(data)

                        # Apply filters
                        if not self._matches_filters(
                            event, since_dt, until_dt, event_type,
                            severity, actor, correlation_id
                        ):
                            continue

                        events.append(event)

                    except (json.JSONDecodeError, KeyError):
                        continue

            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {e}")

        return events

    def export(
        self,
        format: str = "json",
        since: Optional[str] = None,
        until: Optional[str] = None,
        **filters
    ) -> bytes:
        """
        Export audit logs.

        Args:
            format: Export format (json, csv, jsonl)
            since: Start time
            until: End time
            **filters: Additional query filters

        Returns:
            Exported data as bytes
        """
        events = self.query(since=since, until=until, limit=10000, **filters)

        if format == "json":
            data = [e.to_dict() for e in events]
            return json.dumps(data, indent=2, default=str).encode()

        elif format == "jsonl":
            lines = [e.to_json() for e in events]
            return "\n".join(lines).encode()

        elif format == "csv":
            if not events:
                return b"id,timestamp,event_type,severity,message,actor,action,outcome\n"

            lines = ["id,timestamp,event_type,severity,message,actor,action,outcome"]
            for e in events:
                line = f'{e.id},{e.timestamp},{e.event_type.value},{e.severity.value},"{e.message}",{e.actor or ""},{e.action or ""},{e.outcome}'
                lines.append(line)
            return "\n".join(lines).encode()

        else:
            raise ValueError(f"Unknown export format: {format}")

    def add_hook(self, hook: Callable[[AuditEvent], None]) -> None:
        """Add a hook to be called on each audit event."""
        self._hooks.append(hook)

    def remove_hook(self, hook: Callable[[AuditEvent], None]) -> bool:
        """Remove an audit hook."""
        if hook in self._hooks:
            self._hooks.remove(hook)
            return True
        return False

    def _write_event(self, event: AuditEvent) -> None:
        """Write event to log file."""
        with self._write_lock:
            # Check for rotation
            if self._current_log_file.exists():
                size = self._current_log_file.stat().st_size
                if size >= self.max_size_bytes:
                    self._rotate_logs()

            # Write event
            with open(self._current_log_file, 'a') as f:
                f.write(event.to_json() + "\n")

    def _rotate_logs(self) -> None:
        """Rotate log files."""
        # Compress and rename existing backups
        for i in range(self.backup_count - 1, 0, -1):
            old_file = self.log_dir / f"audit.jsonl.{i}.gz"
            new_file = self.log_dir / f"audit.jsonl.{i+1}.gz"
            if old_file.exists():
                if i + 1 >= self.backup_count:
                    old_file.unlink()
                else:
                    old_file.rename(new_file)

        # Compress current log
        if self._current_log_file.exists():
            backup_file = self.log_dir / "audit.jsonl.1.gz"
            with open(self._current_log_file, 'rb') as f_in:
                with gzip.open(backup_file, 'wb') as f_out:
                    f_out.write(f_in.read())
            self._current_log_file.unlink()

        logger.info("Audit logs rotated")

    def _cleanup_old_logs(self) -> None:
        """Remove logs older than retention period."""
        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)

        for log_file in self.log_dir.glob("audit.jsonl.*"):
            try:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < cutoff:
                    log_file.unlink()
                    logger.info(f"Removed old audit log: {log_file}")
            except Exception as e:
                logger.error(f"Error cleaning up {log_file}: {e}")

    def _parse_time(self, time_str: str) -> datetime:
        """Parse time string to datetime."""
        # Check for relative time
        relative_match = re.match(r'^(\d+)([hdwm])$', time_str)
        if relative_match:
            value = int(relative_match.group(1))
            unit = relative_match.group(2)
            deltas = {'h': timedelta(hours=value), 'd': timedelta(days=value),
                      'w': timedelta(weeks=value), 'm': timedelta(days=value*30)}
            return datetime.utcnow() - deltas[unit]

        # Try ISO format
        return datetime.fromisoformat(time_str.replace('Z', '+00:00'))

    def _matches_filters(
        self,
        event: AuditEvent,
        since_dt: Optional[datetime],
        until_dt: Optional[datetime],
        event_type: Optional[AuditEventType],
        severity: Optional[AuditSeverity],
        actor: Optional[str],
        correlation_id: Optional[str]
    ) -> bool:
        """Check if event matches filters."""
        event_dt = datetime.fromisoformat(event.timestamp.replace('Z', '+00:00'))

        if since_dt and event_dt < since_dt:
            return False
        if until_dt and event_dt > until_dt:
            return False
        if event_type and event.event_type != event_type:
            return False
        if severity and event.severity != severity:
            return False
        if actor and event.actor != actor:
            return False
        if correlation_id and event.correlation_id != correlation_id:
            return False

        return True


# Convenience function
def get_audit_logger(**kwargs) -> AuditLogger:
    """Get the singleton AuditLogger instance."""
    return AuditLogger(**kwargs)
