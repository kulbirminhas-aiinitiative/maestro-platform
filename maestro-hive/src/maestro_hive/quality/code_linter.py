#!/usr/bin/env python3
"""
Code Linter - JIT Validation for Agent-Generated Code (MD-3098)

This module implements automated code linting with a feedback loop for the
PersonaExecutor workflow, as specified in the AGORA Architecture (Critics Guild).

Key Features:
    - AC-1: Integrates flake8 and mypy into validation workflow
    - AC-2: Automatically runs linters when output_type == 'code'
    - AC-3: Feedback loop - errors fed back to agent for retry
    - AC-4: Configurable max_lint_retries (default: 3)

Architecture:
    CodeLinter
        ├── lint() - Run all configured linters
        ├── run_flake8() - Style and syntax checking
        ├── run_mypy() - Static type checking
        ├── parse_errors() - Structure error messages
        └── build_retry_prompt() - Generate agent feedback

Usage:
    >>> linter = CodeLinter()
    >>> result = linter.lint("def foo():\\n    return 'bar'")
    >>> if not result.passed:
    ...     prompt = linter.build_retry_prompt(result.errors)
"""

import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION
# =============================================================================

LINTER_CONFIG = {
    # Max retry attempts for lint failures (AC-4)
    "max_lint_retries": int(os.environ.get("MAESTRO_MAX_LINT_RETRIES", 3)),

    # Timeout for lint commands in seconds
    "lint_timeout": int(os.environ.get("MAESTRO_LINT_TIMEOUT", 30)),

    # Enable/disable specific linters
    "enable_flake8": os.environ.get("MAESTRO_ENABLE_FLAKE8", "true").lower() == "true",
    "enable_mypy": os.environ.get("MAESTRO_ENABLE_MYPY", "true").lower() == "true",

    # Flake8 configuration
    "flake8_max_line_length": 120,
    "flake8_ignore": ["E501", "W503"],  # Common exceptions

    # Mypy configuration
    "mypy_ignore_missing_imports": True,
    "mypy_strict": False,

    # Error severity thresholds
    "blocking_error_codes": ["E999", "F821", "F401", "F811"],  # Must fail
    "warning_codes": ["E501", "W291", "W293", "W391"],  # Pass with warning
}


# =============================================================================
# DATA MODELS
# =============================================================================

class LintSeverity(Enum):
    """Severity level for lint issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class LintTool(Enum):
    """Linting tool identifier."""
    FLAKE8 = "flake8"
    MYPY = "mypy"


@dataclass
class LintError:
    """Individual lint error/warning."""
    tool: LintTool
    severity: LintSeverity
    line: int
    column: int
    code: str
    message: str
    file_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "tool": self.tool.value,
            "severity": self.severity.value,
            "line": self.line,
            "column": self.column,
            "code": self.code,
            "message": self.message,
            "file_path": self.file_path
        }

    def to_string(self) -> str:
        """Format as human-readable string."""
        return f"Line {self.line}:{self.column}: [{self.code}] {self.message}"


@dataclass
class LintResult:
    """Result of linting operation."""
    passed: bool
    errors: List[LintError] = field(default_factory=list)
    warnings: List[LintError] = field(default_factory=list)
    flake8_output: str = ""
    mypy_output: str = ""
    duration_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def has_errors(self) -> bool:
        """Check if there are blocking errors."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if there are warnings."""
        return len(self.warnings) > 0

    @property
    def error_count(self) -> int:
        """Get total error count."""
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        """Get total warning count."""
        return len(self.warnings)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "passed": self.passed,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "errors": [e.to_dict() for e in self.errors],
            "warnings": [w.to_dict() for w in self.warnings],
            "flake8_output": self.flake8_output,
            "mypy_output": self.mypy_output,
            "duration_seconds": self.duration_seconds,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class LinterConfig:
    """Configuration for CodeLinter."""
    max_retries: int = 3
    timeout: int = 30
    enable_flake8: bool = True
    enable_mypy: bool = True
    flake8_config: Dict[str, Any] = field(default_factory=dict)
    mypy_config: Dict[str, Any] = field(default_factory=dict)
    blocking_codes: List[str] = field(default_factory=list)
    warning_codes: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.blocking_codes:
            self.blocking_codes = LINTER_CONFIG["blocking_error_codes"]
        if not self.warning_codes:
            self.warning_codes = LINTER_CONFIG["warning_codes"]


# =============================================================================
# CODE LINTER
# =============================================================================

