#!/usr/bin/env python3
"""
Test Reporter: Generate test reports and metrics.

Implements AC-6: Test reporting and metrics collection.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .framework import TestResults, TestStatus

logger = logging.getLogger(__name__)


class ReportFormat(Enum):
    """Supported report formats."""
    JSON = "json"
    HTML = "html"
    XML = "xml"
    TEXT = "text"
    MARKDOWN = "markdown"


@dataclass
class TestMetrics:
    """Aggregated test metrics."""
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    error_tests: int = 0
    pass_rate: float = 0.0
    total_duration: float = 0.0
    avg_duration: float = 0.0
    coverage_percent: float = 0.0
    tests_by_status: Dict[str, int] = field(default_factory=dict)
    tests_by_module: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_tests': self.total_tests,
            'passed_tests': self.passed_tests,
            'failed_tests': self.failed_tests,
            'skipped_tests': self.skipped_tests,
            'error_tests': self.error_tests,
            'pass_rate': self.pass_rate,
            'total_duration': self.total_duration,
            'avg_duration': self.avg_duration,
            'coverage_percent': self.coverage_percent,
            'tests_by_status': self.tests_by_status,
            'tests_by_module': self.tests_by_module
        }


@dataclass
class TestReport:
    """Complete test report."""
    title: str
    timestamp: str
    results: TestResults
    metrics: TestMetrics
    format: ReportFormat
    content: str = ""
    file_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'title': self.title,
            'timestamp': self.timestamp,
            'results': self.results.to_dict(),
            'metrics': self.metrics.to_dict(),
            'format': self.format.value
        }

    def save(self, path: str) -> None:
        """Save report to file."""
        with open(path, 'w') as f:
            f.write(self.content)
        self.file_path = path
        logger.info(f"Report saved to {path}")


class TestReporter:
    """
    Generate test reports.

    AC-6: Test reporting implementation.

    Features:
    - Multiple output formats
    - Metrics aggregation
    - Trend analysis
    - Quality Fabric integration
    """

    def __init__(self):
        self._formatters = {
            ReportFormat.JSON: self._format_json,
            ReportFormat.HTML: self._format_html,
            ReportFormat.XML: self._format_xml,
            ReportFormat.TEXT: self._format_text,
            ReportFormat.MARKDOWN: self._format_markdown
        }

    def generate(
        self,
        results: TestResults,
        format: ReportFormat = ReportFormat.JSON,
        title: str = "Test Report"
    ) -> TestReport:
        """Generate a test report."""
        metrics = self._calculate_metrics(results)
        content = self._format_report(results, metrics, format)

        return TestReport(
            title=title,
            timestamp=datetime.utcnow().isoformat(),
            results=results,
            metrics=metrics,
            format=format,
            content=content
        )

    def _calculate_metrics(self, results: TestResults) -> TestMetrics:
        """Calculate metrics from test results."""
        tests_by_status: Dict[str, int] = {}
        tests_by_module: Dict[str, int] = {}

        for tc in results.test_cases:
            status = tc.status.value
            tests_by_status[status] = tests_by_status.get(status, 0) + 1

            module = tc.module.split('.')[0] if tc.module else 'unknown'
            tests_by_module[module] = tests_by_module.get(module, 0) + 1

        avg_duration = results.duration_seconds / results.total if results.total > 0 else 0

        return TestMetrics(
            total_tests=results.total,
            passed_tests=results.passed,
            failed_tests=results.failed,
            skipped_tests=results.skipped,
            error_tests=results.errors,
            pass_rate=results.pass_rate,
            total_duration=results.duration_seconds,
            avg_duration=avg_duration,
            coverage_percent=results.coverage_percent,
            tests_by_status=tests_by_status,
            tests_by_module=tests_by_module
        )

    def _format_report(
        self,
        results: TestResults,
        metrics: TestMetrics,
        format: ReportFormat
    ) -> str:
        """Format report content."""
        formatter = self._formatters.get(format, self._format_json)
        return formatter(results, metrics)

    def _format_json(
        self,
        results: TestResults,
        metrics: TestMetrics
    ) -> str:
        """Format as JSON."""
        report_data = {
            'summary': {
                'total': results.total,
                'passed': results.passed,
                'failed': results.failed,
                'skipped': results.skipped,
                'errors': results.errors,
                'pass_rate': results.pass_rate,
                'duration': results.duration_seconds,
                'coverage': results.coverage_percent
            },
            'metrics': metrics.to_dict(),
            'test_cases': [tc.to_dict() for tc in results.test_cases],
            'timestamp': results.timestamp
        }
        return json.dumps(report_data, indent=2)

    def _format_html(
        self,
        results: TestResults,
        metrics: TestMetrics
    ) -> str:
        """Format as HTML."""
        status_color = "green" if results.pass_rate >= 80 else "orange" if results.pass_rate >= 60 else "red"

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .summary {{ background: #f5f5f5; padding: 20px; border-radius: 8px; }}
        .pass-rate {{ font-size: 2em; color: {status_color}; }}
        table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #4CAF50; color: white; }}
        .passed {{ color: green; }}
        .failed {{ color: red; }}
        .skipped {{ color: orange; }}
    </style>
</head>
<body>
    <h1>Test Report</h1>
    <div class="summary">
        <p class="pass-rate">{results.pass_rate:.1f}% Pass Rate</p>
        <p>Total: {results.total} | Passed: {results.passed} | Failed: {results.failed} | Skipped: {results.skipped}</p>
        <p>Duration: {results.duration_seconds:.2f}s | Coverage: {results.coverage_percent:.1f}%</p>
    </div>

    <h2>Test Results</h2>
    <table>
        <tr>
            <th>Test</th>
            <th>Module</th>
            <th>Status</th>
            <th>Duration</th>
        </tr>
"""
        for tc in results.test_cases:
            status_class = tc.status.value
            html += f"""        <tr>
            <td>{tc.name}</td>
            <td>{tc.module}</td>
            <td class="{status_class}">{tc.status.value.upper()}</td>
            <td>{tc.duration_seconds:.3f}s</td>
        </tr>
"""

        html += """    </table>
</body>
</html>"""
        return html

    def _format_xml(
        self,
        results: TestResults,
        metrics: TestMetrics
    ) -> str:
        """Format as JUnit XML."""
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<testsuites tests="{results.total}" failures="{results.failed}" errors="{results.errors}" time="{results.duration_seconds}">
    <testsuite name="test_suite" tests="{results.total}" failures="{results.failed}" errors="{results.errors}" time="{results.duration_seconds}">
