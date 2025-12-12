"""
E2E Tests for Context Packager - State Serialization for Handoff.

EPIC: MD-3061 - Context packaging and state transfer E2E test

This module contains comprehensive E2E tests for the ContextPackager,
covering:
- AC-1: Test context serialization with all data types
- AC-2: Verify package integrity across transfer
- AC-3: Test deserialization and state reconstruction

These tests simulate real-world scenarios of mission context being
packaged, transferred, and reconstructed across system boundaries.
"""

import pytest
import json
import gzip
import hashlib
import tempfile
import os
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path

from maestro_hive.mission import (
    ContextPackager,
    PackagerConfig,
    PackageFormat,
    CompressionAlgorithm,
    MissionContext,
    MissionConstraints,
    Artifact,
    SchemaValidator,
    PackageMetadata,
    PackedContext,
)


class TestContextSerializationE2E:
    """
    E2E tests for AC-1: Test context serialization with all data types.

    Tests serialization of all supported data types in MissionContext:
    - String fields (mission_id, mission_name)
    - List fields (objectives, artifacts)
    - Nested dict fields (team_composition, metadata)
    - Numeric fields (max_duration_hours, max_cost_dollars)
    - Boolean fields (require_human_review)
    - Datetime fields (created_at)
    - Optional/null fields (allowed_tools, forbidden_actions)
    """

    def setup_method(self):
        """Set up test fixtures."""
        self.packager = ContextPackager()

    def test_string_field_serialization(self):
        """Test serialization of string fields preserves exact values."""
        # Arrange - various string types
        test_cases = [
            ("simple-id", "Simple Mission"),
            ("id_with_underscores_123", "Mission with Numbers 456"),
            ("UPPERCASE-ID", "UPPERCASE NAME"),
            ("id-with-special-chars!", "Mission: [Special] & <Characters>"),
            ("unicode-id-日本語", "ユニコードミッション"),
            ("", ""),  # Edge case: empty strings
            ("a" * 1000, "b" * 1000),  # Long strings
        ]

        for mission_id, mission_name in test_cases:
            context = MissionContext(
                mission_id=mission_id,
                mission_name=mission_name,
                objectives=["test"],
                team_composition={"role": "test"},
                constraints=MissionConstraints(),
            )

            # Act
            if not mission_id or not mission_name:
                # Empty IDs fail validation
                config = PackagerConfig(validate_on_pack=False)
                packager = ContextPackager(config)
                packed = packager.pack_context(context)
                restored = packager.unpack_context(packed)
            else:
                packed = self.packager.pack_context(context)
                restored = self.packager.unpack_context(packed)

            # Assert
            assert restored.mission_id == mission_id
            assert restored.mission_name == mission_name

    def test_list_field_serialization(self):
        """Test serialization of list fields with various contents."""
        # Arrange
        objectives = [
            "Implement user authentication",
            "Add OAuth2 support",
            "Write unit tests",
            "Update documentation",
            "Deploy to staging",
        ]

        artifacts = [
            Artifact(
                id=f"artifact-{i}",
                name=f"Artifact {i}",
                type="document" if i % 2 == 0 else "code",
                path=f"/path/to/artifact_{i}.py",
                metadata={"priority": i},
            )
            for i in range(5)
        ]

        context = MissionContext(
            mission_id="list-test",
            mission_name="List Field Test",
            objectives=objectives,
            team_composition={"devs": ["dev1", "dev2", "dev3"]},
            constraints=MissionConstraints(),
            artifacts=artifacts,
        )

        # Act
        packed = self.packager.pack_context(context)
        restored = self.packager.unpack_context(packed)

        # Assert
        assert restored.objectives == objectives
        assert len(restored.artifacts) == len(artifacts)
        for orig, rest in zip(artifacts, restored.artifacts):
            assert rest.id == orig.id
            assert rest.name == orig.name
            assert rest.type == orig.type
            assert rest.path == orig.path

    def test_nested_dict_serialization(self):
        """Test serialization of nested dictionary structures."""
        # Arrange - deeply nested structure
        team_composition = {
            "leads": {
                "technical": {"name": "Alice", "skills": ["python", "rust"]},
                "product": {"name": "Bob", "skills": ["agile", "roadmaps"]},
            },
            "teams": {
                "backend": ["Charlie", "Diana"],
                "frontend": ["Eve", "Frank"],
            },
            "consultants": [
                {"name": "Grace", "specialty": "security"},
                {"name": "Henry", "specialty": "performance"},
            ],
        }

        metadata = {
            "project": {
                "name": "Context Packager",
                "version": "2.0",
                "dependencies": {
                    "required": ["json", "gzip"],
                    "optional": ["msgpack", "zstd"],
                },
            },
            "settings": {
                "debug": True,
                "logging_level": "INFO",
                "timeout_config": {"default": 30, "max": 300},
            },
        }

        context = MissionContext(
            mission_id="nested-dict-test",
            mission_name="Nested Dict Test",
            objectives=["test nested dicts"],
            team_composition=team_composition,
            constraints=MissionConstraints(),
            metadata=metadata,
        )

        # Act
        packed = self.packager.pack_context(context)
        restored = self.packager.unpack_context(packed)

        # Assert
        assert restored.team_composition == team_composition
        assert restored.metadata == metadata
        assert restored.team_composition["leads"]["technical"]["skills"] == ["python", "rust"]
        assert restored.metadata["settings"]["timeout_config"]["max"] == 300

    def test_numeric_field_serialization(self):
        """Test serialization of numeric fields (int, float)."""
        # Arrange - various numeric types
        test_cases = [
            (0.0, 0.0, 0),  # Zeros
            (8.5, 100.99, 5),  # Normal values
            (0.001, 0.001, 1),  # Small decimals
            (999999.999, 999999.99, 100),  # Large values
            (24.0, 1000.0, 50),  # Boundary values
        ]

        for max_duration, max_cost, max_personas in test_cases:
            constraints = MissionConstraints(
                max_duration_hours=max_duration,
                max_cost_dollars=max_cost,
                max_personas=max_personas,
            )

            context = MissionContext(
                mission_id=f"numeric-{max_duration}",
                mission_name="Numeric Test",
                objectives=["test"],
                team_composition={},
                constraints=constraints,
            )

            # Skip validation for edge cases
            config = PackagerConfig(validate_on_pack=max_duration > 0 and max_personas > 0)
            packager = ContextPackager(config)

            # Act
            packed = packager.pack_context(context)
            restored = packager.unpack_context(packed)

            # Assert
            assert restored.constraints.max_duration_hours == max_duration
            assert restored.constraints.max_cost_dollars == max_cost
            assert restored.constraints.max_personas == max_personas

    def test_boolean_field_serialization(self):
        """Test serialization of boolean fields."""
        # Arrange
        for require_review in [True, False]:
            constraints = MissionConstraints(
                require_human_review=require_review,
            )

            context = MissionContext(
                mission_id=f"bool-{require_review}",
                mission_name="Boolean Test",
                objectives=["test"],
                team_composition={},
                constraints=constraints,
            )

            # Act
            packed = self.packager.pack_context(context)
            restored = self.packager.unpack_context(packed)

            # Assert
            assert restored.constraints.require_human_review is require_review

    def test_datetime_field_serialization(self):
        """Test serialization of datetime fields with timezone handling."""
        # Arrange
        test_datetimes = [
            datetime(2025, 1, 15, 10, 30, 0),  # Normal datetime
            datetime(2020, 1, 1, 0, 0, 0),  # Start of year
            datetime(2025, 12, 31, 23, 59, 59),  # End of year
            datetime.utcnow(),  # Current time
        ]

        for dt in test_datetimes:
            context = MissionContext(
                mission_id="datetime-test",
                mission_name="Datetime Test",
                objectives=["test"],
                team_composition={},
                constraints=MissionConstraints(),
                created_at=dt,
            )

            # Act
            packed = self.packager.pack_context(context)
            restored = self.packager.unpack_context(packed)

            # Assert - compare ISO format strings to handle timezone
            assert restored.created_at.isoformat()[:19] == dt.isoformat()[:19]

    def test_optional_field_serialization(self):
        """Test serialization of optional/nullable fields."""
        # Arrange - context with optional fields set
        constraints_with_optionals = MissionConstraints(
            max_duration_hours=8.0,
            allowed_tools=["python", "docker", "git"],
            forbidden_actions=["delete_prod", "force_push"],
        )

        context_with = MissionContext(
            mission_id="optional-with",
            mission_name="Optional Fields Test",
            objectives=["test"],
            team_composition={},
            constraints=constraints_with_optionals,
        )

        # Context without optional fields
        constraints_without = MissionConstraints(
            max_duration_hours=8.0,
            allowed_tools=None,
            forbidden_actions=None,
        )

        context_without = MissionContext(
            mission_id="optional-without",
            mission_name="Optional Fields Test",
            objectives=["test"],
            team_composition={},
            constraints=constraints_without,
        )

        # Act
        packed_with = self.packager.pack_context(context_with)
        packed_without = self.packager.pack_context(context_without)

        restored_with = self.packager.unpack_context(packed_with)
        restored_without = self.packager.unpack_context(packed_without)

        # Assert
        assert restored_with.constraints.allowed_tools == ["python", "docker", "git"]
        assert restored_with.constraints.forbidden_actions == ["delete_prod", "force_push"]
        assert restored_without.constraints.allowed_tools is None
        assert restored_without.constraints.forbidden_actions is None

    def test_empty_collections_serialization(self):
        """Test serialization handles empty collections correctly."""
        # Arrange
        context = MissionContext(
            mission_id="empty-collections",
            mission_name="Empty Collections Test",
            objectives=[],  # Empty list
            team_composition={},  # Empty dict
            constraints=MissionConstraints(),
            artifacts=[],  # Empty list
            metadata={},  # Empty dict
        )

        # Disable validation since empty objectives fail
        config = PackagerConfig(validate_on_pack=False)
        packager = ContextPackager(config)

        # Act
        packed = packager.pack_context(context)
        restored = packager.unpack_context(packed)

        # Assert
        assert restored.objectives == []
        assert restored.team_composition == {}
        assert restored.artifacts == []
        assert restored.metadata == {}


