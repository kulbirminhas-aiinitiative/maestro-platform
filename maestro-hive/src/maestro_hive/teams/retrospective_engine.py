"""
RetrospectiveEngine: Autonomous Team Retrospective System

This module implements automated retrospective capabilities that analyze team
performance and generate actionable insights without manual intervention.

EPIC: MD-3015 - Autonomous Team Retrospective & Evaluation

Architecture:
- Collection Layer: Gathers team metrics from various sources
- Analysis Layer: EvaluatorPersona assesses performance
- Recommendation Layer: ProcessImprover suggests improvements

Integrates with:
- PersonaRegistry (MD-2962) for evaluator persona management
- Team metrics infrastructure for data collection
- Action item tracking for follow-up
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Protocol
from enum import Enum
import logging
import uuid


logger = logging.getLogger(__name__)


class RetrospectiveStatus(Enum):
    """Status states for retrospectives"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class ActionItemStatus(Enum):
    """Status states for action items"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DEFERRED = "deferred"
    CANCELLED = "cancelled"


class MetricCategory(Enum):
    """Categories of team metrics"""
    VELOCITY = "velocity"
    QUALITY = "quality"
    COLLABORATION = "collaboration"
    DELIVERY = "delivery"
    TECHNICAL_DEBT = "technical_debt"


@dataclass
class Timeframe:
    """Time period for metrics collection"""
    start_date: datetime
    end_date: datetime

    @classmethod
    def last_sprint(cls, sprint_days: int = 14) -> "Timeframe":
        """Create timeframe for the last sprint"""
        end = datetime.utcnow()
        start = end - timedelta(days=sprint_days)
        return cls(start_date=start, end_date=end)

    @classmethod
    def last_n_days(cls, days: int) -> "Timeframe":
        """Create timeframe for the last N days"""
        end = datetime.utcnow()
        start = end - timedelta(days=days)
        return cls(start_date=start, end_date=end)


@dataclass
class MetricValue:
    """A single metric measurement"""
    name: str
    value: float
    category: MetricCategory
    timestamp: datetime = field(default_factory=datetime.utcnow)
    unit: str = ""
    trend: Optional[float] = None  # Percentage change from previous period


@dataclass
class TeamMetrics:
    """Collection of team performance metrics"""
    team_id: str
    timeframe: Timeframe
    metrics: List[MetricValue] = field(default_factory=list)

    def get_by_category(self, category: MetricCategory) -> List[MetricValue]:
        """Get all metrics in a specific category"""
        return [m for m in self.metrics if m.category == category]

    def get_by_name(self, name: str) -> Optional[MetricValue]:
        """Get a specific metric by name"""
        for m in self.metrics:
            if m.name == name:
                return m
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation"""
        return {
            "team_id": self.team_id,
            "timeframe": {
                "start": self.timeframe.start_date.isoformat(),
                "end": self.timeframe.end_date.isoformat(),
            },
            "metrics": [
                {
                    "name": m.name,
                    "value": m.value,
                    "category": m.category.value,
                    "unit": m.unit,
                    "trend": m.trend,
                }
                for m in self.metrics
            ],
        }


@dataclass
class PerformanceAssessment:
    """Assessment of team performance from evaluator"""
    team_id: str
    overall_score: float  # 0.0 to 1.0
    category_scores: Dict[str, float] = field(default_factory=dict)
    strengths: List[str] = field(default_factory=list)
    areas_for_improvement: List[str] = field(default_factory=list)
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "overall_score": self.overall_score,
            "category_scores": self.category_scores,
            "strengths": self.strengths,
            "areas_for_improvement": self.areas_for_improvement,
            "summary": self.summary,
        }


