"""
Example: Parallel workflows with multiple independent pipelines
"""

import asyncio
import logging

from ml_pipeline import (
    WorkflowOrchestrator,
    WorkflowConfig,
    TaskConfig,
    Priority
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run parallel workflows example"""

    # Define tasks with parallel branches
    tasks = [
        # Parallel data ingestion
        TaskConfig(
            task_id="ingest_users",
            name="Ingest User Data",
            task_type="data_processing",
            dependencies=[],
            priority=Priority.HIGH
        ),
        TaskConfig(
            task_id="ingest_transactions",
            name="Ingest Transaction Data",
            task_type="data_processing",
            dependencies=[],
            priority=Priority.HIGH
        ),
        TaskConfig(
            task_id="ingest_products",
            name="Ingest Product Data",
            task_type="data_processing",
            dependencies=[],
            priority=Priority.HIGH
        ),

        # Parallel processing
        TaskConfig(
            task_id="process_users",
            name="Process User Data",
            task_type="data_processing",
            dependencies=["ingest_users"]
        ),
        TaskConfig(
            task_id="process_transactions",
            name="Process Transaction Data",
            task_type="data_processing",
            dependencies=["ingest_transactions"]
        ),
        TaskConfig(
            task_id="process_products",
            name="Process Product Data",
            task_type="data_processing",
            dependencies=["ingest_products"]
        ),

        # Join data
        TaskConfig(
            task_id="join_data",
            name="Join All Data",
            task_type="data_processing",
            dependencies=["process_users", "process_transactions", "process_products"]
        ),

        # Parallel model training
        TaskConfig(
            task_id="train_recommendation_model",
            name="Train Recommendation Model",
            task_type="model_training",
            dependencies=["join_data"],
            priority=Priority.HIGH
        ),
        TaskConfig(
            task_id="train_churn_model",
            name="Train Churn Prediction Model",
            task_type="model_training",
            dependencies=["join_data"],
            priority=Priority.HIGH
        ),
        TaskConfig(
            task_id="train_fraud_model",
            name="Train Fraud Detection Model",
            task_type="model_training",
            dependencies=["join_data"],
            priority=Priority.CRITICAL
        ),

        # Parallel evaluation
        TaskConfig(
            task_id="eval_recommendation",
            name="Evaluate Recommendation Model",
            task_type="model_evaluation",
            dependencies=["train_recommendation_model"]
        ),
        TaskConfig(
            task_id="eval_churn",
            name="Evaluate Churn Model",
            task_type="model_evaluation",
            dependencies=["train_churn_model"]
        ),
        TaskConfig(
            task_id="eval_fraud",
            name="Evaluate Fraud Model",
            task_type="model_evaluation",
            dependencies=["train_fraud_model"]
        ),

        # Final deployment
        TaskConfig(
            task_id="deploy_all",
            name="Deploy All Models",
            task_type="deployment",
            dependencies=["eval_recommendation", "eval_churn", "eval_fraud"],
            priority=Priority.HIGH
        )
    ]

    workflow_config = WorkflowConfig(
        name="Parallel ML Workflow",
        description="Multiple parallel pipelines with data joining and model training",
        tasks=tasks,
        max_parallel_tasks=5,  # Allow high parallelism
        failure_strategy="continue"  # Continue even if some tasks fail
    )

    orchestrator = WorkflowOrchestrator(config=workflow_config)

    # Show execution order
    execution_order = orchestrator.dag_engine.get_execution_order()
    logger.info("Execution order (parallel levels):")
    for i, level in enumerate(execution_order):
        logger.info(f"Level {i + 1}: {len(level)} tasks in parallel")
        for task_id in level:
            logger.info(f"  - {task_id}")

    # Execute workflow
    logger.info("\nStarting parallel workflow execution")
    execution = await orchestrator.execute()

    logger.info(f"\nExecution completed!")
    logger.info(f"Status: {execution.status.value}")
    logger.info(f"Success rate: {execution.tasks_completed}/{execution.tasks_total}")
    logger.info(f"Duration: {(execution.end_time - execution.start_time).total_seconds():.2f}s")


if __name__ == "__main__":
    asyncio.run(main())