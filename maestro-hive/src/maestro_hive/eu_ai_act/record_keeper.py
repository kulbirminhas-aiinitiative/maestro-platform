"""
Record Keeper Module - EU AI Act Article 12 Compliance

Implements automatic event logging for AI system operations with
audit trail capabilities and retention policies.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import hashlib
import json
import threading
from collections import defaultdict


class AuditEventType(Enum):
    """Types of audit events per Article 12."""
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    INPUT_RECEIVED = "input_received"
    OUTPUT_GENERATED = "output_generated"
    DECISION_MADE = "decision_made"
    HUMAN_INTERVENTION = "human_intervention"
    ERROR_OCCURRED = "error_occurred"
    CONFIG_CHANGED = "config_changed"
    ACCESS_GRANTED = "access_granted"
    ACCESS_DENIED = "access_denied"
    DATA_PROCESSED = "data_processed"
    MODEL_UPDATED = "model_updated"
    ALERT_TRIGGERED = "alert_triggered"
    COMPLIANCE_CHECK = "compliance_check"


class RetentionPolicy(Enum):
    """Data retention policies."""
    SHORT_TERM = 90  # 90 days
    MEDIUM_TERM = 365  # 1 year
    LONG_TERM = 2555  # 7 years (regulatory requirement)
    PERMANENT = -1  # Never delete


@dataclass
class AuditEvent:
    """Single audit event record."""
    event_id: str
    event_type: AuditEventType
    timestamp: datetime
    ai_system_id: str
    actor: str  # User or system component
    action: str
    details: Dict[str, Any]
    input_data_hash: Optional[str] = None
    output_data_hash: Optional[str] = None
    session_id: Optional[str] = None
    correlation_id: Optional[str] = None
    integrity_hash: str = ""

    def __post_init__(self):
        """Calculate integrity hash after initialization."""
        if not self.integrity_hash:
            self.integrity_hash = self._calculate_integrity_hash()

    def _calculate_integrity_hash(self) -> str:
        """Calculate SHA-256 hash for event integrity."""
        content = json.dumps({
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "ai_system_id": self.ai_system_id,
            "actor": self.actor,
            "action": self.action,
            "details": self.details
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def verify_integrity(self) -> bool:
        """Verify event integrity hasn't been tampered with."""
        expected_hash = self._calculate_integrity_hash()
        return self.integrity_hash == expected_hash

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "ai_system_id": self.ai_system_id,
            "actor": self.actor,
            "action": self.action,
            "details": self.details,
            "input_data_hash": self.input_data_hash,
            "output_data_hash": self.output_data_hash,
            "session_id": self.session_id,
            "correlation_id": self.correlation_id,
            "integrity_hash": self.integrity_hash
        }


@dataclass
class AuditTrail:
    """Complete audit trail for an entity."""
    entity_id: str
    entity_type: str
    events: List[AuditEvent] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def add_event(self, event: AuditEvent) -> None:
        """Add event to trail."""
        self.events.append(event)

    def get_events_by_type(self, event_type: AuditEventType) -> List[AuditEvent]:
        """Get events filtered by type."""
        return [e for e in self.events if e.event_type == event_type]

    def get_events_in_range(
        self,
        start: datetime,
        end: datetime
    ) -> List[AuditEvent]:
        """Get events within a time range."""
        return [
            e for e in self.events
            if start <= e.timestamp <= end
        ]


