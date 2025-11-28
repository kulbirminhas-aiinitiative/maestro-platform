"""
BDV Step Registry and Definitions

Provides a decorator-based system for defining Given/When/Then steps
with parameter extraction, context management, and async support.

Key Features:
- @given, @when, @then decorators for step definitions
- Regex-based parameter extraction from step text
- Context object for sharing state between steps
- HTTP client integration (httpx)
- Async step support
- Data table parsing
- Fixture injection
- Custom assertions

Author: Claude Code Implementation
Date: 2025-10-13
Version: 1.0.0
"""

import re
import inspect
import asyncio
from typing import Dict, List, Callable, Any, Optional, Pattern, Union
from dataclasses import dataclass, field
from enum import Enum
import httpx


class StepType(str, Enum):
    """Step definition types"""
    GIVEN = "given"
    WHEN = "when"
    THEN = "then"


@dataclass
class DataTable:
    """Represents a Gherkin data table"""
    headers: List[str]
    rows: List[List[str]]

    def to_dict_list(self) -> List[Dict[str, str]]:
        """Convert table to list of dictionaries"""
        return [
            {self.headers[i]: cell for i, cell in enumerate(row)}
            for row in self.rows
        ]

    def as_dicts(self) -> List[Dict[str, str]]:
        """Alias for to_dict_list"""
        return self.to_dict_list()


@dataclass
class Context:
    """
    Context object for sharing state between steps.

    Attributes are dynamically added as steps execute.
    """
    _data: Dict[str, Any] = field(default_factory=dict)
    _http_client: Optional[httpx.Client] = None
    _async_http_client: Optional[httpx.AsyncClient] = None

    def __setattr__(self, name: str, value: Any):
        """Set attribute on context"""
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            if not hasattr(self, '_data'):
                object.__setattr__(self, '_data', {})
            self._data[name] = value

    def __getattr__(self, name: str) -> Any:
        """Get attribute from context"""
        if name == '_data':
            return object.__getattribute__(self, '_data')
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"Context has no attribute '{name}'")

    def __contains__(self, key: str) -> bool:
        """Check if key exists in context"""
        return key in self._data

    def get(self, key: str, default: Any = None) -> Any:
        """Get value with default"""
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        """Set value in context"""
        self._data[key] = value

    def clear(self):
        """Clear all context data"""
        self._data.clear()
        if self._http_client:
            self._http_client.close()
            self._http_client = None
        if self._async_http_client:
            asyncio.run(self._async_http_client.aclose())
            self._async_http_client = None

    @property
    def http(self) -> httpx.Client:
        """Get HTTP client (creates if doesn't exist)"""
        if not self._http_client:
            self._http_client = httpx.Client(timeout=30.0)
        return self._http_client

    @property
    def async_http(self) -> httpx.AsyncClient:
        """Get async HTTP client (creates if doesn't exist)"""
        if not self._async_http_client:
            self._async_http_client = httpx.AsyncClient(timeout=30.0)
        return self._async_http_client


@dataclass
class StepMatch:
    """Represents a matched step definition"""
    pattern: Pattern
    func: Callable
    step_type: StepType
    is_async: bool
    parameters: Dict[str, Any] = field(default_factory=dict)


