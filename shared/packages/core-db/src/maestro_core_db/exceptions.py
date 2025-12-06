"""
Enterprise database exception handling for MAESTRO.

Provides standardized exception classes for database operations including
connection errors, query failures, migration issues, and multi-tenancy violations.
"""

from typing import Any, Dict, Optional


def _get_logger():
    """Lazy logger initialization to avoid circular imports."""
    try:
        from maestro_core_logging import get_logger
        return get_logger(__name__)
    except ImportError:
        import logging
        return logging.getLogger(__name__)


logger = type("LazyLogger", (), {"__getattr__": lambda self, name: getattr(_get_logger(), name)})()


class DatabaseException(Exception):
    """
    Base exception for all database errors.

    Attributes:
        error_code: Machine-readable error code
        message: Human-readable error message
        details: Additional error details
        retryable: Whether the operation can be retried
    """

    error_code: str = "DATABASE_ERROR"
    message: str = "A database error occurred"
    retryable: bool = False

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        retryable: Optional[bool] = None,
        cause: Optional[Exception] = None
    ):
        """
        Initialize database exception.

        Args:
            message: Custom error message
            details: Additional error details
            error_code: Custom error code
            retryable: Whether the operation can be retried
            cause: Original exception that caused this error
        """
        self.message = message or self.message
        self.details = details or {}
        if error_code:
            self.error_code = error_code
        if retryable is not None:
            self.retryable = retryable
        self.cause = cause
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        result = {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "retryable": self.retryable
            }
        }
        if self.details:
            result["error"]["details"] = self.details
        if self.cause:
            result["error"]["cause"] = str(self.cause)
        return result

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(code={self.error_code!r}, message={self.message!r})"


# Connection Exceptions

class ConnectionException(DatabaseException):
    """Database connection failed."""
    error_code = "CONNECTION_ERROR"
    message = "Failed to connect to database"
    retryable = True


class ConnectionPoolExhaustedException(ConnectionException):
    """Connection pool exhausted - no connections available."""
    error_code = "POOL_EXHAUSTED"
    message = "Connection pool exhausted"
    retryable = True


class ConnectionTimeoutException(ConnectionException):
    """Connection attempt timed out."""
    error_code = "CONNECTION_TIMEOUT"
    message = "Connection timed out"
    retryable = True


class ConnectionRefusedException(ConnectionException):
    """Connection refused by database server."""
    error_code = "CONNECTION_REFUSED"
    message = "Connection refused by database"
    retryable = True


class ConnectionClosedException(ConnectionException):
    """Connection was unexpectedly closed."""
    error_code = "CONNECTION_CLOSED"
    message = "Database connection closed unexpectedly"
    retryable = True


# Query Exceptions

