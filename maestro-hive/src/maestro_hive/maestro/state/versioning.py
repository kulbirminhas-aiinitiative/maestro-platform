"""
State Versioning - History tracking and recovery

EPIC: MD-2528 - AC-3: State versioning and history

Provides version history management and state recovery capabilities.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .store import StateEntry, StateStore

logger = logging.getLogger(__name__)


@dataclass
class VersionDiff:
    """Difference between two state versions."""
    key: str
    from_version: int
    to_version: int
    added_keys: List[str]
    removed_keys: List[str]
    modified_keys: List[str]
    changes: Dict[str, Tuple[Any, Any]]  # key -> (old_value, new_value)


class StateVersioning:
    """
    State version history management.

    Provides:
    - Version history retrieval
    - Version comparison (diff)
    - Rollback to previous versions
    - Snapshot creation and restoration
    """

    def __init__(
        self,
        store: StateStore,
        max_versions: int = 100,
        retention_days: int = 30,
    ):
        """
        Initialize state versioning.

        Args:
            store: State store backend
            max_versions: Maximum versions to retain per key
            retention_days: Days to retain old versions
        """
        self.store = store
        self.max_versions = max_versions
        self.retention_days = retention_days

        logger.info(f"StateVersioning initialized (max={max_versions}, retention={retention_days}d)")

    def get_history(
        self,
        key: str,
        limit: Optional[int] = None,
    ) -> List[StateEntry]:
        """
        Get version history for a key.

        Args:
            key: State key
            limit: Maximum versions to return (newest first)

        Returns:
            List of entries ordered newest to oldest
        """
        versions = self.store.list_versions(key)
        # Reverse to get newest first
        versions = list(reversed(versions))

        if limit:
            versions = versions[:limit]

        return versions

    def get_version(
        self,
        key: str,
        version: int,
    ) -> Optional[StateEntry]:
        """
        Get specific version of state.

        Args:
            key: State key
            version: Version number

        Returns:
            StateEntry or None if not found
        """
        return self.store.load(key, version)

    def get_version_at_time(
        self,
        key: str,
        timestamp: datetime,
    ) -> Optional[StateEntry]:
        """
        Get state version at or before a specific time.

        Args:
            key: State key
            timestamp: Target timestamp

        Returns:
            StateEntry or None if not found
        """
        versions = self.store.list_versions(key)

        # Find latest version at or before timestamp
        result = None
        for entry in versions:
            if entry.timestamp <= timestamp:
                result = entry
            else:
                break  # Versions are ordered, can stop

        return result

    def compare_versions(
        self,
        key: str,
        from_version: int,
        to_version: int,
    ) -> Optional[VersionDiff]:
        """
        Compare two versions and return differences.

        Args:
            key: State key
            from_version: Starting version
            to_version: Ending version

        Returns:
            VersionDiff or None if versions not found
        """
        from_entry = self.store.load(key, from_version)
        to_entry = self.store.load(key, to_version)

        if not from_entry or not to_entry:
            return None

        from_value = from_entry.value
        to_value = to_entry.value

        # Calculate differences
        from_keys = set(from_value.keys())
        to_keys = set(to_value.keys())

        added_keys = list(to_keys - from_keys)
        removed_keys = list(from_keys - to_keys)
        common_keys = from_keys & to_keys

        modified_keys = []
        changes = {}

        for k in common_keys:
            if from_value[k] != to_value[k]:
                modified_keys.append(k)
                changes[k] = (from_value[k], to_value[k])

        for k in added_keys:
            changes[k] = (None, to_value[k])

        for k in removed_keys:
            changes[k] = (from_value[k], None)

        return VersionDiff(
            key=key,
            from_version=from_version,
            to_version=to_version,
            added_keys=added_keys,
            removed_keys=removed_keys,
            modified_keys=modified_keys,
            changes=changes,
        )

    def rollback(
        self,
        key: str,
        to_version: int,
        component_id: Optional[str] = None,
    ) -> Optional[StateEntry]:
        """
        Rollback state to a previous version.

        Creates a new version with the old value (doesn't delete history).

        Args:
            key: State key
            to_version: Version to rollback to
            component_id: ID of component performing rollback

        Returns:
            New StateEntry with rolled back value, or None if version not found
        """
        target = self.store.load(key, to_version)
        if not target:
            logger.warning(f"Cannot rollback {key}: version {to_version} not found")
            return None

        # Save as new version
        entry = self.store.save(
            key=key,
            value=target.value,
            component_id=component_id,
            metadata={
                "rollback": True,
                "rolled_back_from": self.store.get_latest_version(key),
                "rolled_back_to": to_version,
            },
        )

        logger.info(f"Rolled back {key} to version {to_version} (new version: {entry.version})")
        return entry

    def create_snapshot(
        self,
        keys: Optional[List[str]] = None,
        prefix: Optional[str] = None,
    ) -> Dict[str, StateEntry]:
        """
        Create snapshot of current state.

        Args:
            keys: Specific keys to snapshot, or None for all
            prefix: Key prefix filter

        Returns:
            Dict mapping keys to current entries
        """
        if keys is None:
            keys = self.store.list_keys(prefix)

        snapshot = {}
        for key in keys:
            entry = self.store.load(key)
            if entry:
                snapshot[key] = entry

        logger.info(f"Created snapshot of {len(snapshot)} keys")
        return snapshot

    def restore_snapshot(
        self,
        snapshot: Dict[str, StateEntry],
        component_id: Optional[str] = None,
    ) -> int:
        """
        Restore state from snapshot.

        Args:
            snapshot: Snapshot from create_snapshot
            component_id: ID of component performing restore

        Returns:
            Number of keys restored
        """
        count = 0
        for key, entry in snapshot.items():
            self.store.save(
                key=key,
                value=entry.value,
                component_id=component_id,
                metadata={
                    "restored_from_snapshot": True,
                    "original_version": entry.version,
                    "original_timestamp": entry.timestamp.isoformat(),
                },
            )
            count += 1

        logger.info(f"Restored {count} keys from snapshot")
        return count

    def prune_old_versions(
        self,
        key: Optional[str] = None,
    ) -> int:
        """
        Remove old versions based on retention policy.

        Args:
            key: Specific key to prune, or None for all keys

        Returns:
            Total versions pruned
        """
        total_pruned = 0
        keys = [key] if key else self.store.list_keys()

        cutoff = datetime.utcnow() - timedelta(days=self.retention_days)

        for k in keys:
            versions = self.store.list_versions(k)

            # Keep versions within retention or up to max_versions
            versions_to_keep = max(
                len([v for v in versions if v.timestamp > cutoff]),
                min(len(versions), self.max_versions)
            )

            if len(versions) > versions_to_keep:
                pruned = self.store.prune_versions(k, versions_to_keep)
                total_pruned += pruned

        logger.info(f"Pruned {total_pruned} old versions")
        return total_pruned

    def get_version_stats(self, key: str) -> Dict[str, Any]:
        """
        Get statistics for key's version history.

        Args:
            key: State key

        Returns:
            Statistics dict
        """
        versions = self.store.list_versions(key)

        if not versions:
            return {
                "key": key,
                "total_versions": 0,
            }

        return {
            "key": key,
            "total_versions": len(versions),
            "oldest_version": versions[0].version,
            "oldest_timestamp": versions[0].timestamp.isoformat(),
            "latest_version": versions[-1].version,
            "latest_timestamp": versions[-1].timestamp.isoformat(),
            "components": list(set(
                v.component_id for v in versions if v.component_id
            )),
        }

    def find_version_by_metadata(
        self,
        key: str,
        metadata_query: Dict[str, Any],
    ) -> List[StateEntry]:
        """
        Find versions matching metadata query.

        Args:
            key: State key
            metadata_query: Metadata key-value pairs to match

        Returns:
            List of matching entries
        """
        versions = self.store.list_versions(key)
        matches = []

        for entry in versions:
            if all(
                entry.metadata.get(k) == v
                for k, v in metadata_query.items()
            ):
                matches.append(entry)

        return matches
