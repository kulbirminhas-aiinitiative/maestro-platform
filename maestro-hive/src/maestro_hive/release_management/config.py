"""
Configuration for Release Management.

This module provides configuration loading and validation for the
release management module.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging
import os
import yaml

logger = logging.getLogger(__name__)


@dataclass
class EnvironmentDefaults:
    """Default configuration for environments."""
    cpu: str = "1000m"
    memory: str = "1Gi"
    replicas: int = 1
    auto_deploy: bool = False
    data_source: str = "synthetic"


@dataclass
class BranchDefaults:
    """Default configuration for branches."""
    require_reviews: int = 1
    require_ci: bool = True
    require_signed: bool = False
    prevent_force_push: bool = True


@dataclass
class PipelineDefaults:
    """Default configuration for pipelines."""
    default_timeout_minutes: int = 30
    max_concurrent_runs: int = 5
    artifact_retention_days: int = 30


@dataclass
class ReleaseManagementConfig:
    """
    Main configuration class for Release Management.

    Provides configuration loading from files or environment variables
    and validation of configuration values.
    """

    # Environment configuration
    environment_defaults: EnvironmentDefaults = field(
        default_factory=EnvironmentDefaults
    )
    environments: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Branch configuration
    branch_defaults: BranchDefaults = field(default_factory=BranchDefaults)
    branches: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # Pipeline configuration
    pipeline_defaults: PipelineDefaults = field(default_factory=PipelineDefaults)
    pipelines: Dict[str, Dict[str, Any]] = field(default_factory=dict)

    # General settings
    enable_auto_promotion: bool = False
    git_default_branch: str = "main"
    notification_channels: List[str] = field(default_factory=list)

    @classmethod
    def from_file(cls, path: str) -> "ReleaseManagementConfig":
        """
        Load configuration from a YAML file.

        Args:
            path: Path to YAML configuration file

        Returns:
            ReleaseManagementConfig instance

        Raises:
            FileNotFoundError: If configuration file not found
            ValueError: If configuration is invalid
        """
        file_path = Path(path)
        if not file_path.exists():
            logger.error(f"Configuration file not found: {path}")
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(file_path, "r") as f:
            data = yaml.safe_load(f) or {}

        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReleaseManagementConfig":
        """
        Create configuration from a dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            ReleaseManagementConfig instance
        """
        config = cls()

        # Load environment defaults
        if "environment_defaults" in data:
            env_defaults = data["environment_defaults"]
            config.environment_defaults = EnvironmentDefaults(
                cpu=env_defaults.get("cpu", "1000m"),
                memory=env_defaults.get("memory", "1Gi"),
                replicas=env_defaults.get("replicas", 1),
                auto_deploy=env_defaults.get("auto_deploy", False),
                data_source=env_defaults.get("data_source", "synthetic"),
            )

        # Load environments
        if "environments" in data:
            config.environments = data["environments"]

        # Load branch defaults
        if "branch_defaults" in data:
            branch_defaults = data["branch_defaults"]
            config.branch_defaults = BranchDefaults(
                require_reviews=branch_defaults.get("require_reviews", 1),
                require_ci=branch_defaults.get("require_ci", True),
                require_signed=branch_defaults.get("require_signed", False),
                prevent_force_push=branch_defaults.get("prevent_force_push", True),
            )

        # Load branches
        if "branches" in data:
            config.branches = data["branches"]

        # Load pipeline defaults
        if "pipeline_defaults" in data:
            pipeline_defaults = data["pipeline_defaults"]
            config.pipeline_defaults = PipelineDefaults(
                default_timeout_minutes=pipeline_defaults.get(
                    "default_timeout_minutes", 30
                ),
                max_concurrent_runs=pipeline_defaults.get("max_concurrent_runs", 5),
                artifact_retention_days=pipeline_defaults.get(
                    "artifact_retention_days", 30
                ),
            )

        # Load pipelines
        if "pipelines" in data:
            config.pipelines = data["pipelines"]

        # Load general settings
        config.enable_auto_promotion = data.get("enable_auto_promotion", False)
        config.git_default_branch = data.get("git_default_branch", "main")
        config.notification_channels = data.get("notification_channels", [])

        logger.info("Configuration loaded successfully")
        return config

    @classmethod
    def from_env(cls) -> "ReleaseManagementConfig":
        """
        Load configuration from environment variables.

        Returns:
            ReleaseManagementConfig instance
        """
        config = cls()

        # Check for config file path in env
        config_path = os.environ.get("RELEASE_MGMT_CONFIG_PATH")
        if config_path and Path(config_path).exists():
            return cls.from_file(config_path)

        # Load individual settings from env
        config.enable_auto_promotion = (
            os.environ.get("ENABLE_AUTO_PROMOTION", "false").lower() == "true"
        )
        config.git_default_branch = os.environ.get("GIT_DEFAULT_BRANCH", "main")

        # Environment tier from env
        env_tier = os.environ.get("ENVIRONMENT_TIER", "development")
        if env_tier:
            config.environments["current"] = {"tier": env_tier}

        logger.info("Configuration loaded from environment variables")
        return config

    def validate(self) -> bool:
        """
        Validate the configuration.

        Returns:
            True if valid, raises ValueError if invalid
        """
        errors = []

        # Validate environment defaults
        if self.environment_defaults.replicas < 1:
            errors.append("Environment replicas must be at least 1")

        # Validate branch defaults
        if self.branch_defaults.require_reviews < 0:
            errors.append("Required reviews cannot be negative")

        # Validate pipeline defaults
        if self.pipeline_defaults.default_timeout_minutes < 1:
            errors.append("Pipeline timeout must be at least 1 minute")

        if self.pipeline_defaults.max_concurrent_runs < 1:
            errors.append("Max concurrent runs must be at least 1")

        # Validate environment configurations
        valid_tiers = ["development", "test", "pre_prod", "production"]
        for env_name, env_config in self.environments.items():
            if "tier" in env_config:
                if env_config["tier"] not in valid_tiers:
                    errors.append(
                        f"Invalid tier '{env_config['tier']}' for environment '{env_name}'"
                    )

        if errors:
            error_msg = "Configuration validation failed: " + "; ".join(errors)
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info("Configuration validation passed")
        return True

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        Returns:
            Dictionary representation of configuration
        """
        return {
            "environment_defaults": {
                "cpu": self.environment_defaults.cpu,
                "memory": self.environment_defaults.memory,
                "replicas": self.environment_defaults.replicas,
                "auto_deploy": self.environment_defaults.auto_deploy,
                "data_source": self.environment_defaults.data_source,
            },
            "environments": self.environments,
            "branch_defaults": {
                "require_reviews": self.branch_defaults.require_reviews,
                "require_ci": self.branch_defaults.require_ci,
                "require_signed": self.branch_defaults.require_signed,
                "prevent_force_push": self.branch_defaults.prevent_force_push,
            },
            "branches": self.branches,
            "pipeline_defaults": {
                "default_timeout_minutes": self.pipeline_defaults.default_timeout_minutes,
                "max_concurrent_runs": self.pipeline_defaults.max_concurrent_runs,
                "artifact_retention_days": self.pipeline_defaults.artifact_retention_days,
            },
            "pipelines": self.pipelines,
            "enable_auto_promotion": self.enable_auto_promotion,
            "git_default_branch": self.git_default_branch,
            "notification_channels": self.notification_channels,
        }

    def save(self, path: str) -> None:
        """
        Save configuration to a YAML file.

        Args:
            path: Path to save configuration
        """
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f, default_flow_style=False)
        logger.info(f"Configuration saved to {path}")

    def get_environment_config(self, name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific environment.

        Args:
            name: Environment name

        Returns:
            Environment configuration dictionary
        """
        env_config = self.environments.get(name, {})

        # Merge with defaults
        return {
            "cpu": env_config.get("cpu", self.environment_defaults.cpu),
            "memory": env_config.get("memory", self.environment_defaults.memory),
            "replicas": env_config.get("replicas", self.environment_defaults.replicas),
            "auto_deploy": env_config.get(
                "auto_deploy", self.environment_defaults.auto_deploy
            ),
            "data_source": env_config.get(
                "data_source", self.environment_defaults.data_source
            ),
            **{k: v for k, v in env_config.items() if k not in [
                "cpu", "memory", "replicas", "auto_deploy", "data_source"
            ]},
        }

    def get_branch_config(self, name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific branch.

        Args:
            name: Branch name

        Returns:
            Branch configuration dictionary
        """
        branch_config = self.branches.get(name, {})

        # Merge with defaults
        return {
            "require_reviews": branch_config.get(
                "require_reviews", self.branch_defaults.require_reviews
            ),
            "require_ci": branch_config.get(
                "require_ci", self.branch_defaults.require_ci
            ),
            "require_signed": branch_config.get(
                "require_signed", self.branch_defaults.require_signed
            ),
            "prevent_force_push": branch_config.get(
                "prevent_force_push", self.branch_defaults.prevent_force_push
            ),
            **{k: v for k, v in branch_config.items() if k not in [
                "require_reviews", "require_ci", "require_signed", "prevent_force_push"
            ]},
        }
