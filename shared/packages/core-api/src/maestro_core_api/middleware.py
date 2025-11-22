"""
Enterprise middleware components for the API framework.
"""

import time
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, Gauge
from maestro_core_logging import get_logger

# Prometheus metrics
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

ACTIVE_REQUESTS = Gauge(
    'http_requests_active',
    'Active HTTP requests'
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests with structured data."""

    def __init__(self, app):
        super().__init__(app)
        self.logger = get_logger("maestro.api.requests")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request and response details."""
        start_time = time.time()

        # Log request
        self.logger.info(
            "Request started",
            method=request.method,
            path=request.url.path,
            query_params=str(request.query_params),
            client_ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log response
        self.logger.info(
            "Request completed",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration=round(duration, 3)
        )

        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to responses."""

    def __init__(self, app, config=None):
        super().__init__(app)
        self.config = config

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to response."""
        response = await call_next(request)

        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # HSTS header for HTTPS
        if request.url.scheme == "https" and self.config:
            response.headers["Strict-Transport-Security"] = f"max-age={self.config.hsts_max_age}; includeSubDomains"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' https:; "
            "connect-src 'self'"
        )

        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting Prometheus metrics."""

    def __init__(self, app, config=None):
        super().__init__(app)
        self.config = config

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Collect metrics for request."""
        if not self.config or not self.config.enable_metrics:
            return await call_next(request)

        # Skip metrics collection for metrics endpoint
        if request.url.path == self.config.metrics_path:
            return await call_next(request)

        start_time = time.time()
        ACTIVE_REQUESTS.inc()

        try:
            response = await call_next(request)

            # Record metrics
            duration = time.time() - start_time
            endpoint = request.url.path
            method = request.method
            status = str(response.status_code)

            REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=status).inc()
            REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

            return response
        finally:
            ACTIVE_REQUESTS.dec()


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size."""

    def __init__(self, app, max_size: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_size = max_size
        self.logger = get_logger("maestro.api.security")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Check request size limit."""
        content_length = request.headers.get("content-length")

        if content_length and int(content_length) > self.max_size:
            self.logger.warning(
                "Request rejected: size too large",
                content_length=content_length,
                max_size=self.max_size,
                path=request.url.path
            )
            return JSONResponse(
                status_code=413,
                content={
                    "error": "Request entity too large",
                    "message": f"Request size exceeds maximum allowed size of {self.max_size} bytes"
                }
            )

        return await call_next(request)


class TimeoutMiddleware(BaseHTTPMiddleware):
    """Middleware to add request timeout."""

    def __init__(self, app, timeout: int = 30):
        super().__init__(app)
        self.timeout = timeout
        self.logger = get_logger("maestro.api.timeout")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add timeout to request processing."""
        import asyncio

        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            self.logger.warning(
                "Request timeout",
                path=request.url.path,
                method=request.method,
                timeout=self.timeout
            )
            return JSONResponse(
                status_code=408,
                content={
                    "error": "Request timeout",
                    "message": f"Request took longer than {self.timeout} seconds"
                }
            )