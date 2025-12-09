"""
Non-Conformance Tracker Module
==============================

Provides comprehensive NC tracking with workflow management.
"""

import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class NCStatus(Enum):
    """Non-Conformance lifecycle status."""
    IDENTIFIED = "identified"
    UNDER_REVIEW = "under_review"
    CONFIRMED = "confirmed"
    CONTAINMENT = "containment"
    ROOT_CAUSE_ANALYSIS = "root_cause_analysis"
    CAPA_INITIATED = "capa_initiated"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REJECTED = "rejected"


class NCSeverity(Enum):
    """NC severity classification."""
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    OBSERVATION = "observation"


class NCCategory(Enum):
    """NC category classification."""
    PRODUCT = "product"
    PROCESS = "process"
    DOCUMENT = "document"
    SUPPLIER = "supplier"
    CUSTOMER = "customer"
    EQUIPMENT = "equipment"
    PERSONNEL = "personnel"
    OTHER = "other"


@dataclass
class ContainmentAction:
    """Immediate containment action."""
    id: str
    description: str
    responsible_party: str
    implemented_at: Optional[datetime] = None
    effectiveness_verified: bool = False
    notes: str = ""


@dataclass
class NCAttachment:
    """NC attachment/evidence."""
    id: str
    filename: str
    file_type: str
    uploaded_at: datetime
    uploaded_by: str
    description: str = ""


@dataclass
class NonConformance:
    """Non-Conformance record."""
    id: str
    title: str
    description: str
    severity: NCSeverity
    category: NCCategory
    status: NCStatus
    created_at: datetime
    created_by: str
    source: str  # audit, customer, process, etc.
    affected_products: List[str] = field(default_factory=list)
    affected_lots: List[str] = field(default_factory=list)
    location: str = ""
    containment_actions: List[ContainmentAction] = field(default_factory=list)
    root_cause: str = ""
    linked_capa_id: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    attachments: List[NCAttachment] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_critical(self) -> bool:
        """Check if NC is critical severity."""
        return self.severity == NCSeverity.CRITICAL

    @property
    def requires_capa(self) -> bool:
        """Check if NC requires CAPA based on severity."""
        return self.severity in [NCSeverity.CRITICAL, NCSeverity.MAJOR]

    @property
    def days_open(self) -> int:
        """Calculate days since NC was identified."""
        end_date = self.resolved_at or datetime.utcnow()
        return (end_date - self.created_at).days

    @property
    def response_time_hours(self) -> Optional[float]:
        """Calculate response time to first containment action."""
        if self.containment_actions:
            first_action = min(
                (a for a in self.containment_actions if a.implemented_at),
                key=lambda a: a.implemented_at,
                default=None
            )
            if first_action and first_action.implemented_at:
                delta = first_action.implemented_at - self.created_at
                return delta.total_seconds() / 3600
        return None


class NCWorkflow:
    """Manages NC workflow transitions."""

    ALLOWED_TRANSITIONS = {
        NCStatus.IDENTIFIED: [NCStatus.UNDER_REVIEW, NCStatus.REJECTED],
        NCStatus.UNDER_REVIEW: [NCStatus.CONFIRMED, NCStatus.REJECTED],
        NCStatus.CONFIRMED: [NCStatus.CONTAINMENT, NCStatus.ROOT_CAUSE_ANALYSIS],
        NCStatus.CONTAINMENT: [NCStatus.ROOT_CAUSE_ANALYSIS],
        NCStatus.ROOT_CAUSE_ANALYSIS: [NCStatus.CAPA_INITIATED, NCStatus.RESOLVED],
        NCStatus.CAPA_INITIATED: [NCStatus.RESOLVED],
        NCStatus.RESOLVED: [NCStatus.CLOSED],
        NCStatus.CLOSED: [],
        NCStatus.REJECTED: [],
    }

    SEVERITY_RESPONSE_TIMES = {
        NCSeverity.CRITICAL: 4,    # 4 hours
        NCSeverity.MAJOR: 24,      # 24 hours
        NCSeverity.MINOR: 72,      # 72 hours
        NCSeverity.OBSERVATION: 168  # 1 week
    }

    @classmethod
    def can_transition(cls, from_status: NCStatus, to_status: NCStatus) -> bool:
        """Check if status transition is allowed."""
        return to_status in cls.ALLOWED_TRANSITIONS.get(from_status, [])

    @classmethod
    def get_response_time_limit(cls, severity: NCSeverity) -> int:
        """Get response time limit in hours for severity."""
        return cls.SEVERITY_RESPONSE_TIMES.get(severity, 72)


