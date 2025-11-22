"""
Enterprise monitoring manager with integrated observability stack.
"""

import asyncio
from typing import Optional, Dict, Any, List
from prometheus_client import start_http_server, REGISTRY
from opentelemetry import trace, metrics as otel_metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from maestro_core_logging import get_logger

from .metrics import MetricsManager
from .tracing import TracingManager
from .health import HealthCheckManager
from .alerts import AlertManager
from .system import SystemMetrics
from .business import BusinessMetrics


class MonitoringManager:
    """
    Comprehensive monitoring manager for enterprise applications.

    Features:
    - Prometheus metrics collection and export
    - OpenTelemetry distributed tracing
    - Health checks and service status
    - System resource monitoring
    - Business metrics and KPIs
    - Alert management and notification
    - Auto-instrumentation for common frameworks
    """

    def __init__(
        self,
        service_name: str,
        service_version: str = "unknown",
        environment: str = "production",
        prometheus_port: int = 9090,
        prometheus_path: str = "/metrics",
        otlp_endpoint: Optional[str] = None,
        jaeger_endpoint: Optional[str] = None,
        enable_system_metrics: bool = True,
        enable_business_metrics: bool = True,
        enable_auto_instrumentation: bool = True,
        health_check_interval: int = 30,
        resource_attributes: Optional[Dict[str, str]] = None
    ):
        """
        Initialize monitoring manager.

        Args:
            service_name: Name of the service
            service_version: Version of the service
            environment: Environment (dev/staging/prod)
            prometheus_port: Port for Prometheus metrics server
            prometheus_path: Path for metrics endpoint
            otlp_endpoint: OTLP endpoint for traces
            jaeger_endpoint: Jaeger endpoint for traces
            enable_system_metrics: Enable system resource monitoring
            enable_business_metrics: Enable business metrics collection
            enable_auto_instrumentation: Enable auto-instrumentation
            health_check_interval: Health check interval in seconds
            resource_attributes: Additional resource attributes
        """
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment
        self.prometheus_port = prometheus_port
        self.prometheus_path = prometheus_path
        self.otlp_endpoint = otlp_endpoint
        self.jaeger_endpoint = jaeger_endpoint
        self.enable_system_metrics = enable_system_metrics
        self.enable_business_metrics = enable_business_metrics
        self.enable_auto_instrumentation = enable_auto_instrumentation
        self.health_check_interval = health_check_interval

        self.logger = get_logger(__name__)

        # Resource attributes
        self.resource_attributes = {
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": environment,
            **(resource_attributes or {})
        }

        # Component managers
        self.metrics_manager: Optional[MetricsManager] = None
        self.tracing_manager: Optional[TracingManager] = None
        self.health_manager: Optional[HealthCheckManager] = None
        self.alert_manager: Optional[AlertManager] = None
        self.system_metrics: Optional[SystemMetrics] = None
        self.business_metrics: Optional[BusinessMetrics] = None

        # State
        self._started = False
        self._prometheus_server_started = False
        self._background_tasks: List[asyncio.Task] = []

    async def start(self) -> None:
        """Start all monitoring components."""
        if self._started:
            return

        try:
            self.logger.info("Starting monitoring manager",
                           service=self.service_name,
                           environment=self.environment)

            # Initialize components
            await self._initialize_components()

            # Start Prometheus server
            await self._start_prometheus_server()

            # Setup auto-instrumentation
            if self.enable_auto_instrumentation:
                await self._setup_auto_instrumentation()

            # Start background tasks
            await self._start_background_tasks()

            self._started = True
            self.logger.info("Monitoring manager started successfully")

        except Exception as e:
            self.logger.error("Failed to start monitoring manager", error=str(e))
            await self.stop()
            raise

    async def _initialize_components(self) -> None:
        """Initialize all monitoring components."""
        # Metrics manager
        self.metrics_manager = MetricsManager(
            service_name=self.service_name,
            registry=REGISTRY
        )

        # Tracing manager
        self.tracing_manager = TracingManager(
            service_name=self.service_name,
            service_version=self.service_version,
            resource_attributes=self.resource_attributes,
            otlp_endpoint=self.otlp_endpoint,
            jaeger_endpoint=self.jaeger_endpoint
        )
        await self.tracing_manager.initialize()

        # Health check manager
        self.health_manager = HealthCheckManager(
            check_interval=self.health_check_interval
        )

        # Alert manager
        self.alert_manager = AlertManager(
            service_name=self.service_name
        )

        # System metrics
        if self.enable_system_metrics:
            self.system_metrics = SystemMetrics(
                metrics_manager=self.metrics_manager
            )
            await self.system_metrics.start()

        # Business metrics
        if self.enable_business_metrics:
            self.business_metrics = BusinessMetrics(
                metrics_manager=self.metrics_manager,
                service_name=self.service_name
            )

    async def _start_prometheus_server(self) -> None:
        """Start Prometheus metrics server."""
        try:
            start_http_server(
                port=self.prometheus_port,
                addr='0.0.0.0',
                registry=REGISTRY
            )
            self._prometheus_server_started = True
            self.logger.info("Prometheus server started",
                           port=self.prometheus_port,
                           path=self.prometheus_path)
        except Exception as e:
            self.logger.error("Failed to start Prometheus server", error=str(e))
            raise

    async def _setup_auto_instrumentation(self) -> None:
        """Setup auto-instrumentation for common frameworks."""
        try:
            # FastAPI instrumentation
            try:
                from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
                FastAPIInstrumentor().instrument()
                self.logger.debug("FastAPI auto-instrumentation enabled")
            except ImportError:
                pass

            # SQLAlchemy instrumentation
            try:
                from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
                SQLAlchemyInstrumentor().instrument()
                self.logger.debug("SQLAlchemy auto-instrumentation enabled")
            except ImportError:
                pass

            # Redis instrumentation
            try:
                from opentelemetry.instrumentation.redis import RedisInstrumentor
                RedisInstrumentor().instrument()
                self.logger.debug("Redis auto-instrumentation enabled")
            except ImportError:
                pass

            # HTTP client instrumentation
            try:
                from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
                HTTPXClientInstrumentor().instrument()
                self.logger.debug("HTTPX auto-instrumentation enabled")
            except ImportError:
                pass

        except Exception as e:
            self.logger.warning("Some auto-instrumentation failed", error=str(e))

    async def _start_background_tasks(self) -> None:
        """Start background monitoring tasks."""
        # Health check task
        if self.health_manager:
            task = asyncio.create_task(self.health_manager.start())
            self._background_tasks.append(task)

        # System metrics collection
        if self.system_metrics:
            task = asyncio.create_task(self.system_metrics.collect_loop())
            self._background_tasks.append(task)

        # Alert monitoring
        if self.alert_manager:
            task = asyncio.create_task(self.alert_manager.start())
            self._background_tasks.append(task)

    async def stop(self) -> None:
        """Stop all monitoring components."""
        if not self._started:
            return

        self.logger.info("Stopping monitoring manager")

        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()

        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)

        # Stop components
        if self.system_metrics:
            await self.system_metrics.stop()

        if self.health_manager:
            await self.health_manager.stop()

        if self.alert_manager:
            await self.alert_manager.stop()

        self._started = False
        self.logger.info("Monitoring manager stopped")

    def add_health_check(self, name: str, check_func, interval: int = 30) -> None:
        """Add a custom health check."""
        if self.health_manager:
            self.health_manager.add_check(name, check_func, interval)

    def add_alert_rule(self, rule) -> None:
        """Add an alert rule."""
        if self.alert_manager:
            self.alert_manager.add_rule(rule)

    def record_business_metric(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict[str, str]] = None
    ) -> None:
        """Record a business metric."""
        if self.business_metrics:
            self.business_metrics.record_metric(metric_name, value, labels)

    async def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        status = {
            "service": self.service_name,
            "version": self.service_version,
            "environment": self.environment,
            "monitoring_started": self._started,
            "prometheus_server": self._prometheus_server_started,
            "components": {}
        }

        if self.health_manager:
            status["components"]["health_checks"] = await self.health_manager.get_status()

        if self.system_metrics:
            status["components"]["system_metrics"] = await self.system_metrics.get_status()

        if self.alert_manager:
            status["components"]["alerts"] = await self.alert_manager.get_status()

        return status

    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics."""
        if not self.metrics_manager:
            return {}

        return {
            "prometheus_metrics": self.metrics_manager.get_metric_count(),
            "system_metrics": await self.system_metrics.get_latest_metrics() if self.system_metrics else {},
            "business_metrics": self.business_metrics.get_latest_metrics() if self.business_metrics else {}
        }

    def __del__(self):
        """Cleanup on destruction."""
        if self._started:
            self.logger.warning("MonitoringManager not properly stopped - call stop() explicitly")