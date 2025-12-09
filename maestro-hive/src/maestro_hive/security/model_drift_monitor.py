"""
Model Drift Monitoring for AI Systems
EU AI Act Article 15 Compliance - Robustness

Tracks model performance and detects drift over time.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import statistics


class DriftType(Enum):
    """Types of model drift."""
    DATA_DRIFT = "data_drift"
    CONCEPT_DRIFT = "concept_drift"
    PREDICTION_DRIFT = "prediction_drift"
    PERFORMANCE_DRIFT = "performance_drift"
    FEATURE_DRIFT = "feature_drift"
    LABEL_DRIFT = "label_drift"


class DriftSeverity(Enum):
    """Severity of detected drift."""
    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"
    SIGNIFICANT = "significant"
    CRITICAL = "critical"


@dataclass
class PerformanceMetric:
    """A single performance metric observation."""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class DriftAlert:
    """Alert for detected drift."""
    drift_type: DriftType
    severity: DriftSeverity
    metric_name: str
    baseline_value: float
    current_value: float
    deviation_percentage: float
    description: str
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "drift_type": self.drift_type.value,
            "severity": self.severity.value,
            "metric_name": self.metric_name,
            "baseline_value": self.baseline_value,
            "current_value": self.current_value,
            "deviation_percentage": self.deviation_percentage,
            "description": self.description,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class BaselineConfig:
    """Configuration for metric baselines."""
    metric_name: str
    baseline_value: float
    tolerance_percentage: float = 10.0
    window_size: int = 100
    min_samples: int = 10


class ModelDriftMonitor:
    """
    Monitors AI model performance and detects drift.

    Provides:
    - Performance metric tracking
    - Statistical drift detection
    - Baseline comparison
    - Alert generation
    - Trend analysis
    """

    def __init__(
        self,
        model_id: str,
        version: str = "1.0.0",
        window_size: int = 1000,
        alert_threshold: float = 0.1,
    ):
        self.model_id = model_id
        self.version = version
        self.window_size = window_size
        self.alert_threshold = alert_threshold

        self._metrics_history: Dict[str, List[PerformanceMetric]] = {}
        self._baselines: Dict[str, BaselineConfig] = {}
        self._alerts: List[DriftAlert] = []
        self._drift_scores: Dict[str, List[Tuple[datetime, float]]] = {}

    def set_baseline(
        self,
        metric_name: str,
        baseline_value: float,
        tolerance_percentage: float = 10.0,
    ) -> None:
        """Set baseline for a metric."""
        self._baselines[metric_name] = BaselineConfig(
            metric_name=metric_name,
            baseline_value=baseline_value,
            tolerance_percentage=tolerance_percentage,
        )

    def record_metric(
        self,
        metric_name: str,
        value: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[DriftAlert]:
        """Record a performance metric and check for drift."""
        metric = PerformanceMetric(
            name=metric_name,
            value=value,
            metadata=metadata or {},
        )

        if metric_name not in self._metrics_history:
            self._metrics_history[metric_name] = []

        self._metrics_history[metric_name].append(metric)

        # Keep only window_size recent values
        if len(self._metrics_history[metric_name]) > self.window_size:
            self._metrics_history[metric_name] = self._metrics_history[metric_name][-self.window_size:]

        # Check for drift
        return self._check_drift(metric_name)

    def _calculate_statistics(self, values: List[float]) -> Dict[str, float]:
        """Calculate statistics for a list of values."""
        if len(values) < 2:
            return {"mean": values[0] if values else 0, "std": 0}

        return {
            "mean": statistics.mean(values),
            "std": statistics.stdev(values),
            "median": statistics.median(values),
            "min": min(values),
            "max": max(values),
        }

    def _check_drift(self, metric_name: str) -> Optional[DriftAlert]:
        """Check for drift in a metric."""
        if metric_name not in self._metrics_history:
            return None

        history = self._metrics_history[metric_name]
        if len(history) < 10:
            return None

        values = [m.value for m in history]
        recent_values = values[-20:] if len(values) >= 20 else values
        current_value = statistics.mean(recent_values)

        # Check against baseline if set
        if metric_name in self._baselines:
            baseline = self._baselines[metric_name]
            deviation = abs(current_value - baseline.baseline_value) / max(baseline.baseline_value, 0.001)
            deviation_pct = deviation * 100

            if deviation_pct > baseline.tolerance_percentage:
                severity = self._determine_severity(deviation_pct, baseline.tolerance_percentage)
                alert = self._create_alert(
                    drift_type=DriftType.PERFORMANCE_DRIFT,
                    severity=severity,
                    metric_name=metric_name,
                    baseline_value=baseline.baseline_value,
                    current_value=current_value,
                    deviation_pct=deviation_pct,
                )
                self._alerts.append(alert)
                return alert

        # Check for statistical drift (compare first half vs second half)
        if len(values) >= 40:
            first_half = values[:len(values)//2]
            second_half = values[len(values)//2:]

            first_stats = self._calculate_statistics(first_half)
            second_stats = self._calculate_statistics(second_half)

            mean_shift = abs(second_stats["mean"] - first_stats["mean"])
            relative_shift = mean_shift / max(first_stats["mean"], 0.001)

            if relative_shift > self.alert_threshold:
                severity = self._determine_severity(relative_shift * 100, self.alert_threshold * 100)
                alert = self._create_alert(
                    drift_type=DriftType.CONCEPT_DRIFT,
                    severity=severity,
                    metric_name=metric_name,
                    baseline_value=first_stats["mean"],
                    current_value=second_stats["mean"],
                    deviation_pct=relative_shift * 100,
                )
                self._alerts.append(alert)
                return alert

        return None

    def _determine_severity(self, deviation_pct: float, threshold: float) -> DriftSeverity:
        """Determine drift severity based on deviation."""
        ratio = deviation_pct / max(threshold, 1)

        if ratio < 1.0:
            return DriftSeverity.NONE
        elif ratio < 1.5:
            return DriftSeverity.MINOR
        elif ratio < 2.0:
            return DriftSeverity.MODERATE
        elif ratio < 3.0:
            return DriftSeverity.SIGNIFICANT
        else:
            return DriftSeverity.CRITICAL

    def _create_alert(
        self,
        drift_type: DriftType,
        severity: DriftSeverity,
        metric_name: str,
        baseline_value: float,
        current_value: float,
        deviation_pct: float,
    ) -> DriftAlert:
        """Create a drift alert."""
        recommendations = []

        if severity in (DriftSeverity.SIGNIFICANT, DriftSeverity.CRITICAL):
            recommendations.extend([
                "Investigate root cause immediately",
                "Consider model retraining",
                "Review recent data for quality issues",
            ])
        elif severity == DriftSeverity.MODERATE:
            recommendations.extend([
                "Monitor closely for continued drift",
                "Schedule model review",
            ])
        else:
            recommendations.append("Continue monitoring")

        return DriftAlert(
            drift_type=drift_type,
            severity=severity,
            metric_name=metric_name,
            baseline_value=baseline_value,
            current_value=current_value,
            deviation_percentage=deviation_pct,
            description=f"Detected {drift_type.value} in {metric_name}: "
                       f"{deviation_pct:.1f}% deviation from baseline",
            recommendations=recommendations,
        )

    def get_metric_trend(
        self,
        metric_name: str,
        window_minutes: int = 60,
    ) -> Dict[str, Any]:
        """Get trend analysis for a metric."""
        if metric_name not in self._metrics_history:
            return {"error": "Metric not found"}

        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        history = [m for m in self._metrics_history[metric_name] if m.timestamp > cutoff]

        if len(history) < 2:
            return {
                "metric_name": metric_name,
                "samples": len(history),
                "trend": "insufficient_data",
            }

        values = [m.value for m in history]
        stats = self._calculate_statistics(values)

        # Calculate trend direction
        first_quarter = values[:len(values)//4] if len(values) >= 4 else values[:1]
        last_quarter = values[-len(values)//4:] if len(values) >= 4 else values[-1:]

        first_avg = statistics.mean(first_quarter)
        last_avg = statistics.mean(last_quarter)

        if last_avg > first_avg * 1.05:
            trend = "increasing"
        elif last_avg < first_avg * 0.95:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "metric_name": metric_name,
            "window_minutes": window_minutes,
            "samples": len(history),
            "statistics": stats,
            "trend": trend,
            "trend_magnitude": (last_avg - first_avg) / max(first_avg, 0.001),
        }

    def detect_feature_drift(
        self,
        feature_name: str,
        current_distribution: Dict[str, float],
        reference_distribution: Dict[str, float],
    ) -> DriftAlert:
        """Detect drift in feature distributions."""
        # Calculate PSI (Population Stability Index)
        psi = 0.0
        all_keys = set(current_distribution.keys()) | set(reference_distribution.keys())

        for key in all_keys:
            actual = current_distribution.get(key, 0.0001)
            expected = reference_distribution.get(key, 0.0001)
            actual = max(actual, 0.0001)  # Avoid log(0)
            expected = max(expected, 0.0001)

            import math
            psi += (actual - expected) * math.log(actual / expected)

        # Determine severity based on PSI
        if psi < 0.1:
            severity = DriftSeverity.NONE
        elif psi < 0.2:
            severity = DriftSeverity.MINOR
        elif psi < 0.25:
            severity = DriftSeverity.MODERATE
        else:
            severity = DriftSeverity.SIGNIFICANT if psi < 0.5 else DriftSeverity.CRITICAL

        alert = DriftAlert(
            drift_type=DriftType.FEATURE_DRIFT,
            severity=severity,
            metric_name=f"feature_{feature_name}_psi",
            baseline_value=0.0,
            current_value=psi,
            deviation_percentage=psi * 100,
            description=f"Feature '{feature_name}' PSI: {psi:.4f}",
            recommendations=self._get_feature_drift_recommendations(severity),
        )

        if severity != DriftSeverity.NONE:
            self._alerts.append(alert)

        return alert

    def _get_feature_drift_recommendations(self, severity: DriftSeverity) -> List[str]:
        """Get recommendations for feature drift."""
        if severity in (DriftSeverity.SIGNIFICANT, DriftSeverity.CRITICAL):
            return [
                "Investigate feature distribution changes",
                "Check for data quality issues",
                "Consider retraining model with new data",
                "Review upstream data pipelines",
            ]
        elif severity == DriftSeverity.MODERATE:
            return [
                "Monitor feature distribution",
                "Schedule feature engineering review",
            ]
        else:
            return ["Continue standard monitoring"]

    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive model health report."""
        recent_alerts = [a for a in self._alerts
                       if (datetime.utcnow() - a.timestamp).total_seconds() < 86400]

        severity_counts = {}
        for severity in DriftSeverity:
            severity_counts[severity.value] = sum(
                1 for a in recent_alerts if a.severity == severity
            )

        drift_type_counts = {}
        for dt in DriftType:
            drift_type_counts[dt.value] = sum(
                1 for a in recent_alerts if a.drift_type == dt
            )

        metrics_summary = {}
        for metric_name, history in self._metrics_history.items():
            if history:
                values = [m.value for m in history[-100:]]
                metrics_summary[metric_name] = self._calculate_statistics(values)

        return {
            "model_id": self.model_id,
            "version": self.version,
            "report_time": datetime.utcnow().isoformat(),
            "metrics_tracked": len(self._metrics_history),
            "baselines_configured": len(self._baselines),
            "alerts_24h": {
                "total": len(recent_alerts),
                "by_severity": severity_counts,
                "by_drift_type": drift_type_counts,
            },
            "metrics_summary": metrics_summary,
            "health_status": self._determine_health_status(recent_alerts),
        }

    def _determine_health_status(self, recent_alerts: List[DriftAlert]) -> str:
        """Determine overall health status."""
        critical = sum(1 for a in recent_alerts if a.severity == DriftSeverity.CRITICAL)
        significant = sum(1 for a in recent_alerts if a.severity == DriftSeverity.SIGNIFICANT)

        if critical > 0:
            return "CRITICAL"
        elif significant > 2:
            return "DEGRADED"
        elif significant > 0:
            return "WARNING"
        else:
            return "HEALTHY"

    def get_active_alerts(self, max_age_hours: int = 24) -> List[DriftAlert]:
        """Get active alerts within the specified time window."""
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        return [a for a in self._alerts if a.timestamp > cutoff]

    def clear_alerts(self, before: Optional[datetime] = None) -> int:
        """Clear alerts, optionally before a specific time."""
        if before is None:
            count = len(self._alerts)
            self._alerts = []
            return count

        original_count = len(self._alerts)
        self._alerts = [a for a in self._alerts if a.timestamp >= before]
        return original_count - len(self._alerts)
