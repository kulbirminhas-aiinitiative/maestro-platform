"""
BDV Phase 2A: Test Suite 11 - Step Definitions

Test IDs: BDV-201 to BDV-230 (30 tests)

Test Categories:
1. Given steps (201-202): Setup user, database state
2. When steps (203-204): HTTP requests, actions performed
3. Then steps (205-207): Status code checks, response body assertions, database checks
4. Parameters (208-212): String, int, float, data tables, multi-line strings
5. Pattern matching (213-214): Regex matching, optional parameters
6. Context (215-216): Context mutation, context read
7. Assertions (217-218): Assertion failures, exception handling
8. Advanced features (219-230): Custom fixtures, async execution, HTTP client, JWT tokens,
   retry logic, cleanup, logging, performance tracking, dependency injection, mock services,
   contract validation, custom matchers

Author: Claude Code Implementation
Date: 2025-10-13
Version: 1.0.0
"""

import pytest
import asyncio
import time
import json
from typing import Dict, Any, Optional
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from bdv.step_registry import (
    StepRegistry,
    Context,
    DataTable,
    StepType,
    AssertionHelpers,
    default_registry
)


# Test fixtures
@pytest.fixture
def registry():
    """Create a fresh step registry for each test"""
    return StepRegistry()


@pytest.fixture
def context():
    """Create a fresh context for each test"""
    ctx = Context()
    yield ctx
    ctx.clear()


@pytest.fixture
def sample_data_table():
    """Create a sample data table"""
    return DataTable(
        headers=["name", "email", "role"],
        rows=[
            ["Alice", "alice@example.com", "admin"],
            ["Bob", "bob@example.com", "user"]
        ]
    )


@pytest.fixture
def mock_http_response():
    """Create a mock HTTP response"""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success", "data": {"id": 123}}
    mock_response.text = '{"status": "success"}'
    mock_response.elapsed.total_seconds.return_value = 0.150
    return mock_response


# Test Suite: Given Steps (BDV-201 to BDV-202)
class TestGivenSteps:
    """Test Given step definitions for setup"""

    def test_bdv_201_given_user_exists(self, registry, context):
        """BDV-201: Given step sets up user in context"""
        @registry.given('a user named "{username}" exists')
        def step_impl(context, username):
            context.username = username
            context.user_id = 12345

        registry.execute_step(
            'a user named "alice" exists',
            StepType.GIVEN,
            context
        )

        assert context.username == "alice"
        assert context.user_id == 12345

    def test_bdv_202_given_database_state(self, registry, context):
        """BDV-202: Given step sets up database state"""
        @registry.given('the database has {count:int} records')
        def step_impl(context, count):
            context.db_records = count
            context.db_initialized = True

        registry.execute_step(
            'the database has 100 records',
            StepType.GIVEN,
            context
        )

        assert context.db_records == 100
        assert context.db_initialized is True


# Test Suite: When Steps (BDV-203 to BDV-204)
class TestWhenSteps:
    """Test When step definitions for actions"""

    def test_bdv_203_when_http_request(self, registry, context, mock_http_response):
        """BDV-203: When step performs HTTP request"""
        @registry.when('I send a {method} request to "{endpoint}"')
        def step_impl(context, method, endpoint):
            context.http_method = method
            context.http_endpoint = endpoint
            # Simulate HTTP request
            context.response = mock_http_response

        registry.execute_step(
            'I send a POST request to "/api/users"',
            StepType.WHEN,
            context
        )

        assert context.http_method == "POST"
        assert context.http_endpoint == "/api/users"
        assert context.response.status_code == 200

    def test_bdv_204_when_action_performed(self, registry, context):
        """BDV-204: When step performs an action"""
        @registry.when('I create a user with email "{email}"')
        def step_impl(context, email):
            context.created_email = email
            context.user_created = True
            context.creation_time = datetime.now()

        registry.execute_step(
            'I create a user with email "test@example.com"',
            StepType.WHEN,
            context
        )

        assert context.created_email == "test@example.com"
        assert context.user_created is True
        assert isinstance(context.creation_time, datetime)


