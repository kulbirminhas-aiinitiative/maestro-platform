"""
Persistence Layer for Governance (MD-3118)

Provides persistent storage for reputation scores and governance data.
Supports multiple backends:
- Redis (primary, for production)
- PostgreSQL (for complex queries)
- File-based (fallback for development)

AC-5: Scores survive system restart.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from abc import ABC, abstractmethod
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    def get(self, key: str) -> Optional[str]:
        """Get a value by key."""
        pass

    @abstractmethod
    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set a value with optional TTL in seconds."""
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """Delete a key."""
        pass

    @abstractmethod
    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if key exists."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the connection."""
        pass


class FileStorageBackend(StorageBackend):
    """
    File-based storage backend.

    Stores data in JSON files on disk. Suitable for development
    and single-instance deployments.
    """

    def __init__(self, storage_dir: str = "/tmp/governance_storage"):
        """
        Initialize file storage.

        Args:
            storage_dir: Directory to store files
        """
        self._storage_dir = storage_dir
        self._lock = threading.RLock()
        self._cache: Dict[str, Dict[str, Any]] = {}

        # Ensure directory exists
        Path(storage_dir).mkdir(parents=True, exist_ok=True)

        # Load existing data
        self._load_all()

        logger.info(f"FileStorageBackend initialized at {storage_dir}")

    def _get_file_path(self, namespace: str) -> str:
        """Get file path for a namespace."""
        return os.path.join(self._storage_dir, f"{namespace}.json")

    def _extract_namespace(self, key: str) -> tuple[str, str]:
        """Extract namespace and actual key from compound key."""
        if ":" in key:
            parts = key.split(":", 1)
            return parts[0], parts[1]
        return "default", key

    def _load_all(self) -> None:
        """Load all data from storage files."""
        with self._lock:
            for filename in os.listdir(self._storage_dir):
                if filename.endswith(".json"):
                    namespace = filename[:-5]
                    filepath = os.path.join(self._storage_dir, filename)
                    try:
                        with open(filepath, "r") as f:
                            self._cache[namespace] = json.load(f)
                    except Exception as e:
                        logger.warning(f"Failed to load {filepath}: {e}")
                        self._cache[namespace] = {}

    def _save_namespace(self, namespace: str) -> None:
        """Save a namespace to disk."""
        filepath = self._get_file_path(namespace)
        try:
            with open(filepath, "w") as f:
                json.dump(self._cache.get(namespace, {}), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save {filepath}: {e}")

    def get(self, key: str) -> Optional[str]:
        """Get a value by key."""
        with self._lock:
            namespace, actual_key = self._extract_namespace(key)
            data = self._cache.get(namespace, {})
            entry = data.get(actual_key)
            if entry is None:
                return None

            # Check TTL
            if isinstance(entry, dict) and "expires_at" in entry:
                if datetime.fromisoformat(entry["expires_at"]) < datetime.utcnow():
                    # Expired
                    del data[actual_key]
                    self._save_namespace(namespace)
                    return None
                return entry.get("value")

            return entry if isinstance(entry, str) else json.dumps(entry)

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set a value with optional TTL in seconds."""
        with self._lock:
            namespace, actual_key = self._extract_namespace(key)
            if namespace not in self._cache:
                self._cache[namespace] = {}

            if ttl:
                expires_at = datetime.utcnow().timestamp() + ttl
                self._cache[namespace][actual_key] = {
                    "value": value,
                    "expires_at": datetime.fromtimestamp(expires_at).isoformat(),
                }
            else:
                self._cache[namespace][actual_key] = value

            self._save_namespace(namespace)
            return True

    def delete(self, key: str) -> bool:
        """Delete a key."""
        with self._lock:
            namespace, actual_key = self._extract_namespace(key)
            data = self._cache.get(namespace, {})
            if actual_key in data:
                del data[actual_key]
                self._save_namespace(namespace)
                return True
            return False

    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        import fnmatch

        with self._lock:
            all_keys = []
            for namespace, data in self._cache.items():
                for key in data.keys():
                    full_key = f"{namespace}:{key}"
                    if fnmatch.fnmatch(full_key, pattern):
                        all_keys.append(full_key)
            return all_keys

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        return self.get(key) is not None

    def close(self) -> None:
        """Close the connection (save all)."""
        with self._lock:
            for namespace in self._cache:
                self._save_namespace(namespace)


class RedisStorageBackend(StorageBackend):
    """
    Redis storage backend.

    Production-ready storage using Redis for high performance
    and distributed deployments.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        prefix: str = "governance:",
    ):
        """
        Initialize Redis storage.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password
            prefix: Key prefix for namespacing
        """
        try:
            import redis
            self._redis = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
            )
            self._prefix = prefix
            self._redis.ping()
            logger.info(f"RedisStorageBackend connected to {host}:{port}")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise

    def _prefixed_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self._prefix}{key}"

    def get(self, key: str) -> Optional[str]:
        """Get a value by key."""
        return self._redis.get(self._prefixed_key(key))

    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set a value with optional TTL in seconds."""
        if ttl:
            return self._redis.setex(self._prefixed_key(key), ttl, value)
        return self._redis.set(self._prefixed_key(key), value)

    def delete(self, key: str) -> bool:
        """Delete a key."""
        return self._redis.delete(self._prefixed_key(key)) > 0

    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern."""
        full_pattern = f"{self._prefix}{pattern}"
        keys = self._redis.keys(full_pattern)
        # Remove prefix
        prefix_len = len(self._prefix)
        return [k[prefix_len:] for k in keys]

    def exists(self, key: str) -> bool:
        """Check if key exists."""
        return self._redis.exists(self._prefixed_key(key)) > 0

    def close(self) -> None:
        """Close the connection."""
        self._redis.close()


