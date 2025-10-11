"""
Pipeline Tests

Tests for pipeline builder and execution.
"""

import pytest
import time
from unittest.mock import Mock

from mlops.data_pipelines import (
    Pipeline,
    PipelineBuilder,
    PipelineExecutor,
    Task,
    TaskStatus,
    create_simple_pipeline,
)


class TestPipelineBuilder:
    """Test PipelineBuilder"""

    def test_builder_initialization(self):
        """Test pipeline builder initialization"""
        builder = PipelineBuilder(
            pipeline_id="test_pipeline",
            name="Test Pipeline",
            description="Test description"
        )

        assert builder.pipeline.pipeline_id == "test_pipeline"
        assert builder.pipeline.name == "Test Pipeline"
        assert builder.pipeline.description == "Test description"
        assert len(builder.pipeline.tasks) == 0

    def test_add_task(self):
        """Test adding tasks to pipeline"""
        def sample_task(**kwargs):
            return "result"

        builder = PipelineBuilder("test", "Test")
        builder.add_task(
            task_id="task1",
            function=sample_task,
            name="Sample Task"
        )

        assert len(builder.pipeline.tasks) == 1
        assert builder.pipeline.tasks[0].task_id == "task1"
        assert builder.pipeline.tasks[0].name == "Sample Task"

    def test_add_task_with_dependencies(self):
        """Test adding tasks with dependencies"""
        def task1(**kwargs):
            return 1

        def task2(**kwargs):
            return 2

        builder = PipelineBuilder("test", "Test")
        builder.add_task(task_id="task1", function=task1)
        builder.add_task(task_id="task2", function=task2, dependencies=["task1"])

        assert len(builder.pipeline.tasks) == 2
        assert builder.pipeline.tasks[1].dependencies == ["task1"]

    def test_set_schedule(self):
        """Test setting pipeline schedule"""
        builder = PipelineBuilder("test", "Test")
        builder.set_schedule("0 0 * * *")

        assert builder.pipeline.schedule == "0 0 * * *"

    def test_set_default_args(self):
        """Test setting default arguments"""
        builder = PipelineBuilder("test", "Test")
        builder.set_default_args(arg1="value1", arg2="value2")

        assert builder.pipeline.default_args == {"arg1": "value1", "arg2": "value2"}

    def test_fluent_api(self):
        """Test fluent API chaining"""
        def task(**kwargs):
            return "result"

        builder = (PipelineBuilder("test", "Test")
                   .add_task("task1", task)
                   .add_task("task2", task)
                   .set_schedule("0 0 * * *")
                   .set_default_args(arg="value"))

        pipeline = builder.build()

        assert len(pipeline.tasks) == 2
        assert pipeline.schedule == "0 0 * * *"
        assert pipeline.default_args == {"arg": "value"}


class TestPipelineExecutor:
    """Test PipelineExecutor"""

    def test_execute_single_task(self):
        """Test executing a single task"""
        def sample_task(**kwargs):
            return "success"

        pipeline = (PipelineBuilder("test", "Test")
                    .add_task("task1", sample_task)
                    .build())

        executor = PipelineExecutor()
        results = executor.execute(pipeline)

        assert len(results) == 1
        assert "task1" in results
        assert results["task1"].status == TaskStatus.SUCCESS
        assert results["task1"].output == "success"

    def test_execute_multiple_tasks(self):
        """Test executing multiple independent tasks"""
        def task1(**kwargs):
            return 1

        def task2(**kwargs):
            return 2

        pipeline = (PipelineBuilder("test", "Test")
                    .add_task("task1", task1)
                    .add_task("task2", task2)
                    .build())

        executor = PipelineExecutor()
        results = executor.execute(pipeline)

        assert len(results) == 2
        assert results["task1"].status == TaskStatus.SUCCESS
        assert results["task2"].status == TaskStatus.SUCCESS

    def test_execute_with_dependencies(self):
        """Test executing tasks with dependencies"""
        def task1(**kwargs):
            return 10

        def task2(task1_output, **kwargs):
            return task1_output * 2

        pipeline = (PipelineBuilder("test", "Test")
                    .add_task("task1", task1)
                    .add_task("task2", task2, dependencies=["task1"])
                    .build())

        executor = PipelineExecutor()
        results = executor.execute(pipeline)

        assert results["task1"].output == 10
        assert results["task2"].output == 20

    def test_task_failure_stops_pipeline(self):
        """Test that task failure stops dependent tasks"""
        def failing_task(**kwargs):
            raise ValueError("Task failed")

        def dependent_task(**kwargs):
            return "should not run"

        pipeline = (PipelineBuilder("test", "Test")
                    .add_task("failing", failing_task)
                    .add_task("dependent", dependent_task, dependencies=["failing"])
                    .build())

        executor = PipelineExecutor()
        results = executor.execute(pipeline)

        assert results["failing"].status == TaskStatus.FAILED
        assert results["dependent"].status == TaskStatus.SKIPPED

    def test_task_retry(self):
        """Test task retry on failure"""
        call_count = {"count": 0}

        def flaky_task(**kwargs):
            call_count["count"] += 1
            if call_count["count"] < 2:
                raise ValueError("First attempt fails")
            return "success"

        pipeline = (PipelineBuilder("test", "Test")
                    .add_task("flaky", flaky_task, retry_count=2)
                    .build())

        executor = PipelineExecutor()
        results = executor.execute(pipeline)

        assert results["flaky"].status == TaskStatus.SUCCESS
        assert results["flaky"].retry_attempt == 1  # Second attempt (0-indexed)
        assert call_count["count"] == 2

    def test_task_retry_exhausted(self):
        """Test task failure after all retries exhausted"""
        def always_fails(**kwargs):
            raise ValueError("Always fails")

        pipeline = (PipelineBuilder("test", "Test")
                    .add_task("failing", always_fails, retry_count=2)
                    .build())

        executor = PipelineExecutor()
        results = executor.execute(pipeline)

        assert results["failing"].status == TaskStatus.FAILED
        assert results["failing"].retry_attempt == 2

    def test_pipeline_args(self):
        """Test passing arguments to pipeline"""
        def task_with_args(arg1, arg2, **kwargs):
            return arg1 + arg2

        pipeline = (PipelineBuilder("test", "Test")
                    .add_task("task1", task_with_args)
                    .build())

        executor = PipelineExecutor()
        results = executor.execute(pipeline, arg1=10, arg2=20)

        assert results["task1"].output == 30

    def test_default_args_merged(self):
        """Test default args are merged with runtime args"""
        def task(**kwargs):
            return kwargs.get("default_arg", "not set")

        pipeline = (PipelineBuilder("test", "Test")
                    .set_default_args(default_arg="default_value")
                    .add_task("task1", task)
                    .build())

        executor = PipelineExecutor()
        results = executor.execute(pipeline)

        assert results["task1"].output == "default_value"

    def test_topological_sort(self):
        """Test tasks are executed in dependency order"""
        execution_order = []

        def task1(**kwargs):
            execution_order.append("task1")
            return 1

        def task2(**kwargs):
            execution_order.append("task2")
            return 2

        def task3(**kwargs):
            execution_order.append("task3")
            return 3

        pipeline = (PipelineBuilder("test", "Test")
                    .add_task("task3", task3, dependencies=["task2"])
                    .add_task("task1", task1)
                    .add_task("task2", task2, dependencies=["task1"])
                    .build())

        executor = PipelineExecutor()
        executor.execute(pipeline)

        # Task1 should run first, then task2, then task3
        assert execution_order == ["task1", "task2", "task3"]

    def test_task_duration_recorded(self):
        """Test task duration is recorded"""
        def slow_task(**kwargs):
            time.sleep(0.1)
            return "done"

        pipeline = (PipelineBuilder("test", "Test")
                    .add_task("slow", slow_task)
                    .build())

        executor = PipelineExecutor()
        results = executor.execute(pipeline)

        assert results["slow"].duration_seconds >= 0.1
        assert results["slow"].start_time is not None
        assert results["slow"].end_time is not None


