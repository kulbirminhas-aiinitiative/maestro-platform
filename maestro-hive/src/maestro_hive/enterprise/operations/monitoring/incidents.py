"""
Incident Response Integration - AC-4.

Manages incident lifecycle and response.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, List


class IncidentStatus(str, Enum):
    """Incident status."""
    OPEN = "open"
    INVESTIGATING = "investigating"
    IDENTIFIED = "identified"
    MONITORING = "monitoring"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentPriority(str, Enum):
    """Incident priority/severity."""
    P1 = "p1"  # Critical
    P2 = "p2"  # High
    P3 = "p3"  # Medium
    P4 = "p4"  # Low


@dataclass
class IncidentUpdate:
    """Update to an incident."""
    id: str
    message: str
    status: IncidentStatus
    author: str
    created_at: datetime

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "message": self.message,
            "status": self.status.value,
            "author": self.author,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class Incident:
    """Incident representation."""
    id: str
    title: str
    description: str
    priority: IncidentPriority
    status: IncidentStatus
    created_at: datetime
    created_by: str
    updated_at: datetime
    resolved_at: Optional[datetime] = None
    commander: Optional[str] = None
    related_alerts: list[str] = field(default_factory=list)
    affected_services: list[str] = field(default_factory=list)
    updates: list[IncidentUpdate] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)
    postmortem_url: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "updated_at": self.updated_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "commander": self.commander,
            "related_alerts": self.related_alerts,
            "affected_services": self.affected_services,
            "updates": [u.to_dict() for u in self.updates],
            "labels": self.labels
        }


@dataclass
class OnCallSchedule:
    """On-call schedule entry."""
    id: str
    user: str
    start: datetime
    end: datetime
    escalation_level: int = 1

    def is_active(self, at_time: Optional[datetime] = None) -> bool:
        """Check if schedule is currently active."""
        check_time = at_time or datetime.utcnow()
        return self.start <= check_time <= self.end


class IncidentManager:
    """Manages incident lifecycle and response."""

    def __init__(self):
        self._incidents: dict[str, Incident] = {}
        self._on_call: list[OnCallSchedule] = []
        self._escalation_policies: dict[str, list[str]] = {}

    async def create(
        self,
        title: str,
        description: str,
        priority: IncidentPriority,
        created_by: str,
        related_alerts: Optional[list[str]] = None,
        affected_services: Optional[list[str]] = None
    ) -> Incident:
        """Create new incident."""
        now = datetime.utcnow()
        incident = Incident(
            id=str(uuid.uuid4()),
            title=title,
            description=description,
            priority=priority,
            status=IncidentStatus.OPEN,
            created_at=now,
            created_by=created_by,
            updated_at=now,
            related_alerts=related_alerts or [],
            affected_services=affected_services or []
        )

        self._incidents[incident.id] = incident

        # Auto-assign commander from on-call
        commander = self._get_on_call_user()
        if commander:
            incident.commander = commander

        return incident

    async def update_status(
        self,
        incident_id: str,
        status: IncidentStatus,
        message: str,
        author: str
    ) -> Optional[Incident]:
        """Update incident status."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return None

        incident.status = status
        incident.updated_at = datetime.utcnow()

        update = IncidentUpdate(
            id=str(uuid.uuid4()),
            message=message,
            status=status,
            author=author,
            created_at=datetime.utcnow()
        )
        incident.updates.append(update)

        if status == IncidentStatus.RESOLVED:
            incident.resolved_at = datetime.utcnow()

        return incident

    async def add_update(
        self,
        incident_id: str,
        message: str,
        author: str
    ) -> Optional[IncidentUpdate]:
        """Add update to incident."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return None

        update = IncidentUpdate(
            id=str(uuid.uuid4()),
            message=message,
            status=incident.status,
            author=author,
            created_at=datetime.utcnow()
        )
        incident.updates.append(update)
        incident.updated_at = datetime.utcnow()

        return update

    async def assign_commander(
        self,
        incident_id: str,
        commander: str
    ) -> Optional[Incident]:
        """Assign incident commander."""
        incident = self._incidents.get(incident_id)
        if incident:
            incident.commander = commander
            incident.updated_at = datetime.utcnow()
            return incident
        return None

    async def get(self, incident_id: str) -> Optional[Incident]:
        """Get incident by ID."""
        return self._incidents.get(incident_id)

    async def list(
        self,
        status: Optional[IncidentStatus] = None,
        priority: Optional[IncidentPriority] = None,
        limit: int = 100
    ) -> List["Incident"]:
        """List incidents with optional filtering."""
        incidents = list(self._incidents.values())

        if status:
            incidents = [i for i in incidents if i.status == status]

        if priority:
            incidents = [i for i in incidents if i.priority == priority]

        # Sort by priority then created_at
        priority_order = {
            IncidentPriority.P1: 0,
            IncidentPriority.P2: 1,
            IncidentPriority.P3: 2,
            IncidentPriority.P4: 3
        }
        incidents.sort(key=lambda i: (priority_order[i.priority], -i.created_at.timestamp()))

        return incidents[:limit]

    async def get_active(self) -> List["Incident"]:
        """Get all active (non-closed) incidents."""
        return [
            i for i in self._incidents.values()
            if i.status not in [IncidentStatus.RESOLVED, IncidentStatus.CLOSED]
        ]

    def add_on_call(self, schedule: OnCallSchedule) -> None:
        """Add on-call schedule."""
        self._on_call.append(schedule)

    def _get_on_call_user(
        self,
        escalation_level: int = 1
    ) -> Optional[str]:
        """Get current on-call user."""
        now = datetime.utcnow()
        for schedule in self._on_call:
            if schedule.is_active(now) and schedule.escalation_level == escalation_level:
                return schedule.user
        return None

    def set_escalation_policy(self, service: str, users: list[str]) -> None:
        """Set escalation policy for service."""
        self._escalation_policies[service] = users

    async def escalate(self, incident_id: str) -> Optional[str]:
        """Escalate incident to next level."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return None

        # Find next escalation level
        for service in incident.affected_services:
            policy = self._escalation_policies.get(service, [])
            current_idx = policy.index(incident.commander) if incident.commander in policy else -1
            if current_idx < len(policy) - 1:
                next_commander = policy[current_idx + 1]
                incident.commander = next_commander
                incident.updated_at = datetime.utcnow()

                incident.updates.append(IncidentUpdate(
                    id=str(uuid.uuid4()),
                    message=f"Escalated to {next_commander}",
                    status=incident.status,
                    author="system",
                    created_at=datetime.utcnow()
                ))
                return next_commander

        return None

    async def link_postmortem(self, incident_id: str, url: str) -> Optional[Incident]:
        """Link postmortem document to incident."""
        incident = self._incidents.get(incident_id)
        if incident:
            incident.postmortem_url = url
            incident.updated_at = datetime.utcnow()
            return incident
        return None
