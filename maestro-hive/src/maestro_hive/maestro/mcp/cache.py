"""
MCP Result Cache

Implements AC-5: Tool result caching where appropriate.

Provides caching layer for MCP tool results to reduce redundant
executions and improve performance.

Epic: MD-2565
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from enum import Enum
import asyncio
import hashlib
import json
import logging

logger = logging.getLogger(__name__)


class CacheStrategy(str, Enum):
    """Cache eviction strategies"""
    LRU = "lru"       # Least Recently Used
    LFU = "lfu"       # Least Frequently Used
    TTL = "ttl"       # Time To Live only
    FIFO = "fifo"     # First In First Out


@dataclass
class CacheConfig:
    """
    Configuration for MCP result cache.

    AC-5 Implementation: Configurable caching parameters.
    """
    max_entries: int = 1000
    default_ttl_seconds: int = 300  # 5 minutes
    strategy: CacheStrategy = CacheStrategy.LRU
    enabled: bool = True
    persist_to_disk: bool = False
    cache_dir: str = "/tmp/mcp_cache"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "max_entries": self.max_entries,
            "default_ttl_seconds": self.default_ttl_seconds,
            "strategy": self.strategy.value,
            "enabled": self.enabled,
            "persist_to_disk": self.persist_to_disk,
            "cache_dir": self.cache_dir
        }


@dataclass
class CacheEntry:
    """A single cache entry"""
    key: str
    value: Any
    tool_name: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self) -> bool:
        """Check if entry has expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def touch(self) -> None:
        """Update access statistics"""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "key": self.key,
            "value": self.value,
            "tool_name": self.tool_name,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class CacheStats:
    """Cache statistics"""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_entries: int = 0
    total_size_bytes: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "total_entries": self.total_entries,
            "total_size_bytes": self.total_size_bytes,
            "hit_rate": self.hit_rate
        }


