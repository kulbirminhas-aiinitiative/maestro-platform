"""
Roadmap Engine - Generates certification roadmaps.

This module provides the RoadmapEngine class which generates step-by-step
certification paths based on current compliance state and target standards.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from .standards_registry import (
    CertificationStandard,
    ControlRequirement,
    Priority,
    StandardsRegistry,
)

logger = logging.getLogger(__name__)


class MilestoneStatus(Enum):
    """Status of a roadmap milestone."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    DEFERRED = "deferred"


class GapSeverity(Enum):
    """Severity of a compliance gap."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ComplianceState:
    """Represents the current compliance state."""

    implemented_controls: Dict[str, List[str]]  # standard_id -> control_ids
    evidence_inventory: Dict[str, List[str]]  # control_id -> evidence_ids
    last_assessment_date: Optional[datetime] = None
    overall_score: float = 0.0

    def get_implemented_count(self, standard_id: str) -> int:
        """Get count of implemented controls for a standard."""
        return len(self.implemented_controls.get(standard_id, []))

    def is_control_implemented(self, standard_id: str, control_id: str) -> bool:
        """Check if a specific control is implemented."""
        return control_id in self.implemented_controls.get(standard_id, [])


@dataclass
class ComplianceGap:
    """Represents a gap between current state and target standard."""

    control: ControlRequirement
    standard_id: str
    severity: GapSeverity
    finding: str
    remediation_guidance: str
    estimated_effort_hours: int
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert gap to dictionary."""
        return {
            "control_id": self.control.control_id,
            "control_name": self.control.name,
            "standard_id": self.standard_id,
            "severity": self.severity.value,
            "finding": self.finding,
            "remediation_guidance": self.remediation_guidance,
            "estimated_effort_hours": self.estimated_effort_hours,
            "dependencies": self.dependencies,
        }


@dataclass
class GapAnalysisReport:
    """Report from gap analysis."""

    standard_id: str
    analysis_date: datetime
    total_controls: int
    implemented_controls: int
    gaps: List[ComplianceGap]
    overall_compliance_percentage: float
    critical_gaps_count: int
    high_gaps_count: int

    @property
    def gap_count(self) -> int:
        """Total number of gaps."""
        return len(self.gaps)

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "standard_id": self.standard_id,
            "analysis_date": self.analysis_date.isoformat(),
            "total_controls": self.total_controls,
            "implemented_controls": self.implemented_controls,
            "gap_count": self.gap_count,
            "overall_compliance_percentage": self.overall_compliance_percentage,
            "critical_gaps_count": self.critical_gaps_count,
            "high_gaps_count": self.high_gaps_count,
            "gaps": [g.to_dict() for g in self.gaps],
        }


@dataclass
class ResourcePlan:
    """Resource requirements for roadmap completion."""

    total_effort_hours: int
    recommended_team_size: int
    skill_requirements: List[str]
    tool_requirements: List[str]
    budget_estimate_usd: int

    def to_dict(self) -> Dict[str, Any]:
        """Convert resource plan to dictionary."""
        return {
            "total_effort_hours": self.total_effort_hours,
            "recommended_team_size": self.recommended_team_size,
            "skill_requirements": self.skill_requirements,
            "tool_requirements": self.tool_requirements,
            "budget_estimate_usd": self.budget_estimate_usd,
        }


@dataclass
class EffortEstimate:
    """Effort estimate for roadmap completion."""

    total_hours: int
    by_category: Dict[str, int]
    by_priority: Dict[str, int]
    confidence_level: float  # 0-1

    def to_dict(self) -> Dict[str, Any]:
        """Convert estimate to dictionary."""
        return {
            "total_hours": self.total_hours,
            "by_category": self.by_category,
            "by_priority": self.by_priority,
            "confidence_level": self.confidence_level,
        }


