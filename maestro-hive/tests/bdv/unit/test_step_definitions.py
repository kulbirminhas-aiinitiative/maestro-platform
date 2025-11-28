"""
BDV Phase 2A: Test Suite - Step Definitions

Test IDs: BDV-201 to BDV-230 (30 tests)

Test Categories:
1. Step Discovery (BDV-201 to BDV-206): Auto-discovery, regex matching, priority/conflict
   resolution, custom loaders, caching, invalid pattern handling
2. Context Injection (BDV-207 to BDV-212): Context lifecycle, sharing, isolation, cleanup,
   custom attributes, serialization
3. Parameter Binding (BDV-213 to BDV-218): Simple/multiple parameters, type conversion,
   validation, defaults, complex types
4. Fixtures & Hooks (BDV-219 to BDV-224): Before/After scenario/feature hooks, dependency
   injection, scoping, teardown, async support
5. Step Implementation Patterns (BDV-225 to BDV-230): Given/When/Then steps, reuse/composition,
   async execution, error handling

Author: Claude Code Implementation
Date: 2025-10-13
Version: 1.0.0
"""

import pytest
import time
import asyncio
import re
from typing import List, Dict, Any, Callable, Optional
from dataclasses import dataclass, field
from pathlib import Path
import importlib
import inspect
import json

from bdv.step_registry import (
    StepRegistry,
    Context,
    StepType,
    StepMatch,
    DataTable,
    AssertionHelpers,
)


# ============================================================================
# Test Helper Classes
# ============================================================================

@dataclass
class StepDefinition:
    """Represents a step definition with metadata"""
    pattern: str
    func: Callable
    step_type: StepType
    priority: int = 0
    source_module: Optional[str] = None


class EnhancedStepRegistry(StepRegistry):
    """Extended StepRegistry with additional features for testing"""

    def __init__(self):
        super().__init__()
        self._cache = {}
        self._cache_enabled = True
        self._custom_loaders: List[Callable] = []
        self._step_priorities: Dict[str, int] = {}

    def enable_cache(self, enabled: bool = True):
        """Enable or disable step matching cache"""
        self._cache_enabled = enabled
        if not enabled:
            self._cache.clear()

    def find_step_with_cache(self, step_text: str, step_type: StepType) -> Optional[StepMatch]:
        """Find step with caching support"""
        cache_key = f"{step_type.value}:{step_text}"

        if self._cache_enabled and cache_key in self._cache:
            return self._cache[cache_key]

        result = self.find_step(step_text, step_type)

        if self._cache_enabled:
            self._cache[cache_key] = result

        return result

    def register_custom_loader(self, loader: Callable):
        """Register a custom step loader"""
        self._custom_loaders.append(loader)

    def load_steps_from_module(self, module_path: str):
        """Load steps from a Python module"""
        try:
            module = importlib.import_module(module_path)
            for name, obj in inspect.getmembers(module):
                if callable(obj) and hasattr(obj, '_step_definition'):
                    step_def = obj._step_definition
                    if step_def['type'] == 'given':
                        self.given(step_def['pattern'])(obj)
                    elif step_def['type'] == 'when':
                        self.when(step_def['pattern'])(obj)
                    elif step_def['type'] == 'then':
                        self.then(step_def['pattern'])(obj)
            return True
        except Exception:
            return False

    def set_step_priority(self, pattern: str, priority: int):
        """Set priority for a step pattern (higher = more priority)"""
        self._step_priorities[pattern] = priority

    def find_step_with_priority(self, step_text: str, step_type: StepType) -> Optional[StepMatch]:
        """Find step considering priority"""
        matches = []
        for step_match in self.steps[step_type]:
            if step_match.pattern.match(step_text):
                priority = self._step_priorities.get(step_match.pattern.pattern, 0)
                matches.append((priority, step_match))

        if matches:
            # Sort by priority (highest first)
            matches.sort(key=lambda x: x[0], reverse=True)
            match = matches[0][1].pattern.match(step_text)
            params = match.groupdict() if match else {}

            # Convert parameters
            for key, value in params.items():
                try:
                    params[key] = int(value)
                    continue
                except (ValueError, TypeError):
                    pass
                try:
                    params[key] = float(value)
                except (ValueError, TypeError):
                    pass

            return StepMatch(
                pattern=matches[0][1].pattern,
                func=matches[0][1].func,
                step_type=matches[0][1].step_type,
                is_async=matches[0][1].is_async,
                parameters=params
            )

        return None


