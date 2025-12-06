"""
Tests for Journey Coverage Tracker (MD-2099)

Validates:
- Journey and step definitions
- Coverage calculation
- Dependency tracking
- Release enforcement
- Report generation
"""

import pytest
import tempfile
import json
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from bdv.journey_coverage import (
    JourneyCoverageTracker,
    CriticalJourney,
    JourneyStep,
    JourneyStatus,
    JourneySeverity,
    StepCoverage,
    JourneyCoverageResult,
    CoverageReport,
    CoverageGapError,
    get_standard_journeys
)


class TestJourneyStep:
    """Tests for JourneyStep dataclass"""

    def test_creation(self):
        """Test JourneyStep creation"""
        step = JourneyStep(
            id="step-1",
            name="Test Step",
            description="A test step"
        )
        assert step.id == "step-1"
        assert step.name == "Test Step"
        assert step.required is True  # default

    def test_optional_step(self):
        """Test optional step"""
        step = JourneyStep(
            id="step-1",
            name="Optional Step",
            required=False
        )
        assert step.required is False

    def test_matches_feature_no_pattern(self):
        """Test feature matching without pattern"""
        step = JourneyStep(id="step-1", name="Step")
        assert step.matches_feature("any_file.feature") is True

    def test_matches_feature_with_pattern(self):
        """Test feature matching with pattern"""
        step = JourneyStep(
            id="step-1",
            name="Auth Step",
            feature_pattern=r"auth.*login"
        )
        assert step.matches_feature("auth_login.feature") is True
        assert step.matches_feature("AUTH_LOGIN.feature") is True  # case insensitive
        assert step.matches_feature("user_profile.feature") is False

    def test_matches_scenario_no_pattern(self):
        """Test scenario matching without pattern"""
        step = JourneyStep(id="step-1", name="Step")
        assert step.matches_scenario("Any Scenario") is True

    def test_matches_scenario_with_pattern(self):
        """Test scenario matching with pattern"""
        step = JourneyStep(
            id="step-1",
            name="Login Step",
            scenario_pattern=r"user.*login|sign.?in"
        )
        assert step.matches_scenario("User can login") is True
        assert step.matches_scenario("Sign in successfully") is True
        assert step.matches_scenario("User can logout") is False

    def test_to_dict(self):
        """Test conversion to dictionary"""
        step = JourneyStep(
            id="step-1",
            name="Step",
            contract_id="auth-api"
        )
        d = step.to_dict()
        assert d['id'] == "step-1"
        assert d['contract_id'] == "auth-api"


class TestCriticalJourney:
    """Tests for CriticalJourney dataclass"""

    def test_creation(self):
        """Test CriticalJourney creation"""
        journey = CriticalJourney(
            id="journey-1",
            name="Test Journey",
            steps=[
                JourneyStep(id="s1", name="Step 1"),
                JourneyStep(id="s2", name="Step 2")
            ]
        )
        assert journey.id == "journey-1"
        assert journey.step_count == 2

    def test_required_step_count(self):
        """Test required step count calculation"""
        journey = CriticalJourney(
            id="journey-1",
            name="Test",
            steps=[
                JourneyStep(id="s1", name="Required", required=True),
                JourneyStep(id="s2", name="Optional", required=False),
                JourneyStep(id="s3", name="Required 2", required=True)
            ]
        )
        assert journey.step_count == 3
        assert journey.required_step_count == 2

    def test_get_step(self):
        """Test getting step by ID"""
        journey = CriticalJourney(
            id="journey-1",
            name="Test",
            steps=[
                JourneyStep(id="s1", name="Step 1"),
                JourneyStep(id="s2", name="Step 2")
            ]
        )
        assert journey.get_step("s1").name == "Step 1"
        assert journey.get_step("nonexistent") is None

    def test_severity_default(self):
        """Test default severity"""
        journey = CriticalJourney(id="j1", name="J", steps=[])
        assert journey.severity == JourneySeverity.HIGH

    def test_to_dict(self):
        """Test conversion to dictionary"""
        journey = CriticalJourney(
            id="journey-1",
            name="Test Journey",
            severity=JourneySeverity.CRITICAL,
            steps=[JourneyStep(id="s1", name="Step 1")]
        )
        d = journey.to_dict()
        assert d['id'] == "journey-1"
        assert d['severity'] == "critical"
        assert d['step_count'] == 1


