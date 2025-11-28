"""
BDV Phase 2A: Test Suite 9 - Gherkin Feature File Parsing

Test IDs: BDV-001 to BDV-025 (25 tests)

Test Categories:
1. Basic parsing (001-012): Valid .feature file, Background, Scenario, Scenario Outline,
   data tables, tags (@contract:API:v1.2), comments, multi-line strings, Given/When/Then/And/But
2. Error handling (013-015): Step parameters, invalid Gherkin, missing Feature keyword
3. Edge cases (016-021): Empty file, no scenarios, Unicode, language tags, metadata
4. Advanced (022-025): Tag inheritance, Scenario Outline expansion, 100+ scenarios in <1s

Author: Claude Code Implementation
Date: 2025-10-13
Version: 1.0.0
"""

import pytest
import time
import tempfile
from pathlib import Path
from typing import List

from bdv.feature_parser import (
    FeatureParser,
    Feature,
    Scenario,
    Background,
    Step,
    DataTable,
    Example,
    StepKeyword,
    ParseResult,
)


class TestFeatureParserBasics:
    """Basic parsing tests (BDV-001 to BDV-012)"""

    def test_bdv_001_parse_valid_feature_file(self):
        """BDV-001: Parse a valid .feature file with Feature keyword"""
        content = """
Feature: User Login
  As a user
  I want to log in
  So that I can access my account
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        assert result.feature is not None
        assert result.feature.name == "User Login"
        assert "As a user" in result.feature.description
        assert len(result.errors) == 0

    def test_bdv_002_parse_background(self):
        """BDV-002: Parse Feature with Background section"""
        content = """
Feature: Authentication

  Background:
    Given the system is running
    And the database is connected

  Scenario: Login
    When I log in
    Then I should see the dashboard
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        assert result.feature.background is not None
        assert len(result.feature.background.steps) == 2
        assert result.feature.background.steps[0].keyword == StepKeyword.GIVEN
        assert result.feature.background.steps[0].text == "the system is running"
        assert result.feature.background.steps[1].keyword == StepKeyword.AND
        assert result.feature.background.steps[1].text == "the database is connected"

    def test_bdv_003_parse_scenario(self):
        """BDV-003: Parse basic Scenario"""
        content = """
Feature: User Management

  Scenario: Create new user
    Given I am an admin
    When I create a user with email "test@example.com"
    Then the user should be created successfully
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        assert len(result.feature.scenarios) == 1
        scenario = result.feature.scenarios[0]
        assert scenario.name == "Create new user"
        assert scenario.type == "scenario"
        assert not scenario.is_outline
        assert len(scenario.steps) == 3

    def test_bdv_004_parse_scenario_outline(self):
        """BDV-004: Parse Scenario Outline with Examples"""
        content = """
Feature: Calculator

  Scenario Outline: Addition
    Given I have entered <num1> into the calculator
    And I have entered <num2> into the calculator
    When I press add
    Then the result should be <result>

    Examples:
      | num1 | num2 | result |
      | 5    | 10   | 15     |
      | 20   | 30   | 50     |
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        assert len(result.feature.scenarios) == 1
        scenario = result.feature.scenarios[0]
        assert scenario.is_outline
        assert len(scenario.examples) == 1
        assert scenario.examples[0].data_table is not None
        assert len(scenario.examples[0].data_table.rows) == 2
        assert scenario.examples[0].data_table.headers == ["num1", "num2", "result"]

    def test_bdv_005_parse_data_tables(self):
        """BDV-005: Parse data tables in steps"""
        content = """
Feature: User Registration

  Scenario: Register multiple users
    Given the following users exist:
      | name  | email              | role  |
      | Alice | alice@example.com  | admin |
      | Bob   | bob@example.com    | user  |
    When I list all users
    Then I should see 2 users
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        scenario = result.feature.scenarios[0]
        assert len(scenario.steps) == 3

        first_step = scenario.steps[0]
        assert first_step.data_table is not None
        assert first_step.data_table.headers == ["name", "email", "role"]
        assert len(first_step.data_table.rows) == 2
        assert first_step.data_table.rows[0] == ["Alice", "alice@example.com", "admin"]

    def test_bdv_006_parse_contract_tags(self):
        """BDV-006: Parse tags including @contract:API:v1.2 format"""
        content = """
