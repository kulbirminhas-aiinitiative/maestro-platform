"""
Logger Migrator Module - AC-5: Replace console.log with logger utility.

This module provides utilities for migrating console.log statements
to structured logging throughout the codebase.

Implements: MD-2788 AC-5
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class LogLevel(Enum):
    """Standard log levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogType(Enum):
    """Types of log statements found."""
    CONSOLE_LOG = "console.log"
    CONSOLE_ERROR = "console.error"
    CONSOLE_WARN = "console.warn"
    CONSOLE_DEBUG = "console.debug"
    CONSOLE_INFO = "console.info"
    PRINT = "print"


@dataclass
class LogLocation:
    """Location of a log statement in code."""
    file_path: str
    line: int
    column: int
    log_type: LogType
    original_code: str
    suggested_replacement: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "line": self.line,
            "column": self.column,
            "log_type": self.log_type.value,
            "original_code": self.original_code,
            "suggested_replacement": self.suggested_replacement,
        }


@dataclass
class MigrationConfig:
    """Configuration for logger migration."""
    target_logger: str = "logger"
    import_statement: str = "import logging\nlogger = logging.getLogger(__name__)"
    ts_import: str = "import { logger } from '@/utils/logger';"
    exclude_patterns: list[str] = field(default_factory=lambda: [
        ".git", "__pycache__", ".venv", "node_modules", "dist"
    ])
    dry_run: bool = True


@dataclass
class MigrationResult:
    """Result of a migration operation."""
    files_scanned: int = 0
    files_modified: int = 0
    logs_found: int = 0
    logs_migrated: int = 0
    locations: list[LogLocation] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = True

    def add_location(self, location: LogLocation) -> None:
        """Add a log location."""
        self.locations.append(location)
        self.logs_found += 1

    def add_error(self, error: str) -> None:
        """Add an error message."""
        self.errors.append(error)
        self.success = False


