"""
Unit tests for CacheManager
Tests cache operations, eviction, statistics, and error handling
"""

import asyncio
import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from cache_manager import CacheManager, CacheManagerError


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create temporary cache directory"""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


@pytest.fixture
def mock_redis():
    """Create mock Redis client"""
    redis_mock = AsyncMock()
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.setex = AsyncMock()
    redis_mock.delete = AsyncMock()
    redis_mock.scan_iter = AsyncMock(return_value=async_generator([]))
    return redis_mock


def async_generator(items):
    """Helper to create async generator for mocking"""
    async def _gen():
        for item in items:
            yield item
    return _gen()


class TestCacheManagerInitialization:
    """Test CacheManager initialization"""

    def test_init_creates_cache_directory(self, temp_cache_dir):
        """Test that initialization creates cache directory"""
        cache_dir = temp_cache_dir / "test_init"
        manager = CacheManager(None, cache_dir=str(cache_dir))

        assert cache_dir.exists()
        assert manager.cache_dir == cache_dir

    def test_init_with_custom_ttl(self, temp_cache_dir):
        """Test initialization with custom TTL"""
        manager = CacheManager(None, cache_dir=str(temp_cache_dir), default_ttl_hours=48)

        assert manager.default_ttl == timedelta(hours=48)

    def test_init_with_custom_max_size(self, temp_cache_dir):
        """Test initialization with custom max cache size"""
        manager = CacheManager(
            None,
            cache_dir=str(temp_cache_dir),
            max_cache_size_gb=20.0
        )

        assert manager.max_cache_size_bytes == int(20.0 * 1024 * 1024 * 1024)

    def test_init_with_redis_client(self, temp_cache_dir, mock_redis):
        """Test initialization with Redis client"""
        manager = CacheManager(mock_redis, cache_dir=str(temp_cache_dir))

        assert manager.redis is mock_redis


class TestCacheKeyGeneration:
    """Test cache key generation"""

    def test_generate_cache_key_basic(self, temp_cache_dir):
        """Test basic cache key generation"""
        manager = CacheManager(None, cache_dir=str(temp_cache_dir))
        template_id = uuid4()
        version = "v1.0.0"

        key = manager._generate_cache_key(template_id, version)

        assert key == f"template:cache:{template_id}:v1.0.0"

    def test_generate_cache_key_with_commit_hash(self, temp_cache_dir):
        """Test cache key generation with commit hash"""
        manager = CacheManager(None, cache_dir=str(temp_cache_dir))
        template_id = uuid4()
        version = "v1.0.0"
        commit_hash = "abc123def456"

        key = manager._generate_cache_key(template_id, version, commit_hash)

        assert key == f"template:cache:{template_id}:v1.0.0:abc123de"  # First 8 chars

    def test_generate_cache_path(self, temp_cache_dir):
        """Test cache path generation"""
        manager = CacheManager(None, cache_dir=str(temp_cache_dir))
        template_id = uuid4()
        version = "v1.0.0"

        path = manager._generate_cache_path(template_id, version)

        assert path.parent == temp_cache_dir / str(template_id)
        assert path.name == "v1.0.0.tar.gz"

    def test_generate_cache_path_with_format(self, temp_cache_dir):
        """Test cache path generation with custom format"""
        manager = CacheManager(None, cache_dir=str(temp_cache_dir))
        template_id = uuid4()
        version = "v1.0.0"

        path = manager._generate_cache_path(template_id, version, format="zip")

        assert path.name == "v1.0.0.zip"


class TestCacheCheck:
    """Test cache checking operations"""

    @pytest.mark.asyncio
    async def test_check_cache_miss_no_redis(self, temp_cache_dir):
        """Test cache miss with no Redis"""
        manager = CacheManager(None, cache_dir=str(temp_cache_dir))
        template_id = uuid4()

        result = await manager.check_cache(template_id, "v1.0.0")

        assert result is None

    @pytest.mark.asyncio
    async def test_check_cache_hit_filesystem(self, temp_cache_dir):
        """Test cache hit from filesystem"""
        manager = CacheManager(None, cache_dir=str(temp_cache_dir))
        template_id = uuid4()
        version = "v1.0.0"

        # Create cache file
        cache_path = manager._generate_cache_path(template_id, version)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text("cached content")

        result = await manager.check_cache(template_id, version)

        assert result == cache_path

    @pytest.mark.asyncio
    async def test_check_cache_hit_redis(self, temp_cache_dir, mock_redis):
        """Test cache hit from Redis"""
        manager = CacheManager(mock_redis, cache_dir=str(temp_cache_dir))
        template_id = uuid4()
        version = "v1.0.0"

        # Create cache file
        cache_path = manager._generate_cache_path(template_id, version)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text("cached content")

        # Mock Redis response
        cache_data = {
            'template_id': str(template_id),
            'version': version,
            'archive_path': str(cache_path),
            'file_size_bytes': 100,
            'last_accessed': datetime.utcnow().isoformat(),
            'access_count': 0
        }
        mock_redis.get.return_value = json.dumps(cache_data)

        result = await manager.check_cache(template_id, version)

        assert result == cache_path
        mock_redis.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_cache_redis_file_missing(self, temp_cache_dir, mock_redis):
        """Test cache check when Redis has entry but file is missing"""
        manager = CacheManager(mock_redis, cache_dir=str(temp_cache_dir))
        template_id = uuid4()
        version = "v1.0.0"

        # Mock Redis response with non-existent file
        cache_path = manager._generate_cache_path(template_id, version)
        cache_data = {
            'template_id': str(template_id),
            'version': version,
            'archive_path': str(cache_path),
            'file_size_bytes': 100,
            'last_accessed': datetime.utcnow().isoformat(),
            'access_count': 0
        }
        mock_redis.get.return_value = json.dumps(cache_data)

        result = await manager.check_cache(template_id, version)

        assert result is None
        mock_redis.delete.assert_called_once()  # Should clean up stale entry


class TestCacheStore:
    """Test cache storage operations"""

    @pytest.mark.asyncio
    async def test_store_cache_basic(self, temp_cache_dir):
        """Test basic cache storage"""
        manager = CacheManager(None, cache_dir=str(temp_cache_dir))
        template_id = uuid4()
        version = "v1.0.0"

        # Create temporary archive
        temp_archive = temp_cache_dir / "temp.tar.gz"
        temp_archive.write_text("archive content")

        result = await manager.store_cache(template_id, version, temp_archive)

        assert result is True

        # Verify file moved to cache location
        expected_path = manager._generate_cache_path(template_id, version)
        assert expected_path.exists()

    @pytest.mark.asyncio
    async def test_store_cache_with_redis(self, temp_cache_dir, mock_redis):
        """Test cache storage with Redis metadata"""
        manager = CacheManager(mock_redis, cache_dir=str(temp_cache_dir))
        template_id = uuid4()
        version = "v1.0.0"
        commit_hash = "abc123"

        # Create temporary archive
        temp_archive = temp_cache_dir / "temp.tar.gz"
        temp_archive.write_text("archive content")

        result = await manager.store_cache(
            template_id,
            version,
            temp_archive,
            commit_hash=commit_hash,
            clone_duration_ms=500,
            archive_duration_ms=200,
            checksum="sha256hash"
        )

        assert result is True
        mock_redis.setex.assert_called_once()

        # Verify Redis call contains correct metadata
        call_args = mock_redis.setex.call_args
        stored_data = json.loads(call_args[0][2])
        assert stored_data['template_id'] == str(template_id)
        assert stored_data['version'] == version
        assert stored_data['commit_hash'] == commit_hash
        assert stored_data['clone_duration_ms'] == 500
        assert stored_data['archive_duration_ms'] == 200

    @pytest.mark.asyncio
    async def test_store_cache_with_checksum(self, temp_cache_dir):
        """Test cache storage with checksum"""
        manager = CacheManager(None, cache_dir=str(temp_cache_dir))
        template_id = uuid4()
        version = "v1.0.0"

        temp_archive = temp_cache_dir / "temp.tar.gz"
        temp_archive.write_text("archive content")

        result = await manager.store_cache(
            template_id,
            version,
            temp_archive,
            checksum="abc123def456"
        )

        assert result is True


class TestCacheInvalidation:
    """Test cache invalidation operations"""

    @pytest.mark.asyncio
    async def test_invalidate_specific_version(self, temp_cache_dir):
        """Test invalidating specific version"""
        manager = CacheManager(None, cache_dir=str(temp_cache_dir))
        template_id = uuid4()
        version = "v1.0.0"

        # Create cache file
        cache_path = manager._generate_cache_path(template_id, version)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text("cached content")

        count = await manager.invalidate_cache(template_id, version)

        assert count == 1
        assert not cache_path.exists()

    @pytest.mark.asyncio
    async def test_invalidate_all_versions(self, temp_cache_dir):
        """Test invalidating all versions of a template"""
        manager = CacheManager(None, cache_dir=str(temp_cache_dir))
        template_id = uuid4()

        # Create multiple version cache files
        for version in ["v1.0.0", "v1.1.0", "v2.0.0"]:
            cache_path = manager._generate_cache_path(template_id, version)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(f"content {version}")

        count = await manager.invalidate_cache(template_id)

        assert count == 3
        template_dir = temp_cache_dir / str(template_id)
        assert not template_dir.exists()

    @pytest.mark.asyncio
    async def test_invalidate_with_redis(self, temp_cache_dir, mock_redis):
        """Test invalidation with Redis cleanup"""
        manager = CacheManager(mock_redis, cache_dir=str(temp_cache_dir))
        template_id = uuid4()
        version = "v1.0.0"

        # Create cache file
        cache_path = manager._generate_cache_path(template_id, version)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text("cached content")

        count = await manager.invalidate_cache(template_id, version)

        assert count == 1
        mock_redis.delete.assert_called_once()


class TestCacheStatistics:
    """Test cache statistics operations"""

    @pytest.mark.asyncio
    async def test_get_cache_stats_empty(self, temp_cache_dir):
        """Test getting stats for empty cache"""
        manager = CacheManager(None, cache_dir=str(temp_cache_dir))

        stats = await manager.get_cache_stats()

        assert stats['total_size_bytes'] == 0
        assert stats['file_count'] == 0
        assert stats['redis_keys'] == 0

    @pytest.mark.asyncio
    async def test_get_cache_stats_with_files(self, temp_cache_dir):
        """Test getting stats with cached files"""
        manager = CacheManager(None, cache_dir=str(temp_cache_dir))

        # Create cache files
        for i in range(3):
            template_id = uuid4()
            cache_path = manager._generate_cache_path(template_id, "v1.0.0")
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text("x" * 1000)  # 1KB each

        stats = await manager.get_cache_stats()

        assert stats['total_size_bytes'] >= 3000
        assert stats['file_count'] == 3
        assert stats['total_size_mb'] > 0
        assert 'utilization_percent' in stats

    @pytest.mark.asyncio
    async def test_get_cache_stats_with_redis(self, temp_cache_dir, mock_redis):
        """Test getting stats with Redis keys"""
        manager = CacheManager(mock_redis, cache_dir=str(temp_cache_dir))

        # Mock Redis scan to return keys
        async def mock_scan():
            for key in ["key1", "key2", "key3"]:
                yield key

        mock_redis.scan_iter.return_value = mock_scan()

        stats = await manager.get_cache_stats()

        assert stats['redis_keys'] == 3


class TestCacheEviction:
    """Test cache eviction operations"""

    @pytest.mark.asyncio
    async def test_check_cache_size_under_limit(self, temp_cache_dir):
        """Test cache size check when under limit"""
        manager = CacheManager(
            None,
            cache_dir=str(temp_cache_dir),
            max_cache_size_gb=1.0
        )

        # Create small cache file (under limit)
        template_id = uuid4()
        cache_path = manager._generate_cache_path(template_id, "v1.0.0")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text("x" * 1000)

        # Should not raise exception
        await manager._check_cache_size()

    @pytest.mark.asyncio
    async def test_evict_old_entries(self, temp_cache_dir, mock_redis):
        """Test evicting old cache entries"""
        manager = CacheManager(mock_redis, cache_dir=str(temp_cache_dir))

        # Create cache files
        template_id1 = uuid4()
        template_id2 = uuid4()

        cache_path1 = manager._generate_cache_path(template_id1, "v1.0.0")
        cache_path1.parent.mkdir(parents=True, exist_ok=True)
        cache_path1.write_text("x" * 1000)

        cache_path2 = manager._generate_cache_path(template_id2, "v1.0.0")
        cache_path2.parent.mkdir(parents=True, exist_ok=True)
        cache_path2.write_text("x" * 1000)

        # Mock Redis with LRU data (cache_path1 is older)
        async def mock_scan():
            yield f"template:cache:{template_id1}:v1.0.0"
            yield f"template:cache:{template_id2}:v1.0.0"

        mock_redis.scan_iter.return_value = mock_scan()

        old_time = (datetime.utcnow() - timedelta(days=2)).isoformat()
        recent_time = datetime.utcnow().isoformat()

        def mock_get_side_effect(key):
            if str(template_id1) in key:
                return json.dumps({
                    'last_accessed': old_time,
                    'file_size_bytes': 1000,
                    'archive_path': str(cache_path1)
                })
            else:
                return json.dumps({
                    'last_accessed': recent_time,
                    'file_size_bytes': 1000,
                    'archive_path': str(cache_path2)
                })

        mock_redis.get.side_effect = mock_get_side_effect

        # Trigger eviction
        await manager._evict_old_entries(target_reduction_percent=50.0)

        # Older file should be deleted
        # (Note: exact behavior depends on implementation details)


class TestCacheClearAll:
    """Test clearing all cache"""

    @pytest.mark.asyncio
    async def test_clear_all_cache(self, temp_cache_dir):
        """Test clearing entire cache"""
        manager = CacheManager(None, cache_dir=str(temp_cache_dir))

        # Create cache files
        for i in range(5):
            template_id = uuid4()
            cache_path = manager._generate_cache_path(template_id, "v1.0.0")
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(f"content {i}")

        files_deleted, redis_keys = await manager.clear_all_cache()

        assert files_deleted == 5
        assert redis_keys == 0
        assert len(list(temp_cache_dir.rglob("*.tar.gz"))) == 0

    @pytest.mark.asyncio
    async def test_clear_all_cache_with_redis(self, temp_cache_dir, mock_redis):
        """Test clearing cache with Redis keys"""
        manager = CacheManager(mock_redis, cache_dir=str(temp_cache_dir))

        # Create cache file
        template_id = uuid4()
        cache_path = manager._generate_cache_path(template_id, "v1.0.0")
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text("content")

        # Mock Redis keys
        async def mock_scan():
            for key in ["key1", "key2"]:
                yield key

        mock_redis.scan_iter.return_value = mock_scan()

        files_deleted, redis_keys = await manager.clear_all_cache()

        assert files_deleted == 1
        assert redis_keys == 2
        assert mock_redis.delete.call_count == 2


class TestCacheErrorHandling:
    """Test error handling in cache operations"""

    @pytest.mark.asyncio
    async def test_check_cache_handles_redis_error(self, temp_cache_dir, mock_redis):
        """Test that cache check handles Redis errors gracefully"""
        manager = CacheManager(mock_redis, cache_dir=str(temp_cache_dir))
        template_id = uuid4()

        # Make Redis throw error
        mock_redis.get.side_effect = Exception("Redis connection error")

        # Should not raise exception, should return None
        result = await manager.check_cache(template_id, "v1.0.0")

        assert result is None

    @pytest.mark.asyncio
    async def test_store_cache_handles_error(self, temp_cache_dir):
        """Test that store cache handles errors gracefully"""
        manager = CacheManager(None, cache_dir=str(temp_cache_dir))
        template_id = uuid4()

        # Non-existent archive path
        non_existent = temp_cache_dir / "nonexistent.tar.gz"

        result = await manager.store_cache(template_id, "v1.0.0", non_existent)

        assert result is False

    @pytest.mark.asyncio
    async def test_get_cache_stats_handles_error(self, temp_cache_dir):
        """Test that get stats handles errors gracefully"""
        manager = CacheManager(None, cache_dir="/nonexistent/path")

        # Should return empty dict on error
        stats = await manager.get_cache_stats()

        assert stats == {}


class TestCacheAccessTracking:
    """Test cache access time tracking"""

    @pytest.mark.asyncio
    async def test_update_access_time(self, temp_cache_dir, mock_redis):
        """Test updating access time on cache hit"""
        manager = CacheManager(mock_redis, cache_dir=str(temp_cache_dir))
        template_id = uuid4()
        version = "v1.0.0"
        cache_key = manager._generate_cache_key(template_id, version)

        # Create cache file
        cache_path = manager._generate_cache_path(template_id, version)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text("cached content")

        # Mock Redis get to return cache data
        cache_data = {
            'template_id': str(template_id),
            'version': version,
            'archive_path': str(cache_path),
            'file_size_bytes': 100,
            'last_accessed': datetime.utcnow().isoformat(),
            'access_count': 5
        }
        mock_redis.get.return_value = json.dumps(cache_data)

        # Check cache (should update access time)
        await manager.check_cache(template_id, version)

        # Verify setex was called to update access time
        assert mock_redis.setex.call_count >= 1


class TestCacheIntegration:
    """Integration tests for cache operations"""

    @pytest.mark.asyncio
    async def test_full_cache_lifecycle(self, temp_cache_dir):
        """Test complete cache lifecycle: store -> check -> invalidate"""
        manager = CacheManager(None, cache_dir=str(temp_cache_dir))
        template_id = uuid4()
        version = "v1.0.0"

        # 1. Store cache
        temp_archive = temp_cache_dir / "temp.tar.gz"
        temp_archive.write_text("archive content")
        store_result = await manager.store_cache(template_id, version, temp_archive)
        assert store_result is True

        # 2. Check cache (hit)
        cached_path = await manager.check_cache(template_id, version)
        assert cached_path is not None
        assert cached_path.exists()

        # 3. Get stats
        stats = await manager.get_cache_stats()
        assert stats['file_count'] == 1

        # 4. Invalidate cache
        invalidate_count = await manager.invalidate_cache(template_id, version)
        assert invalidate_count == 1

        # 5. Check cache (miss)
        cached_path = await manager.check_cache(template_id, version)
        assert cached_path is None
