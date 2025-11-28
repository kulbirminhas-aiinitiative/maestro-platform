"""
Quality-Fabric Integration for MAESTRO Templates Testing
Provides advanced test metrics, tracking, and reporting integration
"""

import asyncio
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import pytest

logger = logging.getLogger(__name__)


@dataclass
class TestMetrics:
    """Test execution metrics"""
    test_name: str
    test_file: str
    test_class: Optional[str]
    status: str  # passed, failed, skipped, error
    duration_ms: float
    timestamp: str
    markers: List[str]
    coverage_percentage: float = 0.0
    assertions_count: int = 0
    error_message: Optional[str] = None
    error_traceback: Optional[str] = None


@dataclass
class TestSuiteMetrics:
    """Test suite aggregated metrics"""
    suite_name: str
    total_tests: int
    passed: int
    failed: int
    skipped: int
    errors: int
    total_duration_ms: float
    average_duration_ms: float
    coverage_percentage: float
    timestamp: str
    test_metrics: List[TestMetrics]


class QualityFabricReporter:
    """
    Quality-Fabric reporter for test metrics
    Collects, aggregates, and exports test quality metrics
    """

    def __init__(self):
        self.test_metrics: List[TestMetrics] = []
        self.suite_start_time: Optional[datetime] = None
        self.output_dir = "test_reports/quality_fabric"
        os.makedirs(self.output_dir, exist_ok=True)

    def pytest_sessionstart(self, session):
        """Called at start of test session"""
        self.suite_start_time = datetime.utcnow()
        logger.info("Quality-Fabric test tracking started")

    def pytest_runtest_logreport(self, report):
        """Called for each test phase (setup, call, teardown)"""
        if report.when == "call":  # Only track the actual test execution
            markers = [marker.name for marker in report.keywords.get("pytestmark", [])]

            test_metric = TestMetrics(
                test_name=report.nodeid.split("::")[-1],
                test_file=report.nodeid.split("::")[0],
                test_class=report.nodeid.split("::")[1] if "::" in report.nodeid and len(
                    report.nodeid.split("::")) > 2 else None,
                status=report.outcome,
                duration_ms=report.duration * 1000,
                timestamp=datetime.utcnow().isoformat(),
                markers=markers,
                error_message=str(report.longrepr) if report.failed else None,
                error_traceback=str(report.longreprtext) if report.failed else None
            )

            self.test_metrics.append(test_metric)

    def pytest_sessionfinish(self, session, exitstatus):
        """Called at end of test session"""
        if not self.suite_start_time:
            return

        # Calculate aggregated metrics
        suite_duration = (datetime.utcnow() - self.suite_start_time).total_seconds() * 1000

        suite_metrics = TestSuiteMetrics(
            suite_name="maestro_templates_comprehensive_tests",
            total_tests=len(self.test_metrics),
            passed=sum(1 for m in self.test_metrics if m.status == "passed"),
            failed=sum(1 for m in self.test_metrics if m.status == "failed"),
            skipped=sum(1 for m in self.test_metrics if m.status == "skipped"),
            errors=sum(1 for m in self.test_metrics if m.status == "error"),
            total_duration_ms=suite_duration,
            average_duration_ms=suite_duration / len(self.test_metrics) if self.test_metrics else 0,
            coverage_percentage=0.0,  # Will be calculated from coverage report
            timestamp=datetime.utcnow().isoformat(),
            test_metrics=self.test_metrics
        )

        # Export metrics
        self._export_json_report(suite_metrics)
        self._export_summary_report(suite_metrics)
        self._export_detailed_report(suite_metrics)

        logger.info(f"Quality-Fabric tracking complete: {suite_metrics.passed}/{suite_metrics.total_tests} passed")

    def _export_json_report(self, suite_metrics: TestSuiteMetrics):
        """Export metrics as JSON"""
        output_file = os.path.join(self.output_dir, f"metrics_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json")

        metrics_dict = {
            "suite": {
                "name": suite_metrics.suite_name,
                "total_tests": suite_metrics.total_tests,
                "passed": suite_metrics.passed,
                "failed": suite_metrics.failed,
                "skipped": suite_metrics.skipped,
                "errors": suite_metrics.errors,
                "duration_ms": suite_metrics.total_duration_ms,
                "coverage": suite_metrics.coverage_percentage,
                "timestamp": suite_metrics.timestamp
            },
            "tests": [asdict(m) for m in suite_metrics.test_metrics]
        }

        with open(output_file, 'w') as f:
            json.dump(metrics_dict, f, indent=2)

        logger.info(f"JSON metrics exported to {output_file}")

    def _export_summary_report(self, suite_metrics: TestSuiteMetrics):
        """Export summary report as markdown"""
        output_file = os.path.join(self.output_dir, "summary.md")

        pass_rate = (suite_metrics.passed / suite_metrics.total_tests * 100) if suite_metrics.total_tests > 0 else 0

        summary = f"""# MAESTRO Templates - Test Quality Report

## Summary

- **Total Tests**: {suite_metrics.total_tests}
- **Passed**: {suite_metrics.passed} ({pass_rate:.1f}%)
- **Failed**: {suite_metrics.failed}
- **Skipped**: {suite_metrics.skipped}
- **Errors**: {suite_metrics.errors}
- **Total Duration**: {suite_metrics.total_duration_ms / 1000:.2f}s
- **Average Duration**: {suite_metrics.average_duration_ms:.2f}ms
- **Timestamp**: {suite_metrics.timestamp}

## Test Categories

"""

        # Group by markers
        marker_stats = {}
        for metric in suite_metrics.test_metrics:
            for marker in metric.markers:
                if marker not in marker_stats:
                    marker_stats[marker] = {"passed": 0, "failed": 0, "total": 0}
                marker_stats[marker]["total"] += 1
                if metric.status == "passed":
                    marker_stats[marker]["passed"] += 1
                elif metric.status == "failed":
                    marker_stats[marker]["failed"] += 1

        for marker, stats in sorted(marker_stats.items()):
            marker_pass_rate = (stats["passed"] / stats["total"] * 100) if stats["total"] > 0 else 0
            summary += f"- **{marker}**: {stats['passed']}/{stats['total']} ({marker_pass_rate:.1f}%)\n"

        summary += "\n## Failed Tests\n\n"

        failed_tests = [m for m in suite_metrics.test_metrics if m.status == "failed"]
        if failed_tests:
            for test in failed_tests:
                summary += f"- `{test.test_name}` ({test.test_file})\n"
                if test.error_message:
                    summary += f"  - Error: {test.error_message[:200]}\n"
        else:
            summary += "No failed tests!\n"

        with open(output_file, 'w') as f:
            f.write(summary)

        logger.info(f"Summary report exported to {output_file}")

    def _export_detailed_report(self, suite_metrics: TestSuiteMetrics):
        """Export detailed report with all test metrics"""
        output_file = os.path.join(self.output_dir, "detailed_report.md")

        report = f"""# MAESTRO Templates - Detailed Test Report

**Generated**: {suite_metrics.timestamp}
**Total Tests**: {suite_metrics.total_tests}
**Pass Rate**: {(suite_metrics.passed / suite_metrics.total_tests * 100):.1f}%

---

## Test Results by Category

"""

        # Group tests by file
        tests_by_file = {}
        for metric in suite_metrics.test_metrics:
            if metric.test_file not in tests_by_file:
                tests_by_file[metric.test_file] = []
            tests_by_file[metric.test_file].append(metric)

        for test_file, tests in sorted(tests_by_file.items()):
            file_passed = sum(1 for t in tests if t.status == "passed")
            file_total = len(tests)
            file_pass_rate = (file_passed / file_total * 100) if file_total > 0 else 0

            report += f"\n### {test_file}\n\n"
            report += f"**Tests**: {file_total} | **Passed**: {file_passed} ({file_pass_rate:.1f}%)\n\n"

            for test in tests:
                status_emoji = "✅" if test.status == "passed" else "❌" if test.status == "failed" else "⏭️"
                report += f"{status_emoji} **{test.test_name}** - {test.duration_ms:.2f}ms\n"

                if test.status == "failed" and test.error_message:
                    report += f"```\n{test.error_message[:500]}\n```\n"

                report += "\n"

        with open(output_file, 'w') as f:
            f.write(report)

        logger.info(f"Detailed report exported to {output_file}")