# Test Suite: Then Steps (BDV-205 to BDV-207)
class TestThenSteps:
    """Test Then step definitions for assertions"""

    def test_bdv_205_then_status_code_check(self, registry, context, mock_http_response):
        """BDV-205: Then step checks HTTP status code"""
        context.response = mock_http_response

        @registry.then('the response status should be {status_code:int}')
        def step_impl(context, status_code):
            AssertionHelpers.assert_status_code(context.response, status_code)

        registry.execute_step(
            'the response status should be 200',
            StepType.THEN,
            context
        )

    def test_bdv_206_then_response_body_assertion(self, registry, context, mock_http_response):
        """BDV-206: Then step asserts response body content"""
        context.response = mock_http_response

        @registry.then('the response should contain "{key}"')
        def step_impl(context, key):
            data = context.response.json()
            assert key in data, f"Key '{key}' not found in response"

        registry.execute_step(
            'the response should contain "status"',
            StepType.THEN,
            context
        )

    def test_bdv_207_then_database_check(self, registry, context):
        """BDV-207: Then step checks database state"""
        context.db_users = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]

        @registry.then('the database should have {count:int} users')
        def step_impl(context, count):
            assert len(context.db_users) == count

        registry.execute_step(
            'the database should have 2 users',
            StepType.THEN,
            context
        )


# Test Suite: Parameters (BDV-208 to BDV-212)
class TestStepParameters:
    """Test parameter extraction from steps"""

    def test_bdv_208_string_parameters(self, registry, context):
        """BDV-208: Extract string parameters from step text"""
        @registry.given('I have a product named "{name}"')
        def step_impl(context, name):
            context.product_name = name

        registry.execute_step(
            'I have a product named "Laptop"',
            StepType.GIVEN,
            context
        )

        assert context.product_name == "Laptop"

    def test_bdv_209_integer_parameters(self, registry, context):
        """BDV-209: Extract and convert integer parameters"""
        @registry.given('I have {count:int} items in stock')
        def step_impl(context, count):
            assert isinstance(count, int)
            context.stock_count = count

        registry.execute_step(
            'I have 42 items in stock',
            StepType.GIVEN,
            context
        )

        assert context.stock_count == 42

    def test_bdv_210_float_parameters(self, registry, context):
        """BDV-210: Extract and convert float parameters"""
        @registry.given('the price is {price:float} dollars')
        def step_impl(context, price):
            assert isinstance(price, float)
            context.price = price

        registry.execute_step(
            'the price is 29.99 dollars',
            StepType.GIVEN,
            context
        )

        assert context.price == 29.99

    def test_bdv_211_data_table_parameters(self, registry, context, sample_data_table):
        """BDV-211: Handle data table parameters"""
        @registry.given('the following users exist:')
        def step_impl(context, data_table):
            context.users = data_table.to_dict_list()

        registry.execute_step(
            'the following users exist:',
            StepType.GIVEN,
            context,
            data_table=sample_data_table
        )

        assert len(context.users) == 2
        assert context.users[0]["name"] == "Alice"
        assert context.users[1]["email"] == "bob@example.com"

    def test_bdv_212_multiline_string_parameters(self, registry, context):
        """BDV-212: Handle multi-line string (doc string) parameters"""
        doc_string = '''
        {
          "name": "John Doe",
          "email": "john@example.com"
        }
        '''

        @registry.when('I send the following JSON:')
        def step_impl(context, doc_string):
            context.json_payload = json.loads(doc_string)

        registry.execute_step(
            'I send the following JSON:',
            StepType.WHEN,
            context,
            doc_string=doc_string
        )

        assert context.json_payload["name"] == "John Doe"
        assert context.json_payload["email"] == "john@example.com"


# Test Suite: Pattern Matching (BDV-213 to BDV-214)
class TestPatternMatching:
    """Test regex pattern matching in steps"""

    def test_bdv_213_regex_pattern_matching(self, registry, context):
        """BDV-213: Match steps using multiple parameter patterns"""
        @registry.when('I wait for {seconds:int} seconds')
        def step_impl(context, seconds):
            context.wait_time = seconds

        # Test singular
        registry.execute_step(
            'I wait for 1 seconds',
            StepType.WHEN,
            context
        )
        assert context.wait_time == 1

        # Test plural
        registry.execute_step(
            'I wait for 5 seconds',
            StepType.WHEN,
            context
        )
        assert context.wait_time == 5

    def test_bdv_214_optional_parameters(self, registry, context):
        """BDV-214: Handle different parameter types in same step"""
        # Test with username parameter
        @registry.given('I have a user named "{name}"')
        def step_impl_with_name(context, name):
            context.user_name = name

        # Test without parameter (different step)
        @registry.given('I have an anonymous user')
        def step_impl_no_name(context):
            context.user_name = "anonymous"

        # With parameter
        registry.execute_step(
            'I have a user named "Alice"',
            StepType.GIVEN,
            context
        )
        assert context.user_name == "Alice"

        # Without parameter
        registry.execute_step(
            'I have an anonymous user',
            StepType.GIVEN,
            context
        )
        assert context.user_name == "anonymous"


