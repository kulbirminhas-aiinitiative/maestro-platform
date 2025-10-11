"""
Integration Tests for Artifact Storage System
Version: 1.0.0

End-to-end tests for the complete artifact storage workflow.
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
import shutil

from contracts.artifacts.store import ArtifactStore
from contracts.artifacts.models import Artifact, ArtifactManifest, compute_sha256


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def temp_artifact_store():
    """Create temporary artifact store directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir

    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def artifact_store(temp_artifact_store):
    """Create ArtifactStore instance"""
    return ArtifactStore(base_path=temp_artifact_store)


@pytest.fixture
def test_files(temp_artifact_store):
    """Create multiple test files for integration testing"""
    files = {}

    # Design document
    design_file = os.path.join(temp_artifact_store, "design_doc.md")
    with open(design_file, 'w') as f:
        f.write("# Login Form Design\n\nUser interface specification for login form.")
    files['design'] = design_file

    # Implementation code
    code_file = os.path.join(temp_artifact_store, "login_form.py")
    with open(code_file, 'w') as f:
        f.write("def login(username, password):\n    return authenticate(username, password)")
    files['code'] = code_file

    # Test results
    test_results_file = os.path.join(temp_artifact_store, "test_results.json")
    with open(test_results_file, 'w') as f:
        json.dump({"tests_run": 25, "passed": 25, "failed": 0}, f)
    files['test_results'] = test_results_file

    # Screenshot
    screenshot_file = os.path.join(temp_artifact_store, "screenshot.png")
    with open(screenshot_file, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n' + b'\x00' * 100)  # Fake PNG header
    files['screenshot'] = screenshot_file

    # Report
    report_file = os.path.join(temp_artifact_store, "qa_report.md")
    with open(report_file, 'w') as f:
        f.write("# QA Report\n\nAll tests passed. Ready for deployment.")
    files['report'] = report_file

    yield files

    # Cleanup
    for file_path in files.values():
        if os.path.exists(file_path):
            os.unlink(file_path)


# ============================================================================
# Integration Test: Complete Contract Workflow
# ============================================================================

class TestCompleteContractWorkflow:
    """Test complete contract workflow with artifacts"""

    def test_end_to_end_workflow(self, artifact_store, test_files):
        """Test complete workflow from design to deployment"""

        # PHASE 1: DESIGN
        # Store design document
        design_artifact = artifact_store.store(
            file_path=test_files['design'],
            role="specification",
            media_type="text/markdown",
            related_contract_id="contract_login_001",
            related_phase="design",
            created_by="ux_designer",
            description="Login form design specification",
            tags=["design", "login", "ux"]
        )

        assert design_artifact is not None
        assert design_artifact.related_phase == "design"

        # PHASE 2: IMPLEMENTATION
        # Store implementation code
        code_artifact = artifact_store.store(
            file_path=test_files['code'],
            role="deliverable",
            media_type="text/x-python",
            related_contract_id="contract_login_001",
            related_phase="implementation",
            created_by="backend_developer",
            description="Login form implementation",
            tags=["code", "login", "backend"]
        )

        assert code_artifact is not None
        assert code_artifact.related_phase == "implementation"

        # PHASE 3: QA
        # Store test results and screenshot
        test_artifact = artifact_store.store(
            file_path=test_files['test_results'],
            role="evidence",
            media_type="application/json",
            related_contract_id="contract_login_001",
            related_phase="qa",
            created_by="qa_engineer",
            description="Test execution results",
            tags=["tests", "qa", "evidence"]
        )

        screenshot_artifact = artifact_store.store(
            file_path=test_files['screenshot'],
            role="screenshot",
            media_type="image/png",
            related_contract_id="contract_login_001",
            related_phase="qa",
            created_by="qa_engineer",
            description="Login form screenshot",
            tags=["screenshot", "qa", "visual"]
        )

        report_artifact = artifact_store.store(
            file_path=test_files['report'],
            role="report",
            media_type="text/markdown",
            related_contract_id="contract_login_001",
            related_phase="qa",
            created_by="qa_engineer",
            description="QA approval report",
            tags=["report", "qa", "approval"]
        )

        # VERIFY: All artifacts stored
        all_artifacts = artifact_store.list_artifacts(related_contract_id="contract_login_001")
        assert len(all_artifacts) == 5

        # VERIFY: Artifacts by phase
        design_artifacts = artifact_store.list_artifacts(
            related_contract_id="contract_login_001",
            related_phase="design"
        )
        impl_artifacts = artifact_store.list_artifacts(
            related_contract_id="contract_login_001",
            related_phase="implementation"
        )
        qa_artifacts = artifact_store.list_artifacts(
            related_contract_id="contract_login_001",
            related_phase="qa"
        )

        assert len(design_artifacts) == 1
        assert len(impl_artifacts) == 1
        assert len(qa_artifacts) == 3

        # VERIFY: All artifacts are valid
        for artifact in all_artifacts:
            assert artifact_store.verify_artifact(artifact) is True

    def test_manifest_creation_workflow(self, artifact_store, test_files):
        """Test creating and verifying artifact manifest"""

        contract_id = "contract_api_002"

        # Store artifacts for API contract
        spec_artifact = artifact_store.store(
            file_path=test_files['design'],
            role="specification",
            media_type="text/markdown",
            related_contract_id=contract_id,
            related_phase="design",
            created_by="api_designer"
        )

        impl_artifact = artifact_store.store(
            file_path=test_files['code'],
            role="deliverable",
            media_type="text/x-python",
            related_contract_id=contract_id,
            related_phase="implementation",
            created_by="backend_developer"
        )

        test_artifact = artifact_store.store(
            file_path=test_files['test_results'],
            role="evidence",
            media_type="application/json",
            related_contract_id=contract_id,
            related_phase="qa",
            created_by="qa_engineer"
        )

        # Create manifest
        manifest = ArtifactManifest(
            manifest_id="manifest_api_002",
            contract_id=contract_id,
            description="Complete artifact set for API contract"
        )

        manifest.add_artifact(spec_artifact)
        manifest.add_artifact(impl_artifact)
        manifest.add_artifact(test_artifact)

        # Verify manifest
        all_valid, failures = manifest.verify_all(str(artifact_store.base_path))

        assert all_valid is True
        assert failures == []
        assert len(manifest.artifacts) == 3

        # Export manifest to JSON
        manifest_json = manifest.to_json()
        assert manifest_json is not None

        # Restore manifest from JSON
        restored_manifest = ArtifactManifest.from_json(manifest_json)

        assert restored_manifest.manifest_id == manifest.manifest_id
        assert len(restored_manifest.artifacts) == 3

        # Verify restored manifest
        all_valid2, failures2 = restored_manifest.verify_all(str(artifact_store.base_path))

        assert all_valid2 is True
        assert failures2 == []


# ============================================================================
# Integration Test: Multi-Contract Scenario
# ============================================================================

class TestMultiContractScenario:
    """Test managing artifacts across multiple contracts"""

    def test_multiple_contracts_isolated(self, artifact_store, test_files):
        """Test that artifacts from different contracts are properly isolated"""

        # Contract A: Login feature
        artifact_a1 = artifact_store.store(
            file_path=test_files['design'],
            role="specification",
            media_type="text/markdown",
            related_contract_id="contract_login",
            created_by="designer_1"
        )

        artifact_a2 = artifact_store.store(
            file_path=test_files['code'],
            role="deliverable",
            media_type="text/x-python",
            related_contract_id="contract_login",
            created_by="dev_1"
        )

        # Contract B: Registration feature
        artifact_b1 = artifact_store.store(
            file_path=test_files['test_results'],
            role="evidence",
            media_type="application/json",
            related_contract_id="contract_registration",
            created_by="qa_1"
        )

        artifact_b2 = artifact_store.store(
            file_path=test_files['report'],
            role="report",
            media_type="text/markdown",
            related_contract_id="contract_registration",
            created_by="qa_1"
        )

        # Verify isolation
        login_artifacts = artifact_store.list_artifacts(related_contract_id="contract_login")
        registration_artifacts = artifact_store.list_artifacts(related_contract_id="contract_registration")

        assert len(login_artifacts) == 2
        assert len(registration_artifacts) == 2

        # Verify no cross-contamination
        for artifact in login_artifacts:
            assert artifact.related_contract_id == "contract_login"

        for artifact in registration_artifacts:
            assert artifact.related_contract_id == "contract_registration"

    def test_shared_content_deduplication(self, artifact_store, test_files):
        """Test that shared content across contracts is deduplicated"""

        # Store same file for two different contracts
        artifact_1 = artifact_store.store(
            file_path=test_files['design'],
            role="specification",
            media_type="text/markdown",
            related_contract_id="contract_A",
            created_by="designer"
        )

        artifact_2 = artifact_store.store(
            file_path=test_files['design'],  # Same file
            role="specification",
            media_type="text/markdown",
            related_contract_id="contract_B",
            created_by="designer"
        )

        # Different artifact IDs
        assert artifact_1.artifact_id != artifact_2.artifact_id

        # Same digest (deduplicated)
        assert artifact_1.digest == artifact_2.digest

        # File stored only once
        artifact_path = artifact_store.base_path / artifact_1.digest[:2] / artifact_1.digest[2:4] / artifact_1.digest
        assert artifact_path.exists()

        # Both can be retrieved
        retrieved_1 = artifact_store.retrieve(artifact_1.digest)
        retrieved_2 = artifact_store.retrieve(artifact_2.digest)

        assert retrieved_1 is not None
        assert retrieved_2 is not None
        assert retrieved_1 == retrieved_2  # Same path


# ============================================================================
# Integration Test: Artifact Lifecycle
# ============================================================================

class TestArtifactLifecycle:
    """Test complete artifact lifecycle"""

    def test_store_retrieve_verify_delete(self, artifact_store, test_files):
        """Test full lifecycle: store → retrieve → verify → delete"""

        # STORE
        artifact = artifact_store.store(
            file_path=test_files['code'],
            role="deliverable",
            media_type="text/x-python",
            related_contract_id="contract_lifecycle",
            description="Lifecycle test artifact"
        )

        digest = artifact.digest

        # RETRIEVE artifact file
        retrieved_path = artifact_store.retrieve(digest)
        assert retrieved_path is not None
        assert retrieved_path.exists()

        # RETRIEVE metadata
        retrieved_artifact = artifact_store.retrieve_metadata(digest)
        assert retrieved_artifact is not None
        assert retrieved_artifact.artifact_id == artifact.artifact_id

        # VERIFY
        is_valid = artifact_store.verify_artifact(artifact)
        assert is_valid is True

        # DELETE
        deleted = artifact_store.delete_artifact(digest)
        assert deleted is True

        # VERIFY deletion
        assert artifact_store.retrieve(digest) is None
        assert artifact_store.retrieve_metadata(digest) is None

    def test_artifact_integrity_after_operations(self, artifact_store, test_files):
        """Test artifact integrity is maintained through operations"""

        # Store artifact
        artifact = artifact_store.store(
            file_path=test_files['test_results'],
            role="evidence",
            media_type="application/json",
            related_contract_id="contract_integrity"
        )

        original_digest = artifact.digest

        # Multiple retrievals shouldn't affect integrity
        for _ in range(5):
            retrieved_path = artifact_store.retrieve(original_digest)
            assert retrieved_path is not None

            # Recompute digest
            current_digest = compute_sha256(str(retrieved_path))
            assert current_digest == original_digest

        # Verify still passes
        assert artifact_store.verify_artifact(artifact) is True


# ============================================================================
# Integration Test: Storage Statistics
# ============================================================================

class TestStorageStatistics:
    """Test storage statistics across operations"""

    def test_stats_update_after_operations(self, artifact_store, test_files):
        """Test that statistics update correctly after operations"""

        # Initial state
        stats = artifact_store.get_storage_stats()
        initial_count = stats["total_artifacts"]
        initial_size = stats["total_size_bytes"]

        # Store artifacts
        artifact1 = artifact_store.store(
            file_path=test_files['design'],
            role="specification",
            media_type="text/markdown"
        )

        artifact2 = artifact_store.store(
            file_path=test_files['code'],
            role="deliverable",
            media_type="text/x-python"
        )

        # Check updated stats
        stats = artifact_store.get_storage_stats()
        assert stats["total_artifacts"] >= initial_count + 2
        assert stats["total_size_bytes"] > initial_size

        # Delete one artifact
        artifact_store.delete_artifact(artifact1.digest)

        # Check stats after deletion
        stats = artifact_store.get_storage_stats()
        assert stats["total_artifacts"] >= initial_count + 1

    def test_stats_role_distribution(self, artifact_store, test_files):
        """Test role distribution in statistics"""

        # Store artifacts with various roles
        artifact_store.store(
            file_path=test_files['design'],
            role="specification",
            media_type="text/markdown"
        )

        artifact_store.store(
            file_path=test_files['code'],
            role="deliverable",
            media_type="text/x-python"
        )

        artifact_store.store(
            file_path=test_files['code'],
            role="deliverable",
            media_type="text/x-python"
        )

        artifact_store.store(
            file_path=test_files['test_results'],
            role="evidence",
            media_type="application/json"
        )

        artifact_store.store(
            file_path=test_files['screenshot'],
            role="screenshot",
            media_type="image/png"
        )

        artifact_store.store(
            file_path=test_files['report'],
            role="report",
            media_type="text/markdown"
        )

        # Get statistics
        stats = artifact_store.get_storage_stats()
        role_counts = stats["artifacts_by_role"]

        # Verify all roles are present
        assert "specification" in role_counts
        assert "deliverable" in role_counts
        assert "evidence" in role_counts
        assert "screenshot" in role_counts
        assert "report" in role_counts


# ============================================================================
# Integration Test: Error Recovery
# ============================================================================

class TestErrorRecovery:
    """Test error recovery and edge cases"""

    def test_recovery_from_missing_metadata(self, artifact_store, test_files):
        """Test handling of artifacts with missing metadata"""

        # Store artifact
        artifact = artifact_store.store(
            file_path=test_files['code'],
            role="deliverable",
            media_type="text/x-python"
        )

        digest = artifact.digest

        # Delete metadata file
        meta_path = artifact_store.base_path / digest[:2] / digest[2:4] / f"{digest}.meta"
        os.unlink(meta_path)

        # Retrieval should still work
        retrieved_path = artifact_store.retrieve(digest)
        assert retrieved_path is not None

        # Metadata retrieval should return None
        retrieved_metadata = artifact_store.retrieve_metadata(digest)
        assert retrieved_metadata is None

    def test_recovery_from_corrupted_metadata(self, artifact_store, test_files):
        """Test handling of corrupted metadata files"""

        # Store artifact
        artifact = artifact_store.store(
            file_path=test_files['code'],
            role="deliverable",
            media_type="text/x-python"
        )

        digest = artifact.digest

        # Corrupt metadata file
        meta_path = artifact_store.base_path / digest[:2] / digest[2:4] / f"{digest}.meta"
        with open(meta_path, 'w') as f:
            f.write("INVALID JSON{{{")

        # Metadata retrieval should handle error gracefully
        try:
            retrieved_metadata = artifact_store.retrieve_metadata(digest)
            # Should raise exception or return None
        except json.JSONDecodeError:
            # Expected behavior
            pass

    def test_manifest_with_missing_artifacts(self, artifact_store, test_files):
        """Test manifest verification with missing artifacts"""

        # Store artifact
        artifact = artifact_store.store(
            file_path=test_files['code'],
            role="deliverable",
            media_type="text/x-python"
        )

        # Create manifest
        manifest = ArtifactManifest(
            manifest_id="manifest_missing",
            contract_id="contract_test"
        )
        manifest.add_artifact(artifact)

        # Verify initially passes
        all_valid, failures = manifest.verify_all(str(artifact_store.base_path))
        assert all_valid is True

        # Delete artifact file
        artifact_path = artifact_store.base_path / artifact.digest[:2] / artifact.digest[2:4] / artifact.digest
        os.unlink(artifact_path)

        # Verify should now fail
        all_valid, failures = manifest.verify_all(str(artifact_store.base_path))
        assert all_valid is False
        assert artifact.artifact_id in failures


# ============================================================================
# Integration Test: Performance
# ============================================================================

class TestPerformance:
    """Test performance with larger datasets"""

    def test_many_artifacts_storage(self, artifact_store, temp_artifact_store):
        """Test storing many artifacts"""

        artifacts = []

        # Store 50 artifacts
        for i in range(50):
            test_file = os.path.join(temp_artifact_store, f"file_{i}.txt")
            with open(test_file, 'w') as f:
                f.write(f"Content for file {i}" * 10)

            artifact = artifact_store.store(
                file_path=test_file,
                role="deliverable",
                media_type="text/plain",
                related_contract_id=f"contract_{i % 5}",  # 5 contracts
                description=f"Artifact {i}"
            )

            artifacts.append(artifact)

        # Verify all stored
        assert len(artifacts) == 50

        # Test retrieval performance
        for artifact in artifacts:
            retrieved = artifact_store.retrieve(artifact.digest)
            assert retrieved is not None

        # Test listing performance
        all_artifacts = artifact_store.list_artifacts()
        assert len(all_artifacts) >= 50

        # Test filtered listing
        contract_0_artifacts = artifact_store.list_artifacts(related_contract_id="contract_0")
        assert len(contract_0_artifacts) >= 10

    def test_large_manifest(self, artifact_store, temp_artifact_store):
        """Test manifest with many artifacts"""

        manifest = ArtifactManifest(
            manifest_id="manifest_large",
            contract_id="contract_large"
        )

        # Add 30 artifacts to manifest
        for i in range(30):
            test_file = os.path.join(temp_artifact_store, f"manifest_file_{i}.txt")
            with open(test_file, 'w') as f:
                f.write(f"Manifest content {i}")

            artifact = artifact_store.store(
                file_path=test_file,
                role="deliverable",
                media_type="text/plain"
            )

            manifest.add_artifact(artifact)

        # Verify all artifacts
        all_valid, failures = manifest.verify_all(str(artifact_store.base_path))

        assert all_valid is True
        assert failures == []
        assert len(manifest.artifacts) == 30

        # Test JSON serialization
        manifest_json = manifest.to_json()
        assert len(manifest_json) > 1000  # Should be substantial

        # Test deserialization
        restored = ArtifactManifest.from_json(manifest_json)
        assert len(restored.artifacts) == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
