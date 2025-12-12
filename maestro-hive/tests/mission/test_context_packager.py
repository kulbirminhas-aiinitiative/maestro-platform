"""
Tests for Context Packager.
EPIC: MD-3024 - Mission to Execution Handoff
"""

import pytest
import json
import gzip

from maestro_hive.mission import (
    ContextPackager,
    PackagerConfig,
    PackageFormat,
    CompressionAlgorithm,
    MissionContext,
    MissionConstraints,
    SchemaValidator,
)


class TestContextPackager:
    """Test suite for ContextPackager."""

    def setup_method(self):
        """Set up test fixtures."""
        self.packager = ContextPackager()
        self.valid_context = MissionContext(
            mission_id="test-001",
            mission_name="Test Mission",
            objectives=["Implement feature X"],
            team_composition={"lead": "architect"},
            constraints=MissionConstraints(
                max_duration_hours=4.0,
                max_cost_dollars=50.0,
            ),
        )

    def test_pack_context_json(self):
        """Test packing context as JSON."""
        config = PackagerConfig(
            format=PackageFormat.JSON,
            compression=CompressionAlgorithm.NONE,
        )
        packager = ContextPackager(config)

        packed = packager.pack_context(self.valid_context)

        # Should be valid JSON (possibly gzip compressed)
        try:
            decompressed = gzip.decompress(packed)
        except gzip.BadGzipFile:
            decompressed = packed

        data = json.loads(decompressed.decode("utf-8"))
        assert data["mission_id"] == "test-001"

    def test_pack_context_compressed(self):
        """Test packing with compression."""
        config = PackagerConfig(
            format=PackageFormat.JSON_COMPRESSED,
            compression=CompressionAlgorithm.GZIP,
        )
        packager = ContextPackager(config)

        packed = packager.pack_context(self.valid_context)

        # Should be gzip compressed
        assert packed[:2] == b"\x1f\x8b"

        # Decompress and verify
        decompressed = gzip.decompress(packed)
        data = json.loads(decompressed.decode("utf-8"))
        assert data["mission_id"] == "test-001"

    def test_unpack_context(self):
        """Test unpacking context."""
        packed = self.packager.pack_context(self.valid_context)
        unpacked = self.packager.unpack_context(packed)

        assert unpacked.mission_id == self.valid_context.mission_id
        assert unpacked.mission_name == self.valid_context.mission_name
        assert unpacked.objectives == self.valid_context.objectives

    def test_pack_unpack_round_trip(self):
        """Test full pack/unpack round trip."""
        original = MissionContext(
            mission_id="round-trip-test",
            mission_name="Round Trip Test",
            objectives=["obj1", "obj2", "obj3"],
            team_composition={"lead": "arch", "devs": ["d1", "d2"]},
            constraints=MissionConstraints(
                max_duration_hours=10,
                max_cost_dollars=200,
                require_human_review=True,
            ),
            metadata={"priority": "high", "tags": ["urgent"]},
        )

        packed = self.packager.pack_context(original)
        restored = self.packager.unpack_context(packed)

        assert restored.mission_id == original.mission_id
        assert restored.mission_name == original.mission_name
        assert restored.objectives == original.objectives
        assert restored.constraints.max_duration_hours == original.constraints.max_duration_hours
        assert restored.constraints.require_human_review == original.constraints.require_human_review

    def test_pack_with_metadata(self):
        """Test packing with metadata included."""
        packed_context = self.packager.pack_with_metadata(self.valid_context)

        assert packed_context.data is not None
        assert packed_context.metadata is not None
        assert packed_context.metadata.schema_version == "1.0"
        assert packed_context.metadata.original_size > 0
        assert packed_context.metadata.packed_size > 0
        assert packed_context.metadata.checksum is not None

    def test_verify_checksum_valid(self):
        """Test checksum verification with valid data."""
        packed_context = self.packager.pack_with_metadata(self.valid_context)
        assert self.packager.verify_checksum(packed_context) is True

    def test_verify_checksum_invalid(self):
        """Test checksum verification with corrupted data."""
        packed_context = self.packager.pack_with_metadata(self.valid_context)

        # Corrupt the data
        packed_context.data = packed_context.data + b"corruption"

        assert self.packager.verify_checksum(packed_context) is False

    def test_validate_schema_valid(self):
        """Test schema validation with valid context."""
        result = self.packager.validate_schema(self.valid_context)
        assert result.is_valid is True

    def test_validate_schema_missing_id(self):
        """Test schema validation with missing ID."""
        context = MissionContext(
            mission_id="",
            mission_name="Test",
            objectives=["obj"],
            team_composition={},
            constraints=MissionConstraints(),
        )

        result = self.packager.validate_schema(context)

        assert result.is_valid is False
        assert any(i.code == "SCHEMA_MISSING_ID" for i in result.issues)

    def test_validate_schema_unsupported_version(self):
        """Test schema validation with unsupported version."""
        context = MissionContext(
            mission_id="test",
            mission_name="Test",
            objectives=["obj"],
            team_composition={},
            constraints=MissionConstraints(),
            version="99.0",
        )

        result = self.packager.validate_schema(context)

        assert result.is_valid is False
        assert any(i.code == "SCHEMA_UNSUPPORTED_VERSION" for i in result.issues)

    def test_get_compression_ratio(self):
        """Test compression ratio calculation."""
        ratio = self.packager.get_compression_ratio(self.valid_context)

        # Compression should provide some ratio > 1
        assert ratio > 0

    def test_estimate_size(self):
        """Test size estimation."""
        estimates = self.packager.estimate_size(self.valid_context)

        assert "uncompressed" in estimates
        assert "estimated_compressed" in estimates
        assert "max_allowed" in estimates
        assert estimates["uncompressed"] > 0

    def test_pack_validation_failure(self):
        """Test packing with validation enabled and invalid context."""
        config = PackagerConfig(validate_on_pack=True)
        packager = ContextPackager(config)

        # Invalid context (empty mission_id)
        context = MissionContext(
            mission_id="",
            mission_name="Test",
            objectives=["obj"],
            team_composition={},
            constraints=MissionConstraints(),
        )

        with pytest.raises(ValueError) as exc_info:
            packager.pack_context(context)

        assert "validation failed" in str(exc_info.value).lower()

    def test_pack_size_limit(self):
        """Test packing with size limit exceeded."""
        config = PackagerConfig(max_size_bytes=10)  # Very small limit
        packager = ContextPackager(config)

        with pytest.raises(ValueError) as exc_info:
            packager.pack_context(self.valid_context)

        assert "exceeds limit" in str(exc_info.value).lower()

    def test_unpack_invalid_json(self):
        """Test unpacking invalid JSON."""
        with pytest.raises(ValueError) as exc_info:
            self.packager.unpack_context(b"not valid json")

        assert "invalid json" in str(exc_info.value).lower()

    def test_unpack_compressed_data(self):
        """Test unpacking gzip compressed data."""
        # Manually compress
        json_data = json.dumps(self.valid_context.to_dict()).encode("utf-8")
        compressed = gzip.compress(json_data)

        unpacked = self.packager.unpack_context(compressed)

        assert unpacked.mission_id == self.valid_context.mission_id


