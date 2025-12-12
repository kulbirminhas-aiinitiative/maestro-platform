"""
JIT Validation & Persona Reflection Module (MD-3092)

This module implements shift-left validation with JIT syntax checking
and persona reflection loops (Generate → Test → Reflect → Refine).

Components:
    - JITValidator: Main validator orchestrating all checks
    - SyntaxChecker: AST-based Python syntax validation
    - ReflectionEngine: Analyze failures and suggest fixes
    - TestRunner: Execute tests within persona context
    - HelpNeeded: Exception for stuck agents

Usage:
    >>> from maestro_hive.validation import JITValidator
    >>> validator = JITValidator()
    >>> result = validator.validate_code(code, filename="generated.py")
    >>> if not result.valid:
    ...     reflection = validator.reflect(result)
    ...     fixed_code = validator.refine(code, reflection)
"""

from .exceptions import HelpNeeded, ValidationError, ReflectionError
from .syntax_checker import SyntaxChecker, SyntaxCheckResult
from .reflection_engine import ReflectionEngine, ReflectionResult
from .test_runner import TestRunner, TestResult
from .jit_validator import JITValidator, ValidationResult

__all__ = [
    # Main validator
    "JITValidator",
    "ValidationResult",
    # Components
    "SyntaxChecker",
    "SyntaxCheckResult",
    "ReflectionEngine",
    "ReflectionResult",
    "TestRunner",
    "TestResult",
    # Exceptions
    "HelpNeeded",
    "ValidationError",
    "ReflectionError",
]

__version__ = "1.0.0"
