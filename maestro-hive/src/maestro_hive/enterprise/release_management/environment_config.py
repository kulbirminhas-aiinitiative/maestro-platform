"""
Environment Configuration Management.

Provides environment-specific configuration management with support for
multiple tiers (Dev/Test/Pre-Prod/Prod), feature flags, and resource limits.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class EnvironmentTier(Enum):
    """Environment tier levels."""

    DEV = "dev"
    TEST = "test"
    PREPROD = "preprod"
    PROD = "prod"

    @property
    def is_production(self) -> bool:
        """Check if tier is production."""
        return self == EnvironmentTier.PROD

    @property
    def requires_approval(self) -> bool:
        """Check if tier requires approval for changes."""
        return self in (EnvironmentTier.PREPROD, EnvironmentTier.PROD)

    def can_promote_to(self, target: "EnvironmentTier") -> bool:
        """Check if this tier can promote to target."""
        order = [EnvironmentTier.DEV, EnvironmentTier.TEST,
                 EnvironmentTier.PREPROD, EnvironmentTier.PROD]
        try:
            current_idx = order.index(self)
            target_idx = order.index(target)
            return target_idx == current_idx + 1
        except ValueError:
            return False


@dataclass
class ResourceLimits:
    """Resource limits for an environment."""

    max_workers: int = 4
    max_memory_mb: int = 2048
    max_cpu_percent: float = 80.0
    request_timeout_seconds: int = 30
    max_concurrent_requests: int = 100
    max_output_size_mb: int = 10

    def validate(self) -> List[str]:
        """Validate resource limits."""
        errors = []
        if self.max_workers <= 0:
            errors.append("max_workers must be positive")
        if self.max_memory_mb <= 0:
            errors.append("max_memory_mb must be positive")
        if not 0 < self.max_cpu_percent <= 100:
            errors.append("max_cpu_percent must be between 0 and 100")
        if self.request_timeout_seconds <= 0:
            errors.append("request_timeout_seconds must be positive")
        return errors


@dataclass
class ValidationResult:
    """Result of configuration validation."""

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @classmethod
    def success(cls) -> "ValidationResult":
        """Create successful validation result."""
        return cls(valid=True)

    @classmethod
    def failure(cls, errors: List[str]) -> "ValidationResult":
        """Create failed validation result."""
        return cls(valid=False, errors=errors)


@dataclass
class ConfigDiff:
    """Difference between two environment configurations."""

    added_keys: Set[str] = field(default_factory=set)
    removed_keys: Set[str] = field(default_factory=set)
    modified_keys: Dict[str, tuple] = field(default_factory=dict)

    @property
    def has_differences(self) -> bool:
        """Check if there are any differences."""
        return bool(self.added_keys or self.removed_keys or self.modified_keys)

    def summary(self) -> str:
        """Get human-readable summary."""
        parts = []
        if self.added_keys:
            parts.append(f"Added: {len(self.added_keys)} keys")
        if self.removed_keys:
            parts.append(f"Removed: {len(self.removed_keys)} keys")
        if self.modified_keys:
            parts.append(f"Modified: {len(self.modified_keys)} keys")
        return ", ".join(parts) if parts else "No differences"


class EnvironmentConfig:
    """Environment-specific configuration management."""

    def __init__(
        self,
        name: str,
        tier: EnvironmentTier,
        config_values: Optional[Dict[str, Any]] = None,
        feature_flags: Optional[Dict[str, bool]] = None,
        resource_limits: Optional[ResourceLimits] = None,
        secrets_ref: Optional[str] = None,
    ):
        """
        Initialize environment configuration.

        Args:
            name: Environment name (e.g., 'development', 'staging')
            tier: Environment tier level
            config_values: Configuration key-value pairs
            feature_flags: Feature flag settings
            resource_limits: Resource limit configuration
            secrets_ref: Reference to secrets provider
        """
        self.name = name
        self.tier = tier
        self._config_values = config_values or {}
        self._feature_flags = feature_flags or {}
        self.resource_limits = resource_limits or ResourceLimits()
        self.secrets_ref = secrets_ref
        self._created_at = datetime.utcnow()
        self._updated_at = datetime.utcnow()

        logger.info(f"Environment config created: {name} (tier={tier.value})")

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default
        """
        return self._config_values.get(key, default)

    def set_config(self, key: str, value: Any) -> None:
        """
        Set configuration value.

        Args:
            key: Configuration key
            value: Configuration value
        """
        self._config_values[key] = value
        self._updated_at = datetime.utcnow()
        logger.debug(f"Config updated: {self.name}.{key}")

    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration values."""
        return self._config_values.copy()

    def get_feature_flag(self, flag: str, default: bool = False) -> bool:
        """
        Check if feature flag is enabled.

        Args:
            flag: Feature flag name
            default: Default value if flag not found

        Returns:
            True if flag is enabled
        """
        return self._feature_flags.get(flag, default)

    def set_feature_flag(self, flag: str, enabled: bool) -> None:
        """
        Set feature flag value.

        Args:
            flag: Feature flag name
            enabled: Whether flag is enabled
        """
        self._feature_flags[flag] = enabled
        self._updated_at = datetime.utcnow()
        logger.info(f"Feature flag updated: {self.name}.{flag}={enabled}")

    def get_all_feature_flags(self) -> Dict[str, bool]:
        """Get all feature flags."""
        return self._feature_flags.copy()

    def validate(self) -> ValidationResult:
        """
        Validate environment configuration.

        Returns:
            Validation result with any errors or warnings
        """
        errors = []
        warnings = []

        # Validate name
        if not self.name or not self.name.strip():
            errors.append("Environment name cannot be empty")

        # Validate resource limits
        limit_errors = self.resource_limits.validate()
        errors.extend(limit_errors)

        # Production-specific validations
        if self.tier.is_production:
            if self._feature_flags.get("enable_debug_endpoints", False):
                errors.append("Debug endpoints must be disabled in production")
            if self._config_values.get("debug_mode", False):
                errors.append("Debug mode must be disabled in production")

        # Warnings for non-standard configurations
        if self.tier == EnvironmentTier.DEV:
            if self.resource_limits.max_workers > 8:
                warnings.append("Dev environment has high worker count")

        if errors:
            return ValidationResult.failure(errors)

        result = ValidationResult.success()
        result.warnings = warnings
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "name": self.name,
            "tier": self.tier.value,
            "config_values": self._config_values,
            "feature_flags": self._feature_flags,
            "resource_limits": {
                "max_workers": self.resource_limits.max_workers,
                "max_memory_mb": self.resource_limits.max_memory_mb,
                "max_cpu_percent": self.resource_limits.max_cpu_percent,
                "request_timeout_seconds": self.resource_limits.request_timeout_seconds,
                "max_concurrent_requests": self.resource_limits.max_concurrent_requests,
            },
            "secrets_ref": self.secrets_ref,
            "created_at": self._created_at.isoformat(),
            "updated_at": self._updated_at.isoformat(),
        }


class EnvironmentManager:
    """Manages multiple environment configurations."""

    def __init__(self):
        """Initialize environment manager."""
        self._environments: Dict[str, EnvironmentConfig] = {}
        logger.info("EnvironmentManager initialized")

    def create_environment(
        self,
        name: str,
        tier: EnvironmentTier,
        config: Optional[Dict[str, Any]] = None,
        feature_flags: Optional[Dict[str, bool]] = None,
        resource_limits: Optional[ResourceLimits] = None,
    ) -> EnvironmentConfig:
        """
        Create new environment configuration.

        Args:
            name: Environment name
            tier: Environment tier
            config: Initial configuration values
            feature_flags: Initial feature flags
            resource_limits: Resource limits

        Returns:
            Created environment configuration

        Raises:
            ValueError: If environment already exists
        """
        if name in self._environments:
            raise ValueError(f"Environment '{name}' already exists")

        env_config = EnvironmentConfig(
            name=name,
            tier=tier,
            config_values=config,
            feature_flags=feature_flags,
            resource_limits=resource_limits,
        )

        self._environments[name] = env_config
        logger.info(f"Environment created: {name}")
        return env_config

    def get_environment(self, name: str) -> Optional[EnvironmentConfig]:
        """
        Get environment by name.

        Args:
            name: Environment name

        Returns:
            Environment configuration or None if not found
        """
        return self._environments.get(name)

    def list_environments(self) -> List[EnvironmentConfig]:
        """
        List all configured environments.

        Returns:
            List of environment configurations
        """
        return list(self._environments.values())

    def delete_environment(self, name: str) -> bool:
        """
        Delete environment configuration.

        Args:
            name: Environment name

        Returns:
            True if deleted, False if not found
        """
        if name in self._environments:
            del self._environments[name]
            logger.info(f"Environment deleted: {name}")
            return True
        return False

    def compare_environments(self, env1_name: str, env2_name: str) -> ConfigDiff:
        """
        Compare configuration between two environments.

        Args:
            env1_name: First environment name
            env2_name: Second environment name

        Returns:
            Configuration differences

        Raises:
            ValueError: If either environment not found
        """
        env1 = self._environments.get(env1_name)
        env2 = self._environments.get(env2_name)

        if not env1:
            raise ValueError(f"Environment '{env1_name}' not found")
        if not env2:
            raise ValueError(f"Environment '{env2_name}' not found")

        config1 = env1.get_all_config()
        config2 = env2.get_all_config()

        keys1 = set(config1.keys())
        keys2 = set(config2.keys())

        diff = ConfigDiff(
            added_keys=keys2 - keys1,
            removed_keys=keys1 - keys2,
        )

        # Find modified keys
        common_keys = keys1 & keys2
        for key in common_keys:
            if config1[key] != config2[key]:
                diff.modified_keys[key] = (config1[key], config2[key])

        return diff

    def get_by_tier(self, tier: EnvironmentTier) -> List[EnvironmentConfig]:
        """
        Get all environments of a specific tier.

        Args:
            tier: Environment tier

        Returns:
            List of environments matching the tier
        """
        return [env for env in self._environments.values() if env.tier == tier]

    def validate_all(self) -> Dict[str, ValidationResult]:
        """
        Validate all environments.

        Returns:
            Dictionary mapping environment names to validation results
        """
        results = {}
        for name, env in self._environments.items():
            results[name] = env.validate()
        return results
