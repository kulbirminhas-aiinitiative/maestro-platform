#!/usr/bin/env python3
"""
Test Data Generator: Synthetic data generation for tests.

Implements AC-3: Test data generation capabilities.
"""

import json
import logging
import random
import string
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Type

logger = logging.getLogger(__name__)


@dataclass
class DataGeneratorConfig:
    """Configuration for data generation."""
    seed: Optional[int] = None
    locale: str = "en_US"
    max_list_size: int = 10
    max_string_length: int = 100


class TestDataGenerator:
    """
    Generate synthetic test data.

    AC-3: Test data generation implementation.

    Features:
    - Schema-based generation
    - Type-specific generators
    - Reproducible with seed
    - Custom generator registration
    """

    def __init__(self, config: Optional[DataGeneratorConfig] = None):
        self.config = config or DataGeneratorConfig()
        if self.config.seed:
            random.seed(self.config.seed)

        self._generators: Dict[str, Callable] = {
            "string": self._generate_string,
            "int": self._generate_int,
            "float": self._generate_float,
            "bool": self._generate_bool,
            "uuid": self._generate_uuid,
            "email": self._generate_email,
            "date": self._generate_date,
            "datetime": self._generate_datetime,
            "list": self._generate_list,
            "dict": self._generate_dict,
            "user": self._generate_user,
            "team": self._generate_team,
            "task": self._generate_task,
        }

    def generate_sample_data(
        self,
        data_type: str,
        count: int = 1,
        **kwargs
    ) -> Any:
        """
        Generate sample data of specified type.

        Args:
            data_type: Type of data to generate
            count: Number of items (returns list if > 1)
            **kwargs: Additional parameters for generator
        """
        if data_type not in self._generators:
            raise ValueError(f"Unknown data type: {data_type}")

        generator = self._generators[data_type]

        if count == 1:
            return generator(**kwargs)
        return [generator(**kwargs) for _ in range(count)]

    def generate_from_schema(self, schema: Dict[str, Any]) -> Any:
        """
        Generate data matching a JSON schema.

        Supports:
        - type: string, integer, number, boolean, array, object
        - properties: for object types
        - items: for array types
        - enum: restricted values
        - format: email, date, datetime, uuid
        """
        schema_type = schema.get("type", "string")

        if "enum" in schema:
            return random.choice(schema["enum"])

        if schema_type == "string":
            format_type = schema.get("format")
            if format_type == "email":
                return self._generate_email()
            elif format_type == "date":
                return self._generate_date()
            elif format_type == "datetime":
                return self._generate_datetime()
            elif format_type == "uuid":
                return self._generate_uuid()
            else:
                min_len = schema.get("minLength", 5)
                max_len = schema.get("maxLength", 20)
                return self._generate_string(min_len, max_len)

        elif schema_type in ("integer", "int"):
            minimum = schema.get("minimum", 0)
            maximum = schema.get("maximum", 1000)
            return self._generate_int(minimum, maximum)

        elif schema_type in ("number", "float"):
            minimum = schema.get("minimum", 0.0)
            maximum = schema.get("maximum", 1000.0)
            return self._generate_float(minimum, maximum)

        elif schema_type == "boolean":
            return self._generate_bool()

        elif schema_type == "array":
            items_schema = schema.get("items", {"type": "string"})
            min_items = schema.get("minItems", 1)
            max_items = schema.get("maxItems", 5)
            count = random.randint(min_items, max_items)
            return [self.generate_from_schema(items_schema) for _ in range(count)]

        elif schema_type == "object":
            properties = schema.get("properties", {})
            result = {}
            for prop_name, prop_schema in properties.items():
                result[prop_name] = self.generate_from_schema(prop_schema)
            return result

        return None

    def generate_random(self, constraints: Dict[str, Any]) -> Any:
        """Generate random data with constraints."""
        data_type = constraints.get("type", "string")
        return self.generate_sample_data(data_type, **constraints)

    def register_generator(
        self,
        name: str,
        generator: Callable[..., Any]
    ) -> None:
        """Register a custom generator."""
        self._generators[name] = generator

    # Built-in generators
    def _generate_string(
        self,
        min_length: int = 5,
        max_length: int = 20
    ) -> str:
        """Generate random string."""
        length = random.randint(min_length, max_length)
        return ''.join(random.choices(string.ascii_letters, k=length))

    def _generate_int(
        self,
        minimum: int = 0,
        maximum: int = 1000
    ) -> int:
        """Generate random integer."""
        return random.randint(minimum, maximum)

    def _generate_float(
        self,
        minimum: float = 0.0,
        maximum: float = 1000.0
    ) -> float:
        """Generate random float."""
        return round(random.uniform(minimum, maximum), 2)

    def _generate_bool(self) -> bool:
        """Generate random boolean."""
        return random.choice([True, False])

    def _generate_uuid(self) -> str:
        """Generate UUID string."""
        return str(uuid.uuid4())

    def _generate_email(self) -> str:
        """Generate random email address."""
        username = self._generate_string(5, 10).lower()
        domains = ["example.com", "test.org", "sample.net"]
        return f"{username}@{random.choice(domains)}"

    def _generate_date(self) -> str:
        """Generate random date string (ISO format)."""
        days_offset = random.randint(-365, 365)
        date = datetime.now() + timedelta(days=days_offset)
        return date.strftime("%Y-%m-%d")

    def _generate_datetime(self) -> str:
        """Generate random datetime string (ISO format)."""
        days_offset = random.randint(-365, 365)
        hours_offset = random.randint(0, 23)
        dt = datetime.now() + timedelta(days=days_offset, hours=hours_offset)
        return dt.isoformat()

    def _generate_list(
        self,
        item_type: str = "string",
        min_items: int = 1,
        max_items: int = 5
    ) -> List[Any]:
        """Generate list of items."""
        count = random.randint(min_items, max_items)
        if item_type not in self._generators:
            raise ValueError(f"Unknown item type: {item_type}")
        generator = self._generators[item_type]
        return [generator() for _ in range(count)]

    def _generate_dict(
        self,
        keys: Optional[List[str]] = None,
        value_type: str = "string"
    ) -> Dict[str, Any]:
        """Generate dictionary."""
        if keys is None:
            keys = [self._generate_string(5, 10) for _ in range(3)]
        return {key: self.generate_sample_data(value_type) for key in keys}

    # Domain-specific generators
    def _generate_user(self) -> Dict[str, Any]:
        """Generate user object."""
        first_name = self._generate_string(3, 10)
        last_name = self._generate_string(3, 10)
        return {
            "id": self._generate_uuid(),
            "first_name": first_name,
            "last_name": last_name,
            "email": f"{first_name.lower()}.{last_name.lower()}@example.com",
            "active": self._generate_bool(),
            "created_at": self._generate_datetime()
        }

    def _generate_team(self) -> Dict[str, Any]:
        """Generate team object."""
        return {
            "id": self._generate_uuid(),
            "name": f"Team {self._generate_string(3, 8)}",
            "member_count": self._generate_int(3, 12),
            "velocity": self._generate_float(20, 50),
            "quality_score": self._generate_float(70, 100),
            "created_at": self._generate_datetime()
        }

    def _generate_task(self) -> Dict[str, Any]:
        """Generate task object."""
        statuses = ["todo", "in_progress", "review", "done"]
        priorities = ["low", "medium", "high", "critical"]
        return {
            "id": self._generate_uuid(),
            "title": f"Task: {self._generate_string(10, 30)}",
            "description": self._generate_string(20, 100),
            "status": random.choice(statuses),
            "priority": random.choice(priorities),
            "story_points": random.choice([1, 2, 3, 5, 8, 13]),
            "assignee": self._generate_email(),
            "created_at": self._generate_datetime()
        }


def get_data_generator(**kwargs) -> TestDataGenerator:
    """Factory function to create TestDataGenerator instance."""
    config = DataGeneratorConfig(**kwargs) if kwargs else None
    return TestDataGenerator(config=config)
