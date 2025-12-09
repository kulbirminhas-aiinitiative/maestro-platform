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
- Branch Protection Rules (AC-1) - MD-2382
- Pre-commit Hook Enforcement (AC-4) - MD-2382

Reference: MD-2522 CI/CD Pipeline Templates
Reference: MD-2382 Quality Fabric & Evolutionary Templates
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

# MD-2382: Branch Protection Rules (AC-1)
from .branch_protection import (
    BranchProtectionRule,
    BranchProtectionTemplate,
    BranchProtectionManager,
    RequiredStatusCheck,
    RequiredReview,
    SignatureRequirement,
    Platform as BranchProtectionPlatform,
    MergeMethod,
)

# MD-2382: Pre-commit Hook Enforcement (AC-4)
from .precommit import (
    PreCommitConfig,
    PreCommitManager,
    PreCommitTemplate,
    HookDefinition,
    HookType,
    HookStage,
    Repository,
    EnforcementPolicy,
    ValidationResult,
    create_python_config,
    create_javascript_config,
    create_security_config,
    validate_project_config,
)

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
    # Branch Protection (MD-2382 AC-1)
    "BranchProtectionRule",
    "BranchProtectionTemplate",
    "BranchProtectionManager",
    "RequiredStatusCheck",
    "RequiredReview",
    "SignatureRequirement",
    "BranchProtectionPlatform",
    "MergeMethod",
    # Pre-commit Hooks (MD-2382 AC-4)
    "PreCommitConfig",
    "PreCommitManager",
    "PreCommitTemplate",
    "HookDefinition",
    "HookType",
    "HookStage",
    "Repository",
    "EnforcementPolicy",
    "ValidationResult",
    "create_python_config",
    "create_javascript_config",
    "create_security_config",
    "validate_project_config",
]
