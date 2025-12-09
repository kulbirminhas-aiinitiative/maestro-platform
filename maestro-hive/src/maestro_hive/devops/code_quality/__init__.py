"""
Code Quality Module for Maestro Platform.

This module provides code quality automation capabilities including:
- Python code formatting (black, isort)
- Linting (flake8, eslint)
- Technical debt analysis
- Logger migration utilities
- Schema standardization tools

Implements MD-2788: [Maintenance] Code Quality & Tech Debt
"""

from .formatter import (
    CodeFormatter,
    FormatResult,
    format_python_files,
    format_typescript_files,
)
from .linter import (
    CodeLinter,
    LintResult,
    LintViolation,
    run_flake8,
    run_eslint,
)
from .tech_debt import (
    TechDebtAnalyzer,
    DebtReport,
    DebtCategory,
    calculate_debt_score,
)
from .logger_migrator import (
    LoggerMigrator,
    LogLocation,
    MigrationResult,
    find_console_logs,
)
from .schema_migrator import (
    SchemaMigrator,
    CaseConvention,
    migrate_to_camel_case,
)

__all__ = [
    # Formatter
    "CodeFormatter",
    "FormatResult",
    "format_python_files",
    "format_typescript_files",
    # Linter
    "CodeLinter",
    "LintResult",
    "LintViolation",
    "run_flake8",
    "run_eslint",
    # Tech Debt
    "TechDebtAnalyzer",
    "DebtReport",
    "DebtCategory",
    "calculate_debt_score",
    # Logger Migrator
    "LoggerMigrator",
    "LogLocation",
    "MigrationResult",
    "find_console_logs",
    # Schema Migrator
    "SchemaMigrator",
    "CaseConvention",
    "migrate_to_camel_case",
]

__version__ = "1.0.0"
__epic__ = "MD-2788"