"""
        for tc in results.test_cases:
            xml += f'        <testcase name="{tc.name}" classname="{tc.module}" time="{tc.duration_seconds}"'
            if tc.status == TestStatus.FAILED:
                xml += f'>\n            <failure message="{tc.error_message or "Test failed"}"></failure>\n        </testcase>\n'
            elif tc.status == TestStatus.SKIPPED:
                xml += '>\n            <skipped/>\n        </testcase>\n'
            elif tc.status == TestStatus.ERROR:
                xml += f'>\n            <error message="{tc.error_message or "Test error"}"></error>\n        </testcase>\n'
            else:
                xml += '/>\n'

        xml += """    </testsuite>
</testsuites>"""
        return xml

    def _format_text(
        self,
        results: TestResults,
        metrics: TestMetrics
    ) -> str:
        """Format as plain text."""
        text = f"""
============================================================
TEST REPORT
============================================================
Timestamp: {results.timestamp}

SUMMARY
-------
Total:    {results.total}
Passed:   {results.passed}
Failed:   {results.failed}
Skipped:  {results.skipped}
Errors:   {results.errors}

Pass Rate: {results.pass_rate:.1f}%
Duration:  {results.duration_seconds:.2f}s
Coverage:  {results.coverage_percent:.1f}%

TEST RESULTS
------------
"""
        for tc in results.test_cases:
            status = tc.status.value.upper()
            text += f"[{status}] {tc.name} ({tc.module})\n"
            if tc.error_message:
                text += f"         Error: {tc.error_message}\n"

        text += "\n============================================================\n"
        return text

    def _format_markdown(
        self,
        results: TestResults,
        metrics: TestMetrics
    ) -> str:
        """Format as Markdown."""
        md = f"""# Test Report

**Timestamp:** {results.timestamp}

## Summary

| Metric | Value |
|--------|-------|
| Total | {results.total} |
| Passed | {results.passed} |
| Failed | {results.failed} |
| Skipped | {results.skipped} |
| Pass Rate | {results.pass_rate:.1f}% |
| Duration | {results.duration_seconds:.2f}s |
| Coverage | {results.coverage_percent:.1f}% |

## Test Results

| Test | Module | Status | Duration |
|------|--------|--------|----------|
"""
        for tc in results.test_cases:
            md += f"| {tc.name} | {tc.module} | {tc.status.value} | {tc.duration_seconds:.3f}s |\n"

        return md

    def send_to_quality_fabric(
        self,
        report: TestReport,
        qf_url: str = "http://localhost:8000"
    ) -> Dict[str, Any]:
        """
        Send report to Quality Fabric.

        AC-5: Quality Fabric integration.
        """
        import requests

        try:
            response = requests.post(
                f"{qf_url}/api/v1/reports/test-results",
                json=report.to_dict(),
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"status": "error", "code": response.status_code}

        except Exception as e:
            logger.error(f"Failed to send report to Quality Fabric: {e}")
            return {"status": "error", "message": str(e)}


def get_test_reporter() -> TestReporter:
    """Factory function to create TestReporter instance."""
    return TestReporter()
