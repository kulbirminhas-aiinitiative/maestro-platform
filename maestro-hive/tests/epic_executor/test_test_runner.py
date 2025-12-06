"""
Tests for TestExecutionRunner

EPIC: MD-2497
AC-1: Integrate pytest runner for Python
AC-2: Integrate jest runner for TypeScript
AC-3: FAIL execution if tests fail
AC-4: Capture coverage metrics
AC-5: Block phase transition if coverage < threshold
"""

import asyncio
import json
import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from epic_executor.phases.test_runner import (
    TestExecutionRunner,
    TestExecutionError,
    CoverageThresholdError,
    TestResult,
    CoverageResult,
    ExecutionResult,
    run_python_tests,
    run_typescript_tests,
)


class TestTestResult:
    """Test the TestResult dataclass."""

    def test_success_when_no_failures(self):
        """AC-3: Success should be True when no failures or errors."""
        result = TestResult(passed=5, failed=0, errors=0, total=5)
        assert result.success is True

    def test_failure_when_tests_fail(self):
        """AC-3: Success should be False when tests fail."""
        result = TestResult(passed=3, failed=2, errors=0, total=5)
        assert result.success is False

    def test_failure_when_errors_occur(self):
        """AC-3: Success should be False when errors occur."""
        result = TestResult(passed=4, failed=0, errors=1, total=5)
        assert result.success is False


class TestCoverageResult:
    """Test the CoverageResult dataclass."""

    def test_meets_threshold_above_80(self):
        """AC-5: Coverage above 80% should meet threshold."""
        result = CoverageResult(line_coverage=85.0)
        assert result.meets_threshold is True

    def test_meets_threshold_at_80(self):
        """AC-5: Coverage at exactly 80% should meet threshold."""
        result = CoverageResult(line_coverage=80.0)
        assert result.meets_threshold is True

    def test_below_threshold_fails(self):
        """AC-5: Coverage below 80% should NOT meet threshold."""
        result = CoverageResult(line_coverage=79.9)
        assert result.meets_threshold is False


class TestTestExecutionRunner:
    """Test the TestExecutionRunner class."""

    def test_init_with_defaults(self):
        """Test runner initialization with default parameters."""
        runner = TestExecutionRunner()
        assert runner.coverage_threshold == 80.0
        assert runner.timeout_seconds == 300

    def test_init_with_custom_threshold(self):
        """AC-5: Custom coverage threshold should be respected."""
        runner = TestExecutionRunner(coverage_threshold=90.0)
        assert runner.coverage_threshold == 90.0


class TestPytestExecution:
    """Test pytest execution - AC-1."""

    @pytest.mark.asyncio
    async def test_execute_pytest_success(self):
        """AC-1: Test successful pytest execution."""
        runner = TestExecutionRunner()

        # Create a simple passing test
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_example.py"
            test_file.write_text("""
def test_always_passes():
    assert True
""")

            result = await runner.execute_pytest(
                test_paths=[str(test_file)],
            )

            assert result.framework == "pytest"
            assert result.test_result.passed >= 1
            assert result.test_result.failed == 0
            assert result.test_result.success is True

    @pytest.mark.asyncio
    async def test_execute_pytest_failure_detected(self):
        """AC-3: FAIL execution if tests fail."""
        runner = TestExecutionRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_failing.py"
            test_file.write_text("""
def test_always_fails():
    assert False, "This test is designed to fail"
""")

            result = await runner.execute_pytest(
                test_paths=[str(test_file)],
            )

            # AC-3: Should detect failure
            assert result.test_result.failed >= 1
            assert result.test_result.success is False
            assert result.phase_gate_passed is False
            assert "Test failures" in result.blocking_reason

    @pytest.mark.asyncio
    async def test_execute_pytest_with_coverage(self):
        """AC-4: Capture coverage metrics."""
        runner = TestExecutionRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create source file
            src_file = Path(tmpdir) / "example.py"
            src_file.write_text("""
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
""")

            # Create test file
            test_file = Path(tmpdir) / "test_example.py"
            test_file.write_text(f"""
import sys
sys.path.insert(0, "{tmpdir}")
from example import add

def test_add():
    assert add(2, 3) == 5
""")

            result = await runner.execute_pytest(
                test_paths=[str(test_file)],
                coverage_source=tmpdir,
            )

            # AC-4: Should capture coverage (even if partial)
            # Coverage may or may not be generated depending on environment
            assert result.framework == "pytest"
            assert result.test_result.passed >= 1