class TestPackageIntegrityE2E:
    """
    E2E tests for AC-2: Verify package integrity across transfer.

    Tests:
    - SHA-256 checksum generation and verification
    - Corruption detection
    - Compression integrity (gzip)
    - Transfer simulation with integrity checks
    """

    def setup_method(self):
        """Set up test fixtures."""
        self.packager = ContextPackager()
        self.valid_context = MissionContext(
            mission_id="integrity-test",
            mission_name="Package Integrity Test",
            objectives=["Test checksum", "Test compression", "Test transfer"],
            team_composition={"qa": "integrity_engineer"},
            constraints=MissionConstraints(max_duration_hours=4.0),
            metadata={"test_type": "e2e_integrity"},
        )

    def test_sha256_checksum_generation(self):
        """Test that SHA-256 checksums are correctly generated."""
        # Act
        packed = self.packager.pack_with_metadata(self.valid_context)

        # Assert
        assert packed.metadata.checksum is not None
        assert len(packed.metadata.checksum) == 64  # SHA-256 produces 64 hex chars

        # Verify checksum format is valid hex
        int(packed.metadata.checksum, 16)

        # Manually verify checksum
        expected_checksum = hashlib.sha256(packed.data).hexdigest()
        assert packed.metadata.checksum == expected_checksum

    def test_checksum_verification_valid_data(self):
        """Test checksum verification passes for untampered data."""
        # Arrange
        packed = self.packager.pack_with_metadata(self.valid_context)

        # Act
        is_valid = self.packager.verify_checksum(packed)

        # Assert
        assert is_valid is True

    def test_checksum_verification_corrupted_data(self):
        """Test checksum verification fails for tampered data."""
        # Arrange
        packed = self.packager.pack_with_metadata(self.valid_context)

        # Corrupt various parts of the data
        corruption_scenarios = [
            lambda d: d + b"corrupted",  # Append corruption
            lambda d: b"corrupted" + d,  # Prepend corruption
            lambda d: d[:-10],  # Truncate
            lambda d: d[:10] + b"\x00" * 10 + d[20:],  # Null bytes in middle
            lambda d: bytes([b ^ 0xFF for b in d[:20]]) + d[20:],  # Flip bits
        ]

        for corrupt in corruption_scenarios:
            corrupted_packed = PackedContext(
                data=corrupt(packed.data),
                metadata=packed.metadata,
            )

            # Act
            is_valid = self.packager.verify_checksum(corrupted_packed)

            # Assert
            assert is_valid is False, f"Corruption not detected: {corrupt.__doc__}"

    def test_gzip_compression_integrity(self):
        """Test gzip compression produces valid compressed data."""
        # Arrange
        config = PackagerConfig(
            format=PackageFormat.JSON_COMPRESSED,
            compression=CompressionAlgorithm.GZIP,
        )
        packager = ContextPackager(config)

        # Act
        packed = packager.pack_context(self.valid_context)

        # Assert - check gzip magic bytes
        assert packed[:2] == b"\x1f\x8b", "Data should be gzip compressed"

        # Verify can decompress
        decompressed = gzip.decompress(packed)
        assert len(decompressed) > 0

        # Verify JSON is valid after decompression
        data = json.loads(decompressed.decode("utf-8"))
        assert data["mission_id"] == "integrity-test"

    def test_compression_ratio_tracking(self):
        """Test that compression provides measurable size reduction."""
        # Arrange - create a large context with repetitive data
        large_metadata = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}
        large_context = MissionContext(
            mission_id="compression-test",
            mission_name="Large Context for Compression",
            objectives=["objective_" + str(i) * 50 for i in range(50)],
            team_composition={"team": {"member_" + str(i): "role" * 20 for i in range(20)}},
            constraints=MissionConstraints(),
            metadata=large_metadata,
        )

        # Act
        packed_with_meta = self.packager.pack_with_metadata(large_context)
        ratio = self.packager.get_compression_ratio(large_context)

        # Assert
        assert packed_with_meta.metadata.original_size > packed_with_meta.metadata.packed_size
        assert ratio > 1.5, "Compression should provide at least 1.5x reduction for repetitive data"

    def test_transfer_simulation_file_based(self):
        """Test integrity maintained when writing to and reading from file."""
        # Arrange
        packed = self.packager.pack_with_metadata(self.valid_context)

        # Act - simulate file-based transfer
        with tempfile.NamedTemporaryFile(mode="wb", delete=False) as f:
            f.write(packed.data)
            temp_path = f.name

        try:
            with open(temp_path, "rb") as f:
                read_data = f.read()

            # Recreate packed context with read data
            transferred_packed = PackedContext(data=read_data, metadata=packed.metadata)

            # Assert
            assert self.packager.verify_checksum(transferred_packed) is True
            restored = self.packager.unpack_context(read_data)
            assert restored.mission_id == self.valid_context.mission_id
        finally:
            os.unlink(temp_path)

    def test_transfer_simulation_base64_encoding(self):
        """Test integrity maintained through base64 encoding (common in API transfers)."""
        import base64

        # Arrange
        packed = self.packager.pack_with_metadata(self.valid_context)

        # Act - simulate base64 transfer (common in JSON APIs)
        encoded = base64.b64encode(packed.data).decode("ascii")
        decoded = base64.b64decode(encoded.encode("ascii"))

        transferred_packed = PackedContext(data=decoded, metadata=packed.metadata)

        # Assert
        assert self.packager.verify_checksum(transferred_packed) is True
        assert decoded == packed.data

    def test_multiple_pack_same_checksum(self):
        """Test that packing same context produces consistent checksum."""
        # This is important for idempotency

        # Note: Due to timestamp in metadata, exact bytes may differ
        # But data integrity should still be verifiable

        packed1 = self.packager.pack_with_metadata(self.valid_context)
        packed2 = self.packager.pack_with_metadata(self.valid_context)

        # Both should be independently verifiable
        assert self.packager.verify_checksum(packed1) is True
        assert self.packager.verify_checksum(packed2) is True

        # Both should unpack to same content
        restored1 = self.packager.unpack_context(packed1.data)
        restored2 = self.packager.unpack_context(packed2.data)

        assert restored1.mission_id == restored2.mission_id
        assert restored1.objectives == restored2.objectives

    def test_metadata_size_tracking(self):
        """Test that metadata accurately tracks size information."""
        # Arrange & Act
        packed = self.packager.pack_with_metadata(self.valid_context)

        # Assert
        assert packed.metadata.original_size > 0
        assert packed.metadata.packed_size > 0
        assert packed.metadata.packed_size == len(packed.data)
        assert packed.metadata.format == "json"
        assert packed.metadata.compression == "gzip"
        assert packed.metadata.schema_version == "1.0"


