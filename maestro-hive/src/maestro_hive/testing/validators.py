#!/usr/bin/env python3
"""
Validation Helpers: Common validation patterns for tests.

Implements AC-4: Validation helpers for common patterns.
"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type, Union

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of a validation check."""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)

    def merge(self, other: 'ValidationResult') -> 'ValidationResult':
        """Merge with another validation result."""
        return ValidationResult(
            is_valid=self.is_valid and other.is_valid,
            errors=self.errors + other.errors,
            warnings=self.warnings + other.warnings,
            details={**self.details, **other.details}
        )


@dataclass
class AssertionResult:
    """Result of an assertion."""
    passed: bool
    message: str
    expected: Any = None
    actual: Any = None


class ValidationHelpers:
    """
    Common validation patterns for testing.

    AC-4: Validation helpers implementation.

    Provides:
    - Schema validation
    - Type checking
    - Value assertions
    - Custom validators
    """

    def __init__(self):
        self._custom_validators: Dict[str, Callable] = {}

    def validate_schema(
        self,
        data: Any,
        schema: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate data against a JSON schema.

        Supports basic JSON Schema validation.
        """
        result = ValidationResult(is_valid=True)

        schema_type = schema.get("type")
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        # Type validation
        type_valid = self._validate_type(data, schema_type)
        if not type_valid:
            result.add_error(f"Type mismatch: expected {schema_type}, got {type(data).__name__}")
            return result

        # Object validation
        if schema_type == "object" and isinstance(data, dict):
            # Required fields
            for field in required:
                if field not in data:
                    result.add_error(f"Missing required field: {field}")

            # Property validation
            for prop_name, prop_schema in properties.items():
                if prop_name in data:
                    prop_result = self.validate_schema(data[prop_name], prop_schema)
                    if not prop_result.is_valid:
                        for error in prop_result.errors:
                            result.add_error(f"{prop_name}: {error}")

        # Array validation
        elif schema_type == "array" and isinstance(data, list):
            items_schema = schema.get("items", {})
            for i, item in enumerate(data):
                item_result = self.validate_schema(item, items_schema)
                if not item_result.is_valid:
                    for error in item_result.errors:
                        result.add_error(f"[{i}]: {error}")

            # Min/max items
            min_items = schema.get("minItems")
            max_items = schema.get("maxItems")
            if min_items and len(data) < min_items:
                result.add_error(f"Array has {len(data)} items, minimum is {min_items}")
            if max_items and len(data) > max_items:
                result.add_error(f"Array has {len(data)} items, maximum is {max_items}")

        # String validation
        elif schema_type == "string" and isinstance(data, str):
            min_length = schema.get("minLength")
            max_length = schema.get("maxLength")
            pattern = schema.get("pattern")

            if min_length and len(data) < min_length:
                result.add_error(f"String length {len(data)} below minimum {min_length}")
            if max_length and len(data) > max_length:
                result.add_error(f"String length {len(data)} exceeds maximum {max_length}")
            if pattern and not re.match(pattern, data):
                result.add_error(f"String does not match pattern: {pattern}")

        # Number validation
        elif schema_type in ("integer", "number"):
            minimum = schema.get("minimum")
            maximum = schema.get("maximum")

            if minimum is not None and data < minimum:
                result.add_error(f"Value {data} below minimum {minimum}")
            if maximum is not None and data > maximum:
                result.add_error(f"Value {data} exceeds maximum {maximum}")

        # Enum validation
        if "enum" in schema and data not in schema["enum"]:
            result.add_error(f"Value must be one of: {schema['enum']}")

        return result

    def validate_type(
        self,
        value: Any,
        expected_type: Union[Type, str]
    ) -> bool:
        """Check if value matches expected type."""
        type_mapping = {
            "string": str,
            "str": str,
            "integer": int,
            "int": int,
            "number": (int, float),
            "float": float,
            "boolean": bool,
            "bool": bool,
            "array": list,
            "list": list,
            "object": dict,
            "dict": dict,
            "null": type(None),
            "none": type(None)
        }

        if isinstance(expected_type, str):
            expected_type = type_mapping.get(expected_type.lower(), str)

        return isinstance(value, expected_type)

    def _validate_type(self, data: Any, schema_type: str) -> bool:
        """Internal type validation."""
        if schema_type is None:
            return True
        return self.validate_type(data, schema_type)

    def assert_equals(
        self,
        actual: Any,
        expected: Any,
        message: str = ""
    ) -> AssertionResult:
        """Assert two values are equal."""
        passed = actual == expected
        return AssertionResult(
            passed=passed,
            message=message or f"Expected {expected}, got {actual}",
            expected=expected,
            actual=actual
        )

    def assert_not_equals(
        self,
        actual: Any,
        expected: Any,
        message: str = ""
    ) -> AssertionResult:
        """Assert two values are not equal."""
        passed = actual != expected
        return AssertionResult(
            passed=passed,
            message=message or f"Expected not equal to {expected}",
            expected=f"!= {expected}",
            actual=actual
        )

    def assert_true(self, value: Any, message: str = "") -> AssertionResult:
        """Assert value is truthy."""
        return AssertionResult(
            passed=bool(value),
            message=message or f"Expected truthy value, got {value}",
            expected=True,
            actual=value
        )

    def assert_false(self, value: Any, message: str = "") -> AssertionResult:
        """Assert value is falsy."""
        return AssertionResult(
            passed=not bool(value),
            message=message or f"Expected falsy value, got {value}",
            expected=False,
            actual=value
        )

    def assert_contains(
        self,
        container: Any,
        item: Any,
        message: str = ""
    ) -> AssertionResult:
        """Assert container contains item."""
        try:
            passed = item in container
        except TypeError:
            passed = False
        return AssertionResult(
            passed=passed,
            message=message or f"Expected {container} to contain {item}",
            expected=f"contains {item}",
            actual=container
        )

    def assert_not_contains(
        self,
        container: Any,
        item: Any,
        message: str = ""
    ) -> AssertionResult:
        """Assert container does not contain item."""
        try:
            passed = item not in container
        except TypeError:
            passed = True
        return AssertionResult(
            passed=passed,
            message=message or f"Expected {container} to not contain {item}",
            expected=f"not contains {item}",
            actual=container
        )

    def assert_length(
        self,
        value: Any,
        expected_length: int,
        message: str = ""
    ) -> AssertionResult:
        """Assert value has expected length."""
        try:
            actual_length = len(value)
            passed = actual_length == expected_length
        except TypeError:
            actual_length = None
            passed = False
        return AssertionResult(
            passed=passed,
            message=message or f"Expected length {expected_length}, got {actual_length}",
            expected=expected_length,
            actual=actual_length
        )

    def assert_range(
        self,
        value: Any,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        message: str = ""
    ) -> AssertionResult:
        """Assert value is within range."""
        try:
            passed = True
            if min_val is not None and value < min_val:
                passed = False
            if max_val is not None and value > max_val:
                passed = False
        except TypeError:
            passed = False
        return AssertionResult(
            passed=passed,
            message=message or f"Expected value in range [{min_val}, {max_val}], got {value}",
            expected=f"[{min_val}, {max_val}]",
            actual=value
        )

    def assert_regex(
        self,
        value: str,
        pattern: str,
        message: str = ""
    ) -> AssertionResult:
        """Assert value matches regex pattern."""
        passed = bool(re.match(pattern, str(value)))
        return AssertionResult(
            passed=passed,
            message=message or f"Expected '{value}' to match pattern '{pattern}'",
            expected=pattern,
            actual=value
        )

    def register_validator(
        self,
        name: str,
        validator: Callable[[Any], ValidationResult]
    ) -> None:
        """Register a custom validator."""
        self._custom_validators[name] = validator

    def validate_custom(
        self,
        data: Any,
        validator_name: str
    ) -> ValidationResult:
        """Run a custom validator."""
        if validator_name not in self._custom_validators:
            raise ValueError(f"Unknown validator: {validator_name}")
        return self._custom_validators[validator_name](data)


def get_validation_helpers() -> ValidationHelpers:
    """Factory function to create ValidationHelpers instance."""
    return ValidationHelpers()
