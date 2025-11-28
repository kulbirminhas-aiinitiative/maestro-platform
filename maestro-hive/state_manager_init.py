#!/usr/bin/env python3
"""
StateManager Initialization Helper

Provides easy initialization of StateManager with SQLite (for testing) and
optional Redis. Handles all the async setup complexity.

Usage:
    from state_manager_init import init_state_manager_for_testing

    # For testing/development (SQLite + mock Redis)
    state_mgr = await init_state_manager_for_testing()

    # For production (PostgreSQL + real Redis)
    state_mgr = await init_state_manager_for_production()
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Optional

# Add claude_team_sdk to path
CLAUDE_TEAM_SDK_PATH = Path(__file__).parent.parent / "shared" / "claude_team_sdk"
sys.path.insert(0, str(CLAUDE_TEAM_SDK_PATH))

from persistence import (
    DatabaseManager,
    DatabaseConfig,
    RedisManager,
    StateManager
)

logger = logging.getLogger(__name__)


class MockRedisManager:
    """
    Mock Redis manager for testing when Redis is not available.

    Provides the same interface as RedisManager but stores everything in memory.
    No pub/sub functionality, but won't crash if Redis is down.
    """

    def __init__(self):
        self.store = {}
        self.lists = {}
        logger.info("⚠️  Using MockRedisManager (Redis not available)")

    async def initialize(self):
        """Mock initialization"""
        pass

    async def close(self):
        """Mock close"""
        pass

    async def health_check(self) -> bool:
        """Always healthy"""
        return True

    async def get(self, key: str) -> Optional[str]:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        self.store[key] = value
        return True

    async def set_json(self, key: str, value: dict, expire: Optional[int] = None) -> bool:
        import json
        self.store[key] = json.dumps(value)
        return True

    async def get_json(self, key: str) -> Optional[dict]:
        import json
        value = self.store.get(key)
        return json.loads(value) if value else None

    async def delete(self, *keys: str) -> int:
        count = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                count += 1
        return count

    async def lpush(self, key: str, *values: str) -> int:
        if key not in self.lists:
            self.lists[key] = []
        self.lists[key].extend(values)
        return len(self.lists[key])

    async def expire(self, key: str, seconds: int) -> bool:
        return True  # Mock - doesn't actually expire

    async def publish_event(self, channel: str, event_type: str, data: dict) -> int:
        """Mock publish - does nothing"""
        logger.debug(f"Mock publish to {channel}: {event_type}")
        return 0  # No subscribers

    async def acquire_lock(self, lock_name: str, timeout: int = 10, blocking_timeout: Optional[float] = None) -> bool:
        """Mock lock - always succeeds"""
        return True

    async def release_lock(self, lock_name: str):
        """Mock release - does nothing"""
        pass


async def init_state_manager_for_testing(
    db_path: str = "./test_maestro.db",
    use_mock_redis: bool = True
) -> StateManager:
    """
    Initialize StateManager for testing/development.

    Uses SQLite for database and MockRedisManager for Redis.
    Perfect for local development and CI/CD.

    Args:
        db_path: Path to SQLite database file
        use_mock_redis: If True, use mock Redis (no Redis server needed)

    Returns:
        Initialized StateManager instance
    """
    logger.info("="*80)
    logger.info("🔧 Initializing StateManager for Testing")
    logger.info("="*80)

    # Initialize database (SQLite)
    logger.info(f"📊 Setting up SQLite database: {db_path}")
    db_conn_string = f"sqlite+aiosqlite:///{db_path}"
    db_manager = DatabaseManager(db_conn_string, pool_size=5, echo=False)
    await db_manager.initialize()
    logger.info("✅ SQLite database initialized")

    # Initialize Redis (or mock)
    if use_mock_redis:
        redis_manager = MockRedisManager()
        await redis_manager.initialize()
    else:
        logger.info("📡 Connecting to Redis...")
        try:
            redis_manager = RedisManager(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "6379")),
                db=int(os.getenv("REDIS_DB", "0"))
            )
            await redis_manager.initialize()
            logger.info("✅ Redis initialized")
        except Exception as e:
            logger.warning(f"⚠️  Redis connection failed: {e}")
            logger.info("   Falling back to MockRedisManager")
            redis_manager = MockRedisManager()
            await redis_manager.initialize()

    # Create StateManager
    logger.info("🔗 Creating StateManager...")
    state_manager = StateManager(
        db_manager=db_manager,
        redis_manager=redis_manager,
        cache_ttl=300
    )
    logger.info("✅ StateManager initialized")
    logger.info("="*80)

    return state_manager


async def init_state_manager_for_production(
    postgres_url: Optional[str] = None,
    redis_host: str = "localhost",
    redis_port: int = 6379,
    redis_password: Optional[str] = None
) -> StateManager:
    """
    Initialize StateManager for production.

    Uses PostgreSQL for database and real Redis.

    Args:
        postgres_url: PostgreSQL connection URL (or uses DATABASE_URL env var)
        redis_host: Redis host
        redis_port: Redis port
        redis_password: Redis password (if required)

    Returns:
        Initialized StateManager instance
    """
    logger.info("="*80)
    logger.info("🚀 Initializing StateManager for Production")
    logger.info("="*80)

    # Get database URL
    if postgres_url is None:
        postgres_url = os.getenv("DATABASE_URL")
        if postgres_url is None:
            postgres_url = DatabaseConfig.from_env()

    logger.info(f"📊 Connecting to PostgreSQL...")
    db_manager = DatabaseManager(postgres_url, pool_size=20, max_overflow=40)
    await db_manager.initialize()
    logger.info("✅ PostgreSQL initialized")

    # Initialize Redis
    logger.info(f"📡 Connecting to Redis at {redis_host}:{redis_port}...")
    redis_manager = RedisManager(
        host=redis_host,
        port=redis_port,
        password=redis_password
    )
    await redis_manager.initialize()
    logger.info("✅ Redis initialized")

    # Create StateManager
    logger.info("🔗 Creating StateManager...")
    state_manager = StateManager(
        db_manager=db_manager,
        redis_manager=redis_manager,
        cache_ttl=600  # 10 minutes for production
    )
    logger.info("✅ StateManager initialized")
    logger.info("="*80)

    return state_manager


async def cleanup_state_manager(state_manager: StateManager):
    """
    Properly cleanup StateManager resources.

    Args:
        state_manager: StateManager instance to cleanup
    """
    logger.info("🧹 Cleaning up StateManager...")
    await state_manager.db.close()
    await state_manager.redis.close()
    logger.info("✅ StateManager cleaned up")


# Example usage
if __name__ == "__main__":
    async def test():
        # Test initialization
        state_mgr = await init_state_manager_for_testing()

        # Test database
        health = await state_mgr.db.health_check()
        print(f"Database health: {health}")

        # Test Redis
        redis_health = await state_mgr.redis.health_check()
        print(f"Redis health: {redis_health}")

        # Cleanup
        await cleanup_state_manager(state_mgr)

    asyncio.run(test())