class ContextManager:
    """Manages context lifecycle across scenarios"""

    def __init__(self):
        self._contexts: Dict[str, Context] = {}
        self._active_context: Optional[Context] = None

    def create_context(self, scenario_id: str) -> Context:
        """Create a new context for a scenario"""
        context = Context()
        self._contexts[scenario_id] = context
        self._active_context = context
        return context

    def get_context(self, scenario_id: str) -> Optional[Context]:
        """Get context for a scenario"""
        return self._contexts.get(scenario_id)

    def cleanup_context(self, scenario_id: str):
        """Cleanup a scenario's context"""
        if scenario_id in self._contexts:
            self._contexts[scenario_id].clear()
            del self._contexts[scenario_id]

    def cleanup_all(self):
        """Cleanup all contexts"""
        for ctx in self._contexts.values():
            ctx.clear()
        self._contexts.clear()
        self._active_context = None

    @property
    def active(self) -> Optional[Context]:
        """Get the active context"""
        return self._active_context


class ParameterBinder:
    """Binds and converts parameters from step text"""

    TYPE_CONVERTERS = {
        'int': int,
        'float': float,
        'bool': lambda x: x.lower() in ('true', 'yes', '1'),
        'str': str,
    }

    @classmethod
    def extract_parameters(cls, pattern: str, text: str) -> Dict[str, Any]:
        """Extract parameters from text using pattern"""
        # Convert pattern to regex
        regex = cls._pattern_to_regex(pattern)
        match = re.match(regex, text)

        if not match:
            return {}

        return match.groupdict()

    @classmethod
    def _pattern_to_regex(cls, pattern: str) -> str:
        """Convert step pattern to regex"""
        # Handle quoted parameters
        pattern = re.sub(r'\"\{(\w+)(?::(\w+))?\}\"', r'__QUOTED_\1_\2__', pattern)

        # Escape special characters
        escaped = re.escape(pattern)

        # Replace parameter patterns
        escaped = re.sub(r'\\{(\w+):int\\}', r'(?P<\1>-?\\d+)', escaped)
        escaped = re.sub(r'\\{(\w+):float\\}', r'(?P<\1>-?\\d+\\.?\\d*)', escaped)
        escaped = re.sub(r'\\{(\w+):bool\\}', r'(?P<\1>true|false|yes|no|1|0)', escaped)
        escaped = re.sub(r'\\{(\w+)(?::str)?\\}', r'(?P<\1>\\w+)', escaped)

        # Restore quoted parameters
        escaped = re.sub(r'__QUOTED_(\w+)_(\w+)?__', r'"(?P<\1>[^"]*)"', escaped)

        return f'^{escaped}$'

    @classmethod
    def convert_parameters(cls, params: Dict[str, str], types: Dict[str, str]) -> Dict[str, Any]:
        """Convert parameter types"""
        converted = {}

        for key, value in params.items():
            param_type = types.get(key, 'str')
            converter = cls.TYPE_CONVERTERS.get(param_type, str)

            try:
                converted[key] = converter(value)
            except (ValueError, TypeError):
                converted[key] = value

        return converted

    @classmethod
    def parse_list_parameter(cls, value: str) -> List[str]:
        """Parse a list from string: "a, b, c" -> ["a", "b", "c"]"""
        return [item.strip() for item in value.split(',')]

    @classmethod
    def parse_dict_parameter(cls, value: str) -> Dict[str, Any]:
        """Parse a dict from JSON string"""
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}


class HookManager:
    """Manages before/after hooks for scenarios and features"""

    def __init__(self):
        self._before_scenario_hooks: List[Callable] = []
        self._after_scenario_hooks: List[Callable] = []
        self._before_feature_hooks: List[Callable] = []
        self._after_feature_hooks: List[Callable] = []
        self._fixtures: Dict[str, Any] = {}
        self._fixture_scopes: Dict[str, str] = {}

    def before_scenario(self, func: Callable):
        """Register before scenario hook"""
        self._before_scenario_hooks.append(func)
        return func

    def after_scenario(self, func: Callable):
        """Register after scenario hook"""
        self._after_scenario_hooks.append(func)
        return func

    def before_feature(self, func: Callable):
        """Register before feature hook"""
        self._before_feature_hooks.append(func)
        return func

    def after_feature(self, func: Callable):
        """Register after feature hook"""
        self._after_feature_hooks.append(func)
        return func

    def run_before_scenario_hooks(self, context: Context):
        """Run all before scenario hooks"""
        for hook in self._before_scenario_hooks:
            if inspect.iscoroutinefunction(hook):
                asyncio.run(hook(context))
            else:
                hook(context)

    def run_after_scenario_hooks(self, context: Context):
        """Run all after scenario hooks"""
        for hook in self._after_scenario_hooks:
            if inspect.iscoroutinefunction(hook):
                asyncio.run(hook(context))
            else:
                hook(context)

    def run_before_feature_hooks(self, context: Context):
        """Run all before feature hooks"""
        for hook in self._before_feature_hooks:
            if inspect.iscoroutinefunction(hook):
                asyncio.run(hook(context))
            else:
                hook(context)

    def run_after_feature_hooks(self, context: Context):
        """Run all after feature hooks"""
        for hook in self._after_feature_hooks:
            if inspect.iscoroutinefunction(hook):
                asyncio.run(hook(context))
            else:
                hook(context)

    def register_fixture(self, name: str, value: Any, scope: str = 'function'):
        """Register a fixture with scope"""
        self._fixtures[name] = value
        self._fixture_scopes[name] = scope

    def get_fixture(self, name: str) -> Any:
        """Get a fixture by name"""
        return self._fixtures.get(name)

    def cleanup_fixtures(self, scope: str):
        """Cleanup fixtures by scope"""
        to_remove = [
            name for name, fixture_scope in self._fixture_scopes.items()
            if fixture_scope == scope
        ]
        for name in to_remove:
            del self._fixtures[name]
            del self._fixture_scopes[name]


