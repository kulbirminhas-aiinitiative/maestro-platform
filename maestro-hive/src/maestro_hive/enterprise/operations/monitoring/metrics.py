"""
Metrics Collection for Operations Monitoring - AC-4.

Collects and queries runtime metrics.
"""

from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import statistics


class MetricType(str, Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class Aggregation(str, Enum):
    """Aggregation types."""
    SUM = "sum"
    AVG = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    P50 = "p50"
    P95 = "p95"
    P99 = "p99"


@dataclass
class Metric:
    """Single metric data point."""
    name: str
    value: float
    metric_type: MetricType
    timestamp: datetime
    labels: dict[str, str] = field(default_factory=dict)
    unit: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "value": self.value,
            "type": self.metric_type.value,
            "timestamp": self.timestamp.isoformat(),
            "labels": self.labels,
            "unit": self.unit
        }


@dataclass
class MetricQuery:
    """Query for metrics."""
    name: str
    start: datetime
    end: datetime
    aggregation: Aggregation = Aggregation.AVG
    labels: dict[str, str] = field(default_factory=dict)
    step_seconds: int = 60


@dataclass
class MetricDataPoint:
    """Single point in metric result."""
    timestamp: datetime
    value: float


@dataclass
class MetricResult:
    """Result of metric query."""
    name: str
    data: list[MetricDataPoint]
    aggregation: Aggregation
    labels: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric": self.name,
            "aggregation": self.aggregation.value,
            "labels": self.labels,
            "data": [
                {"timestamp": d.timestamp.isoformat(), "value": d.value}
                for d in self.data
            ]
        }


class MetricsBackend:
    """Abstract metrics storage backend."""

    async def store(self, metric: Metric) -> None:
        """Store metric."""
        raise NotImplementedError

    async def query(self, query: MetricQuery) -> MetricResult:
        """Query metrics."""
        raise NotImplementedError


class InMemoryMetricsBackend(MetricsBackend):
    """In-memory metrics backend."""

    def __init__(self):
        self._metrics: dict[str, list[Metric]] = {}

    async def store(self, metric: Metric) -> None:
        """Store metric in memory."""
        if metric.name not in self._metrics:
            self._metrics[metric.name] = []
        self._metrics[metric.name].append(metric)

        # Keep only last 10000 points per metric
        if len(self._metrics[metric.name]) > 10000:
            self._metrics[metric.name] = self._metrics[metric.name][-10000:]

    async def query(self, query: MetricQuery) -> MetricResult:
        """Query metrics from memory."""
        metrics = self._metrics.get(query.name, [])

        # Filter by time range
        filtered = [
            m for m in metrics
            if query.start <= m.timestamp <= query.end
        ]

        # Filter by labels
        if query.labels:
            filtered = [
                m for m in filtered
                if all(m.labels.get(k) == v for k, v in query.labels.items())
            ]

        # Aggregate by step
        data_points = self._aggregate(filtered, query)

        return MetricResult(
            name=query.name,
            data=data_points,
            aggregation=query.aggregation,
            labels=query.labels
        )

    def _aggregate(
        self,
        metrics: list[Metric],
        query: MetricQuery
    ) -> list[MetricDataPoint]:
        """Aggregate metrics by time step."""
        if not metrics:
            return []

        # Group by time bucket
        buckets: dict[datetime, list[float]] = {}
        step = timedelta(seconds=query.step_seconds)

        for m in metrics:
            bucket_time = datetime(
                m.timestamp.year, m.timestamp.month, m.timestamp.day,
                m.timestamp.hour, m.timestamp.minute
            )
            bucket_time = bucket_time.replace(
                minute=(bucket_time.minute // (query.step_seconds // 60)) * (query.step_seconds // 60)
            )

            if bucket_time not in buckets:
                buckets[bucket_time] = []
            buckets[bucket_time].append(m.value)

        # Apply aggregation
        result = []
        for timestamp, values in sorted(buckets.items()):
            if query.aggregation == Aggregation.SUM:
                value = sum(values)
            elif query.aggregation == Aggregation.AVG:
                value = statistics.mean(values)
            elif query.aggregation == Aggregation.MIN:
                value = min(values)
            elif query.aggregation == Aggregation.MAX:
                value = max(values)
            elif query.aggregation == Aggregation.COUNT:
                value = len(values)
            elif query.aggregation == Aggregation.P50:
                value = statistics.median(values)
            elif query.aggregation == Aggregation.P95:
                value = self._percentile(values, 95)
            elif query.aggregation == Aggregation.P99:
                value = self._percentile(values, 99)
            else:
                value = statistics.mean(values)

            result.append(MetricDataPoint(timestamp=timestamp, value=value))

        return result

    def _percentile(self, values: list[float], percentile: int) -> float:
        """Calculate percentile."""
        if not values:
            return 0.0
        sorted_values = sorted(values)
        idx = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(idx, len(sorted_values) - 1)]


class MetricsCollector:
    """Collects runtime metrics."""

    def __init__(self, backend: Optional[MetricsBackend] = None):
        self.backend = backend or InMemoryMetricsBackend()
        self._labels: dict[str, str] = {}

    def set_labels(self, labels: dict[str, str]) -> None:
        """Set default labels for all metrics."""
        self._labels = labels

    async def collect(self, metric: Metric) -> None:
        """Collect metric data point."""
        # Merge with default labels
        metric.labels = {**self._labels, **metric.labels}
        await self.backend.store(metric)

    async def increment(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[dict[str, str]] = None
    ) -> None:
        """Increment counter metric."""
        await self.collect(Metric(
            name=name,
            value=value,
            metric_type=MetricType.COUNTER,
            timestamp=datetime.utcnow(),
            labels=labels or {}
        ))

    async def gauge(
        self,
        name: str,
        value: float,
        labels: Optional[dict[str, str]] = None
    ) -> None:
        """Record gauge metric."""
        await self.collect(Metric(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            timestamp=datetime.utcnow(),
            labels=labels or {}
        ))

    async def histogram(
        self,
        name: str,
        value: float,
        labels: Optional[dict[str, str]] = None
    ) -> None:
        """Record histogram metric."""
        await self.collect(Metric(
            name=name,
            value=value,
            metric_type=MetricType.HISTOGRAM,
            timestamp=datetime.utcnow(),
            labels=labels or {}
        ))

    async def query(self, query: MetricQuery) -> MetricResult:
        """Query metrics."""
        return await self.backend.query(query)

    async def get_current(self, name: str, labels: Optional[dict[str, str]] = None) -> Optional[float]:
        """Get most recent value for metric."""
        now = datetime.utcnow()
        query = MetricQuery(
            name=name,
            start=now - timedelta(minutes=5),
            end=now,
            aggregation=Aggregation.AVG,
            labels=labels or {}
        )
        result = await self.query(query)
        if result.data:
            return result.data[-1].value
        return None
