"""
Metrics Tracker for Persona Evolution.

EPIC: MD-2556
AC-3: Evolution metrics tracked (success rate improvement over time).
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .models import EvolutionMetrics, ExecutionOutcome, Trend

logger = logging.getLogger(__name__)


class MetricsTracker:
    """
    Tracks evolution metrics for personas.

    AC-3: Evolution metrics tracked (success rate improvement over time).
    """

    def __init__(self, weekly_window_weeks: int = 12):
        """
        Initialize the metrics tracker.

        Args:
            weekly_window_weeks: Number of weeks to keep in weekly metrics
        """
        self._metrics: Dict[str, EvolutionMetrics] = {}
        self._weekly_window = weekly_window_weeks

        logger.info(f"MetricsTracker initialized with {weekly_window_weeks} week window")

    def get_metrics(self, persona_id: str) -> EvolutionMetrics:
        """
        Get or create metrics for a persona.

        Args:
            persona_id: Persona ID

        Returns:
            Evolution metrics for the persona
        """
        if persona_id not in self._metrics:
            self._metrics[persona_id] = EvolutionMetrics(persona_id=persona_id)
            logger.info(f"Created new metrics for {persona_id}")

        return self._metrics[persona_id]

    def record_outcome(self, outcome: ExecutionOutcome) -> EvolutionMetrics:
        """
        Record an execution outcome in metrics.

        Args:
            outcome: The execution outcome

        Returns:
            Updated metrics
        """
        metrics = self.get_metrics(outcome.persona_id)
        metrics.record_execution(outcome.success, outcome.quality_score)

        logger.debug(
            f"Recorded outcome for {outcome.persona_id}: "
            f"success_rate={metrics.success_rate:.2%}, "
            f"avg_quality={metrics.average_quality_score:.1f}"
        )

        return metrics

    def record_evolution(self, persona_id: str) -> EvolutionMetrics:
        """
        Record an evolution event.

        Args:
            persona_id: Persona that evolved

        Returns:
            Updated metrics
        """
        metrics = self.get_metrics(persona_id)
        metrics.record_evolution()

        logger.info(
            f"Recorded evolution #{metrics.evolution_count} for {persona_id}"
        )

        return metrics

    def update_weekly_metrics(self, persona_id: str) -> None:
        """
        Update weekly aggregate metrics.

        Should be called periodically (e.g., weekly) to aggregate data.

        Args:
            persona_id: Persona to update
        """
        metrics = self.get_metrics(persona_id)

        # Add current success rate to weekly history
        metrics.weekly_success_rates.append(metrics.success_rate)
        metrics.weekly_quality_scores.append(metrics.average_quality_score)

        # Trim to window size
        if len(metrics.weekly_success_rates) > self._weekly_window:
            metrics.weekly_success_rates = metrics.weekly_success_rates[-self._weekly_window:]
            metrics.weekly_quality_scores = metrics.weekly_quality_scores[-self._weekly_window:]

        logger.debug(f"Updated weekly metrics for {persona_id}")

    def get_success_rate_trend(self, persona_id: str) -> Trend:
        """Get success rate trend for a persona."""
        metrics = self.get_metrics(persona_id)
        return metrics.success_rate_trend

    def get_quality_trend(self, persona_id: str) -> Trend:
        """Get quality score trend for a persona."""
        metrics = self.get_metrics(persona_id)
        return metrics.quality_trend

    def get_improvement_summary(self, persona_id: str) -> Dict[str, Any]:
        """
        Get improvement summary for a persona.

        Args:
            persona_id: Persona ID

        Returns:
            Summary of improvements
        """
        metrics = self.get_metrics(persona_id)

        # Calculate improvements
        success_improvement = 0.0
        quality_improvement = 0.0

        if len(metrics.weekly_success_rates) >= 4:
            recent = sum(metrics.weekly_success_rates[-2:]) / 2
            older = sum(metrics.weekly_success_rates[:2]) / 2
            success_improvement = recent - older

        if len(metrics.weekly_quality_scores) >= 4:
            recent = sum(metrics.weekly_quality_scores[-2:]) / 2
            older = sum(metrics.weekly_quality_scores[:2]) / 2
            quality_improvement = recent - older

        return {
            "persona_id": persona_id,
            "total_executions": metrics.total_executions,
            "current_success_rate": metrics.success_rate,
            "success_rate_trend": metrics.success_rate_trend.value,
            "success_improvement": success_improvement,
            "current_quality": metrics.average_quality_score,
            "quality_trend": metrics.quality_trend.value,
            "quality_improvement": quality_improvement,
            "evolution_count": metrics.evolution_count,
            "is_improving": (
                metrics.success_rate_trend == Trend.IMPROVING
                or metrics.quality_trend == Trend.IMPROVING
            ),
        }

    def compare_personas(
        self,
        persona_ids: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Compare metrics across multiple personas.

        Args:
            persona_ids: List of persona IDs to compare

        Returns:
            List of comparison summaries, sorted by overall performance
        """
        comparisons = []

        for persona_id in persona_ids:
            metrics = self.get_metrics(persona_id)
            comparisons.append({
                "persona_id": persona_id,
                "success_rate": metrics.success_rate,
                "quality_score": metrics.average_quality_score,
                "executions": metrics.total_executions,
                "evolutions": metrics.evolution_count,
                "overall_score": (metrics.success_rate * 50) + (metrics.average_quality_score * 0.5),
            })

        # Sort by overall score
        comparisons.sort(key=lambda c: c["overall_score"], reverse=True)

        return comparisons

    def get_top_performers(
        self,
        metric: str = "success_rate",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Get top performing personas by a metric.

        Args:
            metric: Metric to sort by (success_rate, quality_score, evolutions)
            limit: Maximum results

        Returns:
            List of top performers
        """
        results = []

        for persona_id, metrics in self._metrics.items():
            if metrics.total_executions == 0:
                continue

            value = getattr(metrics, metric, 0)
            if metric == "success_rate":
                value = metrics.success_rate
            elif metric == "quality_score":
                value = metrics.average_quality_score
            elif metric == "evolutions":
                value = metrics.evolution_count

            results.append({
                "persona_id": persona_id,
                "value": value,
                "executions": metrics.total_executions,
            })

        results.sort(key=lambda r: r["value"], reverse=True)

        return results[:limit]

    def get_needs_improvement(
        self,
        success_threshold: float = 0.8,
        quality_threshold: float = 70.0,
    ) -> List[Dict[str, Any]]:
        """
        Get personas that need improvement.

        Args:
            success_threshold: Minimum success rate
            quality_threshold: Minimum quality score

        Returns:
            List of personas needing improvement
        """
        results = []

        for persona_id, metrics in self._metrics.items():
            if metrics.total_executions < 10:  # Skip low sample sizes
                continue

            issues = []
            if metrics.success_rate < success_threshold:
                issues.append(f"success_rate={metrics.success_rate:.1%}")
            if metrics.average_quality_score < quality_threshold:
                issues.append(f"quality={metrics.average_quality_score:.1f}")
            if metrics.success_rate_trend == Trend.DECLINING:
                issues.append("declining_success")
            if metrics.quality_trend == Trend.DECLINING:
                issues.append("declining_quality")

            if issues:
                results.append({
                    "persona_id": persona_id,
                    "issues": issues,
                    "success_rate": metrics.success_rate,
                    "quality_score": metrics.average_quality_score,
                    "executions": metrics.total_executions,
                })

        return results

    def export(self, persona_id: str) -> Dict[str, Any]:
        """Export metrics as dictionary."""
        metrics = self.get_metrics(persona_id)
        return metrics.to_dict()

    def export_all(self) -> Dict[str, Dict[str, Any]]:
        """Export all metrics."""
        return {
            persona_id: metrics.to_dict()
            for persona_id, metrics in self._metrics.items()
        }

    def clear(self, persona_id: Optional[str] = None) -> int:
        """Clear metrics."""
        if persona_id:
            if persona_id in self._metrics:
                del self._metrics[persona_id]
                return 1
            return 0
        else:
            count = len(self._metrics)
            self._metrics = {}
            return count