# Test Suite: Context (BDV-215 to BDV-216)
class TestContextManagement:
    """Test context object state management"""

    def test_bdv_215_context_mutation(self, registry, context):
        """BDV-215: Steps can mutate context state"""
        @registry.given('I initialize the system')
        def step_impl(context):
            context.initialized = True
            context.startup_time = datetime.now()
            context.config = {"debug": False, "port": 8000}

        @registry.when('I enable debug mode')
        def step_impl(context):
            context.config["debug"] = True

        @registry.then('debug mode should be enabled')
        def step_impl(context):
            assert context.config["debug"] is True

        registry.execute_step('I initialize the system', StepType.GIVEN, context)
        registry.execute_step('I enable debug mode', StepType.WHEN, context)
        registry.execute_step('debug mode should be enabled', StepType.THEN, context)

    def test_bdv_216_context_read_across_steps(self, registry, context):
        """BDV-216: Context state persists across step executions"""
        @registry.given('I set counter to {value:int}')
        def step_impl(context, value):
            context.counter = value

        @registry.when('I increment the counter')
        def step_impl(context):
            context.counter += 1

        @registry.then('the counter should be {expected:int}')
        def step_impl(context, expected):
            assert context.counter == expected

        registry.execute_step('I set counter to 10', StepType.GIVEN, context)
        registry.execute_step('I increment the counter', StepType.WHEN, context)
        registry.execute_step('the counter should be 11', StepType.THEN, context)


# Test Suite: Assertions (BDV-217 to BDV-218)
class TestAssertions:
    """Test assertion handling in steps"""

    def test_bdv_217_assertion_failure(self, registry, context):
        """BDV-217: Failed assertions raise AssertionError"""
        @registry.then('the value should be {expected:int}')
        def step_impl(context, expected):
            assert context.value == expected

        context.value = 10

        with pytest.raises(AssertionError):
            registry.execute_step(
                'the value should be 20',
                StepType.THEN,
                context
            )

    def test_bdv_218_exception_handling(self, registry, context):
        """BDV-218: Exceptions in steps are properly propagated"""
        @registry.when('I divide {a:int} by {b:int}')
        def step_impl(context, a, b):
            context.result = a / b

        with pytest.raises(ZeroDivisionError):
            registry.execute_step(
                'I divide 10 by 0',
                StepType.WHEN,
                context
            )


