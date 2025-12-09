"""
Tests for the Logger Migrator module.

Tests AC-5: Replace console.log with logger utility.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from maestro_hive.devops.code_quality.logger_migrator import (
    LoggerMigrator,
    LogLocation,
    LogLevel,
    LogType,
    MigrationConfig,
    MigrationResult,
    find_console_logs,
    migrate_logs,
)


class TestLogLevel:
    """Tests for LogLevel enum."""

    def test_level_values(self):
        """Test log level enum values."""
        assert LogLevel.DEBUG.value == "debug"
        assert LogLevel.INFO.value == "info"
        assert LogLevel.WARNING.value == "warning"
        assert LogLevel.ERROR.value == "error"
        assert LogLevel.CRITICAL.value == "critical"


class TestLogType:
    """Tests for LogType enum."""

    def test_type_values(self):
        """Test log type enum values."""
        assert LogType.CONSOLE_LOG.value == "console.log"
        assert LogType.CONSOLE_ERROR.value == "console.error"
        assert LogType.PRINT.value == "print"


class TestLogLocation:
    """Tests for LogLocation dataclass."""

    def test_create_location(self):
        """Test creating a log location."""
        loc = LogLocation(
            file_path="/path/to/file.ts",
            line=10,
            column=5,
            log_type=LogType.CONSOLE_LOG,
            original_code="console.log('test')",
            suggested_replacement="logger.info('test')",
        )
        assert loc.file_path == "/path/to/file.ts"
        assert loc.line == 10
        assert loc.log_type == LogType.CONSOLE_LOG

    def test_to_dict(self):
        """Test converting to dictionary."""
        loc = LogLocation(
            file_path="test.ts",
            line=1,
            column=1,
            log_type=LogType.CONSOLE_ERROR,
            original_code="console.error('err')",
        )
        d = loc.to_dict()
        assert d["file_path"] == "test.ts"
        assert d["log_type"] == "console.error"


class TestMigrationConfig:
    """Tests for MigrationConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = MigrationConfig()
        assert config.target_logger == "logger"
        assert config.dry_run is True
        assert ".git" in config.exclude_patterns

    def test_custom_config(self):
        """Test custom configuration."""
        config = MigrationConfig(
            target_logger="myLogger",
            dry_run=False,
        )
        assert config.target_logger == "myLogger"
        assert config.dry_run is False


class TestMigrationResult:
    """Tests for MigrationResult dataclass."""

    def test_empty_result(self):
        """Test empty result."""
        result = MigrationResult()
        assert result.logs_found == 0
        assert result.success is True

    def test_add_location(self):
        """Test adding locations."""
        result = MigrationResult()
        result.add_location(LogLocation(
            file_path="test.ts",
            line=1,
            column=1,
            log_type=LogType.CONSOLE_LOG,
            original_code="console.log('test')",
        ))
        assert result.logs_found == 1
        assert len(result.locations) == 1

    def test_add_error(self):
        """Test adding errors."""
        result = MigrationResult()
        result.add_error("Something went wrong")
        assert result.success is False
        assert len(result.errors) == 1


class TestLoggerMigrator:
    """Tests for LoggerMigrator class."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        migrator = LoggerMigrator()
        assert migrator.config is not None
        assert migrator.config.dry_run is True

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = MigrationConfig(dry_run=False)
        migrator = LoggerMigrator(config)
        assert migrator.config.dry_run is False

    def test_find_console_logs_in_file(self, tmp_path):
        """Test finding console.log in a file."""
        ts_file = tmp_path / "app.ts"
        ts_file.write_text("""
const x = 1;
console.log('Hello world');
console.log("Multiple", "args");
""")

        migrator = LoggerMigrator()
        locations = migrator.find_console_logs_in_file(ts_file)

        assert len(locations) == 2
        assert all(loc.log_type == LogType.CONSOLE_LOG for loc in locations)

    def test_find_console_error_in_file(self, tmp_path):
        """Test finding console.error in a file."""
        ts_file = tmp_path / "app.ts"
        ts_file.write_text("console.error('Error occurred');")

        migrator = LoggerMigrator()
        locations = migrator.find_console_logs_in_file(ts_file)

        assert len(locations) == 1
        assert locations[0].log_type == LogType.CONSOLE_ERROR
        assert "logger.error" in locations[0].suggested_replacement

    def test_find_console_warn_in_file(self, tmp_path):
        """Test finding console.warn in a file."""
        ts_file = tmp_path / "app.ts"
        ts_file.write_text("console.warn('Warning');")

        migrator = LoggerMigrator()
        locations = migrator.find_console_logs_in_file(ts_file)

        assert len(locations) == 1
        assert locations[0].log_type == LogType.CONSOLE_WARN
        assert "logger.warning" in locations[0].suggested_replacement

    def test_find_print_statements(self, tmp_path):
        """Test finding print statements in Python."""
        py_file = tmp_path / "test.py"
        py_file.write_text("""