class TestStepCoverage:
    """Tests for StepCoverage dataclass"""

    def test_covered_status(self):
        """Test covered status"""
        coverage = StepCoverage(
            step_id="s1",
            step_name="Step",
            is_covered=True,
            test_count=2,
            passed_count=2,
            failed_count=0
        )
        assert coverage.status == JourneyStatus.COVERED

    def test_partial_status(self):
        """Test partial status (has tests but failing)"""
        coverage = StepCoverage(
            step_id="s1",
            step_name="Step",
            is_covered=False,
            test_count=2,
            passed_count=0,
            failed_count=2
        )
        assert coverage.status == JourneyStatus.PARTIAL

    def test_uncovered_status(self):
        """Test uncovered status"""
        coverage = StepCoverage(
            step_id="s1",
            step_name="Step",
            is_covered=False,
            test_count=0
        )
        assert coverage.status == JourneyStatus.UNCOVERED

    def test_blocked_status(self):
        """Test blocked status"""
        coverage = StepCoverage(
            step_id="s1",
            step_name="Step",
            is_covered=False,
            dependencies_met=False,
            blocked_by=["dep-1"]
        )
        assert coverage.status == JourneyStatus.BLOCKED

    def test_pass_rate(self):
        """Test pass rate calculation"""
        coverage = StepCoverage(
            step_id="s1",
            step_name="Step",
            is_covered=True,
            test_count=4,
            passed_count=3,
            failed_count=1
        )
        assert coverage.pass_rate == 0.75

    def test_pass_rate_no_tests(self):
        """Test pass rate with no tests"""
        coverage = StepCoverage(
            step_id="s1",
            step_name="Step",
            is_covered=False,
            test_count=0
        )
        assert coverage.pass_rate == 0.0


class TestJourneyCoverageResult:
    """Tests for JourneyCoverageResult dataclass"""

    def test_coverage_rate(self):
        """Test coverage rate calculation"""
        result = JourneyCoverageResult(
            journey_id="j1",
            journey_name="Journey",
            severity=JourneySeverity.HIGH,
            step_coverage=[],
            total_steps=10,
            covered_steps=7,
            required_steps=8,
            required_covered=6
        )
        assert result.coverage_rate == 0.7

    def test_required_coverage_rate(self):
        """Test required coverage rate"""
        result = JourneyCoverageResult(
            journey_id="j1",
            journey_name="Journey",
            severity=JourneySeverity.HIGH,
            step_coverage=[],
            total_steps=10,
            covered_steps=5,
            required_steps=5,
            required_covered=4
        )
        assert result.required_coverage_rate == 0.8

    def test_is_fully_covered_true(self):
        """Test fully covered journey"""
        result = JourneyCoverageResult(
            journey_id="j1",
            journey_name="Journey",
            severity=JourneySeverity.HIGH,
            step_coverage=[],
            total_steps=5,
            covered_steps=5,
            required_steps=3,
            required_covered=3
        )
        assert result.is_fully_covered is True

    def test_is_fully_covered_false(self):
        """Test not fully covered journey"""
        result = JourneyCoverageResult(
            journey_id="j1",
            journey_name="Journey",
            severity=JourneySeverity.HIGH,
            step_coverage=[],
            total_steps=5,
            covered_steps=4,
            required_steps=3,
            required_covered=2
        )
        assert result.is_fully_covered is False


class TestCoverageReport:
    """Tests for CoverageReport dataclass"""

    def test_overall_coverage(self):
        """Test overall coverage calculation"""
        report = CoverageReport(
            journeys=[
                JourneyCoverageResult("j1", "J1", JourneySeverity.HIGH, [], 10, 8, 10, 8),
                JourneyCoverageResult("j2", "J2", JourneySeverity.MEDIUM, [], 10, 6, 10, 6)
            ]
        )
        assert report.overall_coverage == 0.7  # 14/20

    def test_critical_coverage(self):
        """Test critical journey coverage"""
        report = CoverageReport(
            journeys=[
                JourneyCoverageResult("j1", "J1", JourneySeverity.CRITICAL, [], 10, 10, 5, 5),
                JourneyCoverageResult("j2", "J2", JourneySeverity.HIGH, [], 10, 5, 10, 5)
            ]
        )
        assert report.critical_coverage == 1.0  # Only counts critical: 5/5

    def test_fully_covered_journeys(self):
        """Test fully covered journey count"""
        report = CoverageReport(
            journeys=[
                JourneyCoverageResult("j1", "J1", JourneySeverity.HIGH, [], 5, 5, 5, 5),
                JourneyCoverageResult("j2", "J2", JourneySeverity.HIGH, [], 5, 3, 5, 3)
            ]
        )
        assert report.fully_covered_journeys == 1


