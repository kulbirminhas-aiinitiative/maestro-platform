"""Tenant context and isolation management."""
from contextvars import ContextVar
from typing import Optional
from uuid import UUID
from dataclasses import dataclass


@dataclass
class TenantContext:
    """Context information for current tenant."""

    tenant_id: UUID
    tenant_name: str
    subscription_tier: str
    is_active: bool = True


# Context variable for tenant
_tenant_context: ContextVar[Optional[TenantContext]] = ContextVar(
    'tenant_context',
    default=None
)


def set_tenant_context(context: TenantContext) -> None:
    """Set the current tenant context."""
    _tenant_context.set(context)


def get_tenant_context() -> Optional[TenantContext]:
    """Get the current tenant context."""
    return _tenant_context.get()


def clear_tenant_context() -> None:
    """Clear the current tenant context."""
    _tenant_context.set(None)


def get_current_tenant_id() -> UUID:
    """Get the current tenant ID."""
    context = get_tenant_context()
    if context is None:
        raise RuntimeError("No tenant context set")
    return context.tenant_id


class TenantContextMiddleware:
    """Middleware to set tenant context from request."""

    async def __call__(self, request, call_next):
        """Process request and set tenant context."""
        tenant_id = request.headers.get('X-Tenant-ID')

        if tenant_id:
            # In production, fetch full tenant info from database
            context = TenantContext(
                tenant_id=UUID(tenant_id),
                tenant_name="",  # Fetch from DB
                subscription_tier="standard"  # Fetch from DB
            )
            set_tenant_context(context)

        try:
            response = await call_next(request)
            return response
        finally:
            clear_tenant_context()