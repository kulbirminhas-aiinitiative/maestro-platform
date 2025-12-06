"""
Content Cache for Embedding Pipeline.

EPIC: MD-2557
AC-5: Incremental updates (don't re-embed unchanged content)
"""

import hashlib
import json
import logging
import os
from abc import ABC, abstractmethod
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from maestro_hive.knowledge.embeddings.exceptions import CacheError

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """Entry in the content cache."""
    content_hash: str
    document_id: str
    embedded_at: datetime
    provider: str
    model: str
    chunk_count: int
    metadata: Dict[str, Any]


class ContentCache(ABC):
    """
    Abstract base class for content caching.

    AC-5: Enables incremental updates by tracking content hashes.
    """

    @abstractmethod
    def get(self, document_id: str) -> Optional[CacheEntry]:
        """
        Get cache entry for a document.

        Args:
            document_id: Document identifier

        Returns:
            CacheEntry if exists, None otherwise
        """
        pass

    @abstractmethod
    def put(self, entry: CacheEntry) -> None:
        """
        Store a cache entry.

        Args:
            entry: Cache entry to store
        """
        pass

    @abstractmethod
    def has_changed(self, document_id: str, content_hash: str) -> bool:
        """
        Check if content has changed since last embedding.

        AC-5: Core method for incremental update detection.

        Args:
            document_id: Document identifier
            content_hash: Current content hash

        Returns:
            True if content changed or not cached, False otherwise
        """
        pass

    @abstractmethod
    def delete(self, document_id: str) -> bool:
        """
        Delete a cache entry.

        Args:
            document_id: Document identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all cache entries."""
        pass

    @abstractmethod
    def size(self) -> int:
        """Return number of cache entries."""
        pass


