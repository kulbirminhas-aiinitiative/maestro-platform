"""
DDE Agent Evaluation Framework (MD-886)

Multi-dimensional evaluation of AI agent performance.
Foundation for agent selection and improvement recommendations.

Evaluation Dimensions:
- Code quality (linting, tests)
- Contract fulfillment
- Time efficiency
- Error rate
- Rework frequency

ML Integration Points:
- Quality prediction model
- Agent improvement recommendations
- Optimal agent for task type
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import statistics

from dde.performance_tracker import get_performance_tracker, AgentPerformanceSummary
from dde.agent_registry import get_agent_registry

logger = logging.getLogger(__name__)


@dataclass
class EvaluationScore:
    """Individual evaluation dimension score"""
    dimension: str
    score: float  # 0.0 to 1.0
    weight: float
    details: str
    trend: str = "stable"  # improving, stable, declining


@dataclass
class AgentEvaluation:
    """Complete agent evaluation result"""
    agent_id: str
    agent_name: str
    overall_score: float
    grade: str  # A, B, C, D, F
    scores: List[EvaluationScore]
    strengths: List[str]
    improvements: List[str]
    recommendations: List[str]
    evaluated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'overall_score': round(self.overall_score, 4),
            'grade': self.grade,
            'scores': [
                {
                    'dimension': s.dimension,
                    'score': round(s.score, 4),
                    'weight': s.weight,
                    'details': s.details,
                    'trend': s.trend
                }
                for s in self.scores
            ],
            'strengths': self.strengths,
            'improvements': self.improvements,
            'recommendations': self.recommendations,
            'evaluated_at': self.evaluated_at.isoformat()
        }


class AgentEvaluator:
    """
    Agent Evaluation Framework

    Provides multi-dimensional evaluation of agent performance.
    """

    # Evaluation weights (ML will optimize these)
    DEFAULT_WEIGHTS = {
        'quality': 0.30,
        'contract_fulfillment': 0.25,
        'time_efficiency': 0.20,
        'error_rate': 0.15,
        'consistency': 0.10
    }

    # Grade thresholds
    GRADE_THRESHOLDS = {
        'A': 0.90,
        'B': 0.80,
        'C': 0.70,
        'D': 0.60,
        'F': 0.0
    }

    def __init__(self, weights: Dict[str, float] = None):
        """
        Initialize evaluator.

        Args:
            weights: Custom evaluation weights
        """
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.tracker = get_performance_tracker()
        self.registry = get_agent_registry()

        logger.info("✅ AgentEvaluator initialized")

    def evaluate_agent(
        self,
        agent_id: str,
        time_window_days: int = 30
    ) -> Optional[AgentEvaluation]:
        """
        Evaluate an agent's performance.

        Args:
            agent_id: Agent to evaluate
            time_window_days: Evaluation period

        Returns:
            AgentEvaluation or None if insufficient data
        """
        # Get agent profile
        profile = self.registry.get_agent(agent_id)
        if not profile:
            logger.warning(f"Agent not found: {agent_id}")
            return None

        # Get performance summary
        summary = self.tracker.get_agent_summary(agent_id, time_window_days)
        if not summary or summary.total_executions < 1:
            logger.warning(f"Insufficient data for {agent_id}")
            return None

        # Calculate dimension scores
        scores = []

        # 1. Quality Score
        quality_score = self._evaluate_quality(summary)
        scores.append(quality_score)

        # 2. Contract Fulfillment
        fulfillment_score = self._evaluate_fulfillment(summary)
        scores.append(fulfillment_score)

        # 3. Time Efficiency
        efficiency_score = self._evaluate_efficiency(summary)
        scores.append(efficiency_score)

        # 4. Error Rate
        error_score = self._evaluate_errors(summary)
        scores.append(error_score)

        # 5. Consistency
        consistency_score = self._evaluate_consistency(agent_id, time_window_days)
        scores.append(consistency_score)

        # Calculate overall score
        overall = sum(s.score * s.weight for s in scores)

        # Determine grade
        grade = self._calculate_grade(overall)

        # Generate insights
        strengths = self._identify_strengths(scores)
        improvements = self._identify_improvements(scores)
        recommendations = self._generate_recommendations(scores, summary)

        return AgentEvaluation(
            agent_id=agent_id,
            agent_name=profile.name,
            overall_score=overall,
            grade=grade,
            scores=scores,
            strengths=strengths,
            improvements=improvements,
            recommendations=recommendations
        )

    def _evaluate_quality(self, summary: AgentPerformanceSummary) -> EvaluationScore:
        """Evaluate code/output quality"""
        score = summary.avg_quality_score
        trend = summary.quality_trend

        if score >= 0.95:
            details = "Excellent quality output"
        elif score >= 0.85:
            details = "Good quality with minor issues"
        elif score >= 0.70:
            details = "Acceptable quality, room for improvement"
        else:
            details = "Quality needs significant improvement"

        return EvaluationScore(
            dimension="Quality",
            score=score,
            weight=self.weights['quality'],
            details=details,
            trend=trend
        )

    def _evaluate_fulfillment(self, summary: AgentPerformanceSummary) -> EvaluationScore:
        """Evaluate contract fulfillment rate"""
        score = summary.contract_fulfillment_rate

        if score >= 0.95:
            details = "Consistently fulfills all contracts"
        elif score >= 0.85:
            details = "Usually fulfills contracts"
        elif score >= 0.70:
            details = "Sometimes misses contract requirements"
        else:
            details = "Frequently fails to fulfill contracts"

        return EvaluationScore(
            dimension="Contract Fulfillment",
            score=score,
            weight=self.weights['contract_fulfillment'],
            details=details
        )

    def _evaluate_efficiency(self, summary: AgentPerformanceSummary) -> EvaluationScore:
        """Evaluate time efficiency"""
        # Compare to expected duration (this would be enhanced with ML)
        # For now, use files per second as proxy
        files_per_min = summary.avg_files_per_execution / (summary.avg_duration_seconds / 60)

        # Normalize to 0-1 (assuming 2 files/min is excellent)
        score = min(1.0, files_per_min / 2.0)

        if score >= 0.8:
            details = f"Efficient: {files_per_min:.1f} files/min"
        elif score >= 0.5:
            details = f"Moderate: {files_per_min:.1f} files/min"
        else:
            details = f"Slow: {files_per_min:.1f} files/min"

        return EvaluationScore(
            dimension="Time Efficiency",
            score=score,
            weight=self.weights['time_efficiency'],
            details=details
        )

    def _evaluate_errors(self, summary: AgentPerformanceSummary) -> EvaluationScore:
        """Evaluate error rate (inverted - lower is better)"""
        # Invert error rate
        score = 1.0 - summary.error_rate

        if score >= 0.95:
            details = "Rarely produces errors"
        elif score >= 0.85:
            details = "Occasional minor errors"
        elif score >= 0.70:
            details = "Moderate error frequency"
        else:
            details = "High error rate needs attention"

        return EvaluationScore(
            dimension="Error Rate",
            score=score,
            weight=self.weights['error_rate'],
            details=details
        )

    def _evaluate_consistency(
        self,
        agent_id: str,
        time_window_days: int
    ) -> EvaluationScore:
        """Evaluate consistency across executions"""
        # Get raw metrics for variance analysis
        cutoff = datetime.now() - timedelta(days=time_window_days)

        tracker = self.tracker
        if agent_id not in tracker._metrics:
            return EvaluationScore(
                dimension="Consistency",
                score=0.8,
                weight=self.weights['consistency'],
                details="Insufficient data for consistency analysis"
            )

        metrics = [m for m in tracker._metrics[agent_id] if m.completed_at >= cutoff]

        if len(metrics) < 3:
            return EvaluationScore(
                dimension="Consistency",
                score=0.8,
                weight=self.weights['consistency'],
                details="Insufficient data for consistency analysis"
            )

        # Calculate coefficient of variation for quality scores
        quality_scores = [m.quality_score for m in metrics]
        mean = statistics.mean(quality_scores)
        stdev = statistics.stdev(quality_scores) if len(quality_scores) > 1 else 0

        cv = stdev / mean if mean > 0 else 0

        # Lower CV = more consistent = higher score
        score = max(0.0, 1.0 - cv * 2)

        if score >= 0.9:
            details = "Very consistent performance"
        elif score >= 0.7:
            details = "Moderately consistent"
        else:
            details = "Variable performance"

        return EvaluationScore(
            dimension="Consistency",
            score=score,
            weight=self.weights['consistency'],
            details=details
        )

    def _calculate_grade(self, score: float) -> str:
        """Calculate letter grade from score"""
        for grade, threshold in self.GRADE_THRESHOLDS.items():
            if score >= threshold:
                return grade
        return 'F'

    def _identify_strengths(self, scores: List[EvaluationScore]) -> List[str]:
        """Identify agent strengths"""
        strengths = []
        for s in scores:
            if s.score >= 0.85:
                strengths.append(f"{s.dimension}: {s.details}")
        return strengths

    def _identify_improvements(self, scores: List[EvaluationScore]) -> List[str]:
        """Identify areas for improvement"""
        improvements = []
        for s in sorted(scores, key=lambda x: x.score):
            if s.score < 0.70:
                improvements.append(f"{s.dimension}: {s.details}")
        return improvements[:3]  # Top 3 areas

    def _generate_recommendations(
        self,
        scores: List[EvaluationScore],
        summary: AgentPerformanceSummary
    ) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []

        # Find lowest scoring dimension
        lowest = min(scores, key=lambda x: x.score)

        if lowest.dimension == "Quality" and lowest.score < 0.80:
            recommendations.append("Add code review step before delivery")
            recommendations.append("Increase test coverage requirements")

        if lowest.dimension == "Contract Fulfillment" and lowest.score < 0.80:
            recommendations.append("Review contract requirements more carefully")
            recommendations.append("Add validation step for deliverables")

        if lowest.dimension == "Time Efficiency" and lowest.score < 0.60:
            recommendations.append("Consider parallel execution where possible")
            recommendations.append("Optimize for most common task types")

        if lowest.dimension == "Error Rate" and lowest.score < 0.80:
            recommendations.append("Add error handling patterns")
            recommendations.append("Implement retry logic for transient failures")

        if lowest.dimension == "Consistency" and lowest.score < 0.70:
            recommendations.append("Standardize approach across similar tasks")
            recommendations.append("Review variable performance cases")

        # Trend-based recommendations
        for s in scores:
            if s.trend == "declining":
                recommendations.append(f"Investigate declining {s.dimension.lower()}")

        return recommendations[:5]

    def evaluate_all_agents(
        self,
        time_window_days: int = 30
    ) -> List[AgentEvaluation]:
        """
        Evaluate all registered agents.

        Args:
            time_window_days: Evaluation period

        Returns:
            List of evaluations sorted by overall score
        """
        evaluations = []

        for agent in self.registry.list_agents():
            evaluation = self.evaluate_agent(agent.agent_id, time_window_days)
            if evaluation:
                evaluations.append(evaluation)

        # Sort by overall score
        evaluations.sort(key=lambda x: x.overall_score, reverse=True)

        return evaluations

    def get_best_agent_for_task_type(
        self,
        task_type: str,
        time_window_days: int = 30
    ) -> Optional[str]:
        """
        Get best performing agent for a task type.

        Args:
            task_type: Task type to check
            time_window_days: Evaluation period

        Returns:
            Best agent ID or None
        """
        # Get task type stats
        stats = self.tracker.get_task_type_stats(task_type, time_window_days)

        if not stats.get('agents'):
            return None

        # Evaluate agents that have done this task type
        best_agent = None
        best_score = 0

        for agent_id in stats['agents']:
            evaluation = self.evaluate_agent(agent_id, time_window_days)
            if evaluation and evaluation.overall_score > best_score:
                best_score = evaluation.overall_score
                best_agent = agent_id

        return best_agent

    def compare_agents(
        self,
        agent_ids: List[str],
        time_window_days: int = 30
    ) -> Dict[str, Any]:
        """
        Compare multiple agents.

        Args:
            agent_ids: Agents to compare
            time_window_days: Evaluation period

        Returns:
            Comparison dictionary
        """
        evaluations = []

        for agent_id in agent_ids:
            evaluation = self.evaluate_agent(agent_id, time_window_days)
            if evaluation:
                evaluations.append(evaluation)

        if not evaluations:
            return {'error': 'No evaluations available'}

        # Build comparison
        comparison = {
            'agents': [e.agent_name for e in evaluations],
            'overall_scores': {e.agent_name: e.overall_score for e in evaluations},
            'grades': {e.agent_name: e.grade for e in evaluations},
            'dimensions': {}
        }

        # Compare by dimension
        dimensions = set()
        for e in evaluations:
            for s in e.scores:
                dimensions.add(s.dimension)

        for dim in dimensions:
            comparison['dimensions'][dim] = {}
            for e in evaluations:
                for s in e.scores:
                    if s.dimension == dim:
                        comparison['dimensions'][dim][e.agent_name] = s.score

        # Determine winner
        winner = max(evaluations, key=lambda x: x.overall_score)
        comparison['winner'] = {
            'agent_id': winner.agent_id,
            'agent_name': winner.agent_name,
            'score': winner.overall_score,
            'grade': winner.grade
        }

        return comparison


# Global instance
_evaluator: Optional[AgentEvaluator] = None


def get_agent_evaluator() -> AgentEvaluator:
    """Get or create global evaluator instance."""
    global _evaluator
    if _evaluator is None:
        _evaluator = AgentEvaluator()
    return _evaluator


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    from dde.performance_tracker import ExecutionOutcome

    # Initialize with sample data
    registry = get_agent_registry()
    registry.initialize_default_agents()

    tracker = get_performance_tracker()

    # Add sample metrics
    for i in range(5):
        tracker.record_execution(
            execution_id=f"eval-test-{i}",
            agent_id="backend_developer",
            task_type="backend_development",
            task_complexity="moderate",
            started_at=datetime.now() - timedelta(minutes=10),
            completed_at=datetime.now(),
            outcome=ExecutionOutcome.SUCCESS,
            quality_score=0.92 + (i * 0.01),
            contract_fulfilled=True,
            files_generated=5 + i,
            error_count=0
        )

    # Evaluate
    evaluator = get_agent_evaluator()
    evaluation = evaluator.evaluate_agent("backend_developer")

    if evaluation:
        print("\n=== Agent Evaluation ===")
        print(f"Agent: {evaluation.agent_name}")
        print(f"Overall: {evaluation.overall_score:.2f} (Grade: {evaluation.grade})")
        print("\nScores:")
        for s in evaluation.scores:
            print(f"  {s.dimension}: {s.score:.2f} ({s.details})")
        print(f"\nStrengths: {evaluation.strengths}")
        print(f"Improvements: {evaluation.improvements}")
        print(f"Recommendations: {evaluation.recommendations}")