class MCPResultCache:
    """
    Cache for MCP tool execution results.

    AC-5 Implementation: Caches tool results to avoid redundant executions.

    Features:
    - Multiple eviction strategies (LRU, LFU, TTL, FIFO)
    - Per-tool TTL configuration
    - Cache statistics tracking
    - Thread-safe operations
    """

    def __init__(self, config: Optional[CacheConfig] = None):
        """
        Initialize cache.

        Args:
            config: Cache configuration (uses defaults if None)
        """
        self.config = config or CacheConfig()
        self._cache: Dict[str, CacheEntry] = {}
        self._stats = CacheStats()
        self._lock = asyncio.Lock()
        self._tool_ttls: Dict[str, int] = {}

    def generate_key(
        self,
        tool_name: str,
        inputs: Dict[str, Any]
    ) -> str:
        """
        Generate cache key for tool inputs.

        Args:
            tool_name: Name of the tool
            inputs: Tool inputs

        Returns:
            Cache key string
        """
        content = json.dumps({
            "tool": tool_name,
            "inputs": inputs
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    async def get(
        self,
        key: str
    ) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if not self.config.enabled:
            return None

        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats.misses += 1
                return None

            if entry.is_expired():
                del self._cache[key]
                self._stats.misses += 1
                self._stats.evictions += 1
                self._stats.total_entries = len(self._cache)
                return None

            entry.touch()
            self._stats.hits += 1
            logger.debug(f"Cache hit for key: {key[:8]}...")
            return entry.value

    async def set(
        self,
        key: str,
        value: Any,
        tool_name: str,
        ttl_seconds: Optional[int] = None,
        **metadata
    ) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            tool_name: Name of the tool
            ttl_seconds: Optional TTL override
            **metadata: Additional metadata
        """
        if not self.config.enabled:
            return

        async with self._lock:
            # Determine TTL
            if ttl_seconds is None:
                ttl_seconds = self._tool_ttls.get(
                    tool_name,
                    self.config.default_ttl_seconds
                )

            # Calculate expiration
            expires_at = None
            if ttl_seconds > 0:
                expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

            # Create entry
            entry = CacheEntry(
                key=key,
                value=value,
                tool_name=tool_name,
                expires_at=expires_at,
                metadata=metadata
            )

            # Evict if at capacity
            if len(self._cache) >= self.config.max_entries and key not in self._cache:
                await self._evict_one()

            self._cache[key] = entry
            self._stats.total_entries = len(self._cache)
            logger.debug(f"Cached result for key: {key[:8]}...")

    async def _evict_one(self) -> None:
        """Evict one entry based on strategy"""
        if not self._cache:
            return

        strategy = self.config.strategy

        if strategy == CacheStrategy.LRU:
            # Evict least recently accessed
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].last_accessed
            )
        elif strategy == CacheStrategy.LFU:
            # Evict least frequently accessed
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].access_count
            )
        elif strategy == CacheStrategy.FIFO:
            # Evict oldest created
            oldest_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].created_at
            )
        else:  # TTL - evict expired first, then oldest
            expired = [k for k, v in self._cache.items() if v.is_expired()]
            if expired:
                oldest_key = expired[0]
            else:
                oldest_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k].created_at
                )

        del self._cache[oldest_key]
        self._stats.evictions += 1
        logger.debug(f"Evicted cache entry: {oldest_key[:8]}...")

    async def invalidate(self, key: str) -> bool:
        """
        Invalidate a specific cache entry.

        Args:
            key: Cache key to invalidate

        Returns:
            True if entry was found and removed
        """
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                self._stats.total_entries = len(self._cache)
                return True
            return False

    async def invalidate_tool(self, tool_name: str) -> int:
        """
        Invalidate all entries for a specific tool.

        Args:
            tool_name: Tool name to invalidate

        Returns:
            Number of entries invalidated
        """
        async with self._lock:
            keys_to_remove = [
                k for k, v in self._cache.items()
                if v.tool_name == tool_name
            ]
            for key in keys_to_remove:
                del self._cache[key]
            self._stats.total_entries = len(self._cache)
            return len(keys_to_remove)

    async def clear(self) -> None:
        """Clear all cache entries"""
        async with self._lock:
            self._cache.clear()
            self._stats.total_entries = 0
            logger.info("Cache cleared")

    async def cleanup_expired(self) -> int:
        """
        Remove all expired entries.

        Returns:
            Number of entries removed
        """
        async with self._lock:
            expired_keys = [
                k for k, v in self._cache.items()
                if v.is_expired()
            ]
            for key in expired_keys:
                del self._cache[key]
            self._stats.evictions += len(expired_keys)
            self._stats.total_entries = len(self._cache)
            return len(expired_keys)

    def set_tool_ttl(self, tool_name: str, ttl_seconds: int) -> None:
        """
        Set custom TTL for a specific tool.

        Args:
            tool_name: Tool name
            ttl_seconds: TTL in seconds (0 for no expiration)
        """
        self._tool_ttls[tool_name] = ttl_seconds

    @property
    def stats(self) -> CacheStats:
        """Get cache statistics"""
        return self._stats

    @property
    def size(self) -> int:
        """Get current cache size"""
        return len(self._cache)

    def get_entries_by_tool(self, tool_name: str) -> List[CacheEntry]:
        """Get all entries for a specific tool"""
        return [
            entry for entry in self._cache.values()
            if entry.tool_name == tool_name
        ]


def create_cache(
    max_entries: int = 1000,
    ttl_seconds: int = 300,
    strategy: str = "lru"
) -> MCPResultCache:
    """
    Factory function to create cache.

    Args:
        max_entries: Maximum cache entries
        ttl_seconds: Default TTL
        strategy: Cache strategy name

    Returns:
        Configured MCPResultCache
    """
    config = CacheConfig(
        max_entries=max_entries,
        default_ttl_seconds=ttl_seconds,
        strategy=CacheStrategy(strategy)
    )
    return MCPResultCache(config)
