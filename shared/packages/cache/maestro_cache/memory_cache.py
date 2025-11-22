"""
In-Memory Cache Implementation

For development, testing, or single-instance deployments.
"""

import asyncio
import time
import logging
from typing import Any, Optional, List, Dict
from collections import OrderedDict

from .interface import CacheInterface

logger = logging.getLogger(__name__)


class InMemoryCache(CacheInterface):
    """
    In-memory cache using OrderedDict with LRU eviction.

    NOT suitable for production multi-instance deployments.
    Use for: development, testing, CI/CD pipelines.
    """

    def __init__(
        self,
        default_ttl: Optional[int] = 3600,
        max_size: int = 10000,
    ):
        """
        Initialize in-memory cache

        Args:
            default_ttl: Default TTL in seconds
            max_size: Maximum number of items (LRU eviction)
        """
        self.default_ttl = default_ttl
        self.max_size = max_size

        # Storage: key -> (value, expiry_timestamp)
        self._cache: OrderedDict[str, tuple[Any, Optional[float]]] = OrderedDict()
        self._lock = asyncio.Lock()

    def _is_expired(self, expiry: Optional[float]) -> bool:
        """Check if entry is expired"""
        if expiry is None:
            return False
        return time.time() > expiry

    def _evict_if_needed(self):
        """Evict oldest item if cache is full (LRU)"""
        if len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)  # Remove oldest

    async def get(self, key: str) -> Optional[Any]:
        """Get value from memory"""
        async with self._lock:
            if key not in self._cache:
                return None

            value, expiry = self._cache[key]

            # Check expiration
            if self._is_expired(expiry):
                del self._cache[key]
                return None

            # Move to end (LRU)
            self._cache.move_to_end(key)
            return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in memory"""
        async with self._lock:
            ttl = ttl if ttl is not None else self.default_ttl
            expiry = time.time() + ttl if ttl else None

            self._evict_if_needed()
            self._cache[key] = (value, expiry)
            self._cache.move_to_end(key)
            return True

    async def delete(self, key: str) -> bool:
        """Delete key from memory"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        async with self._lock:
            if key not in self._cache:
                return False

            _, expiry = self._cache[key]
            if self._is_expired(expiry):
                del self._cache[key]
                return False

            return True

    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear cache entries"""
        async with self._lock:
            if pattern is None:
                count = len(self._cache)
                self._cache.clear()
                return count

            # Simple wildcard matching
            import fnmatch
            keys_to_delete = [
                k for k in self._cache.keys()
                if fnmatch.fnmatch(k, pattern)
            ]

            for key in keys_to_delete:
                del self._cache[key]

            return len(keys_to_delete)

    async def get_many(self, keys: List[str]) -> dict:
        """Get multiple values"""
        result = {}
        for key in keys:
            value = await self.get(key)
            if value is not None:
                result[key] = value
        return result

    async def set_many(self, mapping: dict, ttl: Optional[int] = None) -> bool:
        """Set multiple values"""
        for key, value in mapping.items():
            await self.set(key, value, ttl)
        return True

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        async with self._lock:
            current = 0
            if key in self._cache:
                value, expiry = self._cache[key]
                if not self._is_expired(expiry):
                    current = int(value) if isinstance(value, (int, float)) else 0

            new_value = current + amount
            await self.set(key, new_value)
            return new_value

    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement counter"""
        return await self.increment(key, -amount)

    async def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL"""
        async with self._lock:
            if key not in self._cache:
                return None

            _, expiry = self._cache[key]
            if expiry is None:
                return -1  # No expiration

            remaining = int(expiry - time.time())
            return remaining if remaining > 0 else None

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration"""
        async with self._lock:
            if key not in self._cache:
                return False

            value, _ = self._cache[key]
            expiry = time.time() + ttl
            self._cache[key] = (value, expiry)
            return True

    async def health_check(self) -> bool:
        """Always healthy (in-memory)"""
        return True

    async def close(self):
        """No-op for in-memory cache"""
        pass
