"""
Initiative Tracker Module
==========================

Tracks improvement initiatives and measures effectiveness.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional

from .recommendation_engine import Recommendation, Priority


class InitiativeStatus(Enum):
    """Status of improvement initiative."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    MONITORING = "monitoring"
    COMPLETED = "completed"
    ON_HOLD = "on_hold"
    CANCELLED = "cancelled"


class EffectivenessRating(Enum):
    """Effectiveness rating for completed initiatives."""
    EXCELLENT = "excellent"    # Exceeded expectations
    GOOD = "good"              # Met expectations
    PARTIAL = "partial"        # Partially effective
    INEFFECTIVE = "ineffective"
    NOT_MEASURED = "not_measured"


@dataclass
class Milestone:
    """Initiative milestone."""
    id: str
    name: str
    description: str
    target_date: datetime
    completed_date: Optional[datetime] = None
    status: str = "pending"
    notes: str = ""


@dataclass
class MetricMeasurement:
    """Single measurement of a tracked metric."""
    metric_name: str
    value: float
    measured_at: datetime
    baseline: Optional[float] = None
    target: Optional[float] = None

    @property
    def improvement_percentage(self) -> Optional[float]:
        """Calculate improvement from baseline."""
        if self.baseline and self.baseline != 0:
            return ((self.baseline - self.value) / self.baseline) * 100
        return None