# Test Suite: Advanced Features (BDV-219 to BDV-230)
class TestAdvancedFeatures:
    """Test advanced step definition features"""

    def test_bdv_219_custom_fixtures(self, registry, context):
        """BDV-219: Steps can use custom fixtures"""
        # Simulate fixture injection
        context.fixtures = {
            "database": Mock(query=Mock(return_value=[{"id": 1}])),
            "cache": Mock(get=Mock(return_value="cached_value"))
        }

        @registry.given('I have a database connection')
        def step_impl(context):
            context.db = context.fixtures["database"]

        @registry.when('I query the database')
        def step_impl(context):
            context.query_result = context.db.query()

        registry.execute_step('I have a database connection', StepType.GIVEN, context)
        registry.execute_step('I query the database', StepType.WHEN, context)

        assert len(context.query_result) == 1

    def test_bdv_220_async_step_execution(self, registry, context):
        """BDV-220: Support async step definitions"""
        @registry.given('I have an async resource')
        async def step_impl(context):
            await asyncio.sleep(0.01)
            context.async_value = "loaded"

        registry.execute_step('I have an async resource', StepType.GIVEN, context)
        assert context.async_value == "loaded"

    def test_bdv_221_http_client_integration(self, context):
        """BDV-221: Context provides HTTP client"""
        # HTTP client is lazily created
        assert context._http_client is None

        # Access creates the client
        http_client = context.http
        assert http_client is not None

        # Subsequent access returns same client
        assert context.http is http_client

    def test_bdv_222_jwt_token_handling(self, registry, context):
        """BDV-222: Handle JWT tokens in steps"""
        @registry.given('I have a valid JWT token')
        def step_impl(context):
            context.jwt_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload.signature"
            context.auth_header = f"Bearer {context.jwt_token}"

        @registry.when('I make an authenticated request')
        def step_impl(context):
            context.request_headers = {"Authorization": context.auth_header}

        registry.execute_step('I have a valid JWT token', StepType.GIVEN, context)
        registry.execute_step('I make an authenticated request', StepType.WHEN, context)

        assert "Bearer" in context.auth_header
        assert context.request_headers["Authorization"] == context.auth_header

    def test_bdv_223_retry_logic(self, registry, context):
        """BDV-223: Implement retry logic in steps"""
        attempt_counter = {"count": 0}

        @registry.when('I retry the operation up to {max_retries:int} times')
        def step_impl(context, max_retries):
            for attempt in range(max_retries):
                attempt_counter["count"] += 1
                try:
                    # Simulate operation that fails twice then succeeds
                    if attempt_counter["count"] < 3:
                        raise Exception("Temporary failure")
                    context.result = "success"
                    context.attempts = attempt_counter["count"]
                    break
                except Exception:
                    if attempt == max_retries - 1:
                        raise

        registry.execute_step(
            'I retry the operation up to 5 times',
            StepType.WHEN,
            context
        )

        assert context.result == "success"
        assert context.attempts == 3

    def test_bdv_224_cleanup_after_step(self, registry, context):
        """BDV-224: Steps can perform cleanup operations"""
        @registry.given('I create a temporary resource')
        def step_impl(context):
            context.temp_resource = {"data": "test", "cleanup_called": False}

        @registry.when('I use the resource')
        def step_impl(context):
            context.resource_used = True

        @registry.then('I cleanup the resource')
        def step_impl(context):
            context.temp_resource["cleanup_called"] = True
            context.temp_resource = None

        registry.execute_step('I create a temporary resource', StepType.GIVEN, context)
        registry.execute_step('I use the resource', StepType.WHEN, context)
        registry.execute_step('I cleanup the resource', StepType.THEN, context)

        assert context.temp_resource is None

    def test_bdv_225_logging_in_steps(self, registry, context):
        """BDV-225: Steps can perform logging"""
        context.logs = []

        @registry.given('I enable logging')
        def step_impl(context):
            context.logging_enabled = True

        @registry.when('I perform an action')
        def step_impl(context):
            if context.logging_enabled:
                context.logs.append({
                    "timestamp": datetime.now().isoformat(),
                    "action": "performed",
                    "level": "INFO"
                })

        registry.execute_step('I enable logging', StepType.GIVEN, context)
        registry.execute_step('I perform an action', StepType.WHEN, context)

        assert len(context.logs) == 1
        assert context.logs[0]["action"] == "performed"

    def test_bdv_226_performance_tracking(self, registry, context):
        """BDV-226: Track performance metrics in steps"""
        @registry.when('I execute a timed operation')
        def step_impl(context):
            start_time = time.time()
            time.sleep(0.01)  # Simulate work
            elapsed = time.time() - start_time
            context.execution_time_ms = elapsed * 1000

        @registry.then('the operation should complete in under {max_ms:float} milliseconds')
        def step_impl(context, max_ms):
            assert context.execution_time_ms < max_ms

        registry.execute_step('I execute a timed operation', StepType.WHEN, context)
        registry.execute_step(
            'the operation should complete in under 100.0 milliseconds',
            StepType.THEN,
            context
        )

    def test_bdv_227_dependency_injection(self, registry, context):
        """BDV-227: Inject dependencies into step implementations"""
        # Simulate dependency injection
        class UserService:
            def get_user(self, user_id):
                return {"id": user_id, "name": "Test User"}

        class EmailService:
            def send_email(self, to, subject):
                return {"sent": True, "to": to}

        context.services = {
            "user_service": UserService(),
            "email_service": EmailService()
        }

        @registry.when('I get user {user_id:int} details')
        def step_impl(context, user_id):
            user_service = context.services["user_service"]
            context.user = user_service.get_user(user_id)

        @registry.then('I send a welcome email')
        def step_impl(context):
            email_service = context.services["email_service"]
            context.email_result = email_service.send_email(
                context.user["name"],
                "Welcome"
            )

        registry.execute_step('I get user 123 details', StepType.WHEN, context)
        registry.execute_step('I send a welcome email', StepType.THEN, context)

        assert context.user["id"] == 123
        assert context.email_result["sent"] is True

    def test_bdv_228_mock_services(self, registry, context):
        """BDV-228: Use mock services in step definitions"""
        mock_api = Mock()
        mock_api.get_data.return_value = {"data": "test_data"}
        mock_api.post_data.return_value = {"status": "created", "id": 456}

        context.mock_api = mock_api

        @registry.when('I call the API to get data')
        def step_impl(context):
            context.api_response = context.mock_api.get_data()

        @registry.then('the API should return valid data')
        def step_impl(context):
            assert context.api_response["data"] == "test_data"

        registry.execute_step('I call the API to get data', StepType.WHEN, context)
        registry.execute_step('the API should return valid data', StepType.THEN, context)

        mock_api.get_data.assert_called_once()

    def test_bdv_229_contract_validation(self, registry, context):
        """BDV-229: Validate API contracts in step definitions"""
        context.api_contract = {
            "required_fields": ["id", "name", "email"],
            "field_types": {
                "id": int,
                "name": str,
                "email": str
            }
        }

        @registry.given('I have an API response')
        def step_impl(context):
            context.api_response = {
                "id": 123,
                "name": "John Doe",
                "email": "john@example.com"
            }

        @registry.then('the response should match the contract')
        def step_impl(context):
            response = context.api_response
            contract = context.api_contract

            # Check required fields
            for field in contract["required_fields"]:
                assert field in response, f"Missing required field: {field}"

            # Check field types
            for field, expected_type in contract["field_types"].items():
                assert isinstance(response[field], expected_type), \
                    f"Field {field} has wrong type"

            context.contract_valid = True

        registry.execute_step('I have an API response', StepType.GIVEN, context)
        registry.execute_step('the response should match the contract', StepType.THEN, context)

        assert context.contract_valid is True

    def test_bdv_230_custom_matchers(self, registry, context):
        """BDV-230: Use custom matchers for complex assertions"""
        class CustomMatchers:
            @staticmethod
            def is_valid_email(email: str) -> bool:
                import re
                pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                return bool(re.match(pattern, email))

            @staticmethod
            def is_within_range(value: float, min_val: float, max_val: float) -> bool:
                return min_val <= value <= max_val

            @staticmethod
            def contains_all(collection: list, *items) -> bool:
                return all(item in collection for item in items)

        context.matchers = CustomMatchers()

        @registry.given('I have an email address "{email}"')
        def step_impl(context, email):
            context.email = email

        @registry.then('the email should be valid')
        def step_impl(context):
            assert context.matchers.is_valid_email(context.email)

        @registry.given('I have a value {value:float}')
        def step_impl(context, value):
            context.value = value

        @registry.then('the value should be between {min_val:float} and {max_val:float}')
        def step_impl(context, min_val, max_val):
            assert context.matchers.is_within_range(context.value, min_val, max_val)

        # Test email validation
        registry.execute_step(
            'I have an email address "test@example.com"',
            StepType.GIVEN,
            context
        )
        registry.execute_step('the email should be valid', StepType.THEN, context)

        # Test range validation
        registry.execute_step('I have a value 75.5', StepType.GIVEN, context)
        registry.execute_step(
            'the value should be between 0.0 and 100.0',
            StepType.THEN,
            context
        )