class QueryException(DatabaseException):
    """Query execution failed."""
    error_code = "QUERY_ERROR"
    message = "Query execution failed"
    retryable = False

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        query: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize query exception.

        Args:
            message: Custom error message
            details: Additional error details
            query: The SQL query that failed (truncated for safety)
        """
        super().__init__(message, details, **kwargs)
        # Truncate query to avoid exposing sensitive data
        if query:
            self.details["query_preview"] = query[:200] + "..." if len(query) > 200 else query


class QueryTimeoutException(QueryException):
    """Query execution timed out."""
    error_code = "QUERY_TIMEOUT"
    message = "Query execution timed out"
    retryable = True


class QuerySyntaxException(QueryException):
    """Query has invalid syntax."""
    error_code = "QUERY_SYNTAX_ERROR"
    message = "Invalid query syntax"
    retryable = False


# Integrity Exceptions

class IntegrityException(DatabaseException):
    """Data integrity constraint violated."""
    error_code = "INTEGRITY_ERROR"
    message = "Data integrity constraint violated"
    retryable = False


class UniqueViolationException(IntegrityException):
    """Unique constraint violated."""
    error_code = "UNIQUE_VIOLATION"
    message = "Unique constraint violated"


class ForeignKeyViolationException(IntegrityException):
    """Foreign key constraint violated."""
    error_code = "FOREIGN_KEY_VIOLATION"
    message = "Foreign key constraint violated"


class NotNullViolationException(IntegrityException):
    """Not-null constraint violated."""
    error_code = "NOT_NULL_VIOLATION"
    message = "Required field cannot be null"


class CheckConstraintViolationException(IntegrityException):
    """Check constraint violated."""
    error_code = "CHECK_CONSTRAINT_VIOLATION"
    message = "Check constraint violated"


# Migration Exceptions

class MigrationException(DatabaseException):
    """Migration operation failed."""
    error_code = "MIGRATION_ERROR"
    message = "Database migration failed"
    retryable = False


class MigrationVersionConflict(MigrationException):
    """Migration version conflict detected."""
    error_code = "MIGRATION_VERSION_CONFLICT"
    message = "Migration version conflict - database is at a different revision than expected"


class MigrationLockException(MigrationException):
    """Could not acquire migration lock."""
    error_code = "MIGRATION_LOCK_ERROR"
    message = "Could not acquire migration lock - another migration may be in progress"
    retryable = True


class MigrationNotFoundException(MigrationException):
    """Migration file not found."""
    error_code = "MIGRATION_NOT_FOUND"
    message = "Migration file not found"


# Multi-tenancy Exceptions

class TenantException(DatabaseException):
    """Base exception for multi-tenancy errors."""
    error_code = "TENANT_ERROR"
    message = "Multi-tenancy error"
    retryable = False


class TenantNotFoundException(TenantException):
    """Tenant not found."""
    error_code = "TENANT_NOT_FOUND"
    message = "Tenant not found"


class TenantMismatchException(TenantException):
    """Tenant ID mismatch in multi-tenant query."""
    error_code = "TENANT_MISMATCH"
    message = "Tenant ID mismatch - cross-tenant access denied"


class TenantRequiredException(TenantException):
    """Tenant ID required but not provided."""
    error_code = "TENANT_REQUIRED"
    message = "Tenant ID is required for this operation"


# Transaction Exceptions

class TransactionException(DatabaseException):
    """Transaction operation failed."""
    error_code = "TRANSACTION_ERROR"
    message = "Transaction operation failed"
    retryable = False


class TransactionRollbackException(TransactionException):
    """Transaction was rolled back."""
    error_code = "TRANSACTION_ROLLBACK"
    message = "Transaction was rolled back"
    retryable = True


class DeadlockException(TransactionException):
    """Deadlock detected."""
    error_code = "DEADLOCK_DETECTED"
    message = "Database deadlock detected"
    retryable = True


class SerializationException(TransactionException):
    """Serialization failure (concurrent update conflict)."""
    error_code = "SERIALIZATION_FAILURE"
    message = "Concurrent update conflict - please retry"
    retryable = True


# Cache Exceptions

class CacheException(DatabaseException):
    """Cache operation failed."""
    error_code = "CACHE_ERROR"
    message = "Cache operation failed"
    retryable = True


class CacheConnectionException(CacheException):
    """Cache connection failed."""
    error_code = "CACHE_CONNECTION_ERROR"
    message = "Failed to connect to cache"


class CacheSerializationException(CacheException):
    """Cache serialization failed."""
    error_code = "CACHE_SERIALIZATION_ERROR"
    message = "Failed to serialize/deserialize cache data"
    retryable = False


# Entity Exceptions

class EntityNotFoundException(DatabaseException):
    """Entity not found in database."""
    error_code = "ENTITY_NOT_FOUND"
    message = "Entity not found"
    retryable = False

    def __init__(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[Any] = None,
        **kwargs
    ):
        """
        Initialize entity not found exception.

        Args:
            entity_type: Type of entity (e.g., "User", "Workflow")
            entity_id: ID of the entity that was not found
        """
        details = kwargs.pop("details", {})
        if entity_type:
            details["entity_type"] = entity_type
        if entity_id:
            details["entity_id"] = str(entity_id)
        message = kwargs.pop("message", None)
        if entity_type and entity_id:
            message = message or f"{entity_type} with id '{entity_id}' not found"
        super().__init__(message=message, details=details, **kwargs)


class EntityExistsException(IntegrityException):
    """Entity already exists."""
    error_code = "ENTITY_EXISTS"
    message = "Entity already exists"


# Health Check Exceptions

class HealthCheckException(DatabaseException):
    """Database health check failed."""
    error_code = "HEALTH_CHECK_FAILED"
    message = "Database health check failed"
    retryable = True


# Export all
__all__ = [
    # Base
    "DatabaseException",

    # Connection
    "ConnectionException",
    "ConnectionPoolExhaustedException",
    "ConnectionTimeoutException",
    "ConnectionRefusedException",
    "ConnectionClosedException",

    # Query
    "QueryException",
    "QueryTimeoutException",
    "QuerySyntaxException",

    # Integrity
    "IntegrityException",
    "UniqueViolationException",
    "ForeignKeyViolationException",
    "NotNullViolationException",
    "CheckConstraintViolationException",

    # Migration
    "MigrationException",
    "MigrationVersionConflict",
    "MigrationLockException",
    "MigrationNotFoundException",

    # Multi-tenancy
    "TenantException",
    "TenantNotFoundException",
    "TenantMismatchException",
    "TenantRequiredException",

    # Transaction
    "TransactionException",
    "TransactionRollbackException",
    "DeadlockException",
    "SerializationException",

    # Cache
    "CacheException",
    "CacheConnectionException",
    "CacheSerializationException",

    # Entity
    "EntityNotFoundException",
    "EntityExistsException",

    # Health
    "HealthCheckException",
]
