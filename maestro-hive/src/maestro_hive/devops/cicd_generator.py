#!/usr/bin/env python3
"""
CICD Generator: Generate CI/CD pipeline configurations.

This module provides automated generation of CI/CD pipeline configurations
for multiple platforms including GitHub Actions, GitLab CI, Azure DevOps, and Jenkins.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class CICDPlatform(Enum):
    """Supported CI/CD platforms."""
    GITHUB_ACTIONS = "github_actions"
    GITLAB_CI = "gitlab_ci"
    AZURE_DEVOPS = "azure_devops"
    JENKINS = "jenkins"
    CIRCLECI = "circleci"


class PipelineStage(Enum):
    """Standard pipeline stages."""
    BUILD = "build"
    TEST = "test"
    LINT = "lint"
    SECURITY_SCAN = "security_scan"
    INTEGRATION_TEST = "integration_test"
    DEPLOY_DEV = "deploy_dev"
    DEPLOY_STAGING = "deploy_staging"
    DEPLOY_PROD = "deploy_prod"
    NOTIFY = "notify"


@dataclass
class StageConfig:
    """Configuration for a pipeline stage."""
    name: str
    stage: PipelineStage
    commands: List[str]
    environment: Dict[str, str] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    conditions: Dict[str, Any] = field(default_factory=dict)
    timeout_minutes: int = 30
    retry_count: int = 0
    artifacts: List[str] = field(default_factory=list)
    cache_paths: List[str] = field(default_factory=list)


@dataclass
class PipelineConfig:
    """Complete pipeline configuration."""
    name: str
    platform: CICDPlatform
    stages: List[StageConfig]
    triggers: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, str] = field(default_factory=dict)
    secrets: List[str] = field(default_factory=list)
    docker_image: Optional[str] = None
    python_version: str = "3.11"
    node_version: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CICDGenerator:
    """
    Generate CI/CD pipeline configurations for multiple platforms.

    Supports generation of complete pipeline definitions from a
    platform-agnostic configuration.
    """

    def __init__(self, project_type: str = "python"):
        """
        Initialize the generator.

        Args:
            project_type: Type of project (python, node, java, go)
        """
        self.project_type = project_type
        self._templates: Dict[CICDPlatform, Dict[str, Any]] = {}
        self._load_default_templates()

    def generate(
        self,
        config: PipelineConfig,
        output_dir: Optional[Path] = None
    ) -> Dict[str, str]:
        """
        Generate pipeline configuration files.

        Args:
            config: Pipeline configuration
            output_dir: Directory to write files (optional)

        Returns:
            Dictionary of filename -> content
        """
        generators = {
            CICDPlatform.GITHUB_ACTIONS: self._generate_github_actions,
            CICDPlatform.GITLAB_CI: self._generate_gitlab_ci,
            CICDPlatform.AZURE_DEVOPS: self._generate_azure_devops,
            CICDPlatform.JENKINS: self._generate_jenkins,
            CICDPlatform.CIRCLECI: self._generate_circleci,
        }

        generator = generators.get(config.platform)
        if not generator:
            raise ValueError(f"Unsupported platform: {config.platform}")

        files = generator(config)

        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            for filename, content in files.items():
                file_path = output_dir / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
                logger.info(f"Generated: {file_path}")

        return files

    def create_default_config(
        self,
        name: str,
        platform: CICDPlatform,
        include_security: bool = True,
        include_deployment: bool = False
    ) -> PipelineConfig:
        """
        Create a default pipeline configuration.

        Args:
            name: Pipeline name
            platform: Target platform
            include_security: Include security scanning
            include_deployment: Include deployment stages

        Returns:
            PipelineConfig with default stages
        """
        stages = []

        # Lint stage
        if self.project_type == "python":
            stages.append(StageConfig(
                name="lint",
                stage=PipelineStage.LINT,
                commands=[
                    "pip install flake8 black mypy",
                    "flake8 src/",
                    "black --check src/",
                    "mypy src/"
                ],
                cache_paths=["~/.cache/pip"]
            ))
        elif self.project_type == "node":
            stages.append(StageConfig(
                name="lint",
                stage=PipelineStage.LINT,
                commands=[
                    "npm ci",
                    "npm run lint"
                ],
                cache_paths=["node_modules"]
            ))

        # Build stage
        if self.project_type == "python":
            stages.append(StageConfig(
                name="build",
                stage=PipelineStage.BUILD,
                commands=[
                    "pip install -e .",
                    "pip install build",
                    "python -m build"
                ],
                artifacts=["dist/*"],
                dependencies=["lint"]
            ))
        elif self.project_type == "node":
            stages.append(StageConfig(
                name="build",
                stage=PipelineStage.BUILD,
                commands=[
                    "npm ci",
                    "npm run build"
                ],
                artifacts=["dist/*", "build/*"],
                dependencies=["lint"]
            ))

        # Test stage
        if self.project_type == "python":
            stages.append(StageConfig(
                name="test",
                stage=PipelineStage.TEST,
                commands=[
                    "pip install pytest pytest-cov",
                    "pytest --cov=src --cov-report=xml"
                ],
                artifacts=["coverage.xml"],
                dependencies=["build"]
            ))
        elif self.project_type == "node":
            stages.append(StageConfig(
                name="test",
                stage=PipelineStage.TEST,
                commands=[
                    "npm ci",
                    "npm test -- --coverage"
                ],
                artifacts=["coverage/*"],
                dependencies=["build"]
            ))

        # Security scan
        if include_security:
            if self.project_type == "python":
                stages.append(StageConfig(
                    name="security",
                    stage=PipelineStage.SECURITY_SCAN,
                    commands=[
                        "pip install bandit safety",
                        "bandit -r src/ -f json -o bandit-report.json || true",
                        "safety check --json > safety-report.json || true"
                    ],
                    artifacts=["*-report.json"],
                    dependencies=["test"]
                ))
            elif self.project_type == "node":
                stages.append(StageConfig(
                    name="security",
                    stage=PipelineStage.SECURITY_SCAN,
                    commands=[
                        "npm audit --json > npm-audit.json || true"
                    ],
                    artifacts=["npm-audit.json"],
                    dependencies=["test"]
                ))

        # Deployment stages
        if include_deployment:
            stages.extend([
                StageConfig(
                    name="deploy_staging",
                    stage=PipelineStage.DEPLOY_STAGING,
                    commands=["./deploy.sh staging"],
                    conditions={"branch": "develop"},
                    dependencies=["security"] if include_security else ["test"]
                ),
                StageConfig(
                    name="deploy_prod",
                    stage=PipelineStage.DEPLOY_PROD,
                    commands=["./deploy.sh production"],
                    conditions={"branch": "main", "manual": True},
                    dependencies=["deploy_staging"]
                )
            ])

        return PipelineConfig(
            name=name,
            platform=platform,
            stages=stages,
            triggers={"push": {"branches": ["main", "develop"]}, "pull_request": {}},
            python_version="3.11" if self.project_type == "python" else None,
            node_version="18" if self.project_type == "node" else None
        )

    def _generate_github_actions(self, config: PipelineConfig) -> Dict[str, str]:
        """Generate GitHub Actions workflow."""
        workflow = {
            "name": config.name,
            "on": config.triggers,
            "env": config.variables,
            "jobs": {}
        }

        for stage in config.stages:
            job = {
                "runs-on": "ubuntu-latest",
                "steps": [
                    {"uses": "actions/checkout@v4"}
                ]
            }

            # Setup language
            if config.python_version:
                job["steps"].append({
                    "name": "Set up Python",
                    "uses": "actions/setup-python@v5",
                    "with": {"python-version": config.python_version}
                })

            if config.node_version:
                job["steps"].append({
                    "name": "Set up Node",
                    "uses": "actions/setup-node@v4",
                    "with": {"node-version": config.node_version}
                })

            # Cache
            if stage.cache_paths:
                job["steps"].append({
                    "name": "Cache",
                    "uses": "actions/cache@v4",
                    "with": {
                        "path": "\n".join(stage.cache_paths),
                        "key": f"${{{{ runner.os }}}}-{stage.name}-${{{{ hashFiles('**/requirements*.txt', '**/package-lock.json') }}}}"
                    }
                })

            # Commands
            for cmd in stage.commands:
                job["steps"].append({
                    "name": f"Run: {cmd[:50]}",
                    "run": cmd
                })

            # Artifacts
            if stage.artifacts:
                job["steps"].append({
                    "name": "Upload artifacts",
                    "uses": "actions/upload-artifact@v4",
                    "with": {
                        "name": f"{stage.name}-artifacts",
                        "path": "\n".join(stage.artifacts)
                    },
                    "if": "always()"
                })

            # Dependencies
            if stage.dependencies:
                job["needs"] = stage.dependencies

            # Conditions
            if stage.conditions.get("branch"):
                job["if"] = f"github.ref == 'refs/heads/{stage.conditions['branch']}'"

            if stage.conditions.get("manual"):
                workflow.setdefault("on", {})["workflow_dispatch"] = {}

            job["timeout-minutes"] = stage.timeout_minutes

            workflow["jobs"][stage.name] = job

        # Convert to YAML-like string (simplified)
        content = self._dict_to_yaml(workflow)
        return {".github/workflows/ci.yml": content}

    def _generate_gitlab_ci(self, config: PipelineConfig) -> Dict[str, str]:
        """Generate GitLab CI configuration."""
        ci_config = {
            "stages": [s.stage.value for s in config.stages],
            "variables": config.variables
        }

        if config.docker_image:
            ci_config["image"] = config.docker_image
        elif config.python_version:
            ci_config["image"] = f"python:{config.python_version}"
        elif config.node_version:
            ci_config["image"] = f"node:{config.node_version}"

        for stage in config.stages:
            job = {
                "stage": stage.stage.value,
                "script": stage.commands
            }

            if stage.dependencies:
                job["needs"] = stage.dependencies

            if stage.artifacts:
                job["artifacts"] = {
                    "paths": stage.artifacts,
                    "expire_in": "1 week"
                }

            if stage.cache_paths:
                job["cache"] = {"paths": stage.cache_paths}

            if stage.conditions.get("branch"):
                job["only"] = {"refs": [stage.conditions["branch"]]}

            if stage.conditions.get("manual"):
                job["when"] = "manual"

            ci_config[stage.name] = job

        content = self._dict_to_yaml(ci_config)
        return {".gitlab-ci.yml": content}

    def _generate_azure_devops(self, config: PipelineConfig) -> Dict[str, str]:
        """Generate Azure DevOps pipeline."""
        pipeline = {
            "trigger": list(config.triggers.get("push", {}).get("branches", ["main"])),
            "pool": {"vmImage": "ubuntu-latest"},
            "variables": config.variables,
            "stages": []
        }

        for stage in config.stages:
            azure_stage = {
                "stage": stage.name,
                "displayName": stage.name.replace("_", " ").title(),
                "jobs": [{
                    "job": stage.name,
                    "steps": []
                }]
            }

            if stage.dependencies:
                azure_stage["dependsOn"] = stage.dependencies

            job_steps = azure_stage["jobs"][0]["steps"]

            # Setup tasks
            if config.python_version:
                job_steps.append({
                    "task": "UsePythonVersion@0",
                    "inputs": {"versionSpec": config.python_version}
                })

            if config.node_version:
                job_steps.append({
                    "task": "NodeTool@0",
                    "inputs": {"versionSpec": config.node_version}
                })

            # Script tasks
            for cmd in stage.commands:
                job_steps.append({
                    "script": cmd,
                    "displayName": cmd[:50]
                })

            # Publish artifacts
            if stage.artifacts:
                job_steps.append({
                    "task": "PublishBuildArtifacts@1",
                    "inputs": {
                        "pathToPublish": stage.artifacts[0],
                        "artifactName": f"{stage.name}-artifacts"
                    }
                })

            pipeline["stages"].append(azure_stage)

        content = self._dict_to_yaml(pipeline)
        return {"azure-pipelines.yml": content}

    def _generate_jenkins(self, config: PipelineConfig) -> Dict[str, str]:
        """Generate Jenkinsfile."""
        lines = [
            "pipeline {",
            "    agent any",
            "",
            "    environment {"
        ]

        for key, value in config.variables.items():
            lines.append(f"        {key} = '{value}'")

        lines.extend([
            "    }",
            "",
            "    stages {"
        ])

        for stage in config.stages:
            lines.extend([
                f"        stage('{stage.name}') {{",
                "            steps {"
            ])

            for cmd in stage.commands:
                lines.append(f"                sh '{cmd}'")

            lines.extend([
                "            }",
                "        }",
                ""
            ])

        lines.extend([
            "    }",
            "",
            "    post {",
            "        always {",
            "            cleanWs()",
            "        }",
            "    }",
            "}"
        ])

        return {"Jenkinsfile": "\n".join(lines)}

    def _generate_circleci(self, config: PipelineConfig) -> Dict[str, str]:
        """Generate CircleCI configuration."""
        circle_config = {
            "version": 2.1,
            "jobs": {},
            "workflows": {
                config.name: {
                    "jobs": []
                }
            }
        }

        for stage in config.stages:
            job = {
                "docker": [{"image": f"cimg/python:{config.python_version}" if config.python_version else "cimg/base:stable"}],
                "steps": ["checkout"]
            }

            for cmd in stage.commands:
                job["steps"].append({"run": cmd})

            if stage.artifacts:
                job["steps"].append({
                    "store_artifacts": {
                        "path": stage.artifacts[0]
                    }
                })

            circle_config["jobs"][stage.name] = job

            workflow_job = {stage.name: {}}
            if stage.dependencies:
                workflow_job[stage.name]["requires"] = stage.dependencies

            circle_config["workflows"][config.name]["jobs"].append(workflow_job)

        content = self._dict_to_yaml(circle_config)
        return {".circleci/config.yml": content}

    def _dict_to_yaml(self, data: Dict[str, Any], indent: int = 0) -> str:
        """Convert dictionary to YAML-like string."""
        lines = []
        prefix = "  " * indent

        for key, value in data.items():
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(self._dict_to_yaml(value, indent + 1))
            elif isinstance(value, list):
                lines.append(f"{prefix}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        lines.append(f"{prefix}  -")
                        for k, v in item.items():
                            if isinstance(v, (dict, list)):
                                lines.append(f"{prefix}    {k}:")
                                lines.append(self._dict_to_yaml({k: v}, indent + 2).split(f"{k}:")[1])
                            else:
                                lines.append(f"{prefix}    {k}: {self._format_value(v)}")
                    else:
                        lines.append(f"{prefix}  - {self._format_value(item)}")
            else:
                lines.append(f"{prefix}{key}: {self._format_value(value)}")

        return "\n".join(lines)

    def _format_value(self, value: Any) -> str:
        """Format a value for YAML output."""
        if value is None:
            return "null"
        if isinstance(value, bool):
            return str(value).lower()
        if isinstance(value, str):
            if "\n" in value or ":" in value or value.startswith("-"):
                return f'"{value}"'
            return value
        return str(value)

    def _load_default_templates(self) -> None:
        """Load default pipeline templates."""
        # Templates can be extended with additional defaults
        pass


# Convenience function
def create_cicd_generator(**kwargs) -> CICDGenerator:
    """Create a new CICDGenerator instance."""
    return CICDGenerator(**kwargs)


def generate_pipeline(
    name: str,
    platform: CICDPlatform,
    project_type: str = "python",
    output_dir: Optional[str] = None,
    **options
) -> Dict[str, str]:
    """
    Convenience function to generate a pipeline.

    Args:
        name: Pipeline name
        platform: Target platform
        project_type: Project type
        output_dir: Output directory
        **options: Additional options (include_security, include_deployment)

    Returns:
        Generated file contents
    """
    generator = CICDGenerator(project_type)
    config = generator.create_default_config(name, platform, **options)
    return generator.generate(config, Path(output_dir) if output_dir else None)
