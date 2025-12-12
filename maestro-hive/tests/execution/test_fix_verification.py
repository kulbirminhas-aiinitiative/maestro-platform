"""
Tests for FixVerificationLoop - Fix verification and regression testing.

EPIC: MD-3027 - Self-Healing Execution Loop (Phase 3)
Task: MD-3031 - Implement FixVerificationLoop
"""

import pytest
from datetime import datetime

from maestro_hive.execution.fix_verification import (
    FixVerificationLoop,
    VerificationConfig,
    VerificationResult,
    VerificationStatus,
    TestResult,
    TestType,
    get_fix_verifier,
    reset_fix_verifier,
)


class TestVerificationStatus:
    """Tests for VerificationStatus enum."""

    def test_all_statuses_defined(self):
        """Test all expected statuses are defined."""
        statuses = [
            VerificationStatus.PENDING,
            VerificationStatus.RUNNING,
            VerificationStatus.PASSED,
            VerificationStatus.FAILED,
            VerificationStatus.PARTIAL,
            VerificationStatus.SKIPPED,
        ]
        assert len(statuses) == 6


class TestTestType:
    """Tests for TestType enum."""

    def test_all_types_defined(self):
        """Test all expected test types are defined."""
        types = [
            TestType.UNIT,
            TestType.INTEGRATION,
            TestType.REGRESSION,
            TestType.SMOKE,
            TestType.ALL,
        ]
        assert len(types) == 5