class RecordKeeper:
    """
    Record Keeper for EU AI Act Article 12 compliance.

    Provides automatic event logging with traceability throughout
    the AI system lifecycle.
    """

    def __init__(
        self,
        ai_system_id: str,
        retention_policy: RetentionPolicy = RetentionPolicy.LONG_TERM,
        max_events_in_memory: int = 100000
    ):
        """
        Initialize record keeper.

        Args:
            ai_system_id: Unique identifier for the AI system
            retention_policy: Data retention policy
            max_events_in_memory: Maximum events to keep in memory
        """
        self.ai_system_id = ai_system_id
        self.retention_policy = retention_policy
        self.max_events_in_memory = max_events_in_memory

        self._events: List[AuditEvent] = []
        self._audit_trails: Dict[str, AuditTrail] = {}
        self._event_counter = 0
        self._lock = threading.Lock()
        self._event_handlers: Dict[AuditEventType, List[Callable]] = defaultdict(list)

        # Log system initialization
        self.log_event(
            event_type=AuditEventType.SYSTEM_START,
            actor="system",
            action="record_keeper_initialized",
            details={"retention_policy": retention_policy.name}
        )

    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        with self._lock:
            self._event_counter += 1
            timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S%f")
            return f"EVT-{timestamp}-{self._event_counter:06d}"

    def _hash_data(self, data: Any) -> str:
        """Create SHA-256 hash of data."""
        if data is None:
            return ""
        data_str = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def log_event(
        self,
        event_type: AuditEventType,
        actor: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        input_data: Any = None,
        output_data: Any = None,
        session_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        entity_id: Optional[str] = None
    ) -> AuditEvent:
        """
        Log an audit event.

        Args:
            event_type: Type of event
            actor: Who/what triggered the event
            action: Description of the action
            details: Additional event details
            input_data: Input data (will be hashed)
            output_data: Output data (will be hashed)
            session_id: Session identifier
            correlation_id: Correlation ID for tracing
            entity_id: Entity to associate with audit trail

        Returns:
            Created AuditEvent
        """
        event = AuditEvent(
            event_id=self._generate_event_id(),
            event_type=event_type,
            timestamp=datetime.utcnow(),
            ai_system_id=self.ai_system_id,
            actor=actor,
            action=action,
            details=details or {},
            input_data_hash=self._hash_data(input_data) if input_data else None,
            output_data_hash=self._hash_data(output_data) if output_data else None,
            session_id=session_id,
            correlation_id=correlation_id
        )

        with self._lock:
            self._events.append(event)

            # Associate with audit trail if entity_id provided
            if entity_id:
                if entity_id not in self._audit_trails:
                    self._audit_trails[entity_id] = AuditTrail(
                        entity_id=entity_id,
                        entity_type="unknown"
                    )
                self._audit_trails[entity_id].add_event(event)

            # Trim events if exceeding max
            if len(self._events) > self.max_events_in_memory:
                self._events = self._events[-self.max_events_in_memory:]

        # Trigger event handlers
        self._trigger_handlers(event)

        return event

    def log_decision(
        self,
        decision_id: str,
        decision_type: str,
        input_data: Any,
        output: Any,
        confidence: float,
        actor: str,
        rationale: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> AuditEvent:
        """
        Log an AI decision event with full traceability.

        Args:
            decision_id: Unique decision identifier
            decision_type: Type of decision made
            input_data: Input that led to decision
            output: Decision output/result
            confidence: Confidence score (0-1)
            actor: System component making decision
            rationale: Optional explanation of decision
            session_id: Session identifier

        Returns:
            Created AuditEvent
        """
        return self.log_event(
            event_type=AuditEventType.DECISION_MADE,
            actor=actor,
            action=f"decision:{decision_type}",
            details={
                "decision_id": decision_id,
                "decision_type": decision_type,
                "confidence": confidence,
                "rationale": rationale,
                "output_summary": str(output)[:500]  # Truncate for storage
            },
            input_data=input_data,
            output_data=output,
            session_id=session_id,
            entity_id=decision_id
        )

    def log_error(
        self,
        error_type: str,
        error_message: str,
        stack_trace: Optional[str] = None,
        actor: str = "system",
        severity: str = "error",
        correlation_id: Optional[str] = None
    ) -> AuditEvent:
        """
        Log an error event.

        Args:
            error_type: Type of error
            error_message: Error message
            stack_trace: Optional stack trace
            actor: Component where error occurred
            severity: Error severity level
            correlation_id: Correlation ID for tracing

        Returns:
            Created AuditEvent
        """
        return self.log_event(
            event_type=AuditEventType.ERROR_OCCURRED,
            actor=actor,
            action=f"error:{error_type}",
            details={
                "error_type": error_type,
                "error_message": error_message,
                "stack_trace": stack_trace,
                "severity": severity
            },
            correlation_id=correlation_id
        )

    def log_human_intervention(
        self,
        intervention_type: str,
        user_id: str,
        decision_id: Optional[str] = None,
        original_output: Any = None,
        modified_output: Any = None,
        reason: str = ""
    ) -> AuditEvent:
        """
        Log a human intervention event.

        Args:
            intervention_type: Type of intervention
            user_id: User who intervened
            decision_id: Decision that was intervened
            original_output: Original AI output
            modified_output: Modified output after intervention
            reason: Reason for intervention

        Returns:
            Created AuditEvent
        """
        return self.log_event(
            event_type=AuditEventType.HUMAN_INTERVENTION,
            actor=user_id,
            action=f"intervention:{intervention_type}",
            details={
                "intervention_type": intervention_type,
                "decision_id": decision_id,
                "reason": reason,
                "original_output_hash": self._hash_data(original_output),
                "modified_output_hash": self._hash_data(modified_output)
            },
            entity_id=decision_id
        )

    def register_event_handler(
        self,
        event_type: AuditEventType,
        handler: Callable[[AuditEvent], None]
    ) -> None:
        """
        Register a handler for specific event types.

        Args:
            event_type: Event type to handle
            handler: Callback function
        """
        self._event_handlers[event_type].append(handler)

    def _trigger_handlers(self, event: AuditEvent) -> None:
        """Trigger registered handlers for an event."""
        for handler in self._event_handlers[event.event_type]:
            try:
                handler(event)
            except Exception:
                pass  # Don't let handler errors affect logging

    def get_audit_trail(self, entity_id: str) -> Optional[AuditTrail]:
        """
        Get complete audit trail for an entity.

        Args:
            entity_id: Entity identifier

        Returns:
            AuditTrail or None if not found
        """
        return self._audit_trails.get(entity_id)

    def get_events(
        self,
        event_type: Optional[AuditEventType] = None,
        actor: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditEvent]:
        """
        Query events with filters.

        Args:
            event_type: Filter by event type
            actor: Filter by actor
            start_time: Filter from this time
            end_time: Filter until this time
            limit: Maximum events to return

        Returns:
            List of matching events
        """
        results = self._events.copy()

        if event_type:
            results = [e for e in results if e.event_type == event_type]
        if actor:
            results = [e for e in results if e.actor == actor]
        if start_time:
            results = [e for e in results if e.timestamp >= start_time]
        if end_time:
            results = [e for e in results if e.timestamp <= end_time]

        # Return most recent events first
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    def get_events_by_correlation(self, correlation_id: str) -> List[AuditEvent]:
        """Get all events with a specific correlation ID."""
        return [e for e in self._events if e.correlation_id == correlation_id]

    def verify_chain_integrity(self) -> Dict[str, Any]:
        """
        Verify integrity of the entire audit log chain.

        Returns:
            Dictionary with verification results
        """
        invalid_events = []
        for event in self._events:
            if not event.verify_integrity():
                invalid_events.append(event.event_id)

        return {
            "total_events": len(self._events),
            "verified_events": len(self._events) - len(invalid_events),
            "invalid_events": invalid_events,
            "chain_valid": len(invalid_events) == 0,
            "verification_timestamp": datetime.utcnow().isoformat()
        }

    def apply_retention_policy(self) -> Dict[str, int]:
        """
        Apply retention policy and remove expired events.

        Returns:
            Dictionary with deletion statistics
        """
        if self.retention_policy == RetentionPolicy.PERMANENT:
            return {"deleted": 0, "retained": len(self._events)}

        retention_days = self.retention_policy.value
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        with self._lock:
            original_count = len(self._events)
            self._events = [
                e for e in self._events
                if e.timestamp >= cutoff_date
            ]
            deleted_count = original_count - len(self._events)

        return {
            "deleted": deleted_count,
            "retained": len(self._events),
            "retention_days": retention_days,
            "cutoff_date": cutoff_date.isoformat()
        }

    def export_audit_log(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Export audit log for external storage or analysis.

        Args:
            start_time: Export from this time
            end_time: Export until this time

        Returns:
            Dictionary containing exportable audit data
        """
        events = self.get_events(
            start_time=start_time,
            end_time=end_time,
            limit=self.max_events_in_memory
        )

        return {
            "ai_system_id": self.ai_system_id,
            "export_timestamp": datetime.utcnow().isoformat(),
            "retention_policy": self.retention_policy.name,
            "event_count": len(events),
            "events": [e.to_dict() for e in events],
            "integrity_check": self.verify_chain_integrity()
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get audit log statistics."""
        event_counts = defaultdict(int)
        for event in self._events:
            event_counts[event.event_type.value] += 1

        return {
            "ai_system_id": self.ai_system_id,
            "total_events": len(self._events),
            "total_audit_trails": len(self._audit_trails),
            "events_by_type": dict(event_counts),
            "retention_policy": self.retention_policy.name,
            "oldest_event": self._events[0].timestamp.isoformat() if self._events else None,
            "newest_event": self._events[-1].timestamp.isoformat() if self._events else None,
            "statistics_timestamp": datetime.utcnow().isoformat()
        }
