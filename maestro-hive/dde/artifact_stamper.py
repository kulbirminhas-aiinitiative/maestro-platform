"""
DDE Artifact Stamper

Provides artifact stamping and metadata management for DDE (Dependency-Driven Execution).
All artifacts are stamped with iteration context, node information, and cryptographic hashes.

Convention: {IterationID}/{NodeID}/{ArtifactName}
"""

import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict


@dataclass
class ArtifactMetadata:
    """Metadata for a stamped artifact"""
    iteration_id: str
    node_id: str
    artifact_name: str
    capability: str
    contract_version: Optional[str]
    original_path: str
    stamped_path: str
    sha256: str
    size_bytes: int
    timestamp: str
    labels: Dict[str, str]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ArtifactMetadata':
        """Create from dictionary"""
        return cls(**data)


class ArtifactStamper:
    """
    Stamps artifacts with metadata and manages artifact storage.

    All artifacts are:
    - Copied to a canonical location
    - Tagged with iteration and node context
    - Hashed for integrity verification
    - Labeled with capability and contract information
    """

    def __init__(self, base_path: str = "artifacts"):
        """
        Initialize artifact stamper.

        Args:
            base_path: Base directory for artifact storage
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def stamp_artifact(
        self,
        iteration_id: str,
        node_id: str,
        artifact_path: str,
        capability: str,
        contract_version: Optional[str] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> ArtifactMetadata:
        """
        Stamp artifact with metadata and move to canonical location.

        Args:
            iteration_id: Iteration identifier (e.g., "Iter-20251012-1430-001")
            node_id: Node identifier (e.g., "IF.AuthAPI")
            artifact_path: Path to original artifact
            capability: Capability that produced this artifact
            contract_version: Contract version (for interface nodes)
            labels: Additional labels for artifact

        Returns:
            ArtifactMetadata object with stamping details

        Raises:
            FileNotFoundError: If artifact_path doesn't exist
            ValueError: If iteration_id or node_id format is invalid
        """
        # Validate inputs
        if not Path(artifact_path).exists():
            raise FileNotFoundError(f"Artifact not found: {artifact_path}")

        if not iteration_id.startswith("Iter-"):
            raise ValueError(f"Invalid iteration_id format: {iteration_id}")

        # Create stamped path
        artifact_name = Path(artifact_path).name
        stamped_dir = self.base_path / iteration_id / node_id
        stamped_dir.mkdir(parents=True, exist_ok=True)
        stamped_path = stamped_dir / artifact_name

        # Copy artifact
        shutil.copy2(artifact_path, stamped_path)

        # Compute hash
        sha256 = self._compute_sha256(stamped_path)

        # Get file size
        size_bytes = stamped_path.stat().st_size

        # Create metadata
        metadata = ArtifactMetadata(
            iteration_id=iteration_id,
            node_id=node_id,
            artifact_name=artifact_name,
            capability=capability,
            contract_version=contract_version,
            original_path=str(artifact_path),
            stamped_path=str(stamped_path),
            sha256=sha256,
            size_bytes=size_bytes,
            timestamp=datetime.utcnow().isoformat() + "Z",
            labels=labels or {}
        )

        # Write metadata file
        metadata_path = stamped_path.with_suffix(stamped_path.suffix + ".meta.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata.to_dict(), f, indent=2)

        return metadata

    def verify_artifact(self, stamped_path: str) -> bool:
        """
        Verify artifact integrity using stored hash.

        Args:
            stamped_path: Path to stamped artifact

        Returns:
            True if artifact matches stored hash, False otherwise
        """
        stamped_path = Path(stamped_path)
        metadata_path = stamped_path.with_suffix(stamped_path.suffix + ".meta.json")

        if not metadata_path.exists():
            return False

        # Load metadata
        with open(metadata_path) as f:
            metadata = ArtifactMetadata.from_dict(json.load(f))

        # Compute current hash
        current_hash = self._compute_sha256(stamped_path)

        # Compare
        return current_hash == metadata.sha256

    def get_artifact_metadata(self, stamped_path: str) -> Optional[ArtifactMetadata]:
        """
        Load artifact metadata.

        Args:
            stamped_path: Path to stamped artifact

        Returns:
            ArtifactMetadata if found, None otherwise
        """
        stamped_path = Path(stamped_path)
        metadata_path = stamped_path.with_suffix(stamped_path.suffix + ".meta.json")

        if not metadata_path.exists():
            return None

        with open(metadata_path) as f:
            return ArtifactMetadata.from_dict(json.load(f))

    def list_artifacts(
        self,
        iteration_id: Optional[str] = None,
        node_id: Optional[str] = None
    ) -> List[ArtifactMetadata]:
        """
        List artifacts with optional filtering.

        Args:
            iteration_id: Filter by iteration (optional)
            node_id: Filter by node (optional)

        Returns:
            List of ArtifactMetadata objects
        """
        artifacts = []

        # Build search path
        if iteration_id and node_id:
            search_path = self.base_path / iteration_id / node_id
        elif iteration_id:
            search_path = self.base_path / iteration_id
        else:
            search_path = self.base_path

        # Find all metadata files
        if search_path.exists():
            for meta_file in search_path.rglob("*.meta.json"):
                with open(meta_file) as f:
                    metadata = ArtifactMetadata.from_dict(json.load(f))
                    artifacts.append(metadata)

        return artifacts

    def get_artifact_path(
        self,
        iteration_id: str,
        node_id: str,
        artifact_name: str
    ) -> Optional[Path]:
        """
        Get path to a stamped artifact.

        Args:
            iteration_id: Iteration identifier
            node_id: Node identifier
            artifact_name: Name of artifact

        Returns:
            Path to artifact if it exists, None otherwise
        """
        artifact_path = self.base_path / iteration_id / node_id / artifact_name
        return artifact_path if artifact_path.exists() else None

    def cleanup_iteration(self, iteration_id: str) -> int:
        """
        Remove all artifacts for an iteration.

        Args:
            iteration_id: Iteration identifier

        Returns:
            Number of artifacts removed
        """
        iteration_path = self.base_path / iteration_id

        if not iteration_path.exists():
            return 0

        # Count artifacts (exclude metadata files)
        artifact_count = len([
            f for f in iteration_path.rglob("*")
            if f.is_file() and not f.name.endswith(".meta.json")
        ])

        # Remove directory
        shutil.rmtree(iteration_path)

        return artifact_count

    @staticmethod
    def _compute_sha256(file_path: Path) -> str:
        """
        Compute SHA256 hash of a file.

        Args:
            file_path: Path to file

        Returns:
            Hex-encoded SHA256 hash
        """
        sha256_hash = hashlib.sha256()

        with open(file_path, "rb") as f:
            # Read in 64KB chunks
            for chunk in iter(lambda: f.read(65536), b""):
                sha256_hash.update(chunk)

        return sha256_hash.hexdigest()


# Example usage
if __name__ == "__main__":
    # Create stamper
    stamper = ArtifactStamper(base_path="artifacts")

    # Example: Stamp an artifact
    # metadata = stamper.stamp_artifact(
    #     iteration_id="Iter-20251012-1430-001",
    #     node_id="IF.AuthAPI",
    #     artifact_path="/path/to/openapi.yaml",
    #     capability="Architecture:APIDesign",
    #     contract_version="v1.2",
    #     labels={"type": "api_spec", "format": "openapi3"}
    # )
    # print(f"Artifact stamped: {metadata.stamped_path}")
    # print(f"SHA256: {metadata.sha256}")

    pass
