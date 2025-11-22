"""
MAESTRO Core Database Library

Enterprise-grade database abstraction layer with SQLAlchemy 2.0, connection pooling,
migrations, caching, and monitoring. Follows patterns used by companies like Instagram,
Dropbox, and Reddit.

Usage:
    from maestro_core_db import DatabaseManager, BaseModel, create_session

    # Configure database
    db_manager = DatabaseManager(
        url="postgresql+asyncpg://user:pass@localhost/db",
        pool_size=20,
        enable_query_logging=True
    )

    # Initialize database
    await db_manager.initialize()

    # Use in application
    async with create_session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

    # Define models
    class User(BaseModel):
        __tablename__ = "users"

        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        username: Mapped[str] = mapped_column(String(50), unique=True)
        email: Mapped[str] = mapped_column(String(255), unique=True)
"""

from .manager import DatabaseManager
from .base import BaseModel, BaseRepository
from .session import create_session, get_session, SessionManager
from .migrations import MigrationManager
from .cache import QueryCache, CacheManager
from .monitoring import DatabaseMonitor
from .connection import ConnectionManager, ConnectionPool
from .exceptions import (
    DatabaseException,
    ConnectionException,
    MigrationException,
    QueryException
)

__version__ = "1.0.0"
__all__ = [
    # Core classes
    "DatabaseManager",
    "BaseModel",
    "BaseRepository",

    # Session management
    "create_session",
    "get_session",
    "SessionManager",

    # Migrations
    "MigrationManager",

    # Caching
    "QueryCache",
    "CacheManager",

    # Monitoring
    "DatabaseMonitor",

    # Connection management
    "ConnectionManager",
    "ConnectionPool",

    # Exceptions
    "DatabaseException",
    "ConnectionException",
    "MigrationException",
    "QueryException",
]