class TestJourneyCoverageTracker:
    """Tests for JourneyCoverageTracker class"""

    def test_initialization(self):
        """Test tracker initialization"""
        tracker = JourneyCoverageTracker()
        assert len(tracker.journeys) == 0
        assert tracker.enforce_for_release is True

    def test_add_journey(self):
        """Test adding a journey"""
        tracker = JourneyCoverageTracker()
        journey = CriticalJourney(
            id="j1",
            name="Journey 1",
            steps=[JourneyStep(id="s1", name="Step 1")]
        )
        tracker.add_journey(journey)
        assert "j1" in tracker.journeys

    def test_remove_journey(self):
        """Test removing a journey"""
        tracker = JourneyCoverageTracker()
        journey = CriticalJourney(id="j1", name="J1", steps=[])
        tracker.add_journey(journey)
        assert tracker.remove_journey("j1") is True
        assert "j1" not in tracker.journeys
        assert tracker.remove_journey("nonexistent") is False

    def test_get_journey(self):
        """Test getting a journey"""
        tracker = JourneyCoverageTracker()
        journey = CriticalJourney(id="j1", name="J1", steps=[])
        tracker.add_journey(journey)
        assert tracker.get_journey("j1") is not None
        assert tracker.get_journey("nonexistent") is None

    def test_load_save_journeys(self):
        """Test loading and saving journeys"""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = f"{tmpdir}/journeys.json"

            # Create and save
            tracker1 = JourneyCoverageTracker()
            journey = CriticalJourney(
                id="j1",
                name="Journey 1",
                steps=[JourneyStep(id="s1", name="Step 1")]
            )
            tracker1.add_journey(journey)
            tracker1.save_journeys(filepath)

            # Load in new tracker
            tracker2 = JourneyCoverageTracker(journeys_file=filepath)
            assert "j1" in tracker2.journeys
            assert tracker2.journeys["j1"].step_count == 1

    def test_calculate_step_coverage_by_pattern(self):
        """Test step coverage calculation by pattern matching"""
        tracker = JourneyCoverageTracker()

        step = JourneyStep(
            id="auth-login",
            name="Login",
            feature_pattern=r"auth",
            scenario_pattern=r"login"
        )

        test_results = [
            {'feature_file': 'auth/login.feature', 'scenario_name': 'User can login', 'status': 'passed'},
            {'feature_file': 'auth/login.feature', 'scenario_name': 'Login fails invalid', 'status': 'passed'},
            {'feature_file': 'user/profile.feature', 'scenario_name': 'View profile', 'status': 'passed'}
        ]

        coverage = tracker.calculate_step_coverage(step, test_results, set())

        assert coverage.is_covered is True
        assert coverage.test_count == 2
        assert coverage.passed_count == 2

    def test_calculate_step_coverage_by_contract(self):
        """Test step coverage calculation by contract ID"""
        tracker = JourneyCoverageTracker()

        step = JourneyStep(
            id="auth-login",
            name="Login",
            contract_id="auth-api-v1"
        )

        test_results = [
            {'feature_file': 'any.feature', 'scenario_name': 'Any', 'status': 'passed', 'contract_id': 'auth-api-v1'},
            {'feature_file': 'other.feature', 'scenario_name': 'Other', 'status': 'passed', 'contract_id': 'other-api'}
        ]

        coverage = tracker.calculate_step_coverage(step, test_results, set())

        assert coverage.is_covered is True
        assert coverage.test_count == 1

    def test_calculate_step_coverage_with_failures(self):
        """Test step coverage with failing tests"""
        tracker = JourneyCoverageTracker()

        step = JourneyStep(
            id="s1",
            name="Step",
            feature_pattern=r"test"
        )

        test_results = [
            {'feature_file': 'test.feature', 'scenario_name': 'Test 1', 'status': 'passed'},
            {'feature_file': 'test.feature', 'scenario_name': 'Test 2', 'status': 'failed'}
        ]

        coverage = tracker.calculate_step_coverage(step, test_results, set())

        assert coverage.test_count == 2
        assert coverage.passed_count == 1
        assert coverage.failed_count == 1

    def test_calculate_step_coverage_dependencies_not_met(self):
        """Test step coverage with unmet dependencies"""
        tracker = JourneyCoverageTracker()

        step = JourneyStep(
            id="s2",
            name="Step 2",
            depends_on=["s1"]
        )

        coverage = tracker.calculate_step_coverage(step, [], set())

        assert coverage.dependencies_met is False
        assert "s1" in coverage.blocked_by

    def test_calculate_journey_coverage(self):
        """Test journey coverage calculation"""
        tracker = JourneyCoverageTracker()

        journey = CriticalJourney(
            id="auth",
            name="Auth Flow",
            steps=[
                JourneyStep(id="login", name="Login", feature_pattern=r"login"),
                JourneyStep(id="logout", name="Logout", feature_pattern=r"logout", depends_on=["login"])
            ]
        )
        tracker.add_journey(journey)

        test_results = [
            {'feature_file': 'login.feature', 'scenario_name': 'Login', 'status': 'passed'},
            {'feature_file': 'logout.feature', 'scenario_name': 'Logout', 'status': 'passed'}
        ]

        result = tracker.calculate_journey_coverage(journey, test_results)

        assert result.is_fully_covered is True
        assert result.covered_steps == 2

    def test_calculate_coverage_all_journeys(self):
        """Test coverage calculation for all journeys"""
        tracker = JourneyCoverageTracker()

        tracker.add_journey(CriticalJourney(
            id="j1",
            name="Journey 1",
            severity=JourneySeverity.CRITICAL,
            steps=[JourneyStep(id="s1", name="Step 1", feature_pattern=r"test1")]
        ))
        tracker.add_journey(CriticalJourney(
            id="j2",
            name="Journey 2",
            severity=JourneySeverity.HIGH,
            steps=[JourneyStep(id="s2", name="Step 2", feature_pattern=r"test2")]
        ))

        test_results = [
            {'feature_file': 'test1.feature', 'scenario_name': 'Test', 'status': 'passed'},
            {'feature_file': 'test2.feature', 'scenario_name': 'Test', 'status': 'passed'}
        ]

        report = tracker.calculate_coverage(test_results, "iter-001")

        assert report.total_journeys == 2
        assert report.fully_covered_journeys == 2
        assert report.is_release_ready is True

    def test_calculate_coverage_with_gaps(self):
        """Test coverage with blocking gaps"""
        tracker = JourneyCoverageTracker()

        tracker.add_journey(CriticalJourney(
            id="j1",
            name="Critical Journey",
            severity=JourneySeverity.CRITICAL,
            steps=[
                JourneyStep(id="s1", name="Step 1", feature_pattern=r"step1"),
                JourneyStep(id="s2", name="Step 2", feature_pattern=r"step2")
            ]
        ))

        test_results = [
            {'feature_file': 'step1.feature', 'scenario_name': 'Test', 'status': 'passed'}
            # step2 is not covered
        ]

        report = tracker.calculate_coverage(test_results)

        assert report.is_release_ready is False
        assert len(report.blocking_gaps) == 1
        assert report.blocking_gaps[0]['step_id'] == "s2"

    def test_enforce_coverage_success(self):
        """Test enforce coverage - success case"""
        tracker = JourneyCoverageTracker()

        tracker.add_journey(CriticalJourney(
            id="j1",
            name="Journey",
            severity=JourneySeverity.CRITICAL,
            steps=[JourneyStep(id="s1", name="Step", feature_pattern=r"test")]
        ))

        test_results = [
            {'feature_file': 'test.feature', 'scenario_name': 'Test', 'status': 'passed'}
        ]

        is_ready, report = tracker.enforce_coverage(test_results)

        assert is_ready is True
        assert report.is_release_ready is True

    def test_enforce_coverage_failure_raises(self):
        """Test enforce coverage - raises on failure"""
        tracker = JourneyCoverageTracker()

        tracker.add_journey(CriticalJourney(
            id="j1",
            name="Journey",
            severity=JourneySeverity.CRITICAL,
            steps=[JourneyStep(id="s1", name="Step", feature_pattern=r"test")]
        ))

        test_results = []  # No tests

        with pytest.raises(CoverageGapError):
            tracker.enforce_coverage(test_results, raise_on_failure=True)

    def test_enforce_coverage_failure_no_raise(self):
        """Test enforce coverage - no raise option"""
        tracker = JourneyCoverageTracker()

        tracker.add_journey(CriticalJourney(
            id="j1",
            name="Journey",
            severity=JourneySeverity.CRITICAL,
            steps=[JourneyStep(id="s1", name="Step", feature_pattern=r"test")]
        ))

        test_results = []

        is_ready, report = tracker.enforce_coverage(test_results, raise_on_failure=False)

        assert is_ready is False

    def test_enforce_disabled(self):
        """Test with enforcement disabled"""
        tracker = JourneyCoverageTracker(enforce_for_release=False)

        tracker.add_journey(CriticalJourney(
            id="j1",
            name="Journey",
            severity=JourneySeverity.CRITICAL,
            steps=[JourneyStep(id="s1", name="Step", feature_pattern=r"test")]
        ))

        test_results = []  # No coverage

        is_ready, report = tracker.enforce_coverage(test_results)

        assert is_ready is True  # Enforcement disabled

    def test_min_coverage_thresholds(self):
        """Test minimum coverage thresholds"""
        tracker = JourneyCoverageTracker(
            min_critical_coverage=0.8,
            min_overall_coverage=0.5
        )

        tracker.add_journey(CriticalJourney(
            id="j1",
            name="Critical",
            severity=JourneySeverity.CRITICAL,
            steps=[
                JourneyStep(id="s1", name="Step 1", feature_pattern=r"test1"),
                JourneyStep(id="s2", name="Step 2", feature_pattern=r"test2", required=False)
            ]
        ))

        test_results = [
            {'feature_file': 'test1.feature', 'scenario_name': 'Test', 'status': 'passed'}
        ]

        report = tracker.calculate_coverage(test_results)

        # Required coverage is 100% (1/1), which meets 80% threshold
        assert report.is_release_ready is True


