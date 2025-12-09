#!/usr/bin/env python3
"""
Monitoring Module: Provides observability for the Maestro platform.

This module handles:
- Metrics collection and reporting
- Log aggregation
- Alerting configuration
- Health checks and dashboards
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import uuid

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class AlertSeverity(Enum):
    """Severity levels for alerts."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Status of alerts."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class Metric:
    """A metric data point."""
    name: str
    metric_type: MetricType
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Alert:
    """An alert notification."""
    alert_id: str
    name: str
    message: str
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.ACTIVE
    labels: Dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None


@dataclass
class AlertRule:
    """A rule for generating alerts."""
    rule_id: str
    name: str
    metric_name: str
    condition: str  # e.g., "> 90", "< 10", "== 0"
    threshold: float
    severity: AlertSeverity
    for_duration: int = 0  # seconds condition must be true
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class HealthCheck:
    """A health check result."""
    check_id: str
    name: str
    status: HealthStatus
    details: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class LogEntry:
    """A log entry."""
    log_id: str
    level: str
    message: str
    source: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


class MonitoringService:
    """
    Provides monitoring and observability.

    Implements:
    - monitoring: Collect and report metrics
    - log_aggregation: Aggregate logs from multiple sources
    - alerting: Generate and manage alerts
    - health_checks: Perform system health checks
    """

    def __init__(self, service_name: str = "maestro"):
        """Initialize the monitoring service."""
        self.service_name = service_name

        # Storage
        self._metrics: Dict[str, List[Metric]] = defaultdict(list)
        self._alerts: Dict[str, Alert] = {}
        self._alert_rules: Dict[str, AlertRule] = {}
        self._health_checks: Dict[str, HealthCheck] = {}
        self._logs: List[LogEntry] = []
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}

        # Alert handlers
        self._alert_handlers: List[Callable[[Alert], None]] = []

    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Optional[Dict[str, str]] = None
    ) -> Metric:
        """
        Record a metric value.

        Implements monitoring for metrics collection.
        """
        metric = Metric(
            name=name,
            metric_type=metric_type,
            value=value,
            labels=labels or {}
        )

        # Store metric
        key = f"{name}:{str(labels)}"
        self._metrics[key].append(metric)

        # Keep only last hour of data
        cutoff = datetime.utcnow() - timedelta(hours=1)
        self._metrics[key] = [
            m for m in self._metrics[key] if m.timestamp > cutoff
        ]

        # Update gauges/counters
        if metric_type == MetricType.GAUGE:
            self._gauges[key] = value
        elif metric_type == MetricType.COUNTER:
            self._counters[key] += value

        # Check alert rules
        self._check_alert_rules(name, value, labels)

        return metric

    def increment_counter(
        self,
        name: str,
        value: float = 1.0,
        labels: Optional[Dict[str, str]] = None
    ) -> float:
        """Increment a counter metric."""
        self.record_metric(name, value, MetricType.COUNTER, labels)
        key = f"{name}:{str(labels)}"
        return self._counters[key]

    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> float:
        """Set a gauge metric value."""
        self.record_metric(name, value, MetricType.GAUGE, labels)
        key = f"{name}:{str(labels)}"
        return self._gauges[key]

    def get_metric(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None
    ) -> Optional[float]:
        """Get current value of a metric."""
        key = f"{name}:{str(labels)}"
        if key in self._gauges:
            return self._gauges[key]
        if key in self._counters:
            return self._counters[key]
        return None

    def get_metric_history(
        self,
        name: str,
        labels: Optional[Dict[str, str]] = None,
        duration_minutes: int = 60
    ) -> List[Metric]:
        """Get historical metric values."""
        key = f"{name}:{str(labels)}"
        cutoff = datetime.utcnow() - timedelta(minutes=duration_minutes)
        return [m for m in self._metrics.get(key, []) if m.timestamp > cutoff]

    def log(
        self,
        level: str,
        message: str,
        source: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None
    ) -> LogEntry:
        """
        Record a log entry.

        Implements log_aggregation.
        """
        entry = LogEntry(
            log_id=str(uuid.uuid4()),
            level=level,
            message=message,
            source=source,
            metadata=metadata or {}
        )

        self._logs.append(entry)

        # Keep only last 10000 logs
        if len(self._logs) > 10000:
            self._logs = self._logs[-10000:]

        # Log to standard logger as well
        log_level = getattr(logging, level.upper(), logging.INFO)
        logger.log(log_level, f"[{source}] {message}")

        return entry

    def query_logs(
        self,
        level: Optional[str] = None,
        source: Optional[str] = None,
        search: Optional[str] = None,
        limit: int = 100
    ) -> List[LogEntry]:
        """Query logs with filters."""
        results = self._logs.copy()

        if level:
            results = [l for l in results if l.level == level]
        if source:
            results = [l for l in results if l.source == source]
        if search:
            results = [l for l in results if search.lower() in l.message.lower()]

        return results[-limit:]

    def register_alert_rule(
        self,
        name: str,
        metric_name: str,
        condition: str,
        threshold: float,
        severity: AlertSeverity,
        for_duration: int = 0
    ) -> AlertRule:
        """
        Register an alert rule.

        Implements alerting configuration.
        """
        rule = AlertRule(
            rule_id=str(uuid.uuid4()),
            name=name,
            metric_name=metric_name,
            condition=condition,
            threshold=threshold,
            severity=severity,
            for_duration=for_duration
        )

        self._alert_rules[rule.rule_id] = rule
        logger.info(f"Alert rule registered: {name}")
        return rule

    def _check_alert_rules(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]]
    ) -> None:
        """Check if metric value triggers any alerts."""
        for rule in self._alert_rules.values():
            if rule.metric_name != metric_name:
                continue

            triggered = False
            if rule.condition == ">":
                triggered = value > rule.threshold
            elif rule.condition == "<":
                triggered = value < rule.threshold
            elif rule.condition == ">=":
                triggered = value >= rule.threshold
            elif rule.condition == "<=":
                triggered = value <= rule.threshold
            elif rule.condition == "==":
                triggered = value == rule.threshold

            if triggered:
                self._fire_alert(rule, value, labels)

    def _fire_alert(
        self,
        rule: AlertRule,
        value: float,
        labels: Optional[Dict[str, str]]
    ) -> Alert:
        """Fire an alert based on a rule."""
        # Check if similar alert already exists
        for alert in self._alerts.values():
            if alert.name == rule.name and alert.status == AlertStatus.ACTIVE:
                return alert

        alert = Alert(
            alert_id=str(uuid.uuid4()),
            name=rule.name,
            message=f"Alert: {rule.metric_name} {rule.condition} {rule.threshold} (current: {value})",
            severity=rule.severity,
            labels=labels or {}
        )

        self._alerts[alert.alert_id] = alert

        # Notify handlers
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

        logger.warning(f"Alert fired: {alert.name} - {alert.message}")
        return alert

    def acknowledge_alert(self, alert_id: str) -> Optional[Alert]:
        """Acknowledge an active alert."""
        alert = self._alerts.get(alert_id)
        if alert and alert.status == AlertStatus.ACTIVE:
            alert.status = AlertStatus.ACKNOWLEDGED
            logger.info(f"Alert acknowledged: {alert.name}")
        return alert

    def resolve_alert(self, alert_id: str) -> Optional[Alert]:
        """Resolve an alert."""
        alert = self._alerts.get(alert_id)
        if alert:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            logger.info(f"Alert resolved: {alert.name}")
        return alert

    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return [a for a in self._alerts.values() if a.status == AlertStatus.ACTIVE]

    def register_health_check(
        self,
        name: str,
        check_fn: Callable[[], bool],
        timeout: float = 5.0
    ) -> str:
        """
        Register a health check.

        Implements health_checks.
        """
        check_id = str(uuid.uuid4())

        def wrapped_check():
            start = time.time()
            try:
                result = check_fn()
                latency = (time.time() - start) * 1000
                status = HealthStatus.HEALTHY if result else HealthStatus.UNHEALTHY
            except Exception as e:
                latency = (time.time() - start) * 1000
                status = HealthStatus.UNHEALTHY
                logger.error(f"Health check '{name}' failed: {e}")

            return HealthCheck(
                check_id=check_id,
                name=name,
                status=status,
                latency_ms=latency,
                details={"error": str(e) if status == HealthStatus.UNHEALTHY else None}
            )

        # Store check function reference
        self._health_checks[check_id] = wrapped_check

        logger.info(f"Health check registered: {name}")
        return check_id

    def run_health_checks(self) -> Dict[str, HealthCheck]:
        """Run all registered health checks."""
        results = {}
        for check_id, check_fn in self._health_checks.items():
            if callable(check_fn):
                results[check_id] = check_fn()
        return results

    def get_overall_health(self) -> HealthStatus:
        """Get overall system health."""
        results = self.run_health_checks()

        if not results:
            return HealthStatus.HEALTHY

        statuses = [r.status for r in results.values()]

        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        if HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY

    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add a handler for alert notifications."""
        self._alert_handlers.append(handler)

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get data for monitoring dashboard.

        Aggregates metrics, alerts, and health status.
        """
        return {
            "service": self.service_name,
            "timestamp": datetime.utcnow().isoformat(),
            "health": {
                "overall": self.get_overall_health().value,
                "checks": {
                    check.name: check.status.value
                    for check in self.run_health_checks().values()
                }
            },
            "alerts": {
                "active_count": len(self.get_active_alerts()),
                "by_severity": {
                    s.value: len([a for a in self.get_active_alerts() if a.severity == s])
                    for s in AlertSeverity
                }
            },
            "metrics": {
                "gauges": dict(self._gauges),
                "counters": dict(self._counters)
            },
            "logs": {
                "total": len(self._logs),
                "errors": len([l for l in self._logs if l.level == "error"])
            }
        }


# Factory function
def create_monitoring_service(service_name: str = "maestro") -> MonitoringService:
    """Create a new MonitoringService instance."""
    return MonitoringService(service_name=service_name)
