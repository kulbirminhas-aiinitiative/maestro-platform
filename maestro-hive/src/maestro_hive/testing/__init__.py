"""
Testing & Validation Framework for Maestro Hive.

Implements MD-2787 acceptance criteria:
- AC-1: Comprehensive testing framework for maestro-hive modules
- AC-2: Test discovery and execution utilities
- AC-3: Test data generation capabilities
- AC-4: Validation helpers for common patterns
- AC-5: Integration with Quality Fabric for automated validation
- AC-6: Test reporting and metrics collection
"""

from .framework import TestFramework, TestConfig, TestCase, TestResults
from .runner import TestRunner, RunOptions, RunResult
from .discovery import TestDiscovery, DiscoveryConfig
from .data_generator import TestDataGenerator, DataGeneratorConfig
from .validators import ValidationHelpers, ValidationResult
from .reporter import TestReporter, TestReport, ReportFormat

__all__ = [
    # Framework
    'TestFramework',
    'TestConfig',
    'TestCase',
    'TestResults',
    # Runner
    'TestRunner',
    'RunOptions',
    'RunResult',
    # Discovery
    'TestDiscovery',
    'DiscoveryConfig',
    # Data Generation
    'TestDataGenerator',
    'DataGeneratorConfig',
    # Validation
    'ValidationHelpers',
    'ValidationResult',
    # Reporting
    'TestReporter',
    'TestReport',
    'ReportFormat',
]
