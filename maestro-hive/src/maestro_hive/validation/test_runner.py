"""
Test Runner - Execute Tests Within Persona Context (MD-3092)

AC-3: Personas can execute tests on generated code

This module provides test execution capabilities for personas.
"""

import logging
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .exceptions import TestExecutionError


logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """
    Result of a test execution.
    
    Attributes:
        success: Whether all tests passed
        tests_total: Total number of tests
        tests_passed: Number of passing tests
        tests_failed: Number of failing tests
        tests_skipped: Number of skipped tests
        failed_tests: Names of failed tests
        output: Raw test output
        coverage: Coverage percentage (if available)
        execution_time_seconds: Time taken to run tests
    """
    success: bool
    tests_total: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    tests_skipped: int = 0
    failed_tests: List[str] = field(default_factory=list)
    output: str = ""
    coverage: Optional[float] = None
    execution_time_seconds: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/reporting."""
        return {
            "success": self.success,
            "tests_total": self.tests_total,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "tests_skipped": self.tests_skipped,
            "failed_tests": self.failed_tests,
            "coverage": self.coverage,
            "execution_time_seconds": self.execution_time_seconds,
            "timestamp": self.timestamp.isoformat()
        }


class TestRunner:
    """
    Test runner for executing tests on generated code.
    
    Implements AC-3: Personas can execute tests on generated code.
    
    Features:
        - Run pytest on test files
        - Run tests from code strings
        - Capture and parse test output
        - Extract failed test names for reflection
    
    Example:
        >>> runner = TestRunner()
        >>> result = runner.run_pytest("tests/test_module.py")
        >>> if not result.success:
        ...     print(f"Failed tests: {result.failed_tests}")
    """
    
    def __init__(
        self,
        timeout_seconds: int = 60,
        python_path: Optional[str] = None
    ):
        """
        Initialize the test runner.
        
        Args:
            timeout_seconds: Maximum time for test execution
            python_path: Custom Python interpreter path
        """
        self.timeout_seconds = timeout_seconds
        self.python_path = python_path or sys.executable
    
    def run_pytest(
        self,
        test_path: str,
        extra_args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None
    ) -> TestResult:
        """
        Run pytest on a test file or directory.
        
        Args:
            test_path: Path to test file or directory
            extra_args: Additional pytest arguments
            env: Environment variables for test execution
        
        Returns:
            TestResult with execution details
        """
        import time
        start_time = time.perf_counter()
        
        # Build pytest command
        cmd = [
            self.python_path, "-m", "pytest",
            test_path,
            "-v",
            "--tb=short",
            "-q"
        ]
        
        if extra_args:
            cmd.extend(extra_args)
        
        # Set up environment
        test_env = os.environ.copy()
        if env:
            test_env.update(env)
        
        # Add PYTHONPATH for maestro_hive
        if "PYTHONPATH" not in test_env:
            src_path = Path(__file__).parent.parent.parent.parent
            test_env["PYTHONPATH"] = str(src_path)
        
        logger.info(f"Running pytest: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                env=test_env,
                cwd=str(Path(test_path).parent) if Path(test_path).is_file() else test_path
            )
            
            output = result.stdout + result.stderr
            exit_code = result.returncode
            
        except subprocess.TimeoutExpired:
            execution_time = time.perf_counter() - start_time
            return TestResult(
                success=False,
                output=f"Test execution timed out after {self.timeout_seconds}s",
                execution_time_seconds=execution_time
            )
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            return TestResult(
                success=False,
                output=f"Test execution failed: {e}",
                execution_time_seconds=execution_time
            )
        
        execution_time = time.perf_counter() - start_time
        
        # Parse results
        return self._parse_pytest_output(output, exit_code, execution_time)
    
    def run_test_code(
        self,
        test_code: str,
        implementation_code: Optional[str] = None,
        test_filename: str = "test_generated.py"
    ) -> TestResult:
        """
        Run tests from code strings.
        
        Creates temporary files and runs pytest.
        
        Args:
            test_code: Test code to execute
            implementation_code: Optional implementation code
            test_filename: Name for the test file
        
        Returns:
            TestResult with execution details
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            
            # Write test file
            test_file = tmppath / test_filename
            test_file.write_text(test_code)
            
            # Write implementation if provided
            if implementation_code:
                impl_file = tmppath / "implementation.py"
                impl_file.write_text(implementation_code)
            
            # Run pytest
            return self.run_pytest(str(test_file))
    
    def run_syntax_test(self, code: str, filename: str = "<test>") -> TestResult:
        """
        Run a simple syntax/import test on code.
        
        This validates that the code can be compiled and imported.
        
        Args:
            code: Python code to test
            filename: Filename for error reporting
        
        Returns:
            TestResult indicating syntax validity
        """
        import time
        start_time = time.perf_counter()
        
        try:
            # Try to compile
            compile(code, filename, "exec")
            
            # Try to execute in isolated namespace
            namespace: Dict[str, Any] = {}
            exec(compile(code, filename, "exec"), namespace)
            
            execution_time = time.perf_counter() - start_time
            
            return TestResult(
                success=True,
                tests_total=1,
                tests_passed=1,
                output="Syntax and import validation passed",
                execution_time_seconds=execution_time
            )
            
        except SyntaxError as e:
            execution_time = time.perf_counter() - start_time
            return TestResult(
                success=False,
                tests_total=1,
                tests_failed=1,
                failed_tests=["syntax_validation"],
                output=f"Syntax error: {e}",
                execution_time_seconds=execution_time
            )
            
        except Exception as e:
            execution_time = time.perf_counter() - start_time
            return TestResult(
                success=False,
                tests_total=1,
                tests_failed=1,
                failed_tests=["import_validation"],
                output=f"Import/execution error: {e}",
                execution_time_seconds=execution_time
            )
    
    def _parse_pytest_output(
        self,
        output: str,
        exit_code: int,
        execution_time: float
    ) -> TestResult:
        """Parse pytest output to extract test results."""
        import re
        
        # Default values
        tests_passed = 0
        tests_failed = 0
        tests_skipped = 0
        failed_tests = []
        
        # Parse passed/failed counts from output
        # Matches patterns like "5 passed", "2 failed", "1 skipped"
        passed_match = re.search(r"(\d+)\s+passed", output)
        if passed_match:
            tests_passed = int(passed_match.group(1))
        
        failed_match = re.search(r"(\d+)\s+failed", output)
        if failed_match:
            tests_failed = int(failed_match.group(1))
        
        skipped_match = re.search(r"(\d+)\s+skipped", output)
        if skipped_match:
            tests_skipped = int(skipped_match.group(1))
        
        # Extract failed test names
        # Matches patterns like "FAILED test_module.py::test_function"
        failed_pattern = re.findall(r"FAILED\s+([\w./]+::[\w_]+)", output)
        failed_tests = failed_pattern
        
        # Also check for assertion failures
        assertion_pattern = re.findall(r"def\s+(test_\w+).*?AssertionError", output, re.DOTALL)
        for test_name in assertion_pattern:
            if test_name not in failed_tests:
                failed_tests.append(test_name)
        
        tests_total = tests_passed + tests_failed + tests_skipped
        success = exit_code == 0 and tests_failed == 0
        
        return TestResult(
            success=success,
            tests_total=tests_total,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            tests_skipped=tests_skipped,
            failed_tests=failed_tests,
            output=output,
            execution_time_seconds=execution_time
        )


def run_tests(test_path: str) -> TestResult:
    """
    Convenience function to run tests.
    
    Args:
        test_path: Path to test file or directory
    
    Returns:
        TestResult with execution details
    """
    runner = TestRunner()
    return runner.run_pytest(test_path)
