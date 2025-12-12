"""
Context Packager for Mission State Serialization.
EPIC: MD-3024 - Mission to Execution Handoff

Handles serialization and deserialization of mission context
for handoff between planning and execution phases.
"""

import json
import gzip
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional, List

from .handoff_coordinator import MissionContext, ValidationResult, ValidationIssue, ValidationSeverity

logger = logging.getLogger(__name__)


class PackageFormat(Enum):
    """Supported package formats."""
    JSON = "json"
    JSON_COMPRESSED = "json_compressed"
    MSGPACK = "msgpack"


class CompressionAlgorithm(Enum):
    """Supported compression algorithms."""
    NONE = "none"
    GZIP = "gzip"
    ZSTD = "zstd"


@dataclass
class PackagerConfig:
    """Configuration for context packager."""
    format: PackageFormat = PackageFormat.JSON
    compression: CompressionAlgorithm = CompressionAlgorithm.GZIP
    compression_level: int = 6
    max_size_bytes: int = 10 * 1024 * 1024  # 10 MB
    schema_version: str = "1.0"
    include_metadata: bool = True
    validate_on_pack: bool = True


@dataclass
class PackageMetadata:
    """Metadata about a packed context."""
    schema_version: str
    format: str
    compression: str
    original_size: int
    packed_size: int
    checksum: str
    packed_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "schema_version": self.schema_version,
            "format": self.format,
            "compression": self.compression,
            "original_size": self.original_size,
            "packed_size": self.packed_size,
            "checksum": self.checksum,
            "packed_at": self.packed_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PackageMetadata":
        """Create from dictionary."""
        packed_at = data.get("packed_at")
        if isinstance(packed_at, str):
            packed_at = datetime.fromisoformat(packed_at.replace("Z", "+00:00"))
        elif packed_at is None:
            packed_at = datetime.utcnow()

        return cls(
            schema_version=data["schema_version"],
            format=data["format"],
            compression=data["compression"],
            original_size=data["original_size"],
            packed_size=data["packed_size"],
            checksum=data["checksum"],
            packed_at=packed_at,
        )


@dataclass
class PackedContext:
    """A packed mission context with metadata."""
    data: bytes
    metadata: PackageMetadata


class SchemaValidator:
    """Validates mission context against schema."""

    REQUIRED_FIELDS = ["mission_id", "mission_name", "version"]
    SUPPORTED_VERSIONS = ["1.0", "1.1"]

    def validate(self, context: MissionContext) -> ValidationResult:
        """
        Validate context against schema.

        Args:
            context: Context to validate

        Returns:
            ValidationResult with any issues found
        """
        issues: List[ValidationIssue] = []

        # Check required fields
        if not context.mission_id:
            issues.append(ValidationIssue(
                code="SCHEMA_MISSING_ID",
                message="mission_id is required by schema",
                severity=ValidationSeverity.ERROR,
                field="mission_id",
            ))

        if not context.mission_name:
            issues.append(ValidationIssue(
                code="SCHEMA_MISSING_NAME",
                message="mission_name is required by schema",
                severity=ValidationSeverity.ERROR,
                field="mission_name",
            ))

        # Check version
        if context.version not in self.SUPPORTED_VERSIONS:
            issues.append(ValidationIssue(
                code="SCHEMA_UNSUPPORTED_VERSION",
                message=f"Version {context.version} not supported",
                severity=ValidationSeverity.ERROR,
                field="version",
                suggestion=f"Use one of: {', '.join(self.SUPPORTED_VERSIONS)}",
            ))

        # Check constraints
        if context.constraints:
            if context.constraints.max_duration_hours <= 0:
                issues.append(ValidationIssue(
                    code="SCHEMA_INVALID_DURATION",
                    message="max_duration_hours must be positive",
                    severity=ValidationSeverity.ERROR,
                    field="constraints.max_duration_hours",
                ))

            if context.constraints.max_personas <= 0:
                issues.append(ValidationIssue(
                    code="SCHEMA_INVALID_PERSONAS",
                    message="max_personas must be positive",
                    severity=ValidationSeverity.ERROR,
                    field="constraints.max_personas",
                ))

        is_valid = not any(i.severity == ValidationSeverity.ERROR for i in issues)

        return ValidationResult(is_valid=is_valid, issues=issues)


