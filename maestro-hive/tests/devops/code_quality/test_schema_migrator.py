"""
Tests for the Schema Migrator module.

Tests AC-6: Migrate schema to camelCase convention.
"""

import json
import pytest
from pathlib import Path

from maestro_hive.devops.code_quality.schema_migrator import (
    SchemaMigrator,
    SchemaMigrationConfig,
    MigrationReport,
    FieldMapping,
    CaseConvention,
    SchemaType,
    CaseConverter,
    migrate_to_camel_case,
    convert_field_name,
)


class TestCaseConvention:
    """Tests for CaseConvention enum."""

    def test_convention_values(self):
        """Test convention enum values."""
        assert CaseConvention.SNAKE_CASE.value == "snake_case"
        assert CaseConvention.CAMEL_CASE.value == "camelCase"
        assert CaseConvention.PASCAL_CASE.value == "PascalCase"


class TestSchemaType:
    """Tests for SchemaType enum."""

    def test_type_values(self):
        """Test schema type enum values."""
        assert SchemaType.JSON_SCHEMA.value == "json_schema"
        assert SchemaType.TYPESCRIPT_INTERFACE.value == "typescript_interface"
        assert SchemaType.PYDANTIC_MODEL.value == "pydantic_model"


class TestFieldMapping:
    """Tests for FieldMapping dataclass."""

    def test_create_mapping(self):
        """Test creating a field mapping."""
        mapping = FieldMapping(
            original_name="user_id",
            new_name="userId",
            file_path="/path/to/schema.json",
            line=10,
            schema_type=SchemaType.JSON_SCHEMA,
        )
        assert mapping.original_name == "user_id"
        assert mapping.new_name == "userId"

    def test_to_dict(self):
        """Test converting to dictionary."""
        mapping = FieldMapping(
            original_name="first_name",
            new_name="firstName",
            file_path="model.py",
            schema_type=SchemaType.PYDANTIC_MODEL,
        )
        d = mapping.to_dict()
        assert d["original_name"] == "first_name"
        assert d["new_name"] == "firstName"
        assert d["schema_type"] == "pydantic_model"


