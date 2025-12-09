#!/usr/bin/env python3
"""
Health Monitor: System health monitoring and self-healing triggers.

This module provides comprehensive health monitoring for Maestro components
with support for custom health checks, metrics collection, alerting, and
self-healing trigger mechanisms.
"""

import asyncio
import threading
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status of a component."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class AlertSeverity(Enum):
    """Severity of health alerts."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    component: str
    status: HealthStatus
    message: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['status'] = self.status.value
        return data


@dataclass
class HealthMetric:
    """A health metric measurement."""
    name: str
    value: float
    unit: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class Alert:
    """A health alert."""
    id: str
    component: str
    severity: AlertSeverity
    message: str
    triggered_at: str
    resolved_at: Optional[str] = None
    acknowledged: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComponentConfig:
    """Configuration for a monitored component."""
    name: str
    check_function: Callable[[], HealthCheckResult]
    check_interval_seconds: int = 30
    timeout_seconds: int = 10
    failure_threshold: int = 3
    recovery_threshold: int = 2
    enabled: bool = True
    self_heal_function: Optional[Callable[[], bool]] = None


class HealthMonitor:
    """
    System health monitoring and self-healing triggers.

    Features:
    - Component health checks with configurable intervals
    - Performance metrics collection
    - Threshold-based alerting
    - Self-healing trigger mechanisms
    - Health history and trends
    """

    _instance: Optional['HealthMonitor'] = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        check_interval_seconds: int = 30,
        history_size: int = 1000,
        enable_self_healing: bool = True
    ):
        """
        Initialize the health monitor.

        Args:
            check_interval_seconds: Default interval between health checks
            history_size: Number of health check results to retain
            enable_self_healing: Enable automatic self-healing
        """
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.default_interval = check_interval_seconds
        self.history_size = history_size
        self.enable_self_healing = enable_self_healing

        self._components: Dict[str, ComponentConfig] = {}
        self._results: Dict[str, List[HealthCheckResult]] = {}
        self._metrics: Dict[str, List[HealthMetric]] = {}
        self._alerts: Dict[str, Alert] = {}
        self._failure_counts: Dict[str, int] = {}
        self._recovery_counts: Dict[str, int] = {}
        self._alert_handlers: List[Callable[[Alert], None]] = []
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        self._alert_counter = 0
        self._initialized = True

        logger.info("HealthMonitor initialized")

    def register_component(
        self,
        name: str,
        check_function: Callable[[], HealthCheckResult],
        **config_options
    ) -> None:
        """
        Register a component for health monitoring.

        Args:
            name: Component name
            check_function: Function that returns HealthCheckResult
            **config_options: Additional ComponentConfig options
        """
        config = ComponentConfig(
            name=name,
            check_function=check_function,
            **config_options
        )

        with self._lock:
            self._components[name] = config
            self._results[name] = []
            self._failure_counts[name] = 0
            self._recovery_counts[name] = 0

        logger.info(f"Component registered: {name}")

    def unregister_component(self, name: str) -> bool:
        """
        Unregister a component.

        Args:
            name: Component name

        Returns:
            True if component was found and removed
        """
        with self._lock:
            if name not in self._components:
                return False

            del self._components[name]
            self._results.pop(name, None)
            self._failure_counts.pop(name, None)
            self._recovery_counts.pop(name, None)

        logger.info(f"Component unregistered: {name}")
        return True

    def check_health(self, component: Optional[str] = None) -> Dict[str, HealthCheckResult]:
        """
        Run health checks.

        Args:
            component: Specific component to check (all if None)

        Returns:
            Dictionary of component -> HealthCheckResult
        """
        results = {}

        components_to_check = (
            {component: self._components[component]}
            if component and component in self._components
            else self._components
        )

        for name, config in components_to_check.items():
            if not config.enabled:
                continue

            start_time = time.time()
            try:
                result = self._execute_check(config)
            except Exception as e:
                result = HealthCheckResult(
                    component=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {str(e)}"
                )

            result.latency_ms = (time.time() - start_time) * 1000
            results[name] = result

            # Store result
            self._store_result(name, result)

            # Process result for alerting
            self._process_result(name, config, result)

        return results

    def get_status(self) -> Dict[str, Any]:
        """
        Get overall system health status.

        Returns:
            System health summary
        """
        with self._lock:
            component_statuses = {}
            for name, results in self._results.items():
                if results:
                    latest = results[-1]
                    component_statuses[name] = {
                        "status": latest.status.value,
                        "message": latest.message,
                        "last_check": latest.timestamp,
                        "latency_ms": latest.latency_ms
                    }

            # Determine overall status
            statuses = [HealthStatus(s["status"]) for s in component_statuses.values()]
            if not statuses:
                overall = HealthStatus.UNKNOWN
            elif any(s == HealthStatus.UNHEALTHY for s in statuses):
                overall = HealthStatus.UNHEALTHY
            elif any(s == HealthStatus.DEGRADED for s in statuses):
                overall = HealthStatus.DEGRADED
            else:
                overall = HealthStatus.HEALTHY

            active_alerts = sum(1 for a in self._alerts.values() if not a.resolved_at)

            return {
                "overall_status": overall.value,
                "components": component_statuses,
                "active_alerts": active_alerts,
                "timestamp": datetime.utcnow().isoformat()
            }

    def get_component_history(
        self,
        component: str,
        limit: int = 100
    ) -> List[HealthCheckResult]:
        """
        Get health check history for a component.

        Args:
            component: Component name
            limit: Maximum results to return

        Returns:
            List of HealthCheckResults (most recent first)
        """
        with self._lock:
            results = self._results.get(component, [])
            return list(reversed(results[-limit:]))

    def record_metric(
        self,
        name: str,
        value: float,
        unit: str = "",
        **tags
    ) -> None:
        """
        Record a health metric.

        Args:
            name: Metric name
            value: Metric value
            unit: Unit of measurement
            **tags: Additional tags
        """
        metric = HealthMetric(
            name=name,
            value=value,
            unit=unit,
            tags=tags
        )

        with self._lock:
            if name not in self._metrics:
                self._metrics[name] = []

            self._metrics[name].append(metric)

            # Trim history
            if len(self._metrics[name]) > self.history_size:
                self._metrics[name] = self._metrics[name][-self.history_size:]

    def get_metrics(
        self,
        name: Optional[str] = None,
        since: Optional[str] = None
    ) -> Dict[str, List[HealthMetric]]:
        """
        Get recorded metrics.

        Args:
            name: Specific metric name (all if None)
            since: Filter by time (ISO format)

        Returns:
            Dictionary of metric_name -> List[HealthMetric]
        """
        with self._lock:
            if name:
                metrics = {name: self._metrics.get(name, [])}
            else:
                metrics = dict(self._metrics)

            if since:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
                filtered = {}
                for metric_name, metric_list in metrics.items():
                    filtered[metric_name] = [
                        m for m in metric_list
                        if datetime.fromisoformat(m.timestamp.replace('Z', '+00:00')) >= since_dt
                    ]
                return filtered

            return metrics

    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add a handler for health alerts."""
        self._alert_handlers.append(handler)

    def get_alerts(
        self,
        include_resolved: bool = False,
        component: Optional[str] = None
    ) -> List[Alert]:
        """
        Get health alerts.

        Args:
            include_resolved: Include resolved alerts
            component: Filter by component

        Returns:
            List of alerts
        """
        with self._lock:
            alerts = list(self._alerts.values())

            if not include_resolved:
                alerts = [a for a in alerts if not a.resolved_at]

            if component:
                alerts = [a for a in alerts if a.component == component]

            return sorted(alerts, key=lambda a: a.triggered_at, reverse=True)

    def acknowledge_alert(self, alert_id: str) -> bool:
        """
        Acknowledge an alert.

        Args:
            alert_id: Alert ID

        Returns:
            True if alert was found and acknowledged
        """
        with self._lock:
            if alert_id in self._alerts:
                self._alerts[alert_id].acknowledged = True
                logger.info(f"Alert acknowledged: {alert_id}")
                return True
            return False

    def start(self) -> None:
        """Start background health monitoring."""
        if self._running:
            return

        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("Health monitoring started")

    def stop(self) -> None:
        """Stop background health monitoring."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        logger.info("Health monitoring stopped")

    def trigger_self_heal(self, component: str) -> bool:
        """
        Manually trigger self-healing for a component.

        Args:
            component: Component name

        Returns:
            True if self-healing succeeded
        """
        with self._lock:
            config = self._components.get(component)
            if not config or not config.self_heal_function:
                logger.warning(f"No self-heal function for component: {component}")
                return False

        try:
            result = config.self_heal_function()
            if result:
                logger.info(f"Self-healing succeeded for {component}")
            else:
                logger.warning(f"Self-healing failed for {component}")
            return result
        except Exception as e:
            logger.error(f"Self-healing error for {component}: {e}")
            return False

    def _execute_check(self, config: ComponentConfig) -> HealthCheckResult:
        """Execute a health check with timeout."""
        # Simple synchronous execution
        # In production, would use asyncio with timeout
        return config.check_function()

    def _store_result(self, component: str, result: HealthCheckResult) -> None:
        """Store a health check result."""
        with self._lock:
            if component not in self._results:
                self._results[component] = []

            self._results[component].append(result)

            # Trim history
            if len(self._results[component]) > self.history_size:
                self._results[component] = self._results[component][-self.history_size:]

    def _process_result(
        self,
        component: str,
        config: ComponentConfig,
        result: HealthCheckResult
    ) -> None:
        """Process health check result for alerting and self-healing."""
        with self._lock:
            if result.status == HealthStatus.UNHEALTHY:
                self._failure_counts[component] = self._failure_counts.get(component, 0) + 1
                self._recovery_counts[component] = 0

                if self._failure_counts[component] >= config.failure_threshold:
                    self._trigger_alert(component, result)

                    if self.enable_self_healing and config.self_heal_function:
                        self._attempt_self_heal(component, config)

            elif result.status == HealthStatus.HEALTHY:
                self._recovery_counts[component] = self._recovery_counts.get(component, 0) + 1

                if self._recovery_counts[component] >= config.recovery_threshold:
                    self._resolve_alerts(component)
                    self._failure_counts[component] = 0

    def _trigger_alert(self, component: str, result: HealthCheckResult) -> None:
        """Trigger a health alert."""
        self._alert_counter += 1
        alert_id = f"ALERT-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._alert_counter:04d}"

        # Check if there's already an active alert for this component
        for existing in self._alerts.values():
            if existing.component == component and not existing.resolved_at:
                return  # Don't create duplicate alerts

        alert = Alert(
            id=alert_id,
            component=component,
            severity=AlertSeverity.CRITICAL if result.status == HealthStatus.UNHEALTHY else AlertSeverity.WARNING,
            message=result.message,
            triggered_at=datetime.utcnow().isoformat(),
            metadata=result.metadata
        )

        self._alerts[alert_id] = alert

        # Notify handlers
        for handler in self._alert_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

        logger.warning(f"Health alert triggered: {component} - {result.message}")

    def _resolve_alerts(self, component: str) -> None:
        """Resolve active alerts for a component."""
        resolved_time = datetime.utcnow().isoformat()

        for alert in self._alerts.values():
            if alert.component == component and not alert.resolved_at:
                alert.resolved_at = resolved_time
                logger.info(f"Alert resolved: {alert.id}")

    def _attempt_self_heal(self, component: str, config: ComponentConfig) -> None:
        """Attempt self-healing for a component."""
        logger.info(f"Attempting self-healing for {component}")

        try:
            success = config.self_heal_function()
            if success:
                logger.info(f"Self-healing succeeded for {component}")
            else:
                logger.warning(f"Self-healing failed for {component}")
        except Exception as e:
            logger.error(f"Self-healing error for {component}: {e}")

    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                with self._lock:
                    components = dict(self._components)

                for name, config in components.items():
                    if not config.enabled:
                        continue

                    # Check if it's time to run this check
                    # (simplified - production would track last check time)
                    self.check_health(name)

                time.sleep(self.default_interval)

            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                time.sleep(5)


# Convenience function
def get_health_monitor(**kwargs) -> HealthMonitor:
    """Get the singleton HealthMonitor instance."""
    return HealthMonitor(**kwargs)


# Default health check functions
def create_http_health_check(url: str, timeout: int = 5) -> Callable[[], HealthCheckResult]:
    """Create an HTTP health check function."""
    def check() -> HealthCheckResult:
        import urllib.request
        import urllib.error

        try:
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, timeout=timeout) as response:
                if response.status == 200:
                    return HealthCheckResult(
                        component=url,
                        status=HealthStatus.HEALTHY,
                        message="HTTP check passed"
                    )
                else:
                    return HealthCheckResult(
                        component=url,
                        status=HealthStatus.DEGRADED,
                        message=f"HTTP status: {response.status}"
                    )
        except urllib.error.URLError as e:
            return HealthCheckResult(
                component=url,
                status=HealthStatus.UNHEALTHY,
                message=f"HTTP check failed: {str(e)}"
            )

    return check


def create_process_health_check(process_name: str) -> Callable[[], HealthCheckResult]:
    """Create a process health check function."""
    def check() -> HealthCheckResult:
        import subprocess
        result = subprocess.run(['pgrep', '-f', process_name], capture_output=True)
        if result.returncode == 0:
            return HealthCheckResult(
                component=process_name,
                status=HealthStatus.HEALTHY,
                message=f"Process {process_name} is running"
            )
        else:
            return HealthCheckResult(
                component=process_name,
                status=HealthStatus.UNHEALTHY,
                message=f"Process {process_name} not found"
            )

    return check
