"""
Schema Migrator Module - AC-6: Migrate schema to camelCase convention.

This module provides utilities for migrating database schemas and API
responses from snake_case to camelCase naming convention.

Implements: MD-2788 AC-6
"""

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CaseConvention(Enum):
    """Naming convention types."""
    SNAKE_CASE = "snake_case"
    CAMEL_CASE = "camelCase"
    PASCAL_CASE = "PascalCase"
    KEBAB_CASE = "kebab-case"


class SchemaType(Enum):
    """Types of schemas that can be migrated."""
    JSON_SCHEMA = "json_schema"
    TYPESCRIPT_INTERFACE = "typescript_interface"
    PYTHON_DATACLASS = "python_dataclass"
    PYDANTIC_MODEL = "pydantic_model"
    OPENAPI = "openapi"
    GRAPHQL = "graphql"


@dataclass
class FieldMapping:
    """Mapping of a field from old to new naming."""
    original_name: str
    new_name: str
    file_path: str
    line: Optional[int] = None
    schema_type: Optional[SchemaType] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "original_name": self.original_name,
            "new_name": self.new_name,
            "file_path": self.file_path,
            "line": self.line,
            "schema_type": self.schema_type.value if self.schema_type else None,
        }


@dataclass
class SchemaMigrationConfig:
    """Configuration for schema migration."""
    source_convention: CaseConvention = CaseConvention.SNAKE_CASE
    target_convention: CaseConvention = CaseConvention.CAMEL_CASE
    preserve_acronyms: bool = True
    acronyms: list[str] = field(default_factory=lambda: [
        "ID", "URL", "API", "HTTP", "HTTPS", "UUID", "JSON", "XML", "HTML", "CSS"
    ])
    exclude_patterns: list[str] = field(default_factory=lambda: [
        ".git", "__pycache__", ".venv", "node_modules", "dist"
    ])
    dry_run: bool = True


@dataclass
class MigrationReport:
    """Result of a schema migration."""
    files_scanned: int = 0
    files_modified: int = 0
    fields_migrated: int = 0
    mappings: list[FieldMapping] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = True

    def add_mapping(self, mapping: FieldMapping) -> None:
        """Add a field mapping."""
        self.mappings.append(mapping)
        self.fields_migrated += 1

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        self.success = False

    def get_migration_map(self) -> dict[str, str]:
        """Get dictionary of old to new field names."""
        return {m.original_name: m.new_name for m in self.mappings}


class CaseConverter:
    """Converts between naming conventions."""

    def __init__(self, config: Optional[SchemaMigrationConfig] = None):
        """Initialize converter.

        Args:
            config: Migration configuration.
        """
        self.config = config or SchemaMigrationConfig()

    def snake_to_camel(self, name: str) -> str:
        """Convert snake_case to camelCase.

        Args:
            name: Snake case string.

        Returns:
            CamelCase string.
        """
        if not name or "_" not in name:
            return name

        components = name.split("_")
        # Handle leading underscores
        leading = ""
        while components and not components[0]:
            leading += "_"
            components.pop(0)

        if not components:
            return name

        # First component stays lowercase
        result = components[0].lower()

        # Subsequent components get capitalized
        for comp in components[1:]:
            if not comp:
                continue

            # Check for acronyms
            upper_comp = comp.upper()
            if self.config.preserve_acronyms and upper_comp in self.config.acronyms:
                result += upper_comp
            else:
                result += comp.capitalize()

        return leading + result

    def camel_to_snake(self, name: str) -> str:
        """Convert camelCase to snake_case.

        Args:
            name: CamelCase string.

        Returns:
            snake_case string.
        """
        if not name:
            return name

        # Handle acronyms first
        result = name
        if self.config.preserve_acronyms:
            for acronym in self.config.acronyms:
                result = re.sub(
                    rf'({acronym})([A-Z])',
                    rf'\1_\2',
                    result
                )

        # Insert underscore before capitals
        result = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', result)
        return result.lower()

    def convert(
        self,
        name: str,
        source: CaseConvention,
        target: CaseConvention
    ) -> str:
        """Convert between naming conventions.

        Args:
            name: String to convert.
            source: Source convention.
            target: Target convention.

        Returns:
            Converted string.
        """
        if source == target:
            return name

        if source == CaseConvention.SNAKE_CASE and target == CaseConvention.CAMEL_CASE:
            return self.snake_to_camel(name)
        elif source == CaseConvention.CAMEL_CASE and target == CaseConvention.SNAKE_CASE:
            return self.camel_to_snake(name)
        else:
            # For other conversions, go through snake_case as intermediate
            if source != CaseConvention.SNAKE_CASE:
                name = self.camel_to_snake(name)
            if target != CaseConvention.SNAKE_CASE:
                name = self.snake_to_camel(name)
            return name