class QualityFabricIntegration:
    """
    Main integration class for quality-fabric
    Provides utilities for test quality tracking
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.enabled = os.getenv("QUALITY_FABRIC_ENABLED", "true").lower() == "true"
        self.metrics_buffer = []

    async def track_test_metric(
        self,
        test_name: str,
        status: str,
        duration_ms: float,
        coverage: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Track individual test metric"""
        metric = {
            "test_name": test_name,
            "status": status,
            "duration_ms": duration_ms,
            "coverage": coverage,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }

        self.metrics_buffer.append(metric)

        if self.enabled:
            await self._publish_to_redis(metric)

        logger.debug(f"Test metric tracked: {test_name} - {status}")

    async def _publish_to_redis(self, metric: Dict[str, Any]):
        """Publish metric to Redis Stream (if available)"""
        try:
            # This would integrate with actual quality-fabric Redis stream
            # For now, just log
            logger.debug(f"Would publish to Redis: {metric}")
        except Exception as e:
            logger.warning(f"Failed to publish to Redis: {e}")

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of collected metrics"""
        if not self.metrics_buffer:
            return {"total": 0, "passed": 0, "failed": 0}

        return {
            "total": len(self.metrics_buffer),
            "passed": sum(1 for m in self.metrics_buffer if m["status"] == "passed"),
            "failed": sum(1 for m in self.metrics_buffer if m["status"] == "failed"),
            "skipped": sum(1 for m in self.metrics_buffer if m["status"] == "skipped"),
            "average_duration_ms": sum(m["duration_ms"] for m in self.metrics_buffer) / len(self.metrics_buffer),
            "total_duration_ms": sum(m["duration_ms"] for m in self.metrics_buffer)
        }


# Pytest plugin registration
def pytest_configure(config):
    """Register Quality-Fabric reporter as pytest plugin"""
    if config.option.verbose > 0:
        reporter = QualityFabricReporter()
        config.pluginmanager.register(reporter, "quality_fabric_reporter")


# Global integration instance
_quality_fabric = None


def get_quality_fabric() -> QualityFabricIntegration:
    """Get global Quality-Fabric integration instance"""
    global _quality_fabric
    if _quality_fabric is None:
        _quality_fabric = QualityFabricIntegration()
    return _quality_fabric
