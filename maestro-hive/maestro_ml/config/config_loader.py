"""
Maestro ML Platform - Configuration Loader
Purpose: Load and validate platform configuration from centralized YAML files
Usage: from config.config_loader import load_config, get_config_value
"""

import os
import yaml
from typing import Any, Dict, Optional
from pathlib import Path


class ConfigLoader:
    """Centralized configuration loader for Maestro ML Platform"""

    def __init__(self, config_file: Optional[str] = None, env: Optional[str] = None):
        """
        Initialize configuration loader

        Args:
            config_file: Path to config file (default: platform-config.yaml)
            env: Environment name (dev/staging/prod) for environment-specific overrides
        """
        self.config_file = config_file or os.getenv(
            "ML_PLATFORM_CONFIG",
            str(Path(__file__).parent / "platform-config.yaml")
        )
        self.env = env or os.getenv("ML_PLATFORM_ENV", "dev")
        self.config = self._load_config()
        self._apply_env_overrides()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_file, 'r') as f:
                config = yaml.safe_load(f)
            print(f"✅ Loaded configuration from {self.config_file}")
            return config
        except FileNotFoundError:
            print(f"⚠️  Config file not found: {self.config_file}")
            print("   Using environment variables only")
            return {}
        except Exception as e:
            print(f"❌ Error loading config: {e}")
            return {}

    def _apply_env_overrides(self):
        """Apply environment-specific configuration overrides"""
        env_config_file = str(Path(self.config_file).parent / f"platform-config-{self.env}.yaml")
        if os.path.exists(env_config_file):
            try:
                with open(env_config_file, 'r') as f:
                    env_config = yaml.safe_load(f)
                self._deep_merge(self.config, env_config)
                print(f"✅ Applied {self.env} environment overrides from {env_config_file}")
            except Exception as e:
                print(f"⚠️  Could not load environment overrides: {e}")

    def _deep_merge(self, base: Dict, override: Dict):
        """Deep merge override config into base config"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def _resolve_env_var(self, value: str) -> str:
        """Resolve environment variable placeholders like ${VAR_NAME:-default}"""
        if not isinstance(value, str):
            return value

        # Pattern: ${VAR_NAME:-default_value}
        if value.startswith("${") and value.endswith("}"):
            var_spec = value[2:-1]  # Remove ${ and }

            if ":-" in var_spec:
                var_name, default_value = var_spec.split(":-", 1)
            else:
                var_name = var_spec
                default_value = None

            return os.getenv(var_name, default_value)

        return value

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated key path

        Args:
            key_path: Dot-separated path (e.g., 'mlflow.tracking_uri')
            default: Default value if key not found

        Returns:
            Configuration value with environment variables resolved

        Examples:
            >>> config = ConfigLoader()
            >>> config.get('mlflow.tracking_uri')
            'http://mlflow-tracking:5000'
            >>> config.get('governance.approval.min_accuracy')
            0.85
        """
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        # Resolve environment variable if present
        return self._resolve_env_var(value)

    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section

        Args:
            section: Top-level section name (e.g., 'mlflow', 'kubernetes')

        Returns:
            Dictionary of section configuration
        """
        return self.config.get(section, {})

    def validate(self) -> bool:
        """
        Validate required configuration values are present

        Returns:
            True if all required configs are valid
        """
        required_configs = [
            'mlflow.tracking_uri',
            'database.host',
            'kubernetes.namespace.platform',
            'monitoring.prometheus.url',
        ]

        missing = []
        for config_key in required_configs:
            value = self.get(config_key)
            if value is None:
                missing.append(config_key)

        if missing:
            print(f"❌ Missing required configuration:")
            for key in missing:
                print(f"   - {key}")
            return False

        print("✅ All required configuration values present")
        return True

    def get_mlflow_config(self) -> Dict[str, str]:
        """Get MLflow-specific configuration"""
        return {
            'tracking_uri': self.get('mlflow.tracking_uri'),
            'registry_uri': self.get('mlflow.registry_uri'),
            'artifact_location': self.get('mlflow.artifact_location'),
        }

    def get_database_config(self) -> Dict[str, Any]:
        """Get database configuration"""
        password = os.getenv('DB_PASSWORD')
        if not password:
            print("⚠️  DB_PASSWORD not set in environment")

        return {
            'host': self.get('database.host'),
            'port': self.get('database.port'),
            'database': self.get('database.name'),
            'user': self.get('database.user'),
            'password': password,
        }

    def get_resource_limits(self, component: str, framework: Optional[str] = None) -> Dict[str, str]:
        """
        Get resource limits for a component

        Args:
            component: 'training', 'serving', or 'monitoring'
            framework: For training, specify 'tensorflow', 'pytorch', etc.

        Returns:
            Dictionary with cpu/memory request and limits
        """
        if component == 'training' and framework:
            return {
                'cpu_request': self.get(f'resources.training.{framework}.cpu_request'),
                'cpu_limit': self.get(f'resources.training.{framework}.cpu_limit'),
                'memory_request': self.get(f'resources.training.{framework}.memory_request'),
                'memory_limit': self.get(f'resources.training.{framework}.memory_limit'),
            }
        else:
            return {
                'cpu_request': self.get(f'resources.{component}.cpu_request'),
                'cpu_limit': self.get(f'resources.{component}.cpu_limit'),
                'memory_request': self.get(f'resources.{component}.memory_request'),
                'memory_limit': self.get(f'resources.{component}.memory_limit'),
            }


# Global config instance
_config_instance: Optional[ConfigLoader] = None


def get_config() -> ConfigLoader:
    """Get or create global configuration instance"""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigLoader()
    return _config_instance


def load_config(config_file: Optional[str] = None, env: Optional[str] = None) -> ConfigLoader:
    """
    Load configuration (convenience function)

    Args:
        config_file: Path to config file
        env: Environment name (dev/staging/prod)

    Returns:
        ConfigLoader instance
    """
    global _config_instance
    _config_instance = ConfigLoader(config_file=config_file, env=env)
    return _config_instance


def get_config_value(key_path: str, default: Any = None) -> Any:
    """
    Get configuration value (convenience function)

    Args:
        key_path: Dot-separated path (e.g., 'mlflow.tracking_uri')
        default: Default value if not found

    Returns:
        Configuration value
    """
    return get_config().get(key_path, default)


# Example usage
if __name__ == "__main__":
    # Load configuration
    config = load_config()

    # Validate configuration
    if not config.validate():
        print("Configuration validation failed!")
        exit(1)

    # Example: Get MLflow configuration
    print("\n📊 MLflow Configuration:")
    mlflow_config = config.get_mlflow_config()
    for key, value in mlflow_config.items():
        print(f"  {key}: {value}")

    # Example: Get resource limits
    print("\n💻 TensorFlow Training Resources:")
    tf_resources = config.get_resource_limits('training', 'tensorflow')
    for key, value in tf_resources.items():
        print(f"  {key}: {value}")

    # Example: Get specific values
    print("\n🔧 Configuration Values:")
    print(f"  Min Accuracy: {config.get('governance.approval.min_accuracy')}")
    print(f"  Max Replicas: {config.get('kubernetes.serving.max_replicas')}")
    print(f"  Prometheus URL: {config.get('monitoring.prometheus.url')}")

    print("\n✅ Configuration loaded successfully!")
