"""
Configuration loaders for various sources.

Provides loaders for environment variables, files, Vault, Consul, etc.
"""

import json
import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from maestro_core_logging import get_logger

def _get_logger():
    try:
        from maestro_core_logging import get_logger
        return get_logger(__name__)
    except:
        import logging
        return logging.getLogger(__name__)

logger = type("LazyLogger", (), {"__getattr__": lambda self, name: getattr(_get_logger(), name)})()


class ConfigLoader:
    """Base class for configuration loaders."""

    def load(self) -> Dict[str, Any]:
        """
        Load configuration from source.

        Returns:
            Configuration dictionary

        Raises:
            NotImplementedError: Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement load()")


class EnvironmentLoader(ConfigLoader):
    """
    Load configuration from environment variables.

    Example:
        >>> loader = EnvironmentLoader(prefix="MAESTRO_")
        >>> config = loader.load()
        >>> # Returns all MAESTRO_* environment variables
    """

    def __init__(self, prefix: str = "MAESTRO_", lowercase_keys: bool = True):
        """
        Initialize environment loader.

        Args:
            prefix: Environment variable prefix to filter by
            lowercase_keys: Convert keys to lowercase
        """
        self.prefix = prefix
        self.lowercase_keys = lowercase_keys

    def load(self) -> Dict[str, Any]:
        """
        Load configuration from environment variables.

        Returns:
            Dictionary of environment variables with prefix removed
        """
        config = {}

        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                # Remove prefix
                config_key = key[len(self.prefix):]

                # Convert to lowercase if requested
                if self.lowercase_keys:
                    config_key = config_key.lower()

                # Try to parse JSON values
                try:
                    config[config_key] = json.loads(value)
                except (json.JSONDecodeError, ValueError):
                    config[config_key] = value

        logger.debug(f"Loaded {len(config)} values from environment", prefix=self.prefix)
        return config


class FileLoader(ConfigLoader):
    """
    Load configuration from JSON or YAML files.

    Supports:
        - JSON (.json)
        - YAML (.yaml, .yml)
        - Multiple file merging

    Example:
        >>> loader = FileLoader("config.yaml")
        >>> config = loader.load()
    """

    def __init__(self, file_path: str, required: bool = True):
        """
        Initialize file loader.

        Args:
            file_path: Path to configuration file
            required: Whether file must exist
        """
        self.file_path = Path(file_path)
        self.required = required

    def load(self) -> Dict[str, Any]:
        """
        Load configuration from file.

        Returns:
            Configuration dictionary

        Raises:
            FileNotFoundError: If file doesn't exist and required=True
            ValueError: If file format is unsupported
        """
        if not self.file_path.exists():
            if self.required:
                raise FileNotFoundError(f"Configuration file not found: {self.file_path}")
            logger.warning(f"Optional configuration file not found: {self.file_path}")
            return {}

        # Determine file format from extension
        suffix = self.file_path.suffix.lower()

        if suffix == ".json":
            return self._load_json()
        elif suffix in (".yaml", ".yml"):
            return self._load_yaml()
        else:
            raise ValueError(f"Unsupported configuration file format: {suffix}")

    def _load_json(self) -> Dict[str, Any]:
        """Load JSON configuration file."""
        try:
            with open(self.file_path, 'r') as f:
                config = json.load(f)
            logger.info(f"Loaded configuration from JSON", file=str(self.file_path))
            return config
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON configuration", file=str(self.file_path), error=str(e))
            raise ValueError(f"Invalid JSON in {self.file_path}: {e}")

    def _load_yaml(self) -> Dict[str, Any]:
        """Load YAML configuration file."""
        try:
            with open(self.file_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Loaded configuration from YAML", file=str(self.file_path))
            return config or {}
        except yaml.YAMLError as e:
            logger.error(f"Failed to parse YAML configuration", file=str(self.file_path), error=str(e))
            raise ValueError(f"Invalid YAML in {self.file_path}: {e}")


class MultiFileLoader(ConfigLoader):
    """
    Load and merge configuration from multiple files.

    Files are loaded in order and merged, with later files overriding earlier ones.

    Example:
        >>> loader = MultiFileLoader([
        ...     "config/base.yaml",
        ...     "config/production.yaml"
        ... ])
        >>> config = loader.load()
    """

    def __init__(self, file_paths: list[str], required: Optional[list[bool]] = None):
        """
        Initialize multi-file loader.

        Args:
            file_paths: List of configuration file paths
            required: List of booleans indicating if each file is required
        """
        self.file_paths = file_paths
        self.required = required or [True] * len(file_paths)

    def load(self) -> Dict[str, Any]:
        """
        Load and merge configuration from multiple files.

        Returns:
            Merged configuration dictionary
        """
        merged_config = {}

        for file_path, required in zip(self.file_paths, self.required):
            loader = FileLoader(file_path, required=required)
            file_config = loader.load()

            # Deep merge configurations
            merged_config = self._deep_merge(merged_config, file_config)

        logger.info(f"Loaded and merged {len(self.file_paths)} configuration files")
        return merged_config

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """
        Deep merge two dictionaries.

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result


