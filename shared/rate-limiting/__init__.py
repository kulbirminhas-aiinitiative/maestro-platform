"""
Maestro Shared Rate Limiting Package

A reusable traffic governance platform for all Maestro API services.
Provides distributed rate limiting with Redis backend, policy management,
and analytics.

Usage:
    from maestro_rate_limiting import RateLimiter, RateLimitMiddleware
    from maestro_rate_limiting.policy import PolicyService
"""

from .core.limiter import RateLimiter, RateLimitResult
from .core.tiers import RateLimitTier, RATE_LIMIT_TIERS
from .middleware.fastapi import RateLimitMiddleware
from .policy.service import PolicyService
from .analytics.metrics import RateLimitMetrics

__version__ = "1.0.0"
__all__ = [
    "RateLimiter",
    "RateLimitResult",
    "RateLimitTier",
    "RATE_LIMIT_TIERS",
    "RateLimitMiddleware",
    "PolicyService",
    "RateLimitMetrics",
]
