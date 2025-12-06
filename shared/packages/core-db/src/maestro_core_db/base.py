"""
Enterprise database base models and repository patterns for MAESTRO.

Provides:
- BaseModel with SQLAlchemy 2.0 declarative base
- Mixins for common patterns (timestamps, tenancy, soft delete, audit)
- Generic BaseRepository with async CRUD operations
"""

from datetime import datetime
from typing import (
    Any, Dict, Generic, List, Optional, Sequence, Type, TypeVar, Union,
    Protocol, runtime_checkable
)
from uuid import uuid4
import re

from sqlalchemy import (
    Column, DateTime, String, Boolean, Index, select, delete, update, func,
    inspect, and_, or_
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, declared_attr
)
from sqlalchemy.ext.asyncio import AsyncSession


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
# Type Variables
# =============================================================================

ModelT = TypeVar("ModelT", bound="BaseModel")


# =============================================================================
# Base Model
# =============================================================================

class BaseModel(DeclarativeBase):
    """
    Base model class for all SQLAlchemy models.

    Uses SQLAlchemy 2.0 declarative base with type annotations.
    All models should inherit from this class.

    Attributes:
        id: Primary key (UUID string)
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
    """

    # Use string UUID as default primary key
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4())
    )

    # Automatic timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=True
    )

    @declared_attr.directive
    @classmethod
    def __tablename__(cls) -> str:
        """Generate table name from class name (CamelCase -> snake_case)."""
        name = cls.__name__
        # Convert CamelCase to snake_case
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def to_dict(self, exclude: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Convert model to dictionary.

        Args:
            exclude: List of column names to exclude

        Returns:
            Dictionary representation of the model
        """
        exclude = exclude or []
        result = {}

        for column in inspect(self.__class__).columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                # Convert datetime to ISO string
                if isinstance(value, datetime):
                    value = value.isoformat()
                result[column.name] = value

        return result

    @classmethod
    def from_dict(cls: Type[ModelT], data: Dict[str, Any]) -> ModelT:
        """
        Create model instance from dictionary.

        Args:
            data: Dictionary with model data

        Returns:
            New model instance
        """
        # Filter only valid columns
        valid_columns = {c.name for c in inspect(cls).columns}
        filtered_data = {k: v for k, v in data.items() if k in valid_columns}
        return cls(**filtered_data)

    def update_from_dict(self, data: Dict[str, Any], exclude: Optional[List[str]] = None) -> None:
        """
        Update model from dictionary.

        Args:
            data: Dictionary with updated values
            exclude: List of column names to exclude from update
        """
        exclude = exclude or ["id", "created_at"]
        valid_columns = {c.name for c in inspect(self.__class__).columns}

        for key, value in data.items():
            if key in valid_columns and key not in exclude:
                setattr(self, key, value)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"


# =============================================================================
# Mixins
# =============================================================================

class TenantMixin:
    """
    Mixin for multi-tenancy support.

    Adds tenant_id column for row-level tenant isolation.
    """

    tenant_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True
    )

    @declared_attr
    def __table_args__(cls):
        """Add tenant index to table arguments."""
        existing_args = getattr(super(), "__table_args__", ())
        if isinstance(existing_args, dict):
            return existing_args
        if isinstance(existing_args, tuple):
            return existing_args + (
                Index(f"idx_{cls.__tablename__}_tenant", "tenant_id"),
            )
        return (Index(f"idx_{cls.__tablename__}_tenant", "tenant_id"),)


class SoftDeleteMixin:
    """
    Mixin for soft delete functionality.

    Instead of physically deleting records, marks them as deleted.
    """

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        default=None
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )

    def soft_delete(self) -> None:
        """Mark record as soft deleted."""
        self.is_deleted = True
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Restore soft deleted record."""
        self.is_deleted = False
        self.deleted_at = None


class AuditMixin:
    """
    Mixin for audit trail tracking.

    Tracks who created and last updated the record.
    """

    created_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True
    )
    updated_by: Mapped[Optional[str]] = mapped_column(
        String(36),
        nullable=True
    )