@dataclass
class Initiative:
    """Improvement initiative record."""
    id: str
    title: str
    description: str
    status: InitiativeStatus
    priority: Priority
    source_recommendation_id: Optional[str]
    owner: str
    start_date: Optional[datetime] = None
    target_completion_date: Optional[datetime] = None
    actual_completion_date: Optional[datetime] = None
    budget: float = 0.0
    actual_cost: float = 0.0
    milestones: List[Milestone] = field(default_factory=list)
    metrics: List[MetricMeasurement] = field(default_factory=list)
    effectiveness_rating: EffectivenessRating = EffectivenessRating.NOT_MEASURED
    effectiveness_notes: str = ""
    team_members: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_on_track(self) -> bool:
        """Check if initiative is on track."""
        if self.status in [InitiativeStatus.COMPLETED, InitiativeStatus.CANCELLED, InitiativeStatus.ON_HOLD]:
            return True
        if not self.target_completion_date:
            return True
        if self.status == InitiativeStatus.IN_PROGRESS:
            completed_milestones = sum(1 for m in self.milestones if m.completed_date)
            expected_completion = len(self.milestones) * (
                (datetime.utcnow() - (self.start_date or self.created_at)).days /
                max(1, (self.target_completion_date - (self.start_date or self.created_at)).days)
            )
            return completed_milestones >= expected_completion * 0.8
        return True

    @property
    def budget_variance(self) -> float:
        """Calculate budget variance percentage."""
        if self.budget == 0:
            return 0.0
        return ((self.actual_cost - self.budget) / self.budget) * 100

    @property
    def days_remaining(self) -> Optional[int]:
        """Calculate days remaining until target completion."""
        if not self.target_completion_date:
            return None
        if self.status == InitiativeStatus.COMPLETED:
            return 0
        return (self.target_completion_date - datetime.utcnow()).days

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage based on milestones."""
        if not self.milestones:
            return 0.0 if self.status != InitiativeStatus.COMPLETED else 100.0
        completed = sum(1 for m in self.milestones if m.completed_date)
        return (completed / len(self.milestones)) * 100


class EffectivenessCalculator:
    """Calculates effectiveness scores for initiatives."""

    def calculate_effectiveness(
        self,
        initiative: Initiative
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive effectiveness metrics.

        Returns:
            Dictionary with effectiveness metrics and rating
        """
        if initiative.status != InitiativeStatus.COMPLETED:
            return {
                "rating": EffectivenessRating.NOT_MEASURED,
                "reason": "Initiative not yet completed"
            }

        metrics = {
            "budget_performance": self._assess_budget(initiative),
            "timeline_performance": self._assess_timeline(initiative),
            "metric_improvement": self._assess_metrics(initiative),
            "overall_score": 0.0
        }

        # Calculate overall score
        weights = {"budget": 0.2, "timeline": 0.2, "metrics": 0.6}
        overall = (
            metrics["budget_performance"]["score"] * weights["budget"] +
            metrics["timeline_performance"]["score"] * weights["timeline"] +
            metrics["metric_improvement"]["score"] * weights["metrics"]
        )
        metrics["overall_score"] = overall

        # Determine rating
        if overall >= 90:
            metrics["rating"] = EffectivenessRating.EXCELLENT
        elif overall >= 70:
            metrics["rating"] = EffectivenessRating.GOOD
        elif overall >= 50:
            metrics["rating"] = EffectivenessRating.PARTIAL
        else:
            metrics["rating"] = EffectivenessRating.INEFFECTIVE

        return metrics

    def _assess_budget(self, initiative: Initiative) -> Dict[str, Any]:
        """Assess budget performance."""
        variance = initiative.budget_variance
        if variance <= 0:
            score = 100
        elif variance <= 10:
            score = 90
        elif variance <= 25:
            score = 70
        else:
            score = max(0, 100 - variance * 2)

        return {
            "score": score,
            "variance_percentage": variance,
            "budget": initiative.budget,
            "actual": initiative.actual_cost
        }

    def _assess_timeline(self, initiative: Initiative) -> Dict[str, Any]:
        """Assess timeline performance."""
        if not initiative.target_completion_date or not initiative.actual_completion_date:
            return {"score": 80, "days_variance": 0}

        days_variance = (initiative.actual_completion_date - initiative.target_completion_date).days

        if days_variance <= 0:
            score = 100
        elif days_variance <= 7:
            score = 90
        elif days_variance <= 30:
            score = 70
        else:
            score = max(0, 100 - days_variance)

        return {
            "score": score,
            "days_variance": days_variance,
            "target_date": initiative.target_completion_date.isoformat(),
            "actual_date": initiative.actual_completion_date.isoformat()
        }

    def _assess_metrics(self, initiative: Initiative) -> Dict[str, Any]:
        """Assess metric improvement performance."""
        if not initiative.metrics:
            return {"score": 50, "metrics_assessed": 0}

        improvements = []
        for metric in initiative.metrics:
            if metric.improvement_percentage is not None:
                target_improvement = 50  # Default target
                if metric.target and metric.baseline:
                    target_improvement = ((metric.baseline - metric.target) / metric.baseline) * 100

                achievement = min(100, (metric.improvement_percentage / max(1, target_improvement)) * 100)
                improvements.append(achievement)

        if not improvements:
            return {"score": 50, "metrics_assessed": 0}

        avg_improvement = sum(improvements) / len(improvements)
        return {
            "score": avg_improvement,
            "metrics_assessed": len(improvements),
            "individual_scores": improvements
        }


