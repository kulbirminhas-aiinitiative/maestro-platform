"""
Maestro-Hive Prometheus Metrics Module
Epic: MD-1901 - Maestro-Hive Observability Integration
Task: MD-1904 - Add Prometheus metrics to key workflows

Provides:
- Request count and latency metrics
- Audit result counters by verdict type
- Webhook delivery metrics
- Deployment gate metrics
- /metrics endpoint for Prometheus scraping
"""

import functools
import time
from typing import Any, Callable, Optional, TypeVar

from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    Info,
    generate_latest,
)

F = TypeVar("F", bound=Callable[..., Any])


# =============================================================================
# Service Info
# =============================================================================

SERVICE_INFO = Info(
    "maestro_hive",
    "Maestro-Hive service information",
)
SERVICE_INFO.info(
    {
        "version": "1.0.0",
        "service": "maestro-hive",
        "component": "trimodal-validation",
    }
)


# =============================================================================
# Request Metrics
# =============================================================================

REQUEST_COUNT = Counter(
    "maestro_hive_requests_total",
    "Total number of requests",
    ["method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "maestro_hive_request_latency_seconds",
    "Request latency in seconds",
    ["method", "endpoint"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

REQUEST_IN_PROGRESS = Gauge(
    "maestro_hive_requests_in_progress",
    "Number of requests currently being processed",
    ["method", "endpoint"],
)


# =============================================================================
# Audit Metrics
# =============================================================================

AUDIT_COUNT = Counter(
    "maestro_hive_audits_total",
    "Total number of trimodal audits",
    ["verdict", "can_deploy"],
)

AUDIT_STREAM_RESULTS = Counter(
    "maestro_hive_audit_stream_results_total",
    "Audit results by stream",
    ["stream", "passed"],
)

AUDIT_LATENCY = Histogram(
    "maestro_hive_audit_latency_seconds",
    "Trimodal audit latency in seconds",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)


# =============================================================================
# Deployment Gate Metrics
# =============================================================================

GATE_CHECK_COUNT = Counter(
    "maestro_hive_gate_checks_total",
    "Total number of deployment gate checks",
    ["result"],  # allowed, blocked, override
)

GATE_CHECK_LATENCY = Histogram(
    "maestro_hive_gate_check_latency_seconds",
    "Deployment gate check latency in seconds",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0),
)


# =============================================================================
# Webhook Metrics
# =============================================================================

WEBHOOK_DELIVERY_COUNT = Counter(
    "maestro_hive_webhook_deliveries_total",
    "Total number of webhook delivery attempts",
    ["event_type", "success"],
)

WEBHOOK_DELIVERY_LATENCY = Histogram(
    "maestro_hive_webhook_delivery_latency_seconds",
    "Webhook delivery latency in seconds",
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


# =============================================================================
# Storage Metrics
# =============================================================================

STORAGE_OPERATIONS = Counter(
    "maestro_hive_storage_operations_total",
    "Total number of storage operations",
    ["operation", "success"],
)

STORAGE_SIZE = Gauge(
    "maestro_hive_storage_size_bytes",
    "Size of storage files in bytes",
    ["file_type"],
)


# =============================================================================
# Metrics Registry
# =============================================================================


class MetricsRegistry:
    """
    Central registry for all Maestro-Hive metrics.

    Provides convenience methods for recording metrics
    and generating Prometheus output.
    """

    @staticmethod
    def record_request(method: str, endpoint: str, status: int, latency: float) -> None:
        """Record a request with its status and latency."""
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=str(status)).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(latency)

    @staticmethod
    def record_audit(verdict: str, can_deploy: bool, latency: float) -> None:
        """Record a trimodal audit result."""
        AUDIT_COUNT.labels(verdict=verdict, can_deploy=str(can_deploy).lower()).inc()
        AUDIT_LATENCY.observe(latency)

    @staticmethod
    def record_stream_result(stream: str, passed: bool) -> None:
        """Record an individual stream (DDE/BDV/ACC) result."""
        AUDIT_STREAM_RESULTS.labels(stream=stream, passed=str(passed).lower()).inc()

    @staticmethod
    def record_gate_check(result: str, latency: float) -> None:
        """Record a deployment gate check."""
        GATE_CHECK_COUNT.labels(result=result).inc()
        GATE_CHECK_LATENCY.observe(latency)

    @staticmethod
    def record_webhook_delivery(event_type: str, success: bool, latency: float) -> None:
        """Record a webhook delivery attempt."""
        WEBHOOK_DELIVERY_COUNT.labels(event_type=event_type, success=str(success).lower()).inc()
        WEBHOOK_DELIVERY_LATENCY.observe(latency)

    @staticmethod
    def record_storage_operation(operation: str, success: bool) -> None:
        """Record a storage operation."""
        STORAGE_OPERATIONS.labels(operation=operation, success=str(success).lower()).inc()

    @staticmethod
    def set_storage_size(file_type: str, size_bytes: int) -> None:
        """Set the current storage size for a file type."""
        STORAGE_SIZE.labels(file_type=file_type).set(size_bytes)

    @staticmethod
    def generate_metrics() -> bytes:
        """Generate Prometheus metrics output."""
        return generate_latest()

    @staticmethod
    def get_content_type() -> str:
        """Get the content type for Prometheus metrics."""
        return CONTENT_TYPE_LATEST


# Global metrics instance
_metrics: Optional[MetricsRegistry] = None


def get_metrics() -> MetricsRegistry:
    """Get the global metrics registry instance."""
    global _metrics
    if _metrics is None:
        _metrics = MetricsRegistry()
    return _metrics


# =============================================================================
# Convenience Functions
# =============================================================================


def record_audit_result(
    iteration_id: str,
    verdict: str,
    can_deploy: bool,
    dde_passed: Optional[bool] = None,
    bdv_passed: Optional[bool] = None,
    acc_passed: Optional[bool] = None,
    latency: Optional[float] = None,
) -> None:
    """
    Record a complete trimodal audit result.

    Args:
        iteration_id: Execution iteration ID
        verdict: Audit verdict
        can_deploy: Whether deployment is allowed
        dde_passed: DDE stream result
        bdv_passed: BDV stream result
        acc_passed: ACC stream result
        latency: Audit duration in seconds
    """
    metrics = get_metrics()

    # Record main audit result
    metrics.record_audit(verdict, can_deploy, latency or 0)

    # Record individual stream results
    if dde_passed is not None:
        metrics.record_stream_result("dde", dde_passed)
    if bdv_passed is not None:
        metrics.record_stream_result("bdv", bdv_passed)
    if acc_passed is not None:
        metrics.record_stream_result("acc", acc_passed)


def record_request_latency(method: str, endpoint: str) -> Callable[[F], F]:
    """
    Decorator to record request latency.

    Args:
        method: HTTP method
        endpoint: API endpoint path

    Returns:
        Decorated function

    Example:
        @record_request_latency("POST", "/api/audit")
        async def audit_endpoint():
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
            start = time.perf_counter()
            status = 200
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception:
                status = 500
                raise
            finally:
                latency = time.perf_counter() - start
                REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
                get_metrics().record_request(method, endpoint, status, latency)

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).inc()
            start = time.perf_counter()
            status = 200
            try:
                result = func(*args, **kwargs)
                return result
            except Exception:
                status = 500
                raise
            finally:
                latency = time.perf_counter() - start
                REQUEST_IN_PROGRESS.labels(method=method, endpoint=endpoint).dec()
                get_metrics().record_request(method, endpoint, status, latency)

        import asyncio

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    return decorator


# =============================================================================
# FastAPI Integration
# =============================================================================


def create_metrics_endpoint():
    """
    Create a FastAPI endpoint for Prometheus metrics.

    Returns:
        FastAPI Response with metrics

    Example:
        from fastapi import FastAPI
        from observability.metrics import create_metrics_endpoint

        app = FastAPI()

        @app.get("/metrics")
        async def metrics():
            return create_metrics_endpoint()
    """
    from fastapi.responses import Response

    return Response(
        content=get_metrics().generate_metrics(),
        media_type=get_metrics().get_content_type(),
    )
