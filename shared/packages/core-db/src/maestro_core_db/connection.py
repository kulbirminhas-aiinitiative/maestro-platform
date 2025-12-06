"""
Enterprise database connection management for MAESTRO.

Provides:
- ConnectionConfig for pool configuration
- ConnectionPool for individual pool management
- ConnectionManager for multi-pool coordination with read/write splitting
"""

import asyncio
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from sqlalchemy import text, event
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncConnection
)
from sqlalchemy.pool import QueuePool, NullPool

from .exceptions import (
    ConnectionException,
    ConnectionPoolExhaustedException,
    ConnectionTimeoutException,
    ConnectionRefusedException,
    ConnectionClosedException,
    HealthCheckException
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


# =============================================================================
# Enums
# =============================================================================

class PoolStrategy(str, Enum):
    """Connection pool strategy."""
    QUEUE = "queue"  # Default QueuePool
    NULL = "null"    # NullPool (no pooling, for serverless)


class ConnectionRole(str, Enum):
    """Connection role for read/write splitting."""
    PRIMARY = "primary"   # Read/write
    REPLICA = "replica"   # Read-only


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class ConnectionConfig:
    """
    Database connection configuration.

    Supports both sync and async drivers for PostgreSQL, MySQL, and SQLite.
    """

    # Connection URL (can be sync or async)
    url: str

    # Pool settings
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    pool_pre_ping: bool = True

    # Engine settings
    echo: bool = False
    echo_pool: bool = False

    # Pool strategy
    pool_strategy: PoolStrategy = PoolStrategy.QUEUE

    # Connection role
    role: ConnectionRole = ConnectionRole.PRIMARY

    # Optional name for logging
    name: Optional[str] = None

    # Extra engine options
    engine_options: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate and normalize configuration."""
        if not self.url:
            raise ValueError("Database URL is required")

        # Auto-detect name from URL if not provided
        if not self.name:
            self.name = self._extract_name_from_url()

    def _extract_name_from_url(self) -> str:
        """Extract database name from URL for logging."""
        # Mask credentials in URL
        try:
            match = re.search(r'/([^/?]+)(\?|$)', self.url)
            if match:
                return match.group(1)
        except Exception:
            pass
        return "database"

    @property
    def async_url(self) -> str:
        """
        Get async-compatible database URL.

        Converts sync URLs to async drivers:
        - postgresql:// -> postgresql+asyncpg://
        - mysql:// -> mysql+aiomysql://
        - sqlite:// -> sqlite+aiosqlite://
        """
        url = self.url

        # PostgreSQL
        if url.startswith("postgresql://") or url.startswith("postgres://"):
            return url.replace("postgresql://", "postgresql+asyncpg://").replace(
                "postgres://", "postgresql+asyncpg://"
            )

        # Already async PostgreSQL
        if url.startswith("postgresql+asyncpg://"):
            return url

        # MySQL
        if url.startswith("mysql://"):
            return url.replace("mysql://", "mysql+aiomysql://")

        # SQLite
        if url.startswith("sqlite://"):
            return url.replace("sqlite://", "sqlite+aiosqlite://")

        return url

    def mask_url(self, url: Optional[str] = None) -> str:
        """Mask sensitive information in database URL for logging."""
        target_url = url or self.url
        return re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', target_url)


# =============================================================================
# Connection Pool
# =============================================================================

class ConnectionPool:
    """
    Individual connection pool manager.

    Wraps a SQLAlchemy async engine with health checks and metrics.
    """

    def __init__(self, config: ConnectionConfig):
        """
        Initialize connection pool.

        Args:
            config: Connection configuration
        """
        self.config = config
        self._engine: Optional[AsyncEngine] = None
        self._initialized = False
        self._healthy = False
        self._connection_count = 0
        self._error_count = 0
        self._last_health_check: Optional[float] = None

    @property
    def name(self) -> str:
        """Pool name for logging."""
        return self.config.name or "unnamed"

    @property
    def is_initialized(self) -> bool:
        """Check if pool is initialized."""
        return self._initialized

    @property
    def is_healthy(self) -> bool:
        """Check if pool is healthy."""
        return self._healthy

    @property
    def engine(self) -> AsyncEngine:
        """Get the async engine."""
        if not self._engine:
            raise ConnectionException(
                message=f"Connection pool '{self.name}' not initialized",
                details={"pool_name": self.name}
            )
        return self._engine

    async def initialize(self) -> None:
        """Initialize the connection pool."""
        if self._initialized:
            return

        logger.info(
            "Initializing connection pool",
            pool_name=self.name,
            url=self.config.mask_url()
        )

        try:
            # Select pool class
            pool_class = {
                PoolStrategy.QUEUE: QueuePool,
                PoolStrategy.NULL: NullPool,
            }.get(self.config.pool_strategy, QueuePool)

            # Build engine options
            engine_options = {
                "poolclass": pool_class,
                "echo": self.config.echo,
                "echo_pool": self.config.echo_pool,
                **self.config.engine_options,
            }

            # Add pool-specific options (only for QueuePool)
            if pool_class == QueuePool:
                engine_options.update({
                    "pool_size": self.config.pool_size,
                    "max_overflow": self.config.max_overflow,
                    "pool_timeout": self.config.pool_timeout,
                    "pool_recycle": self.config.pool_recycle,
                    "pool_pre_ping": self.config.pool_pre_ping,
                })

            # Create async engine
            self._engine = create_async_engine(
                self.config.async_url,
                **engine_options
            )

            # Setup event listeners
            self._setup_event_listeners()

            # Test connection
            await self._test_connection()

            self._initialized = True
            self._healthy = True

            logger.info(
                "Connection pool initialized",
                pool_name=self.name,
                pool_size=self.config.pool_size
            )

        except Exception as e:
            logger.error(
                "Failed to initialize connection pool",
                pool_name=self.name,
                error=str(e)
            )
            raise ConnectionException(
                message=f"Failed to initialize pool '{self.name}': {e}",
                details={"pool_name": self.name},
                cause=e
            )

    def _setup_event_listeners(self) -> None:
        """Setup SQLAlchemy event listeners for monitoring."""
        if not self._engine:
            return

        @event.listens_for(self._engine.sync_engine, "connect")
        def on_connect(dbapi_conn, connection_record):
            self._connection_count += 1
            logger.debug(
                "Connection established",
                pool_name=self.name,
                total_connections=self._connection_count
            )

        @event.listens_for(self._engine.sync_engine, "close")
        def on_close(dbapi_conn, connection_record):
            logger.debug("Connection closed", pool_name=self.name)

        @event.listens_for(self._engine.sync_engine, "invalidate")
        def on_invalidate(dbapi_conn, connection_record, exception):
            self._error_count += 1
            logger.warning(
                "Connection invalidated",
                pool_name=self.name,
                error=str(exception) if exception else None
            )

    async def _test_connection(self) -> None:
        """Test connection by executing a simple query."""
        try:
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
        except asyncio.TimeoutError as e:
            raise ConnectionTimeoutException(
                message=f"Connection test timed out for pool '{self.name}'",
                details={"pool_name": self.name},
                cause=e
            )
        except ConnectionRefusedError as e:
            raise ConnectionRefusedException(
                message=f"Connection refused for pool '{self.name}'",
                details={"pool_name": self.name},
                cause=e
            )
        except Exception as e:
            raise ConnectionException(
                message=f"Connection test failed for pool '{self.name}': {e}",
                details={"pool_name": self.name},
                cause=e
            )

    async def health_check(self) -> bool:
        """
        Perform health check on the connection pool.

        Returns:
            True if healthy, False otherwise
        """
        if not self._initialized:
            return False

        import time
        self._last_health_check = time.time()

        try:
            async with self._engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            self._healthy = True
            return True
        except Exception as e:
            self._healthy = False
            self._error_count += 1
            logger.warning(
                "Health check failed",
                pool_name=self.name,
                error=str(e)
            )
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get pool status for monitoring."""
        status = {
            "name": self.name,
            "role": self.config.role.value,
            "initialized": self._initialized,
            "healthy": self._healthy,
            "connection_count": self._connection_count,
            "error_count": self._error_count,
            "last_health_check": self._last_health_check,
        }

        # Add pool stats if using QueuePool
        if self._engine and self.config.pool_strategy == PoolStrategy.QUEUE:
            pool = self._engine.pool
            status.update({
                "pool_size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "invalid": pool.invalidatedcount() if hasattr(pool, 'invalidatedcount') else 0,
            })

        return status

    @asynccontextmanager
    async def acquire(self):
        """
        Acquire a connection from the pool.

        Yields:
            AsyncConnection
        """
        if not self._initialized:
            raise ConnectionException(
                message=f"Pool '{self.name}' not initialized"
            )

        try:
            async with self._engine.connect() as conn:
                yield conn
        except asyncio.TimeoutError as e:
            self._error_count += 1
            raise ConnectionPoolExhaustedException(
                message=f"Pool '{self.name}' exhausted - timeout waiting for connection",
                details={"pool_name": self.name},
                cause=e
            )
        except Exception as e:
            self._error_count += 1
            raise ConnectionException(
                message=f"Failed to acquire connection from pool '{self.name}': {e}",
                details={"pool_name": self.name},
                cause=e
            )

    async def dispose(self) -> None:
        """Dispose of the connection pool and close all connections."""
        if not self._engine:
            return

        logger.info("Disposing connection pool", pool_name=self.name)

        try:
            await self._engine.dispose()
        except Exception as e:
            logger.error(
                "Error disposing connection pool",
                pool_name=self.name,
                error=str(e)
            )
        finally:
            self._engine = None
            self._initialized = False
            self._healthy = False


# =============================================================================
# Connection Manager
# =============================================================================

class ConnectionManager:
    """
    Multi-pool connection manager with read/write splitting.

    Manages multiple connection pools and provides load-balanced
    access to primary and replica databases.
    """

    def __init__(
        self,
        primary_config: ConnectionConfig,
        replica_configs: Optional[List[ConnectionConfig]] = None,
        health_check_interval: int = 30
    ):
        """
        Initialize connection manager.

        Args:
            primary_config: Configuration for primary (read/write) database
            replica_configs: Configurations for read replicas
            health_check_interval: Seconds between health checks
        """
        # Ensure primary has correct role
        primary_config.role = ConnectionRole.PRIMARY
        self._primary_pool = ConnectionPool(primary_config)

        # Setup replica pools
        self._replica_pools: List[ConnectionPool] = []
        if replica_configs:
            for i, config in enumerate(replica_configs):
                config.role = ConnectionRole.REPLICA
                if not config.name:
                    config.name = f"replica-{i}"
                self._replica_pools.append(ConnectionPool(config))

        # Load balancing state
        self._current_replica_index = 0

        # Health check configuration
        self._health_check_interval = health_check_interval
        self._health_check_task: Optional[asyncio.Task] = None

        # State
        self._initialized = False

    @property
    def primary(self) -> ConnectionPool:
        """Get the primary connection pool."""
        return self._primary_pool

    @property
    def replicas(self) -> List[ConnectionPool]:
        """Get all replica connection pools."""
        return self._replica_pools

    @property
    def is_initialized(self) -> bool:
        """Check if manager is initialized."""
        return self._initialized

    async def initialize(self) -> None:
        """Initialize all connection pools."""
        if self._initialized:
            return

        logger.info("Initializing connection manager")

        try:
            # Initialize primary pool (required)
            await self._primary_pool.initialize()

            # Initialize replica pools (optional)
            for pool in self._replica_pools:
                try:
                    await pool.initialize()
                except Exception as e:
                    logger.warning(
                        "Failed to initialize replica pool",
                        pool_name=pool.name,
                        error=str(e)
                    )

            # Start health check loop
            self._health_check_task = asyncio.create_task(
                self._health_check_loop()
            )

            self._initialized = True
            logger.info(
                "Connection manager initialized",
                primary=self._primary_pool.name,
                replicas=[p.name for p in self._replica_pools if p.is_initialized]
            )

        except Exception as e:
            await self.shutdown()
            raise ConnectionException(
                message=f"Failed to initialize connection manager: {e}",
                cause=e
            )

    async def _health_check_loop(self) -> None:
        """Periodic health check loop."""
        while self._initialized:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self._health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Health check loop error", error=str(e))
                await asyncio.sleep(self._health_check_interval * 2)

    async def _perform_health_checks(self) -> None:
        """Perform health checks on all pools."""
        # Check primary
        await self._primary_pool.health_check()

        # Check replicas
        for pool in self._replica_pools:
            if pool.is_initialized:
                await pool.health_check()

    def get_write_engine(self) -> AsyncEngine:
        """
        Get engine for write operations.

        Returns:
            Primary database engine
        """
        if not self._initialized:
            raise ConnectionException("Connection manager not initialized")
        return self._primary_pool.engine

    def get_read_engine(self) -> AsyncEngine:
        """
        Get engine for read operations with load balancing.

        Returns:
            Replica engine if available and healthy, otherwise primary
        """
        if not self._initialized:
            raise ConnectionException("Connection manager not initialized")

        # Get healthy replicas
        healthy_replicas = [
            p for p in self._replica_pools
            if p.is_initialized and p.is_healthy
        ]

        if not healthy_replicas:
            # Fall back to primary
            return self._primary_pool.engine

        # Round-robin load balancing
        pool = healthy_replicas[self._current_replica_index % len(healthy_replicas)]
        self._current_replica_index = (self._current_replica_index + 1) % len(healthy_replicas)

        return pool.engine

    @asynccontextmanager
    async def acquire_write(self):
        """
        Acquire a write connection.

        Yields:
            AsyncConnection for write operations
        """
        async with self._primary_pool.acquire() as conn:
            yield conn

    @asynccontextmanager
    async def acquire_read(self):
        """
        Acquire a read connection with load balancing.

        Yields:
            AsyncConnection for read operations
        """
        # Get healthy replicas
        healthy_replicas = [
            p for p in self._replica_pools
            if p.is_initialized and p.is_healthy
        ]

        if healthy_replicas:
            pool = healthy_replicas[self._current_replica_index % len(healthy_replicas)]
            self._current_replica_index = (self._current_replica_index + 1) % len(healthy_replicas)
        else:
            pool = self._primary_pool

        async with pool.acquire() as conn:
            yield conn

    def get_status(self) -> Dict[str, Any]:
        """Get status of all connection pools."""
        return {
            "initialized": self._initialized,
            "primary": self._primary_pool.get_status(),
            "replicas": [p.get_status() for p in self._replica_pools],
            "health_check_interval": self._health_check_interval,
        }

    async def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on all pools and return status.

        Returns:
            Health status dictionary
        """
        primary_healthy = await self._primary_pool.health_check()

        replica_health = {}
        for pool in self._replica_pools:
            if pool.is_initialized:
                replica_health[pool.name] = await pool.health_check()

        overall_healthy = primary_healthy  # Primary must be healthy

        return {
            "healthy": overall_healthy,
            "primary": primary_healthy,
            "replicas": replica_health,
        }

    async def shutdown(self) -> None:
        """Shutdown all connection pools."""
        logger.info("Shutting down connection manager")

        self._initialized = False

        # Cancel health check task
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Dispose all pools
        await self._primary_pool.dispose()

        for pool in self._replica_pools:
            await pool.dispose()

        logger.info("Connection manager shutdown complete")

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()


# =============================================================================
# Factory Functions
# =============================================================================

def create_connection_config(
    host: str = "localhost",
    port: int = 5432,
    database: str = "maestro",
    username: str = "maestro",
    password: str = "",
    driver: str = "postgresql+asyncpg",
    **kwargs
) -> ConnectionConfig:
    """
    Create a connection configuration from individual parameters.

    Args:
        host: Database host
        port: Database port
        database: Database name
        username: Database username
        password: Database password
        driver: SQLAlchemy driver string
        **kwargs: Additional ConnectionConfig parameters

    Returns:
        ConnectionConfig instance
    """
    url = f"{driver}://{username}:{password}@{host}:{port}/{database}"
    return ConnectionConfig(url=url, **kwargs)


def create_connection_config_from_env(
    prefix: str = "DATABASE",
    defaults: Optional[Dict[str, Any]] = None
) -> ConnectionConfig:
    """
    Create connection configuration from environment variables.

    Environment variables:
        {PREFIX}_URL: Full database URL (takes precedence)
        {PREFIX}_HOST: Database host
        {PREFIX}_PORT: Database port
        {PREFIX}_NAME: Database name
        {PREFIX}_USER: Username
        {PREFIX}_PASSWORD: Password
        {PREFIX}_POOL_SIZE: Pool size
        {PREFIX}_MAX_OVERFLOW: Max overflow
        {PREFIX}_POOL_TIMEOUT: Pool timeout
        {PREFIX}_ECHO: Echo SQL (true/false)

    Args:
        prefix: Environment variable prefix
        defaults: Default values dictionary

    Returns:
        ConnectionConfig instance
    """
    import os

    defaults = defaults or {}

    # Check for full URL first
    url = os.getenv(f"{prefix}_URL")

    if not url:
        # Build URL from components
        host = os.getenv(f"{prefix}_HOST", defaults.get("host", "localhost"))
        port = os.getenv(f"{prefix}_PORT", defaults.get("port", "5432"))
        database = os.getenv(f"{prefix}_NAME", defaults.get("database", "maestro"))
        username = os.getenv(f"{prefix}_USER", defaults.get("username", "maestro"))
        password = os.getenv(f"{prefix}_PASSWORD", defaults.get("password", ""))

        url = f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database}"

    return ConnectionConfig(
        url=url,
        pool_size=int(os.getenv(f"{prefix}_POOL_SIZE", defaults.get("pool_size", 10))),
        max_overflow=int(os.getenv(f"{prefix}_MAX_OVERFLOW", defaults.get("max_overflow", 20))),
        pool_timeout=int(os.getenv(f"{prefix}_POOL_TIMEOUT", defaults.get("pool_timeout", 30))),
        pool_recycle=int(os.getenv(f"{prefix}_POOL_RECYCLE", defaults.get("pool_recycle", 3600))),
        pool_pre_ping=os.getenv(f"{prefix}_POOL_PRE_PING", "true").lower() == "true",
        echo=os.getenv(f"{prefix}_ECHO", "false").lower() == "true",
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Enums
    "PoolStrategy",
    "ConnectionRole",

    # Configuration
    "ConnectionConfig",

    # Pool management
    "ConnectionPool",
    "ConnectionManager",

    # Factory functions
    "create_connection_config",
    "create_connection_config_from_env",
]