@contract:AuthAPI:v1.2
@critical
@smoke
Feature: Authentication API

  @happy_path
  Scenario: Successful login
    Given valid credentials
    When I log in
    Then I should receive a token
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        assert "@contract:AuthAPI:v1.2" in result.feature.tags
        assert "@critical" in result.feature.tags
        assert "@smoke" in result.feature.tags
        assert len(result.feature.contract_tags) == 1
        assert result.feature.contract_tags[0] == "@contract:AuthAPI:v1.2"

        scenario = result.feature.scenarios[0]
        assert "@happy_path" in scenario.tags

    def test_bdv_007_parse_comments(self):
        """BDV-007: Parse and ignore comments"""
        content = """
# This is a comment
Feature: User Login

  # Another comment
  Scenario: Login with valid credentials
    # Step comment
    Given I am on the login page
    When I enter valid credentials
    # Final comment
    Then I should be logged in
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        assert result.feature.name == "User Login"
        assert len(result.feature.scenarios) == 1
        assert len(result.feature.scenarios[0].steps) == 3

    def test_bdv_008_parse_multiline_docstrings(self):
        """BDV-008: Parse multi-line doc strings (triple quotes)"""
        content = '''
Feature: API Testing

  Scenario: Send JSON payload
    Given I have a JSON payload:
      """
      {
        "name": "John Doe",
        "email": "john@example.com",
        "age": 30
      }
      """
    When I send a POST request
    Then the response should be 201
'''
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        scenario = result.feature.scenarios[0]
        first_step = scenario.steps[0]
        assert first_step.doc_string is not None
        assert '"name": "John Doe"' in first_step.doc_string
        assert '"email": "john@example.com"' in first_step.doc_string

    def test_bdv_009_parse_given_when_then(self):
        """BDV-009: Parse Given/When/Then steps"""
        content = """
Feature: Shopping Cart

  Scenario: Add item to cart
    Given I am logged in
    When I add "Laptop" to my cart
    Then my cart should contain 1 item
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        steps = result.feature.scenarios[0].steps
        assert steps[0].keyword == StepKeyword.GIVEN
        assert steps[1].keyword == StepKeyword.WHEN
        assert steps[2].keyword == StepKeyword.THEN

    def test_bdv_010_parse_and_but_steps(self):
        """BDV-010: Parse And/But step keywords"""
        content = """
Feature: Order Processing

  Scenario: Process valid order
    Given I have items in my cart
    And I have a valid payment method
    When I proceed to checkout
    Then the order should be created
    And I should receive a confirmation email
    But I should not be charged twice
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        steps = result.feature.scenarios[0].steps
        assert len(steps) == 6
        assert steps[1].keyword == StepKeyword.AND
        assert steps[4].keyword == StepKeyword.AND
        assert steps[5].keyword == StepKeyword.BUT

    def test_bdv_011_parse_multiple_scenarios(self):
        """BDV-011: Parse multiple scenarios in one feature"""
        content = """
Feature: User Management

  Scenario: Create user
    Given I am an admin
    When I create a user
    Then the user should exist

  Scenario: Delete user
    Given I am an admin
    And a user exists
    When I delete the user
    Then the user should not exist

  Scenario: Update user
    Given I am an admin
    And a user exists
    When I update the user's email
    Then the email should be updated
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        assert len(result.feature.scenarios) == 3
        assert result.feature.scenarios[0].name == "Create user"
        assert result.feature.scenarios[1].name == "Delete user"
        assert result.feature.scenarios[2].name == "Update user"

    def test_bdv_012_parse_feature_description(self):
        """BDV-012: Parse multi-line feature description"""
        content = """
Feature: User Authentication
  As a registered user
  I want to authenticate with my credentials
  So that I can access protected resources

  Additional context:
  This feature covers all authentication scenarios

  Scenario: Login
    Given valid credentials
    When I log in
    Then I should be authenticated
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        assert "As a registered user" in result.feature.description
        assert "I want to authenticate" in result.feature.description
        assert "Additional context" in result.feature.description


class TestFeatureParserErrorHandling:
    """Error handling tests (BDV-013 to BDV-015)"""

    def test_bdv_013_parse_step_parameters(self):
        """BDV-013: Extract step parameters in <brackets> and "quotes" """
        content = """