class ContextPackager:
    """
    Packs and unpacks mission context for transfer.

    Handles:
    - JSON serialization
    - Compression (gzip)
    - Schema validation
    - Checksum verification

    Example:
        packager = ContextPackager()
        packed = packager.pack_context(context)
        unpacked = packager.unpack_context(packed)
    """

    def __init__(self, config: Optional[PackagerConfig] = None):
        """
        Initialize packager.

        Args:
            config: Packager configuration
        """
        self.config = config or PackagerConfig()
        self._schema_validator = SchemaValidator()
        logger.info(f"ContextPackager initialized with format={self.config.format.value}")

    def pack_context(
        self,
        context: MissionContext,
        format: Optional[PackageFormat] = None,
    ) -> bytes:
        """
        Serialize and optionally compress mission context.

        Args:
            context: Mission context to pack
            format: Override format from config

        Returns:
            Packed context as bytes

        Raises:
            ValueError: If validation fails or size exceeds limit
        """
        format = format or self.config.format

        # Validate schema
        if self.config.validate_on_pack:
            validation = self._schema_validator.validate(context)
            if not validation.is_valid:
                errors = [i.message for i in validation.errors]
                raise ValueError(f"Schema validation failed: {'; '.join(errors)}")

        # Serialize to JSON
        context_dict = context.to_dict()

        # Add packaging metadata
        if self.config.include_metadata:
            context_dict["_package_meta"] = {
                "schema_version": self.config.schema_version,
                "packed_at": datetime.utcnow().isoformat(),
            }

        json_bytes = json.dumps(context_dict, indent=None, separators=(",", ":")).encode("utf-8")
        original_size = len(json_bytes)

        # Compress if configured
        if format == PackageFormat.JSON_COMPRESSED or self.config.compression == CompressionAlgorithm.GZIP:
            packed_data = gzip.compress(json_bytes, compresslevel=self.config.compression_level)
            logger.debug(f"Compressed: {original_size} -> {len(packed_data)} bytes")
        else:
            packed_data = json_bytes

        # Check size limit
        if len(packed_data) > self.config.max_size_bytes:
            raise ValueError(
                f"Packed size ({len(packed_data)}) exceeds limit ({self.config.max_size_bytes})"
            )

        logger.info(f"Packed context: {original_size} -> {len(packed_data)} bytes")

        return packed_data

    def unpack_context(
        self,
        data: bytes,
        format: Optional[PackageFormat] = None,
    ) -> MissionContext:
        """
        Deserialize mission context from packed bytes.

        Args:
            data: Packed context bytes
            format: Override format detection

        Returns:
            Unpacked MissionContext

        Raises:
            ValueError: If unpacking fails
        """
        format = format or self.config.format

        # Detect if compressed (gzip magic bytes)
        is_compressed = data[:2] == b"\x1f\x8b"

        if is_compressed:
            try:
                json_bytes = gzip.decompress(data)
            except Exception as e:
                raise ValueError(f"Failed to decompress: {e}")
        else:
            json_bytes = data

        # Parse JSON
        try:
            context_dict = json.loads(json_bytes.decode("utf-8"))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

        # Remove packaging metadata before parsing
        context_dict.pop("_package_meta", None)

        # Create context
        context = MissionContext.from_dict(context_dict)

        logger.info(f"Unpacked context: mission_id={context.mission_id}")

        return context

    def pack_with_metadata(self, context: MissionContext) -> PackedContext:
        """
        Pack context and return with metadata.

        Args:
            context: Context to pack

        Returns:
            PackedContext with data and metadata
        """
        # Serialize to get original size
        json_bytes = json.dumps(context.to_dict(), indent=None).encode("utf-8")
        original_size = len(json_bytes)

        # Pack
        packed_data = self.pack_context(context)

        # Calculate checksum
        checksum = hashlib.sha256(packed_data).hexdigest()

        metadata = PackageMetadata(
            schema_version=self.config.schema_version,
            format=self.config.format.value,
            compression=self.config.compression.value,
            original_size=original_size,
            packed_size=len(packed_data),
            checksum=checksum,
        )

        return PackedContext(data=packed_data, metadata=metadata)

    def validate_schema(self, context: MissionContext) -> ValidationResult:
        """
        Validate context against schema.

        Args:
            context: Context to validate

        Returns:
            ValidationResult with any issues
        """
        return self._schema_validator.validate(context)

    def verify_checksum(self, packed: PackedContext) -> bool:
        """
        Verify packed context checksum.

        Args:
            packed: Packed context to verify

        Returns:
            True if checksum matches
        """
        calculated = hashlib.sha256(packed.data).hexdigest()
        return calculated == packed.metadata.checksum

    def get_compression_ratio(self, context: MissionContext) -> float:
        """
        Calculate compression ratio for a context.

        Args:
            context: Context to analyze

        Returns:
            Compression ratio (original / compressed)
        """
        json_bytes = json.dumps(context.to_dict()).encode("utf-8")
        original_size = len(json_bytes)

        packed = self.pack_context(context)
        packed_size = len(packed)

        if packed_size == 0:
            return 1.0

        return original_size / packed_size

    def estimate_size(self, context: MissionContext) -> Dict[str, int]:
        """
        Estimate packed size without actually packing.

        Args:
            context: Context to estimate

        Returns:
            Dictionary with size estimates
        """
        json_bytes = json.dumps(context.to_dict()).encode("utf-8")

        # Rough compression estimate (typically 2-5x for JSON)
        estimated_compressed = len(json_bytes) // 3

        return {
            "uncompressed": len(json_bytes),
            "estimated_compressed": estimated_compressed,
            "max_allowed": self.config.max_size_bytes,
        }
