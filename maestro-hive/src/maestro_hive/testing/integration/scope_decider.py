"""
Test Scope Decider

EPIC: MD-2509
AC-1: Skip unit tests for TRUSTED blocks
AC-4: 90% fewer tests for composed systems

Automatically determines test requirements based on block status.
"""

import logging
from typing import Any, Dict, List, Optional, Set

from .models import (
    TrustStatus,
    BlockTestScope,
    TestRequirements,
)
from .trust_manager import BlockTrustManager, get_trust_manager

logger = logging.getLogger(__name__)


class TestScopeDecider:
    """
    Decides test scope based on block trust status (AC-1, AC-4).

    Implements the testing scope matrix:
    - TRUSTED: Skip unit tests, contract only, E2E
    - CATALOGUED: Skip unit tests, full interface, E2E
    - NEW: Full test suite

    Example:
        decider = TestScopeDecider()

        # Get test scope for a block
        scope = decider.get_scope("auth_service")

        if not scope.run_unit_tests:
            print("Skipping unit tests")
        if scope.run_contract_tests:
            print("Running contract tests")
    """

    def __init__(
        self,
        trust_manager: Optional[BlockTrustManager] = None,
    ):
        """
        Initialize test scope decider.

        Args:
            trust_manager: Trust manager for status lookups
        """
        self.trust_manager = trust_manager or get_trust_manager()
        self._decisions: Dict[str, BlockTestScope] = {}
        self._override_scopes: Dict[str, TestRequirements] = {}

    def get_scope(
        self,
        block_name: str,
        version: str = "",
    ) -> BlockTestScope:
        """
        Get test scope for a block (AC-1).

        Args:
            block_name: Name of the block
            version: Optional version string

        Returns:
            BlockTestScope with test requirements
        """
        # Check for override
        if block_name in self._override_scopes:
            status = self.trust_manager.get_trust_status(block_name)
            scope = BlockTestScope(
                block_name=block_name,
                block_version=version,
                trust_status=status,
                requirements=self._override_scopes[block_name],
            )
        else:
            scope = self.trust_manager.get_test_scope(block_name, version)

        # Cache decision
        self._decisions[block_name] = scope

        logger.debug(
            f"Test scope for {block_name}: "
            f"unit={scope.run_unit_tests}, "
            f"contract={scope.run_contract_tests}, "
            f"integration={scope.run_integration_tests}"
        )

        return scope

    def get_scopes_for_blocks(
        self,
        block_names: List[str],
    ) -> Dict[str, BlockTestScope]:
        """
        Get test scopes for multiple blocks.

        Args:
            block_names: List of block names

        Returns:
            Dict mapping block name to test scope
        """
        return {name: self.get_scope(name) for name in block_names}

    def override_scope(
        self,
        block_name: str,
        requirements: TestRequirements,
    ) -> None:
        """
        Override test scope for a specific block.

        Use this for temporary overrides or special cases.

        Args:
            block_name: Block to override
            requirements: Custom test requirements
        """
        self._override_scopes[block_name] = requirements
        logger.info(f"Override test scope for {block_name}")

    def clear_override(self, block_name: str) -> None:
        """Clear scope override for a block."""
        if block_name in self._override_scopes:
            del self._override_scopes[block_name]

    def should_run_unit_tests(self, block_name: str) -> bool:
        """Check if unit tests should run for a block (AC-1)."""
        scope = self.get_scope(block_name)
        return scope.run_unit_tests

    def should_run_contract_tests(self, block_name: str) -> bool:
        """Check if contract tests should run for a block (AC-2)."""
        scope = self.get_scope(block_name)
        return scope.run_contract_tests

    def should_run_integration_tests(self, block_name: str) -> bool:
        """Check if integration tests should run for a block (AC-3)."""
        scope = self.get_scope(block_name)
        return scope.run_integration_tests

    def filter_for_unit_tests(
        self,
        block_names: List[str],
    ) -> List[str]:
        """
        Filter blocks that need unit testing (AC-1).

        Returns only NEW blocks that require full unit testing.
        """
        return [
            name for name in block_names
            if self.should_run_unit_tests(name)
        ]

    def filter_for_integration_tests(
        self,
        block_names: List[str],
    ) -> List[str]:
        """
        Filter blocks that need integration testing (AC-3).

        Returns CATALOGUED and NEW blocks.
        """
        return [
            name for name in block_names
            if self.should_run_integration_tests(name)
        ]

    def calculate_test_matrix(
        self,
        block_names: List[str],
    ) -> Dict[str, Any]:
        """
        Calculate complete test matrix for blocks.

        Returns summary of what tests will run for each block.
        """
        matrix = {
            "blocks": {},
            "summary": {
                "total_blocks": len(block_names),
                "trusted": 0,
                "catalogued": 0,
                "new": 0,
                "unit_tests_to_run": 0,
                "contract_tests_to_run": 0,
                "integration_tests_to_run": 0,
                "e2e_tests_to_run": 0,
            }
        }

        for name in block_names:
            scope = self.get_scope(name)

            matrix["blocks"][name] = {
                "trust_status": scope.trust_status.value,
                "unit_tests": scope.run_unit_tests,
                "contract_tests": scope.run_contract_tests,
                "integration_tests": scope.run_integration_tests,
                "e2e_tests": scope.run_e2e_tests,
            }

            # Update summary
            if scope.trust_status == TrustStatus.TRUSTED:
                matrix["summary"]["trusted"] += 1
            elif scope.trust_status == TrustStatus.CATALOGUED:
                matrix["summary"]["catalogued"] += 1
            else:
                matrix["summary"]["new"] += 1

            if scope.run_unit_tests:
                matrix["summary"]["unit_tests_to_run"] += 1
            if scope.run_contract_tests:
                matrix["summary"]["contract_tests_to_run"] += 1
            if scope.run_integration_tests:
                matrix["summary"]["integration_tests_to_run"] += 1
            if scope.run_e2e_tests:
                matrix["summary"]["e2e_tests_to_run"] += 1

        return matrix

    def estimate_test_reduction(
        self,
        block_names: List[str],
        tests_per_block: int = 10,
    ) -> Dict[str, Any]:
        """
        Estimate test reduction from trust-based testing (AC-4).

        Args:
            block_names: Blocks to analyze
            tests_per_block: Estimated tests per block (for calculation)

        Returns:
            Dict with reduction statistics
        """
        total_potential = len(block_names) * tests_per_block
        will_run = 0

        for name in block_names:
            scope = self.get_scope(name)
            if scope.run_unit_tests:
                will_run += tests_per_block
            else:
                # Only contract tests (typically ~20% of unit tests)
                will_run += tests_per_block * 0.2

        reduction = (1 - will_run / total_potential) * 100 if total_potential > 0 else 0

        return {
            "total_blocks": len(block_names),
            "potential_tests": total_potential,
            "estimated_tests_to_run": int(will_run),
            "tests_saved": int(total_potential - will_run),
            "reduction_percent": round(reduction, 1),
            "meets_90_percent_target": reduction >= 90,
        }

    def get_pytest_markers(self, block_name: str) -> List[str]:
        """
        Get pytest markers for a block's tests.

        Useful for pytest mark-based filtering.
        """
        scope = self.get_scope(block_name)
        markers = []

        if scope.run_unit_tests:
            markers.append("unit")
        if scope.run_contract_tests:
            markers.append("contract")
        if scope.run_integration_tests:
            markers.append("integration")
        if scope.run_e2e_tests:
            markers.append("e2e")

        return markers

    def get_skip_markers(self, block_name: str) -> List[str]:
        """
        Get pytest skip markers for a block.

        Returns markers that should be skipped.
        """
        scope = self.get_scope(block_name)
        skip = []

        if not scope.run_unit_tests:
            skip.append("unit")
        if not scope.run_contract_tests:
            skip.append("contract")
        if not scope.run_integration_tests:
            skip.append("integration")
        if not scope.run_e2e_tests:
            skip.append("e2e")

        return skip

    def get_decisions(self) -> Dict[str, BlockTestScope]:
        """Get all cached decisions."""
        return self._decisions.copy()

    def clear_decisions(self) -> None:
        """Clear cached decisions."""
        self._decisions.clear()
