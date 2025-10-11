"""
Performance Degradation Detection

Detects when model performance degrades beyond acceptable thresholds.
"""

from typing import Dict, List, Optional
from datetime import datetime
import numpy as np

from ..models.metrics_models import (
    MetricType,
    MetricThreshold,
    MetricComparisonResult,
    MetricSummary
)
from ..models.alert_models import AlertSeverity
from .metrics_collector import MetricsCollector


class DegradationDetector:
    """
    Detect performance degradation in production models

    Example:
        >>> detector = DegradationDetector(collector)
        >>> result = detector.check_degradation("my_model", "v1.0", MetricType.ACCURACY)
        >>> if result.is_degraded:
        >>>     print(f"Alert! Performance degraded by {result.percentage_change}%")
    """

    def __init__(
        self,
        metrics_collector: MetricsCollector,
        default_degradation_threshold: float = 5.0
    ):
        """
        Initialize degradation detector

        Args:
            metrics_collector: MetricsCollector instance
            default_degradation_threshold: Default max degradation % allowed
        """
        self.collector = metrics_collector
        self.default_degradation_threshold = default_degradation_threshold

        # Metric-specific thresholds
        self.thresholds: Dict[str, MetricThreshold] = {}

    def set_threshold(
        self,
        model_name: str,
        metric_type: MetricType,
        threshold: MetricThreshold
    ) -> None:
        """
        Set custom threshold for a model + metric combination

        Args:
            model_name: Model identifier
            metric_type: Type of metric
            threshold: MetricThreshold configuration
        """
        key = f"{model_name}:{metric_type.value}"
        self.thresholds[key] = threshold

    def get_threshold(
        self,
        model_name: str,
        metric_type: MetricType
    ) -> Optional[MetricThreshold]:
        """Get threshold configuration for a model + metric"""
        key = f"{model_name}:{metric_type.value}"
        return self.thresholds.get(key)

    def check_degradation(
        self,
        model_name: str,
        model_version: str,
        metric_type: MetricType,
        current_value: Optional[float] = None,
        baseline_window_hours: int = 24,
        comparison_window_hours: int = 1
    ) -> MetricComparisonResult:
        """
        Check if a metric has degraded

        Args:
            model_name: Model identifier
            model_version: Model version
            metric_type: Type of metric to check
            current_value: Optional current value (if None, fetches latest)
            baseline_window_hours: Hours to look back for baseline
            comparison_window_hours: Hours to look back for current value

        Returns:
            MetricComparisonResult with degradation analysis
        """
        # Get threshold configuration
        threshold_config = self.get_threshold(model_name, metric_type)

        # Determine if higher is better
        higher_is_better = metric_type not in [
            MetricType.MAE, MetricType.MSE, MetricType.RMSE,
            MetricType.MAPE, MetricType.ERROR_RATE, MetricType.LATENCY
        ]

        # Get baseline metrics
        baseline_metrics = self.collector.get_metric_history(
            model_name=model_name,
            model_version=model_version,
            metric_type=metric_type,
            hours=baseline_window_hours
        )

        if not baseline_metrics:
            return MetricComparisonResult(
                metric_type=metric_type,
                current_value=current_value or 0.0,
                baseline_value=0.0,
                absolute_change=0.0,
                percentage_change=0.0,
                is_degraded=False,
                severity="none",
                recommendation="No baseline data available for comparison"
            )

        # Calculate baseline value
        baseline_values = [m.metric_value for m in baseline_metrics]
        baseline_value = float(np.mean(baseline_values))

        # Get current value
        if current_value is None:
            current_metrics = self.collector.get_metric_history(
                model_name=model_name,
                model_version=model_version,
                metric_type=metric_type,
                hours=comparison_window_hours
            )

            if not current_metrics:
                return MetricComparisonResult(
                    metric_type=metric_type,
                    current_value=0.0,
                    baseline_value=baseline_value,
                    absolute_change=0.0,
                    percentage_change=0.0,
                    is_degraded=False,
                    severity="none",
                    recommendation="No current metrics available"
                )

            current_value = float(np.mean([m.metric_value for m in current_metrics]))

        # Calculate change
        absolute_change = current_value - baseline_value
        percentage_change = ((current_value - baseline_value) / baseline_value * 100) if baseline_value != 0 else 0

        # Determine if degraded
        is_degraded = False
        severity = "none"

        # Check against threshold configuration
        if threshold_config:
            if threshold_config.min_acceptable is not None:
                is_degraded = current_value < threshold_config.min_acceptable
            elif threshold_config.max_acceptable is not None:
                is_degraded = current_value > threshold_config.max_acceptable
            elif threshold_config.max_degradation_percentage is not None:
                degradation_threshold = threshold_config.max_degradation_percentage
                if higher_is_better:
                    is_degraded = percentage_change < -degradation_threshold
                else:
                    is_degraded = percentage_change > degradation_threshold
        else:
            # Use default degradation threshold
            if higher_is_better:
                is_degraded = percentage_change < -self.default_degradation_threshold
            else:
                is_degraded = percentage_change > self.default_degradation_threshold

        # Determine severity
        if is_degraded:
            abs_change_pct = abs(percentage_change)
            if abs_change_pct > 20:
                severity = "critical"
            elif abs_change_pct > 10:
                severity = "high"
            elif abs_change_pct > 5:
                severity = "medium"
            else:
                severity = "low"

        # Generate recommendation
        recommendation = self._generate_recommendation(
            metric_type=metric_type,
            current_value=current_value,
            baseline_value=baseline_value,
            percentage_change=percentage_change,
            is_degraded=is_degraded,
            severity=severity,
            higher_is_better=higher_is_better
        )

        return MetricComparisonResult(
            metric_type=metric_type,
            current_value=current_value,
            baseline_value=baseline_value,
            absolute_change=absolute_change,
            percentage_change=percentage_change,
            is_degraded=is_degraded,
            severity=severity,
            recommendation=recommendation
        )

    def check_all_metrics(
        self,
        model_name: str,
        model_version: str,
        baseline_window_hours: int = 24
    ) -> List[MetricComparisonResult]:
        """
        Check degradation for all metrics of a model

        Args:
            model_name: Model identifier
            model_version: Model version
            baseline_window_hours: Hours to look back for baseline

        Returns:
            List of MetricComparisonResult for all metrics
        """
        # Get performance history to discover all metric types
        history = self.collector.get_performance_history(
            model_name=model_name,
            model_version=model_version,
            hours=baseline_window_hours
        )

        results = []
        for summary in history.metric_summaries:
            result = self.check_degradation(
                model_name=model_name,
                model_version=model_version,
                metric_type=summary.metric_type,
                baseline_window_hours=baseline_window_hours
            )
            results.append(result)

        return results

    def _generate_recommendation(
        self,
        metric_type: MetricType,
        current_value: float,
        baseline_value: float,
        percentage_change: float,
        is_degraded: bool,
        severity: str,
        higher_is_better: bool
    ) -> str:
        """Generate actionable recommendation based on degradation analysis"""
        if not is_degraded:
            if abs(percentage_change) < 1:
                return "✅ Performance is stable within expected range"
            else:
                direction = "improved" if (higher_is_better and percentage_change > 0) or (not higher_is_better and percentage_change < 0) else "changed"
                return f"✅ Performance {direction} by {abs(percentage_change):.1f}% but within acceptable range"

        # Degraded - provide specific recommendations
        if severity == "critical":
            return (
                f"🚨 CRITICAL: {metric_type.value} degraded by {abs(percentage_change):.1f}% "
                f"({baseline_value:.4f} → {current_value:.4f}). "
                f"Immediate action required:\n"
                f"  1. Check for data quality issues\n"
                f"  2. Verify model serving infrastructure\n"
                f"  3. Review recent data drift\n"
                f"  4. Consider rolling back to previous version\n"
                f"  5. Prepare for model retraining"
            )
        elif severity == "high":
            return (
                f"⚠️ HIGH: {metric_type.value} degraded by {abs(percentage_change):.1f}% "
                f"({baseline_value:.4f} → {current_value:.4f}). "
                f"Recommended actions:\n"
                f"  1. Investigate data pipeline for issues\n"
                f"  2. Check for distribution shifts\n"
                f"  3. Review model performance on recent data\n"
                f"  4. Plan model retraining if trend continues"
            )
        elif severity == "medium":
            return (
                f"⚡ MEDIUM: {metric_type.value} degraded by {abs(percentage_change):.1f}% "
                f"({baseline_value:.4f} → {current_value:.4f}). "
                f"Monitor closely and investigate if degradation continues"
            )
        else:
            return (
                f"ℹ️ LOW: {metric_type.value} degraded by {abs(percentage_change):.1f}% "
                f"({baseline_value:.4f} → {current_value:.4f}). "
                f"Continue monitoring"
            )


class DegradationAlert(BaseModel):
    """Alert triggered by performance degradation"""
    model_name: str
    model_version: str
    comparison_results: List[MetricComparisonResult]

    degraded_metrics_count: int
    total_metrics_checked: int

    severity: AlertSeverity
    message: str
    recommendations: List[str]

    timestamp: datetime = Field(default_factory=datetime.utcnow)


from pydantic import BaseModel, Field
