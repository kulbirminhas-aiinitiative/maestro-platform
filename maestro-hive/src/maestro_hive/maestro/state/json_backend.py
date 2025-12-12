"""
JSON State Store - File-based state persistence

EPIC: MD-2528 - AC-1: Unified state store (JSON backend)

File-based state storage for development and simple deployments.
"""

import json
import logging
import os
import shutil
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional

from .store import StateEntry, StateStore

logger = logging.getLogger(__name__)


class JSONStateStore(StateStore):
    """
    JSON file-based state store.

    Stores state in JSON files with versioning support.
    Thread-safe for concurrent access within a single process.

    File structure:
        state_dir/
            {key}/
                current.json  - Latest version
                versions/
                    v001.json
                    v002.json
                    ...
    """

    def __init__(
        self,
        state_dir: str = "/var/maestro/state",
        max_versions: int = 100,
    ):
        """
        Initialize JSON state store.

        Args:
            state_dir: Directory for state files
            max_versions: Maximum versions to retain per key
        """
        self.state_dir = Path(state_dir)
        self.max_versions = max_versions
        self._locks: Dict[str, RLock] = {}
        self._global_lock = RLock()

        self.state_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"JSONStateStore initialized at {self.state_dir}")

    def _get_lock(self, key: str) -> RLock:
        """Get or create lock for key."""
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = RLock()
            return self._locks[key]

    def _key_dir(self, key: str) -> Path:
        """Get directory for key."""
        # Sanitize key for filesystem
        safe_key = key.replace("/", "_").replace("\\", "_")
        return self.state_dir / safe_key

    def _versions_dir(self, key: str) -> Path:
        """Get versions directory for key."""
        return self._key_dir(key) / "versions"

    def _current_path(self, key: str) -> Path:
        """Get path to current version file."""
        return self._key_dir(key) / "current.json"

    def _version_path(self, key: str, version: int) -> Path:
        """Get path to specific version file."""
        return self._versions_dir(key) / f"v{version:06d}.json"

    def save(
        self,
        key: str,
        value: Dict[str, Any],
        component_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StateEntry:
        """Save state with auto-incrementing version."""
        lock = self._get_lock(key)

        with lock:
            # Get next version
            current_version = self.get_latest_version(key)
            new_version = current_version + 1

            # Create entry
            entry = StateEntry(
                key=key,
                value=value,
                version=new_version,
                timestamp=datetime.utcnow(),
                component_id=component_id,
                metadata=metadata or {},
            )

            # Create directories
            key_dir = self._key_dir(key)
            versions_dir = self._versions_dir(key)
            key_dir.mkdir(parents=True, exist_ok=True)
            versions_dir.mkdir(parents=True, exist_ok=True)

            # Save version file
            version_path = self._version_path(key, new_version)
            with open(version_path, "w") as f:
                json.dump(entry.to_dict(), f, indent=2)

            # Update current pointer
            current_path = self._current_path(key)
            with open(current_path, "w") as f:
                json.dump(entry.to_dict(), f, indent=2)

            logger.debug(f"Saved state {key} v{new_version}")

            # Auto-prune if needed
            if new_version > self.max_versions:
                self.prune_versions(key, self.max_versions)

            return entry

    def load(
        self,
        key: str,
        version: Optional[int] = None,
    ) -> Optional[StateEntry]:
        """Load state, optionally at specific version."""
        lock = self._get_lock(key)

        with lock:
            if version is not None:
                path = self._version_path(key, version)
            else:
                path = self._current_path(key)

            if not path.exists():
                return None

            try:
                with open(path, "r") as f:
                    data = json.load(f)
                return StateEntry.from_dict(data)
            except Exception as e:
                logger.error(f"Failed to load state {key}: {e}")
                return None

    def delete(self, key: str) -> bool:
        """Delete all versions of state."""
        lock = self._get_lock(key)

        with lock:
            key_dir = self._key_dir(key)
            if key_dir.exists():
                shutil.rmtree(key_dir)
                logger.info(f"Deleted state {key}")
                return True
            return False

    def exists(self, key: str) -> bool:
        """Check if state exists."""
        return self._current_path(key).exists()

    def list_keys(self, prefix: Optional[str] = None) -> List[str]:
        """List all state keys."""
        keys = []
        for item in self.state_dir.iterdir():
            if item.is_dir() and (self._current_path(item.name).exists()):
                # Convert filesystem name back to key
                key = item.name.replace("_", "/")
                if prefix is None or key.startswith(prefix):
                    keys.append(key)
        return sorted(keys)

    def list_versions(self, key: str) -> List[StateEntry]:
        """Get version history for a key."""
        lock = self._get_lock(key)
        entries = []

        with lock:
            versions_dir = self._versions_dir(key)
            if not versions_dir.exists():
                return []

            for path in sorted(versions_dir.glob("v*.json")):
                try:
                    with open(path, "r") as f:
                        data = json.load(f)
                    entries.append(StateEntry.from_dict(data))
                except Exception as e:
                    logger.warning(f"Failed to load version {path}: {e}")

        return entries

    def get_latest_version(self, key: str) -> int:
        """Get the latest version number."""
        current = self.load(key)
        return current.version if current else 0

    def prune_versions(
        self,
        key: str,
        keep_count: int = 10,
    ) -> int:
        """Remove old versions keeping only the most recent."""
        lock = self._get_lock(key)
        pruned = 0

        with lock:
            versions_dir = self._versions_dir(key)
            if not versions_dir.exists():
                return 0

            # Get all version files sorted by version number
            version_files = sorted(versions_dir.glob("v*.json"))

            # Calculate how many to remove
            remove_count = len(version_files) - keep_count
            if remove_count <= 0:
                return 0

            # Remove oldest versions
            for path in version_files[:remove_count]:
                path.unlink()
                pruned += 1

            logger.info(f"Pruned {pruned} old versions of {key}")

        return pruned

    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        total_keys = 0
        total_versions = 0
        total_size = 0

        for key_dir in self.state_dir.iterdir():
            if key_dir.is_dir():
                total_keys += 1
                versions_dir = key_dir / "versions"
                if versions_dir.exists():
                    for f in versions_dir.glob("*.json"):
                        total_versions += 1
                        total_size += f.stat().st_size

        return {
            "backend": "json",
            "state_dir": str(self.state_dir),
            "total_keys": total_keys,
            "total_versions": total_versions,
            "total_size_bytes": total_size,
            "max_versions": self.max_versions,
        }

    def export_all(self, output_path: str) -> int:
        """
        Export all state to a single JSON file.

        Args:
            output_path: Path for export file

        Returns:
            Number of keys exported
        """
        export_data = {}
        keys = self.list_keys()

        for key in keys:
            entry = self.load(key)
            if entry:
                export_data[key] = entry.to_dict()

        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

        logger.info(f"Exported {len(keys)} keys to {output_path}")
        return len(keys)

    def import_all(
        self,
        input_path: str,
        component_id: Optional[str] = None,
    ) -> int:
        """
        Import state from export file.

        Args:
            input_path: Path to import file
            component_id: ID for import operation

        Returns:
            Number of keys imported
        """
        with open(input_path, "r") as f:
            import_data = json.load(f)

        count = 0
        for key, entry_data in import_data.items():
            self.save(
                key=key,
                value=entry_data.get("value", {}),
                component_id=component_id or entry_data.get("component_id"),
                metadata=entry_data.get("metadata", {}),
            )
            count += 1

        logger.info(f"Imported {count} keys from {input_path}")
        return count
