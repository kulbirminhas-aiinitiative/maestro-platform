"""
Execution Phases for EPIC Executor.

Each phase corresponds to a step in the compliance audit process (inverted):
- Phase 1: Understanding - Parse EPIC, extract ACs, plan work
- Phase 2: Documentation - Generate Confluence docs
- Phase 3: Implementation - Execute work via AI agents
- Phase 4: Testing - Generate tests AND execute them (MD-2497)
- Phase 5: Correctness - TODO/FIXME audit
- Phase 6: Build - Build verification
- Phase 7: Evidence - AC evidence collection
- Phase 8: Compliance - Self-compliance check
"""

from .understanding import UnderstandingPhase
from .documentation import DocumentationPhase
from .implementation import ImplementationPhase
from .testing import TestingPhase
from .correctness import CorrectnessPhase
from .build import BuildPhase
from .evidence import EvidencePhase
from .compliance import CompliancePhase

# MD-2497: Test execution runner for actual test running (not just generation)
from .test_runner import (
    TestExecutionRunner,
    TestExecutionError,
    CoverageThresholdError,
    TestResult,
    CoverageResult,
    ExecutionResult,
    run_python_tests,
    run_typescript_tests,
)

__all__ = [
    "UnderstandingPhase",
    "DocumentationPhase",
    "ImplementationPhase",
    "TestingPhase",
    "CorrectnessPhase",
    "BuildPhase",
    "EvidencePhase",
    "CompliancePhase",
    # MD-2497 additions
    "TestExecutionRunner",
    "TestExecutionError",
    "CoverageThresholdError",
    "TestResult",
    "CoverageResult",
    "ExecutionResult",
    "run_python_tests",
    "run_typescript_tests",
]