class VaultLoader(ConfigLoader):
    """
    Load configuration from HashiCorp Vault.

    Placeholder implementation - requires hvac library for production use.

    Example:
        >>> loader = VaultLoader(
        ...     url="https://vault.example.com",
        ...     token="s.1234567890",
        ...     path="secret/maestro/config"
        ... )
        >>> config = loader.load()
    """

    def __init__(self, url: str, token: str, path: str, mount_point: str = "secret"):
        """
        Initialize Vault loader.

        Args:
            url: Vault server URL
            token: Vault authentication token
            path: Path to secret in Vault
            mount_point: Vault mount point (default: "secret")
        """
        self.url = url
        self.token = token
        self.path = path
        self.mount_point = mount_point

    def load(self) -> Dict[str, Any]:
        """
        Load configuration from Vault.

        Returns:
            Configuration dictionary

        Note:
            This is a placeholder implementation.
            For production, install hvac: pip install hvac
        """
        logger.warning(
            "VaultLoader is a placeholder - install hvac for production use",
            url=self.url,
            path=self.path
        )

        # Placeholder - in production, use hvac client
        # import hvac
        # client = hvac.Client(url=self.url, token=self.token)
        # response = client.secrets.kv.v2.read_secret_version(
        #     path=self.path,
        #     mount_point=self.mount_point
        # )
        # return response['data']['data']

        return {}


class ConsulLoader(ConfigLoader):
    """
    Load configuration from HashiCorp Consul.

    Placeholder implementation - requires python-consul library for production use.

    Example:
        >>> loader = ConsulLoader(
        ...     host="consul.example.com",
        ...     prefix="maestro/config"
        ... )
        >>> config = loader.load()
    """

    def __init__(self, host: str = "localhost", port: int = 8500, prefix: str = "maestro"):
        """
        Initialize Consul loader.

        Args:
            host: Consul host
            port: Consul port
            prefix: Key prefix in Consul
        """
        self.host = host
        self.port = port
        self.prefix = prefix

    def load(self) -> Dict[str, Any]:
        """
        Load configuration from Consul KV store.

        Returns:
            Configuration dictionary

        Note:
            This is a placeholder implementation.
            For production, install python-consul: pip install python-consul
        """
        logger.warning(
            "ConsulLoader is a placeholder - install python-consul for production use",
            host=self.host,
            port=self.port,
            prefix=self.prefix
        )

        # Placeholder - in production, use python-consul
        # import consul
        # c = consul.Consul(host=self.host, port=self.port)
        # index, data = c.kv.get(self.prefix, recurse=True)
        # config = {}
        # for item in data or []:
        #     key = item['Key'].replace(f"{self.prefix}/", "")
        #     config[key] = item['Value'].decode('utf-8')
        # return config

        return {}


class LayeredConfigLoader(ConfigLoader):
    """
    Load configuration from multiple sources with precedence.

    Loads configuration from multiple loaders in order, with later
    loaders overriding earlier ones.

    Example:
        >>> loader = LayeredConfigLoader([
        ...     FileLoader("config/defaults.yaml"),
        ...     FileLoader("config/production.yaml", required=False),
        ...     EnvironmentLoader(prefix="MAESTRO_")
        ... ])
        >>> config = loader.load()
        >>> # Environment variables override file config
    """

    def __init__(self, loaders: list[ConfigLoader]):
        """
        Initialize layered loader.

        Args:
            loaders: List of config loaders in precedence order
        """
        self.loaders = loaders

    def load(self) -> Dict[str, Any]:
        """
        Load configuration from all loaders and merge.

        Returns:
            Merged configuration dictionary
        """
        merged_config = {}

        for loader in self.loaders:
            try:
                layer_config = loader.load()
                merged_config = self._deep_merge(merged_config, layer_config)
                logger.debug(f"Merged configuration layer", loader=loader.__class__.__name__)
            except Exception as e:
                logger.error(f"Failed to load configuration layer", loader=loader.__class__.__name__, error=str(e))
                raise

        logger.info(f"Loaded configuration from {len(self.loaders)} layers")
        return merged_config

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result


# Export all
__all__ = [
    "ConfigLoader",
    "EnvironmentLoader",
    "FileLoader",
    "MultiFileLoader",
    "VaultLoader",
    "ConsulLoader",
    "LayeredConfigLoader",
]
