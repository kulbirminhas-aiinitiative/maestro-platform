"""
Distributed Tracing Middleware

Middleware for automatic trace context propagation and enrichment.
"""

from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode
import time


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware for enriching traces with request/response metadata."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process request and enrich trace with metadata.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response object
        """
        # Get current span
        span = trace.get_current_span()

        # Add request metadata to span
        if span.is_recording():
            # HTTP metadata
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            span.set_attribute("http.target", request.url.path)
            span.set_attribute("http.host", request.url.hostname or "")
            span.set_attribute("http.scheme", request.url.scheme)

            # Client information
            client_host = request.client.host if request.client else ""
            span.set_attribute("http.client_ip", client_host)

            # User agent
            user_agent = request.headers.get("user-agent", "")
            span.set_attribute("http.user_agent", user_agent)

            # Custom headers (if present)
            if "x-tenant-id" in request.headers:
                span.set_attribute("tenant.id", request.headers["x-tenant-id"])

            if "x-user-id" in request.headers:
                span.set_attribute("user.id", request.headers["x-user-id"])

            if "x-request-id" in request.headers:
                span.set_attribute("request.id", request.headers["x-request-id"])

        # Process request
        start_time = time.time()

        try:
            response = await call_next(request)

            # Add response metadata
            if span.is_recording():
                span.set_attribute("http.status_code", response.status_code)
                duration_ms = (time.time() - start_time) * 1000
                span.set_attribute("http.response_time_ms", duration_ms)

                # Set span status based on HTTP status
                if response.status_code >= 500:
                    span.set_status(Status(StatusCode.ERROR))
                elif response.status_code >= 400:
                    span.set_status(Status(StatusCode.ERROR))
                else:
                    span.set_status(Status(StatusCode.OK))

            return response

        except Exception as e:
            # Record exception in span
            if span.is_recording():
                span.record_exception(e)
                span.set_status(Status(StatusCode.ERROR, str(e)))
            raise


class TenantContextMiddleware(BaseHTTPMiddleware):
    """Middleware for tenant context propagation in traces."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Extract tenant context and add to trace.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response object
        """
        # Extract tenant from header or query param
        tenant_id = request.headers.get("x-tenant-id")
        if not tenant_id:
            tenant_id = request.query_params.get("tenant_id")

        # Add to trace context
        if tenant_id:
            span = trace.get_current_span()
            if span.is_recording():
                span.set_attribute("tenant.id", tenant_id)
                span.set_attribute("tenant.context", "active")

        response = await call_next(request)
        return response


class PerformanceTrackingMiddleware(BaseHTTPMiddleware):
    """Middleware for tracking performance metrics in traces."""

    def __init__(self, app, slow_request_threshold_ms: float = 1000.0):
        """
        Initialize performance tracking middleware.

        Args:
            app: FastAPI application
            slow_request_threshold_ms: Threshold for slow request warning
        """
        super().__init__(app)
        self.slow_threshold = slow_request_threshold_ms

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Track request performance and flag slow requests.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response object
        """
        span = trace.get_current_span()
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000

        # Add performance metrics to span
        if span.is_recording():
            span.set_attribute("performance.duration_ms", duration_ms)

            # Flag slow requests
            if duration_ms > self.slow_threshold:
                span.set_attribute("performance.slow_request", True)
                span.set_attribute("performance.threshold_ms", self.slow_threshold)
                span.add_event(
                    "slow_request_detected",
                    attributes={
                        "duration_ms": duration_ms,
                        "threshold_ms": self.slow_threshold,
                        "endpoint": request.url.path
                    }
                )

        return response


def add_tracing_middleware(app):
    """
    Add all tracing middleware to FastAPI app.

    Args:
        app: FastAPI application instance
    """
    # Performance tracking (outermost)
    app.add_middleware(PerformanceTrackingMiddleware, slow_request_threshold_ms=1000.0)

    # Tenant context
    app.add_middleware(TenantContextMiddleware)

    # Core tracing enrichment (innermost)
    app.add_middleware(TracingMiddleware)
