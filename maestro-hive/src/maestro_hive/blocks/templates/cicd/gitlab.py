"""
GitLab CI Pipeline Templates

Generates .gitlab-ci.yml files with:
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
class GitLabPipeline(PipelineTemplate):
    """
    GitLab CI pipeline template.

    Generates .gitlab-ci.yml format with all features:
    - stages, jobs, scripts
    - cache, artifacts
    - rules, needs, dependencies
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
        image: str = "python:3.11",
    ):
        super().__init__(
            pipeline_type=pipeline_type,
            platform=Platform.GITLAB,
            stages=stages or [],
            variables=variables or {},
            cache=cache,
            artifacts=artifacts,
            matrix=matrix,
            environments=environments or [],
            rollback=rollback,
        )
        self.image = image

    def render(self) -> str:
        """Render to .gitlab-ci.yml format."""
        config: Dict[str, Any] = {}

        # Default image
        if self.image:
            config["image"] = self.image

        # Stages list
        if self.stages:
            config["stages"] = [s.name for s in self.stages]

        # Global variables
        if self.variables:
            config["variables"] = self.variables

        # Global cache (AC-3)
        if self.cache:
            config["cache"] = self.cache.to_gitlab()

        # Jobs for each stage
        for stage in self.stages:
            for job in stage.jobs:
                job_config = self._render_job(job, stage.name)
                config[job.name] = job_config

        return yaml.dump(config, default_flow_style=False, sort_keys=False)

    def _render_job(self, job: Job, stage_name: str) -> Dict[str, Any]:
        """Render a single job configuration."""
        job_config: Dict[str, Any] = {"stage": stage_name}

        # Image override
        if job.image:
            job_config["image"] = job.image

        # Services (databases, etc.)
        if job.services:
            job_config["services"] = job.services

        # Variables
        if job.variables:
            job_config["variables"] = job.variables

        # Scripts
        if job.steps:
            before_script = []
            script = []
            after_script = []

            for step in job.steps:
                if step.name.startswith("before_"):
                    before_script.append(step.script)
                elif step.name.startswith("after_"):
                    after_script.append(step.script)
                else:
                    script.append(step.script)

            if before_script:
                job_config["before_script"] = before_script
            job_config["script"] = script if script else ["echo 'No script defined'"]
            if after_script:
                job_config["after_script"] = after_script

        # Cache (AC-3)
        if job.cache:
            job_config["cache"] = job.cache.to_gitlab()

        # Artifacts (AC-2)
        if job.artifacts:
            job_config["artifacts"] = job.artifacts.to_gitlab()

        # Dependencies/needs
        if job.needs:
            job_config["needs"] = job.needs

        # Rules for conditional execution
        if job.rules:
            job_config["rules"] = job.rules

        # Timeout
        if job.timeout:
            job_config["timeout"] = job.timeout

        # Retry
        if job.retry > 0:
            job_config["retry"] = job.retry

        # Allow failure
        if job.allow_failure:
            job_config["allow_failure"] = job.allow_failure

        # Environment (AC-5)
        if job.environment:
            job_config["environment"] = job.environment.to_gitlab()

        return job_config

    def validate(self) -> List[str]:
        """Validate the pipeline configuration."""
        errors = []

        if not self.stages:
            errors.append("Pipeline must have at least one stage")

        for stage in self.stages:
            if not stage.jobs:
                errors.append(f"Stage '{stage.name}' has no jobs")

            for job in stage.jobs:
                if not job.steps:
                    errors.append(f"Job '{job.name}' has no steps")

        # Check for circular dependencies
        stage_names = {s.name for s in self.stages}
        for stage in self.stages:
            for dep in stage.dependencies:
                if dep not in stage_names:
                    errors.append(f"Stage '{stage.name}' depends on unknown stage '{dep}'")

        return errors

    def add_build_stage(self) -> None:
        """Add a standard build stage."""
        build_job = Job(
            name="build",
            steps=[
                Step(name="install", script="pip install -r requirements.txt"),
                Step(name="build", script="python setup.py build"),
            ],
            cache=CacheConfig(
                key="${CI_COMMIT_REF_SLUG}",
                paths=[".cache/pip", ".venv"],
                policy="pull-push",
            ),
            artifacts=ArtifactConfig(
                paths=["dist/"],
                expire_in="1 week",
            ),
        )
        self.add_stage(Stage(name="build", jobs=[build_job]))

    def add_test_stage(self) -> None:
        """Add a standard test stage."""
        test_job = Job(
            name="test",
            steps=[
                Step(name="test", script="pytest --cov --junitxml=report.xml"),
            ],
            needs=["build"],
            artifacts=ArtifactConfig(
                paths=["coverage/"],
                reports={"junit": "report.xml", "coverage_report": {"coverage_format": "cobertura", "path": "coverage.xml"}},
            ),
        )
        self.add_stage(Stage(name="test", jobs=[test_job]))

    def add_deploy_stage(self, env_name: str = "staging", requires_approval: bool = False) -> None:
        """Add a deployment stage with environment promotion (AC-5)."""
        env = Environment(
            name=env_name,
            requires_approval=requires_approval,
            url=f"https://{env_name}.example.com",
        )

        deploy_job = Job(
            name=f"deploy_{env_name}",
            steps=[
                Step(name="deploy", script="./deploy.sh"),
            ],
            needs=["test"],
            environment=env,
            rules=[
                {"if": f"$CI_COMMIT_BRANCH == 'main'", "when": "manual" if requires_approval else "on_success"},
            ],
        )

        # Add rollback capability (AC-6)
        if self.rollback and self.rollback.enabled:
            rollback_job = Job(
                name=f"rollback_{env_name}",
                steps=[
                    Step(name="rollback", script=self.rollback.generate_rollback_script()),
                ],
                rules=[{"when": "manual"}],
                environment=env,
            )
            self.add_stage(Stage(name=f"deploy_{env_name}", jobs=[deploy_job, rollback_job], environment=env))
        else:
            self.add_stage(Stage(name=f"deploy_{env_name}", jobs=[deploy_job], environment=env))