class TestReportGeneration:
    """Tests for report generation"""

    def test_generate_text_report(self):
        """Test text report generation"""
        tracker = JourneyCoverageTracker()

        tracker.add_journey(CriticalJourney(
            id="j1",
            name="Test Journey",
            severity=JourneySeverity.HIGH,
            steps=[JourneyStep(id="s1", name="Step 1")]
        ))

        report = tracker.calculate_coverage([])
        text = tracker.generate_report(report, "text")

        assert "JOURNEY COVERAGE REPORT" in text
        assert "Test Journey" in text

    def test_generate_json_report(self):
        """Test JSON report generation"""
        tracker = JourneyCoverageTracker()

        tracker.add_journey(CriticalJourney(
            id="j1",
            name="Test Journey",
            steps=[JourneyStep(id="s1", name="Step 1")]
        ))

        report = tracker.calculate_coverage([])
        json_str = tracker.generate_report(report, "json")

        data = json.loads(json_str)
        assert "journeys" in data
        assert data['total_journeys'] == 1

    def test_generate_markdown_report(self):
        """Test markdown report generation"""
        tracker = JourneyCoverageTracker()

        tracker.add_journey(CriticalJourney(
            id="j1",
            name="Test Journey",
            steps=[JourneyStep(id="s1", name="Step 1")]
        ))

        report = tracker.calculate_coverage([])
        md = tracker.generate_report(report, "markdown")

        assert "# Journey Coverage Report" in md
        assert "## Coverage Summary" in md
        assert "Test Journey" in md


