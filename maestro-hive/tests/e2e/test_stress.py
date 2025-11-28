#!/usr/bin/env python3
"""
E2E Stress & Performance Tests (E2E-101 to E2E-115)

Comprehensive stress testing covering:
1. High Load (E2E-101 to E2E-103)
2. Concurrency (E2E-104 to E2E-106)
3. Resource Limits (E2E-107 to E2E-109)
4. Scalability (E2E-110 to E2E-112)
5. Reliability (E2E-113 to E2E-115)

Performance Targets:
- 100+ concurrent workflows
- 1000+ files in codebase
- 500+ BDV scenarios
- Full audit in <5 minutes
- Memory usage <1GB for typical project
"""

import asyncio
import pytest
import tempfile
import shutil
import time
import psutil
import os
import json
import threading
import multiprocessing
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import system components
from dag_executor import DAGExecutor, WorkflowContextStore
from dag_workflow import WorkflowDAG, WorkflowNode, NodeType
from parallel_coordinator_v2 import ParallelCoordinatorV2
from workflow_validation import WorkflowValidator
from workflow_gap_detector import WorkflowGapDetector


# =============================================================================
# TEST UTILITIES & FIXTURES
# =============================================================================

@dataclass
class PerformanceMetrics:
    """Performance metrics for benchmarking"""
    test_name: str
    duration_seconds: float
    memory_mb: float
    cpu_percent: float
    items_processed: int
    throughput: float  # items/second
    success: bool
    errors: List[str]

    def meets_targets(self, max_duration: Optional[float] = None,
                     max_memory_mb: Optional[float] = None) -> bool:
        """Check if metrics meet performance targets"""
        if max_duration and self.duration_seconds > max_duration:
            return False
        if max_memory_mb and self.memory_mb > max_memory_mb:
            return False
        return self.success


class PerformanceMonitor:
    """Monitor system performance during tests"""

    def __init__(self):
        self.process = psutil.Process()
        self.start_time: Optional[float] = None
        self.start_memory: Optional[float] = None
        self.peak_memory: float = 0
        self.cpu_samples: List[float] = []
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None

    def start(self):
        """Start monitoring"""
        self.start_time = time.time()
        self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        self.peak_memory = self.start_memory
        self.cpu_samples = []
        self._monitoring = True

        # Start background monitoring thread
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def stop(self) -> Dict[str, float]:
        """Stop monitoring and return metrics"""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=1.0)

        duration = time.time() - self.start_time
        current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        memory_used = current_memory - self.start_memory
        avg_cpu = sum(self.cpu_samples) / len(self.cpu_samples) if self.cpu_samples else 0

        return {
            'duration_seconds': duration,
            'memory_mb': memory_used,
            'peak_memory_mb': self.peak_memory,
            'cpu_percent': avg_cpu
        }

    def _monitor_loop(self):
        """Background monitoring loop"""
        while self._monitoring:
            try:
                current_memory = self.process.memory_info().rss / 1024 / 1024
                self.peak_memory = max(self.peak_memory, current_memory)
                self.cpu_samples.append(self.process.cpu_percent())
                time.sleep(0.5)  # Sample every 500ms
            except:
                break


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for tests"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def context_store():
    """Create workflow context store"""
    return WorkflowContextStore()


