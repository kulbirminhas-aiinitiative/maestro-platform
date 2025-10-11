"""
Universal Contract Protocol - Core Data Models
Version: 1.0.0

This module contains the canonical data model definitions for the Universal Contract Protocol.
These are the single source of truth - DO NOT duplicate these definitions elsewhere.

Import from: from contracts.models import ...
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import hashlib
import json


# ============================================================================
# Contract Lifecycle States
# ============================================================================

class ContractLifecycle(Enum):
    """
    State machine for contract lifecycle.

    Valid transitions:
    - DRAFT → PROPOSED
    - PROPOSED → NEGOTIATING | ACCEPTED | REJECTED
    - NEGOTIATING → ACCEPTED | REJECTED | AMENDED
    - ACCEPTED → IN_PROGRESS
    - IN_PROGRESS → FULFILLED | BREACHED
    - FULFILLED → VERIFIED | VERIFIED_WITH_WARNINGS | BREACHED
    - VERIFIED → (terminal state)
    - VERIFIED_WITH_WARNINGS → (terminal state)
    - BREACHED → AMENDED | (terminal state)
    - REJECTED → (terminal state)
    - AMENDED → PROPOSED
    """
    DRAFT = "draft"
    PROPOSED = "proposed"
    NEGOTIATING = "negotiating"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    FULFILLED = "fulfilled"
    VERIFIED = "verified"
    VERIFIED_WITH_WARNINGS = "verified_with_warnings"
    BREACHED = "breached"
    REJECTED = "rejected"
    AMENDED = "amended"


class ContractEventType(Enum):
    """Types of events in the contract lifecycle"""
    PROPOSED = "proposed"
    NEGOTIATING = "negotiating"
    ACCEPTED = "accepted"
    FULFILLED = "fulfilled"
    VERIFIED = "verified"
    BREACHED = "breached"
    REJECTED = "rejected"
    AMENDED = "amended"
    STATE_CHANGED = "state_changed"


# ============================================================================
# Acceptance Criteria Models
# ============================================================================

@dataclass
class AcceptanceCriterion:
    """
    A single acceptance criterion for a contract.
    This is the CANONICAL definition - do not duplicate.
    """
    # Identity
    criterion_id: str  # Unique identifier for this criterion

    # Definition
    description: str  # Human-readable description of what must be met
    validator_type: str  # Type of validator to use (e.g., "screenshot_diff", "openapi_validator")
    validation_config: Dict[str, Any]  # Validator-specific configuration

    # Enforcement
    required: bool = True  # Must pass for contract to be fulfilled
    blocking: bool = True  # Blocks dependent contracts if failed
    timeout_seconds: int = 300  # Maximum time allowed for validation

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    tags: List[str] = field(default_factory=list)


@dataclass
class CriterionResult:
    """
    Result of evaluating a single acceptance criterion.
    This is the CANONICAL definition - do not duplicate.
    """
    # Identity
    criterion_id: str  # References AcceptanceCriterion.criterion_id

    # Result
    passed: bool  # Did this criterion pass?
    actual_value: Any  # Actual value measured
    expected_value: Any  # Expected value or threshold
    message: str  # Human-readable result message

    # Evidence
    evidence: Dict[str, Any] = field(default_factory=dict)  # Supporting evidence

    # Metadata
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    evaluator: str = "system"  # Validator that evaluated this
    duration_ms: int = 0  # Time taken to evaluate


@dataclass
class VerificationResult:
    """
    Result of verifying an entire contract.
    This is the CANONICAL definition - do not duplicate.
    """
    # Identity
    contract_id: str  # Contract that was verified

    # Overall Result
    passed: bool  # Did the contract pass verification?
    overall_message: str  # Summary message

    # Per-Criterion Results
    criteria_results: List[CriterionResult]  # Results for each criterion

    # Artifacts and Evidence
    artifacts: List[str] = field(default_factory=list)  # Paths to artifact manifests
    evidence_manifest: Optional[str] = None  # Path to evidence manifest

    # Metadata
    verified_at: datetime = field(default_factory=datetime.utcnow)
    verified_by: str = "system"  # Validator or human
    total_duration_ms: int = 0  # Total verification time

    # Versioning (for caching/memoization)
    validator_versions: Dict[str, str] = field(default_factory=dict)  # {"openapi": "0.18.0", "axe": "4.4.0"}
    environment: Dict[str, str] = field(default_factory=dict)  # {"python": "3.11", "node": "20.0"}

    def cache_key(self) -> str:
        """Generate deterministic cache key including validator versions"""
        key_components = [
            self.contract_id,
            json.dumps(self.validator_versions, sort_keys=True),
            json.dumps(self.environment, sort_keys=True)
        ]
        return hashlib.sha256("|".join(key_components).encode()).hexdigest()


# ============================================================================
# Contract Events
# ============================================================================

@dataclass
class ContractEvent:
    """
    Base class for all contract lifecycle events.
    This is the CANONICAL definition - do not duplicate.
    """
    event_id: str  # Unique event identifier
    event_type: str  # Type of event
    contract_id: str  # Contract this event relates to
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContractProposedEvent(ContractEvent):
    """Emitted when a contract is proposed"""
    proposer: str = ""  # Agent who proposed the contract
    contract: Optional['UniversalContract'] = None  # The proposed contract


@dataclass
class ContractAcceptedEvent(ContractEvent):
    """Emitted when a contract is accepted"""
    acceptor: str = ""  # Agent who accepted the contract
    acceptance_timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ContractFulfilledEvent(ContractEvent):
    """Emitted when a contract is fulfilled (claimed complete)"""
    fulfiller: str = ""  # Agent who fulfilled the contract
    deliverables: List[str] = field(default_factory=list)  # Artifact IDs


@dataclass
class ContractVerifiedEvent(ContractEvent):
    """Emitted when a contract is verified"""
    verifier: str = ""  # Validator or agent who verified
    verification_result: Optional[VerificationResult] = None  # Verification result


@dataclass
class ContractBreachedEvent(ContractEvent):
    """Emitted when a contract is breached"""
    breach: Optional['ContractBreach'] = None  # Details of the breach
    severity: str = "major"  # "critical", "major", "minor"


# ============================================================================
# Validation Policy
# ============================================================================

@dataclass
class ValidationPolicy:
    """
    Configurable validation thresholds for different environments.
    Allows realistic defaults with stretch targets.
    """
    # Environment
    environment: str  # "development", "staging", "production"

    # Accessibility Thresholds
    accessibility_min_score: int = 95  # Realistic: minor violations allowed
    accessibility_target_score: int = 98  # Stretch: minimal violations
    accessibility_world_class: int = 100  # Aspirational: zero violations

    # Performance Thresholds (milliseconds)
    response_time_p95_ms: int = 500  # Realistic: acceptable UX
    response_time_p95_target_ms: int = 300  # Stretch: good UX
    response_time_p95_world_class_ms: int = 200  # Aspirational: excellent UX

    response_time_p99_ms: int = 1000
    response_time_p99_target_ms: int = 500
    response_time_p99_world_class_ms: int = 300

    # Test Coverage Thresholds (percentage)
    test_coverage_min: int = 80  # Realistic: good coverage
    test_coverage_target: int = 90  # Stretch: excellent coverage
    test_coverage_world_class: int = 95  # Aspirational: near-complete

    # Security Vulnerability Thresholds
    critical_vulnerabilities: int = 0  # Always zero
    high_vulnerabilities: int = 2  # Realistic
    medium_vulnerabilities: int = 10  # Realistic
    low_vulnerabilities: int = 50  # Informational

    # Code Quality Thresholds
    code_quality_score: int = 8  # Out of 10
    type_coverage_min: int = 70  # Type annotation coverage
    complexity_max: int = 10  # Cyclomatic complexity

    @staticmethod
    def for_environment(env: str) -> 'ValidationPolicy':
        """Get appropriate policy for environment"""
        policies = {
            "development": ValidationPolicy(
                environment="development",
                accessibility_min_score=90,  # More lenient
                response_time_p95_ms=1000,  # More lenient
                test_coverage_min=70
            ),
            "staging": ValidationPolicy(
                environment="staging",
                accessibility_min_score=95,
                response_time_p95_ms=500,
                test_coverage_min=80
            ),
            "production": ValidationPolicy(
                environment="production",
                accessibility_min_score=98,  # Strict
                response_time_p95_ms=300,  # Strict
                test_coverage_min=85
            )
        }
        return policies.get(env, ValidationPolicy(environment=env))


# ============================================================================
# Contract Breach
# ============================================================================

@dataclass
class ContractBreach:
    """Details of a contract breach"""
    breach_id: str
    contract_id: str
    severity: str  # "critical", "major", "minor"
    description: str
    failed_criteria: List[str]  # List of criterion_ids that failed
    timestamp: datetime = field(default_factory=datetime.utcnow)
    remediation_steps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Universal Contract
# ============================================================================

@dataclass
class UniversalContract:
    """
    The main contract class that all agents use to specify requirements.
    This is the CANONICAL definition - do not duplicate.
    """
    # Identity
    contract_id: str  # Unique identifier
    contract_type: str  # Type of contract (UX_DESIGN, API_SPECIFICATION, etc.)
    name: str  # Human-readable name
    description: str  # Detailed description

    # Parties
    provider_agent: str  # Agent providing/fulfilling the contract
    consumer_agents: List[str]  # Agents consuming/verifying the contract

    # Specification
    specification: Dict[str, Any]  # Contract-type specific specification

    # Acceptance Criteria
    acceptance_criteria: List[AcceptanceCriterion]  # Criteria for fulfillment

    # Dependencies
    depends_on: List[str] = field(default_factory=list)  # Contract IDs this depends on

    # Lifecycle
    lifecycle_state: ContractLifecycle = ContractLifecycle.DRAFT
    events: List[ContractEvent] = field(default_factory=list)

    # Priority and Blocking
    is_blocking: bool = True  # Does this block dependent contracts?
    priority: str = "MEDIUM"  # CRITICAL, HIGH, MEDIUM, LOW

    # Versioning
    schema_version: str = "1.0.0"  # Version of the contract schema
    contract_version: str = "1.0.0"  # Version of this specific contract

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = "system"
    tags: List[str] = field(default_factory=list)

    # Verification
    verification_result: Optional[VerificationResult] = None
    breach_consequences: List[str] = field(default_factory=list)

    def transition_to(self, new_state: ContractLifecycle) -> bool:
        """
        Transition contract to a new state if valid.
        Returns True if transition was valid and performed, False otherwise.
        """
        valid_transitions = {
            ContractLifecycle.DRAFT: [ContractLifecycle.PROPOSED],
            ContractLifecycle.PROPOSED: [ContractLifecycle.NEGOTIATING, ContractLifecycle.ACCEPTED, ContractLifecycle.REJECTED],
            ContractLifecycle.NEGOTIATING: [ContractLifecycle.ACCEPTED, ContractLifecycle.REJECTED, ContractLifecycle.AMENDED],
            ContractLifecycle.ACCEPTED: [ContractLifecycle.IN_PROGRESS],
            ContractLifecycle.IN_PROGRESS: [ContractLifecycle.FULFILLED, ContractLifecycle.BREACHED],
            ContractLifecycle.FULFILLED: [ContractLifecycle.VERIFIED, ContractLifecycle.VERIFIED_WITH_WARNINGS, ContractLifecycle.BREACHED],
            ContractLifecycle.VERIFIED: [],  # Terminal state
            ContractLifecycle.VERIFIED_WITH_WARNINGS: [],  # Terminal state
            ContractLifecycle.BREACHED: [ContractLifecycle.AMENDED],  # Can be amended to fix breach
            ContractLifecycle.REJECTED: [],  # Terminal state
            ContractLifecycle.AMENDED: [ContractLifecycle.PROPOSED],
        }

        if new_state in valid_transitions.get(self.lifecycle_state, []):
            self.lifecycle_state = new_state
            self.updated_at = datetime.utcnow()
            return True
        return False

    def add_event(self, event: ContractEvent) -> None:
        """Add an event to the contract's event log"""
        self.events.append(event)
        self.updated_at = datetime.utcnow()

    def is_fulfilled(self) -> bool:
        """Check if contract is in a fulfilled or verified state"""
        return self.lifecycle_state in [
            ContractLifecycle.FULFILLED,
            ContractLifecycle.VERIFIED,
            ContractLifecycle.VERIFIED_WITH_WARNINGS
        ]

    def is_terminal(self) -> bool:
        """Check if contract is in a terminal state"""
        return self.lifecycle_state in [
            ContractLifecycle.VERIFIED,
            ContractLifecycle.VERIFIED_WITH_WARNINGS,
            ContractLifecycle.REJECTED
        ]

    def can_start_work(self) -> bool:
        """Check if work can begin on this contract"""
        return self.lifecycle_state == ContractLifecycle.ACCEPTED


# ============================================================================
# Execution Plan (for dependency resolution)
# ============================================================================

@dataclass
class ExecutionPlan:
    """
    Execution plan for a set of contracts based on dependency graph.
    Generated by ContractRegistry.
    """
    plan_id: str
    contracts: List[UniversalContract]  # All contracts in the plan
    execution_order: List[str]  # Contract IDs in topological order
    dependency_graph: Dict[str, List[str]]  # contract_id -> [dependent_contract_ids]
    parallel_groups: List[List[str]]  # Groups of contracts that can run in parallel
    estimated_duration_minutes: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Module Exports
# ============================================================================

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
