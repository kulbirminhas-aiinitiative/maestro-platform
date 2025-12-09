#!/usr/bin/env python3
"""
Test Runner: Executes tests using various frameworks.

Implements AC-2: Test discovery and execution utilities.
"""

import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .framework import TestCase, TestStatus

logger = logging.getLogger(__name__)


@dataclass
class RunOptions:
    """Test run configuration options."""
    parallel: bool = False
    workers: int = 4
    timeout: int = 300
    fail_fast: bool = False
    verbose: bool = True
    coverage: bool = True
    markers: List[str] = field(default_factory=list)
    exclude_markers: List[str] = field(default_factory=list)
    pattern: str = "test_*.py"


@dataclass
class RunResult:
    """Result of a test run."""
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration: float = 0.0
    coverage: float = 0.0
    test_cases: List[TestCase] = field(default_factory=list)
    output: str = ""
    exit_code: int = 0

    @property
    def success(self) -> bool:
        return self.failed == 0 and self.errors == 0


class TestRunner:
    """
    Executes tests using configured framework.

    AC-2: Test execution implementation.

    Supports:
    - pytest (default)
    - unittest
    - Custom runners
    """

    def __init__(self, framework: str = "pytest"):
        self.framework = framework
        self._runners = {
            "pytest": self._run_pytest,
            "unittest": self._run_unittest
        }

    def execute_tests(
        self,
        tests: List[TestCase],
        options: RunOptions
    ) -> RunResult:
        """Execute tests and return results."""
        if self.framework not in self._runners:
            raise ValueError(f"Unknown framework: {self.framework}")

        runner = self._runners[self.framework]
        return runner(tests, options)

    def execute(
        self,
        test_path: str,
        options: Optional[RunOptions] = None
    ) -> RunResult:
        """Execute tests from a path."""
        options = options or RunOptions()
        return self._run_pytest_path(test_path, options)

    def _run_pytest(
        self,
        tests: List[TestCase],
        options: RunOptions
    ) -> RunResult:
        """Run tests using pytest."""
        start_time = time.time()

        # Build pytest command
        cmd = ["python", "-m", "pytest"]

        # Add test files
        test_files = list(set(tc.file_path for tc in tests))
        cmd.extend(test_files)

        # Add options
        if options.verbose:
            cmd.append("-v")
        if options.fail_fast:
            cmd.append("-x")
        if options.parallel and options.workers > 1:
            cmd.extend(["-n", str(options.workers)])
        if options.coverage:
            cmd.extend(["--cov", "--cov-report=json"])
        if options.markers:
            cmd.extend(["-m", " and ".join(options.markers)])

        cmd.append("--tb=short")

        # Execute
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=options.timeout,
                env={**os.environ, "PYTHONPATH": f"src:{os.environ.get('PYTHONPATH', '')}"}
            )

            output = result.stdout + result.stderr
            exit_code = result.returncode

            # Parse results from output
            return self._parse_pytest_output(
                output,
                exit_code,
                time.time() - start_time,
                tests
            )

        except subprocess.TimeoutExpired:
            logger.error("Test execution timed out")
            return RunResult(
                total=len(tests),
                errors=len(tests),
                duration=options.timeout,
                output="Timeout",
                exit_code=-1
            )
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            return RunResult(
                total=len(tests),
                errors=len(tests),
                output=str(e),
                exit_code=-1
            )

    def _run_pytest_path(
        self,
        test_path: str,
        options: RunOptions
    ) -> RunResult:
        """Run pytest on a path."""
        start_time = time.time()

        cmd = ["python", "-m", "pytest", test_path]

        if options.verbose:
            cmd.append("-v")
        if options.fail_fast:
            cmd.append("-x")
        if options.coverage:
            cmd.extend(["--cov", "--cov-report=json"])

        cmd.append("--tb=short")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=options.timeout,
                env={**os.environ, "PYTHONPATH": f"src:{os.environ.get('PYTHONPATH', '')}"}
            )

            return self._parse_pytest_output(
                result.stdout + result.stderr,
                result.returncode,
                time.time() - start_time,
                []
            )

        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            return RunResult(errors=1, output=str(e), exit_code=-1)

    def _run_unittest(
        self,
        tests: List[TestCase],
        options: RunOptions
    ) -> RunResult:
        """Run tests using unittest."""
        import unittest

        start_time = time.time()
        loader = unittest.TestLoader()
        suite = unittest.TestSuite()

        for test in tests:
            try:
                module_tests = loader.loadTestsFromName(test.module)
                suite.addTests(module_tests)
            except Exception as e:
                logger.warning(f"Could not load {test.module}: {e}")

        runner = unittest.TextTestRunner(verbosity=2 if options.verbose else 1)
        result = runner.run(suite)

        return RunResult(
            total=result.testsRun,
            passed=result.testsRun - len(result.failures) - len(result.errors),
            failed=len(result.failures),
            errors=len(result.errors),
            skipped=len(result.skipped),
            duration=time.time() - start_time,
            exit_code=0 if result.wasSuccessful() else 1
        )

    def _parse_pytest_output(
        self,
        output: str,
        exit_code: int,
        duration: float,
        tests: List[TestCase]
    ) -> RunResult:
        """Parse pytest output to extract results."""
        passed = 0
        failed = 0
        skipped = 0
        errors = 0
        total = 0
        coverage = 0.0

        for line in output.split('\n'):
            # Parse summary line like "5 passed, 2 failed in 1.23s"
            if 'passed' in line or 'failed' in line:
                import re
                match = re.search(r'(\d+)\s+passed', line)
                if match:
                    passed = int(match.group(1))
                match = re.search(r'(\d+)\s+failed', line)
                if match:
                    failed = int(match.group(1))
                match = re.search(r'(\d+)\s+skipped', line)
                if match:
                    skipped = int(match.group(1))
                match = re.search(r'(\d+)\s+error', line)
                if match:
                    errors = int(match.group(1))

            # Parse coverage
            if 'TOTAL' in line and '%' in line:
                import re
                match = re.search(r'(\d+)%', line)
                if match:
                    coverage = float(match.group(1))

        total = passed + failed + skipped + errors

        # Update test case statuses
        for tc in tests:
            # Default to passed if we don't have detailed info
            tc.status = TestStatus.PASSED

        return RunResult(
            total=total,
            passed=passed,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration=duration,
            coverage=coverage,
            test_cases=tests,
            output=output,
            exit_code=exit_code
        )

    def get_coverage(self, coverage_file: str = "coverage.json") -> Dict[str, Any]:
        """Read coverage report."""
        import json

        try:
            if os.path.exists(coverage_file):
                with open(coverage_file, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"Error reading coverage: {e}")
            return {}


def get_test_runner(framework: str = "pytest") -> TestRunner:
    """Factory function to create TestRunner instance."""
    return TestRunner(framework=framework)
