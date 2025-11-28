"""
Tests for DAG Engine
"""

import pytest
import asyncio
from ml_pipeline.engine import DAGEngine, DAGNode, DAGExecutor
from ml_pipeline.models import TaskConfig, TaskStatus, Priority


@pytest.fixture
def sample_tasks():
    """Create sample tasks for testing"""
    return [
        TaskConfig(
            task_id="task1",
            name="Task 1",
            task_type="data_processing",
            dependencies=[]
        ),
        TaskConfig(
            task_id="task2",
            name="Task 2",
            task_type="model_training",
            dependencies=["task1"]
        ),
        TaskConfig(
            task_id="task3",
            name="Task 3",
            task_type="model_evaluation",
            dependencies=["task2"]
        )
    ]


def test_dag_node_creation():
    """Test DAG node creation"""
    task_config = TaskConfig(
        task_id="test1",
        name="Test Task",
        task_type="test",
        dependencies=[]
    )

    node = DAGNode(task_config)

    assert node.task_id == "test1"
    assert node.status == TaskStatus.PENDING
    assert node.result is None
    assert len(node.dependencies) == 0


def test_dag_engine_add_task(sample_tasks):
    """Test adding tasks to DAG engine"""
    engine = DAGEngine()

    for task in sample_tasks:
        engine.add_task(task)

    assert len(engine.nodes) == 3
    assert "task1" in engine.nodes
    assert "task2" in engine.nodes
    assert "task3" in engine.nodes


def test_dag_validation(sample_tasks):
    """Test DAG validation"""
    engine = DAGEngine()

    for task in sample_tasks:
        engine.add_task(task)

    assert engine.validate() is True


def test_dag_cycle_detection():
    """Test cycle detection in DAG"""
    engine = DAGEngine()

    # Create tasks with circular dependency
    task1 = TaskConfig(task_id="t1", name="T1", task_type="test", dependencies=["t2"])
    task2 = TaskConfig(task_id="t2", name="T2", task_type="test", dependencies=["t1"])

    engine.add_task(TaskConfig(task_id="t1", name="T1", task_type="test", dependencies=[]))
    engine.add_task(TaskConfig(task_id="t2", name="T2", task_type="test", dependencies=["t1"]))

    # Manually create cycle for testing
    engine.graph.add_edge("t2", "t1")

    with pytest.raises(ValueError):
        engine.validate()


def test_execution_order(sample_tasks):
    """Test topological sort for execution order"""
    engine = DAGEngine()

    for task in sample_tasks:
        engine.add_task(task)

    order = engine.get_execution_order()

    assert len(order) == 3
    assert order[0] == ["task1"]
    assert order[1] == ["task2"]
    assert order[2] == ["task3"]


def test_parallel_execution_order():
    """Test execution order with parallel tasks"""
    engine = DAGEngine()

    tasks = [
        TaskConfig(task_id="t1", name="T1", task_type="test", dependencies=[]),
        TaskConfig(task_id="t2", name="T2", task_type="test", dependencies=[]),
        TaskConfig(task_id="t3", name="T3", task_type="test", dependencies=["t1", "t2"]),
    ]

    for task in tasks:
        engine.add_task(task)

    order = engine.get_execution_order()

    assert len(order) == 2
    assert set(order[0]) == {"t1", "t2"}
    assert order[1] == ["t3"]


def test_ready_tasks():
    """Test getting ready tasks"""
    engine = DAGEngine()

    tasks = [
        TaskConfig(task_id="t1", name="T1", task_type="test", dependencies=[]),
        TaskConfig(task_id="t2", name="T2", task_type="test", dependencies=["t1"]),
    ]

    for task in tasks:
        engine.add_task(task)

    # Initially, only t1 should be ready
    ready = engine.get_ready_tasks(set())
    assert len(ready) == 1
    assert ready[0].task_id == "t1"

    # After t1 completes, t2 should be ready
    ready = engine.get_ready_tasks({"t1"})
    assert len(ready) == 1
    assert ready[0].task_id == "t2"


@pytest.mark.asyncio
async def test_dag_executor():
    """Test DAG executor"""
    engine = DAGEngine()

    tasks = [
        TaskConfig(task_id="t1", name="T1", task_type="test", dependencies=[]),
        TaskConfig(task_id="t2", name="T2", task_type="test", dependencies=["t1"]),
    ]

    for task in tasks:
        engine.add_task(task)

    async def mock_executor(config):
        await asyncio.sleep(0.1)
        return {"status": "success", "task_id": config.task_id}

    executor = DAGExecutor(engine, mock_executor, max_parallel_tasks=2)
    results = await executor.execute()

    assert len(results) == 2
    assert all(r.status == TaskStatus.SUCCESS for r in results)


@pytest.mark.asyncio
async def test_dag_executor_with_failure():
    """Test DAG executor with task failure"""
    engine = DAGEngine()

    tasks = [
        TaskConfig(
            task_id="t1",
            name="T1",
            task_type="test",
            dependencies=[],
            retry_policy={"max_retries": 0}
        ),
    ]

    for task in tasks:
        engine.add_task(task)

    async def failing_executor(config):
        raise Exception("Task failed")

    executor = DAGExecutor(engine, failing_executor, max_parallel_tasks=1)
    results = await executor.execute()

    assert len(results) == 1
    assert results[0].status == TaskStatus.FAILED


def test_critical_path(sample_tasks):
    """Test critical path calculation"""
    engine = DAGEngine()

    for task in sample_tasks:
        engine.add_task(task)

    critical_path = engine.get_critical_path()

    assert len(critical_path) > 0
    assert critical_path[0] == "task1"
    assert critical_path[-1] == "task3"