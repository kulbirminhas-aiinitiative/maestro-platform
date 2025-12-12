"""
Fix Verification Loop - Verifies fixes and runs regression tests.

This module provides the FixVerificationLoop class that validates fixes
and ensures they don't introduce regressions.

EPIC: MD-3027 - Self-Healing Execution Loop (Phase 3)
Task: MD-3031 - Implement FixVerificationLoop
"""

from __future__ import annotations

import asyncio
import logging
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class VerificationStatus(Enum):
    """Status of fix verification."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    PARTIAL = "partial"
    SKIPPED = "skipped"


class TestType(Enum):
    """Types of tests to run."""
    UNIT = "unit"
    INTEGRATION = "integration"
    REGRESSION = "regression"
    SMOKE = "smoke"
    ALL = "all"


@dataclass
class TestResult:
    """Result of a single test execution."""
    test_name: str
    test_type: TestType
    status: VerificationStatus
    duration_seconds: float
    output: str = ""
    error_message: Optional[str] = None
    assertions_passed: int = 0
    assertions_failed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "test_name": self.test_name,
            "test_type": self.test_type.value,
            "status": self.status.value,
            "duration_seconds": self.duration_seconds,
            "output": self.output[:500] if self.output else "",
            "error_message": self.error_message,
            "assertions_passed": self.assertions_passed,
            "assertions_failed": self.assertions_failed,
        }


@dataclass
class VerificationResult:
    """Result of complete fix verification."""
    verification_id: str
    fix_description: str
    status: VerificationStatus
    test_results: List[TestResult] = field(default_factory=list)
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    total_duration_seconds: float = 0.0
    regressions_detected: List[str] = field(default_factory=list)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def pass_rate(self) -> float:
        """Calculate test pass rate."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100

    @property
    def has_regressions(self) -> bool:
        """Check if any regressions were detected."""
        return len(self.regressions_detected) > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "verification_id": self.verification_id,
            "fix_description": self.fix_description,
            "status": self.status.value,
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "skipped_tests": self.skipped_tests,
            "pass_rate": self.pass_rate,
            "total_duration_seconds": self.total_duration_seconds,
            "regressions_detected": self.regressions_detected,
            "has_regressions": self.has_regressions,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "test_results": [t.to_dict() for t in self.test_results],
        }


@dataclass
class VerificationConfig:
    """Configuration for fix verification."""
    test_directory: str = "tests"
    test_command: str = "pytest"
    test_timeout_seconds: int = 300
    run_regression_tests: bool = True
    run_smoke_tests: bool = True
    fail_fast: bool = False
    min_pass_rate: float = 95.0
    enable_coverage: bool = True
    coverage_threshold: float = 80.0
    parallel_tests: bool = True
    max_parallel: int = 4


