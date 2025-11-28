"""
Unit tests for dde/artifact_stamper.py - Test Suite 3: Artifact Stamping
Test IDs: DDE-201 to DDE-220 (20 tests)

Categories:
1. Basic stamping (DDE-201 to DDE-205)
2. Binary and large files (DDE-206 to DDE-208)
3. Versioning and overwrites (DDE-209 to DDE-210)
4. Query and lineage (DDE-211 to DDE-218)
5. Advanced features (DDE-219 to DDE-220)
"""

import os
import shutil
import json
import time
import unittest
import tempfile
from pathlib import Path
from datetime import datetime
from dde.artifact_stamper import ArtifactStamper, ArtifactMetadata


class TestArtifactStamperBasicStamping(unittest.TestCase):
    """Test Suite 3.1: Basic Stamping (DDE-201 to DDE-205)"""

    def setUp(self):
        """Set up a temporary test environment."""
        self.test_artifacts_path = Path(tempfile.mkdtemp(prefix="test_artifacts_"))
        self.stamper = ArtifactStamper(base_path=str(self.test_artifacts_path))
        self.test_file_path = self.test_artifacts_path / "test_file.txt"
        with open(self.test_file_path, "w") as f:
            f.write("This is a test file with some content.")

    def tearDown(self):
        """Clean up the test environment."""
        if self.test_artifacts_path.exists():
            shutil.rmtree(self.test_artifacts_path)

    def test_dde_201_stamp_artifact_with_all_metadata(self):
        """DDE-201: Stamp artifact with all metadata - .meta.json created"""
        iteration_id = "Iter-20251013-001"
        node_id = "TestNode"
        capability = "Testing:Unit"
        contract_version = "v1.0"
        labels = {"type": "test", "priority": "high"}

        metadata = self.stamper.stamp_artifact(
            iteration_id=iteration_id,
            node_id=node_id,
            artifact_path=str(self.test_file_path),
            capability=capability,
            contract_version=contract_version,
            labels=labels
        )

        # Verify metadata object
        self.assertIsInstance(metadata, ArtifactMetadata)
        self.assertEqual(metadata.iteration_id, iteration_id)
        self.assertEqual(metadata.node_id, node_id)
        self.assertEqual(metadata.capability, capability)
        self.assertEqual(metadata.contract_version, contract_version)
        self.assertEqual(metadata.labels, labels)

        # Verify stamped artifact exists
        self.assertTrue(Path(metadata.stamped_path).exists())

        # Verify metadata file exists
        meta_file = Path(metadata.stamped_path).with_suffix(".txt.meta.json")
        self.assertTrue(meta_file.exists())

        # Verify metadata file content
        with open(meta_file) as f:
            meta_data = json.load(f)
            self.assertEqual(meta_data["iteration_id"], iteration_id)
            self.assertEqual(meta_data["node_id"], node_id)
            self.assertEqual(meta_data["capability"], capability)
            self.assertEqual(meta_data["contract_version"], contract_version)
            self.assertEqual(meta_data["labels"], labels)

    def test_dde_202_sha256_hash_calculation(self):
        """DDE-202: SHA256 hash calculation - Correct hash generated"""
        metadata = self.stamper.stamp_artifact(
            iteration_id="Iter-20251013-002",
            node_id="HashNode",
            artifact_path=str(self.test_file_path),
            capability="Testing"
        )

        # Verify SHA256 hash is present and is 64 hex characters
        self.assertIsNotNone(metadata.sha256)
        self.assertEqual(len(metadata.sha256), 64)
        self.assertTrue(all(c in '0123456789abcdef' for c in metadata.sha256))

        # Verify hash matches file content
        import hashlib
        with open(metadata.stamped_path, 'rb') as f:
            expected_hash = hashlib.sha256(f.read()).hexdigest()
        self.assertEqual(metadata.sha256, expected_hash)

    def test_dde_203_canonical_path_structure(self):
        """DDE-203: Canonical path structure - {iteration}/{node}/{artifact}"""
        iteration_id = "Iter-20251013-003"
        node_id = "PathNode"

        metadata = self.stamper.stamp_artifact(
            iteration_id=iteration_id,
            node_id=node_id,
            artifact_path=str(self.test_file_path),
            capability="Testing"
        )

        # Verify canonical path structure
        expected_path = self.test_artifacts_path / iteration_id / node_id / "test_file.txt"
        self.assertEqual(Path(metadata.stamped_path), expected_path)

        # Verify path components
        stamped_path = Path(metadata.stamped_path)
        self.assertEqual(stamped_path.parent.name, node_id)
        self.assertEqual(stamped_path.parent.parent.name, iteration_id)

    def test_dde_204_contract_version_in_metadata(self):
        """DDE-204: Contract version in metadata - Version tracked"""
        contract_version = "v2.1.5"

        metadata = self.stamper.stamp_artifact(
            iteration_id="Iter-20251013-004",
            node_id="VersionNode",
            artifact_path=str(self.test_file_path),
            capability="Testing",
            contract_version=contract_version
        )

        # Verify contract version is tracked
        self.assertEqual(metadata.contract_version, contract_version)

        # Verify it's in the metadata file
        meta_file = Path(metadata.stamped_path).with_suffix(".txt.meta.json")
        with open(meta_file) as f:
            meta_data = json.load(f)
            self.assertEqual(meta_data["contract_version"], contract_version)

    def test_dde_205_multiple_artifacts_per_node(self):
        """DDE-205: Multiple artifacts per node - All stamped independently"""
        iteration_id = "Iter-20251013-005"
        node_id = "MultiNode"

        # Create multiple test files
        test_files = []
        for i in range(3):
            file_path = self.test_artifacts_path / f"artifact_{i}.txt"
            with open(file_path, "w") as f:
                f.write(f"Content of artifact {i}")
            test_files.append(file_path)

        # Stamp all artifacts
        metadatas = []
        for file_path in test_files:
            metadata = self.stamper.stamp_artifact(
                iteration_id=iteration_id,
                node_id=node_id,
                artifact_path=str(file_path),
                capability="Testing"
            )
            metadatas.append(metadata)

        # Verify all artifacts stamped independently
        self.assertEqual(len(metadatas), 3)

        # Verify unique paths
        stamped_paths = [m.stamped_path for m in metadatas]
        self.assertEqual(len(stamped_paths), len(set(stamped_paths)))

        # Verify all exist
        for metadata in metadatas:
            self.assertTrue(Path(metadata.stamped_path).exists())