Feature: Parameter Extraction

  Scenario: Test parameters
    Given I have <num> items
    When I search for "laptop"
    Then I should see <count> results with title "Best Laptop"
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        steps = result.feature.scenarios[0].steps

        # Test <num> parameter
        assert "num" in steps[0].parameters

        # Test "laptop" parameter
        assert "laptop" in steps[1].parameters

        # Test both <count> and "Best Laptop" parameters
        assert "count" in steps[2].parameters
        assert "Best Laptop" in steps[2].parameters

    def test_bdv_014_handle_invalid_gherkin(self):
        """BDV-014: Handle invalid Gherkin syntax gracefully"""
        content = """
Feature: Invalid Syntax

  Scenario: Missing step keyword
    I do something without a keyword
    When I do something valid
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        # Parser should succeed but may have incomplete scenario
        assert result.success is True
        # The invalid line should be skipped
        scenario = result.feature.scenarios[0]
        # Should only have the valid "When" step
        assert len(scenario.steps) >= 1
        assert scenario.steps[-1].keyword == StepKeyword.WHEN

    def test_bdv_015_missing_feature_keyword(self):
        """BDV-015: Error when Feature keyword is missing"""
        content = """
Scenario: Login
  Given I am on the login page
  When I enter credentials
  Then I should be logged in
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is False
        assert len(result.errors) > 0
        assert "Feature keyword" in result.errors[0] or "Missing" in result.errors[0]


class TestFeatureParserEdgeCases:
    """Edge case tests (BDV-016 to BDV-021)"""

    def test_bdv_016_empty_file(self):
        """BDV-016: Handle empty file"""
        content = ""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is False
        assert len(result.errors) > 0

    def test_bdv_017_feature_with_no_scenarios(self):
        """BDV-017: Parse feature with no scenarios"""
        content = """
Feature: Empty Feature
  This feature has no scenarios yet
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        assert result.feature.name == "Empty Feature"
        assert len(result.feature.scenarios) == 0
        # Should have a warning about no scenarios
        assert len(result.warnings) > 0

    def test_bdv_018_unicode_support(self):
        """BDV-018: Handle Unicode characters in feature files"""
        content = """
Feature: Unicode Support 🚀

  Scenario: Test with emoji and special chars
    Given I have "café" in my inventory
    When I search for "München"
    Then I should see "Côte d'Ivoire" in results
    And the price should be "€100" or "¥1000"
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        assert "🚀" in result.feature.name
        steps = result.feature.scenarios[0].steps
        assert "café" in steps[0].text
        assert "München" in steps[1].text
        assert "Côte d'Ivoire" in steps[2].text

    def test_bdv_019_language_tags(self):
        """BDV-019: Parse language tags (@language:en)"""
        content = """
@language:fr
Feature: Connexion utilisateur

  Scenario: Connexion réussie
    Given je suis sur la page de connexion
    When je saisis mes identifiants
    Then je devrais être connecté
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        assert result.feature.language == "fr"
        assert result.feature.name == "Connexion utilisateur"

    def test_bdv_020_feature_metadata_extraction(self):
        """BDV-020: Extract feature metadata (tags, line numbers, etc.)"""
        content = """
@contract:PaymentAPI:v2.0
@regression
@team:payments
Feature: Payment Processing

  Scenario: Process payment
    Given a valid payment method
    When I submit payment
    Then payment should succeed
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True

        # Check feature metadata
        assert result.feature.line_number > 0
        assert len(result.feature.tags) == 3
        assert "@team:payments" in result.feature.tags

        # Check scenario metadata
        scenario = result.feature.scenarios[0]
        assert scenario.line_number > 0

        # Check step metadata
        for step in scenario.steps:
            assert step.line_number > 0

    def test_bdv_021_whitespace_and_formatting(self):
        """BDV-021: Handle various whitespace and formatting"""
        content = """

@tag1    @tag2


Feature:    User Login


  Scenario:     Login with spaces
    Given     I am on the login page
    When   I enter credentials
    Then      I should be logged in


"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        assert result.feature.name == "User Login"
        assert len(result.feature.tags) == 2
        scenario = result.feature.scenarios[0]
        assert scenario.name == "Login with spaces"
        assert len(scenario.steps) == 3


class TestFeatureParserAdvanced:
    """Advanced features (BDV-022 to BDV-025)"""

    def test_bdv_022_tag_inheritance(self):
        """BDV-022: Test tag inheritance from feature to scenarios"""
        content = """