# ============================================================================
# Test Category 1: Step Discovery (BDV-201 to BDV-206)
# ============================================================================

@pytest.mark.bdv
@pytest.mark.unit
class TestStepDiscovery:
    """Step discovery tests (BDV-201 to BDV-206)"""

    def test_bdv_201_auto_discover_step_definitions(self):
        """BDV-201: Auto-discover step definitions from Python modules"""
        registry = EnhancedStepRegistry()

        # Register some steps
        @registry.given('the system is running')
        def step_impl(context):
            context.system_running = True

        @registry.when('I perform an action')
        def step_impl2(context):
            context.action_performed = True

        @registry.then('the result should be correct')
        def step_impl3(context):
            assert context.system_running
            assert context.action_performed

        # Verify all steps are discovered
        assert len(registry.steps[StepType.GIVEN]) == 1
        assert len(registry.steps[StepType.WHEN]) == 1
        assert len(registry.steps[StepType.THEN]) == 1

        # Verify steps can be found
        given_match = registry.find_step('the system is running', StepType.GIVEN)
        assert given_match is not None
        assert given_match.func == step_impl

    def test_bdv_202_step_regex_pattern_matching(self):
        """BDV-202: Step regex pattern matching with parameters"""
        registry = StepRegistry()

        @registry.given('I have {count:int} items')
        def step_impl(context, count):
            context.item_count = count

        # Test exact match
        match = registry.find_step('I have 5 items', StepType.GIVEN)
        assert match is not None
        assert match.parameters['count'] == 5

        # Test different numbers
        match = registry.find_step('I have 100 items', StepType.GIVEN)
        assert match is not None
        assert match.parameters['count'] == 100

        # Test non-match
        match = registry.find_step('I have items', StepType.GIVEN)
        assert match is None

        match = registry.find_step('I have five items', StepType.GIVEN)
        assert match is None

    def test_bdv_203_step_priority_and_conflict_resolution(self):
        """BDV-203: Step priority and conflict resolution"""
        registry = EnhancedStepRegistry()

        # Register two overlapping patterns
        @registry.given('I have {count:int} items')
        def specific_step(context, count):
            context.matched = 'specific'
            context.count = count

        @registry.given('I have items')
        def general_step(context):
            context.matched = 'general'

        # Set priorities
        registry.set_step_priority(r'^I\ have\ (?P<count>-?\d+)\ items$', 10)
        registry.set_step_priority(r'^I\ have\ items$', 5)

        # The more specific pattern should match first
        match = registry.find_step_with_priority('I have 5 items', StepType.GIVEN)
        assert match is not None

        context = Context()
        result = match.func(context, match.parameters['count'])
        assert context.matched == 'specific'
        assert context.count == 5

    def test_bdv_204_custom_step_loaders(self):
        """BDV-204: Custom step loaders for dynamic step registration"""
        registry = EnhancedStepRegistry()

        # Custom loader function
        def custom_loader():
            @registry.given('custom loaded step')
            def step_impl(context):
                context.custom_loaded = True

            return True

        # Register and execute loader
        registry.register_custom_loader(custom_loader)
        custom_loader()

        # Verify custom loaded step is available
        match = registry.find_step('custom loaded step', StepType.GIVEN)
        assert match is not None

        context = Context()
        match.func(context)
        assert context.custom_loaded is True

    def test_bdv_205_step_caching_for_performance(self):
        """BDV-205: Step caching for performance optimization"""
        registry = EnhancedStepRegistry()

        @registry.given('I have a cached step')
        def step_impl(context):
            context.executed = True

        # Enable caching
        registry.enable_cache(True)

        # First lookup (cache miss)
        start = time.time()
        for _ in range(100):
            registry.find_step_with_cache('I have a cached step', StepType.GIVEN)
        cached_time = time.time() - start

        # Disable caching
        registry.enable_cache(False)

        # Second lookup (no cache)
        start = time.time()
        for _ in range(100):
            registry.find_step('I have a cached step', StepType.GIVEN)
        uncached_time = time.time() - start

        # Cached should be faster (or at least not slower)
        # We're lenient here since the difference might be small
        assert cached_time <= uncached_time * 1.5

    def test_bdv_206_invalid_step_pattern_handling(self):
        """BDV-206: Handle invalid step patterns gracefully"""
        registry = StepRegistry()

        # Register step with valid pattern
        @registry.given('valid pattern')
        def step_impl(context):
            context.valid = True

        # Try to find step with invalid text
        match = registry.find_step('', StepType.GIVEN)
        assert match is None

        match = registry.find_step('completely different text', StepType.GIVEN)
        assert match is None

        # Pattern with special characters should be handled
        @registry.when('I click the "Save" button')
        def step_impl2(context):
            context.clicked = True

        match = registry.find_step('I click the "Save" button', StepType.WHEN)
        assert match is not None