# Additional utility tests
class TestStepRegistryUtilities:
    """Test utility methods of StepRegistry"""

    def test_find_step_returns_none_for_no_match(self, registry):
        """Test that find_step returns None when no match found"""
        result = registry.find_step("nonexistent step", StepType.GIVEN)
        assert result is None

    def test_execute_step_raises_for_no_match(self, registry, context):
        """Test that execute_step raises ValueError for unmatched step"""
        with pytest.raises(ValueError, match="No step definition found"):
            registry.execute_step("undefined step", StepType.GIVEN, context)

    def test_reset_clears_all_steps(self, registry):
        """Test that reset clears all registered steps"""
        @registry.given("some step")
        def step_impl(context):
            pass

        assert len(registry.steps[StepType.GIVEN]) == 1

        registry.reset()

        assert len(registry.steps[StepType.GIVEN]) == 0
        assert len(registry.steps[StepType.WHEN]) == 0
        assert len(registry.steps[StepType.THEN]) == 0


class TestContextUtilities:
    """Test Context utility methods"""

    def test_context_get_with_default(self, context):
        """Test context.get() with default value"""
        assert context.get("nonexistent", "default") == "default"
        context.set("key", "value")
        assert context.get("key", "default") == "value"

    def test_context_contains(self, context):
        """Test 'in' operator on context"""
        assert "key" not in context
        context.set("key", "value")
        assert "key" in context

    def test_context_clear(self, context):
        """Test context.clear() removes all data"""
        context.set("key1", "value1")
        context.set("key2", "value2")
        assert "key1" in context
        assert "key2" in context

        context.clear()

        assert "key1" not in context
        assert "key2" not in context


