"""
Core Rate Limiter with Redis Backend

Implements sliding window algorithm with support for:
- Per-tenant rate limiting
- Concurrent request tracking
- X-RateLimit-Reset header (MD-987)
- Environment-aware configuration
"""

import logging
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .tiers import RateLimitTier, get_tier

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    headers: Dict[str, str]
    retry_after: int = 0
    reset_at: int = 0  # Unix timestamp when window resets


class RateLimiter:
    """
    Redis-backed rate limiter using sliding window algorithm.

    Distributed-safe for multi-instance deployments.
    Supports dynamic policy overrides via PolicyService.
    """

    def __init__(self, redis_client, prefix: str = "ratelimit", policy_service=None):
        """
        Initialize rate limiter.

        Args:
            redis_client: Redis client instance
            prefix: Key prefix for Redis storage
            policy_service: Optional PolicyService for dynamic rules
        """
        self.redis = redis_client
        self.prefix = prefix
        self.policy_service = policy_service
        logger.info(f"RateLimiter initialized with prefix '{prefix}'")

    def _make_key(self, tenant_id: str, window: str) -> str:
        """Generate Redis key for rate limit tracking."""
        return f"{self.prefix}:{tenant_id}:{window}"

    def _make_concurrent_key(self, tenant_id: str) -> str:
        """Generate Redis key for concurrent request tracking."""
        return f"{self.prefix}:concurrent:{tenant_id}"

    async def check_rate_limit(
        self,
        tenant_id: str,
        subscription_tier: str,
        endpoint: Optional[str] = None,
        cost: int = 1,
    ) -> RateLimitResult:
        """
        Check if request is within rate limits.

        Args:
            tenant_id: Tenant identifier
            subscription_tier: Subscription tier name
            endpoint: Optional endpoint for weighted limits
            cost: Request cost (for weighted endpoints)

        Returns:
            RateLimitResult with allowed status and headers
        """
        # Get tier config (from policy service if available, else default)
        tier_config = await self._get_tier_config(tenant_id, subscription_tier)

        # Platform admins get unlimited access
        if subscription_tier.lower() == "platform_admin":
            return RateLimitResult(
                allowed=True,
                headers=self._build_headers(tier_config, 999999, 999999, 0),
                retry_after=0,
                reset_at=0,
            )

        now = time.time()
        minute_window = 60
        hour_window = 3600

        try:
            # Check minute window
            minute_key = self._make_key(tenant_id, "minute")
            minute_allowed, minute_remaining, minute_reset = await self._check_window(
                minute_key, tier_config.requests_per_minute, minute_window, now, cost
            )

            # Check hour window
            hour_key = self._make_key(tenant_id, "hour")
            hour_allowed, hour_remaining, hour_reset = await self._check_window(
                hour_key, tier_config.requests_per_hour, hour_window, now, cost
            )

            allowed = minute_allowed and hour_allowed

            # Calculate retry-after and reset time
            retry_after = 0
            reset_at = 0
            if not allowed:
                if not minute_allowed:
                    retry_after = minute_window
                    reset_at = minute_reset
                elif not hour_allowed:
                    retry_after = hour_window
                    reset_at = hour_reset
            else:
                # Use the nearest reset time
                reset_at = minute_reset

            headers = self._build_headers(
                tier_config, minute_remaining, hour_remaining, reset_at
            )

            return RateLimitResult(
                allowed=allowed,
                headers=headers,
                retry_after=retry_after,
                reset_at=reset_at,
            )

        except Exception as e:
            logger.error(f"Rate limit check error for tenant {tenant_id}: {e}")
            # Fail open - allow request on Redis error
            return RateLimitResult(allowed=True, headers={}, retry_after=0, reset_at=0)

    async def _check_window(
        self, key: str, limit: int, window_seconds: int, now: float, cost: int = 1
    ) -> Tuple[bool, int, int]:
        """
        Check rate limit for a specific time window using Redis sorted set.

        Returns:
            Tuple of (allowed, remaining_requests, reset_timestamp)
        """
        try:
            # Remove entries older than the window
            window_start = now - window_seconds
            self.redis.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            current_count = self.redis.zcard(key)

            if current_count + cost > limit:
                # Rate limit exceeded
                reset_at = int(now + window_seconds)
                return False, 0, reset_at

            # Add current request(s) with timestamp as score
            for i in range(cost):
                request_id = f"{now}:{id(object())}:{i}"
                self.redis.zadd(key, {request_id: now})

            # Set expiration to window size (cleanup)
            self.redis.expire(key, window_seconds)

            remaining = limit - (current_count + cost)
            reset_at = int(now + window_seconds)
            return True, max(0, remaining), reset_at

        except Exception as e:
            logger.error(f"Window check error for key {key}: {e}")
            # Fail open on error
            return True, limit, int(now + window_seconds)

    async def check_concurrent_limit(
        self, tenant_id: str, subscription_tier: str
    ) -> bool:
        """Check if tenant has exceeded concurrent request limit."""
        tier_config = await self._get_tier_config(tenant_id, subscription_tier)

        if subscription_tier.lower() == "platform_admin":
            return True

        try:
            key = self._make_concurrent_key(tenant_id)
            current = int(self.redis.get(key) or 0)
            return current < tier_config.concurrent_requests
        except Exception as e:
            logger.error(f"Concurrent limit check error: {e}")
            return True  # Fail open

    async def increment_concurrent(self, tenant_id: str):
        """Increment concurrent request counter."""
        try:
            key = self._make_concurrent_key(tenant_id)
            self.redis.incr(key)
            self.redis.expire(key, 300)  # 5 minute expiration
        except Exception as e:
            logger.error(f"Increment concurrent error: {e}")

    async def decrement_concurrent(self, tenant_id: str):
        """Decrement concurrent request counter."""
        try:
            key = self._make_concurrent_key(tenant_id)
            current = int(self.redis.get(key) or 0)
            if current > 0:
                self.redis.decr(key)
        except Exception as e:
            logger.error(f"Decrement concurrent error: {e}")

    async def _get_tier_config(
        self, tenant_id: str, subscription_tier: str
    ) -> RateLimitTier:
        """Get tier configuration, checking policy service for overrides."""
        if self.policy_service:
            # Check for tenant-specific override
            override = await self.policy_service.get_tenant_override(tenant_id)
            if override:
                return override

        return get_tier(subscription_tier)

    def _build_headers(
        self,
        tier_config: RateLimitTier,
        minute_remaining: int,
        hour_remaining: int,
        reset_at: int,
    ) -> Dict[str, str]:
        """Build rate limit headers for response."""
        headers = {
            "X-RateLimit-Limit-Minute": str(tier_config.requests_per_minute),
            "X-RateLimit-Remaining-Minute": str(minute_remaining),
            "X-RateLimit-Limit-Hour": str(tier_config.requests_per_hour),
            "X-RateLimit-Remaining-Hour": str(hour_remaining),
            "X-RateLimit-Concurrent-Limit": str(tier_config.concurrent_requests),
        }

        # Add reset timestamp (MD-987)
        if reset_at > 0:
            headers["X-RateLimit-Reset"] = str(reset_at)

        return headers