class InitiativeTracker:
    """
    Tracks improvement initiatives and measures effectiveness.

    Provides complete lifecycle management for improvement initiatives
    from proposal through completion with effectiveness measurement.
    """

    def __init__(self):
        self.initiatives: Dict[str, Initiative] = {}
        self.effectiveness_calculator = EffectivenessCalculator()
        self.logger = logging.getLogger("qms-initiatives")
        self._configure_logger()

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

    def create_initiative(
        self,
        title: str,
        description: str,
        owner: str,
        priority: Priority = Priority.MEDIUM,
        source_recommendation_id: Optional[str] = None,
        budget: float = 0.0,
        target_completion_date: Optional[datetime] = None
    ) -> Initiative:
        """
        Create a new improvement initiative.

        Args:
            title: Initiative title
            description: Detailed description
            owner: Initiative owner
            priority: Priority level
            source_recommendation_id: Optional linked recommendation
            budget: Allocated budget
            target_completion_date: Target completion date

        Returns:
            Created Initiative
        """
        import uuid

        initiative_id = f"INIT-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

        initiative = Initiative(
            id=initiative_id,
            title=title,
            description=description,
            status=InitiativeStatus.PROPOSED,
            priority=priority,
            source_recommendation_id=source_recommendation_id,
            owner=owner,
            budget=budget,
            target_completion_date=target_completion_date
        )

        self.initiatives[initiative_id] = initiative

        self.logger.info(
            f"INITIATIVE_CREATED | id={initiative_id} | title={title} | "
            f"priority={priority.value} | owner={owner}"
        )

        return initiative

    def create_from_recommendation(
        self,
        recommendation: Recommendation,
        owner: str,
        budget: Optional[float] = None,
        target_date: Optional[datetime] = None
    ) -> Initiative:
        """Create initiative from a recommendation."""
        return self.create_initiative(
            title=recommendation.title,
            description=recommendation.description,
            owner=owner,
            priority=recommendation.priority,
            source_recommendation_id=recommendation.id,
            budget=budget or (recommendation.cost_estimate.implementation_cost if recommendation.cost_estimate else 0),
            target_completion_date=target_date or (datetime.utcnow() + timedelta(days=90))
        )

    def get_initiative(self, initiative_id: str) -> Optional[Initiative]:
        """Get initiative by ID."""
        return self.initiatives.get(initiative_id)

    def update_status(
        self,
        initiative_id: str,
        new_status: InitiativeStatus,
        updated_by: str,
        notes: str = ""
    ) -> Initiative:
        """
        Update initiative status.

        Args:
            initiative_id: Initiative ID
            new_status: New status
            updated_by: User making the update
            notes: Optional notes

        Returns:
            Updated Initiative
        """
        initiative = self.get_initiative(initiative_id)
        if not initiative:
            raise ValueError(f"Initiative {initiative_id} not found")

        old_status = initiative.status
        initiative.status = new_status
        initiative.updated_at = datetime.utcnow()

        if new_status == InitiativeStatus.IN_PROGRESS and not initiative.start_date:
            initiative.start_date = datetime.utcnow()

        if new_status == InitiativeStatus.COMPLETED:
            initiative.actual_completion_date = datetime.utcnow()
            # Calculate effectiveness
            effectiveness = self.effectiveness_calculator.calculate_effectiveness(initiative)
            initiative.effectiveness_rating = effectiveness["rating"]
            initiative.effectiveness_notes = notes or str(effectiveness)

        self.logger.info(
            f"INITIATIVE_STATUS_CHANGED | id={initiative_id} | "
            f"from={old_status.value} | to={new_status.value} | by={updated_by}"
        )

        return initiative

    def add_milestone(
        self,
        initiative_id: str,
        name: str,
        description: str,
        target_date: datetime
    ) -> Milestone:
        """Add a milestone to an initiative."""
        import uuid

        initiative = self.get_initiative(initiative_id)
        if not initiative:
            raise ValueError(f"Initiative {initiative_id} not found")

        milestone = Milestone(
            id=f"MS-{str(uuid.uuid4())[:8].upper()}",
            name=name,
            description=description,
            target_date=target_date
        )

        initiative.milestones.append(milestone)
        initiative.updated_at = datetime.utcnow()

        self.logger.info(
            f"MILESTONE_ADDED | initiative_id={initiative_id} | "
            f"milestone_id={milestone.id} | name={name}"
        )

        return milestone

    def complete_milestone(
        self,
        initiative_id: str,
        milestone_id: str,
        notes: str = ""
    ) -> Milestone:
        """Mark a milestone as completed."""
        initiative = self.get_initiative(initiative_id)
        if not initiative:
            raise ValueError(f"Initiative {initiative_id} not found")

        milestone = next((m for m in initiative.milestones if m.id == milestone_id), None)
        if not milestone:
            raise ValueError(f"Milestone {milestone_id} not found")

        milestone.completed_date = datetime.utcnow()
        milestone.status = "completed"
        milestone.notes = notes
        initiative.updated_at = datetime.utcnow()

        self.logger.info(
            f"MILESTONE_COMPLETED | initiative_id={initiative_id} | milestone_id={milestone_id}"
        )

        return milestone

    def record_metric(
        self,
        initiative_id: str,
        metric_name: str,
        value: float,
        baseline: Optional[float] = None,
        target: Optional[float] = None
    ) -> MetricMeasurement:
        """Record a metric measurement."""
        initiative = self.get_initiative(initiative_id)
        if not initiative:
            raise ValueError(f"Initiative {initiative_id} not found")

        measurement = MetricMeasurement(
            metric_name=metric_name,
            value=value,
            measured_at=datetime.utcnow(),
            baseline=baseline,
            target=target
        )

        initiative.metrics.append(measurement)
        initiative.updated_at = datetime.utcnow()

        improvement = measurement.improvement_percentage
        self.logger.info(
            f"METRIC_RECORDED | initiative_id={initiative_id} | "
            f"metric={metric_name} | value={value} | improvement={improvement:.1f}%"
            if improvement else
            f"METRIC_RECORDED | initiative_id={initiative_id} | "
            f"metric={metric_name} | value={value}"
        )

        return measurement

    def update_cost(self, initiative_id: str, cost: float) -> Initiative:
        """Update actual cost."""
        initiative = self.get_initiative(initiative_id)
        if not initiative:
            raise ValueError(f"Initiative {initiative_id} not found")

        initiative.actual_cost = cost
        initiative.updated_at = datetime.utcnow()

        return initiative

    def get_initiatives_by_status(self, status: InitiativeStatus) -> List[Initiative]:
        """Get initiatives by status."""
        return [i for i in self.initiatives.values() if i.status == status]

    def get_at_risk_initiatives(self) -> List[Initiative]:
        """Get initiatives at risk (not on track)."""
        active_statuses = [InitiativeStatus.PLANNING, InitiativeStatus.IN_PROGRESS]
        return [
            i for i in self.initiatives.values()
            if i.status in active_statuses and not i.is_on_track
        ]

    def get_overdue_initiatives(self) -> List[Initiative]:
        """Get overdue initiatives."""
        return [
            i for i in self.initiatives.values()
            if i.days_remaining is not None and i.days_remaining < 0
            and i.status not in [InitiativeStatus.COMPLETED, InitiativeStatus.CANCELLED]
        ]

    def calculate_effectiveness(self, initiative_id: str) -> Dict[str, Any]:
        """Calculate effectiveness for an initiative."""
        initiative = self.get_initiative(initiative_id)
        if not initiative:
            raise ValueError(f"Initiative {initiative_id} not found")

        return self.effectiveness_calculator.calculate_effectiveness(initiative)

    def get_statistics(self) -> Dict[str, Any]:
        """Get initiative portfolio statistics."""
        all_initiatives = list(self.initiatives.values())
        completed = [i for i in all_initiatives if i.status == InitiativeStatus.COMPLETED]

        # Calculate effectiveness distribution
        effectiveness_dist = {}
        for rating in EffectivenessRating:
            effectiveness_dist[rating.value] = len([
                i for i in completed if i.effectiveness_rating == rating
            ])

        return {
            "total_initiatives": len(all_initiatives),
            "by_status": {
                status.value: len([i for i in all_initiatives if i.status == status])
                for status in InitiativeStatus
            },
            "by_priority": {
                priority.value: len([i for i in all_initiatives if i.priority == priority])
                for priority in Priority
            },
            "at_risk": len(self.get_at_risk_initiatives()),
            "overdue": len(self.get_overdue_initiatives()),
            "total_budget": sum(i.budget for i in all_initiatives),
            "total_actual_cost": sum(i.actual_cost for i in all_initiatives),
            "avg_completion_percentage": (
                sum(i.completion_percentage for i in all_initiatives) / len(all_initiatives)
                if all_initiatives else 0
            ),
            "effectiveness_distribution": effectiveness_dist
        }