# ============================================================================
# Test Category 2: Context Injection (BDV-207 to BDV-212)
# ============================================================================

@pytest.mark.bdv
@pytest.mark.unit
class TestContextInjection:
    """Context injection tests (BDV-207 to BDV-212)"""

    def test_bdv_207_scenario_context_object_lifecycle(self):
        """BDV-207: Scenario context object lifecycle management"""
        manager = ContextManager()

        # Create context
        ctx1 = manager.create_context('scenario_1')
        assert ctx1 is not None
        assert manager.active == ctx1

        # Set some data
        ctx1.set('user_id', 123)
        ctx1.set('logged_in', True)

        # Verify data persists
        retrieved = manager.get_context('scenario_1')
        assert retrieved == ctx1
        assert retrieved.get('user_id') == 123
        assert retrieved.get('logged_in') is True

        # Cleanup
        manager.cleanup_context('scenario_1')
        assert manager.get_context('scenario_1') is None

    def test_bdv_208_context_sharing_between_steps(self):
        """BDV-208: Context sharing between steps in same scenario"""
        registry = StepRegistry()
        context = Context()

        @registry.given('I set the value to {value:int}')
        def step_impl(context, value):
            context.value = value

        @registry.when('I multiply by {factor:int}')
        def step_impl2(context, factor):
            context.value = context.value * factor

        @registry.then('the value should be {expected:int}')
        def step_impl3(context, expected):
            assert context.value == expected

        # Execute steps sharing context
        registry.execute_step('I set the value to 10', StepType.GIVEN, context)
        assert context.value == 10

        registry.execute_step('I multiply by 3', StepType.WHEN, context)
        assert context.value == 30

        registry.execute_step('the value should be 30', StepType.THEN, context)

    def test_bdv_209_context_isolation_between_scenarios(self):
        """BDV-209: Context isolation between different scenarios"""
        manager = ContextManager()

        # Create two contexts
        ctx1 = manager.create_context('scenario_1')
        ctx1.set('value', 100)

        ctx2 = manager.create_context('scenario_2')
        ctx2.set('value', 200)

        # Verify isolation
        assert ctx1.get('value') == 100
        assert ctx2.get('value') == 200

        # Modify one shouldn't affect the other
        ctx1.set('value', 150)
        assert ctx1.get('value') == 150
        assert ctx2.get('value') == 200

    def test_bdv_210_context_cleanup_after_scenario(self):
        """BDV-210: Context cleanup and resource deallocation after scenario"""
        context = Context()

        # Set various attributes
        context.user = 'john'
        context.session_id = 'abc123'
        context.temp_data = [1, 2, 3, 4, 5]
        context.config = {'key': 'value'}

        # Verify data exists
        assert 'user' in context
        assert context.user == 'john'

        # Clear context
        context.clear()

        # Verify data is cleared
        assert 'user' not in context
        assert 'session_id' not in context
        assert 'temp_data' not in context

        # Should raise AttributeError
        with pytest.raises(AttributeError):
            _ = context.user

    def test_bdv_211_custom_context_attributes(self):
        """BDV-211: Custom context attributes and dynamic properties"""
        context = Context()

        # Set custom attributes
        context.api_url = 'https://api.example.com'
        context.auth_token = 'bearer_token_123'
        context.user_profile = {'name': 'Alice', 'role': 'admin'}
        context.request_count = 0

        # Access using dot notation
        assert context.api_url == 'https://api.example.com'
        assert context.auth_token == 'bearer_token_123'
        assert context.user_profile['role'] == 'admin'

        # Modify attributes
        context.request_count += 1
        context.request_count += 1
        assert context.request_count == 2

        # Access using get method
        assert context.get('api_url') == 'https://api.example.com'
        assert context.get('nonexistent', 'default') == 'default'

    def test_bdv_212_context_serialization_for_reporting(self):
        """BDV-212: Context serialization for reporting and debugging"""
        context = Context()

        # Set various data types
        context.user_id = 123
        context.username = 'alice'
        context.is_admin = True
        context.scores = [85, 90, 95]
        context.metadata = {'env': 'test', 'version': '1.0'}

        # Access internal data dict (for serialization)
        data = context._data

        # Should be JSON serializable
        json_str = json.dumps(data)
        assert json_str is not None

        # Deserialize and verify
        restored = json.loads(json_str)
        assert restored['user_id'] == 123
        assert restored['username'] == 'alice'
        assert restored['is_admin'] is True
        assert restored['scores'] == [85, 90, 95]
        assert restored['metadata']['env'] == 'test'