print("Hello")
print('World')
x = 1
print(x)
""")

        migrator = LoggerMigrator()
        locations = migrator.find_print_statements(py_file)

        assert len(locations) == 3
        assert all(loc.log_type == LogType.PRINT for loc in locations)
        assert all("logger.info" in loc.suggested_replacement for loc in locations)

    def test_scan_directory(self, tmp_path):
        """Test scanning directory for logs."""
        (tmp_path / "app.ts").write_text("console.log('test');")
        (tmp_path / "test.py").write_text("print('hello')")
        (tmp_path / "other.txt").write_text("console.log ignored")

        migrator = LoggerMigrator()
        result = migrator.scan_directory(str(tmp_path))

        assert result.files_scanned == 2
        assert result.logs_found == 2

    def test_scan_directory_excludes_patterns(self, tmp_path):
        """Test exclusion patterns."""
        (tmp_path / "good.ts").write_text("console.log('find me');")
        node_modules = tmp_path / "node_modules"
        node_modules.mkdir()
        (node_modules / "lib.ts").write_text("console.log('ignore me');")

        migrator = LoggerMigrator()
        result = migrator.scan_directory(str(tmp_path))

        assert result.logs_found == 1

    def test_scan_directory_nonexistent(self):
        """Test scanning non-existent directory."""
        migrator = LoggerMigrator()
        result = migrator.scan_directory("/nonexistent/path")
        assert result.success is False
        assert len(result.errors) > 0

    def test_migrate_file_dry_run(self, tmp_path):
        """Test migrating file in dry run mode."""
        ts_file = tmp_path / "app.ts"
        original = "console.log('test');"
        ts_file.write_text(original)

        config = MigrationConfig(dry_run=True)
        migrator = LoggerMigrator(config)
        result = migrator.migrate_file(str(ts_file))

        # File should not be modified in dry run
        assert ts_file.read_text() == original
        assert result.files_modified == 0

    def test_migrate_file_actual(self, tmp_path):
        """Test actually migrating a file."""
        ts_file = tmp_path / "app.ts"
        ts_file.write_text("console.log('test');")

        config = MigrationConfig(dry_run=False)
        migrator = LoggerMigrator(config)
        result = migrator.migrate_file(str(ts_file))

        content = ts_file.read_text()
        assert "logger.info" in content
        assert "import { logger }" in content
        assert result.files_modified == 1

    def test_migrate_file_python(self, tmp_path):
        """Test migrating Python file."""
        py_file = tmp_path / "test.py"
        py_file.write_text("print('hello')")

        config = MigrationConfig(dry_run=False)
        migrator = LoggerMigrator(config)
        result = migrator.migrate_file(str(py_file))

        content = py_file.read_text()
        assert "logger.info" in content
        assert "import logging" in content

    def test_migrate_directory(self, tmp_path):
        """Test migrating entire directory."""
        (tmp_path / "a.ts").write_text("console.log('a');")
        (tmp_path / "b.ts").write_text("console.log('b');")

        config = MigrationConfig(dry_run=False)
        migrator = LoggerMigrator(config)
        result = migrator.migrate_directory(str(tmp_path))

        assert result.files_scanned == 2
        assert result.files_modified == 2


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_find_console_logs(self, tmp_path):
        """Test find_console_logs function."""
        (tmp_path / "app.ts").write_text("console.log('test');")

        locations = find_console_logs(str(tmp_path))
        assert len(locations) == 1

    def test_migrate_logs_dry_run(self, tmp_path):
        """Test migrate_logs in dry run mode."""
        ts_file = tmp_path / "app.ts"
        original = "console.log('test');"
        ts_file.write_text(original)

        result = migrate_logs(str(tmp_path), dry_run=True)

        assert ts_file.read_text() == original

    def test_migrate_logs_actual(self, tmp_path):
        """Test migrate_logs actually modifying files."""
        ts_file = tmp_path / "app.ts"
        ts_file.write_text("console.log('test');")

        result = migrate_logs(str(tmp_path), dry_run=False)

        content = ts_file.read_text()
        assert "logger.info" in content
