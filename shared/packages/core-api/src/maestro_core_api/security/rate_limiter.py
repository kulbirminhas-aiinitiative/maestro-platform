"""
Simple rate limiter using token bucket algorithm.

Provides request rate limiting for UTCP services to prevent abuse
and ensure fair resource allocation.
"""

import time
from typing import Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

from maestro_core_logging import get_logger

logger = get_logger(__name__)


@dataclass
class TokenBucket:
    """
    Token bucket for rate limiting.

    Tokens are added at a constant rate. Each request consumes one token.
    When bucket is empty, requests are rejected.
    """
    capacity: int  # Maximum tokens
    refill_rate: float  # Tokens per second
    tokens: float = field(init=False)  # Current tokens
    last_refill: float = field(init=False)  # Last refill timestamp

    def __post_init__(self):
        self.tokens = float(self.capacity)
        self.last_refill = time.time()

    def refill(self):
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill

        # Add tokens based on elapsed time
        self.tokens = min(
            self.capacity,
            self.tokens + (elapsed * self.refill_rate)
        )

        self.last_refill = now

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.

        Returns:
            True if tokens available, False otherwise
        """
        self.refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True

        return False

    def get_wait_time(self) -> float:
        """Get time to wait until next token available."""
        self.refill()

        if self.tokens >= 1:
            return 0.0

        tokens_needed = 1 - self.tokens
        return tokens_needed / self.refill_rate


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_minute: int = 100
    burst_size: int = 20
    enable_per_user_limits: bool = True
    enable_per_service_limits: bool = True


class RateLimiter:
    """
    Simple in-memory rate limiter using token bucket algorithm.

    Features:
    - Per-identifier rate limiting
    - Configurable rates and burst sizes
    - Automatic token refill
    - Wait time calculation
    - Clean expired buckets

    Example:
        >>> limiter = RateLimiter(requests_per_minute=100)
        >>> if limiter.check_limit("user-123"):
        >>>     # Process request
        >>>     pass
        >>> else:
        >>>     # Return 429 Too Many Requests
        >>>     pass
    """

    def __init__(
        self,
        requests_per_minute: int = 100,
        burst_size: Optional[int] = None,
        cleanup_interval: int = 300  # 5 minutes
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Average requests per minute allowed
            burst_size: Maximum burst size (defaults to rpm/3)
            cleanup_interval: Seconds between cleanup of expired buckets
        """
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size or max(requests_per_minute // 3, 10)
        self.cleanup_interval = cleanup_interval

        # Token buckets per identifier
        self.buckets: Dict[str, TokenBucket] = {}

        # Last cleanup time
        self.last_cleanup = time.time()

        # Statistics
        self.stats = {
            "total_requests": 0,
            "allowed_requests": 0,
            "rejected_requests": 0,
            "unique_identifiers": 0
        }

        logger.info(
            "Rate limiter initialized",
            rpm=requests_per_minute,
            burst_size=self.burst_size
        )

    def check_limit(self, identifier: str, tokens: int = 1) -> bool:
        """
        Check if request is within rate limit.

        Args:
            identifier: Unique identifier (user_id, ip_address, etc.)
            tokens: Number of tokens to consume (default: 1)

        Returns:
            True if request allowed, False if rate limited
        """
        self.stats["total_requests"] += 1

        # Get or create bucket for this identifier
        if identifier not in self.buckets:
            self.buckets[identifier] = TokenBucket(
                capacity=self.burst_size,
                refill_rate=self.requests_per_minute / 60.0  # Convert to per-second
            )
            self.stats["unique_identifiers"] = len(self.buckets)

        bucket = self.buckets[identifier]

        # Try to consume tokens
        allowed = bucket.consume(tokens)

        if allowed:
            self.stats["allowed_requests"] += 1
            logger.debug(f"Request allowed for {identifier}", tokens_remaining=bucket.tokens)
        else:
            self.stats["rejected_requests"] += 1
            wait_time = bucket.get_wait_time()
            logger.warning(
                f"Rate limit exceeded for {identifier}",
                wait_time_seconds=wait_time
            )

        # Periodic cleanup
        self._maybe_cleanup()

        return allowed

    def get_limit_info(self, identifier: str) -> Dict:
        """
        Get rate limit information for identifier.

        Returns:
            Dictionary with limit info
        """
        if identifier not in self.buckets:
            return {
                "limit": self.requests_per_minute,
                "remaining": self.burst_size,
                "reset_in_seconds": 0,
                "burst_size": self.burst_size
            }

        bucket = self.buckets[identifier]
        bucket.refill()

        return {
            "limit": self.requests_per_minute,
            "remaining": int(bucket.tokens),
            "reset_in_seconds": bucket.get_wait_time() if bucket.tokens < 1 else 0,
            "burst_size": self.burst_size
        }

    def reset_limit(self, identifier: str):
        """Reset rate limit for identifier."""
        if identifier in self.buckets:
            del self.buckets[identifier]
            logger.info(f"Rate limit reset for {identifier}")

    def _maybe_cleanup(self):
        """Clean up old buckets periodically."""
        now = time.time()

        if now - self.last_cleanup < self.cleanup_interval:
            return

        # Remove buckets that haven't been used recently
        cutoff_time = now - self.cleanup_interval
        identifiers_to_remove = [
            identifier
            for identifier, bucket in self.buckets.items()
            if bucket.last_refill < cutoff_time
        ]

        for identifier in identifiers_to_remove:
            del self.buckets[identifier]

        if identifiers_to_remove:
            logger.info(
                f"Cleaned up {len(identifiers_to_remove)} expired rate limit buckets"
            )

        self.last_cleanup = now
        self.stats["unique_identifiers"] = len(self.buckets)

    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        return {
            **self.stats,
            "rejection_rate": (
                self.stats["rejected_requests"] / self.stats["total_requests"]
                if self.stats["total_requests"] > 0
                else 0.0
            )
        }


class ServiceRateLimiter:
    """
    Multi-level rate limiter for services.

    Supports:
    - Global rate limits
    - Per-service rate limits
    - Per-user rate limits

    Example:
        >>> limiter = ServiceRateLimiter()
        >>> limiter.add_service_limit("quality-fabric", rpm=200)
        >>> limiter.add_user_limit("user-123", rpm=50)
        >>>
        >>> allowed = limiter.check_limits(
        >>>     service="quality-fabric",
        >>>     user_id="user-123"
        >>> )
    """

    def __init__(self, global_rpm: int = 1000):
        """
        Initialize service rate limiter.

        Args:
            global_rpm: Global requests per minute limit
        """
        self.global_limiter = RateLimiter(requests_per_minute=global_rpm)
        self.service_limiters: Dict[str, RateLimiter] = {}
        self.user_limiters: Dict[str, RateLimiter] = {}

        logger.info("Service rate limiter initialized", global_rpm=global_rpm)

    def add_service_limit(self, service_name: str, rpm: int):
        """Add rate limit for specific service."""
        self.service_limiters[service_name] = RateLimiter(requests_per_minute=rpm)
        logger.info(f"Added rate limit for service {service_name}", rpm=rpm)

    def add_user_limit(self, user_id: str, rpm: int):
        """Add rate limit for specific user."""
        self.user_limiters[user_id] = RateLimiter(requests_per_minute=rpm)
        logger.info(f"Added rate limit for user {user_id}", rpm=rpm)

    def check_limits(
        self,
        service: Optional[str] = None,
        user_id: Optional[str] = None,
        identifier: Optional[str] = None
    ) -> bool:
        """
        Check all applicable rate limits.

        Args:
            service: Service name
            user_id: User identifier
            identifier: Additional identifier (ip_address, etc.)

        Returns:
            True if all limits pass, False if any limit exceeded
        """
        # Build composite identifier
        composite_id = identifier or "anonymous"
        if user_id:
            composite_id = f"user:{user_id}"
        if service:
            composite_id = f"{composite_id}:service:{service}"

        # Check global limit
        if not self.global_limiter.check_limit(composite_id):
            return False

        # Check service-specific limit
        if service and service in self.service_limiters:
            if not self.service_limiters[service].check_limit(composite_id):
                return False

        # Check user-specific limit
        if user_id and user_id in self.user_limiters:
            if not self.user_limiters[user_id].check_limit(composite_id):
                return False

        return True

    def get_all_stats(self) -> Dict:
        """Get statistics for all limiters."""
        return {
            "global": self.global_limiter.get_stats(),
            "services": {
                name: limiter.get_stats()
                for name, limiter in self.service_limiters.items()
            },
            "users": {
                user_id: limiter.get_stats()
                for user_id, limiter in self.user_limiters.items()
            }
        }


# Global rate limiter instance
_global_rate_limiter: Optional[ServiceRateLimiter] = None


def get_rate_limiter() -> ServiceRateLimiter:
    """Get or create global rate limiter instance."""
    global _global_rate_limiter

    if _global_rate_limiter is None:
        _global_rate_limiter = ServiceRateLimiter(global_rpm=1000)

    return _global_rate_limiter


def rate_limit(
    requests_per_minute: int = 100,
    burst_size: Optional[int] = None
):
    """
    Decorator for rate limiting endpoints.

    Example:
        >>> @app.get("/api/endpoint")
        >>> @rate_limit(requests_per_minute=100)
        >>> async def endpoint(request: Request):
        >>>     return {"status": "ok"}
    """
    def decorator(func):
        limiter = RateLimiter(
            requests_per_minute=requests_per_minute,
            burst_size=burst_size
        )

        async def wrapper(*args, **kwargs):
            from fastapi import Request, HTTPException

            # Extract request from args
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if request is None:
                # No request found, skip rate limiting
                return await func(*args, **kwargs)

            # Get identifier (IP address or user)
            identifier = request.client.host if request.client else "unknown"

            # Check rate limit
            if not limiter.check_limit(identifier):
                limit_info = limiter.get_limit_info(identifier)
                raise HTTPException(
                    status_code=429,
                    detail="Rate limit exceeded",
                    headers={
                        "X-RateLimit-Limit": str(requests_per_minute),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(limit_info["reset_in_seconds"])),
                        "Retry-After": str(int(limit_info["reset_in_seconds"]))
                    }
                )

            # Execute function
            return await func(*args, **kwargs)

        return wrapper

    return decorator
