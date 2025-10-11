"""
Pytest configuration and fixtures for Maestro ML tests
"""
import asyncio
import sys
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from fastapi.testclient import TestClient
from httpx import AsyncClient

# Add project root to Python path FIRST
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Also ensure maestro_ml parent is in path
maestro_ml_parent = os.path.dirname(project_root)
if maestro_ml_parent not in sys.path:
    sys.path.insert(0, maestro_ml_parent)

# Test database URL - using in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Now import application modules
Base = None
get_db = None
app = None

try:
    # Import database models
    from maestro_ml.models.database import Base as _Base
    from maestro_ml.core.database import get_db as _get_db
    Base = _Base
    get_db = _get_db
    print("✅ Successfully imported database modules")
except ImportError as e:
    print(f"⚠️  Database import failed (will use mocks): {e}")
    # Create a mock Base for tests that don't need real DB
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()

try:
    # Import FastAPI app
    from maestro_ml.api.main import app as _app
    app = _app
    print("✅ Successfully imported FastAPI app")
except ImportError as e:
    print(f"⚠️  App import failed (will use mocks): {e}")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def async_engine():
    """Create test database engine"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False}
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session"""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(async_session) -> AsyncGenerator[AsyncClient, None]:
    """Create test HTTP client with database override"""

    async def override_get_db():
        yield async_session

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest.fixture
def sync_client():
    """Create synchronous test client"""
    return TestClient(app)


@pytest.fixture
def settings():
    """Get settings (lazy-loaded)"""
    from maestro_ml.config.settings import get_settings
    return get_settings()