@dataclass
class Milestone:
    """A milestone in the certification roadmap."""

    id: str
    name: str
    description: str
    controls: List[ControlRequirement]
    target_date: datetime
    status: MilestoneStatus = MilestoneStatus.NOT_STARTED
    dependencies: List[str] = field(default_factory=list)
    deliverables: List[str] = field(default_factory=list)
    assigned_team: Optional[str] = None
    completion_date: Optional[datetime] = None

    @property
    def control_count(self) -> int:
        """Number of controls in this milestone."""
        return len(self.controls)

    def to_dict(self) -> Dict[str, Any]:
        """Convert milestone to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "control_count": self.control_count,
            "control_ids": [c.control_id for c in self.controls],
            "target_date": self.target_date.isoformat(),
            "status": self.status.value,
            "dependencies": self.dependencies,
            "deliverables": self.deliverables,
            "assigned_team": self.assigned_team,
            "completion_date": self.completion_date.isoformat() if self.completion_date else None,
        }


@dataclass
class ComplianceRoadmap:
    """Generated roadmap for achieving certification."""

    id: str
    target_standard: CertificationStandard
    current_state: ComplianceState
    milestones: List[Milestone]
    estimated_completion: datetime
    resource_requirements: ResourcePlan
    gap_analysis: GapAnalysisReport
    created_date: datetime = field(default_factory=datetime.utcnow)

    @property
    def total_milestones(self) -> int:
        """Total number of milestones."""
        return len(self.milestones)

    @property
    def completed_milestones(self) -> int:
        """Number of completed milestones."""
        return sum(1 for m in self.milestones if m.status == MilestoneStatus.COMPLETED)

    @property
    def progress_percentage(self) -> float:
        """Calculate progress percentage."""
        if self.total_milestones == 0:
            return 0.0
        return (self.completed_milestones / self.total_milestones) * 100

    def get_next_milestone(self) -> Optional[Milestone]:
        """Get the next incomplete milestone."""
        for milestone in self.milestones:
            if milestone.status in (MilestoneStatus.NOT_STARTED, MilestoneStatus.IN_PROGRESS):
                return milestone
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert roadmap to dictionary."""
        return {
            "id": self.id,
            "target_standard_id": self.target_standard.id,
            "target_standard_name": self.target_standard.name,
            "total_milestones": self.total_milestones,
            "completed_milestones": self.completed_milestones,
            "progress_percentage": self.progress_percentage,
            "estimated_completion": self.estimated_completion.isoformat(),
            "created_date": self.created_date.isoformat(),
            "milestones": [m.to_dict() for m in self.milestones],
            "resource_requirements": self.resource_requirements.to_dict(),
            "gap_analysis": self.gap_analysis.to_dict(),
        }


