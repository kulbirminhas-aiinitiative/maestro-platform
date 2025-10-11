"""
Prometheus Metrics Collector for Maestro ML Platform

Provides comprehensive metrics collection:
- HTTP request metrics (RED pattern)
- Business metrics (models, experiments, deployments)
- System metrics (database, cache, queue)
- Custom application metrics
- SLO/SLI tracking
"""

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    Info,
    generate_latest,
    REGISTRY,
    CollectorRegistry
)
from typing import Dict, Optional, Callable
import time
import functools
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# HTTP Metrics (RED Pattern: Rate, Errors, Duration)
# ============================================================================

# Request rate
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# Request duration
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

# Request size
http_request_size_bytes = Summary(
    'http_request_size_bytes',
    'HTTP request size in bytes',
    ['method', 'endpoint']
)

# Response size
http_response_size_bytes = Summary(
    'http_response_size_bytes',
    'HTTP response size in bytes',
    ['method', 'endpoint']
)

# In-flight requests
http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests in progress',
    ['method', 'endpoint']
)


# ============================================================================
# Business Metrics
# ============================================================================

# Models
models_total = Gauge(
    'models_total',
    'Total number of models',
    ['tenant_id', 'status']
)

models_created_total = Counter(
    'models_created_total',
    'Total models created',
    ['tenant_id']
)

models_deleted_total = Counter(
    'models_deleted_total',
    'Total models deleted',
    ['tenant_id']
)

model_training_duration_seconds = Histogram(
    'model_training_duration_seconds',
    'Model training duration in seconds',
    ['tenant_id', 'model_type'],
    buckets=(10, 30, 60, 300, 600, 1800, 3600, 7200, 14400, 28800)
)

# Experiments
experiments_total = Gauge(
    'experiments_total',
    'Total number of experiments',
    ['tenant_id', 'status']
)

experiments_created_total = Counter(
    'experiments_created_total',
    'Total experiments created',
    ['tenant_id']
)

experiment_runs_total = Counter(
    'experiment_runs_total',
    'Total experiment runs',
    ['tenant_id', 'status']
)

# Deployments
deployments_total = Gauge(
    'deployments_total',
    'Total number of deployments',
    ['tenant_id', 'environment', 'status']
)

deployments_created_total = Counter(
    'deployments_created_total',
    'Total deployments created',
    ['tenant_id', 'environment']
)

deployment_duration_seconds = Histogram(
    'deployment_duration_seconds',
    'Deployment duration in seconds',
    ['tenant_id', 'environment'],
    buckets=(5, 10, 30, 60, 120, 300, 600)
)

# Predictions
predictions_total = Counter(
    'predictions_total',
    'Total predictions made',
    ['tenant_id', 'model_id', 'status']
)

prediction_latency_seconds = Histogram(
    'prediction_latency_seconds',
    'Prediction latency in seconds',
    ['tenant_id', 'model_id'],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0)
)


# ============================================================================
# Database Metrics
# ============================================================================

db_connections_total = Gauge(
    'db_connections_total',
    'Total database connections',
    ['state']  # active, idle
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['operation'],  # select, insert, update, delete
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)
)

db_queries_total = Counter(
    'db_queries_total',
    'Total database queries',
    ['operation', 'status']
)

db_connection_errors_total = Counter(
    'db_connection_errors_total',
    'Total database connection errors'
)

db_pool_size = Gauge(
    'db_pool_size',
    'Database connection pool size'
)

db_pool_overflow = Gauge(
    'db_pool_overflow',
    'Database connection pool overflow'
)


# ============================================================================
# Cache Metrics
# ============================================================================

cache_hits_total = Counter(
    'cache_hits_total',
    'Total cache hits',
    ['cache_name']
)

cache_misses_total = Counter(
    'cache_misses_total',
    'Total cache misses',
    ['cache_name']
)

cache_operations_duration_seconds = Histogram(
    'cache_operations_duration_seconds',
    'Cache operation duration in seconds',
    ['operation', 'cache_name'],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1)
)

cache_size_bytes = Gauge(
    'cache_size_bytes',
    'Cache size in bytes',
    ['cache_name']
)

cache_evictions_total = Counter(
    'cache_evictions_total',
    'Total cache evictions',
    ['cache_name']
)


# ============================================================================
# Queue Metrics
# ============================================================================

queue_messages_total = Gauge(
    'queue_messages_total',
    'Total messages in queue',
    ['queue_name']
)

queue_messages_processed_total = Counter(
    'queue_messages_processed_total',
    'Total messages processed',
    ['queue_name', 'status']
)

queue_processing_duration_seconds = Histogram(
    'queue_processing_duration_seconds',
    'Message processing duration in seconds',
    ['queue_name'],
    buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)
)


# ============================================================================
# Rate Limiting Metrics
# ============================================================================

rate_limit_exceeded_total = Counter(
    'rate_limit_exceeded_total',
    'Total rate limit exceeded events',
    ['tier']  # user, tenant, ip, global
)

