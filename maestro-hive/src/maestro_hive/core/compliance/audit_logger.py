"""
Audit Logger: Structured audit logging for CLI operations.

EPIC: MD-2801 - Core Services & CLI Compliance (Batch 2)
AC-2: CLI Audit Logging

Provides comprehensive audit trail for all CLI command executions,
including structured logging, retention policies, and export capabilities.
"""

import hashlib
import json
import logging
import os
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)


class AuditLevel(Enum):
    """Audit logging detail levels."""
    MINIMAL = "minimal"       # Command and result only
    STANDARD = "standard"     # + session info and timing
    FULL = "full"             # + input/output details
    DEBUG = "debug"           # + internal state


@dataclass
class AuditEntry:
    """Single audit log entry."""
    entry_id: str
    timestamp: str
    level: AuditLevel
    event_type: str           # command, execution, error, session
    session_id: Optional[str] = None
    command: Optional[str] = None
    user: Optional[str] = None
    block_id: Optional[str] = None
    execution_id: Optional[str] = None
    duration_ms: Optional[int] = None
    status: Optional[str] = None
    input_summary: Optional[str] = None
    output_summary: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result = asdict(self)
        result['level'] = self.level.value
        return result

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AuditEntry':
        """Create from dictionary."""
        data = data.copy()
        data['level'] = AuditLevel(data.get('level', 'standard'))
        return cls(**data)


