"""
Redis Cache Manager for Maestro ML Platform

Provides multi-level caching with:
- Redis-based distributed cache
- In-memory LRU cache
- Cache warming strategies
- Automatic invalidation
- Hit rate tracking
"""

import redis
import json
import pickle
import hashlib
import time
from typing import Any, Optional, Callable, Dict, List
from functools import wraps, lru_cache
from datetime import timedelta
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CacheLevel(Enum):
    """Cache level hierarchy"""
    MEMORY = "memory"  # L1: In-process LRU cache
    REDIS = "redis"    # L2: Distributed Redis cache
    DATABASE = "database"  # L3: Source of truth


@dataclass
class CacheStats:
    """Cache statistics"""
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    @property
    def total_requests(self) -> int:
        """Total cache requests"""
        return self.hits + self.misses


class CacheManager:
    """
    Multi-level cache manager with Redis backend

    Usage:
        cache = CacheManager(redis_url="redis://localhost:6379")

        # Cache a value
        cache.set("user:123", user_data, ttl=300)

        # Get a value
        user = cache.get("user:123")

        # Use decorator
        @cache.cached(ttl=60, key_prefix="models")
        def get_model(model_id: str):
            return db.query(Model).filter(Model.id == model_id).first()
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        default_ttl: int = 300,  # 5 minutes
        max_memory_items: int = 1000,
        enable_memory_cache: bool = True
    ):
        """
        Initialize cache manager

        Args:
            redis_url: Redis connection URL
            default_ttl: Default TTL in seconds
            max_memory_items: Maximum items in memory cache
            enable_memory_cache: Enable L1 in-memory cache
        """
        # Redis connection
        self.redis = redis.from_url(redis_url, decode_responses=False)
        self.default_ttl = default_ttl
        self.enable_memory_cache = enable_memory_cache

        # In-memory L1 cache
        if enable_memory_cache:
            self._memory_cache: Dict[str, tuple] = {}
            self._max_memory_items = max_memory_items

        # Statistics
        self.stats = CacheStats()

        # Test connection
        try:
            self.redis.ping()
            logger.info(f"Connected to Redis at {redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def get(self, key: str, default: Any = None) -> Optional[Any]:
        """
        Get value from cache (checks memory → Redis)

        Args:
            key: Cache key
            default: Default value if not found

        Returns:
            Cached value or default
        """
        # Try memory cache first (L1)
        if self.enable_memory_cache:
            if key in self._memory_cache:
                value, expiry = self._memory_cache[key]
                if expiry is None or time.time() < expiry:
                    self.stats.hits += 1
                    logger.debug(f"L1 cache hit: {key}")
                    return value
                else:
                    # Expired
                    del self._memory_cache[key]

        # Try Redis (L2)
        try:
            value = self.redis.get(key)
            if value is not None:
                self.stats.hits += 1
                deserialized = pickle.loads(value)

                # Populate memory cache
                if self.enable_memory_cache:
                    ttl = self.redis.ttl(key)
                    expiry = time.time() + ttl if ttl > 0 else None
                    self._set_memory(key, deserialized, expiry)

                logger.debug(f"L2 cache hit: {key}")
                return deserialized

            self.stats.misses += 1
            logger.debug(f"Cache miss: {key}")
            return default

        except Exception as e:
            self.stats.errors += 1
            logger.error(f"Cache get error for key {key}: {e}")
            return default

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False
    ) -> bool:
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (None = default_ttl)
            nx: Only set if key doesn't exist

        Returns:
            True if set successfully
        """
        ttl = ttl if ttl is not None else self.default_ttl

        try:
            # Serialize value
            serialized = pickle.dumps(value)

            # Set in Redis
            if nx:
                result = self.redis.set(key, serialized, ex=ttl, nx=True)
            else:
                result = self.redis.set(key, serialized, ex=ttl)

            if result:
                self.stats.sets += 1

                # Set in memory cache
                if self.enable_memory_cache:
                    expiry = time.time() + ttl if ttl > 0 else None
                    self._set_memory(key, value, expiry)

                logger.debug(f"Cache set: {key} (TTL: {ttl}s)")
                return True

            return False

        except Exception as e:
            self.stats.errors += 1
            logger.error(f"Cache set error for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        try:
            # Delete from Redis
            result = self.redis.delete(key)

            # Delete from memory
            if self.enable_memory_cache and key in self._memory_cache:
                del self._memory_cache[key]

            if result:
                self.stats.deletes += 1
                logger.debug(f"Cache delete: {key}")
                return True

            return False

        except Exception as e:
            self.stats.errors += 1
            logger.error(f"Cache delete error for key {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern

        Args:
            pattern: Key pattern (e.g., "user:*")

        Returns:
            Number of keys deleted
        """
        try:
            keys = self.redis.keys(pattern)
            if keys:
                deleted = self.redis.delete(*keys)
                self.stats.deletes += deleted

                # Clear memory cache for matching keys
                if self.enable_memory_cache:
                    for key in list(self._memory_cache.keys()):
                        if self._matches_pattern(key, pattern):
                            del self._memory_cache[key]

                logger.info(f"Deleted {deleted} keys matching pattern: {pattern}")
                return deleted

            return 0

        except Exception as e:
            self.stats.errors += 1
            logger.error(f"Cache delete pattern error for {pattern}: {e}")
            return 0

    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        # Check memory first
        if self.enable_memory_cache and key in self._memory_cache:
            _, expiry = self._memory_cache[key]
            if expiry is None or time.time() < expiry:
                return True

        # Check Redis
        return bool(self.redis.exists(key))

    def ttl(self, key: str) -> int:
        """Get remaining TTL for key in seconds"""
        return self.redis.ttl(key)

    def incr(self, key: str, amount: int = 1) -> int:
        """
        Increment counter

        Args:
            key: Counter key
            amount: Amount to increment

        Returns:
            New value
        """
        return self.redis.incrby(key, amount)

    def _set_memory(self, key: str, value: Any, expiry: Optional[float]):
        """Set value in memory cache with LRU eviction"""
        # Check if we need to evict
        if len(self._memory_cache) >= self._max_memory_items:
            # Simple LRU: remove oldest item
            oldest_key = next(iter(self._memory_cache))
            del self._memory_cache[oldest_key]

        self._memory_cache[key] = (value, expiry)

    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Simple pattern matching (supports * wildcard)"""
        import re
        regex_pattern = pattern.replace("*", ".*")
        return bool(re.match(f"^{regex_pattern}$", key))

    def cached(
        self,
        ttl: Optional[int] = None,
        key_prefix: str = "",
        key_builder: Optional[Callable] = None
    ):
        """
        Decorator to cache function results

        Usage:
            @cache.cached(ttl=300, key_prefix="models")
            def get_model(model_id: str):
                return db.query(Model).filter(Model.id == model_id).first()

        Args:
            ttl: Cache TTL in seconds
            key_prefix: Prefix for cache key
            key_builder: Custom function to build cache key
        """
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Build cache key
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    cache_key = self._build_key(func, args, kwargs, key_prefix)

                # Try to get from cache
                cached_value = self.get(cache_key)
                if cached_value is not None:
                    return cached_value

                # Call function
                result = func(*args, **kwargs)

                # Cache result
                if result is not None:
                    self.set(cache_key, result, ttl=ttl)

                return result

            return wrapper
        return decorator

    def _build_key(
        self,
        func: Callable,
        args: tuple,
        kwargs: dict,
        prefix: str = ""
    ) -> str:
        """Build cache key from function and arguments"""
        # Create key from function name and arguments
        key_parts = [prefix, func.__name__] if prefix else [func.__name__]

        # Add positional args
        for arg in args:
            if isinstance(arg, (str, int, float, bool)):
                key_parts.append(str(arg))
            else:
                # Hash complex objects
                key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])

        # Add keyword args
        for k, v in sorted(kwargs.items()):
            if isinstance(v, (str, int, float, bool)):
                key_parts.append(f"{k}={v}")
            else:
                key_parts.append(f"{k}={hashlib.md5(str(v).encode()).hexdigest()[:8]}")

        return ":".join(key_parts)

    def warm_cache(self, keys_and_values: List[tuple], ttl: Optional[int] = None):
        """
        Warm cache with multiple values

        Args:
            keys_and_values: List of (key, value) tuples
            ttl: TTL for all keys
        """
        pipeline = self.redis.pipeline()

        for key, value in keys_and_values:
            serialized = pickle.dumps(value)
            if ttl:
                pipeline.set(key, serialized, ex=ttl)
            else:
                pipeline.set(key, serialized)

        pipeline.execute()
        logger.info(f"Warmed cache with {len(keys_and_values)} items")

    def get_stats(self) -> Dict:
        """Get cache statistics"""
        return {
            "hits": self.stats.hits,
            "misses": self.stats.misses,
            "hit_rate": f"{self.stats.hit_rate:.2f}%",
            "total_requests": self.stats.total_requests,
            "sets": self.stats.sets,
            "deletes": self.stats.deletes,
            "errors": self.stats.errors,
            "memory_cache_size": len(self._memory_cache) if self.enable_memory_cache else 0
        }

    def clear_stats(self):
        """Reset statistics"""
        self.stats = CacheStats()

    def flush_all(self):
        """Clear all cache (USE WITH CAUTION!)"""
        self.redis.flushdb()
        if self.enable_memory_cache:
            self._memory_cache.clear()
        logger.warning("Cache flushed!")


