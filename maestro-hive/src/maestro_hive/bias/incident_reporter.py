"""
Bias Incident Reporter (MD-2157)

EU AI Act Compliance - Article 10

Handles reporting, tracking, and resolution of bias incidents.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
import json
from pathlib import Path

from .models import (
    BiasIncident,
    BiasVectorType,
    BiasSeverity,
    IncidentStatus
)

logger = logging.getLogger(__name__)


class BiasIncidentReporter:
    """
    Bias incident reporting system.

    Handles the full lifecycle of bias incidents from
    reporting through resolution.
    """

    def __init__(
        self,
        incident_dir: Optional[str] = None,
        auto_persist: bool = True
    ):
        """
        Initialize the incident reporter.

        Args:
            incident_dir: Directory for persisting incidents
            auto_persist: Whether to automatically persist incidents
        """
        self.incident_dir = Path(incident_dir) if incident_dir else None
        self.auto_persist = auto_persist

        # In-memory storage
        self._incidents: Dict[str, BiasIncident] = {}
        self._incidents_by_status: Dict[IncidentStatus, List[str]] = {
            status: [] for status in IncidentStatus
        }

        if self.incident_dir:
            self.incident_dir.mkdir(parents=True, exist_ok=True)

        logger.info("BiasIncidentReporter initialized")

    def report_incident(
        self,
        vector_type: BiasVectorType,
        severity: BiasSeverity,
        title: str,
        description: str,
        affected_agents: Optional[List[str]] = None,
        affected_tasks: Optional[List[str]] = None,
        evidence: Optional[Dict[str, Any]] = None,
        audit_records: Optional[List[str]] = None,
        reporter: str = "system"
    ) -> BiasIncident:
        """
        Report a new bias incident.

        Args:
            vector_type: Type of bias vector involved
            severity: Severity of the incident
            title: Short title for the incident
            description: Detailed description
            affected_agents: List of affected agent IDs
            affected_tasks: List of affected task IDs
            evidence: Supporting evidence
            audit_records: Related audit record IDs
            reporter: Who reported the incident

        Returns:
            Created BiasIncident
        """
        incident = BiasIncident(
            vector_type=vector_type,
            severity=severity,
            title=title,
            description=description,
            affected_agents=affected_agents or [],
            affected_tasks=affected_tasks or [],
            evidence=evidence or {},
            audit_records=audit_records or [],
            reporter=reporter
        )

        self._store_incident(incident)

        logger.info(f"Bias incident reported: {incident.incident_id} - {title}")

        return incident

    def _store_incident(self, incident: BiasIncident):
        """Store an incident."""
        self._incidents[incident.incident_id] = incident
        self._incidents_by_status[incident.status].append(incident.incident_id)

        if self.auto_persist and self.incident_dir:
            self._persist_incident(incident)

    def _persist_incident(self, incident: BiasIncident):
        """Persist an incident to disk."""
        if not self.incident_dir:
            return

        incident_file = self.incident_dir / f"{incident.incident_id}.json"
        with open(incident_file, 'w') as f:
            json.dump(incident.to_dict(), f, indent=2)

    def update_status(
        self,
        incident_id: str,
        new_status: IncidentStatus,
        notes: Optional[str] = None
    ) -> Optional[BiasIncident]:
        """
        Update the status of an incident.

        Args:
            incident_id: ID of the incident
            new_status: New status
            notes: Optional notes about the status change

        Returns:
            Updated incident or None
        """
        incident = self._incidents.get(incident_id)
        if not incident:
            logger.warning(f"Incident not found: {incident_id}")
            return None

        old_status = incident.status

        # Update status tracking
        if incident_id in self._incidents_by_status[old_status]:
            self._incidents_by_status[old_status].remove(incident_id)
        self._incidents_by_status[new_status].append(incident_id)

        # Update incident
        incident.status = new_status
        if notes:
            incident.resolution_notes = (incident.resolution_notes or "") + f"\n[{datetime.now().isoformat()}] {notes}"

        if new_status in [IncidentStatus.RESOLVED, IncidentStatus.FALSE_POSITIVE]:
            incident.resolved_at = datetime.now()

        if self.auto_persist:
            self._persist_incident(incident)

        logger.info(f"Incident {incident_id} status: {old_status.value} -> {new_status.value}")

        return incident

    def apply_mitigation(
        self,
        incident_id: str,
        mitigation: str,
        notes: Optional[str] = None
    ) -> Optional[BiasIncident]:
        """
        Record mitigation applied to an incident.

        Args:
            incident_id: ID of the incident
            mitigation: Description of mitigation applied
            notes: Additional notes

        Returns:
            Updated incident or None
        """
        incident = self._incidents.get(incident_id)
        if not incident:
            logger.warning(f"Incident not found: {incident_id}")
            return None

        incident.mitigation_applied = mitigation
        incident.status = IncidentStatus.MITIGATED

        # Update status tracking
        for status, ids in self._incidents_by_status.items():
            if incident_id in ids:
                ids.remove(incident_id)
        self._incidents_by_status[IncidentStatus.MITIGATED].append(incident_id)

        if notes:
            incident.resolution_notes = (incident.resolution_notes or "") + f"\n[{datetime.now().isoformat()}] Mitigation: {notes}"

        if self.auto_persist:
            self._persist_incident(incident)

        logger.info(f"Mitigation applied to incident {incident_id}: {mitigation}")

        return incident

    def get_incident(self, incident_id: str) -> Optional[BiasIncident]:
        """
        Get an incident by ID.

        Args:
            incident_id: ID of the incident

        Returns:
            BiasIncident or None
        """
        return self._incidents.get(incident_id)

    def get_incidents(
        self,
        status: Optional[IncidentStatus] = None,
        severity: Optional[BiasSeverity] = None,
        vector_type: Optional[BiasVectorType] = None,
        since: Optional[datetime] = None,
        limit: int = 100
    ) -> List[BiasIncident]:
        """
        Query incidents.

        Args:
            status: Filter by status
            severity: Filter by severity
            vector_type: Filter by vector type
            since: Filter incidents after this time
            limit: Maximum incidents to return

        Returns:
            List of matching incidents
        """
        incidents = list(self._incidents.values())

        if status:
            incident_ids = set(self._incidents_by_status.get(status, []))
            incidents = [i for i in incidents if i.incident_id in incident_ids]

        if severity:
            incidents = [i for i in incidents if i.severity == severity]

        if vector_type:
            incidents = [i for i in incidents if i.vector_type == vector_type]

        if since:
            incidents = [i for i in incidents if i.reported_at >= since]

        # Sort by reported_at descending
        incidents = sorted(incidents, key=lambda i: i.reported_at, reverse=True)

        return incidents[:limit]

    def get_open_incidents(self) -> List[BiasIncident]:
        """
        Get all open (unresolved) incidents.

        Returns:
            List of open incidents
        """
        open_statuses = [
            IncidentStatus.REPORTED,
            IncidentStatus.INVESTIGATING,
            IncidentStatus.CONFIRMED
        ]

        incidents = []
        for status in open_statuses:
            incident_ids = self._incidents_by_status.get(status, [])
            incidents.extend([
                self._incidents[id] for id in incident_ids
                if id in self._incidents
            ])

        return sorted(incidents, key=lambda i: i.reported_at, reverse=True)

    def get_incidents_by_agent(self, agent_id: str) -> List[BiasIncident]:
        """
        Get incidents affecting a specific agent.

        Args:
            agent_id: ID of the agent

        Returns:
            List of related incidents
        """
        return [
            incident for incident in self._incidents.values()
            if agent_id in incident.affected_agents
        ]

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get incident statistics.

        Returns:
            Statistics dictionary
        """
        by_severity = {}
        by_vector_type = {}
        by_status = {}

        for incident in self._incidents.values():
            by_severity[incident.severity.value] = by_severity.get(incident.severity.value, 0) + 1
            by_vector_type[incident.vector_type.value] = by_vector_type.get(incident.vector_type.value, 0) + 1
            by_status[incident.status.value] = by_status.get(incident.status.value, 0) + 1

        open_incidents = self.get_open_incidents()

        return {
            'total_incidents': len(self._incidents),
            'open_incidents': len(open_incidents),
            'by_severity': by_severity,
            'by_vector_type': by_vector_type,
            'by_status': by_status,
            'high_severity_open': len([i for i in open_incidents if i.severity in [BiasSeverity.HIGH, BiasSeverity.CRITICAL]])
        }

    def export_incidents(
        self,
        output_path: str,
        since: Optional[datetime] = None
    ) -> int:
        """
        Export incidents to a JSON file.

        Args:
            output_path: Path to output file
            since: Export incidents after this time

        Returns:
            Number of incidents exported
        """
        incidents = self.get_incidents(since=since, limit=10000)

        output_path = Path(output_path)
        with open(output_path, 'w') as f:
            json.dump(
                [i.to_dict() for i in incidents],
                f,
                indent=2
            )

        return len(incidents)


# Global instance
_incident_reporter: Optional[BiasIncidentReporter] = None


def get_incident_reporter() -> BiasIncidentReporter:
    """Get or create global incident reporter instance."""
    global _incident_reporter
    if _incident_reporter is None:
        _incident_reporter = BiasIncidentReporter()
    return _incident_reporter