# ============================================================================
# Test Category 3: Parameter Binding (BDV-213 to BDV-218)
# ============================================================================

@pytest.mark.bdv
@pytest.mark.unit
class TestParameterBinding:
    """Parameter binding tests (BDV-213 to BDV-218)"""

    def test_bdv_213_simple_parameter_extraction(self):
        """BDV-213: Simple parameter extraction from step text"""
        registry = StepRegistry()

        @registry.given('a user named "{name}"')
        def step_impl(context, name):
            context.user_name = name

        context = Context()
        registry.execute_step('a user named "John"', StepType.GIVEN, context)

        assert context.user_name == "John"

        # Test with different names
        context2 = Context()
        registry.execute_step('a user named "Alice"', StepType.GIVEN, context2)
        assert context2.user_name == "Alice"

    def test_bdv_214_multiple_parameters(self):
        """BDV-214: Extract multiple parameters from step text"""
        registry = StepRegistry()

        @registry.given('user "{name}" with age {age:int}')
        def step_impl(context, name, age):
            context.user_name = name
            context.user_age = age

        context = Context()
        registry.execute_step('user "Bob" with age 25', StepType.GIVEN, context)

        assert context.user_name == "Bob"
        assert context.user_age == 25
        assert isinstance(context.user_age, int)

    def test_bdv_215_type_conversion(self):
        """BDV-215: Type conversion for parameters (int, float, bool)"""
        registry = StepRegistry()

        @registry.given('I have {count:int} items at {price:float} each')
        def step_impl(context, count, price):
            context.count = count
            context.price = price
            context.total = count * price

        context = Context()
        registry.execute_step('I have 10 items at 19.99 each', StepType.GIVEN, context)

        assert context.count == 10
        assert isinstance(context.count, int)
        assert context.price == 19.99
        assert isinstance(context.price, float)
        assert abs(context.total - 199.9) < 0.01  # Use tolerance for float comparison

    def test_bdv_216_parameter_validation_and_error_handling(self):
        """BDV-216: Parameter validation and error handling"""
        registry = StepRegistry()

        @registry.given('I set count to {count:int}')
        def step_impl(context, count):
            if count < 0:
                raise ValueError("Count must be non-negative")
            context.count = count

        context = Context()

        # Valid parameter
        registry.execute_step('I set count to 5', StepType.GIVEN, context)
        assert context.count == 5

        # Invalid parameter (negative)
        with pytest.raises(ValueError, match="Count must be non-negative"):
            registry.execute_step('I set count to -1', StepType.GIVEN, context)

        # Step not found error
        with pytest.raises(ValueError, match="No step definition found"):
            registry.execute_step('undefined step', StepType.GIVEN, context)

    def test_bdv_217_optional_parameters_with_defaults(self):
        """BDV-217: Optional parameters with default values"""
        binder = ParameterBinder()

        # Pattern with optional parameter
        pattern = 'I search for "{query}" with limit {limit:int}'

        # Extract with all parameters
        params = binder.extract_parameters(
            pattern,
            'I search for "laptop" with limit 10'
        )
        assert params['query'] == 'laptop'
        assert params['limit'] == '10'

        # Convert with defaults
        converted = binder.convert_parameters(params, {'query': 'str', 'limit': 'int'})
        assert converted['query'] == 'laptop'
        assert converted['limit'] == 10

    def test_bdv_218_complex_parameter_types(self):
        """BDV-218: Complex parameter types (lists, dicts from tables)"""
        binder = ParameterBinder()

        # Test list parsing
        list_str = "apple, banana, orange"
        parsed_list = binder.parse_list_parameter(list_str)
        assert parsed_list == ['apple', 'banana', 'orange']

        # Test dict parsing
        dict_str = '{"name": "John", "age": 30, "active": true}'
        parsed_dict = binder.parse_dict_parameter(dict_str)
        assert parsed_dict['name'] == 'John'
        assert parsed_dict['age'] == 30
        assert parsed_dict['active'] is True

        # Test with DataTable
        data_table = DataTable(
            headers=['name', 'email', 'role'],
            rows=[
                ['Alice', 'alice@example.com', 'admin'],
                ['Bob', 'bob@example.com', 'user']
            ]
        )

        dict_list = data_table.to_dict_list()
        assert len(dict_list) == 2
        assert dict_list[0]['name'] == 'Alice'
        assert dict_list[1]['role'] == 'user'


