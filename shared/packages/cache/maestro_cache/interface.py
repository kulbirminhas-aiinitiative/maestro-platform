"""
Cache Interface - Abstract base class for all cache implementations
"""

from abc import ABC, abstractmethod
from typing import Any, Optional, List
from datetime import timedelta


class CacheInterface(ABC):
    """
    Abstract interface for cache implementations.

    All Maestro cache backends must implement this interface.
    """

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (None = no expiration)

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        pass

    @abstractmethod
    async def clear(self, pattern: Optional[str] = None) -> int:
        """
        Clear cache entries

        Args:
            pattern: Optional pattern to match (e.g., "user:*")
                    None = clear all

        Returns:
            Number of keys deleted
        """
        pass

    @abstractmethod
    async def get_many(self, keys: List[str]) -> dict:
        """Get multiple values at once"""
        pass

    @abstractmethod
    async def set_many(self, mapping: dict, ttl: Optional[int] = None) -> bool:
        """Set multiple values at once"""
        pass

    @abstractmethod
    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment a counter"""
        pass

    @abstractmethod
    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement a counter"""
        pass

    @abstractmethod
    async def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL in seconds"""
        pass

    @abstractmethod
    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration on existing key"""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if cache backend is healthy"""
        pass

    @abstractmethod
    async def close(self):
        """Close cache connection"""
        pass
