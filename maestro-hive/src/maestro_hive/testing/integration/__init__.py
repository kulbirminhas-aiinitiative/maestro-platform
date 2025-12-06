"""
Integration Testing Framework

EPIC: MD-2509
[BLOCK-ARCH] Sub-EPIC 4: Integration Testing Framework

Test interfaces, not internals.

Acceptance Criteria:
- AC-1: Skip unit tests for TRUSTED blocks
- AC-2: Contract tests verify interfaces
- AC-3: Integration tests for composition
- AC-4: 90% fewer tests for composed systems
"""

from .models import (
    TrustStatus,
    BlockTestScope,
    ContractSpec,
    ContractResult,
    IntegrationResult,
    TestRequirements,
    TrustEvidence,
)
from .trust_manager import BlockTrustManager
from .contract_tester import ContractTester
from .integration_runner import IntegrationRunner
from .scope_decider import TestScopeDecider

__all__ = [
    # Enums and models
    "TrustStatus",
    "BlockTestScope",
    "ContractSpec",
    "ContractResult",
    "IntegrationResult",
    "TestRequirements",
    "TrustEvidence",
    # Main components
    "BlockTrustManager",
    "ContractTester",
    "IntegrationRunner",
    "TestScopeDecider",
]
