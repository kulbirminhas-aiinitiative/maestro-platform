"""
Redis Cache Implementation

Proper Redis client without custom SSL handling or infrastructure code.
"""

import json
import logging
from typing import Any, Optional, List
from urllib.parse import urlparse

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import RedisError

from .interface import CacheInterface

logger = logging.getLogger(__name__)


class RedisCache(CacheInterface):
    """
    Redis cache implementation using standard redis-py library.

    Configuration via URL:
        redis://[:password@]host:port[/db]
        rediss://[:password@]host:port[/db]  (SSL)

    Examples:
        redis://localhost:6379/0
        redis://:mypassword@redis-server:6379/1
        rediss://redis.example.com:6380/0  (with SSL)
    """

    def __init__(
        self,
        url: str,
        default_ttl: Optional[int] = 3600,
        key_prefix: str = "",
        decode_responses: bool = True,
    ):
        """
        Initialize Redis cache

        Args:
            url: Redis connection URL
            default_ttl: Default TTL in seconds (None = no expiration)
            key_prefix: Prefix for all keys (useful for namespacing)
            decode_responses: Decode bytes to strings automatically
        """
        self.url = url
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self.decode_responses = decode_responses

        # Parse URL to check for SSL
        parsed = urlparse(url)
        self.use_ssl = parsed.scheme == "rediss"

        # Create client using standard from_url (handles SSL automatically)
        self._client: Optional[Redis] = None
        self._initialized = False

    async def _ensure_connected(self):
        """Lazy connection initialization"""
        if not self._initialized:
            try:
                self._client = await aioredis.from_url(
                    self.url,
                    decode_responses=self.decode_responses,
                    encoding="utf-8",
                )
                self._initialized = True
                logger.info(f"Redis cache connected (SSL={self.use_ssl})")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise

    def _make_key(self, key: str) -> str:
        """Add prefix to key"""
        return f"{self.key_prefix}{key}" if self.key_prefix else key

    async def get(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        await self._ensure_connected()
        try:
            value = await self._client.get(self._make_key(key))
            if value is None:
                return None

            # Try to deserialize JSON
            try:
                return json.loads(value) if isinstance(value, str) else value
            except (json.JSONDecodeError, TypeError):
                return value

        except RedisError as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in Redis"""
        await self._ensure_connected()
        try:
            # Serialize complex types to JSON
            if not isinstance(value, (str, bytes, int, float)):
                value = json.dumps(value)

            ttl = ttl if ttl is not None else self.default_ttl

            if ttl:
                await self._client.setex(self._make_key(key), ttl, value)
            else:
                await self._client.set(self._make_key(key), value)

            return True

        except RedisError as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from Redis"""
        await self._ensure_connected()
        try:
            result = await self._client.delete(self._make_key(key))
            return result > 0
        except RedisError as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        await self._ensure_connected()
        try:
            return await self._client.exists(self._make_key(key)) > 0
        except RedisError as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False

    async def clear(self, pattern: Optional[str] = None) -> int:
        """Clear cache entries matching pattern"""
        await self._ensure_connected()
        try:
            if pattern:
                # Use SCAN to avoid blocking
                count = 0
                pattern = self._make_key(pattern)
                async for key in self._client.scan_iter(match=pattern):
                    await self._client.delete(key)
                    count += 1
                return count
            else:
                # Clear entire database (use with caution!)
                await self._client.flushdb()
                return -1  # Unknown count

        except RedisError as e:
            logger.error(f"Redis CLEAR error: {e}")
            return 0

    async def get_many(self, keys: List[str]) -> dict:
        """Get multiple values"""
        await self._ensure_connected()
        try:
            redis_keys = [self._make_key(k) for k in keys]
            values = await self._client.mget(redis_keys)

            result = {}
            for key, value in zip(keys, values):
                if value is not None:
                    try:
                        result[key] = json.loads(value) if isinstance(value, str) else value
                    except (json.JSONDecodeError, TypeError):
                        result[key] = value

            return result

        except RedisError as e:
            logger.error(f"Redis MGET error: {e}")
            return {}

    async def set_many(self, mapping: dict, ttl: Optional[int] = None) -> bool:
        """Set multiple values"""
        await self._ensure_connected()
        try:
            # Prepare data
            redis_mapping = {}
            for key, value in mapping.items():
                if not isinstance(value, (str, bytes, int, float)):
                    value = json.dumps(value)
                redis_mapping[self._make_key(key)] = value

            # Use pipeline for atomicity
            pipe = self._client.pipeline()
            pipe.mset(redis_mapping)

            # Set TTL for each key if specified
            if ttl:
                for key in redis_mapping.keys():
                    pipe.expire(key, ttl)

            await pipe.execute()
            return True

        except RedisError as e:
            logger.error(f"Redis MSET error: {e}")
            return False

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter"""
        await self._ensure_connected()
        try:
            return await self._client.incrby(self._make_key(key), amount)
        except RedisError as e:
            logger.error(f"Redis INCR error for key {key}: {e}")
            return 0

    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrement counter"""
        await self._ensure_connected()
        try:
            return await self._client.decrby(self._make_key(key), amount)
        except RedisError as e:
            logger.error(f"Redis DECR error for key {key}: {e}")
            return 0

    async def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL"""
        await self._ensure_connected()
        try:
            ttl = await self._client.ttl(self._make_key(key))
            return ttl if ttl > 0 else None
        except RedisError as e:
            logger.error(f"Redis TTL error for key {key}: {e}")
            return None

    async def expire(self, key: str, ttl: int) -> bool:
        """Set expiration"""
        await self._ensure_connected()
        try:
            return await self._client.expire(self._make_key(key), ttl)
        except RedisError as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False

    async def health_check(self) -> bool:
        """Check Redis connection"""
        try:
            await self._ensure_connected()
            await self._client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False

    async def close(self):
        """Close Redis connection"""
        if self._client:
            await self._client.close()
            self._initialized = False
            logger.info("Redis cache connection closed")
