"""
Code Formatter Module - AC-1: Code formatting with black, isort, flake8.

This module provides automated code formatting capabilities including:
- Python formatting with black
- Import sorting with isort
- TypeScript/JavaScript formatting with prettier

Implements: MD-2788 AC-1
"""

import logging
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class FormatTool(Enum):
    """Supported formatting tools."""
    BLACK = "black"
    ISORT = "isort"
    PRETTIER = "prettier"
    AUTOPEP8 = "autopep8"


class FormatStatus(Enum):
    """Format operation status."""
    SUCCESS = "success"
    REFORMATTED = "reformatted"
    UNCHANGED = "unchanged"
    ERROR = "error"
    SKIPPED = "skipped"


@dataclass
class FormatConfig:
    """Configuration for code formatting."""
    line_length: int = 88
    target_version: str = "py311"
    skip_string_normalization: bool = False
    isort_profile: str = "black"
    known_first_party: list[str] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=lambda: [
        ".git", "__pycache__", ".venv", "node_modules", "dist", "build"
    ])


@dataclass
class FileFormatResult:
    """Result for a single file format operation."""
    file_path: str
    status: FormatStatus
    tool: FormatTool
    changes_made: bool
    error_message: Optional[str] = None
    diff: Optional[str] = None


@dataclass
class FormatResult:
    """Result of a format operation."""
    files_checked: int = 0
    files_reformatted: int = 0
    files_unchanged: int = 0
    files_errored: int = 0
    file_results: list[FileFormatResult] = field(default_factory=list)
    success: bool = True
    summary: str = ""

    @property
    def total_files(self) -> int:
        """Get total files processed."""
        return self.files_checked

    def add_file_result(self, result: FileFormatResult) -> None:
        """Add a file result and update counters."""
        self.file_results.append(result)
        self.files_checked += 1

        if result.status == FormatStatus.REFORMATTED:
            self.files_reformatted += 1
        elif result.status == FormatStatus.UNCHANGED:
            self.files_unchanged += 1
        elif result.status == FormatStatus.ERROR:
            self.files_errored += 1
            self.success = False


