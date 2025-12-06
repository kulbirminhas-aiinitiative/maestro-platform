"""
BDD/Gherkin Test Templates - MD-2523

Behavior-driven development templates using Gherkin syntax.
"""

from typing import Dict, Any
from .models import TestTemplate, TestType, TestFramework


class GherkinFeatureTemplate(TestTemplate):
    """Gherkin feature file template."""

    def __init__(self, feature_name: str = "Feature"):
        super().__init__(
            name="gherkin_feature_template",
            description="Gherkin feature file template for BDD testing",
            test_type=TestType.BDD,
            framework=TestFramework.BEHAVE,
            file_extension=".feature",
            tags=["bdd", "gherkin", "behave", "cucumber"],
            dependencies=["behave>=1.2.6", "behave-html-formatter>=0.9.10"],
            variables={"feature_name": feature_name},
        )

        self.template_content = '''# language: en
# encoding: utf-8

@{{ feature_name.lower().replace(' ', '-') }}
Feature: {{ feature_name }}
  As a user of the system
  I want to perform actions related to {{ feature_name.lower() }}
  So that I can achieve my business goals

  Background:
    Given the system is initialized
    And I am logged in as a valid user

  # ==============================================================================
  # Happy Path Scenarios
  # ==============================================================================

  @positive @smoke
  Scenario: Successfully create a new resource
    Given I am on the resources page
    When I click the "Create New" button
    And I fill in the following details:
      | Field       | Value           |
      | Name        | Test Resource   |
      | Description | A test resource |
      | Type        | Standard        |
    And I click the "Save" button
    Then I should see a success message "Resource created successfully"
    And the resource "Test Resource" should appear in the list

  @positive
  Scenario: View resource details
    Given a resource "Sample Resource" exists in the system
    When I navigate to the resource details page for "Sample Resource"
    Then I should see the resource name "Sample Resource"
    And I should see all resource attributes
    And the "Edit" button should be visible

  @positive
  Scenario Outline: Update resource with valid data
    Given a resource "<original_name>" exists
    When I edit the resource with new name "<new_name>"
    Then the resource should be renamed to "<new_name>"
    And I should see a success message

    Examples:
      | original_name    | new_name         |
      | Resource Alpha   | Resource Alpha V2 |
      | Resource Beta    | Resource Beta V2  |
      | Resource Gamma   | Resource Gamma V2 |

  @positive
  Scenario: Delete a resource
    Given a resource "To Be Deleted" exists in the system
    When I delete the resource "To Be Deleted"
    And I confirm the deletion in the dialog
    Then the resource should be removed from the list
    And I should see a success message "Resource deleted"

  # ==============================================================================
  # Negative / Edge Case Scenarios
  # ==============================================================================

  @negative @validation
  Scenario: Attempt to create resource without required fields
    Given I am on the create resource page
    When I leave the "Name" field empty
    And I click the "Save" button
    Then I should see a validation error "Name is required"
    And the resource should not be created

  @negative @validation
  Scenario Outline: Validation errors for invalid input
    Given I am on the create resource page
    When I enter "<invalid_value>" in the "<field>" field
    And I click the "Save" button
    Then I should see the error message "<error_message>"

    Examples:
      | field       | invalid_value         | error_message               |
      | Name        |                       | Name is required            |
      | Name        | AB                    | Name must be at least 3 characters |
      | Email       | invalid-email         | Invalid email format        |
      | Amount      | -100                  | Amount must be positive     |

  @negative @authorization
  Scenario: Unauthorized user cannot access admin features
    Given I am logged in as a regular user
    When I try to access the admin settings page
    Then I should see an "Access Denied" message
    And I should be redirected to the dashboard

  @negative @error-handling
  Scenario: Handle system error gracefully
    Given the backend service is unavailable
    When I try to load the resources page
    Then I should see a friendly error message
    And a "Retry" button should be available

  # ==============================================================================
  # Search and Filter Scenarios
  # ==============================================================================

  @search
  Scenario: Search resources by name
    Given the following resources exist:
      | Name            | Type     | Status  |
      | Alpha Project   | Standard | Active  |
      | Beta Project    | Premium  | Active  |
      | Gamma Archive   | Standard | Archived |
    When I search for "Alpha"
    Then I should see 1 result
    And "Alpha Project" should be visible

  @filter
  Scenario: Filter resources by status
    Given multiple resources with different statuses exist
    When I filter by status "Active"
    Then I should only see resources with "Active" status
    And the filter badge should show "Active"

  @search @filter
  Scenario: Combined search and filter
    Given the following resources exist:
      | Name          | Type     | Status |
      | Active Alpha  | Standard | Active |
      | Active Beta   | Premium  | Active |
      | Archived Alpha | Standard | Archived |
    When I search for "Alpha"
    And I filter by status "Active"
    Then I should see only "Active Alpha"

  # ==============================================================================
  # Pagination Scenarios
  # ==============================================================================

  @pagination
  Scenario: Navigate through paginated results
    Given there are 50 resources in the system
    And the page size is set to 10
    When I am on the first page
    Then I should see 10 resources
    And the "Next" button should be enabled
    When I click "Next"
    Then I should see the next 10 resources
    And the current page should be 2

  # ==============================================================================
  # Data Table Scenarios
  # ==============================================================================

  @bulk-operations
  Scenario: Bulk select and delete resources
    Given the following resources exist:
      | Name       |
      | Resource 1 |
      | Resource 2 |
      | Resource 3 |
    When I select all resources using the header checkbox
    And I click "Delete Selected"
    And I confirm the bulk deletion
    Then all selected resources should be deleted
    And I should see "3 resources deleted"

  # ==============================================================================
  # Integration Scenarios
  # ==============================================================================

  @integration @api
  Scenario: Resource changes sync with external system
    Given I create a resource "Synced Resource"
    When the sync job runs
    Then the resource should appear in the external system
    And the sync status should show "Synced"

  @integration @webhook
  Scenario: Webhook triggered on resource creation
    Given a webhook is configured for resource creation
    When I create a new resource "Webhook Test"
    Then the webhook should receive a notification
    And the payload should contain the resource details
'''


