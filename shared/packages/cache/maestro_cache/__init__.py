"""
Maestro Cache - Standardized Cache Interface

Provides unified caching interface for all Maestro Platform services.

Usage:
    from maestro_cache import CacheService

    cache = CacheService()  # Auto-configured from MAESTRO_CACHE_URL
    await cache.set("key", "value", ttl=3600)
    value = await cache.get("key")
"""

from .interface import CacheInterface
from .redis_cache import RedisCache
from .memory_cache import InMemoryCache
from .factory import CacheService

__version__ = "1.0.0"

__all__ = [
    "CacheInterface",
    "RedisCache",
    "InMemoryCache",
    "CacheService",
]
