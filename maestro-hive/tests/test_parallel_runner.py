"""
Tests for Parallel Test Runner (MD-2100)

Validates:
- Worker management
- Resource pooling
- Dependency-aware scheduling
- Result collection
- Parallel execution
"""

import pytest
import time
from pathlib import Path
from datetime import datetime
from threading import Thread
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from bdv.parallel_runner import (
    ParallelTestRunner,
    DependencyScheduler,
    WorkerResultCollector,
    ResourcePool,
    ResourceType,
    WorkerInfo,
    WorkerState,
    TestItem,
    TestResult,
    ParallelResult,
    create_test_items_from_features,
    estimate_test_duration
)


class TestWorkerInfo:
    """Tests for WorkerInfo dataclass"""

    def test_creation(self):
        """Test WorkerInfo creation"""
        worker = WorkerInfo(id="worker-1")
        assert worker.id == "worker-1"
        assert worker.state == WorkerState.IDLE
        assert worker.test_count == 0

    def test_duration(self):
        """Test duration calculation"""
        worker = WorkerInfo(id="worker-1")
        worker.start_time = datetime(2024, 1, 1, 10, 0, 0)
        worker.end_time = datetime(2024, 1, 1, 10, 0, 30)
        assert worker.duration == 30.0

    def test_to_dict(self):
        """Test conversion to dictionary"""
        worker = WorkerInfo(
            id="worker-1",
            state=WorkerState.RUNNING,
            completed_tests=["test-1", "test-2"]
        )
        d = worker.to_dict()
        assert d['id'] == "worker-1"
        assert d['state'] == "running"
        assert d['test_count'] == 2


class TestTestItem:
    """Tests for TestItem dataclass"""

    def test_creation(self):
        """Test TestItem creation"""
        item = TestItem(
            id="test-1",
            feature_file="auth.feature",
            scenario_name="Login"
        )
        assert item.id == "test-1"
        assert item.feature_file == "auth.feature"
        assert item.priority == 0

    def test_with_dependencies(self):
        """Test TestItem with dependencies"""
        item = TestItem(
            id="test-2",
            feature_file="auth.feature",
            scenario_name="Logout",
            dependencies=["test-1"]
        )
        assert "test-1" in item.dependencies

    def test_with_resources(self):
        """Test TestItem with resource requirements"""
        item = TestItem(
            id="test-1",
            feature_file="db.feature",
            scenario_name="Query",
            resource_requirements=[ResourceType.DATABASE]
        )
        assert ResourceType.DATABASE in item.resource_requirements

    def test_to_dict(self):
        """Test conversion to dictionary"""
        item = TestItem(
            id="test-1",
            feature_file="test.feature",
            scenario_name="Test",
            priority=5
        )
        d = item.to_dict()
        assert d['id'] == "test-1"
        assert d['priority'] == 5


class TestTestResult:
    """Tests for TestResult dataclass"""

    def test_creation(self):
        """Test TestResult creation"""
        result = TestResult(
            test_id="test-1",
            worker_id="worker-1",
            status="passed",
            duration=1.5
        )
        assert result.test_id == "test-1"
        assert result.status == "passed"
        assert result.duration == 1.5

    def test_failed_result(self):
        """Test failed result"""
        result = TestResult(
            test_id="test-1",
            worker_id="worker-1",
            status="failed",
            error_message="Assertion failed"
        )
        assert result.status == "failed"
        assert result.error_message == "Assertion failed"


class TestParallelResult:
    """Tests for ParallelResult dataclass"""

    def test_pass_rate(self):
        """Test pass rate calculation"""
        result = ParallelResult(
            total_tests=10,
            passed=8,
            failed=2,
            skipped=0,
            duration=10.0,
            worker_count=4,
            results=[],
            workers=[]
        )
        assert result.pass_rate == 0.8

    def test_pass_rate_zero_tests(self):
        """Test pass rate with zero tests"""
        result = ParallelResult(
            total_tests=0,
            passed=0,
            failed=0,
            skipped=0,
            duration=0,
            worker_count=4,
            results=[],
            workers=[]
        )
        assert result.pass_rate == 0.0

    def test_speedup(self):
        """Test speedup calculation"""
        results = [
            TestResult("t1", "w1", "passed", duration=2.0),
            TestResult("t2", "w1", "passed", duration=2.0),
            TestResult("t3", "w2", "passed", duration=2.0),
            TestResult("t4", "w2", "passed", duration=2.0)
        ]
        result = ParallelResult(
            total_tests=4,
            passed=4,
            failed=0,
            skipped=0,
            duration=4.0,  # Parallel took 4s instead of 8s
            worker_count=2,
            results=results,
            workers=[]
        )
        assert result.speedup == 2.0


