"""
Pytest configuration and fixtures
"""

import pytest
import asyncio
from typing import Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_task_config():
    """Sample task configuration for testing"""
    from ml_pipeline.models import TaskConfig
    return TaskConfig(
        task_id="test_task",
        name="Test Task",
        task_type="test",
        dependencies=[]
    )


@pytest.fixture
def sample_workflow_config():
    """Sample workflow configuration for testing"""
    from ml_pipeline.models import WorkflowConfig, TaskConfig
    return WorkflowConfig(
        name="Test Workflow",
        tasks=[
            TaskConfig(
                task_id="task1",
                name="Task 1",
                task_type="data_processing",
                dependencies=[]
            )
        ]
    )