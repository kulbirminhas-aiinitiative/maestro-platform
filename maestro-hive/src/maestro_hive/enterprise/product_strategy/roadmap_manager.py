"""
Roadmap Manager - High-level product roadmap management

Provides capabilities for:
- Creating and managing product roadmaps with quarterly phases
- Tracking features and objectives within phases
- Calculating progress and generating reports

Implements AC-2: High-level product roadmap with quarterly phases
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from uuid import uuid4
import logging

logger = logging.getLogger(__name__)


class PhaseStatus(Enum):
    """Status of a roadmap phase."""
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


class FeatureStatus(Enum):
    """Status of a feature within a phase."""
    BACKLOG = "backlog"
    PLANNED = "planned"
    IN_DEVELOPMENT = "in_development"
    IN_REVIEW = "in_review"
    COMPLETED = "completed"
    DEFERRED = "deferred"


class FeaturePriority(Enum):
    """Priority level for features."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Feature:
    """Represents a feature within a roadmap phase."""
    feature_id: str
    name: str
    description: str
    priority: FeaturePriority
    status: FeatureStatus = FeatureStatus.BACKLOG
    epic_key: Optional[str] = None
    estimated_effort: Optional[int] = None  # Story points or days
    actual_effort: Optional[int] = None
    dependencies: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict:
        """Convert feature to dictionary representation."""
        return {
            "feature_id": self.feature_id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "epic_key": self.epic_key,
            "estimated_effort": self.estimated_effort,
            "actual_effort": self.actual_effort,
            "dependencies": self.dependencies,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class RoadmapPhase:
    """Represents a phase in the product roadmap."""
    phase_id: str
    name: str
    quarter: str  # Format: "Q1 2025"
    year: int
    objectives: List[str]
    features: List[Feature] = field(default_factory=list)
    status: PhaseStatus = PhaseStatus.PLANNED
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    completion_percentage: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def calculate_completion(self) -> float:
        """Calculate phase completion based on feature status."""
        if not self.features:
            return 0.0
        completed = sum(1 for f in self.features if f.status == FeatureStatus.COMPLETED)
        self.completion_percentage = (completed / len(self.features)) * 100
        return self.completion_percentage

    def get_features_by_status(self, status: FeatureStatus) -> List[Feature]:
        """Get features filtered by status."""
        return [f for f in self.features if f.status == status]

    def to_dict(self) -> Dict:
        """Convert phase to dictionary representation."""
        return {
            "phase_id": self.phase_id,
            "name": self.name,
            "quarter": self.quarter,
            "year": self.year,
            "objectives": self.objectives,
            "features": [f.to_dict() for f in self.features],
            "status": self.status.value,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "completion_percentage": self.completion_percentage,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


@dataclass
class ProgressReport:
    """Progress report for a roadmap or phase."""
    report_id: str
    roadmap_id: str
    generated_at: datetime
    overall_completion: float
    phases_summary: List[Dict]
    at_risk_features: List[Feature]
    completed_features: List[Feature]
    upcoming_milestones: List[str]
    recommendations: List[str]

    def to_dict(self) -> Dict:
        """Convert report to dictionary representation."""
        return {
            "report_id": self.report_id,
            "roadmap_id": self.roadmap_id,
            "generated_at": self.generated_at.isoformat(),
            "overall_completion": self.overall_completion,
            "phases_summary": self.phases_summary,
            "at_risk_features": [f.to_dict() for f in self.at_risk_features],
            "completed_features": [f.to_dict() for f in self.completed_features],
            "upcoming_milestones": self.upcoming_milestones,
            "recommendations": self.recommendations,
        }


@dataclass
class Roadmap:
    """Represents a complete product roadmap."""
    roadmap_id: str
    name: str
    vision: str
    description: str
    phases: List[RoadmapPhase] = field(default_factory=list)
    fiscal_year_start: int = 1  # Month (1=January)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def get_current_phase(self) -> Optional[RoadmapPhase]:
        """Get the phase currently in progress."""
        for phase in self.phases:
            if phase.status == PhaseStatus.IN_PROGRESS:
                return phase
        return None

    def get_phase_by_quarter(self, quarter: str) -> Optional[RoadmapPhase]:
        """Get phase by quarter identifier."""
        for phase in self.phases:
            if phase.quarter == quarter:
                return phase
        return None

    def calculate_overall_progress(self) -> float:
        """Calculate overall roadmap progress."""
        if not self.phases:
            return 0.0
        total_completion = sum(p.calculate_completion() for p in self.phases)
        return total_completion / len(self.phases)

    def to_dict(self) -> Dict:
        """Convert roadmap to dictionary representation."""
        return {
            "roadmap_id": self.roadmap_id,
            "name": self.name,
            "vision": self.vision,
            "description": self.description,
            "phases": [p.to_dict() for p in self.phases],
            "fiscal_year_start": self.fiscal_year_start,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class RoadmapManager:
    """
    Manages product roadmaps with quarterly phases.

    Provides CRUD operations for roadmaps, phases, and features,
    along with progress tracking and reporting capabilities.
    """

    def __init__(self):
        """Initialize the roadmap manager."""
        self._roadmaps: Dict[str, Roadmap] = {}
        logger.info("RoadmapManager initialized")

    def create_roadmap(
        self,
        name: str,
        vision: str,
        description: str = "",
        fiscal_year_start: int = 1,
    ) -> Roadmap:
        """
        Create a new product roadmap.

        Args:
            name: Name of the roadmap
            vision: High-level vision statement
            description: Detailed description
            fiscal_year_start: Month when fiscal year starts (1-12)

        Returns:
            The created Roadmap instance
        """
        roadmap_id = f"RM-{uuid4().hex[:8].upper()}"
        roadmap = Roadmap(
            roadmap_id=roadmap_id,
            name=name,
            vision=vision,
            description=description,
            fiscal_year_start=fiscal_year_start,
        )
        self._roadmaps[roadmap_id] = roadmap
        logger.info(f"Created roadmap: {roadmap_id} - {name}")
        return roadmap

    def get_roadmap(self, roadmap_id: str) -> Optional[Roadmap]:
        """Get a roadmap by ID."""
        return self._roadmaps.get(roadmap_id)

    def list_roadmaps(self) -> List[Roadmap]:
        """List all roadmaps."""
        return list(self._roadmaps.values())

    def add_phase(
        self,
        roadmap_id: str,
        name: str,
        quarter: str,
        year: int,
        objectives: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Optional[str]:
        """
        Add a phase to a roadmap.

        Args:
            roadmap_id: ID of the roadmap
            name: Name of the phase
            quarter: Quarter identifier (e.g., "Q1")
            year: Year for the phase
            objectives: List of phase objectives
            start_date: Phase start date
            end_date: Phase end date

        Returns:
            Phase ID if successful, None otherwise
        """
        roadmap = self._roadmaps.get(roadmap_id)
        if not roadmap:
            logger.error(f"Roadmap not found: {roadmap_id}")
            return None

        phase_id = f"PH-{uuid4().hex[:8].upper()}"
        phase = RoadmapPhase(
            phase_id=phase_id,
            name=name,
            quarter=f"{quarter} {year}",
            year=year,
            objectives=objectives,
            start_date=start_date,
            end_date=end_date,
        )
        roadmap.phases.append(phase)
        roadmap.updated_at = datetime.utcnow()
        logger.info(f"Added phase {phase_id} to roadmap {roadmap_id}")
        return phase_id

    def add_feature_to_phase(
        self,
        roadmap_id: str,
        phase_id: str,
        name: str,
        description: str,
        priority: FeaturePriority,
        epic_key: Optional[str] = None,
        estimated_effort: Optional[int] = None,
    ) -> Optional[str]:
        """
        Add a feature to a phase.

        Args:
            roadmap_id: ID of the roadmap
            phase_id: ID of the phase
            name: Feature name
            description: Feature description
            priority: Feature priority
            epic_key: JIRA epic key if linked
            estimated_effort: Estimated effort

        Returns:
            Feature ID if successful, None otherwise
        """
        roadmap = self._roadmaps.get(roadmap_id)
        if not roadmap:
            logger.error(f"Roadmap not found: {roadmap_id}")
            return None

        phase = next((p for p in roadmap.phases if p.phase_id == phase_id), None)
        if not phase:
            logger.error(f"Phase not found: {phase_id}")
            return None

        feature_id = f"FT-{uuid4().hex[:8].upper()}"
        feature = Feature(
            feature_id=feature_id,
            name=name,
            description=description,
            priority=priority,
            epic_key=epic_key,
            estimated_effort=estimated_effort,
        )
        phase.features.append(feature)
        phase.updated_at = datetime.utcnow()
        roadmap.updated_at = datetime.utcnow()
        logger.info(f"Added feature {feature_id} to phase {phase_id}")
        return feature_id

    def get_current_phase(self, roadmap_id: str) -> Optional[RoadmapPhase]:
        """Get the current phase of a roadmap."""
        roadmap = self._roadmaps.get(roadmap_id)
        if roadmap:
            return roadmap.get_current_phase()
        return None

    def update_phase_status(
        self,
        roadmap_id: str,
        phase_id: str,
        status: PhaseStatus,
    ) -> bool:
        """
        Update the status of a phase.

        Args:
            roadmap_id: ID of the roadmap
            phase_id: ID of the phase
            status: New status

        Returns:
            True if successful, False otherwise
        """
        roadmap = self._roadmaps.get(roadmap_id)
        if not roadmap:
            return False

        phase = next((p for p in roadmap.phases if p.phase_id == phase_id), None)
        if not phase:
            return False

        phase.status = status
        phase.updated_at = datetime.utcnow()
        roadmap.updated_at = datetime.utcnow()
        logger.info(f"Updated phase {phase_id} status to {status.value}")
        return True

    def update_feature_status(
        self,
        roadmap_id: str,
        phase_id: str,
        feature_id: str,
        status: FeatureStatus,
    ) -> bool:
        """Update the status of a feature."""
        roadmap = self._roadmaps.get(roadmap_id)
        if not roadmap:
            return False

        phase = next((p for p in roadmap.phases if p.phase_id == phase_id), None)
        if not phase:
            return False

        feature = next((f for f in phase.features if f.feature_id == feature_id), None)
        if not feature:
            return False

        feature.status = status
        feature.updated_at = datetime.utcnow()
        phase.calculate_completion()
        phase.updated_at = datetime.utcnow()
        roadmap.updated_at = datetime.utcnow()
        logger.info(f"Updated feature {feature_id} status to {status.value}")
        return True

    def get_roadmap_progress(self, roadmap_id: str) -> Optional[ProgressReport]:
        """
        Generate a progress report for a roadmap.

        Args:
            roadmap_id: ID of the roadmap

        Returns:
            ProgressReport instance or None if roadmap not found
        """
        roadmap = self._roadmaps.get(roadmap_id)
        if not roadmap:
            return None

        # Calculate overall completion
        overall_completion = roadmap.calculate_overall_progress()

        # Build phases summary
        phases_summary = []
        all_features = []
        for phase in roadmap.phases:
            phase.calculate_completion()
            phases_summary.append({
                "phase_id": phase.phase_id,
                "name": phase.name,
                "quarter": phase.quarter,
                "status": phase.status.value,
                "completion": phase.completion_percentage,
                "feature_count": len(phase.features),
            })
            all_features.extend(phase.features)

        # Identify at-risk and completed features
        at_risk = [
            f for f in all_features
            if f.status in [FeatureStatus.BACKLOG, FeatureStatus.PLANNED]
            and f.priority in [FeaturePriority.CRITICAL, FeaturePriority.HIGH]
        ]
        completed = [f for f in all_features if f.status == FeatureStatus.COMPLETED]

        # Generate recommendations
        recommendations = []
        if overall_completion < 50:
            recommendations.append("Overall progress is below 50%. Consider reviewing scope.")
        if len(at_risk) > 3:
            recommendations.append(f"{len(at_risk)} high-priority features at risk. Review priorities.")

        report = ProgressReport(
            report_id=f"RPT-{uuid4().hex[:8].upper()}",
            roadmap_id=roadmap_id,
            generated_at=datetime.utcnow(),
            overall_completion=overall_completion,
            phases_summary=phases_summary,
            at_risk_features=at_risk,
            completed_features=completed,
            upcoming_milestones=[],  # Populated by MilestoneTracker
            recommendations=recommendations,
        )
        logger.info(f"Generated progress report for roadmap {roadmap_id}")
        return report
