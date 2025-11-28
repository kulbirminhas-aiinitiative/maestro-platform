"""
Comprehensive Test Configuration and Fixtures
Provides extensive fixtures for all test scenarios
"""

import pytest
import asyncio
import asyncpg
from datetime import datetime, timedelta
from typing import Dict, List, Any, Generator
from unittest.mock import Mock, AsyncMock, patch
import json
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
import redis.asyncio as redis

# Import application modules
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app
from auth import create_access_token, User, create_user, USERS_DB


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom settings"""
    config.addinivalue_line(
        "markers", "quality_fabric: Mark test for quality-fabric tracking"
    )


# ============================================================================
# Event Loop Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Test Client Fixtures
# ============================================================================

@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """FastAPI test client"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="module")
def async_client():
    """Async test client for async operations"""
    from httpx import AsyncClient
    async def _get_client():
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    return _get_client


# ============================================================================
# Authentication Fixtures
# ============================================================================

@pytest.fixture
def auth_headers() -> Dict[str, str]:
    """Get authentication headers with valid token"""
    token = create_access_token(
        data={
            "sub": "test_user",
            "email": "test@example.com",
            "scopes": ["templates:read", "templates:write"]
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def admin_headers() -> Dict[str, str]:
    """Get admin authentication headers"""
    token = create_access_token(
        data={
            "sub": "admin",
            "email": "admin@example.com",
            "scopes": ["admin", "templates:read", "templates:write", "templates:delete"]
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers() -> Dict[str, str]:
    """Get viewer (read-only) authentication headers"""
    token = create_access_token(
        data={
            "sub": "viewer",
            "email": "viewer@example.com",
            "scopes": ["templates:read"]
        }
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def expired_token() -> str:
    """Generate expired token for testing"""
    return create_access_token(
        data={"sub": "test_user", "email": "test@example.com", "scopes": []},
        expires_delta=timedelta(seconds=-1)
    )


@pytest.fixture
def invalid_token() -> str:
    """Generate invalid token for testing"""
    return "invalid.token.here"


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def test_user() -> User:
    """Create test user"""
    return User(
        username="test_user",
        email="test@example.com",
        full_name="Test User",
        disabled=False,
        is_admin=False,
        scopes=["templates:read", "templates:write"]
    )


@pytest.fixture
def admin_user() -> User:
    """Create admin user"""
    return User(
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        disabled=False,
        is_admin=True,
        scopes=["admin", "templates:read", "templates:write", "templates:delete"]
    )


# ============================================================================
# Template Fixtures
# ============================================================================

@pytest.fixture
def sample_template() -> Dict[str, Any]:
    """Create sample template data"""
    return {
        "id": str(uuid.uuid4()),
        "name": "react-typescript-app",
        "version": "1.0.0",
        "description": "React TypeScript application template",
        "category": "frontend",
        "language": "typescript",
        "framework": "react",
        "persona": "frontend_developer",
        "quality_score": 85,
        "quality_tier": "gold",
        "tags": ["react", "typescript", "spa"],
        "dependencies": ["node>=18", "npm>=9"],
        "metadata": {
            "author": "MAESTRO Team",
            "license": "MIT",
            "created_at": datetime.utcnow().isoformat()
        }
    }


@pytest.fixture
def template_list() -> List[Dict[str, Any]]:
    """Create list of template data"""
    templates = []
    categories = ["frontend", "backend", "devops", "database"]
    languages = ["python", "javascript", "typescript", "go"]

    for i in range(20):
        templates.append({
            "id": str(uuid.uuid4()),
            "name": f"template-{i}",
            "version": "1.0.0",
            "description": f"Test template {i}",
            "category": categories[i % len(categories)],
            "language": languages[i % len(languages)],
            "quality_score": 70 + (i % 30),
            "tags": [f"tag{i}", "test"]
        })

    return templates


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
async def db_pool():
    """Create test database connection pool"""
    pool = await asyncpg.create_pool(
        "postgresql://test_user:test_pass@localhost:5432/test_db",
        min_size=1,
        max_size=5
    )
    yield pool
    await pool.close()


@pytest.fixture
async def db_connection(db_pool):
    """Get database connection from pool"""
    async with db_pool.acquire() as conn:
        yield conn


@pytest.fixture
def mock_db():
    """Mock database connection"""
    mock = AsyncMock()
    mock.fetch.return_value = []
    mock.fetchrow.return_value = None
    mock.execute.return_value = None
    return mock


# ============================================================================
# Cache/Redis Fixtures
# ============================================================================

@pytest.fixture
async def redis_client():
    """Create Redis client for testing"""
    client = await redis.from_url("redis://localhost:6379/0")
    yield client
    await client.close()


@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    mock = AsyncMock()
    mock.get.return_value = None
    mock.set.return_value = True
    mock.delete.return_value = 1
    return mock


# ============================================================================
# File System Fixtures
# ============================================================================

@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage directory"""
    storage = tmp_path / "storage"
    storage.mkdir()
    (storage / "templates").mkdir()
    (storage / "cache").mkdir()
    (storage / "git").mkdir()
    return storage


@pytest.fixture
def sample_template_file(temp_storage):
    """Create sample template file"""
    template_dir = temp_storage / "templates" / "sample-template"
    template_dir.mkdir(parents=True)

    manifest = {
        "name": "sample-template",
        "version": "1.0.0",
        "description": "Sample template",
        "files": ["src/main.py", "README.md"]
    }

    manifest_file = template_dir / "manifest.json"
    manifest_file.write_text(json.dumps(manifest))

    return template_dir


# ============================================================================
# Mock Service Fixtures
# ============================================================================

@pytest.fixture
def mock_git_manager():
    """Mock Git manager"""
    mock = Mock()
    mock.clone_repository = AsyncMock(return_value="/tmp/repo")
    mock.get_file_content = AsyncMock(return_value="file content")
    mock.list_files = AsyncMock(return_value=["file1.py", "file2.py"])
    return mock


@pytest.fixture
def mock_cache_manager():
    """Mock cache manager"""
    mock = Mock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=True)
    mock.clear = AsyncMock(return_value=True)
    return mock


# ============================================================================
# Quality Fabric Integration Fixtures
# ============================================================================

@pytest.fixture
def quality_fabric_client():
    """Quality-fabric API client for test metrics"""
    class QualityFabricClient:
        def __init__(self):
            self.base_url = "http://localhost:8004/api/v1"
            self.metrics = []

        async def track_test_execution(self, test_name, duration, status, coverage):
            metric = {
                "test_name": test_name,
                "duration": duration,
                "status": status,
                "coverage": coverage,
                "timestamp": datetime.utcnow().isoformat()
            }
            self.metrics.append(metric)

        async def get_quality_score(self):
            return {"score": 85, "grade": "B+"}

    return QualityFabricClient()


@pytest.fixture(autouse=True)
def track_test_quality(request, quality_fabric_client):
    """Automatically track test quality metrics"""
    start_time = datetime.utcnow()

    yield

    # Calculate test duration
    duration = (datetime.utcnow() - start_time).total_seconds()

    # Track in quality-fabric
    if hasattr(request.node, 'rep_call'):
        status = "passed" if request.node.rep_call.passed else "failed"
        asyncio.create_task(
            quality_fabric_client.track_test_execution(
                test_name=request.node.name,
                duration=duration,
                status=status,
                coverage=0  # Would be populated from coverage plugin
            )
        )


# ============================================================================
# Performance Testing Fixtures
# ============================================================================

@pytest.fixture
def performance_timer():
    """Timer for performance testing"""
    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = datetime.utcnow()

        def stop(self):
            self.end_time = datetime.utcnow()

        @property
        def elapsed_ms(self):
            if self.start_time and self.end_time:
                return (self.end_time - self.start_time).total_seconds() * 1000
            return None

    return Timer()


# ============================================================================
# Data Generation Fixtures
# ============================================================================

@pytest.fixture
def fake_data_generator():
    """Generate fake data for testing"""
    from faker import Faker
    fake = Faker()

    class DataGenerator:
        def __init__(self):
            self.fake = fake

        def template(self):
            return {
                "name": self.fake.slug(),
                "version": f"{self.fake.random_int(1, 5)}.0.0",
                "description": self.fake.sentence(),
                "category": self.fake.random_element(["frontend", "backend", "devops"]),
                "language": self.fake.random_element(["python", "javascript", "go"]),
                "author": self.fake.name(),
                "email": self.fake.email()
            }

        def user(self):
            return {
                "username": self.fake.user_name(),
                "email": self.fake.email(),
                "full_name": self.fake.name()
            }

    return DataGenerator()


# ============================================================================
# Environment Fixtures
# ============================================================================

@pytest.fixture
def test_env_vars(monkeypatch):
    """Set test environment variables"""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("JWT_SECRET_KEY", "test_secret_key_minimum_32_characters_long")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
