"""
Recovery Manager for AI Systems
EU AI Act Article 15 Compliance - Incident Response

Provides rollback and recovery mechanisms for security incidents.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import hashlib
import json


class RecoveryActionType(Enum):
    """Types of recovery actions."""
    ROLLBACK = "rollback"
    RESTART = "restart"
    FAILOVER = "failover"
    ISOLATE = "isolate"
    RESTORE = "restore"
    SCALE = "scale"
    BLOCK = "block"
    ALERT = "alert"


class IncidentSeverity(Enum):
    """Severity of security incidents."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(Enum):
    """Status of an incident."""
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class RollbackPoint:
    """A point-in-time snapshot for rollback."""
    point_id: str
    name: str
    created_at: datetime
    description: str
    state_snapshot: Dict[str, Any]
    model_version: Optional[str] = None
    config_version: Optional[str] = None
    is_valid: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "point_id": self.point_id,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "model_version": self.model_version,
            "config_version": self.config_version,
            "is_valid": self.is_valid,
        }


@dataclass
class RecoveryAction:
    """A recovery action taken."""
    action_id: str
    action_type: RecoveryActionType
    target: str
    initiated_by: str
    initiated_at: datetime
    completed_at: Optional[datetime] = None
    success: bool = False
    details: Dict[str, Any] = field(default_factory=dict)
    rollback_point_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "target": self.target,
            "initiated_by": self.initiated_by,
            "initiated_at": self.initiated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "success": self.success,
            "details": self.details,
            "rollback_point_id": self.rollback_point_id,
        }


@dataclass
class IncidentResponse:
    """Record of an incident and its response."""
    incident_id: str
    title: str
    severity: IncidentSeverity
    status: IncidentStatus
    detected_at: datetime
    description: str
    affected_systems: List[str]
    actions_taken: List[RecoveryAction] = field(default_factory=list)
    root_cause: Optional[str] = None
    resolution_summary: Optional[str] = None
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "incident_id": self.incident_id,
            "title": self.title,
            "severity": self.severity.value,
            "status": self.status.value,
            "detected_at": self.detected_at.isoformat(),
            "description": self.description,
            "affected_systems": self.affected_systems,
            "actions_taken": [a.to_dict() for a in self.actions_taken],
            "root_cause": self.root_cause,
            "resolution_summary": self.resolution_summary,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


