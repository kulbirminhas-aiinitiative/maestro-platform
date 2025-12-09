"""
Compliance Logger Service
Provides PII-masked audit logging for all oversight actions
EU AI Act Article 14 Compliance - EPIC: MD-2158
"""

import re
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Pattern, Callable


class OversightActionType(Enum):
    """Types of oversight actions."""
    OVERRIDE = "override"
    BYPASS = "bypass"
    ESCALATE = "escalate"
    PAUSE = "pause"
    RESUME = "resume"
    APPROVE = "approve"
    REJECT = "reject"
    AMEND = "amend"


@dataclass
class AuditLogEntry:
    """Audit log entry for oversight actions."""
    id: str
    context_id: str
    action: str
    actor: str
    target: str
    details: Dict[str, Any]
    timestamp: datetime
    pii_masked: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "context_id": self.context_id,
            "action": self.action,
            "actor": self.actor,
            "target": self.target,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "pii_masked": self.pii_masked,
        }


@dataclass
class ComplianceContext:
    """Context for compliance operations."""
    session_id: str
    user_id: str
    operation_type: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class PIIMasker:
    """
    PII Masker for compliance logging.
    Masks sensitive data patterns in strings and objects.
    """

    # PII patterns to mask
    PATTERNS: List[tuple[Pattern, str]] = [
        (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL_MASKED]'),
        (re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'), '[PHONE_MASKED]'),
        (re.compile(r'\b\d{3}[-]?\d{2}[-]?\d{4}\b'), '[SSN_MASKED]'),
        (re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'), '[CARD_MASKED]'),
        (re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'), '[IP_MASKED]'),
        (re.compile(r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b'), '[IBAN_MASKED]'),
        (re.compile(r'\b[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?\b'), '[SWIFT_MASKED]'),
    ]

    @classmethod
    def mask_string(cls, text: str) -> str:
        """Mask PII patterns in a string."""
        if not isinstance(text, str):
            return text
        masked = text
        for pattern, replacement in cls.PATTERNS:
            masked = pattern.sub(replacement, masked)
        return masked

    @classmethod
    def mask_object(cls, obj: Any) -> Any:
        """Recursively mask PII in an object."""
        if isinstance(obj, str):
            return cls.mask_string(obj)
        elif isinstance(obj, dict):
            return {k: cls.mask_object(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [cls.mask_object(item) for item in obj]
        return obj


class ComplianceLogger:
    """
    Compliance Logger with PII masking.
    Provides audit logging for all oversight actions with
    automatic PII masking for EU AI Act compliance.
    """

    def __init__(
        self,
        db_client: Optional[Any] = None,
        kafka_producer: Optional[Any] = None,
        audit_topic: str = "compliance.oversight.audit"
    ):
        """
        Initialize compliance logger.

        Args:
            db_client: Optional database client for persistence
            kafka_producer: Optional Kafka producer for streaming
            audit_topic: Kafka topic for audit events
        """
        self._db = db_client
        self._kafka = kafka_producer
        self._audit_topic = audit_topic
        self._entries: Dict[str, AuditLogEntry] = {}

    def _generate_id(self) -> str:
        """Generate unique audit entry ID."""
        return f"audit_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"

    async def log_action(
        self,
        action: OversightActionType,
        actor: str,
        target: str,
        details: Dict[str, Any],
        context: Optional[ComplianceContext] = None
    ) -> AuditLogEntry:
        """
        Log an oversight action with PII masking.

        Args:
            action: Type of oversight action
            actor: User/system performing the action
            target: Target of the action
            details: Action details
            context: Optional compliance context

        Returns:
            Created AuditLogEntry
        """
        entry_id = self._generate_id()
        timestamp = datetime.utcnow()

        # Mask PII in all fields
        masked_actor = PIIMasker.mask_string(actor)
        masked_target = PIIMasker.mask_string(target)
        masked_details = PIIMasker.mask_object(details)

        entry = AuditLogEntry(
            id=entry_id,
            context_id=context.session_id if context else "unknown",
            action=action.value if isinstance(action, OversightActionType) else action,
            actor=masked_actor,
            target=masked_target,
            details=masked_details,
            timestamp=timestamp,
            pii_masked=True,
        )

        # Store in memory
        self._entries[entry_id] = entry

        # Persist to database if available
        if self._db:
            await self._persist_to_database(entry)

        # Send to Kafka if available
        if self._kafka:
            await self._send_to_kafka(entry)

        return entry

    async def log_override(
        self,
        operator_id: str,
        agent_id: str,
        reason: str,
        severity: str,
        result: bool,
        context: Optional[ComplianceContext] = None
    ) -> AuditLogEntry:
        """Log an agent override action (AC-1)."""
        return await self.log_action(
            OversightActionType.OVERRIDE,
            operator_id,
            agent_id,
            {
                "reason": reason,
                "severity": severity,
                "result": result,
                "action_type": "agent_override",
            },
            context
        )

    async def log_bypass(
        self,
        approver_id: str,
        gate_id: str,
        justification: str,
        scope: str,
        expiry: datetime,
        context: Optional[ComplianceContext] = None
    ) -> AuditLogEntry:
        """Log a quality gate bypass action (AC-2)."""
        return await self.log_action(
            OversightActionType.BYPASS,
            approver_id,
            gate_id,
            {
                "justification": justification,
                "scope": scope,
                "expiry": expiry.isoformat(),
                "action_type": "quality_gate_bypass",
            },
            context
        )

    async def log_escalation(
        self,
        escalator_id: str,
        context_id: str,
        tier: int,
        reason: str,
        priority: str,
        context: Optional[ComplianceContext] = None
    ) -> AuditLogEntry:
        """Log an escalation action (AC-3)."""
        return await self.log_action(
            OversightActionType.ESCALATE,
            escalator_id,
            context_id,
            {
                "tier": tier,
                "reason": reason,
                "priority": priority,
                "action_type": "escalation",
            },
            context
        )

    async def log_amendment(
        self,
        requester_id: str,
        contract_id: str,
        amendment_count: int,
        reason: str,
        status: str,
        context: Optional[ComplianceContext] = None
    ) -> AuditLogEntry:
        """Log a contract amendment action (AC-4)."""
        return await self.log_action(
            OversightActionType.AMEND,
            requester_id,
            contract_id,
            {
                "amendment_count": amendment_count,
                "reason": reason,
                "status": status,
                "action_type": "contract_amendment",
            },
            context
        )

    async def log_workflow_control(
        self,
        operator_id: str,
        workflow_id: str,
        action: str,
        reason: str,
        checkpoint_id: Optional[str] = None,
        context: Optional[ComplianceContext] = None
    ) -> AuditLogEntry:
        """Log a workflow pause/resume action (AC-5)."""
        action_type = OversightActionType.PAUSE if action == "pause" else OversightActionType.RESUME
        return await self.log_action(
            action_type,
            operator_id,
            workflow_id,
            {
                "reason": reason,
                "checkpoint_id": checkpoint_id,
                "action_type": f"workflow_{action}",
            },
            context
        )

    async def log_approval(
        self,
        approver_id: str,
        decision_id: str,
        approved: bool,
        comments: str,
        risk_level: str,
        context: Optional[ComplianceContext] = None
    ) -> AuditLogEntry:
        """Log a decision approval action (AC-6)."""
        action_type = OversightActionType.APPROVE if approved else OversightActionType.REJECT
        return await self.log_action(
            action_type,
            approver_id,
            decision_id,
            {
                "approved": approved,
                "comments": comments,
                "risk_level": risk_level,
                "action_type": "decision_approval",
            },
            context
        )

    def query_logs(
        self,
        action: Optional[str] = None,
        actor: Optional[str] = None,
        target: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLogEntry]:
        """
        Query audit log entries.

        Args:
            action: Filter by action type
            actor: Filter by actor
            target: Filter by target
            start_date: Filter by start date
            end_date: Filter by end date
            limit: Maximum number of entries

        Returns:
            List of matching entries
        """
        results = []
        for entry in self._entries.values():
            if action and entry.action != action:
                continue
            if actor and actor not in entry.actor:
                continue
            if target and target not in entry.target:
                continue
            if start_date and entry.timestamp < start_date:
                continue
            if end_date and entry.timestamp > end_date:
                continue
            results.append(entry)

        # Sort by timestamp descending
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    def get_entry(self, entry_id: str) -> Optional[AuditLogEntry]:
        """Get a specific audit entry by ID."""
        return self._entries.get(entry_id)

    async def _persist_to_database(self, entry: AuditLogEntry) -> None:
        """Persist audit entry to database."""
        if not self._db:
            return
        try:
            await self._db.execute(
                """INSERT INTO oversight_audit_log
                   (id, context_id, action, actor, target, details, timestamp, pii_masked)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8)""",
                entry.id, entry.context_id, entry.action, entry.actor,
                entry.target, json.dumps(entry.details), entry.timestamp, entry.pii_masked
            )
        except Exception:
            pass  # Log but don't fail

    async def _send_to_kafka(self, entry: AuditLogEntry) -> None:
        """Send audit entry to Kafka for real-time streaming."""
        if not self._kafka:
            return
        try:
            await self._kafka.send(self._audit_topic, json.dumps(entry.to_dict()))
        except Exception:
            pass  # Log but don't fail

    def export_logs(self) -> Dict[str, Any]:
        """Export all audit logs."""
        return {
            "entries": [e.to_dict() for e in self._entries.values()],
            "total_count": len(self._entries),
            "export_timestamp": datetime.utcnow().isoformat(),
        }
