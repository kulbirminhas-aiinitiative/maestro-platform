# Gherkin Feature Parser - Quick Start Guide

## Installation

No external dependencies required. The parser is built using Python standard library only.

```python
from bdv.feature_parser import FeatureParser
```

## Basic Usage

### Parse a Feature File

```python
from bdv.feature_parser import FeatureParser

parser = FeatureParser()
result = parser.parse_file("features/auth/authentication.feature")

if result.success:
    feature = result.feature
    print(f"Feature: {feature.name}")
    print(f"Scenarios: {len(feature.scenarios)}")
else:
    print(f"Errors: {result.errors}")
```

### Parse Feature Content String

```python
content = """
@contract:AuthAPI:v1.0
Feature: User Login
  As a user I want to log in

  Scenario: Successful login
    Given I have valid credentials
    When I submit the login form
    Then I should be logged in
"""

result = parser.parse_content(content)
print(f"Feature: {result.feature.name}")
print(f"Contract tags: {result.feature.contract_tags}")
```

## Common Use Cases

### 1. Get Summary Statistics

```python
summary = parser.parse_summary("features/my_feature.feature")

print(f"File: {summary['file_path']}")
print(f"Feature: {summary['feature_name']}")
print(f"Total scenarios: {summary['test_count']}")
print(f"Regular scenarios: {summary['scenario_count']}")
print(f"Scenario outlines: {summary['outline_count']}")
print(f"Total steps: {summary['total_steps']}")
print(f"Contract tags: {summary['contract_tags']}")
```

### 2. Extract Contract Tags

```python
result = parser.parse_file("features/api.feature")
feature = result.feature

# All contract tags on feature
for tag in feature.contract_tags:
    print(f"Contract: {tag}")  # e.g., @contract:AuthAPI:v1.0

# All tags including contracts
for tag in feature.tags:
    print(f"Tag: {tag}")  # @contract:..., @smoke, @critical, etc.
```

### 3. Iterate Through Scenarios

```python
result = parser.parse_file("features/users.feature")

for scenario in result.feature.scenarios:
    print(f"\nScenario: {scenario.name}")
    print(f"  Type: {scenario.type}")
    print(f"  Tags: {scenario.tags}")
    print(f"  Steps: {len(scenario.steps)}")

    for step in scenario.steps:
        print(f"    {step.keyword} {step.text}")
```

### 4. Process Data Tables

```python
result = parser.parse_file("features/data.feature")
scenario = result.feature.scenarios[0]

for step in scenario.steps:
    if step.data_table:
        print(f"\n{step.keyword} {step.text}")

        # Access as list of dictionaries
        rows = step.data_table.to_dict_list()
        for row in rows:
            print(f"  - {row}")

        # Or access raw headers and rows
        print(f"  Headers: {step.data_table.headers}")
        print(f"  Rows: {step.data_table.rows}")
```

### 5. Handle Doc Strings

```python
result = parser.parse_file("features/api.feature")

for scenario in result.feature.scenarios:
    for step in scenario.steps:
        if step.doc_string:
            print(f"{step.keyword} {step.text}")
            print("Doc string:")
            print(step.doc_string)
```

### 6. Expand Scenario Outlines

```python
result = parser.parse_file("features/calculator.feature")

for scenario in result.feature.scenarios:
    if scenario.is_outline:
        expanded = scenario.expand_outline()
        print(f"\nOutline: {scenario.name}")
        print(f"Expanded to {len(expanded)} test cases:")

        for test_case in expanded:
            print(f"  - {test_case.name}")
            for step in test_case.steps:
                print(f"      {step.keyword} {step.text}")
```

### 7. Extract Step Parameters

```python
result = parser.parse_file("features/search.feature")

for scenario in result.feature.scenarios:
    for step in scenario.steps:
        if step.parameters:
            print(f"{step.keyword} {step.text}")
            print(f"  Parameters: {step.parameters}")
```

Example:
```
Given I have <count> items
  Parameters: ['count']

When I search for "laptop"
  Parameters: ['laptop']

Then I should see <num> results with title "Best <product>"
  Parameters: ['num', 'Best <product>']
```

## API Reference

### FeatureParser Class

#### Methods

- `parse_file(file_path: Union[str, Path]) -> ParseResult`
  - Parse a .feature file from disk
  - Returns ParseResult with success flag, feature, errors, warnings

- `parse_content(content: str, file_path: Optional[str] = None) -> ParseResult`
  - Parse Gherkin content from string
  - Returns ParseResult

- `parse_summary(file_path: Union[str, Path]) -> Dict[str, Any]`
  - Parse file and return summary statistics
  - Returns dict with: success, file_path, test_count, pass_rate, feature_name, scenario_count, outline_count, total_steps, contract_tags

### Data Models

#### ParseResult
- `success: bool` - Whether parsing succeeded
- `feature: Optional[Feature]` - Parsed feature (if successful)
- `errors: List[str]` - Error messages
- `warnings: List[str]` - Warning messages