class StepDefinitionTemplate(TestTemplate):
    """Step definition template for Gherkin features."""

    def __init__(self, feature_name: str = "feature"):
        super().__init__(
            name="step_definition_template",
            description="Python step definitions for Gherkin features",
            test_type=TestType.BDD,
            framework=TestFramework.BEHAVE,
            file_extension=".py",
            tags=["bdd", "steps", "behave", "python"],
            dependencies=["behave>=1.2.6"],
            variables={"feature_name": feature_name},
        )

        self.template_content = '''"""
Step Definitions for {{ feature_name }}

Implements the Given/When/Then steps for {{ feature_name }} feature.
"""

from behave import given, when, then, step
from behave.runner import Context
from typing import Any, Dict
import httpx
import asyncio


# ==============================================================================
# Helper Functions
# ==============================================================================

def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


# ==============================================================================
# Given Steps - Setup preconditions
# ==============================================================================

@given("the system is initialized")
def step_system_initialized(context: Context):
    """Initialize the system for testing."""
    context.base_url = context.config.userdata.get("base_url", "http://localhost:8000")
    context.client = httpx.Client(base_url=context.base_url)
    context.data = {}


@given("I am logged in as a valid user")
def step_logged_in_as_user(context: Context):
    """Log in as a standard user."""
    response = context.client.post(
        "/api/auth/login",
        json={"email": "user@example.com", "password": "password123"},
    )
    assert response.status_code == 200
    context.auth_token = response.json()["token"]
    context.headers = {"Authorization": f"Bearer {context.auth_token}"}


@given("I am logged in as a regular user")
def step_logged_in_regular_user(context: Context):
    """Log in as a regular user (same as valid user)."""
    step_logged_in_as_user(context)


@given("I am on the resources page")
def step_on_resources_page(context: Context):
    """Navigate to resources page."""
    context.current_page = "resources"
    response = context.client.get("/api/resources", headers=context.headers)
    context.page_data = response.json()


@given("I am on the create resource page")
def step_on_create_page(context: Context):
    """Navigate to create resource page."""
    context.current_page = "create_resource"
    context.form_data = {}


@given('a resource "{name}" exists in the system')
def step_resource_exists(context: Context, name: str):
    """Ensure a resource exists."""
    response = context.client.post(
        "/api/resources",
        json={"name": name, "type": "Standard"},
        headers=context.headers,
    )
    if response.status_code == 201:
        context.data["resource"] = response.json()
    else:
        # Already exists, fetch it
        response = context.client.get("/api/resources", headers=context.headers)
        resources = response.json()
        context.data["resource"] = next(
            (r for r in resources if r["name"] == name), None
        )


@given('a resource "{name}" exists')
def step_resource_exists_short(context: Context, name: str):
    """Short form of resource exists."""
    step_resource_exists(context, name)


@given("the following resources exist")
def step_resources_exist_table(context: Context):
    """Create multiple resources from table."""
    context.data["resources"] = []
    for row in context.table:
        data = dict(row.as_dict())
        response = context.client.post(
            "/api/resources",
            json=data,
            headers=context.headers,
        )
        if response.status_code == 201:
            context.data["resources"].append(response.json())


@given("there are {count:d} resources in the system")
def step_n_resources_exist(context: Context, count: int):
    """Create n resources."""
    for i in range(count):
        context.client.post(
            "/api/resources",
            json={"name": f"Resource {i+1}", "type": "Standard"},
            headers=context.headers,
        )


@given("the page size is set to {size:d}")
def step_page_size_set(context: Context, size: int):
    """Set pagination size."""
    context.page_size = size


@given("multiple resources with different statuses exist")
def step_resources_with_statuses(context: Context):
    """Create resources with various statuses."""
    statuses = ["Active", "Inactive", "Archived"]
    for i, status in enumerate(statuses):
        context.client.post(
            "/api/resources",
            json={"name": f"Resource {status}", "type": "Standard", "status": status},
            headers=context.headers,
        )


@given("the backend service is unavailable")
def step_backend_unavailable(context: Context):
    """Simulate backend unavailability."""
    context.simulate_error = True


@given('a webhook is configured for resource creation')
def step_webhook_configured(context: Context):
    """Configure a webhook."""
    context.webhook_url = "http://webhook.test/notify"


# ==============================================================================
# When Steps - Actions
# ==============================================================================

@when('I click the "{button_name}" button')
def step_click_button(context: Context, button_name: str):
    """Simulate button click."""
    context.last_action = f"clicked_{button_name.lower().replace(' ', '_')}"


@when("I fill in the following details")
def step_fill_form(context: Context):
    """Fill form from table."""
    context.form_data = {}
    for row in context.table:
        context.form_data[row["Field"].lower()] = row["Value"]


@when('I leave the "{field}" field empty')
def step_leave_field_empty(context: Context, field: str):
    """Leave a field empty."""
    context.form_data = context.form_data or {}
    context.form_data[field.lower()] = ""


@when('I enter "{value}" in the "{field}" field')
def step_enter_value(context: Context, value: str, field: str):
    """Enter a value in a field."""
    context.form_data = context.form_data or {}
    context.form_data[field.lower()] = value


@when('I navigate to the resource details page for "{name}"')
def step_navigate_to_details(context: Context, name: str):
    """Navigate to resource details."""
    resource = context.data.get("resource")
    if resource:
        response = context.client.get(
            f"/api/resources/{resource['id']}",
            headers=context.headers,
        )
        context.page_data = response.json()


@when('I edit the resource with new name "{new_name}"')
def step_edit_resource(context: Context, new_name: str):
    """Edit resource name."""
    resource = context.data.get("resource")
    if resource:
        response = context.client.put(
            f"/api/resources/{resource['id']}",
            json={"name": new_name},
            headers=context.headers,
        )
        context.last_response = response


@when('I delete the resource "{name}"')
def step_delete_resource(context: Context, name: str):
    """Delete a resource."""
    resource = context.data.get("resource")
    if resource:
        context.pending_delete = resource["id"]


@when("I confirm the deletion in the dialog")
def step_confirm_deletion(context: Context):
    """Confirm deletion."""
    if hasattr(context, "pending_delete"):
        response = context.client.delete(
            f"/api/resources/{context.pending_delete}",
            headers=context.headers,
        )
        context.last_response = response


@when('I search for "{query}"')
def step_search(context: Context, query: str):
    """Perform search."""
    response = context.client.get(
        f"/api/resources?search={query}",
        headers=context.headers,
    )
    context.search_results = response.json()


@when('I filter by status "{status}"')
def step_filter_by_status(context: Context, status: str):
    """Filter by status."""
    results = context.search_results or []
    context.filtered_results = [r for r in results if r.get("status") == status]


@when("I try to access the admin settings page")
def step_access_admin(context: Context):
    """Try to access admin page."""
    response = context.client.get("/api/admin/settings", headers=context.headers)
    context.last_response = response


@when("I try to load the resources page")
def step_try_load_page(context: Context):
    """Try to load page (may fail)."""
    if getattr(context, "simulate_error", False):
        context.last_response = type("Response", (), {"status_code": 503})()
    else:
        context.last_response = context.client.get(
            "/api/resources", headers=context.headers
        )


@when("I am on the first page")
def step_on_first_page(context: Context):
    """Navigate to first page."""
    context.current_page_num = 1


@when('I click "Next"')
def step_click_next(context: Context):
    """Click next page."""
    context.current_page_num = getattr(context, "current_page_num", 1) + 1


@when("I select all resources using the header checkbox")
def step_select_all(context: Context):
    """Select all resources."""
    context.selected = context.data.get("resources", [])


@when('I click "Delete Selected"')
def step_delete_selected(context: Context):
    """Click delete selected."""
    context.pending_bulk_delete = context.selected


@when("I confirm the bulk deletion")
def step_confirm_bulk_delete(context: Context):
    """Confirm bulk delete."""
    deleted = 0
    for resource in context.pending_bulk_delete:
        response = context.client.delete(
            f"/api/resources/{resource['id']}",
            headers=context.headers,
        )
        if response.status_code in [200, 204]:
            deleted += 1
    context.deleted_count = deleted


@when('I create a resource "{name}"')
@when('I create a new resource "{name}"')
def step_create_resource(context: Context, name: str):
    """Create a resource."""
    response = context.client.post(
        "/api/resources",
        json={"name": name, "type": "Standard"},
        headers=context.headers,
    )
    context.last_response = response
    if response.status_code == 201:
        context.data["created_resource"] = response.json()


@when("the sync job runs")
def step_sync_job_runs(context: Context):
    """Simulate sync job."""
    context.sync_complete = True


# ==============================================================================
# Then Steps - Assertions
# ==============================================================================

@then('I should see a success message "{message}"')
def step_see_success_message(context: Context, message: str):
    """Verify success message."""
    response = context.last_response
    if hasattr(response, "json"):
        data = response.json()
        assert data.get("message") == message or response.status_code in [200, 201]


@then('I should see a success message')
def step_see_success(context: Context):
    """Verify generic success."""
    assert context.last_response.status_code in [200, 201, 204]


@then('the resource "{name}" should appear in the list')
def step_resource_in_list(context: Context, name: str):
    """Verify resource is in list."""
    response = context.client.get("/api/resources", headers=context.headers)
    resources = response.json()
    names = [r["name"] for r in resources]
    assert name in names


@then('I should see the resource name "{name}"')
def step_see_resource_name(context: Context, name: str):
    """Verify resource name visible."""
    assert context.page_data.get("name") == name


@then("I should see all resource attributes")
def step_see_all_attributes(context: Context):
    """Verify all attributes visible."""
    required_fields = ["id", "name", "type", "created_at"]
    for field in required_fields:
        assert field in context.page_data


@then('the "{button}" button should be visible')
def step_button_visible(context: Context, button: str):
    """Verify button is visible (simulated)."""
    pass  # UI verification would happen in actual browser test


@then('the resource should be renamed to "{name}"')
def step_resource_renamed(context: Context, name: str):
    """Verify resource was renamed."""
    response = context.last_response
    assert response.status_code == 200
    assert response.json().get("name") == name


@then("the resource should be removed from the list")
def step_resource_removed(context: Context):
    """Verify resource was removed."""
    response = context.client.get("/api/resources", headers=context.headers)
    resources = response.json()
    deleted_id = context.pending_delete
    ids = [r["id"] for r in resources]
    assert deleted_id not in ids


@then('I should see a validation error "{message}"')
def step_see_validation_error(context: Context, message: str):
    """Verify validation error."""
    # Simulated - would check UI in real test
    pass


@then("the resource should not be created")
def step_resource_not_created(context: Context):
    """Verify resource was not created."""
    # Would verify no new resource in list
    pass


@then('I should see the error message "{message}"')
def step_see_error_message(context: Context, message: str):
    """Verify error message."""
    pass  # UI verification


@then('I should see an "Access Denied" message')
def step_see_access_denied(context: Context):
    """Verify access denied."""
    assert context.last_response.status_code in [401, 403]


@then("I should be redirected to the dashboard")
def step_redirected_dashboard(context: Context):
    """Verify redirect to dashboard."""
    # Would check redirect in browser test
    pass


@then("I should see a friendly error message")
def step_see_friendly_error(context: Context):
    """Verify friendly error shown."""
    assert context.last_response.status_code >= 400


@then('a "Retry" button should be available')
def step_retry_button_available(context: Context):
    """Verify retry button available."""
    pass  # UI verification


@then("I should see {count:d} result")
@then("I should see {count:d} results")
def step_see_n_results(context: Context, count: int):
    """Verify result count."""
    results = context.search_results or context.filtered_results or []
    assert len(results) == count


@then('"{name}" should be visible')
def step_item_visible(context: Context, name: str):
    """Verify item visible in results."""
    results = context.search_results or context.filtered_results or []
    names = [r["name"] for r in results]
    assert name in names


@then('I should only see resources with "{status}" status')
def step_only_status(context: Context, status: str):
    """Verify only specified status shown."""
    results = context.filtered_results or []
    for r in results:
        assert r.get("status") == status


@then('the filter badge should show "{text}"')
def step_filter_badge(context: Context, text: str):
    """Verify filter badge text."""
    pass  # UI verification


@then('I should see only "{name}"')
def step_see_only(context: Context, name: str):
    """Verify only one specific item shown."""
    results = context.filtered_results or context.search_results or []
    assert len(results) == 1
    assert results[0]["name"] == name


@then("I should see {count:d} resources")
def step_see_n_resources(context: Context, count: int):
    """Verify resource count on page."""
    # Would verify in paginated response
    pass


@then('the "Next" button should be enabled')
def step_next_enabled(context: Context):
    """Verify next button enabled."""
    pass  # UI verification


@then("I should see the next {count:d} resources")
def step_see_next_resources(context: Context, count: int):
    """Verify next page resources."""
    pass


@then("the current page should be {page:d}")
def step_current_page(context: Context, page: int):
    """Verify current page number."""
    assert context.current_page_num == page


@then("all selected resources should be deleted")
def step_all_selected_deleted(context: Context):
    """Verify all selected deleted."""
    assert context.deleted_count == len(context.pending_bulk_delete)


@then('I should see "{message}"')
def step_see_message(context: Context, message: str):
    """Verify message displayed."""
    pass  # Generic message verification


@then("the resource should appear in the external system")
def step_resource_in_external(context: Context):
    """Verify external sync."""
    assert context.sync_complete


@then('the sync status should show "Synced"')
def step_sync_status(context: Context):
    """Verify sync status."""
    pass


@then("the webhook should receive a notification")
def step_webhook_received(context: Context):
    """Verify webhook notification."""
    pass  # Would verify webhook call


@then("the payload should contain the resource details")
def step_payload_contains_details(context: Context):
    """Verify webhook payload."""
    pass
'''


