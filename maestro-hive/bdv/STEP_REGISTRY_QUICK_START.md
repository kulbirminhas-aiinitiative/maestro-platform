# BDV Step Registry - Quick Start Guide

## Overview

The Step Registry provides a decorator-based system for defining Gherkin Given/When/Then steps with automatic parameter extraction, type conversion, and context management.

## Installation

The step registry is already installed in the BDV module. No additional dependencies required beyond the standard requirements.

## Basic Usage

### 1. Create a Registry and Context

```python
from bdv.step_registry import StepRegistry, Context, StepType

registry = StepRegistry()
context = Context()
```

### 2. Define Steps with Decorators

#### Given Steps (Setup)
```python
@registry.given('a user named "{username}" exists')
def step_impl(context, username):
    context.username = username
    context.user_id = 12345
```

#### When Steps (Actions)
```python
@registry.when('I send a {method} request to "{endpoint}"')
def step_impl(context, method, endpoint):
    response = context.http.get(endpoint)
    context.response = response
```

#### Then Steps (Assertions)
```python
@registry.then('the response status should be {status:int}')
def step_impl(context, status):
    assert context.response.status_code == status
```

### 3. Execute Steps

```python
registry.execute_step(
    'a user named "alice" exists',
    StepType.GIVEN,
    context
)

registry.execute_step(
    'I send a GET request to "/api/users"',
    StepType.WHEN,
    context
)

registry.execute_step(
    'the response status should be 200',
    StepType.THEN,
    context
)
```

## Parameter Types

### String Parameters (Quoted)
```python
@registry.given('I have a product named "{name}"')
def step_impl(context, name):
    context.product = name

# Matches: I have a product named "Laptop"
```

### Integer Parameters
```python
@registry.given('I have {count:int} items')
def step_impl(context, count):
    # count is automatically converted to int
    context.items = count

# Matches: I have 42 items
```

### Float Parameters
```python
@registry.given('the price is {price:float} dollars')
def step_impl(context, price):
    # price is automatically converted to float
    context.price = price

# Matches: the price is 29.99 dollars
```

### Word Parameters
```python
@registry.when('I select {category} from the menu')
def step_impl(context, category):
    context.category = category

# Matches: I select electronics from the menu
```

### Multiple Parameters
```python
@registry.when('I add {quantity:int} of "{product}" to cart')
def step_impl(context, quantity, product):
    context.cart.add(product, quantity)

# Matches: I add 3 of "Laptop" to cart
```

## Data Tables

```python
@registry.given('the following users exist:')
def step_impl(context, data_table):
    # Convert to list of dictionaries
    users = data_table.to_dict_list()
    context.users = users

# Execute with data table
from bdv.step_registry import DataTable

table = DataTable(
    headers=["name", "email", "role"],
    rows=[
        ["Alice", "alice@example.com", "admin"],
        ["Bob", "bob@example.com", "user"]
    ]
)

registry.execute_step(
    'the following users exist:',
    StepType.GIVEN,
    context,
    data_table=table
)
```

## Doc Strings (Multi-line Text)

```python
@registry.when('I send the following JSON:')
def step_impl(context, doc_string):
    import json
    context.payload = json.loads(doc_string)

# Execute with doc string
doc_string = '''
{
  "name": "John Doe",
  "email": "john@example.com"
}
'''

registry.execute_step(
    'I send the following JSON:',
    StepType.WHEN,
    context,
    doc_string=doc_string
)
```

## Async Steps

```python
@registry.given('I have an async resource')
async def step_impl(context):
    import asyncio
    await asyncio.sleep(0.1)
    context.resource = "loaded"

# Execute (automatically handles async)
registry.execute_step(
    'I have an async resource',
    StepType.GIVEN,
    context
)
```

## Context Management

### Setting Values
```python
@registry.given('I initialize the system')
def step_impl(context):
    context.initialized = True
    context.config = {"debug": False}
```

### Reading Values
```python
@registry.when('I enable debug mode')
def step_impl(context):
    context.config["debug"] = True
```

### Using get/set Methods
```python
@registry.then('the system should be initialized')
def step_impl(context):
    assert context.get("initialized", False) is True
    context.set("verified", True)
```

## HTTP Client

```python
@registry.when('I make a GET request to "{url}"')
def step_impl(context, url):
    # HTTP client is automatically created
    response = context.http.get(url)
    context.response = response

# Async version
@registry.when('I make an async request')
async def step_impl(context):
    response = await context.async_http.get('https://api.example.com')
    context.response = response
```

