"""
BDV Runner - Behavior-Driven Validation Runner

Discovers and runs Gherkin feature files using pytest-bdd.
Provides comprehensive test execution and reporting for behavioral validation.

MD-2094: Added BDVOrchestrator class with full orchestration support including:
- Programmatic pytest hook integration
- Retry logic with exponential backoff
- Result aggregation across parallel workers
"""

import json
import subprocess
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
import re

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry logic with exponential backoff"""
    max_retries: int = 3
    base_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number using exponential backoff"""
        delay = self.base_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


@dataclass
class ScenarioResult:
    """Result of a single scenario execution"""
    feature_file: str
    scenario_name: str
    status: str  # 'passed', 'failed', 'skipped'
    duration: float  # seconds
    error_message: Optional[str] = None
    contract_tag: Optional[str] = None
    retry_count: int = 0
    worker_id: Optional[str] = None

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
        # Get the features directory path for conftest.py discovery
        features_dir = str(self.features_path.resolve())

        args = [
            "pytest",
            "--tb=short",
            "-v",
            "--override-ini=addopts=",  # Disable strict-markers from pytest.ini
            "-W", "ignore::pytest.PytestUnknownMarkWarning",  # Ignore marker warnings
            f"--confcutdir={features_dir}",  # Set conftest.py search boundary
            "-c", "features/pytest_bdv.ini",  # Use BDV-specific pytest config
        ]

        if tags:
            args.extend(["-m", tags])

        # Run the test module which imports the feature files
        args.append("features/test_generated_features.py")

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


