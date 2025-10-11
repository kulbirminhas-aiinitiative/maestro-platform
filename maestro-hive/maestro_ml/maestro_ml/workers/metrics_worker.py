#!/usr/bin/env python3
"""
Metrics Collection Worker

Background worker that periodically collects metrics from:
- Git repositories
- CI/CD systems
- MLflow experiments
- Artifact usage

Runs on a configurable schedule (default: 5 minutes).
"""

import asyncio
import logging
from datetime import datetime
from typing import List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from maestro_ml.config.settings import get_settings
from maestro_ml.core.database import AsyncSessionLocal
from maestro_ml.models.database import Project
from maestro_ml.services.metrics_collector import MetricsCollector

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MetricsWorker:
    """Background worker for metrics collection"""

    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.collection_interval = settings.METRICS_COLLECTION_INTERVAL
        self.running = False

    async def collect_project_metrics(self, session: AsyncSession, project: Project):
        """Collect all metrics for a single project"""
        try:
            logger.info(f"Collecting metrics for project: {project.name} ({project.id})")

            # Collect Git metrics if repo metadata exists
            if project.metadata and "repo_path" in project.metadata:
                repo_path = project.metadata["repo_path"]
                git_metrics = await self.metrics_collector.collect_git_metrics(
                    session, str(project.id), repo_path
                )
                logger.info(f"  Git metrics: {git_metrics}")

            # Collect CI/CD metrics if config exists
            if project.metadata and "ci_config" in project.metadata:
                ci_config = project.metadata["ci_config"]
                ci_metrics = await self.metrics_collector.collect_ci_metrics(
                    session, str(project.id), ci_config
                )
                logger.info(f"  CI/CD metrics: {ci_metrics}")

            # Collect MLflow metrics if experiment exists
            if project.metadata and "mlflow_experiment" in project.metadata:
                experiment_name = project.metadata["mlflow_experiment"]
                mlflow_metrics = await self.metrics_collector.collect_mlflow_metrics(
                    session, str(project.id), experiment_name
                )
                logger.info(f"  MLflow metrics: {mlflow_metrics}")

            # Collect artifact usage metrics
            artifact_metrics = await self.metrics_collector.collect_artifact_metrics(
                session, str(project.id)
            )
            logger.info(f"  Artifact metrics: {artifact_metrics}")

            # Calculate development velocity
            velocity = await self.metrics_collector.calculate_development_velocity(
                session, str(project.id)
            )
            logger.info(f"  Development velocity: {velocity:.2f}")

        except Exception as e:
            logger.error(f"Error collecting metrics for project {project.id}: {e}")

    async def collect_all_metrics(self):
        """Collect metrics for all active projects"""
        async with AsyncSessionLocal() as session:
            try:
                # Get all active projects
                stmt = select(Project).where(Project.metadata["status"].astext != "archived")
                result = await session.execute(stmt)
                projects = result.scalars().all()

                logger.info(f"Found {len(projects)} active projects")

                # Collect metrics for each project
                for project in projects:
                    await self.collect_project_metrics(session, project)

                logger.info("Metrics collection completed successfully")

            except Exception as e:
                logger.error(f"Error in metrics collection cycle: {e}")

    async def run(self):
        """Main worker loop"""
        self.running = True
        logger.info(f"Metrics worker started (interval: {self.collection_interval}s)")

        while self.running:
            try:
                start_time = datetime.now()
                logger.info("Starting metrics collection cycle...")

                await self.collect_all_metrics()

                # Calculate next run time
                elapsed = (datetime.now() - start_time).total_seconds()
                sleep_time = max(0, self.collection_interval - elapsed)

                logger.info(f"Cycle completed in {elapsed:.2f}s. Next run in {sleep_time:.2f}s")
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                logger.info("Worker cancelled, shutting down...")
                break
            except Exception as e:
                logger.error(f"Unexpected error in worker loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute on error

        self.running = False
        logger.info("Metrics worker stopped")

    def stop(self):
        """Stop the worker"""
        self.running = False


async def main():
    """Entry point for metrics worker"""
    worker = MetricsWorker()

    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
