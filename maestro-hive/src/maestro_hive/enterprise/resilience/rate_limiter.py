"""
Rate Limiter Implementation for Maestro Platform.

Provides per-user rate limiting using token bucket algorithm with sliding window.
Fulfills AC-3: Rate limiting at 1000 req/min per user.

Author: EPIC Executor v2.1
EPIC: MD-2050 - Resilience and Scaling
"""

import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Any
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RateLimitStrategy(Enum):
    """Rate limiting algorithm strategies."""
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimiterConfig:
    """Configuration for rate limiter."""
    requests_per_minute: int = 1000
    burst_size: int = 100
    strategy: RateLimitStrategy = RateLimitStrategy.TOKEN_BUCKET
    refill_rate: float = 16.67  # tokens per second for 1000/min
    window_size_seconds: int = 60


@dataclass
class UserBucket:
    """Token bucket state for a single user."""
    tokens: float
    last_refill: float
    request_count: int = 0
    window_start: float = 0.0


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_at: float
    retry_after: Optional[float] = None
    limit: int = 1000


class RateLimiter:
    """
    Per-user rate limiter using token bucket algorithm.

    Implements AC-3: Rate limiting at 1000 req/min per user.

    Features:
    - Token bucket with configurable refill rate
    - Per-user tracking with automatic cleanup
    - Burst handling for traffic spikes
    - Sliding window fallback

    Example:
        limiter = RateLimiter(requests_per_minute=1000, burst_size=100)

        async def handle_request(user_id: str):
            result = await limiter.acquire(user_id)
            if not result.allowed:
                raise RateLimitExceeded(retry_after=result.retry_after)
            # Process request...
    """

    _instance: Optional['RateLimiter'] = None

    def __init__(
        self,
        requests_per_minute: int = 1000,
        burst_size: int = 100,
        config: Optional[RateLimiterConfig] = None
    ):
        """Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute per user
            burst_size: Maximum burst capacity
            config: Optional full configuration object
        """
        if config:
            self.config = config
        else:
            self.config = RateLimiterConfig(
                requests_per_minute=requests_per_minute,
                burst_size=burst_size,
                refill_rate=requests_per_minute / 60.0
            )

        self._buckets: Dict[str, UserBucket] = {}
        self._lock = asyncio.Lock()
        self._cleanup_interval = 300  # 5 minutes
        self._last_cleanup = time.time()

        logger.info(
            f"RateLimiter initialized: {self.config.requests_per_minute} req/min, "
            f"burst={self.config.burst_size}"
        )

    @classmethod
    def get_instance(cls) -> 'RateLimiter':
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton instance (for testing)."""
        cls._instance = None

    async def acquire(self, user_id: str, tokens: int = 1) -> RateLimitResult:
        """
        Attempt to acquire tokens for a user request.

        Args:
            user_id: Unique user identifier
            tokens: Number of tokens to acquire (default 1)

        Returns:
            RateLimitResult with allowed status and metadata
        """
        async with self._lock:
            current_time = time.time()

            # Periodic cleanup
            if current_time - self._last_cleanup > self._cleanup_interval:
                await self._cleanup_stale_buckets(current_time)

            # Get or create user bucket
            bucket = self._get_or_create_bucket(user_id, current_time)

            # Refill tokens based on elapsed time
            self._refill_bucket(bucket, current_time)

            # Check if tokens available
            if bucket.tokens >= tokens:
                bucket.tokens -= tokens
                bucket.request_count += 1

                remaining = int(bucket.tokens)
                reset_at = current_time + (
                    (self.config.burst_size - bucket.tokens) / self.config.refill_rate
                )

                logger.debug(
                    f"Rate limit ALLOWED for {user_id}: "
                    f"remaining={remaining}, used={bucket.request_count}"
                )

                return RateLimitResult(
                    allowed=True,
                    remaining=remaining,
                    reset_at=reset_at,
                    limit=self.config.requests_per_minute
                )
            else:
                # Calculate retry time
                tokens_needed = tokens - bucket.tokens
                retry_after = tokens_needed / self.config.refill_rate
                reset_at = current_time + retry_after

                logger.warning(
                    f"Rate limit EXCEEDED for {user_id}: "
                    f"retry_after={retry_after:.2f}s"
                )

                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_at=reset_at,
                    retry_after=retry_after,
                    limit=self.config.requests_per_minute
                )

    def _get_or_create_bucket(self, user_id: str, current_time: float) -> UserBucket:
        """Get existing bucket or create new one."""
        if user_id not in self._buckets:
            self._buckets[user_id] = UserBucket(
                tokens=float(self.config.burst_size),
                last_refill=current_time,
                window_start=current_time
            )
        return self._buckets[user_id]

    def _refill_bucket(self, bucket: UserBucket, current_time: float) -> None:
        """Refill tokens based on elapsed time."""
        elapsed = current_time - bucket.last_refill
        new_tokens = elapsed * self.config.refill_rate

        bucket.tokens = min(
            bucket.tokens + new_tokens,
            float(self.config.burst_size)
        )
        bucket.last_refill = current_time

        # Reset window if needed
        if current_time - bucket.window_start >= self.config.window_size_seconds:
            bucket.request_count = 0
            bucket.window_start = current_time

    async def _cleanup_stale_buckets(self, current_time: float) -> None:
        """Remove buckets that haven't been used recently."""
        stale_threshold = 600  # 10 minutes
        stale_users = [
            user_id for user_id, bucket in self._buckets.items()
            if current_time - bucket.last_refill > stale_threshold
        ]

        for user_id in stale_users:
            del self._buckets[user_id]

        if stale_users:
            logger.info(f"Cleaned up {len(stale_users)} stale rate limit buckets")

        self._last_cleanup = current_time

    def get_user_status(self, user_id: str) -> Dict[str, Any]:
        """
        Get current rate limit status for a user.

        Args:
            user_id: User identifier

        Returns:
            Dict with remaining, limit, reset, and usage stats
        """
        current_time = time.time()

        if user_id not in self._buckets:
            return {
                "remaining": self.config.requests_per_minute,
                "limit": self.config.requests_per_minute,
                "burst": self.config.burst_size,
                "reset_at": current_time + self.config.window_size_seconds,
                "request_count": 0
            }

        bucket = self._buckets[user_id]
        self._refill_bucket(bucket, current_time)

        return {
            "remaining": int(bucket.tokens),
            "limit": self.config.requests_per_minute,
            "burst": self.config.burst_size,
            "reset_at": bucket.window_start + self.config.window_size_seconds,
            "request_count": bucket.request_count
        }

    def reset_user(self, user_id: str) -> None:
        """
        Reset rate limit for a specific user.

        Args:
            user_id: User identifier to reset
        """
        if user_id in self._buckets:
            del self._buckets[user_id]
            logger.info(f"Reset rate limit for user: {user_id}")

    def reset_all(self) -> None:
        """Reset all user rate limits."""
        count = len(self._buckets)
        self._buckets.clear()
        logger.info(f"Reset all rate limits ({count} users)")

    def get_stats(self) -> Dict[str, Any]:
        """Get overall rate limiter statistics."""
        current_time = time.time()
        active_users = len(self._buckets)

        total_requests = sum(b.request_count for b in self._buckets.values())
        limited_users = sum(
            1 for b in self._buckets.values()
            if b.tokens < 1
        )

        return {
            "active_users": active_users,
            "limited_users": limited_users,
            "total_requests_current_window": total_requests,
            "config": {
                "requests_per_minute": self.config.requests_per_minute,
                "burst_size": self.config.burst_size,
                "strategy": self.config.strategy.value
            }
        }


class RateLimitExceeded(Exception):
    """Exception raised when rate limit is exceeded."""

    def __init__(self, retry_after: float, message: str = "Rate limit exceeded"):
        self.retry_after = retry_after
        self.message = message
        super().__init__(self.message)


# Convenience function for decorator usage
def rate_limited(
    limiter: RateLimiter,
    user_id_param: str = "user_id"
):
    """
    Decorator to apply rate limiting to async functions.

    Args:
        limiter: RateLimiter instance
        user_id_param: Name of the parameter containing user ID

    Example:
        @rate_limited(limiter, "user_id")
        async def handle_api_request(user_id: str, data: dict):
            # This will be rate limited
            pass
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            user_id = kwargs.get(user_id_param)
            if not user_id:
                raise ValueError(f"Missing required parameter: {user_id_param}")

            result = await limiter.acquire(user_id)
            if not result.allowed:
                raise RateLimitExceeded(retry_after=result.retry_after)

            return await func(*args, **kwargs)
        return wrapper
    return decorator
