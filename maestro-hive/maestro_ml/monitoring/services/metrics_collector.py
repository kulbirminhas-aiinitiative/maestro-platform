"""
Metrics Collection Service

Collects and stores model performance metrics over time.
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np

from ..models.metrics_models import (
    MetricType,
    PerformanceMetric,
    MetricSnapshot,
    MetricSummary,
    ModelPerformanceHistory
)
from ..storage.time_series_store import TimeSeriesStore, InMemoryTimeSeriesStore


class MetricsCollector:
    """
    Collect and manage model performance metrics

    Example:
        >>> collector = MetricsCollector()
        >>> collector.record_metric("my_model", "v1.0", MetricType.ACCURACY, 0.95)
        >>> collector.record_snapshot("my_model", "v1.0", {"accuracy": 0.95, "f1_score": 0.93})
        >>> history = collector.get_performance_history("my_model", "v1.0", hours=24)
    """

    def __init__(self, store: Optional[TimeSeriesStore] = None):
        """
        Initialize metrics collector

        Args:
            store: Time-series storage backend (defaults to in-memory)
        """
        self.store = store or InMemoryTimeSeriesStore()

    def record_metric(
        self,
        model_name: str,
        model_version: str,
        metric_type: MetricType,
        metric_value: float,
        dataset_name: Optional[str] = None,
        dataset_size: Optional[int] = None,
        metadata: Optional[Dict] = None,
        tags: Optional[List[str]] = None
    ) -> PerformanceMetric:
        """
        Record a single performance metric

        Args:
            model_name: Model identifier
            model_version: Model version
            metric_type: Type of metric
            metric_value: Metric value
            dataset_name: Dataset used for evaluation
            dataset_size: Number of samples in dataset
            metadata: Additional metadata
            tags: Tags for categorization

        Returns:
            PerformanceMetric instance
        """
        metric = PerformanceMetric(
            model_name=model_name,
            model_version=model_version,
            metric_type=metric_type,
            metric_value=metric_value,
            dataset_name=dataset_name,
            dataset_size=dataset_size,
            metadata=metadata or {},
            tags=tags or []
        )

        self.store.store_metric(metric)
        return metric

    def record_snapshot(
        self,
        model_name: str,
        model_version: str,
        metrics: Dict[str, float],
        dataset_name: Optional[str] = None,
        environment: str = "production"
    ) -> MetricSnapshot:
        """
        Record a complete snapshot of all metrics at once

        Args:
            model_name: Model identifier
            model_version: Model version
            metrics: Dictionary of metric_name -> value
            dataset_name: Dataset used
            environment: Environment (production, staging, test)

        Returns:
            MetricSnapshot instance
        """
        snapshot = MetricSnapshot(
            model_name=model_name,
            model_version=model_version,
            metrics=metrics,
            dataset_name=dataset_name,
            environment=environment
        )

        # Also store individual metrics
        for metric_name, value in metrics.items():
            try:
                metric_type = MetricType(metric_name.lower())
                self.record_metric(
                    model_name=model_name,
                    model_version=model_version,
                    metric_type=metric_type,
                    metric_value=value,
                    dataset_name=dataset_name
                )
            except ValueError:
                # Unknown metric type, store as custom
                self.record_metric(
                    model_name=model_name,
                    model_version=model_version,
                    metric_type=MetricType.CUSTOM,
                    metric_value=value,
                    dataset_name=dataset_name,
                    metadata={"custom_metric_name": metric_name}
                )

        self.store.store_snapshot(snapshot)
        return snapshot

    def get_latest_metrics(
        self,
        model_name: str,
        model_version: str
    ) -> Optional[MetricSnapshot]:
        """Get the most recent metric snapshot for a model"""
        return self.store.get_latest_snapshot(model_name, model_version)

    def get_metric_history(
        self,
        model_name: str,
        model_version: str,
        metric_type: MetricType,
        hours: int = 24,
        limit: int = 1000
    ) -> List[PerformanceMetric]:
        """
        Get historical data for a specific metric

        Args:
            model_name: Model identifier
            model_version: Model version
            metric_type: Type of metric
            hours: How many hours back to look
            limit: Maximum number of data points

        Returns:
            List of PerformanceMetric instances
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        return self.store.get_metrics(
            model_name=model_name,
            model_version=model_version,
            metric_type=metric_type,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )

    def get_metric_summary(
        self,
        model_name: str,
        model_version: str,
        metric_type: MetricType,
        hours: int = 24
    ) -> Optional[MetricSummary]:
        """
        Get statistical summary for a metric

        Args:
            model_name: Model identifier
            model_version: Model version
            metric_type: Type of metric
            hours: Time window for analysis

        Returns:
            MetricSummary with statistics
        """
        metrics = self.get_metric_history(
            model_name=model_name,
            model_version=model_version,
            metric_type=metric_type,
            hours=hours
        )

        if not metrics:
            return None

        values = [m.metric_value for m in metrics]
        current_value = values[0]  # Most recent (sorted desc)

        # Calculate baseline (average of older values)
        baseline_value = None
        if len(values) > 1:
            baseline_value = float(np.mean(values[1:]))

        # Determine trend
        trend = "stable"
        change_percentage = None

        if baseline_value is not None and baseline_value != 0:
            change_percentage = ((current_value - baseline_value) / baseline_value) * 100

            # Determine if higher is better based on metric type
            higher_is_better = metric_type not in [
                MetricType.MAE, MetricType.MSE, MetricType.RMSE,
                MetricType.MAPE, MetricType.ERROR_RATE, MetricType.LATENCY
            ]

            if abs(change_percentage) > 5:  # >5% change
                if higher_is_better:
                    trend = "improving" if change_percentage > 0 else "degrading"
                else:
                    trend = "degrading" if change_percentage > 0 else "improving"

        return MetricSummary(
            metric_type=metric_type,
            current_value=current_value,
            baseline_value=baseline_value,
            mean=float(np.mean(values)),
            median=float(np.median(values)),
            std=float(np.std(values)),
            min=float(np.min(values)),
            max=float(np.max(values)),
            trend=trend,
            change_percentage=change_percentage,
            start_time=metrics[-1].timestamp,
            end_time=metrics[0].timestamp,
            data_points=len(metrics)
        )

    def get_performance_history(
        self,
        model_name: str,
        model_version: str,
        hours: int = 24
    ) -> ModelPerformanceHistory:
        """
        Get complete performance history for a model

        Args:
            model_name: Model identifier
            model_version: Model version
            hours: Time window for analysis

        Returns:
            ModelPerformanceHistory with all metrics and analysis
        """
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=hours)

        # Get all snapshots
        snapshots = self.store.get_snapshots(
            model_name=model_name,
            model_version=model_version,
            start_time=start_time,
            end_time=end_time
        )

        # Get summaries for all metric types found
        metric_summaries = []
        metric_types_found = set()

        for snapshot in snapshots:
            for metric_name in snapshot.metrics.keys():
                try:
                    metric_type = MetricType(metric_name.lower())
                    metric_types_found.add(metric_type)
                except ValueError:
                    pass

        for metric_type in metric_types_found:
            summary = self.get_metric_summary(
                model_name=model_name,
                model_version=model_version,
                metric_type=metric_type,
                hours=hours
            )
            if summary:
                metric_summaries.append(summary)

        # Assess overall health
        overall_health = self._assess_health(metric_summaries)
        health_trend = self._assess_health_trend(metric_summaries)

        return ModelPerformanceHistory(
            model_name=model_name,
            model_version=model_version,
            start_time=start_time,
            end_time=end_time,
            total_snapshots=len(snapshots),
            metric_summaries=metric_summaries,
            snapshots=snapshots,
            overall_health=overall_health,
            health_trend=health_trend
        )

    def _assess_health(self, summaries: List[MetricSummary]) -> str:
        """Assess overall model health from metric summaries"""
        if not summaries:
            return "unknown"

        degrading_count = sum(1 for s in summaries if s.trend == "degrading")
        improving_count = sum(1 for s in summaries if s.trend == "improving")

        total = len(summaries)
        degrading_pct = (degrading_count / total) * 100

        if degrading_pct > 50:
            return "poor"
        elif degrading_pct > 25:
            return "fair"
        elif improving_count > degrading_count:
            return "excellent"
        else:
            return "good"

    def _assess_health_trend(self, summaries: List[MetricSummary]) -> str:
        """Assess overall health trend"""
        if not summaries:
            return "unknown"

        degrading_count = sum(1 for s in summaries if s.trend == "degrading")
        improving_count = sum(1 for s in summaries if s.trend == "improving")

        if improving_count > degrading_count:
            return "improving"
        elif degrading_count > improving_count:
            return "degrading"
        else:
            return "stable"

    def cleanup_old_data(self, days: int = 30) -> int:
        """
        Delete metrics older than specified days

        Args:
            days: Number of days to retain

        Returns:
            Number of deleted records
        """
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        return self.store.delete_old_data(cutoff_time)
