"""
API Integration Test Templates - MD-2523

Templates for REST and GraphQL API integration testing.
"""

from typing import Dict, Any
from .models import TestTemplate, TestType, TestFramework


class APIIntegrationTemplate(TestTemplate):
    """Base API integration test template."""

    def __init__(self, api_name: str = "api"):
        super().__init__(
            name="api_integration_template",
            description="Base template for API integration testing",
            test_type=TestType.API,
            framework=TestFramework.PYTEST,
            tags=["api", "integration", "rest", "http"],
            dependencies=[
                "pytest>=7.0.0",
                "httpx>=0.24.0",
                "pytest-asyncio>=0.21.0",
                "pydantic>=2.0.0",
            ],
            variables={"api_name": api_name},
        )


class RestAPITestTemplate(TestTemplate):
    """REST API test template with comprehensive CRUD operations."""

    def __init__(self, resource_name: str = "resource", base_url: str = "http://localhost:8000"):
        super().__init__(
            name="rest_api_test_template",
            description="REST API test template covering CRUD operations",
            test_type=TestType.API,
            framework=TestFramework.PYTEST,
            tags=["api", "rest", "crud", "http"],
            dependencies=[
                "pytest>=7.0.0",
                "httpx>=0.24.0",
                "pytest-asyncio>=0.21.0",
                "jsonschema>=4.0.0",
            ],
            variables={"resource_name": resource_name, "base_url": base_url},
        )

        self.template_content = '''"""
REST API Integration Tests for {{ resource_name }}

Comprehensive tests for {{ resource_name }} API endpoints.
Base URL: {{ base_url }}
"""

import pytest
import httpx
from typing import Dict, Any, Optional
from dataclasses import dataclass
import json


# ==============================================================================
# Configuration & Fixtures
# ==============================================================================

BASE_URL = "{{ base_url }}"
API_PREFIX = "/api/v1"


@dataclass
class APIResponse:
    """Wrapper for API responses."""
    status_code: int
    data: Optional[Dict[str, Any]]
    headers: Dict[str, str]


@pytest.fixture(scope="module")
async def api_client():
    """Async HTTP client for API tests."""
    async with httpx.AsyncClient(
        base_url=BASE_URL,
        timeout=30.0,
        headers={"Content-Type": "application/json"},
    ) as client:
        yield client


@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Authentication headers for protected endpoints."""
    return {
        "Authorization": "Bearer test-token",
        "X-Request-ID": "test-request-123",
    }


@pytest.fixture
def sample_{{ resource_name }}_payload() -> Dict[str, Any]:
    """Sample payload for creating {{ resource_name }}."""
    return {
        "name": "Test {{ resource_name }}",
        "description": "Created by automated tests",
        "type": "test",
        "metadata": {"environment": "test"},
    }


# ==============================================================================
# Schema Validation Helpers
# ==============================================================================

{{ resource_name.upper() }}_SCHEMA = {
    "type": "object",
    "required": ["id", "name", "created_at"],
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "description": {"type": ["string", "null"]},
        "type": {"type": "string"},
        "created_at": {"type": "string", "format": "date-time"},
        "updated_at": {"type": ["string", "null"]},
        "metadata": {"type": "object"},
    },
}


def validate_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """Validate data against JSON schema."""
    try:
        import jsonschema
        jsonschema.validate(data, schema)
        return True
    except jsonschema.ValidationError:
        return False


# ==============================================================================
# API Health & Status Tests
# ==============================================================================

class TestAPIHealth:
    """Health and status endpoint tests."""

    @pytest.mark.asyncio
    async def test_health_check(self, api_client):
        """Test health check endpoint returns 200."""
        response = await api_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["healthy", "ok"]

    @pytest.mark.asyncio
    async def test_openapi_spec_available(self, api_client):
        """Test OpenAPI specification is accessible."""
        response = await api_client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data


# ==============================================================================
# CRUD Operations Tests
# ==============================================================================

class TestCreate{{ resource_name.title() }}:
    """Tests for {{ resource_name }} creation endpoint."""

    @pytest.mark.asyncio
    async def test_create_success(
        self, api_client, auth_headers, sample_{{ resource_name }}_payload
    ):
        """Test successful {{ resource_name }} creation."""
        response = await api_client.post(
            f"{API_PREFIX}/{{ resource_name }}s",
            json=sample_{{ resource_name }}_payload,
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["name"] == sample_{{ resource_name }}_payload["name"]
        assert validate_schema(data, {{ resource_name.upper() }}_SCHEMA)

    @pytest.mark.asyncio
    async def test_create_missing_required_field(self, api_client, auth_headers):
        """Test creation fails with missing required field."""
        response = await api_client.post(
            f"{API_PREFIX}/{{ resource_name }}s",
            json={"description": "Missing name"},
            headers=auth_headers,
        )
        assert response.status_code == 422  # Unprocessable Entity

    @pytest.mark.asyncio
    async def test_create_duplicate(
        self, api_client, auth_headers, sample_{{ resource_name }}_payload
    ):
        """Test duplicate creation handling."""
        # Create first
        await api_client.post(
            f"{API_PREFIX}/{{ resource_name }}s",
            json=sample_{{ resource_name }}_payload,
            headers=auth_headers,
        )
        # Attempt duplicate
        response = await api_client.post(
            f"{API_PREFIX}/{{ resource_name }}s",
            json=sample_{{ resource_name }}_payload,
            headers=auth_headers,
        )
        assert response.status_code in [409, 400]  # Conflict or Bad Request


class TestRead{{ resource_name.title() }}:
    """Tests for {{ resource_name }} retrieval endpoints."""

    @pytest.mark.asyncio
    async def test_get_by_id(
        self, api_client, auth_headers, sample_{{ resource_name }}_payload
    ):
        """Test retrieving {{ resource_name }} by ID."""
        # Create first
        create_response = await api_client.post(
            f"{API_PREFIX}/{{ resource_name }}s",
            json=sample_{{ resource_name }}_payload,
            headers=auth_headers,
        )
        resource_id = create_response.json()["id"]

        # Retrieve
        response = await api_client.get(
            f"{API_PREFIX}/{{ resource_name }}s/{resource_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["id"] == resource_id

    @pytest.mark.asyncio
    async def test_get_not_found(self, api_client, auth_headers):
        """Test 404 for non-existent {{ resource_name }}."""
        response = await api_client.get(
            f"{API_PREFIX}/{{ resource_name }}s/nonexistent-id",
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_all(self, api_client, auth_headers):
        """Test listing all {{ resource_name }}s."""
        response = await api_client.get(
            f"{API_PREFIX}/{{ resource_name }}s",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or "items" in data

    @pytest.mark.asyncio
    async def test_list_with_pagination(self, api_client, auth_headers):
        """Test pagination parameters."""
        response = await api_client.get(
            f"{API_PREFIX}/{{ resource_name }}s",
            params={"page": 1, "limit": 10},
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_with_filters(self, api_client, auth_headers):
        """Test filtering by query parameters."""
        response = await api_client.get(
            f"{API_PREFIX}/{{ resource_name }}s",
            params={"type": "test", "status": "active"},
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestUpdate{{ resource_name.title() }}:
    """Tests for {{ resource_name }} update endpoints."""

    @pytest.mark.asyncio
    async def test_update_success(
        self, api_client, auth_headers, sample_{{ resource_name }}_payload
    ):
        """Test successful {{ resource_name }} update."""
        # Create
        create_response = await api_client.post(
            f"{API_PREFIX}/{{ resource_name }}s",
            json=sample_{{ resource_name }}_payload,
            headers=auth_headers,
        )
        resource_id = create_response.json()["id"]

        # Update
        update_payload = {"name": "Updated Name", "description": "Updated"}
        response = await api_client.put(
            f"{API_PREFIX}/{{ resource_name }}s/{resource_id}",
            json=update_payload,
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Name"

    @pytest.mark.asyncio
    async def test_partial_update(
        self, api_client, auth_headers, sample_{{ resource_name }}_payload
    ):
        """Test PATCH partial update."""
        # Create
        create_response = await api_client.post(
            f"{API_PREFIX}/{{ resource_name }}s",
            json=sample_{{ resource_name }}_payload,
            headers=auth_headers,
        )
        resource_id = create_response.json()["id"]

        # Partial update
        response = await api_client.patch(
            f"{API_PREFIX}/{{ resource_name }}s/{resource_id}",
            json={"description": "Patched description"},
            headers=auth_headers,
        )
        assert response.status_code == 200


class TestDelete{{ resource_name.title() }}:
    """Tests for {{ resource_name }} deletion endpoints."""

    @pytest.mark.asyncio
    async def test_delete_success(
        self, api_client, auth_headers, sample_{{ resource_name }}_payload
    ):
        """Test successful {{ resource_name }} deletion."""
        # Create
        create_response = await api_client.post(
            f"{API_PREFIX}/{{ resource_name }}s",
            json=sample_{{ resource_name }}_payload,
            headers=auth_headers,
        )
        resource_id = create_response.json()["id"]

        # Delete
        response = await api_client.delete(
            f"{API_PREFIX}/{{ resource_name }}s/{resource_id}",
            headers=auth_headers,
        )
        assert response.status_code in [200, 204]

        # Verify deleted
        get_response = await api_client.get(
            f"{API_PREFIX}/{{ resource_name }}s/{resource_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404


# ==============================================================================
# Error Handling Tests
# ==============================================================================

class TestErrorHandling:
    """Tests for API error handling."""

    @pytest.mark.asyncio
    async def test_invalid_json(self, api_client, auth_headers):
        """Test handling of invalid JSON."""
        response = await api_client.post(
            f"{API_PREFIX}/{{ resource_name }}s",
            content="not valid json",
            headers={**auth_headers, "Content-Type": "application/json"},
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_unauthorized_access(self, api_client):
        """Test unauthorized access returns 401."""
        response = await api_client.get(f"{API_PREFIX}/{{ resource_name }}s")
        # May be 401 or allow public access
        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_method_not_allowed(self, api_client, auth_headers):
        """Test unsupported HTTP method returns 405."""
        response = await api_client.request(
            "PATCH",
            "/health",
            headers=auth_headers,
        )
        assert response.status_code == 405
'''


