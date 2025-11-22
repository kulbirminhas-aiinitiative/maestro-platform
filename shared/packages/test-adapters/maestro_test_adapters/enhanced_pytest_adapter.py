#!/usr/bin/env python3
"""
Enhanced Pytest Adapter with Production-Ready Result Parsing

This module provides comprehensive pytest integration with:
- Structured JSON report parsing
- JUnit XML parsing
- Coverage integration
- Detailed test analysis
- Artifact management
"""

import asyncio
import json
import time
import logging
import subprocess
import tempfile
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum
import os
import re

from ..core.telemetry import telemetry, trace_decorator, metrics_collector

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Individual test result"""
    test_id: str
    name: str
    status: str  # passed, failed, skipped, error
    duration: float
    file_path: str
    line_number: Optional[int]
    error_message: Optional[str] = None
    failure_type: Optional[str] = None
    stdout: Optional[str] = None
    stderr: Optional[str] = None


@dataclass
class CoverageReport:
    """Test coverage report"""
    total_statements: int
    covered_statements: int
    missing_statements: int
    coverage_percentage: float
    file_coverage: Dict[str, Dict[str, Any]]


@dataclass
class PytestResult:
    """Comprehensive pytest execution result"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    error_tests: int
    duration: float
    coverage: Optional[CoverageReport]
    test_results: List[TestResult]
    artifacts: List[str]
    summary: Dict[str, Any]


