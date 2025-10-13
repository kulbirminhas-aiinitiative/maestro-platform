"""
BDV Runner - Behavior-Driven Validation Runner

Discovers and runs Gherkin feature files using pytest-bdd.
Provides comprehensive test execution and reporting for behavioral validation.
"""

import json
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import re


@dataclass
class ScenarioResult:
    """Result of a single scenario execution"""
    feature_file: str
    scenario_name: str
    status: str  # 'passed', 'failed', 'skipped'
    duration: float  # seconds
    error_message: Optional[str] = None
    contract_tag: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)


@dataclass
class BDVResult:
    """Aggregated results from BDV test execution"""
    iteration_id: Optional[str]
    total_scenarios: int
    passed: int
    failed: int
    skipped: int
    duration: float  # seconds
    timestamp: str
    scenarios: List[ScenarioResult]
    summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'iteration_id': self.iteration_id,
            'total_scenarios': self.total_scenarios,
            'passed': self.passed,
            'failed': self.failed,
            'skipped': self.skipped,
            'duration': self.duration,
            'timestamp': self.timestamp,
            'scenarios': [s.to_dict() for s in self.scenarios],
            'summary': self.summary
        }


class BDVRunner:
    """
    BDV Runner for executing behavioral validation tests.

    Uses pytest-bdd to run Gherkin feature files and collects results.
    """

    def __init__(self, base_url: str, features_path: str = "features/"):
        """
        Initialize BDV runner.

        Args:
            base_url: Base URL of the system under test
            features_path: Path to feature files directory
        """
        self.base_url = base_url
        self.features_path = Path(features_path)
        self.results: List[ScenarioResult] = []

    def discover_features(self) -> List[Path]:
        """
        Discover all .feature files in the features directory.

        Returns:
            List of Path objects for feature files
        """
        if not self.features_path.exists():
            return []

        return sorted(self.features_path.rglob("*.feature"))

    def extract_contract_tags(self, feature_file: Path) -> List[str]:
        """
        Extract contract tags from a feature file.

        Args:
            feature_file: Path to feature file

        Returns:
            List of contract tags (e.g., ['contract:AuthAPI:v1.2'])
        """
        tags = []

        with open(feature_file) as f:
            for line in f:
                # Look for @contract: tags
                match = re.search(r'@contract:(\w+):v([\d.]+)', line)
                if match:
                    contract_name, version = match.groups()
                    tags.append(f"contract:{contract_name}:v{version}")

        return tags

    def run(
        self,
        feature_files: Optional[List[str]] = None,
        iteration_id: Optional[str] = None,
        tags: Optional[str] = None
    ) -> BDVResult:
        """
        Run BDV tests and collect results.

        Args:
            feature_files: Specific feature files to run (optional, runs all if None)
            iteration_id: Iteration identifier for tracking (optional)
            tags: pytest-bdd tags to filter scenarios (optional, e.g., "@happy_path")

        Returns:
            BDVResult with execution results
        """
        start_time = datetime.now()

        # Discover feature files if not specified
        if not feature_files:
            discovered = self.discover_features()
            feature_files = [str(f) for f in discovered]

        if not feature_files:
            return self._create_empty_result(iteration_id, start_time)

        # Build pytest command
        pytest_args = self._build_pytest_args(feature_files, tags)

        # Execute pytest
        try:
            result = subprocess.run(
                pytest_args,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            # Parse results
            bdv_result = self._parse_pytest_output(
                result.stdout,
                result.stderr,
                result.returncode,
                iteration_id,
                start_time
            )

        except subprocess.TimeoutExpired:
            bdv_result = self._create_timeout_result(iteration_id, start_time)
        except Exception as e:
            bdv_result = self._create_error_result(iteration_id, start_time, str(e))

        # Save results
        self._save_results(bdv_result, iteration_id)

        return bdv_result

    def run_with_pytest_bdd(
        self,
        feature_files: List[str],
        iteration_id: Optional[str] = None
    ) -> BDVResult:
        """
        Run tests using pytest-bdd directly (alternative implementation).

        This method uses pytest-bdd's programmatic API instead of subprocess.

        Args:
            feature_files: List of feature files to run
            iteration_id: Iteration identifier (optional)

        Returns:
            BDVResult with execution results
        """
        import pytest

        start_time = datetime.now()

        # Build pytest args
        pytest_args = [
            "--tb=short",
            "--json-report",
            f"--json-report-file=bdv_report_{iteration_id or 'default'}.json",
            "--base-url", self.base_url,
            "-v"
        ]
        pytest_args.extend(feature_files)

        # Run pytest
        exit_code = pytest.main(pytest_args)

        # Parse JSON report
        report_file = f"bdv_report_{iteration_id or 'default'}.json"
        if Path(report_file).exists():
            with open(report_file) as f:
                report_data = json.load(f)

            bdv_result = self._parse_json_report(
                report_data,
                iteration_id,
                start_time
            )
        else:
            bdv_result = self._create_error_result(
                iteration_id,
                start_time,
                "JSON report not generated"
            )

        return bdv_result

    def _build_pytest_args(
        self,
        feature_files: List[str],
        tags: Optional[str] = None
    ) -> List[str]:
        """
        Build pytest command line arguments.

        Args:
            feature_files: List of feature files
            tags: Optional tags filter

        Returns:
            List of command line arguments
        """
        args = [
            "pytest",
            "--tb=short",
            "-v",
            f"--base-url={self.base_url}"
        ]

        if tags:
            args.extend(["-m", tags])

        args.extend(feature_files)

        return args

    def _parse_pytest_output(
        self,
        stdout: str,
        stderr: str,
        returncode: int,
        iteration_id: Optional[str],
        start_time: datetime
    ) -> BDVResult:
        """
        Parse pytest output to extract results.

        Args:
            stdout: Standard output from pytest
            stderr: Standard error from pytest
            returncode: pytest exit code
            iteration_id: Iteration ID
            start_time: Test start time

        Returns:
            BDVResult
        """
        # This is a simplified parser - in production, use pytest-json-report
        scenarios = []
        passed = 0
        failed = 0
        skipped = 0

        # Parse output (simplified - pytest-json-report would be better)
        for line in stdout.splitlines():
            if "PASSED" in line:
                passed += 1
            elif "FAILED" in line:
                failed += 1
            elif "SKIPPED" in line:
                skipped += 1

        duration = (datetime.now() - start_time).total_seconds()

        return BDVResult(
            iteration_id=iteration_id,
            total_scenarios=passed + failed + skipped,
            passed=passed,
            failed=failed,
            skipped=skipped,
            duration=duration,
            timestamp=datetime.utcnow().isoformat() + "Z",
            scenarios=scenarios,
            summary={
                'exit_code': returncode,
                'stdout_lines': len(stdout.splitlines()),
                'stderr_lines': len(stderr.splitlines())
            }
        )

    def _parse_json_report(
        self,
        report_data: Dict[str, Any],
        iteration_id: Optional[str],
        start_time: datetime
    ) -> BDVResult:
        """
        Parse pytest JSON report.

        Args:
            report_data: Parsed JSON report data
            iteration_id: Iteration ID
            start_time: Test start time

        Returns:
            BDVResult
        """
        summary = report_data.get('summary', {})
        tests = report_data.get('tests', [])

        scenarios = []
        for test in tests:
            scenario = ScenarioResult(
                feature_file=test.get('location', ['unknown'])[0],
                scenario_name=test.get('name', 'unknown'),
                status=test.get('outcome', 'unknown'),
                duration=test.get('duration', 0.0),
                error_message=test.get('call', {}).get('longrepr') if test.get('outcome') == 'failed' else None
            )
            scenarios.append(scenario)

        duration = report_data.get('duration', 0.0)

        return BDVResult(
            iteration_id=iteration_id,
            total_scenarios=summary.get('total', 0),
            passed=summary.get('passed', 0),
            failed=summary.get('failed', 0),
            skipped=summary.get('skipped', 0),
            duration=duration,
            timestamp=datetime.utcnow().isoformat() + "Z",
            scenarios=scenarios,
            summary=summary
        )

    def _create_empty_result(
        self,
        iteration_id: Optional[str],
        start_time: datetime
    ) -> BDVResult:
        """Create empty result (no features found)"""
        return BDVResult(
            iteration_id=iteration_id,
            total_scenarios=0,
            passed=0,
            failed=0,
            skipped=0,
            duration=0.0,
            timestamp=datetime.utcnow().isoformat() + "Z",
            scenarios=[],
            summary={'message': 'No feature files found'}
        )

    def _create_timeout_result(
        self,
        iteration_id: Optional[str],
        start_time: datetime
    ) -> BDVResult:
        """Create timeout result"""
        duration = (datetime.now() - start_time).total_seconds()
        return BDVResult(
            iteration_id=iteration_id,
            total_scenarios=0,
            passed=0,
            failed=0,
            skipped=0,
            duration=duration,
            timestamp=datetime.utcnow().isoformat() + "Z",
            scenarios=[],
            summary={'error': 'Execution timed out after 1 hour'}
        )

    def _create_error_result(
        self,
        iteration_id: Optional[str],
        start_time: datetime,
        error_message: str
    ) -> BDVResult:
        """Create error result"""
        duration = (datetime.now() - start_time).total_seconds()
        return BDVResult(
            iteration_id=iteration_id,
            total_scenarios=0,
            passed=0,
            failed=0,
            skipped=0,
            duration=duration,
            timestamp=datetime.utcnow().isoformat() + "Z",
            scenarios=[],
            summary={'error': error_message}
        )

    def _save_results(self, result: BDVResult, iteration_id: Optional[str]):
        """
        Save BDV results to file.

        Args:
            result: BDVResult to save
            iteration_id: Iteration ID for file naming
        """
        output_dir = Path(f"reports/bdv/{iteration_id or 'default'}")
        output_dir.mkdir(parents=True, exist_ok=True)

        output_file = output_dir / "bdv_results.json"
        with open(output_file, "w") as f:
            json.dump(result.to_dict(), f, indent=2)


# Example usage
if __name__ == "__main__":
    # Create runner
    runner = BDVRunner(base_url="http://localhost:8000")

    # Discover features
    features = runner.discover_features()
    print(f"Found {len(features)} feature files:")
    for feature in features:
        print(f"  - {feature}")
        tags = runner.extract_contract_tags(feature)
        if tags:
            print(f"    Tags: {tags}")

    # Run tests (example - requires pytest-bdd setup)
    # result = runner.run(iteration_id="Iter-20251012-1430-001")
    # print(f"\nResults: {result.passed}/{result.total_scenarios} passed")