class TestResourcePool:
    """Tests for ResourcePool class"""

    def test_creation(self):
        """Test pool creation"""
        pool = ResourcePool(ResourceType.DATABASE, pool_size=3)
        assert pool.resource_type == ResourceType.DATABASE
        assert pool.pool_size == 3

    def test_initialize(self):
        """Test pool initialization"""
        pool = ResourcePool(ResourceType.DATABASE, pool_size=2)
        pool.initialize(lambda: {"conn": "mock"})
        assert pool.available == 2

    def test_acquire_release(self):
        """Test acquire and release"""
        pool = ResourcePool(ResourceType.API_CLIENT, pool_size=2)
        pool.initialize(lambda: {"client": "mock"})

        resource = pool.acquire(timeout=1.0)
        assert resource is not None
        assert pool.available == 1

        pool.release(resource)
        assert pool.available == 2

    def test_acquire_timeout(self):
        """Test acquire timeout"""
        pool = ResourcePool(ResourceType.DATABASE, pool_size=1)
        pool.initialize(lambda: "resource")

        # Acquire the only resource
        pool.acquire(timeout=1.0)

        # Second acquire should timeout
        with pytest.raises(TimeoutError):
            pool.acquire(timeout=0.1)

    def test_cleanup(self):
        """Test pool cleanup"""
        pool = ResourcePool(ResourceType.DATABASE, pool_size=2)
        pool.initialize(lambda: {"conn": "mock"})

        cleanup_count = [0]
        def cleanup_fn(resource):
            cleanup_count[0] += 1

        pool.cleanup(cleanup_fn)
        assert cleanup_count[0] == 2


class TestDependencyScheduler:
    """Tests for DependencyScheduler class"""

    def test_add_tests(self):
        """Test adding tests"""
        scheduler = DependencyScheduler()
        tests = [
            TestItem("t1", "f1", "s1"),
            TestItem("t2", "f1", "s2")
        ]
        scheduler.add_tests(tests)
        assert scheduler.pending_count == 2

    def test_get_ready_tests_no_deps(self):
        """Test getting ready tests without dependencies"""
        scheduler = DependencyScheduler()
        tests = [
            TestItem("t1", "f1", "s1"),
            TestItem("t2", "f1", "s2")
        ]
        scheduler.add_tests(tests)

        ready = scheduler.get_ready_tests()
        assert len(ready) == 2

    def test_get_ready_tests_with_deps(self):
        """Test getting ready tests with dependencies"""
        scheduler = DependencyScheduler()
        tests = [
            TestItem("t1", "f1", "s1"),
            TestItem("t2", "f1", "s2", dependencies=["t1"])
        ]
        scheduler.add_tests(tests)

        # First round: only t1 should be ready
        ready = scheduler.get_ready_tests()
        assert len(ready) == 1
        assert ready[0].id == "t1"

        # Mark t1 completed
        scheduler.mark_completed("t1")

        # Second round: t2 should now be ready
        ready = scheduler.get_ready_tests()
        assert len(ready) == 1
        assert ready[0].id == "t2"

    def test_priority_ordering(self):
        """Test priority-based ordering"""
        scheduler = DependencyScheduler()
        tests = [
            TestItem("t1", "f1", "s1", priority=1),
            TestItem("t2", "f1", "s2", priority=10),
            TestItem("t3", "f1", "s3", priority=5)
        ]
        scheduler.add_tests(tests)

        ready = scheduler.get_ready_tests(max_count=3)
        assert ready[0].id == "t2"  # Highest priority first
        assert ready[1].id == "t3"
        assert ready[2].id == "t1"

    def test_mark_completed(self):
        """Test marking tests completed"""
        scheduler = DependencyScheduler()
        tests = [TestItem("t1", "f1", "s1")]
        scheduler.add_tests(tests)

        scheduler.get_ready_tests()  # Mark as running
        scheduler.mark_completed("t1")

        assert scheduler.completed_count == 1
        assert scheduler.pending_count == 0

    def test_reset(self):
        """Test scheduler reset"""
        scheduler = DependencyScheduler()
        tests = [TestItem("t1", "f1", "s1")]
        scheduler.add_tests(tests)

        scheduler.get_ready_tests()
        scheduler.mark_completed("t1")
        scheduler.reset()

        assert scheduler.completed_count == 0