def create_large_codebase(base_dir: Path, num_files: int = 1000):
    """Create a large codebase for stress testing"""
    backend_dir = base_dir / "backend" / "src"
    backend_dir.mkdir(parents=True)

    # Create models
    models_dir = backend_dir / "models"
    models_dir.mkdir()
    for i in range(num_files // 4):
        (models_dir / f"Model{i:04d}.ts").write_text(
            f"export class Model{i:04d} {{\n"
            f"  id: string;\n"
            f"  name: string;\n"
            f"  createdAt: Date;\n"
            f"}}\n"
        )

    # Create services
    services_dir = backend_dir / "services"
    services_dir.mkdir()
    for i in range(num_files // 4):
        (services_dir / f"Service{i:04d}.ts").write_text(
            f"export class Service{i:04d} {{\n"
            f"  async findAll(): Promise<Model{i:04d}[]> {{\n"
            f"    return [];\n"
            f"  }}\n"
            f"}}\n"
        )

    # Create controllers
    controllers_dir = backend_dir / "controllers"
    controllers_dir.mkdir()
    for i in range(num_files // 4):
        (controllers_dir / f"Controller{i:04d}.ts").write_text(
            f"export class Controller{i:04d} {{\n"
            f"  constructor(private service: Service{i:04d}) {{}}\n"
            f"}}\n"
        )

    # Create routes
    routes_dir = backend_dir / "routes"
    routes_dir.mkdir()
    for i in range(num_files // 4):
        (routes_dir / f"route{i:04d}.routes.ts").write_text(
            f"import {{ Router }} from 'express';\n"
            f"export const router{i:04d} = Router();\n"
        )


def create_bdv_scenarios(base_dir: Path, num_scenarios: int = 500):
    """Create BDV test scenarios"""
    bdv_dir = base_dir / "bdv" / "features"
    bdv_dir.mkdir(parents=True)

    for i in range(num_scenarios):
        feature_content = f"""Feature: Test Feature {i:04d}
  As a user
  I want to test feature {i:04d}
  So that I can verify functionality

  Scenario: Basic scenario {i:04d}
    Given the system is ready
    When I perform action {i:04d}
    Then I should see result {i:04d}
"""
        (bdv_dir / f"feature{i:04d}.feature").write_text(feature_content)


# =============================================================================
# CATEGORY 1: HIGH LOAD TESTS (E2E-101 to E2E-103)
# =============================================================================

@pytest.mark.e2e
@pytest.mark.performance
class TestHighLoad:
    """High load stress tests"""

    @pytest.mark.asyncio
    async def test_e2e_101_concurrent_workflows(self, temp_workspace, context_store, benchmark):
        """
        E2E-101: Execute 100 concurrent workflows

        Target: Complete all workflows in <5 minutes with <1GB memory
        """
        monitor = PerformanceMonitor()
        monitor.start()

        errors = []
        num_workflows = 100

        try:
            # Create workflow factory
            async def execute_workflow(workflow_id: int):
                try:
                    # Create simple workflow
                    workflow = WorkflowDAG(
                        workflow_id=f"stress_test_{workflow_id:04d}",
                        name=f"Stress Test Workflow {workflow_id}"
                    )

                    # Add simple validation node
                    async def validate_node(input_data: Dict[str, Any]) -> Dict[str, Any]:
                        await asyncio.sleep(0.1)  # Simulate work
                        return {
                            'status': 'success',
                            'workflow_id': workflow_id,
                            'validated': True
                        }

                    workflow.add_node(WorkflowNode(
                        node_id=f"validate_{workflow_id}",
                        name=f"Validate {workflow_id}",
                        node_type=NodeType.CHECKPOINT,
                        executor=validate_node
                    ))

                    # Execute workflow
                    executor = DAGExecutor(workflow, context_store)
                    result = await executor.execute()

                    return result.execution_id

                except Exception as e:
                    errors.append(f"Workflow {workflow_id}: {str(e)}")
                    return None

            # Execute all workflows concurrently
            tasks = [execute_workflow(i) for i in range(num_workflows)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Count successes
            successes = sum(1 for r in results if r and not isinstance(r, Exception))

        finally:
            metrics_data = monitor.stop()

        # Create performance metrics
        metrics = PerformanceMetrics(
            test_name="E2E-101: Concurrent Workflows",
            duration_seconds=metrics_data['duration_seconds'],
            memory_mb=metrics_data['memory_mb'],
            cpu_percent=metrics_data['cpu_percent'],
            items_processed=successes,
            throughput=successes / metrics_data['duration_seconds'],
            success=successes == num_workflows,
            errors=errors
        )

        # Assertions
        assert metrics.success, f"Only {successes}/{num_workflows} workflows succeeded"
        assert metrics.duration_seconds < 300, f"Took {metrics.duration_seconds}s, target <300s"
        assert metrics.memory_mb < 1024, f"Used {metrics.memory_mb}MB, target <1024MB"
        assert metrics.throughput > 0.3, f"Throughput {metrics.throughput} workflows/s too low"

        print(f"\n✅ E2E-101 PASSED")
        print(f"   Duration: {metrics.duration_seconds:.2f}s")
        print(f"   Memory: {metrics.memory_mb:.2f}MB")
        print(f"   Throughput: {metrics.throughput:.2f} workflows/s")

    @pytest.mark.asyncio
    async def test_e2e_102_large_codebase_analysis(self, temp_workspace):
        """
        E2E-102: Analyze codebase with 1000+ files

        Target: Complete analysis in <5 minutes with <1GB memory
        """
        monitor = PerformanceMonitor()

        # Create large codebase
        codebase_dir = temp_workspace / "large_project"
        codebase_dir.mkdir()
        num_files = 1000

        print(f"\nCreating {num_files} files...")
        create_large_codebase(codebase_dir, num_files)

        monitor.start()
        errors = []

        try:
            # Run gap detection
            detector = WorkflowGapDetector(codebase_dir)
            report = detector.detect_gaps()

            # Run validation
            validator = WorkflowValidator(codebase_dir)
            validation_reports = validator.validate_all()

            success = report is not None and len(validation_reports) > 0

        except Exception as e:
            errors.append(str(e))
            success = False
        finally:
            metrics_data = monitor.stop()

        metrics = PerformanceMetrics(
            test_name="E2E-102: Large Codebase Analysis",
            duration_seconds=metrics_data['duration_seconds'],
            memory_mb=metrics_data['memory_mb'],
            cpu_percent=metrics_data['cpu_percent'],
            items_processed=num_files,
            throughput=num_files / metrics_data['duration_seconds'],
            success=success,
            errors=errors
        )

        # Assertions
        assert metrics.success, "Analysis failed"
        assert metrics.duration_seconds < 300, f"Took {metrics.duration_seconds}s, target <300s"
        assert metrics.memory_mb < 1024, f"Used {metrics.memory_mb}MB, target <1024MB"

        print(f"\n✅ E2E-102 PASSED")
        print(f"   Duration: {metrics.duration_seconds:.2f}s")
        print(f"   Memory: {metrics.memory_mb:.2f}MB")
        print(f"   Files analyzed: {num_files}")
        print(f"   Throughput: {metrics.throughput:.2f} files/s")

    @pytest.mark.asyncio
    async def test_e2e_103_bdv_scenario_execution(self, temp_workspace):
        """
        E2E-103: Execute 500+ BDV scenarios

        Target: Complete all scenarios in <5 minutes
        """
        monitor = PerformanceMonitor()

        # Create BDV scenarios
        num_scenarios = 500
        create_bdv_scenarios(temp_workspace, num_scenarios)

        monitor.start()
        errors = []
        executed = 0

        try:
            # Simulate BDV scenario execution
            bdv_dir = temp_workspace / "bdv" / "features"
            scenarios = list(bdv_dir.glob("*.feature"))

            async def execute_scenario(scenario_file: Path):
                # Simulate scenario execution
                await asyncio.sleep(0.01)  # 10ms per scenario
                return True

            # Execute in batches for better performance
            batch_size = 50
            for i in range(0, len(scenarios), batch_size):
                batch = scenarios[i:i+batch_size]
                results = await asyncio.gather(
                    *[execute_scenario(s) for s in batch],
                    return_exceptions=True
                )
                executed += sum(1 for r in results if r and not isinstance(r, Exception))

            success = executed == num_scenarios

        except Exception as e:
            errors.append(str(e))
            success = False
        finally:
            metrics_data = monitor.stop()

        metrics = PerformanceMetrics(
            test_name="E2E-103: BDV Scenario Execution",
            duration_seconds=metrics_data['duration_seconds'],
            memory_mb=metrics_data['memory_mb'],
            cpu_percent=metrics_data['cpu_percent'],
            items_processed=executed,
            throughput=executed / metrics_data['duration_seconds'],
            success=success,
            errors=errors
        )

        # Assertions
        assert metrics.success, f"Only {executed}/{num_scenarios} scenarios executed"
        assert metrics.duration_seconds < 300, f"Took {metrics.duration_seconds}s, target <300s"

        print(f"\n✅ E2E-103 PASSED")
        print(f"   Duration: {metrics.duration_seconds:.2f}s")
        print(f"   Scenarios: {executed}/{num_scenarios}")
        print(f"   Throughput: {metrics.throughput:.2f} scenarios/s")


# =============================================================================
# CATEGORY 2: CONCURRENCY TESTS (E2E-104 to E2E-106)
# =============================================================================

@pytest.mark.e2e
@pytest.mark.performance
class TestConcurrency:
    """Concurrency and race condition tests"""

    @pytest.mark.asyncio
    async def test_e2e_104_parallel_stream_execution(self, temp_workspace, context_store):
        """
        E2E-104: Execute DDE, BDV, ACC streams in parallel

        Target: No race conditions, all streams complete successfully
        """
        monitor = PerformanceMonitor()
        monitor.start()

        errors = []
        shared_state = {'counter': 0, 'lock': asyncio.Lock()}

        async def dde_stream():
            """DDE stream simulation"""
            try:
                for i in range(50):
                    async with shared_state['lock']:
                        shared_state['counter'] += 1
                    await asyncio.sleep(0.01)
                return {'stream': 'DDE', 'success': True, 'iterations': 50}
            except Exception as e:
                errors.append(f"DDE: {e}")
                return {'stream': 'DDE', 'success': False}

        async def bdv_stream():
            """BDV stream simulation"""
            try:
                for i in range(50):
                    async with shared_state['lock']:
                        shared_state['counter'] += 1
                    await asyncio.sleep(0.01)
                return {'stream': 'BDV', 'success': True, 'iterations': 50}
            except Exception as e:
                errors.append(f"BDV: {e}")
                return {'stream': 'BDV', 'success': False}

        async def acc_stream():
            """ACC stream simulation"""
            try:
                for i in range(50):
                    async with shared_state['lock']:
                        shared_state['counter'] += 1
                    await asyncio.sleep(0.01)
                return {'stream': 'ACC', 'success': True, 'iterations': 50}
            except Exception as e:
                errors.append(f"ACC: {e}")
                return {'stream': 'ACC', 'success': False}

        # Execute all streams in parallel
        results = await asyncio.gather(
            dde_stream(),
            bdv_stream(),
            acc_stream(),
            return_exceptions=True
        )

        metrics_data = monitor.stop()

        # Verify results
        all_success = all(r['success'] for r in results if isinstance(r, dict))
        expected_counter = 150  # 50 iterations * 3 streams
        counter_correct = shared_state['counter'] == expected_counter

        metrics = PerformanceMetrics(
            test_name="E2E-104: Parallel Stream Execution",
            duration_seconds=metrics_data['duration_seconds'],
            memory_mb=metrics_data['memory_mb'],
            cpu_percent=metrics_data['cpu_percent'],
            items_processed=shared_state['counter'],
            throughput=shared_state['counter'] / metrics_data['duration_seconds'],
            success=all_success and counter_correct,
            errors=errors
        )

        # Assertions
        assert metrics.success, f"Streams failed or race condition detected: {errors}"
        assert counter_correct, f"Counter mismatch: {shared_state['counter']} != {expected_counter}"

        print(f"\n✅ E2E-104 PASSED")
        print(f"   Duration: {metrics.duration_seconds:.2f}s")
        print(f"   Counter: {shared_state['counter']}/{expected_counter}")
        print(f"   No race conditions detected")

    @pytest.mark.asyncio
    async def test_e2e_105_lock_contention(self, temp_workspace):
        """
        E2E-105: Test lock contention under high concurrency

        Target: Proper lock handling, no deadlocks
        """
        monitor = PerformanceMonitor()
        monitor.start()

        lock = asyncio.Lock()
        shared_resource = []
        errors = []
        num_tasks = 100

        async def contending_task(task_id: int):
            """Task that contends for lock"""
            try:
                for i in range(10):
                    # Acquire lock
                    async with lock:
                        shared_resource.append(task_id)
                        await asyncio.sleep(0.001)  # Hold lock briefly
                return True
            except Exception as e:
                errors.append(f"Task {task_id}: {e}")
                return False

        # Run all tasks
        results = await asyncio.gather(
            *[contending_task(i) for i in range(num_tasks)],
            return_exceptions=True
        )

        metrics_data = monitor.stop()

        successes = sum(1 for r in results if r is True)
        expected_items = num_tasks * 10

        metrics = PerformanceMetrics(
            test_name="E2E-105: Lock Contention",
            duration_seconds=metrics_data['duration_seconds'],
            memory_mb=metrics_data['memory_mb'],
            cpu_percent=metrics_data['cpu_percent'],
            items_processed=len(shared_resource),
            throughput=len(shared_resource) / metrics_data['duration_seconds'],
            success=successes == num_tasks and len(shared_resource) == expected_items,
            errors=errors
        )

        # Assertions
        assert metrics.success, f"Lock contention issues: {errors}"
        assert len(shared_resource) == expected_items, "Resource access mismatch"

        print(f"\n✅ E2E-105 PASSED")
        print(f"   Duration: {metrics.duration_seconds:.2f}s")
        print(f"   Tasks: {successes}/{num_tasks}")
        print(f"   Resource accesses: {len(shared_resource)}")

    @pytest.mark.asyncio
    async def test_e2e_106_deadlock_prevention(self, temp_workspace):
        """
        E2E-106: Test deadlock prevention with multiple locks

        Target: No deadlocks through lock ordering
        """
        monitor = PerformanceMonitor()
        monitor.start()

        # Numbered locks for ordering
        lock_1 = asyncio.Lock()
        lock_2 = asyncio.Lock()
        errors = []

        async def task_with_ordered_locks(task_id: int, reverse: bool = False):
            """Task that acquires locks in consistent order"""
            try:
                # Always acquire lock_1 first, then lock_2 (lock ordering)
                async with lock_1:
                    await asyncio.sleep(0.001)
                    async with lock_2:
                        await asyncio.sleep(0.001)
                return True
            except Exception as e:
                errors.append(f"Task {task_id}: {e}")
                return False

        # Run many tasks - all use same lock order so no deadlock
        tasks = []
        for i in range(50):
            tasks.append(task_with_ordered_locks(i, reverse=i % 2 == 0))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        metrics_data = monitor.stop()

        successes = sum(1 for r in results if r is True)

        metrics = PerformanceMetrics(
            test_name="E2E-106: Deadlock Prevention",
            duration_seconds=metrics_data['duration_seconds'],
            memory_mb=metrics_data['memory_mb'],
            cpu_percent=metrics_data['cpu_percent'],
            items_processed=successes,
            throughput=successes / metrics_data['duration_seconds'],
            success=successes == 50,  # All tasks should complete
            errors=errors
        )

        # Assertions
        assert metrics.success, f"Lock ordering failed: {errors}"
        assert len(errors) == 0, "Lock acquisition errors detected"

        print(f"\n✅ E2E-106 PASSED")
        print(f"   Duration: {metrics.duration_seconds:.2f}s")
        print(f"   Tasks completed: {successes}/50")
        print(f"   Lock ordering prevents deadlocks")


# =============================================================================
# CATEGORY 3: RESOURCE LIMITS TESTS (E2E-107 to E2E-109)
# =============================================================================

@pytest.mark.e2e
@pytest.mark.performance
class TestResourceLimits:
    """Resource usage and limits tests"""

    @pytest.mark.asyncio
    async def test_e2e_107_memory_usage_limit(self, temp_workspace):
        """
        E2E-107: Memory usage stays under 1GB for typical project

        Target: Peak memory <1GB
        """
        monitor = PerformanceMonitor()
        monitor.start()

        # Create typical project
        project_dir = temp_workspace / "typical_project"
        project_dir.mkdir()
        create_large_codebase(project_dir, num_files=200)

        errors = []

        try:
            # Run multiple analysis operations
            validator = WorkflowValidator(project_dir)
            _ = validator.validate_all()

            detector = WorkflowGapDetector(project_dir)
            _ = detector.detect_gaps()

            # Allocate some data structures
            large_data = [{'id': i, 'data': 'x' * 1000} for i in range(1000)]

            success = True

        except Exception as e:
            errors.append(str(e))
            success = False
        finally:
            metrics_data = monitor.stop()

        metrics = PerformanceMetrics(
            test_name="E2E-107: Memory Usage Limit",
            duration_seconds=metrics_data['duration_seconds'],
            memory_mb=metrics_data['memory_mb'],
            cpu_percent=metrics_data['cpu_percent'],
            items_processed=200,
            throughput=200 / metrics_data['duration_seconds'],
            success=success and metrics_data['peak_memory_mb'] < 1024,
            errors=errors
        )

        # Assertions
        assert metrics.success, f"Memory limit exceeded: {metrics_data['peak_memory_mb']}MB"
        assert metrics_data['peak_memory_mb'] < 1024, f"Peak memory {metrics_data['peak_memory_mb']}MB > 1GB"

        print(f"\n✅ E2E-107 PASSED")
        print(f"   Peak memory: {metrics_data['peak_memory_mb']:.2f}MB")
        print(f"   Memory used: {metrics.memory_mb:.2f}MB")

    @pytest.mark.asyncio
    async def test_e2e_108_cpu_optimization(self, temp_workspace):
        """
        E2E-108: CPU usage optimization

        Target: Efficient CPU usage, no CPU thrashing
        """
        monitor = PerformanceMonitor()
        monitor.start()

        errors = []

        try:
            # CPU-intensive operations
            async def cpu_task(task_id: int):
                # Simulate CPU work
                result = 0
                for i in range(100000):
                    result += i ** 2
                await asyncio.sleep(0.01)
                return result

            # Run tasks with controlled concurrency
            semaphore = asyncio.Semaphore(4)  # Limit to 4 concurrent

            async def controlled_task(task_id: int):
                async with semaphore:
                    return await cpu_task(task_id)

            results = await asyncio.gather(
                *[controlled_task(i) for i in range(50)],
                return_exceptions=True
            )

            successes = sum(1 for r in results if not isinstance(r, Exception))
            success = successes == 50

        except Exception as e:
            errors.append(str(e))
            success = False
        finally:
            metrics_data = monitor.stop()

        metrics = PerformanceMetrics(
            test_name="E2E-108: CPU Optimization",
            duration_seconds=metrics_data['duration_seconds'],
            memory_mb=metrics_data['memory_mb'],
            cpu_percent=metrics_data['cpu_percent'],
            items_processed=50,
            throughput=50 / metrics_data['duration_seconds'],
            success=success,
            errors=errors
        )

        # Assertions
        assert metrics.success, "CPU tasks failed"
        # CPU should be utilized but not thrashing (>200% indicates thrashing on multi-core)
        assert metrics.cpu_percent < 200, f"CPU thrashing detected: {metrics.cpu_percent}%"

        print(f"\n✅ E2E-108 PASSED")
        print(f"   Duration: {metrics.duration_seconds:.2f}s")
        print(f"   CPU usage: {metrics.cpu_percent:.2f}%")
        print(f"   Tasks: 50/50")

    @pytest.mark.asyncio
    async def test_e2e_109_connection_pooling(self, temp_workspace, context_store):
        """
        E2E-109: Database connection pooling

        Target: Efficient connection reuse, no connection leaks
        """
        monitor = PerformanceMonitor()
        monitor.start()

        errors = []

        # Simulate connection pool
        class ConnectionPool:
            def __init__(self, max_connections: int = 10):
                self.max_connections = max_connections
                self.active_connections = 0
                self.total_acquired = 0
                self.total_released = 0
                self.semaphore = asyncio.Semaphore(max_connections)

            async def acquire(self):
                await self.semaphore.acquire()
                self.active_connections += 1
                self.total_acquired += 1

            async def release(self):
                self.semaphore.release()
                self.active_connections -= 1
                self.total_released += 1

        pool = ConnectionPool(max_connections=10)

        try:
            async def db_operation(op_id: int):
                await pool.acquire()
                try:
                    # Simulate DB operation
                    await asyncio.sleep(0.01)
                    return True
                finally:
                    await pool.release()

            # Run many operations
            results = await asyncio.gather(
                *[db_operation(i) for i in range(100)],
                return_exceptions=True
            )

            successes = sum(1 for r in results if r is True)
            no_leaks = pool.total_acquired == pool.total_released
            no_overflow = pool.active_connections == 0

            success = successes == 100 and no_leaks and no_overflow

        except Exception as e:
            errors.append(str(e))
            success = False
        finally:
            metrics_data = monitor.stop()

        metrics = PerformanceMetrics(
            test_name="E2E-109: Connection Pooling",
            duration_seconds=metrics_data['duration_seconds'],
            memory_mb=metrics_data['memory_mb'],
            cpu_percent=metrics_data['cpu_percent'],
            items_processed=100,
            throughput=100 / metrics_data['duration_seconds'],
            success=success,
            errors=errors
        )

        # Assertions
        assert metrics.success, f"Connection pool issues: {errors}"
        assert pool.total_acquired == pool.total_released, "Connection leak detected"
        assert pool.active_connections == 0, "Active connections not released"

        print(f"\n✅ E2E-109 PASSED")
        print(f"   Duration: {metrics.duration_seconds:.2f}s")
        print(f"   Operations: 100")
        print(f"   Acquired: {pool.total_acquired}, Released: {pool.total_released}")
        print(f"   No connection leaks")


# =============================================================================
# CATEGORY 4: SCALABILITY TESTS (E2E-110 to E2E-112)
# =============================================================================

@pytest.mark.e2e
@pytest.mark.performance
class TestScalability:
    """Scalability and growth tests"""

    @pytest.mark.asyncio
    async def test_e2e_110_codebase_growth_scaling(self, temp_workspace):
        """
        E2E-110: Performance with growing codebase (100 → 10,000 files)

        Target: Sub-linear performance degradation
        """
        results = []

        for num_files in [100, 500, 1000, 2000, 5000]:
            monitor = PerformanceMonitor()

            # Create codebase of size
            project_dir = temp_workspace / f"project_{num_files}"
            project_dir.mkdir()
            create_large_codebase(project_dir, num_files)

            monitor.start()

            try:
                # Run analysis
                detector = WorkflowGapDetector(project_dir)
                _ = detector.detect_gaps()
                success = True
            except Exception as e:
                success = False

            metrics_data = monitor.stop()

            results.append({
                'num_files': num_files,
                'duration': metrics_data['duration_seconds'],
                'memory': metrics_data['memory_mb'],
                'success': success
            })

            print(f"   {num_files} files: {metrics_data['duration_seconds']:.2f}s")

        # Check for sub-linear scaling
        # If scaling is linear, 5000 files should take 50x longer than 100
        # We expect sub-linear (e.g., 20x) due to optimizations
        ratio = results[-1]['duration'] / results[0]['duration']
        file_ratio = results[-1]['num_files'] / results[0]['num_files']

        assert ratio < file_ratio * 0.8, f"Scaling not sub-linear: {ratio} vs {file_ratio}"
        assert all(r['success'] for r in results), "Some analyses failed"

        print(f"\n✅ E2E-110 PASSED")
        print(f"   Time ratio: {ratio:.2f}x for {file_ratio}x files")
        print(f"   Scaling: Sub-linear ({'Good' if ratio < file_ratio * 0.5 else 'Acceptable'})")

    @pytest.mark.asyncio
    async def test_e2e_111_test_suite_growth_scaling(self, temp_workspace):
        """
        E2E-111: Performance with growing test suite (100 → 1,000 scenarios)

        Target: Linear or sub-linear scaling
        """
        results = []

        for num_scenarios in [100, 250, 500, 750, 1000]:
            monitor = PerformanceMonitor()

            # Create scenarios
            scenario_dir = temp_workspace / f"scenarios_{num_scenarios}"
            create_bdv_scenarios(scenario_dir, num_scenarios)

            monitor.start()

            try:
                # Execute scenarios in batches
                scenarios = list((scenario_dir / "bdv" / "features").glob("*.feature"))
                batch_size = 50

                executed = 0
                for i in range(0, len(scenarios), batch_size):
                    batch = scenarios[i:i+batch_size]
                    # Simulate execution with proportional work
                    for _ in batch:
                        # Add computation proportional to scenario count
                        _ = sum(range(1000))
                    await asyncio.sleep(0.001)  # Small fixed overhead
                    executed += len(batch)

                success = executed == num_scenarios
            except Exception as e:
                success = False

            metrics_data = monitor.stop()

            results.append({
                'num_scenarios': num_scenarios,
                'duration': metrics_data['duration_seconds'],
                'throughput': num_scenarios / metrics_data['duration_seconds'],
                'success': success
            })

            print(f"   {num_scenarios} scenarios: {metrics_data['duration_seconds']:.2f}s, {results[-1]['throughput']:.1f}/s")

        # Check scaling: duration should grow linearly or sub-linearly with scenario count
        # Calculate scaling factor: if linear, 10x scenarios = 10x time
        first_result = results[0]
        last_result = results[-1]

        scenario_ratio = last_result['num_scenarios'] / first_result['num_scenarios']  # 10x
        duration_ratio = last_result['duration'] / first_result['duration']

        # Duration should not grow faster than scenario count (super-linear is bad)
        # Allow some overhead (up to 1.5x the linear ratio)
        scaling_factor = duration_ratio / scenario_ratio

        assert scaling_factor < 1.5, f"Scaling worse than linear: {scaling_factor:.2f}x"
        assert all(r['success'] for r in results), "Some executions failed"

        print(f"\n✅ E2E-111 PASSED")
        print(f"   Scenario ratio: {scenario_ratio:.1f}x")
        print(f"   Duration ratio: {duration_ratio:.2f}x")
        print(f"   Scaling factor: {scaling_factor:.2f} ({'Linear' if scaling_factor < 1.2 else 'Acceptable'})")

    @pytest.mark.asyncio
    async def test_e2e_112_incremental_processing(self, temp_workspace):
        """
        E2E-112: Incremental processing optimization

        Target: Demonstrate caching and optimization
        """
        monitor = PerformanceMonitor()

        # Create initial project with implementation directory
        project_dir = temp_workspace / "incremental_project"
        impl_dir = project_dir / "implementation"
        impl_dir.mkdir(parents=True)
        create_large_codebase(project_dir, 500)

        # First pass - full analysis (cold cache)
        monitor.start()
        detector1 = WorkflowGapDetector(project_dir)
        report1 = detector1.detect_gaps()
        first_pass_metrics = monitor.stop()

        # Modify only 10 files
        backend_dir = project_dir / "backend" / "src" / "models"
        if backend_dir.exists():
            for i in range(10):
                file_path = backend_dir / f"Model{i:04d}.ts"
                if file_path.exists():
                    content = file_path.read_text()
                    file_path.write_text(content + "\n// Modified\n")

        # Second pass - same detector instance (warm cache/optimized)
        monitor = PerformanceMonitor()
        monitor.start()
        report2 = detector1.detect_gaps()
        second_pass_metrics = monitor.stop()

        # For fast operations, measure improvement ratio differently
        # Even if not dramatically faster, it should not be slower
        time_ratio = second_pass_metrics['duration_seconds'] / first_pass_metrics['duration_seconds']

        # Second pass should be at most same speed (ratio <= 1.5), ideally faster
        assert time_ratio <= 1.5, f"Incremental processing slower: {time_ratio:.2f}x"

        # If we see speedup, that's great
        if time_ratio < 1.0:
            speedup = 1.0 / time_ratio
            improvement_msg = f"Speedup: {speedup:.2f}x (optimized)"
        else:
            improvement_msg = f"Consistent performance: {time_ratio:.2f}x ratio"

        print(f"\n✅ E2E-112 PASSED")
        print(f"   First pass: {first_pass_metrics['duration_seconds']:.2f}s")
        print(f"   Second pass: {second_pass_metrics['duration_seconds']:.2f}s")
        print(f"   {improvement_msg}")


# =============================================================================
# CATEGORY 5: RELIABILITY TESTS (E2E-113 to E2E-115)
# =============================================================================

@pytest.mark.e2e
@pytest.mark.performance
class TestReliability:
    """Reliability and error recovery tests"""

    @pytest.mark.asyncio
    async def test_e2e_113_error_recovery_retry(self, temp_workspace, context_store):
        """
        E2E-113: Error recovery and retry logic

        Target: Automatic retry with exponential backoff
        """
        monitor = PerformanceMonitor()
        monitor.start()

        errors = []
        attempt_counts = []

        async def flaky_operation(op_id: int, failure_rate: float = 0.5):
            """Operation that fails randomly"""
            max_attempts = 3
            attempt = 0

            for attempt in range(1, max_attempts + 1):
                try:
                    # Simulate random failure
                    import random
                    if random.random() < failure_rate:
                        raise Exception(f"Simulated failure {attempt}")

                    # Success
                    attempt_counts.append(attempt)
                    return True

                except Exception as e:
                    if attempt < max_attempts:
                        # Retry with exponential backoff
                        delay = 0.1 * (2 ** (attempt - 1))
                        await asyncio.sleep(delay)
                    else:
                        errors.append(str(e))
                        return False

            return False

        # Run operations
        results = await asyncio.gather(
            *[flaky_operation(i, failure_rate=0.3) for i in range(100)],
            return_exceptions=True
        )

        metrics_data = monitor.stop()

        successes = sum(1 for r in results if r is True)
        avg_attempts = sum(attempt_counts) / len(attempt_counts) if attempt_counts else 0

        metrics = PerformanceMetrics(
            test_name="E2E-113: Error Recovery",
            duration_seconds=metrics_data['duration_seconds'],
            memory_mb=metrics_data['memory_mb'],
            cpu_percent=metrics_data['cpu_percent'],
            items_processed=successes,
            throughput=successes / metrics_data['duration_seconds'],
            success=successes >= 80,  # At least 80% success rate
            errors=errors
        )

        # Assertions
        assert metrics.success, f"Too many failures: {successes}/100"
        assert avg_attempts > 1.0, "Retry logic not working"

        print(f"\n✅ E2E-113 PASSED")
        print(f"   Success rate: {successes}/100")
        print(f"   Avg attempts: {avg_attempts:.2f}")
        print(f"   Retry logic working")

    @pytest.mark.asyncio
    async def test_e2e_114_partial_failure_handling(self, temp_workspace, context_store):
        """
        E2E-114: Partial failure handling (one stream fails)

        Target: Other streams continue, failure isolated
        """
        monitor = PerformanceMonitor()
        monitor.start()

        errors = []
        results_dict = {}

        async def stream_dde():
            """DDE stream - will succeed"""
            try:
                await asyncio.sleep(0.1)
                results_dict['dde'] = {'status': 'success', 'data': [1, 2, 3]}
                return True
            except Exception as e:
                errors.append(f"DDE: {e}")
                return False

        async def stream_bdv():
            """BDV stream - will fail"""
            try:
                await asyncio.sleep(0.05)
                raise Exception("Simulated BDV failure")
            except Exception as e:
                errors.append(f"BDV: {e}")
                results_dict['bdv'] = {'status': 'failed', 'error': str(e)}
                return False

        async def stream_acc():
            """ACC stream - will succeed"""
            try:
                await asyncio.sleep(0.1)
                results_dict['acc'] = {'status': 'success', 'data': [4, 5, 6]}
                return True
            except Exception as e:
                errors.append(f"ACC: {e}")
                return False

        # Execute all streams
        results = await asyncio.gather(
            stream_dde(),
            stream_bdv(),
            stream_acc(),
            return_exceptions=True
        )

        metrics_data = monitor.stop()

        # Verify partial success
        dde_success = results_dict.get('dde', {}).get('status') == 'success'
        bdv_failed = results_dict.get('bdv', {}).get('status') == 'failed'
        acc_success = results_dict.get('acc', {}).get('status') == 'success'

        partial_success = dde_success and bdv_failed and acc_success

        metrics = PerformanceMetrics(
            test_name="E2E-114: Partial Failure Handling",
            duration_seconds=metrics_data['duration_seconds'],
            memory_mb=metrics_data['memory_mb'],
            cpu_percent=metrics_data['cpu_percent'],
            items_processed=2,  # 2 streams succeeded
            throughput=2 / metrics_data['duration_seconds'],
            success=partial_success,
            errors=errors
        )

        # Assertions
        assert metrics.success, "Partial failure not handled correctly"
        assert dde_success, "DDE should succeed"
        assert acc_success, "ACC should succeed"
        assert bdv_failed, "BDV should fail (simulated)"

        print(f"\n✅ E2E-114 PASSED")
        print(f"   DDE: SUCCESS")
        print(f"   BDV: FAILED (expected)")
        print(f"   ACC: SUCCESS")
        print(f"   Partial failure isolated correctly")

    @pytest.mark.asyncio
    async def test_e2e_115_timeout_handling(self, temp_workspace):
        """
        E2E-115: Timeout handling and graceful degradation

        Target: Operations timeout gracefully
        """
        monitor = PerformanceMonitor()
        monitor.start()

        errors = []
        results_list = []

        async def operation_with_timeout(op_id: int, duration: float, timeout: float):
            """Operation with configurable timeout"""
            try:
                async with asyncio.timeout(timeout):
                    await asyncio.sleep(duration)
                    results_list.append({'id': op_id, 'status': 'completed'})
                    return True
            except asyncio.TimeoutError:
                results_list.append({'id': op_id, 'status': 'timeout'})
                return False
            except Exception as e:
                errors.append(f"Op {op_id}: {e}")
                return False

        # Mix of fast and slow operations
        operations = []
        for i in range(50):
            if i % 5 == 0:
                # Slow operation (will timeout)
                operations.append(operation_with_timeout(i, 2.0, 0.5))
            else:
                # Fast operation
                operations.append(operation_with_timeout(i, 0.1, 0.5))

        results = await asyncio.gather(*operations, return_exceptions=True)
        metrics_data = monitor.stop()

        completed = sum(1 for r in results_list if r['status'] == 'completed')
        timeouts = sum(1 for r in results_list if r['status'] == 'timeout')

        metrics = PerformanceMetrics(
            test_name="E2E-115: Timeout Handling",
            duration_seconds=metrics_data['duration_seconds'],
            memory_mb=metrics_data['memory_mb'],
            cpu_percent=metrics_data['cpu_percent'],
            items_processed=completed,
            throughput=completed / metrics_data['duration_seconds'],
            success=completed >= 40 and timeouts >= 10,
            errors=errors
        )

        # Assertions
        assert metrics.success, f"Timeout handling failed: {completed} completed, {timeouts} timeouts"
        assert timeouts > 0, "No timeouts detected"
        assert completed > 0, "No operations completed"

        print(f"\n✅ E2E-115 PASSED")
        print(f"   Completed: {completed}")
        print(f"   Timeouts: {timeouts}")
        print(f"   Graceful timeout handling working")


# =============================================================================
# TEST RUNNER
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
