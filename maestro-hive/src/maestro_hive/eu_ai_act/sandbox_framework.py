"""
Sandbox Framework Module - EU AI Act Article 53 Compliance

Supports regulatory sandbox compliance with controlled testing
environment and risk monitoring.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
import threading
import uuid


class SandboxStatus(Enum):
    """Status of sandbox session."""
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    EXPIRED = "expired"


class RiskMonitoringLevel(Enum):
    """Level of risk monitoring."""
    MINIMAL = "minimal"
    STANDARD = "standard"
    ENHANCED = "enhanced"
    INTENSIVE = "intensive"


class TestPhase(Enum):
    """Phases of sandbox testing."""
    PREPARATION = "preparation"
    INITIAL_TESTING = "initial_testing"
    EXPANDED_TESTING = "expanded_testing"
    REAL_WORLD_VALIDATION = "real_world_validation"
    FINAL_REVIEW = "final_review"


@dataclass
class SandboxConfiguration:
    """Configuration for sandbox environment."""
    config_id: str
    name: str
    max_users: int
    max_transactions: int
    data_restrictions: List[str]
    geographic_restrictions: List[str]
    time_limit_days: int
    monitoring_level: RiskMonitoringLevel
    safeguards: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class RiskIncident:
    """Risk incident during sandbox testing."""
    incident_id: str
    session_id: str
    incident_type: str
    severity: str
    description: str
    affected_users: int
    mitigation_taken: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    resolved: bool = False
    resolution_notes: Optional[str] = None


@dataclass
class TestResult:
    """Result from sandbox testing."""
    result_id: str
    session_id: str
    test_phase: TestPhase
    test_name: str
    passed: bool
    metrics: Dict[str, Any]
    findings: List[str]
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SandboxSession:
    """A regulatory sandbox session."""
    session_id: str
    ai_system_id: str
    ai_system_name: str
    provider_name: str
    configuration: SandboxConfiguration
    status: SandboxStatus
    current_phase: TestPhase
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    regulatory_authority: str = ""
    supervisor_contact: str = ""
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    test_results: List[TestResult] = field(default_factory=list)
    incidents: List[RiskIncident] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def is_active(self) -> bool:
        """Check if session is currently active."""
        return self.status == SandboxStatus.ACTIVE

    def is_expired(self) -> bool:
        """Check if session has expired."""
        if self.end_date is None:
            return False
        return datetime.utcnow() > self.end_date

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "ai_system_id": self.ai_system_id,
            "ai_system_name": self.ai_system_name,
            "provider_name": self.provider_name,
            "status": self.status.value,
            "current_phase": self.current_phase.value,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "regulatory_authority": self.regulatory_authority,
            "approved_by": self.approved_by,
            "test_results_count": len(self.test_results),
            "incidents_count": len(self.incidents),
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ComplianceReport:
    """Compliance report for regulatory authority."""
    report_id: str
    session_id: str
    report_type: str
    period_start: datetime
    period_end: datetime
    summary: str
    key_findings: List[str]
    risks_identified: List[str]
    mitigations_implemented: List[str]
    metrics: Dict[str, Any]
    recommendations: List[str]
    generated_at: datetime = field(default_factory=datetime.utcnow)


class SandboxFramework:
    """
    Sandbox Framework for EU AI Act Article 53 compliance.

    Provides controlled testing environment for AI systems with
    appropriate safeguards and regulatory oversight.
    """

    def __init__(
        self,
        ai_system_id: str,
        ai_system_name: str,
        provider_name: str,
        regulatory_authority: str = "National AI Authority"
    ):
        """
        Initialize sandbox framework.

        Args:
            ai_system_id: Unique identifier for the AI system
            ai_system_name: Human-readable AI system name
            provider_name: Name of the provider
            regulatory_authority: Name of regulatory authority
        """
        self.ai_system_id = ai_system_id
        self.ai_system_name = ai_system_name
        self.provider_name = provider_name
        self.regulatory_authority = regulatory_authority

        self._sessions: Dict[str, SandboxSession] = {}
        self._configurations: Dict[str, SandboxConfiguration] = {}
        self._reports: Dict[str, ComplianceReport] = {}
        self._risk_monitors: Dict[str, Callable] = {}
        self._lock = threading.Lock()

        # Initialize default configuration
        self._initialize_default_config()

    def _initialize_default_config(self) -> None:
        """Initialize default sandbox configuration."""
        default_config = SandboxConfiguration(
            config_id="CFG-DEFAULT",
            name="Standard Sandbox Configuration",
            max_users=1000,
            max_transactions=10000,
            data_restrictions=["no_real_pii", "no_financial_data", "synthetic_data_only"],
            geographic_restrictions=["EU_only"],
            time_limit_days=180,
            monitoring_level=RiskMonitoringLevel.STANDARD,
            safeguards=[
                "real_time_monitoring",
                "automatic_shutdown_on_critical_risk",
                "user_consent_required",
                "data_minimization",
                "audit_logging"
            ]
        )
        self._configurations[default_config.config_id] = default_config

    def create_configuration(
        self,
        name: str,
        max_users: int,
        max_transactions: int,
        data_restrictions: List[str],
        geographic_restrictions: List[str],
        time_limit_days: int,
        monitoring_level: RiskMonitoringLevel,
        safeguards: List[str]
    ) -> SandboxConfiguration:
        """
        Create a custom sandbox configuration.

        Args:
            name: Configuration name
            max_users: Maximum number of users
            max_transactions: Maximum transactions allowed
            data_restrictions: Data usage restrictions
            geographic_restrictions: Geographic limitations
            time_limit_days: Maximum duration in days
            monitoring_level: Level of risk monitoring
            safeguards: List of required safeguards

        Returns:
            Created SandboxConfiguration
        """
        config_id = f"CFG-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        config = SandboxConfiguration(
            config_id=config_id,
            name=name,
            max_users=max_users,
            max_transactions=max_transactions,
            data_restrictions=data_restrictions,
            geographic_restrictions=geographic_restrictions,
            time_limit_days=time_limit_days,
            monitoring_level=monitoring_level,
            safeguards=safeguards
        )
        self._configurations[config_id] = config
        return config

    def request_sandbox_session(
        self,
        configuration_id: Optional[str] = None,
        supervisor_contact: str = "",
        notes: Optional[List[str]] = None
    ) -> SandboxSession:
        """
        Request a new sandbox session.

        Args:
            configuration_id: Configuration to use (default if None)
            supervisor_contact: Contact for regulatory supervisor
            notes: Initial notes for the session

        Returns:
            Created SandboxSession (pending approval)
        """
        config_id = configuration_id or "CFG-DEFAULT"
        config = self._configurations.get(config_id)

        if not config:
            config = self._configurations["CFG-DEFAULT"]

        session = SandboxSession(
            session_id=str(uuid.uuid4()),
            ai_system_id=self.ai_system_id,
            ai_system_name=self.ai_system_name,
            provider_name=self.provider_name,
            configuration=config,
            status=SandboxStatus.PENDING_APPROVAL,
            current_phase=TestPhase.PREPARATION,
            regulatory_authority=self.regulatory_authority,
            supervisor_contact=supervisor_contact,
            notes=notes or []
        )

        with self._lock:
            self._sessions[session.session_id] = session

        return session

    def approve_session(
        self,
        session_id: str,
        approved_by: str,
        start_date: Optional[datetime] = None
    ) -> bool:
        """
        Approve a sandbox session (typically by regulatory authority).

        Args:
            session_id: Session to approve
            approved_by: Name of approver
            start_date: When to start (default: now)

        Returns:
            True if approved successfully
        """
        if session_id not in self._sessions:
            return False

        session = self._sessions[session_id]
        if session.status != SandboxStatus.PENDING_APPROVAL:
            return False

        start = start_date or datetime.utcnow()
        end = start + timedelta(days=session.configuration.time_limit_days)

        with self._lock:
            session.status = SandboxStatus.ACTIVE
            session.approved_by = approved_by
            session.approved_at = datetime.utcnow()
            session.start_date = start
            session.end_date = end
            session.current_phase = TestPhase.INITIAL_TESTING

        return True

    def advance_phase(
        self,
        session_id: str,
        notes: Optional[str] = None
    ) -> Optional[TestPhase]:
        """
        Advance session to next testing phase.

        Args:
            session_id: Session ID
            notes: Notes for phase transition

        Returns:
            New phase or None if cannot advance
        """
        if session_id not in self._sessions:
            return None

        session = self._sessions[session_id]
        if session.status != SandboxStatus.ACTIVE:
            return None

        phase_order = [
            TestPhase.PREPARATION,
            TestPhase.INITIAL_TESTING,
            TestPhase.EXPANDED_TESTING,
            TestPhase.REAL_WORLD_VALIDATION,
            TestPhase.FINAL_REVIEW
        ]

        current_index = phase_order.index(session.current_phase)
        if current_index >= len(phase_order) - 1:
            return None

        with self._lock:
            session.current_phase = phase_order[current_index + 1]
            if notes:
                session.notes.append(f"Phase advanced: {notes}")

        return session.current_phase

    def record_test_result(
        self,
        session_id: str,
        test_name: str,
        passed: bool,
        metrics: Dict[str, Any],
        findings: List[str],
        recommendations: Optional[List[str]] = None
    ) -> Optional[TestResult]:
        """
        Record a test result.

        Args:
            session_id: Session ID
            test_name: Name of the test
            passed: Whether test passed
            metrics: Test metrics
            findings: Test findings
            recommendations: Recommendations based on findings

        Returns:
            TestResult or None if session not found
        """
        if session_id not in self._sessions:
            return None

        session = self._sessions[session_id]

        result = TestResult(
            result_id=str(uuid.uuid4()),
            session_id=session_id,
            test_phase=session.current_phase,
            test_name=test_name,
            passed=passed,
            metrics=metrics,
            findings=findings,
            recommendations=recommendations or []
        )

        with self._lock:
            session.test_results.append(result)

        return result

    def report_incident(
        self,
        session_id: str,
        incident_type: str,
        severity: str,
        description: str,
        affected_users: int,
        mitigation_taken: str
    ) -> Optional[RiskIncident]:
        """
        Report a risk incident during testing.

        Args:
            session_id: Session ID
            incident_type: Type of incident
            severity: Severity level
            description: Incident description
            affected_users: Number of affected users
            mitigation_taken: Mitigation actions taken

        Returns:
            RiskIncident or None if session not found
        """
        if session_id not in self._sessions:
            return None

        session = self._sessions[session_id]

        incident = RiskIncident(
            incident_id=str(uuid.uuid4()),
            session_id=session_id,
            incident_type=incident_type,
            severity=severity,
            description=description,
            affected_users=affected_users,
            mitigation_taken=mitigation_taken
        )

        with self._lock:
            session.incidents.append(incident)

            # Auto-pause on critical incidents
            if severity.lower() == "critical":
                session.status = SandboxStatus.PAUSED
                session.notes.append(f"Auto-paused due to critical incident: {incident.incident_id}")

        return incident

    def resolve_incident(
        self,
        session_id: str,
        incident_id: str,
        resolution_notes: str
    ) -> bool:
        """
        Mark an incident as resolved.

        Args:
            session_id: Session ID
            incident_id: Incident ID
            resolution_notes: Resolution details

        Returns:
            True if resolved successfully
        """
        if session_id not in self._sessions:
            return False

        session = self._sessions[session_id]

        for incident in session.incidents:
            if incident.incident_id == incident_id:
                with self._lock:
                    incident.resolved = True
                    incident.resolution_notes = resolution_notes
                return True

        return False

    def resume_session(self, session_id: str, notes: str) -> bool:
        """
        Resume a paused session.

        Args:
            session_id: Session ID
            notes: Reason for resuming

        Returns:
            True if resumed successfully
        """
        if session_id not in self._sessions:
            return False

        session = self._sessions[session_id]
        if session.status != SandboxStatus.PAUSED:
            return False

        with self._lock:
            session.status = SandboxStatus.ACTIVE
            session.notes.append(f"Resumed: {notes}")

        return True

    def complete_session(
        self,
        session_id: str,
        final_notes: str
    ) -> bool:
        """
        Complete a sandbox session.

        Args:
            session_id: Session ID
            final_notes: Final notes/summary

        Returns:
            True if completed successfully
        """
        if session_id not in self._sessions:
            return False

        session = self._sessions[session_id]
        if session.status not in [SandboxStatus.ACTIVE, SandboxStatus.PAUSED]:
            return False

        with self._lock:
            session.status = SandboxStatus.COMPLETED
            session.end_date = datetime.utcnow()
            session.notes.append(f"Completed: {final_notes}")

        return True

    def terminate_session(
        self,
        session_id: str,
        reason: str
    ) -> bool:
        """
        Terminate a sandbox session.

        Args:
            session_id: Session ID
            reason: Reason for termination

        Returns:
            True if terminated successfully
        """
        if session_id not in self._sessions:
            return False

        session = self._sessions[session_id]

        with self._lock:
            session.status = SandboxStatus.TERMINATED
            session.end_date = datetime.utcnow()
            session.notes.append(f"Terminated: {reason}")

        return True

    def generate_compliance_report(
        self,
        session_id: str,
        report_type: str = "periodic",
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> Optional[ComplianceReport]:
        """
        Generate a compliance report for regulatory authority.

        Args:
            session_id: Session ID
            report_type: Type of report
            period_start: Report period start
            period_end: Report period end

        Returns:
            ComplianceReport or None if session not found
        """
        if session_id not in self._sessions:
            return None

        session = self._sessions[session_id]
        start = period_start or session.start_date or datetime.utcnow()
        end = period_end or datetime.utcnow()

        # Calculate metrics
        tests_in_period = [
            t for t in session.test_results
            if start <= t.timestamp <= end
        ]
        incidents_in_period = [
            i for i in session.incidents
            if start <= i.timestamp <= end
        ]

        pass_rate = (
            sum(1 for t in tests_in_period if t.passed) / len(tests_in_period)
            if tests_in_period else 0.0
        )

        # Generate findings and recommendations
        findings = []
        recommendations = []
        risks = []

        for test in tests_in_period:
            findings.extend(test.findings)
            recommendations.extend(test.recommendations)

        for incident in incidents_in_period:
            risks.append(f"{incident.severity}: {incident.incident_type}")

        # Create summary
        summary = (
            f"Sandbox session {session_id} - {report_type} report. "
            f"Phase: {session.current_phase.value}. "
            f"Tests run: {len(tests_in_period)}, Pass rate: {pass_rate:.1%}. "
            f"Incidents: {len(incidents_in_period)}."
        )

        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            session_id=session_id,
            report_type=report_type,
            period_start=start,
            period_end=end,
            summary=summary,
            key_findings=list(set(findings))[:10],
            risks_identified=list(set(risks)),
            mitigations_implemented=[i.mitigation_taken for i in incidents_in_period if i.resolved],
            metrics={
                "tests_run": len(tests_in_period),
                "tests_passed": sum(1 for t in tests_in_period if t.passed),
                "pass_rate": pass_rate,
                "incidents_total": len(incidents_in_period),
                "incidents_resolved": sum(1 for i in incidents_in_period if i.resolved),
                "current_phase": session.current_phase.value
            },
            recommendations=list(set(recommendations))[:10]
        )

        with self._lock:
            self._reports[report.report_id] = report

        return report

    def get_session(self, session_id: str) -> Optional[SandboxSession]:
        """Get a specific sandbox session."""
        return self._sessions.get(session_id)

    def get_active_sessions(self) -> List[SandboxSession]:
        """Get all active sandbox sessions."""
        return [s for s in self._sessions.values() if s.is_active()]

    def process_expired_sessions(self) -> List[str]:
        """Process and mark expired sessions."""
        expired = []
        with self._lock:
            for session in self._sessions.values():
                if session.status == SandboxStatus.ACTIVE and session.is_expired():
                    session.status = SandboxStatus.EXPIRED
                    session.notes.append("Session expired due to time limit")
                    expired.append(session.session_id)
        return expired

    def get_statistics(self) -> Dict[str, Any]:
        """Get sandbox framework statistics."""
        status_counts = {}
        phase_counts = {}

        for session in self._sessions.values():
            status_counts[session.status.value] = status_counts.get(session.status.value, 0) + 1
            phase_counts[session.current_phase.value] = phase_counts.get(session.current_phase.value, 0) + 1

        total_tests = sum(len(s.test_results) for s in self._sessions.values())
        total_incidents = sum(len(s.incidents) for s in self._sessions.values())

        return {
            "ai_system_id": self.ai_system_id,
            "regulatory_authority": self.regulatory_authority,
            "total_sessions": len(self._sessions),
            "sessions_by_status": status_counts,
            "sessions_by_phase": phase_counts,
            "total_configurations": len(self._configurations),
            "total_tests_run": total_tests,
            "total_incidents": total_incidents,
            "total_reports_generated": len(self._reports),
            "statistics_timestamp": datetime.utcnow().isoformat()
        }

    def export_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Export all data for a session."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        return {
            "session": session.to_dict(),
            "configuration": {
                "config_id": session.configuration.config_id,
                "name": session.configuration.name,
                "max_users": session.configuration.max_users,
                "max_transactions": session.configuration.max_transactions,
                "time_limit_days": session.configuration.time_limit_days,
                "monitoring_level": session.configuration.monitoring_level.value,
                "safeguards": session.configuration.safeguards
            },
            "test_results": [
                {
                    "result_id": t.result_id,
                    "phase": t.test_phase.value,
                    "test_name": t.test_name,
                    "passed": t.passed,
                    "metrics": t.metrics,
                    "timestamp": t.timestamp.isoformat()
                }
                for t in session.test_results
            ],
            "incidents": [
                {
                    "incident_id": i.incident_id,
                    "type": i.incident_type,
                    "severity": i.severity,
                    "resolved": i.resolved,
                    "timestamp": i.timestamp.isoformat()
                }
                for i in session.incidents
            ],
            "notes": session.notes,
            "export_date": datetime.utcnow().isoformat()
        }
