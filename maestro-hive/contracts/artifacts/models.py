"""
Artifact Storage Models
Version: 1.0.0

Data models for content-addressable artifact storage with integrity verification.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import hashlib
import json


def compute_sha256(file_path: str) -> str:
    """
    Compute SHA-256 digest of file.

    Args:
        file_path: Path to file

    Returns:
        SHA-256 hex digest
    """
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        # Read in chunks to handle large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()


@dataclass
class Artifact:
    """
    Content-addressable artifact with verification.
    Immutable once stored (content change = new artifact).
    """

    # ===== Identity =====
    artifact_id: str  # UUID (unique identifier)

    # ===== Storage =====
    path: str  # Relative path in artifact store (content-addressable)

    # ===== Content Verification =====
    digest: str  # SHA-256 hash of content
    size_bytes: int  # File size in bytes

    # ===== Metadata =====
    media_type: str  # MIME type (e.g., "application/json", "image/png")
    role: str  # "deliverable", "evidence", "report", "screenshot", "specification"

    # ===== Timestamps =====
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"  # Agent or persona that created it

    # ===== Relationships =====
    related_contract_id: Optional[str] = None  # Contract this artifact belongs to
    related_node_id: Optional[str] = None  # Workflow node that produced it
    related_phase: Optional[str] = None  # Phase that produced it (e.g., "design")

    # ===== Additional Metadata =====
    tags: List[str] = field(default_factory=list)
    description: str = ""

    def verify(self, artifact_store_base: str = "/var/maestro/artifacts") -> bool:
        """
        Verify artifact integrity by checking digest.

        Args:
            artifact_store_base: Base path of artifact store

        Returns:
            True if digest matches file content, False otherwise
        """
        full_path = Path(artifact_store_base) / self.path

        if not full_path.exists():
            return False

        # Compute SHA-256 of file
        actual_digest = compute_sha256(str(full_path))

        return actual_digest == self.digest

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "artifact_id": self.artifact_id,
            "path": self.path,
            "digest": self.digest,
            "size_bytes": self.size_bytes,
            "media_type": self.media_type,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "related_contract_id": self.related_contract_id,
            "related_node_id": self.related_node_id,
            "related_phase": self.related_phase,
            "tags": self.tags,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Artifact':
        """Deserialize from dictionary"""
        artifact = cls(
            artifact_id=data["artifact_id"],
            path=data["path"],
            digest=data["digest"],
            size_bytes=data["size_bytes"],
            media_type=data["media_type"],
            role=data["role"],
            created_by=data.get("created_by", "system"),
            related_contract_id=data.get("related_contract_id"),
            related_node_id=data.get("related_node_id"),
            related_phase=data.get("related_phase"),
            tags=data.get("tags", []),
            description=data.get("description", "")
        )

        # Parse created_at
        if "created_at" in data:
            artifact.created_at = datetime.fromisoformat(data["created_at"])

        return artifact


@dataclass
class ArtifactManifest:
    """
    Manifest listing all artifacts for a contract, phase, or workflow node.
    Provides grouped access to artifacts with verification.
    """

    # ===== Identity =====
    manifest_id: str  # Unique identifier

    # ===== Association =====
    contract_id: Optional[str] = None  # Associated contract
    node_id: Optional[str] = None  # Associated workflow node
    phase: Optional[str] = None  # Associated phase

    # ===== Artifacts =====
    artifacts: List[Artifact] = field(default_factory=list)

    # ===== Metadata =====
    created_at: datetime = field(default_factory=datetime.utcnow)
    manifest_version: str = "1.0.0"
    description: str = ""

    def add_artifact(self, artifact: Artifact) -> None:
        """Add artifact to manifest"""
        self.artifacts.append(artifact)

    def get_artifacts_by_role(self, role: str) -> List[Artifact]:
        """Get all artifacts with specified role"""
        return [a for a in self.artifacts if a.role == role]

    def verify_all(self, artifact_store_base: str = "/var/maestro/artifacts") -> Tuple[bool, List[str]]:
        """
        Verify integrity of all artifacts in manifest.

        Returns:
            (all_valid, list_of_failed_artifact_ids)
        """
        failures = []

        for artifact in self.artifacts:
            if not artifact.verify(artifact_store_base):
                failures.append(artifact.artifact_id)

        return len(failures) == 0, failures

    def to_json(self) -> str:
        """Serialize manifest to JSON"""
        return json.dumps({
            "manifest_id": self.manifest_id,
            "contract_id": self.contract_id,
            "node_id": self.node_id,
            "phase": self.phase,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "created_at": self.created_at.isoformat(),
            "manifest_version": self.manifest_version,
            "description": self.description
        }, indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> 'ArtifactManifest':
        """Deserialize manifest from JSON"""
        data = json.loads(json_str)

        manifest = cls(
            manifest_id=data["manifest_id"],
            contract_id=data.get("contract_id"),
            node_id=data.get("node_id"),
            phase=data.get("phase"),
            manifest_version=data.get("manifest_version", "1.0.0"),
            description=data.get("description", "")
        )

        # Parse created_at
        if "created_at" in data:
            manifest.created_at = datetime.fromisoformat(data["created_at"])

        # Parse artifacts
        for artifact_data in data.get("artifacts", []):
            artifact = Artifact.from_dict(artifact_data)
            manifest.add_artifact(artifact)

        return manifest


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "compute_sha256",
    "Artifact",
    "ArtifactManifest",
]
