"""
Base configuration classes for MAESTRO configuration management.

Provides foundational configuration models and utilities.
"""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, SecretStr as PydanticSecretStr, validator
from maestro_core_logging import get_logger

def _get_logger():
    try:
        from maestro_core_logging import get_logger
        return get_logger(__name__)
    except:
        import logging
        return logging.getLogger(__name__)

logger = type("LazyLogger", (), {"__getattr__": lambda self, name: getattr(_get_logger(), name)})()


class SecretStr(PydanticSecretStr):
    """
    Secure string type that masks sensitive values in logs and string representations.

    Extends Pydantic's SecretStr with additional utilities.

    Example:
        >>> api_key = SecretStr("sk-1234567890")
        >>> print(api_key)
        **********
        >>> print(api_key.get_secret_value())
        sk-1234567890
    """

    def __repr__(self) -> str:
        """Mask secret in repr."""
        return f"SecretStr('**********')"

    def __str__(self) -> str:
        """Mask secret in str."""
        return "**********"


class BaseConfig(BaseModel):
    """
    Base configuration model with common functionality.

    All MAESTRO configuration classes should inherit from this base.

    Features:
        - Pydantic validation
        - Environment variable loading
        - Secret masking
        - Nested configuration support
        - Validation hooks

    Example:
        >>> class DatabaseConfig(BaseConfig):
        ...     host: str = "localhost"
        ...     port: int = 5432
        ...     password: SecretStr
        ...
        >>> config = DatabaseConfig(password="secret123")
        >>> print(config.password)
        **********
    """

    class Config:
        """Pydantic configuration."""
        # Allow environment variables
        env_prefix = "MAESTRO_"

        # Validate on assignment
        validate_assignment = True

        # Allow extra fields (can be restricted in subclasses)
        extra = "allow"

        # Use enum values
        use_enum_values = True

        # JSON encoders for special types
        json_encoders = {
            SecretStr: lambda v: "**********" if v else None,
            PydanticSecretStr: lambda v: "**********" if v else None,
        }

    def dict(self, **kwargs) -> Dict[str, Any]:
        """
        Convert config to dictionary with secret masking.

        Args:
            **kwargs: Additional arguments passed to Pydantic's dict()

        Returns:
            Dictionary representation with secrets masked
        """
        # Default to excluding unset values
        kwargs.setdefault("exclude_unset", False)
        kwargs.setdefault("exclude_none", False)

        result = super().dict(**kwargs)

        # Mask secrets in nested structures
        return self._mask_secrets(result)

    def _mask_secrets(self, data: Any) -> Any:
        """
        Recursively mask secret values in data structures.

        Args:
            data: Data to mask secrets in

        Returns:
            Data with secrets masked
        """
        if isinstance(data, dict):
            return {k: self._mask_secrets(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._mask_secrets(item) for item in data]
        elif isinstance(data, (SecretStr, PydanticSecretStr)):
            return "**********"
        else:
            return data

    def get_secret_value(self, field_name: str) -> Optional[str]:
        """
        Safely get the actual value of a secret field.

        Args:
            field_name: Name of the secret field

        Returns:
            Actual secret value or None if field doesn't exist

        Example:
            >>> config = DatabaseConfig(password="secret123")
            >>> actual_password = config.get_secret_value("password")
            >>> print(actual_password)
            secret123
        """
        field_value = getattr(self, field_name, None)

        if isinstance(field_value, (SecretStr, PydanticSecretStr)):
            return field_value.get_secret_value()

        return field_value

    def validate_config(self) -> bool:
        """
        Validate configuration after loading.

        Override this method in subclasses for custom validation logic.

        Returns:
            True if valid, raises exception otherwise

        Raises:
            ValueError: If configuration is invalid

        Example:
            >>> class AppConfig(BaseConfig):
            ...     port: int
            ...
            ...     def validate_config(self) -> bool:
            ...         if self.port < 1024:
            ...             raise ValueError("Port must be >= 1024")
            ...         return super().validate_config()
        """
        logger.debug(f"Validating configuration: {self.__class__.__name__}")
        return True

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseConfig":
        """
        Create configuration from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            Configuration instance

        Example:
            >>> config_dict = {"host": "localhost", "port": 5432}
            >>> config = DatabaseConfig.from_dict(config_dict)
        """
        return cls(**data)

    @classmethod
    def from_env(cls) -> "BaseConfig":
        """
        Create configuration from environment variables.

        Reads environment variables with MAESTRO_ prefix.

        Returns:
            Configuration instance

        Example:
            >>> # With MAESTRO_HOST=localhost and MAESTRO_PORT=5432 in env
            >>> config = DatabaseConfig.from_env()
        """
        import os

        # Collect environment variables with prefix
        env_vars = {}
        prefix = cls.Config.env_prefix

        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove prefix and convert to lowercase
                field_name = key[len(prefix):].lower()
                env_vars[field_name] = value

        logger.debug(f"Loading {cls.__name__} from environment", fields=list(env_vars.keys()))
        return cls(**env_vars)


# Export all
__all__ = [
    "BaseConfig",
    "SecretStr",
]