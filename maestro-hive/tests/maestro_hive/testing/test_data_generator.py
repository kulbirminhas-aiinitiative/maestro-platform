#!/usr/bin/env python3
"""
Tests for TestDataGenerator.

Tests AC-3: Test data generation capabilities.
"""

import pytest
import re

from maestro_hive.testing.data_generator import (
    TestDataGenerator, DataGeneratorConfig, get_data_generator
)


class TestDataGeneratorConfig:
    """Tests for DataGeneratorConfig."""

    def test_default_config(self):
        """Test default configuration."""
        config = DataGeneratorConfig()
        assert config.seed is None
        assert config.locale == "en_US"
        assert config.max_list_size == 10

    def test_custom_config(self):
        """Test custom configuration."""
        config = DataGeneratorConfig(seed=42, locale="en_GB")
        assert config.seed == 42
        assert config.locale == "en_GB"


class TestTestDataGenerator:
    """Tests for TestDataGenerator."""

    @pytest.fixture
    def generator(self):
        """Create generator with seed for reproducibility."""
        return TestDataGenerator(DataGeneratorConfig(seed=42))

    def test_generate_string(self, generator):
        """AC-3: Test string generation."""
        result = generator.generate_sample_data("string")
        assert isinstance(result, str)
        assert len(result) >= 5

    def test_generate_string_with_length(self, generator):
        """AC-3: Test string with custom length."""
        result = generator.generate_sample_data("string", min_length=10, max_length=20)
        assert 10 <= len(result) <= 20

    def test_generate_int(self, generator):
        """AC-3: Test integer generation."""
        result = generator.generate_sample_data("int")
        assert isinstance(result, int)
        assert 0 <= result <= 1000

    def test_generate_int_with_range(self, generator):
        """AC-3: Test integer with custom range."""
        result = generator.generate_sample_data("int", minimum=100, maximum=200)
        assert 100 <= result <= 200

    def test_generate_float(self, generator):
        """AC-3: Test float generation."""
        result = generator.generate_sample_data("float")
        assert isinstance(result, float)

    def test_generate_bool(self, generator):
        """AC-3: Test boolean generation."""
        result = generator.generate_sample_data("bool")
        assert isinstance(result, bool)

    def test_generate_uuid(self, generator):
        """AC-3: Test UUID generation."""
        result = generator.generate_sample_data("uuid")
        assert isinstance(result, str)
        # UUID format check
        assert len(result) == 36
        assert result.count('-') == 4

    def test_generate_email(self, generator):
        """AC-3: Test email generation."""
        result = generator.generate_sample_data("email")
        assert isinstance(result, str)
        assert '@' in result
        assert '.' in result

    def test_generate_date(self, generator):
        """AC-3: Test date generation."""
        result = generator.generate_sample_data("date")
        assert isinstance(result, str)
        assert re.match(r'\d{4}-\d{2}-\d{2}', result)

    def test_generate_datetime(self, generator):
        """AC-3: Test datetime generation."""
        result = generator.generate_sample_data("datetime")
        assert isinstance(result, str)
        assert 'T' in result

    def test_generate_list(self, generator):
        """AC-3: Test list generation."""
        result = generator.generate_sample_data("list", item_type="int")
        assert isinstance(result, list)
        assert all(isinstance(item, int) for item in result)

    def test_generate_dict(self, generator):
        """AC-3: Test dict generation."""
        result = generator.generate_sample_data("dict")
        assert isinstance(result, dict)

    def test_generate_user(self, generator):
        """AC-3: Test user object generation."""
        result = generator.generate_sample_data("user")
        assert isinstance(result, dict)
        assert 'id' in result
        assert 'email' in result
        assert 'first_name' in result

    def test_generate_team(self, generator):
        """AC-3: Test team object generation."""
        result = generator.generate_sample_data("team")
        assert isinstance(result, dict)
        assert 'id' in result
        assert 'name' in result
        assert 'velocity' in result

    def test_generate_task(self, generator):
        """AC-3: Test task object generation."""
        result = generator.generate_sample_data("task")
        assert isinstance(result, dict)
        assert 'status' in result
        assert 'priority' in result

    def test_generate_multiple(self, generator):
        """AC-3: Test generating multiple items."""
        results = generator.generate_sample_data("user", count=5)
        assert isinstance(results, list)
        assert len(results) == 5

    def test_generate_from_schema(self, generator):
        """AC-3: Test schema-based generation."""
        schema = {
            "type": "object",
            "properties": {
                "name": {"type": "string", "minLength": 3},
                "age": {"type": "integer", "minimum": 18, "maximum": 65},
                "active": {"type": "boolean"}
            }
        }

        result = generator.generate_from_schema(schema)
        assert isinstance(result, dict)
        assert 'name' in result
        assert 'age' in result
        assert 18 <= result['age'] <= 65

    def test_generate_from_schema_array(self, generator):
        """AC-3: Test array schema generation."""
        schema = {
            "type": "array",
            "items": {"type": "integer"},
            "minItems": 2,
            "maxItems": 5
        }

        result = generator.generate_from_schema(schema)
        assert isinstance(result, list)
        assert 2 <= len(result) <= 5

    def test_generate_from_schema_enum(self, generator):
        """AC-3: Test enum schema generation."""
        schema = {
            "type": "string",
            "enum": ["red", "green", "blue"]
        }

        result = generator.generate_from_schema(schema)
        assert result in ["red", "green", "blue"]

    def test_custom_generator(self, generator):
        """AC-3: Test registering custom generator."""
        def custom_gen(**kwargs):
            return {"custom": True, "value": 42}

        generator.register_generator("custom_type", custom_gen)
        result = generator.generate_sample_data("custom_type")

        assert result["custom"] is True
        assert result["value"] == 42

    def test_unknown_type_raises(self, generator):
        """Test unknown type raises error."""
        with pytest.raises(ValueError, match="Unknown data type"):
            generator.generate_sample_data("unknown_type")


class TestDataGeneratorFactory:
    """Tests for get_data_generator factory."""

    def test_factory_default(self):
        """Test factory with defaults."""
        gen = get_data_generator()
        assert isinstance(gen, TestDataGenerator)

    def test_factory_with_seed(self):
        """Test factory with seed."""
        gen = get_data_generator(seed=123)
        assert gen.config.seed == 123
