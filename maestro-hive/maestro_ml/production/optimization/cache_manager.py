"""
Performance Optimization: Cache Manager
"""

import hashlib
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CacheStrategy(str, Enum):
    """Cache strategies"""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL = "ttl"  # Time To Live


class CacheEntry(BaseModel):
    """Cache entry"""

    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: Optional[int] = None


class CacheManager:
    """
    Performance optimization cache manager

    Features:
    - Multiple cache strategies (LRU, LFU, FIFO, TTL)
    - Cache hit/miss tracking
    - Memory limit enforcement
    - Automatic eviction
    - Cache warming
    """

    def __init__(
        self,
        strategy: CacheStrategy = CacheStrategy.LRU,
        max_size: int = 1000,
        default_ttl_seconds: Optional[int] = 3600,
    ):
        self.strategy = strategy
        self.max_size = max_size
        self.default_ttl_seconds = default_ttl_seconds

        self.cache: dict[str, CacheEntry] = {}
        self.hits = 0
        self.misses = 0
        self.logger = logger

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if key not in self.cache:
            self.misses += 1
            return None

        entry = self.cache[key]

        # Check TTL
        if entry.ttl_seconds:
            age = (datetime.utcnow() - entry.created_at).total_seconds()
            if age > entry.ttl_seconds:
                del self.cache[key]
                self.misses += 1
                return None

        # Update access tracking
        entry.last_accessed = datetime.utcnow()
        entry.access_count += 1

        self.hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None):
        """
        Set cache value

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live (None = use default)
        """
        # Check if we need to evict
        if key not in self.cache and len(self.cache) >= self.max_size:
            self._evict()

        # Create entry
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.utcnow(),
            last_accessed=datetime.utcnow(),
            ttl_seconds=ttl_seconds or self.default_ttl_seconds,
        )

        self.cache[key] = entry

    def delete(self, key: str):
        """Delete a cache entry"""
        if key in self.cache:
            del self.cache[key]

    def clear(self):
        """Clear all cache"""
        self.cache.clear()
        self.hits = 0
        self.misses = 0
        self.logger.info("Cache cleared")

    def _evict(self):
        """Evict an entry based on strategy"""
        if not self.cache:
            return

        if self.strategy == CacheStrategy.LRU:
            # Evict least recently used
            oldest_key = min(
                self.cache.keys(), key=lambda k: self.cache[k].last_accessed
            )
        elif self.strategy == CacheStrategy.LFU:
            # Evict least frequently used
            oldest_key = min(
                self.cache.keys(), key=lambda k: self.cache[k].access_count
            )
        elif self.strategy == CacheStrategy.FIFO:
            # Evict oldest entry
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k].created_at)
        else:  # TTL
            # Evict expired or oldest
            now = datetime.utcnow()
            expired = [
                k
                for k, v in self.cache.items()
                if v.ttl_seconds
                and (now - v.created_at).total_seconds() > v.ttl_seconds
            ]
            if expired:
                oldest_key = expired[0]
            else:
                oldest_key = min(
                    self.cache.keys(), key=lambda k: self.cache[k].created_at
                )

        del self.cache[oldest_key]
        self.logger.debug(f"Evicted cache entry: {oldest_key}")

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics"""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests * 100) if total_requests > 0 else 0

        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "utilization_pct": (len(self.cache) / self.max_size * 100),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_pct": hit_rate,
            "strategy": self.strategy.value,
        }

    @staticmethod
    def generate_key(*args, **kwargs) -> str:
        """
        Generate cache key from arguments

        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Cache key string
        """
        key_str = f"{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_str.encode()).hexdigest()


# Decorator for caching function results
def cached(ttl_seconds: Optional[int] = 3600):
    """
    Decorator to cache function results

    Usage:
        @cached(ttl_seconds=300)
        def expensive_function(arg1, arg2):
            return result
    """
    cache = CacheManager(strategy=CacheStrategy.TTL, default_ttl_seconds=ttl_seconds)

    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            key = CacheManager.generate_key(func.__name__, args, kwargs)

            # Check cache
            result = cache.get(key)
            if result is not None:
                return result

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            cache.set(key, result, ttl_seconds=ttl_seconds)

            return result

        return wrapper

    return decorator
