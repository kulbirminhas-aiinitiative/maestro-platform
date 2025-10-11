#!/usr/bin/env python3
"""
Metrics Collector Service

Collects development process metrics from various sources:
- Git (commit frequency, PR times, collaboration)
- CI/CD (run times, success rates, resource usage)
- Experiments (MLflow tracking)
- Artifacts (usage patterns)
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import subprocess
import json

from maestro_ml.models.database import ProcessMetric, Project


class MetricsCollector:
    """Collect and store process metrics"""

    async def collect_git_metrics(
        self,
        session: AsyncSession,
        project_id: str,
        repo_path: str
    ) -> Dict[str, float]:
        """
        Collect Git metrics for a project

        Metrics:
        - Commit frequency (commits per day)
        - Average time to merge PR
        - Code churn (lines changed per commit)
        - Collaboration score (unique contributors)
        """
        metrics = {}

        try:
            # Get commit count in last 7 days
            cmd = f"cd {repo_path} && git log --since='7 days ago' --oneline | wc -l"
            commits = int(subprocess.check_output(cmd, shell=True).decode().strip())
            metrics["commits_per_week"] = commits

            # Get unique contributors
            cmd = f"cd {repo_path} && git log --since='30 days ago' --format='%an' | sort -u | wc -l"
            contributors = int(subprocess.check_output(cmd, shell=True).decode().strip())
            metrics["unique_contributors"] = contributors

            # Save metrics
            for metric_type, value in metrics.items():
                await self.save_metric(session, project_id, metric_type, value)

        except Exception as e:
            print(f"Error collecting git metrics: {e}")

        return metrics

    async def collect_ci_metrics(
        self,
        session: AsyncSession,
        project_id: str,
        ci_config: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Collect CI/CD metrics

        Metrics:
        - Average pipeline duration
        - Success rate
        - Resource usage (CPU hours, GPU hours)
        - Deployment frequency
        """
        # This would integrate with GitHub Actions, Jenkins, etc.
        # Placeholder implementation
        metrics = {
            "avg_pipeline_duration_minutes": 0.0,
            "pipeline_success_rate": 0.0,
            "total_cpu_hours": 0.0,
            "total_gpu_hours": 0.0
        }

        for metric_type, value in metrics.items():
            await self.save_metric(session, project_id, metric_type, value)

        return metrics

    async def collect_mlflow_metrics(
        self,
        session: AsyncSession,
        project_id: str,
        experiment_name: str
    ) -> Dict[str, float]:
        """
        Collect MLflow experiment metrics

        Metrics:
        - Total experiments run
        - Best model performance
        - Average training time
        - Hyperparameter search iterations
        """
        # This would integrate with MLflow Tracking API
        # Placeholder implementation
        metrics = {
            "total_experiments": 0,
            "best_model_metric": 0.0,
            "avg_training_time_hours": 0.0,
            "hyperparameter_iterations": 0
        }

        for metric_type, value in metrics.items():
            await self.save_metric(session, project_id, metric_type, value)

        return metrics

    async def collect_artifact_metrics(
        self,
        session: AsyncSession,
        project_id: str
    ) -> Dict[str, float]:
        """
        Collect artifact usage metrics for a project

        Metrics:
        - Number of artifacts reused
        - Artifact reuse rate (%)
        - Average artifact impact score
        """
        from maestro_ml.models.database import ArtifactUsage

        # Get artifact usage count for this project
        stmt = select(ArtifactUsage).where(ArtifactUsage.project_id == project_id)
        result = await session.execute(stmt)
        usages = result.scalars().all()

        metrics = {
            "artifacts_reused_count": len(usages),
            "artifact_reuse_rate": len(usages) * 10.0 if usages else 0.0,  # Simplified calc
        }

        for metric_type, value in metrics.items():
            await self.save_metric(session, project_id, metric_type, value)

        return metrics

    async def save_metric(
        self,
        session: AsyncSession,
        project_id: str,
        metric_type: str,
        metric_value: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessMetric:
        """Save a process metric"""
        import uuid as uuid_lib

        # Convert string ID to UUID
        project_uuid = uuid_lib.UUID(project_id) if isinstance(project_id, str) else project_id

        metric = ProcessMetric(
            project_id=project_uuid,
            metric_type=metric_type,
            metric_value=metric_value,
            meta=metadata or {}
        )

        session.add(metric)
        await session.commit()
        await session.refresh(metric)

        return metric

    async def get_project_metrics_summary(
        self,
        session: AsyncSession,
        project_id: str
    ) -> Dict[str, Any]:
        """Get summary of all metrics for a project"""
        import uuid as uuid_lib

        # Convert string ID to UUID
        project_uuid = uuid_lib.UUID(project_id) if isinstance(project_id, str) else project_id

        stmt = select(ProcessMetric).where(ProcessMetric.project_id == project_uuid)
        result = await session.execute(stmt)
        metrics = result.scalars().all()

        # Group by type
        summary = {}
        for metric in metrics:
            if metric.metric_type not in summary:
                summary[metric.metric_type] = []
            summary[metric.metric_type].append({
                "value": metric.metric_value,
                "timestamp": metric.timestamp
            })

        return summary

    async def calculate_development_velocity(
        self,
        session: AsyncSession,
        project_id: str
    ) -> float:
        """
        Calculate overall development velocity score (0-100)

        Based on:
        - Commit frequency
        - Pipeline success rate
        - Artifact reuse rate
        """
        summary = await self.get_project_metrics_summary(session, project_id)

        # Weighted score
        velocity = 0.0
        weights = {
            "commits_per_week": 0.3,
            "pipeline_success_rate": 0.3,
            "artifact_reuse_rate": 0.4
        }

        for metric_type, weight in weights.items():
            if metric_type in summary:
                latest = summary[metric_type][-1]["value"]
                velocity += latest * weight

        return min(100.0, velocity)
