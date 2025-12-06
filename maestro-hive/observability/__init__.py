"""
Maestro-Hive Observability Module
Epic: MD-1901 - Maestro-Hive Observability Integration

Provides structured logging, Prometheus metrics, and OpenTelemetry tracing
for the Maestro-Hive AI Team Orchestration Engine.
"""

from observability.logging import (
    configure_logging,
    get_logger,
    mask_sensitive_data,
)
from observability.metrics import (
    MetricsRegistry,
    get_metrics,
    record_audit_result,
    record_request_latency,
)
from observability.tracing import (
    TracingConfig,
    configure_tracing,
    get_tracer,
    trace_function,
)

__all__ = [
    # Logging
    "configure_logging",
    "get_logger",
    "mask_sensitive_data",
    # Metrics
    "MetricsRegistry",
    "get_metrics",
    "record_audit_result",
    "record_request_latency",
    # Tracing
    "TracingConfig",
    "configure_tracing",
    "get_tracer",
    "trace_function",
]