class BDVOrchestrator:
    """
    BDV Orchestrator for full test execution orchestration (MD-2094).

    Provides:
    - Programmatic pytest hook integration
    - Retry logic with exponential backoff
    - Result aggregation across parallel workers
    - Suite-level coordination
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        features_path: str = "features/",
        retry_config: Optional[RetryConfig] = None,
        max_workers: int = 4
    ):
        """
        Initialize BDV orchestrator.

        Args:
            base_url: Base URL of the system under test
            features_path: Path to feature files directory
            retry_config: Configuration for retry logic
            max_workers: Maximum parallel workers
        """
        self.runner = BDVRunner(base_url, features_path)
        self.retry_config = retry_config or RetryConfig()
        self.max_workers = max_workers
        self._scenario_results: Dict[str, List[ScenarioResult]] = {}
        self._hooks: Dict[str, List[Callable]] = {
            'before_suite': [],
            'after_suite': [],
            'before_scenario': [],
            'after_scenario': [],
            'on_retry': [],
            'on_failure': []
        }
        logger.info(f"BDVOrchestrator initialized with {max_workers} workers")

    def register_hook(self, hook_type: str, callback: Callable):
        """
        Register a callback for a specific hook type.

        Args:
            hook_type: Type of hook (before_suite, after_suite, etc.)
            callback: Callback function to execute
        """
        if hook_type in self._hooks:
            self._hooks[hook_type].append(callback)
            logger.debug(f"Registered hook: {hook_type}")

    def _execute_hooks(self, hook_type: str, **kwargs):
        """Execute all registered hooks of given type"""
        for callback in self._hooks.get(hook_type, []):
            try:
                callback(**kwargs)
            except Exception as e:
                logger.warning(f"Hook {hook_type} failed: {e}")

    def run_suite(
        self,
        features: Optional[List[str]] = None,
        iteration_id: Optional[str] = None,
        parallel: bool = False,
        tags: Optional[str] = None
    ) -> BDVResult:
        """
        Run a complete test suite with orchestration.

        Args:
            features: List of feature files to run
            iteration_id: Iteration identifier
            parallel: Whether to run tests in parallel
            tags: Tags filter for scenarios

        Returns:
            Aggregated BDVResult
        """
        iteration_id = iteration_id or f"iter-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        start_time = datetime.now()

        logger.info(f"Starting BDV suite: {iteration_id}")
        self._execute_hooks('before_suite', iteration_id=iteration_id)

        # Discover features if not specified
        if not features:
            discovered = self.runner.discover_features()
            features = [str(f) for f in discovered]

        if not features:
            logger.warning("No feature files found")
            return self.runner._create_empty_result(iteration_id, start_time)

        # Run tests (parallel or sequential)
        if parallel and len(features) > 1:
            result = self._run_parallel(features, iteration_id, tags)
        else:
            result = self._run_sequential(features, iteration_id, tags)

        self._execute_hooks('after_suite', iteration_id=iteration_id, result=result)
        logger.info(f"Suite complete: {result.passed}/{result.total_scenarios} passed")

        return result

    def _run_sequential(
        self,
        features: List[str],
        iteration_id: str,
        tags: Optional[str]
    ) -> BDVResult:
        """Run features sequentially with retry support"""
        all_scenarios = []
        total_passed = 0
        total_failed = 0
        total_skipped = 0
        start_time = datetime.now()

        for feature in features:
            result = self._run_with_retry(feature, iteration_id, tags)
            all_scenarios.extend(result.scenarios)
            total_passed += result.passed
            total_failed += result.failed
            total_skipped += result.skipped

        duration = (datetime.now() - start_time).total_seconds()

        return BDVResult(
            iteration_id=iteration_id,
            total_scenarios=len(all_scenarios),
            passed=total_passed,
            failed=total_failed,
            skipped=total_skipped,
            duration=duration,
            timestamp=datetime.utcnow().isoformat() + "Z",
            scenarios=all_scenarios,
            summary={
                'execution_mode': 'sequential',
                'features_count': len(features)
            }
        )

    def _run_parallel(
        self,
        features: List[str],
        iteration_id: str,
        tags: Optional[str]
    ) -> BDVResult:
        """Run features in parallel across workers"""
        all_scenarios = []
        results_by_worker: Dict[str, List[BDVResult]] = {}
        start_time = datetime.now()

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_feature = {
                executor.submit(
                    self._run_with_retry,
                    feature,
                    iteration_id,
                    tags,
                    f"worker-{i % self.max_workers}"
                ): feature
                for i, feature in enumerate(features)
            }

            for future in as_completed(future_to_feature):
                feature = future_to_feature[future]
                try:
                    result = future.result()
                    all_scenarios.extend(result.scenarios)
                except Exception as e:
                    logger.error(f"Feature {feature} failed: {e}")
                    # Create error scenario
                    all_scenarios.append(ScenarioResult(
                        feature_file=feature,
                        scenario_name="Unknown (worker error)",
                        status='failed',
                        duration=0.0,
                        error_message=str(e)
                    ))

        # Aggregate results
        total_passed = sum(1 for s in all_scenarios if s.status == 'passed')
        total_failed = sum(1 for s in all_scenarios if s.status == 'failed')
        total_skipped = sum(1 for s in all_scenarios if s.status == 'skipped')
        duration = (datetime.now() - start_time).total_seconds()

        return BDVResult(
            iteration_id=iteration_id,
            total_scenarios=len(all_scenarios),
            passed=total_passed,
            failed=total_failed,
            skipped=total_skipped,
            duration=duration,
            timestamp=datetime.utcnow().isoformat() + "Z",
            scenarios=all_scenarios,
            summary={
                'execution_mode': 'parallel',
                'workers': self.max_workers,
                'features_count': len(features)
            }
        )

    def _run_with_retry(
        self,
        feature: str,
        iteration_id: str,
        tags: Optional[str],
        worker_id: Optional[str] = None
    ) -> BDVResult:
        """
        Run a single feature with retry logic.

        Args:
            feature: Feature file path
            iteration_id: Iteration identifier
            tags: Tags filter
            worker_id: Worker identifier for parallel execution

        Returns:
            BDVResult after retries
        """
        last_result = None
        last_error = None

        for attempt in range(self.retry_config.max_retries + 1):
            try:
                self._execute_hooks('before_scenario', feature=feature, attempt=attempt)

                result = self.runner.run(
                    feature_files=[feature],
                    iteration_id=f"{iteration_id}-attempt-{attempt}",
                    tags=tags
                )

                # Mark scenarios with worker_id and retry count
                for scenario in result.scenarios:
                    scenario.worker_id = worker_id
                    scenario.retry_count = attempt

                self._execute_hooks('after_scenario', feature=feature, result=result)

                # If all passed or skipped, no retry needed
                if result.failed == 0:
                    return result

                last_result = result

                # If failed and can retry, execute retry hooks and wait
                if attempt < self.retry_config.max_retries:
                    delay = self.retry_config.get_delay(attempt)
                    logger.info(f"Retrying {feature} in {delay:.1f}s (attempt {attempt + 1})")
                    self._execute_hooks('on_retry', feature=feature, attempt=attempt, delay=delay)
                    time.sleep(delay)

            except Exception as e:
                last_error = e
                logger.error(f"Error running {feature}: {e}")

                if attempt < self.retry_config.max_retries:
                    delay = self.retry_config.get_delay(attempt)
                    time.sleep(delay)

        # All retries exhausted
        if last_result:
            self._execute_hooks('on_failure', feature=feature, result=last_result)
            return last_result

        # Return error result
        return BDVResult(
            iteration_id=iteration_id,
            total_scenarios=0,
            passed=0,
            failed=1,
            skipped=0,
            duration=0.0,
            timestamp=datetime.utcnow().isoformat() + "Z",
            scenarios=[ScenarioResult(
                feature_file=feature,
                scenario_name="Unknown",
                status='failed',
                duration=0.0,
                error_message=str(last_error) if last_error else "Unknown error",
                worker_id=worker_id
            )],
            summary={'error': str(last_error) if last_error else "Max retries exceeded"}
        )

    def run_scenario(
        self,
        scenario_id: str,
        iteration_id: Optional[str] = None
    ) -> ScenarioResult:
        """
        Run a single scenario by ID.

        Args:
            scenario_id: Scenario identifier (feature:scenario_name format)
            iteration_id: Optional iteration identifier

        Returns:
            ScenarioResult for the scenario
        """
        # Parse scenario_id (format: "path/to/feature.feature::Scenario Name")
        if "::" in scenario_id:
            feature_path, scenario_name = scenario_id.rsplit("::", 1)
        else:
            feature_path = scenario_id
            scenario_name = None

        result = self.runner.run(
            feature_files=[feature_path],
            iteration_id=iteration_id
        )

        # Find matching scenario
        for scenario in result.scenarios:
            if scenario_name is None or scenario.scenario_name == scenario_name:
                return scenario

        return ScenarioResult(
            feature_file=feature_path,
            scenario_name=scenario_name or "Unknown",
            status='failed',
            duration=0.0,
            error_message="Scenario not found"
        )

    def collect_results(self, iteration_id: str) -> Dict[str, Any]:
        """
        Collect and aggregate results for an iteration.

        Args:
            iteration_id: Iteration identifier

        Returns:
            Dictionary with aggregated results
        """
        report_dir = Path(f"reports/bdv/{iteration_id}")
        if not report_dir.exists():
            return {'error': f"No results found for {iteration_id}"}

        # Collect all result files
        all_results = []
        for result_file in report_dir.glob("**/bdv_results.json"):
            with open(result_file) as f:
                all_results.append(json.load(f))

        if not all_results:
            return {'error': "No result files found"}

        # Aggregate
        total_scenarios = sum(r.get('total_scenarios', 0) for r in all_results)
        total_passed = sum(r.get('passed', 0) for r in all_results)
        total_failed = sum(r.get('failed', 0) for r in all_results)
        total_skipped = sum(r.get('skipped', 0) for r in all_results)
        total_duration = sum(r.get('duration', 0) for r in all_results)

        return {
            'iteration_id': iteration_id,
            'total_scenarios': total_scenarios,
            'passed': total_passed,
            'failed': total_failed,
            'skipped': total_skipped,
            'pass_rate': total_passed / total_scenarios if total_scenarios > 0 else 0.0,
            'duration': total_duration,
            'result_files': len(all_results)
        }

    def generate_coverage_report(self, iteration_id: str) -> Dict[str, Any]:
        """
        Generate a coverage report for the test suite.

        Args:
            iteration_id: Iteration identifier

        Returns:
            Coverage report dictionary
        """
        results = self.collect_results(iteration_id)
        if 'error' in results:
            return results

        # Get all discovered features
        all_features = [str(f) for f in self.runner.discover_features()]

        # Get tested features from results
        report_dir = Path(f"reports/bdv/{iteration_id}")
        tested_features = set()

        for result_file in report_dir.glob("**/bdv_results.json"):
            with open(result_file) as f:
                data = json.load(f)
                for scenario in data.get('scenarios', []):
                    tested_features.add(scenario.get('feature_file', ''))

        # Calculate coverage
        untested = set(all_features) - tested_features
        coverage = len(tested_features) / len(all_features) if all_features else 0.0

        return {
            'iteration_id': iteration_id,
            'total_features': len(all_features),
            'tested_features': len(tested_features),
            'untested_features': list(untested),
            'coverage_percent': round(coverage * 100, 2),
            'results': results
        }


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Create orchestrator
    orchestrator = BDVOrchestrator(
        base_url="http://localhost:8000",
        retry_config=RetryConfig(max_retries=2, base_delay=0.5),
        max_workers=4
    )

    # Register hooks
    def on_suite_start(iteration_id):
        print(f"Starting suite: {iteration_id}")

    def on_failure(feature, result):
        print(f"Feature failed: {feature} - {result.failed} failures")

    orchestrator.register_hook('before_suite', on_suite_start)
    orchestrator.register_hook('on_failure', on_failure)

    # Run suite
    print("\n=== Running BDV Suite ===")
    result = orchestrator.run_suite(iteration_id="test-orchestrator-001")
    print(f"Results: {result.passed}/{result.total_scenarios} passed")

    # Generate coverage report
    coverage = orchestrator.generate_coverage_report("test-orchestrator-001")
    print(f"Coverage: {coverage.get('coverage_percent', 0)}%")