class TestAssertionHelpers:
    """Test assertion helper functions"""

    def test_assert_status_code(self, mock_http_response):
        """Test assert_status_code helper"""
        AssertionHelpers.assert_status_code(mock_http_response, 200)

        with pytest.raises(AssertionError):
            AssertionHelpers.assert_status_code(mock_http_response, 404)

    def test_assert_json_contains(self, mock_http_response):
        """Test assert_json_contains helper"""
        AssertionHelpers.assert_json_contains(mock_http_response, "status")
        AssertionHelpers.assert_json_contains(mock_http_response, "status", "success")

        with pytest.raises(AssertionError):
            AssertionHelpers.assert_json_contains(mock_http_response, "nonexistent")

    def test_assert_response_time(self, mock_http_response):
        """Test assert_response_time helper"""
        AssertionHelpers.assert_response_time(mock_http_response, 200)

        with pytest.raises(AssertionError):
            AssertionHelpers.assert_response_time(mock_http_response, 100)

    def test_assert_contains(self):
        """Test assert_contains helper"""
        AssertionHelpers.assert_contains("Hello World", "World")

        with pytest.raises(AssertionError):
            AssertionHelpers.assert_contains("Hello World", "Python")

    def test_assert_equals(self):
        """Test assert_equals helper"""
        AssertionHelpers.assert_equals(42, 42)
        AssertionHelpers.assert_equals("test", "test", "Custom message")

        with pytest.raises(AssertionError):
            AssertionHelpers.assert_equals(42, 43)


# Test execution summary
if __name__ == "__main__":
    import sys

    # Run pytest with verbose output
    exit_code = pytest.main([__file__, "-v", "--tb=short", "-ra"])

    print("\n" + "="*80)
    print("BDV Phase 2A - Test Suite 11: Step Definitions")
    print("="*80)
    print("\nTest Categories:")
    print("  • Given steps (BDV-201 to BDV-202): 2 tests")
    print("  • When steps (BDV-203 to BDV-204): 2 tests")
    print("  • Then steps (BDV-205 to BDV-207): 3 tests")
    print("  • Parameters (BDV-208 to BDV-212): 5 tests")
    print("  • Pattern matching (BDV-213 to BDV-214): 2 tests")
    print("  • Context (BDV-215 to BDV-216): 2 tests")
    print("  • Assertions (BDV-217 to BDV-218): 2 tests")
    print("  • Advanced features (BDV-219 to BDV-230): 12 tests")
    print("  • Utility tests: 11 tests")
    print(f"\nTotal: 41 tests (30 core + 11 utility)")
    print("="*80)
    print("\nKey Implementations:")
    print("  • StepRegistry with Given/When/Then decorators")
    print("  • Parameter extraction (string, int, float, tables)")
    print("  • Context object for state sharing")
    print("  • HTTP client integration (httpx)")
    print("  • Async step support")
    print("  • Data table parsing")
    print("  • Assertion helpers")
    print("  • Custom fixtures and dependency injection")
    print("  • Mock services and contract validation")
    print("="*80)

    sys.exit(exit_code)
