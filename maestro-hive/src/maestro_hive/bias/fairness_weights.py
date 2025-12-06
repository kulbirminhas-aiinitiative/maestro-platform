"""
Fairness Weight Calculator (MD-2157)

EU AI Act Compliance - Article 10

Computes fairness-adjusted weights for scoring algorithms
to counteract identified biases.
"""

import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict

from .models import (
    FairnessWeight,
    BiasVectorType
)

logger = logging.getLogger(__name__)


class FairnessWeightCalculator:
    """
    Calculator for fairness-adjusted weights.

    Adjusts scoring weights to counteract historical performance
    bias and ensure fair opportunity distribution.
    """

    # Default configuration
    DEFAULT_CONFIG = {
        'history_lookback_days': 30,
        'min_samples_for_adjustment': 5,
        'max_adjustment_factor': 0.3,
        'smoothing_factor': 0.1,
        'assignment_threshold': 0.7,  # Above this triggers adjustment
        'quality_variance_threshold': 0.1
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the fairness weight calculator.

        Args:
            config: Optional configuration overrides
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}

        # Active weight adjustments
        self._active_weights: Dict[str, FairnessWeight] = {}

        # Historical data
        self._assignment_counts: Dict[str, int] = defaultdict(int)
        self._quality_scores: Dict[str, List[float]] = defaultdict(list)
        self._last_calculated: Optional[datetime] = None

        logger.info("FairnessWeightCalculator initialized")

    def calculate_fairness_weight(
        self,
        agent_id: str,
        factor_name: str,
        original_weight: float,
        assignment_history: Optional[List[Dict[str, Any]]] = None,
        quality_history: Optional[List[float]] = None
    ) -> FairnessWeight:
        """
        Calculate fairness-adjusted weight for an agent.

        Args:
            agent_id: ID of the agent
            factor_name: Name of the factor being weighted
            original_weight: Original weight value
            assignment_history: Historical assignment data
            quality_history: Historical quality scores

        Returns:
            FairnessWeight with adjusted value
        """
        # Update historical data
        if assignment_history:
            self._update_assignment_history(agent_id, assignment_history)
        if quality_history:
            self._update_quality_history(agent_id, quality_history)

        # Calculate adjustment
        adjustment = self._calculate_adjustment(agent_id, factor_name)
        adjusted_weight = original_weight * (1 + adjustment)

        # Clamp to valid range
        adjusted_weight = max(0.0, min(1.0, adjusted_weight))

        # Determine adjustment reason
        reason = self._get_adjustment_reason(agent_id, adjustment)

        # Create weight record
        weight = FairnessWeight(
            agent_id=agent_id,
            factor_name=factor_name,
            original_weight=original_weight,
            adjusted_weight=adjusted_weight,
            adjustment_reason=reason,
            adjustment_source=self._get_adjustment_source(agent_id)
        )

        # Store active weight
        key = f"{agent_id}:{factor_name}"
        self._active_weights[key] = weight

        logger.debug(f"Fairness weight for {agent_id}/{factor_name}: "
                    f"{original_weight:.3f} -> {adjusted_weight:.3f} ({reason})")

        return weight

    def _update_assignment_history(
        self,
        agent_id: str,
        assignment_history: List[Dict[str, Any]]
    ):
        """Update assignment history for an agent."""
        # Count recent assignments
        cutoff = datetime.now() - timedelta(days=self.config['history_lookback_days'])
        recent_count = 0

        for assignment in assignment_history:
            timestamp = assignment.get('timestamp')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)
            if timestamp and timestamp >= cutoff:
                recent_count += 1

        self._assignment_counts[agent_id] = recent_count

    def _update_quality_history(
        self,
        agent_id: str,
        quality_history: List[float]
    ):
        """Update quality history for an agent."""
        # Keep recent quality scores
        max_samples = self.config.get('max_quality_samples', 100)
        self._quality_scores[agent_id] = quality_history[-max_samples:]

    def _calculate_adjustment(
        self,
        agent_id: str,
        factor_name: str
    ) -> float:
        """
        Calculate the adjustment factor.

        Returns a value between -max_adjustment and +max_adjustment.
        Negative = reduce weight (agent is over-represented)
        Positive = increase weight (agent is under-represented)
        """
        max_adj = self.config['max_adjustment_factor']
        adjustment = 0.0

        # Factor 1: Assignment frequency adjustment
        if self._assignment_counts:
            total_assignments = sum(self._assignment_counts.values())
            if total_assignments > 0:
                agent_assignments = self._assignment_counts.get(agent_id, 0)
                expected_share = 1.0 / len(self._assignment_counts)
                actual_share = agent_assignments / total_assignments

                if actual_share > self.config['assignment_threshold']:
                    # Over-assigned - reduce weight
                    over_factor = (actual_share - expected_share) / expected_share
                    adjustment -= min(max_adj, over_factor * 0.5)
                elif actual_share < expected_share * 0.5:
                    # Under-assigned - increase weight
                    under_factor = (expected_share - actual_share) / expected_share
                    adjustment += min(max_adj, under_factor * 0.3)

        # Factor 2: Quality variance adjustment
        quality_scores = self._quality_scores.get(agent_id, [])
        if len(quality_scores) >= self.config['min_samples_for_adjustment']:
            try:
                variance = statistics.variance(quality_scores)
                if variance > self.config['quality_variance_threshold']:
                    # High variance - slight penalty
                    adjustment -= min(0.1, variance * 0.2)
            except statistics.StatisticsError:
                pass

        # Apply smoothing
        smoothing = self.config['smoothing_factor']
        adjustment = adjustment * smoothing

        return max(-max_adj, min(max_adj, adjustment))

    def _get_adjustment_reason(self, agent_id: str, adjustment: float) -> str:
        """Get human-readable reason for adjustment."""
        if abs(adjustment) < 0.01:
            return "No significant adjustment needed"

        if adjustment < 0:
            agent_assignments = self._assignment_counts.get(agent_id, 0)
            total = sum(self._assignment_counts.values()) or 1
            share = agent_assignments / total
            return f"Reducing weight due to over-assignment ({share:.1%} of tasks)"
        else:
            return "Increasing weight to improve assignment fairness"

    def _get_adjustment_source(self, agent_id: str) -> BiasVectorType:
        """Determine the primary bias source being addressed."""
        agent_assignments = self._assignment_counts.get(agent_id, 0)
        total = sum(self._assignment_counts.values()) or 1
        share = agent_assignments / total

        if share > self.config['assignment_threshold']:
            return BiasVectorType.HISTORICAL_PERFORMANCE

        quality_scores = self._quality_scores.get(agent_id, [])
        if quality_scores:
            try:
                variance = statistics.variance(quality_scores)
                if variance > self.config['quality_variance_threshold']:
                    return BiasVectorType.HARD_THRESHOLD
            except statistics.StatisticsError:
                pass

        return BiasVectorType.DEFAULT_STRATEGY

    def get_adjusted_weights(
        self,
        agent_id: str,
        weights: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Get all adjusted weights for an agent.

        Args:
            agent_id: ID of the agent
            weights: Original weights dictionary

        Returns:
            Dictionary of adjusted weights
        """
        adjusted = {}
        for factor_name, original_weight in weights.items():
            fw = self.calculate_fairness_weight(
                agent_id=agent_id,
                factor_name=factor_name,
                original_weight=original_weight
            )
            adjusted[factor_name] = fw.adjusted_weight

        return adjusted

    def get_active_adjustments(
        self,
        agent_id: Optional[str] = None
    ) -> List[FairnessWeight]:
        """
        Get active weight adjustments.

        Args:
            agent_id: Filter by agent ID (optional)

        Returns:
            List of active FairnessWeight records
        """
        weights = list(self._active_weights.values())

        if agent_id:
            weights = [w for w in weights if w.agent_id == agent_id]

        # Filter to only active weights
        weights = [w for w in weights if w.is_active]

        return weights

    def get_assignment_distribution(self) -> Dict[str, float]:
        """
        Get current assignment distribution across agents.

        Returns:
            Dictionary of agent_id -> assignment share
        """
        total = sum(self._assignment_counts.values())
        if total == 0:
            return {}

        return {
            agent_id: count / total
            for agent_id, count in self._assignment_counts.items()
        }

    def get_fairness_score(self) -> float:
        """
        Calculate overall fairness score.

        Returns:
            Score between 0 (unfair) and 1 (fair)
        """
        distribution = self.get_assignment_distribution()
        if not distribution:
            return 1.0

        # Calculate Gini coefficient (0 = perfect equality, 1 = maximum inequality)
        values = sorted(distribution.values())
        n = len(values)
        if n == 0:
            return 1.0

        # Calculate Gini
        cumulative = 0
        total = sum(values)
        if total == 0:
            return 1.0

        for i, value in enumerate(values):
            cumulative += (2 * (i + 1) - n - 1) * value

        gini = cumulative / (n * total)

        # Convert to fairness score (1 - Gini)
        return 1.0 - abs(gini)

    def reset_history(self, agent_id: Optional[str] = None):
        """
        Reset historical data.

        Args:
            agent_id: Reset only for this agent (or all if None)
        """
        if agent_id:
            self._assignment_counts.pop(agent_id, None)
            self._quality_scores.pop(agent_id, None)
            keys_to_remove = [k for k in self._active_weights if k.startswith(f"{agent_id}:")]
            for key in keys_to_remove:
                del self._active_weights[key]
        else:
            self._assignment_counts.clear()
            self._quality_scores.clear()
            self._active_weights.clear()

        logger.info(f"Reset fairness history for {agent_id or 'all agents'}")


# Global instance
_fairness_calculator: Optional[FairnessWeightCalculator] = None


def get_fairness_calculator() -> FairnessWeightCalculator:
    """Get or create global fairness calculator instance."""
    global _fairness_calculator
    if _fairness_calculator is None:
        _fairness_calculator = FairnessWeightCalculator()
    return _fairness_calculator
