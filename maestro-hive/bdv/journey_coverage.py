"""
Journey Coverage Tracker (MD-2099)

Tracks critical user journey coverage for BDV test suites.
Ensures 100% coverage of defined critical paths before releases.

A "critical journey" is a user flow that must be validated before
any release (e.g., login -> browse -> purchase -> logout).
"""

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any, Callable

logger = logging.getLogger(__name__)


class JourneyStatus(Enum):
    """Status of journey coverage"""
    COVERED = "covered"  # All steps have passing tests
    PARTIAL = "partial"  # Some steps covered
    UNCOVERED = "uncovered"  # No coverage
    BLOCKED = "blocked"  # Dependencies not met


class JourneySeverity(Enum):
    """Severity level for journey coverage gaps"""
    CRITICAL = "critical"  # Must block release
    HIGH = "high"  # Should block, with override
    MEDIUM = "medium"  # Warning only
    LOW = "low"  # Informational


@dataclass
class JourneyStep:
    """
    A single step within a critical journey.

    Attributes:
        id: Unique step identifier
        name: Human-readable step name
        description: Detailed description
        contract_id: Associated contract ID (optional)
        feature_pattern: Regex pattern for matching feature files
        scenario_pattern: Regex pattern for matching scenario names
        depends_on: List of step IDs this step depends on
        required: Whether this step must be covered
    """
    id: str
    name: str
    description: str = ""
    contract_id: Optional[str] = None
    feature_pattern: Optional[str] = None
    scenario_pattern: Optional[str] = None
    depends_on: List[str] = field(default_factory=list)
    required: bool = True

    def matches_feature(self, feature_file: str) -> bool:
        """Check if a feature file matches this step's pattern"""
        if not self.feature_pattern:
            return True
        return bool(re.search(self.feature_pattern, feature_file, re.IGNORECASE))

    def matches_scenario(self, scenario_name: str) -> bool:
        """Check if a scenario name matches this step's pattern"""
        if not self.scenario_pattern:
            return True
        return bool(re.search(self.scenario_pattern, scenario_name, re.IGNORECASE))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'contract_id': self.contract_id,
            'feature_pattern': self.feature_pattern,
            'scenario_pattern': self.scenario_pattern,
            'depends_on': self.depends_on,
            'required': self.required
        }


@dataclass
class CriticalJourney:
    """
    Defines a critical user journey with multiple steps.

    Attributes:
        id: Unique journey identifier
        name: Human-readable journey name
        description: Detailed journey description
        steps: Ordered list of journey steps
        severity: How critical this journey is
        owner: Team/person responsible
        tags: Optional tags for filtering
    """
    id: str
    name: str
    steps: List[JourneyStep]
    description: str = ""
    severity: JourneySeverity = JourneySeverity.HIGH
    owner: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    @property
    def step_count(self) -> int:
        """Number of steps in this journey"""
        return len(self.steps)

    @property
    def required_step_count(self) -> int:
        """Number of required steps"""
        return len([s for s in self.steps if s.required])

    def get_step(self, step_id: str) -> Optional[JourneyStep]:
        """Get step by ID"""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'steps': [s.to_dict() for s in self.steps],
            'severity': self.severity.value,
            'owner': self.owner,
            'tags': self.tags,
            'step_count': self.step_count,
            'required_step_count': self.required_step_count
        }