class RoadmapEngine:
    """
    Generates certification roadmaps.

    Analyzes current compliance state and generates step-by-step
    roadmaps for achieving target certifications.
    """

    # Default effort estimates (hours) by priority
    EFFORT_BY_PRIORITY = {
        Priority.CRITICAL: 40,
        Priority.HIGH: 24,
        Priority.MEDIUM: 16,
        Priority.LOW: 8,
    }

    # Priority weights for milestone ordering
    PRIORITY_WEIGHTS = {
        Priority.CRITICAL: 4,
        Priority.HIGH: 3,
        Priority.MEDIUM: 2,
        Priority.LOW: 1,
    }

    def __init__(self, registry: StandardsRegistry):
        """
        Initialize the roadmap engine.

        Args:
            registry: The standards registry instance
        """
        self._registry = registry
        self._milestone_counter = 0
        logger.info("RoadmapEngine initialized")

    def generate_roadmap(
        self,
        target_standard: str,
        current_state: ComplianceState,
        timeline_months: int = 12,
        priority_order: Optional[List[str]] = None,
    ) -> ComplianceRoadmap:
        """
        Generate a roadmap to achieve certification.

        Args:
            target_standard: ID of the target certification standard
            current_state: Current compliance state
            timeline_months: Target timeline in months
            priority_order: Optional custom priority ordering

        Returns:
            Generated compliance roadmap
        """
        logger.info("Generating roadmap for standard '%s'", target_standard)

        standard = self._registry.get_standard(target_standard)
        gap_analysis = self.analyze_gaps(target_standard, current_state)

        # Generate milestones from gaps
        milestones = self._generate_milestones(
            standard=standard,
            gaps=gap_analysis.gaps,
            timeline_months=timeline_months,
            priority_order=priority_order,
        )

        # Calculate resource requirements
        resources = self._calculate_resources(gap_analysis.gaps)

        # Calculate estimated completion
        start_date = datetime.utcnow()
        estimated_completion = start_date + timedelta(days=timeline_months * 30)

        roadmap = ComplianceRoadmap(
            id=f"roadmap_{target_standard}_{int(start_date.timestamp())}",
            target_standard=standard,
            current_state=current_state,
            milestones=milestones,
            estimated_completion=estimated_completion,
            resource_requirements=resources,
            gap_analysis=gap_analysis,
        )

        logger.info(
            "Generated roadmap with %d milestones, estimated completion: %s",
            len(milestones),
            estimated_completion.isoformat(),
        )

        return roadmap

    def analyze_gaps(
        self,
        standard_id: str,
        current_state: ComplianceState,
    ) -> GapAnalysisReport:
        """
        Analyze gaps between current state and target standard.

        Args:
            standard_id: Target standard ID
            current_state: Current compliance state

        Returns:
            Gap analysis report
        """
        logger.info("Analyzing gaps for standard '%s'", standard_id)

        standard = self._registry.get_standard(standard_id)
        gaps = []

        for control in standard.controls:
            if not current_state.is_control_implemented(standard_id, control.control_id):
                gap = self._create_gap(control, standard_id)
                gaps.append(gap)

        implemented_count = current_state.get_implemented_count(standard_id)
        total_controls = standard.total_controls
        compliance_percentage = (
            (implemented_count / total_controls * 100) if total_controls > 0 else 0
        )

        critical_gaps = sum(1 for g in gaps if g.severity == GapSeverity.CRITICAL)
        high_gaps = sum(1 for g in gaps if g.severity == GapSeverity.HIGH)

        report = GapAnalysisReport(
            standard_id=standard_id,
            analysis_date=datetime.utcnow(),
            total_controls=total_controls,
            implemented_controls=implemented_count,
            gaps=gaps,
            overall_compliance_percentage=compliance_percentage,
            critical_gaps_count=critical_gaps,
            high_gaps_count=high_gaps,
        )

        logger.info(
            "Gap analysis complete: %d gaps found, %.1f%% compliant",
            len(gaps),
            compliance_percentage,
        )

        return report

    def estimate_effort(self, roadmap: ComplianceRoadmap) -> EffortEstimate:
        """
        Estimate effort required for roadmap completion.

        Args:
            roadmap: The compliance roadmap

        Returns:
            Effort estimate
        """
        by_category: Dict[str, int] = {}
        by_priority: Dict[str, int] = {}

        total_hours = 0

        for gap in roadmap.gap_analysis.gaps:
            hours = gap.estimated_effort_hours

            # Aggregate by category
            category = gap.control.category.value
            by_category[category] = by_category.get(category, 0) + hours

            # Aggregate by priority
            priority = gap.severity.value
            by_priority[priority] = by_priority.get(priority, 0) + hours

            total_hours += hours

        # Calculate confidence based on gap count
        gap_count = len(roadmap.gap_analysis.gaps)
        confidence = max(0.5, 1.0 - (gap_count * 0.01))

        return EffortEstimate(
            total_hours=total_hours,
            by_category=by_category,
            by_priority=by_priority,
            confidence_level=confidence,
        )

    def _create_gap(
        self,
        control: ControlRequirement,
        standard_id: str,
    ) -> ComplianceGap:
        """Create a compliance gap from a missing control."""
        severity = self._map_priority_to_severity(control.priority)
        effort = self.EFFORT_BY_PRIORITY.get(control.priority, 16)

        return ComplianceGap(
            control=control,
            standard_id=standard_id,
            severity=severity,
            finding=f"Control {control.control_id} ({control.name}) is not implemented",
            remediation_guidance=control.implementation_guidance,
            estimated_effort_hours=effort,
            dependencies=control.related_controls,
        )

    def _map_priority_to_severity(self, priority: Priority) -> GapSeverity:
        """Map control priority to gap severity."""
        mapping = {
            Priority.CRITICAL: GapSeverity.CRITICAL,
            Priority.HIGH: GapSeverity.HIGH,
            Priority.MEDIUM: GapSeverity.MEDIUM,
            Priority.LOW: GapSeverity.LOW,
        }
        return mapping.get(priority, GapSeverity.MEDIUM)

    def _generate_milestones(
        self,
        standard: CertificationStandard,
        gaps: List[ComplianceGap],
        timeline_months: int,
        priority_order: Optional[List[str]] = None,
    ) -> List[Milestone]:
        """Generate milestones from gaps."""
        if not gaps:
            return []

        # Group gaps by category
        gaps_by_category: Dict[str, List[ComplianceGap]] = {}
        for gap in gaps:
            category = gap.control.category.value
            if category not in gaps_by_category:
                gaps_by_category[category] = []
            gaps_by_category[category].append(gap)

        # Sort categories by highest priority gap
        def category_priority(category: str) -> int:
            category_gaps = gaps_by_category[category]
            max_weight = max(
                self.PRIORITY_WEIGHTS.get(g.control.priority, 0)
                for g in category_gaps
            )
            return max_weight

        sorted_categories = sorted(
            gaps_by_category.keys(),
            key=category_priority,
            reverse=True,
        )

        # Generate milestones
        milestones = []
        start_date = datetime.utcnow()
        days_per_milestone = (timeline_months * 30) // max(len(sorted_categories), 1)

        for idx, category in enumerate(sorted_categories):
            category_gaps = gaps_by_category[category]
            controls = [g.control for g in category_gaps]

            self._milestone_counter += 1
            milestone_id = f"MS-{self._milestone_counter:03d}"

            target_date = start_date + timedelta(days=days_per_milestone * (idx + 1))

            milestone = Milestone(
                id=milestone_id,
                name=f"Implement {category.replace('_', ' ').title()} Controls",
                description=f"Implement {len(controls)} controls in the {category} category",
                controls=controls,
                target_date=target_date,
                deliverables=[
                    f"Control {c.control_id} implemented and documented"
                    for c in controls[:3]  # Sample deliverables
                ] + (["Additional controls implemented"] if len(controls) > 3 else []),
            )
            milestones.append(milestone)

        # Add dependencies based on control relationships
        self._add_milestone_dependencies(milestones)

        return milestones

    def _add_milestone_dependencies(self, milestones: List[Milestone]) -> None:
        """Add dependencies between milestones based on control relationships."""
        # Create mapping of control_id to milestone_id
        control_to_milestone: Dict[str, str] = {}
        for milestone in milestones:
            for control in milestone.controls:
                control_to_milestone[control.control_id] = milestone.id

        # Add dependencies
        for milestone in milestones:
            for control in milestone.controls:
                for dep_control_id in control.related_controls:
                    if dep_control_id in control_to_milestone:
                        dep_milestone_id = control_to_milestone[dep_control_id]
                        if dep_milestone_id != milestone.id:
                            if dep_milestone_id not in milestone.dependencies:
                                milestone.dependencies.append(dep_milestone_id)

    def _calculate_resources(self, gaps: List[ComplianceGap]) -> ResourcePlan:
        """Calculate resource requirements from gaps."""
        total_hours = sum(g.estimated_effort_hours for g in gaps)

        # Assume 160 hours per month per person
        # Target completion in reasonable time
        recommended_team_size = max(1, total_hours // 480)  # 3 months worth of effort

        # Determine skill requirements based on gap categories
        categories = set(g.control.category.value for g in gaps)
        skill_requirements = []

        if "access_control" in categories or "cryptography" in categories:
            skill_requirements.append("Security Engineer")
        if "compliance" in categories or "privacy" in categories:
            skill_requirements.append("Compliance Analyst")
        if "operations_security" in categories or "incident_management" in categories:
            skill_requirements.append("Operations Engineer")
        if "organization" in categories or "human_resources" in categories:
            skill_requirements.append("Policy Specialist")

        if not skill_requirements:
            skill_requirements.append("Security/Compliance Generalist")

        # Tool requirements
        tool_requirements = [
            "GRC Platform",
            "Evidence Management System",
            "Policy Documentation Tool",
        ]

        # Budget estimate (rough): $150/hour fully loaded cost
        budget_estimate = total_hours * 150

        return ResourcePlan(
            total_effort_hours=total_hours,
            recommended_team_size=recommended_team_size,
            skill_requirements=skill_requirements,
            tool_requirements=tool_requirements,
            budget_estimate_usd=budget_estimate,
        )

    def status(self) -> Dict[str, Any]:
        """Get engine status."""
        return {
            "status": "operational",
            "registry_connected": True,
            "milestones_generated": self._milestone_counter,
        }
