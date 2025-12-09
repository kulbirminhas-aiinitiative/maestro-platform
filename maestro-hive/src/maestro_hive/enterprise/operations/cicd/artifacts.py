"""
Artifact Management for CI/CD Pipeline.

Handles build artifact storage, versioning, and retrieval.
"""

import hashlib
import uuid
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


@dataclass
class Artifact:
    """Build artifact representation."""
    id: str
    name: str
    path: str
    hash: str
    size_bytes: int
    content_type: str
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        name: str,
        path: str,
        content: bytes,
        content_type: str = "application/octet-stream",
        metadata: dict[str, Any] = None
    ) -> "Artifact":
        """Create artifact from content."""
        artifact_hash = hashlib.sha256(content).hexdigest()
        return cls(
            id=str(uuid.uuid4()),
            name=name,
            path=path,
            hash=f"sha256:{artifact_hash}",
            size_bytes=len(content),
            content_type=content_type,
            created_at=datetime.utcnow(),
            metadata=metadata or {}
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "path": self.path,
            "hash": self.hash,
            "size_bytes": self.size_bytes,
            "content_type": self.content_type,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
            "tags": self.tags
        }


class ArtifactStorage:
    """Abstract artifact storage backend."""

    async def store(self, artifact: Artifact, content: bytes) -> str:
        """Store artifact content. Returns storage URL."""
        raise NotImplementedError

    async def retrieve(self, artifact_id: str) -> Optional[bytes]:
        """Retrieve artifact content."""
        raise NotImplementedError

    async def delete(self, artifact_id: str) -> bool:
        """Delete artifact."""
        raise NotImplementedError

    async def list(self, prefix: str = "") -> list[Artifact]:
        """List artifacts."""
        raise NotImplementedError


class LocalArtifactStorage(ArtifactStorage):
    """Local filesystem artifact storage."""

    def __init__(self, base_path: str = "/tmp/artifacts"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._artifacts: dict[str, Artifact] = {}

    async def store(self, artifact: Artifact, content: bytes) -> str:
        """Store artifact to local filesystem."""
        artifact_path = self.base_path / artifact.id
        artifact_path.write_bytes(content)
        self._artifacts[artifact.id] = artifact
        return str(artifact_path)

    async def retrieve(self, artifact_id: str) -> Optional[bytes]:
        """Retrieve artifact from local filesystem."""
        artifact_path = self.base_path / artifact_id
        if artifact_path.exists():
            return artifact_path.read_bytes()
        return None

    async def delete(self, artifact_id: str) -> bool:
        """Delete artifact from local filesystem."""
        artifact_path = self.base_path / artifact_id
        if artifact_path.exists():
            artifact_path.unlink()
            self._artifacts.pop(artifact_id, None)
            return True
        return False

    async def list(self, prefix: str = "") -> list[Artifact]:
        """List all artifacts."""
        return [
            a for a in self._artifacts.values()
            if a.name.startswith(prefix)
        ]


class ArtifactManager:
    """Manages artifacts throughout pipeline lifecycle."""

    def __init__(self, storage: Optional[ArtifactStorage] = None):
        self.storage = storage or LocalArtifactStorage()
        self._pending: list[Artifact] = []
        self._stored: dict[str, Artifact] = {}

    def register(self, artifact: Artifact) -> None:
        """Register artifact for later collection."""
        self._pending.append(artifact)

    async def store(self, artifact: Artifact, content: bytes) -> str:
        """Store artifact immediately."""
        url = await self.storage.store(artifact, content)
        self._stored[artifact.id] = artifact
        return url

    async def collect_all(self) -> list[dict[str, Any]]:
        """Collect all registered artifacts."""
        collected = []
        for artifact in self._pending:
            self._stored[artifact.id] = artifact
            collected.append(artifact.to_dict())
        self._pending.clear()
        return collected

    async def get(self, artifact_id: str) -> Optional[Artifact]:
        """Get artifact by ID."""
        return self._stored.get(artifact_id)

    async def get_by_name(self, name: str) -> list[Artifact]:
        """Get artifacts by name pattern."""
        return [
            a for a in self._stored.values()
            if name in a.name
        ]

    async def get_by_tag(self, tag: str) -> list[Artifact]:
        """Get artifacts by tag."""
        return [
            a for a in self._stored.values()
            if tag in a.tags
        ]

    def tag(self, artifact_id: str, tag: str) -> bool:
        """Add tag to artifact."""
        artifact = self._stored.get(artifact_id)
        if artifact:
            if tag not in artifact.tags:
                artifact.tags.append(tag)
            return True
        return False

    async def cleanup(self, older_than_days: int = 30) -> int:
        """Clean up old artifacts."""
        now = datetime.utcnow()
        cleaned = 0
        to_remove = []

        for artifact_id, artifact in self._stored.items():
            age_days = (now - artifact.created_at).days
            if age_days > older_than_days:
                await self.storage.delete(artifact_id)
                to_remove.append(artifact_id)
                cleaned += 1

        for artifact_id in to_remove:
            del self._stored[artifact_id]

        return cleaned