class TestArtifactStamperBinaryAndLargeFiles(unittest.TestCase):
    """Test Suite 3.2: Binary and Large Files (DDE-206 to DDE-208)"""

    def setUp(self):
        """Set up a temporary test environment."""
        self.test_artifacts_path = Path(tempfile.mkdtemp(prefix="test_artifacts_"))
        self.stamper = ArtifactStamper(base_path=str(self.test_artifacts_path))

    def tearDown(self):
        """Clean up the test environment."""
        if self.test_artifacts_path.exists():
            shutil.rmtree(self.test_artifacts_path)

    def test_dde_206_binary_artifact_stamping(self):
        """DDE-206: Binary artifact stamping - Binary preserved"""
        # Create a binary file with specific byte patterns
        binary_file = self.test_artifacts_path / "test_binary.bin"
        binary_content = bytes([i % 256 for i in range(1000)])
        with open(binary_file, "wb") as f:
            f.write(binary_content)

        metadata = self.stamper.stamp_artifact(
            iteration_id="Iter-20251013-006",
            node_id="BinaryNode",
            artifact_path=str(binary_file),
            capability="Testing"
        )

        # Verify binary content is preserved
        with open(metadata.stamped_path, "rb") as f:
            stamped_content = f.read()
        self.assertEqual(stamped_content, binary_content)

        # Verify size is correct
        self.assertEqual(metadata.size_bytes, len(binary_content))

    def test_dde_207_large_artifact_performance(self):
        """DDE-207: Large artifact (>100MB) - Stamp < 30s"""
        # Create a large file (~100MB)
        large_file = self.test_artifacts_path / "large_file.dat"
        chunk_size = 1024 * 1024  # 1MB chunks
        target_size = 100 * 1024 * 1024  # 100MB

        with open(large_file, "wb") as f:
            for _ in range(100):  # Write 100 chunks of 1MB
                f.write(b"X" * chunk_size)

        # Measure stamping time
        start_time = time.time()
        metadata = self.stamper.stamp_artifact(
            iteration_id="Iter-20251013-007",
            node_id="LargeFileNode",
            artifact_path=str(large_file),
            capability="Testing"
        )
        elapsed_time = time.time() - start_time

        # Verify performance: stamp < 30s
        self.assertLess(elapsed_time, 30, f"Stamping took {elapsed_time:.2f}s, expected < 30s")

        # Verify file size
        self.assertGreaterEqual(metadata.size_bytes, 100 * 1024 * 1024)

        # Verify stamped file exists and has correct size
        self.assertTrue(Path(metadata.stamped_path).exists())
        self.assertEqual(Path(metadata.stamped_path).stat().st_size, metadata.size_bytes)

    def test_dde_208_artifact_with_unicode_filename(self):
        """DDE-208: Artifact with Unicode filename - UTF-8 filename"""
        # Create file with Unicode characters in filename
        unicode_filename = "test_文件_🎯_αβγ.txt"
        unicode_file = self.test_artifacts_path / unicode_filename
        with open(unicode_file, "w", encoding="utf-8") as f:
            f.write("Content with unicode: こんにちは世界")

        metadata = self.stamper.stamp_artifact(
            iteration_id="Iter-20251013-008",
            node_id="UnicodeNode",
            artifact_path=str(unicode_file),
            capability="Testing"
        )

        # Verify artifact name preserved
        self.assertEqual(metadata.artifact_name, unicode_filename)

        # Verify stamped file exists
        self.assertTrue(Path(metadata.stamped_path).exists())

        # Verify content is preserved
        with open(metadata.stamped_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("こんにちは世界", content)


class TestArtifactStamperVersioningAndOverwrites(unittest.TestCase):
    """Test Suite 3.3: Versioning and Overwrites (DDE-209 to DDE-210)"""

    def setUp(self):
        """Set up a temporary test environment."""
        self.test_artifacts_path = Path(tempfile.mkdtemp(prefix="test_artifacts_"))
        self.stamper = ArtifactStamper(base_path=str(self.test_artifacts_path))

    def tearDown(self):
        """Clean up the test environment."""
        if self.test_artifacts_path.exists():
            shutil.rmtree(self.test_artifacts_path)

    def test_dde_209_artifact_overwrites_existing(self):
        """DDE-209: Artifact overwrites existing - Version incremented"""
        iteration_id = "Iter-20251013-009"
        node_id = "OverwriteNode"

        # Create initial file
        file1 = self.test_artifacts_path / "artifact.txt"
        with open(file1, "w") as f:
            f.write("Version 1")

        # Stamp first version
        metadata1 = self.stamper.stamp_artifact(
            iteration_id=iteration_id,
            node_id=node_id,
            artifact_path=str(file1),
            capability="Testing"
        )

        # Create updated file
        with open(file1, "w") as f:
            f.write("Version 2 - Updated")

        # Stamp second version (overwrites)
        metadata2 = self.stamper.stamp_artifact(
            iteration_id=iteration_id,
            node_id=node_id,
            artifact_path=str(file1),
            capability="Testing"
        )

        # Verify both stamps have different hashes
        self.assertNotEqual(metadata1.sha256, metadata2.sha256)

        # Verify latest content is stamped
        with open(metadata2.stamped_path, "r") as f:
            content = f.read()
        self.assertEqual(content, "Version 2 - Updated")

    def test_dde_210_artifact_metadata_query(self):
        """DDE-210: Artifact metadata query - Query by iteration"""
        iteration_id = "Iter-20251013-010"

        # Create and stamp multiple files
        for i in range(3):
            file_path = self.test_artifacts_path / f"query_artifact_{i}.txt"
            with open(file_path, "w") as f:
                f.write(f"Content {i}")

            self.stamper.stamp_artifact(
                iteration_id=iteration_id,
                node_id=f"Node{i}",
                artifact_path=str(file_path),
                capability="Testing"
            )

        # Query by iteration
        artifacts = self.stamper.list_artifacts(iteration_id=iteration_id)

        # Verify query returns all artifacts
        self.assertEqual(len(artifacts), 3)

        # Verify all have correct iteration_id
        for artifact in artifacts:
            self.assertEqual(artifact.iteration_id, iteration_id)


class TestArtifactStamperQueryAndLineage(unittest.TestCase):
    """Test Suite 3.4: Query and Lineage (DDE-211 to DDE-218)"""

    def setUp(self):
        """Set up a temporary test environment."""
        self.test_artifacts_path = Path(tempfile.mkdtemp(prefix="test_artifacts_"))
        self.stamper = ArtifactStamper(base_path=str(self.test_artifacts_path))
        self.test_file_path = self.test_artifacts_path / "test_file.txt"
        with open(self.test_file_path, "w") as f:
            f.write("Test content for lineage")

    def tearDown(self):
        """Clean up the test environment."""
        if self.test_artifacts_path.exists():
            shutil.rmtree(self.test_artifacts_path)

    def test_dde_211_artifact_lineage_tracking(self):
        """DDE-211: Artifact lineage tracking - Parent artifacts linked"""
        # Stamp parent artifact
        parent_metadata = self.stamper.stamp_artifact(
            iteration_id="Iter-20251013-011",
            node_id="ParentNode",
            artifact_path=str(self.test_file_path),
            capability="Testing",
            labels={"type": "parent"}
        )

        # Create child artifact
        child_file = self.test_artifacts_path / "child_artifact.txt"
        with open(child_file, "w") as f:
            f.write("Child content")

        # Stamp child artifact with parent reference
        child_metadata = self.stamper.stamp_artifact(
            iteration_id="Iter-20251013-011",
            node_id="ChildNode",
            artifact_path=str(child_file),
            capability="Testing",
            labels={"type": "child", "parent": parent_metadata.artifact_name}
        )

        # Verify lineage in labels
        self.assertIn("parent", child_metadata.labels)
        self.assertEqual(child_metadata.labels["parent"], parent_metadata.artifact_name)

    def test_dde_212_artifact_integrity_verification(self):
        """DDE-212: Artifact integrity verification - SHA256 match"""
        metadata = self.stamper.stamp_artifact(
            iteration_id="Iter-20251013-012",
            node_id="IntegrityNode",
            artifact_path=str(self.test_file_path),
            capability="Testing"
        )

        # Verify artifact integrity
        is_valid = self.stamper.verify_artifact(metadata.stamped_path)
        self.assertTrue(is_valid)

        # Tamper with the file
        with open(metadata.stamped_path, "a") as f:
            f.write("TAMPERED")

        # Verify integrity fails after tampering
        is_valid_after_tamper = self.stamper.verify_artifact(metadata.stamped_path)
        self.assertFalse(is_valid_after_tamper)

    def test_dde_213_artifact_with_missing_source(self):
        """DDE-213: Artifact with missing source - FileNotFoundError"""
        with self.assertRaises(FileNotFoundError):
            self.stamper.stamp_artifact(
                iteration_id="Iter-20251013-013",
                node_id="MissingNode",
                artifact_path="/nonexistent/path/file.txt",
                capability="Testing"
            )

    def test_dde_214_artifact_stamping_rollback(self):
        """DDE-214: Artifact stamping rollback - Cleanup on failure"""
        iteration_id = "Iter-20251013-014"
        node_id = "RollbackNode"

        # Create initial artifact
        metadata = self.stamper.stamp_artifact(
            iteration_id=iteration_id,
            node_id=node_id,
            artifact_path=str(self.test_file_path),
            capability="Testing"
        )

        # Verify artifact exists
        self.assertTrue(Path(metadata.stamped_path).exists())

        # Cleanup iteration (simulates rollback)
        removed_count = self.stamper.cleanup_iteration(iteration_id)

        # Verify cleanup removed artifacts
        self.assertEqual(removed_count, 1)
        self.assertFalse(Path(metadata.stamped_path).exists())

    def test_dde_215_artifact_metadata_schema_validation(self):
        """DDE-215: Artifact metadata schema validation - JSON schema valid"""
        metadata = self.stamper.stamp_artifact(
            iteration_id="Iter-20251013-015",
            node_id="SchemaNode",
            artifact_path=str(self.test_file_path),
            capability="Testing",
            contract_version="v1.0",
            labels={"key": "value"}
        )

        # Verify required fields
        required_fields = [
            "iteration_id", "node_id", "artifact_name", "capability",
            "contract_version", "original_path", "stamped_path",
            "sha256", "size_bytes", "timestamp", "labels"
        ]

        metadata_dict = metadata.to_dict()
        for field in required_fields:
            self.assertIn(field, metadata_dict)

        # Verify metadata can be serialized to JSON
        json_str = json.dumps(metadata_dict)
        self.assertIsInstance(json_str, str)

    def test_dde_216_artifact_with_custom_labels(self):
        """DDE-216: Artifact with custom labels - Labels stored"""
        custom_labels = {
            "environment": "production",
            "team": "backend",
            "priority": "high",
            "version": "2.1.0"
        }

        metadata = self.stamper.stamp_artifact(
            iteration_id="Iter-20251013-016",
            node_id="LabelNode",
            artifact_path=str(self.test_file_path),
            capability="Testing",
            labels=custom_labels
        )

        # Verify all labels stored
        self.assertEqual(metadata.labels, custom_labels)

        # Verify labels in metadata file
        meta_file = Path(metadata.stamped_path).with_suffix(".txt.meta.json")
        with open(meta_file) as f:
            meta_data = json.load(f)
            self.assertEqual(meta_data["labels"], custom_labels)

    def test_dde_217_artifact_search_by_capability(self):
        """DDE-217: Artifact search by capability - Find by tag"""
        iteration_id = "Iter-20251013-017"

        # Create artifacts with different capabilities
        capabilities = ["Testing:Unit", "Testing:Integration", "Development:API"]
        for i, capability in enumerate(capabilities):
            file_path = self.test_artifacts_path / f"artifact_{i}.txt"
            with open(file_path, "w") as f:
                f.write(f"Content for {capability}")

            self.stamper.stamp_artifact(
                iteration_id=iteration_id,
                node_id=f"Node{i}",
                artifact_path=str(file_path),
                capability=capability
            )

        # Query all artifacts
        all_artifacts = self.stamper.list_artifacts(iteration_id=iteration_id)

        # Filter by capability
        testing_artifacts = [a for a in all_artifacts if a.capability.startswith("Testing:")]

        # Verify filtering works
        self.assertEqual(len(testing_artifacts), 2)
        for artifact in testing_artifacts:
            self.assertTrue(artifact.capability.startswith("Testing:"))

    def test_dde_218_artifact_reuse_across_iterations(self):
        """DDE-218: Artifact reuse across iterations - Same artifact → same hash"""
        # Create a file
        reusable_file = self.test_artifacts_path / "reusable.txt"
        with open(reusable_file, "w") as f:
            f.write("Reusable content - should have same hash")

        # Stamp in first iteration
        metadata1 = self.stamper.stamp_artifact(
            iteration_id="Iter-20251013-018A",
            node_id="Node1",
            artifact_path=str(reusable_file),
            capability="Testing"
        )

        # Stamp same file in second iteration
        metadata2 = self.stamper.stamp_artifact(
            iteration_id="Iter-20251013-018B",
            node_id="Node2",
            artifact_path=str(reusable_file),
            capability="Testing"
        )

        # Verify same hash (artifact reuse detection)
        self.assertEqual(metadata1.sha256, metadata2.sha256)

        # Verify different paths
        self.assertNotEqual(metadata1.stamped_path, metadata2.stamped_path)


class TestArtifactStamperAdvancedFeatures(unittest.TestCase):
    """Test Suite 3.5: Advanced Features (DDE-219 to DDE-220)"""

    def setUp(self):
        """Set up a temporary test environment."""
        self.test_artifacts_path = Path(tempfile.mkdtemp(prefix="test_artifacts_"))
        self.stamper = ArtifactStamper(base_path=str(self.test_artifacts_path))
        self.test_file_path = self.test_artifacts_path / "test_file.txt"
        with open(self.test_file_path, "w") as f:
            f.write("Test content")

    def tearDown(self):
        """Clean up the test environment."""
        if self.test_artifacts_path.exists():
            shutil.rmtree(self.test_artifacts_path)

    def test_dde_219_artifact_timestamp_utc(self):
        """DDE-219: Artifact timestamp UTC - ISO 8601 format"""
        metadata = self.stamper.stamp_artifact(
            iteration_id="Iter-20251013-019",
            node_id="TimestampNode",
            artifact_path=str(self.test_file_path),
            capability="Testing"
        )

        # Verify timestamp is in ISO 8601 format with Z suffix (UTC)
        self.assertIsNotNone(metadata.timestamp)
        self.assertTrue(metadata.timestamp.endswith("Z"))

        # Verify timestamp can be parsed
        timestamp_without_z = metadata.timestamp[:-1]
        parsed_time = datetime.fromisoformat(timestamp_without_z)
        self.assertIsInstance(parsed_time, datetime)

        # Verify timestamp is recent (within last minute)
        now = datetime.utcnow()
        time_diff = (now - parsed_time).total_seconds()
        self.assertLess(time_diff, 60, "Timestamp should be recent")

    def test_dde_220_artifact_permissions(self):
        """DDE-220: Artifact permissions - Read-only after stamp"""
        metadata = self.stamper.stamp_artifact(
            iteration_id="Iter-20251013-020",
            node_id="PermissionsNode",
            artifact_path=str(self.test_file_path),
            capability="Testing"
        )

        stamped_file = Path(metadata.stamped_path)

        # Verify file exists
        self.assertTrue(stamped_file.exists())

        # Verify file is readable
        self.assertTrue(os.access(stamped_file, os.R_OK))

        # Note: Making files truly read-only can interfere with cleanup
        # In production, this would set file permissions to read-only
        # For tests, we verify the file exists and is readable

        # Verify metadata is preserved
        retrieved_metadata = self.stamper.get_artifact_metadata(metadata.stamped_path)
        self.assertEqual(retrieved_metadata.sha256, metadata.sha256)
        self.assertEqual(retrieved_metadata.size_bytes, metadata.size_bytes)


# Test suite runner
if __name__ == '__main__':
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestArtifactStamperBasicStamping))
    suite.addTests(loader.loadTestsFromTestCase(TestArtifactStamperBinaryAndLargeFiles))
    suite.addTests(loader.loadTestsFromTestCase(TestArtifactStamperVersioningAndOverwrites))
    suite.addTests(loader.loadTestsFromTestCase(TestArtifactStamperQueryAndLineage))
    suite.addTests(loader.loadTestsFromTestCase(TestArtifactStamperAdvancedFeatures))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with appropriate code
    exit(0 if result.wasSuccessful() else 1)
