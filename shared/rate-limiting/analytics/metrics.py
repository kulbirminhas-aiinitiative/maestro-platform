"""
Rate Limiting Metrics and Analytics

Provides Prometheus metrics and analytics for rate limiting events.
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class RateLimitMetrics:
    """
    Metrics collector for rate limiting events.

    Provides Prometheus-compatible metrics and Redis-based analytics.
    """

    def __init__(self, redis_client, prefix: str = "ratelimit:metrics"):
        """
        Initialize metrics collector.

        Args:
            redis_client: Redis client instance
            prefix: Key prefix for metrics storage
        """
        self.redis = redis_client
        self.prefix = prefix
        self._prometheus_enabled = False
        self._counters = {}

        # Try to import prometheus_client
        try:
            from prometheus_client import Counter, Histogram

            self.requests_total = Counter(
                "rate_limit_requests_total",
                "Total rate limited requests",
                ["tenant_id", "endpoint", "status"]
            )
            self.rejections_total = Counter(
                "rate_limit_rejections_total",
                "Total rate limit rejections",
                ["tenant_id", "endpoint", "reason"]
            )
            self.request_duration = Histogram(
                "rate_limit_check_duration_seconds",
                "Time to check rate limit"
            )
            self._prometheus_enabled = True
            logger.info("RateLimitMetrics initialized with Prometheus support")
        except ImportError:
            logger.info("RateLimitMetrics initialized (Prometheus not available)")

    async def record_request(self, tenant_id: str, endpoint: str):
        """Record a successful request."""
        try:
            # Prometheus metrics
            if self._prometheus_enabled:
                self.requests_total.labels(
                    tenant_id=tenant_id, endpoint=endpoint, status="allowed"
                ).inc()

            # Redis analytics
            today = datetime.utcnow().strftime("%Y-%m-%d")
            hour = datetime.utcnow().strftime("%Y-%m-%d:%H")

            # Daily counter
            daily_key = f"{self.prefix}:daily:{today}:{tenant_id}"
            self.redis.incr(daily_key)
            self.redis.expire(daily_key, 86400 * 7)  # Keep 7 days

            # Hourly counter
            hourly_key = f"{self.prefix}:hourly:{hour}:{tenant_id}"
            self.redis.incr(hourly_key)
            self.redis.expire(hourly_key, 3600 * 24)  # Keep 24 hours

            # Endpoint counter
            endpoint_key = f"{self.prefix}:endpoint:{today}:{endpoint}"
            self.redis.incr(endpoint_key)
            self.redis.expire(endpoint_key, 86400 * 7)

        except Exception as e:
            logger.error(f"Error recording request metric: {e}")

    async def record_rejection(
        self, tenant_id: str, endpoint: str, reason: str
    ):
        """
        Record a rate limit rejection.

        Args:
            tenant_id: Tenant identifier
            endpoint: Request endpoint
            reason: Rejection reason (rate_limit, concurrent_limit)
        """
        try:
            # Prometheus metrics
            if self._prometheus_enabled:
                self.rejections_total.labels(
                    tenant_id=tenant_id, endpoint=endpoint, reason=reason
                ).inc()

            # Redis analytics
            today = datetime.utcnow().strftime("%Y-%m-%d")

            # Rejection counter
            rejection_key = f"{self.prefix}:rejections:{today}:{tenant_id}"
            self.redis.incr(rejection_key)
            self.redis.expire(rejection_key, 86400 * 30)  # Keep 30 days

            # Log for alerting
            logger.warning(
                f"Rate limit rejection: tenant={tenant_id}, "
                f"endpoint={endpoint}, reason={reason}"
            )

        except Exception as e:
            logger.error(f"Error recording rejection metric: {e}")

    async def get_tenant_stats(self, tenant_id: str, days: int = 7) -> dict:
        """
        Get rate limiting stats for a tenant.

        Args:
            tenant_id: Tenant identifier
            days: Number of days to look back

        Returns:
            Dictionary with stats
        """
        try:
            stats = {
                "tenant_id": tenant_id,
                "total_requests": 0,
                "total_rejections": 0,
                "daily_breakdown": [],
            }

            for i in range(days):
                date = datetime.utcnow()
                date = date.replace(day=date.day - i)
                day_str = date.strftime("%Y-%m-%d")

                # Get daily counts
                daily_key = f"{self.prefix}:daily:{day_str}:{tenant_id}"
                rejection_key = f"{self.prefix}:rejections:{day_str}:{tenant_id}"

                requests = int(self.redis.get(daily_key) or 0)
                rejections = int(self.redis.get(rejection_key) or 0)

                stats["total_requests"] += requests
                stats["total_rejections"] += rejections
                stats["daily_breakdown"].append({
                    "date": day_str,
                    "requests": requests,
                    "rejections": rejections,
                })

            return stats

        except Exception as e:
            logger.error(f"Error getting tenant stats: {e}")
            return {"error": str(e)}

    async def get_top_endpoints(self, days: int = 1, limit: int = 10) -> list:
        """Get top endpoints by request count."""
        try:
            date = datetime.utcnow().strftime("%Y-%m-%d")
            pattern = f"{self.prefix}:endpoint:{date}:*"

            endpoints = []
            for key in self.redis.keys(pattern):
                endpoint = key.decode().split(":")[-1]
                count = int(self.redis.get(key) or 0)
                endpoints.append({"endpoint": endpoint, "count": count})

            endpoints.sort(key=lambda x: x["count"], reverse=True)
            return endpoints[:limit]

        except Exception as e:
            logger.error(f"Error getting top endpoints: {e}")
            return []

    async def check_spike(
        self, tenant_id: str, threshold_multiplier: float = 3.0
    ) -> bool:
        """
        Check if tenant has unusual spike in rejections.

        Args:
            tenant_id: Tenant identifier
            threshold_multiplier: How many times above average to trigger

        Returns:
            True if spike detected
        """
        try:
            today = datetime.utcnow().strftime("%Y-%m-%d")

            # Get today's rejections
            today_key = f"{self.prefix}:rejections:{today}:{tenant_id}"
            today_rejections = int(self.redis.get(today_key) or 0)

            # Get average from last 7 days
            total = 0
            for i in range(1, 8):
                date = datetime.utcnow()
                date = date.replace(day=date.day - i)
                day_str = date.strftime("%Y-%m-%d")
                key = f"{self.prefix}:rejections:{day_str}:{tenant_id}"
                total += int(self.redis.get(key) or 0)

            avg = total / 7 if total > 0 else 1

            return today_rejections > (avg * threshold_multiplier)

        except Exception as e:
            logger.error(f"Error checking spike: {e}")
            return False
