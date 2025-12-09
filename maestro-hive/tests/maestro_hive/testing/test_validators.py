#!/usr/bin/env python3
"""
Tests for ValidationHelpers.

Tests AC-4: Validation helpers for common patterns.
"""

import pytest

from maestro_hive.testing.validators import (
    ValidationHelpers, ValidationResult, AssertionResult,
    get_validation_helpers
)


class TestValidationResult:
    """Tests for ValidationResult."""

    def test_result_creation(self):
        """Test ValidationResult creation."""
        result = ValidationResult(is_valid=True)
        assert result.is_valid
        assert result.errors == []

    def test_add_error(self):
        """Test adding error."""
        result = ValidationResult(is_valid=True)
        result.add_error("Test error")

        assert not result.is_valid
        assert "Test error" in result.errors

    def test_add_warning(self):
        """Test adding warning."""
        result = ValidationResult(is_valid=True)
        result.add_warning("Test warning")

        assert result.is_valid  # Warnings don't change validity
        assert "Test warning" in result.warnings

    def test_merge_results(self):
        """Test merging validation results."""
        r1 = ValidationResult(is_valid=True, errors=[], warnings=["w1"])
        r2 = ValidationResult(is_valid=True, errors=[], warnings=["w2"])

        merged = r1.merge(r2)
        assert merged.is_valid
        assert len(merged.warnings) == 2

    def test_merge_with_invalid(self):
        """Test merging with invalid result."""
        r1 = ValidationResult(is_valid=True)
        r2 = ValidationResult(is_valid=False, errors=["error"])

        merged = r1.merge(r2)
        assert not merged.is_valid


