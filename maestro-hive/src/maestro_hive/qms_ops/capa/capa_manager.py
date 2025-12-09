"""
CAPA Manager Module
===================

Provides comprehensive CAPA lifecycle management with workflow automation.
"""

import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class CAPAStatus(Enum):
    """CAPA lifecycle status."""
    DRAFT = "draft"
    OPEN = "open"
    INVESTIGATION = "investigation"
    ACTION_PLANNING = "action_planning"
    IMPLEMENTATION = "implementation"
    VERIFICATION = "verification"
    CLOSED = "closed"
    REJECTED = "rejected"


class CAPAType(Enum):
    """Type of CAPA action."""
    CORRECTIVE = "corrective"
    PREVENTIVE = "preventive"
    BOTH = "corrective_and_preventive"


class Priority(Enum):
    """CAPA priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class CAPAAction:
    """Individual action within a CAPA."""
    id: str
    description: str
    responsible_party: str
    due_date: datetime
    status: str = "pending"
    completed_date: Optional[datetime] = None
    evidence: List[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class CAPA:
    """Corrective and Preventive Action record."""
    id: str
    title: str
    description: str
    capa_type: CAPAType
    status: CAPAStatus
    priority: Priority
    created_at: datetime
    created_by: str
    source_nc_id: Optional[str] = None
    root_cause: str = ""
    root_cause_analysis: Dict[str, Any] = field(default_factory=dict)
    actions: List[CAPAAction] = field(default_factory=list)
    due_date: Optional[datetime] = None
    closed_date: Optional[datetime] = None
    effectiveness_review_date: Optional[datetime] = None
    effectiveness_verified: bool = False
    attachments: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_overdue(self) -> bool:
        """Check if CAPA is past due date."""
        if self.due_date and self.status not in [CAPAStatus.CLOSED, CAPAStatus.REJECTED]:
            return datetime.utcnow() > self.due_date
        return False

    @property
    def days_open(self) -> int:
        """Calculate days since CAPA was opened."""
        end_date = self.closed_date or datetime.utcnow()
        return (end_date - self.created_at).days

    @property
    def completion_percentage(self) -> float:
        """Calculate action completion percentage."""
        if not self.actions:
            return 0.0
        completed = sum(1 for a in self.actions if a.status == "completed")
        return (completed / len(self.actions)) * 100


class CAPALogger:
    """Logging utility for CAPA events."""

    def __init__(self, name: str = "qms-capa"):
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def log_event(self, capa_id: str, event: str, details: str = "") -> None:
        """Log a CAPA event."""
        self.logger.info(f"CAPA_EVENT | capa_id={capa_id} | event={event} | {details}")


class CAPAWorkflow:
    """Manages CAPA workflow transitions."""

    ALLOWED_TRANSITIONS = {
        CAPAStatus.DRAFT: [CAPAStatus.OPEN, CAPAStatus.REJECTED],
        CAPAStatus.OPEN: [CAPAStatus.INVESTIGATION, CAPAStatus.REJECTED],
        CAPAStatus.INVESTIGATION: [CAPAStatus.ACTION_PLANNING, CAPAStatus.OPEN],
        CAPAStatus.ACTION_PLANNING: [CAPAStatus.IMPLEMENTATION, CAPAStatus.INVESTIGATION],
        CAPAStatus.IMPLEMENTATION: [CAPAStatus.VERIFICATION, CAPAStatus.ACTION_PLANNING],
        CAPAStatus.VERIFICATION: [CAPAStatus.CLOSED, CAPAStatus.IMPLEMENTATION],
        CAPAStatus.CLOSED: [],
        CAPAStatus.REJECTED: [],
    }

    @classmethod
    def can_transition(cls, from_status: CAPAStatus, to_status: CAPAStatus) -> bool:
        """Check if status transition is allowed."""
        return to_status in cls.ALLOWED_TRANSITIONS.get(from_status, [])

    @classmethod
    def get_next_statuses(cls, current: CAPAStatus) -> List[CAPAStatus]:
        """Get allowed next statuses."""
        return cls.ALLOWED_TRANSITIONS.get(current, [])


class CAPAManager:
    """
    Manages CAPA lifecycle and operations.

    Provides complete CAPA management including creation, workflow,
    action tracking, and effectiveness verification.
    """

    def __init__(self, storage_backend: Optional[Any] = None):
        self.capas: Dict[str, CAPA] = {}
        self.storage = storage_backend
        self.logger = CAPALogger()
        self._event_handlers: Dict[str, List[Callable]] = {}

    def create_capa(
        self,
        title: str,
        description: str,
        capa_type: CAPAType,
        priority: Priority,
        created_by: str,
        source_nc_id: Optional[str] = None,
        due_days: int = 90
    ) -> CAPA:
        """
        Create a new CAPA record.

        Args:
            title: CAPA title
            description: Detailed description
            capa_type: Corrective, Preventive, or Both
            priority: Priority level
            created_by: User creating the CAPA
            source_nc_id: Optional linked non-conformance ID
            due_days: Days until due (default 90)

        Returns:
            Created CAPA object
        """
        capa_id = f"CAPA-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        now = datetime.utcnow()

        capa = CAPA(
            id=capa_id,
            title=title,
            description=description,
            capa_type=capa_type,
            status=CAPAStatus.DRAFT,
            priority=priority,
            created_at=now,
            created_by=created_by,
            source_nc_id=source_nc_id,
            due_date=now + timedelta(days=due_days)
        )

        self.capas[capa_id] = capa
        self.logger.log_event(capa_id, "CREATED", f"type={capa_type.value} priority={priority.value}")
        self._trigger_event("capa_created", capa)

        return capa

    def get_capa(self, capa_id: str) -> Optional[CAPA]:
        """Get a CAPA by ID."""
        return self.capas.get(capa_id)

    def update_status(self, capa_id: str, new_status: CAPAStatus, updated_by: str) -> CAPA:
        """
        Update CAPA status with workflow validation.

        Args:
            capa_id: CAPA identifier
            new_status: Target status
            updated_by: User making the change

        Returns:
            Updated CAPA

        Raises:
            ValueError: If transition is not allowed
        """
        capa = self.get_capa(capa_id)
        if not capa:
            raise ValueError(f"CAPA {capa_id} not found")

        if not CAPAWorkflow.can_transition(capa.status, new_status):
            raise ValueError(
                f"Cannot transition from {capa.status.value} to {new_status.value}"
            )

        old_status = capa.status
        capa.status = new_status

        if new_status == CAPAStatus.CLOSED:
            capa.closed_date = datetime.utcnow()
            capa.effectiveness_review_date = datetime.utcnow() + timedelta(days=90)

        self.logger.log_event(
            capa_id, "STATUS_CHANGED",
            f"from={old_status.value} to={new_status.value} by={updated_by}"
        )
        self._trigger_event("status_changed", capa, old_status, new_status)

        return capa

    def add_action(
        self,
        capa_id: str,
        description: str,
        responsible_party: str,
        due_date: datetime
    ) -> CAPAAction:
        """Add an action to a CAPA."""
        capa = self.get_capa(capa_id)
        if not capa:
            raise ValueError(f"CAPA {capa_id} not found")

        action = CAPAAction(
            id=f"ACT-{str(uuid.uuid4())[:8].upper()}",
            description=description,
            responsible_party=responsible_party,
            due_date=due_date
        )

        capa.actions.append(action)
        self.logger.log_event(capa_id, "ACTION_ADDED", f"action_id={action.id}")

        return action

    def complete_action(
        self,
        capa_id: str,
        action_id: str,
        evidence: List[str] = None,
        notes: str = ""
    ) -> CAPAAction:
        """Mark an action as completed."""
        capa = self.get_capa(capa_id)
        if not capa:
            raise ValueError(f"CAPA {capa_id} not found")

        action = next((a for a in capa.actions if a.id == action_id), None)
        if not action:
            raise ValueError(f"Action {action_id} not found")

        action.status = "completed"
        action.completed_date = datetime.utcnow()
        action.evidence = evidence or []
        action.notes = notes

        self.logger.log_event(capa_id, "ACTION_COMPLETED", f"action_id={action_id}")

        return action

    def set_root_cause(
        self,
        capa_id: str,
        root_cause: str,
        analysis: Dict[str, Any] = None
    ) -> CAPA:
        """Set the root cause for a CAPA."""
        capa = self.get_capa(capa_id)
        if not capa:
            raise ValueError(f"CAPA {capa_id} not found")

        capa.root_cause = root_cause
        capa.root_cause_analysis = analysis or {}

        self.logger.log_event(capa_id, "ROOT_CAUSE_SET", f"cause={root_cause[:50]}...")

        return capa

    def verify_effectiveness(self, capa_id: str, verified: bool, notes: str = "") -> CAPA:
        """Verify CAPA effectiveness."""
        capa = self.get_capa(capa_id)
        if not capa:
            raise ValueError(f"CAPA {capa_id} not found")

        capa.effectiveness_verified = verified
        capa.metadata["effectiveness_notes"] = notes
        capa.metadata["effectiveness_verified_at"] = datetime.utcnow().isoformat()

        self.logger.log_event(capa_id, "EFFECTIVENESS_VERIFIED", f"verified={verified}")

        return capa

    def get_overdue_capas(self) -> List[CAPA]:
        """Get all overdue CAPAs."""
        return [c for c in self.capas.values() if c.is_overdue]

    def get_capas_by_status(self, status: CAPAStatus) -> List[CAPA]:
        """Get CAPAs by status."""
        return [c for c in self.capas.values() if c.status == status]

    def get_capas_by_priority(self, priority: Priority) -> List[CAPA]:
        """Get CAPAs by priority."""
        return [c for c in self.capas.values() if c.priority == priority]

    def get_statistics(self) -> Dict[str, Any]:
        """Get CAPA statistics."""
        all_capas = list(self.capas.values())
        return {
            "total": len(all_capas),
            "by_status": {
                status.value: len([c for c in all_capas if c.status == status])
                for status in CAPAStatus
            },
            "by_priority": {
                priority.value: len([c for c in all_capas if c.priority == priority])
                for priority in Priority
            },
            "overdue": len(self.get_overdue_capas()),
            "avg_days_open": (
                sum(c.days_open for c in all_capas) / len(all_capas)
                if all_capas else 0
            )
        }

    def on_event(self, event_name: str, handler: Callable) -> None:
        """Register an event handler."""
        if event_name not in self._event_handlers:
            self._event_handlers[event_name] = []
        self._event_handlers[event_name].append(handler)

    def _trigger_event(self, event_name: str, *args, **kwargs) -> None:
        """Trigger event handlers."""
        for handler in self._event_handlers.get(event_name, []):
            try:
                handler(*args, **kwargs)
            except Exception as e:
                self.logger.logger.error(f"Event handler error: {e}")
