"""
Parallel Test Runner (MD-2100)

Provides parallelization for BDV test execution with:
- pytest-xdist integration
- Worker-aware result collection
- Dependency-aware scheduling
- Resource pooling
"""

import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from queue import Queue, Empty
from threading import Lock, Event
from typing import (
    Dict, List, Optional, Set, Tuple, Any, Callable, Iterator
)

logger = logging.getLogger(__name__)


class WorkerState(Enum):
    """Worker state enum"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ResourceType(Enum):
    """Resource type for pooling"""
    DATABASE = "database"
    API_CLIENT = "api_client"
    BROWSER = "browser"
    CUSTOM = "custom"


@dataclass
class WorkerInfo:
    """
    Information about a test worker.

    Attributes:
        id: Unique worker identifier
        state: Current worker state
        assigned_tests: Tests assigned to this worker
        completed_tests: Tests completed by this worker
        start_time: When the worker started
        end_time: When the worker finished
    """
    id: str
    state: WorkerState = WorkerState.IDLE
    assigned_tests: List[str] = field(default_factory=list)
    completed_tests: List[str] = field(default_factory=list)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    @property
    def duration(self) -> float:
        """Get worker duration in seconds"""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0.0

    @property
    def test_count(self) -> int:
        """Number of tests completed"""
        return len(self.completed_tests)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'state': self.state.value,
            'assigned_tests': self.assigned_tests,
            'completed_tests': self.completed_tests,
            'test_count': self.test_count,
            'duration': self.duration,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None
        }


@dataclass
class TestItem:
    """
    A test item for scheduling.

    Attributes:
        id: Unique test identifier
        feature_file: Path to feature file
        scenario_name: Name of scenario
        dependencies: Tests that must complete first
        priority: Test priority (higher = run first)
        resource_requirements: Required resources
        estimated_duration: Estimated duration in seconds
        tags: Test tags
    """
    id: str
    feature_file: str
    scenario_name: str
    dependencies: List[str] = field(default_factory=list)
    priority: int = 0
    resource_requirements: List[ResourceType] = field(default_factory=list)
    estimated_duration: float = 1.0
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'feature_file': self.feature_file,
            'scenario_name': self.scenario_name,
            'dependencies': self.dependencies,
            'priority': self.priority,
            'resource_requirements': [r.value for r in self.resource_requirements],
            'estimated_duration': self.estimated_duration,
            'tags': self.tags
        }


@dataclass
class TestResult:
    """
    Result of a single test execution.

    Attributes:
        test_id: Test identifier
        worker_id: Worker that ran the test
        status: Test status (passed/failed/skipped)
        duration: Actual duration in seconds
        error_message: Error message if failed
        output: Test output
    """
    test_id: str
    worker_id: str
    status: str
    duration: float = 0.0
    error_message: Optional[str] = None
    output: str = ""
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'test_id': self.test_id,
            'worker_id': self.worker_id,
            'status': self.status,
            'duration': self.duration,
            'error_message': self.error_message,
            'output': self.output,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class ParallelResult:
    """
    Result of parallel test execution.

    Attributes:
        total_tests: Total number of tests
        passed: Number of passed tests
        failed: Number of failed tests
        skipped: Number of skipped tests
        duration: Total duration
        worker_count: Number of workers used
        results: Individual test results
        workers: Worker information
    """
    total_tests: int
    passed: int
    failed: int
    skipped: int
    duration: float
    worker_count: int
    results: List[TestResult]
    workers: List[WorkerInfo]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate"""
        if self.total_tests == 0:
            return 0.0
        return self.passed / self.total_tests

    @property
    def speedup(self) -> float:
        """Calculate speedup factor"""
        sequential_time = sum(r.duration for r in self.results)
        if self.duration == 0:
            return 1.0
        return sequential_time / self.duration

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'total_tests': self.total_tests,
            'passed': self.passed,
            'failed': self.failed,
            'skipped': self.skipped,
            'pass_rate': self.pass_rate,
            'duration': self.duration,
            'speedup': self.speedup,
            'worker_count': self.worker_count,
            'results': [r.to_dict() for r in self.results],
            'workers': [w.to_dict() for w in self.workers],
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class ResourcePool:
    """
    Manages shared resources for parallel test execution.

    Provides thread-safe access to pooled resources like database
    connections, API clients, etc.
    """

    def __init__(self, resource_type: ResourceType, pool_size: int = 5):
        """
        Initialize the resource pool.

        Args:
            resource_type: Type of resource to pool
            pool_size: Number of resources in the pool
        """
        self.resource_type = resource_type
        self.pool_size = pool_size
        self._pool: Queue = Queue(maxsize=pool_size)
        self._lock = Lock()
        self._initialized = False
        self._factory: Optional[Callable[[], Any]] = None

    def initialize(self, factory: Callable[[], Any]) -> None:
        """
        Initialize the pool with a factory function.

        Args:
            factory: Function to create new resources
        """
        with self._lock:
            if self._initialized:
                return

            self._factory = factory
            for _ in range(self.pool_size):
                resource = factory()
                self._pool.put(resource)

            self._initialized = True
            logger.info(
                f"Initialized {self.resource_type.value} pool with {self.pool_size} resources"
            )

    def acquire(self, timeout: float = 30.0) -> Any:
        """
        Acquire a resource from the pool.

        Args:
            timeout: Maximum time to wait for a resource

        Returns:
            Resource from the pool

        Raises:
            TimeoutError: If no resource available within timeout
        """
        try:
            resource = self._pool.get(timeout=timeout)
            return resource
        except Empty:
            raise TimeoutError(
                f"Could not acquire {self.resource_type.value} within {timeout}s"
            )

    def release(self, resource: Any) -> None:
        """
        Release a resource back to the pool.

        Args:
            resource: Resource to release
        """
        try:
            self._pool.put_nowait(resource)
        except Exception as e:
            logger.warning(f"Error releasing resource: {e}")

    def cleanup(self, cleanup_fn: Optional[Callable[[Any], None]] = None) -> None:
        """
        Cleanup all resources in the pool.

        Args:
            cleanup_fn: Optional function to cleanup each resource
        """
        with self._lock:
            while not self._pool.empty():
                try:
                    resource = self._pool.get_nowait()
                    if cleanup_fn:
                        try:
                            cleanup_fn(resource)
                        except Exception as e:
                            logger.warning(f"Error cleaning up resource: {e}")
                except Empty:
                    break

            self._initialized = False
            logger.info(f"Cleaned up {self.resource_type.value} pool")

    @property
    def available(self) -> int:
        """Number of available resources"""
        return self._pool.qsize()