class AuditLogger:
    """
    Structured audit logging service for CLI operations.

    Features:
    - Thread-safe logging with RLock
    - Configurable retention policies
    - Multiple output formats (JSON, log file)
    - Session-based grouping
    - Automatic entry expiration

    Implements singleton pattern for global access.
    """

    _instance: Optional['AuditLogger'] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern for global audit access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        level: AuditLevel = AuditLevel.STANDARD,
        persistence_dir: Optional[str] = None,
        retention_days: int = 90,
        max_entries: int = 100000,
        enabled: bool = True
    ):
        """
        Initialize the audit logger.

        Args:
            level: Audit detail level
            persistence_dir: Directory for persistent storage
            retention_days: How long to keep audit entries
            max_entries: Maximum in-memory entries
            enabled: Whether logging is active
        """
        if hasattr(self, '_initialized') and self._initialized:
            return

        self._level = level
        self._persistence_dir = Path(persistence_dir) if persistence_dir else None
        self._retention_days = retention_days
        self._max_entries = max_entries
        self._enabled = enabled
        self._audit_lock = threading.RLock()
        self._entries: List[AuditEntry] = []
        self._sessions: Dict[str, List[str]] = {}  # session_id -> entry_ids
        self._initialized = True

        if self._persistence_dir:
            self._persistence_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"AuditLogger initialized with level: {level.value}")

    def _generate_entry_id(self) -> str:
        """Generate unique entry ID."""
        return f"audit_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    def _summarize(self, data: Any, max_length: int = 200) -> str:
        """Create summary of data for logging."""
        if data is None:
            return ""
        try:
            if isinstance(data, dict):
                keys = list(data.keys())[:5]
                return f"dict({len(data)} keys: {', '.join(keys)})"
            elif isinstance(data, (list, tuple)):
                return f"list({len(data)} items)"
            else:
                text = str(data)
                if len(text) > max_length:
                    return text[:max_length] + "..."
                return text
        except Exception:
            return "<unserializable>"

    def _cleanup_old_entries(self) -> None:
        """Remove entries older than retention period."""
        if not self._entries:
            return

        cutoff = datetime.utcnow() - timedelta(days=self._retention_days)
        cutoff_str = cutoff.isoformat()

        self._entries = [
            e for e in self._entries
            if e.timestamp >= cutoff_str
        ]

        # Trim to max entries
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries:]

    def log_command(
        self,
        command: str,
        session_id: Optional[str] = None,
        user: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a CLI command execution.

        Args:
            command: The command being executed
            session_id: Session identifier
            user: User executing the command
            metadata: Additional context

        Returns:
            Entry ID for the logged event
        """
        if not self._enabled:
            return ""

        with self._audit_lock:
            entry = AuditEntry(
                entry_id=self._generate_entry_id(),
                timestamp=datetime.utcnow().isoformat(),
                level=self._level,
                event_type="command",
                session_id=session_id,
                command=command,
                user=user or os.environ.get("USER", "unknown"),
                metadata=metadata or {},
            )

            self._entries.append(entry)
            if session_id:
                if session_id not in self._sessions:
                    self._sessions[session_id] = []
                self._sessions[session_id].append(entry.entry_id)

            self._persist_entry(entry)
            self._cleanup_old_entries()

            logger.debug(f"Logged command: {command[:50]}...")
            return entry.entry_id

    def log_execution(
        self,
        execution_id: str,
        block_id: str,
        status: str,
        duration_ms: int,
        session_id: Optional[str] = None,
        inputs: Optional[Dict[str, Any]] = None,
        outputs: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a block execution.

        Args:
            execution_id: Unique execution identifier
            block_id: Block that was executed
            status: Execution status (completed, failed, etc.)
            duration_ms: Execution duration in milliseconds
            session_id: Session identifier
            inputs: Input data (summarized)
            outputs: Output data (summarized)
            metadata: Additional context

        Returns:
            Entry ID for the logged event
        """
        if not self._enabled:
            return ""

        with self._audit_lock:
            input_summary = None
            output_summary = None

            if self._level in (AuditLevel.FULL, AuditLevel.DEBUG):
                input_summary = self._summarize(inputs)
                output_summary = self._summarize(outputs)

            entry = AuditEntry(
                entry_id=self._generate_entry_id(),
                timestamp=datetime.utcnow().isoformat(),
                level=self._level,
                event_type="execution",
                session_id=session_id,
                block_id=block_id,
                execution_id=execution_id,
                duration_ms=duration_ms,
                status=status,
                input_summary=input_summary,
                output_summary=output_summary,
                metadata=metadata or {},
            )

            self._entries.append(entry)
            if session_id:
                if session_id not in self._sessions:
                    self._sessions[session_id] = []
                self._sessions[session_id].append(entry.entry_id)

            self._persist_entry(entry)

            logger.debug(f"Logged execution: {block_id} -> {status}")
            return entry.entry_id

    def log_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        execution_id: Optional[str] = None
    ) -> str:
        """
        Log an error event.

        Args:
            error: The exception that occurred
            context: Additional error context
            session_id: Session identifier
            execution_id: Related execution ID

        Returns:
            Entry ID for the logged event
        """
        if not self._enabled:
            return ""

        with self._audit_lock:
            entry = AuditEntry(
                entry_id=self._generate_entry_id(),
                timestamp=datetime.utcnow().isoformat(),
                level=self._level,
                event_type="error",
                session_id=session_id,
                execution_id=execution_id,
                status="error",
                error=f"{type(error).__name__}: {str(error)}",
                metadata=context or {},
            )

            self._entries.append(entry)
            if session_id:
                if session_id not in self._sessions:
                    self._sessions[session_id] = []
                self._sessions[session_id].append(entry.entry_id)

            self._persist_entry(entry)

            logger.warning(f"Logged error: {error}")
            return entry.entry_id

    def log_session(
        self,
        session_id: str,
        event: str,  # started, resumed, completed, failed
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a session lifecycle event.

        Args:
            session_id: Session identifier
            event: Session event type
            metadata: Additional context

        Returns:
            Entry ID for the logged event
        """
        if not self._enabled:
            return ""

        with self._audit_lock:
            entry = AuditEntry(
                entry_id=self._generate_entry_id(),
                timestamp=datetime.utcnow().isoformat(),
                level=self._level,
                event_type="session",
                session_id=session_id,
                status=event,
                metadata=metadata or {},
            )

            self._entries.append(entry)
            if session_id not in self._sessions:
                self._sessions[session_id] = []
            self._sessions[session_id].append(entry.entry_id)

            self._persist_entry(entry)

            logger.debug(f"Logged session event: {session_id} -> {event}")
            return entry.entry_id

    def _persist_entry(self, entry: AuditEntry) -> None:
        """Persist entry to disk if configured."""
        if not self._persistence_dir:
            return

        try:
            date_str = datetime.utcnow().strftime("%Y%m%d")
            log_file = self._persistence_dir / f"audit_{date_str}.jsonl"

            with open(log_file, "a") as f:
                f.write(entry.to_json() + "\n")
        except Exception as e:
            logger.error(f"Failed to persist audit entry: {e}")

    def get_audit_trail(
        self,
        session_id: Optional[str] = None,
        event_type: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 100
    ) -> List[AuditEntry]:
        """
        Retrieve audit entries with optional filtering.

        Args:
            session_id: Filter by session
            event_type: Filter by event type
            start_time: Filter by start time (ISO format)
            end_time: Filter by end time (ISO format)
            limit: Maximum entries to return

        Returns:
            List of matching audit entries
        """
        with self._audit_lock:
            entries = self._entries.copy()

            if session_id:
                entry_ids = self._sessions.get(session_id, [])
                entries = [e for e in entries if e.entry_id in entry_ids]

            if event_type:
                entries = [e for e in entries if e.event_type == event_type]

            if start_time:
                entries = [e for e in entries if e.timestamp >= start_time]

            if end_time:
                entries = [e for e in entries if e.timestamp <= end_time]

            return entries[-limit:]

    def export_audit_trail(
        self,
        format: str = "json",
        session_id: Optional[str] = None
    ) -> str:
        """
        Export audit trail to specified format.

        Args:
            format: Export format (json, csv)
            session_id: Optional session filter

        Returns:
            Formatted audit trail string
        """
        entries = self.get_audit_trail(session_id=session_id, limit=10000)

        if format == "json":
            return json.dumps([e.to_dict() for e in entries], indent=2, default=str)
        elif format == "csv":
            if not entries:
                return ""
            headers = list(entries[0].to_dict().keys())
            lines = [",".join(headers)]
            for entry in entries:
                d = entry.to_dict()
                values = [str(d.get(h, "")).replace(",", ";") for h in headers]
                lines.append(",".join(values))
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def get_session_summary(self, session_id: str) -> Dict[str, Any]:
        """Get summary of a session's audit trail."""
        entries = self.get_audit_trail(session_id=session_id, limit=10000)

        if not entries:
            return {"session_id": session_id, "entries": 0}

        commands = [e for e in entries if e.event_type == "command"]
        executions = [e for e in entries if e.event_type == "execution"]
        errors = [e for e in entries if e.event_type == "error"]

        return {
            "session_id": session_id,
            "entries": len(entries),
            "commands": len(commands),
            "executions": len(executions),
            "errors": len(errors),
            "start_time": entries[0].timestamp,
            "end_time": entries[-1].timestamp,
        }

    def set_level(self, level: AuditLevel) -> None:
        """Update audit level."""
        self._level = level
        logger.info(f"Audit level updated to: {level.value}")

    def enable(self) -> None:
        """Enable audit logging."""
        self._enabled = True
        logger.info("Audit logging enabled")

    def disable(self) -> None:
        """Disable audit logging."""
        self._enabled = False
        logger.info("Audit logging disabled")

    @property
    def is_enabled(self) -> bool:
        """Check if logging is enabled."""
        return self._enabled

    @property
    def entry_count(self) -> int:
        """Get current entry count."""
        return len(self._entries)


def get_audit_logger(**kwargs) -> AuditLogger:
    """Get the singleton AuditLogger instance."""
    return AuditLogger(**kwargs)
