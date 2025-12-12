"""
Performance Optimizer Module - MD-3020

Analyzes and optimizes team performance through metrics analysis
and actionable recommendations.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging
import statistics

logger = logging.getLogger(__name__)


class OptimizationTarget(Enum):
    """Optimization targets for teams."""
    THROUGHPUT = "throughput"
    QUALITY = "quality"
    EFFICIENCY = "efficiency"
    BALANCED = "balanced"


class RecommendationPriority(Enum):
    """Priority levels for recommendations."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class PerformanceMetric:
    """A single performance measurement."""
    name: str
    value: float
    timestamp: datetime
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceSnapshot:
    """Snapshot of team performance at a point in time."""
    team_id: str
    timestamp: datetime
    throughput: float
    quality: float
    efficiency: float
    metrics: List[PerformanceMetric] = field(default_factory=list)

    @property
    def overall_score(self) -> float:
        """Calculate overall performance score."""
        return (self.throughput + self.quality + self.efficiency) / 3


@dataclass
class Recommendation:
    """An optimization recommendation."""
    id: str
    team_id: str
    title: str
    description: str
    priority: RecommendationPriority
    estimated_impact: float
    action_type: str
    action_details: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.8
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "team_id": self.team_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "estimated_impact": self.estimated_impact,
            "action_type": self.action_type,
            "action_details": self.action_details,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class AnalysisResult:
    """Result of performance analysis."""
    team_id: str
    analysis_timestamp: datetime
    current_performance: PerformanceSnapshot
    trend: str  # "improving", "declining", "stable"
    trend_confidence: float
    bottlenecks: List[str]
    strengths: List[str]
    recommendations: List[Recommendation]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OptimizationResult:
    """Result of an optimization run."""
    team_id: str
    target: OptimizationTarget
    before_score: float
    after_score: float
    improvement: float
    actions_taken: List[str]
    recommendations_applied: List[str]
    duration_ms: int
    success: bool


@dataclass
class OptimizerConfig:
    """Configuration for the performance optimizer."""
    target: OptimizationTarget = OptimizationTarget.BALANCED
    history_window: int = 30  # days
    min_data_points: int = 10
    recommendation_limit: int = 5
    confidence_threshold: float = 0.7
    trend_threshold: float = 0.05


