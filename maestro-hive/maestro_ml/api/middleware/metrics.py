"""
Prometheus Metrics Middleware for FastAPI

Collects and exposes metrics for monitoring ML platform operations.
"""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.routing import Match
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
    REGISTRY,
    CollectorRegistry
)
from prometheus_client.multiprocess import MultiProcessCollector


# HTTP Request Metrics
http_requests_total = Counter(
    'maestro_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'maestro_http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

http_requests_in_progress = Gauge(
    'maestro_http_requests_in_progress',
    'HTTP requests currently being processed',
    ['method', 'endpoint']
)

# ML-Specific Metrics
ml_models_total = Gauge(
    'maestro_ml_models_total',
    'Total number of registered models',
    ['tenant_id']
)

ml_model_operations_total = Counter(
    'maestro_ml_model_operations_total',
    'Total model operations',
    ['operation', 'tenant_id', 'status']
)

ml_model_size_bytes = Histogram(
    'maestro_ml_model_size_bytes',
    'Model size in bytes',
    ['tenant_id'],
    buckets=(1e6, 10e6, 100e6, 500e6, 1e9, 5e9, 10e9)  # 1MB to 10GB
)

ml_experiments_total = Counter(
    'maestro_ml_experiments_total',
    'Total ML experiments',
    ['tenant_id', 'status']
)

ml_training_duration_seconds = Histogram(
    'maestro_ml_training_duration_seconds',
    'ML training job duration',
    ['tenant_id', 'job_type'],
    buckets=(60, 300, 900, 1800, 3600, 7200, 14400, 28800, 86400)  # 1min to 24h
)

# Feature Discovery Metrics
feature_discovery_operations_total = Counter(
    'maestro_feature_discovery_operations_total',
    'Feature discovery operations',
    ['operation', 'status']
)

feature_discovery_duration_seconds = Histogram(
    'maestro_feature_discovery_duration_seconds',
    'Feature discovery operation duration',
    ['operation'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
)

# Model Card Metrics
model_card_generations_total = Counter(
    'maestro_model_card_generations_total',
    'Model card generations',
    ['format', 'status']
)

# Tenant Metrics
tenant_quota_usage_ratio = Gauge(
    'maestro_tenant_quota_usage_ratio',
    'Tenant quota usage as ratio (0-1)',
    ['tenant_id', 'resource_type']
)

tenant_active_users = Gauge(
    'maestro_tenant_active_users',
    'Active users per tenant',
    ['tenant_id']
)

# API Error Metrics
api_errors_total = Counter(
    'maestro_api_errors_total',
    'Total API errors',
    ['method', 'endpoint', 'error_type']
)

# Rate Limiting Metrics
rate_limit_exceeded_total = Counter(
    'maestro_rate_limit_exceeded_total',
    'Rate limit exceeded events',
    ['identifier_type']  # 'user' or 'ip'
)

# Application Info
app_info = Info('maestro_app', 'Maestro ML Platform application info')


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that collects Prometheus metrics for all requests
    """

    def _get_route_pattern(self, request: Request) -> str:
        """Get the route pattern for the request"""
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                return route.path
        return request.url.path

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Collect metrics for each request"""
        method = request.method
        endpoint = self._get_route_pattern(request)

        # Skip metrics endpoint itself
        if endpoint == "/metrics":
            return await call_next(request)

        # Track in-progress requests
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()

        # Track request duration
        start_time = time.time()

        try:
            response = await call_next(request)
            status_code = response.status_code

            # Record successful request
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status_code
            ).inc()

            # Track errors
            if status_code >= 400:
                error_type = "client_error" if status_code < 500 else "server_error"
                api_errors_total.labels(
                    method=method,
                    endpoint=endpoint,
                    error_type=error_type
                ).inc()

            return response

        except Exception as e:
            # Track exception
            api_errors_total.labels(
                method=method,
                endpoint=endpoint,
                error_type=type(e).__name__
            ).inc()
            raise

        finally:
            # Record duration
            duration = time.time() - start_time
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint
            ).observe(duration)

            # Decrement in-progress counter
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()


# Helper functions for recording ML-specific metrics

def record_model_operation(operation: str, tenant_id: str, status: str = "success"):
    """
    Record a model operation metric

    Args:
        operation: Operation type (create, update, delete, deploy)
        tenant_id: Tenant ID
        status: Operation status (success, failure)
    """
    ml_model_operations_total.labels(
        operation=operation,
        tenant_id=tenant_id,
        status=status
    ).inc()


def record_model_size(tenant_id: str, size_bytes: float):
    """Record model size metric"""
    ml_model_size_bytes.labels(tenant_id=tenant_id).observe(size_bytes)


def update_model_count(tenant_id: str, count: int):
    """Update total model count for tenant"""
    ml_models_total.labels(tenant_id=tenant_id).set(count)


def record_experiment(tenant_id: str, status: str = "completed"):
    """Record ML experiment metric"""
    ml_experiments_total.labels(tenant_id=tenant_id, status=status).inc()


def record_training_duration(tenant_id: str, job_type: str, duration_seconds: float):
    """Record training job duration"""
    ml_training_duration_seconds.labels(
        tenant_id=tenant_id,
        job_type=job_type
    ).observe(duration_seconds)


def record_feature_discovery(operation: str, duration_seconds: float, status: str = "success"):
    """Record feature discovery operation"""
    feature_discovery_operations_total.labels(
        operation=operation,
        status=status
    ).inc()
    feature_discovery_duration_seconds.labels(operation=operation).observe(duration_seconds)


def record_model_card_generation(format: str, status: str = "success"):
    """Record model card generation"""
    model_card_generations_total.labels(format=format, status=status).inc()


def update_tenant_quota_usage(tenant_id: str, resource_type: str, usage_ratio: float):
    """
    Update tenant quota usage metric

    Args:
        tenant_id: Tenant ID
        resource_type: Type of resource (models, storage, etc.)
        usage_ratio: Usage as ratio 0-1 (used/quota)
    """
    tenant_quota_usage_ratio.labels(
        tenant_id=tenant_id,
        resource_type=resource_type
    ).set(usage_ratio)


def update_tenant_active_users(tenant_id: str, user_count: int):
    """Update active user count for tenant"""
    tenant_active_users.labels(tenant_id=tenant_id).set(user_count)


def record_rate_limit_exceeded(identifier_type: str):
    """
    Record rate limit exceeded event

    Args:
        identifier_type: 'user' or 'ip'
    """
    rate_limit_exceeded_total.labels(identifier_type=identifier_type).inc()


def set_app_info(version: str, environment: str):
    """Set application info"""
    app_info.info({
        'version': version,
        'environment': environment,
        'platform': 'maestro-ml'
    })
