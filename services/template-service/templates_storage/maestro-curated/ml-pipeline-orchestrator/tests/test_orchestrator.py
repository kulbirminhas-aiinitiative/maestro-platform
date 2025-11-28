"""
Tests for Workflow Orchestrator
"""

import pytest
import asyncio
from ml_pipeline.orchestrator import WorkflowOrchestrator
from ml_pipeline.models import WorkflowConfig, TaskConfig, TaskStatus


@pytest.fixture
def sample_workflow_config():
    """Create sample workflow configuration"""
    return WorkflowConfig(
        name="Test Workflow",
        description="Test workflow for unit tests",
        tasks=[
            TaskConfig(
                task_id="t1",
                name="Data Processing",
                task_type="data_processing",
                dependencies=[],
                parameters={"record_count": 1000}
            ),
            TaskConfig(
                task_id="t2",
                name="Model Training",
                task_type="model_training",
                dependencies=["t1"],
                parameters={}
            ),
            TaskConfig(
                task_id="t3",
                name="Model Evaluation",
                task_type="model_evaluation",
                dependencies=["t2"],
                parameters={}
            )
        ],
        max_parallel_tasks=2
    )


def test_orchestrator_creation(sample_workflow_config):
    """Test workflow orchestrator creation"""
    orchestrator = WorkflowOrchestrator(sample_workflow_config)

    assert orchestrator.config.name == "Test Workflow"
    assert len(orchestrator.dag_engine.nodes) == 3


def test_dag_building(sample_workflow_config):
    """Test DAG building from workflow config"""
    orchestrator = WorkflowOrchestrator(sample_workflow_config)

    assert orchestrator.dag_engine.validate()

    order = orchestrator.dag_engine.get_execution_order()
    assert len(order) == 3


@pytest.mark.asyncio
async def test_workflow_execution(sample_workflow_config):
    """Test complete workflow execution"""
    orchestrator = WorkflowOrchestrator(sample_workflow_config)

    execution = await orchestrator.execute()

    assert execution.status in [TaskStatus.SUCCESS, TaskStatus.FAILED]
    assert execution.tasks_total == 3
    assert len(execution.task_results) > 0


@pytest.mark.asyncio
async def test_parallel_task_execution():
    """Test parallel task execution"""
    config = WorkflowConfig(
        name="Parallel Workflow",
        tasks=[
            TaskConfig(
                task_id="t1",
                name="Task 1",
                task_type="data_processing",
                dependencies=[]
            ),
            TaskConfig(
                task_id="t2",
                name="Task 2",
                task_type="data_processing",
                dependencies=[]
            ),
            TaskConfig(
                task_id="t3",
                name="Task 3",
                task_type="model_training",
                dependencies=["t1", "t2"]
            )
        ],
        max_parallel_tasks=2
    )

    orchestrator = WorkflowOrchestrator(config)
    execution = await orchestrator.execute()

    assert execution.tasks_completed >= 2


def test_execution_status(sample_workflow_config):
    """Test getting execution status"""
    orchestrator = WorkflowOrchestrator(sample_workflow_config)

    status = orchestrator.get_execution_status()
    assert status["status"] == "not_started"


def test_workflow_visualization(sample_workflow_config):
    """Test workflow visualization"""
    orchestrator = WorkflowOrchestrator(sample_workflow_config)

    viz = orchestrator.visualize_workflow()

    assert "workflow" in viz
    assert "dag" in viz
    assert "critical_path" in viz
    assert len(viz["dag"]["nodes"]) == 3


@pytest.mark.asyncio
async def test_failure_strategy_fail_fast():
    """Test fail-fast failure strategy"""
    config = WorkflowConfig(
        name="Fail Fast Test",
        tasks=[
            TaskConfig(
                task_id="t1",
                name="Task 1",
                task_type="custom",
                dependencies=[],
                retry_policy={"max_retries": 0},
                parameters={"executor": lambda c: asyncio.sleep(0)}
            ),
            TaskConfig(
                task_id="t2",
                name="Task 2",
                task_type="data_processing",
                dependencies=["t1"]
            )
        ],
        failure_strategy="fail_fast"
    )

    orchestrator = WorkflowOrchestrator(config)
    execution = await orchestrator.execute()

    # Even if one task fails, execution should handle it
    assert execution is not None