class PerformanceOptimizer:
    """
    Optimizes team performance through analysis and recommendations.

    Analyzes historical performance data, identifies bottlenecks,
    and generates actionable recommendations for improvement.
    """

    def __init__(self, config: Optional[OptimizerConfig] = None):
        self.config = config or OptimizerConfig()
        self._history: Dict[str, List[PerformanceSnapshot]] = {}
        self._recommendations: Dict[str, List[Recommendation]] = {}
        self._rec_counter = 0
        logger.info(f"PerformanceOptimizer initialized with target: {self.config.target.value}")

    def record_performance(
        self,
        team_id: str,
        throughput: float,
        quality: float,
        efficiency: float,
        metrics: Optional[List[PerformanceMetric]] = None
    ) -> PerformanceSnapshot:
        """Record a performance snapshot for a team."""
        snapshot = PerformanceSnapshot(
            team_id=team_id,
            timestamp=datetime.now(),
            throughput=throughput,
            quality=quality,
            efficiency=efficiency,
            metrics=metrics or []
        )

        if team_id not in self._history:
            self._history[team_id] = []

        self._history[team_id].append(snapshot)

        # Prune old history
        cutoff = datetime.now() - timedelta(days=self.config.history_window)
        self._history[team_id] = [
            s for s in self._history[team_id]
            if s.timestamp >= cutoff
        ]

        logger.debug(f"Recorded performance for {team_id}: {snapshot.overall_score:.2f}")
        return snapshot

    def get_history(
        self,
        team_id: str,
        days: Optional[int] = None
    ) -> List[PerformanceSnapshot]:
        """Get performance history for a team."""
        history = self._history.get(team_id, [])

        if days:
            cutoff = datetime.now() - timedelta(days=days)
            history = [s for s in history if s.timestamp >= cutoff]

        return history

    def analyze(
        self,
        team_id: str,
        metrics: Optional[List[PerformanceMetric]] = None
    ) -> AnalysisResult:
        """
        Analyze team performance and generate insights.

        Args:
            team_id: ID of the team to analyze
            metrics: Optional additional metrics to include

        Returns:
            AnalysisResult with findings and recommendations
        """
        history = self.get_history(team_id)

        # Get or create current snapshot
        if history:
            current = history[-1]
        else:
            # Create default snapshot
            current = PerformanceSnapshot(
                team_id=team_id,
                timestamp=datetime.now(),
                throughput=0.5,
                quality=0.5,
                efficiency=0.5
            )

        # Calculate trend
        trend, trend_confidence = self._calculate_trend(history)

        # Identify bottlenecks and strengths
        bottlenecks = self._identify_bottlenecks(current)
        strengths = self._identify_strengths(current)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            team_id, current, history, bottlenecks
        )

        return AnalysisResult(
            team_id=team_id,
            analysis_timestamp=datetime.now(),
            current_performance=current,
            trend=trend,
            trend_confidence=trend_confidence,
            bottlenecks=bottlenecks,
            strengths=strengths,
            recommendations=recommendations
        )

    def optimize(
        self,
        team_id: str,
        target: Optional[OptimizationTarget] = None
    ) -> OptimizationResult:
        """
        Run optimization for a team.

        Args:
            team_id: ID of the team to optimize
            target: Optimization target (uses config default if not specified)

        Returns:
            OptimizationResult with optimization outcomes
        """
        start_time = datetime.now()
        target = target or self.config.target

        # Get current state
        history = self.get_history(team_id)
        before_score = history[-1].overall_score if history else 0.5

        # Get recommendations
        recommendations = self.get_recommendations(team_id)

        # Apply recommendations (simulated)
        actions_taken = []
        applied_recs = []

        for rec in recommendations[:3]:  # Apply top 3 recommendations
            if rec.confidence >= self.config.confidence_threshold:
                actions_taken.append(rec.action_type)
                applied_recs.append(rec.id)

                # Simulate improvement
                self._apply_recommendation(team_id, rec, target)

        # Calculate new score
        history = self.get_history(team_id)
        after_score = history[-1].overall_score if history else before_score

        duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return OptimizationResult(
            team_id=team_id,
            target=target,
            before_score=before_score,
            after_score=after_score,
            improvement=after_score - before_score,
            actions_taken=actions_taken,
            recommendations_applied=applied_recs,
            duration_ms=duration_ms,
            success=after_score >= before_score
        )

    def get_recommendations(self, team_id: str) -> List[Recommendation]:
        """Get current recommendations for a team."""
        if team_id not in self._recommendations:
            analysis = self.analyze(team_id)
            self._recommendations[team_id] = analysis.recommendations

        return self._recommendations.get(team_id, [])

    def calculate_efficiency(self, team_id: str) -> float:
        """Calculate current efficiency score for a team."""
        history = self.get_history(team_id)
        if not history:
            return 0.0
        return history[-1].efficiency

    def calculate_overall_score(self, team_id: str) -> float:
        """Calculate overall performance score for a team."""
        history = self.get_history(team_id)
        if not history:
            return 0.0
        return history[-1].overall_score

    def _calculate_trend(
        self,
        history: List[PerformanceSnapshot]
    ) -> Tuple[str, float]:
        """Calculate performance trend from history."""
        if len(history) < self.config.min_data_points:
            return "stable", 0.5

        scores = [s.overall_score for s in history]
        n = len(scores)

        # Simple linear regression
        x_mean = (n - 1) / 2
        y_mean = sum(scores) / n

        numerator = sum((i - x_mean) * (scores[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return "stable", 0.5

        slope = numerator / denominator

        # Determine trend
        if slope > self.config.trend_threshold:
            trend = "improving"
        elif slope < -self.config.trend_threshold:
            trend = "declining"
        else:
            trend = "stable"

        # Calculate confidence based on variance
        variance = statistics.variance(scores) if len(scores) > 1 else 0
        confidence = max(0.0, min(1.0, 1.0 - variance))

        return trend, confidence

    def _identify_bottlenecks(self, snapshot: PerformanceSnapshot) -> List[str]:
        """Identify performance bottlenecks."""
        bottlenecks = []
        threshold = 0.6

        if snapshot.throughput < threshold:
            bottlenecks.append("low_throughput")
        if snapshot.quality < threshold:
            bottlenecks.append("quality_issues")
        if snapshot.efficiency < threshold:
            bottlenecks.append("low_efficiency")

        # Check individual metrics
        for metric in snapshot.metrics:
            if metric.value < 0.5:
                bottlenecks.append(f"low_{metric.name}")

        return bottlenecks

    def _identify_strengths(self, snapshot: PerformanceSnapshot) -> List[str]:
        """Identify team strengths."""
        strengths = []
        threshold = 0.8

        if snapshot.throughput >= threshold:
            strengths.append("high_throughput")
        if snapshot.quality >= threshold:
            strengths.append("excellent_quality")
        if snapshot.efficiency >= threshold:
            strengths.append("high_efficiency")

        return strengths

    def _generate_recommendations(
        self,
        team_id: str,
        current: PerformanceSnapshot,
        history: List[PerformanceSnapshot],
        bottlenecks: List[str]
    ) -> List[Recommendation]:
        """Generate optimization recommendations."""
        recommendations = []

        # Generate recommendations based on bottlenecks
        for bottleneck in bottlenecks:
            rec = self._create_recommendation_for_bottleneck(team_id, bottleneck)
            if rec:
                recommendations.append(rec)

        # Add general recommendations if needed
        if current.overall_score < 0.7:
            self._rec_counter += 1
            recommendations.append(Recommendation(
                id=f"rec_{self._rec_counter}",
                team_id=team_id,
                title="Consider team composition review",
                description="Overall performance below threshold. Review team roles and skills.",
                priority=RecommendationPriority.HIGH,
                estimated_impact=0.15,
                action_type="composition_review",
                confidence=0.8
            ))

        # Sort by priority and impact
        recommendations.sort(
            key=lambda r: (r.priority.value, -r.estimated_impact)
        )

        return recommendations[:self.config.recommendation_limit]

    def _create_recommendation_for_bottleneck(
        self,
        team_id: str,
        bottleneck: str
    ) -> Optional[Recommendation]:
        """Create a recommendation for a specific bottleneck."""
        self._rec_counter += 1

        recommendations_map = {
            "low_throughput": {
                "title": "Increase team velocity",
                "description": "Throughput is below target. Consider adding parallel work streams or removing blockers.",
                "priority": RecommendationPriority.HIGH,
                "impact": 0.2,
                "action": "increase_throughput"
            },
            "quality_issues": {
                "title": "Improve quality processes",
                "description": "Quality metrics need attention. Add more testing or code review.",
                "priority": RecommendationPriority.CRITICAL,
                "impact": 0.25,
                "action": "improve_quality"
            },
            "low_efficiency": {
                "title": "Optimize resource utilization",
                "description": "Efficiency is low. Review task allocation and reduce context switching.",
                "priority": RecommendationPriority.MEDIUM,
                "impact": 0.15,
                "action": "optimize_efficiency"
            }
        }

        if bottleneck in recommendations_map:
            rec_data = recommendations_map[bottleneck]
            return Recommendation(
                id=f"rec_{self._rec_counter}",
                team_id=team_id,
                title=rec_data["title"],
                description=rec_data["description"],
                priority=rec_data["priority"],
                estimated_impact=rec_data["impact"],
                action_type=rec_data["action"],
                confidence=0.85
            )

        return None

    def _apply_recommendation(
        self,
        team_id: str,
        recommendation: Recommendation,
        target: OptimizationTarget
    ) -> None:
        """Apply a recommendation (simulate improvement)."""
        history = self.get_history(team_id)
        if not history:
            return

        last_snapshot = history[-1]

        # Calculate improvement based on recommendation impact
        improvement = recommendation.estimated_impact * recommendation.confidence

        # Apply improvement based on target
        if target == OptimizationTarget.THROUGHPUT:
            new_throughput = min(1.0, last_snapshot.throughput + improvement)
            self.record_performance(
                team_id, new_throughput, last_snapshot.quality, last_snapshot.efficiency
            )
        elif target == OptimizationTarget.QUALITY:
            new_quality = min(1.0, last_snapshot.quality + improvement)
            self.record_performance(
                team_id, last_snapshot.throughput, new_quality, last_snapshot.efficiency
            )
        elif target == OptimizationTarget.EFFICIENCY:
            new_efficiency = min(1.0, last_snapshot.efficiency + improvement)
            self.record_performance(
                team_id, last_snapshot.throughput, last_snapshot.quality, new_efficiency
            )
        else:  # BALANCED
            partial = improvement / 3
            self.record_performance(
                team_id,
                min(1.0, last_snapshot.throughput + partial),
                min(1.0, last_snapshot.quality + partial),
                min(1.0, last_snapshot.efficiency + partial)
            )

        logger.info(f"Applied recommendation {recommendation.id} to team {team_id}")

    def get_available_targets(self) -> List[str]:
        """Return list of available optimization targets."""
        return [t.value for t in OptimizationTarget]

    def clear_history(self, team_id: str) -> None:
        """Clear performance history for a team."""
        if team_id in self._history:
            self._history[team_id] = []
        if team_id in self._recommendations:
            del self._recommendations[team_id]
        logger.info(f"Cleared history for team {team_id}")


# Module-level convenience functions
_default_optimizer: Optional[PerformanceOptimizer] = None


def get_default_optimizer() -> PerformanceOptimizer:
    """Get or create the default performance optimizer instance."""
    global _default_optimizer
    if _default_optimizer is None:
        _default_optimizer = PerformanceOptimizer()
    return _default_optimizer


def analyze_team(team_id: str) -> AnalysisResult:
    """Convenience function for quick team analysis."""
    optimizer = get_default_optimizer()
    return optimizer.analyze(team_id)


def optimize_team(
    team_id: str,
    target: str = "balanced"
) -> OptimizationResult:
    """Convenience function for quick team optimization."""
    optimizer = get_default_optimizer()
    target_enum = OptimizationTarget(target)
    return optimizer.optimize(team_id, target_enum)
