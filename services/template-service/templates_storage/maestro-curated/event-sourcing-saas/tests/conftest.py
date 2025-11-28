"""Pytest configuration and fixtures."""
import asyncio
import pytest
import asyncpg
from typing import AsyncGenerator


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_pool() -> AsyncGenerator:
    """Create database connection pool for tests."""
    pool = await asyncpg.create_pool(
        host="localhost",
        port=5432,
        database="eventsourcing_test",
        user="postgres",
        password="postgres",
        min_size=1,
        max_size=5
    )

    yield pool

    await pool.close()


@pytest.fixture(autouse=True)
async def setup_test_database(db_pool):
    """Setup and teardown test database."""
    # Setup - run migrations
    async with db_pool.acquire() as conn:
        # Clean tables
        await conn.execute("TRUNCATE TABLE events CASCADE")
        await conn.execute("TRUNCATE TABLE snapshots CASCADE")
        await conn.execute("TRUNCATE TABLE read_model_entities CASCADE")

    yield

    # Teardown handled by truncate in next test