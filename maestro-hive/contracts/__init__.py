"""
Universal Contract Protocol - Main Module

This module provides the core contract protocol functionality for multi-agent
software development.

Version: 1.0.0
"""

from contracts.models import (
    # Enums
    ContractLifecycle,
    ContractEventType,

    # Acceptance Criteria
    AcceptanceCriterion,
    CriterionResult,
    VerificationResult,

    # Events
    ContractEvent,
    ContractProposedEvent,
    ContractAcceptedEvent,
    ContractFulfilledEvent,
    ContractVerifiedEvent,
    ContractBreachedEvent,

    # Validation
    ValidationPolicy,

    # Contract
    ContractBreach,
    UniversalContract,

    # Execution
    ExecutionPlan,
)

__version__ = "1.0.0"

__all__ = [
    # Enums
    "ContractLifecycle",
    "ContractEventType",

    # Acceptance Criteria
    "AcceptanceCriterion",
    "CriterionResult",
    "VerificationResult",

    # Events
    "ContractEvent",
    "ContractProposedEvent",
    "ContractAcceptedEvent",
    "ContractFulfilledEvent",
    "ContractVerifiedEvent",
    "ContractBreachedEvent",

    # Validation
    "ValidationPolicy",

    # Contract
    "ContractBreach",
    "UniversalContract",

    # Execution
    "ExecutionPlan",
]
