"""Devops module for Maestro Hive.

This module provides DevOps automation capabilities including:
- Code quality tools (formatting, linting, technical debt analysis)
- Logger migration utilities
- Schema standardization tools

Implements: MD-2788 Code Quality & Tech Debt
"""

from .code_quality import (
    # Formatter
    CodeFormatter,
    FormatResult,
    format_python_files,
    format_typescript_files,
    # Linter
    CodeLinter,
    LintResult,
    LintViolation,
    run_flake8,
    run_eslint,
    # Tech Debt
    TechDebtAnalyzer,
    DebtReport,
    DebtCategory,
    calculate_debt_score,
    # Logger Migrator
    LoggerMigrator,
    LogLocation,
    MigrationResult,
    find_console_logs,
    # Schema Migrator
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
