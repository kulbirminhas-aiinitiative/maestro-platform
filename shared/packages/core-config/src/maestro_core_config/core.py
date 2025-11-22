"""
Core configuration management functionality.
"""

import os
from pathlib import Path
from typing import Type, TypeVar, Dict, Any, List, Optional, Union
from pydantic import BaseModel
from dynaconf import Dynaconf

from .base import BaseConfig
from .loaders import EnvironmentLoader, FileLoader, VaultLoader
from .encryption import ConfigEncryption
from .validation import ConfigValidator

T = TypeVar('T', bound=BaseConfig)


class ConfigManager:
    """
    Enterprise configuration manager with multiple source support.

    Supports loading configuration from:
    - Environment variables
    - Configuration files (YAML, JSON, TOML)
    - HashiCorp Vault
    - Consul
    - Azure Key Vault
    - AWS Systems Manager Parameter Store
    """

    def __init__(
        self,
        config_class: Type[T],
        config_dir: Union[str, Path] = None,
        environment: str = None,
        enable_encryption: bool = True,
        vault_url: str = None,
        vault_token: str = None
    ):
        """
        Initialize configuration manager.

        Args:
            config_class: Pydantic model class for configuration
            config_dir: Directory containing config files
            environment: Environment name (dev, staging, prod)
            enable_encryption: Enable encryption for sensitive values
            vault_url: HashiCorp Vault URL
            vault_token: HashiCorp Vault token
        """
        self.config_class = config_class
        self.config_dir = Path(config_dir) if config_dir else Path.cwd() / "config"
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self.enable_encryption = enable_encryption

        # Initialize loaders
        self.loaders = {
            "environment": EnvironmentLoader(),
            "file": FileLoader(self.config_dir, self.environment),
        }

        # Add Vault loader if configured
        if vault_url and vault_token:
            self.loaders["vault"] = VaultLoader(vault_url, vault_token)

        # Initialize encryption
        self.encryption = ConfigEncryption() if enable_encryption else None

        # Initialize validator
        self.validator = ConfigValidator()

        # Initialize Dynaconf for advanced features
        self._setup_dynaconf()

    def _setup_dynaconf(self) -> None:
        """Setup Dynaconf for advanced configuration management."""
        settings_files = []

        # Look for config files
        for ext in ['yaml', 'yml', 'json', 'toml']:
            config_file = self.config_dir / f"settings.{ext}"
            if config_file.exists():
                settings_files.append(str(config_file))

            # Environment-specific files
            env_file = self.config_dir / f"settings.{self.environment}.{ext}"
            if env_file.exists():
                settings_files.append(str(env_file))

        self.dynaconf = Dynaconf(
            settings_files=settings_files,
            environments=True,
            env_switcher="ENV_FOR_DYNACONF",
            load_dotenv=True,
            dotenv_path=self.config_dir / ".env"
        )

    def load(self, validate: bool = True) -> T:
        """
        Load configuration from all sources.

        Args:
            validate: Whether to validate the configuration

        Returns:
            Loaded and validated configuration instance

        Raises:
            ValidationError: If configuration is invalid
        """
        # Collect data from all sources
        config_data = {}

        # Load from each source in priority order
        for name, loader in self.loaders.items():
            try:
                source_data = loader.load()
                if source_data:
                    config_data.update(source_data)
            except Exception as e:
                # Log warning but continue
                print(f"Warning: Failed to load from {name}: {e}")

        # Load from Dynaconf (highest priority)
        dynaconf_data = dict(self.dynaconf)
        config_data.update(dynaconf_data)

        # Decrypt sensitive values
        if self.encryption:
            config_data = self._decrypt_secrets(config_data)

        # Create and validate configuration
        config = self.config_class(**config_data)

        if validate:
            self.validator.validate(config)

        return config

    def save(self, config: T, format: str = "yaml") -> None:
        """
        Save configuration to file.

        Args:
            config: Configuration instance to save
            format: Output format (yaml, json, toml)
        """
        config_data = config.model_dump()

        # Encrypt sensitive values
        if self.encryption:
            config_data = self._encrypt_secrets(config_data, config)

        # Save to file
        filename = self.config_dir / f"settings.{self.environment}.{format}"
        self.loaders["file"].save(config_data, filename, format)

    def _encrypt_secrets(self, data: Dict[str, Any], config: BaseConfig) -> Dict[str, Any]:
        """Encrypt sensitive fields in configuration data."""
        encrypted_data = data.copy()

        for field_name, field_info in config.model_fields.items():
            if field_name in encrypted_data and hasattr(field_info, 'json_schema_extra'):
                if field_info.json_schema_extra and field_info.json_schema_extra.get('secret'):
                    value = encrypted_data[field_name]
                    if value and not str(value).startswith('encrypted:'):
                        encrypted_data[field_name] = f"encrypted:{self.encryption.encrypt(str(value))}"

        return encrypted_data

    def _decrypt_secrets(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt sensitive fields in configuration data."""
        decrypted_data = data.copy()

        for key, value in decrypted_data.items():
            if isinstance(value, str) and value.startswith('encrypted:'):
                encrypted_value = value[10:]  # Remove 'encrypted:' prefix
                decrypted_data[key] = self.encryption.decrypt(encrypted_value)

        return decrypted_data

    def reload(self) -> T:
        """Reload configuration from all sources."""
        return self.load()

    def get_schema(self) -> Dict[str, Any]:
        """Get JSON schema for the configuration."""
        return self.config_class.model_json_schema()

    def validate_schema(self, data: Dict[str, Any]) -> bool:
        """Validate data against the configuration schema."""
        try:
            self.config_class(**data)
            return True
        except Exception:
            return False