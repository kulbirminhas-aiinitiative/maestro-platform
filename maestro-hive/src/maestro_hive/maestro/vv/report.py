"""
Validation Report Builder for Verification & Validation.

EPIC: MD-2521 - [SDLC-Phase7] Verification & Validation
AC-4: Validation Report Builder - Comprehensive V&V reports with traceability matrix

This module provides:
- Traceability matrix generation
- Coverage analysis (requirements to tests)
- Gap identification
- Executive summary with metrics
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class CoverageStatus(Enum):
    """Status of requirement coverage."""
    FULLY_COVERED = "fully_covered"
    PARTIALLY_COVERED = "partially_covered"
    NOT_COVERED = "not_covered"
    NOT_APPLICABLE = "not_applicable"


class ValidationStatus(Enum):
    """Overall validation status."""
    PASSED = "passed"
    FAILED = "failed"
    INCOMPLETE = "incomplete"
    NOT_RUN = "not_run"


@dataclass
class Requirement:
    """A requirement to be validated."""
    requirement_id: str
    title: str
    description: str
    priority: str  # P1, P2, P3, etc.
    source: str  # Where it came from
    acceptance_criteria: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "requirement_id": self.requirement_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority,
            "source": self.source,
            "acceptance_criteria": self.acceptance_criteria,
            "metadata": self.metadata
        }


@dataclass
class TestCase:
    """A test case that validates requirements."""
    test_id: str
    name: str
    description: str
    test_type: str  # unit, integration, e2e, etc.
    requirements_covered: List[str]  # Requirement IDs
    status: ValidationStatus = ValidationStatus.NOT_RUN
    result: Optional[str] = None
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "test_id": self.test_id,
            "name": self.name,
            "description": self.description,
            "test_type": self.test_type,
            "requirements_covered": self.requirements_covered,
            "status": self.status.value,
            "result": self.result,
            "duration_ms": self.duration_ms,
            "metadata": self.metadata
        }


@dataclass
class TraceabilityLink:
    """A link between requirement and test."""
    requirement_id: str
    test_id: str
    link_type: str  # verifies, validates, covers
    status: CoverageStatus

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "requirement_id": self.requirement_id,
            "test_id": self.test_id,
            "link_type": self.link_type,
            "status": self.status.value
        }


@dataclass
class CoverageGap:
    """An identified coverage gap."""
    gap_id: str
    requirement_id: str
    gap_type: str  # no_tests, partial_coverage, failed_tests
    description: str
    severity: str  # critical, high, medium, low
    recommendation: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "gap_id": self.gap_id,
            "requirement_id": self.requirement_id,
            "gap_type": self.gap_type,
            "description": self.description,
            "severity": self.severity,
            "recommendation": self.recommendation
        }


@dataclass
class TraceabilityMatrix:
    """
    Requirements to tests traceability matrix.

    Maps each requirement to its associated tests and coverage status.
    """
    requirements: List[Requirement]
    tests: List[TestCase]
    links: List[TraceabilityLink]
    generated_at: datetime = field(default_factory=datetime.utcnow)

    def get_requirement_coverage(self, requirement_id: str) -> CoverageStatus:
        """Get coverage status for a requirement."""
        related_links = [l for l in self.links if l.requirement_id == requirement_id]

        if not related_links:
            return CoverageStatus.NOT_COVERED

        all_covered = all(l.status == CoverageStatus.FULLY_COVERED for l in related_links)
        any_covered = any(l.status in [CoverageStatus.FULLY_COVERED, CoverageStatus.PARTIALLY_COVERED]
                         for l in related_links)

        if all_covered:
            return CoverageStatus.FULLY_COVERED
        elif any_covered:
            return CoverageStatus.PARTIALLY_COVERED
        else:
            return CoverageStatus.NOT_COVERED

    def get_tests_for_requirement(self, requirement_id: str) -> List[TestCase]:
        """Get all tests covering a requirement."""
        test_ids = {l.test_id for l in self.links if l.requirement_id == requirement_id}
        return [t for t in self.tests if t.test_id in test_ids]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "requirements": [r.to_dict() for r in self.requirements],
            "tests": [t.to_dict() for t in self.tests],
            "links": [l.to_dict() for l in self.links],
            "generated_at": self.generated_at.isoformat()
        }


@dataclass
class ValidationReport:
    """Comprehensive V&V report."""
    report_id: str
    project_name: str
    version: str
    matrix: TraceabilityMatrix
    gaps: List[CoverageGap]
    generated_at: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def total_requirements(self) -> int:
        """Total number of requirements."""
        return len(self.matrix.requirements)

    @property
    def total_tests(self) -> int:
        """Total number of tests."""
        return len(self.matrix.tests)

    @property
    def passed_tests(self) -> int:
        """Number of passed tests."""
        return sum(1 for t in self.matrix.tests if t.status == ValidationStatus.PASSED)

    @property
    def failed_tests(self) -> int:
        """Number of failed tests."""
        return sum(1 for t in self.matrix.tests if t.status == ValidationStatus.FAILED)

    @property
    def coverage_rate(self) -> float:
        """Requirements coverage rate (0.0 to 1.0)."""
        if not self.matrix.requirements:
            return 1.0

        covered = sum(
            1 for r in self.matrix.requirements
            if self.matrix.get_requirement_coverage(r.requirement_id)
            in [CoverageStatus.FULLY_COVERED, CoverageStatus.PARTIALLY_COVERED]
        )
        return covered / len(self.matrix.requirements)

    @property
    def test_pass_rate(self) -> float:
        """Test pass rate (0.0 to 1.0)."""
        run_tests = [t for t in self.matrix.tests if t.status != ValidationStatus.NOT_RUN]
        if not run_tests:
            return 0.0
        return self.passed_tests / len(run_tests)

    @property
    def overall_status(self) -> ValidationStatus:
        """Overall validation status."""
        if self.failed_tests > 0:
            return ValidationStatus.FAILED
        if any(t.status == ValidationStatus.INCOMPLETE for t in self.matrix.tests):
            return ValidationStatus.INCOMPLETE
        if all(t.status == ValidationStatus.PASSED for t in self.matrix.tests):
            return ValidationStatus.PASSED
        return ValidationStatus.NOT_RUN

    def get_executive_summary(self) -> Dict[str, Any]:
        """Generate executive summary."""
        return {
            "report_id": self.report_id,
            "project": self.project_name,
            "version": self.version,
            "generated_at": self.generated_at.isoformat(),
            "overall_status": self.overall_status.value,
            "metrics": {
                "requirements": {
                    "total": self.total_requirements,
                    "coverage_rate": f"{self.coverage_rate:.1%}"
                },
                "tests": {
                    "total": self.total_tests,
                    "passed": self.passed_tests,
                    "failed": self.failed_tests,
                    "pass_rate": f"{self.test_pass_rate:.1%}"
                },
                "gaps": {
                    "total": len(self.gaps),
                    "critical": sum(1 for g in self.gaps if g.severity == "critical"),
                    "high": sum(1 for g in self.gaps if g.severity == "high")
                }
            },
            "recommendation": self._generate_recommendation()
        }

    def _generate_recommendation(self) -> str:
        """Generate a recommendation based on results."""
        if self.overall_status == ValidationStatus.PASSED and self.coverage_rate >= 0.9:
            return "Ready for release - all validations passed with excellent coverage"
        elif self.overall_status == ValidationStatus.PASSED:
            return "Consider adding more test coverage before release"
        elif self.failed_tests > 0:
            return f"Fix {self.failed_tests} failing test(s) before proceeding"
        else:
            return "Complete test execution before making release decisions"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "project_name": self.project_name,
            "version": self.version,
            "executive_summary": self.get_executive_summary(),
            "matrix": self.matrix.to_dict(),
            "gaps": [g.to_dict() for g in self.gaps],
            "generated_at": self.generated_at.isoformat(),
            "metadata": self.metadata
        }


class ReportBuilder:
    """
    Builder for V&V reports.

    Collects requirements and tests, generates traceability,
    identifies gaps, and produces comprehensive reports.
    """

    def __init__(self, project_name: str, version: str):
        """
        Initialize the report builder.

        Args:
            project_name: Name of the project
            version: Version being validated
        """
        self._project_name = project_name
        self._version = version
        self._requirements: Dict[str, Requirement] = {}
        self._tests: Dict[str, TestCase] = {}
        self._links: List[TraceabilityLink] = []
        logger.info(f"ReportBuilder initialized for {project_name} v{version}")

    def add_requirement(self, requirement: Requirement) -> "ReportBuilder":
        """Add a requirement."""
        self._requirements[requirement.requirement_id] = requirement
        return self

    def add_test(self, test: TestCase) -> "ReportBuilder":
        """Add a test case."""
        self._tests[test.test_id] = test

        # Create links for covered requirements
        for req_id in test.requirements_covered:
            status = CoverageStatus.NOT_COVERED
            if test.status == ValidationStatus.PASSED:
                status = CoverageStatus.FULLY_COVERED
            elif test.status == ValidationStatus.FAILED:
                status = CoverageStatus.NOT_COVERED
            elif test.status == ValidationStatus.INCOMPLETE:
                status = CoverageStatus.PARTIALLY_COVERED

            self._links.append(TraceabilityLink(
                requirement_id=req_id,
                test_id=test.test_id,
                link_type="verifies",
                status=status
            ))

        return self

    def link_requirement_to_test(
        self,
        requirement_id: str,
        test_id: str,
        link_type: str = "verifies"
    ) -> "ReportBuilder":
        """Manually link a requirement to a test."""
        test = self._tests.get(test_id)
        status = CoverageStatus.NOT_COVERED

        if test and test.status == ValidationStatus.PASSED:
            status = CoverageStatus.FULLY_COVERED
        elif test and test.status == ValidationStatus.INCOMPLETE:
            status = CoverageStatus.PARTIALLY_COVERED

        self._links.append(TraceabilityLink(
            requirement_id=requirement_id,
            test_id=test_id,
            link_type=link_type,
            status=status
        ))
        return self

    def identify_gaps(self) -> List[CoverageGap]:
        """Identify coverage gaps."""
        gaps = []
        gap_counter = 0

        # Check each requirement
        covered_reqs: Set[str] = {l.requirement_id for l in self._links}

        for req_id, req in self._requirements.items():
            if req_id not in covered_reqs:
                gap_counter += 1
                gaps.append(CoverageGap(
                    gap_id=f"GAP-{gap_counter:03d}",
                    requirement_id=req_id,
                    gap_type="no_tests",
                    description=f"No tests cover requirement: {req.title}",
                    severity="high" if req.priority == "P1" else "medium",
                    recommendation=f"Create tests to validate: {req.title}"
                ))
            else:
                # Check if any covering tests failed
                related_tests = [
                    self._tests[l.test_id]
                    for l in self._links
                    if l.requirement_id == req_id and l.test_id in self._tests
                ]
                failed_tests = [t for t in related_tests if t.status == ValidationStatus.FAILED]

                if failed_tests:
                    gap_counter += 1
                    gaps.append(CoverageGap(
                        gap_id=f"GAP-{gap_counter:03d}",
                        requirement_id=req_id,
                        gap_type="failed_tests",
                        description=f"Tests for {req.title} are failing",
                        severity="critical" if req.priority == "P1" else "high",
                        recommendation=f"Fix failing tests: {', '.join(t.name for t in failed_tests)}"
                    ))

        return gaps

    def build(self) -> ValidationReport:
        """Build the validation report."""
        matrix = TraceabilityMatrix(
            requirements=list(self._requirements.values()),
            tests=list(self._tests.values()),
            links=self._links
        )

        gaps = self.identify_gaps()

        report = ValidationReport(
            report_id=f"VVR-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            project_name=self._project_name,
            version=self._version,
            matrix=matrix,
            gaps=gaps
        )

        logger.info(f"Built validation report: {report.report_id}")
        return report

    def export_json(self, report: ValidationReport) -> str:
        """Export report to JSON."""
        return json.dumps(report.to_dict(), indent=2)

    def export_markdown(self, report: ValidationReport) -> str:
        """Export report to Markdown."""
        summary = report.get_executive_summary()

        md = f"""# Validation Report: {report.project_name} v{report.version}