class CodeFormatter:
    """Manages code formatting operations."""

    def __init__(self, config: Optional[FormatConfig] = None):
        """Initialize code formatter.

        Args:
            config: Formatting configuration. Uses defaults if not provided.
        """
        self.config = config or FormatConfig()

    def _run_command(
        self,
        cmd: list[str],
        capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """Run a command and return the result."""
        logger.debug(f"Running command: {' '.join(cmd)}")
        return subprocess.run(
            cmd,
            capture_output=capture_output,
            text=True
        )

    def _find_python_files(self, path: Path) -> list[Path]:
        """Find all Python files in a path."""
        if path.is_file():
            return [path] if path.suffix == ".py" else []

        python_files = []
        for pattern in ["**/*.py"]:
            for file in path.glob(pattern):
                # Check exclusions
                skip = False
                for exclude in self.config.exclude_patterns:
                    if exclude in str(file):
                        skip = True
                        break
                if not skip:
                    python_files.append(file)

        return python_files

    def _find_typescript_files(self, path: Path) -> list[Path]:
        """Find all TypeScript/JavaScript files in a path."""
        if path.is_file():
            return [path] if path.suffix in [".ts", ".tsx", ".js", ".jsx"] else []

        ts_files = []
        for pattern in ["**/*.ts", "**/*.tsx", "**/*.js", "**/*.jsx"]:
            for file in path.glob(pattern):
                skip = False
                for exclude in self.config.exclude_patterns:
                    if exclude in str(file):
                        skip = True
                        break
                if not skip:
                    ts_files.append(file)

        return ts_files

    def format_with_black(
        self,
        path: str,
        check_only: bool = False
    ) -> FormatResult:
        """Format Python files with black.

        Args:
            path: File or directory path to format.
            check_only: If True, only check without modifying files.

        Returns:
            FormatResult with operation details.
        """
        result = FormatResult()
        target_path = Path(path)

        if not target_path.exists():
            result.success = False
            result.summary = f"Path does not exist: {path}"
            return result

        # Build black command
        cmd = [
            "black",
            "--line-length", str(self.config.line_length),
            "--target-version", self.config.target_version,
        ]

        if check_only:
            cmd.append("--check")
            cmd.append("--diff")

        # Add exclusions
        for exclude in self.config.exclude_patterns:
            cmd.extend(["--exclude", exclude])

        cmd.append(str(target_path))

        # Run black
        proc = self._run_command(cmd)

        # Parse results
        if proc.returncode == 0:
            result.summary = "All files formatted correctly"
            # Count files checked
            files = self._find_python_files(target_path)
            for f in files:
                result.add_file_result(FileFormatResult(
                    file_path=str(f),
                    status=FormatStatus.UNCHANGED,
                    tool=FormatTool.BLACK,
                    changes_made=False
                ))
        elif proc.returncode == 1 and not check_only:
            # Files were reformatted
            result.summary = "Files reformatted"
            # Parse output to find reformatted files
            if proc.stderr:
                for line in proc.stderr.split("\n"):
                    if "reformatted" in line.lower():
                        result.add_file_result(FileFormatResult(
                            file_path=line.strip(),
                            status=FormatStatus.REFORMATTED,
                            tool=FormatTool.BLACK,
                            changes_made=True
                        ))
        else:
            result.success = False
            result.summary = f"Black failed: {proc.stderr}"
            logger.error(f"Black failed: {proc.stderr}")

        return result

    def format_with_isort(
        self,
        path: str,
        check_only: bool = False
    ) -> FormatResult:
        """Sort imports with isort.

        Args:
            path: File or directory path to format.
            check_only: If True, only check without modifying files.

        Returns:
            FormatResult with operation details.
        """
        result = FormatResult()
        target_path = Path(path)

        if not target_path.exists():
            result.success = False
            result.summary = f"Path does not exist: {path}"
            return result

        # Build isort command
        cmd = [
            "isort",
            "--profile", self.config.isort_profile,
            "--line-length", str(self.config.line_length),
        ]

        if check_only:
            cmd.append("--check-only")
            cmd.append("--diff")

        # Add known first party
        if self.config.known_first_party:
            cmd.extend([
                "--known-first-party",
                ",".join(self.config.known_first_party)
            ])

        cmd.append(str(target_path))

        # Run isort
        proc = self._run_command(cmd)

        if proc.returncode == 0:
            result.summary = "All imports sorted correctly"
            files = self._find_python_files(target_path)
            for f in files:
                result.add_file_result(FileFormatResult(
                    file_path=str(f),
                    status=FormatStatus.UNCHANGED,
                    tool=FormatTool.ISORT,
                    changes_made=False
                ))
        elif proc.returncode == 1 and not check_only:
            result.summary = "Imports were re-sorted"
            # Some files were modified
            files = self._find_python_files(target_path)
            for f in files:
                result.add_file_result(FileFormatResult(
                    file_path=str(f),
                    status=FormatStatus.REFORMATTED,
                    tool=FormatTool.ISORT,
                    changes_made=True
                ))
        else:
            result.success = False
            result.summary = f"isort failed: {proc.stderr}"

        return result

    def format_with_prettier(
        self,
        path: str,
        check_only: bool = False
    ) -> FormatResult:
        """Format TypeScript/JavaScript files with prettier.

        Args:
            path: File or directory path to format.
            check_only: If True, only check without modifying files.

        Returns:
            FormatResult with operation details.
        """
        result = FormatResult()
        target_path = Path(path)

        if not target_path.exists():
            result.success = False
            result.summary = f"Path does not exist: {path}"
            return result

        # Find TS/JS files
        files = self._find_typescript_files(target_path)
        if not files:
            result.summary = "No TypeScript/JavaScript files found"
            return result

        # Build prettier command
        cmd = ["npx", "prettier"]

        if check_only:
            cmd.append("--check")
        else:
            cmd.append("--write")

        cmd.extend([str(f) for f in files])

        # Run prettier
        proc = self._run_command(cmd)

        if proc.returncode == 0:
            result.summary = "All files formatted correctly"
            for f in files:
                result.add_file_result(FileFormatResult(
                    file_path=str(f),
                    status=FormatStatus.UNCHANGED,
                    tool=FormatTool.PRETTIER,
                    changes_made=False
                ))
        else:
            # Parse output for modified files
            for f in files:
                result.add_file_result(FileFormatResult(
                    file_path=str(f),
                    status=FormatStatus.REFORMATTED,
                    tool=FormatTool.PRETTIER,
                    changes_made=True
                ))
            result.summary = "Files reformatted with prettier"

        return result

    def format_all(
        self,
        path: str,
        check_only: bool = False
    ) -> dict[str, FormatResult]:
        """Run all formatters on a path.

        Args:
            path: File or directory path to format.
            check_only: If True, only check without modifying files.

        Returns:
            Dictionary of tool name to FormatResult.
        """
        results = {}

        # Run black
        logger.info("Running black formatter...")
        results["black"] = self.format_with_black(path, check_only)

        # Run isort
        logger.info("Running isort...")
        results["isort"] = self.format_with_isort(path, check_only)

        # Run prettier for TS/JS
        logger.info("Running prettier...")
        results["prettier"] = self.format_with_prettier(path, check_only)

        return results


def format_python_files(
    path: str,
    check_only: bool = False,
    config: Optional[FormatConfig] = None
) -> FormatResult:
    """Convenience function to format Python files.

    Args:
        path: Path to format.
        check_only: If True, only check without modifying.
        config: Optional format configuration.

    Returns:
        Combined FormatResult from black and isort.
    """
    formatter = CodeFormatter(config)

    # Run both black and isort
    black_result = formatter.format_with_black(path, check_only)
    isort_result = formatter.format_with_isort(path, check_only)

    # Combine results
    combined = FormatResult()
    combined.files_checked = black_result.files_checked
    combined.files_reformatted = black_result.files_reformatted + isort_result.files_reformatted
    combined.files_unchanged = min(black_result.files_unchanged, isort_result.files_unchanged)
    combined.files_errored = black_result.files_errored + isort_result.files_errored
    combined.success = black_result.success and isort_result.success
    combined.file_results = black_result.file_results + isort_result.file_results

    return combined


def format_typescript_files(
    path: str,
    check_only: bool = False,
    config: Optional[FormatConfig] = None
) -> FormatResult:
    """Convenience function to format TypeScript files.

    Args:
        path: Path to format.
        check_only: If True, only check without modifying.
        config: Optional format configuration.

    Returns:
        FormatResult from prettier.
    """
    formatter = CodeFormatter(config)
    return formatter.format_with_prettier(path, check_only)
