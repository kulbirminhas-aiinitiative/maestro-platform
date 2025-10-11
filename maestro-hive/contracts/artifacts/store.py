"""
Artifact Store
Version: 1.0.0

Content-addressable artifact storage with SHA-256 digests and integrity verification.

Storage structure:
    /var/maestro/artifacts/
        {digest[0:2]}/
            {digest[2:4]}/
                {full_digest}  ← Actual file
                {full_digest}.meta  ← Metadata (JSON)
"""

from pathlib import Path
from typing import Optional, List
import shutil
import uuid
import logging
import os
import json

from contracts.artifacts.models import Artifact, compute_sha256

logger = logging.getLogger(__name__)


class ArtifactStore:
    """
    Content-addressable artifact storage.

    Benefits:
    - Content verification (digest mismatch = corruption detected)
    - Deduplication (same content = same hash = stored once)
    - Immutability (content change = different hash)
    - Deterministic retrieval (hash always finds same content)
    """

    def __init__(self, base_path: str = "/var/maestro/artifacts"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        logger.info(f"ArtifactStore initialized at {self.base_path}")

    def store(
        self,
        file_path: str,
        role: str,
        media_type: str,
        related_contract_id: Optional[str] = None,
        related_node_id: Optional[str] = None,
        related_phase: Optional[str] = None,
        created_by: str = "system",
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> Artifact:
        """
        Store file in content-addressable storage.

        Args:
            file_path: Path to file to store
            role: Artifact role ("deliverable", "evidence", "report", etc.)
            media_type: MIME type
            related_contract_id: Associated contract (if any)
            related_node_id: Associated workflow node (if any)
            related_phase: Associated phase (if any)
            created_by: Creator identifier
            description: Human-readable description
            tags: Optional tags for categorization

        Returns:
            Artifact object with content-addressable path
        """
        # Compute digest
        digest = compute_sha256(file_path)

        # Content-addressable path: {digest[0:2]}/{digest[2:4]}/{digest}
        dest_dir = self.base_path / digest[:2] / digest[2:4]
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_file = dest_dir / digest

        # Copy file if not already stored
        if not dest_file.exists():
            shutil.copy2(file_path, dest_file)
            logger.info(f"Stored artifact {digest[:8]}... ({os.path.getsize(file_path)} bytes)")
        else:
            logger.info(f"Artifact {digest[:8]}... already exists (deduplication)")

        # Get file size
        size_bytes = os.path.getsize(str(dest_file))

        # Create artifact
        artifact = Artifact(
            artifact_id=str(uuid.uuid4()),
            path=str(dest_file.relative_to(self.base_path)),  # Relative path
            digest=digest,
            size_bytes=size_bytes,
            media_type=media_type,
            role=role,
            created_by=created_by,
            related_contract_id=related_contract_id,
            related_node_id=related_node_id,
            related_phase=related_phase,
            description=description,
            tags=tags or []
        )

        # Store metadata
        self._store_metadata(artifact)

        return artifact

    def _store_metadata(self, artifact: Artifact) -> None:
        """Store artifact metadata as JSON file"""
        digest = artifact.digest
        meta_path = self.base_path / digest[:2] / digest[2:4] / f"{digest}.meta"

        with open(meta_path, 'w') as f:
            json.dump(artifact.to_dict(), f, indent=2)

    def retrieve(self, digest: str) -> Optional[Path]:
        """
        Retrieve artifact by digest.

        Args:
            digest: SHA-256 digest of artifact

        Returns:
            Path to artifact file, or None if not found
        """
        artifact_path = self.base_path / digest[:2] / digest[2:4] / digest

        if artifact_path.exists():
            return artifact_path
        else:
            logger.warning(f"Artifact {digest[:8]}... not found")
            return None

    def retrieve_metadata(self, digest: str) -> Optional[Artifact]:
        """
        Retrieve artifact metadata by digest.

        Args:
            digest: SHA-256 digest of artifact

        Returns:
            Artifact object, or None if not found
        """
        meta_path = self.base_path / digest[:2] / digest[2:4] / f"{digest}.meta"

        if meta_path.exists():
            with open(meta_path, 'r') as f:
                data = json.load(f)

            return Artifact.from_dict(data)
        else:
            logger.warning(f"Metadata for {digest[:8]}... not found")
            return None

    def verify_artifact(self, artifact: Artifact) -> bool:
        """Verify artifact integrity"""
        return artifact.verify(str(self.base_path))

    def list_artifacts(
        self,
        role: Optional[str] = None,
        related_contract_id: Optional[str] = None,
        related_phase: Optional[str] = None
    ) -> List[Artifact]:
        """
        List artifacts matching criteria.

        Args:
            role: Filter by role (optional)
            related_contract_id: Filter by contract (optional)
            related_phase: Filter by phase (optional)

        Returns:
            List of matching artifacts
        """
        artifacts = []

        # Walk artifact store
        for digest_dir_1 in self.base_path.iterdir():
            if not digest_dir_1.is_dir() or len(digest_dir_1.name) != 2:
                continue

            for digest_dir_2 in digest_dir_1.iterdir():
                if not digest_dir_2.is_dir() or len(digest_dir_2.name) != 2:
                    continue

                for item in digest_dir_2.iterdir():
                    if item.suffix == ".meta":
                        # Load metadata
                        with open(item, 'r') as f:
                            data = json.load(f)

                        # Apply filters
                        if role and data.get("role") != role:
                            continue

                        if related_contract_id and data.get("related_contract_id") != related_contract_id:
                            continue

                        if related_phase and data.get("related_phase") != related_phase:
                            continue

                        # Create artifact
                        artifact = Artifact.from_dict(data)
                        artifacts.append(artifact)

        return artifacts

    def delete_artifact(self, digest: str) -> bool:
        """
        Delete artifact and its metadata.

        CAUTION: This permanently deletes the artifact!

        Args:
            digest: SHA-256 digest of artifact

        Returns:
            True if deleted, False if not found
        """
        artifact_path = self.base_path / digest[:2] / digest[2:4] / digest
        meta_path = self.base_path / digest[:2] / digest[2:4] / f"{digest}.meta"

        deleted = False

        if artifact_path.exists():
            artifact_path.unlink()
            deleted = True
            logger.info(f"Deleted artifact {digest[:8]}...")

        if meta_path.exists():
            meta_path.unlink()
            logger.info(f"Deleted metadata {digest[:8]}...")

        return deleted

    def get_storage_stats(self) -> dict:
        """
        Get storage statistics.

        Returns:
            Dictionary with storage stats
        """
        total_artifacts = 0
        total_size = 0
        artifacts_by_role = {}

        for artifact in self.list_artifacts():
            total_artifacts += 1
            total_size += artifact.size_bytes

            role = artifact.role
            if role not in artifacts_by_role:
                artifacts_by_role[role] = 0
            artifacts_by_role[role] += 1

        return {
            "total_artifacts": total_artifacts,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "artifacts_by_role": artifacts_by_role,
            "base_path": str(self.base_path)
        }


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "ArtifactStore",
]
