"""
Enterprise database query caching for MAESTRO.

Provides:
- CacheConfig for Redis/memory cache configuration
- QueryCache for key-value query result caching
- CacheManager for cache lifecycle and decorators
"""

import asyncio
import hashlib
import json
import pickle
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import (
    Any, Callable, Dict, Generic, List, Optional, Set, TypeVar, Union
)

from .exceptions import CacheException, CacheConnectionException, CacheSerializationException


def _get_logger():
    """Lazy logger initialization to avoid circular imports."""
    try:
        from maestro_core_logging import get_logger
        return get_logger(__name__)
    except ImportError:
        import logging
        return logging.getLogger(__name__)


logger = type("LazyLogger", (), {"__getattr__": lambda self, name: getattr(_get_logger(), name)})()


T = TypeVar("T")


# =============================================================================
# Enums
# =============================================================================

class CacheBackend(str, Enum):
    """Supported cache backends."""
    MEMORY = "memory"      # In-memory (single process)
    REDIS = "redis"        # Redis (distributed)
    NONE = "none"          # No caching


class SerializationFormat(str, Enum):
    """Cache serialization formats."""
    JSON = "json"          # JSON (human readable, slower)
    PICKLE = "pickle"      # Pickle (faster, Python only)
    MSGPACK = "msgpack"    # MessagePack (compact, cross-language)


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class CacheConfig:
    """
    Cache configuration settings.

    Attributes:
        backend: Cache backend to use
        redis_url: Redis connection URL (for Redis backend)
        default_ttl: Default TTL in seconds
        max_memory_items: Max items in memory cache
        serialization: Serialization format
        key_prefix: Prefix for all cache keys
    """

    backend: CacheBackend = CacheBackend.MEMORY
    redis_url: str = "redis://localhost:6379/0"
    default_ttl: int = 300  # 5 minutes
    max_memory_items: int = 10000
    serialization: SerializationFormat = SerializationFormat.JSON
    key_prefix: str = "maestro:db:"
    enable_stats: bool = True

    def __post_init__(self):
        """Validate configuration."""
        if self.default_ttl <= 0:
            raise ValueError("default_ttl must be positive")
        if self.max_memory_items <= 0:
            raise ValueError("max_memory_items must be positive")


@dataclass
class CacheEntry:
    """Single cache entry with metadata."""

    value: Any
    expires_at: float
    created_at: float = field(default_factory=time.time)
    hits: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if entry is expired."""
        return time.time() > self.expires_at

    @property
    def ttl_remaining(self) -> float:
        """Get remaining TTL in seconds."""
        return max(0, self.expires_at - time.time())


@dataclass
class CacheStats:
    """Cache statistics."""

    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    evictions: int = 0
    errors: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate percentage."""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "sets": self.sets,
            "deletes": self.deletes,
            "evictions": self.evictions,
            "errors": self.errors,
            "hit_rate": round(self.hit_rate, 2),
        }


# =============================================================================
# Cache Backend Interface
# =============================================================================

