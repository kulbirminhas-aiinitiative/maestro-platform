"""
Tests for FlakeDetector (MD-2096)

Validates:
- Scenario run tracking
- Flake rate calculation
- Status classification
- Quarantine mechanism
- Report generation
"""

import pytest
import tempfile
from pathlib import Path
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from bdv.flake_detector import (
    FlakeDetector,
    FlakeStatus,
    FlakeAnalysis,
    FlakeReport,
    ScenarioRun
)


class TestScenarioRun:
    """Tests for ScenarioRun dataclass"""

    def test_creation(self):
        """Test ScenarioRun creation"""
        run = ScenarioRun(
            scenario_id="test-1",
            run_number=1,
            passed=True,
            duration=0.5
        )
        assert run.scenario_id == "test-1"
        assert run.run_number == 1
        assert run.passed is True
        assert run.duration == 0.5

    def test_failed_run(self):
        """Test failed scenario run"""
        run = ScenarioRun(
            scenario_id="test-1",
            run_number=1,
            passed=False,
            duration=0.3,
            error_message="Assertion failed"
        )
        assert run.passed is False
        assert run.error_message == "Assertion failed"

    def test_to_dict(self):
        """Test conversion to dictionary"""
        run = ScenarioRun(
            scenario_id="test-1",
            run_number=1,
            passed=True,
            duration=0.5
        )
        d = run.to_dict()
        assert d['scenario_id'] == "test-1"
        assert d['passed'] is True


class TestFlakeAnalysis:
    """Tests for FlakeAnalysis dataclass"""

    def test_creation(self):
        """Test FlakeAnalysis creation"""
        analysis = FlakeAnalysis(
            scenario_id="test-1",
            scenario_name="Test Scenario",
            feature_file="test.feature",
            total_runs=3,
            passed_runs=2,
            failed_runs=1,
            flake_rate=0.44,
            status=FlakeStatus.FLAKY,
            avg_duration=0.5
        )
        assert analysis.total_runs == 3
        assert analysis.status == FlakeStatus.FLAKY

    def test_pass_rate(self):
        """Test pass rate calculation"""
        analysis = FlakeAnalysis(
            scenario_id="test-1",
            scenario_name="Test",
            feature_file="test.feature",
            total_runs=4,
            passed_runs=3,
            failed_runs=1,
            flake_rate=0.0,
            status=FlakeStatus.STABLE,
            avg_duration=0.5
        )
        assert analysis.pass_rate == 0.75

    def test_to_dict(self):
        """Test conversion to dictionary"""
        analysis = FlakeAnalysis(
            scenario_id="test-1",
            scenario_name="Test",
            feature_file="test.feature",
            total_runs=3,
            passed_runs=3,
            failed_runs=0,
            flake_rate=0.0,
            status=FlakeStatus.STABLE,
            avg_duration=0.5
        )
        d = analysis.to_dict()
        assert d['status'] == 'stable'
        assert d['pass_rate'] == 1.0


class TestFlakeReport:
    """Tests for FlakeReport dataclass"""

    def test_creation(self):
        """Test FlakeReport creation"""
        analyses = [
            FlakeAnalysis(
                scenario_id="test-1",
                scenario_name="Stable",
                feature_file="test.feature",
                total_runs=3,
                passed_runs=3,
                failed_runs=0,
                flake_rate=0.0,
                status=FlakeStatus.STABLE,
                avg_duration=0.5
            ),
            FlakeAnalysis(
                scenario_id="test-2",
                scenario_name="Flaky",
                feature_file="test.feature",
                total_runs=3,
                passed_runs=2,
                failed_runs=1,
                flake_rate=0.44,
                status=FlakeStatus.FLAKY,
                avg_duration=0.5
            )
        ]

        report = FlakeReport(
            iteration_id="test-iter",
            total_scenarios=2,
            stable_count=1,
            flaky_count=1,
            failing_count=0,
            quarantined_count=0,
            overall_flake_rate=0.22,
            analyses=analyses,
            run_count=3
        )

        assert report.total_scenarios == 2
        assert report.stable_count == 1
        assert report.flaky_count == 1

    def test_flaky_scenarios_property(self):
        """Test flaky_scenarios property"""
        analyses = [
            FlakeAnalysis("s1", "S1", "f", 3, 3, 0, 0.0, FlakeStatus.STABLE, 0.5),
            FlakeAnalysis("s2", "S2", "f", 3, 2, 1, 0.44, FlakeStatus.FLAKY, 0.5),
        ]
        report = FlakeReport("iter", 2, 1, 1, 0, 0, 0.22, analyses, 3)

        flaky = report.flaky_scenarios
        assert len(flaky) == 1
        assert flaky[0].scenario_id == "s2"