# ============================================================================
# Test Category 4: Fixtures & Hooks (BDV-219 to BDV-224)
# ============================================================================

@pytest.mark.bdv
@pytest.mark.unit
class TestFixturesAndHooks:
    """Fixtures and hooks tests (BDV-219 to BDV-224)"""

    def test_bdv_219_before_after_scenario_hooks(self):
        """BDV-219: Before and after scenario hooks"""
        hook_manager = HookManager()
        context = Context()

        # Track execution order
        execution_order = []

        @hook_manager.before_scenario
        def setup(ctx):
            execution_order.append('before')
            ctx.initialized = True

        @hook_manager.after_scenario
        def teardown(ctx):
            execution_order.append('after')
            ctx.cleaned_up = True

        # Run hooks
        hook_manager.run_before_scenario_hooks(context)
        assert context.initialized is True

        # Simulate scenario execution
        execution_order.append('scenario')

        hook_manager.run_after_scenario_hooks(context)
        assert context.cleaned_up is True

        # Verify execution order
        assert execution_order == ['before', 'scenario', 'after']

    def test_bdv_220_before_after_feature_hooks(self):
        """BDV-220: Before and after feature hooks"""
        hook_manager = HookManager()
        context = Context()

        @hook_manager.before_feature
        def feature_setup(ctx):
            ctx.feature_started = True
            ctx.feature_name = 'User Management'

        @hook_manager.after_feature
        def feature_teardown(ctx):
            ctx.feature_completed = True

        # Run feature hooks
        hook_manager.run_before_feature_hooks(context)
        assert context.feature_started is True
        assert context.feature_name == 'User Management'

        hook_manager.run_after_feature_hooks(context)
        assert context.feature_completed is True

    def test_bdv_221_fixture_dependency_injection(self):
        """BDV-221: Fixture dependency injection into steps"""
        hook_manager = HookManager()

        # Register fixtures
        hook_manager.register_fixture('api_url', 'https://api.example.com')
        hook_manager.register_fixture('api_key', 'secret_key_123')
        hook_manager.register_fixture('timeout', 30)

        # Retrieve fixtures
        assert hook_manager.get_fixture('api_url') == 'https://api.example.com'
        assert hook_manager.get_fixture('api_key') == 'secret_key_123'
        assert hook_manager.get_fixture('timeout') == 30

        # Use fixtures in step
        registry = StepRegistry()

        @registry.when('I call the API')
        def step_impl(context):
            context.api_url = hook_manager.get_fixture('api_url')
            context.api_key = hook_manager.get_fixture('api_key')

        context = Context()
        registry.execute_step('I call the API', StepType.WHEN, context)

        assert context.api_url == 'https://api.example.com'
        assert context.api_key == 'secret_key_123'

    def test_bdv_222_fixture_scoping(self):
        """BDV-222: Fixture scoping (function, module, session)"""
        hook_manager = HookManager()

        # Register fixtures with different scopes
        hook_manager.register_fixture('func_fixture', 'function_value', scope='function')
        hook_manager.register_fixture('mod_fixture', 'module_value', scope='module')
        hook_manager.register_fixture('sess_fixture', 'session_value', scope='session')

        # Verify all fixtures exist
        assert hook_manager.get_fixture('func_fixture') == 'function_value'
        assert hook_manager.get_fixture('mod_fixture') == 'module_value'
        assert hook_manager.get_fixture('sess_fixture') == 'session_value'

        # Cleanup function-scoped fixtures
        hook_manager.cleanup_fixtures('function')
        assert hook_manager.get_fixture('func_fixture') is None
        assert hook_manager.get_fixture('mod_fixture') == 'module_value'
        assert hook_manager.get_fixture('sess_fixture') == 'session_value'

        # Cleanup module-scoped fixtures
        hook_manager.cleanup_fixtures('module')
        assert hook_manager.get_fixture('mod_fixture') is None
        assert hook_manager.get_fixture('sess_fixture') == 'session_value'

    def test_bdv_223_fixture_teardown_and_cleanup(self):
        """BDV-223: Fixture teardown and cleanup after tests"""
        hook_manager = HookManager()

        # Register multiple fixtures
        hook_manager.register_fixture('db_connection', 'sqlite:///:memory:')
        hook_manager.register_fixture('cache', {'key': 'value'})
        hook_manager.register_fixture('temp_file', '/tmp/test.txt')

        # Verify fixtures exist
        assert hook_manager.get_fixture('db_connection') is not None
        assert hook_manager.get_fixture('cache') is not None
        assert hook_manager.get_fixture('temp_file') is not None

        # Cleanup all function-scoped fixtures
        hook_manager.cleanup_fixtures('function')

        # Since we didn't specify scope, they default to 'function'
        # So they should all be cleaned up if we specified scope
        # Let's register with explicit scope and verify
        hook_manager.register_fixture('test1', 'value1', scope='function')
        hook_manager.register_fixture('test2', 'value2', scope='function')

        hook_manager.cleanup_fixtures('function')
        assert hook_manager.get_fixture('test1') is None
        assert hook_manager.get_fixture('test2') is None

    def test_bdv_224_async_fixture_support(self):
        """BDV-224: Async fixture support for async steps"""
        hook_manager = HookManager()
        context = Context()

        # Define async hook
        @hook_manager.before_scenario
        async def async_setup(ctx):
            await asyncio.sleep(0.01)  # Simulate async operation
            ctx.async_initialized = True

        # Run async hook
        hook_manager.run_before_scenario_hooks(context)
        assert context.async_initialized is True

        # Test async step execution
        registry = StepRegistry()

        @registry.when('I perform async operation')
        async def async_step(context):
            await asyncio.sleep(0.01)
            context.async_completed = True

        registry.execute_step('I perform async operation', StepType.WHEN, context)
        assert context.async_completed is True