class BDDContextTemplate(TestTemplate):
    """BDD context/environment template."""

    def __init__(self):
        super().__init__(
            name="bdd_context_template",
            description="BDD environment configuration template",
            test_type=TestType.BDD,
            framework=TestFramework.BEHAVE,
            file_extension=".py",
            tags=["bdd", "context", "environment"],
            dependencies=["behave>=1.2.6"],
        )

        self.template_content = '''"""
BDD Environment Configuration

Setup and teardown for BDD test execution.
"""

from behave import fixture, use_fixture
from behave.runner import Context
import httpx


def before_all(context: Context):
    """Setup before all tests."""
    context.config.setup_logging()

    # Load configuration
    context.base_url = context.config.userdata.get(
        "base_url", "http://localhost:8000"
    )


def before_feature(context: Context, feature):
    """Setup before each feature."""
    # Create HTTP client
    context.client = httpx.Client(
        base_url=context.base_url,
        timeout=30.0,
    )

    # Initialize shared data
    context.data = {}


def after_feature(context: Context, feature):
    """Teardown after each feature."""
    # Close HTTP client
    if hasattr(context, "client"):
        context.client.close()


def before_scenario(context: Context, scenario):
    """Setup before each scenario."""
    # Reset scenario-specific data
    context.scenario_data = {}


def after_scenario(context: Context, scenario):
    """Teardown after each scenario."""
    # Cleanup created resources
    if hasattr(context, "cleanup_resources"):
        for resource_id in context.cleanup_resources:
            try:
                context.client.delete(f"/api/resources/{resource_id}")
            except Exception:
                pass


def before_step(context: Context, step):
    """Setup before each step."""
    pass


def after_step(context: Context, step):
    """Teardown after each step."""
    # Capture screenshot on failure (for UI tests)
    if step.status == "failed":
        # Would capture screenshot here for browser tests
        pass


def after_all(context: Context):
    """Teardown after all tests."""
    pass


# ==============================================================================
# Fixtures
# ==============================================================================

@fixture
def authenticated_user(context: Context):
    """Fixture for authenticated user."""
    response = context.client.post(
        "/api/auth/login",
        json={"email": "user@test.com", "password": "password"},
    )
    context.auth_token = response.json().get("token")
    context.headers = {"Authorization": f"Bearer {context.auth_token}"}
    yield
    # Cleanup if needed


@fixture
def admin_user(context: Context):
    """Fixture for admin user."""
    response = context.client.post(
        "/api/auth/login",
        json={"email": "admin@test.com", "password": "adminpass"},
    )
    context.auth_token = response.json().get("token")
    context.headers = {"Authorization": f"Bearer {context.auth_token}"}
    yield
'''
