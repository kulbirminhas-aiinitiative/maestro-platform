"""Environment Management Module - AC-2 Implementation."""

from .manager import (
    EnvironmentManager,
    Environment,
    EnvironmentStatus,
    PromotionResult,
)
from .config import EnvironmentConfig, ConfigSource
from .promotion import PromotionPolicy, ApprovalRequirement
from .secrets import SecretManager, Secret, SecretRotation

__all__ = [
    "EnvironmentManager",
    "Environment",
    "EnvironmentStatus",
    "PromotionResult",
    "EnvironmentConfig",
    "ConfigSource",
    "PromotionPolicy",
    "ApprovalRequirement",
    "SecretManager",
    "Secret",
    "SecretRotation",
]
