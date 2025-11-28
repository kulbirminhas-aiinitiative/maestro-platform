"""
ACC Contract Tests: EventType Schema Validation & Schema Registry
Test IDs: ACC-100 to ACC-150

Tests for event schema contracts:
- Schema registry integration
- Event versioning (semantic versioning)
- Breaking change detection
- Backward/forward compatibility
- Schema evolution rules
- Contract validation

These tests ensure:
1. All events conform to registered schemas
2. Schema changes follow compatibility rules
3. Breaking changes are detected and rejected
4. Version management is enforced
"""

import pytest
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import re


class CompatibilityMode(Enum):
    """Schema compatibility modes"""
    BACKWARD = "BACKWARD"  # Consumers using old schema can read new data
    FORWARD = "FORWARD"  # Consumers using new schema can read old data
    FULL = "FULL"  # Both backward and forward compatible
    NONE = "NONE"  # No compatibility checks


class SchemaType(Enum):
    """Schema definition types"""
    JSON_SCHEMA = "JSON_SCHEMA"
    AVRO = "AVRO"
    PROTOBUF = "PROTOBUF"


@dataclass
class SchemaVersion:
    """Schema version information"""
    subject: str
    version: str  # Semantic version (e.g., "v1.2.3")
    schema: Dict[str, Any]
    schema_type: SchemaType = SchemaType.JSON_SCHEMA
    compatibility: CompatibilityMode = CompatibilityMode.BACKWARD
    created_at: Optional[str] = None

    def get_major_version(self) -> int:
        """Extract major version number"""
        match = re.match(r'v?(\d+)', self.version)
        return int(match.group(1)) if match else 0

    def get_minor_version(self) -> int:
        """Extract minor version number"""
        match = re.match(r'v?\d+\.(\d+)', self.version)
        return int(match.group(1)) if match else 0

    def get_patch_version(self) -> int:
        """Extract patch version number"""
        match = re.match(r'v?\d+\.\d+\.(\d+)', self.version)
        return int(match.group(1)) if match else 0


class BreakingChangeError(Exception):
    """Raised when a breaking schema change is detected"""
    pass


class SchemaValidationError(Exception):
    """Raised when schema validation fails"""
    pass