class TestStandardJourneys:
    """Tests for predefined standard journeys"""

    def test_get_standard_journeys(self):
        """Test getting standard journeys"""
        journeys = get_standard_journeys()

        assert len(journeys) >= 3
        journey_ids = [j.id for j in journeys]
        assert "auth-flow" in journey_ids
        assert "workflow-execution" in journey_ids

    def test_standard_journey_structure(self):
        """Test standard journey structure"""
        journeys = get_standard_journeys()
        auth_journey = next(j for j in journeys if j.id == "auth-flow")

        assert auth_journey.severity == JourneySeverity.CRITICAL
        assert auth_journey.step_count >= 3
        assert auth_journey.get_step("auth-login") is not None


class TestJourneyStatus:
    """Tests for JourneyStatus enum"""

    def test_status_values(self):
        """Test status enum values"""
        assert JourneyStatus.COVERED.value == "covered"
        assert JourneyStatus.PARTIAL.value == "partial"
        assert JourneyStatus.UNCOVERED.value == "uncovered"
        assert JourneyStatus.BLOCKED.value == "blocked"


class TestJourneySeverity:
    """Tests for JourneySeverity enum"""

    def test_severity_values(self):
        """Test severity enum values"""
        assert JourneySeverity.CRITICAL.value == "critical"
        assert JourneySeverity.HIGH.value == "high"
        assert JourneySeverity.MEDIUM.value == "medium"
        assert JourneySeverity.LOW.value == "low"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
