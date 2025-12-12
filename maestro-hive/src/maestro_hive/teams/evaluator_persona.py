"""
EvaluatorPersona: AI-Powered Team Performance Evaluator

This module implements an AI persona specialized in evaluating software team
performance. It integrates with PersonaRegistry (MD-2962) and provides
multi-dimensional assessment of team metrics.

EPIC: MD-3015 - Autonomous Team Retrospective & Evaluation

Evaluation Criteria:
- Velocity Consistency (25%): Sprint-over-sprint stability
- Quality Metrics (30%): Bug rates, code coverage, review quality
- Collaboration Score (20%): PR reviews, pair programming, knowledge sharing
- Delivery Reliability (25%): Commitment accuracy, deadline adherence
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum
import logging


logger = logging.getLogger(__name__)


class EvaluationLevel(Enum):
    """Performance evaluation levels"""
    EXCEPTIONAL = "exceptional"  # 0.9 - 1.0
    STRONG = "strong"            # 0.75 - 0.9
    MEETING_EXPECTATIONS = "meeting_expectations"  # 0.6 - 0.75
    NEEDS_IMPROVEMENT = "needs_improvement"        # 0.4 - 0.6
    CRITICAL = "critical"        # 0.0 - 0.4


class EvaluationCriteria(Enum):
    """Evaluation criteria categories"""
    VELOCITY_CONSISTENCY = "velocity_consistency"
    QUALITY_METRICS = "quality_metrics"
    COLLABORATION_SCORE = "collaboration_score"
    DELIVERY_RELIABILITY = "delivery_reliability"


# Default weights for evaluation criteria
DEFAULT_WEIGHTS = {
    EvaluationCriteria.VELOCITY_CONSISTENCY: 0.25,
    EvaluationCriteria.QUALITY_METRICS: 0.30,
    EvaluationCriteria.COLLABORATION_SCORE: 0.20,
    EvaluationCriteria.DELIVERY_RELIABILITY: 0.25,
}


@dataclass
class CriterionScore:
    """Score for a single evaluation criterion"""
    criterion: EvaluationCriteria
    score: float  # 0.0 to 1.0
    weight: float
    weighted_score: float
    analysis: str = ""
    data_points: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class FeedbackItem:
    """A single piece of feedback"""
    category: str
    feedback_type: str  # "strength" or "improvement"
    message: str
    priority: int = 0
    actionable: bool = True


@dataclass
class FeedbackReport:
    """Comprehensive feedback report"""
    team_id: str
    generated_at: datetime = field(default_factory=datetime.utcnow)
    overall_feedback: str = ""
    strengths: List[FeedbackItem] = field(default_factory=list)
    improvements: List[FeedbackItem] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "generated_at": self.generated_at.isoformat(),
            "overall_feedback": self.overall_feedback,
            "strengths": [
                {"category": s.category, "message": s.message}
                for s in self.strengths
            ],
            "improvements": [
                {"category": i.category, "message": i.message, "priority": i.priority}
                for i in self.improvements
            ],
            "recommendations": self.recommendations,
        }


@dataclass
class TeamScore:
    """Overall team performance score"""
    team_id: str
    overall: float
    level: EvaluationLevel
    criterion_scores: List[CriterionScore] = field(default_factory=list)
    trend: Optional[float] = None  # Change from previous period
    evaluated_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "team_id": self.team_id,
            "overall": self.overall,
            "level": self.level.value,
            "criterion_scores": [
                {
                    "criterion": cs.criterion.value,
                    "score": cs.score,
                    "weight": cs.weight,
                    "weighted_score": cs.weighted_score,
                }
                for cs in self.criterion_scores
            ],
            "trend": self.trend,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


@dataclass
class EvaluatorConfig:
    """Configuration for the evaluator persona"""
    persona_id: str = "team_evaluator"
    model_id: str = "claude-3-sonnet-20240229"
    temperature: float = 0.3
    max_tokens: int = 4096
    weights: Dict[EvaluationCriteria, float] = field(default_factory=lambda: DEFAULT_WEIGHTS.copy())
    min_data_points: int = 3  # Minimum data points required for reliable evaluation


class EvaluatorPersona:
    """
    AI-Powered Team Performance Evaluator

    Evaluates team performance across multiple dimensions using
    configurable criteria and weights. Integrates with PersonaRegistry
    for consistent persona management.

    Example:
        >>> evaluator = EvaluatorPersona()
        >>> assessment = evaluator.evaluate_performance(metrics)
        >>> print(f"Team score: {assessment.overall_score}")
    """

    def __init__(
        self,
        persona_id: str = "team_evaluator",
        criteria: Optional[List[EvaluationCriteria]] = None,
        config: Optional[EvaluatorConfig] = None
    ):
        """
        Initialize the EvaluatorPersona.

        Args:
            persona_id: Unique identifier for this persona
            criteria: List of evaluation criteria to use
            config: Configuration options
        """
        self.persona_id = persona_id
        self.criteria = criteria or list(EvaluationCriteria)
        self.config = config or EvaluatorConfig(persona_id=persona_id)
        self._evaluation_history: List[TeamScore] = []

        logger.info(f"EvaluatorPersona initialized: {persona_id}")

    def evaluate_performance(self, metrics: Any) -> Any:
        """
        Evaluate team performance based on collected metrics.

        Args:
            metrics: TeamMetrics object with collected data

        Returns:
            PerformanceAssessment with evaluation results
        """
        from .retrospective_engine import PerformanceAssessment, MetricCategory

        logger.info(f"Evaluating performance for team {metrics.team_id}")

        # Calculate criterion scores
        criterion_scores = []
        for criterion in self.criteria:
            score = self._evaluate_criterion(criterion, metrics)
            criterion_scores.append(score)

        # Calculate overall score
        total_weighted = sum(cs.weighted_score for cs in criterion_scores)
        overall_score = min(1.0, max(0.0, total_weighted))

        # Determine level
        level = self._determine_level(overall_score)

        # Identify strengths and areas for improvement
        strengths = []
        improvements = []

        for cs in criterion_scores:
            if cs.score >= 0.75:
                strengths.append(f"Strong {cs.criterion.value.replace('_', ' ')}: {cs.score:.0%}")
            elif cs.score < 0.6:
                improvements.append(f"Improve {cs.criterion.value.replace('_', ' ')}: currently at {cs.score:.0%}")

        # Generate summary
        summary = self._generate_summary(overall_score, level, criterion_scores)

        # Create TeamScore for history
        team_score = TeamScore(
            team_id=metrics.team_id,
            overall=overall_score,
            level=level,
            criterion_scores=criterion_scores,
        )
        self._evaluation_history.append(team_score)

        # Return PerformanceAssessment
        return PerformanceAssessment(
            team_id=metrics.team_id,
            overall_score=overall_score,
            category_scores={
                cs.criterion.value: cs.score
                for cs in criterion_scores
            },
            strengths=strengths,
            areas_for_improvement=improvements,
            summary=summary,
        )

    def generate_feedback(self, assessment: Any) -> FeedbackReport:
        """
        Generate detailed feedback report from assessment.

        Args:
            assessment: PerformanceAssessment to analyze

        Returns:
            FeedbackReport with actionable feedback
        """
        logger.info(f"Generating feedback for team {assessment.team_id}")

        strengths = [
            FeedbackItem(
                category="performance",
                feedback_type="strength",
                message=strength,
            )
            for strength in assessment.strengths
        ]

        improvements = [
            FeedbackItem(
                category="performance",
                feedback_type="improvement",
                message=improvement,
                priority=idx + 1,
            )
            for idx, improvement in enumerate(assessment.areas_for_improvement)
        ]

        recommendations = self._generate_recommendations(assessment)

        return FeedbackReport(
            team_id=assessment.team_id,
            overall_feedback=assessment.summary,
            strengths=strengths,
            improvements=improvements,
            recommendations=recommendations,
        )

    def score_team(self, metrics: Any) -> float:
        """
        Calculate overall team score from metrics.

        Args:
            metrics: TeamMetrics object

        Returns:
            Overall score (0.0 to 1.0)
        """
        assessment = self.evaluate_performance(metrics)
        return assessment.overall_score

    def get_evaluation_history(self, team_id: str, limit: int = 10) -> List[TeamScore]:
        """Get historical evaluations for a team"""
        history = [e for e in self._evaluation_history if e.team_id == team_id]
        return sorted(history, key=lambda e: e.evaluated_at, reverse=True)[:limit]

    def _evaluate_criterion(self, criterion: EvaluationCriteria, metrics: Any) -> CriterionScore:
        """Evaluate a single criterion"""
        from .retrospective_engine import MetricCategory

        weight = self.config.weights.get(criterion, 0.25)
        score = 0.5  # Default score
        analysis = ""

        # Map criteria to metric categories and calculate scores
        if criterion == EvaluationCriteria.VELOCITY_CONSISTENCY:
            velocity_metrics = metrics.get_by_category(MetricCategory.VELOCITY)
            if velocity_metrics:
                # Higher velocity with positive trend = better
                base_score = velocity_metrics[0].value / 50.0  # Normalize to ~50 points
                trend_bonus = (velocity_metrics[0].trend or 0) / 100.0
                score = min(1.0, max(0.0, base_score + trend_bonus))
                analysis = f"Velocity at {velocity_metrics[0].value} points"

        elif criterion == EvaluationCriteria.QUALITY_METRICS:
            quality_metrics = metrics.get_by_category(MetricCategory.QUALITY)
            if quality_metrics:
                # Lower bug rate = better score
                bug_rate = quality_metrics[0].value
                score = max(0.0, 1.0 - bug_rate * 2)  # 0.5 bugs/story = 0 score
                analysis = f"Bug rate at {bug_rate:.2f}"

        elif criterion == EvaluationCriteria.COLLABORATION_SCORE:
            collab_metrics = metrics.get_by_category(MetricCategory.COLLABORATION)
            if collab_metrics:
                # Lower review turnaround = better
                turnaround = collab_metrics[0].value
                score = max(0.0, 1.0 - turnaround / 24.0)  # 24h = 0 score
                analysis = f"Review turnaround: {turnaround:.1f}h"

        elif criterion == EvaluationCriteria.DELIVERY_RELIABILITY:
            delivery_metrics = metrics.get_by_category(MetricCategory.DELIVERY)
            if delivery_metrics:
                # Completion rate directly maps to score
                score = delivery_metrics[0].value
                analysis = f"Sprint completion: {score:.0%}"

        return CriterionScore(
            criterion=criterion,
            score=score,
            weight=weight,
            weighted_score=score * weight,
            analysis=analysis,
        )

    def _determine_level(self, score: float) -> EvaluationLevel:
        """Determine evaluation level from score"""
        if score >= 0.9:
            return EvaluationLevel.EXCEPTIONAL
        elif score >= 0.75:
            return EvaluationLevel.STRONG
        elif score >= 0.6:
            return EvaluationLevel.MEETING_EXPECTATIONS
        elif score >= 0.4:
            return EvaluationLevel.NEEDS_IMPROVEMENT
        else:
            return EvaluationLevel.CRITICAL

    def _generate_summary(
        self,
        overall: float,
        level: EvaluationLevel,
        scores: List[CriterionScore]
    ) -> str:
        """Generate evaluation summary text"""
        level_text = level.value.replace("_", " ").title()

        top_criterion = max(scores, key=lambda s: s.score)
        bottom_criterion = min(scores, key=lambda s: s.score)

        summary = (
            f"Team performance: {level_text} ({overall:.0%}). "
            f"Strongest in {top_criterion.criterion.value.replace('_', ' ')} ({top_criterion.score:.0%}). "
            f"Focus area: {bottom_criterion.criterion.value.replace('_', ' ')} ({bottom_criterion.score:.0%})."
        )

        return summary

    def _generate_recommendations(self, assessment: Any) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        if assessment.overall_score < 0.6:
            recommendations.append("Schedule a team retrospective meeting to discuss improvement areas")

        for area in assessment.areas_for_improvement[:2]:
            if "velocity" in area.lower():
                recommendations.append("Review sprint planning process and commitment practices")
            elif "quality" in area.lower():
                recommendations.append("Implement or enhance code review requirements")
            elif "collaboration" in area.lower():
                recommendations.append("Consider pair programming sessions and knowledge sharing")
            elif "delivery" in area.lower():
                recommendations.append("Break down stories into smaller, deliverable increments")

        return recommendations


# Factory function
def create_evaluator_persona(
    persona_id: str = "team_evaluator",
    config: Optional[EvaluatorConfig] = None
) -> EvaluatorPersona:
    """
    Factory function to create an EvaluatorPersona.

    Args:
        persona_id: Identifier for the persona
        config: Optional configuration

    Returns:
        Configured EvaluatorPersona instance
    """
    return EvaluatorPersona(
        persona_id=persona_id,
        config=config,
    )