class TestVerificationConfig:
    """Tests for VerificationConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = VerificationConfig()
        assert config.test_directory == "tests"
        assert config.test_command == "pytest"
        assert config.test_timeout_seconds == 300
        assert config.run_regression_tests is True
        assert config.min_pass_rate == 95.0

    def test_custom_values(self):
        """Test custom configuration values."""
        config = VerificationConfig(
            test_directory="custom_tests",
            test_timeout_seconds=60,
            fail_fast=True,
        )
        assert config.test_directory == "custom_tests"
        assert config.test_timeout_seconds == 60
        assert config.fail_fast is True


class TestTestResult:
    """Tests for TestResult dataclass."""

    def test_create_result(self):
        """Test creating a test result."""
        result = TestResult(
            test_name="test_example.py",
            test_type=TestType.UNIT,
            status=VerificationStatus.PASSED,
            duration_seconds=1.5,
            assertions_passed=10,
        )
        assert result.test_name == "test_example.py"
        assert result.status == VerificationStatus.PASSED
        assert result.assertions_passed == 10

    def test_to_dict(self):
        """Test serialization to dictionary."""
        result = TestResult(
            test_name="test_example.py",
            test_type=TestType.UNIT,
            status=VerificationStatus.PASSED,
            duration_seconds=1.5,
        )
        data = result.to_dict()
        assert data["test_name"] == "test_example.py"
        assert data["test_type"] == "unit"
        assert data["status"] == "passed"


class TestVerificationResult:
    """Tests for VerificationResult dataclass."""

    def test_create_result(self):
        """Test creating a verification result."""
        result = VerificationResult(
            verification_id="FIX-001",
            fix_description="Fixed timeout handling",
            status=VerificationStatus.PASSED,
        )
        assert result.verification_id == "FIX-001"
        assert result.fix_description == "Fixed timeout handling"

    def test_pass_rate_calculation(self):
        """Test pass rate calculation."""
        result = VerificationResult(
            verification_id="FIX-001",
            fix_description="Test",
            status=VerificationStatus.PASSED,
            total_tests=10,
            passed_tests=8,
            failed_tests=2,
        )
        assert result.pass_rate == 80.0

    def test_pass_rate_zero_tests(self):
        """Test pass rate with no tests."""
        result = VerificationResult(
            verification_id="FIX-001",
            fix_description="Test",
            status=VerificationStatus.PENDING,
        )
        assert result.pass_rate == 0.0

    def test_has_regressions(self):
        """Test regression detection property."""
        result = VerificationResult(
            verification_id="FIX-001",
            fix_description="Test",
            status=VerificationStatus.FAILED,
            regressions_detected=["test_a", "test_b"],
        )
        assert result.has_regressions is True

        result_no_regression = VerificationResult(
            verification_id="FIX-002",
            fix_description="Test",
            status=VerificationStatus.PASSED,
        )
        assert result_no_regression.has_regressions is False

    def test_to_dict(self):
        """Test serialization to dictionary."""
        result = VerificationResult(
            verification_id="FIX-001",
            fix_description="Test fix",
            status=VerificationStatus.PASSED,
            total_tests=5,
            passed_tests=5,
        )
        data = result.to_dict()
        assert data["verification_id"] == "FIX-001"
        assert data["pass_rate"] == 100.0
        assert data["has_regressions"] is False


class TestFixVerificationLoop:
    """Tests for FixVerificationLoop class."""

    @pytest.fixture
    def verifier(self):
        """Create verifier for tests."""
        config = VerificationConfig(
            test_timeout_seconds=30,
            run_regression_tests=False,
            run_smoke_tests=False,
        )
        return FixVerificationLoop(config=config)

    @pytest.mark.asyncio
    async def test_verify_fix_with_custom_runner(self):
        """Test verification with custom test runner."""
        test_results = []

        async def custom_runner(test_path: str) -> bool:
            test_results.append(test_path)
            return True

        verifier = FixVerificationLoop(test_runner=custom_runner)

        result = await verifier.verify_fix(
            fix_id="FIX-001",
            fix_description="Test fix",
            specific_tests=["test_example.py"],
        )

        assert result.status == VerificationStatus.PASSED
        assert len(test_results) >= 1

    @pytest.mark.asyncio
    async def test_verify_fix_failing_tests(self):
        """Test verification with failing tests."""
        async def failing_runner(test_path: str) -> bool:
            return False

        verifier = FixVerificationLoop(test_runner=failing_runner)

        result = await verifier.verify_fix(
            fix_id="FIX-002",
            fix_description="Failing fix",
            specific_tests=["test_fail.py"],
        )

        assert result.status == VerificationStatus.FAILED

    def test_get_verification_history(self, verifier):
        """Test getting verification history."""
        history = verifier.get_verification_history()
        assert isinstance(history, list)

    def test_get_statistics(self, verifier):
        """Test getting verifier statistics."""
        stats = verifier.get_statistics()
        assert "total_verifications" in stats

    def test_clear_baseline(self, verifier):
        """Test clearing baseline results."""
        verifier._baseline_results["test"] = TestResult(
            test_name="test",
            test_type=TestType.UNIT,
            status=VerificationStatus.PASSED,
            duration_seconds=1.0,
        )
        verifier.clear_baseline()
        assert len(verifier._baseline_results) == 0

    def test_clear_history(self, verifier):
        """Test clearing verification history."""
        verifier._verification_history.append(
            VerificationResult(
                verification_id="test",
                fix_description="test",
                status=VerificationStatus.PASSED,
            )
        )
        verifier.clear_history()
        assert len(verifier._verification_history) == 0


class TestRegressionDetection:
    """Tests for regression detection."""

    @pytest.fixture
    def verifier(self):
        """Create verifier with baseline."""
        verifier = FixVerificationLoop()
        # Set baseline - test was passing
        verifier._baseline_results["test_example.py"] = TestResult(
            test_name="test_example.py",
            test_type=TestType.UNIT,
            status=VerificationStatus.PASSED,
            duration_seconds=1.0,
        )
        return verifier

    def test_detect_regression(self, verifier):
        """Test regression is detected."""
        current_results = [
            TestResult(
                test_name="test_example.py",
                test_type=TestType.UNIT,
                status=VerificationStatus.FAILED,  # Now failing
                duration_seconds=1.0,
            )
        ]

        regressions = verifier._detect_regressions(current_results)
        assert len(regressions) == 1
        assert "REGRESSION" in regressions[0]

    def test_no_regression_when_still_passing(self, verifier):
        """Test no regression when test still passes."""
        current_results = [
            TestResult(
                test_name="test_example.py",
                test_type=TestType.UNIT,
                status=VerificationStatus.PASSED,
                duration_seconds=1.0,
            )
        ]

        regressions = verifier._detect_regressions(current_results)
        assert len(regressions) == 0


class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_fix_verifier(self):
        """Test singleton getter."""
        reset_fix_verifier()
        verifier1 = get_fix_verifier()
        verifier2 = get_fix_verifier()
        assert verifier1 is verifier2

    def test_reset_fix_verifier(self):
        """Test singleton reset."""
        verifier1 = get_fix_verifier()
        reset_fix_verifier()
        verifier2 = get_fix_verifier()
        assert verifier1 is not verifier2
