"""
Pipeline Manager for Release Management.

This module provides the PipelineManager class for configuring and managing
CI/CD pipelines across different environments.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import logging
import uuid

from .models import (
    Pipeline,
    PipelineStage,
    PipelineStatus,
    PipelineRun,
    DeploymentGate,
    GateType,
)

logger = logging.getLogger(__name__)


class PipelineManager:
    """
    Manages CI/CD pipeline configurations and execution.

    Provides functionality to configure pipelines per environment,
    add deployment gates, and manage pipeline runs.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the PipelineManager.

        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self._pipelines: Dict[str, Pipeline] = {}
        self._runs: Dict[str, PipelineRun] = {}
        self._default_stages = self._get_default_stages()
        logger.info("PipelineManager initialized")

    def _get_default_stages(self) -> List[PipelineStage]:
        """Get default pipeline stages."""
        return [
            PipelineStage(
                name="build",
                order=1,
                timeout_minutes=10,
                scripts=["npm install", "npm run build"],
            ),
            PipelineStage(
                name="unit-tests",
                order=2,
                timeout_minutes=15,
                dependencies=["build"],
                scripts=["npm run test:unit"],
            ),
            PipelineStage(
                name="integration-tests",
                order=3,
                timeout_minutes=30,
                dependencies=["unit-tests"],
                scripts=["npm run test:integration"],
            ),
            PipelineStage(
                name="security-scan",
                order=4,
                timeout_minutes=20,
                dependencies=["build"],
                scripts=["npm audit", "snyk test"],
            ),
            PipelineStage(
                name="deploy",
                order=5,
                timeout_minutes=15,
                dependencies=["unit-tests", "integration-tests", "security-scan"],
                scripts=["deploy.sh"],
            ),
        ]

    def configure_pipeline(
        self,
        environment: str,
        name: Optional[str] = None,
        stages: Optional[List[str]] = None,
        custom_stages: Optional[List[PipelineStage]] = None,
    ) -> Pipeline:
        """
        Configure a new pipeline for an environment.

        Args:
            environment: Target environment name
            name: Optional pipeline name
            stages: Optional list of stage names to include
            custom_stages: Optional custom stage definitions

        Returns:
            Configured Pipeline instance
        """
        pipeline_id = str(uuid.uuid4())[:8]
        pipeline_name = name or f"{environment}-pipeline"

        # Use custom stages or filter default stages
        if custom_stages:
            pipeline_stages = custom_stages
        elif stages:
            pipeline_stages = [
                s for s in self._default_stages if s.name in stages
            ]
            # Re-order based on input order
            stage_order = {name: i for i, name in enumerate(stages)}
            pipeline_stages.sort(key=lambda s: stage_order.get(s.name, 999))
        else:
            pipeline_stages = self._default_stages.copy()

        pipeline = Pipeline(
            id=pipeline_id,
            name=pipeline_name,
            environment=environment,
            stages=pipeline_stages,
        )

        self._pipelines[pipeline_id] = pipeline
        logger.info(
            f"Configured pipeline '{pipeline_name}' for environment '{environment}'"
        )
        return pipeline

    def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        """
        Get a pipeline by ID.

        Args:
            pipeline_id: Pipeline ID

        Returns:
            Pipeline instance or None if not found
        """
        return self._pipelines.get(pipeline_id)

    def get_pipeline_by_environment(self, environment: str) -> Optional[Pipeline]:
        """
        Get pipeline configured for an environment.

        Args:
            environment: Environment name

        Returns:
            Pipeline instance or None if not found
        """
        for pipeline in self._pipelines.values():
            if pipeline.environment == environment:
                return pipeline
        return None

    def list_pipelines(
        self,
        environment: Optional[str] = None,
    ) -> List[Pipeline]:
        """
        List all pipelines, optionally filtered by environment.

        Args:
            environment: Optional environment filter

        Returns:
            List of Pipeline instances
        """
        pipelines = list(self._pipelines.values())

        if environment:
            pipelines = [p for p in pipelines if p.environment == environment]

        return pipelines

    def update_pipeline(
        self,
        pipeline_id: str,
        stages: Optional[List[PipelineStage]] = None,
        variables: Optional[Dict[str, str]] = None,
        triggers: Optional[Dict[str, Any]] = None,
    ) -> Optional[Pipeline]:
        """
        Update a pipeline configuration.

        Args:
            pipeline_id: Pipeline ID
            stages: Optional new stages
            variables: Optional new variables
            triggers: Optional new triggers

        Returns:
            Updated Pipeline instance or None if not found
        """
        pipeline = self._pipelines.get(pipeline_id)
        if pipeline is None:
            logger.warning(f"Pipeline '{pipeline_id}' not found")
            return None

        if stages is not None:
            pipeline.stages = stages

        if variables is not None:
            pipeline.variables.update(variables)

        if triggers is not None:
            pipeline.triggers.update(triggers)

        pipeline.updated_at = datetime.utcnow()
        logger.info(f"Updated pipeline '{pipeline_id}'")
        return pipeline

    def delete_pipeline(self, pipeline_id: str) -> bool:
        """
        Delete a pipeline.

        Args:
            pipeline_id: Pipeline ID

        Returns:
            True if deleted, False if not found
        """
        if pipeline_id not in self._pipelines:
            logger.warning(f"Pipeline '{pipeline_id}' not found")
            return False

        del self._pipelines[pipeline_id]
        logger.info(f"Deleted pipeline '{pipeline_id}'")
        return True

    def add_gate(
        self,
        pipeline_id: str,
        gate: DeploymentGate,
        after_stage: Optional[str] = None,
    ) -> bool:
        """
        Add a deployment gate to a pipeline.

        Args:
            pipeline_id: Pipeline ID
            gate: DeploymentGate to add
            after_stage: Optional stage name to place gate after

        Returns:
            True if added, False if pipeline not found
        """
        pipeline = self._pipelines.get(pipeline_id)
        if pipeline is None:
            logger.warning(f"Pipeline '{pipeline_id}' not found")
            return False

        pipeline.gates.append(gate)
        logger.info(f"Added gate '{gate.name}' to pipeline '{pipeline_id}'")
        return True

    def remove_gate(self, pipeline_id: str, gate_name: str) -> bool:
        """
        Remove a deployment gate from a pipeline.

        Args:
            pipeline_id: Pipeline ID
            gate_name: Name of gate to remove

        Returns:
            True if removed, False otherwise
        """
        pipeline = self._pipelines.get(pipeline_id)
        if pipeline is None:
            logger.warning(f"Pipeline '{pipeline_id}' not found")
            return False

        original_count = len(pipeline.gates)
        pipeline.gates = [g for g in pipeline.gates if g.name != gate_name]

        if len(pipeline.gates) < original_count:
            logger.info(f"Removed gate '{gate_name}' from pipeline '{pipeline_id}'")
            return True

        logger.warning(f"Gate '{gate_name}' not found in pipeline")
        return False

    def trigger(
        self,
        pipeline_id: str,
        version: Optional[str] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> PipelineRun:
        """
        Trigger a pipeline run.

        Args:
            pipeline_id: Pipeline ID
            version: Optional version to deploy
            params: Optional run parameters

        Returns:
            PipelineRun instance
        """
        pipeline = self._pipelines.get(pipeline_id)

        if pipeline is None:
            run = PipelineRun(
                id=str(uuid.uuid4())[:8],
                pipeline_id=pipeline_id,
                status=PipelineStatus.FAILED,
                error=f"Pipeline '{pipeline_id}' not found",
            )
            return run

        run_id = str(uuid.uuid4())[:8]
        run = PipelineRun(
            id=run_id,
            pipeline_id=pipeline_id,
            status=PipelineStatus.RUNNING,
            version=version,
            trigger="manual",
            started_at=datetime.utcnow(),
            metadata=params or {},
        )

        # Start first stage
        if pipeline.stages:
            run.current_stage = pipeline.stages[0].name

        self._runs[run_id] = run
        logger.info(f"Triggered pipeline run '{run_id}' for pipeline '{pipeline_id}'")
        return run

    def get_run(self, run_id: str) -> Optional[PipelineRun]:
        """
        Get a pipeline run by ID.

        Args:
            run_id: Run ID

        Returns:
            PipelineRun instance or None if not found
        """
        return self._runs.get(run_id)

    def get_status(self, run_id: str) -> PipelineStatus:
        """
        Get the status of a pipeline run.

        Args:
            run_id: Run ID

        Returns:
            PipelineStatus or FAILED if not found
        """
        run = self._runs.get(run_id)
        if run is None:
            return PipelineStatus.FAILED
        return run.status

    def complete_run(
        self,
        run_id: str,
        status: PipelineStatus,
        artifacts: Optional[List[str]] = None,
        error: Optional[str] = None,
    ) -> Optional[PipelineRun]:
        """
        Complete a pipeline run.

        Args:
            run_id: Run ID
            status: Final status
            artifacts: Optional list of artifact paths
            error: Optional error message

        Returns:
            Updated PipelineRun or None if not found
        """
        run = self._runs.get(run_id)
        if run is None:
            logger.warning(f"Pipeline run '{run_id}' not found")
            return None

        run.status = status
        run.completed_at = datetime.utcnow()

        if artifacts:
            run.artifacts = artifacts

        if error:
            run.error = error

        logger.info(f"Completed pipeline run '{run_id}' with status '{status.value}'")
        return run

    def cancel_run(self, run_id: str) -> bool:
        """
        Cancel a pipeline run.

        Args:
            run_id: Run ID

        Returns:
            True if cancelled, False otherwise
        """
        run = self._runs.get(run_id)
        if run is None:
            logger.warning(f"Pipeline run '{run_id}' not found")
            return False

        if run.status not in [PipelineStatus.PENDING, PipelineStatus.RUNNING]:
            logger.warning(f"Cannot cancel run in status '{run.status.value}'")
            return False

        run.status = PipelineStatus.CANCELLED
        run.completed_at = datetime.utcnow()
        logger.info(f"Cancelled pipeline run '{run_id}'")
        return True

    def list_runs(
        self,
        pipeline_id: Optional[str] = None,
        status: Optional[PipelineStatus] = None,
        limit: int = 100,
    ) -> List[PipelineRun]:
        """
        List pipeline runs.

        Args:
            pipeline_id: Optional pipeline filter
            status: Optional status filter
            limit: Maximum number of runs to return

        Returns:
            List of PipelineRun instances
        """
        runs = list(self._runs.values())

        if pipeline_id:
            runs = [r for r in runs if r.pipeline_id == pipeline_id]

        if status:
            runs = [r for r in runs if r.status == status]

        # Sort by started_at descending
        runs.sort(key=lambda r: r.started_at or datetime.min, reverse=True)

        return runs[:limit]

    def add_stage(
        self,
        pipeline_id: str,
        stage: PipelineStage,
        position: Optional[int] = None,
    ) -> bool:
        """
        Add a stage to a pipeline.

        Args:
            pipeline_id: Pipeline ID
            stage: PipelineStage to add
            position: Optional position index

        Returns:
            True if added, False if pipeline not found
        """
        pipeline = self._pipelines.get(pipeline_id)
        if pipeline is None:
            logger.warning(f"Pipeline '{pipeline_id}' not found")
            return False

        if position is not None:
            pipeline.stages.insert(position, stage)
        else:
            pipeline.stages.append(stage)

        pipeline.updated_at = datetime.utcnow()
        logger.info(f"Added stage '{stage.name}' to pipeline '{pipeline_id}'")
        return True

    def remove_stage(self, pipeline_id: str, stage_name: str) -> bool:
        """
        Remove a stage from a pipeline.

        Args:
            pipeline_id: Pipeline ID
            stage_name: Name of stage to remove

        Returns:
            True if removed, False otherwise
        """
        pipeline = self._pipelines.get(pipeline_id)
        if pipeline is None:
            logger.warning(f"Pipeline '{pipeline_id}' not found")
            return False

        original_count = len(pipeline.stages)
        pipeline.stages = [s for s in pipeline.stages if s.name != stage_name]

        if len(pipeline.stages) < original_count:
            pipeline.updated_at = datetime.utcnow()
            logger.info(f"Removed stage '{stage_name}' from pipeline '{pipeline_id}'")
            return True

        logger.warning(f"Stage '{stage_name}' not found in pipeline")
        return False

    def create_environment_pipeline(
        self,
        environment: str,
        tier: str,
    ) -> Pipeline:
        """
        Create a pipeline configured for a specific environment tier.

        Args:
            environment: Environment name
            tier: Environment tier (development, test, pre_prod)

        Returns:
            Configured Pipeline instance
        """
        # Configure based on tier
        if tier == "development":
            stages = ["build", "unit-tests", "deploy"]
            gates = []
        elif tier == "test":
            stages = ["build", "unit-tests", "integration-tests", "deploy"]
            gates = [
                DeploymentGate(
                    name="automated-quality",
                    gate_type=GateType.AUTOMATED,
                    conditions={
                        "test_coverage_min": 80,
                        "no_critical_vulnerabilities": True,
                    },
                )
            ]
        else:  # pre_prod or production
            stages = ["build", "unit-tests", "integration-tests", "security-scan", "deploy"]
            gates = [
                DeploymentGate(
                    name="qa-approval",
                    gate_type=GateType.MANUAL,
                    approvers=["qa-team"],
                    timeout_hours=24,
                ),
                DeploymentGate(
                    name="security-approval",
                    gate_type=GateType.APPROVAL,
                    approvers=["security-team"],
                    timeout_hours=48,
                ),
            ]

        pipeline = self.configure_pipeline(environment, stages=stages)

        for gate in gates:
            self.add_gate(pipeline.id, gate)

        return pipeline

    def get_pipeline_metrics(
        self,
        pipeline_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """
        Get metrics for a pipeline.

        Args:
            pipeline_id: Pipeline ID
            days: Number of days to include

        Returns:
            Dictionary with pipeline metrics
        """
        pipeline = self._pipelines.get(pipeline_id)
        if pipeline is None:
            return {"error": f"Pipeline '{pipeline_id}' not found"}

        runs = self.list_runs(pipeline_id=pipeline_id)

        # Calculate metrics
        total_runs = len(runs)
        successful_runs = len([r for r in runs if r.status == PipelineStatus.SUCCESS])
        failed_runs = len([r for r in runs if r.status == PipelineStatus.FAILED])

        durations = [
            r.duration_seconds() for r in runs if r.duration_seconds() is not None
        ]
        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "pipeline_id": pipeline_id,
            "pipeline_name": pipeline.name,
            "environment": pipeline.environment,
            "total_runs": total_runs,
            "successful_runs": successful_runs,
            "failed_runs": failed_runs,
            "success_rate": (
                successful_runs / total_runs if total_runs > 0 else 0
            ),
            "average_duration_seconds": avg_duration,
            "stages_count": len(pipeline.stages),
            "gates_count": len(pipeline.gates),
        }
