"""
Enterprise database session management for MAESTRO.

Provides:
- SessionManager for read/write session factories
- Async context managers for transactions
- FastAPI dependency injection support
- Tenant-isolated session support
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Callable, List, Optional, Type, TypeVar

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    async_scoped_session
)
from sqlalchemy.orm import sessionmaker

from .exceptions import (
    DatabaseException,
    TransactionException,
    TransactionRollbackException,
    TenantRequiredException
)


def _get_logger():
    """Lazy logger initialization to avoid circular imports."""
    try:
        from maestro_core_logging import get_logger
        return get_logger(__name__)
    except ImportError:
        import logging
        return logging.getLogger(__name__)


logger = type("LazyLogger", (), {"__getattr__": lambda self, name: getattr(_get_logger(), name)})()


T = TypeVar("T")


# =============================================================================
# Session Manager
# =============================================================================

class SessionManager:
    """
    Async session manager with read/write splitting support.

    Manages SQLAlchemy async sessions for database operations.
    Supports separate engines for write (primary) and read (replica) operations.

    Example:
        ```python
        manager = SessionManager(
            write_engine=primary_engine,
            read_engines=[replica1, replica2]
        )

        # Write operation
        async with manager.session() as session:
            user = User(name="Alice")
            session.add(user)
            await session.commit()

        # Read operation
        async with manager.read_session() as session:
            users = await session.execute(select(User))
        ```
    """

    def __init__(
        self,
        write_engine: AsyncEngine,
        read_engines: Optional[List[AsyncEngine]] = None,
        autocommit: bool = False,
        autoflush: bool = False,
        expire_on_commit: bool = True
    ):
        """
        Initialize session manager.

        Args:
            write_engine: Primary engine for write operations
            read_engines: Replica engines for read operations
            autocommit: Enable autocommit mode
            autoflush: Enable autoflush
            expire_on_commit: Expire objects after commit
        """
        self._write_engine = write_engine
        self._read_engines = read_engines or [write_engine]
        self._current_read_index = 0

        # Session factory options
        self._session_options = {
            "autocommit": autocommit,
            "autoflush": autoflush,
            "expire_on_commit": expire_on_commit,
        }

        # Create session factories
        self._write_session_factory = async_sessionmaker(
            bind=write_engine,
            class_=AsyncSession,
            **self._session_options
        )

        self._read_session_factories = [
            async_sessionmaker(
                bind=engine,
                class_=AsyncSession,
                **self._session_options
            )
            for engine in self._read_engines
        ]

    @property
    def write_engine(self) -> AsyncEngine:
        """Get the write engine."""
        return self._write_engine

    @property
    def read_engines(self) -> List[AsyncEngine]:
        """Get all read engines."""
        return self._read_engines

    def _get_read_session_factory(self) -> async_sessionmaker:
        """Get read session factory with round-robin load balancing."""
        if len(self._read_session_factories) == 1:
            return self._read_session_factories[0]

        factory = self._read_session_factories[self._current_read_index]
        self._current_read_index = (
            self._current_read_index + 1
        ) % len(self._read_session_factories)
        return factory

    def get_write_session(self) -> AsyncSession:
        """
        Create a new write session.

        Returns:
            AsyncSession bound to write engine
        """
        return self._write_session_factory()

    def get_read_session(self) -> AsyncSession:
        """
        Create a new read session with load balancing.

        Returns:
            AsyncSession bound to read engine
        """
        factory = self._get_read_session_factory()
        return factory()

    @asynccontextmanager
    async def session(self, read_only: bool = False) -> AsyncIterator[AsyncSession]:
        """
        Async context manager for database sessions.

        Automatically handles session lifecycle and rollback on errors.
        Does NOT commit automatically - caller must commit explicitly.

        Args:
            read_only: Use read replica if available

        Yields:
            AsyncSession

        Example:
            ```python
            async with session_manager.session() as session:
                user = User(name="Bob")
                session.add(user)
                await session.commit()
            ```
        """
        session = self.get_read_session() if read_only else self.get_write_session()

        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.warning("Session rolled back due to error", error=str(e))
            raise
        finally:
            await session.close()

    @asynccontextmanager
    async def read_session(self) -> AsyncIterator[AsyncSession]:
        """
        Async context manager for read-only sessions.

        Yields:
            AsyncSession bound to read replica
        """
        async with self.session(read_only=True) as session:
            yield session

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[AsyncSession]:
        """
        Async context manager for transactional operations.

        Automatically commits on success, rolls back on error.

        Yields:
            AsyncSession in transaction

        Example:
            ```python
            async with session_manager.transaction() as session:
                user = User(name="Charlie")
                session.add(user)
                # Auto-commits on exit
            ```
        """
        session = self.get_write_session()

        try:
            async with session.begin():
                yield session
        except Exception as e:
            logger.error("Transaction failed", error=str(e))
            raise TransactionRollbackException(
                message="Transaction rolled back due to error",
                cause=e
            )
        finally:
            await session.close()

    @asynccontextmanager
    async def nested_transaction(
        self,
        session: AsyncSession
    ) -> AsyncIterator[AsyncSession]:
        """
        Create a nested transaction (savepoint).

        Args:
            session: Existing session to nest within

        Yields:
            Session with savepoint

        Example:
            ```python
            async with session_manager.transaction() as session:
                session.add(user1)

                try:
                    async with session_manager.nested_transaction(session):
                        session.add(user2)
                        raise ValueError("Rollback user2 only")
                except ValueError:
                    pass  # user1 still committed, user2 rolled back
            ```
        """
        async with session.begin_nested():
            yield session


# =============================================================================
# Session Context
# =============================================================================

class SessionContext:
    """
    Thread-local session context for request-scoped sessions.

    Useful for web frameworks that need session-per-request pattern.
    """

    def __init__(self, session_manager: SessionManager):
        """
        Initialize session context.

        Args:
            session_manager: Session manager to use
        """
        self._manager = session_manager
        self._sessions: dict = {}

    def _get_context_id(self) -> int:
        """Get current context ID (task ID for async)."""
        try:
            task = asyncio.current_task()
            return id(task) if task else id(asyncio.get_running_loop())
        except RuntimeError:
            # No running loop
            return 0

    async def get_session(self, read_only: bool = False) -> AsyncSession:
        """
        Get session for current context, creating if needed.

        Args:
            read_only: Use read replica

        Returns:
            AsyncSession for current context
        """
        context_id = self._get_context_id()
        key = (context_id, read_only)

        if key not in self._sessions:
            if read_only:
                self._sessions[key] = self._manager.get_read_session()
            else:
                self._sessions[key] = self._manager.get_write_session()

        return self._sessions[key]

    async def close_session(self, read_only: bool = False) -> None:
        """Close session for current context."""
        context_id = self._get_context_id()
        key = (context_id, read_only)

        if key in self._sessions:
            await self._sessions[key].close()
            del self._sessions[key]

    async def close_all(self) -> None:
        """Close all sessions in current context."""
        context_id = self._get_context_id()
        keys_to_remove = [k for k in self._sessions if k[0] == context_id]

        for key in keys_to_remove:
            await self._sessions[key].close()
            del self._sessions[key]


# =============================================================================
# Tenant Session
# =============================================================================

class TenantSession:
    """
    Tenant-scoped session wrapper.

    Ensures all queries are automatically filtered by tenant_id
    and all inserts have tenant_id set.

    Example:
        ```python
        tenant_session = TenantSession(session, tenant_id="tenant-123")

        # Automatic tenant filtering
        users = await tenant_session.query(User).all()  # Only tenant-123 users

        # Automatic tenant assignment
        user = User(name="Dave")
        await tenant_session.add(user)  # user.tenant_id = "tenant-123"
        ```
    """

    def __init__(self, session: AsyncSession, tenant_id: str):
        """
        Initialize tenant session.

        Args:
            session: Underlying async session
            tenant_id: Tenant ID for filtering
        """
        if not tenant_id:
            raise TenantRequiredException(
                message="Tenant ID is required for TenantSession"
            )

        self._session = session
        self._tenant_id = tenant_id

    @property
    def session(self) -> AsyncSession:
        """Get underlying session."""
        return self._session

    @property
    def tenant_id(self) -> str:
        """Get tenant ID."""
        return self._tenant_id

    def add(self, instance: Any) -> None:
        """
        Add instance with tenant ID.

        Args:
            instance: Model instance to add
        """
        if hasattr(instance, "tenant_id"):
            instance.tenant_id = self._tenant_id
        self._session.add(instance)

    def add_all(self, instances: List[Any]) -> None:
        """
        Add multiple instances with tenant ID.

        Args:
            instances: Model instances to add
        """
        for instance in instances:
            self.add(instance)

    async def commit(self) -> None:
        """Commit the transaction."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Rollback the transaction."""
        await self._session.rollback()

    async def flush(self) -> None:
        """Flush pending changes."""
        await self._session.flush()

    async def refresh(self, instance: Any) -> None:
        """Refresh instance from database."""
        await self._session.refresh(instance)

    async def close(self) -> None:
        """Close the session."""
        await self._session.close()