class TestSchemaMigrationConfig:
    """Tests for SchemaMigrationConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = SchemaMigrationConfig()
        assert config.source_convention == CaseConvention.SNAKE_CASE
        assert config.target_convention == CaseConvention.CAMEL_CASE
        assert config.preserve_acronyms is True
        assert "ID" in config.acronyms
        assert config.dry_run is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = SchemaMigrationConfig(
            preserve_acronyms=False,
            dry_run=False,
        )
        assert config.preserve_acronyms is False
        assert config.dry_run is False


class TestMigrationReport:
    """Tests for MigrationReport dataclass."""

    def test_empty_report(self):
        """Test empty report."""
        report = MigrationReport()
        assert report.fields_migrated == 0
        assert report.success is True

    def test_add_mapping(self):
        """Test adding mappings."""
        report = MigrationReport()
        report.add_mapping(FieldMapping(
            original_name="user_id",
            new_name="userId",
            file_path="test.json",
        ))
        assert report.fields_migrated == 1
        assert len(report.mappings) == 1

    def test_add_error(self):
        """Test adding errors."""
        report = MigrationReport()
        report.add_error("Failed to parse file")
        assert report.success is False
        assert len(report.errors) == 1

    def test_get_migration_map(self):
        """Test getting migration map."""
        report = MigrationReport()
        report.add_mapping(FieldMapping("user_id", "userId", "a.json"))
        report.add_mapping(FieldMapping("first_name", "firstName", "a.json"))

        m = report.get_migration_map()
        assert m["user_id"] == "userId"
        assert m["first_name"] == "firstName"


class TestCaseConverter:
    """Tests for CaseConverter class."""

    def test_snake_to_camel_simple(self):
        """Test simple snake_case to camelCase."""
        converter = CaseConverter()
        assert converter.snake_to_camel("user_name") == "userName"
        assert converter.snake_to_camel("first_name") == "firstName"
        assert converter.snake_to_camel("a_b_c") == "aBC"

    def test_snake_to_camel_single_word(self):
        """Test single word conversion."""
        converter = CaseConverter()
        assert converter.snake_to_camel("name") == "name"
        assert converter.snake_to_camel("user") == "user"

    def test_snake_to_camel_with_acronym(self):
        """Test acronym preservation."""
        config = SchemaMigrationConfig(preserve_acronyms=True)
        converter = CaseConverter(config)

        assert converter.snake_to_camel("user_id") == "userID"
        assert converter.snake_to_camel("api_url") == "apiURL"

    def test_snake_to_camel_without_acronym(self):
        """Test without acronym preservation."""
        config = SchemaMigrationConfig(preserve_acronyms=False)
        converter = CaseConverter(config)

        assert converter.snake_to_camel("user_id") == "userId"

    def test_snake_to_camel_leading_underscore(self):
        """Test with leading underscore."""
        converter = CaseConverter()
        assert converter.snake_to_camel("_private_field") == "_privateField"

    def test_camel_to_snake_simple(self):
        """Test simple camelCase to snake_case."""
        converter = CaseConverter()
        assert converter.camel_to_snake("userName") == "user_name"
        assert converter.camel_to_snake("firstName") == "first_name"

    def test_camel_to_snake_single_word(self):
        """Test single word conversion."""
        converter = CaseConverter()
        assert converter.camel_to_snake("name") == "name"

    def test_convert_same_convention(self):
        """Test converting to same convention."""
        converter = CaseConverter()
        result = converter.convert(
            "user_name",
            CaseConvention.SNAKE_CASE,
            CaseConvention.SNAKE_CASE
        )
        assert result == "user_name"


class TestSchemaMigrator:
    """Tests for SchemaMigrator class."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        migrator = SchemaMigrator()
        assert migrator.config is not None
        assert migrator.config.dry_run is True

    def test_migrate_json_object(self):
        """Test migrating JSON object fields."""
        migrator = SchemaMigrator()
        obj = {
            "user_id": 1,
            "first_name": "John",
            "last_name": "Doe",
        }
        result = migrator.migrate_json_object(obj)

        assert "userId" in result or "userID" in result
        assert "firstName" in result
        assert "lastName" in result
        assert "user_id" not in result

    def test_migrate_json_object_nested(self):
        """Test migrating nested JSON object."""
        migrator = SchemaMigrator()
        obj = {
            "user_data": {
                "first_name": "John",
                "contact_info": {
                    "email_address": "john@example.com"
                }
            }
        }
        result = migrator.migrate_json_object(obj)

        assert "userData" in result
        assert "firstName" in result["userData"]
        assert "contactInfo" in result["userData"]
        assert "emailAddress" in result["userData"]["contactInfo"]

    def test_migrate_json_object_array(self):
        """Test migrating JSON with arrays."""
        migrator = SchemaMigrator()
        obj = {
            "user_list": [
                {"first_name": "John"},
                {"first_name": "Jane"},
            ]
        }
        result = migrator.migrate_json_object(obj)

        assert "userList" in result
        assert all("firstName" in u for u in result["userList"])

    def test_migrate_json_file(self, tmp_path):
        """Test migrating JSON file."""
        json_file = tmp_path / "schema.json"
        json_file.write_text(json.dumps({
            "user_id": 1,
            "user_name": "test"
        }))

        migrator = SchemaMigrator()
        report = migrator.migrate_json_file(str(json_file))

        assert report.files_scanned == 1
        assert report.fields_migrated == 2

    def test_migrate_json_file_dry_run(self, tmp_path):
        """Test migrating JSON file in dry run mode."""
        json_file = tmp_path / "schema.json"
        original = json.dumps({"user_id": 1})
        json_file.write_text(original)

        config = SchemaMigrationConfig(dry_run=True)
        migrator = SchemaMigrator(config)
        report = migrator.migrate_json_file(str(json_file))

        # File should not be modified
        assert json_file.read_text() == original
        assert report.files_modified == 0

    def test_migrate_json_file_actual(self, tmp_path):
        """Test actually migrating JSON file."""
        json_file = tmp_path / "schema.json"
        json_file.write_text(json.dumps({"user_id": 1}))

        config = SchemaMigrationConfig(dry_run=False)
        migrator = SchemaMigrator(config)
        report = migrator.migrate_json_file(str(json_file))

        content = json.loads(json_file.read_text())
        assert "userId" in content or "userID" in content
        assert report.files_modified == 1

    def test_migrate_json_file_invalid(self, tmp_path):
        """Test migrating invalid JSON file."""
        json_file = tmp_path / "bad.json"
        json_file.write_text("not valid json")

        migrator = SchemaMigrator()
        report = migrator.migrate_json_file(str(json_file))

        assert report.success is False
        assert len(report.errors) > 0

    def test_migrate_typescript_interface(self, tmp_path):
        """Test migrating TypeScript interface."""
        ts_file = tmp_path / "types.ts"
        ts_file.write_text("""
interface User {
    user_id: number;
    first_name: string;
    last_name?: string;
}
""")

        migrator = SchemaMigrator()
        report = migrator.migrate_typescript_interface(str(ts_file))

        assert report.files_scanned == 1
        assert report.fields_migrated >= 2

    def test_migrate_pydantic_model(self, tmp_path):
        """Test migrating Pydantic model."""
        py_file = tmp_path / "models.py"
        py_file.write_text("""
from pydantic import BaseModel

class User(BaseModel):
    user_id: int
    first_name: str
    last_name: str
""")

        migrator = SchemaMigrator()
        report = migrator.migrate_pydantic_model(str(py_file))

        assert report.files_scanned == 1
        assert report.fields_migrated >= 2

    def test_scan_directory(self, tmp_path):
        """Test scanning directory."""
        (tmp_path / "schema.json").write_text(json.dumps({"user_id": 1, "first_name": "test"}))
        # TS interface with proper format for regex
        (tmp_path / "types.ts").write_text("""interface User {
    user_name: string;
}""")

        migrator = SchemaMigrator()
        report = migrator.scan_directory(str(tmp_path))

        assert report.files_scanned >= 2
        # At minimum we should find fields in the JSON file
        assert report.fields_migrated >= 1

    def test_scan_directory_excludes_patterns(self, tmp_path):
        """Test exclusion patterns."""
        (tmp_path / "good.json").write_text(json.dumps({"user_id": 1}))
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "bad.json").write_text(json.dumps({"user_id": 2}))

        migrator = SchemaMigrator()
        report = migrator.scan_directory(str(tmp_path))

        # Should only find the one in root
        assert report.fields_migrated == 1

    def test_scan_directory_nonexistent(self):
        """Test scanning non-existent directory."""
        migrator = SchemaMigrator()
        report = migrator.scan_directory("/nonexistent/path")
        assert report.success is False


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_migrate_to_camel_case(self, tmp_path):
        """Test migrate_to_camel_case function."""
        (tmp_path / "schema.json").write_text(json.dumps({"user_id": 1}))

        report = migrate_to_camel_case(str(tmp_path))
        assert report.fields_migrated >= 1

    def test_convert_field_name(self):
        """Test convert_field_name function."""
        assert convert_field_name("user_name") == "userName"
        assert convert_field_name(
            "userName",
            CaseConvention.CAMEL_CASE,
            CaseConvention.SNAKE_CASE
        ) == "user_name"