class NCTracker:
    """
    Manages Non-Conformance tracking and workflow.

    Provides complete NC lifecycle management including identification,
    containment, root cause analysis, and closure.
    """

    def __init__(self, capa_manager: Optional[Any] = None):
        self.ncs: Dict[str, NonConformance] = {}
        self.capa_manager = capa_manager
        self.logger = logging.getLogger("qms-nc")
        self._configure_logger()
        self._event_handlers: Dict[str, List[Callable]] = {}

    def _configure_logger(self) -> None:
        """Configure logger."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    def create_nc(
        self,
        title: str,
        description: str,
        severity: NCSeverity,
        category: NCCategory,
        created_by: str,
        source: str = "internal",
        affected_products: List[str] = None,
        affected_lots: List[str] = None,
        location: str = ""
    ) -> NonConformance:
        """
        Create a new Non-Conformance record.

        Args:
            title: NC title
            description: Detailed description
            severity: Severity classification
            category: Category classification
            created_by: User creating the NC
            source: Source of NC (audit, customer, etc.)
            affected_products: List of affected products
            location: Location where NC occurred

        Returns:
            Created NonConformance object
        """
        nc_id = f"NC-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        now = datetime.utcnow()

        nc = NonConformance(
            id=nc_id,
            title=title,
            description=description,
            severity=severity,
            category=category,
            status=NCStatus.IDENTIFIED,
            created_at=now,
            created_by=created_by,
            source=source,
            affected_products=affected_products or [],
            affected_lots=affected_lots or [],
            location=location
        )

        self.ncs[nc_id] = nc

        self.logger.info(
            f"NC_CREATED | nc_id={nc_id} | severity={severity.value} | "
            f"category={category.value} | source={source}"
        )
        self._trigger_event("nc_created", nc)

        # Alert for critical NCs
        if nc.is_critical:
            self._trigger_event("critical_nc_alert", nc)

        return nc

    def get_nc(self, nc_id: str) -> Optional[NonConformance]:
        """Get an NC by ID."""
        return self.ncs.get(nc_id)

    def update_status(self, nc_id: str, new_status: NCStatus, updated_by: str) -> NonConformance:
        """
        Update NC status with workflow validation.

        Args:
            nc_id: NC identifier
            new_status: Target status
            updated_by: User making the change

        Returns:
            Updated NonConformance

        Raises:
            ValueError: If transition is not allowed
        """
        nc = self.get_nc(nc_id)
        if not nc:
            raise ValueError(f"NC {nc_id} not found")

        if not NCWorkflow.can_transition(nc.status, new_status):
            raise ValueError(
                f"Cannot transition from {nc.status.value} to {new_status.value}"
            )

        old_status = nc.status
        nc.status = new_status

        if new_status == NCStatus.RESOLVED:
            nc.resolved_at = datetime.utcnow()
            nc.resolved_by = updated_by

        self.logger.info(
            f"NC_STATUS_CHANGED | nc_id={nc_id} | from={old_status.value} | "
            f"to={new_status.value} | by={updated_by}"
        )
        self._trigger_event("status_changed", nc, old_status, new_status)

        return nc

    def add_containment_action(
        self,
        nc_id: str,
        description: str,
        responsible_party: str
    ) -> ContainmentAction:
        """Add a containment action to an NC."""
        nc = self.get_nc(nc_id)
        if not nc:
            raise ValueError(f"NC {nc_id} not found")

        action = ContainmentAction(
            id=f"CONT-{str(uuid.uuid4())[:8].upper()}",
            description=description,
            responsible_party=responsible_party
        )

        nc.containment_actions.append(action)
        self.logger.info(f"NC_CONTAINMENT_ADDED | nc_id={nc_id} | action_id={action.id}")

        return action

    def implement_containment(
        self,
        nc_id: str,
        action_id: str,
        notes: str = ""
    ) -> ContainmentAction:
        """Mark a containment action as implemented."""
        nc = self.get_nc(nc_id)
        if not nc:
            raise ValueError(f"NC {nc_id} not found")

        action = next((a for a in nc.containment_actions if a.id == action_id), None)
        if not action:
            raise ValueError(f"Containment action {action_id} not found")

        action.implemented_at = datetime.utcnow()
        action.notes = notes

        self.logger.info(f"NC_CONTAINMENT_IMPLEMENTED | nc_id={nc_id} | action_id={action_id}")

        return action

    def set_root_cause(self, nc_id: str, root_cause: str) -> NonConformance:
        """Set the root cause for an NC."""
        nc = self.get_nc(nc_id)
        if not nc:
            raise ValueError(f"NC {nc_id} not found")

        nc.root_cause = root_cause
        self.logger.info(f"NC_ROOT_CAUSE_SET | nc_id={nc_id}")

        return nc

    def initiate_capa(self, nc_id: str, initiated_by: str) -> Optional[str]:
        """
        Initiate a CAPA from this NC.

        Returns:
            CAPA ID if created, None if CAPA manager not available
        """
        nc = self.get_nc(nc_id)
        if not nc:
            raise ValueError(f"NC {nc_id} not found")

        if not self.capa_manager:
            self.logger.warning(f"NC_CAPA_SKIPPED | nc_id={nc_id} | reason=no_capa_manager")
            return None

        # Import here to avoid circular imports
        from .capa_manager import CAPAType, Priority

        # Map NC severity to CAPA priority
        priority_map = {
            NCSeverity.CRITICAL: Priority.CRITICAL,
            NCSeverity.MAJOR: Priority.HIGH,
            NCSeverity.MINOR: Priority.MEDIUM,
            NCSeverity.OBSERVATION: Priority.LOW
        }

        capa = self.capa_manager.create_capa(
            title=f"CAPA for NC: {nc.title}",
            description=f"CAPA initiated from Non-Conformance {nc.id}\n\n{nc.description}",
            capa_type=CAPAType.CORRECTIVE,
            priority=priority_map.get(nc.severity, Priority.MEDIUM),
            created_by=initiated_by,
            source_nc_id=nc.id
        )

        nc.linked_capa_id = capa.id
        nc.status = NCStatus.CAPA_INITIATED

        self.logger.info(f"NC_CAPA_INITIATED | nc_id={nc_id} | capa_id={capa.id}")

        return capa.id

    def add_attachment(
        self,
        nc_id: str,
        filename: str,
        file_type: str,
        uploaded_by: str,
        description: str = ""
    ) -> NCAttachment:
        """Add an attachment to an NC."""
        nc = self.get_nc(nc_id)
        if not nc:
            raise ValueError(f"NC {nc_id} not found")

        attachment = NCAttachment(
            id=f"ATT-{str(uuid.uuid4())[:8].upper()}",
            filename=filename,
            file_type=file_type,
            uploaded_at=datetime.utcnow(),
            uploaded_by=uploaded_by,
            description=description
        )

        nc.attachments.append(attachment)
        return attachment

    def get_ncs_by_status(self, status: NCStatus) -> List[NonConformance]:
        """Get NCs by status."""
        return [nc for nc in self.ncs.values() if nc.status == status]

    def get_ncs_by_severity(self, severity: NCSeverity) -> List[NonConformance]:
        """Get NCs by severity."""
        return [nc for nc in self.ncs.values() if nc.severity == severity]

    def get_overdue_responses(self) -> List[NonConformance]:
        """Get NCs with overdue initial response."""
        overdue = []
        for nc in self.ncs.values():
            if nc.status in [NCStatus.IDENTIFIED, NCStatus.UNDER_REVIEW]:
                limit_hours = NCWorkflow.get_response_time_limit(nc.severity)
                hours_open = (datetime.utcnow() - nc.created_at).total_seconds() / 3600
                if hours_open > limit_hours and not nc.containment_actions:
                    overdue.append(nc)
        return overdue

    def get_statistics(self) -> Dict[str, Any]:
        """Get NC statistics."""
        all_ncs = list(self.ncs.values())
        return {
            "total": len(all_ncs),
            "by_status": {
                status.value: len([nc for nc in all_ncs if nc.status == status])
                for status in NCStatus
            },
            "by_severity": {
                severity.value: len([nc for nc in all_ncs if nc.severity == severity])
                for severity in NCSeverity
            },
            "by_category": {
                category.value: len([nc for nc in all_ncs if nc.category == category])
                for category in NCCategory
            },
            "overdue_responses": len(self.get_overdue_responses()),
            "avg_days_to_resolution": self._calculate_avg_resolution_time()
        }

    def _calculate_avg_resolution_time(self) -> float:
        """Calculate average days to resolution."""
        resolved = [nc for nc in self.ncs.values() if nc.resolved_at]
        if not resolved:
            return 0.0
        total_days = sum(nc.days_open for nc in resolved)
        return total_days / len(resolved)

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
                self.logger.error(f"Event handler error: {e}")