class SchemaMigrator:
    """Migrates schema field names between naming conventions."""

    def __init__(self, config: Optional[SchemaMigrationConfig] = None):
        """Initialize migrator.

        Args:
            config: Migration configuration.
        """
        self.config = config or SchemaMigrationConfig()
        self.converter = CaseConverter(self.config)

    def _should_skip(self, path: Path) -> bool:
        """Check if path should be skipped."""
        path_str = str(path)
        return any(p in path_str for p in self.config.exclude_patterns)

    def _find_snake_case_fields(self, obj: Any, path: str = "") -> list[str]:
        """Find snake_case field names in a JSON-like structure."""
        fields = []

        if isinstance(obj, dict):
            for key, value in obj.items():
                if "_" in key and not key.startswith("_"):
                    fields.append(key)
                # Recurse into nested structures
                fields.extend(self._find_snake_case_fields(value, f"{path}.{key}"))

        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                fields.extend(self._find_snake_case_fields(item, f"{path}[{i}]"))

        return fields

    def migrate_json_object(self, obj: Any) -> Any:
        """Migrate field names in a JSON object.

        Args:
            obj: JSON-like object (dict, list, or primitive).

        Returns:
            Object with migrated field names.
        """
        if isinstance(obj, dict):
            return {
                self.converter.convert(
                    k,
                    self.config.source_convention,
                    self.config.target_convention
                ): self.migrate_json_object(v)
                for k, v in obj.items()
            }
        elif isinstance(obj, list):
            return [self.migrate_json_object(item) for item in obj]
        else:
            return obj

    def migrate_json_file(self, file_path: str) -> MigrationReport:
        """Migrate field names in a JSON file.

        Args:
            file_path: Path to JSON file.

        Returns:
            MigrationReport with details.
        """
        report = MigrationReport()
        path = Path(file_path)

        if not path.exists():
            report.add_error(f"File does not exist: {file_path}")
            return report

        report.files_scanned = 1

        try:
            content = path.read_text()
            data = json.loads(content)

            # Find snake_case fields
            snake_fields = self._find_snake_case_fields(data)

            for field_name in set(snake_fields):
                new_name = self.converter.convert(
                    field_name,
                    self.config.source_convention,
                    self.config.target_convention
                )
                if new_name != field_name:
                    report.add_mapping(FieldMapping(
                        original_name=field_name,
                        new_name=new_name,
                        file_path=file_path,
                        schema_type=SchemaType.JSON_SCHEMA,
                    ))

            if not self.config.dry_run and report.fields_migrated > 0:
                migrated = self.migrate_json_object(data)
                path.write_text(json.dumps(migrated, indent=2))
                report.files_modified = 1

        except json.JSONDecodeError as e:
            report.add_error(f"Invalid JSON in {file_path}: {e}")
        except Exception as e:
            report.add_error(f"Failed to process {file_path}: {e}")

        return report

    def migrate_typescript_interface(self, file_path: str) -> MigrationReport:
        """Migrate field names in TypeScript interfaces.

        Args:
            file_path: Path to TypeScript file.

        Returns:
            MigrationReport with details.
        """
        report = MigrationReport()
        path = Path(file_path)

        if not path.exists():
            report.add_error(f"File does not exist: {file_path}")
            return report

        report.files_scanned = 1

        try:
            content = path.read_text()

            # Pattern to find interface/type fields
            # Matches: field_name: type or field_name?: type
            field_pattern = re.compile(
                r'^(\s*)([a-z][a-z0-9]*(?:_[a-z0-9]+)+)(\??):\s*',
                re.MULTILINE | re.IGNORECASE
            )

            modified_content = content
            for match in field_pattern.finditer(content):
                field_name = match.group(2)
                new_name = self.converter.convert(
                    field_name,
                    self.config.source_convention,
                    self.config.target_convention
                )

                if new_name != field_name:
                    report.add_mapping(FieldMapping(
                        original_name=field_name,
                        new_name=new_name,
                        file_path=file_path,
                        line=content[:match.start()].count('\n') + 1,
                        schema_type=SchemaType.TYPESCRIPT_INTERFACE,
                    ))

                    if not self.config.dry_run:
                        indent = match.group(1)
                        optional = match.group(3)
                        modified_content = modified_content.replace(
                            match.group(0),
                            f"{indent}{new_name}{optional}: "
                        )

            if not self.config.dry_run and report.fields_migrated > 0:
                path.write_text(modified_content)
                report.files_modified = 1

        except Exception as e:
            report.add_error(f"Failed to process {file_path}: {e}")

        return report

    def migrate_pydantic_model(self, file_path: str) -> MigrationReport:
        """Migrate field names in Pydantic models.

        Args:
            file_path: Path to Python file with Pydantic models.

        Returns:
            MigrationReport with details.
        """
        report = MigrationReport()
        path = Path(file_path)

        if not path.exists():
            report.add_error(f"File does not exist: {file_path}")
            return report

        report.files_scanned = 1

        try:
            content = path.read_text()

            # Pattern for Pydantic field definitions
            # Matches: field_name: type = Field(...) or field_name: type
            field_pattern = re.compile(
                r'^(\s*)([a-z][a-z0-9]*(?:_[a-z0-9]+)+):\s*([^=\n]+)',
                re.MULTILINE
            )

            modified_content = content
            for match in field_pattern.finditer(content):
                field_name = match.group(2)
                new_name = self.converter.convert(
                    field_name,
                    self.config.source_convention,
                    self.config.target_convention
                )

                if new_name != field_name:
                    report.add_mapping(FieldMapping(
                        original_name=field_name,
                        new_name=new_name,
                        file_path=file_path,
                        line=content[:match.start()].count('\n') + 1,
                        schema_type=SchemaType.PYDANTIC_MODEL,
                    ))

                    if not self.config.dry_run:
                        indent = match.group(1)
                        type_hint = match.group(3)
                        # Add alias for backward compatibility
                        if "Field(" in type_hint:
                            # Already has Field, add alias
                            modified_content = modified_content.replace(
                                match.group(0),
                                f'{indent}{new_name}: {type_hint.rstrip()}, alias="{field_name}")'
                            )
                        else:
                            # Add Field with alias
                            modified_content = modified_content.replace(
                                match.group(0),
                                f'{indent}{new_name}: {type_hint.rstrip()} = Field(alias="{field_name}")'
                            )

            if not self.config.dry_run and report.fields_migrated > 0:
                path.write_text(modified_content)
                report.files_modified = 1

        except Exception as e:
            report.add_error(f"Failed to process {file_path}: {e}")

        return report

    def scan_directory(self, path: str) -> MigrationReport:
        """Scan directory for fields to migrate.

        Args:
            path: Directory path to scan.

        Returns:
            MigrationReport with all mappings.
        """
        report = MigrationReport()
        target_path = Path(path)

        if not target_path.exists():
            report.add_error(f"Path does not exist: {path}")
            return report

        # Scan JSON files
        for f in target_path.glob("**/*.json"):
            if self._should_skip(f):
                continue
            file_report = self.migrate_json_file(str(f))
            report.files_scanned += file_report.files_scanned
            report.mappings.extend(file_report.mappings)
            report.fields_migrated += file_report.fields_migrated
            report.errors.extend(file_report.errors)

        # Scan TypeScript files
        for pattern in ["**/*.ts", "**/*.tsx"]:
            for f in target_path.glob(pattern):
                if self._should_skip(f):
                    continue
                file_report = self.migrate_typescript_interface(str(f))
                report.files_scanned += file_report.files_scanned
                report.mappings.extend(file_report.mappings)
                report.fields_migrated += file_report.fields_migrated
                report.errors.extend(file_report.errors)

        # Scan Python files
        for f in target_path.glob("**/*.py"):
            if self._should_skip(f):
                continue
            file_report = self.migrate_pydantic_model(str(f))
            report.files_scanned += file_report.files_scanned
            report.mappings.extend(file_report.mappings)
            report.fields_migrated += file_report.fields_migrated
            report.errors.extend(file_report.errors)

        report.success = len(report.errors) == 0
        return report


def migrate_to_camel_case(
    path: str,
    dry_run: bool = True
) -> MigrationReport:
    """Convenience function to migrate schema to camelCase.

    Args:
        path: Path to migrate.
        dry_run: If True, don't modify files.

    Returns:
        MigrationReport with operation details.
    """
    config = SchemaMigrationConfig(dry_run=dry_run)
    migrator = SchemaMigrator(config)
    return migrator.scan_directory(path)


def convert_field_name(
    name: str,
    source: CaseConvention = CaseConvention.SNAKE_CASE,
    target: CaseConvention = CaseConvention.CAMEL_CASE
) -> str:
    """Convenience function to convert a single field name.

    Args:
        name: Field name to convert.
        source: Source naming convention.
        target: Target naming convention.

    Returns:
        Converted field name.
    """
    converter = CaseConverter()
    return converter.convert(name, source, target)
