"""
Test Execution Runner for EPIC Executor

EPIC: MD-2497
AC-1: Integrate pytest runner for Python
AC-2: Integrate jest runner for TypeScript
AC-3: FAIL execution if tests fail
AC-4: Capture coverage metrics
AC-5: Block phase transition if coverage < threshold

This module provides actual test execution capabilities instead of just test generation.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class TestExecutionError(Exception):
    """Raised when test execution fails."""
    pass


class CoverageThresholdError(Exception):
    """Raised when coverage is below threshold - blocks phase transition."""
    pass


@dataclass
class TestResult:
    """Result from a single test run."""
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    total: int = 0
    duration_seconds: float = 0.0
    output: str = ""

    @property
    def success(self) -> bool:
        return self.failed == 0 and self.errors == 0


@dataclass
class CoverageResult:
    """Code coverage metrics."""
    line_coverage: float = 0.0
    branch_coverage: float = 0.0
    files_covered: int = 0
    total_files: int = 0
    uncovered_lines: Dict[str, List[int]] = field(default_factory=dict)

    @property
    def meets_threshold(self) -> bool:
        """Check if coverage meets minimum threshold (80%)."""
        return self.line_coverage >= 80.0


@dataclass
class ExecutionResult:
    """Combined test execution and coverage result."""
    test_result: TestResult
    coverage_result: Optional[CoverageResult]
    framework: str  # pytest, jest
    timestamp: datetime
    phase_gate_passed: bool = True
    blocking_reason: Optional[str] = None


class TestExecutionRunner:
    """
    Executes tests using pytest (Python) and jest (TypeScript).

    This class implements the actual test execution that was missing from
    the TestingPhase. It:
    1. Runs pytest/jest against test files (AC-1, AC-2)
    2. Fails if any tests fail (AC-3)
    3. Captures coverage metrics (AC-4)
    4. Blocks phase transition if coverage < threshold (AC-5)

    Usage:
        runner = TestExecutionRunner(
            project_root="/path/to/project",
            coverage_threshold=80.0
        )

        # Execute Python tests
        result = await runner.execute_pytest(test_paths=["/path/to/tests"])

        # Check if phase can proceed
        if not result.phase_gate_passed:
            raise CoverageThresholdError(result.blocking_reason)
    """

    def __init__(
        self,
        project_root: str = ".",
        coverage_threshold: float = 80.0,
        timeout_seconds: int = 300,
    ):
        """
        Initialize the test execution runner.

        Args:
            project_root: Root directory of the project
            coverage_threshold: Minimum coverage percentage required (AC-5)
            timeout_seconds: Maximum time for test execution
        """
        self.project_root = Path(project_root)
        self.coverage_threshold = coverage_threshold
        self.timeout_seconds = timeout_seconds

        logger.info(
            f"TestExecutionRunner initialized: "
            f"root={project_root}, threshold={coverage_threshold}%"
        )

    async def execute_pytest(
        self,
        test_paths: List[str],
        coverage_source: Optional[str] = None,
        extra_args: Optional[List[str]] = None,
    ) -> ExecutionResult:
        """
        Execute pytest and capture results.

        AC-1: Integrate pytest runner for Python
        AC-3: FAIL execution if tests fail
        AC-4: Capture coverage metrics
        AC-5: Block phase transition if coverage < threshold

        Args:
            test_paths: List of test file or directory paths
            coverage_source: Source directory for coverage measurement
            extra_args: Additional pytest arguments

        Returns:
            ExecutionResult with test and coverage information

        Raises:
            TestExecutionError: If pytest execution fails completely
        """
        logger.info(f"Executing pytest for: {test_paths}")
        started_at = datetime.now()

        # Build pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            "--tb=short",
            "-v",
            "--json-report",
            "--json-report-file=/tmp/pytest_report.json",
        ]

        # Add coverage if source provided
        if coverage_source:
            cmd.extend([
                f"--cov={coverage_source}",
                "--cov-report=json:/tmp/coverage.json",
                "--cov-report=term-missing",
            ])

        # Add extra args
        if extra_args:
            cmd.extend(extra_args)

        # Add test paths
        cmd.extend(test_paths)

        logger.debug(f"Pytest command: {' '.join(cmd)}")

        try:
            # Execute pytest
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(self.project_root),
            )

            try:
                stdout, _ = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout_seconds
                )
                output = stdout.decode("utf-8", errors="replace")
            except asyncio.TimeoutError:
                process.kill()
                raise TestExecutionError(
                    f"Test execution timed out after {self.timeout_seconds}s"
                )

            # Parse test results
            test_result = self._parse_pytest_results(output)
            test_result.output = output

            ended_at = datetime.now()
            test_result.duration_seconds = (ended_at - started_at).total_seconds()

            # Parse coverage if available
            coverage_result = None
            if coverage_source and Path("/tmp/coverage.json").exists():
                coverage_result = self._parse_coverage_results()

            # AC-3: Check if tests failed
            if not test_result.success:
                logger.error(
                    f"Tests failed: {test_result.failed} failures, "
                    f"{test_result.errors} errors"
                )

            # AC-5: Check coverage threshold
            phase_gate_passed = True
            blocking_reason = None

            if coverage_result and not coverage_result.meets_threshold:
                phase_gate_passed = False
                blocking_reason = (
                    f"Coverage {coverage_result.line_coverage:.1f}% is below "
                    f"threshold {self.coverage_threshold}%"
                )
                logger.warning(f"Phase gate blocked: {blocking_reason}")

            if not test_result.success:
                phase_gate_passed = False
                blocking_reason = (
                    f"Test failures: {test_result.failed} failed, "
                    f"{test_result.errors} errors"
                )

            return ExecutionResult(
                test_result=test_result,
                coverage_result=coverage_result,
                framework="pytest",
                timestamp=started_at,
                phase_gate_passed=phase_gate_passed,
                blocking_reason=blocking_reason,
            )

        except FileNotFoundError:
            raise TestExecutionError(
                "pytest not found. Install with: pip install pytest pytest-cov"
            )
        except Exception as e:
            raise TestExecutionError(f"Pytest execution failed: {e}")

    async def execute_jest(
        self,
        test_paths: List[str],
        config_path: Optional[str] = None,
    ) -> ExecutionResult:
        """
        Execute jest and capture results.

        AC-2: Integrate jest runner for TypeScript
        AC-3: FAIL execution if tests fail
        AC-4: Capture coverage metrics
        AC-5: Block phase transition if coverage < threshold

        Args:
            test_paths: List of test file or directory paths
            config_path: Path to jest config file

        Returns:
            ExecutionResult with test and coverage information

        Raises:
            TestExecutionError: If jest execution fails completely
        """
        logger.info(f"Executing jest for: {test_paths}")
        started_at = datetime.now()

        # Build jest command
        cmd = ["npx", "jest", "--json", "--coverage"]

        if config_path:
            cmd.extend(["--config", config_path])

        cmd.extend(test_paths)

        logger.debug(f"Jest command: {' '.join(cmd)}")

        try:
            # Execute jest
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(self.project_root),
            )

            try:
                stdout, _ = await asyncio.wait_for(
                    process.communicate(),
                    timeout=self.timeout_seconds
                )
                output = stdout.decode("utf-8", errors="replace")
            except asyncio.TimeoutError:
                process.kill()
                raise TestExecutionError(
                    f"Test execution timed out after {self.timeout_seconds}s"
                )

            # Parse jest JSON output
            test_result, coverage_result = self._parse_jest_results(output)
            test_result.output = output

            ended_at = datetime.now()
            test_result.duration_seconds = (ended_at - started_at).total_seconds()

            # AC-3 & AC-5: Check test results and coverage
            phase_gate_passed = True
            blocking_reason = None

            if not test_result.success:
                phase_gate_passed = False
                blocking_reason = (
                    f"Test failures: {test_result.failed} failed, "
                    f"{test_result.errors} errors"
                )

            if coverage_result and not coverage_result.meets_threshold:
                phase_gate_passed = False
                blocking_reason = (
                    f"Coverage {coverage_result.line_coverage:.1f}% is below "
                    f"threshold {self.coverage_threshold}%"
                )

            return ExecutionResult(
                test_result=test_result,
                coverage_result=coverage_result,
                framework="jest",
                timestamp=started_at,
                phase_gate_passed=phase_gate_passed,
                blocking_reason=blocking_reason,
            )

        except FileNotFoundError:
            raise TestExecutionError(
                "jest not found. Install with: npm install jest"
            )
        except Exception as e:
            raise TestExecutionError(f"Jest execution failed: {e}")

    def _parse_pytest_results(self, output: str) -> TestResult:
        """Parse pytest output to extract test results."""
        result = TestResult()

        # Try to read JSON report first
        json_report = Path("/tmp/pytest_report.json")
        if json_report.exists():
            try:
                with open(json_report) as f:
                    data = json.load(f)

                summary = data.get("summary", {})
                result.passed = summary.get("passed", 0)
                result.failed = summary.get("failed", 0)
                result.skipped = summary.get("skipped", 0)
                result.errors = summary.get("error", 0)
                result.total = sum([
                    result.passed, result.failed,
                    result.skipped, result.errors
                ])
                result.duration_seconds = data.get("duration", 0)
                return result
            except Exception as e:
                logger.warning(f"Failed to parse pytest JSON: {e}")

        # Fallback: parse stdout
        import re

        # Look for summary line like "5 passed, 2 failed, 1 skipped"
        summary_match = re.search(
            r"(\d+) passed.*?(\d+) failed|(\d+) passed",
            output,
            re.IGNORECASE
        )

        if summary_match:
            if summary_match.group(1):
                result.passed = int(summary_match.group(1))
            if summary_match.group(2):
                result.failed = int(summary_match.group(2))
            if summary_match.group(3):
                result.passed = int(summary_match.group(3))

        # Count errors
        result.errors = output.count("ERROR")
        result.total = result.passed + result.failed + result.errors

        return result

    def _parse_coverage_results(self) -> CoverageResult:
        """Parse coverage.json to extract coverage metrics."""
        result = CoverageResult()

        coverage_file = Path("/tmp/coverage.json")
        if not coverage_file.exists():
            return result

        try:
            with open(coverage_file) as f:
                data = json.load(f)

            totals = data.get("totals", {})
            result.line_coverage = totals.get("percent_covered", 0.0)
            result.files_covered = totals.get("covered_lines", 0)
            result.total_files = len(data.get("files", {}))

            # Extract uncovered lines per file
            for file_path, file_data in data.get("files", {}).items():
                missing = file_data.get("missing_lines", [])
                if missing:
                    result.uncovered_lines[file_path] = missing

        except Exception as e:
            logger.warning(f"Failed to parse coverage JSON: {e}")

        return result

    def _parse_jest_results(
        self,
        output: str
    ) -> Tuple[TestResult, Optional[CoverageResult]]:
        """Parse jest JSON output."""
        test_result = TestResult()
        coverage_result = None

        try:
            # Jest outputs JSON to stdout
            data = json.loads(output)

            test_result.passed = data.get("numPassedTests", 0)
            test_result.failed = data.get("numFailedTests", 0)
            test_result.total = data.get("numTotalTests", 0)
            test_result.skipped = data.get("numPendingTests", 0)

            # Parse coverage summary
            coverage_map = data.get("coverageMap", {})
            if coverage_map:
                coverage_result = CoverageResult()
                total_lines = 0
                covered_lines = 0

                for file_data in coverage_map.values():
                    line_map = file_data.get("s", {})
                    total_lines += len(line_map)
                    covered_lines += sum(1 for v in line_map.values() if v > 0)

                if total_lines > 0:
                    coverage_result.line_coverage = (
                        covered_lines / total_lines * 100
                    )
                coverage_result.total_files = len(coverage_map)

        except json.JSONDecodeError:
            # Fallback: parse text output
            import re

            passed_match = re.search(r"(\d+) passed", output)
            failed_match = re.search(r"(\d+) failed", output)

            if passed_match:
                test_result.passed = int(passed_match.group(1))
            if failed_match:
                test_result.failed = int(failed_match.group(1))

            test_result.total = test_result.passed + test_result.failed

        return test_result, coverage_result

    async def execute_all(
        self,
        python_tests: Optional[List[str]] = None,
        typescript_tests: Optional[List[str]] = None,
        python_source: Optional[str] = None,
    ) -> Dict[str, ExecutionResult]:
        """
        Execute both pytest and jest tests.

        Args:
            python_tests: Python test paths
            typescript_tests: TypeScript test paths
            python_source: Python source directory for coverage

        Returns:
            Dict mapping framework name to ExecutionResult
        """
        results = {}

        if python_tests:
            try:
                results["pytest"] = await self.execute_pytest(
                    test_paths=python_tests,
                    coverage_source=python_source,
                )
            except TestExecutionError as e:
                logger.error(f"Pytest execution failed: {e}")
                results["pytest"] = ExecutionResult(
                    test_result=TestResult(errors=1),
                    coverage_result=None,
                    framework="pytest",
                    timestamp=datetime.now(),
                    phase_gate_passed=False,
                    blocking_reason=str(e),
                )

        if typescript_tests:
            try:
                results["jest"] = await self.execute_jest(
                    test_paths=typescript_tests,
                )
            except TestExecutionError as e:
                logger.error(f"Jest execution failed: {e}")
                results["jest"] = ExecutionResult(
                    test_result=TestResult(errors=1),
                    coverage_result=None,
                    framework="jest",
                    timestamp=datetime.now(),
                    phase_gate_passed=False,
                    blocking_reason=str(e),
                )

        return results

    def check_phase_gate(
        self,
        results: Dict[str, ExecutionResult]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if all test results pass the phase gate.

        AC-5: Block phase transition if coverage < threshold

        Args:
            results: Dict of execution results by framework

        Returns:
            Tuple of (passed, blocking_reason)
        """
        for framework, result in results.items():
            if not result.phase_gate_passed:
                return False, result.blocking_reason

        return True, None


# Convenience functions for backward compatibility

async def run_python_tests(
    test_paths: List[str],
    coverage_source: Optional[str] = None,
    coverage_threshold: float = 80.0,
) -> ExecutionResult:
    """
    Run Python tests with pytest.

    This is a convenience wrapper for quick test execution.
    """
    runner = TestExecutionRunner(coverage_threshold=coverage_threshold)
    return await runner.execute_pytest(test_paths, coverage_source)


async def run_typescript_tests(
    test_paths: List[str],
    config_path: Optional[str] = None,
    coverage_threshold: float = 80.0,
) -> ExecutionResult:
    """
    Run TypeScript tests with jest.

    This is a convenience wrapper for quick test execution.
    """
    runner = TestExecutionRunner(coverage_threshold=coverage_threshold)
    return await runner.execute_jest(test_paths, config_path)