class DependencyScheduler:
    """
    Schedules tests based on dependencies and priorities.

    Ensures tests with dependencies run after their dependencies
    complete, while maximizing parallelism.
    """

    def __init__(self):
        """Initialize the scheduler"""
        self._tests: Dict[str, TestItem] = {}
        self._completed: Set[str] = set()
        self._running: Set[str] = set()
        self._lock = Lock()

    def add_tests(self, tests: List[TestItem]) -> None:
        """
        Add tests to the scheduler.

        Args:
            tests: List of test items to schedule
        """
        with self._lock:
            for test in tests:
                self._tests[test.id] = test
            logger.debug(f"Added {len(tests)} tests to scheduler")

    def get_ready_tests(self, max_count: int = 10) -> List[TestItem]:
        """
        Get tests that are ready to run.

        Tests are ready when all their dependencies have completed.

        Args:
            max_count: Maximum number of tests to return

        Returns:
            List of ready test items, sorted by priority
        """
        with self._lock:
            ready = []

            for test_id, test in self._tests.items():
                # Skip if already completed or running
                if test_id in self._completed or test_id in self._running:
                    continue

                # Check if all dependencies are completed
                deps_met = all(
                    dep in self._completed
                    for dep in test.dependencies
                )

                if deps_met:
                    ready.append(test)

            # Sort by priority (higher first)
            ready.sort(key=lambda t: t.priority, reverse=True)

            # Mark as running
            result = ready[:max_count]
            for test in result:
                self._running.add(test.id)

            return result

    def mark_completed(self, test_id: str) -> None:
        """
        Mark a test as completed.

        Args:
            test_id: ID of completed test
        """
        with self._lock:
            self._running.discard(test_id)
            self._completed.add(test_id)

    def mark_failed(self, test_id: str) -> None:
        """
        Mark a test as failed.

        Failed tests are also marked completed so dependents
        know they won't run.

        Args:
            test_id: ID of failed test
        """
        self.mark_completed(test_id)

    def reset(self) -> None:
        """Reset the scheduler state"""
        with self._lock:
            self._completed.clear()
            self._running.clear()

    @property
    def pending_count(self) -> int:
        """Number of tests still pending"""
        with self._lock:
            return len(self._tests) - len(self._completed)

    @property
    def completed_count(self) -> int:
        """Number of completed tests"""
        return len(self._completed)


