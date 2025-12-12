"""
Release Management Module for Maestro Platform.

This module provides environment strategy, branching management, and CI/CD pipeline
configuration capabilities for the Maestro platform.

Components:
- EnvironmentManager: Manages Dev/Test/Pre-Prod environments
- BranchManager: Manages branching strategy (stable-demo, working-beta)
- PipelineManager: Configures CI/CD pipelines per environment
- PromotionService: Handles deployment promotions between environments
"""

from .models import (
    Environment,
    EnvironmentConfig,
    EnvironmentTier,
    EnvironmentStatus,
    Branch,
    BranchType,
    ProtectionRules,
    MergeStrategy,
    MergeResult,
    Pipeline,
    PipelineStage,
    PipelineStatus,
    PipelineRun,
    DeploymentGate,
    GateType,
    PromotionResult,
    RollbackResult,
)

from .environments import EnvironmentManager
from .branching import BranchManager
from .pipelines import PipelineManager
from .promotion import PromotionService
from .config import ReleaseManagementConfig

__all__ = [
    # Models
    "Environment",
    "EnvironmentConfig",
    "EnvironmentTier",
    "EnvironmentStatus",
    "Branch",
    "BranchType",
    "ProtectionRules",
    "MergeStrategy",
    "MergeResult",
    "Pipeline",
    "PipelineStage",
    "PipelineStatus",
    "PipelineRun",
    "DeploymentGate",
    "GateType",
    "PromotionResult",
    "RollbackResult",
    # Services
    "EnvironmentManager",
    "BranchManager",
    "PipelineManager",
    "PromotionService",
    "ReleaseManagementConfig",
]

__version__ = "1.0.0"
