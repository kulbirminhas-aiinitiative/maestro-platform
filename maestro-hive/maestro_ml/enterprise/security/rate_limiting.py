"""
API Rate Limiting

Provides rate limiting middleware to prevent API abuse and DoS attacks.
"""

import time
import logging
from typing import Optional, Callable
from collections import defaultdict
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    For production, use Redis-based implementation for distributed rate limiting.
    """

    def __init__(self):
        # Store: {key: [(timestamp, count)]}
        self.requests: dict[str, list[tuple[float, int]]] = defaultdict(list)
        self.cleanup_interval = 60  # seconds
        self.last_cleanup = time.time()

    def is_allowed(
        self,
        key: str,
        limit: int,
        window: int = 60
    ) -> tuple[bool, dict[str, int]]:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Rate limit key (e.g., user_id, ip_address)
            limit: Maximum requests allowed
            window: Time window in seconds

        Returns:
            (is_allowed, headers) tuple with rate limit headers
        """
        now = time.time()
        window_start = now - window

        # Cleanup old entries periodically
        if now - self.last_cleanup > self.cleanup_interval:
            self._cleanup()
            self.last_cleanup = now

        # Get requests in current window
        request_list = self.requests[key]

        # Remove requests outside window
        request_list[:] = [(ts, count) for ts, count in request_list if ts > window_start]

        # Count requests in window
        current_count = sum(count for _, count in request_list)

        # Check if allowed
        allowed = current_count < limit

        if allowed:
            # Add current request
            request_list.append((now, 1))

        # Calculate rate limit headers
        remaining = max(0, limit - current_count - (1 if allowed else 0))
        reset_time = int(now + window) if request_list else int(now + window)

        headers = {
            "X-RateLimit-Limit": limit,
            "X-RateLimit-Remaining": remaining,
            "X-RateLimit-Reset": reset_time,
        }

        if not allowed:
            # Calculate retry after
            oldest_request = request_list[0][0] if request_list else now
            retry_after = int(oldest_request + window - now) + 1
            headers["Retry-After"] = retry_after

        return allowed, headers

    def _cleanup(self):
        """Remove old entries to prevent memory growth"""
        # Remove keys with no recent requests
        cutoff = time.time() - 3600  # 1 hour
        keys_to_remove = []

        for key, requests in self.requests.items():
            # Remove old requests
            requests[:] = [(ts, count) for ts, count in requests if ts > cutoff]

            # Mark empty keys for removal
            if not requests:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self.requests[key]

        if keys_to_remove:
            logger.debug(f"Cleaned up {len(keys_to_remove)} rate limit keys")


