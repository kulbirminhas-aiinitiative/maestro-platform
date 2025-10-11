"""
Tenant Isolation for Database Queries

Provides automatic tenant filtering for SQLAlchemy queries to enforce multi-tenancy.
"""

import logging
from typing import Optional, Any
from contextlib import contextmanager
from sqlalchemy import event
from sqlalchemy.orm import Session, Query
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# Context variable to store current tenant ID
current_tenant_id: ContextVar[Optional[str]] = ContextVar('current_tenant_id', default=None)


class TenantContext:
    """
    Tenant context manager.

    Stores current tenant ID in context variable for request lifetime.
    """

    @staticmethod
    def set_tenant(tenant_id: Optional[str]):
        """Set current tenant ID"""
        current_tenant_id.set(tenant_id)
        logger.debug(f"Set tenant context: {tenant_id}")

    @staticmethod
    def get_tenant() -> Optional[str]:
        """Get current tenant ID"""
        return current_tenant_id.get()

    @staticmethod
    def clear():
        """Clear tenant context"""
        current_tenant_id.set(None)
        logger.debug("Cleared tenant context")


@contextmanager
def tenant_context(tenant_id: str):
    """
    Context manager for tenant isolation.

    Usage:
        with tenant_context("tenant-123"):
            # All queries in this block are filtered by tenant
            models = session.query(Model).all()
    """
    TenantContext.set_tenant(tenant_id)
    try:
        yield
    finally:
        TenantContext.clear()


class TenantIsolationMiddleware:
    """
    Middleware to automatically set tenant context from request headers.
    """

    async def __call__(self, request: Request, call_next):
        """
        Extract tenant ID from request and set context.

        Args:
            request: Incoming request
            call_next: Next handler

        Returns:
            Response
        """
        # Extract tenant from header
        tenant_id = request.headers.get("x-tenant-id")

        # Set tenant context for request lifetime
        if tenant_id:
            TenantContext.set_tenant(tenant_id)

        try:
            response = await call_next(request)
            return response
        finally:
            # Clear context after request
            TenantContext.clear()


def apply_tenant_filter(query: Query, model_class: Any) -> Query:
    """
    Apply tenant filter to SQLAlchemy query.

    Args:
        query: SQLAlchemy query
        model_class: Model class being queried

    Returns:
        Filtered query
    """
    # Check if model has tenant_id column
    if not hasattr(model_class, 'tenant_id'):
        # Model is not tenant-scoped
        return query

    # Get current tenant
    tenant_id = TenantContext.get_tenant()

    if tenant_id:
        # Filter by tenant
        query = query.filter(model_class.tenant_id == tenant_id)
        logger.debug(f"Applied tenant filter: {tenant_id} to {model_class.__name__}")

    return query


def setup_tenant_isolation(engine):
    """
    Setup automatic tenant isolation for SQLAlchemy engine.

    This registers event listeners that automatically filter queries by tenant.

    Args:
        engine: SQLAlchemy engine

    Example:
        from maestro_ml.core.database import engine
        from maestro_ml.enterprise.tenancy import setup_tenant_isolation

        setup_tenant_isolation(engine)
    """

    @event.listens_for(Session, "do_orm_execute")
    def receive_do_orm_execute(orm_execute_state):
        """
        Intercept ORM execute and add tenant filter.

        This automatically adds tenant_id filtering to all queries.
        """
        if orm_execute_state.is_select:
            # Get the model class from the query
            entities = orm_execute_state.statement.column_descriptions

            for entity in entities:
                if 'entity' in entity and entity['entity']:
                    model_class = entity['entity']

                    # Apply tenant filter
                    if hasattr(model_class, 'tenant_id'):
                        tenant_id = TenantContext.get_tenant()

                        if tenant_id:
                            # Add tenant filter to WHERE clause
                            orm_execute_state.statement = (
                                orm_execute_state.statement.filter(
                                    model_class.tenant_id == tenant_id
                                )
                            )
                            logger.debug(
                                f"Auto-filtered query for {model_class.__name__} "
                                f"with tenant_id={tenant_id}"
                            )

    logger.info("Tenant isolation event listeners registered")


