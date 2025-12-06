"""
CI/CD Pipeline Template Models

Core data models for pipeline templates supporting:
- Multi-platform generation
- Artifact management (AC-2)
- Caching strategies (AC-3)
- Matrix builds (AC-4)
- Environment promotion (AC-5)
- Rollback capability (AC-6)

Reference: MD-2522 CI/CD Pipeline Templates
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod


class PipelineType(Enum):
    """Types of CI/CD pipelines."""
    BUILD = "build"
    TEST = "test"
    DEPLOY = "deploy"
    RELEASE = "release"


class Platform(Enum):
    """Supported CI/CD platforms."""
    GITLAB = "gitlab"
    AZURE = "azure"
    JENKINS = "jenkins"
    GITHUB = "github"


@dataclass
class Step:
    """A single step within a job."""
    name: str
    script: str
    condition: Optional[str] = None
    timeout: Optional[str] = None
    retry: int = 0
    allow_failure: bool = False
    environment: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result: Dict[str, Any] = {"name": self.name, "script": self.script}
        if self.condition:
            result["condition"] = self.condition
        if self.timeout:
            result["timeout"] = self.timeout
        if self.retry > 0:
            result["retry"] = self.retry
        if self.allow_failure:
            result["allow_failure"] = self.allow_failure
        if self.environment:
            result["environment"] = self.environment
        return result


@dataclass
class CacheConfig:
    """
    Cache configuration for dependency and build caching (AC-3).

    Supports multiple caching strategies:
    - Dependency caching (node_modules, .venv, .m2)
    - Build caching (.cache, dist)
    - Docker layer caching
    """
    key: str = "${CI_COMMIT_REF_SLUG}"
    paths: List[str] = field(default_factory=list)
    policy: str = "pull-push"  # pull, push, pull-push
    fallback_keys: List[str] = field(default_factory=list)
    untracked: bool = False
    when: str = "on_success"  # on_success, on_failure, always

    def to_gitlab(self) -> Dict[str, Any]:
        """Convert to GitLab CI cache format."""
        result: Dict[str, Any] = {
            "key": self.key,
            "paths": self.paths,
            "policy": self.policy,
        }
        if self.fallback_keys:
            result["key"] = {"files": self.fallback_keys, "prefix": self.key}
        if self.untracked:
            result["untracked"] = self.untracked
        result["when"] = self.when
        return result

    def to_azure(self) -> Dict[str, Any]:
        """Convert to Azure Pipelines cache format."""
        return {
            "key": f"'{self.key}' | **/*.lock",
            "path": self.paths[0] if self.paths else ".cache",
            "restoreKeys": self.fallback_keys or [self.key],
        }

    def to_jenkins(self) -> str:
        """Convert to Jenkins pipeline cache syntax."""
        paths_str = ", ".join([f'"{p}"' for p in self.paths])
        return f"""
        cache(caches: [
            [$class: 'ArbitraryFileCache', path: {paths_str}, cacheValidityDecidingFile: '**/package-lock.json']
        ])"""


@dataclass
class ArtifactConfig:
    """
    Artifact configuration for build outputs (AC-2).

    Manages:
    - Build artifacts (dist/, coverage/)
    - Test reports (JUnit, coverage)
    - Retention policies
    """
    paths: List[str] = field(default_factory=list)
    expire_in: str = "7 days"
    reports: Dict[str, str] = field(default_factory=dict)
    upload_on_failure: bool = False
    exclude: List[str] = field(default_factory=list)
    name: str = "artifacts"

    def to_gitlab(self) -> Dict[str, Any]:
        """Convert to GitLab CI artifacts format."""
        result: Dict[str, Any] = {
            "paths": self.paths,
            "expire_in": self.expire_in,
        }
        if self.reports:
            result["reports"] = self.reports
        if self.upload_on_failure:
            result["when"] = "always"
        if self.exclude:
            result["exclude"] = self.exclude
        if self.name != "artifacts":
            result["name"] = self.name
        return result

    def to_azure(self) -> Dict[str, Any]:
        """Convert to Azure Pipelines publish artifact task."""
        return {
            "task": "PublishBuildArtifacts@1",
            "inputs": {
                "pathToPublish": self.paths[0] if self.paths else "$(Build.ArtifactStagingDirectory)",
                "artifactName": self.name,
            },
        }

    def to_jenkins(self) -> str:
        """Convert to Jenkins archiveArtifacts step."""
        includes = ", ".join(self.paths)
        return f'archiveArtifacts artifacts: "{includes}", allowEmptyArchive: true'


@dataclass
class MatrixDimension:
    """A single dimension in a matrix build."""
    name: str
    values: List[str]


@dataclass
class MatrixConfig:
    """
    Matrix build configuration (AC-4).

    Enables running jobs across multiple configurations:
    - OS variants (ubuntu, windows, macos)
    - Language versions (python 3.9, 3.10, 3.11)
    - Node versions (16, 18, 20)
    """
    dimensions: Dict[str, List[str]] = field(default_factory=dict)
    exclude: List[Dict[str, str]] = field(default_factory=list)
    include: List[Dict[str, Any]] = field(default_factory=list)
    fail_fast: bool = True
    max_parallel: Optional[int] = None

    def to_gitlab(self) -> Dict[str, Any]:
        """Convert to GitLab CI matrix format."""
        if not self.dimensions:
            return {}

        matrix = []
        # Generate all combinations
        keys = list(self.dimensions.keys())
        if keys:
            first_key = keys[0]
            for value in self.dimensions[first_key]:
                combo = {first_key: value}
                matrix.append(combo)

        return {"parallel": {"matrix": [self.dimensions]}}

    def to_azure(self) -> Dict[str, Any]:
        """Convert to Azure Pipelines matrix format."""
        if not self.dimensions:
            return {}

        matrix: Dict[str, Dict[str, str]] = {}
        # Create matrix entries
        for key, values in self.dimensions.items():
            for value in values:
                entry_name = f"{key}_{value}".replace(".", "_")
                matrix[entry_name] = {key: str(value)}

        return {
            "strategy": {
                "matrix": matrix,
                "maxParallel": self.max_parallel or len(matrix),
            }
        }

    def to_jenkins(self) -> str:
        """Convert to Jenkins matrix axis syntax."""
        axes = []
        for key, values in self.dimensions.items():
            values_str = ", ".join([f'"{v}"' for v in values])
            axes.append(f'axis {{ name "{key}"; values {values_str} }}')

        return f"""
        matrix {{
            {chr(10).join(axes)}
            failFast {str(self.fail_fast).lower()}
        }}"""


@dataclass
class HealthCheck:
    """
    Health check configuration for deployments.

    Used to verify deployment success before completing.
    """
    endpoint: str = "/health"
    expected_status: int = 200
    timeout: str = "5m"
    interval: str = "10s"
    threshold: int = 3  # Consecutive failures before rollback
    headers: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "endpoint": self.endpoint,
            "expected_status": self.expected_status,
            "timeout": self.timeout,
            "interval": self.interval,
            "threshold": self.threshold,
            "headers": self.headers,
        }


@dataclass
class RollbackConfig:
    """
    Rollback configuration for deployments (AC-6).

    Strategies:
    - previous_version: Revert to last successful deployment
    - specific_version: Revert to a specific version
    - blue_green: Switch traffic back to stable environment
    """
    enabled: bool = True
    strategy: str = "previous_version"  # previous_version, specific_version, blue_green
    health_check: Optional[HealthCheck] = None
    max_attempts: int = 3
    cooldown: str = "30s"
    on_failure: str = "rollback"  # rollback, pause, continue
    notify: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "enabled": self.enabled,
            "strategy": self.strategy,
            "health_check": self.health_check.to_dict() if self.health_check else None,
            "max_attempts": self.max_attempts,
            "cooldown": self.cooldown,
            "on_failure": self.on_failure,
            "notify": self.notify,
        }

    def generate_rollback_script(self) -> str:
        """Generate rollback script based on strategy."""
        if self.strategy == "previous_version":
            return """