**Report ID:** {report.report_id}
**Generated:** {report.generated_at.isoformat()}
**Status:** {summary["overall_status"].upper()}

## Executive Summary

| Metric | Value |
|--------|-------|
| Requirements | {summary["metrics"]["requirements"]["total"]} |
| Coverage Rate | {summary["metrics"]["requirements"]["coverage_rate"]} |
| Total Tests | {summary["metrics"]["tests"]["total"]} |
| Passed Tests | {summary["metrics"]["tests"]["passed"]} |
| Failed Tests | {summary["metrics"]["tests"]["failed"]} |
| Pass Rate | {summary["metrics"]["tests"]["pass_rate"]} |

### Recommendation
{summary["recommendation"]}

## Coverage Gaps

"""
        if report.gaps:
            md += "| Gap ID | Requirement | Type | Severity | Recommendation |\n"
            md += "|--------|-------------|------|----------|----------------|\n"
            for gap in report.gaps:
                md += f"| {gap.gap_id} | {gap.requirement_id} | {gap.gap_type} | {gap.severity} | {gap.recommendation} |\n"
        else:
            md += "No coverage gaps identified.\n"

        md += "\n## Traceability Matrix\n\n"
        md += "| Requirement | Tests | Status |\n"
        md += "|-------------|-------|--------|\n"

        for req in report.matrix.requirements:
            tests = report.matrix.get_tests_for_requirement(req.requirement_id)
            test_names = ", ".join(t.name for t in tests) if tests else "None"
            coverage = report.matrix.get_requirement_coverage(req.requirement_id)
            md += f"| {req.requirement_id} | {test_names} | {coverage.value} |\n"

        return md
