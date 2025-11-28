"""
Example: Simple ML workflow with DAG execution
"""

import asyncio
import logging
from pathlib import Path

from ml_pipeline import (
    WorkflowOrchestrator,
    WorkflowConfig,
    TaskConfig,
    Priority
)
from ml_pipeline.pipeline import (
    DataIngestionStage,
    DataPreprocessingStage,
    FeatureEngineeringStage,
    ModelTrainingStage,
    ModelEvaluationStage,
    ModelDeploymentStage
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run simple ML workflow example"""

    # Define workflow tasks
    tasks = [
        TaskConfig(
            task_id="data_ingestion",
            name="Data Ingestion",
            task_type="data_processing",
            dependencies=[],
            priority=Priority.HIGH,
            parameters={
                "source_path": "/data/raw/dataset.csv",
                "output_path": "/data/processed/ingested.csv",
                "record_count": 10000
            }
        ),
        TaskConfig(
            task_id="preprocessing",
            name="Data Preprocessing",
            task_type="data_processing",
            dependencies=["data_ingestion"],
            parameters={
                "transformations": ["normalize", "fill_missing"]
            }
        ),
        TaskConfig(
            task_id="feature_engineering",
            name="Feature Engineering",
            task_type="data_processing",
            dependencies=["preprocessing"],
            parameters={
                "feature_extractors": ["numeric", "categorical"]
            }
        ),
        TaskConfig(
            task_id="model_training",
            name="Model Training",
            task_type="model_training",
            dependencies=["feature_engineering"],
            priority=Priority.HIGH,
            parameters={
                "model_type": "random_forest",
                "hyperparameters": {
                    "n_estimators": 100,
                    "max_depth": 10
                }
            }
        ),
        TaskConfig(
            task_id="model_evaluation",
            name="Model Evaluation",
            task_type="model_evaluation",
            dependencies=["model_training"],
            parameters={
                "metrics": ["accuracy", "precision", "recall", "f1_score"]
            }
        ),
        TaskConfig(
            task_id="deployment",
            name="Model Deployment",
            task_type="deployment",
            dependencies=["model_evaluation"],
            priority=Priority.MEDIUM,
            parameters={
                "environment": "staging",
                "endpoint": "/api/v1/predict"
            }
        )
    ]

    # Create workflow configuration
    workflow_config = WorkflowConfig(
        name="Simple ML Workflow",
        description="End-to-end ML pipeline from data ingestion to deployment",
        tasks=tasks,
        max_parallel_tasks=3,
        failure_strategy="fail_fast"
    )

    # Create stage registry
    stage_registry = {
        "data_ingestion": DataIngestionStage,
        "data_preprocessing": DataPreprocessingStage,
        "feature_engineering": FeatureEngineeringStage,
        "model_training": ModelTrainingStage,
        "model_evaluation": ModelEvaluationStage,
        "model_deployment": ModelDeploymentStage
    }

    # Create and execute orchestrator
    logger.info("Creating workflow orchestrator")
    orchestrator = WorkflowOrchestrator(
        config=workflow_config,
        stage_registry=stage_registry
    )

    # Visualize workflow
    logger.info("Workflow visualization:")
    viz = orchestrator.visualize_workflow()
    logger.info(f"Tasks: {len(viz['dag']['nodes'])}")
    logger.info(f"Dependencies: {len(viz['dag']['edges'])}")
    logger.info(f"Critical path: {viz['critical_path']}")

    # Execute workflow
    logger.info("Starting workflow execution")
    execution = await orchestrator.execute()

    # Print results
    logger.info(f"\nWorkflow execution completed!")
    logger.info(f"Status: {execution.status.value}")
    logger.info(f"Tasks completed: {execution.tasks_completed}/{execution.tasks_total}")
    logger.info(f"Tasks failed: {execution.tasks_failed}")
    logger.info(f"Duration: {(execution.end_time - execution.start_time).total_seconds():.2f}s")

    # Export results
    output_dir = Path("./output/examples")
    orchestrator.export_results(output_dir)
    logger.info(f"Results exported to {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())