class FixVerificationLoop:
    """
    Verifies fixes by running tests and detecting regressions.

    This class:
    - Runs targeted tests for specific fixes
    - Executes regression test suites
    - Detects new failures introduced by fixes
    - Provides detailed verification reports

    Example:
        >>> verifier = FixVerificationLoop()
        >>> result = await verifier.verify_fix(
        ...     fix_id="FIX-001",
        ...     fix_description="Fixed timeout handling",
        ...     affected_modules=["execution.py", "retry.py"]
        ... )
        >>> if result.status == VerificationStatus.PASSED:
        ...     print("Fix verified successfully!")
    """

    def __init__(
        self,
        config: Optional[VerificationConfig] = None,
        test_runner: Optional[Callable] = None,
    ):
        """
        Initialize the verification loop.

        Args:
            config: Verification configuration
            test_runner: Optional custom test runner function
        """
        self.config = config or VerificationConfig()
        self._custom_test_runner = test_runner
        self._baseline_results: Dict[str, TestResult] = {}
        self._verification_history: List[VerificationResult] = []

        logger.info(
            f"FixVerificationLoop initialized with test_dir={self.config.test_directory}"
        )

    async def _run_pytest(
        self,
        test_path: str,
        test_type: TestType,
        extra_args: Optional[List[str]] = None,
    ) -> TestResult:
        """Run pytest for a specific test path."""
        start_time = time.time()

        cmd = [
            self.config.test_command,
            test_path,
            "-v",
            "--tb=short",
        ]

        if extra_args:
            cmd.extend(extra_args)

        if self.config.enable_coverage:
            cmd.extend(["--cov", "--cov-report=term-missing"])

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.config.test_timeout_seconds,
                )
            except asyncio.TimeoutError:
                process.kill()
                return TestResult(
                    test_name=test_path,
                    test_type=test_type,
                    status=VerificationStatus.FAILED,
                    duration_seconds=time.time() - start_time,
                    error_message=f"Test timed out after {self.config.test_timeout_seconds}s",
                )

            output = stdout.decode() + stderr.decode()
            duration = time.time() - start_time

            # Parse test results
            passed = output.count(" passed")
            failed = output.count(" failed")
            skipped = output.count(" skipped")

            if process.returncode == 0:
                status = VerificationStatus.PASSED
            elif failed > 0:
                status = VerificationStatus.FAILED
            else:
                status = VerificationStatus.PARTIAL

            return TestResult(
                test_name=test_path,
                test_type=test_type,
                status=status,
                duration_seconds=duration,
                output=output,
                assertions_passed=passed,
                assertions_failed=failed,
            )

        except Exception as e:
            return TestResult(
                test_name=test_path,
                test_type=test_type,
                status=VerificationStatus.FAILED,
                duration_seconds=time.time() - start_time,
                error_message=str(e),
            )

    async def _run_custom_tests(
        self,
        test_path: str,
        test_type: TestType,
    ) -> TestResult:
        """Run tests using custom test runner."""
        if not self._custom_test_runner:
            raise ValueError("No custom test runner configured")

        start_time = time.time()

        try:
            if asyncio.iscoroutinefunction(self._custom_test_runner):
                result = await self._custom_test_runner(test_path)
            else:
                result = self._custom_test_runner(test_path)

            return TestResult(
                test_name=test_path,
                test_type=test_type,
                status=VerificationStatus.PASSED if result else VerificationStatus.FAILED,
                duration_seconds=time.time() - start_time,
            )
        except Exception as e:
            return TestResult(
                test_name=test_path,
                test_type=test_type,
                status=VerificationStatus.FAILED,
                duration_seconds=time.time() - start_time,
                error_message=str(e),
            )

    def _detect_regressions(
        self,
        current_results: List[TestResult],
    ) -> List[str]:
        """
        Detect tests that previously passed but now fail.

        Args:
            current_results: Current test results

        Returns:
            List of regression descriptions
        """
        regressions = []

        for result in current_results:
            baseline = self._baseline_results.get(result.test_name)

            if baseline and baseline.status == VerificationStatus.PASSED:
                if result.status == VerificationStatus.FAILED:
                    regressions.append(
                        f"REGRESSION: {result.test_name} (was passing, now failing)"
                    )

        return regressions

    async def _run_tests_parallel(
        self,
        test_paths: List[str],
        test_type: TestType,
    ) -> List[TestResult]:
        """Run multiple tests in parallel."""
        semaphore = asyncio.Semaphore(self.config.max_parallel)

        async def run_with_semaphore(path: str) -> TestResult:
            async with semaphore:
                if self._custom_test_runner:
                    return await self._run_custom_tests(path, test_type)
                else:
                    return await self._run_pytest(path, test_type)

        tasks = [run_with_semaphore(path) for path in test_paths]
        return await asyncio.gather(*tasks)

    async def verify_fix(
        self,
        fix_id: str,
        fix_description: str,
        affected_modules: Optional[List[str]] = None,
        specific_tests: Optional[List[str]] = None,
        test_types: Optional[List[TestType]] = None,
    ) -> VerificationResult:
        """
        Verify a fix by running relevant tests.

        Args:
            fix_id: Unique identifier for the fix
            fix_description: Description of what was fixed
            affected_modules: List of affected module paths
            specific_tests: Specific test files to run
            test_types: Types of tests to run (defaults to all)

        Returns:
            VerificationResult with test outcomes
        """
        result = VerificationResult(
            verification_id=fix_id,
            fix_description=fix_description,
            status=VerificationStatus.PENDING,
            started_at=datetime.utcnow(),
        )

        start_time = time.time()
        test_types = test_types or [TestType.UNIT, TestType.REGRESSION]

        logger.info(f"Starting verification for fix: {fix_id}")

        try:
            result.status = VerificationStatus.RUNNING

            # Determine which tests to run
            tests_to_run: List[tuple[str, TestType]] = []

            if specific_tests:
                for test in specific_tests:
                    tests_to_run.append((test, TestType.UNIT))
            elif affected_modules:
                # Find related tests
                for module in affected_modules:
                    module_name = Path(module).stem
                    test_file = f"{self.config.test_directory}/test_{module_name}.py"
                    if Path(test_file).exists():
                        tests_to_run.append((test_file, TestType.UNIT))

            # Add regression tests if configured
            if self.config.run_regression_tests and TestType.REGRESSION in test_types:
                regression_dir = f"{self.config.test_directory}/regression"
                if Path(regression_dir).exists():
                    tests_to_run.append((regression_dir, TestType.REGRESSION))

            # Add smoke tests if configured
            if self.config.run_smoke_tests and TestType.SMOKE in test_types:
                smoke_dir = f"{self.config.test_directory}/smoke"
                if Path(smoke_dir).exists():
                    tests_to_run.append((smoke_dir, TestType.SMOKE))

            # If no specific tests found, run all
            if not tests_to_run:
                tests_to_run.append((self.config.test_directory, TestType.ALL))

            # Run tests
            if self.config.parallel_tests:
                test_paths = [t[0] for t in tests_to_run]
                test_type = tests_to_run[0][1] if tests_to_run else TestType.ALL
                test_results = await self._run_tests_parallel(test_paths, test_type)
            else:
                test_results = []
                for test_path, test_type in tests_to_run:
                    if self._custom_test_runner:
                        tr = await self._run_custom_tests(test_path, test_type)
                    else:
                        tr = await self._run_pytest(test_path, test_type)
                    test_results.append(tr)

                    # Fail fast if configured
                    if self.config.fail_fast and tr.status == VerificationStatus.FAILED:
                        break

            # Aggregate results
            result.test_results = test_results
            result.total_tests = len(test_results)
            result.passed_tests = sum(1 for t in test_results if t.status == VerificationStatus.PASSED)
            result.failed_tests = sum(1 for t in test_results if t.status == VerificationStatus.FAILED)
            result.skipped_tests = sum(1 for t in test_results if t.status == VerificationStatus.SKIPPED)

            # Check for regressions
            result.regressions_detected = self._detect_regressions(test_results)

            # Determine overall status
            if result.failed_tests > 0 or result.has_regressions:
                result.status = VerificationStatus.FAILED
            elif result.pass_rate >= self.config.min_pass_rate:
                result.status = VerificationStatus.PASSED
            else:
                result.status = VerificationStatus.PARTIAL

            # Update baseline for future comparisons
            for tr in test_results:
                self._baseline_results[tr.test_name] = tr

        except Exception as e:
            result.status = VerificationStatus.FAILED
            logger.error(f"Verification failed: {e}")

        finally:
            result.completed_at = datetime.utcnow()
            result.total_duration_seconds = time.time() - start_time
            self._verification_history.append(result)

            logger.info(
                f"Verification {fix_id} completed: {result.status.value} "
                f"({result.passed_tests}/{result.total_tests} passed)"
            )

        return result

    async def run_regression_suite(self) -> VerificationResult:
        """
        Run the full regression test suite.

        Returns:
            VerificationResult for the regression run
        """
        return await self.verify_fix(
            fix_id=f"regression_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            fix_description="Full regression test suite",
            test_types=[TestType.REGRESSION],
        )

    async def run_smoke_tests(self) -> VerificationResult:
        """
        Run smoke tests for quick validation.

        Returns:
            VerificationResult for smoke tests
        """
        return await self.verify_fix(
            fix_id=f"smoke_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            fix_description="Smoke test suite",
            test_types=[TestType.SMOKE],
        )

    def get_verification_history(self) -> List[VerificationResult]:
        """Get history of verifications."""
        return list(self._verification_history)

    def get_statistics(self) -> Dict[str, Any]:
        """Get verification statistics."""
        if not self._verification_history:
            return {"total_verifications": 0}

        passed = sum(1 for v in self._verification_history if v.status == VerificationStatus.PASSED)
        failed = sum(1 for v in self._verification_history if v.status == VerificationStatus.FAILED)

        return {
            "total_verifications": len(self._verification_history),
            "passed": passed,
            "failed": failed,
            "pass_rate": (passed / len(self._verification_history)) * 100,
            "total_regressions": sum(len(v.regressions_detected) for v in self._verification_history),
            "baseline_tests_tracked": len(self._baseline_results),
        }

    def clear_baseline(self) -> None:
        """Clear baseline results."""
        self._baseline_results.clear()

    def clear_history(self) -> None:
        """Clear verification history."""
        self._verification_history.clear()


# Singleton instance
_default_verifier: Optional[FixVerificationLoop] = None


def get_fix_verifier(config: Optional[VerificationConfig] = None) -> FixVerificationLoop:
    """Get or create the default FixVerificationLoop instance."""
    global _default_verifier
    if _default_verifier is None:
        _default_verifier = FixVerificationLoop(config=config)
    return _default_verifier


def reset_fix_verifier() -> None:
    """Reset the default verifier instance."""
    global _default_verifier
    _default_verifier = None