## Assertion Helpers

```python
from bdv.step_registry import AssertionHelpers

@registry.then('the response should be successful')
def step_impl(context):
    AssertionHelpers.assert_status_code(context.response, 200)
    AssertionHelpers.assert_json_contains(context.response, "status", "success")
    AssertionHelpers.assert_response_time(context.response, 1000)  # max 1000ms
```

## Complete Example

```python
from bdv.step_registry import StepRegistry, Context, StepType, DataTable

# Setup
registry = StepRegistry()
context = Context()

# Define steps
@registry.given('I have {count:int} products')
def setup_products(context, count):
    context.products = [f"Product {i}" for i in range(count)]

@registry.when('I search for "{query}"')
def search_products(context, query):
    context.results = [p for p in context.products if query in p]

@registry.then('I should see {count:int} results')
def verify_results(context, count):
    assert len(context.results) == count

# Execute scenario
registry.execute_step('I have 10 products', StepType.GIVEN, context)
registry.execute_step('I search for "Product 5"', StepType.WHEN, context)
registry.execute_step('I should see 1 results', StepType.THEN, context)

print(f"Test passed! Found: {context.results}")
# Output: Test passed! Found: ['Product 5']
```

## Best Practices

### 1. Keep Steps Focused
Each step should do one thing and do it well.

```python
# Good
@registry.given('a user exists')
def step_impl(context):
    context.user = create_user()

# Avoid
@registry.given('a user exists and is logged in and has permissions')
def step_impl(context):
    # Too much in one step
    pass
```

### 2. Use Descriptive Parameter Names
```python
# Good
@registry.when('I add {quantity:int} of "{product}" to cart')
def step_impl(context, quantity, product):
    pass

# Avoid
@registry.when('I add {x:int} of "{y}" to cart')
def step_impl(context, x, y):
    pass
```

### 3. Clean Up Resources
```python
@registry.then('I cleanup the test data')
def step_impl(context):
    if hasattr(context, 'test_user'):
        delete_user(context.test_user)
    context.clear()
```

### 4. Use Fixtures for Shared Setup
```python
@registry.given('the test environment is ready')
def step_impl(context):
    context.fixtures = {
        'database': setup_database(),
        'cache': setup_cache()
    }
```

## Advanced Features

### Dependency Injection
```python
@registry.given('I have a user service')
def step_impl(context):
    class UserService:
        def get_user(self, user_id):
            return {"id": user_id, "name": "Test User"}

    context.services = {"user_service": UserService()}

@registry.when('I get user {user_id:int}')
def step_impl(context, user_id):
    service = context.services["user_service"]
    context.user = service.get_user(user_id)
```

### Mock Services
```python
from unittest.mock import Mock

@registry.given('I have a mock API')
def step_impl(context):
    mock_api = Mock()
    mock_api.get_data.return_value = {"data": "test"}
    context.api = mock_api

@registry.when('I call the API')
def step_impl(context):
    context.result = context.api.get_data()

@registry.then('the API should have been called')
def step_impl(context):
    context.api.get_data.assert_called_once()
```

### Retry Logic
```python
@registry.when('I retry the operation up to {max_attempts:int} times')
def step_impl(context, max_attempts):
    for attempt in range(max_attempts):
        try:
            result = flaky_operation()
            context.result = result
            break
        except Exception as e:
            if attempt == max_attempts - 1:
                raise
```

## Troubleshooting

### Step Not Found
```
ValueError: No step definition found for: <step_text>
```
**Solution:** Check that the pattern matches exactly. Use quotes for strings and correct parameter types.

### Type Conversion Error
If a parameter can't be converted to int/float, it remains a string.

### Context Attribute Error
```
AttributeError: Context has no attribute 'xyz'
```
**Solution:** Make sure the attribute is set in a previous step.

## Files

- **Implementation:** `/home/ec2-user/projects/maestro-platform/maestro-hive/bdv/step_registry.py`
- **Tests:** `/home/ec2-user/projects/maestro-platform/maestro-hive/tests/bdv/integration/test_step_definitions.py`
- **Documentation:** `/home/ec2-user/projects/maestro-platform/maestro-hive/tests/bdv/integration/BDV_PHASE_2A_TEST_SUITE_11_SUMMARY.md`

## Support

For questions or issues:
1. Check the test suite for examples
2. Review the summary document for detailed implementation notes
3. Examine the step_registry.py source code for advanced usage

---

**Version:** 1.0.0
**Last Updated:** 2025-10-13
