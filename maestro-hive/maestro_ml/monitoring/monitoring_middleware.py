"""
Monitoring Middleware for FastAPI

Automatically instruments FastAPI applications with:
- HTTP request metrics (RED pattern)
- Tenant tracking
- SLO/SLI calculation
- Database monitoring
- Cache monitoring
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp
import time
from typing import Callable, Optional
import logging
from contextlib import asynccontextmanager

from monitoring.metrics_collector import metrics_collector

logger = logging.getLogger(__name__)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically collect Prometheus metrics for all HTTP requests

    Usage:
        from fastapi import FastAPI
        from monitoring.monitoring_middleware import PrometheusMiddleware

        app = FastAPI()
        app.add_middleware(PrometheusMiddleware)
    """

    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: Optional[list] = None
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/metrics", "/health"]

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip metrics collection for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Extract metadata
        method = request.method
        path = self._get_path_template(request)

        # Track in-progress requests
        with metrics_collector.track_request_in_progress(method, path):
            # Record start time
            start_time = time.time()

            # Get request size
            request_size = request.headers.get("content-length")
            request_size = int(request_size) if request_size else 0

            # Process request
            try:
                response = await call_next(request)
                status_code = response.status_code

                # Get response size
                response_size = 0
                if hasattr(response, "body"):
                    response_size = len(response.body)

                # Record metrics
                duration = time.time() - start_time
                metrics_collector.record_http_request(
                    method=method,
                    endpoint=path,
                    status_code=status_code,
                    duration=duration,
                    request_size=request_size,
                    response_size=response_size
                )

                # Track tenant requests
                tenant_id = request.headers.get("x-tenant-id")
                if tenant_id:
                    metrics_collector.record_tenant_request(tenant_id)

                return response

            except Exception as e:
                # Record error
                duration = time.time() - start_time
                metrics_collector.record_http_request(
                    method=method,
                    endpoint=path,
                    status_code=500,
                    duration=duration,
                    request_size=request_size
                )
                raise

    def _get_path_template(self, request: Request) -> str:
        """
        Get path template (e.g., /models/{id} instead of /models/123)

        This provides better cardinality for metrics
        """
        # Try to get matched route path
        if hasattr(request, "scope") and "route" in request.scope:
            route = request.scope["route"]
            if hasattr(route, "path"):
                return route.path

        # Fallback to actual path
        return request.url.path


class DatabaseMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track database metrics

    Requires database session in request.state.db

    Usage:
        app.add_middleware(DatabaseMetricsMiddleware)
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        # Process request
        response = await call_next(request)

        # Collect database metrics if available
        if hasattr(request.state, "db"):
            db = request.state.db
            if hasattr(db, "bind") and hasattr(db.bind, "pool"):
                pool = db.bind.pool

                # Connection pool metrics
                if hasattr(pool, "size"):
                    metrics_collector.db_pool_size.set(pool.size())

                if hasattr(pool, "overflow"):
                    metrics_collector.db_pool_overflow.set(pool.overflow())

                if hasattr(pool, "checkedin") and hasattr(pool, "checkedout"):
                    active = pool.checkedout()
                    idle = pool.checkedin()
                    metrics_collector.set_db_connections(active, idle)

        return response


class SLOTrackingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track SLO/SLI metrics

    Calculates:
    - Success rate (availability)
    - Latency percentiles
    - Error budget

    Usage:
        app.add_middleware(SLOTrackingMiddleware, service_name="api")
    """

    def __init__(
        self,
        app: ASGIApp,
        service_name: str = "api",
        success_rate_target: float = 0.999,  # 99.9%
        latency_p99_target: float = 1.0,     # 1 second
        window_size: int = 300                # 5 minutes
    ):
        super().__init__(app)
        self.service_name = service_name
        self.success_rate_target = success_rate_target
        self.latency_p99_target = latency_p99_target
        self.window_size = window_size

        # In-memory tracking (for simple cases; use Prometheus for production)
        self.recent_requests = []
        self.recent_latencies = []
        self.max_samples = 10000

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.time()

        try:
            response = await call_next(request)
            success = 200 <= response.status_code < 500  # 4xx are client errors, not service failures
            latency = time.time() - start_time

            # Track samples
            self._track_sample(success, latency)

            # Update SLO metrics periodically
            if len(self.recent_requests) % 100 == 0:
                self._update_slo_metrics()

            return response

        except Exception as e:
            # Service failure
            latency = time.time() - start_time
            self._track_sample(False, latency)
            raise

    def _track_sample(self, success: bool, latency: float):
        """Track a request sample"""
        current_time = time.time()

        # Add sample
        self.recent_requests.append((current_time, success))
        self.recent_latencies.append((current_time, latency))

        # Trim old samples
        cutoff = current_time - self.window_size
        self.recent_requests = [(t, s) for t, s in self.recent_requests if t > cutoff]
        self.recent_latencies = [(t, l) for t, l in self.recent_latencies if t > cutoff]

        # Limit memory usage
        if len(self.recent_requests) > self.max_samples:
            self.recent_requests = self.recent_requests[-self.max_samples:]
        if len(self.recent_latencies) > self.max_samples:
            self.recent_latencies = self.recent_latencies[-self.max_samples:]

    def _update_slo_metrics(self):
        """Update SLO metrics"""
        if not self.recent_requests:
            return

        # Calculate success rate
        total = len(self.recent_requests)
        successes = sum(1 for _, s in self.recent_requests if s)
        success_rate = successes / total if total > 0 else 0.0

        metrics_collector.set_slo_success_rate(self.service_name, success_rate)
        metrics_collector.set_slo_availability(self.service_name, success_rate)

        # Calculate p99 latency
        if self.recent_latencies:
            latencies = sorted([l for _, l in self.recent_latencies])
            p99_index = int(len(latencies) * 0.99)
            p99_latency = latencies[p99_index] if p99_index < len(latencies) else latencies[-1]
            metrics_collector.set_slo_latency_p99(self.service_name, p99_latency)

        # Calculate error budget remaining
        # Error budget = (1 - target_success_rate) * 100
        # Remaining = budget - actual_errors
        target_errors_pct = (1 - self.success_rate_target) * 100
        actual_errors_pct = (1 - success_rate) * 100
        remaining_pct = max(0, (target_errors_pct - actual_errors_pct) / target_errors_pct * 100)

        metrics_collector.set_error_budget_remaining(self.service_name, remaining_pct)


class TenantMetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware to track per-tenant metrics

    Usage:
        app.add_middleware(TenantMetricsMiddleware)
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        # Extract tenant ID
        tenant_id = request.headers.get("x-tenant-id")

        if tenant_id:
            # Track tenant request
            metrics_collector.record_tenant_request(tenant_id)

        # Process request
        response = await call_next(request)

        return response


# ============================================================================
# Database Query Tracking
# ============================================================================

class DatabaseQueryTracker:
    """
    Context manager to track database query metrics

    Usage:
        with DatabaseQueryTracker("select"):
            result = db.query(Model).all()
    """

    def __init__(self, operation: str):
        self.operation = operation
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        status = "success" if exc_type is None else "error"
        metrics_collector.record_db_query(self.operation, duration, status)

        if exc_type is not None:
            metrics_collector.record_db_connection_error()


# ============================================================================
# Cache Operation Tracking
# ============================================================================

class CacheOperationTracker:
    """
    Context manager to track cache operation metrics

    Usage:
        with CacheOperationTracker("get", "models"):
            value = cache.get("key")
            if value is None:
                tracker.record_miss()
            else:
                tracker.record_hit()
    """

    def __init__(self, operation: str, cache_name: str):
        self.operation = operation
        self.cache_name = cache_name
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        metrics_collector.record_cache_operation(
            self.operation,
            self.cache_name,
            duration
        )

    def record_hit(self):
        """Record cache hit"""
        metrics_collector.record_cache_hit(self.cache_name)

    def record_miss(self):
        """Record cache miss"""
        metrics_collector.record_cache_miss(self.cache_name)


# ============================================================================
# Async Context Managers
# ============================================================================

@asynccontextmanager
async def track_db_query(operation: str):
    """
    Async context manager for database queries

    Usage:
        async with track_db_query("select"):
            results = await db.execute(query)
    """
    start_time = time.time()
    try:
        yield
        duration = time.time() - start_time
        metrics_collector.record_db_query(operation, duration, "success")
    except Exception as e:
        duration = time.time() - start_time
        metrics_collector.record_db_query(operation, duration, "error")
        metrics_collector.record_db_connection_error()
        raise


@asynccontextmanager
async def track_cache_operation(operation: str, cache_name: str):
    """
    Async context manager for cache operations

    Usage:
        async with track_cache_operation("get", "models") as tracker:
            value = await cache.get("key")
            if value:
                tracker.record_hit()
            else:
                tracker.record_miss()
    """
    start_time = time.time()
    tracker = CacheOperationTracker(operation, cache_name)
    tracker.start_time = start_time

    try:
        yield tracker
    finally:
        duration = time.time() - start_time
        metrics_collector.record_cache_operation(operation, cache_name, duration)


# ============================================================================
# Metrics Utilities
# ============================================================================

def setup_monitoring(app: ASGIApp, service_name: str = "maestro-ml-api"):
    """
    Setup all monitoring middleware

    Usage:
        from fastapi import FastAPI
        from monitoring.monitoring_middleware import setup_monitoring

        app = FastAPI()
        setup_monitoring(app)
    """
    # Add middleware in reverse order (outermost last)
    app.add_middleware(DatabaseMetricsMiddleware)
    app.add_middleware(TenantMetricsMiddleware)
    app.add_middleware(
        SLOTrackingMiddleware,
        service_name=service_name,
        success_rate_target=0.999,
        latency_p99_target=1.0
    )
    app.add_middleware(PrometheusMiddleware)

    logger.info(f"Monitoring middleware configured for {service_name}")


# ============================================================================
# Usage Examples
# ============================================================================

"""
1. Setup Monitoring (FastAPI):

   from fastapi import FastAPI
   from monitoring.monitoring_middleware import setup_monitoring

   app = FastAPI()
   setup_monitoring(app, service_name="maestro-ml-api")

