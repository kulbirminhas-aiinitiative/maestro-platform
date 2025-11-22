"""
Policy Management Service

Provides dynamic rate limit rule management without redeployment.
Stores policies in Redis for fast access across instances.
"""

import json
import logging
from typing import Dict, Optional

from ..core.tiers import RateLimitTier

logger = logging.getLogger(__name__)


class PolicyService:
    """
    Dynamic policy management for rate limiting.

    Allows per-tenant overrides, environment-based rules, and time-based adjustments.
    """

    def __init__(self, redis_client, prefix: str = "ratelimit:policy"):
        """
        Initialize policy service.

        Args:
            redis_client: Redis client instance
            prefix: Key prefix for policy storage
        """
        self.redis = redis_client
        self.prefix = prefix
        logger.info(f"PolicyService initialized with prefix '{prefix}'")

    async def get_tenant_override(self, tenant_id: str) -> Optional[RateLimitTier]:
        """
        Get tenant-specific rate limit override.

        Args:
            tenant_id: Tenant identifier

        Returns:
            RateLimitTier if override exists, None otherwise
        """
        try:
            key = f"{self.prefix}:tenant:{tenant_id}"
            data = self.redis.get(key)
            if data:
                config = json.loads(data)
                return RateLimitTier(
                    name=config.get("name", "custom"),
                    requests_per_minute=config["requests_per_minute"],
                    requests_per_hour=config["requests_per_hour"],
                    concurrent_requests=config["concurrent_requests"],
                    burst_allowance=config.get("burst_allowance", 10),
                    monthly_quota=config.get("monthly_quota", 0),
                )
            return None
        except Exception as e:
            logger.error(f"Error getting tenant override for {tenant_id}: {e}")
            return None

    async def set_tenant_override(
        self,
        tenant_id: str,
        requests_per_minute: int,
        requests_per_hour: int,
        concurrent_requests: int,
        burst_allowance: int = 10,
        monthly_quota: int = 0,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set tenant-specific rate limit override.

        Args:
            tenant_id: Tenant identifier
            requests_per_minute: Requests allowed per minute
            requests_per_hour: Requests allowed per hour
            concurrent_requests: Max concurrent requests
            burst_allowance: Burst allowance
            monthly_quota: Monthly quota (0 = unlimited)
            ttl: Optional TTL in seconds (for temporary overrides)

        Returns:
            True if successful
        """
        try:
            key = f"{self.prefix}:tenant:{tenant_id}"
            config = {
                "name": f"custom:{tenant_id}",
                "requests_per_minute": requests_per_minute,
                "requests_per_hour": requests_per_hour,
                "concurrent_requests": concurrent_requests,
                "burst_allowance": burst_allowance,
                "monthly_quota": monthly_quota,
            }
            self.redis.set(key, json.dumps(config))
            if ttl:
                self.redis.expire(key, ttl)
            logger.info(f"Set rate limit override for tenant {tenant_id}")
            return True
        except Exception as e:
            logger.error(f"Error setting tenant override for {tenant_id}: {e}")
            return False

    async def remove_tenant_override(self, tenant_id: str) -> bool:
        """Remove tenant-specific override."""
        try:
            key = f"{self.prefix}:tenant:{tenant_id}"
            self.redis.delete(key)
            logger.info(f"Removed rate limit override for tenant {tenant_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing tenant override for {tenant_id}: {e}")
            return False

    async def get_environment_multiplier(self, environment: str) -> float:
        """
        Get rate limit multiplier for environment.

        Args:
            environment: Environment name (dev, staging, production)

        Returns:
            Multiplier to apply to rate limits
        """
        try:
            key = f"{self.prefix}:env:{environment}"
            multiplier = self.redis.get(key)
            if multiplier:
                return float(multiplier)
            # Default multipliers
            defaults = {
                "development": 0.5,   # Stricter in dev
                "staging": 0.75,      # Moderate in staging
                "production": 1.0,    # Full limits in prod
            }
            return defaults.get(environment.lower(), 1.0)
        except Exception as e:
            logger.error(f"Error getting env multiplier for {environment}: {e}")
            return 1.0

    async def set_environment_multiplier(
        self, environment: str, multiplier: float
    ) -> bool:
        """Set rate limit multiplier for environment."""
        try:
            key = f"{self.prefix}:env:{environment}"
            self.redis.set(key, str(multiplier))
            logger.info(f"Set env multiplier for {environment}: {multiplier}")
            return True
        except Exception as e:
            logger.error(f"Error setting env multiplier: {e}")
            return False

    async def list_tenant_overrides(self) -> Dict[str, Dict]:
        """List all tenant overrides."""
        try:
            pattern = f"{self.prefix}:tenant:*"
            keys = self.redis.keys(pattern)
            overrides = {}
            for key in keys:
                tenant_id = key.decode().split(":")[-1]
                data = self.redis.get(key)
                if data:
                    overrides[tenant_id] = json.loads(data)
            return overrides
        except Exception as e:
            logger.error(f"Error listing tenant overrides: {e}")
            return {}
