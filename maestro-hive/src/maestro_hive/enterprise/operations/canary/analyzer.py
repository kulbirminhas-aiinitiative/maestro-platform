"""
Canary Analyzer Implementation.

Analyzes canary deployment health by comparing metrics
between stable and canary versions.
"""

import asyncio
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Any, Optional
from enum import Enum


class MetricComparison(str, Enum):
    """Comparison result."""
    BETTER = "better"
    SAME = "same"
    WORSE = "worse"
    UNKNOWN = "unknown"


@dataclass
class HealthCriteria:
    """Health criteria for canary analysis."""
    error_rate_delta_max: float = 0.01  # 1% max error rate increase
    latency_p99_delta_max: float = 0.10  # 10% max latency increase
    success_rate_min: float = 0.99  # 99% minimum success rate
    min_observation_period: timedelta = field(default_factory=lambda: timedelta(minutes=5))
    min_request_count: int = 100

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_rate_delta_max": self.error_rate_delta_max,
            "latency_p99_delta_max": self.latency_p99_delta_max,
            "success_rate_min": self.success_rate_min,
            "min_observation_period_seconds": self.min_observation_period.total_seconds(),
            "min_request_count": self.min_request_count,
        }


@dataclass
class CanaryMetrics:
    """Metrics collected for canary analysis."""
    version: str
    request_count: int
    error_count: int
    success_rate: float
    latency_p50: float
    latency_p95: float
    latency_p99: float
    collected_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def error_rate(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "request_count": self.request_count,
            "error_count": self.error_count,
            "success_rate": self.success_rate,
            "error_rate": self.error_rate,
            "latency_p50": self.latency_p50,
            "latency_p95": self.latency_p95,
            "latency_p99": self.latency_p99,
            "collected_at": self.collected_at.isoformat(),
        }


@dataclass
class MetricDelta:
    """Delta between stable and canary metrics."""
    name: str
    stable_value: float
    canary_value: float
    delta: float
    delta_percent: float
    comparison: MetricComparison
    threshold_exceeded: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "stable_value": self.stable_value,
            "canary_value": self.canary_value,
            "delta": self.delta,
            "delta_percent": self.delta_percent,
            "comparison": self.comparison.value,
            "threshold_exceeded": self.threshold_exceeded,
        }


@dataclass
class AnalysisResult:
    """Result of canary analysis."""
    passed: bool
    stable_metrics: CanaryMetrics
    canary_metrics: CanaryMetrics
    deltas: list[MetricDelta]
    reason: str
    analyzed_at: datetime
    observation_period: timedelta
    criteria_used: HealthCriteria

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "stable_metrics": self.stable_metrics.to_dict(),
            "canary_metrics": self.canary_metrics.to_dict(),
            "deltas": [d.to_dict() for d in self.deltas],
            "reason": self.reason,
            "analyzed_at": self.analyzed_at.isoformat(),
            "observation_period_seconds": self.observation_period.total_seconds(),
            "criteria_used": self.criteria_used.to_dict(),
        }


