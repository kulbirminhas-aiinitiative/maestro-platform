"""
Time-Series Storage for Performance Metrics

In-memory implementation with interface for future database backends.
"""

from typing import List, Optional, Dict
from datetime import datetime, timedelta
from abc import ABC, abstractmethod
from collections import defaultdict
import numpy as np

from ..models.metrics_models import (
    PerformanceMetric,
    MetricSnapshot,
    MetricType
)


class TimeSeriesStore(ABC):
    """Abstract interface for time-series metric storage"""

    @abstractmethod
    def store_metric(self, metric: PerformanceMetric) -> None:
        """Store a single metric data point"""
        pass

    @abstractmethod
    def store_snapshot(self, snapshot: MetricSnapshot) -> None:
        """Store a complete metric snapshot"""
        pass

    @abstractmethod
    def get_metrics(
        self,
        model_name: str,
        model_version: Optional[str] = None,
        metric_type: Optional[MetricType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[PerformanceMetric]:
        """Retrieve metrics with filtering"""
        pass

    @abstractmethod
    def get_snapshots(
        self,
        model_name: str,
        model_version: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[MetricSnapshot]:
        """Retrieve metric snapshots"""
        pass

    @abstractmethod
    def get_latest_snapshot(
        self,
        model_name: str,
        model_version: str
    ) -> Optional[MetricSnapshot]:
        """Get most recent snapshot for a model"""
        pass

    @abstractmethod
    def delete_old_data(self, before: datetime) -> int:
        """Delete data older than specified time"""
        pass


class InMemoryTimeSeriesStore(TimeSeriesStore):
    """
    In-memory time-series storage

    Production deployment should use proper time-series DB (InfluxDB, TimescaleDB, etc.)
    """

    def __init__(self):
        # Store metrics: {model_name: {model_version: [metrics]}}
        self._metrics: Dict[str, Dict[str, List[PerformanceMetric]]] = defaultdict(lambda: defaultdict(list))

        # Store snapshots: {model_name: {model_version: [snapshots]}}
        self._snapshots: Dict[str, Dict[str, List[MetricSnapshot]]] = defaultdict(lambda: defaultdict(list))

    def store_metric(self, metric: PerformanceMetric) -> None:
        """Store a single metric data point"""
        self._metrics[metric.model_name][metric.model_version].append(metric)

        # Keep sorted by timestamp
        self._metrics[metric.model_name][metric.model_version].sort(
            key=lambda m: m.timestamp
        )

    def store_snapshot(self, snapshot: MetricSnapshot) -> None:
        """Store a complete metric snapshot"""
        self._snapshots[snapshot.model_name][snapshot.model_version].append(snapshot)

        # Keep sorted by timestamp
        self._snapshots[snapshot.model_name][snapshot.model_version].sort(
            key=lambda s: s.timestamp
        )

    def get_metrics(
        self,
        model_name: str,
        model_version: Optional[str] = None,
        metric_type: Optional[MetricType] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> List[PerformanceMetric]:
        """Retrieve metrics with filtering"""
        if model_name not in self._metrics:
            return []

        # Collect metrics from specified version(s)
        all_metrics = []
        if model_version:
            if model_version in self._metrics[model_name]:
                all_metrics = self._metrics[model_name][model_version].copy()
        else:
            # All versions
            for version_metrics in self._metrics[model_name].values():
                all_metrics.extend(version_metrics)

        # Filter by metric type
        if metric_type:
            all_metrics = [m for m in all_metrics if m.metric_type == metric_type]

        # Filter by time range
        if start_time:
            all_metrics = [m for m in all_metrics if m.timestamp >= start_time]
        if end_time:
            all_metrics = [m for m in all_metrics if m.timestamp <= end_time]

        # Sort by timestamp (most recent first)
        all_metrics.sort(key=lambda m: m.timestamp, reverse=True)

        # Limit results
        return all_metrics[:limit]

    def get_snapshots(
        self,
        model_name: str,
        model_version: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[MetricSnapshot]:
        """Retrieve metric snapshots"""
        if model_name not in self._snapshots:
            return []

        # Collect snapshots
        all_snapshots = []
        if model_version:
            if model_version in self._snapshots[model_name]:
                all_snapshots = self._snapshots[model_name][model_version].copy()
        else:
            for version_snapshots in self._snapshots[model_name].values():
                all_snapshots.extend(version_snapshots)

        # Filter by time range
        if start_time:
            all_snapshots = [s for s in all_snapshots if s.timestamp >= start_time]
        if end_time:
            all_snapshots = [s for s in all_snapshots if s.timestamp <= end_time]

        # Sort by timestamp (most recent first)
        all_snapshots.sort(key=lambda s: s.timestamp, reverse=True)

        return all_snapshots[:limit]

    def get_latest_snapshot(
        self,
        model_name: str,
        model_version: str
    ) -> Optional[MetricSnapshot]:
        """Get most recent snapshot for a model"""
        snapshots = self.get_snapshots(model_name, model_version, limit=1)
        return snapshots[0] if snapshots else None

    def delete_old_data(self, before: datetime) -> int:
        """Delete data older than specified time"""
        deleted_count = 0

        # Delete old metrics
        for model_name in list(self._metrics.keys()):
            for version in list(self._metrics[model_name].keys()):
                original_count = len(self._metrics[model_name][version])
                self._metrics[model_name][version] = [
                    m for m in self._metrics[model_name][version]
                    if m.timestamp >= before
                ]
                deleted_count += original_count - len(self._metrics[model_name][version])

        # Delete old snapshots
        for model_name in list(self._snapshots.keys()):
            for version in list(self._snapshots[model_name].keys()):
                original_count = len(self._snapshots[model_name][version])
                self._snapshots[model_name][version] = [
                    s for s in self._snapshots[model_name][version]
                    if s.timestamp >= before
                ]
                deleted_count += original_count - len(self._snapshots[model_name][version])

        return deleted_count

    def get_baseline_metrics(
        self,
        model_name: str,
        model_version: str,
        metric_type: MetricType,
        window_hours: int = 24
    ) -> List[PerformanceMetric]:
        """Get baseline metrics for comparison (past N hours)"""
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=window_hours)

        return self.get_metrics(
            model_name=model_name,
            model_version=model_version,
            metric_type=metric_type,
            start_time=start_time,
            end_time=end_time
        )

    def calculate_metric_statistics(
        self,
        metrics: List[PerformanceMetric]
    ) -> Dict[str, float]:
        """Calculate statistical measures for a list of metrics"""
        if not metrics:
            return {}

        values = [m.metric_value for m in metrics]

        return {
            "mean": float(np.mean(values)),
            "median": float(np.median(values)),
            "std": float(np.std(values)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "count": len(values)
        }