class GitLabAdapter:
    """
    Adapter for generating GitLab CI pipelines.

    Provides factory methods for common pipeline types.
    """

    @staticmethod
    def create_build_pipeline(
        image: str = "python:3.11",
        cache_paths: Optional[List[str]] = None,
        artifact_paths: Optional[List[str]] = None,
    ) -> GitLabPipeline:
        """Create a build-only pipeline."""
        pipeline = GitLabPipeline(
            pipeline_type=PipelineType.BUILD,
            image=image,
            cache=CacheConfig(
                key="${CI_COMMIT_REF_SLUG}",
                paths=cache_paths or [".cache/pip", "node_modules"],
            ),
            artifacts=ArtifactConfig(
                paths=artifact_paths or ["dist/", "build/"],
                expire_in="1 week",
            ),
        )
        pipeline.add_build_stage()
        return pipeline

    @staticmethod
    def create_test_pipeline(
        image: str = "python:3.11",
        matrix: Optional[MatrixConfig] = None,
    ) -> GitLabPipeline:
        """Create a test pipeline with optional matrix builds (AC-4)."""
        pipeline = GitLabPipeline(
            pipeline_type=PipelineType.TEST,
            image=image,
            matrix=matrix,
        )
        pipeline.add_build_stage()
        pipeline.add_test_stage()
        return pipeline

    @staticmethod
    def create_deploy_pipeline(
        environments: Optional[List[str]] = None,
        rollback_enabled: bool = True,
    ) -> GitLabPipeline:
        """Create a deployment pipeline with environment promotion (AC-5, AC-6)."""
        envs = environments or ["staging", "production"]

        rollback = RollbackConfig(
            enabled=rollback_enabled,
            strategy="previous_version",
            health_check=HealthCheck(
                endpoint="/health",
                expected_status=200,
                timeout="5m",
            ),
        ) if rollback_enabled else None

        pipeline = GitLabPipeline(
            pipeline_type=PipelineType.DEPLOY,
            rollback=rollback,
        )

        pipeline.add_build_stage()
        pipeline.add_test_stage()

        for i, env in enumerate(envs):
            requires_approval = i > 0  # First env auto, rest manual
            pipeline.add_deploy_stage(env, requires_approval)

        return pipeline

    @staticmethod
    def create_release_pipeline() -> GitLabPipeline:
        """Create a release pipeline with versioning."""
        pipeline = GitLabPipeline(
            pipeline_type=PipelineType.RELEASE,
            variables={
                "RELEASE_VERSION": "${CI_COMMIT_TAG}",
            },
        )

        # Build stage
        pipeline.add_build_stage()

        # Test stage
        pipeline.add_test_stage()

        # Release stage
        release_job = Job(
            name="release",
            steps=[
                Step(name="version", script="echo $RELEASE_VERSION"),
                Step(name="changelog", script="git-changelog --output CHANGELOG.md"),
                Step(name="publish", script="twine upload dist/*"),
            ],
            rules=[
                {"if": "$CI_COMMIT_TAG", "when": "on_success"},
            ],
            artifacts=ArtifactConfig(
                paths=["CHANGELOG.md", "dist/"],
            ),
        )
        pipeline.add_stage(Stage(name="release", jobs=[release_job]))

        return pipeline