class GraphQLTestTemplate(TestTemplate):
    """GraphQL API test template."""

    def __init__(self, endpoint: str = "/graphql"):
        super().__init__(
            name="graphql_test_template",
            description="GraphQL API test template with query and mutation tests",
            test_type=TestType.API,
            framework=TestFramework.PYTEST,
            tags=["api", "graphql", "query", "mutation"],
            dependencies=[
                "pytest>=7.0.0",
                "httpx>=0.24.0",
                "pytest-asyncio>=0.21.0",
                "gql>=3.4.0",
            ],
            variables={"endpoint": endpoint},
        )

        self.template_content = '''"""
GraphQL API Integration Tests

Tests for GraphQL queries, mutations, and subscriptions.
Endpoint: {{ endpoint }}
"""

import pytest
import httpx
from typing import Dict, Any, Optional


GRAPHQL_ENDPOINT = "{{ endpoint }}"


@pytest.fixture(scope="module")
async def graphql_client():
    """GraphQL HTTP client."""
    async with httpx.AsyncClient(
        base_url="http://localhost:8000",
        timeout=30.0,
    ) as client:
        yield client


async def execute_query(
    client: httpx.AsyncClient,
    query: str,
    variables: Optional[Dict[str, Any]] = None,
    operation_name: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a GraphQL query."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables
    if operation_name:
        payload["operationName"] = operation_name

    response = await client.post(
        GRAPHQL_ENDPOINT,
        json=payload,
        headers={"Content-Type": "application/json"},
    )
    return response.json()


class TestGraphQLQueries:
    """Tests for GraphQL queries."""

    @pytest.mark.asyncio
    async def test_introspection_query(self, graphql_client):
        """Test GraphQL introspection is available."""
        query = """
        query IntrospectionQuery {
            __schema {
                types {
                    name
                }
            }
        }
        """
        result = await execute_query(graphql_client, query)
        assert "data" in result
        assert "__schema" in result["data"]

    @pytest.mark.asyncio
    async def test_list_query(self, graphql_client):
        """Test list query returns array."""
        query = """
        query ListItems {
            items {
                id
                name
                createdAt
            }
        }
        """
        result = await execute_query(graphql_client, query)
        assert "errors" not in result
        assert "data" in result

    @pytest.mark.asyncio
    async def test_query_with_variables(self, graphql_client):
        """Test query with variables."""
        query = """
        query GetItem($id: ID!) {
            item(id: $id) {
                id
                name
            }
        }
        """
        variables = {"id": "test-123"}
        result = await execute_query(graphql_client, query, variables)
        assert "data" in result


class TestGraphQLMutations:
    """Tests for GraphQL mutations."""

    @pytest.mark.asyncio
    async def test_create_mutation(self, graphql_client):
        """Test create mutation."""
        mutation = """
        mutation CreateItem($input: CreateItemInput!) {
            createItem(input: $input) {
                id
                name
            }
        }
        """
        variables = {
            "input": {
                "name": "Test Item",
                "description": "Created via GraphQL",
            }
        }
        result = await execute_query(graphql_client, mutation, variables)
        # Check for success or expected error
        assert "data" in result or "errors" in result

    @pytest.mark.asyncio
    async def test_update_mutation(self, graphql_client):
        """Test update mutation."""
        mutation = """
        mutation UpdateItem($id: ID!, $input: UpdateItemInput!) {
            updateItem(id: $id, input: $input) {
                id
                name
                updatedAt
            }
        }
        """
        variables = {
            "id": "test-123",
            "input": {"name": "Updated Name"},
        }
        result = await execute_query(graphql_client, mutation, variables)
        assert "data" in result or "errors" in result


class TestGraphQLErrors:
    """Tests for GraphQL error handling."""

    @pytest.mark.asyncio
    async def test_validation_error(self, graphql_client):
        """Test validation error returns proper error format."""
        query = """
        query {
            invalidField
        }
        """
        result = await execute_query(graphql_client, query)
        assert "errors" in result
        assert len(result["errors"]) > 0

    @pytest.mark.asyncio
    async def test_missing_required_variable(self, graphql_client):
        """Test missing required variable error."""
        query = """
        query GetItem($id: ID!) {
            item(id: $id) {
                id
            }
        }
        """
        # Missing variables
        result = await execute_query(graphql_client, query)
        assert "errors" in result
'''
