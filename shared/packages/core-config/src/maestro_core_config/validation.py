"""
Configuration validation utilities.

Provides validation helpers for configuration values.
"""

from typing import Any, Callable, Dict, List, Optional
from maestro_core_logging import get_logger

def _get_logger():
    try:
        from maestro_core_logging import get_logger
        return get_logger(__name__)
    except:
        import logging
        return logging.getLogger(__name__)

logger = type("LazyLogger", (), {"__getattr__": lambda self, name: getattr(_get_logger(), name)})()


class ConfigValidator:
    """
    Validate configuration values with custom rules.

    Example:
        >>> validator = ConfigValidator()
        >>> validator.add_rule("port", lambda x: 1024 <= x <= 65535, "Port must be 1024-65535")
        >>> validator.validate({"port": 8080})
        True
    """

    def __init__(self):
        """Initialize configuration validator."""
        self.rules: Dict[str, List[tuple[Callable, str]]] = {}

    def add_rule(self, field: str, validator: Callable[[Any], bool], message: str) -> None:
        """
        Add a validation rule for a field.

        Args:
            field: Configuration field name
            validator: Validation function that returns True if valid
            message: Error message if validation fails

        Example:
            >>> validator.add_rule(
            ...     "database_port",
            ...     lambda x: isinstance(x, int) and 1 <= x <= 65535,
            ...     "Database port must be 1-65535"
            ... )
        """
        if field not in self.rules:
            self.rules[field] = []

        self.rules[field].append((validator, message))
        logger.debug(f"Added validation rule for field", field=field)

    def validate(self, config: Dict[str, Any]) -> bool:
        """
        Validate configuration against all rules.

        Args:
            config: Configuration dictionary to validate

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails

        Example:
            >>> validator = ConfigValidator()
            >>> validator.add_rule("port", lambda x: x > 0, "Port must be positive")
            >>> validator.validate({"port": 8080})
            True
        """
        errors = []

        for field, rules in self.rules.items():
            if field not in config:
                logger.warning(f"Field not found in config", field=field)
                continue

            value = config[field]

            for validator_func, error_message in rules:
                try:
                    if not validator_func(value):
                        errors.append(f"{field}: {error_message} (got: {value})")
                        logger.warning(
                            f"Validation failed for field",
                            field=field,
                            value=value,
                            message=error_message
                        )
                except Exception as e:
                    errors.append(f"{field}: Validation error - {str(e)}")
                    logger.error(f"Validation exception for field", field=field, error=str(e))

        if errors:
            error_msg = "; ".join(errors)
            raise ValueError(f"Configuration validation failed: {error_msg}")

        logger.info(f"Configuration validation successful", fields_validated=len(self.rules))
        return True

    def validate_safe(self, config: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate configuration without raising exceptions.

        Args:
            config: Configuration dictionary to validate

        Returns:
            Tuple of (is_valid, error_message)

        Example:
            >>> validator = ConfigValidator()
            >>> validator.add_rule("port", lambda x: x > 0, "Port must be positive")
            >>> is_valid, error = validator.validate_safe({"port": -1})
            >>> print(is_valid)
            False
            >>> print(error)
            Configuration validation failed: port: Port must be positive (got: -1)
        """
        try:
            self.validate(config)
            return True, None
        except ValueError as e:
            return False, str(e)


# Common validation functions

def is_port(value: Any) -> bool:
    """
    Validate that value is a valid port number.

    Args:
        value: Value to validate

    Returns:
        True if valid port (1-65535)

    Example:
        >>> is_port(8080)
        True
        >>> is_port(0)
        False
    """
    return isinstance(value, int) and 1 <= value <= 65535


def is_url(value: Any) -> bool:
    """
    Validate that value is a valid URL.

    Args:
        value: Value to validate

    Returns:
        True if valid URL

    Example:
        >>> is_url("http://example.com")
        True
        >>> is_url("not-a-url")
        False
    """
    if not isinstance(value, str):
        return False

    from urllib.parse import urlparse
    try:
        result = urlparse(value)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def is_email(value: Any) -> bool:
    """
    Validate that value is a valid email address.

    Args:
        value: Value to validate

    Returns:
        True if valid email

    Example:
        >>> is_email("user@example.com")
        True
        >>> is_email("not-an-email")
        False
    """
    if not isinstance(value, str):
        return False

    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, value))


def is_in_range(min_val: float, max_val: float) -> Callable[[Any], bool]:
    """
    Create a validator that checks if value is in range.

    Args:
        min_val: Minimum value (inclusive)
        max_val: Maximum value (inclusive)

    Returns:
        Validator function

    Example:
        >>> validator = is_in_range(0, 100)
        >>> validator(50)
        True
        >>> validator(150)
        False
    """
    def validate(value: Any) -> bool:
        try:
            num_value = float(value)
            return min_val <= num_value <= max_val
        except (TypeError, ValueError):
            return False

    return validate


def is_one_of(allowed_values: List[Any]) -> Callable[[Any], bool]:
    """
    Create a validator that checks if value is one of allowed values.

    Args:
        allowed_values: List of allowed values

    Returns:
        Validator function

    Example:
        >>> validator = is_one_of(["development", "staging", "production"])
        >>> validator("production")
        True
        >>> validator("local")
        False
    """
    def validate(value: Any) -> bool:
        return value in allowed_values

    return validate


def is_non_empty(value: Any) -> bool:
    """
    Validate that value is not empty.

    Args:
        value: Value to validate

    Returns:
        True if value is not None and not empty

    Example:
        >>> is_non_empty("hello")
        True
        >>> is_non_empty("")
        False
    """
    if value is None:
        return False

    if isinstance(value, str):
        return bool(value.strip())

    if isinstance(value, (list, dict, tuple, set)):
        return len(value) > 0

    return True


def matches_pattern(pattern: str) -> Callable[[Any], bool]:
    """
    Create a validator that checks if value matches regex pattern.

    Args:
        pattern: Regular expression pattern

    Returns:
        Validator function

    Example:
        >>> validator = matches_pattern(r'^[a-z]{3,10}$')
        >>> validator("hello")
        True
        >>> validator("HELLO")
        False
    """
    import re
    compiled_pattern = re.compile(pattern)

    def validate(value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return bool(compiled_pattern.match(value))

    return validate


# Export all
__all__ = [
    "ConfigValidator",
    "is_port",
    "is_url",
    "is_email",
    "is_in_range",
    "is_one_of",
    "is_non_empty",
    "matches_pattern",
]
