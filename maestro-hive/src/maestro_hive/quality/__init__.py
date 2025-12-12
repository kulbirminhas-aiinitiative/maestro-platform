"""
Quality Module for Maestro Hive

This module provides quality assurance tools including:
- Code Linting (MD-3098): JIT validation for agent-generated code
- Quality Fabric Integration: Validation system integration
- Progressive Quality Management: Phase-based quality gates
"""

from .code_linter import (
    CodeLinter,
    LintResult,
    LintError,
    LintSeverity,
    LintTool,
    LinterConfig,
    LINTER_CONFIG,
    get_code_linter,
    reset_code_linter,
    lint_code,
)

__all__ = [
    # Code Linter (MD-3098)
    "CodeLinter",
    "LintResult",
    "LintError",
    "LintSeverity",
    "LintTool",
    "LinterConfig",
    "LINTER_CONFIG",
    "get_code_linter",
    "reset_code_linter",
    "lint_code",
]
