"""
Adaptive Scorer (MD-2157)

EU AI Act Compliance - Article 10

Replaces hard thresholds with adaptive scoring that
adjusts based on context and historical performance.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from .models import AdaptiveThreshold

logger = logging.getLogger(__name__)


class AdaptiveScorer:
    """
    Adaptive scoring system.

    Replaces hard-coded thresholds with adaptive thresholds
    that adjust based on historical performance and context.
    """

    # Default thresholds to replace
    DEFAULT_THRESHOLDS = {
        'grade_a': {
            'name': 'Grade A Threshold',
            'description': 'Threshold for A grade',
            'base_value': 0.90,
            'min_value': 0.85,
            'max_value': 0.95
        },
        'grade_b': {
            'name': 'Grade B Threshold',
            'description': 'Threshold for B grade',
            'base_value': 0.80,
            'min_value': 0.75,
            'max_value': 0.85
        },
        'grade_c': {
            'name': 'Grade C Threshold',
            'description': 'Threshold for C grade',
            'base_value': 0.70,
            'min_value': 0.65,
            'max_value': 0.75
        },
        'pass_threshold': {
            'name': 'Pass Threshold',
            'description': 'Minimum threshold to pass',
            'base_value': 0.60,
            'min_value': 0.50,
            'max_value': 0.70
        },
        'deployment_approved': {
            'name': 'Deployment Approved Threshold',
            'description': 'Threshold for auto-approved deployment',
            'base_value': 0.80,
            'min_value': 0.75,
            'max_value': 0.90
        },
        'quality_minimum': {
            'name': 'Quality Minimum Threshold',
            'description': 'Minimum acceptable quality score',
            'base_value': 0.70,
            'min_value': 0.60,
            'max_value': 0.80
        }
    }

    def __init__(
        self,
        adaptation_rate: float = 0.1,
        sensitivity: float = 0.5,
        sample_window: int = 100
    ):
        """
        Initialize the adaptive scorer.

        Args:
            adaptation_rate: Rate at which thresholds adapt (0-1)
            sensitivity: Sensitivity to performance changes (0-1)
            sample_window: Number of samples to consider
        """
        self.adaptation_rate = adaptation_rate
        self.sensitivity = sensitivity
        self.sample_window = sample_window

        # Initialize thresholds
        self._thresholds: Dict[str, AdaptiveThreshold] = {}
        self._initialize_thresholds()

        # Performance history
        self._performance_history: List[Dict[str, Any]] = []

        logger.info("AdaptiveScorer initialized")

    def _initialize_thresholds(self):
        """Initialize default adaptive thresholds."""
        for threshold_id, config in self.DEFAULT_THRESHOLDS.items():
            self._thresholds[threshold_id] = AdaptiveThreshold(
                threshold_id=threshold_id,
                name=config['name'],
                description=config['description'],
                base_value=config['base_value'],
                min_value=config['min_value'],
                max_value=config['max_value'],
                current_value=config['base_value'],
                adaptation_rate=self.adaptation_rate,
                sample_window=self.sample_window,
                sensitivity=self.sensitivity
            )

    def get_threshold(self, threshold_id: str) -> Optional[AdaptiveThreshold]:
        """
        Get an adaptive threshold.

        Args:
            threshold_id: ID of the threshold

        Returns:
            AdaptiveThreshold or None
        """
        return self._thresholds.get(threshold_id)

    def get_threshold_value(self, threshold_id: str) -> float:
        """
        Get the current value of a threshold.

        Args:
            threshold_id: ID of the threshold

        Returns:
            Current threshold value (or base value if not found)
        """
        threshold = self._thresholds.get(threshold_id)
        if threshold:
            return threshold.current_value
        return self.DEFAULT_THRESHOLDS.get(threshold_id, {}).get('base_value', 0.5)

    def evaluate_with_adaptive_threshold(
        self,
        threshold_id: str,
        value: float,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a value against an adaptive threshold.

        Args:
            threshold_id: ID of the threshold to use
            value: Value to evaluate
            context: Optional context for adaptation

        Returns:
            Evaluation result with decision and details
        """
        threshold = self._thresholds.get(threshold_id)
        if not threshold:
            logger.warning(f"Unknown threshold: {threshold_id}")
            return {
                'passed': value >= 0.5,
                'value': value,
                'threshold': 0.5,
                'margin': value - 0.5,
                'adaptive': False
            }

        current_threshold = threshold.current_value
        passed = value >= current_threshold
        margin = value - current_threshold

        result = {
            'passed': passed,
            'value': value,
            'threshold': current_threshold,
            'base_threshold': threshold.base_value,
            'margin': margin,
            'adaptive': True,
            'threshold_id': threshold_id
        }

        # Record performance for adaptation
        self._record_performance(threshold_id, value, passed, context)

        return result

    def _record_performance(
        self,
        threshold_id: str,
        value: float,
        passed: bool,
        context: Optional[Dict[str, Any]] = None
    ):
        """Record performance for future adaptation."""
        self._performance_history.append({
            'threshold_id': threshold_id,
            'value': value,
            'passed': passed,
            'context': context or {},
            'timestamp': datetime.now().isoformat()
        })

        # Trim history
        if len(self._performance_history) > self.sample_window * 2:
            self._performance_history = self._performance_history[-self.sample_window:]

    def adapt_thresholds(
        self,
        performance_metrics: Dict[str, float],
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Adapt thresholds based on recent performance.

        Args:
            performance_metrics: Performance metrics by threshold ID
            context: Optional context factors
        """
        for threshold_id, performance_delta in performance_metrics.items():
            threshold = self._thresholds.get(threshold_id)
            if threshold:
                old_value = threshold.current_value
                new_value = threshold.adapt(performance_delta, context)

                if abs(new_value - old_value) > 0.01:
                    logger.info(f"Adapted threshold {threshold_id}: "
                               f"{old_value:.3f} -> {new_value:.3f}")

    def get_grade(
        self,
        score: float,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get grade using adaptive thresholds.

        Args:
            score: Score to grade
            context: Optional context

        Returns:
            Grade string (A, B, C, D, F)
        """
        # Check each grade threshold
        if score >= self.get_threshold_value('grade_a'):
            return 'A'
        elif score >= self.get_threshold_value('grade_b'):
            return 'B'
        elif score >= self.get_threshold_value('grade_c'):
            return 'C'
        elif score >= self.get_threshold_value('pass_threshold'):
            return 'D'
        else:
            return 'F'

    def get_deployment_decision(
        self,
        score: float,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Get deployment decision using adaptive thresholds.

        Args:
            score: Quality score
            context: Optional context

        Returns:
            Decision string (approved, conditional, blocked)
        """
        approved_threshold = self.get_threshold_value('deployment_approved')
        pass_threshold = self.get_threshold_value('pass_threshold')

        if score >= approved_threshold:
            return 'approved'
        elif score >= pass_threshold:
            return 'conditional'
        else:
            return 'blocked'

    def set_threshold(
        self,
        threshold_id: str,
        value: float,
        reason: str = "manual_override"
    ):
        """
        Manually set a threshold value.

        Args:
            threshold_id: ID of the threshold
            value: New value
            reason: Reason for the change
        """
        threshold = self._thresholds.get(threshold_id)
        if threshold:
            old_value = threshold.current_value
            threshold.current_value = max(threshold.min_value, min(threshold.max_value, value))
            threshold.adjustment_history.append({
                'timestamp': datetime.now().isoformat(),
                'old_value': old_value,
                'new_value': threshold.current_value,
                'reason': reason,
                'manual': True
            })
            logger.info(f"Manually set threshold {threshold_id}: "
                       f"{old_value:.3f} -> {threshold.current_value:.3f} ({reason})")

    def reset_threshold(self, threshold_id: str):
        """
        Reset a threshold to its base value.

        Args:
            threshold_id: ID of the threshold
        """
        threshold = self._thresholds.get(threshold_id)
        if threshold:
            threshold.current_value = threshold.base_value
            threshold.adjustment_history.clear()
            logger.info(f"Reset threshold {threshold_id} to {threshold.base_value:.3f}")

    def reset_all_thresholds(self):
        """Reset all thresholds to base values."""
        for threshold_id in self._thresholds:
            self.reset_threshold(threshold_id)

    def add_context_weight(
        self,
        threshold_id: str,
        context_key: str,
        weight: float
    ):
        """
        Add a context weight to a threshold.

        Args:
            threshold_id: ID of the threshold
            context_key: Context key to weight
            weight: Weight value
        """
        threshold = self._thresholds.get(threshold_id)
        if threshold:
            threshold.context_weights[context_key] = weight

    def get_all_thresholds(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all thresholds with their current values.

        Returns:
            Dictionary of threshold configurations
        """
        return {
            threshold_id: threshold.to_dict()
            for threshold_id, threshold in self._thresholds.items()
        }

    def get_adaptation_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about threshold adaptations.

        Returns:
            Statistics dictionary
        """
        total_adaptations = 0
        avg_adjustments = {}

        for threshold_id, threshold in self._thresholds.items():
            history = threshold.adjustment_history
            total_adaptations += len(history)

            if history:
                adjustments = [h['new_value'] - h['old_value'] for h in history]
                avg_adjustments[threshold_id] = sum(adjustments) / len(adjustments)

        return {
            'total_adaptations': total_adaptations,
            'thresholds_adapted': len([t for t in self._thresholds.values() if t.adjustment_history]),
            'avg_adjustments': avg_adjustments,
            'performance_samples': len(self._performance_history)
        }


# Global instance
_adaptive_scorer: Optional[AdaptiveScorer] = None


def get_adaptive_scorer() -> AdaptiveScorer:
    """Get or create global adaptive scorer instance."""
    global _adaptive_scorer
    if _adaptive_scorer is None:
        _adaptive_scorer = AdaptiveScorer()
    return _adaptive_scorer
