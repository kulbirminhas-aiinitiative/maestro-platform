"""
Azure Pipelines Templates

Generates azure-pipelines.yml files with:
- Multi-stage pipelines
- Artifact management
- Caching strategies
- Matrix builds
- Environment promotion
- Rollback capability

Reference: MD-2522 AC-1 through AC-6
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import yaml

from .models import (
    PipelineTemplate,
    PipelineType,
    Platform,
    Stage,
    Job,
    Step,
    CacheConfig,
    ArtifactConfig,
    MatrixConfig,
    Environment,
    RollbackConfig,
    HealthCheck,
)


@dataclass
class AzurePipeline(PipelineTemplate):
    """
    Azure Pipelines template.

    Generates azure-pipelines.yml format with:
    - stages, jobs, steps
    - pool configuration
    - variables, templates
    - environments, deployments
    """

    def __init__(
        self,
        pipeline_type: PipelineType = PipelineType.BUILD,
        stages: Optional[List[Stage]] = None,
        variables: Optional[Dict[str, str]] = None,
        cache: Optional[CacheConfig] = None,
        artifacts: Optional[ArtifactConfig] = None,
        matrix: Optional[MatrixConfig] = None,
        environments: Optional[List[Environment]] = None,
        rollback: Optional[RollbackConfig] = None,
        pool: str = "ubuntu-latest",
        trigger_branches: Optional[List[str]] = None,
    ):
        super().__init__(
            pipeline_type=pipeline_type,
            platform=Platform.AZURE,
            stages=stages or [],
            variables=variables or {},
            cache=cache,
            artifacts=artifacts,
            matrix=matrix,
            environments=environments or [],
            rollback=rollback,
        )
        self.pool = pool
        self.trigger_branches = trigger_branches or ["main", "develop"]

    def render(self) -> str:
        """Render to azure-pipelines.yml format."""
        config: Dict[str, Any] = {}

        # Trigger configuration
        config["trigger"] = self.trigger_branches

        # Pool configuration
        config["pool"] = {"vmImage": self.pool}

        # Variables
        if self.variables:
            config["variables"] = self.variables

        # Stages
        if self.stages:
            config["stages"] = self._render_stages()

        return yaml.dump(config, default_flow_style=False, sort_keys=False)

    def _render_stages(self) -> List[Dict[str, Any]]:
        """Render all stages."""
        return [self._render_stage(stage) for stage in self.stages]

    def _render_stage(self, stage: Stage) -> Dict[str, Any]:
        """Render a single stage."""
        stage_config: Dict[str, Any] = {
            "stage": stage.name,
            "displayName": stage.name.replace("_", " ").title(),
        }

        # Dependencies
        if stage.dependencies:
            stage_config["dependsOn"] = stage.dependencies

        # Condition
        if stage.condition:
            stage_config["condition"] = stage.condition

        # Jobs
        stage_config["jobs"] = [self._render_job(job) for job in stage.jobs]

        return stage_config

    def _render_job(self, job: Job) -> Dict[str, Any]:
        """Render a single job."""
        job_config: Dict[str, Any] = {
            "job": job.name,
            "displayName": job.name.replace("_", " ").title(),
        }

        # Pool override
        if job.image:
            job_config["pool"] = {"vmImage": job.image}

        # Variables
        if job.variables:
            job_config["variables"] = job.variables

        # Strategy for matrix builds (AC-4)
        if self.matrix and self.matrix.dimensions:
            job_config.update(self.matrix.to_azure())

        # Steps
        job_config["steps"] = self._render_steps(job)

        # Timeout
        if job.timeout:
            job_config["timeoutInMinutes"] = self._parse_timeout(job.timeout)

        # Continue on error
        if job.allow_failure:
            job_config["continueOnError"] = True

        # Environment (AC-5)
        if job.environment:
            job_config["environment"] = job.environment.name

        return job_config

    def _render_steps(self, job: Job) -> List[Dict[str, Any]]:
        """Render job steps."""
        steps = []

        # Add cache step (AC-3)
        if job.cache or self.cache:
            cache_config = job.cache or self.cache
            if cache_config:
                steps.append({
                    "task": "Cache@2",
                    "inputs": cache_config.to_azure(),
                })

        # Script steps
        for step in job.steps:
            step_config: Dict[str, Any] = {
                "script": step.script,
                "displayName": step.name,
            }
            if step.condition:
                step_config["condition"] = step.condition
            if step.environment:
                step_config["env"] = step.environment
            steps.append(step_config)

        # Publish artifacts (AC-2)
        if job.artifacts or self.artifacts:
            artifact_config = job.artifacts or self.artifacts
            if artifact_config:
                steps.append(artifact_config.to_azure())

        return steps

    def _parse_timeout(self, timeout: str) -> int:
        """Parse timeout string to minutes."""
        if timeout.endswith("h"):
            return int(timeout[:-1]) * 60
        elif timeout.endswith("m"):
            return int(timeout[:-1])
        return 60  # Default 1 hour

    def validate(self) -> List[str]:
        """Validate the pipeline configuration."""
        errors = []

        if not self.stages:
            errors.append("Pipeline must have at least one stage")

        for stage in self.stages:
            if not stage.jobs:
                errors.append(f"Stage '{stage.name}' has no jobs")

        return errors

    def add_build_stage(self) -> None:
        """Add a standard build stage."""
        build_job = Job(
            name="Build",
            steps=[
                Step(name="Install dependencies", script="pip install -r requirements.txt"),
                Step(name="Build", script="python setup.py build"),
            ],
            cache=CacheConfig(
                key="pip | $(Agent.OS) | requirements.txt",
                paths=[".cache/pip"],
            ),
            artifacts=ArtifactConfig(
                paths=["$(Build.ArtifactStagingDirectory)"],
                name="drop",
            ),
        )
        self.add_stage(Stage(name="Build", jobs=[build_job]))

    def add_test_stage(self) -> None:
        """Add a standard test stage."""
        test_job = Job(
            name="Test",
            steps=[
                Step(name="Run tests", script="pytest --cov --junitxml=$(Build.SourcesDirectory)/test-results.xml"),
            ],
        )
        self.add_stage(Stage(name="Test", jobs=[test_job], dependencies=["Build"]))

    def add_deploy_stage(self, env_name: str = "staging", requires_approval: bool = False) -> None:
        """Add a deployment stage (AC-5)."""
        env = Environment(
            name=env_name,
            requires_approval=requires_approval,
        )

        deploy_job = Job(
            name=f"Deploy_{env_name}",
            steps=[
                Step(name="Download artifact", script="echo 'Downloading artifact...'"),
                Step(name="Deploy", script="./deploy.sh"),
            ],
            environment=env,
        )

        stage = Stage(
            name=f"Deploy_{env_name}",
            jobs=[deploy_job],
            dependencies=["Test"],
            environment=env,
        )

        if requires_approval:
            stage.condition = "and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))"

        self.add_stage(stage)


class AzureAdapter:
    """
    Adapter for generating Azure Pipelines.

    Provides factory methods for common pipeline types.
    """

    @staticmethod
    def create_build_pipeline(
        pool: str = "ubuntu-latest",
        cache_paths: Optional[List[str]] = None,
    ) -> AzurePipeline:
        """Create a build-only pipeline."""
        pipeline = AzurePipeline(
            pipeline_type=PipelineType.BUILD,
            pool=pool,
            cache=CacheConfig(
                key="deps | $(Agent.OS)",
                paths=cache_paths or [".cache", "node_modules"],
            ),
        )
        pipeline.add_build_stage()
        return pipeline

    @staticmethod
    def create_test_pipeline(
        pool: str = "ubuntu-latest",
        matrix: Optional[MatrixConfig] = None,
    ) -> AzurePipeline:
        """Create a test pipeline with optional matrix (AC-4)."""
        pipeline = AzurePipeline(
            pipeline_type=PipelineType.TEST,
            pool=pool,
            matrix=matrix,
        )
        pipeline.add_build_stage()
        pipeline.add_test_stage()
        return pipeline

    @staticmethod
    def create_deploy_pipeline(
        environments: Optional[List[str]] = None,
        rollback_enabled: bool = True,
    ) -> AzurePipeline:
        """Create a deployment pipeline (AC-5, AC-6)."""
        envs = environments or ["staging", "production"]

        rollback = RollbackConfig(
            enabled=rollback_enabled,
            strategy="previous_version",
        ) if rollback_enabled else None

        pipeline = AzurePipeline(
            pipeline_type=PipelineType.DEPLOY,
            rollback=rollback,
        )

        pipeline.add_build_stage()
        pipeline.add_test_stage()

        for i, env in enumerate(envs):
            requires_approval = i > 0
            pipeline.add_deploy_stage(env, requires_approval)

        return pipeline

    @staticmethod
    def create_release_pipeline() -> AzurePipeline:
        """Create a release pipeline."""
        pipeline = AzurePipeline(
            pipeline_type=PipelineType.RELEASE,
            trigger_branches=["refs/tags/*"],
            variables={
                "releaseVersion": "$(Build.SourceBranchName)",
            },
        )

        pipeline.add_build_stage()
        pipeline.add_test_stage()

        # Release stage
        release_job = Job(
            name="Release",
            steps=[
                Step(name="Create release", script="echo 'Creating release $(releaseVersion)'"),
                Step(name="Publish package", script="twine upload dist/*"),
            ],
        )
        pipeline.add_stage(Stage(
            name="Release",
            jobs=[release_job],
            dependencies=["Test"],
            condition="startsWith(variables['Build.SourceBranch'], 'refs/tags/')",
        ))

        return pipeline