class InMemoryCache(ContentCache):
    """
    In-memory content cache.

    AC-5: Fast cache for development and testing.
    """

    def __init__(self, max_size: int = 10000, ttl_hours: int = 168):
        """
        Initialize in-memory cache.

        Args:
            max_size: Maximum entries to cache
            ttl_hours: Time-to-live in hours (default 1 week)
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_size = max_size
        self._ttl = timedelta(hours=ttl_hours)
        self._hits = 0
        self._misses = 0

    def get(self, document_id: str) -> Optional[CacheEntry]:
        """Get cache entry."""
        entry = self._cache.get(document_id)
        if entry:
            # Check TTL
            if datetime.utcnow() - entry.embedded_at > self._ttl:
                del self._cache[document_id]
                self._misses += 1
                return None
            # Move to end (most recently accessed)
            self._cache.move_to_end(document_id)
            self._hits += 1
            return entry
        self._misses += 1
        return None

    def put(self, entry: CacheEntry) -> None:
        """Store cache entry."""
        # Evict oldest if at capacity
        while len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)

        self._cache[entry.document_id] = entry

    def has_changed(self, document_id: str, content_hash: str) -> bool:
        """Check if content has changed."""
        entry = self.get(document_id)
        if entry is None:
            return True
        return entry.content_hash != content_hash

    def delete(self, document_id: str) -> bool:
        """Delete cache entry."""
        if document_id in self._cache:
            del self._cache[document_id]
            return True
        return False

    def clear(self) -> None:
        """Clear all entries."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    def size(self) -> int:
        """Return cache size."""
        return len(self._cache)

    def hit_rate(self) -> float:
        """Return cache hit rate."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        return {
            "size": self.size(),
            "max_size": self._max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate(),
        }


class FileCache(ContentCache):
    """
    File-based content cache.

    AC-5: Persistent cache for production use.
    """

    def __init__(
        self,
        cache_dir: str = "data/embeddings/cache",
        ttl_hours: int = 168,
    ):
        """
        Initialize file cache.

        Args:
            cache_dir: Directory for cache files
            ttl_hours: Time-to-live in hours
        """
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._ttl = timedelta(hours=ttl_hours)
        self._index: Dict[str, str] = {}  # document_id -> cache file name
        self._load_index()

    def _index_path(self) -> Path:
        """Get index file path."""
        return self._cache_dir / "index.json"

    def _load_index(self) -> None:
        """Load index from file."""
        index_path = self._index_path()
        if index_path.exists():
            try:
                with open(index_path) as f:
                    self._index = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache index: {e}")
                self._index = {}

    def _save_index(self) -> None:
        """Save index to file."""
        try:
            with open(self._index_path(), "w") as f:
                json.dump(self._index, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache index: {e}")

    def _entry_path(self, document_id: str) -> Path:
        """Get path for document cache entry."""
        # Create safe filename from document_id
        safe_id = hashlib.sha256(document_id.encode()).hexdigest()[:16]
        return self._cache_dir / f"{safe_id}.json"

    def get(self, document_id: str) -> Optional[CacheEntry]:
        """Get cache entry from file."""
        entry_path = self._entry_path(document_id)
        if not entry_path.exists():
            return None

        try:
            with open(entry_path) as f:
                data = json.load(f)

            entry = CacheEntry(
                content_hash=data["content_hash"],
                document_id=data["document_id"],
                embedded_at=datetime.fromisoformat(data["embedded_at"]),
                provider=data["provider"],
                model=data["model"],
                chunk_count=data["chunk_count"],
                metadata=data.get("metadata", {}),
            )

            # Check TTL
            if datetime.utcnow() - entry.embedded_at > self._ttl:
                self.delete(document_id)
                return None

            return entry

        except Exception as e:
            logger.warning(f"Failed to read cache entry for {document_id}: {e}")
            return None

    def put(self, entry: CacheEntry) -> None:
        """Store cache entry to file."""
        entry_path = self._entry_path(entry.document_id)

        try:
            data = {
                "content_hash": entry.content_hash,
                "document_id": entry.document_id,
                "embedded_at": entry.embedded_at.isoformat(),
                "provider": entry.provider,
                "model": entry.model,
                "chunk_count": entry.chunk_count,
                "metadata": entry.metadata,
            }

            with open(entry_path, "w") as f:
                json.dump(data, f, indent=2)

            self._index[entry.document_id] = str(entry_path)
            self._save_index()

        except Exception as e:
            raise CacheError(f"Failed to save cache entry: {e}")

    def has_changed(self, document_id: str, content_hash: str) -> bool:
        """Check if content has changed."""
        entry = self.get(document_id)
        if entry is None:
            return True
        return entry.content_hash != content_hash

    def delete(self, document_id: str) -> bool:
        """Delete cache entry."""
        entry_path = self._entry_path(document_id)
        if entry_path.exists():
            try:
                entry_path.unlink()
                if document_id in self._index:
                    del self._index[document_id]
                    self._save_index()
                return True
            except Exception as e:
                logger.warning(f"Failed to delete cache entry: {e}")
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        try:
            for cache_file in self._cache_dir.glob("*.json"):
                if cache_file.name != "index.json":
                    cache_file.unlink()
            self._index = {}
            self._save_index()
        except Exception as e:
            raise CacheError(f"Failed to clear cache: {e}")

    def size(self) -> int:
        """Return number of cache entries."""
        return len(list(self._cache_dir.glob("*.json"))) - 1  # Exclude index

    def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count of removed entries."""
        removed = 0
        now = datetime.utcnow()

        for cache_file in self._cache_dir.glob("*.json"):
            if cache_file.name == "index.json":
                continue

            try:
                with open(cache_file) as f:
                    data = json.load(f)
                embedded_at = datetime.fromisoformat(data["embedded_at"])

                if now - embedded_at > self._ttl:
                    cache_file.unlink()
                    removed += 1
            except Exception:
                pass

        # Rebuild index
        if removed > 0:
            self._index = {}
            for cache_file in self._cache_dir.glob("*.json"):
                if cache_file.name != "index.json":
                    try:
                        with open(cache_file) as f:
                            data = json.load(f)
                        self._index[data["document_id"]] = str(cache_file)
                    except Exception:
                        pass
            self._save_index()

        return removed