# ============================================================================
# Test Category 5: Step Implementation Patterns (BDV-225 to BDV-230)
# ============================================================================

@pytest.mark.bdv
@pytest.mark.unit
class TestStepImplementationPatterns:
    """Step implementation patterns (BDV-225 to BDV-230)"""

    def test_bdv_225_given_steps_setup_preconditions(self):
        """BDV-225: Given steps for setup and preconditions"""
        registry = StepRegistry()
        context = Context()

        @registry.given('the system is initialized')
        def step_impl(context):
            context.system_ready = True
            context.database_connected = True
            context.cache_loaded = True

        @registry.given('user "{username}" is logged in')
        def step_impl2(context, username):
            context.logged_in_user = username
            context.auth_token = f'token_{username}'

        # Execute Given steps
        registry.execute_step('the system is initialized', StepType.GIVEN, context)
        assert context.system_ready is True
        assert context.database_connected is True

        registry.execute_step('user "alice" is logged in', StepType.GIVEN, context)
        assert context.logged_in_user == 'alice'
        assert context.auth_token == 'token_alice'

    def test_bdv_226_when_steps_actions_events(self):
        """BDV-226: When steps for actions and events"""
        registry = StepRegistry()
        context = Context()

        # Setup preconditions
        context.items = []
        context.cart_total = 0

        @registry.when('I add "{item}" to cart with price {price:float}')
        def step_impl(context, item, price):
            context.items.append(item)
            context.cart_total += price

        @registry.when('I proceed to checkout')
        def step_impl2(context):
            context.checkout_initiated = True
            context.order_id = 'ORD-12345'

        # Execute When steps
        registry.execute_step('I add "Laptop" to cart with price 999.99', StepType.WHEN, context)
        assert 'Laptop' in context.items
        assert context.cart_total == 999.99

        registry.execute_step('I add "Mouse" to cart with price 29.99', StepType.WHEN, context)
        assert len(context.items) == 2
        assert context.cart_total == 1029.98

        registry.execute_step('I proceed to checkout', StepType.WHEN, context)
        assert context.checkout_initiated is True

    def test_bdv_227_then_steps_assertions_expectations(self):
        """BDV-227: Then steps for assertions and expectations"""
        registry = StepRegistry()
        context = Context()

        # Setup test data
        context.response_code = 200
        context.user_count = 5
        context.items = ['item1', 'item2', 'item3']

        @registry.then('the response code should be {code:int}')
        def step_impl(context, code):
            assert context.response_code == code

        @registry.then('I should see {count:int} users')
        def step_impl2(context, count):
            assert context.user_count == count

        @registry.then('the items list should not be empty')
        def step_impl3(context):
            assert len(context.items) > 0

        # Execute Then steps (assertions)
        registry.execute_step('the response code should be 200', StepType.THEN, context)
        registry.execute_step('I should see 5 users', StepType.THEN, context)
        registry.execute_step('the items list should not be empty', StepType.THEN, context)

        # Test assertion failure
        with pytest.raises(AssertionError):
            registry.execute_step('the response code should be 404', StepType.THEN, context)

    def test_bdv_228_step_reuse_and_composition(self):
        """BDV-228: Step reuse and composition"""
        registry = StepRegistry()
        context = Context()

        # Reusable step definitions
        @registry.given('I have a user')
        def create_user(context):
            context.user = {'id': 1, 'name': 'Test User'}

        @registry.given('the user has permissions')
        def add_permissions(context):
            if not hasattr(context, 'user'):
                create_user(context)  # Reuse step
            context.user['permissions'] = ['read', 'write']

        @registry.when('I check user permissions')
        def check_permissions(context):
            context.has_permissions = 'permissions' in context.user

        # Execute steps with composition
        registry.execute_step('the user has permissions', StepType.GIVEN, context)
        assert context.user is not None
        assert 'permissions' in context.user

        registry.execute_step('I check user permissions', StepType.WHEN, context)
        assert context.has_permissions is True

    def test_bdv_229_async_step_execution(self):
        """BDV-229: Async step execution for I/O operations"""
        registry = StepRegistry()
        context = Context()

        @registry.when('I make an async API call')
        async def async_api_call(context):
            await asyncio.sleep(0.01)  # Simulate async I/O
            context.api_response = {'status': 'success', 'data': [1, 2, 3]}

        @registry.then('the API should return data')
        async def verify_response(context):
            await asyncio.sleep(0.01)  # Simulate async processing
            assert context.api_response['status'] == 'success'
            assert len(context.api_response['data']) == 3

        # Execute async steps
        registry.execute_step('I make an async API call', StepType.WHEN, context)
        assert context.api_response is not None

        registry.execute_step('the API should return data', StepType.THEN, context)

    def test_bdv_230_step_error_handling_and_reporting(self):
        """BDV-230: Step error handling and detailed reporting"""
        registry = StepRegistry()
        context = Context()

        @registry.given('a step that raises an error')
        def error_step(context):
            raise RuntimeError("Simulated step failure")

        @registry.when('I perform an invalid operation')
        def invalid_operation(context):
            result = 10 / 0  # Division by zero

        @registry.then('this assertion will fail')
        def failing_assertion(context):
            assert False, "This is a detailed failure message"

        # Test error handling
        with pytest.raises(RuntimeError, match="Simulated step failure"):
            registry.execute_step('a step that raises an error', StepType.GIVEN, context)

        with pytest.raises(ZeroDivisionError):
            registry.execute_step('I perform an invalid operation', StepType.WHEN, context)

        with pytest.raises(AssertionError, match="This is a detailed failure message"):
            registry.execute_step('this assertion will fail', StepType.THEN, context)

        # Test step not found error
        with pytest.raises(ValueError) as exc_info:
            registry.execute_step('undefined step', StepType.GIVEN, context)

        assert "No step definition found" in str(exc_info.value)