class SchemaRegistry:
    """In-memory schema registry for testing"""

    def __init__(self):
        self._schemas: Dict[str, List[SchemaVersion]] = {}

    def register(
        self,
        subject: str,
        schema: Dict[str, Any],
        version: Optional[str] = None,
        compatibility: CompatibilityMode = CompatibilityMode.BACKWARD
    ) -> SchemaVersion:
        """
        Register a new schema version.

        Args:
            subject: Schema subject (e.g., "user.created")
            schema: Schema definition (JSON Schema format)
            version: Optional version string (auto-incremented if not provided)
            compatibility: Compatibility mode for validation

        Returns:
            SchemaVersion object

        Raises:
            BreakingChangeError: If schema is not compatible with previous version
        """
        # Get existing versions
        existing_versions = self._schemas.get(subject, [])

        # Determine version
        if version is None:
            if not existing_versions:
                version = "v1.0.0"
            else:
                # Auto-increment patch version
                latest = existing_versions[-1]
                patch = latest.get_patch_version() + 1
                version = f"v{latest.get_major_version()}.{latest.get_minor_version()}.{patch}"

        # Check compatibility with previous version
        if existing_versions and compatibility != CompatibilityMode.NONE:
            latest = existing_versions[-1]
            if not self._is_compatible(latest.schema, schema, compatibility):
                breaking_changes = self._find_breaking_changes(latest.schema, schema)
                raise BreakingChangeError(
                    f"Schema for {subject} v{version} has breaking changes: {breaking_changes}"
                )

        # Create schema version
        schema_version = SchemaVersion(
            subject=subject,
            version=version,
            schema=schema,
            compatibility=compatibility
        )

        # Store
        if subject not in self._schemas:
            self._schemas[subject] = []
        self._schemas[subject].append(schema_version)

        return schema_version

    def get_schema(self, subject: str, version: Optional[str] = None) -> Optional[SchemaVersion]:
        """Get schema for subject (latest version if not specified)"""
        versions = self._schemas.get(subject, [])
        if not versions:
            return None

        if version is None:
            return versions[-1]

        for sv in versions:
            if sv.version == version:
                return sv

        return None

    def list_versions(self, subject: str) -> List[str]:
        """List all versions for a subject"""
        versions = self._schemas.get(subject, [])
        return [sv.version for sv in versions]

    def validate_event(self, subject: str, event_data: Dict[str, Any], version: Optional[str] = None) -> bool:
        """
        Validate event data against schema.

        Args:
            subject: Schema subject
            event_data: Event data to validate
            version: Schema version (uses latest if not specified)

        Returns:
            True if valid

        Raises:
            SchemaValidationError: If validation fails
        """
        schema_version = self.get_schema(subject, version)
        if not schema_version:
            raise SchemaValidationError(f"No schema found for subject {subject}")

        # Validate against JSON Schema
        errors = self._validate_json_schema(schema_version.schema, event_data)
        if errors:
            raise SchemaValidationError(f"Validation errors: {errors}")

        return True

    def _is_compatible(
        self,
        old_schema: Dict[str, Any],
        new_schema: Dict[str, Any],
        mode: CompatibilityMode
    ) -> bool:
        """Check if new schema is compatible with old schema"""
        if mode == CompatibilityMode.BACKWARD:
            # Backward compatible: new schema can read old data
            # Rules: Can't remove required fields, can add optional fields
            return self._is_backward_compatible(old_schema, new_schema)
        elif mode == CompatibilityMode.FORWARD:
            # Forward compatible: old schema can read new data
            # Rules: Can't add required fields, can remove optional fields
            return self._is_forward_compatible(old_schema, new_schema)
        elif mode == CompatibilityMode.FULL:
            # Both backward and forward compatible
            return (
                self._is_backward_compatible(old_schema, new_schema) and
                self._is_forward_compatible(old_schema, new_schema)
            )
        return True

    def _is_backward_compatible(self, old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> bool:
        """Check backward compatibility"""
        old_required = set(old_schema.get("required", []))
        new_required = set(new_schema.get("required", []))

        # Can't remove required fields
        removed_required = old_required - new_required
        if removed_required:
            return False

        # Check field types haven't changed
        old_props = old_schema.get("properties", {})
        new_props = new_schema.get("properties", {})

        for field, old_type_def in old_props.items():
            if field in new_props:
                old_type = old_type_def.get("type")
                new_type = new_props[field].get("type")
                if old_type != new_type:
                    return False

        return True

    def _is_forward_compatible(self, old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> bool:
        """Check forward compatibility"""
        old_required = set(old_schema.get("required", []))
        new_required = set(new_schema.get("required", []))

        # Can't add required fields
        added_required = new_required - old_required
        if added_required:
            return False

        return True

    def _find_breaking_changes(self, old_schema: Dict[str, Any], new_schema: Dict[str, Any]) -> List[str]:
        """Find breaking changes between schemas"""
        changes = []

        old_required = set(old_schema.get("required", []))
        new_required = set(new_schema.get("required", []))

        removed = old_required - new_required
        if removed:
            changes.append(f"Removed required fields: {removed}")

        added = new_required - old_required
        if added:
            changes.append(f"Added required fields: {added}")

        # Check type changes
        old_props = old_schema.get("properties", {})
        new_props = new_schema.get("properties", {})

        for field, old_type_def in old_props.items():
            if field in new_props:
                old_type = old_type_def.get("type")
                new_type = new_props[field].get("type")
                if old_type != new_type:
                    changes.append(f"Changed type of {field}: {old_type} -> {new_type}")

        return changes

    def _validate_json_schema(self, schema: Dict[str, Any], data: Dict[str, Any]) -> List[str]:
        """Validate data against JSON schema (simplified)"""
        errors = []

        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Check field types
        properties = schema.get("properties", {})
        for field, value in data.items():
            if field in properties:
                expected_type = properties[field].get("type")
                actual_type = type(value).__name__

                # Map Python types to JSON Schema types
                type_map = {
                    "str": "string",
                    "int": "integer",
                    "float": "number",
                    "bool": "boolean",
                    "list": "array",
                    "dict": "object"
                }
                actual_type = type_map.get(actual_type, actual_type)

                if expected_type and expected_type != actual_type:
                    errors.append(f"Type mismatch for {field}: expected {expected_type}, got {actual_type}")

        return errors


@pytest.mark.acc
@pytest.mark.contract
class TestSchemaRegistry:
    """Test suite for schema registry operations"""

    @pytest.fixture
    def registry(self):
        """Create fresh schema registry for each test"""
        return SchemaRegistry()

    def test_acc_101_register_first_schema_version(self, registry):
        """ACC-101: First schema registration creates v1.0.0"""
        schema = {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "email": {"type": "string"}
            },
            "required": ["user_id", "email"]
        }

        result = registry.register("user.created", schema)

        assert result.subject == "user.created"
        assert result.version == "v1.0.0"
        assert result.schema == schema

    def test_acc_102_register_with_custom_version(self, registry):
        """ACC-102: Can register schema with custom version"""
        schema = {"type": "object", "properties": {}}

        result = registry.register("order.created", schema, version="v2.5.1")

        assert result.version == "v2.5.1"

    def test_acc_103_auto_increment_patch_version(self, registry):
        """ACC-103: Auto-increment creates next patch version"""
        schema1 = {"type": "object", "properties": {"field1": {"type": "string"}}}
        schema2 = {"type": "object", "properties": {"field1": {"type": "string"}, "field2": {"type": "string"}}}

        registry.register("event.test", schema1)
        result2 = registry.register("event.test", schema2)

        assert result2.version == "v1.0.1"

    def test_acc_104_get_latest_schema_version(self, registry):
        """ACC-104: Get latest schema version when version not specified"""
        schema1 = {"type": "object", "properties": {"v": {"type": "integer"}}}
        schema2 = {"type": "object", "properties": {"v": {"type": "integer"}}}

        registry.register("event.test", schema1, version="v1.0.0")
        registry.register("event.test", schema2, version="v1.1.0")

        latest = registry.get_schema("event.test")

        assert latest.version == "v1.1.0"

    def test_acc_105_get_specific_schema_version(self, registry):
        """ACC-105: Can retrieve specific schema version"""
        schema1 = {"properties": {"field": {"type": "string"}}}
        schema2 = {"properties": {"field": {"type": "integer"}}}

        registry.register("event.test", schema1, version="v1.0.0")
        registry.register("event.test", schema2, version="v2.0.0", compatibility=CompatibilityMode.NONE)

        v1 = registry.get_schema("event.test", version="v1.0.0")
        v2 = registry.get_schema("event.test", version="v2.0.0")

        assert v1.schema["properties"]["field"]["type"] == "string"
        assert v2.schema["properties"]["field"]["type"] == "integer"

    def test_acc_106_list_all_versions(self, registry):
        """ACC-106: Can list all versions for a subject"""
        schema = {"type": "object"}

        registry.register("event.test", schema, version="v1.0.0")
        registry.register("event.test", schema, version="v1.1.0")
        registry.register("event.test", schema, version="v2.0.0")

        versions = registry.list_versions("event.test")

        assert versions == ["v1.0.0", "v1.1.0", "v2.0.0"]


@pytest.mark.acc
@pytest.mark.contract
class TestBackwardCompatibility:
    """Test suite for backward compatibility checks"""

    @pytest.fixture
    def registry(self):
        return SchemaRegistry()

    def test_acc_110_add_optional_field_backward_compatible(self, registry):
        """ACC-110: Adding optional field is backward compatible"""
        old_schema = {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"}
            },
            "required": ["user_id"]
        }

        new_schema = {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "email": {"type": "string"}  # New optional field
            },
            "required": ["user_id"]
        }

        registry.register("user.created", old_schema)
        result = registry.register("user.created", new_schema)  # Should succeed

        assert result.version == "v1.0.1"

    def test_acc_111_remove_required_field_breaks_backward(self, registry):
        """ACC-111: Removing required field breaks backward compatibility"""
        old_schema = {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "email": {"type": "string"}
            },
            "required": ["user_id", "email"]
        }

        new_schema = {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"}
            },
            "required": ["user_id"]  # Removed email from required
        }

        registry.register("user.created", old_schema)

        with pytest.raises(BreakingChangeError, match="Removed required fields"):
            registry.register("user.created", new_schema)

    def test_acc_112_change_field_type_breaks_backward(self, registry):
        """ACC-112: Changing field type breaks backward compatibility"""
        old_schema = {
            "type": "object",
            "properties": {
                "age": {"type": "integer"}
            }
        }

        new_schema = {
            "type": "object",
            "properties": {
                "age": {"type": "string"}  # Changed type
            }
        }

        registry.register("user.updated", old_schema)

        with pytest.raises(BreakingChangeError, match="Changed type"):
            registry.register("user.updated", new_schema)


