"""
EPIC Executor Module

Inverse of epic-compliance: Executes EPIC work with compliance-ready output.
Ensures 95%+ compliance score through systematic execution and documentation.

Usage:
    from epic_executor import EpicExecutor

    executor = EpicExecutor(jira_config, confluence_config)
    result = await executor.execute("MD-2385")
    print(f"Compliance Score: {result.compliance_score}%")
"""

from .executor import EpicExecutor
from .models import (
    ExecutionResult,
    ExecutionPhase,
    AcceptanceCriterion,
    ACEvidence,
    DocumentInfo,
    ComplianceScore,
    PhaseResult,
)

__all__ = [
    "EpicExecutor",
    "ExecutionResult",
    "ExecutionPhase",
    "AcceptanceCriterion",
    "ACEvidence",
    "DocumentInfo",
    "ComplianceScore",
    "PhaseResult",
]

__version__ = "1.0.0"
