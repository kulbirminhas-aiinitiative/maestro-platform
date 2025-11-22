"""
Rate Limit Tier Configuration

Defines subscription tiers and their rate limit configurations.
Can be overridden by Policy Management Service for dynamic updates.
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class RateLimitTier:
    """Rate limit configuration for a subscription tier."""

    name: str
    requests_per_minute: int
    requests_per_hour: int
    concurrent_requests: int
    burst_allowance: int = 10
    monthly_quota: int = 0  # 0 = unlimited

    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "requests_per_minute": self.requests_per_minute,
            "requests_per_hour": self.requests_per_hour,
            "concurrent_requests": self.concurrent_requests,
            "burst_allowance": self.burst_allowance,
            "monthly_quota": self.monthly_quota,
        }


# Default tier configurations
RATE_LIMIT_TIERS: Dict[str, RateLimitTier] = {
    "anonymous": RateLimitTier(
        name="anonymous",
        requests_per_minute=5,
        requests_per_hour=50,
        concurrent_requests=5,
        burst_allowance=2,
        monthly_quota=1000,
    ),
    "starter": RateLimitTier(
        name="starter",
        requests_per_minute=10,
        requests_per_hour=100,
        concurrent_requests=10,
        burst_allowance=5,
        monthly_quota=10000,
    ),
    "professional": RateLimitTier(
        name="professional",
        requests_per_minute=50,
        requests_per_hour=1000,
        concurrent_requests=50,
        burst_allowance=20,
        monthly_quota=100000,
    ),
    "enterprise": RateLimitTier(
        name="enterprise",
        requests_per_minute=500,
        requests_per_hour=10000,
        concurrent_requests=200,
        burst_allowance=100,
        monthly_quota=1000000,
    ),
    "platform_admin": RateLimitTier(
        name="platform_admin",
        requests_per_minute=999999,
        requests_per_hour=999999,
        concurrent_requests=999999,
        burst_allowance=999999,
        monthly_quota=0,  # Unlimited
    ),
}


def get_tier(tier_name: str) -> RateLimitTier:
    """Get tier configuration by name, defaulting to starter if not found."""
    return RATE_LIMIT_TIERS.get(tier_name.lower(), RATE_LIMIT_TIERS["starter"])
