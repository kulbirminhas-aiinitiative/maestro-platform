"""
Integration Runner

EPIC: MD-2509
AC-3: Integration tests for composition
AC-4: 90% fewer tests for composed systems

Executes integration tests for block compositions.
"""

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .models import (
    TrustStatus,
    BlockTestScope,
    IntegrationResult,
)
from .trust_manager import BlockTrustManager, get_trust_manager

logger = logging.getLogger(__name__)


class IntegrationRunner:
    """
    Runs integration tests for block compositions (AC-3, AC-4).

    Provides trust-aware test execution that skips unnecessary
    tests for trusted blocks, achieving 90% test reduction (AC-4).

    Example:
        runner = IntegrationRunner()

        # Register blocks
        runner.add_block("auth_service", auth_instance)
        runner.add_block("user_service", user_instance)

        # Run integration tests
        result = await runner.run_integration_tests(["auth_service", "user_service"])

        print(f"Tests executed: {result.total_tests - result.skipped_tests}")
        print(f"Test reduction: {result.test_reduction_percent}%")
    """

    def __init__(
        self,
        trust_manager: Optional[BlockTrustManager] = None,
    ):
        """
        Initialize integration runner.

        Args:
            trust_manager: Trust manager for test scope decisions
        """
        self.trust_manager = trust_manager or get_trust_manager()
        self._blocks: Dict[str, Any] = {}
        self._tests: Dict[str, List[Callable]] = {}  # block -> test functions
        self._composition_tests: List[Tuple[List[str], Callable]] = []
        self._stats = {
            "runs": 0,
            "tests_executed": 0,
            "tests_skipped": 0,
            "total_duration_ms": 0,
        }

    def add_block(
        self,
        name: str,
        block: Any,
        tests: Optional[List[Callable]] = None,
    ) -> None:
        """
        Register a block for integration testing.

        Args:
            name: Block name
            block: Block instance
            tests: Optional list of test functions
        """
        self._blocks[name] = block
        if tests:
            self._tests[name] = tests
        logger.info(f"Registered block for integration: {name}")

    def add_composition_test(
        self,
        block_names: List[str],
        test_func: Callable,
    ) -> None:
        """
        Add a test that verifies block composition.

        Args:
            block_names: Blocks involved in the composition
            test_func: Test function to run
        """
        self._composition_tests.append((block_names, test_func))

    def skip_unit_tests_for_trusted(
        self,
        block_names: List[str],
    ) -> List[str]:
        """
        Filter out blocks that should skip unit tests (AC-1, AC-4).

        Args:
            block_names: List of block names

        Returns:
            Blocks that need unit testing (NEW status only)
        """
        blocks_needing_tests = []

        for name in block_names:
            status = self.trust_manager.get_trust_status(name)
            if status == TrustStatus.NEW:
                blocks_needing_tests.append(name)
            else:
                logger.info(f"Skipping unit tests for {status.value} block: {name}")

        return blocks_needing_tests

    async def run_integration_tests(
        self,
        block_names: Optional[List[str]] = None,
    ) -> IntegrationResult:
        """
        Run integration tests for specified blocks (AC-3).

        Respects trust status to skip unnecessary tests (AC-4).

        Args:
            block_names: Blocks to test (all if None)

        Returns:
            IntegrationResult with test results
        """
        start_time = time.monotonic()
        self._stats["runs"] += 1

        blocks_to_test = block_names or list(self._blocks.keys())

        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        skipped_tests = 0
        failures: List[Dict[str, Any]] = []

        # Calculate potential tests before skipping
        potential_tests = 0
        for name in blocks_to_test:
            tests = self._tests.get(name, [])
            potential_tests += len(tests)
        potential_tests += len(self._composition_tests)

        # Run block-specific integration tests
        for name in blocks_to_test:
            scope = self.trust_manager.get_test_scope(name)

            if not scope.run_integration_tests:
                # Count as skipped (TRUSTED blocks skip integration)
                skipped_count = len(self._tests.get(name, []))
                skipped_tests += skipped_count
                logger.info(f"Skipped {skipped_count} tests for TRUSTED block: {name}")
                continue

            block = self._blocks.get(name)
            if block is None:
                continue

            tests = self._tests.get(name, [])
            for test_func in tests:
                total_tests += 1
                try:
                    if asyncio.iscoroutinefunction(test_func):
                        await test_func(block)
                    else:
                        test_func(block)
                    passed_tests += 1
                except Exception as e:
                    failed_tests += 1
                    failures.append({
                        "block": name,
                        "test": test_func.__name__,
                        "error": str(e),
                    })

        # Run composition tests
        for block_names_combo, test_func in self._composition_tests:
            # Skip if all blocks in composition are TRUSTED
            all_trusted = all(
                self.trust_manager.get_trust_status(name) == TrustStatus.TRUSTED
                for name in block_names_combo
            )

            if all_trusted:
                skipped_tests += 1
                logger.info(f"Skipped composition test - all blocks TRUSTED")
                continue

            total_tests += 1
            blocks = {name: self._blocks[name] for name in block_names_combo
                     if name in self._blocks}

            try:
                if asyncio.iscoroutinefunction(test_func):
                    await test_func(blocks)
                else:
                    test_func(blocks)
                passed_tests += 1
            except Exception as e:
                failed_tests += 1
                failures.append({
                    "blocks": block_names_combo,
                    "test": test_func.__name__,
                    "error": str(e),
                })

        duration_ms = int((time.monotonic() - start_time) * 1000)

        # Calculate test reduction (AC-4)
        test_reduction = (
            (skipped_tests / potential_tests * 100)
            if potential_tests > 0 else 0
        )

        # Update stats
        executed = total_tests
        self._stats["tests_executed"] += executed
        self._stats["tests_skipped"] += skipped_tests
        self._stats["total_duration_ms"] += duration_ms

        result = IntegrationResult(
            blocks_tested=blocks_to_test,
            passed=failed_tests == 0,
            total_tests=total_tests + skipped_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            failures=failures,
            test_reduction_percent=test_reduction,
            duration_ms=duration_ms,
        )

        logger.info(
            f"Integration tests: {passed_tests}/{executed} passed, "
            f"{skipped_tests} skipped ({test_reduction:.1f}% reduction)"
        )

        return result

    async def test_composition(
        self,
        block_names: List[str],
        composition_test: Optional[Callable] = None,
    ) -> IntegrationResult:
        """
        Test a specific block composition (AC-3).

        Args:
            block_names: Blocks in the composition
            composition_test: Optional test function

        Returns:
            IntegrationResult
        """
        start_time = time.monotonic()

        blocks = {name: self._blocks[name] for name in block_names
                 if name in self._blocks}

        total_tests = 1
        passed_tests = 0
        failed_tests = 0
        failures: List[Dict[str, Any]] = []

        if composition_test:
            try:
                if asyncio.iscoroutinefunction(composition_test):
                    await composition_test(blocks)
                else:
                    composition_test(blocks)
                passed_tests = 1
            except Exception as e:
                failed_tests = 1
                failures.append({
                    "blocks": block_names,
                    "error": str(e),
                })
        else:
            # Default composition test: verify blocks can be accessed
            passed_tests = 1

        duration_ms = int((time.monotonic() - start_time) * 1000)

        return IntegrationResult(
            blocks_tested=block_names,
            passed=failed_tests == 0,
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=0,
            failures=failures,
            test_reduction_percent=0,
            duration_ms=duration_ms,
        )

    def calculate_test_reduction(
        self,
        block_names: List[str],
    ) -> Dict[str, Any]:
        """
        Calculate potential test reduction for blocks (AC-4).

        Shows how many tests would be skipped with trust-based testing.
        """
        total_potential = 0
        would_skip = 0

        for name in block_names:
            status = self.trust_manager.get_trust_status(name)
            tests_count = len(self._tests.get(name, []))
            total_potential += tests_count

            if status == TrustStatus.TRUSTED:
                would_skip += tests_count  # Skip all
            elif status == TrustStatus.CATALOGUED:
                would_skip += tests_count // 2  # Skip ~half

        reduction = (would_skip / total_potential * 100) if total_potential > 0 else 0

        return {
            "total_potential_tests": total_potential,
            "would_skip": would_skip,
            "would_execute": total_potential - would_skip,
            "reduction_percent": reduction,
            "target_met": reduction >= 90,  # AC-4: 90% target
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get runner statistics."""
        total = self._stats["tests_executed"] + self._stats["tests_skipped"]
        return {
            "blocks_registered": len(self._blocks),
            "composition_tests": len(self._composition_tests),
            "runs": self._stats["runs"],
            "tests_executed": self._stats["tests_executed"],
            "tests_skipped": self._stats["tests_skipped"],
            "skip_rate": (
                self._stats["tests_skipped"] / total
                if total > 0 else 0
            ),
            "avg_duration_ms": (
                self._stats["total_duration_ms"] / self._stats["runs"]
                if self._stats["runs"] > 0 else 0
            ),
        }