class WorkerResultCollector:
    """
    Collects test results from multiple workers.

    Thread-safe result collection with aggregation.
    """

    def __init__(self):
        """Initialize the collector"""
        self._results: List[TestResult] = []
        self._lock = Lock()
        self._passed = 0
        self._failed = 0
        self._skipped = 0

    def add_result(self, result: TestResult) -> None:
        """
        Add a test result.

        Args:
            result: Test result to add
        """
        with self._lock:
            self._results.append(result)

            if result.status == 'passed':
                self._passed += 1
            elif result.status == 'failed':
                self._failed += 1
            elif result.status == 'skipped':
                self._skipped += 1

    def get_results(self) -> List[TestResult]:
        """Get all collected results"""
        with self._lock:
            return list(self._results)

    def get_summary(self) -> Dict[str, int]:
        """Get summary statistics"""
        with self._lock:
            return {
                'total': len(self._results),
                'passed': self._passed,
                'failed': self._failed,
                'skipped': self._skipped
            }

    def clear(self) -> None:
        """Clear all results"""
        with self._lock:
            self._results.clear()
            self._passed = 0
            self._failed = 0
            self._skipped = 0


class ParallelTestRunner:
    """
    Runs BDV tests in parallel with dependency awareness.

    Features:
    - Configurable worker count
    - Dependency-aware scheduling
    - Resource pooling
    - Worker-aware result collection
    - pytest-xdist compatibility
    """

    def __init__(
        self,
        max_workers: int = 4,
        use_xdist: bool = False,
        resource_pools: Optional[Dict[ResourceType, int]] = None
    ):
        """
        Initialize the parallel runner.

        Args:
            max_workers: Maximum number of parallel workers
            use_xdist: Whether to use pytest-xdist (requires installation)
            resource_pools: Resource pool configuration {type: pool_size}
        """
        self.max_workers = max_workers
        self.use_xdist = use_xdist
        self._scheduler = DependencyScheduler()
        self._collector = WorkerResultCollector()
        self._pools: Dict[ResourceType, ResourcePool] = {}
        self._workers: Dict[str, WorkerInfo] = {}
        self._stop_event = Event()

        # Initialize resource pools
        if resource_pools:
            for resource_type, pool_size in resource_pools.items():
                self._pools[resource_type] = ResourcePool(resource_type, pool_size)

        logger.info(
            f"ParallelTestRunner initialized with {max_workers} workers, "
            f"xdist={'enabled' if use_xdist else 'disabled'}"
        )

    def initialize_pool(
        self,
        resource_type: ResourceType,
        factory: Callable[[], Any]
    ) -> None:
        """
        Initialize a resource pool.

        Args:
            resource_type: Type of resource
            factory: Factory function to create resources
        """
        if resource_type in self._pools:
            self._pools[resource_type].initialize(factory)
        else:
            raise ValueError(f"No pool configured for {resource_type.value}")

    def acquire_resource(
        self,
        resource_type: ResourceType,
        timeout: float = 30.0
    ) -> Any:
        """
        Acquire a resource from a pool.

        Args:
            resource_type: Type of resource
            timeout: Maximum wait time

        Returns:
            Resource from the pool
        """
        if resource_type not in self._pools:
            raise ValueError(f"No pool for {resource_type.value}")
        return self._pools[resource_type].acquire(timeout)

    def release_resource(
        self,
        resource_type: ResourceType,
        resource: Any
    ) -> None:
        """
        Release a resource back to its pool.

        Args:
            resource_type: Type of resource
            resource: Resource to release
        """
        if resource_type in self._pools:
            self._pools[resource_type].release(resource)

    def run_parallel(
        self,
        tests: List[TestItem],
        test_runner: Callable[[TestItem, str], TestResult],
        iteration_id: Optional[str] = None
    ) -> ParallelResult:
        """
        Run tests in parallel.

        Args:
            tests: List of test items to run
            test_runner: Function that runs a single test and returns result.
                         Takes (test_item, worker_id) and returns TestResult.
            iteration_id: Optional iteration identifier

        Returns:
            ParallelResult with all test results
        """
        if self.use_xdist:
            return self._run_with_xdist(tests, iteration_id)

        return self._run_with_threadpool(tests, test_runner)

    def _run_with_threadpool(
        self,
        tests: List[TestItem],
        test_runner: Callable[[TestItem, str], TestResult]
    ) -> ParallelResult:
        """Run tests using ThreadPoolExecutor"""
        started_at = datetime.utcnow()
        self._scheduler.add_tests(tests)
        self._collector.clear()
        self._workers.clear()
        self._stop_event.clear()

        # Create workers
        for i in range(min(self.max_workers, len(tests))):
            worker_id = f"worker-{i}"
            self._workers[worker_id] = WorkerInfo(id=worker_id)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures: Dict[Future, Tuple[TestItem, str]] = {}
            worker_queue = list(self._workers.keys())
            worker_idx = 0

            while self._scheduler.pending_count > 0 and not self._stop_event.is_set():
                # Get ready tests
                ready_tests = self._scheduler.get_ready_tests(
                    max_count=len(worker_queue)
                )

                if not ready_tests and not futures:
                    # No ready tests and no running tests - might have circular deps
                    logger.warning("No tests ready and none running - possible circular dependency")
                    break

                # Submit ready tests
                for test in ready_tests:
                    worker_id = worker_queue[worker_idx % len(worker_queue)]
                    worker_idx += 1

                    worker = self._workers[worker_id]
                    worker.assigned_tests.append(test.id)

                    if worker.state == WorkerState.IDLE:
                        worker.state = WorkerState.RUNNING
                        worker.start_time = datetime.utcnow()

                    future = executor.submit(test_runner, test, worker_id)
                    futures[future] = (test, worker_id)

                # Wait for at least one completion if we have running tests
                if futures:
                    done, _ = as_completed(futures.keys()).__iter__().__next__(), None
                    for future in list(futures.keys()):
                        if future.done():
                            test, worker_id = futures.pop(future)
                            try:
                                result = future.result()
                                self._collector.add_result(result)
                                self._workers[worker_id].completed_tests.append(test.id)

                                if result.status == 'failed':
                                    self._scheduler.mark_failed(test.id)
                                else:
                                    self._scheduler.mark_completed(test.id)

                            except Exception as e:
                                logger.error(f"Test {test.id} raised exception: {e}")
                                error_result = TestResult(
                                    test_id=test.id,
                                    worker_id=worker_id,
                                    status='failed',
                                    error_message=str(e)
                                )
                                self._collector.add_result(error_result)
                                self._scheduler.mark_failed(test.id)

            # Wait for remaining futures
            for future in as_completed(futures.keys()):
                test, worker_id = futures[future]
                try:
                    result = future.result()
                    self._collector.add_result(result)
                    self._scheduler.mark_completed(test.id)
                except Exception as e:
                    error_result = TestResult(
                        test_id=test.id,
                        worker_id=worker_id,
                        status='failed',
                        error_message=str(e)
                    )
                    self._collector.add_result(error_result)

        # Mark all workers as completed
        completed_at = datetime.utcnow()
        for worker in self._workers.values():
            if worker.state == WorkerState.RUNNING:
                worker.state = WorkerState.COMPLETED
                worker.end_time = completed_at

        # Build result
        results = self._collector.get_results()
        summary = self._collector.get_summary()
        duration = (completed_at - started_at).total_seconds()

        return ParallelResult(
            total_tests=summary['total'],
            passed=summary['passed'],
            failed=summary['failed'],
            skipped=summary['skipped'],
            duration=duration,
            worker_count=len(self._workers),
            results=results,
            workers=list(self._workers.values()),
            started_at=started_at,
            completed_at=completed_at
        )

    def _run_with_xdist(
        self,
        tests: List[TestItem],
        iteration_id: Optional[str] = None
    ) -> ParallelResult:
        """
        Run tests using pytest-xdist.

        This integrates with pytest-xdist for distributed testing.
        """
        import subprocess
        import json
        import tempfile

        started_at = datetime.utcnow()

        # Create a temporary file with test IDs
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            test_data = [t.to_dict() for t in tests]
            json.dump(test_data, f)
            tests_file = f.name

        try:
            # Build pytest command with xdist
            cmd = [
                'python', '-m', 'pytest',
                '-n', str(self.max_workers),
                '--dist', 'loadscope',  # Group by scope
                '-q',
                '--json-report',
            ]

            # Add feature files
            feature_files = list(set(t.feature_file for t in tests))
            cmd.extend(feature_files)

            # Run pytest
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )

            completed_at = datetime.utcnow()
            duration = (completed_at - started_at).total_seconds()

            # Parse results (simplified - real impl would parse JSON report)
            passed = result.returncode == 0
            results = []

            # Create synthetic results for now
            for test in tests:
                results.append(TestResult(
                    test_id=test.id,
                    worker_id="xdist",
                    status='passed' if passed else 'failed',
                    output=result.stdout
                ))

            return ParallelResult(
                total_tests=len(tests),
                passed=len(tests) if passed else 0,
                failed=0 if passed else len(tests),
                skipped=0,
                duration=duration,
                worker_count=self.max_workers,
                results=results,
                workers=[],
                started_at=started_at,
                completed_at=completed_at
            )

        finally:
            # Cleanup
            os.unlink(tests_file)

    def stop(self) -> None:
        """Stop the parallel runner gracefully"""
        self._stop_event.set()
        logger.info("Stopping parallel runner")

    def cleanup(self) -> None:
        """Cleanup all resources"""
        for pool in self._pools.values():
            pool.cleanup()
        logger.info("Parallel runner cleaned up")


