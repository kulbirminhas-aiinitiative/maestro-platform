"""
CI/CD Pipeline Templates

Comprehensive pipeline templates for multiple CI/CD platforms:
- GitLab CI (.gitlab-ci.yml)
- Azure Pipelines (azure-pipelines.yml)
- Jenkins (Jenkinsfile)

Features:
- Artifact management (AC-2)
- Caching strategies (AC-3)
- Matrix builds (AC-4)
- Environment promotion (AC-5)
- Rollback capability (AC-6)

Reference: MD-2522 CI/CD Pipeline Templates
"""

from .models import (
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
    PipelineTemplate,
)
from .gitlab import GitLabPipeline, GitLabAdapter
from .azure import AzurePipeline, AzureAdapter
from .jenkins import JenkinsPipeline, JenkinsAdapter
from .registry import PipelineRegistry, get_pipeline_registry

__all__ = [
    # Models
    "PipelineType",
    "Platform",
    "Stage",
    "Job",
    "Step",
    "CacheConfig",
    "ArtifactConfig",
    "MatrixConfig",
    "Environment",
    "RollbackConfig",
    "HealthCheck",
    "PipelineTemplate",
    # GitLab
    "GitLabPipeline",
    "GitLabAdapter",
    # Azure
    "AzurePipeline",
    "AzureAdapter",
    # Jenkins
    "JenkinsPipeline",
    "JenkinsAdapter",
    # Registry
    "PipelineRegistry",
    "get_pipeline_registry",
]
