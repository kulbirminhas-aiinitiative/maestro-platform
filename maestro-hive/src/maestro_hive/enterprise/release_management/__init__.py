"""
Release Management Module for Maestro Platform.

This module provides environment strategy, branching management,
release workflows, and promotion gates for enterprise deployments.

Components:
- EnvironmentConfig: Environment-specific configuration management
- EnvironmentManager: Multi-environment configuration orchestration
- BranchStrategy: Git branching strategy implementation
- ReleaseManager: Release workflow and versioning
- PromotionGates: Environment promotion and approval workflows
"""

from .environment_config import (
    EnvironmentTier,
    ResourceLimits,
    EnvironmentConfig,
    EnvironmentManager,
    ConfigDiff,
    ValidationResult,
)

from .branch_strategy import (
    ProtectionLevel,
    StrategyType,
    BranchRule,
    BranchStrategy,
    BranchValidationResult,
)

from .release_manager import (
    ReleaseType,
    BumpType,
    ReleaseStatus,
    Release,
    ReleaseManager,
    RollbackResult,
)

from .promotion_gates import (
    ApprovalStatus,
    GateStatus,
    QualityGate,
    ApprovalRequest,
    PromotionRecord,
    ReadinessResult,
    PromotionResult,
    PromotionGates,
)

__all__ = [
    # Environment Config
    "EnvironmentTier",
    "ResourceLimits",
    "EnvironmentConfig",
    "EnvironmentManager",
    "ConfigDiff",
    "ValidationResult",
    # Branch Strategy
    "ProtectionLevel",
    "StrategyType",
    "BranchRule",
    "BranchStrategy",
    "BranchValidationResult",
    # Release Manager
    "ReleaseType",
    "BumpType",
    "ReleaseStatus",
    "Release",
    "ReleaseManager",
    "RollbackResult",
    # Promotion Gates
    "ApprovalStatus",
    "GateStatus",
    "QualityGate",
    "ApprovalRequest",
    "PromotionRecord",
    "ReadinessResult",
    "PromotionResult",
    "PromotionGates",
]