# Utility functions

def create_test_items_from_features(
    features_path: Path,
    dependency_map: Optional[Dict[str, List[str]]] = None
) -> List[TestItem]:
    """
    Create TestItem list from feature files.

    Args:
        features_path: Path to features directory
        dependency_map: Optional map of test dependencies {test_id: [dep_ids]}

    Returns:
        List of TestItem objects
    """
    tests = []
    dependency_map = dependency_map or {}

    for feature_file in features_path.glob('**/*.feature'):
        # Simple parsing - a real implementation would use feature_parser
        with open(feature_file) as f:
            content = f.read()

        # Extract scenarios (simplified)
        import re
        scenarios = re.findall(r'Scenario(?:\s+Outline)?:\s*(.+)', content)

        for scenario_name in scenarios:
            test_id = f"{feature_file.stem}::{scenario_name.strip()}"
            tests.append(TestItem(
                id=test_id,
                feature_file=str(feature_file),
                scenario_name=scenario_name.strip(),
                dependencies=dependency_map.get(test_id, [])
            ))

    return tests


def estimate_test_duration(
    test_id: str,
    historical_results: Optional[List[Dict[str, Any]]] = None
) -> float:
    """
    Estimate test duration based on historical data.

    Args:
        test_id: Test identifier
        historical_results: Optional historical result data

    Returns:
        Estimated duration in seconds
    """
    if not historical_results:
        return 1.0  # Default estimate

    # Find matching historical results
    matching = [
        r for r in historical_results
        if r.get('test_id') == test_id
    ]

    if not matching:
        return 1.0

    # Use average of recent results
    durations = [r.get('duration', 1.0) for r in matching[-5:]]
    return sum(durations) / len(durations)


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Create runner
    runner = ParallelTestRunner(
        max_workers=4,
        resource_pools={ResourceType.DATABASE: 2}
    )

    # Initialize database pool with mock factory
    runner.initialize_pool(
        ResourceType.DATABASE,
        lambda: {"connection": "mock_db"}
    )

    # Create some test items
    tests = [
        TestItem(id="test-1", feature_file="auth.feature", scenario_name="Login"),
        TestItem(id="test-2", feature_file="auth.feature", scenario_name="Logout", dependencies=["test-1"]),
        TestItem(id="test-3", feature_file="user.feature", scenario_name="Profile"),
        TestItem(id="test-4", feature_file="user.feature", scenario_name="Settings"),
    ]

    # Simple test runner
    def mock_runner(test: TestItem, worker_id: str) -> TestResult:
        time.sleep(0.1)  # Simulate test execution
        return TestResult(
            test_id=test.id,
            worker_id=worker_id,
            status='passed',
            duration=0.1
        )

    # Run tests
    result = runner.run_parallel(tests, mock_runner)

    print(f"\nParallel Test Results:")
    print(f"  Total: {result.total_tests}")
    print(f"  Passed: {result.passed}")
    print(f"  Failed: {result.failed}")
    print(f"  Duration: {result.duration:.2f}s")
    print(f"  Speedup: {result.speedup:.2f}x")

    # Cleanup
    runner.cleanup()