class TestValidationHelpers:
    """Tests for ValidationHelpers."""

    @pytest.fixture
    def validator(self):
        """Create ValidationHelpers instance."""
        return ValidationHelpers()

    # Schema validation tests
    def test_validate_schema_string(self, validator):
        """AC-4: Validate string against schema."""
        schema = {"type": "string"}
        result = validator.validate_schema("hello", schema)
        assert result.is_valid

    def test_validate_schema_string_invalid(self, validator):
        """AC-4: Invalid string type."""
        schema = {"type": "string"}
        result = validator.validate_schema(123, schema)
        assert not result.is_valid

    def test_validate_schema_string_length(self, validator):
        """AC-4: String length validation."""
        schema = {"type": "string", "minLength": 5, "maxLength": 10}

        assert validator.validate_schema("hello", schema).is_valid
        assert not validator.validate_schema("hi", schema).is_valid
        assert not validator.validate_schema("hello world!", schema).is_valid

    def test_validate_schema_string_pattern(self, validator):
        """AC-4: String pattern validation."""
        schema = {"type": "string", "pattern": r"^\d{3}-\d{4}$"}

        assert validator.validate_schema("123-4567", schema).is_valid
        assert not validator.validate_schema("12-4567", schema).is_valid

    def test_validate_schema_integer(self, validator):
        """AC-4: Integer validation."""
        schema = {"type": "integer", "minimum": 0, "maximum": 100}

        assert validator.validate_schema(50, schema).is_valid
        assert not validator.validate_schema(-1, schema).is_valid
        assert not validator.validate_schema(150, schema).is_valid

    def test_validate_schema_object(self, validator):
        """AC-4: Object validation."""
        schema = {
            "type": "object",
            "required": ["name", "age"],
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"}
            }
        }

        valid_data = {"name": "John", "age": 30}
        assert validator.validate_schema(valid_data, schema).is_valid

        missing_field = {"name": "John"}
        assert not validator.validate_schema(missing_field, schema).is_valid

    def test_validate_schema_array(self, validator):
        """AC-4: Array validation."""
        schema = {
            "type": "array",
            "items": {"type": "integer"},
            "minItems": 2,
            "maxItems": 5
        }

        assert validator.validate_schema([1, 2, 3], schema).is_valid
        assert not validator.validate_schema([1], schema).is_valid
        assert not validator.validate_schema([1, 2, 3, 4, 5, 6], schema).is_valid

    def test_validate_schema_enum(self, validator):
        """AC-4: Enum validation."""
        schema = {"enum": ["red", "green", "blue"]}

        assert validator.validate_schema("red", schema).is_valid
        assert not validator.validate_schema("yellow", schema).is_valid

    # Type validation tests
    def test_validate_type_string(self, validator):
        """AC-4: Type validation for string."""
        assert validator.validate_type("hello", str)
        assert validator.validate_type("hello", "string")
        assert not validator.validate_type(123, str)

    def test_validate_type_int(self, validator):
        """AC-4: Type validation for int."""
        assert validator.validate_type(42, int)
        assert validator.validate_type(42, "integer")
        assert not validator.validate_type("42", int)

    def test_validate_type_list(self, validator):
        """AC-4: Type validation for list."""
        assert validator.validate_type([1, 2, 3], list)
        assert validator.validate_type([1, 2, 3], "array")

    def test_validate_type_dict(self, validator):
        """AC-4: Type validation for dict."""
        assert validator.validate_type({"a": 1}, dict)
        assert validator.validate_type({"a": 1}, "object")

    # Assertion tests
    def test_assert_equals_pass(self, validator):
        """AC-4: Assert equals passing."""
        result = validator.assert_equals(5, 5)
        assert result.passed

    def test_assert_equals_fail(self, validator):
        """AC-4: Assert equals failing."""
        result = validator.assert_equals(5, 10)
        assert not result.passed
        assert result.expected == 10
        assert result.actual == 5

    def test_assert_not_equals(self, validator):
        """AC-4: Assert not equals."""
        assert validator.assert_not_equals(5, 10).passed
        assert not validator.assert_not_equals(5, 5).passed

    def test_assert_true(self, validator):
        """AC-4: Assert true."""
        assert validator.assert_true(True).passed
        assert validator.assert_true(1).passed
        assert not validator.assert_true(False).passed
        assert not validator.assert_true(0).passed

    def test_assert_false(self, validator):
        """AC-4: Assert false."""
        assert validator.assert_false(False).passed
        assert validator.assert_false(0).passed
        assert not validator.assert_false(True).passed

    def test_assert_contains(self, validator):
        """AC-4: Assert contains."""
        assert validator.assert_contains([1, 2, 3], 2).passed
        assert validator.assert_contains("hello", "ell").passed
        assert not validator.assert_contains([1, 2, 3], 5).passed

    def test_assert_not_contains(self, validator):
        """AC-4: Assert not contains."""
        assert validator.assert_not_contains([1, 2, 3], 5).passed
        assert not validator.assert_not_contains([1, 2, 3], 2).passed

    def test_assert_length(self, validator):
        """AC-4: Assert length."""
        assert validator.assert_length([1, 2, 3], 3).passed
        assert validator.assert_length("hello", 5).passed
        assert not validator.assert_length([1, 2], 3).passed

    def test_assert_range(self, validator):
        """AC-4: Assert range."""
        assert validator.assert_range(5, min_val=0, max_val=10).passed
        assert not validator.assert_range(15, min_val=0, max_val=10).passed
        assert not validator.assert_range(-5, min_val=0, max_val=10).passed

    def test_assert_regex(self, validator):
        """AC-4: Assert regex."""
        assert validator.assert_regex("test@example.com", r".+@.+\..+").passed
        assert not validator.assert_regex("invalid", r".+@.+\..+").passed

    # Custom validator tests
    def test_custom_validator(self, validator):
        """AC-4: Custom validator registration."""
        def even_validator(data):
            result = ValidationResult(is_valid=True)
            if data % 2 != 0:
                result.add_error("Value must be even")
            return result

        validator.register_validator("even", even_validator)

        assert validator.validate_custom(4, "even").is_valid
        assert not validator.validate_custom(5, "even").is_valid

    def test_unknown_validator_raises(self, validator):
        """Test unknown validator raises error."""
        with pytest.raises(ValueError, match="Unknown validator"):
            validator.validate_custom(1, "nonexistent")


class TestValidationHelpersFactory:
    """Tests for get_validation_helpers factory."""

    def test_factory(self):
        """Test factory function."""
        helper = get_validation_helpers()
        assert isinstance(helper, ValidationHelpers)