class CacheBackendInterface(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass

    @abstractmethod
    async def clear(self) -> int:
        """Clear all cache entries."""
        pass

    @abstractmethod
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        pass


# =============================================================================
# Memory Cache Backend
# =============================================================================

class MemoryCacheBackend(CacheBackendInterface):
    """
    In-memory cache backend.

    Simple LRU-style cache for single-process applications.
    """

    def __init__(self, max_items: int = 10000, default_ttl: int = 300):
        """
        Initialize memory cache.

        Args:
            max_items: Maximum number of items to store
            default_ttl: Default TTL in seconds
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._max_items = max_items
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                return None

            if entry.is_expired:
                del self._cache[key]
                return None

            entry.hits += 1
            return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        ttl = ttl or self._default_ttl
        expires_at = time.time() + ttl

        async with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self._max_items and key not in self._cache:
                await self._evict_oldest()

            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
            return True

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        entry = self._cache.get(key)
        if entry is None:
            return False
        if entry.is_expired:
            async with self._lock:
                self._cache.pop(key, None)
            return False
        return True

    async def clear(self) -> int:
        """Clear all cache entries."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        import fnmatch

        all_keys = list(self._cache.keys())

        if pattern == "*":
            return all_keys

        return [k for k in all_keys if fnmatch.fnmatch(k, pattern)]

    async def _evict_oldest(self) -> None:
        """Evict oldest/least accessed entries."""
        # First, remove expired entries
        expired = [k for k, v in self._cache.items() if v.is_expired]
        for key in expired:
            del self._cache[key]

        # If still at capacity, remove least recently accessed
        if len(self._cache) >= self._max_items:
            # Sort by hits (ascending) and created_at (ascending)
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: (self._cache[k].hits, self._cache[k].created_at)
            )
            # Remove bottom 10%
            to_remove = max(1, len(sorted_keys) // 10)
            for key in sorted_keys[:to_remove]:
                del self._cache[key]

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_hits = sum(e.hits for e in self._cache.values())
        expired_count = sum(1 for e in self._cache.values() if e.is_expired)

        return {
            "total_entries": len(self._cache),
            "max_entries": self._max_items,
            "expired_entries": expired_count,
            "total_hits": total_hits,
        }


# =============================================================================
# Redis Cache Backend
# =============================================================================

class RedisCacheBackend(CacheBackendInterface):
    """
    Redis cache backend.

    Distributed cache for multi-process/multi-server applications.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        default_ttl: int = 300,
        serialization: SerializationFormat = SerializationFormat.JSON
    ):
        """
        Initialize Redis cache.

        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds
            serialization: Serialization format
        """
        self._redis_url = redis_url
        self._default_ttl = default_ttl
        self._serialization = serialization
        self._redis = None

    async def _get_redis(self):
        """Get or create Redis connection."""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(self._redis_url)
            except ImportError:
                raise CacheException(
                    message="redis package not installed. Install with: pip install redis"
                )
            except Exception as e:
                raise CacheConnectionException(
                    message=f"Failed to connect to Redis: {e}",
                    cause=e
                )
        return self._redis

    def _serialize(self, value: Any) -> bytes:
        """Serialize value for storage."""
        try:
            if self._serialization == SerializationFormat.JSON:
                return json.dumps(value, default=str).encode("utf-8")
            elif self._serialization == SerializationFormat.PICKLE:
                return pickle.dumps(value)
            elif self._serialization == SerializationFormat.MSGPACK:
                import msgpack
                return msgpack.packb(value, default=str)
            else:
                return json.dumps(value, default=str).encode("utf-8")
        except Exception as e:
            raise CacheSerializationException(
                message=f"Failed to serialize cache value: {e}",
                cause=e
            )

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize value from storage."""
        try:
            if self._serialization == SerializationFormat.JSON:
                return json.loads(data.decode("utf-8"))
            elif self._serialization == SerializationFormat.PICKLE:
                return pickle.loads(data)
            elif self._serialization == SerializationFormat.MSGPACK:
                import msgpack
                return msgpack.unpackb(data, raw=False)
            else:
                return json.loads(data.decode("utf-8"))
        except Exception as e:
            raise CacheSerializationException(
                message=f"Failed to deserialize cache value: {e}",
                cause=e
            )

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis."""
        redis = await self._get_redis()
        try:
            data = await redis.get(key)
            if data is None:
                return None
            return self._deserialize(data)
        except CacheSerializationException:
            raise
        except Exception as e:
            raise CacheException(
                message=f"Redis get failed: {e}",
                cause=e
            )

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis."""
        ttl = ttl or self._default_ttl
        redis = await self._get_redis()

        try:
            data = self._serialize(value)
            await redis.setex(key, ttl, data)
            return True
        except CacheSerializationException:
            raise
        except Exception as e:
            raise CacheException(
                message=f"Redis set failed: {e}",
                cause=e
            )

    async def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        redis = await self._get_redis()
        try:
            result = await redis.delete(key)
            return result > 0
        except Exception as e:
            raise CacheException(
                message=f"Redis delete failed: {e}",
                cause=e
            )

    async def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        redis = await self._get_redis()
        try:
            return await redis.exists(key) > 0
        except Exception as e:
            raise CacheException(
                message=f"Redis exists check failed: {e}",
                cause=e
            )

    async def clear(self) -> int:
        """Clear all cache entries with prefix."""
        redis = await self._get_redis()
        try:
            keys = await redis.keys("*")
            if keys:
                return await redis.delete(*keys)
            return 0
        except Exception as e:
            raise CacheException(
                message=f"Redis clear failed: {e}",
                cause=e
            )

    async def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        redis = await self._get_redis()
        try:
            keys = await redis.keys(pattern)
            return [k.decode("utf-8") if isinstance(k, bytes) else k for k in keys]
        except Exception as e:
            raise CacheException(
                message=f"Redis keys failed: {e}",
                cause=e
            )

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None


# =============================================================================
# Query Cache
# =============================================================================

class QueryCache:
    """
    Query result cache with intelligent key generation.

    Caches database query results to reduce database load.

    Example:
        ```python
        cache = QueryCache(config)
        await cache.initialize()

        # Cache a query result
        key = cache.generate_key("SELECT * FROM users WHERE id = ?", [123])
        await cache.set(key, user_data, ttl=300)

        # Retrieve cached result
        cached = await cache.get(key)
        ```
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialize query cache.

        Args:
            config: Cache configuration
        """
        self._config = config or CacheConfig()
        self._backend: Optional[CacheBackendInterface] = None
        self._stats = CacheStats()
        self._initialized = False

    @property
    def stats(self) -> CacheStats:
        """Get cache statistics."""
        return self._stats

    async def initialize(self) -> None:
        """Initialize cache backend."""
        if self._initialized:
            return

        if self._config.backend == CacheBackend.MEMORY:
            self._backend = MemoryCacheBackend(
                max_items=self._config.max_memory_items,
                default_ttl=self._config.default_ttl
            )
        elif self._config.backend == CacheBackend.REDIS:
            self._backend = RedisCacheBackend(
                redis_url=self._config.redis_url,
                default_ttl=self._config.default_ttl,
                serialization=self._config.serialization
            )
        else:
            # No-op backend
            self._backend = None

        self._initialized = True
        logger.info(
            "Query cache initialized",
            backend=self._config.backend.value
        )

    def generate_key(
        self,
        query: str,
        params: Optional[Union[Dict, List, tuple]] = None,
        prefix: Optional[str] = None
    ) -> str:
        """
        Generate cache key from query and parameters.

        Args:
            query: SQL query string
            params: Query parameters
            prefix: Optional key prefix

        Returns:
            Cache key string
        """
        # Normalize query (remove extra whitespace)
        normalized_query = " ".join(query.split())

        # Serialize params
        params_str = json.dumps(params, sort_keys=True, default=str) if params else ""

        # Create hash
        content = f"{normalized_query}:{params_str}"
        hash_value = hashlib.md5(content.encode()).hexdigest()

        # Build key
        key_prefix = prefix or self._config.key_prefix
        return f"{key_prefix}{hash_value}"

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if not self._backend:
            return None

        try:
            value = await self._backend.get(key)

            if value is not None:
                self._stats.hits += 1
                logger.debug("Cache hit", key=key)
            else:
                self._stats.misses += 1
                logger.debug("Cache miss", key=key)

            return value

        except Exception as e:
            self._stats.errors += 1
            logger.warning("Cache get error", key=key, error=str(e))
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        if not self._backend:
            return False

        try:
            result = await self._backend.set(key, value, ttl)
            self._stats.sets += 1
            logger.debug("Cache set", key=key, ttl=ttl or self._config.default_ttl)
            return result

        except Exception as e:
            self._stats.errors += 1
            logger.warning("Cache set error", key=key, error=str(e))
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        if not self._backend:
            return False

        try:
            result = await self._backend.delete(key)
            if result:
                self._stats.deletes += 1
            return result

        except Exception as e:
            self._stats.errors += 1
            logger.warning("Cache delete error", key=key, error=str(e))
            return False

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        Invalidate all keys matching pattern.

        Args:
            pattern: Key pattern (supports * wildcard)

        Returns:
            Number of keys invalidated
        """
        if not self._backend:
            return 0

        try:
            keys = await self._backend.keys(f"{self._config.key_prefix}{pattern}")
            count = 0

            for key in keys:
                if await self._backend.delete(key):
                    count += 1
                    self._stats.deletes += 1

            logger.info("Cache invalidated", pattern=pattern, count=count)
            return count

        except Exception as e:
            self._stats.errors += 1
            logger.warning("Cache invalidation error", pattern=pattern, error=str(e))
            return 0

    async def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        if not self._backend:
            return 0

        try:
            count = await self._backend.clear()
            self._stats = CacheStats()  # Reset stats
            logger.info("Cache cleared", count=count)
            return count

        except Exception as e:
            logger.warning("Cache clear error", error=str(e))
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        stats = self._stats.to_dict()
        stats["backend"] = self._config.backend.value
        stats["initialized"] = self._initialized

        if isinstance(self._backend, MemoryCacheBackend):
            stats["backend_stats"] = self._backend.get_stats()

        return stats


# =============================================================================
# Cache Manager
# =============================================================================

class CacheManager:
    """
    High-level cache manager with decorator support.

    Provides easy-to-use caching decorators and utilities.

    Example:
        ```python
        manager = CacheManager()
        await manager.initialize()

        @manager.cached(ttl=300)
        async def get_user(user_id: str) -> User:
            return await db.query(User).get(user_id)

        # First call hits database
        user = await get_user("123")

        # Second call returns cached
        user = await get_user("123")
        ```
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialize cache manager.

        Args:
            config: Cache configuration
        """
        self._config = config or CacheConfig()
        self._cache = QueryCache(self._config)
        self._initialized = False

    @property
    def cache(self) -> QueryCache:
        """Get underlying query cache."""
        return self._cache

    async def initialize(self) -> None:
        """Initialize cache manager."""
        if self._initialized:
            return

        await self._cache.initialize()
        self._initialized = True

    async def close(self) -> None:
        """Close cache connections."""
        if isinstance(self._cache._backend, RedisCacheBackend):
            await self._cache._backend.close()

    def cached(
        self,
        ttl: Optional[int] = None,
        key_prefix: Optional[str] = None,
        key_builder: Optional[Callable[..., str]] = None
    ) -> Callable:
        """
        Decorator for caching function results.

        Args:
            ttl: Cache TTL in seconds
            key_prefix: Optional key prefix
            key_builder: Optional function to build cache key

        Returns:
            Decorator function

        Example:
            ```python
            @cache_manager.cached(ttl=600)
            async def expensive_query(param: str) -> List[Dict]:
                return await db.execute(...)
            ```
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Build cache key
                if key_builder:
                    key = key_builder(*args, **kwargs)
                else:
                    # Default key builder
                    key_parts = [
                        key_prefix or func.__name__,
                        str(args) if args else "",
                        str(sorted(kwargs.items())) if kwargs else ""
                    ]
                    key = self._cache.generate_key(
                        ":".join(key_parts),
                        prefix=self._config.key_prefix
                    )

                # Try to get from cache
                cached = await self._cache.get(key)
                if cached is not None:
                    return cached

                # Execute function
                result = await func(*args, **kwargs)

                # Cache result
                await self._cache.set(key, result, ttl)

                return result

            # Add cache control methods
            wrapper.cache_key = lambda *a, **kw: key_builder(*a, **kw) if key_builder else None
            wrapper.invalidate = lambda: self._cache.invalidate_pattern(f"{key_prefix or func.__name__}*")

            return wrapper

        return decorator

    def invalidate_on(self, *patterns: str) -> Callable:
        """
        Decorator to invalidate cache patterns after function execution.

        Args:
            *patterns: Cache key patterns to invalidate

        Returns:
            Decorator function

        Example:
            ```python
            @cache_manager.invalidate_on("user:*", "users_list")
            async def update_user(user_id: str, data: dict):
                # After this runs, user:* and users_list are invalidated
                await db.update(User, user_id, data)
            ```
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                result = await func(*args, **kwargs)

                # Invalidate patterns
                for pattern in patterns:
                    await self._cache.invalidate_pattern(pattern)

                return result

            return wrapper

        return decorator

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return await self._cache.get(key)

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        return await self._cache.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        return await self._cache.delete(key)

    async def clear(self) -> int:
        """Clear all cache."""
        return await self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._cache.get_stats()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "CacheBackend",
    "SerializationFormat",

    # Configuration
    "CacheConfig",
    "CacheEntry",
    "CacheStats",

    # Backends
    "CacheBackendInterface",
    "MemoryCacheBackend",
    "RedisCacheBackend",

    # Cache
    "QueryCache",
    "CacheManager",
]