class CodeLinter:
    """
    Lint code with flake8 and mypy, with support for feedback loops.

    This class implements:
    - AC-1: flake8 and mypy integration
    - AC-2: Automatic linting for code output
    - AC-3: Error feedback for agent retry
    - AC-4: Configurable max retries (default: 3)

    Example:
        >>> linter = CodeLinter()
        >>> code = "def foo():\\n  return 'bar'"
        >>> result = linter.lint(code)
        >>> if not result.passed:
        ...     retry_prompt = linter.build_retry_prompt(result.errors)
        ...     print(retry_prompt)
    """

    def __init__(self, config: Optional[LinterConfig] = None):
        """
        Initialize the code linter.

        Args:
            config: Optional configuration override
        """
        self.config = config or LinterConfig(
            max_retries=LINTER_CONFIG["max_lint_retries"],
            timeout=LINTER_CONFIG["lint_timeout"],
            enable_flake8=LINTER_CONFIG["enable_flake8"],
            enable_mypy=LINTER_CONFIG["enable_mypy"]
        )

        logger.info("CodeLinter initialized")
        logger.info(f"  Max retries: {self.config.max_retries}")
        logger.info(f"  Timeout: {self.config.timeout}s")
        logger.info(f"  Flake8: {'enabled' if self.config.enable_flake8 else 'disabled'}")
        logger.info(f"  Mypy: {'enabled' if self.config.enable_mypy else 'disabled'}")

    def lint(
        self,
        code: str,
        language: str = "python",
        file_name: str = "generated_code.py"
    ) -> LintResult:
        """
        Lint the provided code.

        Args:
            code: The code to lint
            language: Programming language (currently only python supported)
            file_name: Name for temp file (affects mypy behavior)

        Returns:
            LintResult with all errors and warnings
        """
        import time
        start_time = time.time()

        if language != "python":
            logger.warning(f"Language {language} not supported, skipping lint")
            return LintResult(passed=True)

        errors: List[LintError] = []
        warnings: List[LintError] = []
        flake8_output = ""
        mypy_output = ""

        # Write code to temp file for linting
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.py',
            prefix='lint_',
            delete=False
        ) as tmp_file:
            tmp_file.write(code)
            tmp_path = tmp_file.name

        try:
            # Run flake8
            if self.config.enable_flake8:
                flake8_errors, flake8_output = self._run_flake8(tmp_path)
                for err in flake8_errors:
                    if err.code in self.config.blocking_codes:
                        errors.append(err)
                    elif err.code in self.config.warning_codes:
                        warnings.append(err)
                    else:
                        # Default to error for unknown codes
                        errors.append(err)

            # Run mypy
            if self.config.enable_mypy:
                mypy_errors, mypy_output = self._run_mypy(tmp_path)
                for err in mypy_errors:
                    # mypy errors are always blocking
                    errors.append(err)

        finally:
            # Clean up temp file
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        duration = time.time() - start_time
        passed = len(errors) == 0

        result = LintResult(
            passed=passed,
            errors=errors,
            warnings=warnings,
            flake8_output=flake8_output,
            mypy_output=mypy_output,
            duration_seconds=duration
        )

        logger.info(f"Lint completed in {duration:.2f}s - {'PASS' if passed else 'FAIL'}")
        if errors:
            logger.info(f"  Errors: {len(errors)}")
        if warnings:
            logger.info(f"  Warnings: {len(warnings)}")

        return result

    def _run_flake8(self, file_path: str) -> tuple[List[LintError], str]:
        """
        Run flake8 on the file.

        Returns:
            Tuple of (errors list, raw output)
        """
        errors: List[LintError] = []

        # Build flake8 command
        cmd = [
            "flake8",
            "--format=%(row)d:%(col)d:%(code)s:%(text)s",
            f"--max-line-length={LINTER_CONFIG['flake8_max_line_length']}"
        ]

        if LINTER_CONFIG["flake8_ignore"]:
            cmd.append(f"--ignore={','.join(LINTER_CONFIG['flake8_ignore'])}")

        cmd.append(file_path)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout
            )
            output = result.stdout + result.stderr

            # Parse output
            for line in output.strip().split('\n'):
                if line and ':' in line:
                    try:
                        parts = line.split(':', 3)
                        if len(parts) >= 4:
                            errors.append(LintError(
                                tool=LintTool.FLAKE8,
                                severity=LintSeverity.ERROR,
                                line=int(parts[0]),
                                column=int(parts[1]),
                                code=parts[2],
                                message=parts[3].strip(),
                                file_path=file_path
                            ))
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Could not parse flake8 line: {line} - {e}")

            return errors, output

        except subprocess.TimeoutExpired:
            logger.error(f"flake8 timed out after {self.config.timeout}s")
            return [], "TIMEOUT"
        except FileNotFoundError:
            logger.error("flake8 not found - is it installed?")
            return [], "FLAKE8_NOT_FOUND"

    def _run_mypy(self, file_path: str) -> tuple[List[LintError], str]:
        """
        Run mypy on the file.

        Returns:
            Tuple of (errors list, raw output)
        """
        errors: List[LintError] = []

        # Build mypy command
        cmd = ["mypy"]

        if LINTER_CONFIG["mypy_ignore_missing_imports"]:
            cmd.append("--ignore-missing-imports")

        if LINTER_CONFIG["mypy_strict"]:
            cmd.append("--strict")

        cmd.append(file_path)

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.timeout
            )
            output = result.stdout + result.stderr

            # Parse output
            for line in output.strip().split('\n'):
                if ': error:' in line:
                    try:
                        # Format: file.py:line: error: message
                        parts = line.split(':', 3)
                        if len(parts) >= 4:
                            errors.append(LintError(
                                tool=LintTool.MYPY,
                                severity=LintSeverity.ERROR,
                                line=int(parts[1]),
                                column=0,  # mypy doesn't always provide column
                                code="mypy",
                                message=parts[3].strip(),
                                file_path=file_path
                            ))
                    except (ValueError, IndexError) as e:
                        logger.debug(f"Could not parse mypy line: {line} - {e}")

            return errors, output

        except subprocess.TimeoutExpired:
            logger.error(f"mypy timed out after {self.config.timeout}s")
            return [], "TIMEOUT"
        except FileNotFoundError:
            logger.error("mypy not found - is it installed?")
            return [], "MYPY_NOT_FOUND"

    def build_retry_prompt(self, errors: List[LintError]) -> str:
        """
        Build a retry prompt for the agent with error details.

        This implements AC-3: Feedback loop with specific error context.

        Args:
            errors: List of lint errors

        Returns:
            Formatted prompt string for agent retry
        """
        lines = [
            "Your code failed linting with the following errors:",
            ""
        ]

        # Group by tool
        flake8_errors = [e for e in errors if e.tool == LintTool.FLAKE8]
        mypy_errors = [e for e in errors if e.tool == LintTool.MYPY]

        if flake8_errors:
            lines.append("flake8:")
            for err in flake8_errors:
                lines.append(f"- {err.to_string()}")
            lines.append("")

        if mypy_errors:
            lines.append("mypy:")
            for err in mypy_errors:
                lines.append(f"- {err.to_string()}")
            lines.append("")

        lines.append("Please fix these errors and provide the corrected code.")

        return '\n'.join(lines)

    def lint_with_retry(
        self,
        code: str,
        fix_callback,
        max_retries: Optional[int] = None
    ) -> tuple[LintResult, str, int]:
        """
        Lint code with automatic retry loop.

        This implements AC-4: Max retry loops.

        Args:
            code: Initial code to lint
            fix_callback: Async function that takes retry_prompt and returns fixed code
            max_retries: Override max retries

        Returns:
            Tuple of (final_result, final_code, attempts)
        """
        retries = max_retries or self.config.max_retries
        current_code = code
        attempts = 0

        for attempt in range(retries + 1):
            attempts = attempt + 1
            result = self.lint(current_code)

            if result.passed:
                logger.info(f"Lint passed on attempt {attempts}")
                return result, current_code, attempts

            if attempt < retries:
                logger.info(f"Lint failed on attempt {attempts}, retrying...")
                retry_prompt = self.build_retry_prompt(result.errors)
                current_code = fix_callback(retry_prompt)
            else:
                logger.warning(f"Lint failed after {attempts} attempts")

        return result, current_code, attempts


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_global_linter: Optional[CodeLinter] = None


def get_code_linter() -> CodeLinter:
    """Get or create global CodeLinter instance."""
    global _global_linter
    if _global_linter is None:
        _global_linter = CodeLinter()
    return _global_linter


def reset_code_linter() -> None:
    """Reset the global CodeLinter instance."""
    global _global_linter
    _global_linter = None


def lint_code(code: str, language: str = "python") -> LintResult:
    """
    Quick function to lint code.

    Args:
        code: Code to lint
        language: Programming language

    Returns:
        LintResult
    """
    return get_code_linter().lint(code, language)
