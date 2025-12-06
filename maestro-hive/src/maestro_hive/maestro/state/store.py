"""
State Store - Abstract interface for state persistence

EPIC: MD-2528 - AC-1: Unified state store

Defines abstract interface for state storage with pluggable backends.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class StateEntry:
    """
    Entry in the state store with versioning.

    Attributes:
        key: Unique identifier for this state
        value: State data (serializable to JSON)
        version: Version number for this entry
        timestamp: When this version was created
        component_id: ID of component that created this version
        metadata: Additional metadata about this state
    """
    key: str
    value: Dict[str, Any]
    version: int = 1
    timestamp: datetime = field(default_factory=datetime.utcnow)
    component_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "key": self.key,
            "value": self.value,
            "version": self.version,
            "timestamp": self.timestamp.isoformat(),
            "component_id": self.component_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateEntry":
        """Create entry from dictionary."""
        return cls(
            key=data["key"],
            value=data["value"],
            version=data.get("version", 1),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.utcnow(),
            component_id=data.get("component_id"),
            metadata=data.get("metadata", {}),
        )


class StateStore(ABC):
    """
    Abstract interface for state storage.

    Implementations must handle:
    - State persistence with versioning
    - Atomic updates
    - Version history retrieval
    - State cleanup/pruning
    """

    @abstractmethod
    def save(
        self,
        key: str,
        value: Dict[str, Any],
        component_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StateEntry:
        """
        Save state and return the entry with version.

        Args:
            key: State key
            value: State data
            component_id: ID of saving component
            metadata: Additional metadata

        Returns:
            StateEntry with assigned version
        """
        pass

    @abstractmethod
    def load(
        self,
        key: str,
        version: Optional[int] = None,
    ) -> Optional[StateEntry]:
        """
        Load state, optionally at specific version.

        Args:
            key: State key
            version: Specific version or None for latest

        Returns:
            StateEntry or None if not found
        """
        pass

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete all versions of state.

        Args:
            key: State key

        Returns:
            True if deleted, False if not found
        """
        pass

    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if state exists.

        Args:
            key: State key

        Returns:
            True if state exists
        """
        pass

    @abstractmethod
    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """
        List all state keys, optionally filtered by prefix.

        Args:
            prefix: Key prefix to filter

        Returns:
            List of keys
        """
        pass

    @abstractmethod
    def list_versions(self, key: str) -> List[StateEntry]:
        """
        Get version history for a key.

        Args:
            key: State key

        Returns:
            List of entries ordered by version (oldest first)
        """
        pass

    @abstractmethod
    def get_latest_version(self, key: str) -> int:
        """
        Get the latest version number for a key.

        Args:
            key: State key

        Returns:
            Latest version number or 0 if not found
        """
        pass

    @abstractmethod
    def prune_versions(
        self,
        key: str,
        keep_count: int = 10,
    ) -> int:
        """
        Remove old versions keeping only the most recent.

        Args:
            key: State key
            keep_count: Number of versions to keep

        Returns:
            Number of versions pruned
        """
        pass

    def compare_and_swap(
        self,
        key: str,
        expected_version: int,
        new_value: Dict[str, Any],
        component_id: Optional[str] = None,
    ) -> Optional[StateEntry]:
        """
        Atomically update state if current version matches expected.

        Args:
            key: State key
            expected_version: Expected current version
            new_value: New state value
            component_id: ID of updating component

        Returns:
            New StateEntry if successful, None if version mismatch
        """
        current = self.load(key)
        if current is None and expected_version == 0:
            # Creating new state
            return self.save(key, new_value, component_id)
        elif current is None:
            logger.warning(f"CAS failed: key {key} does not exist")
            return None
        elif current.version != expected_version:
            logger.warning(
                f"CAS failed: version mismatch for {key} "
                f"(expected {expected_version}, got {current.version})"
            )
            return None
        else:
            return self.save(key, new_value, component_id)

    def batch_save(
        self,
        entries: List[tuple],
        component_id: Optional[str] = None,
    ) -> List[StateEntry]:
        """
        Save multiple state entries.

        Args:
            entries: List of (key, value) tuples
            component_id: ID of saving component

        Returns:
            List of saved entries
        """
        results = []
        for key, value in entries:
            entry = self.save(key, value, component_id)
            results.append(entry)
        return results

    def batch_load(self, keys: List[str]) -> Dict[str, Optional[StateEntry]]:
        """
        Load multiple state entries.

        Args:
            keys: List of keys to load

        Returns:
            Dict mapping keys to entries (None if not found)
        """
        return {key: self.load(key) for key in keys}
