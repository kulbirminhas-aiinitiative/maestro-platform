"""
Validator Framework
Version: 1.0.0

Pluggable validator system for contract acceptance criteria verification.
"""

from contracts.validators.base import BaseValidator, ValidationResult, ValidationError
from contracts.validators.screenshot_diff import ScreenshotDiffValidator
from contracts.validators.openapi import OpenAPIValidator
from contracts.validators.axe_core import AxeCoreValidator
from contracts.validators.performance import PerformanceValidator
from contracts.validators.security import SecurityValidator

__all__ = [
    "BaseValidator",
    "ValidationResult",
    "ValidationError",
    "ScreenshotDiffValidator",
    "OpenAPIValidator",
    "AxeCoreValidator",
    "PerformanceValidator",
    "SecurityValidator",
]
