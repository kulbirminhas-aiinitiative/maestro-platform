"""
Workflow Orchestrator integrating DAG engine with ML pipelines
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from pathlib import Path
import json

from .engine import DAGEngine, DAGExecutor
from .pipeline import MLPipeline, PipelineStage
from .models import (
    WorkflowConfig,
    WorkflowExecution,
    TaskConfig,
    TaskStatus,
    ExecutionResult
)

logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """Orchestrates complex ML workflows using DAG execution"""

    def __init__(
        self,
        config: WorkflowConfig,
        stage_registry: Optional[Dict[str, type]] = None
    ):
        self.config = config
        self.dag_engine = DAGEngine()
        self.stage_registry = stage_registry or {}
        self.execution: Optional[WorkflowExecution] = None
        self.task_executors: Dict[str, Callable] = {}

        # Build DAG from config
        self._build_dag()

    def _build_dag(self) -> None:
        """Build DAG from workflow configuration"""
        logger.info(f"Building DAG for workflow: {self.config.name}")

        for task_config in self.config.tasks:
            self.dag_engine.add_task(task_config)

            # Register task executor
            self.task_executors[task_config.task_id] = self._create_task_executor(task_config)

        # Validate DAG
        self.dag_engine.validate()
        logger.info(f"DAG built with {len(self.config.tasks)} tasks")

    def _create_task_executor(self, task_config: TaskConfig) -> Callable:
        """Create executor function for a task"""

        async def executor(config: TaskConfig) -> Dict[str, Any]:
            """Execute task based on type"""
            task_type = config.task_type

            if task_type == "ml_pipeline":
                return await self._execute_ml_pipeline(config)
            elif task_type == "data_processing":
                return await self._execute_data_processing(config)
            elif task_type == "model_training":
                return await self._execute_model_training(config)
            elif task_type == "model_evaluation":
                return await self._execute_model_evaluation(config)
            elif task_type == "deployment":
                return await self._execute_deployment(config)
            elif task_type == "custom":
                return await self._execute_custom_task(config)
            else:
                raise ValueError(f"Unknown task type: {task_type}")

        return executor

    async def _execute_ml_pipeline(self, config: TaskConfig) -> Dict[str, Any]:
        """Execute a full ML pipeline"""
        pipeline_config = config.parameters.get("pipeline", {})
        stages = []

        for stage_config in pipeline_config.get("stages", []):
            stage_type = stage_config.get("type")
            stage_class = self.stage_registry.get(stage_type)

            if stage_class:
                stage = stage_class(
                    name=stage_config.get("name"),
                    config=stage_config.get("config", {})
                )
                stages.append(stage)

        if stages:
            pipeline = MLPipeline(name=config.name, stages=stages)
            result = await pipeline.execute(config.parameters.get("input"))
            return result

        return {"status": "success", "message": "No stages to execute"}

    async def _execute_data_processing(self, config: TaskConfig) -> Dict[str, Any]:
        """Execute data processing task"""
        logger.info(f"Executing data processing: {config.name}")

        # Simulate processing
        await asyncio.sleep(1)

        return {
            "status": "success",
            "records_processed": config.parameters.get("record_count", 1000),
            "output_path": config.parameters.get("output_path")
        }

    async def _execute_model_training(self, config: TaskConfig) -> Dict[str, Any]:
        """Execute model training task"""
        logger.info(f"Executing model training: {config.name}")

        # Simulate training
        await asyncio.sleep(2)

        return {
            "status": "success",
            "model_id": f"model_{config.task_id}",
            "metrics": {
                "accuracy": 0.95,
                "loss": 0.05
            }
        }

    async def _execute_model_evaluation(self, config: TaskConfig) -> Dict[str, Any]:
        """Execute model evaluation task"""
        logger.info(f"Executing model evaluation: {config.name}")

        # Simulate evaluation
        await asyncio.sleep(1)

        return {
            "status": "success",
            "evaluation_metrics": {
                "accuracy": 0.95,
                "precision": 0.93,
                "recall": 0.92
            }
        }

    async def _execute_deployment(self, config: TaskConfig) -> Dict[str, Any]:
        """Execute deployment task"""
        logger.info(f"Executing deployment: {config.name}")

        # Simulate deployment
        await asyncio.sleep(1)

        return {
            "status": "success",
            "deployment_url": f"https://api.example.com/models/{config.task_id}",
            "environment": config.parameters.get("environment", "staging")
        }

    async def _execute_custom_task(self, config: TaskConfig) -> Dict[str, Any]:
        """Execute custom task"""
        logger.info(f"Executing custom task: {config.name}")

        # Get custom executor if registered
        custom_executor = config.parameters.get("executor")
        if custom_executor and callable(custom_executor):
            return await custom_executor(config)

        return {"status": "success", "message": "Custom task completed"}

    async def execute(self) -> WorkflowExecution:
        """Execute the entire workflow"""
        logger.info(f"Starting workflow execution: {self.config.name}")

        # Initialize execution
        self.execution = WorkflowExecution(
            workflow_id=self.config.workflow_id,
            status=TaskStatus.RUNNING,
            tasks_total=len(self.config.tasks)
        )

        try:
            # Create executor
            async def task_executor(config: TaskConfig) -> Dict[str, Any]:
                executor = self.task_executors.get(config.task_id)
                if not executor:
                    raise ValueError(f"No executor found for task {config.task_id}")
                return await executor(config)

            dag_executor = DAGExecutor(
                dag_engine=self.dag_engine,
                task_executor=task_executor,
                max_parallel_tasks=self.config.max_parallel_tasks
            )

            # Execute DAG
            results = await dag_executor.execute(
                failure_strategy=self.config.failure_strategy
            )

            # Update execution status
            self.execution.task_results = results
            self.execution.tasks_completed = len([r for r in results if r.status == TaskStatus.SUCCESS])
            self.execution.tasks_failed = len([r for r in results if r.status == TaskStatus.FAILED])
            self.execution.end_time = datetime.utcnow()

            if self.execution.tasks_failed == 0:
                self.execution.status = TaskStatus.SUCCESS
            elif self.execution.tasks_completed > 0:
                self.execution.status = TaskStatus.FAILED
            else:
                self.execution.status = TaskStatus.FAILED

            logger.info(f"Workflow execution completed: {self.execution.status}")

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            self.execution.status = TaskStatus.FAILED
            self.execution.end_time = datetime.utcnow()
            self.execution.metadata["error"] = str(e)
            raise

        return self.execution

    def get_execution_status(self) -> Dict[str, Any]:
        """Get current execution status"""
        if not self.execution:
            return {"status": "not_started"}

        return {
            "execution_id": self.execution.execution_id,
            "status": self.execution.status.value,
            "progress": {
                "completed": self.execution.tasks_completed,
                "failed": self.execution.tasks_failed,
                "total": self.execution.tasks_total,
                "percentage": (self.execution.tasks_completed / self.execution.tasks_total * 100) if self.execution.tasks_total > 0 else 0
            },
            "duration": (
                (self.execution.end_time - self.execution.start_time).total_seconds()
                if self.execution.end_time else None
            )
        }

    def visualize_workflow(self) -> Dict[str, Any]:
        """Generate workflow visualization data"""
        dag_viz = self.dag_engine.visualize()
        critical_path = self.dag_engine.get_critical_path()

        return {
            "workflow": {
                "id": self.config.workflow_id,
                "name": self.config.name,
                "description": self.config.description
            },
            "dag": dag_viz,
            "critical_path": critical_path,
            "execution_order": self.dag_engine.get_execution_order()
        }

    def export_results(self, output_dir: Path) -> None:
        """Export execution results"""
        if not self.execution:
            logger.warning("No execution to export")
            return

        output_dir.mkdir(parents=True, exist_ok=True)

        # Export execution summary
        summary_file = output_dir / f"execution_{self.execution.execution_id}.json"
        with open(summary_file, 'w') as f:
            json.dump(self.execution.dict(), f, indent=2, default=str)

        # Export visualization
        viz_file = output_dir / f"workflow_{self.config.workflow_id}_viz.json"
        with open(viz_file, 'w') as f:
            json.dump(self.visualize_workflow(), f, indent=2)

        logger.info(f"Results exported to {output_dir}")