@dataclass
class Improvement:
    """A suggested improvement"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    category: str = ""
    impact_score: float = 0.0  # Expected impact (0.0 to 1.0)
    effort_score: float = 0.0  # Required effort (0.0 to 1.0)
    priority: int = 0  # Lower is higher priority
    confidence: float = 0.0  # Confidence in the suggestion

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "impact_score": self.impact_score,
            "effort_score": self.effort_score,
            "priority": self.priority,
            "confidence": self.confidence,
        }


@dataclass
class ActionItem:
    """An actionable item from the retrospective"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    assignee: Optional[str] = None
    due_date: Optional[datetime] = None
    status: ActionItemStatus = ActionItemStatus.OPEN
    improvement_id: Optional[str] = None  # Link to source improvement
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "assignee": self.assignee,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status.value,
            "improvement_id": self.improvement_id,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class RetrospectiveReport:
    """Final retrospective report"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    team_id: str = ""
    sprint_id: str = ""
    generated_at: datetime = field(default_factory=datetime.utcnow)
    metrics_summary: Dict[str, Any] = field(default_factory=dict)
    assessment_summary: str = ""
    top_improvements: List[Dict[str, Any]] = field(default_factory=list)
    action_items: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "team_id": self.team_id,
            "sprint_id": self.sprint_id,
            "generated_at": self.generated_at.isoformat(),
            "metrics_summary": self.metrics_summary,
            "assessment_summary": self.assessment_summary,
            "top_improvements": self.top_improvements,
            "action_items": self.action_items,
        }


@dataclass
class RetrospectiveResult:
    """Complete result from a retrospective run"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    team_id: str = ""
    sprint_id: str = ""
    status: RetrospectiveStatus = RetrospectiveStatus.PENDING
    metrics: Optional[TeamMetrics] = None
    assessment: Optional[PerformanceAssessment] = None
    improvements: List[Improvement] = field(default_factory=list)
    action_items: List[ActionItem] = field(default_factory=list)
    report: Optional[RetrospectiveReport] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "team_id": self.team_id,
            "sprint_id": self.sprint_id,
            "status": self.status.value,
            "metrics": self.metrics.to_dict() if self.metrics else None,
            "assessment": self.assessment.to_dict() if self.assessment else None,
            "improvements": [i.to_dict() for i in self.improvements],
            "action_items": [a.to_dict() for a in self.action_items],
            "report": self.report.to_dict() if self.report else None,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error,
        }


@dataclass
class RetrospectiveConfig:
    """Configuration for the retrospective engine"""
    auto_schedule: bool = True
    schedule_cron: str = "0 9 * * 1"  # Monday 9am
    retention_days: int = 365
    max_action_items: int = 10
    max_improvements: int = 5
    min_confidence_threshold: float = 0.7


class EvaluatorInterface(Protocol):
    """Protocol for evaluator implementations"""

    def evaluate_performance(self, metrics: TeamMetrics) -> PerformanceAssessment:
        """Evaluate team performance based on metrics"""
        ...

    def score_team(self, metrics: TeamMetrics) -> float:
        """Calculate overall team score"""
        ...


class ImproverInterface(Protocol):
    """Protocol for process improver implementations"""

    def suggest_improvements(self, metrics: TeamMetrics, assessment: PerformanceAssessment) -> List[Improvement]:
        """Generate improvement suggestions"""
        ...

    def prioritize_actions(self, improvements: List[Improvement]) -> List[Improvement]:
        """Prioritize improvements by impact/effort"""
        ...


class MetricsCollector(Protocol):
    """Protocol for metrics collection"""

    def collect(self, team_id: str, timeframe: Timeframe) -> TeamMetrics:
        """Collect metrics for a team"""
        ...


@dataclass
class DefaultMetricsCollector:
    """Default implementation of metrics collector"""

    def collect(self, team_id: str, timeframe: Timeframe) -> TeamMetrics:
        """Collect default metrics (placeholder implementation)"""
        logger.info(f"Collecting metrics for team {team_id}")

        # Generate sample metrics - in production, these would come from real sources
        metrics = TeamMetrics(
            team_id=team_id,
            timeframe=timeframe,
            metrics=[
                MetricValue(
                    name="velocity",
                    value=42.0,
                    category=MetricCategory.VELOCITY,
                    unit="story_points",
                    trend=5.0,
                ),
                MetricValue(
                    name="bug_rate",
                    value=0.12,
                    category=MetricCategory.QUALITY,
                    unit="bugs_per_story",
                    trend=-2.0,
                ),
                MetricValue(
                    name="code_review_turnaround",
                    value=4.5,
                    category=MetricCategory.COLLABORATION,
                    unit="hours",
                    trend=-10.0,
                ),
                MetricValue(
                    name="sprint_completion_rate",
                    value=0.85,
                    category=MetricCategory.DELIVERY,
                    unit="percentage",
                    trend=3.0,
                ),
            ],
        )

        return metrics