rate_limit_current_usage = Gauge(
    'rate_limit_current_usage',
    'Current rate limit usage',
    ['tier', 'identifier']
)


# ============================================================================
# Tenant Metrics
# ============================================================================

tenant_requests_total = Counter(
    'tenant_requests_total',
    'Total requests per tenant',
    ['tenant_id']
)

tenant_active_users = Gauge(
    'tenant_active_users',
    'Active users per tenant',
    ['tenant_id']
)

tenant_storage_bytes = Gauge(
    'tenant_storage_bytes',
    'Storage used per tenant in bytes',
    ['tenant_id']
)


# ============================================================================
# SLO/SLI Metrics
# ============================================================================

slo_http_request_success_rate = Gauge(
    'slo_http_request_success_rate',
    'HTTP request success rate (SLI)',
    ['service']
)

slo_http_request_latency_p99 = Gauge(
    'slo_http_request_latency_p99',
    'HTTP request p99 latency (SLI)',
    ['service']
)

slo_availability = Gauge(
    'slo_availability',
    'Service availability (SLI)',
    ['service']
)

slo_error_budget_remaining = Gauge(
    'slo_error_budget_remaining',
    'Error budget remaining (percentage)',
    ['service']
)


# ============================================================================
# Application Info
# ============================================================================

app_info = Info(
    'maestro_ml_app',
    'Application information'
)

app_info.info({
    'version': '2.0.0',
    'environment': 'production',
    'deployment': 'kubernetes'
})

app_build_info = Gauge(
    'maestro_ml_build_info',
    'Build information',
    ['version', 'git_commit', 'build_date']
)


# ============================================================================
# Metrics Collector Class
# ============================================================================

class MetricsCollector:
    """
    Central metrics collector for the application

    Usage:
        collector = MetricsCollector()

        # Record HTTP request
        collector.record_http_request(
            method="GET",
            endpoint="/models",
            status_code=200,
            duration=0.123
        )

        # Record business event
        collector.record_model_created(tenant_id="tenant-123")
    """

    def __init__(self):
        self.start_time = time.time()

    # HTTP Metrics
    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status_code: int,
        duration: float,
        request_size: Optional[int] = None,
        response_size: Optional[int] = None
    ):
        """Record HTTP request metrics"""
        http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=str(status_code)
        ).inc()

        http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

        if request_size:
            http_request_size_bytes.labels(
                method=method,
                endpoint=endpoint
            ).observe(request_size)

        if response_size:
            http_response_size_bytes.labels(
                method=method,
                endpoint=endpoint
            ).observe(response_size)

    def track_request_in_progress(self, method: str, endpoint: str):
        """Context manager to track in-progress requests"""
        class RequestTracker:
            def __enter__(self):
                http_requests_in_progress.labels(
                    method=method,
                    endpoint=endpoint
                ).inc()
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                http_requests_in_progress.labels(
                    method=method,
                    endpoint=endpoint
                ).dec()

        return RequestTracker()

    # Business Metrics
    def record_model_created(self, tenant_id: str):
        """Record model creation"""
        models_created_total.labels(tenant_id=tenant_id).inc()

    def record_model_deleted(self, tenant_id: str):
        """Record model deletion"""
        models_deleted_total.labels(tenant_id=tenant_id).inc()

    def record_model_training(self, tenant_id: str, model_type: str, duration: float):
        """Record model training duration"""
        model_training_duration_seconds.labels(
            tenant_id=tenant_id,
            model_type=model_type
        ).observe(duration)

    def set_models_total(self, tenant_id: str, status: str, count: int):
        """Set total models gauge"""
        models_total.labels(tenant_id=tenant_id, status=status).set(count)

    def record_experiment_created(self, tenant_id: str):
        """Record experiment creation"""
        experiments_created_total.labels(tenant_id=tenant_id).inc()

    def record_experiment_run(self, tenant_id: str, status: str):
        """Record experiment run"""
        experiment_runs_total.labels(tenant_id=tenant_id, status=status).inc()

    def record_deployment_created(self, tenant_id: str, environment: str):
        """Record deployment creation"""
        deployments_created_total.labels(
            tenant_id=tenant_id,
            environment=environment
        ).inc()

    def record_deployment_duration(self, tenant_id: str, environment: str, duration: float):
        """Record deployment duration"""
        deployment_duration_seconds.labels(
            tenant_id=tenant_id,
            environment=environment
        ).observe(duration)

    def record_prediction(self, tenant_id: str, model_id: str, status: str, latency: float):
        """Record prediction"""
        predictions_total.labels(
            tenant_id=tenant_id,
            model_id=model_id,
            status=status
        ).inc()

        prediction_latency_seconds.labels(
            tenant_id=tenant_id,
            model_id=model_id
        ).observe(latency)

    # Database Metrics
    def record_db_query(self, operation: str, duration: float, status: str = "success"):
        """Record database query"""
        db_queries_total.labels(operation=operation, status=status).inc()
        db_query_duration_seconds.labels(operation=operation).observe(duration)

    def set_db_connections(self, active: int, idle: int):
        """Set database connection counts"""
        db_connections_total.labels(state="active").set(active)
        db_connections_total.labels(state="idle").set(idle)

    def record_db_connection_error(self):
        """Record database connection error"""
        db_connection_errors_total.inc()

    # Cache Metrics
    def record_cache_hit(self, cache_name: str):
        """Record cache hit"""
        cache_hits_total.labels(cache_name=cache_name).inc()

    def record_cache_miss(self, cache_name: str):
        """Record cache miss"""
        cache_misses_total.labels(cache_name=cache_name).inc()

    def record_cache_operation(self, operation: str, cache_name: str, duration: float):
        """Record cache operation duration"""
        cache_operations_duration_seconds.labels(
            operation=operation,
            cache_name=cache_name
        ).observe(duration)

    # Rate Limiting Metrics
    def record_rate_limit_exceeded(self, tier: str):
        """Record rate limit exceeded"""
        rate_limit_exceeded_total.labels(tier=tier).inc()

    def set_rate_limit_usage(self, tier: str, identifier: str, usage: int):
        """Set current rate limit usage"""
        rate_limit_current_usage.labels(tier=tier, identifier=identifier).set(usage)

    # Tenant Metrics
    def record_tenant_request(self, tenant_id: str):
        """Record tenant request"""
        tenant_requests_total.labels(tenant_id=tenant_id).inc()

    def set_tenant_active_users(self, tenant_id: str, count: int):
        """Set active users for tenant"""
        tenant_active_users.labels(tenant_id=tenant_id).set(count)

    def set_tenant_storage(self, tenant_id: str, bytes_used: int):
        """Set storage used by tenant"""
        tenant_storage_bytes.labels(tenant_id=tenant_id).set(bytes_used)

    # SLO/SLI Metrics
    def set_slo_success_rate(self, service: str, rate: float):
        """Set SLO success rate (0.0-1.0)"""
        slo_http_request_success_rate.labels(service=service).set(rate)

    def set_slo_latency_p99(self, service: str, latency: float):
        """Set SLO p99 latency"""
        slo_http_request_latency_p99.labels(service=service).set(latency)

    def set_slo_availability(self, service: str, availability: float):
        """Set SLO availability (0.0-1.0)"""
        slo_availability.labels(service=service).set(availability)

    def set_error_budget_remaining(self, service: str, percentage: float):
        """Set error budget remaining (0.0-100.0)"""
        slo_error_budget_remaining.labels(service=service).set(percentage)

    # Utility Methods
    def get_uptime_seconds(self) -> float:
        """Get application uptime in seconds"""
        return time.time() - self.start_time


