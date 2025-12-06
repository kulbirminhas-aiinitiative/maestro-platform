"""
Persona Version Store

Implements AC-2: Version history queryable (who changed, when, what).

Provides storage backends for persona version history.

Epic: MD-2555
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Dict, List, Optional, Any
import json
import os

from .version import PersonaVersion, PersonaSnapshot, VersionChange


class PersonaVersionStore(ABC):
    """
    Abstract base class for persona version storage.

    Defines the interface for storing and retrieving persona versions.
    Implementations may use JSON files, PostgreSQL, or other backends.
    """

    @abstractmethod
    def save_version(self, version: PersonaVersion) -> None:
        """
        Save a new persona version.

        Args:
            version: The PersonaVersion to persist
        """
        pass

    @abstractmethod
    def get_version(
        self,
        persona_id: str,
        version_id: str
    ) -> Optional[PersonaVersion]:
        """
        Get a specific version by ID.

        Args:
            persona_id: The persona identifier
            version_id: The version identifier

        Returns:
            PersonaVersion if found, None otherwise
        """
        pass

    @abstractmethod
    def get_latest_version(self, persona_id: str) -> Optional[PersonaVersion]:
        """
        Get the most recent version of a persona.

        Args:
            persona_id: The persona identifier

        Returns:
            Latest PersonaVersion if any exist, None otherwise
        """
        pass

    @abstractmethod
    def get_history(
        self,
        persona_id: str,
        limit: int = 100
    ) -> List[PersonaVersion]:
        """
        Get version history for a persona.

        AC-2 Implementation: Queryable version history.

        Args:
            persona_id: The persona identifier
            limit: Maximum number of versions to return

        Returns:
            List of PersonaVersions, most recent first
        """
        pass

    @abstractmethod
    def get_version_by_number(
        self,
        persona_id: str,
        version_number: str
    ) -> Optional[PersonaVersion]:
        """
        Get a version by its semantic version number.

        Args:
            persona_id: The persona identifier
            version_number: Semantic version string (e.g., "1.2.3")

        Returns:
            PersonaVersion if found, None otherwise
        """
        pass

    @abstractmethod
    def list_personas(self) -> List[str]:
        """
        List all persona IDs with version history.

        Returns:
            List of persona identifiers
        """
        pass

    @abstractmethod
    def delete_version(self, persona_id: str, version_id: str) -> bool:
        """
        Delete a specific version.

        Args:
            persona_id: The persona identifier
            version_id: The version identifier

        Returns:
            True if deleted, False if not found
        """
        pass


class JSONVersionStore(PersonaVersionStore):
    """
    JSON file-based version store implementation.

    Stores persona versions as JSON files in a directory structure:
    {version_dir}/{persona_id}/versions.json
    """

    def __init__(
        self,
        version_dir: str = "/tmp/maestro/persona_versions",
        max_versions_per_persona: int = 100
    ):
        """
        Initialize JSON version store.

        Args:
            version_dir: Directory for storing version files
            max_versions_per_persona: Maximum versions to retain per persona
        """
        self.version_dir = Path(version_dir)
        self.max_versions = max_versions_per_persona
        self._locks: Dict[str, RLock] = {}
        self._global_lock = RLock()
        self.version_dir.mkdir(parents=True, exist_ok=True)

    def _get_lock(self, persona_id: str) -> RLock:
        """Get or create lock for persona"""
        with self._global_lock:
            if persona_id not in self._locks:
                self._locks[persona_id] = RLock()
            return self._locks[persona_id]

    def _get_persona_file(self, persona_id: str) -> Path:
        """Get path to persona version file"""
        persona_dir = self.version_dir / persona_id
        persona_dir.mkdir(parents=True, exist_ok=True)
        return persona_dir / "versions.json"

    def _load_versions(self, persona_id: str) -> List[PersonaVersion]:
        """Load all versions for a persona from disk"""
        file_path = self._get_persona_file(persona_id)
        if not file_path.exists():
            return []

        with open(file_path, "r") as f:
            data = json.load(f)

        return [PersonaVersion.from_dict(v) for v in data.get("versions", [])]

    def _save_versions(self, persona_id: str, versions: List[PersonaVersion]) -> None:
        """Save all versions for a persona to disk"""
        file_path = self._get_persona_file(persona_id)

        # Sort by timestamp descending
        versions.sort(key=lambda v: v.timestamp, reverse=True)

        # Prune old versions if over limit
        if len(versions) > self.max_versions:
            versions = versions[:self.max_versions]

        data = {
            "persona_id": persona_id,
            "version_count": len(versions),
            "last_updated": datetime.utcnow().isoformat(),
            "versions": [v.to_dict() for v in versions]
        }

        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    def save_version(self, version: PersonaVersion) -> None:
        """Save a new persona version"""
        with self._get_lock(version.persona_id):
            versions = self._load_versions(version.persona_id)

            # Check for duplicate version_id
            existing_ids = {v.version_id for v in versions}
            if version.version_id in existing_ids:
                raise ValueError(f"Version ID {version.version_id} already exists")

            versions.append(version)
            self._save_versions(version.persona_id, versions)

    def get_version(
        self,
        persona_id: str,
        version_id: str
    ) -> Optional[PersonaVersion]:
        """Get a specific version by ID"""
        with self._get_lock(persona_id):
            versions = self._load_versions(persona_id)
            for v in versions:
                if v.version_id == version_id:
                    return v
            return None

    def get_latest_version(self, persona_id: str) -> Optional[PersonaVersion]:
        """Get the most recent version"""
        with self._get_lock(persona_id):
            versions = self._load_versions(persona_id)
            if not versions:
                return None
            # Versions are sorted by timestamp descending
            return versions[0]

    def get_history(
        self,
        persona_id: str,
        limit: int = 100
    ) -> List[PersonaVersion]:
        """Get version history, most recent first"""
        with self._get_lock(persona_id):
            versions = self._load_versions(persona_id)
            return versions[:limit]

    def get_version_by_number(
        self,
        persona_id: str,
        version_number: str
    ) -> Optional[PersonaVersion]:
        """Get a version by semantic version number"""
        with self._get_lock(persona_id):
            versions = self._load_versions(persona_id)
            for v in versions:
                if v.version_number == version_number:
                    return v
            return None

    def list_personas(self) -> List[str]:
        """List all persona IDs with version history"""
        if not self.version_dir.exists():
            return []

        personas = []
        for item in self.version_dir.iterdir():
            if item.is_dir() and (item / "versions.json").exists():
                personas.append(item.name)
        return sorted(personas)

    def delete_version(self, persona_id: str, version_id: str) -> bool:
        """Delete a specific version"""
        with self._get_lock(persona_id):
            versions = self._load_versions(persona_id)
            original_count = len(versions)

            versions = [v for v in versions if v.version_id != version_id]

            if len(versions) == original_count:
                return False  # Not found

            self._save_versions(persona_id, versions)
            return True

    def get_versions_by_author(
        self,
        persona_id: str,
        author: str
    ) -> List[PersonaVersion]:
        """Get all versions created by a specific author"""
        with self._get_lock(persona_id):
            versions = self._load_versions(persona_id)
            return [v for v in versions if v.author == author]

    def get_versions_in_range(
        self,
        persona_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[PersonaVersion]:
        """Get versions within a time range"""
        with self._get_lock(persona_id):
            versions = self._load_versions(persona_id)
            return [
                v for v in versions
                if start_time <= v.timestamp <= end_time
            ]