@pytest.mark.acc
@pytest.mark.contract
class TestForwardCompatibility:
    """Test suite for forward compatibility checks"""

    @pytest.fixture
    def registry(self):
        return SchemaRegistry()

    def test_acc_120_remove_optional_field_forward_compatible(self, registry):
        """ACC-120: Removing optional field is forward compatible"""
        old_schema = {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "temp_field": {"type": "string"}
            },
            "required": ["user_id"]
        }

        new_schema = {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"}
                # Removed temp_field
            },
            "required": ["user_id"]
        }

        registry.register("user.created", old_schema)
        result = registry.register(
            "user.created",
            new_schema,
            compatibility=CompatibilityMode.FORWARD
        )

        assert result is not None

    def test_acc_121_add_required_field_breaks_forward(self, registry):
        """ACC-121: Adding required field breaks forward compatibility"""
        old_schema = {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"}
            },
            "required": ["user_id"]
        }

        new_schema = {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "email": {"type": "string"}
            },
            "required": ["user_id", "email"]  # Added required field
        }

        registry.register("user.created", old_schema)

        with pytest.raises(BreakingChangeError, match="Added required fields"):
            registry.register(
                "user.created",
                new_schema,
                compatibility=CompatibilityMode.FORWARD
            )


@pytest.mark.acc
@pytest.mark.contract
class TestEventValidation:
    """Test suite for event data validation"""

    @pytest.fixture
    def registry(self):
        registry = SchemaRegistry()
        schema = {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "email": {"type": "string"},
                "age": {"type": "integer"}
            },
            "required": ["user_id", "email"]
        }
        registry.register("user.created", schema)
        return registry

    def test_acc_130_valid_event_passes(self, registry):
        """ACC-130: Valid event data passes validation"""
        event_data = {
            "user_id": "user-123",
            "email": "alice@example.com",
            "age": 30
        }

        result = registry.validate_event("user.created", event_data)

        assert result is True

    def test_acc_131_missing_required_field_fails(self, registry):
        """ACC-131: Missing required field fails validation"""
        event_data = {
            "user_id": "user-123"
            # Missing email
        }

        with pytest.raises(SchemaValidationError, match="Missing required field: email"):
            registry.validate_event("user.created", event_data)

    def test_acc_132_wrong_field_type_fails(self, registry):
        """ACC-132: Wrong field type fails validation"""
        event_data = {
            "user_id": "user-123",
            "email": "alice@example.com",
            "age": "thirty"  # Should be integer
        }

        with pytest.raises(SchemaValidationError, match="Type mismatch"):
            registry.validate_event("user.created", event_data)

    def test_acc_133_extra_fields_allowed(self, registry):
        """ACC-133: Extra fields not in schema are allowed"""
        event_data = {
            "user_id": "user-123",
            "email": "alice@example.com",
            "extra_field": "extra_value"  # Not in schema
        }

        result = registry.validate_event("user.created", event_data)

        assert result is True  # Still valid

    def test_acc_134_validate_against_specific_version(self, registry):
        """ACC-134: Can validate against specific schema version"""
        # Register v2 with different required fields
        schema_v2 = {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "email": {"type": "string"},
                "phone": {"type": "string"}
            },
            "required": ["user_id", "email", "phone"]
        }
        registry.register("user.created", schema_v2, version="v2.0.0")

        event_data = {
            "user_id": "user-123",
            "email": "alice@example.com"
            # No phone field
        }

        # Should pass against v1.0.0 (no phone required)
        result_v1 = registry.validate_event("user.created", event_data, version="v1.0.0")
        assert result_v1 is True

        # Should fail against v2.0.0 (phone required)
        with pytest.raises(SchemaValidationError):
            registry.validate_event("user.created", event_data, version="v2.0.0")


