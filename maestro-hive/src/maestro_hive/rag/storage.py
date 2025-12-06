"""
Storage Backends for RAG Service.

Manages persistent storage of execution history and embeddings.

EPIC: MD-2499
"""

import json
import logging
import os
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from maestro_hive.rag.exceptions import StorageError
from maestro_hive.rag.models import ExecutionRecord

logger = logging.getLogger(__name__)


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    def store(self, record: ExecutionRecord) -> None:
        """
        Store an execution record.

        Args:
            record: Execution record to store

        Raises:
            StorageError: If storage fails
        """
        pass

    @abstractmethod
    def get(self, execution_id: str) -> Optional[ExecutionRecord]:
        """
        Retrieve an execution record by ID.

        Args:
            execution_id: Unique identifier

        Returns:
            ExecutionRecord or None if not found
        """
        pass

    @abstractmethod
    def list_all(self) -> List[ExecutionRecord]:
        """
        List all stored execution records.

        Returns:
            List of all execution records
        """
        pass

    @abstractmethod
    def delete(self, execution_id: str) -> bool:
        """
        Delete an execution record.

        Args:
            execution_id: Unique identifier

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """Return total number of stored records."""
        pass

    def search_by_embedding(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        threshold: float = 0.0,
    ) -> List[tuple[ExecutionRecord, float]]:
        """
        Search for similar records using embedding similarity.

        Default implementation performs linear scan.
        Override for more efficient implementations.

        Args:
            query_embedding: Query vector
            top_k: Maximum results to return
            threshold: Minimum similarity threshold

        Returns:
            List of (record, similarity_score) tuples
        """
        records = self.list_all()
        scored = []

        for record in records:
            if record.embedding is None:
                continue

            similarity = self._cosine_similarity(query_embedding, record.embedding)
            if similarity >= threshold:
                scored.append((record, similarity))

        # Sort by similarity (descending) and return top_k
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        magnitude_a = sum(x * x for x in a) ** 0.5
        magnitude_b = sum(x * x for x in b) ** 0.5

        if magnitude_a == 0 or magnitude_b == 0:
            return 0.0

        return dot_product / (magnitude_a * magnitude_b)


class InMemoryStorage(StorageBackend):
    """
    In-memory storage for development and testing.

    Data is lost when the process terminates.
    """

    def __init__(self):
        """Initialize empty storage."""
        self._records: Dict[str, ExecutionRecord] = {}

    def store(self, record: ExecutionRecord) -> None:
        """Store record in memory."""
        self._records[record.execution_id] = record

    def get(self, execution_id: str) -> Optional[ExecutionRecord]:
        """Get record from memory."""
        return self._records.get(execution_id)

    def list_all(self) -> List[ExecutionRecord]:
        """List all records."""
        return list(self._records.values())

    def delete(self, execution_id: str) -> bool:
        """Delete record from memory."""
        if execution_id in self._records:
            del self._records[execution_id]
            return True
        return False

    def count(self) -> int:
        """Return record count."""
        return len(self._records)

    def clear(self) -> None:
        """Clear all records."""
        self._records.clear()


class FileStorage(StorageBackend):
    """
    File-based storage using JSON files.

    Each execution is stored as a separate JSON file.
    Suitable for development and small-scale deployments.
    """

    def __init__(
        self,
        path: str = "data/rag/executions",
        index_path: Optional[str] = None,
    ):
        """
        Initialize file storage.

        Args:
            path: Directory path for execution files
            index_path: Optional path for index file
        """
        self.path = Path(path)
        self.index_path = Path(index_path) if index_path else self.path / "index.json"
        self._ensure_directories()
        self._index: Dict[str, Dict[str, Any]] = {}
        self._load_index()

    def _ensure_directories(self) -> None:
        """Create storage directories if they don't exist."""
        try:
            self.path.mkdir(parents=True, exist_ok=True)
            self.index_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise StorageError(f"Failed to create storage directories: {e}")

    def _load_index(self) -> None:
        """Load index from file."""
        if self.index_path.exists():
            try:
                with open(self.index_path) as f:
                    self._index = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load index: {e}")
                self._index = {}

    def _save_index(self) -> None:
        """Save index to file."""
        try:
            with open(self.index_path, "w") as f:
                json.dump(self._index, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save index: {e}")

    def _get_file_path(self, execution_id: str) -> Path:
        """Get file path for an execution ID."""
        # Sanitize ID for filename
        safe_id = "".join(c if c.isalnum() or c in "-_" else "_" for c in execution_id)
        return self.path / f"{safe_id}.json"

    def store(self, record: ExecutionRecord) -> None:
        """Store record to file."""
        try:
            file_path = self._get_file_path(record.execution_id)
            with open(file_path, "w") as f:
                json.dump(record.to_dict(), f, indent=2)

            # Update index
            self._index[record.execution_id] = {
                "file": str(file_path),
                "outcome": record.outcome.value,
                "timestamp": record.timestamp.isoformat(),
            }
            self._save_index()

        except Exception as e:
            raise StorageError(f"Failed to store record: {e}")

    def get(self, execution_id: str) -> Optional[ExecutionRecord]:
        """Get record from file."""
        file_path = self._get_file_path(execution_id)
        if not file_path.exists():
            return None

        try:
            with open(file_path) as f:
                data = json.load(f)
            return ExecutionRecord.from_dict(data)
        except Exception as e:
            logger.warning(f"Failed to load record {execution_id}: {e}")
            return None

    def list_all(self) -> List[ExecutionRecord]:
        """List all records from files."""
        records = []
        for file_path in self.path.glob("*.json"):
            if file_path.name == "index.json":
                continue
            try:
                with open(file_path) as f:
                    data = json.load(f)
                records.append(ExecutionRecord.from_dict(data))
            except Exception as e:
                logger.warning(f"Failed to load {file_path}: {e}")
        return records

    def delete(self, execution_id: str) -> bool:
        """Delete record file."""
        file_path = self._get_file_path(execution_id)
        if file_path.exists():
            try:
                file_path.unlink()
                if execution_id in self._index:
                    del self._index[execution_id]
                    self._save_index()
                return True
            except Exception as e:
                logger.warning(f"Failed to delete {execution_id}: {e}")
        return False

    def count(self) -> int:
        """Return record count."""
        return len(list(self.path.glob("*.json"))) - (
            1 if self.index_path.exists() else 0
        )

    def rebuild_index(self) -> None:
        """Rebuild index from files."""
        self._index = {}
        for record in self.list_all():
            self._index[record.execution_id] = {
                "file": str(self._get_file_path(record.execution_id)),
                "outcome": record.outcome.value,
                "timestamp": record.timestamp.isoformat(),
            }
        self._save_index()
        logger.info(f"Rebuilt index with {len(self._index)} records")


class HybridStorage(StorageBackend):
    """
    Hybrid storage with in-memory cache and file persistence.

    Provides fast reads with durable storage.
    """

    def __init__(
        self,
        file_storage: Optional[FileStorage] = None,
        cache_size: int = 100,
    ):
        """
        Initialize hybrid storage.

        Args:
            file_storage: Underlying file storage
            cache_size: Maximum records to keep in memory
        """
        self._file_storage = file_storage or FileStorage()
        self._cache: Dict[str, ExecutionRecord] = {}
        self._cache_size = cache_size
        self._access_order: List[str] = []

    def _update_cache(self, record: ExecutionRecord) -> None:
        """Update cache with record, evicting oldest if needed."""
        execution_id = record.execution_id

        # Remove from current position if exists
        if execution_id in self._access_order:
            self._access_order.remove(execution_id)

        # Add to end (most recent)
        self._access_order.append(execution_id)
        self._cache[execution_id] = record

        # Evict oldest if over capacity
        while len(self._cache) > self._cache_size:
            oldest_id = self._access_order.pop(0)
            del self._cache[oldest_id]

    def store(self, record: ExecutionRecord) -> None:
        """Store to both cache and file."""
        self._file_storage.store(record)
        self._update_cache(record)

    def get(self, execution_id: str) -> Optional[ExecutionRecord]:
        """Get from cache or file."""
        if execution_id in self._cache:
            # Update access order
            self._access_order.remove(execution_id)
            self._access_order.append(execution_id)
            return self._cache[execution_id]

        record = self._file_storage.get(execution_id)
        if record:
            self._update_cache(record)
        return record

    def list_all(self) -> List[ExecutionRecord]:
        """List all from file storage."""
        return self._file_storage.list_all()

    def delete(self, execution_id: str) -> bool:
        """Delete from both cache and file."""
        if execution_id in self._cache:
            del self._cache[execution_id]
            if execution_id in self._access_order:
                self._access_order.remove(execution_id)
        return self._file_storage.delete(execution_id)

    def count(self) -> int:
        """Return record count from file storage."""
        return self._file_storage.count()

    def clear_cache(self) -> None:
        """Clear in-memory cache."""
        self._cache.clear()
        self._access_order.clear()
