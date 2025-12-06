"""
Orchestrator Health Monitor (MD-2127)

Provides health monitoring for the workflow orchestrator:
- Health check endpoint
- Metrics tracking: active workflows, phase distribution, failure rate
- Alerting integration
"""

import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
from threading import Lock

from .event_bus import EventBus, Event, EventType, get_event_bus

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class MetricPoint:
    """A single metric data point"""
    value: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class WorkflowMetrics:
    """Metrics for a single workflow"""
    workflow_id: str
    state: str
    phase: str
    started_at: datetime
    duration_seconds: float = 0.0
    task_count: int = 0
    error_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'workflow_id': self.workflow_id,
            'state': self.state,
            'phase': self.phase,
            'started_at': self.started_at.isoformat(),
            'duration_seconds': self.duration_seconds,
            'task_count': self.task_count,
            'error_count': self.error_count
        }


@dataclass
class HealthReport:
    """
    Health check report.

    Attributes:
        status: Overall health status
        timestamp: Report timestamp
        active_workflows: Count of active workflows
        phase_distribution: Workflows per phase
        failure_rate: Recent failure rate (0-1)
        avg_duration: Average workflow duration
        components: Individual component health
        alerts: Active alerts
    """
    status: HealthStatus
    timestamp: datetime = field(default_factory=datetime.utcnow)
    active_workflows: int = 0
    phase_distribution: Dict[str, int] = field(default_factory=dict)
    failure_rate: float = 0.0
    success_rate: float = 1.0
    avg_duration_seconds: float = 0.0
    total_completed: int = 0
    total_failed: int = 0
    components: Dict[str, HealthStatus] = field(default_factory=dict)
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    uptime_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'status': self.status.value,
            'timestamp': self.timestamp.isoformat(),
            'active_workflows': self.active_workflows,
            'phase_distribution': self.phase_distribution,
            'failure_rate': self.failure_rate,
            'success_rate': self.success_rate,
            'avg_duration_seconds': self.avg_duration_seconds,
            'total_completed': self.total_completed,
            'total_failed': self.total_failed,
            'components': {k: v.value for k, v in self.components.items()},
            'alerts': self.alerts,
            'uptime_seconds': self.uptime_seconds,
            'metadata': self.metadata
        }


# Alert handler type
AlertHandler = Callable[[str, str, Dict[str, Any]], None]


@dataclass
class AlertConfig:
    """Alert configuration"""
    name: str
    condition: Callable[[HealthReport], bool]
    severity: str = "warning"  # info, warning, critical
    cooldown_seconds: int = 300  # Don't re-alert within this time


