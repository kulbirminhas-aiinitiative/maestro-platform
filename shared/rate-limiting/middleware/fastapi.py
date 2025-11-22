"""
FastAPI Rate Limiting Middleware

Reusable middleware for any FastAPI application.
"""

import logging
from typing import Callable, List, Optional

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..core.limiter import RateLimiter
from ..analytics.metrics import RateLimitMetrics

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.

    Usage:
        from maestro_rate_limiting import RateLimitMiddleware

        app.add_middleware(
            RateLimitMiddleware,
            redis_client=redis,
            tenant_extractor=my_tenant_extractor
        )
    """

    def __init__(
        self,
        app,
        redis_client,
        tenant_extractor: Optional[Callable] = None,
        skip_paths: Optional[List[str]] = None,
        metrics: Optional[RateLimitMetrics] = None,
        policy_service=None,
    ):
        """
        Initialize rate limiting middleware.

        Args:
            app: FastAPI application
            redis_client: Redis client instance
            tenant_extractor: Async function to extract tenant info from request
                             Returns (tenant_id, subscription_tier) tuple
            skip_paths: Paths to skip rate limiting
            metrics: Optional metrics collector
            policy_service: Optional policy service for dynamic rules
        """
        super().__init__(app)
        self.limiter = RateLimiter(
            redis_client=redis_client,
            policy_service=policy_service
        )
        self.tenant_extractor = tenant_extractor or self._default_tenant_extractor
        self.skip_paths = skip_paths or [
            "/health", "/ready", "/metrics", "/docs", "/redoc", "/openapi.json"
        ]
        self.metrics = metrics
        logger.info("RateLimitMiddleware initialized")

    async def dispatch(self, request: Request, call_next: Callable):
        """Process request with rate limiting."""

        # Skip rate limiting for specific paths
        if any(request.url.path.startswith(path) for path in self.skip_paths):
            return await call_next(request)

        # Extract tenant info
        tenant_id, subscription_tier = await self.tenant_extractor(request)

        # Check concurrent request limit
        concurrent_allowed = await self.limiter.check_concurrent_limit(
            tenant_id, subscription_tier
        )

        if not concurrent_allowed:
            logger.warning(f"Concurrent limit exceeded for tenant {tenant_id}")
            if self.metrics:
                await self.metrics.record_rejection(
                    tenant_id, request.url.path, "concurrent_limit"
                )
            return Response(
                content='{"error": "Too many concurrent requests. Please try again later."}',
                status_code=429,
                media_type="application/json",
                headers={
                    "Retry-After": "10",
                    "X-RateLimit-Error": "concurrent_limit_exceeded"
                },
            )

        # Check rate limit
        result = await self.limiter.check_rate_limit(tenant_id, subscription_tier)

        if not result.allowed:
            logger.warning(
                f"Rate limit exceeded for tenant {tenant_id} "
                f"(tier={subscription_tier}, path={request.url.path})"
            )
            if self.metrics:
                await self.metrics.record_rejection(
                    tenant_id, request.url.path, "rate_limit"
                )

            result.headers["Retry-After"] = str(result.retry_after)
            result.headers["X-RateLimit-Error"] = "rate_limit_exceeded"

            return Response(
                content='{"error": "Rate limit exceeded. Please upgrade your subscription or wait before retrying."}',
                status_code=429,
                media_type="application/json",
                headers=result.headers,
            )

        # Track concurrent request
        await self.limiter.increment_concurrent(tenant_id)

        try:
            # Process request
            response = await call_next(request)

            # Add rate limit headers to response
            for header_name, header_value in result.headers.items():
                response.headers[header_name] = header_value

            # Record successful request
            if self.metrics:
                await self.metrics.record_request(tenant_id, request.url.path)

            return response

        finally:
            # Decrement concurrent counter
            await self.limiter.decrement_concurrent(tenant_id)

    async def _default_tenant_extractor(self, request: Request):
        """
        Default tenant extraction from request.

        Override this for your specific authentication system.
        """
        # Check for tenant context in request state
        tenant_context = getattr(request.state, "tenant_context", None)

        if tenant_context:
            tenant_id = str(getattr(tenant_context, "tenant_id", "unknown"))
            subscription_tier = getattr(
                tenant_context, "subscription_tier", "starter"
            )
            if hasattr(subscription_tier, "value"):
                subscription_tier = subscription_tier.value
            return tenant_id, subscription_tier

        # Fall back to IP-based for anonymous
        client_ip = request.client.host if request.client else "unknown"
        return f"anonymous:{client_ip}", "anonymous"
