"""
Cache Manager Service
Manages template archive caching using Redis and filesystem storage
"""

import asyncio
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
from uuid import UUID

import redis.asyncio as redis
import structlog

logger = structlog.get_logger(__name__)


class CacheManagerError(Exception):
    """Base exception for cache manager errors"""
    pass


class CacheManager:
    """
    Manages template archive caching

    Features:
    - Redis-based cache key management
    - Filesystem storage for archives
    - Cache hit/miss tracking
    - Automatic cache expiration
    - Cache statistics
    """

    def __init__(
        self,
        redis_client: Optional[redis.Redis],
        cache_dir: str = "/storage/cache",
        default_ttl_hours: int = 24,
        max_cache_size_gb: float = 10.0
    ):
        """
        Initialize Cache Manager

        Args:
            redis_client: Redis client for cache metadata
            cache_dir: Directory for storing cached archives
            default_ttl_hours: Default cache TTL in hours
            max_cache_size_gb: Maximum cache size in GB
        """
        self.redis = redis_client
        self.cache_dir = Path(cache_dir)
        self.default_ttl = timedelta(hours=default_ttl_hours)
        self.max_cache_size_bytes = int(max_cache_size_gb * 1024 * 1024 * 1024)

        # Ensure cache directory exists
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            "cache_manager_initialized",
            cache_dir=str(self.cache_dir),
            ttl_hours=default_ttl_hours,
            max_size_gb=max_cache_size_gb
        )

    def _generate_cache_key(
        self,
        template_id: UUID,
        version: str,
        commit_hash: Optional[str] = None
    ) -> str:
        """Generate Redis cache key"""
        if commit_hash:
            return f"template:cache:{template_id}:{version}:{commit_hash[:8]}"
        return f"template:cache:{template_id}:{version}"

    def _generate_cache_path(
        self,
        template_id: UUID,
        version: str,
        format: str = "tar.gz"
    ) -> Path:
        """Generate filesystem path for cached archive"""
        # Organize by template_id subdirectory
        template_dir = self.cache_dir / str(template_id)
        template_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{version}.{format}"
        return template_dir / filename

    async def check_cache(
        self,
        template_id: UUID,
        version: str,
        commit_hash: Optional[str] = None
    ) -> Optional[Path]:
        """
        Check if template is cached

        Args:
            template_id: Template UUID
            version: Version string
            commit_hash: Git commit hash (optional)

        Returns:
            Path to cached archive if exists, None otherwise
        """
        cache_key = self._generate_cache_key(template_id, version, commit_hash)

        try:
            if self.redis:
                # Check Redis for cache metadata
                cache_data_str = await self.redis.get(cache_key)

                if cache_data_str:
                    cache_data = json.loads(cache_data_str)
                    archive_path = Path(cache_data['archive_path'])

                    # Verify file still exists
                    if archive_path.exists():
                        # Update access time
                        await self._update_access_time(cache_key)

                        logger.info(
                            "cache_hit",
                            template_id=str(template_id),
                            version=version,
                            cache_key=cache_key
                        )
                        return archive_path

                    else:
                        # File missing, clear cache entry
                        await self.redis.delete(cache_key)
                        logger.warning(
                            "cache_file_missing",
                            template_id=str(template_id),
                            archive_path=str(archive_path)
                        )

            # Fallback: check filesystem directly
            for format in ['tar.gz', 'zip']:
                cache_path = self._generate_cache_path(template_id, version, format)
                if cache_path.exists():
                    logger.info(
                        "cache_hit_filesystem",
                        template_id=str(template_id),
                        version=version
                    )
                    return cache_path

            logger.debug(
                "cache_miss",
                template_id=str(template_id),
                version=version
            )
            return None

        except Exception as e:
            logger.error(
                "cache_check_error",
                template_id=str(template_id),
                error=str(e)
            )
            return None

    async def store_cache(
        self,
        template_id: UUID,
        version: str,
        archive_path: Path,
        commit_hash: Optional[str] = None,
        clone_duration_ms: Optional[int] = None,
        archive_duration_ms: Optional[int] = None,
        checksum: Optional[str] = None
    ) -> bool:
        """
        Store template in cache

        Args:
            template_id: Template UUID
            version: Version string
            archive_path: Path to archive file
            commit_hash: Git commit hash
            clone_duration_ms: Time to clone repository
            archive_duration_ms: Time to create archive
            checksum: SHA256 checksum of archive

        Returns:
            True if successfully cached, False otherwise
        """
        cache_key = self._generate_cache_key(template_id, version, commit_hash)
        cache_storage_path = self._generate_cache_path(
            template_id,
            version,
            archive_path.suffix.lstrip('.')
        )

        try:
            # Move/copy archive to cache directory
            if archive_path != cache_storage_path:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    archive_path.rename,
                    cache_storage_path
                )

            file_size = cache_storage_path.stat().st_size

            # Store metadata in Redis
            if self.redis:
                cache_data = {
                    'template_id': str(template_id),
                    'version': version,
                    'commit_hash': commit_hash,
                    'archive_path': str(cache_storage_path),
                    'file_size_bytes': file_size,
                    'checksum': checksum,
                    'cached_at': datetime.utcnow().isoformat(),
                    'last_accessed': datetime.utcnow().isoformat(),
                    'access_count': 0,
                    'clone_duration_ms': clone_duration_ms,
                    'archive_duration_ms': archive_duration_ms
                }

                await self.redis.setex(
                    cache_key,
                    int(self.default_ttl.total_seconds()),
                    json.dumps(cache_data)
                )

            logger.info(
                "cache_stored",
                template_id=str(template_id),
                version=version,
                cache_key=cache_key,
                size_bytes=file_size
            )

            # Check if we need to evict old entries
            await self._check_cache_size()

            return True

        except Exception as e:
            logger.error(
                "cache_store_error",
                template_id=str(template_id),
                error=str(e)
            )
            return False

    async def _update_access_time(self, cache_key: str):
        """Update access time and increment access count"""
        if not self.redis:
            return

        try:
            cache_data_str = await self.redis.get(cache_key)
            if cache_data_str:
                cache_data = json.loads(cache_data_str)
                cache_data['last_accessed'] = datetime.utcnow().isoformat()
                cache_data['access_count'] = cache_data.get('access_count', 0) + 1

                # Update with extended TTL
                await self.redis.setex(
                    cache_key,
                    int(self.default_ttl.total_seconds()),
                    json.dumps(cache_data)
                )

        except Exception as e:
            logger.warning("access_time_update_failed", cache_key=cache_key, error=str(e))

    async def invalidate_cache(
        self,
        template_id: UUID,
        version: Optional[str] = None
    ) -> int:
        """
        Invalidate cache entries for a template

        Args:
            template_id: Template UUID
            version: Specific version (if None, invalidate all versions)

        Returns:
            Number of cache entries invalidated
        """
        count = 0

        try:
            if version:
                # Invalidate specific version
                cache_key = self._generate_cache_key(template_id, version)
                if self.redis:
                    await self.redis.delete(cache_key)

                cache_path = self._generate_cache_path(template_id, version)
                if cache_path.exists():
                    cache_path.unlink()
                    count += 1

            else:
                # Invalidate all versions for this template
                template_dir = self.cache_dir / str(template_id)

                if template_dir.exists():
                    for cache_file in template_dir.glob("*"):
                        cache_file.unlink()
                        count += 1
                    template_dir.rmdir()

                # Clear Redis entries
                if self.redis:
                    pattern = f"template:cache:{template_id}:*"
                    async for key in self.redis.scan_iter(match=pattern):
                        await self.redis.delete(key)

            logger.info(
                "cache_invalidated",
                template_id=str(template_id),
                version=version,
                count=count
            )

            return count

        except Exception as e:
            logger.error(
                "cache_invalidation_error",
                template_id=str(template_id),
                error=str(e)
            )
            return count

    async def get_cache_stats(self) -> dict:
        """
        Get cache statistics

        Returns:
            Dict with cache statistics
        """
        try:
            # Calculate total cache size
            total_size = 0
            file_count = 0

            for cache_file in self.cache_dir.rglob("*"):
                if cache_file.is_file():
                    total_size += cache_file.stat().st_size
                    file_count += 1

            # Get Redis stats if available
            redis_keys = 0
            if self.redis:
                async for _ in self.redis.scan_iter(match="template:cache:*"):
                    redis_keys += 1

            stats = {
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'total_size_gb': round(total_size / (1024 * 1024 * 1024), 2),
                'file_count': file_count,
                'redis_keys': redis_keys,
                'cache_dir': str(self.cache_dir),
                'max_size_gb': self.max_cache_size_bytes / (1024 * 1024 * 1024),
                'utilization_percent': round((total_size / self.max_cache_size_bytes) * 100, 2)
            }

            return stats

        except Exception as e:
            logger.error("cache_stats_error", error=str(e))
            return {}

    async def _check_cache_size(self):
        """Check cache size and evict old entries if needed"""
        try:
            stats = await self.get_cache_stats()
            total_size = stats.get('total_size_bytes', 0)

            if total_size > self.max_cache_size_bytes:
                logger.warning(
                    "cache_size_exceeded",
                    total_size_gb=stats.get('total_size_gb'),
                    max_size_gb=self.max_cache_size_bytes / (1024 * 1024 * 1024)
                )

                await self._evict_old_entries()

        except Exception as e:
            logger.error("cache_size_check_error", error=str(e))

    async def _evict_old_entries(self, target_reduction_percent: float = 20.0):
        """
        Evict old cache entries based on LRU strategy

        Args:
            target_reduction_percent: Percentage of cache to free up
        """
        try:
            # Get all cache entries with access times from Redis
            entries = []

            if self.redis:
                async for key in self.redis.scan_iter(match="template:cache:*"):
                    data_str = await self.redis.get(key)
                    if data_str:
                        data = json.loads(data_str)
                        entries.append({
                            'key': key,
                            'last_accessed': datetime.fromisoformat(data['last_accessed']),
                            'file_size': data['file_size_bytes'],
                            'archive_path': data['archive_path']
                        })

            # Sort by last accessed (oldest first)
            entries.sort(key=lambda x: x['last_accessed'])

            # Calculate target bytes to free
            stats = await self.get_cache_stats()
            target_bytes = int(stats['total_size_bytes'] * (target_reduction_percent / 100))

            freed_bytes = 0
            evicted_count = 0

            for entry in entries:
                if freed_bytes >= target_bytes:
                    break

                # Delete file
                archive_path = Path(entry['archive_path'])
                if archive_path.exists():
                    archive_path.unlink()
                    freed_bytes += entry['file_size']

                # Delete Redis key
                if self.redis:
                    await self.redis.delete(entry['key'])

                evicted_count += 1

            logger.info(
                "cache_eviction_complete",
                evicted_count=evicted_count,
                freed_mb=round(freed_bytes / (1024 * 1024), 2)
            )

        except Exception as e:
            logger.error("cache_eviction_error", error=str(e))

    async def clear_all_cache(self) -> Tuple[int, int]:
        """
        Clear all cache entries

        Returns:
            Tuple of (files_deleted, redis_keys_deleted)
        """
        files_deleted = 0
        redis_keys = 0

        try:
            # Delete all files
            for cache_file in self.cache_dir.rglob("*"):
                if cache_file.is_file():
                    cache_file.unlink()
                    files_deleted += 1

            # Remove empty directories
            for cache_dir in sorted(self.cache_dir.rglob("*"), reverse=True):
                if cache_dir.is_dir() and not any(cache_dir.iterdir()):
                    cache_dir.rmdir()

            # Clear Redis
            if self.redis:
                async for key in self.redis.scan_iter(match="template:cache:*"):
                    await self.redis.delete(key)
                    redis_keys += 1

            logger.info(
                "cache_cleared",
                files_deleted=files_deleted,
                redis_keys=redis_keys
            )

            return files_deleted, redis_keys

        except Exception as e:
            logger.error("cache_clear_error", error=str(e))
            return files_deleted, redis_keys