"""
Environment Configuration Management.

Handles environment-specific configuration with multiple sources.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional
import os


class ConfigSource(str, Enum):
    """Configuration source types."""
    DEFAULT = "default"
    ENVIRONMENT = "environment"
    FILE = "file"
    VAULT = "vault"
    AWS_SECRETS = "aws_secrets"


@dataclass
class ConfigValue:
    """Configuration value with metadata."""
    key: str
    value: Any
    source: ConfigSource
    encrypted: bool = False
    sensitive: bool = False
    version: int = 1

    def get_display_value(self) -> str:
        """Get display-safe value."""
        if self.sensitive:
            return "********"
        return str(self.value)


class EnvironmentConfig:
    """Environment-specific configuration."""

    def __init__(self, name: str):
        self.name = name
        self._values: dict[str, ConfigValue] = {}
        self._overrides: dict[str, str] = {}

    def set(self, key: str, value: Any, source: ConfigSource = ConfigSource.DEFAULT,
            sensitive: bool = False) -> None:
        """Set configuration value."""
        self._values[key] = ConfigValue(
            key=key,
            value=value,
            source=source,
            sensitive=sensitive
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        # Check overrides first
        if key in self._overrides:
            return self._overrides[key]

        # Check stored values
        config_value = self._values.get(key)
        if config_value:
            return config_value.value

        # Check environment variables
        env_value = os.environ.get(f"{self.name.upper()}_{key}")
        if env_value:
            return env_value

        return default

    def get_all(self) -> dict[str, Any]:
        """Get all configuration values."""
        result = {}
        for key, config_value in self._values.items():
            result[key] = config_value.get_display_value()
        return result

    def override(self, key: str, value: str) -> None:
        """Override configuration value temporarily."""
        self._overrides[key] = value

    def clear_overrides(self) -> None:
        """Clear all overrides."""
        self._overrides.clear()

    def merge(self, other: "EnvironmentConfig") -> None:
        """Merge another config into this one."""
        for key, value in other._values.items():
            if key not in self._values:
                self._values[key] = value

    def validate(self, required_keys: list[str]) -> list[str]:
        """Validate required configuration keys exist."""
        missing = []
        for key in required_keys:
            if self.get(key) is None:
                missing.append(key)
        return missing

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "values": {k: v.get_display_value() for k, v in self._values.items()},
            "overrides_count": len(self._overrides)
        }

    def to_env_vars(self) -> dict[str, str]:
        """Convert to environment variable format."""
        result = {}
        for key, config_value in self._values.items():
            if not config_value.sensitive:
                result[key] = str(config_value.value)
        return result


class ConfigLoader:
    """Loads configuration from various sources."""

    def __init__(self):
        self._sources: list[ConfigSource] = []

    def add_source(self, source: ConfigSource) -> None:
        """Add configuration source."""
        self._sources.append(source)

    async def load(self, environment: str) -> EnvironmentConfig:
        """Load configuration for environment."""
        config = EnvironmentConfig(environment)

        for source in self._sources:
            if source == ConfigSource.ENVIRONMENT:
                self._load_from_env(config, environment)
            elif source == ConfigSource.FILE:
                await self._load_from_file(config, environment)

        return config

    def _load_from_env(self, config: EnvironmentConfig, environment: str) -> None:
        """Load from environment variables."""
        prefix = f"{environment.upper()}_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):]
                config.set(config_key, value, ConfigSource.ENVIRONMENT)

    async def _load_from_file(self, config: EnvironmentConfig, environment: str) -> None:
        """Load from configuration file."""
        pass


@dataclass
class ConfigDiff:
    """Difference between two configurations."""
    added: dict[str, Any] = field(default_factory=dict)
    removed: dict[str, Any] = field(default_factory=dict)
    modified: dict[str, tuple[Any, Any]] = field(default_factory=dict)

    @classmethod
    def compare(cls, old: EnvironmentConfig, new: EnvironmentConfig) -> "ConfigDiff":
        """Compare two configurations."""
        diff = cls()
        old_keys = set(old._values.keys())
        new_keys = set(new._values.keys())

        for key in new_keys - old_keys:
            diff.added[key] = new.get(key)

        for key in old_keys - new_keys:
            diff.removed[key] = old.get(key)

        for key in old_keys & new_keys:
            old_val = old.get(key)
            new_val = new.get(key)
            if old_val != new_val:
                diff.modified[key] = (old_val, new_val)

        return diff

    def has_changes(self) -> bool:
        """Check if there are any changes."""
        return bool(self.added or self.removed or self.modified)