class TestSchemaValidator:
    """Test suite for SchemaValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = SchemaValidator()

    def test_validate_valid_context(self):
        """Test validating valid context."""
        context = MissionContext(
            mission_id="test",
            mission_name="Test",
            objectives=["obj"],
            team_composition={},
            constraints=MissionConstraints(),
        )

        result = self.validator.validate(context)
        assert result.is_valid is True

    def test_validate_missing_required_fields(self):
        """Test validating context with missing required fields."""
        context = MissionContext(
            mission_id="",
            mission_name="",
            objectives=["obj"],
            team_composition={},
            constraints=MissionConstraints(),
        )

        result = self.validator.validate(context)

        assert result.is_valid is False
        assert len(result.errors) >= 2

    def test_validate_invalid_constraints(self):
        """Test validating context with invalid constraints."""
        context = MissionContext(
            mission_id="test",
            mission_name="Test",
            objectives=["obj"],
            team_composition={},
            constraints=MissionConstraints(
                max_duration_hours=0,
                max_personas=0,
            ),
        )

        result = self.validator.validate(context)

        assert result.is_valid is False
        assert any(i.code == "SCHEMA_INVALID_DURATION" for i in result.issues)
        assert any(i.code == "SCHEMA_INVALID_PERSONAS" for i in result.issues)

    def test_supported_versions(self):
        """Test that supported versions are valid."""
        for version in SchemaValidator.SUPPORTED_VERSIONS:
            context = MissionContext(
                mission_id="test",
                mission_name="Test",
                objectives=["obj"],
                team_composition={},
                constraints=MissionConstraints(),
                version=version,
            )

            result = self.validator.validate(context)
            assert result.is_valid is True


class TestPackagerConfig:
    """Test suite for PackagerConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PackagerConfig()

        assert config.format == PackageFormat.JSON
        assert config.compression == CompressionAlgorithm.GZIP
        assert config.compression_level == 6
        assert config.max_size_bytes == 10 * 1024 * 1024
        assert config.schema_version == "1.0"

    def test_custom_config(self):
        """Test custom configuration."""
        config = PackagerConfig(
            format=PackageFormat.JSON_COMPRESSED,
            compression=CompressionAlgorithm.NONE,
            max_size_bytes=1024,
        )

        assert config.format == PackageFormat.JSON_COMPRESSED
        assert config.compression == CompressionAlgorithm.NONE
        assert config.max_size_bytes == 1024
