#!/usr/bin/env python3
"""
Test Framework: Core testing framework for Maestro Hive.

Implements AC-1: Comprehensive testing framework for maestro-hive modules.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class TestStatus(Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestConfig:
    """Test framework configuration."""
    framework: str = "pytest"
    coverage_enabled: bool = True
    coverage_min_threshold: float = 80.0
    parallel_workers: int = 4
    timeout_seconds: int = 300
    fail_fast: bool = False
    verbose: bool = True
    report_format: str = "json"
    quality_fabric_url: str = "http://localhost:8000"

    @classmethod
    def from_env(cls) -> 'TestConfig':
        """Load configuration from environment variables."""
        return cls(
            framework=os.getenv('TEST_FRAMEWORK', 'pytest'),
            coverage_enabled=os.getenv('TEST_COVERAGE_ENABLED', 'true').lower() == 'true',
            coverage_min_threshold=float(os.getenv('TEST_COVERAGE_MIN', '80')),
            parallel_workers=int(os.getenv('TEST_PARALLEL_WORKERS', '4')),
            timeout_seconds=int(os.getenv('TEST_TIMEOUT', '300')),
            fail_fast=os.getenv('TEST_FAIL_FAST', 'false').lower() == 'true',
            verbose=os.getenv('TEST_VERBOSE', 'true').lower() == 'true',
            report_format=os.getenv('TEST_REPORT_FORMAT', 'json'),
            quality_fabric_url=os.getenv('QUALITY_FABRIC_URL', 'http://localhost:8000')
        )


@dataclass
class TestCase:
    """Individual test case representation."""
    id: str
    name: str
    module: str
    file_path: str
    line_number: int
    description: str = ""
    tags: List[str] = field(default_factory=list)
    status: TestStatus = TestStatus.PENDING
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    stack_trace: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'module': self.module,
            'file_path': self.file_path,
            'line_number': self.line_number,
            'description': self.description,
            'tags': self.tags,
            'status': self.status.value,
            'duration_seconds': self.duration_seconds,
            'error_message': self.error_message,
            'stack_trace': self.stack_trace
        }


@dataclass
class TestResults:
    """Aggregated test results."""
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration_seconds: float = 0.0
    coverage_percent: float = 0.0
    test_cases: List[TestCase] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate percentage."""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total': self.total,
            'passed': self.passed,
            'failed': self.failed,
            'skipped': self.skipped,
            'errors': self.errors,
            'duration_seconds': self.duration_seconds,
            'coverage_percent': self.coverage_percent,
            'pass_rate': self.pass_rate,
            'test_cases': [tc.to_dict() for tc in self.test_cases],
            'timestamp': self.timestamp
        }


class TestFramework:
    """
    Core testing framework for Maestro Hive.

    AC-1: Comprehensive testing framework implementation.

    Provides:
    - Test discovery across modules
    - Pluggable test runners (pytest, unittest)
    - Coverage integration
    - Quality Fabric validation
    """

    def __init__(self, config: Optional[TestConfig] = None):
        self.config = config or TestConfig.from_env()
        self._discovered_tests: List[TestCase] = []
        self._results: Optional[TestResults] = None

    def discover_tests(self, path: str) -> List[TestCase]:
        """
        Discover tests in the given path.

        AC-2: Test discovery implementation.
        """
        from .discovery import TestDiscovery

        discovery = TestDiscovery()
        self._discovered_tests = discovery.discover_tests(path)
        logger.info(f"Discovered {len(self._discovered_tests)} tests in {path}")
        return self._discovered_tests

    def run_tests(
        self,
        tests: Optional[List[TestCase]] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> TestResults:
        """
        Run tests and collect results.

        AC-1: Test execution through framework.
        """
        from .runner import TestRunner, RunOptions

        tests = tests or self._discovered_tests
        run_options = RunOptions(
            parallel=self.config.parallel_workers > 1,
            workers=self.config.parallel_workers,
            timeout=self.config.timeout_seconds,
            fail_fast=self.config.fail_fast,
            verbose=self.config.verbose,
            coverage=self.config.coverage_enabled,
            **(options or {})
        )

        runner = TestRunner(framework=self.config.framework)
        result = runner.execute_tests(tests, run_options)

        self._results = TestResults(
            total=result.total,
            passed=result.passed,
            failed=result.failed,
            skipped=result.skipped,
            errors=result.errors,
            duration_seconds=result.duration,
            coverage_percent=result.coverage,
            test_cases=result.test_cases
        )

        logger.info(f"Test run complete: {self._results.passed}/{self._results.total} passed")
        return self._results

    def generate_report(
        self,
        results: Optional[TestResults] = None,
        format: str = "json"
    ) -> 'TestReport':
        """
        Generate test report.

        AC-6: Test reporting implementation.
        """
        from .reporter import TestReporter, ReportFormat

        results = results or self._results
        if not results:
            raise ValueError("No test results available. Run tests first.")

        reporter = TestReporter()
        report_format = ReportFormat(format)
        return reporter.generate(results, report_format)

    def validate_with_quality_fabric(
        self,
        results: Optional[TestResults] = None
    ) -> Dict[str, Any]:
        """
        Validate results with Quality Fabric.

        AC-5: Quality Fabric integration.
        """
        import requests

        results = results or self._results
        if not results:
            raise ValueError("No test results available")

        try:
            response = requests.post(
                f"{self.config.quality_fabric_url}/api/v1/sdlc/validate-persona",
                json={
                    "persona_id": "test_framework",
                    "persona_type": "qa_engineer",
                    "artifacts": {
                        "test_results": results.to_dict()
                    },
                    "project_context": {
                        "coverage": results.coverage_percent,
                        "pass_rate": results.pass_rate
                    }
                },
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Quality Fabric validation failed: {response.status_code}")
                return {"status": "unavailable", "error": response.text}

        except Exception as e:
            logger.error(f"Quality Fabric connection failed: {e}")
            return {"status": "error", "error": str(e)}

    def get_results(self) -> Optional[TestResults]:
        """Get the last test results."""
        return self._results


def get_test_framework(**kwargs) -> TestFramework:
    """Factory function to create TestFramework instance."""
    config = TestConfig(**kwargs) if kwargs else None
    return TestFramework(config=config)
