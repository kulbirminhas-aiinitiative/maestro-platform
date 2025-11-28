#!/usr/bin/env python3
"""
Quality Fabric - Error Monitor
Continuously monitors projects for errors and failures
"""

import asyncio
import logging
import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime
import subprocess

logger = logging.getLogger(__name__)


class ErrorType(str, Enum):
    """Types of errors that can be monitored"""
    TEST_FAILURE = "test_failure"
    BUILD_ERROR = "build_error"
    TYPE_ERROR = "type_error"
    LINT_ERROR = "lint_error"
    RUNTIME_ERROR = "runtime_error"
    IMPORT_ERROR = "import_error"
    DEPENDENCY_ERROR = "dependency_error"


class ErrorSeverity(str, Enum):
    """Severity levels for errors"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class ErrorEvent:
    """Represents a detected error event"""
    error_id: str
    error_type: ErrorType
    severity: ErrorSeverity
    file_path: str
    line_number: Optional[int]
    error_message: str
    stack_trace: Optional[str]
    context: Dict[str, Any]
    timestamp: str
    healable: bool
    confidence: float


class ErrorMonitor:
    """Continuously monitor projects for errors"""

    def __init__(self, project_path: str, config: Dict[str, Any] = None):
        self.project_path = Path(project_path)
        self.config = config or {}
        self.is_monitoring = False
        self.error_callbacks: List[Callable] = []
        self.error_history: List[ErrorEvent] = []

        # Monitor intervals (seconds)
        self.test_monitor_interval = self.config.get('test_monitor_interval', 30)
        self.build_monitor_interval = self.config.get('build_monitor_interval', 60)
        self.type_monitor_interval = self.config.get('type_monitor_interval', 45)

        logger.info(f"Error Monitor initialized for: {self.project_path}")

    async def start_monitoring(self):
        """Start all error monitors"""
        self.is_monitoring = True
        logger.info("Starting continuous error monitoring...")

        # Start all monitor tasks concurrently
        tasks = [
            self.monitor_test_failures(),
            self.monitor_build_errors(),
            self.monitor_type_errors(),
            self.monitor_lint_errors()
        ]

        await asyncio.gather(*tasks, return_exceptions=True)

    async def stop_monitoring(self):
        """Stop all monitors"""
        self.is_monitoring = False
        logger.info("Stopped error monitoring")

    def register_error_callback(self, callback: Callable):
        """Register a callback for error events"""
        self.error_callbacks.append(callback)

    async def emit_error(self, error: ErrorEvent):
        """Emit error event to all registered callbacks"""
        self.error_history.append(error)

        logger.warning(f"Error detected: {error.error_type} - {error.error_message}")

        # Notify all callbacks
        for callback in self.error_callbacks:
            try:
                await callback(error)
            except Exception as e:
                logger.error(f"Error callback failed: {e}")

    # ========================================================================
    # Test Failure Monitoring
    # ========================================================================

    async def monitor_test_failures(self):
        """Continuously monitor for test failures"""
        logger.info("Test failure monitor started")

        while self.is_monitoring:
            try:
                await self._check_test_failures()
            except Exception as e:
                logger.error(f"Test monitor error: {e}")

            await asyncio.sleep(self.test_monitor_interval)

    async def _check_test_failures(self):
        """Check for test failures by running tests"""
        # Detect test framework
        if (self.project_path / 'package.json').exists():
            # JavaScript/TypeScript project
            await self._check_js_tests()
        elif (self.project_path / 'pytest.ini').exists() or (self.project_path / 'pyproject.toml').exists():
            # Python project
            await self._check_python_tests()

    async def _check_js_tests(self):
        """Check JavaScript/TypeScript tests (Jest/Vitest)"""
        try:
            result = subprocess.run(
                ['npm', 'test', '--', '--reporter=json'],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=120
            )

            # Parse test output
            if result.returncode != 0:
                await self._parse_js_test_failures(result.stdout, result.stderr)

        except subprocess.TimeoutExpired:
            logger.warning("Test execution timed out")
        except Exception as e:
            logger.error(f"Failed to check JS tests: {e}")

    async def _parse_js_test_failures(self, stdout: str, stderr: str):
        """Parse JavaScript test failures"""
        # Parse Jest/Vitest JSON output
        try:
            # Look for test failure patterns
            failure_pattern = re.compile(r'FAIL\s+(.+\.test\.[tj]sx?)')
            error_pattern = re.compile(r'●\s+(.+)')

            for match in failure_pattern.finditer(stdout + stderr):
                file_path = match.group(1)

                error = ErrorEvent(
                    error_id=f"test_{hash(file_path + str(datetime.now()))}",
                    error_type=ErrorType.TEST_FAILURE,
                    severity=ErrorSeverity.HIGH,
                    file_path=file_path,
                    line_number=None,
                    error_message="Test failed",
                    stack_trace=stderr[:500],
                    context={"output": stdout[:1000]},
                    timestamp=datetime.now().isoformat(),
                    healable=True,
                    confidence=0.8
                )

                await self.emit_error(error)

        except Exception as e:
            logger.error(f"Failed to parse JS test failures: {e}")

    async def _check_python_tests(self):
        """Check Python tests (pytest)"""
        try:
            result = subprocess.run(
                ['pytest', '--json-report', '--json-report-file=/tmp/pytest_report.json'],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                await self._parse_python_test_failures(result.stdout, result.stderr)

        except Exception as e:
            logger.error(f"Failed to check Python tests: {e}")

    async def _parse_python_test_failures(self, stdout: str, stderr: str):
        """Parse Python test failures"""
        # Parse pytest output for failures
        failure_pattern = re.compile(r'FAILED\s+(.+)::([\w_]+)')

        for match in failure_pattern.finditer(stdout):
            file_path = match.group(1)
            test_name = match.group(2)

            error = ErrorEvent(
                error_id=f"pytest_{hash(file_path + test_name)}",
                error_type=ErrorType.TEST_FAILURE,
                severity=ErrorSeverity.HIGH,
                file_path=file_path,
                line_number=None,
                error_message=f"Test failed: {test_name}",
                stack_trace=stderr[:500],
                context={"test_name": test_name},
                timestamp=datetime.now().isoformat(),
                healable=True,
                confidence=0.85
            )

            await self.emit_error(error)

    # ========================================================================
    # Build Error Monitoring
    # ========================================================================

    async def monitor_build_errors(self):
        """Continuously monitor for build errors"""
        logger.info("Build error monitor started")

        while self.is_monitoring:
            try:
                await self._check_build_errors()
            except Exception as e:
                logger.error(f"Build monitor error: {e}")

            await asyncio.sleep(self.build_monitor_interval)

    async def _check_build_errors(self):
        """Check for build errors"""
        if (self.project_path / 'package.json').exists():
            await self._check_npm_build()

    async def _check_npm_build(self):
        """Check npm build"""
        try:
            result = subprocess.run(
                ['npm', 'run', 'build'],
                cwd=str(self.project_path),
                capture_output=True,
                text=True,
                timeout=180
            )

            if result.returncode != 0:
                await self._parse_build_errors(result.stdout, result.stderr)

        except subprocess.TimeoutExpired:
            logger.warning("Build timed out")
        except Exception as e:
            logger.error(f"Failed to check build: {e}")

    async def _parse_build_errors(self, stdout: str, stderr: str):
        """Parse build errors"""
        error_pattern = re.compile(r'ERROR in (.+)')

        for match in error_pattern.finditer(stdout + stderr):
            error_msg = match.group(1)

            error = ErrorEvent(
                error_id=f"build_{hash(error_msg)}",
                error_type=ErrorType.BUILD_ERROR,
                severity=ErrorSeverity.CRITICAL,
                file_path="build",
                line_number=None,
                error_message=error_msg,
                stack_trace=stderr[:500],
                context={"output": stdout[:1000]},
                timestamp=datetime.now().isoformat(),
                healable=True,
                confidence=0.7
            )

            await self.emit_error(error)

    # ========================================================================
    # Type Error Monitoring
    # ========================================================================

    async def monitor_type_errors(self):
        """Continuously monitor for TypeScript type errors"""
        logger.info("Type error monitor started")

        while self.is_monitoring:
            try:
                await self._check_type_errors()
            except Exception as e:
                logger.error(f"Type monitor error: {e}")

            await asyncio.sleep(self.type_monitor_interval)

    async def _check_type_errors(self):
        """Check for TypeScript type errors"""
        if (self.project_path / 'tsconfig.json').exists():
            try:
                result = subprocess.run(
                    ['npx', 'tsc', '--noEmit'],
                    cwd=str(self.project_path),
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode != 0:
                    await self._parse_type_errors(result.stdout, result.stderr)

            except Exception as e:
                logger.error(f"Failed to check type errors: {e}")

    async def _parse_type_errors(self, stdout: str, stderr: str):
        """Parse TypeScript type errors"""
        # Pattern: file.ts(line,col): error TS2322: Type 'X' is not assignable to type 'Y'
        type_error_pattern = re.compile(
            r'(.+\.tsx?)\((\d+),(\d+)\):\s+error\s+(TS\d+):\s+(.+)'
        )

        for match in type_error_pattern.finditer(stdout + stderr):
            file_path = match.group(1)
            line_number = int(match.group(2))
            error_code = match.group(4)
            error_msg = match.group(5)

            error = ErrorEvent(
                error_id=f"type_{hash(file_path + str(line_number))}",
                error_type=ErrorType.TYPE_ERROR,
                severity=ErrorSeverity.MEDIUM,
                file_path=file_path,
                line_number=line_number,
                error_message=f"{error_code}: {error_msg}",
                stack_trace=None,
                context={"error_code": error_code},
                timestamp=datetime.now().isoformat(),
                healable=True,
                confidence=0.75
            )

            await self.emit_error(error)

    # ========================================================================
    # Lint Error Monitoring
    # ========================================================================

    async def monitor_lint_errors(self):
        """Continuously monitor for linting errors"""
        logger.info("Lint error monitor started")

        while self.is_monitoring:
            try:
                await self._check_lint_errors()
            except Exception as e:
                logger.error(f"Lint monitor error: {e}")

            await asyncio.sleep(60)  # Check every minute

    async def _check_lint_errors(self):
        """Check for linting errors"""
        if (self.project_path / '.eslintrc.js').exists() or (self.project_path / '.eslintrc.json').exists():
            try:
                result = subprocess.run(
                    ['npx', 'eslint', '.', '--format=json'],
                    cwd=str(self.project_path),
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.stdout:
                    await self._parse_lint_errors(result.stdout)

            except Exception as e:
                logger.error(f"Failed to check lint errors: {e}")

    async def _parse_lint_errors(self, output: str):
        """Parse ESLint errors"""
        try:
            lint_results = json.loads(output)

            for file_result in lint_results:
                if file_result.get('errorCount', 0) > 0:
                    for message in file_result.get('messages', []):
                        if message.get('severity') == 2:  # Error (not warning)
                            error = ErrorEvent(
                                error_id=f"lint_{hash(file_result['filePath'] + str(message['line']))}",
                                error_type=ErrorType.LINT_ERROR,
                                severity=ErrorSeverity.LOW,
                                file_path=file_result['filePath'],
                                line_number=message.get('line'),
                                error_message=message.get('message', ''),
                                stack_trace=None,
                                context={"rule": message.get('ruleId')},
                                timestamp=datetime.now().isoformat(),
                                healable=True,
                                confidence=0.9
                            )

                            await self.emit_error(error)

        except json.JSONDecodeError:
            logger.error("Failed to parse lint output as JSON")

    # ========================================================================
    # Utility Methods
    # ========================================================================

    def get_error_history(self, limit: int = 100) -> List[ErrorEvent]:
        """Get recent error history"""
        return self.error_history[-limit:]

    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        stats = {
            "total_errors": len(self.error_history),
            "by_type": {},
            "by_severity": {},
            "healable_count": 0
        }

        for error in self.error_history:
            # Count by type
            error_type = error.error_type.value
            stats["by_type"][error_type] = stats["by_type"].get(error_type, 0) + 1

            # Count by severity
            severity = error.severity.value
            stats["by_severity"][severity] = stats["by_severity"].get(severity, 0) + 1

            # Count healable
            if error.healable:
                stats["healable_count"] += 1

        return stats