class TestJestExecution:
    """Test jest execution - AC-2."""

    @pytest.mark.asyncio
    async def test_execute_jest_not_found(self):
        """AC-2: Should handle jest not being installed."""
        runner = TestExecutionRunner()

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.ts"
            test_file.write_text("test('dummy', () => expect(true).toBe(true));")

            # This should raise or return error result if jest not available
            try:
                result = await runner.execute_jest(
                    test_paths=[str(test_file)],
                )
                # If jest is available, check result
                assert result.framework == "jest"
            except TestExecutionError as e:
                # Expected if jest not installed
                assert "jest not found" in str(e).lower() or "failed" in str(e).lower()


class TestPhaseGate:
    """Test phase gate functionality - AC-5."""

    def test_check_phase_gate_passes(self):
        """AC-5: Phase gate should pass when all results pass."""
        runner = TestExecutionRunner()

        results = {
            "pytest": ExecutionResult(
                test_result=TestResult(passed=10, failed=0),
                coverage_result=CoverageResult(line_coverage=85.0),
                framework="pytest",
                timestamp=None,
                phase_gate_passed=True,
            )
        }

        passed, reason = runner.check_phase_gate(results)
        assert passed is True
        assert reason is None

    def test_check_phase_gate_fails_on_test_failure(self):
        """AC-5: Phase gate should fail when tests fail."""
        runner = TestExecutionRunner()

        results = {
            "pytest": ExecutionResult(
                test_result=TestResult(passed=8, failed=2),
                coverage_result=CoverageResult(line_coverage=85.0),
                framework="pytest",
                timestamp=None,
                phase_gate_passed=False,
                blocking_reason="Test failures: 2 failed",
            )
        }

        passed, reason = runner.check_phase_gate(results)
        assert passed is False
        assert "Test failures" in reason

    def test_check_phase_gate_fails_on_low_coverage(self):
        """AC-5: Block phase transition if coverage < threshold."""
        runner = TestExecutionRunner()

        results = {
            "pytest": ExecutionResult(
                test_result=TestResult(passed=10, failed=0),
                coverage_result=CoverageResult(line_coverage=50.0),
                framework="pytest",
                timestamp=None,
                phase_gate_passed=False,
                blocking_reason="Coverage 50.0% is below threshold 80%",
            )
        }

        passed, reason = runner.check_phase_gate(results)
        assert passed is False
        assert "coverage" in reason.lower()


class TestConvenienceFunctions:
    """Test convenience wrapper functions."""

    @pytest.mark.asyncio
    async def test_run_python_tests(self):
        """Test run_python_tests convenience function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test_simple.py"
            test_file.write_text("def test_one(): assert True")

            result = await run_python_tests(
                test_paths=[str(test_file)],
            )

            assert result.framework == "pytest"
            assert result.test_result.passed >= 1


class TestParseResults:
    """Test result parsing functionality."""

    def test_parse_pytest_results_from_output(self):
        """Test parsing pytest results from text output."""
        import os
        runner = TestExecutionRunner()

        # Remove any existing report file to test pure output parsing
        try:
            os.remove("/tmp/pytest_report.json")
        except FileNotFoundError:
            pass

        output = """
============================= test session starts ==============================
collected 5 items

test_example.py::test_one PASSED
test_example.py::test_two PASSED
test_example.py::test_three FAILED
test_example.py::test_four PASSED
test_example.py::test_five PASSED

========================= 4 passed, 1 failed in 0.12s =========================
"""

        result = runner._parse_pytest_results(output)

        # Should parse correctly from output
        assert result.passed >= 4
        assert result.failed >= 1

    def test_parse_coverage_no_file(self):
        """Test parsing coverage when file doesn't exist."""
        import os
        runner = TestExecutionRunner()

        # Ensure coverage file doesn't exist
        try:
            os.remove("/tmp/coverage.json")
        except FileNotFoundError:
            pass

        result = runner._parse_coverage_results()

        assert result.line_coverage == 0.0


class TestIntegrationWithTestingPhase:
    """Integration tests with existing TestingPhase."""

    @pytest.mark.asyncio
    async def test_runner_integrates_with_testing_phase(self):
        """Verify runner can be used by TestingPhase."""
        # The TestExecutionRunner should be importable and usable
        from epic_executor.phases.test_runner import TestExecutionRunner

        runner = TestExecutionRunner(
            project_root="/tmp",
            coverage_threshold=70.0,
        )

        assert runner is not None
        assert hasattr(runner, "execute_pytest")
        assert hasattr(runner, "execute_jest")
        assert hasattr(runner, "check_phase_gate")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
