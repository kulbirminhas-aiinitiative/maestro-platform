"""
Cache Factory - Auto-configure cache from environment variables

Reads MAESTRO_CACHE_URL and creates appropriate cache backend.
"""

import os
import logging
from typing import Optional
from urllib.parse import urlparse

from .interface import CacheInterface
from .redis_cache import RedisCache
from .memory_cache import InMemoryCache

logger = logging.getLogger(__name__)


def CacheService(
    url: Optional[str] = None,
    default_ttl: Optional[int] = None,
    key_prefix: str = "",
) -> CacheInterface:
    """
    Create cache service from environment configuration.

    Configuration via environment variables:
        MAESTRO_CACHE_URL - Cache backend URL
            redis://localhost:6379/0  → Redis cache
            rediss://host:6379/0      → Redis with SSL
            memory://                 → In-memory cache

        MAESTRO_CACHE_TTL - Default TTL in seconds (default: 3600)
        MAESTRO_CACHE_PREFIX - Key prefix for namespacing

    Args:
        url: Override MAESTRO_CACHE_URL
        default_ttl: Override MAESTRO_CACHE_TTL
        key_prefix: Override MAESTRO_CACHE_PREFIX

    Returns:
        Configured cache instance

    Examples:
        # Auto-configure from environment
        cache = CacheService()

        # Override URL
        cache = CacheService(url="redis://localhost:6379/0")

        # Custom namespace
        cache = CacheService(key_prefix="myservice:")
    """

    # Get configuration from environment
    cache_url = url or os.getenv("MAESTRO_CACHE_URL", "memory://")
    cache_ttl = default_ttl or int(os.getenv("MAESTRO_CACHE_TTL", "3600"))
    cache_prefix = key_prefix or os.getenv("MAESTRO_CACHE_PREFIX", "")

    # Parse URL scheme
    parsed = urlparse(cache_url)
    scheme = parsed.scheme.lower()

    logger.info(f"Initializing cache service: {scheme}:// (TTL={cache_ttl}s, prefix='{cache_prefix}')")

    # Create appropriate backend
    if scheme in ("redis", "rediss"):
        return RedisCache(
            url=cache_url,
            default_ttl=cache_ttl,
            key_prefix=cache_prefix,
        )

    elif scheme == "memory":
        max_size = int(os.getenv("MAESTRO_CACHE_MAX_SIZE", "10000"))
        return InMemoryCache(
            default_ttl=cache_ttl,
            max_size=max_size,
        )

    else:
        logger.warning(f"Unknown cache scheme '{scheme}', falling back to in-memory")
        return InMemoryCache(default_ttl=cache_ttl)


# Singleton instance (optional convenience)
_default_cache: Optional[CacheInterface] = None


def get_cache() -> CacheInterface:
    """
    Get singleton cache instance.

    Useful for simple cases where you want a shared cache instance.
    """
    global _default_cache

    if _default_cache is None:
        _default_cache = CacheService()

    return _default_cache