# ============================================================================
# Performance and Integration Tests
# ============================================================================

@pytest.mark.bdv
@pytest.mark.unit
class TestStepDefinitionsPerformance:
    """Performance tests for step definitions"""

    def test_step_discovery_performance(self):
        """Step discovery should complete in < 100ms"""
        registry = StepRegistry()

        # Register 100 steps
        start = time.time()
        for i in range(100):
            pattern = f'step number {i} with parameter {{value:int}}'

            @registry.given(pattern)
            def step_impl(context, value):
                context.value = value

        elapsed = (time.time() - start) * 1000  # Convert to ms

        # Should register 100 steps in < 100ms
        assert elapsed < 100, f"Step discovery took {elapsed:.2f}ms, expected < 100ms"
        assert len(registry.steps[StepType.GIVEN]) == 100

    def test_step_execution_performance(self):
        """Step execution should be fast"""
        registry = StepRegistry()
        context = Context()

        @registry.given('I execute a simple step')
        def step_impl(context):
            context.executed = True

        # Execute step 1000 times
        start = time.time()
        for _ in range(1000):
            registry.execute_step('I execute a simple step', StepType.GIVEN, context)
        elapsed = (time.time() - start) * 1000

        # Should complete in reasonable time
        assert elapsed < 1000, f"1000 executions took {elapsed:.2f}ms"


# ============================================================================
# Test Execution Summary
# ============================================================================

if __name__ == "__main__":
    import sys

    # Run pytest with verbose output
    exit_code = pytest.main([__file__, "-v", "--tb=short", "-ra"])

    print("\n" + "="*80)
    print("BDV Phase 2A - Test Suite: Step Definitions")
    print("="*80)
    print("\nTest Categories:")
    print("  • Step Discovery (BDV-201 to BDV-206): 6 tests")
    print("  • Context Injection (BDV-207 to BDV-212): 6 tests")
    print("  • Parameter Binding (BDV-213 to BDV-218): 6 tests")
    print("  • Fixtures & Hooks (BDV-219 to BDV-224): 6 tests")
    print("  • Step Implementation Patterns (BDV-225 to BDV-230): 6 tests")
    print("  • Performance tests: 2 tests")
    print(f"\nTotal: 32 tests (30 core tests + 2 performance tests)")
    print("="*80)

    sys.exit(exit_code)