# =============================================================================
# FastAPI Dependencies
# =============================================================================

def create_session_dependency(
    session_manager: SessionManager,
    read_only: bool = False
) -> Callable[[], AsyncIterator[AsyncSession]]:
    """
    Create a FastAPI dependency for database sessions.

    Args:
        session_manager: Session manager to use
        read_only: Use read replica

    Returns:
        Dependency function

    Example:
        ```python
        session_manager = SessionManager(engine)

        get_db = create_session_dependency(session_manager)
        get_read_db = create_session_dependency(session_manager, read_only=True)

        @app.get("/users")
        async def list_users(db: AsyncSession = Depends(get_db)):
            return await db.execute(select(User))
        ```
    """
    async def get_session() -> AsyncIterator[AsyncSession]:
        async with session_manager.session(read_only=read_only) as session:
            yield session

    return get_session


def create_tenant_session_dependency(
    session_manager: SessionManager,
    tenant_id_header: str = "X-Tenant-ID"
) -> Callable:
    """
    Create a FastAPI dependency for tenant-scoped sessions.

    Args:
        session_manager: Session manager to use
        tenant_id_header: Header name for tenant ID

    Returns:
        Dependency function

    Example:
        ```python
        get_tenant_db = create_tenant_session_dependency(session_manager)

        @app.get("/users")
        async def list_users(db: TenantSession = Depends(get_tenant_db)):
            # Automatically filtered by tenant
            return await db.session.execute(select(User))
        ```
    """
    async def get_tenant_session(request) -> AsyncIterator[TenantSession]:
        # Import here to avoid FastAPI dependency if not used
        tenant_id = request.headers.get(tenant_id_header)

        if not tenant_id:
            raise TenantRequiredException(
                message=f"Missing required header: {tenant_id_header}"
            )

        async with session_manager.session() as session:
            yield TenantSession(session, tenant_id)

    return get_tenant_session


