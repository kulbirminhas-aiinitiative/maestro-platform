"""
Data Models for Integration Testing Framework

EPIC: MD-2509
AC-1: Skip unit tests for TRUSTED blocks
AC-2: Contract tests verify interfaces

Defines the core data models for trust-based testing.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from uuid import UUID, uuid4


class TrustStatus(str, Enum):
    """
    Trust status for blocks (AC-1).

    Determines what level of testing is required.
    """
    TRUSTED = "trusted"      # Skip unit tests, contract only
    CATALOGUED = "catalogued"  # Skip unit tests, full interface
    NEW = "new"              # Full test suite


@dataclass
class TestRequirements:
    """
    Test requirements based on trust status.

    Used by TestScopeDecider to determine what tests to run.
    """
    run_unit_tests: bool = True
    run_contract_tests: bool = True
    run_integration_tests: bool = True
    run_e2e_tests: bool = True

    @classmethod
    def for_status(cls, status: TrustStatus) -> "TestRequirements":
        """Get test requirements for a trust status."""
        if status == TrustStatus.TRUSTED:
            return cls(
                run_unit_tests=False,
                run_contract_tests=True,
                run_integration_tests=False,
                run_e2e_tests=True,
            )
        elif status == TrustStatus.CATALOGUED:
            return cls(
                run_unit_tests=False,
                run_contract_tests=True,
                run_integration_tests=True,
                run_e2e_tests=True,
            )
        else:  # NEW
            return cls(
                run_unit_tests=True,
                run_contract_tests=True,
                run_integration_tests=True,
                run_e2e_tests=True,
            )


@dataclass
class TrustEvidence:
    """
    Evidence supporting a block's trust status.

    Required to promote a block to TRUSTED status.
    """
    id: UUID = field(default_factory=uuid4)
    block_name: str = ""
    block_version: str = ""
    verified_by: str = ""
    verified_at: datetime = field(default_factory=datetime.utcnow)
    evidence_type: str = ""  # "manual_review", "automated", "external_audit"
    evidence_url: Optional[str] = None
    notes: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "block_name": self.block_name,
            "block_version": self.block_version,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at.isoformat(),
            "evidence_type": self.evidence_type,
            "evidence_url": self.evidence_url,
            "notes": self.notes,
            "metadata": self.metadata,
        }


@dataclass
class BlockTestScope:
    """
    Test scope for a specific block (AC-1, AC-3).

    Encapsulates what tests should run for a block.
    """
    block_name: str
    block_version: str = ""
    trust_status: TrustStatus = TrustStatus.NEW
    requirements: TestRequirements = field(default_factory=TestRequirements)
    skipped_test_count: int = 0
    executed_test_count: int = 0

    @property
    def run_unit_tests(self) -> bool:
        return self.requirements.run_unit_tests

    @property
    def run_contract_tests(self) -> bool:
        return self.requirements.run_contract_tests

    @property
    def run_integration_tests(self) -> bool:
        return self.requirements.run_integration_tests

    @property
    def run_e2e_tests(self) -> bool:
        return self.requirements.run_e2e_tests

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "block_name": self.block_name,
            "block_version": self.block_version,
            "trust_status": self.trust_status.value,
            "run_unit_tests": self.run_unit_tests,
            "run_contract_tests": self.run_contract_tests,
            "run_integration_tests": self.run_integration_tests,
            "run_e2e_tests": self.run_e2e_tests,
            "skipped_test_count": self.skipped_test_count,
            "executed_test_count": self.executed_test_count,
        }


@dataclass
class ContractSpec:
    """
    Specification for a block's contract (AC-2).

    Defines the interface that must be verified.
    """
    name: str
    version: str = "1.0.0"
    inputs: Dict[str, str] = field(default_factory=dict)  # name -> type
    outputs: Dict[str, str] = field(default_factory=dict)  # name -> type
    required_methods: List[str] = field(default_factory=list)
    invariants: List[str] = field(default_factory=list)
    pre_conditions: List[str] = field(default_factory=list)
    post_conditions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "required_methods": self.required_methods,
            "invariants": self.invariants,
            "pre_conditions": self.pre_conditions,
            "post_conditions": self.post_conditions,
            "metadata": self.metadata,
        }


@dataclass
class ContractResult:
    """
    Result of contract verification (AC-2).

    Contains details of what passed/failed during contract testing.
    """
    id: UUID = field(default_factory=uuid4)
    contract_name: str = ""
    block_name: str = ""
    passed: bool = False
    total_checks: int = 0
    passed_checks: int = 0
    failed_checks: int = 0
    failures: List[Dict[str, Any]] = field(default_factory=list)
    duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate."""
        if self.total_checks == 0:
            return 0.0
        return self.passed_checks / self.total_checks

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "contract_name": self.contract_name,
            "block_name": self.block_name,
            "passed": self.passed,
            "total_checks": self.total_checks,
            "passed_checks": self.passed_checks,
            "failed_checks": self.failed_checks,
            "pass_rate": self.pass_rate,
            "failures": self.failures,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class IntegrationResult:
    """
    Result of integration testing (AC-3).

    Contains results of testing block composition.
    """
    id: UUID = field(default_factory=uuid4)
    blocks_tested: List[str] = field(default_factory=list)
    passed: bool = False
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    failures: List[Dict[str, Any]] = field(default_factory=list)
    test_reduction_percent: float = 0.0  # AC-4: 90% fewer tests
    duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate (excluding skipped)."""
        executed = self.total_tests - self.skipped_tests
        if executed == 0:
            return 0.0
        return self.passed_tests / executed

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "blocks_tested": self.blocks_tested,
            "passed": self.passed,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "skipped_tests": self.skipped_tests,
            "pass_rate": self.pass_rate,
            "failures": self.failures,
            "test_reduction_percent": self.test_reduction_percent,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp.isoformat(),
        }
