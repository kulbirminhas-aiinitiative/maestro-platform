"""
Pytest configuration and fixtures for template service tests.
"""

import asyncio
from typing import AsyncGenerator, Generator
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient

# Test configuration
TEST_DATABASE_URL = "postgresql://maestro:test@localhost:5432/maestro_templates_test"
TEST_REDIS_URL = "redis://localhost:6379/15"  # Use separate DB for tests


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def test_redis_client():
    """Provide a Redis client for testing."""
    import redis.asyncio as redis

    client = redis.from_url(TEST_REDIS_URL, decode_responses=True)

    yield client

    # Cleanup
    await client.flushdb()
    await client.close()


@pytest_asyncio.fixture
async def test_db_session():
    """Provide a database session for testing."""
    # TODO: Implement database session fixture
    # This would create a test database session and clean up after tests
    pass


@pytest.fixture
def test_tenant_id() -> str:
    """Provide a test tenant ID."""
    return f"test-tenant-{uuid4()}"


@pytest.fixture
def test_user_id() -> str:
    """Provide a test user ID."""
    return f"test-user-{uuid4()}"


@pytest.fixture
def sample_template_data(test_tenant_id: str) -> dict:
    """Provide sample template data for testing."""
    return {
        "name": "Test Backend API Template",
        "category": "backend_developer",
        "version": "1.0.0",
        "description": "A test template for backend APIs",
        "tenant_id": test_tenant_id,
        "manifest": {
            "dependencies": {
                "fastapi": "^0.104.0",
                "sqlalchemy": "^2.0.0"
            },
            "files": [
                "src/main.py",
                "src/models.py",
                "tests/test_main.py"
            ]
        },
        "tags": ["api", "backend", "fastapi"]
    }


@pytest.fixture
def sample_workflow_data(test_tenant_id: str) -> dict:
    """Provide sample workflow data for testing."""
    return {
        "name": "Test Workflow",
        "description": "A test workflow",
        "tenant_id": test_tenant_id,
        "definition": {
            "steps": [
                {
                    "name": "Setup",
                    "action": "initialize",
                    "parameters": {}
                },
                {
                    "name": "Execute",
                    "action": "run_template",
                    "parameters": {
                        "template_id": "test-template"
                    }
                }
            ]
        }
    }


@pytest_asyncio.fixture
async def template_message_handler(test_redis_client):
    """Provide a TemplateMessageHandler for testing."""
    from template_service.message_handler import TemplateMessageHandler

    handler = TemplateMessageHandler(
        redis_url=TEST_REDIS_URL,
        consumer_name=f"test-worker-{uuid4()}"
    )

    await handler.start()

    yield handler

    await handler.stop()


# Mock fixtures
@pytest.fixture
def mock_git_manager():
    """Provide a mock GitManager for testing."""
    class MockGitManager:
        async def commit(self, message: str):
            pass

        async def get_versions(self, file_path: str):
            return [
                {"version": "1.0.0", "timestamp": "2025-10-26T10:00:00Z"},
                {"version": "0.9.0", "timestamp": "2025-10-25T10:00:00Z"}
            ]

        async def sync(self):
            pass

    return MockGitManager()


@pytest.fixture
def mock_cache_manager():
    """Provide a mock CacheManager for testing."""
    class MockCacheManager:
        def __init__(self):
            self._cache = {}

        async def get(self, key: str):
            return self._cache.get(key)

        async def set(self, key: str, value: any, ttl: int = 300):
            self._cache[key] = value

        async def delete(self, key: str):
            self._cache.pop(key, None)

        async def clear(self):
            self._cache.clear()

    return MockCacheManager()