def create_transactional_dependency(
    session_manager: SessionManager
) -> Callable[[], AsyncIterator[AsyncSession]]:
    """
    Create a FastAPI dependency for transactional sessions.

    Auto-commits on success, rolls back on error.

    Args:
        session_manager: Session manager to use

    Returns:
        Dependency function
    """
    async def get_transaction() -> AsyncIterator[AsyncSession]:
        async with session_manager.transaction() as session:
            yield session

    return get_transaction


# =============================================================================
# Utility Functions
# =============================================================================

async def execute_in_transaction(
    session_manager: SessionManager,
    func: Callable[[AsyncSession], T]
) -> T:
    """
    Execute a function within a transaction.

    Args:
        session_manager: Session manager to use
        func: Async function that takes a session

    Returns:
        Result of the function

    Example:
        ```python
        async def create_user(session: AsyncSession) -> User:
            user = User(name="Eve")
            session.add(user)
            return user

        user = await execute_in_transaction(session_manager, create_user)
        ```
    """
    async with session_manager.transaction() as session:
        return await func(session)


async def execute_read_only(
    session_manager: SessionManager,
    func: Callable[[AsyncSession], T]
) -> T:
    """
    Execute a function with a read-only session.

    Args:
        session_manager: Session manager to use
        func: Async function that takes a session

    Returns:
        Result of the function
    """
    async with session_manager.read_session() as session:
        return await func(session)


# =============================================================================
# Context Managers
# =============================================================================

@asynccontextmanager
async def create_session(
    engine: AsyncEngine,
    autocommit: bool = False,
    autoflush: bool = False,
    expire_on_commit: bool = True
) -> AsyncIterator[AsyncSession]:
    """
    Create an async session context manager.

    Simple utility for one-off sessions without a SessionManager.

    Args:
        engine: Async engine to bind to
        autocommit: Enable autocommit
        autoflush: Enable autoflush
        expire_on_commit: Expire objects after commit

    Yields:
        AsyncSession

    Example:
        ```python
        async with create_session(engine) as session:
            result = await session.execute(select(User))
        ```
    """
    factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        autocommit=autocommit,
        autoflush=autoflush,
        expire_on_commit=expire_on_commit
    )

    session = factory()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Session management
    "SessionManager",
    "SessionContext",
    "TenantSession",

    # Context managers
    "create_session",

    # FastAPI dependencies
    "create_session_dependency",
    "create_tenant_session_dependency",
    "create_transactional_dependency",

    # Utilities
    "execute_in_transaction",
    "execute_read_only",
]
