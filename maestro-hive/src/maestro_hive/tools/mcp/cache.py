"""
Tool Result Cache

EPIC: MD-2565
AC-5: Tool result caching where appropriate

Provides caching for tool results to improve performance.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from collections import OrderedDict
import asyncio
import hashlib
import json
import logging

from .config import CacheConfig

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A cached tool result."""
    key: str
    value: Any
    tool_name: str
    created_at: datetime
    expires_at: datetime
    size_bytes: int
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        return datetime.utcnow() > self.expires_at

    @property
    def ttl_remaining_seconds(self) -> float:
        """Get remaining TTL in seconds."""
        remaining = (self.expires_at - datetime.utcnow()).total_seconds()
        return max(0, remaining)


class ToolResultCache:
    """
    Cache for tool execution results (AC-5).

    Features:
    - LRU eviction when max entries reached
    - TTL-based expiration
    - Per-tool TTL configuration
    - Size limits for cached entries
    - Thread-safe with async support

    Example:
        cache = ToolResultCache(CacheConfig(enabled=True, default_ttl_seconds=300))

        # Check cache
        result = await cache.get("search", {"query": "hello"})
        if result is None:
            result = await tool.execute(query="hello")
            await cache.set("search", {"query": "hello"}, result)
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        self.config = config or CacheConfig()
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "expirations": 0,
        }

    def _generate_key(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """Generate cache key from tool name and arguments."""
        sorted_args = json.dumps(arguments, sort_keys=True, default=str)
        key_input = f"{tool_name}:{sorted_args}"
        return hashlib.sha256(key_input.encode()).hexdigest()

    def _estimate_size(self, value: Any) -> int:
        """Estimate size of a value in bytes."""
        try:
            return len(json.dumps(value, default=str).encode())
        except (TypeError, ValueError):
            return 0

    async def get(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Optional[Any]:
        """
        Get cached result for tool invocation.

        Returns None if not cached or expired.
        """
        if not self.config.enabled:
            return None

        key = self._generate_key(tool_name, arguments)

        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats["misses"] += 1
                return None

            if entry.is_expired:
                del self._cache[key]
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                logger.debug(f"Cache expired for {tool_name}")
                return None

            # Move to end (LRU)
            self._cache.move_to_end(key)
            entry.hit_count += 1
            self._stats["hits"] += 1

            logger.debug(f"Cache hit for {tool_name}")
            return entry.value

    async def set(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        value: Any,
        ttl_seconds: Optional[int] = None,
    ) -> bool:
        """
        Cache a tool result.

        Returns True if cached successfully.
        """
        if not self.config.enabled:
            return False

        size = self._estimate_size(value)
        if size > self.config.max_entry_size_bytes:
            logger.warning(f"Value too large to cache for {tool_name}: {size} bytes")
            return False

        key = self._generate_key(tool_name, arguments)
        ttl = ttl_seconds or self.config.get_ttl(tool_name)

        now = datetime.utcnow()
        entry = CacheEntry(
            key=key,
            value=value,
            tool_name=tool_name,
            created_at=now,
            expires_at=now + timedelta(seconds=ttl),
            size_bytes=size,
        )

        async with self._lock:
            # Evict if at capacity
            while len(self._cache) >= self.config.max_entries:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._stats["evictions"] += 1
                logger.debug(f"Evicted cache entry: {oldest_key[:16]}...")

            self._cache[key] = entry
            logger.debug(f"Cached result for {tool_name} (TTL: {ttl}s)")
            return True

    async def invalidate(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Invalidate cached entries.

        If arguments provided, invalidates specific entry.
        Otherwise, invalidates all entries for the tool.

        Returns number of entries invalidated.
        """
        count = 0

        async with self._lock:
            if arguments is not None:
                key = self._generate_key(tool_name, arguments)
                if key in self._cache:
                    del self._cache[key]
                    count = 1
            else:
                keys_to_delete = [
                    key for key, entry in self._cache.items()
                    if entry.tool_name == tool_name
                ]
                for key in keys_to_delete:
                    del self._cache[key]
                count = len(keys_to_delete)

        if count > 0:
            logger.info(f"Invalidated {count} cache entries for {tool_name}")

        return count

    async def clear(self) -> int:
        """Clear all cached entries. Returns number cleared."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.info(f"Cleared {count} cache entries")
            return count

    async def cleanup_expired(self) -> int:
        """Remove expired entries. Returns number removed."""
        count = 0

        async with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if entry.is_expired
            ]
            for key in expired_keys:
                del self._cache[key]
            count = len(expired_keys)
            self._stats["expirations"] += count

        if count > 0:
            logger.debug(f"Cleaned up {count} expired cache entries")

        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._stats["hits"] + self._stats["misses"]
        hit_rate = self._stats["hits"] / total_requests if total_requests > 0 else 0

        return {
            "enabled": self.config.enabled,
            "size": len(self._cache),
            "max_size": self.config.max_entries,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "hit_rate": hit_rate,
            "evictions": self._stats["evictions"],
            "expirations": self._stats["expirations"],
        }

    def get_entries_info(self) -> list:
        """Get info about cached entries (for debugging)."""
        return [
            {
                "tool_name": entry.tool_name,
                "key": entry.key[:16] + "...",
                "created_at": entry.created_at.isoformat(),
                "ttl_remaining": entry.ttl_remaining_seconds,
                "size_bytes": entry.size_bytes,
                "hit_count": entry.hit_count,
            }
            for entry in self._cache.values()
        ]
