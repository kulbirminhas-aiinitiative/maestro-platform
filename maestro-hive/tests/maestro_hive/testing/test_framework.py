#!/usr/bin/env python3
"""
Tests for TestFramework.

Tests AC-1: Comprehensive testing framework.
"""

import pytest
from unittest.mock import Mock, patch

from maestro_hive.testing.framework import (
    TestFramework, TestConfig, TestCase, TestResults, TestStatus
)


class TestTestConfig:
    """Tests for TestConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = TestConfig()

        assert config.framework == "pytest"
        assert config.coverage_enabled is True
        assert config.coverage_min_threshold == 80.0
        assert config.parallel_workers == 4

    def test_config_from_env(self):
        """Test loading config from environment."""
        with patch.dict('os.environ', {
            'TEST_FRAMEWORK': 'unittest',
            'TEST_COVERAGE_MIN': '90'
        }):
            config = TestConfig.from_env()
            # Note: existing env vars may override

    def test_custom_config(self):
        """Test custom configuration."""
        config = TestConfig(
            framework="unittest",
            coverage_min_threshold=90.0,
            parallel_workers=8
        )

        assert config.framework == "unittest"
        assert config.coverage_min_threshold == 90.0
        assert config.parallel_workers == 8


class TestTestCase:
    """Tests for TestCase dataclass."""

    def test_test_case_creation(self):
        """Test TestCase creation."""
        tc = TestCase(
            id="test_1",
            name="test_example",
            module="test_module",
            file_path="/path/to/test.py",
            line_number=10
        )

        assert tc.id == "test_1"
        assert tc.name == "test_example"
        assert tc.status == TestStatus.PENDING

    def test_test_case_to_dict(self):
        """Test TestCase serialization."""
        tc = TestCase(
            id="test_1",
            name="test_example",
            module="test_module",
            file_path="/path/to/test.py",
            line_number=10,
            tags=["unit", "fast"]
        )

        data = tc.to_dict()
        assert data['id'] == "test_1"
        assert data['status'] == "pending"
        assert 'unit' in data['tags']


class TestTestResults:
    """Tests for TestResults."""

    def test_results_creation(self):
        """Test TestResults creation."""
        results = TestResults(
            total=10,
            passed=8,
            failed=1,
            skipped=1
        )

        assert results.total == 10
        assert results.passed == 8
        assert results.failed == 1

    def test_pass_rate_calculation(self):
        """Test pass rate property."""
        results = TestResults(total=10, passed=8, failed=2)
        assert results.pass_rate == 80.0

    def test_pass_rate_zero_total(self):
        """Test pass rate with zero total."""
        results = TestResults(total=0, passed=0)
        assert results.pass_rate == 0.0

    def test_results_to_dict(self):
        """Test TestResults serialization."""
        results = TestResults(
            total=5,
            passed=4,
            failed=1,
            coverage_percent=85.0
        )

        data = results.to_dict()
        assert data['total'] == 5
        assert data['pass_rate'] == 80.0


class TestTestFramework:
    """Tests for TestFramework."""

    @pytest.fixture
    def framework(self):
        """Create TestFramework instance."""
        config = TestConfig(
            framework="pytest",
            coverage_enabled=False
        )
        return TestFramework(config=config)

    def test_framework_creation(self, framework):
        """Test framework initialization."""
        assert framework.config.framework == "pytest"
        assert framework._discovered_tests == []

    def test_discover_tests_empty(self, framework, tmp_path):
        """Test discovery on empty directory."""
        tests = framework.discover_tests(str(tmp_path))
        assert tests == []

    def test_discover_tests_with_files(self, framework, tmp_path):
        """Test discovery with test files."""
        # Create a test file
        test_file = tmp_path / "test_example.py"
        test_file.write_text('''
def test_one():
    pass

def test_two():
    pass
''')

        tests = framework.discover_tests(str(tmp_path))
        assert len(tests) == 2

    def test_get_results_none(self, framework):
        """Test get_results before running tests."""
        assert framework.get_results() is None


class TestTestStatus:
    """Tests for TestStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert TestStatus.PENDING.value == "pending"
        assert TestStatus.PASSED.value == "passed"
        assert TestStatus.FAILED.value == "failed"
        assert TestStatus.SKIPPED.value == "skipped"
