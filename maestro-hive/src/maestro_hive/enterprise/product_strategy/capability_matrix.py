"""
Capability Matrix - Capability maturity assessment and progression

Provides capabilities for:
- Defining capabilities with maturity levels
- Assessing current maturity state
- Creating progression plans
- Tracking capability development over time

Implements AC-5: Capability maturity progression defined
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


class MaturityLevel(Enum):
    """Maturity levels for capabilities (5-level model)."""
    LEVEL_1_INITIAL = 1  # Ad-hoc, unpredictable
    LEVEL_2_MANAGED = 2  # Planned and tracked
    LEVEL_3_DEFINED = 3  # Standardized processes
    LEVEL_4_MEASURED = 4  # Quantitatively managed
    LEVEL_5_OPTIMIZING = 5  # Continuous improvement

    @property
    def name_display(self) -> str:
        """Get display name for the level."""
        names = {
            1: "Initial",
            2: "Managed",
            3: "Defined",
            4: "Measured",
            5: "Optimizing",
        }
        return names.get(self.value, "Unknown")

    @property
    def description(self) -> str:
        """Get description for the level."""
        descriptions = {
            1: "Processes are ad-hoc and unpredictable",
            2: "Processes are planned and tracked at project level",
            3: "Processes are standardized across the organization",
            4: "Processes are quantitatively managed with metrics",
            5: "Continuous process improvement based on data",
        }
        return descriptions.get(self.value, "")


class CapabilityCategory(Enum):
    """Categories for capabilities."""
    TECHNICAL = "technical"
    PROCESS = "process"
    PEOPLE = "people"
    TOOLS = "tools"
    GOVERNANCE = "governance"


@dataclass
class MaturityCriteria:
    """Criteria for achieving a maturity level."""
    criteria_id: str
    level: MaturityLevel
    description: str
    evidence_required: List[str]
    is_met: bool = False
    met_date: Optional[datetime] = None
    evidence_provided: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        """Convert criteria to dictionary representation."""
        return {
            "criteria_id": self.criteria_id,
            "level": self.level.value,
            "level_name": self.level.name_display,
            "description": self.description,
            "evidence_required": self.evidence_required,
            "is_met": self.is_met,
            "met_date": self.met_date.isoformat() if self.met_date else None,
            "evidence_provided": self.evidence_provided,
        }


@dataclass
class Capability:
    """Represents a capability with maturity tracking."""
    capability_id: str
    name: str
    description: str
    category: CapabilityCategory
    current_level: MaturityLevel = MaturityLevel.LEVEL_1_INITIAL
    target_level: MaturityLevel = MaturityLevel.LEVEL_3_DEFINED
    criteria: List[MaturityCriteria] = field(default_factory=list)
    owner: Optional[str] = None
    related_objectives: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def get_gap(self) -> int:
        """Get the gap between current and target level."""
        return self.target_level.value - self.current_level.value

    def get_criteria_for_level(self, level: MaturityLevel) -> List[MaturityCriteria]:
        """Get criteria for a specific maturity level."""
        return [c for c in self.criteria if c.level == level]

    def get_unmet_criteria(self) -> List[MaturityCriteria]:
        """Get criteria that haven't been met yet."""
        return [c for c in self.criteria if not c.is_met]

    def get_next_level_criteria(self) -> List[MaturityCriteria]:
        """Get criteria needed for the next maturity level."""
        if self.current_level.value >= 5:
            return []
        next_level = MaturityLevel(self.current_level.value + 1)
        return self.get_criteria_for_level(next_level)

    def to_dict(self) -> Dict:
        """Convert capability to dictionary representation."""
        return {
            "capability_id": self.capability_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "current_level": self.current_level.value,
            "current_level_name": self.current_level.name_display,
            "target_level": self.target_level.value,
            "target_level_name": self.target_level.name_display,
            "gap": self.get_gap(),
            "criteria": [c.to_dict() for c in self.criteria],
            "owner": self.owner,
            "related_objectives": self.related_objectives,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class ProgressionStep:
    """A step in a capability progression plan."""
    step_id: str
    capability_id: str
    from_level: MaturityLevel
    to_level: MaturityLevel
    actions: List[str]
    resources_needed: List[str]
    estimated_duration: str  # e.g., "2 weeks", "1 month"
    dependencies: List[str] = field(default_factory=list)
    is_completed: bool = False
    completed_date: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Convert step to dictionary representation."""
        return {
            "step_id": self.step_id,
            "capability_id": self.capability_id,
            "from_level": self.from_level.value,
            "from_level_name": self.from_level.name_display,
            "to_level": self.to_level.value,
            "to_level_name": self.to_level.name_display,
            "actions": self.actions,
            "resources_needed": self.resources_needed,
            "estimated_duration": self.estimated_duration,
            "dependencies": self.dependencies,
            "is_completed": self.is_completed,
            "completed_date": self.completed_date.isoformat() if self.completed_date else None,
        }


@dataclass
class ProgressionPlan:
    """Plan for progressing capability maturity."""
    plan_id: str
    name: str
    capability_id: str
    target_level: MaturityLevel
    steps: List[ProgressionStep] = field(default_factory=list)
    start_date: Optional[datetime] = None
    target_completion_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def get_completion_percentage(self) -> float:
        """Calculate plan completion percentage."""
        if not self.steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.is_completed)
        return (completed / len(self.steps)) * 100

    def get_current_step(self) -> Optional[ProgressionStep]:
        """Get the current (first incomplete) step."""
        for step in self.steps:
            if not step.is_completed:
                return step
        return None

    def to_dict(self) -> Dict:
        """Convert plan to dictionary representation."""
        return {
            "plan_id": self.plan_id,
            "name": self.name,
            "capability_id": self.capability_id,
            "target_level": self.target_level.value,
            "target_level_name": self.target_level.name_display,
            "steps": [s.to_dict() for s in self.steps],
            "completion_percentage": self.get_completion_percentage(),
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "target_completion_date": self.target_completion_date.isoformat() if self.target_completion_date else None,
            "actual_completion_date": self.actual_completion_date.isoformat() if self.actual_completion_date else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class Assessment:
    """Assessment of capability maturity."""
    assessment_id: str
    capability_id: str
    assessed_level: MaturityLevel
    assessor: str
    assessment_date: datetime
    evidence: List[str]
    findings: List[str]
    recommendations: List[str]
    next_assessment_date: Optional[datetime] = None

    def to_dict(self) -> Dict:
        """Convert assessment to dictionary representation."""
        return {
            "assessment_id": self.assessment_id,
            "capability_id": self.capability_id,
            "assessed_level": self.assessed_level.value,
            "assessed_level_name": self.assessed_level.name_display,
            "assessor": self.assessor,
            "assessment_date": self.assessment_date.isoformat(),
            "evidence": self.evidence,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "next_assessment_date": self.next_assessment_date.isoformat() if self.next_assessment_date else None,
        }


class CapabilityMatrix:
    """
    Manages capability maturity assessment and progression.

    Provides CRUD operations for capabilities, assessments, and progression plans.
    """

    def __init__(self):
        """Initialize the capability matrix."""
        self._capabilities: Dict[str, Capability] = {}
        self._progression_plans: Dict[str, ProgressionPlan] = {}
        self._assessments: Dict[str, Assessment] = {}
        logger.info("CapabilityMatrix initialized")

    def create_capability(
        self,
        name: str,
        description: str,
        category: CapabilityCategory,
        target_level: MaturityLevel = MaturityLevel.LEVEL_3_DEFINED,
        owner: Optional[str] = None,
    ) -> Capability:
        """
        Create a new capability.

        Args:
            name: Capability name
            description: Detailed description
            category: Capability category
            target_level: Target maturity level
            owner: Capability owner

        Returns:
            The created Capability instance
        """
        capability_id = f"CAP-{uuid4().hex[:8].upper()}"
        capability = Capability(
            capability_id=capability_id,
            name=name,
            description=description,
            category=category,
            target_level=target_level,
            owner=owner,
        )
        self._capabilities[capability_id] = capability
        logger.info(f"Created capability: {capability_id} - {name}")
        return capability

    def get_capability(self, capability_id: str) -> Optional[Capability]:
        """Get a capability by ID."""
        return self._capabilities.get(capability_id)

    def list_capabilities(self) -> List[Capability]:
        """List all capabilities."""
        return list(self._capabilities.values())

    def get_capabilities_by_category(
        self, category: CapabilityCategory
    ) -> List[Capability]:
        """Get capabilities filtered by category."""
        return [c for c in self._capabilities.values() if c.category == category]

    def add_maturity_criteria(
        self,
        capability_id: str,
        level: MaturityLevel,
        description: str,
        evidence_required: List[str],
    ) -> Optional[str]:
        """
        Add maturity criteria to a capability.

        Args:
            capability_id: ID of the capability
            level: Maturity level for the criteria
            description: Criteria description
            evidence_required: List of required evidence

        Returns:
            Criteria ID if successful, None otherwise
        """
        capability = self._capabilities.get(capability_id)
        if not capability:
            return None

        criteria_id = f"CRT-{uuid4().hex[:8].upper()}"
        criteria = MaturityCriteria(
            criteria_id=criteria_id,
            level=level,
            description=description,
            evidence_required=evidence_required,
        )
        capability.criteria.append(criteria)
        capability.updated_at = datetime.utcnow()
        logger.info(f"Added criteria {criteria_id} to capability {capability_id}")
        return criteria_id

    def mark_criteria_met(
        self,
        capability_id: str,
        criteria_id: str,
        evidence_provided: List[str],
    ) -> bool:
        """
        Mark criteria as met with evidence.

        Args:
            capability_id: ID of the capability
            criteria_id: ID of the criteria
            evidence_provided: List of evidence provided

        Returns:
            True if successful, False otherwise
        """
        capability = self._capabilities.get(capability_id)
        if not capability:
            return False

        criteria = next(
            (c for c in capability.criteria if c.criteria_id == criteria_id), None
        )
        if not criteria:
            return False

        criteria.is_met = True
        criteria.met_date = datetime.utcnow()
        criteria.evidence_provided = evidence_provided
        capability.updated_at = datetime.utcnow()

        # Check if we can advance the maturity level
        self._update_maturity_level(capability)

        logger.info(f"Marked criteria {criteria_id} as met")
        return True

    def _update_maturity_level(self, capability: Capability) -> None:
        """Update capability maturity level based on met criteria."""
        for level in MaturityLevel:
            if level.value > capability.current_level.value:
                criteria_for_level = capability.get_criteria_for_level(level)
                if criteria_for_level and all(c.is_met for c in criteria_for_level):
                    capability.current_level = level
                    logger.info(
                        f"Capability {capability.capability_id} advanced to level {level.value}"
                    )
                else:
                    break

    def conduct_assessment(
        self,
        capability_id: str,
        assessed_level: MaturityLevel,
        assessor: str,
        evidence: List[str],
        findings: List[str],
        recommendations: List[str],
        next_assessment_date: Optional[datetime] = None,
    ) -> Optional[Assessment]:
        """
        Conduct a maturity assessment.

        Args:
            capability_id: ID of the capability
            assessed_level: Assessed maturity level
            assessor: Person conducting assessment
            evidence: List of evidence reviewed
            findings: List of findings
            recommendations: List of recommendations
            next_assessment_date: Date for next assessment

        Returns:
            The created Assessment or None
        """
        capability = self._capabilities.get(capability_id)
        if not capability:
            return None

        assessment_id = f"ASM-{uuid4().hex[:8].upper()}"
        assessment = Assessment(
            assessment_id=assessment_id,
            capability_id=capability_id,
            assessed_level=assessed_level,
            assessor=assessor,
            assessment_date=datetime.utcnow(),
            evidence=evidence,
            findings=findings,
            recommendations=recommendations,
            next_assessment_date=next_assessment_date,
        )
        self._assessments[assessment_id] = assessment

        # Update capability level if assessment differs
        if assessed_level != capability.current_level:
            capability.current_level = assessed_level
            capability.updated_at = datetime.utcnow()

        logger.info(f"Conducted assessment {assessment_id} for capability {capability_id}")
        return assessment

    def get_assessments_for_capability(
        self, capability_id: str
    ) -> List[Assessment]:
        """Get all assessments for a capability."""
        return [
            a for a in self._assessments.values() if a.capability_id == capability_id
        ]

    def create_progression_plan(
        self,
        capability_id: str,
        name: str,
        target_level: MaturityLevel,
        start_date: Optional[datetime] = None,
        target_completion_date: Optional[datetime] = None,
    ) -> Optional[ProgressionPlan]:
        """
        Create a progression plan for a capability.

        Args:
            capability_id: ID of the capability
            name: Plan name
            target_level: Target maturity level
            start_date: Plan start date
            target_completion_date: Target completion date

        Returns:
            The created ProgressionPlan or None
        """
        capability = self._capabilities.get(capability_id)
        if not capability:
            return None

        plan_id = f"PLN-{uuid4().hex[:8].upper()}"
        plan = ProgressionPlan(
            plan_id=plan_id,
            name=name,
            capability_id=capability_id,
            target_level=target_level,
            start_date=start_date,
            target_completion_date=target_completion_date,
        )
        self._progression_plans[plan_id] = plan
        logger.info(f"Created progression plan {plan_id} for capability {capability_id}")
        return plan

    def add_progression_step(
        self,
        plan_id: str,
        from_level: MaturityLevel,
        to_level: MaturityLevel,
        actions: List[str],
        resources_needed: List[str],
        estimated_duration: str,
        dependencies: Optional[List[str]] = None,
    ) -> Optional[str]:
        """
        Add a step to a progression plan.

        Args:
            plan_id: ID of the plan
            from_level: Starting maturity level
            to_level: Target maturity level
            actions: List of actions required
            resources_needed: List of resources needed
            estimated_duration: Estimated duration
            dependencies: List of dependent step IDs

        Returns:
            Step ID if successful, None otherwise
        """
        plan = self._progression_plans.get(plan_id)
        if not plan:
            return None

        step_id = f"STP-{uuid4().hex[:8].upper()}"
        step = ProgressionStep(
            step_id=step_id,
            capability_id=plan.capability_id,
            from_level=from_level,
            to_level=to_level,
            actions=actions,
            resources_needed=resources_needed,
            estimated_duration=estimated_duration,
            dependencies=dependencies or [],
        )
        plan.steps.append(step)
        plan.updated_at = datetime.utcnow()
        logger.info(f"Added step {step_id} to plan {plan_id}")
        return step_id

    def complete_progression_step(self, plan_id: str, step_id: str) -> bool:
        """
        Mark a progression step as completed.

        Args:
            plan_id: ID of the plan
            step_id: ID of the step

        Returns:
            True if successful, False otherwise
        """
        plan = self._progression_plans.get(plan_id)
        if not plan:
            return False

        step = next((s for s in plan.steps if s.step_id == step_id), None)
        if not step:
            return False

        step.is_completed = True
        step.completed_date = datetime.utcnow()
        plan.updated_at = datetime.utcnow()

        # Check if plan is complete
        if plan.get_completion_percentage() == 100:
            plan.actual_completion_date = datetime.utcnow()

        logger.info(f"Completed step {step_id} in plan {plan_id}")
        return True

    def get_capability_matrix_summary(self) -> Dict:
        """
        Get summary of the capability matrix.

        Returns:
            Summary dictionary
        """
        if not self._capabilities:
            return {"total": 0, "by_level": {}, "by_category": {}}

        by_level = {}
        for level in MaturityLevel:
            count = len(
                [c for c in self._capabilities.values() if c.current_level == level]
            )
            if count > 0:
                by_level[level.name_display] = count

        by_category = {}
        for category in CapabilityCategory:
            count = len(
                [c for c in self._capabilities.values() if c.category == category]
            )
            if count > 0:
                by_category[category.value] = count

        # Calculate average maturity
        total_level = sum(c.current_level.value for c in self._capabilities.values())
        avg_maturity = total_level / len(self._capabilities)

        # Count capabilities below target
        below_target = len(
            [c for c in self._capabilities.values() if c.get_gap() > 0]
        )

        return {
            "total": len(self._capabilities),
            "by_level": by_level,
            "by_category": by_category,
            "average_maturity": round(avg_maturity, 2),
            "below_target_count": below_target,
            "active_plans": len(
                [p for p in self._progression_plans.values() if p.get_completion_percentage() < 100]
            ),
        }

    def get_progression_plan(self, plan_id: str) -> Optional[ProgressionPlan]:
        """Get a progression plan by ID."""
        return self._progression_plans.get(plan_id)

    def list_progression_plans(self) -> List[ProgressionPlan]:
        """List all progression plans."""
        return list(self._progression_plans.values())

    def get_plans_for_capability(self, capability_id: str) -> List[ProgressionPlan]:
        """Get all progression plans for a capability."""
        return [
            p for p in self._progression_plans.values()
            if p.capability_id == capability_id
        ]