class RetrospectiveEngine:
    """
    Autonomous Retrospective Engine

    Orchestrates the retrospective process:
    1. Collects team metrics
    2. Evaluates performance via EvaluatorPersona
    3. Generates improvements via ProcessImprover
    4. Creates actionable items and reports

    Example:
        >>> engine = RetrospectiveEngine()
        >>> result = await engine.run_retrospective("team-1", "sprint-42")
        >>> print(f"Score: {result.assessment.overall_score}")
    """

    def __init__(
        self,
        evaluator: Optional[EvaluatorInterface] = None,
        improver: Optional[ImproverInterface] = None,
        metrics_collector: Optional[MetricsCollector] = None,
        config: Optional[RetrospectiveConfig] = None
    ):
        """
        Initialize the RetrospectiveEngine.

        Args:
            evaluator: EvaluatorPersona instance for performance assessment
            improver: ProcessImprover instance for improvement suggestions
            metrics_collector: MetricsCollector for gathering team data
            config: Configuration options
        """
        self.evaluator = evaluator
        self.improver = improver
        self.metrics_collector = metrics_collector or DefaultMetricsCollector()
        self.config = config or RetrospectiveConfig()
        self._results_store: Dict[str, RetrospectiveResult] = {}

        logger.info("RetrospectiveEngine initialized")

    async def run_retrospective(
        self,
        team_id: str,
        sprint_id: str,
        timeframe: Optional[Timeframe] = None
    ) -> RetrospectiveResult:
        """
        Run a complete retrospective for a team.

        Args:
            team_id: Identifier for the team
            sprint_id: Identifier for the sprint
            timeframe: Optional custom timeframe (defaults to last sprint)

        Returns:
            RetrospectiveResult with all analysis and recommendations
        """
        logger.info(f"[RETRO] Started retrospective for team={team_id}, sprint={sprint_id}")

        result = RetrospectiveResult(
            team_id=team_id,
            sprint_id=sprint_id,
            status=RetrospectiveStatus.IN_PROGRESS,
        )

        try:
            # 1. Collect metrics
            timeframe = timeframe or Timeframe.last_sprint()
            result.metrics = self.get_metrics(team_id, timeframe)

            # 2. Evaluate performance
            if self.evaluator:
                result.assessment = self.evaluator.evaluate_performance(result.metrics)
                logger.info(f"[EVAL] Performance assessment completed score={result.assessment.overall_score}")
            else:
                # Default assessment if no evaluator
                result.assessment = self._default_assessment(result.metrics)

            # 3. Generate improvements
            if self.improver:
                improvements = self.improver.suggest_improvements(
                    result.metrics,
                    result.assessment
                )
                result.improvements = self.improver.prioritize_actions(improvements)
                logger.info(f"[IMPROVE] Generated {len(result.improvements)} improvement suggestions")
            else:
                result.improvements = self._default_improvements(result.assessment)

            # 4. Create action items from top improvements
            result.action_items = self._create_action_items(
                result.improvements[:self.config.max_action_items]
            )

            # 5. Generate report
            result.report = self.generate_report(result)

            result.status = RetrospectiveStatus.COMPLETED
            result.completed_at = datetime.utcnow()

        except Exception as e:
            logger.error(f"Retrospective failed: {e}")
            result.status = RetrospectiveStatus.FAILED
            result.error = str(e)

        # Store result
        self._results_store[result.id] = result

        return result

    def get_metrics(self, team_id: str, timeframe: Timeframe) -> TeamMetrics:
        """
        Collect team metrics for a given timeframe.

        Args:
            team_id: Team identifier
            timeframe: Time period for metrics

        Returns:
            TeamMetrics with collected data
        """
        return self.metrics_collector.collect(team_id, timeframe)

    def track_action_item(self, item: ActionItem) -> bool:
        """
        Track an action item status update.

        Args:
            item: ActionItem to track

        Returns:
            True if tracking successful
        """
        logger.info(f"Tracking action item {item.id}: {item.status.value}")
        return True

    def generate_report(self, result: RetrospectiveResult) -> RetrospectiveReport:
        """
        Generate a human-readable report from results.

        Args:
            result: RetrospectiveResult to summarize

        Returns:
            RetrospectiveReport for presentation
        """
        return RetrospectiveReport(
            team_id=result.team_id,
            sprint_id=result.sprint_id,
            metrics_summary=result.metrics.to_dict() if result.metrics else {},
            assessment_summary=result.assessment.summary if result.assessment else "",
            top_improvements=[
                i.to_dict()
                for i in result.improvements[:3]
            ],
            action_items=[
                a.to_dict()
                for a in result.action_items
            ],
        )

    def get_retrospective(self, retrospective_id: str) -> Optional[RetrospectiveResult]:
        """Get a stored retrospective result by ID"""
        return self._results_store.get(retrospective_id)

    def list_retrospectives(
        self,
        team_id: Optional[str] = None,
        limit: int = 10
    ) -> List[RetrospectiveResult]:
        """List retrospectives, optionally filtered by team"""
        results = list(self._results_store.values())
        if team_id:
            results = [r for r in results if r.team_id == team_id]
        return sorted(results, key=lambda r: r.started_at, reverse=True)[:limit]

    def _default_assessment(self, metrics: TeamMetrics) -> PerformanceAssessment:
        """Generate a default assessment when no evaluator is available"""
        # Simple scoring based on available metrics
        scores = {}
        total = 0.0
        count = 0

        for metric in metrics.metrics:
            category = metric.category.value
            # Normalize metric values to 0-1 scale (simplified)
            normalized = min(1.0, max(0.0, metric.value / 100.0 if metric.value > 1 else metric.value))
            scores[category] = normalized
            total += normalized
            count += 1

        overall = total / count if count > 0 else 0.5

        return PerformanceAssessment(
            team_id=metrics.team_id,
            overall_score=overall,
            category_scores=scores,
            strengths=["Consistent delivery", "Good collaboration"],
            areas_for_improvement=["Technical debt reduction", "Testing coverage"],
            summary=f"Team performance score: {overall:.2f}",
        )

    def _default_improvements(self, assessment: PerformanceAssessment) -> List[Improvement]:
        """Generate default improvements based on assessment"""
        improvements = []

        for area in assessment.areas_for_improvement:
            improvements.append(
                Improvement(
                    title=f"Improve {area}",
                    description=f"Focus on improving {area} based on retrospective analysis",
                    category="process",
                    impact_score=0.7,
                    effort_score=0.5,
                    priority=len(improvements) + 1,
                    confidence=0.75,
                )
            )

        return improvements

    def _create_action_items(self, improvements: List[Improvement]) -> List[ActionItem]:
        """Create action items from improvements"""
        action_items = []

        for improvement in improvements:
            action_items.append(
                ActionItem(
                    title=improvement.title,
                    description=improvement.description,
                    improvement_id=improvement.id,
                    due_date=datetime.utcnow() + timedelta(days=14),
                )
            )

        return action_items


# Module-level factory function
def create_retrospective_engine(
    evaluator: Optional[EvaluatorInterface] = None,
    improver: Optional[ImproverInterface] = None,
    config: Optional[RetrospectiveConfig] = None
) -> RetrospectiveEngine:
    """
    Factory function to create a configured RetrospectiveEngine.

    Args:
        evaluator: Optional EvaluatorPersona instance
        improver: Optional ProcessImprover instance
        config: Optional configuration

    Returns:
        Configured RetrospectiveEngine instance
    """
    return RetrospectiveEngine(
        evaluator=evaluator,
        improver=improver,
        config=config,
    )
