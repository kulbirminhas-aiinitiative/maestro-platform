"""
Pipeline Builder

Simplified pipeline orchestration for ML workflows.
Provides a clean API for defining and executing data pipelines.
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class Task(BaseModel):
    """Pipeline task definition"""

    task_id: str = Field(..., description="Unique task identifier")
    name: str = Field(..., description="Human-readable task name")
    function: Any = Field(..., description="Callable to execute")
    dependencies: list[str] = Field(default_factory=list, description="Task IDs this depends on")
    retry_count: int = Field(0, description="Number of retries on failure")
    timeout_seconds: Optional[int] = Field(None, description="Task timeout")

    class Config:
        arbitrary_types_allowed = True


class TaskResult(BaseModel):
    """Task execution result"""

    task_id: str
    status: TaskStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    output: Optional[Any] = None
    error: Optional[str] = None
    retry_attempt: int = 0

    class Config:
        arbitrary_types_allowed = True


class Pipeline(BaseModel):
    """Pipeline definition"""

    pipeline_id: str = Field(..., description="Unique pipeline identifier")
    name: str = Field(..., description="Pipeline name")
    description: Optional[str] = Field(None, description="Pipeline description")
    tasks: list[Task] = Field(default_factory=list, description="Pipeline tasks")
    schedule: Optional[str] = Field(None, description="Cron schedule expression")
    default_args: dict[str, Any] = Field(default_factory=dict, description="Default arguments")

    class Config:
        arbitrary_types_allowed = True


class PipelineExecutor:
    """
    Pipeline Executor

    Executes pipeline tasks in dependency order with retry logic.
    """

    def __init__(self):
        self.task_results: dict[str, TaskResult] = {}
        self.task_outputs: dict[str, Any] = {}

    def execute(self, pipeline: Pipeline, **kwargs) -> dict[str, TaskResult]:
        """
        Execute pipeline

        Args:
            pipeline: Pipeline to execute
            **kwargs: Runtime arguments

        Returns:
            Dictionary of task results
        """
        logger.info(f"Executing pipeline: {pipeline.name}")

        # Merge default args with runtime args
        args = {**pipeline.default_args, **kwargs}

        # Topological sort of tasks based on dependencies
        sorted_tasks = self._topological_sort(pipeline.tasks)

        # Execute tasks in order
        for task in sorted_tasks:
            if self._should_skip_task(task):
                logger.info(f"Skipping task {task.task_id} due to failed dependencies")
                self.task_results[task.task_id] = TaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.SKIPPED
                )
                continue

            # Execute task with retries
            result = self._execute_task(task, args)
            self.task_results[task.task_id] = result

            # Store output for downstream tasks
            if result.output is not None:
                self.task_outputs[task.task_id] = result.output

            # Stop if task failed
            if result.status == TaskStatus.FAILED:
                logger.error(f"Task {task.task_id} failed, stopping pipeline")
                break

        logger.info(f"Pipeline execution completed")
        return self.task_results

    def _topological_sort(self, tasks: list[Task]) -> list[Task]:
        """Sort tasks by dependency order"""
        # Simple topological sort
        sorted_tasks = []
        task_dict = {t.task_id: t for t in tasks}
        visited = set()

        def visit(task_id: str):
            if task_id in visited:
                return
            task = task_dict[task_id]
            for dep_id in task.dependencies:
                if dep_id in task_dict:
                    visit(dep_id)
            visited.add(task_id)
            sorted_tasks.append(task)

        for task in tasks:
            visit(task.task_id)

        return sorted_tasks

    def _should_skip_task(self, task: Task) -> bool:
        """Check if task should be skipped due to failed dependencies"""
        for dep_id in task.dependencies:
            if dep_id in self.task_results:
                dep_result = self.task_results[dep_id]
                if dep_result.status in [TaskStatus.FAILED, TaskStatus.SKIPPED]:
                    return True
        return False

    def _execute_task(self, task: Task, args: dict[str, Any]) -> TaskResult:
        """Execute a single task with retry logic"""
        logger.info(f"Executing task: {task.name} ({task.task_id})")

        for attempt in range(task.retry_count + 1):
            start_time = datetime.utcnow()

            try:
                # Prepare task arguments
                task_args = self._prepare_task_args(task, args)

                # Execute function
                output = task.function(**task_args)

                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()

                logger.info(f"Task {task.task_id} completed successfully in {duration:.2f}s")

                return TaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.SUCCESS,
                    start_time=start_time,
                    end_time=end_time,
                    duration_seconds=duration,
                    output=output,
                    retry_attempt=attempt
                )

            except Exception as e:
                logger.error(f"Task {task.task_id} failed (attempt {attempt + 1}/{task.retry_count + 1}): {e}")

                if attempt < task.retry_count:
                    logger.info(f"Retrying task {task.task_id}...")
                    continue

                # Final failure
                end_time = datetime.utcnow()
                duration = (end_time - start_time).total_seconds()

                return TaskResult(
                    task_id=task.task_id,
                    status=TaskStatus.FAILED,
                    start_time=start_time,
                    end_time=end_time,
                    duration_seconds=duration,
                    error=str(e),
                    retry_attempt=attempt
                )

    def _prepare_task_args(self, task: Task, pipeline_args: dict[str, Any]) -> dict[str, Any]:
        """Prepare arguments for task execution"""
        # Start with pipeline args
        task_args = pipeline_args.copy()

        # Add outputs from dependencies
        for dep_id in task.dependencies:
            if dep_id in self.task_outputs:
                task_args[f"{dep_id}_output"] = self.task_outputs[dep_id]

        return task_args


class PipelineBuilder:
    """
    Pipeline Builder

    Fluent API for building ML pipelines.
    """

    def __init__(self, pipeline_id: str, name: str, description: Optional[str] = None):
        """
        Initialize pipeline builder

        Args:
            pipeline_id: Unique pipeline ID
            name: Pipeline name
            description: Pipeline description
        """
        self.pipeline = Pipeline(
            pipeline_id=pipeline_id,
            name=name,
            description=description
        )

    def add_task(
        self,
        task_id: str,
        function: Callable,
        name: Optional[str] = None,
        dependencies: Optional[list[str]] = None,
        retry_count: int = 0,
        timeout_seconds: Optional[int] = None
    ) -> "PipelineBuilder":
        """
        Add a task to the pipeline

        Args:
            task_id: Unique task ID
            function: Function to execute
            name: Human-readable task name
            dependencies: List of task IDs this depends on
            retry_count: Number of retries on failure
            timeout_seconds: Task timeout

        Returns:
            Self for chaining
        """
        task = Task(
            task_id=task_id,
            name=name or task_id,
            function=function,
            dependencies=dependencies or [],
            retry_count=retry_count,
            timeout_seconds=timeout_seconds
        )

        self.pipeline.tasks.append(task)
        return self

    def set_schedule(self, cron_expression: str) -> "PipelineBuilder":
        """
        Set pipeline schedule

        Args:
            cron_expression: Cron expression (e.g., "0 0 * * *" for daily)

        Returns:
            Self for chaining
        """
        self.pipeline.schedule = cron_expression
        return self

    def set_default_args(self, **kwargs) -> "PipelineBuilder":
        """
        Set default arguments for all tasks

        Returns:
            Self for chaining
        """
        self.pipeline.default_args.update(kwargs)
        return self

    def build(self) -> Pipeline:
        """
        Build and return the pipeline

        Returns:
            Constructed pipeline
        """
        return self.pipeline

    def execute(self, **kwargs) -> dict[str, TaskResult]:
        """
        Build and execute the pipeline

        Args:
            **kwargs: Runtime arguments

        Returns:
            Task results
        """
        pipeline = self.build()
        executor = PipelineExecutor()
        return executor.execute(pipeline, **kwargs)


def create_simple_pipeline(
    pipeline_id: str,
    tasks: list[tuple[str, Callable]],
    name: Optional[str] = None
) -> Pipeline:
    """
    Create a simple linear pipeline

    Args:
        pipeline_id: Pipeline ID
        tasks: List of (task_id, function) tuples
        name: Pipeline name

    Returns:
        Pipeline with tasks in linear dependency order
    """
    builder = PipelineBuilder(
        pipeline_id=pipeline_id,
        name=name or pipeline_id
    )

    prev_task_id = None
    for task_id, function in tasks:
        dependencies = [prev_task_id] if prev_task_id else []
        builder.add_task(
            task_id=task_id,
            function=function,
            dependencies=dependencies
        )
        prev_task_id = task_id

    return builder.build()
