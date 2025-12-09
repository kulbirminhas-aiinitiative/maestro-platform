"""
SDLC Validation Module - MD-2482
Core validation capabilities for the SDLC Engine.
"""

from .bdv.framework_detector import TestFramework, TestFrameworkDetector, FrameworkConfig
from .bdv.test_runner import TestRunner, TestResults, CoverageReport, IsolatedTestRunner
from .acc.architecture_validator import (
    ArchitectureValidator,
    ArchitecturePattern,
    ValidationResult,
    ContractValidator,
)
from .mock.mock_manager import MockManager, MockServer, MockStatus, MockRegistry

__all__ = [
    # BDV
    "TestFramework",
    "TestFrameworkDetector",
    "FrameworkConfig",
    "TestRunner",
    "TestResults",
    "CoverageReport",
    "IsolatedTestRunner",
    # ACC
    "ArchitectureValidator",
    "ArchitecturePattern",
    "ValidationResult",
    "ContractValidator",
    # Mock
    "MockManager",
    "MockServer",
    "MockStatus",
    "MockRegistry",
]