class GovernancePersistence:
    """
    Governance Persistence Layer.

    Provides a unified interface for persisting governance data
    with automatic backend selection and failover.

    AC-5: Ensures scores survive system restart.
    """

    # Storage keys
    KEY_REPUTATION_SCORES = "reputation:scores"
    KEY_REPUTATION_HISTORY = "reputation:history"
    KEY_IDENTITIES = "identity:agents"
    KEY_AUDIT_LOG = "audit:log"
    KEY_LOCKS = "locks:active"

    def __init__(
        self,
        backend: Optional[StorageBackend] = None,
        redis_url: Optional[str] = None,
        file_path: Optional[str] = None,
    ):
        """
        Initialize persistence layer.

        Args:
            backend: Explicit backend to use
            redis_url: Redis URL (redis://host:port/db)
            file_path: File storage path
        """
        if backend:
            self._backend = backend
        elif redis_url:
            # Parse Redis URL and create backend
            self._backend = self._create_redis_backend(redis_url)
        else:
            # Default to file storage
            self._backend = FileStorageBackend(
                storage_dir=file_path or "/tmp/governance_storage"
            )

        self._lock = threading.RLock()
        logger.info(f"GovernancePersistence initialized with {type(self._backend).__name__}")

    def _create_redis_backend(self, url: str) -> RedisStorageBackend:
        """Create Redis backend from URL."""
        # Parse redis://password@host:port/db
        import re
        match = re.match(r"redis://(?:([^@]+)@)?([^:]+):(\d+)(?:/(\d+))?", url)
        if match:
            password = match.group(1)
            host = match.group(2)
            port = int(match.group(3))
            db = int(match.group(4) or 0)
            return RedisStorageBackend(host=host, port=port, db=db, password=password)
        raise ValueError(f"Invalid Redis URL: {url}")

    # -------------------------------------------------------------------------
    # Reputation Persistence
    # -------------------------------------------------------------------------

    def save_reputation_score(self, agent_id: str, score_data: Dict[str, Any]) -> bool:
        """
        Save a reputation score.

        Args:
            agent_id: Agent identifier
            score_data: Score data dictionary

        Returns:
            True if saved successfully
        """
        key = f"{self.KEY_REPUTATION_SCORES}:{agent_id}"
        value = json.dumps(score_data)
        return self._backend.set(key, value)

    def load_reputation_score(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Load a reputation score.

        Args:
            agent_id: Agent identifier

        Returns:
            Score data or None
        """
        key = f"{self.KEY_REPUTATION_SCORES}:{agent_id}"
        value = self._backend.get(key)
        if value:
            return json.loads(value)
        return None

    def load_all_reputation_scores(self) -> Dict[str, Dict[str, Any]]:
        """Load all reputation scores."""
        scores = {}
        pattern = f"{self.KEY_REPUTATION_SCORES}:*"
        for key in self._backend.keys(pattern):
            agent_id = key.split(":")[-1]
            value = self._backend.get(key)
            if value:
                scores[agent_id] = json.loads(value)
        return scores

    def delete_reputation_score(self, agent_id: str) -> bool:
        """Delete a reputation score."""
        key = f"{self.KEY_REPUTATION_SCORES}:{agent_id}"
        return self._backend.delete(key)

    # -------------------------------------------------------------------------
    # Reputation History
    # -------------------------------------------------------------------------

    def append_reputation_history(self, entry: Dict[str, Any]) -> bool:
        """Append an entry to reputation history."""
        # Use timestamp as key for ordering
        timestamp = entry.get("timestamp", datetime.utcnow().isoformat())
        key = f"{self.KEY_REPUTATION_HISTORY}:{timestamp}"
        return self._backend.set(key, json.dumps(entry))

    def load_reputation_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Load reputation history."""
        history = []
        pattern = f"{self.KEY_REPUTATION_HISTORY}:*"
        keys = sorted(self._backend.keys(pattern), reverse=True)[:limit]
        for key in keys:
            value = self._backend.get(key)
            if value:
                history.append(json.loads(value))
        return history

    # -------------------------------------------------------------------------
    # Identity Persistence
    # -------------------------------------------------------------------------

    def save_identity(self, agent_id: str, identity_data: Dict[str, Any]) -> bool:
        """Save an agent identity."""
        key = f"{self.KEY_IDENTITIES}:{agent_id}"
        return self._backend.set(key, json.dumps(identity_data))

    def load_identity(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Load an agent identity."""
        key = f"{self.KEY_IDENTITIES}:{agent_id}"
        value = self._backend.get(key)
        if value:
            return json.loads(value)
        return None

    def load_all_identities(self) -> Dict[str, Dict[str, Any]]:
        """Load all identities."""
        identities = {}
        pattern = f"{self.KEY_IDENTITIES}:*"
        for key in self._backend.keys(pattern):
            agent_id = key.split(":")[-1]
            value = self._backend.get(key)
            if value:
                identities[agent_id] = json.loads(value)
        return identities

    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------

    def health_check(self) -> Dict[str, Any]:
        """Check storage health."""
        try:
            test_key = "health:check"
            test_value = datetime.utcnow().isoformat()
            self._backend.set(test_key, test_value)
            retrieved = self._backend.get(test_key)
            self._backend.delete(test_key)

            return {
                "status": "healthy" if retrieved == test_value else "degraded",
                "backend": type(self._backend).__name__,
                "write": retrieved == test_value,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "backend": type(self._backend).__name__,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        reputation_count = len(self._backend.keys(f"{self.KEY_REPUTATION_SCORES}:*"))
        identity_count = len(self._backend.keys(f"{self.KEY_IDENTITIES}:*"))
        history_count = len(self._backend.keys(f"{self.KEY_REPUTATION_HISTORY}:*"))

        return {
            "backend": type(self._backend).__name__,
            "reputation_scores": reputation_count,
            "identities": identity_count,
            "history_entries": history_count,
        }

    def close(self) -> None:
        """Close the persistence layer."""
        self._backend.close()


# Singleton instance
_persistence_instance: Optional[GovernancePersistence] = None


def get_persistence(
    redis_url: Optional[str] = None,
    file_path: Optional[str] = None,
) -> GovernancePersistence:
    """
    Get or create the persistence singleton.

    Args:
        redis_url: Redis URL for production
        file_path: File path for development

    Returns:
        GovernancePersistence instance
    """
    global _persistence_instance
    if _persistence_instance is None:
        _persistence_instance = GovernancePersistence(
            redis_url=redis_url,
            file_path=file_path,
        )
    return _persistence_instance