#### Feature
- `name: str` - Feature name
- `description: str` - Multi-line description
- `tags: List[str]` - All tags (e.g., @smoke, @contract:...)
- `contract_tags: List[str]` - Only @contract: tags
- `background: Optional[Background]` - Background section
- `scenarios: List[Scenario]` - All scenarios
- `language: str` - Language code (default: "en")
- `line_number: int` - Line number in file
- `file_path: Optional[str]` - Source file path
- `total_scenarios(expanded: bool = False) -> int` - Count scenarios

#### Scenario
- `name: str` - Scenario name
- `type: str` - "scenario" or "scenario_outline"
- `tags: List[str]` - Scenario tags
- `steps: List[Step]` - Scenario steps
- `examples: List[Example]` - Examples (for outlines)
- `description: str` - Scenario description
- `line_number: int` - Line number
- `is_outline: bool` - Property: is this a Scenario Outline?
- `expand_outline() -> List[Scenario]` - Expand outline to concrete scenarios

#### Step
- `keyword: StepKeyword` - GIVEN, WHEN, THEN, AND, BUT
- `text: str` - Step text
- `line_number: int` - Line number
- `data_table: Optional[DataTable]` - Associated data table
- `doc_string: Optional[str]` - Multi-line doc string
- `parameters: List[str]` - Extracted parameters from text

#### DataTable
- `headers: List[str]` - Column headers
- `rows: List[List[str]]` - Data rows
- `to_dict_list() -> List[Dict[str, str]]` - Convert to list of dicts

#### Background
- `line_number: int` - Line number
- `steps: List[Step]` - Background steps
- `description: str` - Background description

#### Example
- `line_number: int` - Line number
- `tags: List[str]` - Example tags
- `data_table: Optional[DataTable]` - Examples data

## Error Handling

### File Errors

```python
result = parser.parse_file("nonexistent.feature")
if not result.success:
    print(f"Errors: {result.errors}")
    # Output: ['File not found: nonexistent.feature']
```

### Syntax Errors

```python
content = """
Scenario: No feature keyword
  Given something
"""

result = parser.parse_content(content)
if not result.success:
    print(f"Errors: {result.errors}")
    # Output: ['Missing Feature keyword at line 2']
```

### Warnings

```python
content = """
Feature: Empty feature
  This feature has no scenarios
"""

result = parser.parse_content(content)
if result.warnings:
    print(f"Warnings: {result.warnings}")
    # Output: ['Feature has no scenarios or background']
```

## Gherkin Syntax Examples

### Complete Example

```gherkin
@contract:UserAPI:v1.0
@smoke
Feature: User Management
  As an administrator
  I want to manage user accounts
  So that I can control system access

  Background:
    Given the system is running
    And I am logged in as admin

  @happy_path
  Scenario: Create new user
    Given I have the user data:
      | name  | email              | role  |
      | Alice | alice@example.com  | user  |
    When I create the user
    Then the user should exist in the database
    And the user should receive a welcome email

  @validation
  Scenario Outline: Validate email format
    Given I try to create a user with email "<email>"
    Then I should see validation error "<error>"

    Examples: Invalid emails
      | email           | error                |
      | invalid         | Invalid email format |
      | @example.com    | Invalid email format |
      | user@           | Invalid email format |

  Scenario: Send API request
    Given I have a JSON payload:
      """
      {
        "name": "Bob",
        "email": "bob@example.com",
        "role": "admin"
      }
      """
    When I POST to /api/users
    Then the response status should be 201
```

## Tips and Best Practices

1. **Always check `result.success`** before accessing `result.feature`
2. **Use `parse_summary()`** for quick statistics without full parsing
3. **Check for warnings** even on successful parses
4. **Use `expand_outline()`** to get concrete test cases from outlines
5. **Access `contract_tags` property** for easy contract tag filtering
6. **Use `to_dict_list()`** for easy data table processing
7. **Check `step.data_table` and `step.doc_string`** before accessing
8. **Use `scenario.is_outline`** to identify Scenario Outlines

## Integration Examples

### With BDV Runner

```python
from bdv.feature_parser import FeatureParser
from bdv.bdv_runner import BDVRunner

parser = FeatureParser()
runner = BDVRunner(base_url="http://localhost:8000")

# Discover and parse features
for feature_file in Path("features").rglob("*.feature"):
    result = parser.parse_file(feature_file)
    if result.success:
        print(f"Running: {result.feature.name}")
        print(f"Contracts: {result.feature.contract_tags}")

        # Run tests
        bdv_result = runner.run(
            feature_files=[str(feature_file)],
            iteration_id="test-run-001"
        )
```

### With Quality Fabric

```python
from bdv.feature_parser import FeatureParser

parser = FeatureParser()

for feature_file in Path("features").rglob("*.feature"):
    summary = parser.parse_summary(feature_file)

    # Log to quality fabric
    quality_fabric_client.log_test_suite({
        'suite_name': summary['feature_name'],
        'test_count': summary['test_count'],
        'file_path': summary['file_path'],
        'contract_tags': summary['contract_tags']
    })
```

## Support

For issues or questions:
1. Check test suite: `tests/bdv/unit/test_feature_parser.py`
2. Review summary doc: `tests/bdv/unit/BDV_PHASE_2A_TEST_SUITE_9_SUMMARY.md`
3. Run tests: `pytest tests/bdv/unit/test_feature_parser.py -v`

## License

Part of Maestro Platform - BDV (Behavior-Driven Validation) System