# Rollback to previous version
PREVIOUS_VERSION=$(git describe --tags --abbrev=0 HEAD^)
echo "Rolling back to ${PREVIOUS_VERSION}"
git checkout ${PREVIOUS_VERSION}
./deploy.sh
"""
        elif self.strategy == "blue_green":
            return """
# Blue-green rollback
CURRENT_ENV=$(cat /tmp/current_env)
if [ "$CURRENT_ENV" = "blue" ]; then
    NEW_ENV="green"
else
    NEW_ENV="blue"
fi
echo "Switching traffic to ${NEW_ENV}"
./switch-traffic.sh ${NEW_ENV}
"""
        return "# Manual rollback required"


@dataclass
class Environment:
    """
    Deployment environment configuration (AC-5).

    Supports environment promotion with:
    - Approval gates
    - Protection rules
    - Deployment tracking
    """
    name: str
    url: Optional[str] = None
    requires_approval: bool = False
    approvers: List[str] = field(default_factory=list)
    protection_rules: List[str] = field(default_factory=list)
    variables: Dict[str, str] = field(default_factory=dict)
    auto_stop: Optional[str] = None  # Auto-stop after duration

    def to_gitlab(self) -> Dict[str, Any]:
        """Convert to GitLab CI environment format."""
        result: Dict[str, Any] = {"name": self.name}
        if self.url:
            result["url"] = self.url
        if self.auto_stop:
            result["on_stop"] = f"stop_{self.name}"
            result["auto_stop_in"] = self.auto_stop
        return result

    def to_azure(self) -> Dict[str, Any]:
        """Convert to Azure Pipelines environment format."""
        return {
            "environment": self.name,
            "strategy": {"runOnce": {"deploy": {"steps": []}}},
        }


@dataclass
class Job:
    """A job within a pipeline stage."""
    name: str
    steps: List[Step] = field(default_factory=list)
    image: Optional[str] = None
    services: List[str] = field(default_factory=list)
    variables: Dict[str, str] = field(default_factory=dict)
    cache: Optional[CacheConfig] = None
    artifacts: Optional[ArtifactConfig] = None
    needs: List[str] = field(default_factory=list)
    rules: List[Dict[str, Any]] = field(default_factory=list)
    timeout: Optional[str] = None
    retry: int = 0
    allow_failure: bool = False
    environment: Optional[Environment] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        result: Dict[str, Any] = {
            "name": self.name,
            "steps": [s.to_dict() for s in self.steps],
        }
        if self.image:
            result["image"] = self.image
        if self.services:
            result["services"] = self.services
        if self.variables:
            result["variables"] = self.variables
        if self.cache:
            result["cache"] = self.cache.to_gitlab()
        if self.artifacts:
            result["artifacts"] = self.artifacts.to_gitlab()
        if self.needs:
            result["needs"] = self.needs
        if self.timeout:
            result["timeout"] = self.timeout
        if self.retry > 0:
            result["retry"] = self.retry
        if self.allow_failure:
            result["allow_failure"] = self.allow_failure
        if self.environment:
            result["environment"] = self.environment.to_gitlab()
        return result


@dataclass
class Stage:
    """A stage in the pipeline."""
    name: str
    jobs: List[Job] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    condition: Optional[str] = None
    environment: Optional[Environment] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "jobs": [j.to_dict() for j in self.jobs],
            "dependencies": self.dependencies,
            "condition": self.condition,
            "environment": self.environment.to_gitlab() if self.environment else None,
        }


@dataclass
class PipelineTemplate(ABC):
    """
    Base class for pipeline templates.

    Provides common functionality for all CI/CD platforms.
    """
    pipeline_type: PipelineType
    platform: Platform
    stages: List[Stage] = field(default_factory=list)
    variables: Dict[str, str] = field(default_factory=dict)
    cache: Optional[CacheConfig] = None
    artifacts: Optional[ArtifactConfig] = None
    matrix: Optional[MatrixConfig] = None
    environments: List[Environment] = field(default_factory=list)
    rollback: Optional[RollbackConfig] = None
    timeout: str = "1h"

    @abstractmethod
    def render(self) -> str:
        """Render the pipeline to platform-specific format."""
        pass

    @abstractmethod
    def validate(self) -> List[str]:
        """Validate the pipeline configuration."""
        pass

    def add_stage(self, stage: Stage) -> None:
        """Add a stage to the pipeline."""
        self.stages.append(stage)

    def add_environment(self, env: Environment) -> None:
        """Add an environment for promotion."""
        self.environments.append(env)

    def get_stage_order(self) -> List[str]:
        """Get ordered list of stage names."""
        return [s.name for s in self.stages]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "pipeline_type": self.pipeline_type.value,
            "platform": self.platform.value,
            "stages": [s.to_dict() for s in self.stages],
            "variables": self.variables,
            "cache": self.cache.to_gitlab() if self.cache else None,
            "artifacts": self.artifacts.to_gitlab() if self.artifacts else None,
            "matrix": self.matrix.to_gitlab() if self.matrix else None,
            "environments": [e.to_gitlab() for e in self.environments],
            "rollback": self.rollback.to_dict() if self.rollback else None,
        }