@pytest.mark.acc
@pytest.mark.contract
class TestSemanticVersioning:
    """Test suite for semantic versioning"""

    @pytest.fixture
    def registry(self):
        return SchemaRegistry()

    def test_acc_140_parse_major_version(self, registry):
        """ACC-140: Can parse major version number"""
        schema = {"type": "object"}
        result = registry.register("test", schema, version="v3.5.7")

        assert result.get_major_version() == 3

    def test_acc_141_parse_minor_version(self, registry):
        """ACC-141: Can parse minor version number"""
        schema = {"type": "object"}
        result = registry.register("test", schema, version="v3.5.7")

        assert result.get_minor_version() == 5

    def test_acc_142_parse_patch_version(self, registry):
        """ACC-142: Can parse patch version number"""
        schema = {"type": "object"}
        result = registry.register("test", schema, version="v3.5.7")

        assert result.get_patch_version() == 7

    def test_acc_143_version_without_v_prefix(self, registry):
        """ACC-143: Versions without 'v' prefix are parsed correctly"""
        schema = {"type": "object"}
        result = registry.register("test", schema, version="2.4.6")

        assert result.get_major_version() == 2
        assert result.get_minor_version() == 4
        assert result.get_patch_version() == 6


@pytest.mark.acc
@pytest.mark.contract
class TestCompatibilityModes:
    """Test suite for different compatibility modes"""

    @pytest.fixture
    def registry(self):
        return SchemaRegistry()

    def test_acc_145_none_mode_allows_breaking_changes(self, registry):
        """ACC-145: NONE compatibility mode allows any changes"""
        old_schema = {
            "type": "object",
            "properties": {"field": {"type": "string"}},
            "required": ["field"]
        }

        new_schema = {
            "type": "object",
            "properties": {"field": {"type": "integer"}},  # Breaking change
            "required": []
        }

        registry.register("test", old_schema)
        result = registry.register(
            "test",
            new_schema,
            compatibility=CompatibilityMode.NONE
        )

        assert result is not None  # Should succeed

    def test_acc_146_full_mode_most_restrictive(self, registry):
        """ACC-146: FULL mode is most restrictive (backward + forward)"""
        old_schema = {
            "type": "object",
            "properties": {"field1": {"type": "string"}},
            "required": ["field1"]
        }

        # Can only add optional fields in FULL mode
        new_schema = {
            "type": "object",
            "properties": {
                "field1": {"type": "string"},
                "field2": {"type": "string"}  # Optional field
            },
            "required": ["field1"]
        }

        registry.register("test", old_schema)
        result = registry.register(
            "test",
            new_schema,
            compatibility=CompatibilityMode.FULL
        )

        assert result is not None