# ============================================================================
# Global Cache Instance
# ============================================================================

# Initialize global cache (configure in your app startup)
cache_manager: Optional[CacheManager] = None


def init_cache(redis_url: str = "redis://localhost:6379/0", **kwargs):
    """Initialize global cache manager"""
    global cache_manager
    cache_manager = CacheManager(redis_url=redis_url, **kwargs)
    return cache_manager


def get_cache() -> CacheManager:
    """Get global cache instance"""
    if cache_manager is None:
        raise RuntimeError("Cache not initialized. Call init_cache() first.")
    return cache_manager


# ============================================================================
# Common Cache Patterns
# ============================================================================

class ModelCache:
    """Cache manager for ML models"""

    def __init__(self, cache: CacheManager, ttl: int = 600):
        self.cache = cache
        self.ttl = ttl
        self.key_prefix = "model"

    def get_model(self, model_id: str) -> Optional[Any]:
        """Get model from cache"""
        key = f"{self.key_prefix}:{model_id}"
        return self.cache.get(key)

    def set_model(self, model_id: str, model_data: Any):
        """Cache model data"""
        key = f"{self.key_prefix}:{model_id}"
        self.cache.set(key, model_data, ttl=self.ttl)

    def invalidate_model(self, model_id: str):
        """Invalidate model cache"""
        key = f"{self.key_prefix}:{model_id}"
        self.cache.delete(key)

    def invalidate_tenant_models(self, tenant_id: str):
        """Invalidate all models for a tenant"""
        pattern = f"{self.key_prefix}:*:{tenant_id}:*"
        self.cache.delete_pattern(pattern)