class RecoveryManager:
    """
    Manages recovery operations for AI systems.

    Provides:
    - Rollback point management
    - Incident tracking and response
    - Recovery action execution
    - Automatic recovery playbooks
    """

    def __init__(
        self,
        system_id: str,
        max_rollback_points: int = 10,
        auto_recovery_enabled: bool = True,
    ):
        self.system_id = system_id
        self.max_rollback_points = max_rollback_points
        self.auto_recovery_enabled = auto_recovery_enabled

        self._rollback_points: List[RollbackPoint] = []
        self._incidents: List[IncidentResponse] = []
        self._recovery_actions: List[RecoveryAction] = []
        self._recovery_handlers: Dict[RecoveryActionType, Callable] = {}
        self._auto_playbooks: Dict[str, List[Dict[str, Any]]] = {}

    def register_recovery_handler(
        self,
        action_type: RecoveryActionType,
        handler: Callable[[str, Dict[str, Any]], bool],
    ) -> None:
        """Register a handler for a recovery action type."""
        self._recovery_handlers[action_type] = handler

    def register_auto_playbook(
        self,
        trigger_pattern: str,
        actions: List[Dict[str, Any]],
    ) -> None:
        """Register an automatic recovery playbook."""
        self._auto_playbooks[trigger_pattern] = actions

    def create_rollback_point(
        self,
        name: str,
        description: str,
        state_snapshot: Dict[str, Any],
        model_version: Optional[str] = None,
        config_version: Optional[str] = None,
    ) -> RollbackPoint:
        """Create a new rollback point."""
        point_id = hashlib.sha256(
            f"{name}{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:12]

        point = RollbackPoint(
            point_id=point_id,
            name=name,
            created_at=datetime.utcnow(),
            description=description,
            state_snapshot=state_snapshot,
            model_version=model_version,
            config_version=config_version,
        )

        self._rollback_points.append(point)

        # Maintain max points
        while len(self._rollback_points) > self.max_rollback_points:
            oldest = min(self._rollback_points, key=lambda p: p.created_at)
            oldest.is_valid = False
            self._rollback_points.remove(oldest)

        return point

    def get_rollback_points(
        self,
        valid_only: bool = True,
    ) -> List[RollbackPoint]:
        """Get available rollback points."""
        points = self._rollback_points
        if valid_only:
            points = [p for p in points if p.is_valid]
        return sorted(points, key=lambda p: p.created_at, reverse=True)

    def execute_rollback(
        self,
        point_id: str,
        initiated_by: str = "system",
    ) -> RecoveryAction:
        """Execute rollback to a specific point."""
        point = next((p for p in self._rollback_points if p.point_id == point_id), None)

        if not point:
            action = RecoveryAction(
                action_id=self._generate_action_id(),
                action_type=RecoveryActionType.ROLLBACK,
                target=point_id,
                initiated_by=initiated_by,
                initiated_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                success=False,
                details={"error": "Rollback point not found"},
            )
            self._recovery_actions.append(action)
            return action

        if not point.is_valid:
            action = RecoveryAction(
                action_id=self._generate_action_id(),
                action_type=RecoveryActionType.ROLLBACK,
                target=point_id,
                initiated_by=initiated_by,
                initiated_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                success=False,
                details={"error": "Rollback point is no longer valid"},
            )
            self._recovery_actions.append(action)
            return action

        # Execute rollback handler if registered
        success = True
        details = {"rollback_point": point.to_dict()}

        if RecoveryActionType.ROLLBACK in self._recovery_handlers:
            try:
                handler = self._recovery_handlers[RecoveryActionType.ROLLBACK]
                success = handler(point_id, point.state_snapshot)
            except Exception as e:
                success = False
                details["error"] = str(e)

        action = RecoveryAction(
            action_id=self._generate_action_id(),
            action_type=RecoveryActionType.ROLLBACK,
            target=point_id,
            initiated_by=initiated_by,
            initiated_at=datetime.utcnow(),
            completed_at=datetime.utcnow(),
            success=success,
            details=details,
            rollback_point_id=point_id,
        )

        self._recovery_actions.append(action)
        return action

    def _generate_action_id(self) -> str:
        """Generate a unique action ID."""
        return hashlib.sha256(
            f"{datetime.utcnow().isoformat()}{len(self._recovery_actions)}".encode()
        ).hexdigest()[:12]

    def create_incident(
        self,
        title: str,
        severity: IncidentSeverity,
        description: str,
        affected_systems: List[str],
    ) -> IncidentResponse:
        """Create a new incident record."""
        incident_id = hashlib.sha256(
            f"{title}{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:12]

        incident = IncidentResponse(
            incident_id=incident_id,
            title=title,
            severity=severity,
            status=IncidentStatus.DETECTED,
            detected_at=datetime.utcnow(),
            description=description,
            affected_systems=affected_systems,
        )

        self._incidents.append(incident)

        # Trigger auto-recovery if enabled
        if self.auto_recovery_enabled:
            self._check_auto_playbooks(incident)

        return incident

    def _check_auto_playbooks(self, incident: IncidentResponse) -> None:
        """Check if any auto-recovery playbooks should be triggered."""
        incident_text = f"{incident.title} {incident.description}".lower()

        for pattern, actions in self._auto_playbooks.items():
            if pattern.lower() in incident_text:
                for action_def in actions:
                    self.execute_recovery_action(
                        action_type=RecoveryActionType(action_def["type"]),
                        target=action_def.get("target", incident.affected_systems[0] if incident.affected_systems else "system"),
                        initiated_by="auto_playbook",
                        incident_id=incident.incident_id,
                        details=action_def.get("details", {}),
                    )

    def update_incident_status(
        self,
        incident_id: str,
        status: IncidentStatus,
        notes: Optional[str] = None,
    ) -> Optional[IncidentResponse]:
        """Update incident status."""
        incident = next((i for i in self._incidents if i.incident_id == incident_id), None)

        if not incident:
            return None

        incident.status = status

        if status == IncidentStatus.RESOLVED:
            incident.resolved_at = datetime.utcnow()
            if notes:
                incident.resolution_summary = notes

        return incident

    def set_root_cause(
        self,
        incident_id: str,
        root_cause: str,
    ) -> Optional[IncidentResponse]:
        """Set root cause for an incident."""
        incident = next((i for i in self._incidents if i.incident_id == incident_id), None)

        if incident:
            incident.root_cause = root_cause

        return incident

    def execute_recovery_action(
        self,
        action_type: RecoveryActionType,
        target: str,
        initiated_by: str = "system",
        incident_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> RecoveryAction:
        """Execute a recovery action."""
        action = RecoveryAction(
            action_id=self._generate_action_id(),
            action_type=action_type,
            target=target,
            initiated_by=initiated_by,
            initiated_at=datetime.utcnow(),
            details=details or {},
        )

        # Execute handler if registered
        success = True
        if action_type in self._recovery_handlers:
            try:
                handler = self._recovery_handlers[action_type]
                success = handler(target, details or {})
            except Exception as e:
                success = False
                action.details["error"] = str(e)

        action.completed_at = datetime.utcnow()
        action.success = success

        self._recovery_actions.append(action)

        # Link to incident if provided
        if incident_id:
            incident = next((i for i in self._incidents if i.incident_id == incident_id), None)
            if incident:
                incident.actions_taken.append(action)

        return action

    def get_active_incidents(self) -> List[IncidentResponse]:
        """Get all active (non-closed) incidents."""
        return [i for i in self._incidents
                if i.status not in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED)]

    def get_incident_history(
        self,
        days: int = 30,
        severity: Optional[IncidentSeverity] = None,
    ) -> List[IncidentResponse]:
        """Get incident history."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        incidents = [i for i in self._incidents if i.detected_at > cutoff]

        if severity:
            incidents = [i for i in incidents if i.severity == severity]

        return sorted(incidents, key=lambda i: i.detected_at, reverse=True)

    def get_recovery_metrics(self) -> Dict[str, Any]:
        """Get recovery system metrics."""
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)

        recent_incidents_24h = [i for i in self._incidents if i.detected_at > last_24h]
        recent_incidents_7d = [i for i in self._incidents if i.detected_at > last_7d]
        recent_actions_24h = [a for a in self._recovery_actions if a.initiated_at > last_24h]

        # Calculate MTTR (Mean Time To Recovery)
        resolved_incidents = [i for i in recent_incidents_7d
                            if i.resolved_at and i.status == IncidentStatus.RESOLVED]
        if resolved_incidents:
            mttr_seconds = sum(
                (i.resolved_at - i.detected_at).total_seconds()
                for i in resolved_incidents
            ) / len(resolved_incidents)
            mttr_minutes = mttr_seconds / 60
        else:
            mttr_minutes = None

        return {
            "system_id": self.system_id,
            "rollback_points_available": len([p for p in self._rollback_points if p.is_valid]),
            "max_rollback_points": self.max_rollback_points,
            "auto_recovery_enabled": self.auto_recovery_enabled,
            "incidents_24h": len(recent_incidents_24h),
            "incidents_7d": len(recent_incidents_7d),
            "active_incidents": len(self.get_active_incidents()),
            "recovery_actions_24h": len(recent_actions_24h),
            "mttr_minutes": mttr_minutes,
            "severity_distribution_7d": {
                sev.value: sum(1 for i in recent_incidents_7d if i.severity == sev)
                for sev in IncidentSeverity
            },
        }

    def generate_incident_report(
        self,
        incident_id: str,
    ) -> Dict[str, Any]:
        """Generate a detailed incident report."""
        incident = next((i for i in self._incidents if i.incident_id == incident_id), None)

        if not incident:
            return {"error": "Incident not found"}

        time_to_resolve = None
        if incident.resolved_at:
            time_to_resolve = (incident.resolved_at - incident.detected_at).total_seconds() / 60

        return {
            "incident": incident.to_dict(),
            "timeline": [
                {"time": incident.detected_at.isoformat(), "event": "Incident detected"},
                *[
                    {"time": a.initiated_at.isoformat(), "event": f"Action: {a.action_type.value} on {a.target}"}
                    for a in incident.actions_taken
                ],
                *([{"time": incident.resolved_at.isoformat(), "event": "Incident resolved"}]
                  if incident.resolved_at else []),
            ],
            "metrics": {
                "time_to_resolve_minutes": time_to_resolve,
                "actions_taken": len(incident.actions_taken),
                "successful_actions": sum(1 for a in incident.actions_taken if a.success),
            },
            "lessons_learned": self._generate_lessons_learned(incident),
        }

    def _generate_lessons_learned(self, incident: IncidentResponse) -> List[str]:
        """Generate lessons learned from an incident."""
        lessons = []

        if incident.root_cause:
            lessons.append(f"Root cause identified: {incident.root_cause}")

        if not incident.actions_taken:
            lessons.append("Consider implementing automatic recovery for this incident type")

        failed_actions = [a for a in incident.actions_taken if not a.success]
        if failed_actions:
            lessons.append(f"{len(failed_actions)} recovery actions failed - review recovery procedures")

        if incident.severity in (IncidentSeverity.HIGH, IncidentSeverity.CRITICAL):
            lessons.append("High severity incident - consider additional preventive measures")

        return lessons