@contract:API:v1.0
@smoke
Feature: API Testing

  @critical
  Scenario: Test endpoint
    Given the API is running
    When I call the endpoint
    Then I should get a response

  Scenario: Test another endpoint
    Given the API is running
    When I call another endpoint
    Then I should get a response
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True

        # Feature tags
        assert "@contract:API:v1.0" in result.feature.tags
        assert "@smoke" in result.feature.tags

        # First scenario has its own tag
        assert "@critical" in result.feature.scenarios[0].tags

        # Second scenario has no additional tags
        assert len(result.feature.scenarios[1].tags) == 0

    def test_bdv_023_scenario_outline_expansion(self):
        """BDV-023: Expand Scenario Outline into individual test cases"""
        content = """
Feature: Calculator

  Scenario Outline: Arithmetic operations
    Given I have <a> and <b>
    When I perform <operation>
    Then the result should be <expected>

    Examples:
      | a  | b  | operation | expected |
      | 10 | 5  | add       | 15       |
      | 10 | 5  | subtract  | 5        |
      | 10 | 5  | multiply  | 50       |
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        outline = result.feature.scenarios[0]
        assert outline.is_outline

        # Expand outline
        expanded = outline.expand_outline()
        assert len(expanded) == 3

        # Check first expanded scenario
        assert "15" in expanded[0].steps[2].text
        assert "add" in expanded[0].steps[1].text

        # Check second expanded scenario
        assert "5" in expanded[1].steps[2].text
        assert "subtract" in expanded[1].steps[1].text

    def test_bdv_024_multiple_examples_in_outline(self):
        """BDV-024: Handle Scenario Outline with multiple Examples tables"""
        content = """
Feature: Multi-example test

  Scenario Outline: Login attempts
    Given I attempt to login with <username> and <password>
    Then I should see <result>

    @happy_path
    Examples: Valid credentials
      | username | password | result  |
      | alice    | pass123  | success |
      | bob      | secret   | success |

    @error_cases
    Examples: Invalid credentials
      | username | password | result |
      | alice    | wrong    | error  |
      | invalid  | pass123  | error  |
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        outline = result.feature.scenarios[0]
        assert len(outline.examples) == 2

        # Check tags on examples
        assert "@happy_path" in outline.examples[0].tags
        assert "@error_cases" in outline.examples[1].tags

        # Expand should create 4 scenarios (2 from each examples table)
        expanded = outline.expand_outline()
        assert len(expanded) == 4

    def test_bdv_025_performance_100_scenarios(self):
        """BDV-025: Performance - Parse 100+ scenarios in <1 second"""
        # Generate feature with 100 scenarios
        scenarios = []
        for i in range(100):
            scenarios.append(f"""
  @tag{i}
  Scenario: Test scenario {i}
    Given precondition {i}
    When action {i}
    Then result {i}
""")

        content = f"""
Feature: Large Feature File
  This feature has 100+ scenarios for performance testing

{''.join(scenarios)}
"""

        parser = FeatureParser()
        start_time = time.time()
        result = parser.parse_content(content)
        elapsed = time.time() - start_time

        assert result.success is True
        assert len(result.feature.scenarios) == 100
        assert elapsed < 1.0, f"Parsing took {elapsed:.2f}s, should be < 1s"


class TestFeatureParserSummary:
    """Test summary functionality"""

    def test_parse_summary_successful(self):
        """Test parse_summary method returns correct statistics"""
        content = """
@contract:TestAPI:v1.0
Feature: Test Feature

  Background:
    Given background step

  Scenario: Test 1
    Given step 1
    When step 2
    Then step 3

  Scenario Outline: Test 2
    Given <param>
    When action
    Then result

    Examples:
      | param |
      | a     |
      | b     |
"""
        # Create temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.feature', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            parser = FeatureParser()
            summary = parser.parse_summary(temp_path)

            assert summary['success'] is True
            assert summary['file_path'] == temp_path
            assert summary['feature_name'] == "Test Feature"
            assert summary['scenario_count'] == 1  # Non-outline scenarios
            assert summary['outline_count'] == 1  # Outline scenarios
            assert summary['test_count'] == 3  # 1 scenario + 2 expanded from outline
            assert summary['pass_rate'] == 0.0  # Parsing doesn't execute
            assert len(summary['contract_tags']) == 1
            assert "@contract:TestAPI:v1.0" in summary['contract_tags']
            assert summary['total_steps'] == 7  # 1 background + 3 in scenario + 3 in outline
        finally:
            Path(temp_path).unlink()

    def test_parse_summary_with_errors(self):
        """Test parse_summary handles errors gracefully"""
        parser = FeatureParser()
        summary = parser.parse_summary("/nonexistent/file.feature")

        assert summary['success'] is False
        assert summary['test_count'] == 0
        assert summary['pass_rate'] == 0.0
        assert len(summary['errors']) > 0


