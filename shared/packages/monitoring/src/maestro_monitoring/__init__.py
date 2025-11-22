"""
MAESTRO Monitoring Library

Enterprise-grade monitoring and observability with Prometheus metrics,
OpenTelemetry tracing, and Grafana dashboards. Follows CNCF standards
and patterns used by companies like Google, Uber, and Netflix.

Usage:
    from maestro_monitoring import MonitoringManager, metrics, tracing

    # Initialize monitoring
    monitoring = MonitoringManager(
        service_name="my-service",
        prometheus_port=9090,
        otlp_endpoint="http://jaeger:14268/api/traces"
    )

    # Start monitoring
    await monitoring.start()

    # Use metrics
    from maestro_monitoring.metrics import counter, histogram, gauge

    request_counter = counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "status"]
    )

    request_duration = histogram(
        "http_request_duration_seconds",
        "HTTP request duration"
    )

    # Use tracing
    from maestro_monitoring.tracing import trace, get_tracer

    tracer = get_tracer(__name__)

    @trace("process_request")
    async def process_request():
        with tracer.start_as_current_span("database_query"):
            # Database operation
            pass
"""

from .manager import MonitoringManager
from .metrics import (
    MetricsManager,
    counter,
    histogram,
    gauge,
    summary,
    info
)
from .tracing import (
    TracingManager,
    trace,
    get_tracer,
    get_current_span,
    add_span_attribute,
    record_exception
)
from .health import HealthCheckManager, HealthCheck
from .alerts import AlertManager, Alert, AlertRule
from .dashboards import DashboardManager, GrafanaDashboard
from .system import SystemMetrics, ResourceMonitor
from .business import BusinessMetrics, KPITracker

__version__ = "1.0.0"
__all__ = [
    # Core management
    "MonitoringManager",

    # Metrics
    "MetricsManager",
    "counter",
    "histogram",
    "gauge",
    "summary",
    "info",

    # Tracing
    "TracingManager",
    "trace",
    "get_tracer",
    "get_current_span",
    "add_span_attribute",
    "record_exception",

    # Health checks
    "HealthCheckManager",
    "HealthCheck",

    # Alerting
    "AlertManager",
    "Alert",
    "AlertRule",

    # Dashboards
    "DashboardManager",
    "GrafanaDashboard",

    # System monitoring
    "SystemMetrics",
    "ResourceMonitor",

    # Business metrics
    "BusinessMetrics",
    "KPITracker",
]