class HealthMonitor:
    """
    Health monitoring for the workflow orchestrator.

    Tracks:
    - Active workflow count
    - Phase distribution
    - Success/failure rates
    - Average duration
    - Component health

    Provides:
    - Health check endpoint
    - Metrics collection
    - Alert generation
    """

    def __init__(
        self,
        event_bus: Optional[EventBus] = None,
        failure_threshold: float = 0.2,
        degraded_threshold: float = 0.1,
        max_active_workflows: int = 100,
        metrics_retention_hours: int = 24
    ):
        """
        Initialize the health monitor.

        Args:
            event_bus: Event bus to subscribe to
            failure_threshold: Failure rate threshold for UNHEALTHY
            degraded_threshold: Failure rate threshold for DEGRADED
            max_active_workflows: Maximum active workflows (alert if exceeded)
            metrics_retention_hours: How long to retain metrics
        """
        self.event_bus = event_bus or get_event_bus()
        self.failure_threshold = failure_threshold
        self.degraded_threshold = degraded_threshold
        self.max_active_workflows = max_active_workflows
        self.metrics_retention_hours = metrics_retention_hours

        self._started_at = datetime.utcnow()
        self._lock = Lock()

        # Metrics storage
        self._active_workflows: Dict[str, WorkflowMetrics] = {}
        self._completed_workflows: List[WorkflowMetrics] = []
        self._phase_counts: Dict[str, int] = defaultdict(int)
        self._total_completed = 0
        self._total_failed = 0
        self._durations: List[float] = []

        # Alerting
        self._alert_configs: List[AlertConfig] = []
        self._alert_handlers: List[AlertHandler] = []
        self._last_alerts: Dict[str, datetime] = {}

        # Component health
        self._component_health: Dict[str, HealthStatus] = {
            'event_bus': HealthStatus.HEALTHY,
            'orchestrator': HealthStatus.HEALTHY,
            'governance': HealthStatus.HEALTHY,
            'documentation': HealthStatus.HEALTHY,
            'task_management': HealthStatus.HEALTHY
        }

        # Subscribe to events
        self._subscribe_to_events()

        # Register default alerts
        self._register_default_alerts()

        logger.info("HealthMonitor initialized")

    def _subscribe_to_events(self) -> None:
        """Subscribe to orchestrator events"""
        self.event_bus.subscribe(EventType.WORKFLOW_STARTED, self._on_workflow_started)
        self.event_bus.subscribe(EventType.WORKFLOW_COMPLETED, self._on_workflow_completed)
        self.event_bus.subscribe(EventType.WORKFLOW_FAILED, self._on_workflow_failed)
        self.event_bus.subscribe(EventType.PHASE_STARTED, self._on_phase_started)
        self.event_bus.subscribe(EventType.PHASE_COMPLETED, self._on_phase_completed)
        self.event_bus.subscribe(EventType.PHASE_FAILED, self._on_phase_failed)
        self.event_bus.subscribe(EventType.ERROR_OCCURRED, self._on_error)

    def _register_default_alerts(self) -> None:
        """Register default alert configurations"""
        # High failure rate alert
        self.register_alert(AlertConfig(
            name="high_failure_rate",
            condition=lambda r: r.failure_rate > self.failure_threshold,
            severity="critical",
            cooldown_seconds=600
        ))

        # Degraded failure rate alert
        self.register_alert(AlertConfig(
            name="elevated_failure_rate",
            condition=lambda r: r.failure_rate > self.degraded_threshold,
            severity="warning",
            cooldown_seconds=300
        ))

        # Too many active workflows
        self.register_alert(AlertConfig(
            name="high_workflow_count",
            condition=lambda r: r.active_workflows > self.max_active_workflows,
            severity="warning",
            cooldown_seconds=300
        ))

    def _on_workflow_started(self, event: Event) -> None:
        """Handle workflow started event"""
        with self._lock:
            metrics = WorkflowMetrics(
                workflow_id=event.workflow_id,
                state='running',
                phase='started',
                started_at=event.timestamp
            )
            self._active_workflows[event.workflow_id] = metrics

    def _on_workflow_completed(self, event: Event) -> None:
        """Handle workflow completed event"""
        with self._lock:
            if event.workflow_id in self._active_workflows:
                metrics = self._active_workflows.pop(event.workflow_id)
                metrics.state = 'completed'
                metrics.duration_seconds = (
                    datetime.utcnow() - metrics.started_at
                ).total_seconds()
                self._completed_workflows.append(metrics)
                self._durations.append(metrics.duration_seconds)
                self._total_completed += 1

    def _on_workflow_failed(self, event: Event) -> None:
        """Handle workflow failed event"""
        with self._lock:
            if event.workflow_id in self._active_workflows:
                metrics = self._active_workflows.pop(event.workflow_id)
                metrics.state = 'failed'
                metrics.error_count += 1
                self._completed_workflows.append(metrics)
                self._total_failed += 1

    def _on_phase_started(self, event: Event) -> None:
        """Handle phase started event"""
        with self._lock:
            if event.workflow_id in self._active_workflows:
                self._active_workflows[event.workflow_id].phase = event.phase or 'unknown'
            if event.phase:
                self._phase_counts[event.phase] += 1

    def _on_phase_completed(self, event: Event) -> None:
        """Handle phase completed event"""
        pass  # Phase transition tracked in phase_started

    def _on_phase_failed(self, event: Event) -> None:
        """Handle phase failed event"""
        with self._lock:
            if event.workflow_id in self._active_workflows:
                self._active_workflows[event.workflow_id].error_count += 1

    def _on_error(self, event: Event) -> None:
        """Handle error event"""
        with self._lock:
            if event.workflow_id in self._active_workflows:
                self._active_workflows[event.workflow_id].error_count += 1

    def register_alert(self, config: AlertConfig) -> None:
        """Register an alert configuration"""
        self._alert_configs.append(config)
        logger.debug(f"Alert registered: {config.name}")

    def add_alert_handler(self, handler: AlertHandler) -> None:
        """Add a handler for alerts"""
        self._alert_handlers.append(handler)

    def set_component_health(
        self,
        component: str,
        status: HealthStatus
    ) -> None:
        """Set health status for a component"""
        with self._lock:
            self._component_health[component] = status

    def check_health(self) -> HealthReport:
        """
        Perform a health check.

        Returns:
            HealthReport with current health status
        """
        with self._lock:
            # Calculate metrics
            active_count = len(self._active_workflows)
            total = self._total_completed + self._total_failed
            failure_rate = self._total_failed / total if total > 0 else 0.0
            success_rate = 1.0 - failure_rate
            avg_duration = sum(self._durations) / len(self._durations) if self._durations else 0.0

            # Phase distribution
            phase_dist = {}
            for wf in self._active_workflows.values():
                phase_dist[wf.phase] = phase_dist.get(wf.phase, 0) + 1

            # Determine overall status
            if failure_rate >= self.failure_threshold:
                status = HealthStatus.UNHEALTHY
            elif failure_rate >= self.degraded_threshold:
                status = HealthStatus.DEGRADED
            elif any(h == HealthStatus.UNHEALTHY for h in self._component_health.values()):
                status = HealthStatus.DEGRADED
            else:
                status = HealthStatus.HEALTHY

            uptime = (datetime.utcnow() - self._started_at).total_seconds()

            report = HealthReport(
                status=status,
                active_workflows=active_count,
                phase_distribution=phase_dist,
                failure_rate=failure_rate,
                success_rate=success_rate,
                avg_duration_seconds=avg_duration,
                total_completed=self._total_completed,
                total_failed=self._total_failed,
                components=self._component_health.copy(),
                uptime_seconds=uptime
            )

        # Check alerts (outside lock)
        self._check_alerts(report)

        return report

    def _check_alerts(self, report: HealthReport) -> None:
        """Check alert conditions and fire alerts"""
        now = datetime.utcnow()

        for config in self._alert_configs:
            try:
                if config.condition(report):
                    # Check cooldown
                    last = self._last_alerts.get(config.name)
                    if last and (now - last).total_seconds() < config.cooldown_seconds:
                        continue

                    # Fire alert
                    self._last_alerts[config.name] = now
                    alert_data = {
                        'name': config.name,
                        'severity': config.severity,
                        'timestamp': now.isoformat(),
                        'report': report.to_dict()
                    }

                    report.alerts.append(alert_data)

                    for handler in self._alert_handlers:
                        try:
                            handler(config.name, config.severity, alert_data)
                        except Exception as e:
                            logger.error(f"Alert handler error: {e}")

            except Exception as e:
                logger.error(f"Alert check error for {config.name}: {e}")

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get detailed metrics.

        Returns:
            Dictionary with all metrics
        """
        with self._lock:
            active_list = [m.to_dict() for m in self._active_workflows.values()]
            recent_completed = [
                m.to_dict() for m in self._completed_workflows[-100:]
            ]

            return {
                'active_workflows': active_list,
                'recent_completed': recent_completed,
                'phase_distribution': dict(self._phase_counts),
                'total_completed': self._total_completed,
                'total_failed': self._total_failed,
                'durations': {
                    'avg': sum(self._durations) / len(self._durations) if self._durations else 0,
                    'min': min(self._durations) if self._durations else 0,
                    'max': max(self._durations) if self._durations else 0,
                    'count': len(self._durations)
                }
            }

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get status for a specific workflow"""
        with self._lock:
            if workflow_id in self._active_workflows:
                return self._active_workflows[workflow_id].to_dict()
        return None

    def reset_metrics(self) -> None:
        """Reset all metrics (for testing)"""
        with self._lock:
            self._active_workflows.clear()
            self._completed_workflows.clear()
            self._phase_counts.clear()
            self._total_completed = 0
            self._total_failed = 0
            self._durations.clear()
            self._last_alerts.clear()

        logger.info("Metrics reset")

    def cleanup_old_metrics(self) -> int:
        """
        Clean up metrics older than retention period.

        Returns:
            Number of metrics cleaned up
        """
        cutoff = datetime.utcnow() - timedelta(hours=self.metrics_retention_hours)
        count = 0

        with self._lock:
            original_len = len(self._completed_workflows)
            self._completed_workflows = [
                m for m in self._completed_workflows
                if m.started_at >= cutoff
            ]
            count = original_len - len(self._completed_workflows)

        if count > 0:
            logger.info(f"Cleaned up {count} old metrics")

        return count


# Singleton instance
_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get the default health monitor instance"""
    global _monitor
    if _monitor is None:
        _monitor = HealthMonitor()
    return _monitor


def check_health() -> HealthReport:
    """Convenience function to check health"""
    return get_health_monitor().check_health()


def get_metrics() -> Dict[str, Any]:
    """Convenience function to get metrics"""
    return get_health_monitor().get_metrics()
