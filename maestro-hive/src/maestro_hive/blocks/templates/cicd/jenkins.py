"""
Jenkins Pipeline Templates

Generates Jenkinsfile (declarative pipeline) with:
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
class JenkinsPipeline(PipelineTemplate):
    """
    Jenkins Pipeline template.

    Generates Jenkinsfile declarative syntax with:
    - stages, steps
    - agent configuration
    - post actions
    - environment variables
    - input for manual approvals
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
        agent: str = "any",
        docker_image: Optional[str] = None,
    ):
        super().__init__(
            pipeline_type=pipeline_type,
            platform=Platform.JENKINS,
            stages=stages or [],
            variables=variables or {},
            cache=cache,
            artifacts=artifacts,
            matrix=matrix,
            environments=environments or [],
            rollback=rollback,
        )
        self.agent = agent
        self.docker_image = docker_image

    def render(self) -> str:
        """Render to Jenkinsfile declarative syntax."""
        lines = ["pipeline {"]

        # Agent configuration
        lines.extend(self._render_agent())

        # Environment variables
        if self.variables:
            lines.extend(self._render_environment())

        # Options
        lines.extend(self._render_options())

        # Stages
        lines.append("    stages {")
        for stage in self.stages:
            lines.extend(self._render_stage(stage))
        lines.append("    }")

        # Post actions
        lines.extend(self._render_post())

        lines.append("}")
        return "\n".join(lines)

    def _render_agent(self) -> List[str]:
        """Render agent configuration."""
        if self.docker_image:
            return [
                "    agent {",
                "        docker {",
                f'            image "{self.docker_image}"',
                "        }",
                "    }",
            ]
        return [f"    agent {self.agent}"]

    def _render_environment(self) -> List[str]:
        """Render environment variables."""
        lines = ["    environment {"]
        for key, value in self.variables.items():
            lines.append(f'        {key} = "{value}"')
        lines.append("    }")
        return lines

    def _render_options(self) -> List[str]:
        """Render pipeline options."""
        return [
            "    options {",
            "        buildDiscarder(logRotator(numToKeepStr: '10'))",
            "        timestamps()",
            "        disableConcurrentBuilds()",
            f"        timeout(time: 1, unit: 'HOURS')",
            "    }",
        ]

    def _render_stage(self, stage: Stage) -> List[str]:
        """Render a single stage."""
        lines = [f'        stage("{stage.name}") {{']

        # Matrix configuration (AC-4)
        if self.matrix and self.matrix.dimensions and len(self.stages) > 0 and stage == self.stages[0]:
            lines.extend(self._render_matrix())

        # Environment for deployment (AC-5)
        if stage.environment and stage.environment.requires_approval:
            lines.extend([
                "            input {",
                f'                message "Deploy to {stage.environment.name}?"',
                '                ok "Deploy"',
                "            }",
            ])

        # Steps
        lines.append("            steps {")

        # Cache restore (AC-3)
        if self.cache:
            lines.append(self.cache.to_jenkins())

        # Actual steps
        for job in stage.jobs:
            for step in job.steps:
                lines.extend(self._render_step(step))

        # Artifact archive (AC-2)
        if self.artifacts:
            lines.append(f'                {self.artifacts.to_jenkins()}')

        lines.append("            }")

        # Post actions for stage
        if stage.environment:
            lines.extend(self._render_stage_post(stage))

        lines.append("        }")
        return lines

    def _render_matrix(self) -> List[str]:
        """Render matrix configuration (AC-4)."""
        if not self.matrix:
            return []

        lines = ["            matrix {"]
        lines.append("                axes {")

        for dim_name, dim_values in self.matrix.dimensions.items():
            values_str = ", ".join([f'"{v}"' for v in dim_values])
            lines.append(f'                    axis {{ name "{dim_name}"; values {values_str} }}')

        lines.append("                }")

        if not self.matrix.fail_fast:
            lines.append("                failFast false")

        lines.append("            }")
        return lines

    def _render_step(self, step: Step) -> List[str]:
        """Render a single step."""
        lines = []

        # Conditional step
        if step.condition:
            lines.append(f'                when {{ expression {{ {step.condition} }} }}')

        # Script with retry
        if step.retry > 0:
            lines.append(f"                retry({step.retry}) {{")
            lines.append(f'                    sh "{step.script}"')
            lines.append("                }")
        else:
            lines.append(f'                sh "{step.script}"')

        return lines

    def _render_stage_post(self, stage: Stage) -> List[str]:
        """Render post actions for deployment stages."""
        lines = ["            post {"]

        # Success notification
        lines.extend([
            "                success {",
            f'                    echo "Deployed to {stage.environment.name if stage.environment else "unknown"} successfully"',
            "                }",
        ])

        # Failure with rollback (AC-6)
        if self.rollback and self.rollback.enabled:
            lines.extend([
                "                failure {",
                f'                    echo "Deployment failed, initiating rollback"',
                '                    sh "./rollback.sh"',
                "                }",
            ])

        lines.append("            }")
        return lines

    def _render_post(self) -> List[str]:
        """Render global post actions."""
        return [
            "    post {",
            "        always {",
            '            echo "Pipeline completed"',
            "            cleanWs()",
            "        }",
            "        success {",
            '            echo "Pipeline succeeded"',
            "        }",
            "        failure {",
            '            echo "Pipeline failed"',
            "        }",
            "    }",
        ]

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
            name="build",
            steps=[
                Step(name="install", script="pip install -r requirements.txt"),
                Step(name="build", script="python setup.py build"),
            ],
        )
        self.add_stage(Stage(name="Build", jobs=[build_job]))

    def add_test_stage(self) -> None:
        """Add a standard test stage."""
        test_job = Job(
            name="test",
            steps=[
                Step(name="test", script="pytest --cov --junitxml=test-results.xml"),
            ],
        )
        self.add_stage(Stage(name="Test", jobs=[test_job]))

    def add_deploy_stage(self, env_name: str = "staging", requires_approval: bool = False) -> None:
        """Add a deployment stage (AC-5)."""
        env = Environment(
            name=env_name,
            requires_approval=requires_approval,
        )

        deploy_job = Job(
            name=f"deploy_{env_name}",
            steps=[
                Step(name="deploy", script="./deploy.sh"),
            ],
            environment=env,
        )

        self.add_stage(Stage(
            name=f"Deploy to {env_name.title()}",
            jobs=[deploy_job],
            environment=env,
        ))