class VersionMixin:
    """
    Mixin for optimistic locking with version number.

    Prevents concurrent update conflicts.
    """

    version: Mapped[int] = mapped_column(
        default=1,
        nullable=False
    )


# =============================================================================
# Protocol for Repository Pattern
# =============================================================================

@runtime_checkable
class RepositoryProtocol(Protocol[ModelT]):
    """Protocol defining repository interface."""

    async def get(self, id: str) -> Optional[ModelT]: ...
    async def get_by_ids(self, ids: List[str]) -> Sequence[ModelT]: ...
    async def list(self, limit: int = 100, offset: int = 0) -> Sequence[ModelT]: ...
    async def create(self, entity: ModelT) -> ModelT: ...
    async def update(self, entity: ModelT) -> ModelT: ...
    async def delete(self, id: str) -> bool: ...


# =============================================================================
# Base Repository
# =============================================================================

class BaseRepository(Generic[ModelT]):
    """
    Generic async repository with CRUD operations.

    Provides standard data access patterns for any SQLAlchemy model.
    Designed for use with async SQLAlchemy sessions.

    Example:
        ```python
        class UserRepository(BaseRepository[User]):
            def __init__(self, session: AsyncSession):
                super().__init__(session, User)

            async def find_by_email(self, email: str) -> Optional[User]:
                return await self.find_one(email=email)

        # Usage
        async with session_manager.get_session() as session:
            repo = UserRepository(session)
            user = await repo.get("user-123")
            users = await repo.list(limit=50)
        ```
    """

    def __init__(self, session: AsyncSession, model_class: Type[ModelT]):
        """
        Initialize repository.

        Args:
            session: Async SQLAlchemy session
            model_class: Model class this repository manages
        """
        self.session = session
        self.model_class = model_class

    async def get(self, id: str) -> Optional[ModelT]:
        """
        Get entity by ID.

        Args:
            id: Entity ID

        Returns:
            Entity if found, None otherwise
        """
        return await self.session.get(self.model_class, id)

    async def get_by_ids(self, ids: List[str]) -> Sequence[ModelT]:
        """
        Get multiple entities by IDs.

        Args:
            ids: List of entity IDs

        Returns:
            Sequence of found entities
        """
        if not ids:
            return []

        stmt = select(self.model_class).where(
            self.model_class.id.in_(ids)
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
        descending: bool = True,
        filters: Optional[Dict[str, Any]] = None
    ) -> Sequence[ModelT]:
        """
        List entities with pagination.

        Args:
            limit: Maximum number of results
            offset: Number of results to skip
            order_by: Column name to order by (default: created_at)
            descending: Sort in descending order
            filters: Dictionary of column=value filters

        Returns:
            Sequence of entities
        """
        stmt = select(self.model_class)

        # Apply filters
        if filters:
            for column_name, value in filters.items():
                if hasattr(self.model_class, column_name):
                    column = getattr(self.model_class, column_name)
                    stmt = stmt.where(column == value)

        # Apply ordering
        order_column = order_by or "created_at"
        if hasattr(self.model_class, order_column):
            column = getattr(self.model_class, order_column)
            if descending:
                stmt = stmt.order_by(column.desc())
            else:
                stmt = stmt.order_by(column.asc())

        # Apply pagination
        stmt = stmt.limit(limit).offset(offset)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def find_one(self, **kwargs) -> Optional[ModelT]:
        """
        Find a single entity by column values.

        Args:
            **kwargs: Column=value pairs to filter by

        Returns:
            First matching entity or None
        """
        stmt = select(self.model_class)

        for column_name, value in kwargs.items():
            if hasattr(self.model_class, column_name):
                column = getattr(self.model_class, column_name)
                stmt = stmt.where(column == value)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_all(self, **kwargs) -> Sequence[ModelT]:
        """
        Find all entities matching column values.

        Args:
            **kwargs: Column=value pairs to filter by

        Returns:
            Sequence of matching entities
        """
        stmt = select(self.model_class)

        for column_name, value in kwargs.items():
            if hasattr(self.model_class, column_name):
                column = getattr(self.model_class, column_name)
                stmt = stmt.where(column == value)

        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def exists(self, id: str) -> bool:
        """
        Check if entity exists.

        Args:
            id: Entity ID

        Returns:
            True if entity exists
        """
        stmt = select(func.count()).select_from(self.model_class).where(
            self.model_class.id == id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one() > 0

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count entities.

        Args:
            filters: Optional column=value filters

        Returns:
            Number of matching entities
        """
        stmt = select(func.count()).select_from(self.model_class)

        if filters:
            for column_name, value in filters.items():
                if hasattr(self.model_class, column_name):
                    column = getattr(self.model_class, column_name)
                    stmt = stmt.where(column == value)

        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def create(self, entity: ModelT) -> ModelT:
        """
        Create a new entity.

        Args:
            entity: Entity to create

        Returns:
            Created entity with generated ID
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def create_many(self, entities: List[ModelT]) -> List[ModelT]:
        """
        Create multiple entities.

        Args:
            entities: List of entities to create

        Returns:
            List of created entities
        """
        self.session.add_all(entities)
        await self.session.flush()

        for entity in entities:
            await self.session.refresh(entity)

        return entities

    async def update(self, entity: ModelT) -> ModelT:
        """
        Update an existing entity.

        Args:
            entity: Entity to update

        Returns:
            Updated entity
        """
        merged = await self.session.merge(entity)
        await self.session.flush()
        return merged

    async def update_by_id(
        self,
        id: str,
        values: Dict[str, Any]
    ) -> bool:
        """
        Update entity by ID with given values.

        Args:
            id: Entity ID
            values: Dictionary of column=value pairs to update

        Returns:
            True if entity was updated
        """
        # Remove protected fields
        values.pop("id", None)
        values.pop("created_at", None)

        # Add updated_at if model has it
        if hasattr(self.model_class, "updated_at"):
            values["updated_at"] = datetime.utcnow()

        stmt = (
            update(self.model_class)
            .where(self.model_class.id == id)
            .values(**values)
        )

        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def delete(self, id: str) -> bool:
        """
        Delete entity by ID.

        Args:
            id: Entity ID

        Returns:
            True if entity was deleted
        """
        stmt = delete(self.model_class).where(self.model_class.id == id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    async def delete_many(self, ids: List[str]) -> int:
        """
        Delete multiple entities by IDs.

        Args:
            ids: List of entity IDs

        Returns:
            Number of deleted entities
        """
        if not ids:
            return 0

        stmt = delete(self.model_class).where(self.model_class.id.in_(ids))
        result = await self.session.execute(stmt)
        return result.rowcount


class TenantAwareRepository(BaseRepository[ModelT]):
    """
    Repository with automatic tenant filtering.

    Ensures all queries are scoped to the current tenant.
    """

    def __init__(
        self,
        session: AsyncSession,
        model_class: Type[ModelT],
        tenant_id: str
    ):
        """
        Initialize tenant-aware repository.

        Args:
            session: Async SQLAlchemy session
            model_class: Model class (must include TenantMixin)
            tenant_id: Current tenant ID
        """
        super().__init__(session, model_class)
        self.tenant_id = tenant_id

        # Verify model has tenant_id column
        if not hasattr(model_class, "tenant_id"):
            raise ValueError(
                f"Model {model_class.__name__} must include TenantMixin for TenantAwareRepository"
            )

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
        descending: bool = True,
        filters: Optional[Dict[str, Any]] = None
    ) -> Sequence[ModelT]:
        """List entities filtered by tenant."""
        filters = filters or {}
        filters["tenant_id"] = self.tenant_id
        return await super().list(limit, offset, order_by, descending, filters)

    async def find_one(self, **kwargs) -> Optional[ModelT]:
        """Find entity filtered by tenant."""
        kwargs["tenant_id"] = self.tenant_id
        return await super().find_one(**kwargs)

    async def find_all(self, **kwargs) -> Sequence[ModelT]:
        """Find all entities filtered by tenant."""
        kwargs["tenant_id"] = self.tenant_id
        return await super().find_all(**kwargs)

    async def get(self, id: str) -> Optional[ModelT]:
        """Get entity by ID, ensuring tenant ownership."""
        entity = await super().get(id)
        if entity and getattr(entity, "tenant_id", None) != self.tenant_id:
            return None  # Entity belongs to different tenant
        return entity

    async def create(self, entity: ModelT) -> ModelT:
        """Create entity with tenant ID."""
        if hasattr(entity, "tenant_id"):
            setattr(entity, "tenant_id", self.tenant_id)
        return await super().create(entity)

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """Count entities filtered by tenant."""
        filters = filters or {}
        filters["tenant_id"] = self.tenant_id
        return await super().count(filters)

    async def delete(self, id: str) -> bool:
        """Delete entity by ID, ensuring tenant ownership."""
        # First check tenant ownership
        entity = await self.get(id)
        if not entity:
            return False
        return await super().delete(id)


class SoftDeleteRepository(BaseRepository[ModelT]):
    """
    Repository with soft delete support.

    Automatically filters out soft-deleted records.
    """

    def __init__(
        self,
        session: AsyncSession,
        model_class: Type[ModelT],
        include_deleted: bool = False
    ):
        """
        Initialize soft delete repository.

        Args:
            session: Async SQLAlchemy session
            model_class: Model class (must include SoftDeleteMixin)
            include_deleted: Whether to include soft-deleted records
        """
        super().__init__(session, model_class)
        self.include_deleted = include_deleted

        # Verify model has is_deleted column
        if not hasattr(model_class, "is_deleted"):
            raise ValueError(
                f"Model {model_class.__name__} must include SoftDeleteMixin for SoftDeleteRepository"
            )

    async def list(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
        descending: bool = True,
        filters: Optional[Dict[str, Any]] = None
    ) -> Sequence[ModelT]:
        """List entities, filtering out soft-deleted unless configured otherwise."""
        filters = filters or {}
        if not self.include_deleted:
            filters["is_deleted"] = False
        return await super().list(limit, offset, order_by, descending, filters)

    async def find_one(self, **kwargs) -> Optional[ModelT]:
        """Find entity, filtering out soft-deleted."""
        if not self.include_deleted:
            kwargs["is_deleted"] = False
        return await super().find_one(**kwargs)

    async def find_all(self, **kwargs) -> Sequence[ModelT]:
        """Find all entities, filtering out soft-deleted."""
        if not self.include_deleted:
            kwargs["is_deleted"] = False
        return await super().find_all(**kwargs)

    async def delete(self, id: str) -> bool:
        """Soft delete entity by ID."""
        return await self.update_by_id(id, {
            "is_deleted": True,
            "deleted_at": datetime.utcnow()
        })

    async def hard_delete(self, id: str) -> bool:
        """Permanently delete entity by ID."""
        return await super().delete(id)

    async def restore(self, id: str) -> bool:
        """Restore soft-deleted entity."""
        return await self.update_by_id(id, {
            "is_deleted": False,
            "deleted_at": None
        })


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Base model
    "BaseModel",

    # Mixins
    "TenantMixin",
    "SoftDeleteMixin",
    "AuditMixin",
    "VersionMixin",

    # Repositories
    "BaseRepository",
    "TenantAwareRepository",
    "SoftDeleteRepository",
    "RepositoryProtocol",

    # Type variables
    "ModelT",
]