class LoggerMigrator:
    """Migrates console.log and print statements to structured logging."""

    # Patterns for different log types
    CONSOLE_PATTERNS = {
        LogType.CONSOLE_LOG: re.compile(r'console\.log\s*\(([^)]*)\)', re.MULTILINE),
        LogType.CONSOLE_ERROR: re.compile(r'console\.error\s*\(([^)]*)\)', re.MULTILINE),
        LogType.CONSOLE_WARN: re.compile(r'console\.warn\s*\(([^)]*)\)', re.MULTILINE),
        LogType.CONSOLE_DEBUG: re.compile(r'console\.debug\s*\(([^)]*)\)', re.MULTILINE),
        LogType.CONSOLE_INFO: re.compile(r'console\.info\s*\(([^)]*)\)', re.MULTILINE),
    }

    PRINT_PATTERN = re.compile(r'^(\s*)print\s*\(([^)]*)\)', re.MULTILINE)

    # Mapping from console methods to log levels
    LEVEL_MAP = {
        LogType.CONSOLE_LOG: LogLevel.INFO,
        LogType.CONSOLE_ERROR: LogLevel.ERROR,
        LogType.CONSOLE_WARN: LogLevel.WARNING,
        LogType.CONSOLE_DEBUG: LogLevel.DEBUG,
        LogType.CONSOLE_INFO: LogLevel.INFO,
        LogType.PRINT: LogLevel.INFO,
    }

    def __init__(self, config: Optional[MigrationConfig] = None):
        """Initialize migrator.

        Args:
            config: Migration configuration.
        """
        self.config = config or MigrationConfig()

    def _should_skip(self, path: Path) -> bool:
        """Check if path should be skipped."""
        path_str = str(path)
        return any(p in path_str for p in self.config.exclude_patterns)

    def _find_files(self, path: Path, extensions: list[str]) -> list[Path]:
        """Find files with given extensions."""
        files = []
        for ext in extensions:
            for f in path.glob(f"**/*{ext}"):
                if not self._should_skip(f):
                    files.append(f)
        return files

    def _get_line_column(self, content: str, match_start: int) -> tuple[int, int]:
        """Get line and column from match position."""
        lines = content[:match_start].split('\n')
        line = len(lines)
        column = len(lines[-1]) + 1 if lines else 1
        return line, column

    def find_console_logs_in_file(self, file_path: Path) -> list[LogLocation]:
        """Find console.log statements in a file.

        Args:
            file_path: Path to file to scan.

        Returns:
            List of LogLocation objects.
        """
        locations = []

        try:
            content = file_path.read_text()

            for log_type, pattern in self.CONSOLE_PATTERNS.items():
                for match in pattern.finditer(content):
                    line, column = self._get_line_column(content, match.start())
                    level = self.LEVEL_MAP[log_type]

                    # Generate replacement
                    args = match.group(1)
                    replacement = f"logger.{level.value}({args})"

                    locations.append(LogLocation(
                        file_path=str(file_path),
                        line=line,
                        column=column,
                        log_type=log_type,
                        original_code=match.group(0),
                        suggested_replacement=replacement,
                    ))

        except Exception as e:
            logger.warning(f"Failed to scan {file_path}: {e}")

        return locations

    def find_print_statements(self, file_path: Path) -> list[LogLocation]:
        """Find print statements in Python files.

        Args:
            file_path: Path to Python file.

        Returns:
            List of LogLocation objects.
        """
        locations = []

        try:
            content = file_path.read_text()

            for match in self.PRINT_PATTERN.finditer(content):
                line, column = self._get_line_column(content, match.start())
                indent = match.group(1)
                args = match.group(2)

                # Generate replacement
                replacement = f"{indent}logger.info({args})"

                locations.append(LogLocation(
                    file_path=str(file_path),
                    line=line,
                    column=column,
                    log_type=LogType.PRINT,
                    original_code=match.group(0),
                    suggested_replacement=replacement,
                ))

        except Exception as e:
            logger.warning(f"Failed to scan {file_path}: {e}")

        return locations

    def scan_directory(self, path: str) -> MigrationResult:
        """Scan directory for log statements to migrate.

        Args:
            path: Directory path to scan.

        Returns:
            MigrationResult with all found locations.
        """
        result = MigrationResult()
        target_path = Path(path)

        if not target_path.exists():
            result.add_error(f"Path does not exist: {path}")
            return result

        # Scan TypeScript/JavaScript files for console.log
        ts_files = self._find_files(target_path, [".ts", ".tsx", ".js", ".jsx"])
        for f in ts_files:
            result.files_scanned += 1
            locations = self.find_console_logs_in_file(f)
            for loc in locations:
                result.add_location(loc)

        # Scan Python files for print statements
        py_files = self._find_files(target_path, [".py"])
        for f in py_files:
            result.files_scanned += 1
            locations = self.find_print_statements(f)
            for loc in locations:
                result.add_location(loc)

        return result

    def migrate_file(self, file_path: str) -> MigrationResult:
        """Migrate log statements in a single file.

        Args:
            file_path: Path to file to migrate.

        Returns:
            MigrationResult for this file.
        """
        result = MigrationResult()
        path = Path(file_path)

        if not path.exists():
            result.add_error(f"File does not exist: {file_path}")
            return result

        result.files_scanned = 1

        try:
            content = path.read_text()
            original_content = content
            modified = False

            # Handle TypeScript/JavaScript files
            if path.suffix in [".ts", ".tsx", ".js", ".jsx"]:
                for log_type, pattern in self.CONSOLE_PATTERNS.items():
                    level = self.LEVEL_MAP[log_type]

                    def replace_console(match):
                        nonlocal modified
                        modified = True
                        args = match.group(1)
                        return f"logger.{level.value}({args})"

                    content = pattern.sub(replace_console, content)

                # Add import if modified and not present
                if modified and "import { logger }" not in content:
                    content = self.config.ts_import + "\n\n" + content

            # Handle Python files
            elif path.suffix == ".py":
                def replace_print(match):
                    nonlocal modified
                    modified = True
                    indent = match.group(1)
                    args = match.group(2)
                    return f"{indent}logger.info({args})"

                content = self.PRINT_PATTERN.sub(replace_print, content)

                # Add import if modified and not present
                if modified and "logger = logging.getLogger" not in content:
                    content = self.config.import_statement + "\n\n" + content

            if modified and not self.config.dry_run:
                path.write_text(content)
                result.files_modified = 1
                result.logs_migrated = sum(
                    1 for _ in self.PRINT_PATTERN.finditer(original_content)
                ) + sum(
                    len(list(p.finditer(original_content)))
                    for p in self.CONSOLE_PATTERNS.values()
                )

        except Exception as e:
            result.add_error(f"Failed to migrate {file_path}: {e}")

        return result

    def migrate_directory(self, path: str) -> MigrationResult:
        """Migrate all log statements in a directory.

        Args:
            path: Directory path to migrate.

        Returns:
            MigrationResult for all files.
        """
        result = MigrationResult()
        target_path = Path(path)

        if not target_path.exists():
            result.add_error(f"Path does not exist: {path}")
            return result

        # Get all relevant files
        all_files = (
            self._find_files(target_path, [".ts", ".tsx", ".js", ".jsx"]) +
            self._find_files(target_path, [".py"])
        )

        for f in all_files:
            file_result = self.migrate_file(str(f))
            result.files_scanned += file_result.files_scanned
            result.files_modified += file_result.files_modified
            result.logs_migrated += file_result.logs_migrated
            result.errors.extend(file_result.errors)

        result.success = len(result.errors) == 0
        return result


def find_console_logs(path: str) -> list[LogLocation]:
    """Convenience function to find all console.log statements.

    Args:
        path: Directory path to scan.

    Returns:
        List of LogLocation objects.
    """
    migrator = LoggerMigrator()
    result = migrator.scan_directory(path)
    return result.locations


def migrate_logs(
    path: str,
    dry_run: bool = True,
    config: Optional[MigrationConfig] = None
) -> MigrationResult:
    """Convenience function to migrate log statements.

    Args:
        path: Path to migrate.
        dry_run: If True, don't modify files.
        config: Optional migration configuration.

    Returns:
        MigrationResult with operation details.
    """
    cfg = config or MigrationConfig()
    cfg.dry_run = dry_run
    migrator = LoggerMigrator(cfg)
    return migrator.migrate_directory(path)