class JenkinsAdapter:
    """
    Adapter for generating Jenkins Pipelines.

    Provides factory methods for common pipeline types.
    """

    @staticmethod
    def create_build_pipeline(
        agent: str = "any",
        docker_image: Optional[str] = None,
    ) -> JenkinsPipeline:
        """Create a build-only pipeline."""
        pipeline = JenkinsPipeline(
            pipeline_type=PipelineType.BUILD,
            agent=agent,
            docker_image=docker_image,
            cache=CacheConfig(
                paths=[".cache", "node_modules"],
            ),
            artifacts=ArtifactConfig(
                paths=["dist/**", "build/**"],
            ),
        )
        pipeline.add_build_stage()
        return pipeline

    @staticmethod
    def create_test_pipeline(
        agent: str = "any",
        matrix: Optional[MatrixConfig] = None,
    ) -> JenkinsPipeline:
        """Create a test pipeline with optional matrix (AC-4)."""
        pipeline = JenkinsPipeline(
            pipeline_type=PipelineType.TEST,
            agent=agent,
            matrix=matrix,
        )
        pipeline.add_build_stage()
        pipeline.add_test_stage()
        return pipeline

    @staticmethod
    def create_deploy_pipeline(
        environments: Optional[List[str]] = None,
        rollback_enabled: bool = True,
    ) -> JenkinsPipeline:
        """Create a deployment pipeline (AC-5, AC-6)."""
        envs = environments or ["staging", "production"]

        rollback = RollbackConfig(
            enabled=rollback_enabled,
            strategy="previous_version",
        ) if rollback_enabled else None

        pipeline = JenkinsPipeline(
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
    def create_release_pipeline() -> JenkinsPipeline:
        """Create a release pipeline."""
        pipeline = JenkinsPipeline(
            pipeline_type=PipelineType.RELEASE,
            variables={
                "RELEASE_VERSION": "${env.TAG_NAME}",
            },
        )

        pipeline.add_build_stage()
        pipeline.add_test_stage()

        # Release stage
        release_job = Job(
            name="release",
            steps=[
                Step(name="tag", script="git tag -a $RELEASE_VERSION -m 'Release $RELEASE_VERSION'"),
                Step(name="publish", script="twine upload dist/*"),
            ],
        )
        pipeline.add_stage(Stage(name="Release", jobs=[release_job]))

        return pipeline