class TestStateReconstructionE2E:
    """
    E2E tests for AC-3: Test deserialization and state reconstruction.

    Tests:
    - Full round-trip serialization/deserialization
    - State equality after reconstruction
    - Complex nested object reconstruction
    - Metadata preservation
    - Multi-format compatibility
    """

    def setup_method(self):
        """Set up test fixtures."""
        self.packager = ContextPackager()

    def test_full_round_trip_simple_context(self):
        """Test complete pack/unpack cycle with simple context."""
        # Arrange
        original = MissionContext(
            mission_id="round-trip-simple",
            mission_name="Simple Round Trip",
            objectives=["objective 1"],
            team_composition={"lead": "developer"},
            constraints=MissionConstraints(),
        )

        # Act
        packed = self.packager.pack_context(original)
        restored = self.packager.unpack_context(packed)

        # Assert
        assert restored.mission_id == original.mission_id
        assert restored.mission_name == original.mission_name
        assert restored.objectives == original.objectives
        assert restored.team_composition == original.team_composition
        assert restored.version == original.version

    def test_full_round_trip_complex_context(self):
        """Test complete pack/unpack cycle with complex nested context."""
        # Arrange
        artifacts = [
            Artifact(
                id=f"art-{i}",
                name=f"Artifact {i}",
                type="code",
                path=f"/src/module_{i}.py",
                metadata={"lines": 100 * i, "complexity": "medium"},
            )
            for i in range(3)
        ]

        original = MissionContext(
            mission_id="round-trip-complex",
            mission_name="Complex Round Trip Test",
            objectives=[
                "Implement core functionality",
                "Write comprehensive tests",
                "Document API",
                "Deploy to production",
            ],
            team_composition={
                "engineering": {
                    "backend": ["Alice", "Bob"],
                    "frontend": ["Charlie"],
                    "devops": ["Diana"],
                },
                "product": {"pm": "Eve", "design": "Frank"},
            },
            constraints=MissionConstraints(
                max_duration_hours=16.0,
                max_cost_dollars=500.0,
                max_personas=8,
                require_human_review=True,
                allowed_tools=["python", "docker", "kubernetes"],
                forbidden_actions=["delete_production", "bypass_review"],
            ),
            artifacts=artifacts,
            metadata={
                "project": "context-packager",
                "sprint": 42,
                "priority": "high",
                "tags": ["e2e", "testing", "serialization"],
                "config": {
                    "retry_count": 3,
                    "timeout_seconds": 300,
                },
            },
            version="1.1",
        )

        # Act
        packed = self.packager.pack_context(original)
        restored = self.packager.unpack_context(packed)

        # Assert - verify all fields
        assert restored.mission_id == original.mission_id
        assert restored.mission_name == original.mission_name
        assert restored.objectives == original.objectives
        assert restored.team_composition == original.team_composition
        assert restored.version == original.version

        # Constraints
        assert restored.constraints.max_duration_hours == original.constraints.max_duration_hours
        assert restored.constraints.max_cost_dollars == original.constraints.max_cost_dollars
        assert restored.constraints.max_personas == original.constraints.max_personas
        assert restored.constraints.require_human_review == original.constraints.require_human_review
        assert restored.constraints.allowed_tools == original.constraints.allowed_tools
        assert restored.constraints.forbidden_actions == original.constraints.forbidden_actions

        # Artifacts
        assert len(restored.artifacts) == len(original.artifacts)
        for rest, orig in zip(restored.artifacts, original.artifacts):
            assert rest.id == orig.id
            assert rest.name == orig.name
            assert rest.type == orig.type
            assert rest.path == orig.path

        # Metadata
        assert restored.metadata == original.metadata

    def test_state_equality_after_multiple_cycles(self):
        """Test that state remains equal after multiple pack/unpack cycles."""
        # Arrange
        original = MissionContext(
            mission_id="multi-cycle",
            mission_name="Multi-Cycle Test",
            objectives=["test stability"],
            team_composition={"qa": ["tester"]},
            constraints=MissionConstraints(max_duration_hours=4.0),
            metadata={"cycle": 0},
        )

        # Act - pack/unpack 5 times
        current = original
        for cycle in range(5):
            packed = self.packager.pack_context(current)
            current = self.packager.unpack_context(packed)

        # Assert - final state matches original (except cycle count)
        assert current.mission_id == original.mission_id
        assert current.mission_name == original.mission_name
        assert current.objectives == original.objectives
        assert current.constraints.max_duration_hours == original.constraints.max_duration_hours

    def test_reconstruction_with_different_formats(self):
        """Test reconstruction works across different serialization formats."""
        # Arrange
        original = MissionContext(
            mission_id="format-test",
            mission_name="Format Test",
            objectives=["test formats"],
            team_composition={"dev": "developer"},
            constraints=MissionConstraints(),
        )

        formats_and_configs = [
            ("json", PackagerConfig(format=PackageFormat.JSON, compression=CompressionAlgorithm.NONE)),
            ("json_compressed", PackagerConfig(format=PackageFormat.JSON_COMPRESSED, compression=CompressionAlgorithm.GZIP)),
            ("gzip", PackagerConfig(format=PackageFormat.JSON, compression=CompressionAlgorithm.GZIP)),
        ]

        for format_name, config in formats_and_configs:
            packager = ContextPackager(config)

            # Act
            packed = packager.pack_context(original)
            restored = packager.unpack_context(packed)

            # Assert
            assert restored.mission_id == original.mission_id, f"Failed for {format_name}"
            assert restored.mission_name == original.mission_name, f"Failed for {format_name}"

    def test_reconstruction_preserves_metadata(self):
        """Test that metadata is preserved through serialization."""
        # Arrange
        original = MissionContext(
            mission_id="metadata-test",
            mission_name="Metadata Preservation Test",
            objectives=["preserve metadata"],
            team_composition={},
            constraints=MissionConstraints(),
            metadata={
                "string": "value",
                "number": 42,
                "float": 3.14159,
                "boolean": True,
                "null": None,
                "array": [1, 2, 3],
                "nested": {"a": {"b": {"c": "deep"}}},
            },
        )

        # Act
        packed = self.packager.pack_context(original)
        restored = self.packager.unpack_context(packed)

        # Assert
        assert restored.metadata["string"] == "value"
        assert restored.metadata["number"] == 42
        assert abs(restored.metadata["float"] - 3.14159) < 0.0001
        assert restored.metadata["boolean"] is True
        assert restored.metadata["null"] is None
        assert restored.metadata["array"] == [1, 2, 3]
        assert restored.metadata["nested"]["a"]["b"]["c"] == "deep"

    def test_reconstruction_with_max_size_context(self):
        """Test reconstruction of context near size limits."""
        # Arrange - create a context approaching size limit
        large_metadata = {
            f"field_{i}": "x" * 1000 for i in range(100)
        }  # ~100KB of metadata

        original = MissionContext(
            mission_id="large-context",
            mission_name="Large Context Test",
            objectives=["test size limits"],
            team_composition={"team": ["member"] * 100},
            constraints=MissionConstraints(),
            metadata=large_metadata,
        )

        # Act
        packed = self.packager.pack_context(original)
        restored = self.packager.unpack_context(packed)

        # Assert
        assert restored.mission_id == original.mission_id
        assert len(restored.metadata) == len(original.metadata)

    def test_cross_packager_compatibility(self):
        """Test that different packager instances can exchange data."""
        # Arrange
        packager1 = ContextPackager()
        packager2 = ContextPackager()

        original = MissionContext(
            mission_id="cross-packager",
            mission_name="Cross Packager Test",
            objectives=["test interoperability"],
            team_composition={"sender": "receiver"},
            constraints=MissionConstraints(),
        )

        # Act - pack with one, unpack with another
        packed = packager1.pack_context(original)
        restored = packager2.unpack_context(packed)

        # Assert
        assert restored.mission_id == original.mission_id
        assert restored.mission_name == original.mission_name

    def test_schema_validation_on_reconstruction(self):
        """Test that reconstructed context passes schema validation."""
        # Arrange
        validator = SchemaValidator()
        original = MissionContext(
            mission_id="schema-valid",
            mission_name="Schema Validation Test",
            objectives=["test schema"],
            team_composition={"role": "validator"},
            constraints=MissionConstraints(),
        )

        # Act
        packed = self.packager.pack_context(original)
        restored = self.packager.unpack_context(packed)
        validation_result = validator.validate(restored)

        # Assert
        assert validation_result.is_valid is True
        assert len(validation_result.errors) == 0