# ============================================================================
# Decorators
# ============================================================================

def track_time(metric: Histogram, **labels):
    """Decorator to track function execution time"""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start
                metric.labels(**labels).observe(duration)
        return wrapper
    return decorator


def count_calls(metric: Counter, **labels):
    """Decorator to count function calls"""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            metric.labels(**labels).inc()
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# Global Instance
# ============================================================================

metrics_collector = MetricsCollector()


# ============================================================================
# Metrics Endpoint
# ============================================================================

def get_metrics() -> bytes:
    """
    Get Prometheus metrics in text format

    Returns:
        Metrics in Prometheus text format
    """
    return generate_latest(REGISTRY)


# ============================================================================
# Usage Examples
# ============================================================================

"""
1. Record HTTP Request:

   from monitoring.metrics_collector import metrics_collector

   metrics_collector.record_http_request(
       method="GET",
       endpoint="/models",
       status_code=200,
       duration=0.123,
       request_size=1024,
       response_size=4096
   )

2. Track Request in Progress:

   with metrics_collector.track_request_in_progress("GET", "/models"):
       # Do work
       pass

3. Record Business Events:

   metrics_collector.record_model_created(tenant_id="tenant-123")
   metrics_collector.record_prediction(
       tenant_id="tenant-123",
       model_id="model-456",
       status="success",
       latency=0.015
   )

4. Use Decorators:

   from monitoring.metrics_collector import track_time, db_query_duration_seconds

   @track_time(db_query_duration_seconds, operation="select")
   def fetch_models():
       # Database query
       pass

5. Set SLO Metrics:

   metrics_collector.set_slo_success_rate("api", 0.999)
   metrics_collector.set_slo_latency_p99("api", 0.5)
   metrics_collector.set_error_budget_remaining("api", 95.5)

6. Expose Metrics Endpoint (FastAPI):

   from fastapi import FastAPI, Response
   from monitoring.metrics_collector import get_metrics

   app = FastAPI()

   @app.get("/metrics")
   def metrics():
       return Response(content=get_metrics(), media_type="text/plain")

7. Query Metrics (PromQL):

   # Request rate
   rate(http_requests_total[5m])

   # Error rate
   rate(http_requests_total{status=~"5.."}[5m])

   # p99 latency
   histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))

   # Availability
   sum(rate(http_requests_total{status!~"5.."}[5m])) /
   sum(rate(http_requests_total[5m]))
"""