class TestFeatureParserFileOperations:
    """Test file-based operations"""

    def test_parse_file_success(self):
        """Test parsing from actual file"""
        content = """
Feature: File Test
  Scenario: Test from file
    Given a file
    When I parse it
    Then it should work
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.feature', delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            parser = FeatureParser()
            result = parser.parse_file(temp_path)

            assert result.success is True
            assert result.feature.name == "File Test"
            assert result.feature.file_path == temp_path
        finally:
            Path(temp_path).unlink()

    def test_parse_file_not_found(self):
        """Test parsing non-existent file"""
        parser = FeatureParser()
        result = parser.parse_file("/nonexistent/file.feature")

        assert result.success is False
        assert "not found" in result.errors[0].lower()

    def test_parse_file_wrong_extension(self):
        """Test parsing file without .feature extension"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Feature: Test")
            temp_path = f.name

        try:
            parser = FeatureParser()
            result = parser.parse_file(temp_path)

            assert result.success is False
            assert "Not a .feature file" in result.errors[0]
        finally:
            Path(temp_path).unlink()


class TestDataTableConversion:
    """Test DataTable utility methods"""

    def test_data_table_to_dict_list(self):
        """Test DataTable.to_dict_list() method"""
        content = """
Feature: Table Test

  Scenario: Test table conversion
    Given the following data:
      | name  | age | city     |
      | Alice | 30  | New York |
      | Bob   | 25  | London   |
    When I process the data
    Then it should be converted
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        step = result.feature.scenarios[0].steps[0]
        assert step.data_table is not None

        dict_list = step.data_table.to_dict_list()
        assert len(dict_list) == 2
        assert dict_list[0] == {"name": "Alice", "age": "30", "city": "New York"}
        assert dict_list[1] == {"name": "Bob", "age": "25", "city": "London"}


class TestFeatureTotalScenarios:
    """Test Feature.total_scenarios() method"""

    def test_total_scenarios_not_expanded(self):
        """Test total_scenarios without expansion"""
        content = """
Feature: Count Test

  Scenario: Test 1
    Given step

  Scenario: Test 2
    Given step

  Scenario Outline: Test 3
    Given <param>

    Examples:
      | param |
      | a     |
      | b     |
      | c     |
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        assert result.feature.total_scenarios(expanded=False) == 3

    def test_total_scenarios_expanded(self):
        """Test total_scenarios with expansion"""
        content = """
Feature: Count Test

  Scenario: Test 1
    Given step

  Scenario: Test 2
    Given step

  Scenario Outline: Test 3
    Given <param>

    Examples:
      | param |
      | a     |
      | b     |
      | c     |
"""
        parser = FeatureParser()
        result = parser.parse_content(content)

        assert result.success is True
        # 2 regular scenarios + 3 expanded from outline
        assert result.feature.total_scenarios(expanded=True) == 5


# Test execution summary
if __name__ == "__main__":
    import sys

    # Run pytest with verbose output
    exit_code = pytest.main([__file__, "-v", "--tb=short", "-ra"])

    print("\n" + "="*80)
    print("BDV Phase 2A - Test Suite 9: Gherkin Feature File Parsing")
    print("="*80)
    print("\nTest Categories:")
    print("  • Basic parsing (BDV-001 to BDV-012): 12 tests")
    print("  • Error handling (BDV-013 to BDV-015): 3 tests")
    print("  • Edge cases (BDV-016 to BDV-021): 6 tests")
    print("  • Advanced (BDV-022 to BDV-025): 4 tests")
    print("  • Additional utility tests: 8 tests")
    print(f"\nTotal: 33 tests")
    print("="*80)

    sys.exit(exit_code)
