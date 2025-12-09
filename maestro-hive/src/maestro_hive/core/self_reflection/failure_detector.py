#!/usr/bin/env python3
"""
FailureDetector: Pattern Recognition from Execution History

Part of MD-2533: Self-Healing Mechanism - Auto-Refactoring

This module scans pytest output, application logs, and execution history
to identify failures that can be automatically remediated.

Architecture parallel with GapDetector:
- GapDetector: Static analysis gaps (missing files/capabilities)
- FailureDetector: Runtime failures (test failures, exceptions)
"""

import json
import re
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class FailureType(Enum):
    """Types of failures that can be detected and potentially auto-fixed."""
    TEST_FAILURE = "TEST_FAILURE"
    IMPORT_ERROR = "IMPORT_ERROR"
    ATTRIBUTE_ERROR = "ATTRIBUTE_ERROR"
    TYPE_ERROR = "TYPE_ERROR"
    SYNTAX_ERROR = "SYNTAX_ERROR"
    ASSERTION_ERROR = "ASSERTION_ERROR"
    NAME_ERROR = "NAME_ERROR"
    KEY_ERROR = "KEY_ERROR"
    INDEX_ERROR = "INDEX_ERROR"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    UNKNOWN = "UNKNOWN"


class Severity(Enum):
    """Severity levels for failures."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class Failure:
    """
    Represents a detected failure that may be auto-remediated.

    Analogous to Gap in gap_detector.py but for runtime failures.
    """
    failure_id: str
    failure_type: FailureType
    error_message: str
    stack_trace: str
    file_path: Optional[str]
    line_number: Optional[int]
    function_name: Optional[str]
    severity: Severity
    source: str  # 'pytest', 'logs', 'execution_history'
    context: Dict[str, Any] = field(default_factory=dict)
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def get_hash(self) -> str:
        """Generate a deterministic hash for deduplication."""
        unique_str = f"{self.failure_type.value}|{self.file_path}|{self.line_number}|{self.error_message[:100]}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        d = asdict(self)
        d['failure_type'] = self.failure_type.value
        d['severity'] = self.severity.value
        return d


class FailureDetector:
    """
    Detects failures from various sources for the self-healing loop.

    Sources:
    - pytest output files
    - Application logs
    - Execution history store (MD-2500)

    Usage:
        detector = FailureDetector()
        failures = detector.scan_pytest("pytest_output.txt")
        failures += detector.scan_logs("/var/log/app.log")
    """

    # Regex patterns for parsing pytest output
    PYTEST_FAILURE_PATTERN = re.compile(
        r'(?:FAILED|ERROR)\s+(\S+)::(\S+)(?:::(\S+))?',
        re.MULTILINE
    )

    PYTEST_ERROR_PATTERN = re.compile(
        r'([\w.]+Error|[\w.]+Exception):\s*(.+?)(?:\n|$)',
        re.MULTILINE
    )

    PYTEST_LOCATION_PATTERN = re.compile(
        r'(\S+\.py):(\d+):',
        re.MULTILINE
    )

    # Patterns for log parsing
    LOG_ERROR_PATTERN = re.compile(
        r'\b(ERROR|CRITICAL|FATAL)\b.*?(?:Exception|Error):\s*(.+)',
        re.IGNORECASE
    )

    # Error type to FailureType mapping
    ERROR_TYPE_MAP = {
        'ImportError': FailureType.IMPORT_ERROR,
        'ModuleNotFoundError': FailureType.IMPORT_ERROR,
        'AttributeError': FailureType.ATTRIBUTE_ERROR,
        'TypeError': FailureType.TYPE_ERROR,
        'SyntaxError': FailureType.SYNTAX_ERROR,
        'AssertionError': FailureType.ASSERTION_ERROR,
        'NameError': FailureType.NAME_ERROR,
        'KeyError': FailureType.KEY_ERROR,
        'IndexError': FailureType.INDEX_ERROR,
        'RuntimeError': FailureType.RUNTIME_ERROR,
    }

    def __init__(self, workspace_root: Optional[str] = None):
        """
        Initialize FailureDetector.

        Args:
            workspace_root: Root directory for resolving relative paths
        """
        self.workspace_root = Path(workspace_root) if workspace_root else Path.cwd()
        self.failures: List[Failure] = []
        self._seen_hashes: set = set()

    def scan_pytest(self, output_path: str) -> List[Failure]:
        """
        Parse pytest output file to extract failures.

        Args:
            output_path: Path to pytest output file (stdout capture)

        Returns:
            List of detected Failure objects
        """
        logger.info(f"Scanning pytest output: {output_path}")

        output_file = Path(output_path)
        if not output_file.exists():
            logger.warning(f"Pytest output file not found: {output_path}")
            return []

        content = output_file.read_text(errors='replace')
        failures = self._parse_pytest_output(content)

        # Deduplicate
        new_failures = []
        for f in failures:
            h = f.get_hash()
            if h not in self._seen_hashes:
                self._seen_hashes.add(h)
                new_failures.append(f)
                self.failures.append(f)

        logger.info(f"Found {len(new_failures)} unique failures in pytest output")
        return new_failures

    def scan_pytest_json(self, json_path: str) -> List[Failure]:
        """
        Parse pytest JSON report (from pytest-json-report).

        Args:
            json_path: Path to pytest JSON report

        Returns:
            List of detected Failure objects
        """
        logger.info(f"Scanning pytest JSON report: {json_path}")

        json_file = Path(json_path)
        if not json_file.exists():
            logger.warning(f"Pytest JSON report not found: {json_path}")
            return []

        try:
            with open(json_file, 'r') as f:
                report = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON report: {e}")
            return []

        failures = []
        for test in report.get('tests', []):
            if test.get('outcome') in ('failed', 'error'):
                failure = self._parse_pytest_json_test(test)
                if failure:
                    h = failure.get_hash()
                    if h not in self._seen_hashes:
                        self._seen_hashes.add(h)
                        failures.append(failure)
                        self.failures.append(failure)

        logger.info(f"Found {len(failures)} failures in JSON report")
        return failures

    def scan_logs(self, log_path: str, since: Optional[datetime] = None) -> List[Failure]:
        """
        Parse application logs for errors.

        Args:
            log_path: Path to log file
            since: Only consider log entries after this timestamp

        Returns:
            List of detected Failure objects
        """
        logger.info(f"Scanning logs: {log_path}")

        log_file = Path(log_path)
        if not log_file.exists():
            logger.warning(f"Log file not found: {log_path}")
            return []

        content = log_file.read_text(errors='replace')
        failures = []

        for match in self.LOG_ERROR_PATTERN.finditer(content):
            level, message = match.groups()

            # Determine failure type from message
            failure_type = FailureType.UNKNOWN
            for error_name, ft in self.ERROR_TYPE_MAP.items():
                if error_name in message:
                    failure_type = ft
                    break

            # Determine severity from log level
            severity = Severity.HIGH if level.upper() in ('CRITICAL', 'FATAL') else Severity.MEDIUM

            failure = Failure(
                failure_id=f"log_{hashlib.md5(message.encode()).hexdigest()[:8]}",
                failure_type=failure_type,
                error_message=message.strip(),
                stack_trace="",  # Logs may not have full trace
                file_path=None,
                line_number=None,
                function_name=None,
                severity=severity,
                source='logs',
                context={'log_file': str(log_path), 'log_level': level}
            )

            h = failure.get_hash()
            if h not in self._seen_hashes:
                self._seen_hashes.add(h)
                failures.append(failure)
                self.failures.append(failure)

        logger.info(f"Found {len(failures)} failures in logs")
        return failures

    def scan_execution_history(self, history_path: str) -> List[Failure]:
        """
        Parse execution history store (JSON format).

        Args:
            history_path: Path to execution history JSON file

        Returns:
            List of detected Failure objects
        """
        logger.info(f"Scanning execution history: {history_path}")

        history_file = Path(history_path)
        if not history_file.exists():
            logger.warning(f"Execution history not found: {history_path}")
            return []

        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse execution history: {e}")
            return []

        failures = []
        executions = history.get('executions', [])

        for execution in executions:
            if execution.get('status') == 'FAILED':
                error = execution.get('error', {})

                failure = Failure(
                    failure_id=execution.get('id', f"exec_{len(failures)}"),
                    failure_type=self._classify_error(error.get('type', '')),
                    error_message=error.get('message', 'Unknown error'),
                    stack_trace=error.get('stack_trace', ''),
                    file_path=error.get('file_path'),
                    line_number=error.get('line_number'),
                    function_name=error.get('function'),
                    severity=self._determine_severity(error),
                    source='execution_history',
                    context={
                        'execution_id': execution.get('id'),
                        'block_id': execution.get('block_id'),
                        'timestamp': execution.get('timestamp')
                    }
                )

                h = failure.get_hash()
                if h not in self._seen_hashes:
                    self._seen_hashes.add(h)
                    failures.append(failure)
                    self.failures.append(failure)

        logger.info(f"Found {len(failures)} failures in execution history")
        return failures

    def _parse_pytest_output(self, content: str) -> List[Failure]:
        """Parse raw pytest output text."""
        failures = []

        # Split into test sections
        sections = re.split(r'_{10,}', content)

        for section in sections:
            if 'FAILED' in section or 'ERROR' in section:
                failure = self._parse_pytest_section(section)
                if failure:
                    failures.append(failure)

        return failures

    def _parse_pytest_section(self, section: str) -> Optional[Failure]:
        """Parse a single pytest failure section."""
        # Extract test identifier
        test_match = self.PYTEST_FAILURE_PATTERN.search(section)
        if not test_match:
            return None

        file_path = test_match.group(1)
        test_class = test_match.group(2)
        test_method = test_match.group(3) or test_class

        # Extract error type and message
        error_match = self.PYTEST_ERROR_PATTERN.search(section)
        error_type = 'AssertionError'
        error_message = 'Test failed'

        if error_match:
            error_type = error_match.group(1)
            error_message = error_match.group(2).strip()

        # Extract line number
        loc_match = self.PYTEST_LOCATION_PATTERN.search(section)
        line_number = int(loc_match.group(2)) if loc_match else None

        failure_type = self._classify_error(error_type)

        return Failure(
            failure_id=f"pytest_{hashlib.md5(section.encode()).hexdigest()[:8]}",
            failure_type=failure_type,
            error_message=error_message,
            stack_trace=section,
            file_path=file_path,
            line_number=line_number,
            function_name=test_method,
            severity=self._severity_from_type(failure_type),
            source='pytest',
            context={
                'test_class': test_class,
                'test_method': test_method
            }
        )

    def _parse_pytest_json_test(self, test: Dict[str, Any]) -> Optional[Failure]:
        """Parse a test entry from pytest JSON report."""
        call_info = test.get('call', {})
        if not call_info:
            return None

        # Extract location
        nodeid = test.get('nodeid', '')
        parts = nodeid.split('::')
        file_path = parts[0] if parts else None
        function_name = parts[-1] if len(parts) > 1 else None

        # Extract error info
        longrepr = call_info.get('longrepr', '')
        if isinstance(longrepr, dict):
            longrepr = longrepr.get('reprcrash', {}).get('message', str(longrepr))

        # Try to extract error type
        error_type = 'AssertionError'
        for etype in self.ERROR_TYPE_MAP.keys():
            if etype in str(longrepr):
                error_type = etype
                break

        failure_type = self._classify_error(error_type)

        return Failure(
            failure_id=f"pytest_{test.get('nodeid', 'unknown')[:20]}",
            failure_type=failure_type,
            error_message=str(longrepr)[:500],
            stack_trace=call_info.get('traceback', ''),
            file_path=file_path,
            line_number=test.get('lineno'),
            function_name=function_name,
            severity=self._severity_from_type(failure_type),
            source='pytest_json',
            context={
                'nodeid': nodeid,
                'duration': call_info.get('duration', 0)
            }
        )

    def _classify_error(self, error_type: str) -> FailureType:
        """Classify an error string into FailureType."""
        for key, value in self.ERROR_TYPE_MAP.items():
            if key in error_type:
                return value
        return FailureType.UNKNOWN

    def _severity_from_type(self, failure_type: FailureType) -> Severity:
        """Determine severity from failure type."""
        severity_map = {
            FailureType.SYNTAX_ERROR: Severity.CRITICAL,
            FailureType.IMPORT_ERROR: Severity.HIGH,
            FailureType.NAME_ERROR: Severity.HIGH,
            FailureType.TYPE_ERROR: Severity.MEDIUM,
            FailureType.ATTRIBUTE_ERROR: Severity.MEDIUM,
            FailureType.ASSERTION_ERROR: Severity.MEDIUM,
            FailureType.KEY_ERROR: Severity.LOW,
            FailureType.INDEX_ERROR: Severity.LOW,
        }
        return severity_map.get(failure_type, Severity.MEDIUM)

    def _determine_severity(self, error: Dict[str, Any]) -> Severity:
        """Determine severity from error context."""
        if error.get('fatal') or error.get('blocking'):
            return Severity.CRITICAL
        error_type = error.get('type', '')
        return self._severity_from_type(self._classify_error(error_type))

    def get_failures_by_severity(self) -> Dict[Severity, List[Failure]]:
        """Group failures by severity level."""
        by_severity = {s: [] for s in Severity}
        for f in self.failures:
            by_severity[f.severity].append(f)
        return by_severity

    def get_failures_by_type(self) -> Dict[FailureType, List[Failure]]:
        """Group failures by failure type."""
        by_type = {t: [] for t in FailureType}
        for f in self.failures:
            by_type[f.failure_type].append(f)
        return by_type

    def generate_report(self, output_format: str = 'text') -> str:
        """Generate a human-readable failure report."""
        if not self.failures:
            return "No failures detected."

        if output_format == 'json':
            return json.dumps([f.to_dict() for f in self.failures], indent=2)

        # Text report
        lines = ["# Failure Detection Report", ""]

        by_severity = self.get_failures_by_severity()

        for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW]:
            failures = by_severity[severity]
            if failures:
                lines.append(f"## {severity.value} ({len(failures)})")
                for f in failures:
                    lines.append(f"- [{f.failure_type.value}] {f.error_message[:80]}")
                    if f.file_path:
                        lines.append(f"  Location: {f.file_path}:{f.line_number or '?'}")
                lines.append("")

        return "\n".join(lines)

    def clear(self):
        """Clear all detected failures."""
        self.failures.clear()
        self._seen_hashes.clear()


if __name__ == "__main__":
    # Demo usage
    import sys

    detector = FailureDetector()

    if len(sys.argv) > 1:
        # Scan provided file
        path = sys.argv[1]
        if path.endswith('.json'):
            detector.scan_pytest_json(path)
        else:
            detector.scan_pytest(path)
    else:
        print("Usage: python failure_detector.py <pytest_output_file>")
        print("\nThis module detects failures from:")
        print("  - pytest output files")
        print("  - pytest JSON reports")
        print("  - Application logs")
        print("  - Execution history")

    print(detector.generate_report())