# Global rate limiter instance
_rate_limiter = RateLimiter()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API rate limiting.

    Supports multiple rate limit tiers:
    - Per-user limits
    - Per-tenant limits
    - Per-IP limits (fallback for unauthenticated)
    - Global limits
    """

    def __init__(
        self,
        app,
        rate_limiter: RateLimiter = _rate_limiter,
        # Rate limits (requests per minute)
        per_user_limit: int = 1000,
        per_tenant_limit: int = 5000,
        per_ip_limit: int = 100,
        global_limit: int = 10000,
        # Time windows (seconds)
        window: int = 60,
        # Exempt paths
        exempt_paths: Optional[list[str]] = None
    ):
        """
        Initialize rate limiting middleware.

        Args:
            app: FastAPI application
            rate_limiter: RateLimiter instance
            per_user_limit: Max requests per user per window
            per_tenant_limit: Max requests per tenant per window
            per_ip_limit: Max requests per IP per window
            global_limit: Max total requests per window
            window: Time window in seconds
            exempt_paths: Paths to exempt from rate limiting
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.per_user_limit = per_user_limit
        self.per_tenant_limit = per_tenant_limit
        self.per_ip_limit = per_ip_limit
        self.global_limit = global_limit
        self.window = window
        self.exempt_paths = exempt_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/openapi.json",
            "/redoc"
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Apply rate limiting to request.

        Args:
            request: Incoming request
            call_next: Next middleware/handler

        Returns:
            Response object
        """
        # Check if path is exempt
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)

        # Extract identifiers
        user_id = request.headers.get("x-user-id")
        tenant_id = request.headers.get("x-tenant-id")
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limits in order of specificity
        rate_limit_headers = {}

        # 1. Global limit (most restrictive)
        allowed, headers = self.rate_limiter.is_allowed(
            key="global",
            limit=self.global_limit,
            window=self.window
        )
        rate_limit_headers.update(headers)

        if not allowed:
            logger.warning(f"Global rate limit exceeded")
            return self._rate_limit_response(headers)

        # 2. Tenant limit (if tenant specified)
        if tenant_id:
            allowed, headers = self.rate_limiter.is_allowed(
                key=f"tenant:{tenant_id}",
                limit=self.per_tenant_limit,
                window=self.window
            )
            rate_limit_headers.update({f"X-RateLimit-Tenant-{k}": v for k, v in headers.items()})

            if not allowed:
                logger.warning(f"Tenant rate limit exceeded: {tenant_id}")
                return self._rate_limit_response(headers)

        # 3. User limit (if user specified)
        if user_id:
            allowed, headers = self.rate_limiter.is_allowed(
                key=f"user:{user_id}",
                limit=self.per_user_limit,
                window=self.window
            )
            rate_limit_headers.update({f"X-RateLimit-User-{k}": v for k, v in headers.items()})

            if not allowed:
                logger.warning(f"User rate limit exceeded: {user_id}")
                return self._rate_limit_response(headers)

        # 4. IP limit (fallback for unauthenticated requests)
        if not user_id:
            allowed, headers = self.rate_limiter.is_allowed(
                key=f"ip:{client_ip}",
                limit=self.per_ip_limit,
                window=self.window
            )
            rate_limit_headers.update({f"X-RateLimit-IP-{k}": v for k, v in headers.items()})

            if not allowed:
                logger.warning(f"IP rate limit exceeded: {client_ip}")
                return self._rate_limit_response(headers)

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        for key, value in rate_limit_headers.items():
            response.headers[key] = str(value)

        return response

    def _rate_limit_response(self, headers: dict) -> Response:
        """Create rate limit exceeded response"""
        retry_after = headers.get("Retry-After", 60)

        return Response(
            content='{"detail":"Rate limit exceeded. Please try again later."}',
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            headers={
                "Content-Type": "application/json",
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(headers.get("X-RateLimit-Limit", 0)),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(headers.get("X-RateLimit-Reset", 0)),
            }
        )


class RateLimitConfig:
    """Configuration for rate limiting"""

    def __init__(
        self,
        per_user_limit: int = 1000,
        per_tenant_limit: int = 5000,
        per_ip_limit: int = 100,
        global_limit: int = 10000,
        window: int = 60,
        exempt_paths: Optional[list[str]] = None
    ):
        self.per_user_limit = per_user_limit
        self.per_tenant_limit = per_tenant_limit
        self.per_ip_limit = per_ip_limit
        self.global_limit = global_limit
        self.window = window
        self.exempt_paths = exempt_paths or []


def add_rate_limiting(
    app,
    config: Optional[RateLimitConfig] = None,
    rate_limiter: RateLimiter = _rate_limiter
):
    """
    Add rate limiting middleware to FastAPI app.

    Args:
        app: FastAPI application
        config: Rate limit configuration
        rate_limiter: RateLimiter instance

    Example:
        from enterprise.security.rate_limiting import add_rate_limiting, RateLimitConfig

        config = RateLimitConfig(
            per_user_limit=500,
            per_ip_limit=50
        )
        add_rate_limiting(app, config)
    """
    if config is None:
        config = RateLimitConfig()

    app.add_middleware(
        RateLimitMiddleware,
        rate_limiter=rate_limiter,
        per_user_limit=config.per_user_limit,
        per_tenant_limit=config.per_tenant_limit,
        per_ip_limit=config.per_ip_limit,
        global_limit=config.global_limit,
        window=config.window,
        exempt_paths=config.exempt_paths
    )
