"""
Database manager for PostgreSQL connections
Handles connection pooling, session management, and migrations
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.pool import NullPool
from sqlalchemy import text

from .models import Base


class DatabaseManager:
    """
    Manages PostgreSQL database connections with async support
    """

    def __init__(
        self,
        connection_string: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        echo: bool = False
    ):
        """
        Initialize database manager

        Args:
            connection_string: PostgreSQL connection string
                              e.g., "postgresql+asyncpg://user:pass@localhost/dbname"
            pool_size: Connection pool size
            max_overflow: Max connections beyond pool_size
            echo: Echo SQL statements (debug mode)
        """
        self.connection_string = connection_string
        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        self.echo = echo

    async def initialize(self):
        """Initialize database engine and create tables"""
        self.engine = create_async_engine(
            self.connection_string,
            echo=self.echo,
            pool_size=self.pool_size,
            max_overflow=self.max_overflow,
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,  # Recycle connections after 1 hour
        )

        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        # Create all tables
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self):
        """Close database connections"""
        if self.engine:
            await self.engine.dispose()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session context manager

        Usage:
            async with db_manager.session() as session:
                result = await session.execute(...)
        """
        if not self.session_factory:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        session = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def health_check(self) -> bool:
        """Check database connectivity"""
        try:
            async with self.session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            print(f"Database health check failed: {e}")
            return False

    async def get_table_counts(self) -> dict:
        """Get row counts for all tables (useful for monitoring)"""
        counts = {}
        async with self.session() as session:
            for table in Base.metadata.tables.keys():
                result = await session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                counts[table] = result.scalar()
        return counts


async def init_database(connection_string: str, **kwargs) -> DatabaseManager:
    """
    Convenience function to initialize database

    Args:
        connection_string: PostgreSQL connection string
        **kwargs: Additional arguments for DatabaseManager

    Returns:
        Initialized DatabaseManager instance
    """
    db = DatabaseManager(connection_string, **kwargs)
    await db.initialize()
    return db


class DatabaseConfig:
    """Database configuration helper"""

    @staticmethod
    def from_env() -> str:
        """Build connection string from environment variables"""
        import os

        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        host = os.getenv("POSTGRES_HOST", "localhost")
        port = os.getenv("POSTGRES_PORT", "5432")
        database = os.getenv("POSTGRES_DB", "claude_team")

        return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}"

    @staticmethod
    def for_testing() -> str:
        """Get connection string for testing (uses SQLite)"""
        return "sqlite+aiosqlite:///./test_claude_team.db"

    @staticmethod
    def local_postgres(database: str = "claude_team") -> str:
        """Get connection string for local PostgreSQL"""
        return f"postgresql+asyncpg://postgres:postgres@localhost:5432/{database}"

    @staticmethod
    def from_settings() -> str:
        """Build connection string from dynaconf settings"""
        try:
            from claude_team_sdk.config import get_database_url
            return get_database_url()
        except ImportError:
            # Fallback if config not available
            return DatabaseConfig.from_env()


# Example usage and testing
if __name__ == "__main__":
    async def test_database():
        """Test database connectivity"""
        # Use SQLite for quick testing
        db = await init_database(DatabaseConfig.for_testing())

        print("✓ Database initialized")

        # Health check
        healthy = await db.health_check()
        print(f"✓ Health check: {'OK' if healthy else 'FAILED'}")

        # Get table counts
        counts = await db.get_table_counts()
        print(f"✓ Table counts: {counts}")

        # Test session
        async with db.session() as session:
            from .models import Message, MessageType
            import uuid

            msg = Message(
                id=str(uuid.uuid4()),
                team_id="test_team",
                from_agent="test_agent",
                message_type=MessageType.INFO,
                content="Test message"
            )
            session.add(msg)

        print("✓ Test message created")

        # Verify
        counts = await db.get_table_counts()
        print(f"✓ Updated table counts: {counts}")

        await db.close()
        print("✓ Database closed")

    asyncio.run(test_database())
