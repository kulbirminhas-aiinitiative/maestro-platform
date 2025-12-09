"""
Runbook Generator for AI Systems
EU AI Act Article 15 Compliance - Operational Documentation

Generates operational runbooks and incident playbooks.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import json


class RunbookCategory(Enum):
    """Categories of runbook procedures."""
    DEPLOYMENT = "deployment"
    MONITORING = "monitoring"
    INCIDENT_RESPONSE = "incident_response"
    SECURITY = "security"
    MAINTENANCE = "maintenance"
    RECOVERY = "recovery"
    COMPLIANCE = "compliance"


class StepType(Enum):
    """Types of runbook steps."""
    MANUAL = "manual"
    AUTOMATED = "automated"
    DECISION = "decision"
    VERIFICATION = "verification"
    NOTIFICATION = "notification"


@dataclass
class RunbookStep:
    """A single step in a runbook procedure."""
    step_number: int
    title: str
    description: str
    step_type: StepType
    commands: List[str] = field(default_factory=list)
    expected_outcome: str = ""
    rollback_action: str = ""
    duration_minutes: int = 5
    requires_approval: bool = False
    decision_options: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_number": self.step_number,
            "title": self.title,
            "description": self.description,
            "step_type": self.step_type.value,
            "commands": self.commands,
            "expected_outcome": self.expected_outcome,
            "rollback_action": self.rollback_action,
            "duration_minutes": self.duration_minutes,
            "requires_approval": self.requires_approval,
            "decision_options": self.decision_options,
        }

    def to_markdown(self) -> str:
        """Convert to markdown format."""
        md = f"### Step {self.step_number}: {self.title}\n\n"
        md += f"**Type:** {self.step_type.value}\n\n"
        md += f"{self.description}\n\n"

        if self.commands:
            md += "**Commands:**\n```bash\n"
            md += "\n".join(self.commands)
            md += "\n```\n\n"

        if self.expected_outcome:
            md += f"**Expected Outcome:** {self.expected_outcome}\n\n"

        if self.rollback_action:
            md += f"**Rollback:** {self.rollback_action}\n\n"

        if self.requires_approval:
            md += "**Requires Approval:** Yes\n\n"

        if self.decision_options:
            md += "**Decision Points:**\n"
            for opt in self.decision_options:
                md += f"- If {opt.get('condition', 'N/A')}: {opt.get('action', 'N/A')}\n"
            md += "\n"

        return md


@dataclass
class RunbookSection:
    """A section of a runbook."""
    title: str
    description: str
    steps: List[RunbookStep] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "title": self.title,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "prerequisites": self.prerequisites,
            "warnings": self.warnings,
        }

    def to_markdown(self) -> str:
        """Convert to markdown format."""
        md = f"## {self.title}\n\n"
        md += f"{self.description}\n\n"

        if self.prerequisites:
            md += "### Prerequisites\n"
            for prereq in self.prerequisites:
                md += f"- {prereq}\n"
            md += "\n"

        if self.warnings:
            md += "### Warnings\n"
            for warning in self.warnings:
                md += f"- {warning}\n"
            md += "\n"

        for step in self.steps:
            md += step.to_markdown()

        return md


@dataclass
class OperationalProcedure:
    """A complete operational procedure/runbook."""
    procedure_id: str
    title: str
    category: RunbookCategory
    version: str
    description: str
    owner: str
    sections: List[RunbookSection] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    tags: List[str] = field(default_factory=list)
    related_procedures: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "procedure_id": self.procedure_id,
            "title": self.title,
            "category": self.category.value,
            "version": self.version,
            "description": self.description,
            "owner": self.owner,
            "sections": [s.to_dict() for s in self.sections],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "tags": self.tags,
            "related_procedures": self.related_procedures,
        }

    def to_markdown(self) -> str:
        """Convert to markdown format."""
        md = f"# {self.title}\n\n"
        md += f"**Procedure ID:** {self.procedure_id}  \n"
        md += f"**Category:** {self.category.value}  \n"
        md += f"**Version:** {self.version}  \n"
        md += f"**Owner:** {self.owner}  \n"
        md += f"**Last Updated:** {self.updated_at.strftime('%Y-%m-%d')}  \n\n"

        md += f"## Overview\n\n{self.description}\n\n"

        if self.tags:
            md += f"**Tags:** {', '.join(self.tags)}\n\n"

        if self.related_procedures:
            md += "**Related Procedures:** " + ", ".join(self.related_procedures) + "\n\n"

        for section in self.sections:
            md += section.to_markdown()

        return md

    def get_total_duration(self) -> int:
        """Get total estimated duration in minutes."""
        return sum(
            step.duration_minutes
            for section in self.sections
            for step in section.steps
        )


@dataclass
class IncidentPlaybook:
    """A playbook for handling specific incident types."""
    playbook_id: str
    incident_type: str
    severity_levels: List[str]
    title: str
    description: str
    initial_response: List[str]
    investigation_steps: List[RunbookStep]
    mitigation_steps: List[RunbookStep]
    recovery_steps: List[RunbookStep]
    post_incident: List[str]
    escalation_matrix: Dict[str, str]
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "playbook_id": self.playbook_id,
            "incident_type": self.incident_type,
            "severity_levels": self.severity_levels,
            "title": self.title,
            "description": self.description,
            "initial_response": self.initial_response,
            "investigation_steps": [s.to_dict() for s in self.investigation_steps],
            "mitigation_steps": [s.to_dict() for s in self.mitigation_steps],
            "recovery_steps": [s.to_dict() for s in self.recovery_steps],
            "post_incident": self.post_incident,
            "escalation_matrix": self.escalation_matrix,
            "created_at": self.created_at.isoformat(),
        }

    def to_markdown(self) -> str:
        """Convert to markdown format."""
        md = f"# Incident Playbook: {self.title}\n\n"
        md += f"**Playbook ID:** {self.playbook_id}  \n"
        md += f"**Incident Type:** {self.incident_type}  \n"
        md += f"**Severity Levels:** {', '.join(self.severity_levels)}  \n\n"

        md += f"## Description\n\n{self.description}\n\n"

        md += "## Initial Response\n\n"
        for item in self.initial_response:
            md += f"1. {item}\n"
        md += "\n"

        md += "## Investigation Steps\n\n"
        for step in self.investigation_steps:
            md += step.to_markdown()

        md += "## Mitigation Steps\n\n"
        for step in self.mitigation_steps:
            md += step.to_markdown()

        md += "## Recovery Steps\n\n"
        for step in self.recovery_steps:
            md += step.to_markdown()

        md += "## Post-Incident Actions\n\n"
        for item in self.post_incident:
            md += f"- {item}\n"
        md += "\n"

        md += "## Escalation Matrix\n\n"
        md += "| Severity | Contact |\n|----------|----------|\n"
        for sev, contact in self.escalation_matrix.items():
            md += f"| {sev} | {contact} |\n"

        return md


class RunbookGenerator:
    """
    Generates operational runbooks and incident playbooks.

    Provides:
    - Template-based runbook generation
    - Incident playbook creation
    - Runbook validation
    - Export to multiple formats
    """

    def __init__(self, organization: str = "Maestro Platform"):
        self.organization = organization
        self._procedures: Dict[str, OperationalProcedure] = {}
        self._playbooks: Dict[str, IncidentPlaybook] = {}
        self._templates: Dict[str, Dict[str, Any]] = {}
        self._setup_default_templates()

    def _setup_default_templates(self) -> None:
        """Set up default runbook templates."""
        self._templates["security_incident"] = {
            "category": RunbookCategory.INCIDENT_RESPONSE,
            "sections": [
                {
                    "title": "Detection and Assessment",
                    "steps": [
                        {"title": "Identify incident scope", "type": StepType.MANUAL},
                        {"title": "Assess severity", "type": StepType.DECISION},
                        {"title": "Document initial findings", "type": StepType.MANUAL},
                    ],
                },
                {
                    "title": "Containment",
                    "steps": [
                        {"title": "Isolate affected systems", "type": StepType.AUTOMATED},
                        {"title": "Preserve evidence", "type": StepType.MANUAL},
                    ],
                },
                {
                    "title": "Recovery",
                    "steps": [
                        {"title": "Restore from backup", "type": StepType.AUTOMATED},
                        {"title": "Verify system integrity", "type": StepType.VERIFICATION},
                    ],
                },
            ],
        }

        self._templates["model_deployment"] = {
            "category": RunbookCategory.DEPLOYMENT,
            "sections": [
                {
                    "title": "Pre-Deployment Checks",
                    "steps": [
                        {"title": "Verify model artifacts", "type": StepType.VERIFICATION},
                        {"title": "Run integration tests", "type": StepType.AUTOMATED},
                        {"title": "Obtain deployment approval", "type": StepType.MANUAL, "requires_approval": True},
                    ],
                },
                {
                    "title": "Deployment",
                    "steps": [
                        {"title": "Create rollback point", "type": StepType.AUTOMATED},
                        {"title": "Deploy model", "type": StepType.AUTOMATED},
                        {"title": "Verify deployment", "type": StepType.VERIFICATION},
                    ],
                },
                {
                    "title": "Post-Deployment",
                    "steps": [
                        {"title": "Monitor metrics", "type": StepType.VERIFICATION},
                        {"title": "Notify stakeholders", "type": StepType.NOTIFICATION},
                    ],
                },
            ],
        }

        self._templates["drift_detection"] = {
            "category": RunbookCategory.MONITORING,
            "sections": [
                {
                    "title": "Drift Alert Response",
                    "steps": [
                        {"title": "Review drift metrics", "type": StepType.MANUAL},
                        {"title": "Analyze root cause", "type": StepType.MANUAL},
                        {"title": "Determine action required", "type": StepType.DECISION},
                    ],
                },
                {
                    "title": "Remediation",
                    "steps": [
                        {"title": "Schedule retraining if needed", "type": StepType.MANUAL},
                        {"title": "Update monitoring thresholds", "type": StepType.AUTOMATED},
                        {"title": "Document findings", "type": StepType.MANUAL},
                    ],
                },
            ],
        }

    def create_procedure(
        self,
        procedure_id: str,
        title: str,
        category: RunbookCategory,
        description: str,
        owner: str,
        template: Optional[str] = None,
    ) -> OperationalProcedure:
        """Create a new operational procedure."""
        procedure = OperationalProcedure(
            procedure_id=procedure_id,
            title=title,
            category=category,
            version="1.0.0",
            description=description,
            owner=owner,
        )

        if template and template in self._templates:
            procedure = self._apply_template(procedure, self._templates[template])

        self._procedures[procedure_id] = procedure
        return procedure

    def _apply_template(
        self,
        procedure: OperationalProcedure,
        template: Dict[str, Any],
    ) -> OperationalProcedure:
        """Apply a template to a procedure."""
        for section_def in template.get("sections", []):
            section = RunbookSection(
                title=section_def["title"],
                description=section_def.get("description", ""),
            )

            for i, step_def in enumerate(section_def.get("steps", []), 1):
                step = RunbookStep(
                    step_number=i,
                    title=step_def["title"],
                    description=step_def.get("description", ""),
                    step_type=step_def.get("type", StepType.MANUAL),
                    requires_approval=step_def.get("requires_approval", False),
                )
                section.steps.append(step)

            procedure.sections.append(section)

        return procedure

    def add_section(
        self,
        procedure_id: str,
        section: RunbookSection,
    ) -> Optional[OperationalProcedure]:
        """Add a section to a procedure."""
        if procedure_id not in self._procedures:
            return None

        self._procedures[procedure_id].sections.append(section)
        self._procedures[procedure_id].updated_at = datetime.utcnow()
        return self._procedures[procedure_id]

    def create_incident_playbook(
        self,
        playbook_id: str,
        incident_type: str,
        title: str,
        description: str,
        severity_levels: Optional[List[str]] = None,
    ) -> IncidentPlaybook:
        """Create an incident response playbook."""
        playbook = IncidentPlaybook(
            playbook_id=playbook_id,
            incident_type=incident_type,
            severity_levels=severity_levels or ["medium", "high", "critical"],
            title=title,
            description=description,
            initial_response=[
                "Acknowledge the incident",
                "Assess initial severity",
                "Notify on-call team",
                "Begin documentation",
            ],
            investigation_steps=[
                RunbookStep(
                    step_number=1,
                    title="Gather initial information",
                    description="Collect logs, metrics, and alerts",
                    step_type=StepType.MANUAL,
                ),
                RunbookStep(
                    step_number=2,
                    title="Identify affected components",
                    description="Map the blast radius",
                    step_type=StepType.MANUAL,
                ),
            ],
            mitigation_steps=[
                RunbookStep(
                    step_number=1,
                    title="Implement temporary fix",
                    description="Apply immediate mitigation",
                    step_type=StepType.MANUAL,
                ),
            ],
            recovery_steps=[
                RunbookStep(
                    step_number=1,
                    title="Restore normal operations",
                    description="Return to normal state",
                    step_type=StepType.AUTOMATED,
                ),
                RunbookStep(
                    step_number=2,
                    title="Verify recovery",
                    description="Confirm all systems operational",
                    step_type=StepType.VERIFICATION,
                ),
            ],
            post_incident=[
                "Conduct post-incident review",
                "Update documentation",
                "Implement preventive measures",
                "Share lessons learned",
            ],
            escalation_matrix={
                "low": "On-call engineer",
                "medium": "Team lead",
                "high": "Engineering manager",
                "critical": "VP Engineering + Security team",
            },
        )

        self._playbooks[playbook_id] = playbook
        return playbook

    def generate_security_runbook(self) -> OperationalProcedure:
        """Generate a comprehensive security operations runbook."""
        procedure = self.create_procedure(
            procedure_id="SECURITY-OPS-001",
            title="AI Security Operations Runbook",
            category=RunbookCategory.SECURITY,
            description="Comprehensive runbook for AI system security operations, "
                       "including monitoring, incident response, and compliance checks.",
            owner="Security Team",
        )

        # Add monitoring section
        monitoring_section = RunbookSection(
            title="Security Monitoring",
            description="Procedures for ongoing security monitoring",
            prerequisites=[
                "Access to monitoring dashboard",
                "Security alert notifications configured",
            ],
            steps=[
                RunbookStep(
                    step_number=1,
                    title="Review Security Dashboard",
                    description="Check the security monitoring dashboard for anomalies",
                    step_type=StepType.MANUAL,
                    duration_minutes=10,
                ),
                RunbookStep(
                    step_number=2,
                    title="Check Adversarial Detection Alerts",
                    description="Review any triggered adversarial detection alerts",
                    step_type=StepType.MANUAL,
                    commands=["maestro security alerts --last-24h"],
                    duration_minutes=15,
                ),
                RunbookStep(
                    step_number=3,
                    title="Verify Model Integrity",
                    description="Run model integrity checks",
                    step_type=StepType.AUTOMATED,
                    commands=["maestro model verify --all"],
                    expected_outcome="All model checksums match",
                    duration_minutes=5,
                ),
            ],
        )
        procedure.sections.append(monitoring_section)

        # Add incident response section
        incident_section = RunbookSection(
            title="Incident Response",
            description="Procedures for responding to security incidents",
            warnings=[
                "Always preserve evidence before making changes",
                "Follow escalation procedures for high-severity incidents",
            ],
            steps=[
                RunbookStep(
                    step_number=1,
                    title="Initial Assessment",
                    description="Quickly assess the scope and severity of the incident",
                    step_type=StepType.MANUAL,
                    duration_minutes=10,
                    decision_options=[
                        {"condition": "Critical severity", "action": "Escalate immediately"},
                        {"condition": "High severity", "action": "Notify team lead"},
                        {"condition": "Medium/Low severity", "action": "Continue investigation"},
                    ],
                ),
                RunbookStep(
                    step_number=2,
                    title="Contain the Incident",
                    description="Take steps to contain the incident and prevent spread",
                    step_type=StepType.MANUAL,
                    commands=[
                        "maestro security isolate --target <affected_system>",
                        "maestro traffic block --source <malicious_source>",
                    ],
                    duration_minutes=15,
                ),
                RunbookStep(
                    step_number=3,
                    title="Collect Evidence",
                    description="Gather logs and artifacts for investigation",
                    step_type=StepType.AUTOMATED,
                    commands=["maestro forensics collect --incident-id <id>"],
                    duration_minutes=20,
                ),
            ],
        )
        procedure.sections.append(incident_section)

        # Add compliance section
        compliance_section = RunbookSection(
            title="Compliance Verification",
            description="EU AI Act Article 15 compliance checks",
            steps=[
                RunbookStep(
                    step_number=1,
                    title="Generate Compliance Report",
                    description="Generate the periodic compliance report",
                    step_type=StepType.AUTOMATED,
                    commands=["maestro compliance report --framework 'EU AI Act'"],
                    duration_minutes=10,
                ),
                RunbookStep(
                    step_number=2,
                    title="Review Audit Logs",
                    description="Verify audit log integrity",
                    step_type=StepType.VERIFICATION,
                    commands=["maestro audit verify-chain"],
                    expected_outcome="Chain integrity verified",
                    duration_minutes=5,
                ),
            ],
        )
        procedure.sections.append(compliance_section)

        self._procedures[procedure.procedure_id] = procedure
        return procedure

    def get_procedure(self, procedure_id: str) -> Optional[OperationalProcedure]:
        """Get a procedure by ID."""
        return self._procedures.get(procedure_id)

    def get_playbook(self, playbook_id: str) -> Optional[IncidentPlaybook]:
        """Get a playbook by ID."""
        return self._playbooks.get(playbook_id)

    def list_procedures(
        self,
        category: Optional[RunbookCategory] = None,
    ) -> List[OperationalProcedure]:
        """List all procedures, optionally filtered by category."""
        procedures = list(self._procedures.values())
        if category:
            procedures = [p for p in procedures if p.category == category]
        return procedures

    def list_playbooks(self) -> List[IncidentPlaybook]:
        """List all incident playbooks."""
        return list(self._playbooks.values())

    def export_procedure(
        self,
        procedure_id: str,
        format: str = "markdown",
    ) -> Optional[str]:
        """Export a procedure in the specified format."""
        procedure = self._procedures.get(procedure_id)
        if not procedure:
            return None

        if format == "markdown":
            return procedure.to_markdown()
        elif format == "json":
            return json.dumps(procedure.to_dict(), indent=2, default=str)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def export_playbook(
        self,
        playbook_id: str,
        format: str = "markdown",
    ) -> Optional[str]:
        """Export a playbook in the specified format."""
        playbook = self._playbooks.get(playbook_id)
        if not playbook:
            return None

        if format == "markdown":
            return playbook.to_markdown()
        elif format == "json":
            return json.dumps(playbook.to_dict(), indent=2, default=str)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def validate_procedure(self, procedure_id: str) -> Dict[str, Any]:
        """Validate a procedure for completeness."""
        procedure = self._procedures.get(procedure_id)
        if not procedure:
            return {"valid": False, "errors": ["Procedure not found"]}

        errors = []
        warnings = []

        if not procedure.sections:
            errors.append("Procedure has no sections")

        for section in procedure.sections:
            if not section.steps:
                warnings.append(f"Section '{section.title}' has no steps")

            for step in section.steps:
                if not step.description:
                    warnings.append(f"Step '{step.title}' lacks description")
                if step.step_type == StepType.AUTOMATED and not step.commands:
                    warnings.append(f"Automated step '{step.title}' has no commands")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "total_steps": sum(len(s.steps) for s in procedure.sections),
            "estimated_duration": procedure.get_total_duration(),
        }