class StepRegistry:
    """
    Registry for step definitions with Given/When/Then decorators.

    Usage:
        registry = StepRegistry()

        @registry.given('I have {count:int} items')
        def step_impl(context, count):
            context.item_count = count

        @registry.when('I search for "{query}"')
        def step_impl(context, query):
            context.search_query = query

        @registry.then('I should see {count:int} results')
        def step_impl(context, count):
            assert len(context.results) == count
    """

    def __init__(self):
        self.steps: Dict[StepType, List[StepMatch]] = {
            StepType.GIVEN: [],
            StepType.WHEN: [],
            StepType.THEN: []
        }
        self._context = None

    def given(self, pattern: str) -> Callable:
        """Decorator for Given steps"""
        return self._register_step(pattern, StepType.GIVEN)

    def when(self, pattern: str) -> Callable:
        """Decorator for When steps"""
        return self._register_step(pattern, StepType.WHEN)

    def then(self, pattern: str) -> Callable:
        """Decorator for Then steps"""
        return self._register_step(pattern, StepType.THEN)

    def _register_step(self, pattern: str, step_type: StepType) -> Callable:
        """Register a step definition"""
        def decorator(func: Callable) -> Callable:
            # Convert pattern to regex
            regex_pattern = self._pattern_to_regex(pattern)
            compiled = re.compile(regex_pattern)

            # Check if function is async
            is_async = inspect.iscoroutinefunction(func)

            # Create step match
            step_match = StepMatch(
                pattern=compiled,
                func=func,
                step_type=step_type,
                is_async=is_async
            )

            # Register step
            self.steps[step_type].append(step_match)

            return func
        return decorator

    def _pattern_to_regex(self, pattern: str) -> str:
        """
        Convert step pattern to regex.

        Supports:
        - {name} -> capture any word
        - {name:int} -> capture integer
        - {name:float} -> capture float
        - "{name}" -> capture quoted string with named group
        - (?:optional)? -> optional text
        """
        # First, handle quoted string parameters before escaping
        # This captures patterns like "{name}" and converts them to named groups
        pattern = re.sub(
            r'\"\{(\w+)\}\"',
            r'__QUOTED_PARAM_\1__',
            pattern
        )

        # Escape special regex characters
        escaped = re.escape(pattern)

        # Replace escaped parameter patterns with regex groups
        # {name:int}
        escaped = re.sub(
            r'\\{(\w+):int\\}',
            r'(?P<\1>-?\\d+)',
            escaped
        )

        # {name:float}
        escaped = re.sub(
            r'\\{(\w+):float\\}',
            r'(?P<\1>-?\\d+\\.?\\d*)',
            escaped
        )

        # {name:str} or {name} - match word characters
        escaped = re.sub(
            r'\\{(\w+)(?::str)?\\}',
            r'(?P<\1>\\w+)',
            escaped
        )

        # Restore quoted parameters as named groups capturing anything between quotes
        escaped = re.sub(
            r'__QUOTED_PARAM_(\w+)__',
            r'"(?P<\1>[^"]*)"',
            escaped
        )

        # Optional groups: (?:text)?
        escaped = re.sub(
            r'\\\(\\\?:([^)]+)\\\)\\\?',
            r'(?:\1)?',
            escaped
        )

        return f'^{escaped}$'

    def find_step(self, step_text: str, step_type: StepType) -> Optional[StepMatch]:
        """
        Find matching step definition for given text.

        Args:
            step_text: The step text to match
            step_type: The step type (given/when/then)

        Returns:
            StepMatch if found, None otherwise
        """
        for step_match in self.steps[step_type]:
            match = step_match.pattern.match(step_text)
            if match:
                # Extract parameters
                params = match.groupdict()

                # Convert typed parameters
                for key, value in params.items():
                    # Try to convert to int
                    try:
                        params[key] = int(value)
                        continue
                    except (ValueError, TypeError):
                        pass

                    # Try to convert to float
                    try:
                        params[key] = float(value)
                        continue
                    except (ValueError, TypeError):
                        pass

                # Create new StepMatch with parameters
                return StepMatch(
                    pattern=step_match.pattern,
                    func=step_match.func,
                    step_type=step_match.step_type,
                    is_async=step_match.is_async,
                    parameters=params
                )

        return None

    def execute_step(
        self,
        step_text: str,
        step_type: StepType,
        context: Context,
        data_table: Optional[DataTable] = None,
        doc_string: Optional[str] = None
    ) -> Any:
        """
        Execute a step.

        Args:
            step_text: The step text
            step_type: The step type
            context: The context object
            data_table: Optional data table
            doc_string: Optional doc string

        Returns:
            Result from step function

        Raises:
            ValueError: If step not found
            AssertionError: If assertion fails
        """
        step_match = self.find_step(step_text, step_type)
        if not step_match:
            raise ValueError(f"No step definition found for: {step_text}")

        # Prepare arguments
        args = [context]

        # Add positional parameters in order they appear in function signature
        sig = inspect.signature(step_match.func)
        param_names = list(sig.parameters.keys())[1:]  # Skip 'context'

        for param_name in param_names:
            if param_name in step_match.parameters:
                args.append(step_match.parameters[param_name])
            elif param_name == 'data_table' and data_table:
                args.append(data_table)
            elif param_name == 'doc_string' and doc_string:
                args.append(doc_string)

        # Execute step
        if step_match.is_async:
            return asyncio.run(step_match.func(*args))
        else:
            return step_match.func(*args)

    async def execute_step_async(
        self,
        step_text: str,
        step_type: StepType,
        context: Context,
        data_table: Optional[DataTable] = None,
        doc_string: Optional[str] = None
    ) -> Any:
        """Execute a step asynchronously"""
        step_match = self.find_step(step_text, step_type)
        if not step_match:
            raise ValueError(f"No step definition found for: {step_text}")

        # Prepare arguments
        args = [context]
        sig = inspect.signature(step_match.func)
        param_names = list(sig.parameters.keys())[1:]

        for param_name in param_names:
            if param_name in step_match.parameters:
                args.append(step_match.parameters[param_name])
            elif param_name == 'data_table' and data_table:
                args.append(data_table)
            elif param_name == 'doc_string' and doc_string:
                args.append(doc_string)

        # Execute step
        if step_match.is_async:
            return await step_match.func(*args)
        else:
            return step_match.func(*args)

    def reset(self):
        """Reset all registered steps"""
        self.steps = {
            StepType.GIVEN: [],
            StepType.WHEN: [],
            StepType.THEN: []
        }


# Assertion helpers
class AssertionHelpers:
    """Helper functions for common assertions in step definitions"""

    @staticmethod
    def assert_status_code(response: httpx.Response, expected: int):
        """Assert HTTP status code"""
        assert response.status_code == expected, \
            f"Expected status {expected}, got {response.status_code}"

    @staticmethod
    def assert_json_contains(response: httpx.Response, key: str, value: Any = None):
        """Assert JSON response contains key (and optionally value)"""
        data = response.json()
        assert key in data, f"Key '{key}' not found in response"
        if value is not None:
            assert data[key] == value, \
                f"Expected {key}={value}, got {data[key]}"

    @staticmethod
    def assert_response_time(response: httpx.Response, max_ms: float):
        """Assert response time is below threshold"""
        elapsed_ms = response.elapsed.total_seconds() * 1000
        assert elapsed_ms <= max_ms, \
            f"Response took {elapsed_ms:.2f}ms, expected <= {max_ms}ms"

    @staticmethod
    def assert_contains(text: str, substring: str):
        """Assert text contains substring"""
        assert substring in text, \
            f"Expected '{substring}' in text, but not found"

    @staticmethod
    def assert_equals(actual: Any, expected: Any, message: str = None):
        """Assert equality with custom message"""
        if message:
            assert actual == expected, message
        else:
            assert actual == expected, \
                f"Expected {expected}, got {actual}"


# Global instance for convenient access
default_registry = StepRegistry()
given = default_registry.given
when = default_registry.when
then = default_registry.then