class TenantAwareQueryMixin:
    """
    Mixin to add tenant-aware query methods to models.

    Usage:
        class MyModel(Base, TenantAwareQueryMixin):
            __tablename__ = 'my_models'
            id = Column(String, primary_key=True)
            tenant_id = Column(String, nullable=False, index=True)
            name = Column(String)

        # Queries are automatically filtered by tenant
        with tenant_context("tenant-123"):
            models = MyModel.query_for_tenant(session).all()
    """

    @classmethod
    def query_for_tenant(cls, session: Session, tenant_id: Optional[str] = None):
        """
        Get query filtered by tenant.

        Args:
            session: Database session
            tenant_id: Tenant ID (uses context if not provided)

        Returns:
            Filtered query
        """
        tenant = tenant_id or TenantContext.get_tenant()

        query = session.query(cls)

        if hasattr(cls, 'tenant_id') and tenant:
            query = query.filter(cls.tenant_id == tenant)

        return query

    @classmethod
    async def query_for_tenant_async(
        cls,
        session: AsyncSession,
        tenant_id: Optional[str] = None
    ):
        """
        Get async query filtered by tenant.

        Args:
            session: Async database session
            tenant_id: Tenant ID (uses context if not provided)

        Returns:
            Filtered query
        """
        from sqlalchemy import select

        tenant = tenant_id or TenantContext.get_tenant()

        stmt = select(cls)

        if hasattr(cls, 'tenant_id') and tenant:
            stmt = stmt.filter(cls.tenant_id == tenant)

        return stmt


def enforce_tenant_on_create(obj: Any, tenant_id: Optional[str] = None):
    """
    Enforce tenant ID on object creation.

    Args:
        obj: Object to set tenant on
        tenant_id: Tenant ID (uses context if not provided)

    Raises:
        ValueError: If no tenant context is set

    Example:
        model = Model(name="test")
        enforce_tenant_on_create(model)  # Sets tenant_id from context
        session.add(model)
    """
    if not hasattr(obj, 'tenant_id'):
        return

    tenant = tenant_id or TenantContext.get_tenant()

    if not tenant:
        raise ValueError(
            f"Cannot create {obj.__class__.__name__} without tenant context. "
            "Set tenant using tenant_context() or provide tenant_id."
        )

    obj.tenant_id = tenant
    logger.debug(f"Set tenant_id={tenant} on {obj.__class__.__name__}")


def verify_tenant_access(obj: Any, user_tenant_id: str):
    """
    Verify user has access to object based on tenant.

    Args:
        obj: Object to check
        user_tenant_id: User's tenant ID

    Raises:
        PermissionError: If tenant mismatch

    Example:
        model = session.query(Model).filter(Model.id == model_id).first()
        verify_tenant_access(model, user.tenant_id)
    """
    if not hasattr(obj, 'tenant_id'):
        # Object is not tenant-scoped
        return

    if obj.tenant_id != user_tenant_id:
        logger.warning(
            f"Tenant access violation: User tenant {user_tenant_id} "
            f"attempted to access {obj.__class__.__name__} from tenant {obj.tenant_id}"
        )
        raise PermissionError(
            f"Access denied: Cannot access resource from another tenant"
        )


# Decorator for tenant-aware routes
def require_tenant_context(func):
    """
    Decorator to ensure tenant context is set for route.

    Usage:
        @app.get("/models")
        @require_tenant_context
        async def list_models(db: Session = Depends(get_db)):
            # Tenant context is guaranteed to be set
            models = db.query(Model).all()  # Auto-filtered by tenant
            return models
    """
    from functools import wraps

    @wraps(func)
    async def wrapper(*args, **kwargs):
        tenant_id = TenantContext.get_tenant()

        if not tenant_id:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant context required (x-tenant-id header)"
            )

        return await func(*args, **kwargs)

    return wrapper
