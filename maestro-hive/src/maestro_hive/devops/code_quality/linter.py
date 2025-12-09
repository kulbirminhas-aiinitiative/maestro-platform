"""
Code Linter Module - AC-2: Linting violation fixes.

This module provides linting capabilities including:
- Python linting with flake8
- TypeScript/JavaScript linting with eslint
- Violation tracking and reporting

Implements: MD-2788 AC-2
"""

import json
import logging
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class LintSeverity(Enum):
    """Lint violation severity levels."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    CONVENTION = "convention"


class LintTool(Enum):
    """Supported linting tools."""
    FLAKE8 = "flake8"
    ESLINT = "eslint"
    MYPY = "mypy"
    PYLINT = "pylint"


@dataclass
class LintViolation:
    """A single lint violation."""
    file_path: str
    line: int
    column: int
    code: str
    message: str
    severity: LintSeverity
    tool: LintTool
    rule: Optional[str] = None
    suggestion: Optional[str] = None

    @property
    def location(self) -> str:
        """Get location string."""
        return f"{self.file_path}:{self.line}:{self.column}"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "file_path": self.file_path,
            "line": self.line,
            "column": self.column,
            "code": self.code,
            "message": self.message,
            "severity": self.severity.value,
            "tool": self.tool.value,
            "rule": self.rule,
            "suggestion": self.suggestion,
        }


@dataclass
class LintConfig:
    """Configuration for linting."""
    max_line_length: int = 88
    max_complexity: int = 10
    ignore_codes: list[str] = field(default_factory=lambda: [
        "E203",  # Whitespace before ':' (black conflict)
        "E501",  # Line too long (handled by black)
        "W503",  # Line break before binary operator
    ])
    exclude_patterns: list[str] = field(default_factory=lambda: [
        ".git", "__pycache__", ".venv", "node_modules", "dist"
    ])


@dataclass
class LintResult:
    """Result of a linting operation."""
    total_files: int = 0
    files_with_violations: int = 0
    violations: list[LintViolation] = field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0
    success: bool = True
    summary: str = ""

    @property
    def total_violations(self) -> int:
        """Get total violation count."""
        return len(self.violations)

    def add_violation(self, violation: LintViolation) -> None:
        """Add a violation and update counters."""
        self.violations.append(violation)
        if violation.severity == LintSeverity.ERROR:
            self.error_count += 1
        elif violation.severity == LintSeverity.WARNING:
            self.warning_count += 1

    def get_violations_by_file(self) -> dict[str, list[LintViolation]]:
        """Group violations by file."""
        by_file: dict[str, list[LintViolation]] = {}
        for v in self.violations:
            if v.file_path not in by_file:
                by_file[v.file_path] = []
            by_file[v.file_path].append(v)
        return by_file

    def get_violations_by_code(self) -> dict[str, list[LintViolation]]:
        """Group violations by error code."""
        by_code: dict[str, list[LintViolation]] = {}
        for v in self.violations:
            if v.code not in by_code:
                by_code[v.code] = []
            by_code[v.code].append(v)
        return by_code


class CodeLinter:
    """Manages code linting operations."""

    def __init__(self, config: Optional[LintConfig] = None):
        """Initialize code linter.

        Args:
            config: Linting configuration.
        """
        self.config = config or LintConfig()

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

    def _parse_flake8_output(self, output: str) -> list[LintViolation]:
        """Parse flake8 output into violations."""
        violations = []

        for line in output.strip().split("\n"):
            if not line:
                continue

            # Format: file:line:column: code message
            try:
                parts = line.split(":", 3)
                if len(parts) >= 4:
                    file_path = parts[0]
                    line_num = int(parts[1])
                    column = int(parts[2])
                    code_msg = parts[3].strip()

                    # Extract code and message
                    if " " in code_msg:
                        code, message = code_msg.split(" ", 1)
                    else:
                        code = code_msg
                        message = ""

                    # Determine severity
                    if code.startswith("E"):
                        severity = LintSeverity.ERROR
                    elif code.startswith("W"):
                        severity = LintSeverity.WARNING
                    elif code.startswith("F"):
                        severity = LintSeverity.ERROR
                    else:
                        severity = LintSeverity.CONVENTION

                    violations.append(LintViolation(
                        file_path=file_path,
                        line=line_num,
                        column=column,
                        code=code,
                        message=message,
                        severity=severity,
                        tool=LintTool.FLAKE8,
                    ))
            except (ValueError, IndexError) as e:
                logger.warning(f"Failed to parse flake8 line: {line} - {e}")

        return violations

    def _parse_eslint_output(self, output: str) -> list[LintViolation]:
        """Parse eslint JSON output into violations."""
        violations = []

        try:
            data = json.loads(output)
            for file_result in data:
                file_path = file_result.get("filePath", "")
                for msg in file_result.get("messages", []):
                    severity = (
                        LintSeverity.ERROR if msg.get("severity") == 2
                        else LintSeverity.WARNING
                    )
                    violations.append(LintViolation(
                        file_path=file_path,
                        line=msg.get("line", 0),
                        column=msg.get("column", 0),
                        code=msg.get("ruleId", ""),
                        message=msg.get("message", ""),
                        severity=severity,
                        tool=LintTool.ESLINT,
                        rule=msg.get("ruleId"),
                    ))
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse eslint output: {e}")

        return violations

    def run_flake8(
        self,
        path: str,
        show_source: bool = False
    ) -> LintResult:
        """Run flake8 linting on Python files.

        Args:
            path: File or directory path to lint.
            show_source: If True, include source code in output.

        Returns:
            LintResult with violations.
        """
        result = LintResult()
        target_path = Path(path)

        if not target_path.exists():
            result.success = False
            result.summary = f"Path does not exist: {path}"
            return result

        # Build flake8 command
        cmd = [
            "flake8",
            "--max-line-length", str(self.config.max_line_length),
            "--max-complexity", str(self.config.max_complexity),
        ]

        # Add ignored codes
        if self.config.ignore_codes:
            cmd.extend(["--extend-ignore", ",".join(self.config.ignore_codes)])

        # Add exclusions
        if self.config.exclude_patterns:
            cmd.extend(["--exclude", ",".join(self.config.exclude_patterns)])

        if show_source:
            cmd.append("--show-source")

        cmd.append(str(target_path))

        # Run flake8
        proc = self._run_command(cmd)

        # Parse output
        if proc.stdout:
            violations = self._parse_flake8_output(proc.stdout)
            for v in violations:
                result.add_violation(v)

        # Count files
        if target_path.is_dir():
            python_files = list(target_path.glob("**/*.py"))
            result.total_files = len([
                f for f in python_files
                if not any(p in str(f) for p in self.config.exclude_patterns)
            ])
        else:
            result.total_files = 1

        result.files_with_violations = len(result.get_violations_by_file())
        result.success = result.error_count == 0
        result.summary = (
            f"Found {result.total_violations} violations "
            f"({result.error_count} errors, {result.warning_count} warnings)"
        )

        return result

    def run_eslint(
        self,
        path: str,
        fix: bool = False
    ) -> LintResult:
        """Run eslint on TypeScript/JavaScript files.

        Args:
            path: File or directory path to lint.
            fix: If True, auto-fix violations where possible.

        Returns:
            LintResult with violations.
        """
        result = LintResult()
        target_path = Path(path)

        if not target_path.exists():
            result.success = False
            result.summary = f"Path does not exist: {path}"
            return result

        # Build eslint command
        cmd = [
            "npx", "eslint",
            "--format", "json",
            "--ext", ".ts,.tsx,.js,.jsx",
        ]

        if fix:
            cmd.append("--fix")

        cmd.append(str(target_path))

        # Run eslint
        proc = self._run_command(cmd)

        # Parse output
        if proc.stdout:
            violations = self._parse_eslint_output(proc.stdout)
            for v in violations:
                result.add_violation(v)

        # Count files
        if target_path.is_dir():
            ts_files = list(target_path.glob("**/*.ts")) + list(target_path.glob("**/*.tsx"))
            result.total_files = len([
                f for f in ts_files
                if not any(p in str(f) for p in self.config.exclude_patterns)
            ])
        else:
            result.total_files = 1

        result.files_with_violations = len(result.get_violations_by_file())
        result.success = result.error_count == 0
        result.summary = (
            f"Found {result.total_violations} violations "
            f"({result.error_count} errors, {result.warning_count} warnings)"
        )

        return result

    def run_all(self, path: str) -> dict[str, LintResult]:
        """Run all linters on a path.

        Args:
            path: File or directory path to lint.

        Returns:
            Dictionary of tool name to LintResult.
        """
        results = {}

        logger.info("Running flake8...")
        results["flake8"] = self.run_flake8(path)

        logger.info("Running eslint...")
        results["eslint"] = self.run_eslint(path)

        return results


def run_flake8(
    path: str,
    config: Optional[LintConfig] = None
) -> LintResult:
    """Convenience function to run flake8.

    Args:
        path: Path to lint.
        config: Optional lint configuration.

    Returns:
        LintResult with violations.
    """
    linter = CodeLinter(config)
    return linter.run_flake8(path)


def run_eslint(
    path: str,
    config: Optional[LintConfig] = None
) -> LintResult:
    """Convenience function to run eslint.

    Args:
        path: Path to lint.
        config: Optional lint configuration.

    Returns:
        LintResult with violations.
    """
    linter = CodeLinter(config)
    return linter.run_eslint(path)
