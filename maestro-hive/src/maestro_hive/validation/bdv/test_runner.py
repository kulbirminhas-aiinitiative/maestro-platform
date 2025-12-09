"""
BDV Test Runner
MD-2482 Task 1.1: Execute tests in isolated environment with result parsing.

AC-1: BDV executes tests against generated code using appropriate framework
AC-2: Test results integrated with quality gates
AC-3: Coverage metrics captured and reported
"""

import os
import subprocess
import tempfile
import json
import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import logging
import shutil

from .framework_detector import TestFramework, FrameworkConfig, TestFrameworkDetector

logger = logging.getLogger(__name__)


@dataclass
class TestFailure:
    """Details of a test failure."""
    test_name: str
    file_path: str
    line_number: Optional[int] = None
    error_message: str = ""
    traceback: str = ""
    duration: float = 0.0


@dataclass
class CoverageReport:
    """Code coverage metrics."""
    total_lines: int = 0
    covered_lines: int = 0
    coverage_percent: float = 0.0
    uncovered_files: List[str] = field(default_factory=list)
    branch_coverage: Optional[float] = None
    
    def meets_threshold(self, threshold: float = 80.0) -> bool:
        """Check if coverage meets threshold."""
        return self.coverage_percent >= threshold


@dataclass
class TestResults:
    """
    Complete test execution results.
    AC-2: Test results integrated with quality gates
    """
    total: int = 0
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    duration: float = 0.0
    failures: List[TestFailure] = field(default_factory=list)
    coverage: Optional[CoverageReport] = None
    framework: TestFramework = TestFramework.UNKNOWN
    raw_output: str = ""
    execution_time: str = ""
    
    @property
    def success_rate(self) -> float:
        """Calculate test success rate."""
        if self.total == 0:
            return 0.0
        return (self.passed / self.total) * 100
    
    @property
    def passed_quality_gate(self) -> bool:
        """Check if results pass quality gate."""
        return self.failed == 0 and self.errors == 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "errors": self.errors,
            "duration": self.duration,
            "success_rate": self.success_rate,
            "passed_quality_gate": self.passed_quality_gate,
            "failures": [
                {
                    "test_name": f.test_name,
                    "file_path": f.file_path,
                    "error_message": f.error_message,
                }
                for f in self.failures
            ],
            "coverage": {
                "percent": self.coverage.coverage_percent,
                "meets_threshold": self.coverage.meets_threshold() if self.coverage else False,
            } if self.coverage else None,
            "framework": self.framework.value,
            "execution_time": self.execution_time,
        }