@dataclass
class StepCoverage:
    """Coverage details for a single step"""
    step_id: str
    step_name: str
    is_covered: bool
    test_count: int = 0
    passed_count: int = 0
    failed_count: int = 0
    matching_tests: List[str] = field(default_factory=list)
    dependencies_met: bool = True
    blocked_by: List[str] = field(default_factory=list)

    @property
    def status(self) -> JourneyStatus:
        """Get coverage status"""
        if not self.dependencies_met:
            return JourneyStatus.BLOCKED
        if self.is_covered and self.failed_count == 0:
            return JourneyStatus.COVERED
        if self.test_count > 0:
            return JourneyStatus.PARTIAL
        return JourneyStatus.UNCOVERED

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate"""
        if self.test_count == 0:
            return 0.0
        return self.passed_count / self.test_count

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'step_id': self.step_id,
            'step_name': self.step_name,
            'is_covered': self.is_covered,
            'status': self.status.value,
            'test_count': self.test_count,
            'passed_count': self.passed_count,
            'failed_count': self.failed_count,
            'pass_rate': self.pass_rate,
            'matching_tests': self.matching_tests,
            'dependencies_met': self.dependencies_met,
            'blocked_by': self.blocked_by
        }


@dataclass
class JourneyCoverageResult:
    """Coverage result for a single journey"""
    journey_id: str
    journey_name: str
    severity: JourneySeverity
    step_coverage: List[StepCoverage]
    total_steps: int
    covered_steps: int
    required_steps: int
    required_covered: int

    @property
    def coverage_rate(self) -> float:
        """Overall coverage percentage"""
        if self.total_steps == 0:
            return 0.0
        return self.covered_steps / self.total_steps

    @property
    def required_coverage_rate(self) -> float:
        """Required steps coverage percentage"""
        if self.required_steps == 0:
            return 1.0  # No required steps = fully covered
        return self.required_covered / self.required_steps

    @property
    def is_fully_covered(self) -> bool:
        """Check if all required steps are covered"""
        return self.required_covered == self.required_steps

    @property
    def status(self) -> JourneyStatus:
        """Overall journey status"""
        if self.is_fully_covered:
            return JourneyStatus.COVERED
        if self.covered_steps > 0:
            return JourneyStatus.PARTIAL
        return JourneyStatus.UNCOVERED

    @property
    def uncovered_steps(self) -> List[StepCoverage]:
        """Get list of uncovered steps"""
        return [s for s in self.step_coverage if not s.is_covered]

    @property
    def failing_steps(self) -> List[StepCoverage]:
        """Get list of steps with failing tests"""
        return [s for s in self.step_coverage if s.failed_count > 0]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'journey_id': self.journey_id,
            'journey_name': self.journey_name,
            'severity': self.severity.value,
            'status': self.status.value,
            'coverage_rate': self.coverage_rate,
            'required_coverage_rate': self.required_coverage_rate,
            'is_fully_covered': self.is_fully_covered,
            'total_steps': self.total_steps,
            'covered_steps': self.covered_steps,
            'required_steps': self.required_steps,
            'required_covered': self.required_covered,
            'step_coverage': [s.to_dict() for s in self.step_coverage],
            'uncovered_step_count': len(self.uncovered_steps),
            'failing_step_count': len(self.failing_steps)
        }


@dataclass
class CoverageReport:
    """Complete coverage report for all journeys"""
    journeys: List[JourneyCoverageResult]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    iteration_id: Optional[str] = None
    is_release_ready: bool = False
    blocking_gaps: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def total_journeys(self) -> int:
        """Total number of journeys"""
        return len(self.journeys)

    @property
    def fully_covered_journeys(self) -> int:
        """Number of fully covered journeys"""
        return len([j for j in self.journeys if j.is_fully_covered])

    @property
    def overall_coverage(self) -> float:
        """Overall coverage across all journeys"""
        if not self.journeys:
            return 0.0
        total = sum(j.total_steps for j in self.journeys)
        covered = sum(j.covered_steps for j in self.journeys)
        return covered / total if total > 0 else 0.0

    @property
    def critical_coverage(self) -> float:
        """Coverage for critical journeys only"""
        critical = [j for j in self.journeys if j.severity == JourneySeverity.CRITICAL]
        if not critical:
            return 1.0
        total = sum(j.required_steps for j in critical)
        covered = sum(j.required_covered for j in critical)
        return covered / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'iteration_id': self.iteration_id,
            'is_release_ready': self.is_release_ready,
            'overall_coverage': self.overall_coverage,
            'critical_coverage': self.critical_coverage,
            'total_journeys': self.total_journeys,
            'fully_covered_journeys': self.fully_covered_journeys,
            'journeys': [j.to_dict() for j in self.journeys],
            'blocking_gaps': self.blocking_gaps
        }


class JourneyCoverageTracker:
    """
    Tracks critical journey coverage for BDV test suites.

    Features:
    - Define critical user journeys with multiple steps
    - Map test scenarios to journey steps
    - Calculate coverage percentages
    - Enforce 100% coverage for releases
    - Generate coverage reports
    """

    def __init__(
        self,
        journeys_file: Optional[str] = None,
        enforce_for_release: bool = True,
        min_critical_coverage: float = 1.0,
        min_overall_coverage: float = 0.8
    ):
        """
        Initialize the coverage tracker.

        Args:
            journeys_file: Path to JSON file with journey definitions
            enforce_for_release: Whether to enforce 100% critical coverage
            min_critical_coverage: Minimum coverage for critical journeys (0-1)
            min_overall_coverage: Minimum overall coverage (0-1)
        """
        self.journeys: Dict[str, CriticalJourney] = {}
        self.enforce_for_release = enforce_for_release
        self.min_critical_coverage = min_critical_coverage
        self.min_overall_coverage = min_overall_coverage

        # Load journeys from file if provided
        if journeys_file and Path(journeys_file).exists():
            self.load_journeys(journeys_file)

        logger.info(
            f"JourneyCoverageTracker initialized with {len(self.journeys)} journeys"
        )

    def add_journey(self, journey: CriticalJourney) -> None:
        """Add a critical journey"""
        self.journeys[journey.id] = journey
        logger.debug(f"Added journey: {journey.id} ({journey.step_count} steps)")

    def remove_journey(self, journey_id: str) -> bool:
        """Remove a journey by ID"""
        if journey_id in self.journeys:
            del self.journeys[journey_id]
            return True
        return False

    def get_journey(self, journey_id: str) -> Optional[CriticalJourney]:
        """Get journey by ID"""
        return self.journeys.get(journey_id)

    def load_journeys(self, filepath: str) -> int:
        """
        Load journeys from a JSON file.

        Args:
            filepath: Path to JSON file

        Returns:
            Number of journeys loaded
        """
        with open(filepath) as f:
            data = json.load(f)

        count = 0
        for j in data.get('journeys', []):
            steps = [
                JourneyStep(
                    id=s['id'],
                    name=s['name'],
                    description=s.get('description', ''),
                    contract_id=s.get('contract_id'),
                    feature_pattern=s.get('feature_pattern'),
                    scenario_pattern=s.get('scenario_pattern'),
                    depends_on=s.get('depends_on', []),
                    required=s.get('required', True)
                )
                for s in j.get('steps', [])
            ]

            journey = CriticalJourney(
                id=j['id'],
                name=j['name'],
                description=j.get('description', ''),
                steps=steps,
                severity=JourneySeverity(j.get('severity', 'high')),
                owner=j.get('owner'),
                tags=j.get('tags', [])
            )

            self.add_journey(journey)
            count += 1

        logger.info(f"Loaded {count} journeys from {filepath}")
        return count

    def save_journeys(self, filepath: str) -> None:
        """Save journeys to a JSON file"""
        data = {
            'journeys': [j.to_dict() for j in self.journeys.values()]
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(self.journeys)} journeys to {filepath}")

    def calculate_step_coverage(
        self,
        step: JourneyStep,
        test_results: List[Dict[str, Any]],
        covered_steps: Set[str]
    ) -> StepCoverage:
        """
        Calculate coverage for a single step.

        Args:
            step: The journey step to evaluate
            test_results: List of test result dictionaries
            covered_steps: Set of step IDs already covered

        Returns:
            StepCoverage object
        """
        # Check dependencies
        blocked_by = []
        for dep_id in step.depends_on:
            if dep_id not in covered_steps:
                blocked_by.append(dep_id)

        dependencies_met = len(blocked_by) == 0

        # Find matching tests
        matching_tests = []
        passed_count = 0
        failed_count = 0

        for result in test_results:
            feature = result.get('feature_file', '')
            scenario = result.get('scenario_name', '')
            status = result.get('status', '')
            contract = result.get('contract_id', '')

            # Match by contract ID first (most specific) - if contract_id is defined,
            # only match by contract and skip pattern matching
            if step.contract_id:
                if contract == step.contract_id:
                    matching_tests.append(f"{feature}::{scenario}")
                    if status == 'passed':
                        passed_count += 1
                    elif status == 'failed':
                        failed_count += 1
                continue  # Skip pattern matching when contract_id is defined

            # Match by feature and scenario patterns (only when no contract_id)
            if step.matches_feature(feature) and step.matches_scenario(scenario):
                matching_tests.append(f"{feature}::{scenario}")
                if status == 'passed':
                    passed_count += 1
                elif status == 'failed':
                    failed_count += 1

        is_covered = passed_count > 0

        return StepCoverage(
            step_id=step.id,
            step_name=step.name,
            is_covered=is_covered,
            test_count=len(matching_tests),
            passed_count=passed_count,
            failed_count=failed_count,
            matching_tests=matching_tests,
            dependencies_met=dependencies_met,
            blocked_by=blocked_by
        )

    def calculate_journey_coverage(
        self,
        journey: CriticalJourney,
        test_results: List[Dict[str, Any]]
    ) -> JourneyCoverageResult:
        """
        Calculate coverage for a single journey.

        Args:
            journey: The journey to evaluate
            test_results: List of test result dictionaries

        Returns:
            JourneyCoverageResult object
        """
        step_coverage: List[StepCoverage] = []
        covered_steps: Set[str] = set()

        # Process steps in order (for dependency tracking)
        for step in journey.steps:
            coverage = self.calculate_step_coverage(step, test_results, covered_steps)
            step_coverage.append(coverage)

            if coverage.is_covered:
                covered_steps.add(step.id)

        # Calculate totals
        covered = len([s for s in step_coverage if s.is_covered])
        required = len([s for s in journey.steps if s.required])
        required_covered = len([
            s for s in step_coverage
            if s.is_covered and journey.get_step(s.step_id).required
        ])

        return JourneyCoverageResult(
            journey_id=journey.id,
            journey_name=journey.name,
            severity=journey.severity,
            step_coverage=step_coverage,
            total_steps=len(journey.steps),
            covered_steps=covered,
            required_steps=required,
            required_covered=required_covered
        )

    def calculate_coverage(
        self,
        test_results: List[Dict[str, Any]],
        iteration_id: Optional[str] = None
    ) -> CoverageReport:
        """
        Calculate coverage for all journeys.

        Args:
            test_results: List of test result dictionaries with keys:
                - feature_file: Path to feature file
                - scenario_name: Name of scenario
                - status: Test status (passed/failed/skipped)
                - contract_id: Optional contract ID
            iteration_id: Optional iteration identifier

        Returns:
            CoverageReport with all journey coverage details
        """
        journey_results: List[JourneyCoverageResult] = []
        blocking_gaps: List[Dict[str, Any]] = []

        for journey in self.journeys.values():
            result = self.calculate_journey_coverage(journey, test_results)
            journey_results.append(result)

            # Track blocking gaps
            if not result.is_fully_covered:
                if journey.severity in (JourneySeverity.CRITICAL, JourneySeverity.HIGH):
                    for step in result.uncovered_steps:
                        if journey.get_step(step.step_id).required:
                            blocking_gaps.append({
                                'journey_id': journey.id,
                                'journey_name': journey.name,
                                'severity': journey.severity.value,
                                'step_id': step.step_id,
                                'step_name': step.step_name,
                                'reason': 'uncovered' if step.test_count == 0 else 'failing'
                            })

        # Determine release readiness
        is_release_ready = self._check_release_ready(journey_results)

        return CoverageReport(
            journeys=journey_results,
            iteration_id=iteration_id,
            is_release_ready=is_release_ready,
            blocking_gaps=blocking_gaps
        )

    def _check_release_ready(
        self,
        journey_results: List[JourneyCoverageResult]
    ) -> bool:
        """Check if coverage meets release criteria"""
        if not self.enforce_for_release:
            return True

        # Check critical journeys (must be 100%)
        critical = [j for j in journey_results if j.severity == JourneySeverity.CRITICAL]
        for j in critical:
            if j.required_coverage_rate < self.min_critical_coverage:
                return False

        # Check overall coverage
        if journey_results:
            total = sum(j.total_steps for j in journey_results)
            covered = sum(j.covered_steps for j in journey_results)
            overall = covered / total if total > 0 else 0
            if overall < self.min_overall_coverage:
                return False

        return True

    def enforce_coverage(
        self,
        test_results: List[Dict[str, Any]],
        iteration_id: Optional[str] = None,
        raise_on_failure: bool = True
    ) -> Tuple[bool, CoverageReport]:
        """
        Enforce coverage requirements.

        Args:
            test_results: List of test result dictionaries
            iteration_id: Optional iteration identifier
            raise_on_failure: Whether to raise exception on failure

        Returns:
            Tuple of (is_ready, report)

        Raises:
            CoverageGapError: If coverage requirements not met and raise_on_failure=True
        """
        report = self.calculate_coverage(test_results, iteration_id)

        if not report.is_release_ready and raise_on_failure:
            gaps = report.blocking_gaps
            gap_summary = "; ".join([
                f"{g['journey_name']}/{g['step_name']} ({g['reason']})"
                for g in gaps[:5]  # Limit to first 5
            ])
            raise CoverageGapError(
                f"Coverage requirements not met. {len(gaps)} blocking gaps: {gap_summary}"
            )

        return report.is_release_ready, report

    def generate_report(
        self,
        report: CoverageReport,
        output_format: str = "text"
    ) -> str:
        """
        Generate a human-readable coverage report.

        Args:
            report: Coverage report to format
            output_format: Output format (text, json, markdown)

        Returns:
            Formatted report string
        """
        if output_format == "json":
            return json.dumps(report.to_dict(), indent=2)

        if output_format == "markdown":
            return self._generate_markdown_report(report)

        return self._generate_text_report(report)

    def _generate_text_report(self, report: CoverageReport) -> str:
        """Generate text format report"""
        lines = [
            "=" * 60,
            "JOURNEY COVERAGE REPORT",
            "=" * 60,
            f"Timestamp: {report.timestamp.isoformat()}",
            f"Iteration: {report.iteration_id or 'N/A'}",
            f"Release Ready: {'YES' if report.is_release_ready else 'NO'}",
            f"Overall Coverage: {report.overall_coverage:.1%}",
            f"Critical Coverage: {report.critical_coverage:.1%}",
            "",
            "-" * 60,
            "JOURNEY SUMMARY",
            "-" * 60
        ]

        for j in report.journeys:
            status_icon = "✓" if j.is_fully_covered else "✗"
            lines.append(
                f"[{status_icon}] {j.journey_name} ({j.severity.value}): "
                f"{j.covered_steps}/{j.total_steps} steps "
                f"({j.coverage_rate:.0%})"
            )

            if not j.is_fully_covered:
                for step in j.uncovered_steps:
                    lines.append(f"    - Missing: {step.step_name}")

        if report.blocking_gaps:
            lines.extend([
                "",
                "-" * 60,
                f"BLOCKING GAPS ({len(report.blocking_gaps)})",
                "-" * 60
            ])
            for gap in report.blocking_gaps:
                lines.append(
                    f"  • [{gap['severity']}] {gap['journey_name']} / "
                    f"{gap['step_name']} - {gap['reason']}"
                )

        lines.append("=" * 60)
        return "\n".join(lines)

    def _generate_markdown_report(self, report: CoverageReport) -> str:
        """Generate markdown format report"""
        lines = [
            "# Journey Coverage Report",
            "",
            f"**Timestamp:** {report.timestamp.isoformat()}  ",
            f"**Iteration:** {report.iteration_id or 'N/A'}  ",
            f"**Release Ready:** {'✅ YES' if report.is_release_ready else '❌ NO'}  ",
            "",
            "## Coverage Summary",
            "",
            f"| Metric | Value |",
            f"|--------|-------|",
            f"| Overall Coverage | {report.overall_coverage:.1%} |",
            f"| Critical Coverage | {report.critical_coverage:.1%} |",
            f"| Total Journeys | {report.total_journeys} |",
            f"| Fully Covered | {report.fully_covered_journeys} |",
            "",
            "## Journey Details",
            ""
        ]

        for j in report.journeys:
            status = "✅" if j.is_fully_covered else "⚠️"
            lines.extend([
                f"### {status} {j.journey_name}",
                "",
                f"- **Severity:** {j.severity.value}",
                f"- **Coverage:** {j.covered_steps}/{j.total_steps} ({j.coverage_rate:.0%})",
                f"- **Status:** {j.status.value}",
                ""
            ])

            if j.step_coverage:
                lines.append("| Step | Status | Tests | Pass Rate |")
                lines.append("|------|--------|-------|-----------|")
                for step in j.step_coverage:
                    s_icon = "✅" if step.is_covered else "❌"
                    lines.append(
                        f"| {step.step_name} | {s_icon} {step.status.value} | "
                        f"{step.test_count} | {step.pass_rate:.0%} |"
                    )
                lines.append("")

        if report.blocking_gaps:
            lines.extend([
                "## Blocking Gaps",
                "",
                "| Journey | Step | Severity | Reason |",
                "|---------|------|----------|--------|"
            ])
            for gap in report.blocking_gaps:
                lines.append(
                    f"| {gap['journey_name']} | {gap['step_name']} | "
                    f"{gap['severity']} | {gap['reason']} |"
                )

        return "\n".join(lines)


class CoverageGapError(Exception):
    """Raised when coverage requirements are not met"""
    pass


# Predefined common journeys
def get_standard_journeys() -> List[CriticalJourney]:
    """
    Get a list of standard/common critical journeys.

    Returns:
        List of predefined CriticalJourney objects
    """
    return [
        CriticalJourney(
            id="auth-flow",
            name="Authentication Flow",
            description="User authentication and session management",
            severity=JourneySeverity.CRITICAL,
            steps=[
                JourneyStep(
                    id="auth-login",
                    name="User Login",
                    feature_pattern=r"auth.*login|login",
                    scenario_pattern=r"login|sign.?in",
                    required=True
                ),
                JourneyStep(
                    id="auth-session",
                    name="Session Validation",
                    feature_pattern=r"auth.*session|session",
                    scenario_pattern=r"session|token",
                    depends_on=["auth-login"],
                    required=True
                ),
                JourneyStep(
                    id="auth-logout",
                    name="User Logout",
                    feature_pattern=r"auth.*logout|logout",
                    scenario_pattern=r"logout|sign.?out",
                    depends_on=["auth-login"],
                    required=True
                )
            ]
        ),
        CriticalJourney(
            id="workflow-execution",
            name="Workflow Execution",
            description="Core workflow creation and execution",
            severity=JourneySeverity.CRITICAL,
            steps=[
                JourneyStep(
                    id="workflow-create",
                    name="Create Workflow",
                    feature_pattern=r"workflow.*create|create.*workflow",
                    scenario_pattern=r"create|new|build",
                    required=True
                ),
                JourneyStep(
                    id="workflow-validate",
                    name="Validate Workflow",
                    feature_pattern=r"workflow.*valid|valid.*workflow",
                    scenario_pattern=r"valid|check|verify",
                    depends_on=["workflow-create"],
                    required=True
                ),
                JourneyStep(
                    id="workflow-execute",
                    name="Execute Workflow",
                    feature_pattern=r"workflow.*exec|exec.*workflow|run",
                    scenario_pattern=r"exec|run|start",
                    depends_on=["workflow-validate"],
                    required=True
                ),
                JourneyStep(
                    id="workflow-results",
                    name="View Results",
                    feature_pattern=r"workflow.*result|result",
                    scenario_pattern=r"result|output|status",
                    depends_on=["workflow-execute"],
                    required=True
                )
            ]
        ),
        CriticalJourney(
            id="team-collaboration",
            name="Team Collaboration",
            description="Multi-agent team collaboration",
            severity=JourneySeverity.HIGH,
            steps=[
                JourneyStep(
                    id="team-setup",
                    name="Setup Team",
                    feature_pattern=r"team.*setup|setup.*team",
                    scenario_pattern=r"setup|configure|create",
                    required=True
                ),
                JourneyStep(
                    id="team-assign",
                    name="Assign Tasks",
                    feature_pattern=r"team.*assign|task.*assign",
                    scenario_pattern=r"assign|delegate|allocate",
                    depends_on=["team-setup"],
                    required=True
                ),
                JourneyStep(
                    id="team-collaborate",
                    name="Collaborate",
                    feature_pattern=r"team.*collab|collab",
                    scenario_pattern=r"collab|communicate|share",
                    depends_on=["team-assign"],
                    required=False
                )
            ]
        )
    ]


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Create tracker with standard journeys
    tracker = JourneyCoverageTracker()
    for journey in get_standard_journeys():
        tracker.add_journey(journey)

    # Sample test results
    test_results = [
        {'feature_file': 'auth/login.feature', 'scenario_name': 'User can login', 'status': 'passed'},
        {'feature_file': 'auth/session.feature', 'scenario_name': 'Session validated', 'status': 'passed'},
        {'feature_file': 'auth/logout.feature', 'scenario_name': 'User can logout', 'status': 'passed'},
        {'feature_file': 'workflow/create.feature', 'scenario_name': 'Create new workflow', 'status': 'passed'},
        {'feature_file': 'workflow/validate.feature', 'scenario_name': 'Validate workflow', 'status': 'failed'},
    ]

    # Calculate and print coverage
    report = tracker.calculate_coverage(test_results)
    print(tracker.generate_report(report))
