# Artifact Storage Standard
## Content-Addressable Artifact Management

**Version:** 1.0.0
**Date:** 2025-10-11
**Status:** Phase 1 Complete

---

## Executive Summary

The **Artifact Storage Standard** defines a content-addressable storage system for contract artifacts with integrity verification, manifest-based organization, and deterministic retrieval.

**Problem Solved**: Arbitrary file paths in contract examples
- Cannot verify artifact integrity
- Cannot implement caching reliably
- No way to address artifacts in distributed systems
- Lost artifacts

**Solution**: Content-addressable storage with SHA-256 digests and manifest files

---

## Table of Contents

1. [Core Concepts](#core-concepts)
2. [Data Models](#data-models)
3. [ArtifactStore Implementation](#artifactstore-implementation)
4. [Content-Addressable Storage](#content-addressable-storage)
5. [Manifest Management](#manifest-management)
6. [Integration Guide](#integration-guide)
7. [Examples](#examples)
8. [Best Practices](#best-practices)

---

## Core Concepts

### Content-Addressable Storage

Traditional storage:
```
/tmp/design.png  ← Arbitrary path, can change
/var/uploads/api_spec.yaml  ← No integrity verification
```

Content-addressable storage:
```
artifacts/ac/f3/acf3d19b8c7e2f1a5b4d3c2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0
                ↑          ↑
                |          Full SHA-256 digest (content hash)
                First 2 chars (directory sharding)
```

**Benefits**:
- ✅ Content verification (digest mismatch = corruption detected)
- ✅ Deduplication (same content = same hash = stored once)
- ✅ Immutability (content change = different hash)
- ✅ Deterministic retrieval (hash always finds same content)
- ✅ Distributed-friendly (copy artifacts by hash)

### Artifact Roles

Artifacts serve different purposes:

- **deliverable**: Primary output of a contract (e.g., Figma export, built binary)
- **evidence**: Proof of verification (e.g., test report, screenshot comparison)
- **report**: Summary or analysis (e.g., coverage report, security scan)
- **screenshot**: Visual output for comparison
- **specification**: Input specification (e.g., OpenAPI spec, design file)

---

## Data Models

### Artifact

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import hashlib
import os

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
    tags: list[str] = field(default_factory=list)
    description: str = ""

    def verify(self, artifact_store_base: str = "/var/maestro/artifacts") -> bool:
        """
        Verify artifact integrity by checking digest.

        Args:
            artifact_store_base: Base path of artifact store

        Returns:
            True if digest matches file content, False otherwise
        """
        from pathlib import Path

        full_path = Path(artifact_store_base) / self.path

        if not full_path.exists():
            return False

        # Compute SHA-256 of file
        actual_digest = compute_sha256(str(full_path))

        return actual_digest == self.digest

    def to_dict(self) -> dict:
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


def compute_sha256(file_path: str) -> str:
    """Compute SHA-256 digest of file"""
    sha256_hash = hashlib.sha256()

    with open(file_path, "rb") as f:
        # Read in chunks to handle large files
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)

    return sha256_hash.hexdigest()
```

### ArtifactManifest

```python
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
    artifacts: list[Artifact] = field(default_factory=list)

    # ===== Metadata =====
    created_at: datetime = field(default_factory=datetime.utcnow)
    manifest_version: str = "1.0.0"
    description: str = ""

    def add_artifact(self, artifact: Artifact) -> None:
        """Add artifact to manifest"""
        self.artifacts.append(artifact)

    def get_artifacts_by_role(self, role: str) -> list[Artifact]:
        """Get all artifacts with specified role"""
        return [a for a in self.artifacts if a.role == role]

    def verify_all(self, artifact_store_base: str = "/var/maestro/artifacts") -> tuple[bool, list[str]]:
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
        import json

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
        import json
        from datetime import datetime

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
            artifact = Artifact(
                artifact_id=artifact_data["artifact_id"],
                path=artifact_data["path"],
                digest=artifact_data["digest"],
                size_bytes=artifact_data["size_bytes"],
                media_type=artifact_data["media_type"],
                role=artifact_data["role"],
                created_by=artifact_data.get("created_by", "system"),
                related_contract_id=artifact_data.get("related_contract_id"),
                related_node_id=artifact_data.get("related_node_id"),
                related_phase=artifact_data.get("related_phase"),
                tags=artifact_data.get("tags", []),
                description=artifact_data.get("description", "")
            )

            if "created_at" in artifact_data:
                artifact.created_at = datetime.fromisoformat(artifact_data["created_at"])

            manifest.add_artifact(artifact)

        return manifest
```

---

## ArtifactStore Implementation

### ArtifactStore Class

```python
from pathlib import Path
import shutil
import uuid
import logging

logger = logging.getLogger(__name__)


class ArtifactStore:
    """
    Content-addressable artifact storage.

    Storage structure:
        /var/maestro/artifacts/
            {digest[0:2]}/
                {digest[2:4]}/
                    {full_digest}  ← Actual file
                    {full_digest}.meta  ← Metadata (JSON)
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
        tags: Optional[list[str]] = None
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
        size_bytes = os.path.getsize(dest_file)

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
        import json

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
        import json

        meta_path = self.base_path / digest[:2] / digest[2:4] / f"{digest}.meta"

        if meta_path.exists():
            with open(meta_path, 'r') as f:
                data = json.load(f)

            return Artifact(
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
        else:
            logger.warning(f"Metadata for {digest[:8]}... not found")
            return None

    def verify_artifact(self, artifact: Artifact) -> bool:
        """Verify artifact integrity"""
        return artifact.verify(str(self.base_path))

    def list_artifacts(
        self,
        role: Optional[str] = None,
        related_contract_id: Optional[str] = None
    ) -> list[Artifact]:
        """
        List artifacts matching criteria.

        Args:
            role: Filter by role (optional)
            related_contract_id: Filter by contract (optional)

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
                            import json
                            data = json.load(f)

                        # Apply filters
                        if role and data.get("role") != role:
                            continue

                        if related_contract_id and data.get("related_contract_id") != related_contract_id:
                            continue

                        # Create artifact
                        artifact = Artifact(**data)
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
```

---

## Content-Addressable Storage

### Storage Layout

```
/var/maestro/artifacts/
├── ac/
│   └── f3/
│       ├── acf3d19b8c7e2f1a5b4d3c2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0
│       └── acf3d19b8c7e2f1a5b4d3c2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0.meta
├── 12/
│   └── 34/
│       ├── 1234567890abcdef...
│       └── 1234567890abcdef....meta
└── ab/
    └── cd/
        ├── abcdef1234567890...
        └── abcdef1234567890....meta
```

### Why Sharding (Two-Level Directories)?

**Problem**: Storing millions of files in a single directory causes performance issues.

**Solution**: Shard by first 4 characters of digest:
- First 2 chars: First-level directory (256 possibilities: 00-ff)
- Next 2 chars: Second-level directory (256 possibilities: 00-ff)
- **Total**: Up to 65,536 top-level shards

**Benefit**: Each directory contains manageable number of files.

### Metadata Files

Each artifact has a `.meta` JSON file with full metadata:

```json
{
  "artifact_id": "550e8400-e29b-41d4-a716-446655440000",
  "path": "ac/f3/acf3d19b8c7e2f1a...",
  "digest": "acf3d19b8c7e2f1a5b4d3c2e1f0a9b8c7d6e5f4a3b2c1d0e9f8a7b6c5d4e3f2a1b0",
  "size_bytes": 245678,
  "media_type": "application/json",
  "role": "deliverable",
  "created_at": "2025-10-11T14:30:00Z",
  "created_by": "ux_designer",
  "related_contract_id": "UX_LOGIN_001",
  "related_phase": "design",
  "tags": ["figma", "login-form"],
  "description": "Figma export for LoginForm component"
}
```

---

## Manifest Management

### Creating Manifests

```python
# Create manifest for a contract
manifest = ArtifactManifest(
    manifest_id="manifest_design_phase_001",
    contract_id="UX_LOGIN_001",
    phase="design",
    description="Design artifacts for authentication feature"
)

# Add artifacts
artifact1 = artifact_store.store(
    file_path="/tmp/figma_export.json",
    role="deliverable",
    media_type="application/json",
    related_contract_id="UX_LOGIN_001"
)

manifest.add_artifact(artifact1)

# Save manifest
manifest_json = manifest.to_json()
with open("/var/maestro/manifests/manifest_design_phase_001.json", 'w') as f:
    f.write(manifest_json)
```

### Loading Manifests

```python
# Load manifest
with open("/var/maestro/manifests/manifest_design_phase_001.json", 'r') as f:
    manifest_json = f.read()

manifest = ArtifactManifest.from_json(manifest_json)

# Verify all artifacts
all_valid, failures = manifest.verify_all()

if all_valid:
    print("✅ All artifacts verified")
else:
    print(f"❌ {len(failures)} artifacts failed verification: {failures}")
```

---

## Integration Guide

### Step 1: Initialize ArtifactStore

```python
# In system initialization
artifact_store = ArtifactStore(base_path="/var/maestro/artifacts")
```

### Step 2: Store Artifacts During Phase Execution

```python
# After phase produces artifacts

# Store design file
design_artifact = artifact_store.store(
    file_path="/tmp/design_output/figma_export.json",
    role="deliverable",
    media_type="application/json",
    related_contract_id="UX_LOGIN_001",
    related_phase="design",
    created_by="ux_designer",
    description="Figma export for LoginForm",
    tags=["figma", "login", "design"]
)

print(f"Stored artifact: {design_artifact.artifact_id}")
print(f"Digest: {design_artifact.digest}")
print(f"Path: {design_artifact.path}")
```

### Step 3: Create Manifest for Phase

```python
# Create manifest for phase
manifest = ArtifactManifest(
    manifest_id=f"manifest_{phase_name}_{int(time.time())}",
    phase=phase_name,
    description=f"Artifacts from {phase_name} phase"
)

# Add all phase artifacts
for artifact in phase_artifacts:
    manifest.add_artifact(artifact)

# Save manifest
manifest_path = f"/var/maestro/manifests/{manifest.manifest_id}.json"
with open(manifest_path, 'w') as f:
    f.write(manifest.to_json())
```

### Step 4: Pass Manifest in HandoffSpec

```python
# Create handoff with manifest
handoff_spec = HandoffSpec(
    handoff_id="handoff_design_impl_001",
    from_phase="design",
    to_phase="implementation",
    tasks=[...],
    input_artifacts=manifest,  # ← Pass manifest
    acceptance_criteria=[...]
)
```

### Step 5: Next Phase Retrieves Artifacts

```python
# In next phase, retrieve artifacts from manifest
for artifact in handoff_spec.input_artifacts.artifacts:
    # Get file path
    file_path = artifact_store.retrieve(artifact.digest)

    # Verify integrity
    if artifact.verify(str(artifact_store.base_path)):
        print(f"✅ Artifact {artifact.artifact_id} verified")
        # Use artifact...
    else:
        print(f"❌ Artifact {artifact.artifact_id} verification failed!")
```

---

## Examples

### Example 1: Storing Design Artifacts

```python
artifact_store = ArtifactStore()

# Store Figma export
figma_artifact = artifact_store.store(
    file_path="/tmp/figma_export.json",
    role="deliverable",
    media_type="application/json",
    related_contract_id="UX_LOGIN_001",
    related_phase="design",
    created_by="ux_designer",
    description="Figma export for LoginForm component",
    tags=["figma", "login-form", "material-ui"]
)

# Store design tokens
tokens_artifact = artifact_store.store(
    file_path="/tmp/design_tokens.json",
    role="specification",
    media_type="application/json",
    related_contract_id="UX_LOGIN_001",
    related_phase="design",
    created_by="ux_designer",
    description="Material-UI design tokens",
    tags=["design-tokens", "material-ui"]
)

# Create manifest
manifest = ArtifactManifest(
    manifest_id="manifest_design_001",
    contract_id="UX_LOGIN_001",
    phase="design",
    description="Design artifacts for LoginForm"
)

manifest.add_artifact(figma_artifact)
manifest.add_artifact(tokens_artifact)

# Save manifest
with open("/var/maestro/manifests/manifest_design_001.json", 'w') as f:
    f.write(manifest.to_json())

print(f"Stored {len(manifest.artifacts)} artifacts")
print(f"Manifest: {manifest.manifest_id}")
```

### Example 2: Storing Test Evidence

```python
# Store test report
test_report_artifact = artifact_store.store(
    file_path="/tmp/test_report.html",
    role="evidence",
    media_type="text/html",
    related_contract_id="TEST_AUTH_001",
    related_phase="testing",
    created_by="qa_engineer",
    description="Integration test report for authentication",
    tags=["test-report", "integration", "auth"]
)

# Store coverage report
coverage_artifact = artifact_store.store(
    file_path="/tmp/coverage.json",
    role="report",
    media_type="application/json",
    related_contract_id="TEST_AUTH_001",
    related_phase="testing",
    created_by="qa_engineer",
    description="Code coverage report (85%)",
    tags=["coverage", "metrics"]
)

# Store screenshot for visual testing
screenshot_artifact = artifact_store.store(
    file_path="/tmp/login_screenshot.png",
    role="screenshot",
    media_type="image/png",
    related_contract_id="UX_LOGIN_001",
    related_phase="testing",
    created_by="qa_engineer",
    description="Screenshot of implemented LoginForm for comparison",
    tags=["screenshot", "visual-testing"]
)
```

### Example 3: Verifying Artifact Integrity

```python
# Load manifest
with open("/var/maestro/manifests/manifest_design_001.json", 'r') as f:
    manifest = ArtifactManifest.from_json(f.read())

# Verify all artifacts
all_valid, failures = manifest.verify_all(artifact_store_base="/var/maestro/artifacts")

if all_valid:
    print("✅ All artifacts passed integrity check")

    # Retrieve and use artifacts
    for artifact in manifest.artifacts:
        file_path = artifact_store.retrieve(artifact.digest)
        print(f"Artifact {artifact.artifact_id}: {file_path}")
else:
    print(f"❌ {len(failures)} artifacts failed verification:")
    for failed_id in failures:
        print(f"  - {failed_id}")
```

---

## Best Practices

### 1. Always Verify Integrity

✅ **Good**: Verify before using
```python
if artifact.verify(artifact_store_base):
    use_artifact(artifact)
else:
    logger.error(f"Artifact {artifact.artifact_id} verification failed!")
```

❌ **Bad**: Trust without verification
```python
use_artifact(artifact)  # No verification!
```

### 2. Use Manifests for Organization

✅ **Good**: Group related artifacts
```python
manifest = ArtifactManifest(contract_id="UX_LOGIN_001", phase="design")
manifest.add_artifact(artifact1)
manifest.add_artifact(artifact2)
```

❌ **Bad**: Loose artifact references
```python
artifacts = [artifact1, artifact2]  # No organization
```

### 3. Set Appropriate Roles

✅ **Good**: Clear roles
```python
artifact_store.store(..., role="deliverable")  # Primary output
artifact_store.store(..., role="evidence")     # Proof
```

❌ **Bad**: Generic role
```python
artifact_store.store(..., role="file")  # Unclear purpose
```

### 4. Add Descriptive Metadata

✅ **Good**: Rich metadata
```python
artifact_store.store(
    ...,
    description="Figma export for LoginForm component with Material-UI styling",
    tags=["figma", "login-form", "material-ui", "wcag-aa"]
)
```

❌ **Bad**: Missing metadata
```python
artifact_store.store(...)  # No description or tags
```

### 5. Clean Up Temporary Files

✅ **Good**: Remove source after storing
```python
artifact = artifact_store.store(file_path="/tmp/temp_file.json", ...)
os.remove("/tmp/temp_file.json")  # Clean up
```

---

## Summary

The Artifact Storage Standard provides:

- ✅ Content-addressable storage with SHA-256 digests
- ✅ Automatic integrity verification
- ✅ Deduplication (same content = single storage)
- ✅ Manifest-based organization
- ✅ Rich metadata with roles and tags
- ✅ Deterministic retrieval
- ✅ Distributed-system friendly

**Integration Points**:
- HandoffSpec (phase-to-phase transfers)
- VerificationResult (evidence storage)
- Contract fulfillment (deliverable storage)

**Related Documents**:
- `HANDOFF_SPEC.md` - Uses ArtifactManifest for handoffs
- `PROTOCOL_CORRECTIONS.md` - Section 6 (Artifact Standardization)
- `UNIVERSAL_CONTRACT_PROTOCOL.md` - Artifact references in contracts

---

**Document Version:** 1.0.0
**Last Updated:** 2025-10-11
**Status:** Ready for implementation
