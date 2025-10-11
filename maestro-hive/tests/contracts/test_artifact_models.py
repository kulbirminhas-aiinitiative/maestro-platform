"""
Unit Tests for Artifact Storage Models
Version: 1.0.0

Comprehensive tests for Artifact and ArtifactManifest data models.
"""

import pytest
import tempfile
import os
from pathlib import Path
from datetime import datetime
import json

from contracts.artifacts.models import (
    compute_sha256,
    Artifact,
    ArtifactManifest
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_artifact_file():
    """Create a temporary file for testing"""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as f:
        f.write("Test artifact content for SHA-256 verification")
        temp_path = f.name

    yield temp_path

    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


@pytest.fixture
def temp_artifact_dir():
    """Create temporary directory for artifact storage"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir

    # Cleanup
    import shutil
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def sample_artifact(temp_artifact_file):
    """Create a sample artifact for testing"""
    digest = compute_sha256(temp_artifact_file)
    size = os.path.getsize(temp_artifact_file)

    return Artifact(
        artifact_id="art_001",
        path=f"{digest[:2]}/{digest[2:4]}/{digest}",
        digest=digest,
        size_bytes=size,
        media_type="text/plain",
        role="deliverable",
        created_by="test_agent",
        related_contract_id="contract_001",
        related_node_id="node_001",
        related_phase="implementation",
        description="Test artifact",
        tags=["test", "sample"]
    )


@pytest.fixture
def sample_manifest(sample_artifact):
    """Create a sample manifest for testing"""
    return ArtifactManifest(
        manifest_id="manifest_001",
        contract_id="contract_001",
        node_id="node_001",
        phase="implementation",
        artifacts=[sample_artifact],
        description="Test manifest"
    )


# ============================================================================
# Test compute_sha256()
# ============================================================================

class TestComputeSHA256:
    """Tests for SHA-256 digest computation"""

    def test_compute_sha256_basic(self, temp_artifact_file):
        """Test basic SHA-256 computation"""
        digest = compute_sha256(temp_artifact_file)

        # SHA-256 produces 64-character hex string
        assert len(digest) == 64
        assert all(c in '0123456789abcdef' for c in digest)

    def test_compute_sha256_deterministic(self, temp_artifact_file):
        """Test that same file produces same digest"""
        digest1 = compute_sha256(temp_artifact_file)
        digest2 = compute_sha256(temp_artifact_file)

        assert digest1 == digest2

    def test_compute_sha256_different_content(self, temp_artifact_dir):
        """Test that different content produces different digests"""
        # Create two files with different content
        file1 = os.path.join(temp_artifact_dir, "file1.txt")
        file2 = os.path.join(temp_artifact_dir, "file2.txt")

        with open(file1, 'w') as f:
            f.write("Content A")

        with open(file2, 'w') as f:
            f.write("Content B")

        digest1 = compute_sha256(file1)
        digest2 = compute_sha256(file2)

        assert digest1 != digest2

    def test_compute_sha256_large_file(self, temp_artifact_dir):
        """Test SHA-256 computation with large file (>4096 bytes)"""
        large_file = os.path.join(temp_artifact_dir, "large.txt")

        # Create 10KB file
        with open(large_file, 'w') as f:
            f.write("x" * 10240)

        digest = compute_sha256(large_file)

        assert len(digest) == 64

    def test_compute_sha256_empty_file(self, temp_artifact_dir):
        """Test SHA-256 computation with empty file"""
        empty_file = os.path.join(temp_artifact_dir, "empty.txt")

        with open(empty_file, 'w') as f:
            pass  # Empty file

        digest = compute_sha256(empty_file)

        # SHA-256 of empty file is known constant
        assert digest == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    def test_compute_sha256_binary_file(self, temp_artifact_dir):
        """Test SHA-256 computation with binary file"""
        binary_file = os.path.join(temp_artifact_dir, "binary.bin")

        with open(binary_file, 'wb') as f:
            f.write(b'\x00\x01\x02\x03\x04\x05')

        digest = compute_sha256(binary_file)

        assert len(digest) == 64

    def test_compute_sha256_nonexistent_file(self):
        """Test SHA-256 computation with nonexistent file raises error"""
        with pytest.raises(FileNotFoundError):
            compute_sha256("/nonexistent/file.txt")


# ============================================================================
# Test Artifact
# ============================================================================

class TestArtifact:
    """Tests for Artifact data model"""

    def test_artifact_creation(self, sample_artifact):
        """Test basic artifact creation"""
        assert sample_artifact.artifact_id == "art_001"
        assert sample_artifact.role == "deliverable"
        assert sample_artifact.media_type == "text/plain"
        assert sample_artifact.created_by == "test_agent"
        assert sample_artifact.related_contract_id == "contract_001"
        assert sample_artifact.related_node_id == "node_001"
        assert sample_artifact.related_phase == "implementation"
        assert sample_artifact.description == "Test artifact"
        assert sample_artifact.tags == ["test", "sample"]

    def test_artifact_default_values(self):
        """Test artifact creation with default values"""
        artifact = Artifact(
            artifact_id="art_002",
            path="ab/cd/abcdef",
            digest="abcdef" * 10 + "abcd",  # 64 chars
            size_bytes=1024,
            media_type="application/json",
            role="evidence"
        )

        assert artifact.created_by == "system"
        assert artifact.related_contract_id is None
        assert artifact.related_node_id is None
        assert artifact.related_phase is None
        assert artifact.tags == []
        assert artifact.description == ""
        assert isinstance(artifact.created_at, datetime)

    def test_artifact_all_roles(self):
        """Test artifact with all valid roles"""
        roles = ["deliverable", "evidence", "report", "screenshot", "specification"]

        for role in roles:
            artifact = Artifact(
                artifact_id=f"art_{role}",
                path="path/to/artifact",
                digest="a" * 64,
                size_bytes=100,
                media_type="text/plain",
                role=role
            )
            assert artifact.role == role

    def test_artifact_to_dict(self, sample_artifact):
        """Test artifact serialization to dictionary"""
        data = sample_artifact.to_dict()

        assert data["artifact_id"] == "art_001"
        assert data["digest"] == sample_artifact.digest
        assert data["size_bytes"] == sample_artifact.size_bytes
        assert data["media_type"] == "text/plain"
        assert data["role"] == "deliverable"
        assert data["created_by"] == "test_agent"
        assert data["related_contract_id"] == "contract_001"
        assert data["related_node_id"] == "node_001"
        assert data["related_phase"] == "implementation"
        assert data["tags"] == ["test", "sample"]
        assert data["description"] == "Test artifact"
        assert "created_at" in data

    def test_artifact_from_dict(self, sample_artifact):
        """Test artifact deserialization from dictionary"""
        data = sample_artifact.to_dict()
        artifact = Artifact.from_dict(data)

        assert artifact.artifact_id == sample_artifact.artifact_id
        assert artifact.digest == sample_artifact.digest
        assert artifact.size_bytes == sample_artifact.size_bytes
        assert artifact.media_type == sample_artifact.media_type
        assert artifact.role == sample_artifact.role
        assert artifact.created_by == sample_artifact.created_by
        assert artifact.related_contract_id == sample_artifact.related_contract_id
        assert artifact.related_node_id == sample_artifact.related_node_id
        assert artifact.related_phase == sample_artifact.related_phase
        assert artifact.tags == sample_artifact.tags
        assert artifact.description == sample_artifact.description

    def test_artifact_round_trip_serialization(self, sample_artifact):
        """Test artifact survives round-trip serialization"""
        data = sample_artifact.to_dict()
        artifact = Artifact.from_dict(data)
        data2 = artifact.to_dict()

        assert data == data2

    def test_artifact_verify_success(self, temp_artifact_file, temp_artifact_dir):
        """Test artifact verification with valid file"""
        # Copy file to artifact store structure
        digest = compute_sha256(temp_artifact_file)
        artifact_path = Path(temp_artifact_dir) / digest[:2] / digest[2:4]
        artifact_path.mkdir(parents=True)

        import shutil
        dest_file = artifact_path / digest
        shutil.copy2(temp_artifact_file, dest_file)

        # Create artifact
        artifact = Artifact(
            artifact_id="art_verify",
            path=f"{digest[:2]}/{digest[2:4]}/{digest}",
            digest=digest,
            size_bytes=os.path.getsize(temp_artifact_file),
            media_type="text/plain",
            role="deliverable"
        )

        # Verify
        assert artifact.verify(str(temp_artifact_dir)) is True

    def test_artifact_verify_missing_file(self, sample_artifact, temp_artifact_dir):
        """Test artifact verification with missing file"""
        # Artifact points to non-existent file
        assert sample_artifact.verify(str(temp_artifact_dir)) is False

    def test_artifact_verify_corrupted_file(self, temp_artifact_file, temp_artifact_dir):
        """Test artifact verification with corrupted file"""
        # Compute original digest
        digest = compute_sha256(temp_artifact_file)

        # Copy file
        artifact_path = Path(temp_artifact_dir) / digest[:2] / digest[2:4]
        artifact_path.mkdir(parents=True)

        import shutil
        dest_file = artifact_path / digest
        shutil.copy2(temp_artifact_file, dest_file)

        # Corrupt the file
        with open(dest_file, 'a') as f:
            f.write("CORRUPTED")

        # Create artifact with original digest
        artifact = Artifact(
            artifact_id="art_corrupt",
            path=f"{digest[:2]}/{digest[2:4]}/{digest}",
            digest=digest,
            size_bytes=os.path.getsize(temp_artifact_file),
            media_type="text/plain",
            role="deliverable"
        )

        # Verification should fail
        assert artifact.verify(str(temp_artifact_dir)) is False

    def test_artifact_with_optional_fields_none(self):
        """Test artifact with all optional fields as None"""
        artifact = Artifact(
            artifact_id="art_minimal",
            path="path/to/file",
            digest="a" * 64,
            size_bytes=100,
            media_type="text/plain",
            role="deliverable",
            created_by="agent",
            related_contract_id=None,
            related_node_id=None,
            related_phase=None,
            description="",
            tags=[]
        )

        data = artifact.to_dict()
        restored = Artifact.from_dict(data)

        assert restored.related_contract_id is None
        assert restored.related_node_id is None
        assert restored.related_phase is None


# ============================================================================
# Test ArtifactManifest
# ============================================================================

class TestArtifactManifest:
    """Tests for ArtifactManifest data model"""

    def test_manifest_creation(self, sample_manifest):
        """Test basic manifest creation"""
        assert sample_manifest.manifest_id == "manifest_001"
        assert sample_manifest.contract_id == "contract_001"
        assert sample_manifest.node_id == "node_001"
        assert sample_manifest.phase == "implementation"
        assert len(sample_manifest.artifacts) == 1
        assert sample_manifest.description == "Test manifest"
        assert sample_manifest.manifest_version == "1.0.0"

    def test_manifest_default_values(self):
        """Test manifest creation with default values"""
        manifest = ArtifactManifest(
            manifest_id="manifest_002"
        )

        assert manifest.contract_id is None
        assert manifest.node_id is None
        assert manifest.phase is None
        assert manifest.artifacts == []
        assert manifest.description == ""
        assert manifest.manifest_version == "1.0.0"
        assert isinstance(manifest.created_at, datetime)

    def test_manifest_add_artifact(self, sample_manifest, sample_artifact):
        """Test adding artifact to manifest"""
        initial_count = len(sample_manifest.artifacts)

        new_artifact = Artifact(
            artifact_id="art_002",
            path="path/to/art2",
            digest="b" * 64,
            size_bytes=200,
            media_type="application/json",
            role="evidence"
        )

        sample_manifest.add_artifact(new_artifact)

        assert len(sample_manifest.artifacts) == initial_count + 1
        assert new_artifact in sample_manifest.artifacts

    def test_manifest_get_artifacts_by_role(self):
        """Test filtering artifacts by role"""
        manifest = ArtifactManifest(manifest_id="manifest_filter")

        # Add artifacts with different roles
        manifest.add_artifact(Artifact(
            artifact_id="art_d1",
            path="path1",
            digest="a" * 64,
            size_bytes=100,
            media_type="text/plain",
            role="deliverable"
        ))

        manifest.add_artifact(Artifact(
            artifact_id="art_e1",
            path="path2",
            digest="b" * 64,
            size_bytes=200,
            media_type="text/plain",
            role="evidence"
        ))

        manifest.add_artifact(Artifact(
            artifact_id="art_d2",
            path="path3",
            digest="c" * 64,
            size_bytes=300,
            media_type="text/plain",
            role="deliverable"
        ))

        # Filter by role
        deliverables = manifest.get_artifacts_by_role("deliverable")
        evidence = manifest.get_artifacts_by_role("evidence")
        reports = manifest.get_artifacts_by_role("report")

        assert len(deliverables) == 2
        assert len(evidence) == 1
        assert len(reports) == 0

        assert all(a.role == "deliverable" for a in deliverables)
        assert all(a.role == "evidence" for a in evidence)

    def test_manifest_to_json(self, sample_manifest):
        """Test manifest serialization to JSON"""
        json_str = sample_manifest.to_json()

        # Parse JSON
        data = json.loads(json_str)

        assert data["manifest_id"] == "manifest_001"
        assert data["contract_id"] == "contract_001"
        assert data["node_id"] == "node_001"
        assert data["phase"] == "implementation"
        assert len(data["artifacts"]) == 1
        assert data["manifest_version"] == "1.0.0"
        assert data["description"] == "Test manifest"
        assert "created_at" in data

    def test_manifest_from_json(self, sample_manifest):
        """Test manifest deserialization from JSON"""
        json_str = sample_manifest.to_json()
        manifest = ArtifactManifest.from_json(json_str)

        assert manifest.manifest_id == sample_manifest.manifest_id
        assert manifest.contract_id == sample_manifest.contract_id
        assert manifest.node_id == sample_manifest.node_id
        assert manifest.phase == sample_manifest.phase
        assert len(manifest.artifacts) == len(sample_manifest.artifacts)
        assert manifest.manifest_version == sample_manifest.manifest_version
        assert manifest.description == sample_manifest.description

    def test_manifest_round_trip_json(self, sample_manifest):
        """Test manifest survives round-trip JSON serialization"""
        json_str1 = sample_manifest.to_json()
        manifest = ArtifactManifest.from_json(json_str1)
        json_str2 = manifest.to_json()

        data1 = json.loads(json_str1)
        data2 = json.loads(json_str2)

        assert data1 == data2

    def test_manifest_verify_all_success(self, temp_artifact_file, temp_artifact_dir):
        """Test verifying all artifacts successfully"""
        # Create artifact with valid file
        digest = compute_sha256(temp_artifact_file)
        artifact_path = Path(temp_artifact_dir) / digest[:2] / digest[2:4]
        artifact_path.mkdir(parents=True)

        import shutil
        dest_file = artifact_path / digest
        shutil.copy2(temp_artifact_file, dest_file)

        artifact = Artifact(
            artifact_id="art_v1",
            path=f"{digest[:2]}/{digest[2:4]}/{digest}",
            digest=digest,
            size_bytes=os.path.getsize(temp_artifact_file),
            media_type="text/plain",
            role="deliverable"
        )

        manifest = ArtifactManifest(manifest_id="manifest_v1")
        manifest.add_artifact(artifact)

        all_valid, failures = manifest.verify_all(str(temp_artifact_dir))

        assert all_valid is True
        assert failures == []

    def test_manifest_verify_all_failures(self, sample_manifest, temp_artifact_dir):
        """Test verifying all artifacts with failures"""
        all_valid, failures = sample_manifest.verify_all(str(temp_artifact_dir))

        assert all_valid is False
        assert len(failures) == 1
        assert "art_001" in failures

    def test_manifest_verify_all_mixed(self, temp_artifact_file, temp_artifact_dir):
        """Test verifying artifacts with mixed results"""
        # Create one valid artifact
        digest = compute_sha256(temp_artifact_file)
        artifact_path = Path(temp_artifact_dir) / digest[:2] / digest[2:4]
        artifact_path.mkdir(parents=True)

        import shutil
        dest_file = artifact_path / digest
        shutil.copy2(temp_artifact_file, dest_file)

        valid_artifact = Artifact(
            artifact_id="art_valid",
            path=f"{digest[:2]}/{digest[2:4]}/{digest}",
            digest=digest,
            size_bytes=os.path.getsize(temp_artifact_file),
            media_type="text/plain",
            role="deliverable"
        )

        # Create one invalid artifact
        invalid_artifact = Artifact(
            artifact_id="art_invalid",
            path="path/to/missing",
            digest="z" * 64,
            size_bytes=100,
            media_type="text/plain",
            role="evidence"
        )

        manifest = ArtifactManifest(manifest_id="manifest_mixed")
        manifest.add_artifact(valid_artifact)
        manifest.add_artifact(invalid_artifact)

        all_valid, failures = manifest.verify_all(str(temp_artifact_dir))

        assert all_valid is False
        assert len(failures) == 1
        assert "art_invalid" in failures
        assert "art_valid" not in failures

    def test_manifest_empty_artifacts(self):
        """Test manifest with no artifacts"""
        manifest = ArtifactManifest(manifest_id="manifest_empty")

        all_valid, failures = manifest.verify_all("/tmp")

        assert all_valid is True
        assert failures == []

    def test_manifest_with_multiple_artifacts(self):
        """Test manifest with multiple artifacts"""
        manifest = ArtifactManifest(manifest_id="manifest_multi")

        for i in range(5):
            manifest.add_artifact(Artifact(
                artifact_id=f"art_{i}",
                path=f"path/{i}",
                digest=f"{i}" * 64,
                size_bytes=100 * i,
                media_type="text/plain",
                role="deliverable" if i % 2 == 0 else "evidence"
            ))

        assert len(manifest.artifacts) == 5

        deliverables = manifest.get_artifacts_by_role("deliverable")
        evidence = manifest.get_artifacts_by_role("evidence")

        assert len(deliverables) == 3
        assert len(evidence) == 2


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_artifact_with_special_characters_in_description(self):
        """Test artifact with special characters in description"""
        artifact = Artifact(
            artifact_id="art_special",
            path="path/to/file",
            digest="a" * 64,
            size_bytes=100,
            media_type="text/plain",
            role="deliverable",
            description="Test with 'quotes', \"double quotes\", and\nnewlines"
        )

        data = artifact.to_dict()
        restored = Artifact.from_dict(data)

        assert restored.description == artifact.description

    def test_artifact_with_unicode_in_tags(self):
        """Test artifact with Unicode characters in tags"""
        artifact = Artifact(
            artifact_id="art_unicode",
            path="path/to/file",
            digest="a" * 64,
            size_bytes=100,
            media_type="text/plain",
            role="deliverable",
            tags=["测试", "テスト", "🎉"]
        )

        data = artifact.to_dict()
        restored = Artifact.from_dict(data)

        assert restored.tags == artifact.tags

    def test_manifest_json_with_empty_optional_fields(self):
        """Test manifest JSON serialization with empty optional fields"""
        manifest = ArtifactManifest(
            manifest_id="manifest_empty_fields",
            contract_id=None,
            node_id=None,
            phase=None
        )

        json_str = manifest.to_json()
        data = json.loads(json_str)

        assert data["contract_id"] is None
        assert data["node_id"] is None
        assert data["phase"] is None

    def test_artifact_large_file_size(self):
        """Test artifact with very large file size"""
        large_size = 10 * 1024 * 1024 * 1024  # 10 GB

        artifact = Artifact(
            artifact_id="art_large",
            path="path/to/large",
            digest="a" * 64,
            size_bytes=large_size,
            media_type="application/octet-stream",
            role="deliverable"
        )

        assert artifact.size_bytes == large_size

        data = artifact.to_dict()
        restored = Artifact.from_dict(data)

        assert restored.size_bytes == large_size

    def test_manifest_with_many_artifacts(self):
        """Test manifest with many artifacts"""
        manifest = ArtifactManifest(manifest_id="manifest_many")

        # Add 100 artifacts
        for i in range(100):
            manifest.add_artifact(Artifact(
                artifact_id=f"art_{i:03d}",
                path=f"path/{i}",
                digest=f"{i:064d}",
                size_bytes=i * 100,
                media_type="text/plain",
                role="deliverable"
            ))

        assert len(manifest.artifacts) == 100

        # Test JSON serialization
        json_str = manifest.to_json()
        restored = ArtifactManifest.from_json(json_str)

        assert len(restored.artifacts) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