2. Add Metrics Endpoint:

   from fastapi import Response
   from monitoring.metrics_collector import get_metrics

   @app.get("/metrics")
   def metrics():
       return Response(content=get_metrics(), media_type="text/plain")

3. Track Database Queries:

   from monitoring.monitoring_middleware import DatabaseQueryTracker

   with DatabaseQueryTracker("select"):
       models = db.query(Model).all()

   # Async version
   async with track_db_query("select"):
       result = await db.execute(query)

4. Track Cache Operations:

   from monitoring.monitoring_middleware import CacheOperationTracker

   with CacheOperationTracker("get", "models") as tracker:
       value = cache.get("key")
       if value:
           tracker.record_hit()
       else:
           tracker.record_miss()

5. Record Business Events:

   from monitoring.metrics_collector import metrics_collector

   # Model created
   metrics_collector.record_model_created(tenant_id="tenant-123")

   # Prediction made
   metrics_collector.record_prediction(
       tenant_id="tenant-123",
       model_id="model-456",
       status="success",
       latency=0.015
   )

6. View Metrics:

   curl http://localhost:8000/metrics

7. Query in Prometheus:

   # Request rate
   rate(http_requests_total[5m])

   # Error rate
   sum(rate(http_requests_total{status=~"5.."}[5m])) /
   sum(rate(http_requests_total[5m]))

   # p99 latency
   histogram_quantile(0.99,
     rate(http_request_duration_seconds_bucket[5m]))

   # SLO success rate
   slo_http_request_success_rate{service="api"}

   # Error budget remaining
   slo_error_budget_remaining{service="api"}

8. Alert Examples:

   # High error rate
   sum(rate(http_requests_total{status=~"5.."}[5m])) /
   sum(rate(http_requests_total[5m])) > 0.01

   # High latency
   histogram_quantile(0.99,
     rate(http_request_duration_seconds_bucket[5m])) > 1.0

   # SLO violation
   slo_http_request_success_rate{service="api"} < 0.999

   # Low error budget
   slo_error_budget_remaining{service="api"} < 10
"""
