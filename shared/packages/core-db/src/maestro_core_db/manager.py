"""
Enterprise database manager with connection pooling, monitoring, and health checks.
"""

import asyncio
from typing import Optional, Dict, Any, List
from contextlib import asynccontextmanager
from sqlalchemy import text, event
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    async_sessionmaker,
    AsyncSession
)
from sqlalchemy.pool import QueuePool
from maestro_core_logging import get_logger

from .session import SessionManager
from .migrations import MigrationManager
from .cache import CacheManager
from .monitoring import DatabaseMonitor
from .exceptions import DatabaseException, ConnectionException


class DatabaseManager:
    """
    Enterprise database manager with advanced features.

    Features:
    - Connection pooling with health checks
    - Automatic failover and reconnection
    - Query performance monitoring
    - Connection leak detection
    - Read/write splitting
    - Database metrics collection
    """

    def __init__(
        self,
        url: str,
        pool_size: int = 10,
        max_overflow: int = 20,
        pool_timeout: int = 30,
        pool_recycle: int = 3600,
        pool_pre_ping: bool = True,
        echo: bool = False,
        echo_pool: bool = False,
        read_replica_urls: Optional[List[str]] = None,
        enable_monitoring: bool = True,
        enable_query_cache: bool = True,
        enable_migrations: bool = True,
        migration_location: str = "migrations"
    ):
        """
        Initialize database manager.

        Args:
            url: Primary database URL
            pool_size: Connection pool size
            max_overflow: Maximum overflow connections
            pool_timeout: Connection timeout in seconds
            pool_recycle: Connection recycle time in seconds
            pool_pre_ping: Enable connection pre-ping
            echo: Echo SQL queries
            echo_pool: Echo pool events
            read_replica_urls: Read replica database URLs
            enable_monitoring: Enable database monitoring
            enable_query_cache: Enable query result caching
            enable_migrations: Enable migration management
            migration_location: Migration files location
        """
        self.url = url
        self.read_replica_urls = read_replica_urls or []
        self.logger = get_logger(__name__)

        # Connection configuration
        self.engine_config = {
            "poolclass": QueuePool,
            "pool_size": pool_size,
            "max_overflow": max_overflow,
            "pool_timeout": pool_timeout,
            "pool_recycle": pool_recycle,
            "pool_pre_ping": pool_pre_ping,
            "echo": echo,
            "echo_pool": echo_pool,
        }

        # Engines
        self._write_engine: Optional[AsyncEngine] = None
        self._read_engines: List[AsyncEngine] = []
        self._current_read_engine_index = 0

        # Managers
        self.session_manager: Optional[SessionManager] = None
        self.migration_manager: Optional[MigrationManager] = None
        self.cache_manager: Optional[CacheManager] = None
        self.monitor: Optional[DatabaseMonitor] = None

        # Configuration flags
        self.enable_monitoring = enable_monitoring
        self.enable_query_cache = enable_query_cache
        self.enable_migrations = enable_migrations
        self.migration_location = migration_location

        # State
        self._initialized = False
        self._health_check_task: Optional[asyncio.Task] = None

    async def initialize(self) -> None:
        """Initialize database connections and managers."""
        if self._initialized:
            return

        try:
            self.logger.info("Initializing database manager", url=self._mask_url(self.url))

            # Create engines
            await self._create_engines()

            # Initialize managers
            await self._initialize_managers()

            # Start health checks
            await self._start_health_checks()

            # Run migrations if enabled
            if self.enable_migrations:
                await self.migration_manager.run_migrations()

            self._initialized = True
            self.logger.info("Database manager initialized successfully")

        except Exception as e:
            self.logger.error("Failed to initialize database manager", error=str(e))
            await self.shutdown()
            raise DatabaseException(f"Database initialization failed: {e}")

    async def _create_engines(self) -> None:
        """Create database engines for write and read operations."""
        # Create write engine
        self._write_engine = create_async_engine(self.url, **self.engine_config)

        # Test write connection
        try:
            async with self._write_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as e:
            raise ConnectionException(f"Failed to connect to write database: {e}")

        # Create read engines
        for replica_url in self.read_replica_urls:
            try:
                read_engine = create_async_engine(replica_url, **self.engine_config)
                # Test read connection
                async with read_engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))
                self._read_engines.append(read_engine)
                self.logger.info("Read replica connected", url=self._mask_url(replica_url))
            except Exception as e:
                self.logger.warning("Failed to connect to read replica",
                                  url=self._mask_url(replica_url),
                                  error=str(e))

        # Use write engine as read fallback if no read replicas
        if not self._read_engines:
            self._read_engines = [self._write_engine]

    async def _initialize_managers(self) -> None:
        """Initialize sub-managers."""
        # Session manager
        self.session_manager = SessionManager(
            write_engine=self._write_engine,
            read_engines=self._read_engines
        )

        # Migration manager
        if self.enable_migrations:
            self.migration_manager = MigrationManager(
                engine=self._write_engine,
                migration_location=self.migration_location
            )

        # Cache manager
        if self.enable_query_cache:
            self.cache_manager = CacheManager()

        # Database monitor
        if self.enable_monitoring:
            self.monitor = DatabaseMonitor(
                write_engine=self._write_engine,
                read_engines=self._read_engines
            )
            await self.monitor.start()

    async def _start_health_checks(self) -> None:
        """Start periodic health checks."""
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def _health_check_loop(self) -> None:
        """Periodic health check loop."""
        while self._initialized:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(30)  # Check every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Health check failed", error=str(e))
                await asyncio.sleep(60)  # Back off on errors

    async def _perform_health_checks(self) -> None:
        """Perform health checks on all connections."""
        # Check write engine
        try:
            async with self._write_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception as e:
            self.logger.error("Write database health check failed", error=str(e))
            if self.monitor:
                await self.monitor.record_connection_error("write")

        # Check read engines
        for i, engine in enumerate(self._read_engines):
            if engine == self._write_engine:
                continue  # Already checked

            try:
                async with engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))
            except Exception as e:
                self.logger.error("Read database health check failed",
                                replica_index=i,
                                error=str(e))
                if self.monitor:
                    await self.monitor.record_connection_error(f"read_{i}")

    def get_write_session(self) -> AsyncSession:
        """Get session for write operations."""
        if not self._initialized:
            raise DatabaseException("Database manager not initialized")
        return self.session_manager.get_write_session()

    def get_read_session(self) -> AsyncSession:
        """Get session for read operations (with load balancing)."""
        if not self._initialized:
            raise DatabaseException("Database manager not initialized")
        return self.session_manager.get_read_session()

    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions."""
        async with self.get_write_session() as session:
            async with session.begin():
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise

    async def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        use_cache: bool = False,
        cache_ttl: int = 300,
        read_only: bool = False
    ) -> Any:
        """
        Execute raw SQL query with optional caching.

        Args:
            query: SQL query
            params: Query parameters
            use_cache: Whether to cache results
            cache_ttl: Cache TTL in seconds
            read_only: Whether this is a read-only query

        Returns:
            Query result
        """
        # Check cache first
        if use_cache and self.cache_manager:
            cache_key = self.cache_manager.generate_cache_key(query, params)
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result

        # Choose appropriate session
        session_func = self.get_read_session if read_only else self.get_write_session

        # Execute query
        async with session_func() as session:
            result = await session.execute(text(query), params or {})

            # Cache result if requested
            if use_cache and self.cache_manager and read_only:
                await self.cache_manager.set(cache_key, result, ttl=cache_ttl)

            return result

    async def get_health_status(self) -> Dict[str, Any]:
        """Get database health status."""
        if not self._initialized:
            return {"status": "not_initialized"}

        status = {
            "status": "healthy",
            "write_engine": "healthy",
            "read_engines": [],
            "connections": {
                "pool_size": self._write_engine.pool.size(),
                "checked_in": self._write_engine.pool.checkedin(),
                "checked_out": self._write_engine.pool.checkedout(),
                "overflow": self._write_engine.pool.overflow(),
            }
        }

        # Check write engine
        try:
            async with self._write_engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
        except Exception:
            status["write_engine"] = "unhealthy"
            status["status"] = "degraded"

        # Check read engines
        for i, engine in enumerate(self._read_engines):
            if engine == self._write_engine:
                status["read_engines"].append({"index": i, "status": status["write_engine"]})
                continue

            try:
                async with engine.begin() as conn:
                    await conn.execute(text("SELECT 1"))
                status["read_engines"].append({"index": i, "status": "healthy"})
            except Exception:
                status["read_engines"].append({"index": i, "status": "unhealthy"})
                if status["status"] == "healthy":
                    status["status"] = "degraded"

        return status

    async def shutdown(self) -> None:
        """Shutdown database manager and cleanup resources."""
        if not self._initialized:
            return

        self.logger.info("Shutting down database manager")

        # Cancel health checks
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Stop monitoring
        if self.monitor:
            await self.monitor.stop()

        # Dispose engines
        if self._write_engine:
            await self._write_engine.dispose()

        for engine in self._read_engines:
            if engine != self._write_engine:
                await engine.dispose()

        self._initialized = False
        self.logger.info("Database manager shutdown complete")

    def _mask_url(self, url: str) -> str:
        """Mask sensitive information in database URL."""
        import re
        return re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', url)

    def __del__(self):
        """Cleanup on garbage collection."""
        if self._initialized:
            # Note: Can't use await in __del__, so we log a warning
            self.logger.warning("DatabaseManager not properly shutdown - call shutdown() explicitly")