class EnhancedPytestAdapter:
    """
    Enhanced Pytest Adapter with Production-Ready Features

    Solves the "limited result parsing" problem with:
    - JSON report parsing
    - JUnit XML parsing
    - Coverage integration
    - Detailed test analysis
    - Comprehensive error reporting
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.pytest_path = None
        self.output_dir = None

    async def initialize(self) -> bool:
        """Initialize enhanced pytest adapter"""
        try:
            # Check if pytest is available
            result = subprocess.run(
                ["pytest", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                self.pytest_path = "pytest"
                # Create output directory for artifacts
                self.output_dir = tempfile.mkdtemp(prefix="pytest_results_")
                logger.info(f"Enhanced pytest adapter initialized: {result.stdout.strip()}")
                return True
            else:
                logger.warning("Pytest not available")
                return False

        except Exception as e:
            logger.warning(f"Pytest initialization failed: {e}")
            return False

    @trace_decorator("pytest_test_execution")
    async def run_tests(self, test_config: Dict[str, Any] = None) -> PytestResult:
        """Run pytest with comprehensive result collection"""
        start_time = time.time()

        with telemetry.trace_operation("pytest_test_execution", {
            "test.framework": "pytest",
            "test.path": test_config.get("test_path", "unknown") if test_config else "unknown",
            "test.config": str(test_config) if test_config else "default"
        }) as span:
            try:
                config = test_config or {}

                # Track test execution metrics
                metrics_collector.increment_counter(
                    "quality_fabric_tests_started_total",
                    attributes={"framework": "pytest"}
                )

                # Prepare pytest command with comprehensive reporting
                pytest_cmd = await self._build_pytest_command(config)

                # Execute pytest
                result = subprocess.run(
                    pytest_cmd,
                    capture_output=True,
                    text=True,
                    timeout=config.get("timeout", 600),
                    cwd=config.get("working_directory", ".")
                )

                # Parse comprehensive results
                pytest_result = await self._parse_comprehensive_results(
                    result.stdout, result.stderr, result.returncode
                )

                pytest_result.duration = time.time() - start_time
                return pytest_result

            except Exception as e:
                logger.error(f"Pytest execution failed: {e}")
                return PytestResult(
                    total_tests=0,
                    passed_tests=0,
                    failed_tests=0,
                    skipped_tests=0,
                    error_tests=1,
                    duration=time.time() - start_time,
                    coverage=None,
                    test_results=[],
                    artifacts=[],
                    summary={"error": str(e)}
                )

    async def _build_pytest_command(self, config: Dict[str, Any]) -> List[str]:
        """Build comprehensive pytest command with all reporting options"""

        cmd = [self.pytest_path]

        # Test discovery options
        test_path = config.get("test_path", "tests/")
        if test_path:
            cmd.append(test_path)

        # Markers and filtering
        markers = config.get("markers", [])
        if markers:
            cmd.extend(["-m", " and ".join(markers)])

        keywords = config.get("keywords")
        if keywords:
            cmd.extend(["-k", keywords])

        # Parallel execution
        if config.get("parallel", False):
            workers = config.get("workers", "auto")
            cmd.extend(["-n", str(workers)])

        # Verbosity
        verbosity = config.get("verbosity", 2)
        cmd.append(f"-{'v' * verbosity}")

        # JSON reporting (pytest-json-report plugin)
        json_report_path = os.path.join(self.output_dir, "pytest_report.json")
        cmd.extend(["--json-report", f"--json-report-file={json_report_path}"])

        # JUnit XML reporting
        junit_path = os.path.join(self.output_dir, "pytest_junit.xml")
        cmd.extend(["--junitxml", junit_path])

        # Coverage reporting
        if config.get("coverage", True):
            coverage_path = os.path.join(self.output_dir, "coverage.json")
            cmd.extend([
                "--cov=.",
                f"--cov-report=json:{coverage_path}",
                "--cov-report=term-missing",
                "--cov-report=html:" + os.path.join(self.output_dir, "htmlcov")
            ])

        # HTML reporting
        html_report_path = os.path.join(self.output_dir, "pytest_report.html")
        cmd.extend(["--html", html_report_path, "--self-contained-html"])

        # Additional options
        if config.get("capture", "no") == "no":
            cmd.append("-s")  # No capture

        if config.get("exitfirst", False):
            cmd.append("-x")  # Exit on first failure

        if config.get("lf", False):
            cmd.append("--lf")  # Last failed

        if config.get("ff", False):
            cmd.append("--ff")  # Failed first

        # Custom options
        custom_args = config.get("custom_args", [])
        if custom_args:
            cmd.extend(custom_args)

        return cmd

    async def _parse_comprehensive_results(self, stdout: str, stderr: str, return_code: int) -> PytestResult:
        """Parse pytest results from multiple sources"""

        # Initialize result structure
        result = PytestResult(
            total_tests=0,
            passed_tests=0,
            failed_tests=0,
            skipped_tests=0,
            error_tests=0,
            duration=0.0,
            coverage=None,
            test_results=[],
            artifacts=[],
            summary={}
        )

        # Try JSON report first (most comprehensive)
        json_report_path = os.path.join(self.output_dir, "pytest_report.json")
        if os.path.exists(json_report_path):
            await self._parse_json_report(json_report_path, result)
        else:
            # Fallback to JUnit XML
            junit_path = os.path.join(self.output_dir, "pytest_junit.xml")
            if os.path.exists(junit_path):
                await self._parse_junit_report(junit_path, result)
            else:
                # Last resort: parse stdout
                await self._parse_stdout_results(stdout, stderr, return_code, result)

        # Parse coverage report
        coverage_path = os.path.join(self.output_dir, "coverage.json")
        if os.path.exists(coverage_path):
            result.coverage = await self._parse_coverage_report(coverage_path)

        # Collect artifacts
        result.artifacts = await self._collect_artifacts()

        # Generate summary
        result.summary = await self._generate_result_summary(result, stdout, stderr)

        return result

    async def _parse_json_report(self, json_path: str, result: PytestResult):
        """Parse pytest JSON report (pytest-json-report plugin)"""
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)

            # Extract summary statistics
            summary = data.get("summary", {})
            result.total_tests = summary.get("total", 0)
            result.passed_tests = summary.get("passed", 0)
            result.failed_tests = summary.get("failed", 0)
            result.skipped_tests = summary.get("skipped", 0)
            result.error_tests = summary.get("error", 0)
            result.duration = data.get("duration", 0.0)

            # Parse individual tests
            tests = data.get("tests", [])
            for test_data in tests:
                test_result = TestResult(
                    test_id=test_data.get("nodeid", "unknown"),
                    name=test_data.get("name", "unknown"),
                    status=test_data.get("outcome", "unknown"),
                    duration=test_data.get("duration", 0.0),
                    file_path=test_data.get("file", "unknown"),
                    line_number=test_data.get("line"),
                    error_message=self._extract_error_message(test_data),
                    failure_type=self._extract_failure_type(test_data),
                    stdout=test_data.get("stdout"),
                    stderr=test_data.get("stderr")
                )
                result.test_results.append(test_result)

        except Exception as e:
            logger.warning(f"Failed to parse JSON report: {e}")

    async def _parse_junit_report(self, junit_path: str, result: PytestResult):
        """Parse JUnit XML report"""
        try:
            tree = ET.parse(junit_path)
            root = tree.getroot()

            # Extract summary from testsuite element
            result.total_tests = int(root.get("tests", 0))
            result.failed_tests = int(root.get("failures", 0))
            result.error_tests = int(root.get("errors", 0))
            result.skipped_tests = int(root.get("skipped", 0))
            result.passed_tests = result.total_tests - result.failed_tests - result.error_tests - result.skipped_tests
            result.duration = float(root.get("time", 0.0))

            # Parse individual test cases
            for testcase in root.findall(".//testcase"):
                name = testcase.get("name", "unknown")
                classname = testcase.get("classname", "unknown")
                duration = float(testcase.get("time", 0.0))

                # Determine status and extract error information
                status = "passed"
                error_message = None
                failure_type = None

                failure = testcase.find("failure")
                if failure is not None:
                    status = "failed"
                    error_message = failure.get("message")
                    failure_type = failure.get("type")

                error = testcase.find("error")
                if error is not None:
                    status = "error"
                    error_message = error.get("message")
                    failure_type = error.get("type")

                skipped = testcase.find("skipped")
                if skipped is not None:
                    status = "skipped"
                    error_message = skipped.get("message")

                test_result = TestResult(
                    test_id=f"{classname}::{name}",
                    name=name,
                    status=status,
                    duration=duration,
                    file_path=classname.replace(".", "/") + ".py",
                    line_number=None,
                    error_message=error_message,
                    failure_type=failure_type,
                    stdout=None,
                    stderr=None
                )
                result.test_results.append(test_result)

        except Exception as e:
            logger.warning(f"Failed to parse JUnit report: {e}")

    async def _parse_stdout_results(self, stdout: str, stderr: str, return_code: int, result: PytestResult):
        """Parse pytest results from stdout (fallback method)"""
        try:
            lines = stdout.split('\n')

            # Look for summary line
            summary_patterns = [
                r'=+ (\d+) failed,? (\d+) passed,? (\d+) skipped,? (\d+) error.* =+',
                r'=+ (\d+) passed,? (\d+) skipped,? (\d+) failed.* =+',
                r'=+ (\d+) passed.* =+',
                r'=+ (\d+) failed.* =+',
                r'=+ (\d+) error.* =+'
            ]

            for line in lines:
                for pattern in summary_patterns:
                    match = re.search(pattern, line)
                    if match:
                        # Extract numbers based on pattern
                        numbers = [int(x) for x in match.groups()]

                        # Simple parsing logic
                        if "passed" in line:
                            result.passed_tests = numbers[0] if numbers else 0
                        if "failed" in line:
                            result.failed_tests = numbers[0] if "failed" in line.split()[1] else 0
                        if "skipped" in line:
                            result.skipped_tests = numbers[1] if len(numbers) > 1 else 0
                        if "error" in line:
                            result.error_tests = numbers[-1] if numbers else 0

            result.total_tests = result.passed_tests + result.failed_tests + result.skipped_tests + result.error_tests

            # Extract duration
            duration_match = re.search(r'in ([\d.]+)s', stdout)
            if duration_match:
                result.duration = float(duration_match.group(1))

            # Parse individual test results from output
            await self._parse_individual_tests_from_stdout(stdout, result)

        except Exception as e:
            logger.warning(f"Failed to parse stdout results: {e}")

    async def _parse_individual_tests_from_stdout(self, stdout: str, result: PytestResult):
        """Parse individual test results from stdout"""
        lines = stdout.split('\n')

        current_test = None
        collecting_output = False

        for line in lines:
            line = line.strip()

            # Test start patterns
            if '::' in line and any(status in line for status in ['PASSED', 'FAILED', 'SKIPPED', 'ERROR']):
                if '::' in line:
                    parts = line.split()
                    test_path = parts[0]
                    status_part = parts[-1] if parts else ""

                    # Extract status
                    status = "unknown"
                    if "PASSED" in status_part:
                        status = "passed"
                    elif "FAILED" in status_part:
                        status = "failed"
                    elif "SKIPPED" in status_part:
                        status = "skipped"
                    elif "ERROR" in status_part:
                        status = "error"

                    # Extract duration if present
                    duration = 0.0
                    duration_match = re.search(r'\[([\d.]+)s\]', line)
                    if duration_match:
                        duration = float(duration_match.group(1))

                    test_result = TestResult(
                        test_id=test_path,
                        name=test_path.split("::")[-1] if "::" in test_path else test_path,
                        status=status,
                        duration=duration,
                        file_path=test_path.split("::")[0] if "::" in test_path else "unknown",
                        line_number=None,
                        error_message=None,
                        failure_type=None,
                        stdout=None,
                        stderr=None
                    )
                    result.test_results.append(test_result)

    async def _parse_coverage_report(self, coverage_path: str) -> Optional[CoverageReport]:
        """Parse coverage report from JSON"""
        try:
            with open(coverage_path, 'r') as f:
                data = json.load(f)

            totals = data.get("totals", {})
            files = data.get("files", {})

            coverage_report = CoverageReport(
                total_statements=totals.get("num_statements", 0),
                covered_statements=totals.get("covered_lines", 0),
                missing_statements=totals.get("missing_lines", 0),
                coverage_percentage=totals.get("percent_covered", 0.0),
                file_coverage={}
            )

            # Parse per-file coverage
            for file_path, file_data in files.items():
                coverage_report.file_coverage[file_path] = {
                    "statements": file_data.get("summary", {}).get("num_statements", 0),
                    "covered": file_data.get("summary", {}).get("covered_lines", 0),
                    "missing": file_data.get("summary", {}).get("missing_lines", 0),
                    "percentage": file_data.get("summary", {}).get("percent_covered", 0.0),
                    "missing_lines": file_data.get("missing_lines", [])
                }

            return coverage_report

        except Exception as e:
            logger.warning(f"Failed to parse coverage report: {e}")
            return None

    async def _collect_artifacts(self) -> List[str]:
        """Collect all generated artifacts"""
        artifacts = []

        if not self.output_dir or not os.path.exists(self.output_dir):
            return artifacts

        # Common artifact files
        artifact_patterns = [
            "pytest_report.json",
            "pytest_report.html",
            "pytest_junit.xml",
            "coverage.json",
            "htmlcov/index.html"
        ]

        for pattern in artifact_patterns:
            artifact_path = os.path.join(self.output_dir, pattern)
            if os.path.exists(artifact_path):
                artifacts.append(artifact_path)

        # Find any additional HTML/JSON files
        for root, dirs, files in os.walk(self.output_dir):
            for file in files:
                if file.endswith(('.html', '.json', '.xml')) and file not in [os.path.basename(a) for a in artifacts]:
                    artifacts.append(os.path.join(root, file))

        return artifacts

    async def _generate_result_summary(self, result: PytestResult, stdout: str, stderr: str) -> Dict[str, Any]:
        """Generate comprehensive result summary"""

        summary = {
            "execution_summary": {
                "total_tests": result.total_tests,
                "passed": result.passed_tests,
                "failed": result.failed_tests,
                "skipped": result.skipped_tests,
                "errors": result.error_tests,
                "success_rate": result.passed_tests / max(1, result.total_tests),
                "duration": result.duration
            },
            "test_analysis": {
                "fastest_test": None,
                "slowest_test": None,
                "avg_test_duration": 0.0,
                "failed_tests": [],
                "error_tests": []
            },
            "coverage_summary": None,
            "recommendations": []
        }

        # Analyze test performance
        if result.test_results:
            durations = [t.duration for t in result.test_results if t.duration > 0]
            if durations:
                summary["test_analysis"]["avg_test_duration"] = sum(durations) / len(durations)

                # Find fastest and slowest tests
                fastest = min(result.test_results, key=lambda x: x.duration)
                slowest = max(result.test_results, key=lambda x: x.duration)

                summary["test_analysis"]["fastest_test"] = {
                    "name": fastest.name,
                    "duration": fastest.duration
                }
                summary["test_analysis"]["slowest_test"] = {
                    "name": slowest.name,
                    "duration": slowest.duration
                }

            # Collect failed and error tests
            summary["test_analysis"]["failed_tests"] = [
                {
                    "name": t.name,
                    "error": t.error_message,
                    "type": t.failure_type
                }
                for t in result.test_results if t.status == "failed"
            ]

            summary["test_analysis"]["error_tests"] = [
                {
                    "name": t.name,
                    "error": t.error_message,
                    "type": t.failure_type
                }
                for t in result.test_results if t.status == "error"
            ]

        # Coverage summary
        if result.coverage:
            summary["coverage_summary"] = {
                "total_coverage": result.coverage.coverage_percentage,
                "statements_covered": result.coverage.covered_statements,
                "statements_total": result.coverage.total_statements,
                "files_with_low_coverage": [
                    {"file": file_path, "coverage": file_data["percentage"]}
                    for file_path, file_data in result.coverage.file_coverage.items()
                    if file_data["percentage"] < 80
                ]
            }

        # Generate recommendations
        summary["recommendations"] = await self._generate_recommendations(result)

        return summary

    async def _generate_recommendations(self, result: PytestResult) -> List[str]:
        """Generate actionable recommendations based on test results"""
        recommendations = []

        # Coverage recommendations
        if result.coverage:
            if result.coverage.coverage_percentage < 80:
                recommendations.append(f"Improve test coverage from {result.coverage.coverage_percentage:.1f}% to at least 80%")

            low_coverage_files = [
                file_path for file_path, file_data in result.coverage.file_coverage.items()
                if file_data["percentage"] < 60
            ]
            if low_coverage_files:
                recommendations.append(f"Focus on testing {len(low_coverage_files)} files with coverage below 60%")

        # Performance recommendations
        if result.test_results:
            slow_tests = [t for t in result.test_results if t.duration > 5.0]
            if slow_tests:
                recommendations.append(f"Optimize {len(slow_tests)} slow tests (>5s duration)")

        # Failure analysis
        if result.failed_tests > 0:
            recommendations.append(f"Fix {result.failed_tests} failing tests before proceeding")

        if result.error_tests > 0:
            recommendations.append(f"Resolve {result.error_tests} test errors")

        # Skipped tests
        if result.skipped_tests > result.total_tests * 0.1:
            recommendations.append("Review and potentially re-enable skipped tests")

        return recommendations

    def _extract_error_message(self, test_data: Dict[str, Any]) -> Optional[str]:
        """Extract error message from test data"""

        call = test_data.get("call", {})
        if call and "longrepr" in call:
            return call["longrepr"]

        # Check setup/teardown for errors
        for phase in ["setup", "teardown"]:
            phase_data = test_data.get(phase, {})
            if phase_data and "longrepr" in phase_data:
                return phase_data["longrepr"]

        return None

    def _extract_failure_type(self, test_data: Dict[str, Any]) -> Optional[str]:
        """Extract failure type from test data"""

        call = test_data.get("call", {})
        if call and "crash" in call:
            crash = call["crash"]
            return crash.get("typename") or crash.get("path")

        return None

    async def cleanup(self) -> bool:
        """Cleanup adapter resources"""
        if self.output_dir and os.path.exists(self.output_dir):
            try:
                import shutil
                shutil.rmtree(self.output_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup output directory: {e}")

        return True


# Example usage
async def main():
    """Demonstrate enhanced pytest adapter"""

    adapter = EnhancedPytestAdapter()

    if await adapter.initialize():
        print("✅ Enhanced Pytest Adapter initialized")

        # Example test configuration
        config = {
            "test_path": "tests/",
            "coverage": True,
            "parallel": True,
            "workers": 4,
            "markers": ["unit", "fast"],
            "verbosity": 2,
            "html_report": True
        }

        result = await adapter.run_tests(config)

        print(f"📊 Test Results:")
        print(f"   Total: {result.total_tests}")
        print(f"   Passed: {result.passed_tests}")
        print(f"   Failed: {result.failed_tests}")
        print(f"   Duration: {result.duration:.2f}s")

        if result.coverage:
            print(f"   Coverage: {result.coverage.coverage_percentage:.1f}%")

        print(f"   Artifacts: {len(result.artifacts)}")

        await adapter.cleanup()
    else:
        print("❌ Failed to initialize enhanced pytest adapter")


if __name__ == "__main__":
    asyncio.run(main())