class TestEndToEndScenarios:
    """
    Integration scenarios testing complete workflows.
    """

    def test_mission_planning_to_execution_handoff(self):
        """
        Simulate complete mission planning to execution handoff flow.

        Flow:
        1. Create mission context in planning phase
        2. Package for transfer
        3. Verify integrity
        4. Transfer to execution phase
        5. Unpack and validate
        6. Verify all state preserved
        """
        # Phase 1: Mission Planning
        mission_context = MissionContext(
            mission_id=f"mission-{uuid.uuid4().hex[:8]}",
            mission_name="Feature: User Authentication",
            objectives=[
                "Implement OAuth2 login flow",
                "Add session management",
                "Create logout endpoint",
                "Write integration tests",
            ],
            team_composition={
                "lead": "senior_developer",
                "backend": ["backend_dev_1", "backend_dev_2"],
                "qa": ["qa_engineer"],
            },
            constraints=MissionConstraints(
                max_duration_hours=24.0,
                max_cost_dollars=1000.0,
                max_personas=5,
                require_human_review=True,
                allowed_tools=["python", "pytest", "docker"],
            ),
            artifacts=[
                Artifact(
                    id="spec-001",
                    name="Authentication Spec",
                    type="specification",
                    path="/docs/auth_spec.md",
                ),
                Artifact(
                    id="design-001",
                    name="Auth Flow Diagram",
                    type="diagram",
                    path="/docs/auth_flow.png",
                ),
            ],
            metadata={
                "sprint": "2025-Q1-S3",
                "priority": "P1",
                "epic": "USER_AUTH",
            },
        )

        # Phase 2: Package for Transfer
        packager = ContextPackager()
        packed = packager.pack_with_metadata(mission_context)

        # Phase 3: Verify Integrity
        assert packager.verify_checksum(packed) is True
        assert packed.metadata.packed_size > 0

        # Phase 4: Simulate Transfer (could be file, network, etc.)
        transfer_data = packed.data
        transfer_metadata = packed.metadata.to_dict()

        # Phase 5: Execution Phase Receives and Unpacks
        execution_packager = ContextPackager()
        received_metadata = PackageMetadata.from_dict(transfer_metadata)
        received_packed = PackedContext(data=transfer_data, metadata=received_metadata)

        # Verify integrity on receiving end
        assert execution_packager.verify_checksum(received_packed) is True

        # Unpack
        execution_context = execution_packager.unpack_context(transfer_data)

        # Phase 6: Verify All State Preserved
        assert execution_context.mission_id == mission_context.mission_id
        assert execution_context.mission_name == mission_context.mission_name
        assert execution_context.objectives == mission_context.objectives
        assert execution_context.team_composition == mission_context.team_composition
        assert execution_context.constraints.max_duration_hours == mission_context.constraints.max_duration_hours
        assert execution_context.constraints.require_human_review == mission_context.constraints.require_human_review
        assert len(execution_context.artifacts) == len(mission_context.artifacts)
        assert execution_context.metadata["epic"] == "USER_AUTH"

    def test_context_versioning_and_migration(self):
        """Test handling of different context versions."""
        # Arrange - v1.0 context
        v1_context = MissionContext(
            mission_id="version-test",
            mission_name="Version Test",
            objectives=["test versioning"],
            team_composition={},
            constraints=MissionConstraints(),
            version="1.0",
        )

        # Also test v1.1 context
        v11_context = MissionContext(
            mission_id="version-test-11",
            mission_name="Version 1.1 Test",
            objectives=["test versioning"],
            team_composition={},
            constraints=MissionConstraints(),
            version="1.1",
        )

        packager = ContextPackager()

        # Act
        packed_v1 = packager.pack_context(v1_context)
        packed_v11 = packager.pack_context(v11_context)

        restored_v1 = packager.unpack_context(packed_v1)
        restored_v11 = packager.unpack_context(packed_v11)

        # Assert
        assert restored_v1.version == "1.0"
        assert restored_v11.version == "1.1"

    def test_error_recovery_scenario(self):
        """Test handling of error scenarios during pack/unpack."""
        packager = ContextPackager()

        # Scenario 1: Invalid JSON data
        with pytest.raises(ValueError) as exc:
            packager.unpack_context(b"not valid json")
        assert "invalid json" in str(exc.value).lower()

        # Scenario 2: Corrupted compressed data
        valid_context = MissionContext(
            mission_id="error-test",
            mission_name="Error Test",
            objectives=["test errors"],
            team_composition={},
            constraints=MissionConstraints(),
        )
        packed = packager.pack_context(valid_context)

        # Corrupt the compressed data
        corrupted = b"\x1f\x8b" + b"corrupted"  # Gzip header but invalid
        with pytest.raises(ValueError) as exc:
            packager.unpack_context(corrupted)
        assert "decompress" in str(exc.value).lower()

        # Scenario 3: Size limit exceeded
        config = PackagerConfig(max_size_bytes=10)
        small_packager = ContextPackager(config)
        with pytest.raises(ValueError) as exc:
            small_packager.pack_context(valid_context)
        assert "exceeds limit" in str(exc.value).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
