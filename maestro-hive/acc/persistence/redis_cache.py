"""
ACC Redis Suppression Cache (MD-2087)

Provides fast read access for active suppressions.
Syncs with PostgreSQL for persistence.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set

logger = logging.getLogger(__name__)

# Try to import redis
try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    logger.warning("redis not installed. Install with: pip install redis")


class RedisSuppressionCache:
    """
    Redis cache for ACC suppressions.

    Provides fast read access with automatic expiry.
    """

    # Redis key prefixes
    KEY_PREFIX = "acc:suppression:"
    INDEX_PREFIX = "acc:index:"
    PATTERN_SET = "acc:patterns"

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        url: Optional[str] = None,
        default_ttl: int = 3600  # 1 hour default TTL
    ):
        """
        Initialize Redis cache.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (optional)
            url: Redis URL (overrides host/port/db)
            default_ttl: Default TTL for cache entries in seconds
        """
        if not HAS_REDIS:
            raise RuntimeError("redis package not installed")

        if url:
            self._client = redis.from_url(url, decode_responses=True)
        else:
            self._client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True
            )

        self.default_ttl = default_ttl

    def ping(self) -> bool:
        """Check Redis connection."""
        try:
            return self._client.ping()
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False

    def cache_suppression(
        self,
        suppression: Dict[str, Any],
        ttl: Optional[int] = None
    ):
        """
        Cache a suppression entry.

        Args:
            suppression: Suppression dictionary
            ttl: Optional TTL in seconds (uses default if not specified)
        """
        key = f"{self.KEY_PREFIX}{suppression['id']}"
        ttl = ttl or self.default_ttl

        # Calculate TTL from expiry if available
        if suppression.get('expires'):
            try:
                expires_at = datetime.fromisoformat(suppression['expires'])
                remaining = (expires_at - datetime.now()).total_seconds()
                if remaining > 0:
                    ttl = min(ttl, int(remaining))
                else:
                    # Already expired, don't cache
                    logger.debug(f"Suppression {suppression['id']} already expired, not caching")
                    return
            except (ValueError, TypeError):
                pass

        try:
            # Store suppression data
            self._client.setex(key, ttl, json.dumps(suppression))

            # Add to pattern index for fast lookup
            self._client.sadd(self.PATTERN_SET, suppression['id'])

            # Index by pattern
            pattern_key = f"{self.INDEX_PREFIX}pattern:{suppression['pattern']}"
            self._client.sadd(pattern_key, suppression['id'])
            self._client.expire(pattern_key, ttl)

            # Index by ADR reference
            if suppression.get('adr_reference'):
                adr_key = f"{self.INDEX_PREFIX}adr:{suppression['adr_reference']}"
                self._client.sadd(adr_key, suppression['id'])
                self._client.expire(adr_key, ttl)

            logger.debug(f"Cached suppression {suppression['id']} with TTL {ttl}s")

        except Exception as e:
            logger.error(f"Failed to cache suppression: {e}")

    def get_suppression(self, suppression_id: str) -> Optional[Dict[str, Any]]:
        """Get suppression from cache."""
        key = f"{self.KEY_PREFIX}{suppression_id}"

        try:
            data = self._client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"Failed to get suppression from cache: {e}")

        return None

    def get_all_cached(self) -> List[Dict[str, Any]]:
        """Get all cached suppressions."""
        try:
            suppression_ids = self._client.smembers(self.PATTERN_SET)
            suppressions = []

            for supp_id in suppression_ids:
                supp = self.get_suppression(supp_id)
                if supp:
                    suppressions.append(supp)

            return suppressions

        except Exception as e:
            logger.error(f"Failed to get cached suppressions: {e}")
            return []

    def invalidate(self, suppression_id: str):
        """Invalidate a cached suppression."""
        key = f"{self.KEY_PREFIX}{suppression_id}"

        try:
            # Get suppression data for index cleanup
            data = self._client.get(key)
            if data:
                suppression = json.loads(data)

                # Remove from indexes
                self._client.srem(self.PATTERN_SET, suppression_id)

                pattern_key = f"{self.INDEX_PREFIX}pattern:{suppression['pattern']}"
                self._client.srem(pattern_key, suppression_id)

                if suppression.get('adr_reference'):
                    adr_key = f"{self.INDEX_PREFIX}adr:{suppression['adr_reference']}"
                    self._client.srem(adr_key, suppression_id)

            # Delete the suppression
            self._client.delete(key)
            logger.debug(f"Invalidated suppression {suppression_id}")

        except Exception as e:
            logger.error(f"Failed to invalidate suppression: {e}")

    def invalidate_all(self):
        """Invalidate all cached suppressions."""
        try:
            # Get all suppression IDs
            suppression_ids = self._client.smembers(self.PATTERN_SET)

            # Delete each suppression
            for supp_id in suppression_ids:
                key = f"{self.KEY_PREFIX}{supp_id}"
                self._client.delete(key)

            # Clear pattern set
            self._client.delete(self.PATTERN_SET)

            # Clear index keys (pattern matching is expensive, skip for now)
            logger.info(f"Invalidated {len(suppression_ids)} cached suppressions")

        except Exception as e:
            logger.error(f"Failed to invalidate all suppressions: {e}")

    def get_by_pattern(self, pattern: str) -> List[Dict[str, Any]]:
        """Get suppressions matching a pattern."""
        pattern_key = f"{self.INDEX_PREFIX}pattern:{pattern}"

        try:
            suppression_ids = self._client.smembers(pattern_key)
            return [
                supp for supp_id in suppression_ids
                if (supp := self.get_suppression(supp_id))
            ]
        except Exception as e:
            logger.error(f"Failed to get suppressions by pattern: {e}")
            return []

    def get_by_adr(self, adr_reference: str) -> List[Dict[str, Any]]:
        """Get suppressions linked to an ADR."""
        adr_key = f"{self.INDEX_PREFIX}adr:{adr_reference}"

        try:
            suppression_ids = self._client.smembers(adr_key)
            return [
                supp for supp_id in suppression_ids
                if (supp := self.get_suppression(supp_id))
            ]
        except Exception as e:
            logger.error(f"Failed to get suppressions by ADR: {e}")
            return []

    def update_use_count(self, suppression_id: str):
        """Increment use count in cache."""
        key = f"{self.KEY_PREFIX}{suppression_id}"

        try:
            data = self._client.get(key)
            if data:
                suppression = json.loads(data)
                suppression['use_count'] = suppression.get('use_count', 0) + 1
                suppression['last_used'] = datetime.now().isoformat()

                # Get remaining TTL
                ttl = self._client.ttl(key)
                if ttl > 0:
                    self._client.setex(key, ttl, json.dumps(suppression))

        except Exception as e:
            logger.error(f"Failed to update use count: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            cached_count = self._client.scard(self.PATTERN_SET)
            info = self._client.info('memory')

            return {
                'cached_suppressions': cached_count,
                'used_memory': info.get('used_memory_human', 'N/A'),
                'connected': True
            }
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {
                'cached_suppressions': 0,
                'used_memory': 'N/A',
                'connected': False,
                'error': str(e)
            }


class SyncedSuppressionStore:
    """
    Synchronized store that combines PostgreSQL and Redis.

    Writes go to PostgreSQL and Redis.
    Reads try Redis first, fall back to PostgreSQL.
    """

    def __init__(
        self,
        postgres_store=None,
        redis_cache=None,
        auto_sync: bool = True
    ):
        """
        Initialize synced store.

        Args:
            postgres_store: PostgresSuppressionStore instance
            redis_cache: RedisSuppressionCache instance
            auto_sync: Automatically sync PostgreSQL to Redis on startup
        """
        self.postgres = postgres_store
        self.redis = redis_cache
        self.auto_sync = auto_sync

        if auto_sync and self.postgres and self.redis:
            self.sync_postgres_to_redis()

    def sync_postgres_to_redis(self):
        """Sync active suppressions from PostgreSQL to Redis."""
        if not self.postgres or not self.redis:
            return

        try:
            suppressions = self.postgres.get_active_suppressions()
            for supp in suppressions:
                self.redis.cache_suppression(supp)

            logger.info(f"Synced {len(suppressions)} suppressions to Redis")

        except Exception as e:
            logger.error(f"Failed to sync PostgreSQL to Redis: {e}")

    def save_suppression(self, suppression: Dict[str, Any], changed_by: str = "system"):
        """Save suppression to both stores."""
        # Write to PostgreSQL
        if self.postgres:
            self.postgres.save_suppression(suppression, changed_by)

        # Cache in Redis
        if self.redis:
            self.redis.cache_suppression(suppression)

    def get_suppression(self, suppression_id: str) -> Optional[Dict[str, Any]]:
        """Get suppression (Redis first, then PostgreSQL)."""
        # Try Redis first
        if self.redis:
            cached = self.redis.get_suppression(suppression_id)
            if cached:
                return cached

        # Fall back to PostgreSQL
        if self.postgres:
            supp = self.postgres.get_suppression(suppression_id)
            if supp and self.redis:
                # Cache for next time
                self.redis.cache_suppression(supp)
            return supp

        return None

    def get_active_suppressions(self) -> List[Dict[str, Any]]:
        """Get all active suppressions."""
        # Try Redis first
        if self.redis:
            cached = self.redis.get_all_cached()
            if cached:
                return cached

        # Fall back to PostgreSQL
        if self.postgres:
            return self.postgres.get_active_suppressions()

        return []

    def delete_suppression(self, suppression_id: str, changed_by: str = "system"):
        """Delete suppression from both stores."""
        if self.postgres:
            self.postgres.delete_suppression(suppression_id, changed_by)

        if self.redis:
            self.redis.invalidate(suppression_id)

    def update_use_count(self, suppression_id: str):
        """Update use count in both stores."""
        if self.redis:
            self.redis.update_use_count(suppression_id)

        if self.postgres:
            self.postgres.update_use_count(suppression_id)


# Convenience function
def get_synced_store(
    postgres_url: Optional[str] = None,
    redis_url: Optional[str] = None
) -> SyncedSuppressionStore:
    """Get configured synced store."""
    import os

    postgres = None
    redis_cache = None

    # Set up PostgreSQL
    if postgres_url or os.environ.get('DATABASE_URL'):
        try:
            from acc.persistence.postgres_store import PostgresSuppressionStore
            postgres = PostgresSuppressionStore(
                connection_string=postgres_url or os.environ.get('DATABASE_URL')
            )
            postgres.connect()
        except Exception as e:
            logger.warning(f"Failed to connect to PostgreSQL: {e}")

    # Set up Redis
    if redis_url or os.environ.get('REDIS_URL'):
        try:
            redis_cache = RedisSuppressionCache(
                url=redis_url or os.environ.get('REDIS_URL')
            )
            if not redis_cache.ping():
                redis_cache = None
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")

    return SyncedSuppressionStore(
        postgres_store=postgres,
        redis_cache=redis_cache
    )