class TestRunner:
    """
    Execute tests in isolated environment.
    
    Supports pytest, jest, mocha, behave frameworks.
    Captures results and coverage metrics.
    """
    
    def __init__(
        self,
        project_path: str,
        config: Optional[FrameworkConfig] = None,
        timeout: int = 300,
        capture_coverage: bool = True,
    ):
        """
        Initialize test runner.
        
        Args:
            project_path: Path to project root
            config: Optional framework config (auto-detected if not provided)
            timeout: Test execution timeout in seconds
            capture_coverage: Whether to capture coverage metrics
        """
        self.project_path = Path(project_path)
        self.timeout = timeout
        self.capture_coverage = capture_coverage
        
        # Detect or use provided config
        if config:
            self.config = config
        else:
            detector = TestFrameworkDetector(project_path)
            self.config = detector.detect()
    
    def execute(self, test_filter: Optional[str] = None) -> TestResults:
        """
        Execute tests and return results.
        
        Args:
            test_filter: Optional filter pattern for tests
            
        Returns:
            TestResults with execution details
        """
        logger.info(f"Executing tests with {self.config.framework.value}")
        
        start_time = datetime.now()
        
        # Build command
        cmd = self._build_command(test_filter)
        
        # Execute
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=self._get_env(),
            )
            
            raw_output = result.stdout + result.stderr
            exit_code = result.returncode
            
        except subprocess.TimeoutExpired:
            logger.error(f"Test execution timed out after {self.timeout}s")
            return TestResults(
                errors=1,
                raw_output="Test execution timed out",
                framework=self.config.framework,
            )
        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            return TestResults(
                errors=1,
                raw_output=str(e),
                framework=self.config.framework,
            )
        
        # Parse results
        duration = (datetime.now() - start_time).total_seconds()
        results = self._parse_results(raw_output, exit_code)
        results.duration = duration
        results.execution_time = start_time.isoformat()
        results.raw_output = raw_output
        
        # Capture coverage
        if self.capture_coverage:
            results.coverage = self._parse_coverage(raw_output)
        
        logger.info(
            f"Tests complete: {results.passed}/{results.total} passed, "
            f"{results.failed} failed in {duration:.2f}s"
        )
        
        return results
    
    def _build_command(self, test_filter: Optional[str]) -> List[str]:
        """Build test execution command."""
        cmd = list(self.config.command)
        
        if self.config.framework in [TestFramework.PYTEST, TestFramework.PYTEST_BDD]:
            # Add pytest options
            cmd.extend(["--tb=short", "-q"])
            
            if self.capture_coverage:
                cmd.extend(["--cov=.", "--cov-report=term-missing"])
            
            if test_filter:
                cmd.extend(["-k", test_filter])
                
        elif self.config.framework == TestFramework.JEST:
            if self.capture_coverage:
                cmd.append("--coverage")
            if test_filter:
                cmd.extend(["--testNamePattern", test_filter])
                
        elif self.config.framework == TestFramework.BEHAVE:
            if test_filter:
                cmd.extend(["--name", test_filter])
        
        return cmd
    
    def _get_env(self) -> Dict[str, str]:
        """Get environment variables for test execution."""
        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["PYTEST_CURRENT_TEST"] = "true"
        return env
    
    def _parse_results(self, output: str, exit_code: int) -> TestResults:
        """Parse test results from output."""
        results = TestResults(framework=self.config.framework)
        
        if self.config.framework in [TestFramework.PYTEST, TestFramework.PYTEST_BDD]:
            results = self._parse_pytest_results(output, exit_code)
        elif self.config.framework == TestFramework.JEST:
            results = self._parse_jest_results(output, exit_code)
        elif self.config.framework == TestFramework.BEHAVE:
            results = self._parse_behave_results(output, exit_code)
        else:
            # Generic parsing
            results.errors = 1 if exit_code != 0 else 0
        
        results.framework = self.config.framework
        return results
    
    def _parse_pytest_results(self, output: str, exit_code: int) -> TestResults:
        """Parse pytest output."""
        results = TestResults()
        
        # Parse summary line: "5 passed, 2 failed, 1 skipped in 1.23s"
        summary_pattern = r"(\d+) passed|(\d+) failed|(\d+) skipped|(\d+) error"
        matches = re.findall(summary_pattern, output)
        
        for match in matches:
            if match[0]:
                results.passed = int(match[0])
            if match[1]:
                results.failed = int(match[1])
            if match[2]:
                results.skipped = int(match[2])
            if match[3]:
                results.errors = int(match[3])
        
        results.total = results.passed + results.failed + results.skipped
        
        # Parse failures
        failure_pattern = r"FAILED ([\w/._]+)::([\w_]+)"
        for match in re.finditer(failure_pattern, output):
            results.failures.append(TestFailure(
                test_name=match.group(2),
                file_path=match.group(1),
            ))
        
        return results
    
    def _parse_jest_results(self, output: str, exit_code: int) -> TestResults:
        """Parse Jest output."""
        results = TestResults()
        
        # Parse summary: "Tests: 5 passed, 2 failed, 7 total"
        tests_pattern = r"Tests:\s*(\d+)\s*passed,?\s*(\d+)?\s*failed?,?\s*(\d+)\s*total"
        match = re.search(tests_pattern, output)
        if match:
            results.passed = int(match.group(1))
            results.failed = int(match.group(2) or 0)
            results.total = int(match.group(3))
        
        return results
    
    def _parse_behave_results(self, output: str, exit_code: int) -> TestResults:
        """Parse Behave output."""
        results = TestResults()
        
        # Parse: "2 features passed, 0 failed"
        # Parse: "6 scenarios passed, 0 failed"
        scenario_pattern = r"(\d+) scenarios? passed,\s*(\d+) failed"
        match = re.search(scenario_pattern, output)
        if match:
            results.passed = int(match.group(1))
            results.failed = int(match.group(2))
            results.total = results.passed + results.failed
        
        return results
    
    def _parse_coverage(self, output: str) -> Optional[CoverageReport]:
        """Parse coverage metrics from output."""
        # AC-3: Coverage metrics captured and reported
        
        # Pytest-cov format: "TOTAL    1000    200    80%"
        cov_pattern = r"TOTAL\s+(\d+)\s+(\d+)\s+(\d+)%"
        match = re.search(cov_pattern, output)
        
        if match:
            total = int(match.group(1))
            missed = int(match.group(2))
            percent = float(match.group(3))
            
            return CoverageReport(
                total_lines=total,
                covered_lines=total - missed,
                coverage_percent=percent,
            )
        
        # Jest format: "All files | 80 | 75 | 85 | 80"
        jest_pattern = r"All files\s*\|\s*([\d.]+)"
        match = re.search(jest_pattern, output)
        if match:
            return CoverageReport(
                coverage_percent=float(match.group(1)),
            )
        
        return None


class IsolatedTestRunner(TestRunner):
    """
    Run tests in a completely isolated environment.
    Creates temp directory, installs dependencies, runs tests.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.temp_dir: Optional[Path] = None
    
    def execute_isolated(self, test_filter: Optional[str] = None) -> TestResults:
        """Execute tests in isolated temp directory."""
        try:
            # Create temp directory
            self.temp_dir = Path(tempfile.mkdtemp(prefix="bdv_test_"))
            
            # Copy project
            shutil.copytree(
                self.project_path,
                self.temp_dir / "project",
                ignore=shutil.ignore_patterns(
                    "__pycache__", "*.pyc", ".git", "node_modules", ".venv"
                ),
            )
            
            # Update project path
            original_path = self.project_path
            self.project_path = self.temp_dir / "project"
            
            # Run tests
            results = self.execute(test_filter)
            
            # Restore
            self.project_path = original_path
            
            return results
            
        finally:
            # Cleanup
            if self.temp_dir and self.temp_dir.exists():
                shutil.rmtree(self.temp_dir, ignore_errors=True)