class TestCreateSimplePipeline:
    """Test create_simple_pipeline helper"""

    def test_create_simple_pipeline(self):
        """Test creating a simple linear pipeline"""
        def task1(**kwargs):
            return 1

        def task2(**kwargs):
            return 2

        def task3(**kwargs):
            return 3

        tasks = [
            ("task1", task1),
            ("task2", task2),
            ("task3", task3)
        ]

        pipeline = create_simple_pipeline("simple", tasks)

        assert len(pipeline.tasks) == 3
        # Check linear dependencies
        assert pipeline.tasks[0].dependencies == []
        assert pipeline.tasks[1].dependencies == ["task1"]
        assert pipeline.tasks[2].dependencies == ["task2"]


class TestTask:
    """Test Task model"""

    def test_task_creation(self):
        """Test task creation"""
        def sample_func(**kwargs):
            pass

        task = Task(
            task_id="test_task",
            name="Test Task",
            function=sample_func,
            dependencies=["dep1", "dep2"],
            retry_count=3
        )

        assert task.task_id == "test_task"
        assert task.name == "Test Task"
        assert task.dependencies == ["dep1", "dep2"]
        assert task.retry_count == 3


class TestPipelineTemplates:
    """Test pipeline templates"""

    def test_ingestion_pipeline_creation(self):
        """Test ingestion pipeline template"""
        from mlops.data_pipelines.templates import create_ingestion_pipeline

        builder = create_ingestion_pipeline()
        pipeline = builder.build()

        assert pipeline.pipeline_id == "data_ingestion"
        assert len(pipeline.tasks) == 4
        assert pipeline.tasks[0].task_id == "load_data"
        assert pipeline.tasks[1].task_id == "validate_data"
        assert pipeline.tasks[2].task_id == "clean_data"
        assert pipeline.tasks[3].task_id == "save_data"

    def test_training_pipeline_creation(self):
        """Test training pipeline template"""
        from mlops.data_pipelines.templates import create_training_pipeline

        builder = create_training_pipeline()
        pipeline = builder.build()

        assert pipeline.pipeline_id == "model_training"
        assert len(pipeline.tasks) == 6
        assert any(t.task_id == "load_data" for t in pipeline.tasks)
        assert any(t.task_id == "train_model" for t in pipeline.tasks)
        assert any(t.task_id == "evaluate_model" for t in pipeline.tasks)


class TestPipelineIntegration:
    """Integration tests for pipelines"""

    def test_end_to_end_data_pipeline(self, tmp_path):
        """Test complete data pipeline execution"""
        import pandas as pd

        # Create sample data
        df = pd.DataFrame({
            "feature1": range(100),
            "feature2": range(100, 200),
            "target": [0, 1] * 50
        })

        input_path = tmp_path / "input.csv"
        output_path = tmp_path / "output.parquet"

        df.to_csv(input_path, index=False)

        # Create and execute pipeline
        from mlops.data_pipelines.templates import create_ingestion_pipeline

        pipeline = create_ingestion_pipeline()

        results = pipeline.execute(
            input_path=str(input_path),
            output_path=str(output_path),
            required_columns=["feature1", "feature2", "target"],
            drop_duplicates=True,
            format="parquet"
        )

        # Check all tasks succeeded
        assert all(r.status == TaskStatus.SUCCESS for r in results.values())

        # Check output file was created
        assert output_path.exists()

        # Verify output data
        output_df = pd.read_parquet(output_path)
        assert len(output_df) == 100


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
