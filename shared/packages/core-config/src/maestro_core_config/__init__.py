"""
MAESTRO Core Configuration Library

Enterprise-grade configuration management with validation, encryption,
and multiple source support (env vars, files, Vault, etc.).

Usage:
    from maestro_core_config import ConfigManager, BaseConfig

    class MyConfig(BaseConfig):
        database_url: str
        api_key: str = Field(..., secret=True)
        debug: bool = False

    config = ConfigManager(MyConfig).load()
    print(config.database_url)
"""

from .core import ConfigManager
from .base import BaseConfig, SecretStr
from .loaders import (
    EnvironmentLoader,
    FileLoader,
    VaultLoader,
    ConsulLoader
)
from .encryption import ConfigEncryption
from .validation import (
    ConfigValidator,
    is_port,
    is_url,
    is_email,
    is_in_range,
    is_one_of,
    is_non_empty,
    matches_pattern
)

__version__ = "1.0.0"
__all__ = [
    "ConfigManager",
    "BaseConfig",
    "SecretStr",
    "EnvironmentLoader",
    "FileLoader",
    "VaultLoader",
    "ConsulLoader",
    "ConfigEncryption",
    "ConfigValidator",
    "is_port",
    "is_url",
    "is_email",
    "is_in_range",
    "is_one_of",
    "is_non_empty",
    "matches_pattern",
]