class TestWorkerResultCollector:
    """Tests for WorkerResultCollector class"""

    def test_add_result(self):
        """Test adding results"""
        collector = WorkerResultCollector()
        result = TestResult("t1", "w1", "passed")
        collector.add_result(result)

        summary = collector.get_summary()
        assert summary['total'] == 1
        assert summary['passed'] == 1

    def test_multiple_results(self):
        """Test multiple results"""
        collector = WorkerResultCollector()
        collector.add_result(TestResult("t1", "w1", "passed"))
        collector.add_result(TestResult("t2", "w1", "failed"))
        collector.add_result(TestResult("t3", "w2", "skipped"))

        summary = collector.get_summary()
        assert summary['total'] == 3
        assert summary['passed'] == 1
        assert summary['failed'] == 1
        assert summary['skipped'] == 1

    def test_get_results(self):
        """Test getting all results"""
        collector = WorkerResultCollector()
        collector.add_result(TestResult("t1", "w1", "passed"))
        collector.add_result(TestResult("t2", "w1", "passed"))

        results = collector.get_results()
        assert len(results) == 2

    def test_clear(self):
        """Test clearing results"""
        collector = WorkerResultCollector()
        collector.add_result(TestResult("t1", "w1", "passed"))
        collector.clear()

        summary = collector.get_summary()
        assert summary['total'] == 0

    def test_thread_safety(self):
        """Test thread safety of result collection"""
        collector = WorkerResultCollector()

        def add_results(worker_id: str):
            for i in range(100):
                collector.add_result(TestResult(f"t-{worker_id}-{i}", worker_id, "passed"))

        threads = [Thread(target=add_results, args=(f"w{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        summary = collector.get_summary()
        assert summary['total'] == 500


class TestParallelTestRunner:
    """Tests for ParallelTestRunner class"""

    def test_initialization(self):
        """Test runner initialization"""
        runner = ParallelTestRunner(max_workers=4)
        assert runner.max_workers == 4
        assert runner.use_xdist is False

    def test_initialization_with_xdist(self):
        """Test runner with xdist enabled"""
        runner = ParallelTestRunner(max_workers=4, use_xdist=True)
        assert runner.use_xdist is True

    def test_initialization_with_pools(self):
        """Test runner with resource pools"""
        runner = ParallelTestRunner(
            max_workers=4,
            resource_pools={ResourceType.DATABASE: 2}
        )
        assert ResourceType.DATABASE in runner._pools

    def test_run_parallel_single_test(self):
        """Test running a single test"""
        runner = ParallelTestRunner(max_workers=2)

        tests = [TestItem("t1", "f1", "s1")]

        def mock_runner(test: TestItem, worker_id: str) -> TestResult:
            return TestResult(test.id, worker_id, "passed", duration=0.1)

        result = runner.run_parallel(tests, mock_runner)

        assert result.total_tests == 1
        assert result.passed == 1
        assert result.failed == 0

    def test_run_parallel_multiple_tests(self):
        """Test running multiple tests"""
        runner = ParallelTestRunner(max_workers=4)

        tests = [
            TestItem("t1", "f1", "s1"),
            TestItem("t2", "f1", "s2"),
            TestItem("t3", "f1", "s3"),
            TestItem("t4", "f1", "s4")
        ]

        def mock_runner(test: TestItem, worker_id: str) -> TestResult:
            time.sleep(0.05)
            return TestResult(test.id, worker_id, "passed", duration=0.05)

        result = runner.run_parallel(tests, mock_runner)

        assert result.total_tests == 4
        assert result.passed == 4
        assert result.worker_count <= 4

    def test_run_parallel_with_dependencies(self):
        """Test running tests with dependencies"""
        runner = ParallelTestRunner(max_workers=2)

        execution_order = []

        tests = [
            TestItem("t1", "f1", "s1"),
            TestItem("t2", "f1", "s2", dependencies=["t1"]),
            TestItem("t3", "f1", "s3", dependencies=["t2"])
        ]

        def tracking_runner(test: TestItem, worker_id: str) -> TestResult:
            execution_order.append(test.id)
            time.sleep(0.05)
            return TestResult(test.id, worker_id, "passed", duration=0.05)

        result = runner.run_parallel(tests, tracking_runner)

        # t1 must run before t2, t2 before t3
        assert execution_order.index("t1") < execution_order.index("t2")
        assert execution_order.index("t2") < execution_order.index("t3")
        assert result.passed == 3

    def test_run_parallel_with_failure(self):
        """Test handling test failures"""
        runner = ParallelTestRunner(max_workers=2)

        tests = [
            TestItem("t1", "f1", "s1"),
            TestItem("t2", "f1", "s2")
        ]

        def failing_runner(test: TestItem, worker_id: str) -> TestResult:
            if test.id == "t1":
                return TestResult(test.id, worker_id, "failed", error_message="Error")
            return TestResult(test.id, worker_id, "passed")

        result = runner.run_parallel(tests, failing_runner)

        assert result.total_tests == 2
        assert result.passed == 1
        assert result.failed == 1

    def test_run_parallel_with_exception(self):
        """Test handling test exceptions"""
        runner = ParallelTestRunner(max_workers=2)

        tests = [
            TestItem("t1", "f1", "s1"),
            TestItem("t2", "f1", "s2")
        ]

        def exception_runner(test: TestItem, worker_id: str) -> TestResult:
            if test.id == "t1":
                raise ValueError("Test error")
            return TestResult(test.id, worker_id, "passed")

        result = runner.run_parallel(tests, exception_runner)

        assert result.total_tests == 2
        # t1 should be marked as failed due to exception
        assert result.failed >= 1

    def test_resource_pool_integration(self):
        """Test resource pool usage in parallel runner"""
        runner = ParallelTestRunner(
            max_workers=2,
            resource_pools={ResourceType.DATABASE: 2}
        )

        runner.initialize_pool(
            ResourceType.DATABASE,
            lambda: {"connection": "mock"}
        )

        tests = [
            TestItem("t1", "f1", "s1", resource_requirements=[ResourceType.DATABASE]),
            TestItem("t2", "f1", "s2", resource_requirements=[ResourceType.DATABASE])
        ]

        def db_runner(test: TestItem, worker_id: str) -> TestResult:
            if ResourceType.DATABASE in test.resource_requirements:
                db = runner.acquire_resource(ResourceType.DATABASE)
                time.sleep(0.05)
                runner.release_resource(ResourceType.DATABASE, db)
            return TestResult(test.id, worker_id, "passed")

        result = runner.run_parallel(tests, db_runner)

        assert result.passed == 2
        runner.cleanup()

    def test_stop(self):
        """Test stopping the runner"""
        runner = ParallelTestRunner(max_workers=2)
        runner.stop()
        assert runner._stop_event.is_set()

    def test_cleanup(self):
        """Test cleanup"""
        runner = ParallelTestRunner(
            max_workers=2,
            resource_pools={ResourceType.DATABASE: 2}
        )
        runner.initialize_pool(ResourceType.DATABASE, lambda: "conn")
        runner.cleanup()
        # Should not raise


class TestUtilityFunctions:
    """Tests for utility functions"""

    def test_estimate_test_duration_no_history(self):
        """Test duration estimation without history"""
        duration = estimate_test_duration("test-1")
        assert duration == 1.0  # Default

    def test_estimate_test_duration_with_history(self):
        """Test duration estimation with history"""
        history = [
            {'test_id': 'test-1', 'duration': 2.0},
            {'test_id': 'test-1', 'duration': 3.0},
            {'test_id': 'test-1', 'duration': 2.5}
        ]
        duration = estimate_test_duration("test-1", history)
        assert duration == 2.5  # Average of 2.0, 3.0, 2.5


class TestWorkerState:
    """Tests for WorkerState enum"""

    def test_state_values(self):
        """Test state enum values"""
        assert WorkerState.IDLE.value == "idle"
        assert WorkerState.RUNNING.value == "running"
        assert WorkerState.COMPLETED.value == "completed"
        assert WorkerState.FAILED.value == "failed"


class TestResourceType:
    """Tests for ResourceType enum"""

    def test_resource_values(self):
        """Test resource type enum values"""
        assert ResourceType.DATABASE.value == "database"
        assert ResourceType.API_CLIENT.value == "api_client"
        assert ResourceType.BROWSER.value == "browser"
        assert ResourceType.CUSTOM.value == "custom"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