class TestFlakeDetector:
    """Tests for FlakeDetector class"""

    def test_initialization_defaults(self):
        """Test default initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = FlakeDetector(
                quarantine_file=f"{tmpdir}/quarantine.json"
            )
            assert detector.run_count == 3
            assert detector.flake_threshold == 0.10
            assert detector.auto_quarantine is True

    def test_initialization_custom(self):
        """Test custom initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = FlakeDetector(
                run_count=5,
                flake_threshold=0.20,
                auto_quarantine=False,
                quarantine_file=f"{tmpdir}/quarantine.json"
            )
            assert detector.run_count == 5
            assert detector.flake_threshold == 0.20
            assert detector.auto_quarantine is False

    def test_quarantine(self):
        """Test quarantine mechanism"""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = FlakeDetector(
                quarantine_file=f"{tmpdir}/quarantine.json"
            )

            # Quarantine a scenario
            detector.quarantine("test-1", "Too flaky")

            assert detector.is_quarantined("test-1")
            assert not detector.is_quarantined("test-2")

    def test_unquarantine(self):
        """Test unquarantine"""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = FlakeDetector(
                quarantine_file=f"{tmpdir}/quarantine.json"
            )

            detector.quarantine("test-1", "Too flaky")
            detector.unquarantine("test-1")

            assert not detector.is_quarantined("test-1")

    def test_analyze_consistency_all_pass(self):
        """Test consistency analysis - all pass"""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = FlakeDetector(
                quarantine_file=f"{tmpdir}/quarantine.json"
            )

            results = [True, True, True]
            analysis = detector.analyze_consistency(results)

            assert analysis['passed'] == 3
            assert analysis['failed'] == 0
            assert analysis['pass_rate'] == 1.0
            assert analysis['flake_rate'] == 0.0
            assert analysis['is_flaky'] is False
            assert analysis['is_consistent'] is True

    def test_analyze_consistency_all_fail(self):
        """Test consistency analysis - all fail"""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = FlakeDetector(
                quarantine_file=f"{tmpdir}/quarantine.json"
            )

            results = [False, False, False]
            analysis = detector.analyze_consistency(results)

            assert analysis['passed'] == 0
            assert analysis['failed'] == 3
            assert analysis['flake_rate'] == 0.0
            assert analysis['is_consistent'] is True

    def test_analyze_consistency_mixed(self):
        """Test consistency analysis - mixed results"""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = FlakeDetector(
                flake_threshold=0.1,
                quarantine_file=f"{tmpdir}/quarantine.json"
            )

            results = [True, False, True]  # 2 pass, 1 fail
            analysis = detector.analyze_consistency(results)

            assert analysis['passed'] == 2
            assert analysis['failed'] == 1
            assert analysis['flake_rate'] > 0
            assert analysis['is_flaky'] is True

    def test_analyze_consistency_empty(self):
        """Test consistency analysis - empty"""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = FlakeDetector(
                quarantine_file=f"{tmpdir}/quarantine.json"
            )

            results = []
            analysis = detector.analyze_consistency(results)

            assert analysis['total_runs'] == 0
            assert analysis['is_consistent'] is True

    def test_classify_status_stable(self):
        """Test status classification - stable"""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = FlakeDetector(
                quarantine_file=f"{tmpdir}/quarantine.json"
            )

            status = detector._classify_status(3, 0, 0.0)
            assert status == FlakeStatus.STABLE

    def test_classify_status_consistently_failing(self):
        """Test status classification - consistently failing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = FlakeDetector(
                quarantine_file=f"{tmpdir}/quarantine.json"
            )

            status = detector._classify_status(0, 3, 0.0)
            assert status == FlakeStatus.CONSISTENTLY_FAILING

    def test_classify_status_flaky(self):
        """Test status classification - flaky"""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = FlakeDetector(
                quarantine_file=f"{tmpdir}/quarantine.json"
            )

            status = detector._classify_status(2, 1, 0.44)
            assert status == FlakeStatus.FLAKY

    def test_detect_flaky_tests_stable(self):
        """Test flake detection with stable test"""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = FlakeDetector(
                run_count=3,
                quarantine_file=f"{tmpdir}/quarantine.json"
            )

            # Runner that always passes
            def stable_runner(scenario):
                return True, 0.5, None

            scenarios = [
                {'id': 'stable-1', 'name': 'Stable Test', 'feature_file': 'test.feature'}
            ]

            report = detector.detect_flaky_tests(stable_runner, scenarios)

            assert report.total_scenarios == 1
            assert report.stable_count == 1
            assert report.flaky_count == 0

    def test_detect_flaky_tests_failing(self):
        """Test flake detection with failing test"""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = FlakeDetector(
                run_count=3,
                quarantine_file=f"{tmpdir}/quarantine.json"
            )

            # Runner that always fails
            def failing_runner(scenario):
                return False, 0.5, "Always fails"

            scenarios = [
                {'id': 'fail-1', 'name': 'Failing Test', 'feature_file': 'test.feature'}
            ]

            report = detector.detect_flaky_tests(failing_runner, scenarios)

            assert report.total_scenarios == 1
            assert report.failing_count == 1
            assert report.flaky_count == 0

    def test_detect_flaky_tests_flaky(self):
        """Test flake detection with flaky test"""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = FlakeDetector(
                run_count=3,
                auto_quarantine=False,
                quarantine_file=f"{tmpdir}/quarantine.json"
            )

            # Runner that alternates
            call_count = [0]
            def flaky_runner(scenario):
                call_count[0] += 1
                return call_count[0] % 2 == 0, 0.5, None if call_count[0] % 2 == 0 else "Flaky"

            scenarios = [
                {'id': 'flaky-1', 'name': 'Flaky Test', 'feature_file': 'test.feature'}
            ]

            report = detector.detect_flaky_tests(flaky_runner, scenarios)

            assert report.total_scenarios == 1
            assert report.flaky_count == 1

    def test_auto_quarantine(self):
        """Test auto-quarantine functionality"""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = FlakeDetector(
                run_count=3,
                flake_threshold=0.10,
                auto_quarantine=True,
                quarantine_file=f"{tmpdir}/quarantine.json"
            )

            # Runner that alternates (high flake rate)
            call_count = [0]
            def flaky_runner(scenario):
                call_count[0] += 1
                return call_count[0] % 2 == 0, 0.5, None

            scenarios = [
                {'id': 'flaky-1', 'name': 'Flaky Test', 'feature_file': 'test.feature'}
            ]

            report = detector.detect_flaky_tests(flaky_runner, scenarios)

            # Should be auto-quarantined
            assert report.analyses[0].is_quarantined is True

    def test_quarantined_scenarios_skipped(self):
        """Test that quarantined scenarios are skipped"""
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = FlakeDetector(
                quarantine_file=f"{tmpdir}/quarantine.json"
            )

            # Pre-quarantine a scenario
            detector.quarantine("skip-me", "Already quarantined")

            call_count = [0]
            def counter_runner(scenario):
                call_count[0] += 1
                return True, 0.5, None

            scenarios = [
                {'id': 'skip-me', 'name': 'Quarantined', 'feature_file': 'test.feature'},
                {'id': 'run-me', 'name': 'Normal', 'feature_file': 'test.feature'}
            ]

            report = detector.detect_flaky_tests(counter_runner, scenarios)

            # Only one scenario should have been run
            assert call_count[0] == 3  # 3 runs for 'run-me' only
            assert report.quarantined_count == 1


class TestFlakeStatus:
    """Tests for FlakeStatus enum"""

    def test_status_values(self):
        """Test status enum values"""
        assert FlakeStatus.STABLE.value == "stable"
        assert FlakeStatus.FLAKY.value == "flaky"
        assert FlakeStatus.CONSISTENTLY_FAILING.value == "consistently_failing"
        assert FlakeStatus.QUARANTINED.value == "quarantined"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