class CanaryAnalyzer:
    """Analyzes canary deployment health."""

    def __init__(self, metrics_collector=None):
        self.metrics_collector = metrics_collector
        self._metric_history: dict[str, list[CanaryMetrics]] = {}

    async def analyze(
        self,
        service: str,
        stable_version: str,
        canary_version: str,
        criteria: Optional[HealthCriteria] = None,
    ) -> AnalysisResult:
        """Analyze canary health compared to stable."""
        criteria = criteria or HealthCriteria()

        # Collect metrics
        stable_metrics = await self._collect_metrics(service, stable_version)
        canary_metrics = await self._collect_metrics(service, canary_version)

        # Calculate deltas
        deltas = self._calculate_deltas(stable_metrics, canary_metrics, criteria)

        # Determine if passed
        passed, reason = self._evaluate(stable_metrics, canary_metrics, deltas, criteria)

        return AnalysisResult(
            passed=passed,
            stable_metrics=stable_metrics,
            canary_metrics=canary_metrics,
            deltas=deltas,
            reason=reason,
            analyzed_at=datetime.utcnow(),
            observation_period=criteria.min_observation_period,
            criteria_used=criteria,
        )

    async def _collect_metrics(self, service: str, version: str) -> CanaryMetrics:
        """Collect metrics for a version (simulated)."""
        await asyncio.sleep(0.01)

        # Simulated metrics - in production would query actual metrics
        return CanaryMetrics(
            version=version,
            request_count=1000,
            error_count=5,
            success_rate=0.995,
            latency_p50=50.0,
            latency_p95=150.0,
            latency_p99=250.0,
            collected_at=datetime.utcnow(),
        )

    def _calculate_deltas(
        self,
        stable: CanaryMetrics,
        canary: CanaryMetrics,
        criteria: HealthCriteria,
    ) -> list[MetricDelta]:
        """Calculate metric deltas between versions."""
        deltas = []

        # Error rate delta
        error_delta = canary.error_rate - stable.error_rate
        error_percent = (error_delta / stable.error_rate * 100) if stable.error_rate > 0 else 0
        deltas.append(MetricDelta(
            name="error_rate",
            stable_value=stable.error_rate,
            canary_value=canary.error_rate,
            delta=error_delta,
            delta_percent=error_percent,
            comparison=self._compare(stable.error_rate, canary.error_rate, lower_is_better=True),
            threshold_exceeded=error_delta > criteria.error_rate_delta_max,
        ))

        # Latency P99 delta
        latency_delta = canary.latency_p99 - stable.latency_p99
        latency_percent = (latency_delta / stable.latency_p99 * 100) if stable.latency_p99 > 0 else 0
        deltas.append(MetricDelta(
            name="latency_p99",
            stable_value=stable.latency_p99,
            canary_value=canary.latency_p99,
            delta=latency_delta,
            delta_percent=latency_percent,
            comparison=self._compare(stable.latency_p99, canary.latency_p99, lower_is_better=True),
            threshold_exceeded=latency_percent / 100 > criteria.latency_p99_delta_max,
        ))

        # Success rate
        success_delta = canary.success_rate - stable.success_rate
        deltas.append(MetricDelta(
            name="success_rate",
            stable_value=stable.success_rate,
            canary_value=canary.success_rate,
            delta=success_delta,
            delta_percent=(success_delta / stable.success_rate * 100) if stable.success_rate > 0 else 0,
            comparison=self._compare(stable.success_rate, canary.success_rate, lower_is_better=False),
            threshold_exceeded=canary.success_rate < criteria.success_rate_min,
        ))

        return deltas

    def _compare(
        self,
        stable: float,
        canary: float,
        lower_is_better: bool,
    ) -> MetricComparison:
        """Compare metric values."""
        threshold = 0.01  # 1% tolerance for "same"

        if stable == 0:
            if canary == 0:
                return MetricComparison.SAME
            return MetricComparison.WORSE if lower_is_better else MetricComparison.BETTER

        percent_diff = abs(canary - stable) / stable

        if percent_diff < threshold:
            return MetricComparison.SAME

        if lower_is_better:
            return MetricComparison.BETTER if canary < stable else MetricComparison.WORSE
        else:
            return MetricComparison.BETTER if canary > stable else MetricComparison.WORSE

    def _evaluate(
        self,
        stable: CanaryMetrics,
        canary: CanaryMetrics,
        deltas: list[MetricDelta],
        criteria: HealthCriteria,
    ) -> tuple[bool, str]:
        """Evaluate if canary passes health criteria."""
        # Check minimum request count
        if canary.request_count < criteria.min_request_count:
            return False, f"Insufficient requests: {canary.request_count} < {criteria.min_request_count}"

        # Check for threshold violations
        violations = [d for d in deltas if d.threshold_exceeded]

        if violations:
            violation_names = [v.name for v in violations]
            return False, f"Threshold exceeded for: {', '.join(violation_names)}"

        # Check for significantly worse metrics
        worse_metrics = [d for d in deltas if d.comparison == MetricComparison.WORSE]
        if len(worse_metrics) >= 2:
            worse_names = [w.name for w in worse_metrics]
            return False, f"Multiple degraded metrics: {', '.join(worse_names)}"

        return True, "All health criteria passed"

    def record_metrics(self, service: str, metrics: CanaryMetrics) -> None:
        """Record metrics for historical analysis."""
        key = f"{service}:{metrics.version}"
        if key not in self._metric_history:
            self._metric_history[key] = []

        self._metric_history[key].append(metrics)

        # Keep only last 100 records
        if len(self._metric_history[key]) > 100:
            self._metric_history[key] = self._metric_history[key][-100:]

    def get_metric_history(
        self,
        service: str,
        version: str,
        limit: int = 10,
    ) -> list[CanaryMetrics]:
        """Get metric history for a version."""
        key = f"{service}:{version}"
        history = self._metric_history.get(key, [])
        return history[-limit:]

    def get_trend(
        self,
        service: str,
        version: str,
        metric_name: str,
    ) -> dict[str, Any]:
        """Get trend for a specific metric."""
        history = self.get_metric_history(service, version, limit=20)

        if not history:
            return {"trend": "unknown", "samples": 0}

        values = []
        for m in history:
            if metric_name == "error_rate":
                values.append(m.error_rate)
            elif metric_name == "latency_p99":
                values.append(m.latency_p99)
            elif metric_name == "success_rate":
                values.append(m.success_rate)

        if len(values) < 2:
            return {"trend": "stable", "samples": len(values)}

        # Simple trend detection
        first_half = sum(values[:len(values)//2]) / (len(values)//2)
        second_half = sum(values[len(values)//2:]) / (len(values) - len(values)//2)

        if second_half > first_half * 1.05:
            trend = "increasing"
        elif second_half < first_half * 0.95:
            trend = "decreasing"
        else:
            trend = "stable"

        return {
            "trend": trend,
            "samples": len(values),
            "first_half_avg": first_half,
            "second_half_avg": second_half,
        }
