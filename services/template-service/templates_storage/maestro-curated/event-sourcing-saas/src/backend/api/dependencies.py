"""FastAPI dependencies."""
from fastapi import Header, HTTPException, Request
from typing import Optional
from uuid import UUID

from ..application.commands.command_handler import CommandBus
from ..application.queries.query_handler import QueryBus
from ..infrastructure.multi_tenancy.tenant_context import get_tenant_context, TenantContext


async def get_command_bus(request: Request) -> CommandBus:
    """Get command bus instance."""
    return request.app.state.command_bus


async def get_query_bus(request: Request) -> QueryBus:
    """Get query bus instance."""
    return request.app.state.query_bus


async def get_tenant_id(x_tenant_id: Optional[str] = Header(None)) -> UUID:
    """Extract and validate tenant ID from header."""
    if not x_tenant_id:
        raise HTTPException(status_code=400, detail="X-Tenant-ID header required")

    try:
        return UUID(x_tenant_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid tenant ID format")


async def verify_tenant_context() -> TenantContext:
    """Verify tenant context is set."""
    context = get_tenant_context()
    if context is None:
        raise HTTPException(status_code=401, detail="No tenant context")

    if not context.is_active:
        raise HTTPException(status_code=403, detail="Tenant is not active")

    return context