class PredictionCache:
    """Cache manager for predictions"""

    def __init__(self, cache: CacheManager, ttl: int = 60):
        self.cache = cache
        self.ttl = ttl
        self.key_prefix = "prediction"

    def get_prediction(self, model_id: str, input_hash: str) -> Optional[Any]:
        """Get cached prediction"""
        key = f"{self.key_prefix}:{model_id}:{input_hash}"
        return self.cache.get(key)

    def set_prediction(self, model_id: str, input_hash: str, prediction: Any):
        """Cache prediction"""
        key = f"{self.key_prefix}:{model_id}:{input_hash}"
        self.cache.set(key, prediction, ttl=self.ttl)

    @staticmethod
    def hash_input(input_data: dict) -> str:
        """Create hash of input data"""
        serialized = json.dumps(input_data, sort_keys=True)
        return hashlib.md5(serialized.encode()).hexdigest()


# ============================================================================
# Usage Examples
# ============================================================================

"""
1. Initialize Cache:

   from performance.cache_manager import init_cache

   # At application startup
   cache = init_cache(redis_url="redis://localhost:6379/0")

2. Basic Usage:

   from performance.cache_manager import get_cache

   cache = get_cache()

   # Set value
   cache.set("user:123", {"name": "John", "email": "john@example.com"}, ttl=300)

   # Get value
   user = cache.get("user:123")

3. Decorator Usage:

   from performance.cache_manager import get_cache

   cache = get_cache()

   @cache.cached(ttl=600, key_prefix="models")
   def get_model(model_id: str):
       # Expensive database query
       return db.query(Model).filter(Model.id == model_id).first()

   # First call: cache miss, queries database
   model = get_model("model-123")

   # Second call: cache hit, returns from cache
   model = get_model("model-123")

4. Model Caching:

   from performance.cache_manager import get_cache, ModelCache

   cache = get_cache()
   model_cache = ModelCache(cache, ttl=600)

   # Cache model
   model_cache.set_model("model-123", model_data)

   # Get model
   model = model_cache.get_model("model-123")

   # Invalidate when model changes
   model_cache.invalidate_model("model-123")

5. Prediction Caching:

   from performance.cache_manager import get_cache, PredictionCache

   cache = get_cache()
   pred_cache = PredictionCache(cache, ttl=60)

   # Hash input
   input_hash = pred_cache.hash_input({"feature1": 0.5, "feature2": 0.8})

   # Check cache
   prediction = pred_cache.get_prediction("model-123", input_hash)
   if prediction is None:
       # Compute prediction
       prediction = model.predict(input_data)
       # Cache result
       pred_cache.set_prediction("model-123", input_hash, prediction)

6. Cache Statistics:

   cache = get_cache()

   # Get stats
   stats = cache.get_stats()
   print(f"Hit rate: {stats['hit_rate']}")
   print(f"Total requests: {stats['total_requests']}")

7. Cache Warming:

   cache = get_cache()

   # Warm cache on startup
   popular_models = db.query(Model).filter(Model.is_popular == True).all()
   keys_and_values = [(f"model:{m.id}", m.to_dict()) for m in popular_models]
   cache.warm_cache(keys_and_values, ttl=3600)

8. Integration with FastAPI:

   from fastapi import FastAPI, Depends
   from performance.cache_manager import init_cache, get_cache

   app = FastAPI()

   @app.on_event("startup")
   async def startup():
       init_cache(redis_url="redis://redis:6379/0")

   @app.get("/models/{model_id}")
   async def get_model(model_id: str):
       cache = get_cache()

       # Check cache
       cached_model = cache.get(f"model:{model_id}")
       if cached_model:
           return cached_model

       # Query database
       model = db.query(Model).filter(Model.id == model_id).first()

       # Cache result
       if model:
           cache.set(f"model:{model_id}", model.dict(), ttl=600)

       return model

Expected Performance Improvements:
- Cache hit rate: 70-90% for hot data
- Response time: 50-90% reduction for cached requests
- Database load: 60-80% reduction
- P95 latency: <50ms for cached requests
- P99 latency: <100ms for cached requests
"""
