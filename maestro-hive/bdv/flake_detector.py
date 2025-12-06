"""
Flake Detector (MD-2096)

Detects flaky tests by running scenarios multiple times and analyzing consistency.
Provides quarantine mechanism for tests with high flake rates.

Features:
- Run scenarios multiple times (default 3)
- Calculate flake probability per scenario
- Classify as stable, flaky, or consistently-failing
- Auto-quarantine tests with >10% flake rate
- Generate flake reports
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class FlakeStatus(str, Enum):
    """Classification status for scenarios"""
    STABLE = "stable"  # Always passes or always fails consistently
    FLAKY = "flaky"  # Inconsistent results
    CONSISTENTLY_FAILING = "consistently_failing"  # Always fails
    QUARANTINED = "quarantined"  # Manually or auto quarantined


@dataclass
class ScenarioRun:
    """Result of a single scenario run"""
    scenario_id: str
    run_number: int
    passed: bool
    duration: float
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'scenario_id': self.scenario_id,
            'run_number': self.run_number,
            'passed': self.passed,
            'duration': self.duration,
            'error_message': self.error_message,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class FlakeAnalysis:
    """Flake analysis result for a scenario"""
    scenario_id: str
    scenario_name: str
    feature_file: str
    total_runs: int
    passed_runs: int
    failed_runs: int
    flake_rate: float
    status: FlakeStatus
    avg_duration: float
    runs: List[ScenarioRun] = field(default_factory=list)
    is_quarantined: bool = False
    quarantine_reason: Optional[str] = None

    @property
    def pass_rate(self) -> float:
        return self.passed_runs / self.total_runs if self.total_runs > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'scenario_id': self.scenario_id,
            'scenario_name': self.scenario_name,
            'feature_file': self.feature_file,
            'total_runs': self.total_runs,
            'passed_runs': self.passed_runs,
            'failed_runs': self.failed_runs,
            'flake_rate': round(self.flake_rate, 4),
            'pass_rate': round(self.pass_rate, 4),
            'status': self.status.value,
            'avg_duration': round(self.avg_duration, 3),
            'is_quarantined': self.is_quarantined,
            'quarantine_reason': self.quarantine_reason,
            'runs': [r.to_dict() for r in self.runs]
        }


@dataclass
class FlakeReport:
    """Comprehensive flake detection report"""
    iteration_id: str
    total_scenarios: int
    stable_count: int
    flaky_count: int
    failing_count: int
    quarantined_count: int
    overall_flake_rate: float
    analyses: List[FlakeAnalysis]
    run_count: int
    generated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'iteration_id': self.iteration_id,
            'total_scenarios': self.total_scenarios,
            'stable_count': self.stable_count,
            'flaky_count': self.flaky_count,
            'failing_count': self.failing_count,
            'quarantined_count': self.quarantined_count,
            'overall_flake_rate': round(self.overall_flake_rate, 4),
            'run_count': self.run_count,
            'generated_at': self.generated_at.isoformat(),
            'analyses': [a.to_dict() for a in self.analyses]
        }

    @property
    def flaky_scenarios(self) -> List[FlakeAnalysis]:
        """Get all flaky scenarios"""
        return [a for a in self.analyses if a.status == FlakeStatus.FLAKY]

    @property
    def stable_scenarios(self) -> List[FlakeAnalysis]:
        """Get all stable scenarios"""
        return [a for a in self.analyses if a.status == FlakeStatus.STABLE]


class FlakeDetector:
    """
    Flake Detector for identifying flaky BDV tests.

    Runs each scenario multiple times and analyzes consistency to detect flaky tests.
    """

    DEFAULT_RUN_COUNT = 3
    DEFAULT_FLAKE_THRESHOLD = 0.10  # 10%

    def __init__(
        self,
        run_count: int = DEFAULT_RUN_COUNT,
        flake_threshold: float = DEFAULT_FLAKE_THRESHOLD,
        auto_quarantine: bool = True,
        quarantine_file: Optional[str] = None
    ):
        """
        Initialize flake detector.

        Args:
            run_count: Number of times to run each scenario
            flake_threshold: Threshold above which tests are considered flaky (0.0-1.0)
            auto_quarantine: Whether to automatically quarantine flaky tests
            quarantine_file: Path to quarantine list file
        """
        self.run_count = run_count
        self.flake_threshold = flake_threshold
        self.auto_quarantine = auto_quarantine
        self.quarantine_file = quarantine_file or "bdv_quarantine.json"

        self._quarantined: Set[str] = set()
        self._historical_data: Dict[str, List[FlakeAnalysis]] = defaultdict(list)

        # Load existing quarantine list
        self._load_quarantine_list()

        logger.info(f"FlakeDetector initialized: {run_count} runs, "
                   f"{flake_threshold*100:.0f}% threshold")

    def _load_quarantine_list(self):
        """Load quarantined scenarios from file"""
        quarantine_path = Path(self.quarantine_file)
        if quarantine_path.exists():
            try:
                with open(quarantine_path) as f:
                    data = json.load(f)
                    self._quarantined = set(data.get('quarantined', []))
                logger.info(f"Loaded {len(self._quarantined)} quarantined scenarios")
            except Exception as e:
                logger.warning(f"Failed to load quarantine file: {e}")

    def _save_quarantine_list(self):
        """Save quarantined scenarios to file"""
        try:
            with open(self.quarantine_file, 'w') as f:
                json.dump({
                    'quarantined': list(self._quarantined),
                    'updated_at': datetime.now().isoformat()
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save quarantine file: {e}")

    def quarantine(self, scenario_id: str, reason: str = "Auto-quarantined"):
        """
        Quarantine a scenario.

        Args:
            scenario_id: Scenario identifier
            reason: Reason for quarantine
        """
        self._quarantined.add(scenario_id)
        self._save_quarantine_list()
        logger.info(f"Quarantined scenario: {scenario_id} - {reason}")

    def unquarantine(self, scenario_id: str):
        """Remove scenario from quarantine"""
        self._quarantined.discard(scenario_id)
        self._save_quarantine_list()
        logger.info(f"Unquarantined scenario: {scenario_id}")

    def is_quarantined(self, scenario_id: str) -> bool:
        """Check if scenario is quarantined"""
        return scenario_id in self._quarantined

    def detect_flaky_tests(
        self,
        scenario_runner: callable,
        scenarios: List[Dict[str, Any]],
        iteration_id: Optional[str] = None
    ) -> FlakeReport:
        """
        Detect flaky tests by running scenarios multiple times.

        Args:
            scenario_runner: Callable that runs a scenario and returns (passed, duration, error)
            scenarios: List of scenario dicts with 'id', 'name', 'feature_file'
            iteration_id: Optional iteration identifier

        Returns:
            FlakeReport with analysis results
        """
        iteration_id = iteration_id or f"flake-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        logger.info(f"Starting flake detection: {len(scenarios)} scenarios, "
                   f"{self.run_count} runs each")

        analyses = []

        for scenario in scenarios:
            scenario_id = scenario.get('id', f"{scenario.get('feature_file')}::{scenario.get('name')}")

            # Skip quarantined scenarios
            if self.is_quarantined(scenario_id):
                analyses.append(FlakeAnalysis(
                    scenario_id=scenario_id,
                    scenario_name=scenario.get('name', 'Unknown'),
                    feature_file=scenario.get('feature_file', 'Unknown'),
                    total_runs=0,
                    passed_runs=0,
                    failed_runs=0,
                    flake_rate=0.0,
                    status=FlakeStatus.QUARANTINED,
                    avg_duration=0.0,
                    is_quarantined=True,
                    quarantine_reason="Previously quarantined"
                ))
                continue

            # Run scenario multiple times
            analysis = self._analyze_scenario(scenario_runner, scenario)
            analyses.append(analysis)

            # Auto-quarantine if needed
            if (self.auto_quarantine and
                analysis.flake_rate > self.flake_threshold and
                analysis.status == FlakeStatus.FLAKY):
                self.quarantine(
                    scenario_id,
                    f"Flake rate {analysis.flake_rate*100:.1f}% exceeds threshold"
                )
                analysis.is_quarantined = True
                analysis.quarantine_reason = f"Auto-quarantined: {analysis.flake_rate*100:.1f}% flake rate"

        # Generate report
        report = self._generate_report(analyses, iteration_id)

        # Save report
        self._save_report(report, iteration_id)

        logger.info(f"Flake detection complete: {report.flaky_count} flaky, "
                   f"{report.stable_count} stable, {report.failing_count} failing")

        return report

    def _analyze_scenario(
        self,
        scenario_runner: callable,
        scenario: Dict[str, Any]
    ) -> FlakeAnalysis:
        """
        Analyze a single scenario for flakiness.

        Args:
            scenario_runner: Callable to run the scenario
            scenario: Scenario definition dict

        Returns:
            FlakeAnalysis result
        """
        scenario_id = scenario.get('id', f"{scenario.get('feature_file')}::{scenario.get('name')}")
        runs = []
        durations = []

        for run_num in range(self.run_count):
            try:
                passed, duration, error = scenario_runner(scenario)
                run = ScenarioRun(
                    scenario_id=scenario_id,
                    run_number=run_num + 1,
                    passed=passed,
                    duration=duration,
                    error_message=error
                )
                runs.append(run)
                durations.append(duration)

            except Exception as e:
                logger.error(f"Error running scenario {scenario_id}: {e}")
                runs.append(ScenarioRun(
                    scenario_id=scenario_id,
                    run_number=run_num + 1,
                    passed=False,
                    duration=0.0,
                    error_message=str(e)
                ))

        # Calculate statistics
        passed_count = sum(1 for r in runs if r.passed)
        failed_count = len(runs) - passed_count
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        # Calculate flake rate
        # Flake rate = variance in results / total runs
        # If all pass or all fail: 0%, if 50/50: ~100%
        if len(runs) == 0:
            flake_rate = 0.0
        else:
            # Variance-based flake rate
            pass_rate = passed_count / len(runs)
            flake_rate = 2 * pass_rate * (1 - pass_rate)  # 0 when all same, max at 50/50

        # Determine status
        status = self._classify_status(passed_count, failed_count, flake_rate)

        return FlakeAnalysis(
            scenario_id=scenario_id,
            scenario_name=scenario.get('name', 'Unknown'),
            feature_file=scenario.get('feature_file', 'Unknown'),
            total_runs=len(runs),
            passed_runs=passed_count,
            failed_runs=failed_count,
            flake_rate=flake_rate,
            status=status,
            avg_duration=avg_duration,
            runs=runs
        )

    def _classify_status(
        self,
        passed_count: int,
        failed_count: int,
        flake_rate: float
    ) -> FlakeStatus:
        """
        Classify scenario status based on run results.

        Args:
            passed_count: Number of passed runs
            failed_count: Number of failed runs
            flake_rate: Calculated flake rate

        Returns:
            FlakeStatus classification
        """
        total = passed_count + failed_count

        if total == 0:
            return FlakeStatus.STABLE

        # All passed - stable
        if failed_count == 0:
            return FlakeStatus.STABLE

        # All failed - consistently failing
        if passed_count == 0:
            return FlakeStatus.CONSISTENTLY_FAILING

        # Mixed results - flaky
        if flake_rate > 0:
            return FlakeStatus.FLAKY

        return FlakeStatus.STABLE

    def _generate_report(
        self,
        analyses: List[FlakeAnalysis],
        iteration_id: str
    ) -> FlakeReport:
        """Generate comprehensive flake report"""
        stable_count = sum(1 for a in analyses if a.status == FlakeStatus.STABLE)
        flaky_count = sum(1 for a in analyses if a.status == FlakeStatus.FLAKY)
        failing_count = sum(1 for a in analyses if a.status == FlakeStatus.CONSISTENTLY_FAILING)
        quarantined_count = sum(1 for a in analyses if a.status == FlakeStatus.QUARANTINED)

        # Calculate overall flake rate
        if analyses:
            overall_flake_rate = sum(a.flake_rate for a in analyses) / len(analyses)
        else:
            overall_flake_rate = 0.0

        return FlakeReport(
            iteration_id=iteration_id,
            total_scenarios=len(analyses),
            stable_count=stable_count,
            flaky_count=flaky_count,
            failing_count=failing_count,
            quarantined_count=quarantined_count,
            overall_flake_rate=overall_flake_rate,
            analyses=analyses,
            run_count=self.run_count
        )

    def _save_report(self, report: FlakeReport, iteration_id: str):
        """Save flake report to file"""
        output_dir = Path(f"reports/flake/{iteration_id}")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "flake_report.json"
        with open(output_file, 'w') as f:
            json.dump(report.to_dict(), f, indent=2)

        logger.debug(f"Saved flake report to {output_file}")

    def get_historical_flake_rate(self, scenario_id: str) -> float:
        """
        Get historical flake rate for a scenario.

        Args:
            scenario_id: Scenario identifier

        Returns:
            Average flake rate across all historical analyses
        """
        history = self._historical_data.get(scenario_id, [])
        if not history:
            return 0.0

        return sum(a.flake_rate for a in history) / len(history)

    def analyze_consistency(self, results: List[bool]) -> Dict[str, Any]:
        """
        Analyze consistency of a series of test results.

        Args:
            results: List of pass/fail booleans

        Returns:
            Dictionary with consistency metrics
        """
        if not results:
            return {
                'total_runs': 0,
                'passed': 0,
                'failed': 0,
                'pass_rate': 0.0,
                'flake_rate': 0.0,
                'is_flaky': False,
                'is_consistent': True
            }

        passed = sum(results)
        failed = len(results) - passed
        pass_rate = passed / len(results)

        # Calculate flake rate (variance)
        flake_rate = 2 * pass_rate * (1 - pass_rate)

        # Determine if flaky
        is_flaky = flake_rate > self.flake_threshold and 0 < passed < len(results)

        return {
            'total_runs': len(results),
            'passed': passed,
            'failed': failed,
            'pass_rate': round(pass_rate, 4),
            'flake_rate': round(flake_rate, 4),
            'is_flaky': is_flaky,
            'is_consistent': flake_rate == 0
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Create detector
    detector = FlakeDetector(
        run_count=3,
        flake_threshold=0.10,
        auto_quarantine=True
    )

    # Mock scenario runner
    import random
    def mock_runner(scenario):
        # Simulate different behaviors
        if 'flaky' in scenario.get('name', '').lower():
            passed = random.choice([True, False])
        elif 'fail' in scenario.get('name', '').lower():
            passed = False
        else:
            passed = True
        return passed, 0.5, None if passed else "Assertion failed"

    # Test scenarios
    scenarios = [
        {'id': 'stable-1', 'name': 'Stable Test', 'feature_file': 'stable.feature'},
        {'id': 'flaky-1', 'name': 'Flaky Test', 'feature_file': 'flaky.feature'},
        {'id': 'fail-1', 'name': 'Failing Test', 'feature_file': 'fail.feature'},
    ]

    # Run detection
    report = detector.detect_flaky_tests(mock_runner, scenarios)

    print(f"\n=== Flake Report ===")
    print(f"Total: {report.total_scenarios}")
    print(f"Stable: {report.stable_count}")
    print(f"Flaky: {report.flaky_count}")
    print(f"Failing: {report.failing_count}")
    print(f"Overall flake rate: {report.overall_flake_rate*100:.1f}%")

    # Analyze consistency example
    results = [True, True, False, True, False]
    analysis = detector.analyze_consistency(results)
    print(f"\nConsistency analysis: {analysis}")
