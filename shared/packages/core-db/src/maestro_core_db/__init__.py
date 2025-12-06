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
    async with create_session(engine) as session:
        result = await session.execute(select(User))
        users = result.scalars().all()

    # Define models
    class User(BaseModel):
        __tablename__ = "users"

        username: Mapped[str] = mapped_column(String(50), unique=True)
        email: Mapped[str] = mapped_column(String(255), unique=True)
"""

# Manager
from .manager import DatabaseManager

# Base models and repositories
from .base import (
    BaseModel,
    BaseRepository,
    TenantAwareRepository,
    SoftDeleteRepository,
    TenantMixin,
    SoftDeleteMixin,
    AuditMixin,
    VersionMixin,
    ModelT,
)

# Session management
from .session import (
    SessionManager,
    SessionContext,
    TenantSession,
    create_session,
    create_session_dependency,
    create_tenant_session_dependency,
    create_transactional_dependency,
    execute_in_transaction,
    execute_read_only,
)

# Migrations
from .migrations import (
    MigrationManager,
    MigrationConfig,
    MigrationInfo,
)

# Caching
from .cache import (
    QueryCache,
    CacheManager,
    CacheConfig,
    CacheBackend,
    MemoryCacheBackend,
    RedisCacheBackend,
)

# Monitoring
from .monitoring import (
    DatabaseMonitor,
    DatabaseMetrics,
    QueryLogger,
    PoolStats,
    HealthStatus,
    PrometheusExporter,
)

# Connection management
from .connection import (
    ConnectionManager,
    ConnectionPool,
    ConnectionConfig,
    PoolStrategy,
    ConnectionRole,
    create_connection_config,
    create_connection_config_from_env,
)

# Exceptions
from .exceptions import (
    # Base
    DatabaseException,
    # Connection
    ConnectionException,
    ConnectionPoolExhaustedException,
    ConnectionTimeoutException,
    ConnectionRefusedException,
    ConnectionClosedException,
    # Query
    QueryException,
    QueryTimeoutException,
    QuerySyntaxException,
    # Integrity
    IntegrityException,
    UniqueViolationException,
    ForeignKeyViolationException,
    NotNullViolationException,
    CheckConstraintViolationException,
    # Migration
    MigrationException,
    MigrationVersionConflict,
    MigrationLockException,
    MigrationNotFoundException,
    # Multi-tenancy
    TenantException,
    TenantNotFoundException,
    TenantMismatchException,
    TenantRequiredException,
    # Transaction
    TransactionException,
    TransactionRollbackException,
    DeadlockException,
    SerializationException,
    # Cache
    CacheException,
    CacheConnectionException,
    CacheSerializationException,
    # Entity
    EntityNotFoundException,
    EntityExistsException,
    # Health
    HealthCheckException,
)

__version__ = "1.0.0"
__all__ = [
    # Manager
    "DatabaseManager",

    # Base models and repositories
    "BaseModel",
    "BaseRepository",
    "TenantAwareRepository",
    "SoftDeleteRepository",
    "TenantMixin",
    "SoftDeleteMixin",
    "AuditMixin",
    "VersionMixin",
    "ModelT",

    # Session management
    "SessionManager",
    "SessionContext",
    "TenantSession",
    "create_session",
    "create_session_dependency",
    "create_tenant_session_dependency",
    "create_transactional_dependency",
    "execute_in_transaction",
    "execute_read_only",

    # Migrations
    "MigrationManager",
    "MigrationConfig",
    "MigrationInfo",

    # Caching
    "QueryCache",
    "CacheManager",
    "CacheConfig",
    "CacheBackend",
    "MemoryCacheBackend",
    "RedisCacheBackend",

    # Monitoring
    "DatabaseMonitor",
    "DatabaseMetrics",
    "QueryLogger",
    "PoolStats",
    "HealthStatus",
    "PrometheusExporter",

    # Connection management
    "ConnectionManager",
    "ConnectionPool",
    "ConnectionConfig",
    "PoolStrategy",
    "ConnectionRole",
    "create_connection_config",
    "create_connection_config_from_env",

    # Exceptions
    "DatabaseException",
    "ConnectionException",
    "ConnectionPoolExhaustedException",
    "ConnectionTimeoutException",
    "ConnectionRefusedException",
    "ConnectionClosedException",
    "QueryException",
    "QueryTimeoutException",
    "QuerySyntaxException",
    "IntegrityException",
    "UniqueViolationException",
    "ForeignKeyViolationException",
    "NotNullViolationException",
    "CheckConstraintViolationException",
    "MigrationException",
    "MigrationVersionConflict",
    "MigrationLockException",
    "MigrationNotFoundException",
    "TenantException",
    "TenantNotFoundException",
    "TenantMismatchException",
    "TenantRequiredException",
    "TransactionException",
    "TransactionRollbackException",
    "DeadlockException",
    "SerializationException",
    "CacheException",
    "CacheConnectionException",
    "CacheSerializationException",
    "EntityNotFoundException",
    "EntityExistsException",
    "HealthCheckException",
]