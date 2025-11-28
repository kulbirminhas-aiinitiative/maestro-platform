"""Query API endpoints."""
from fastapi import APIRouter, Depends
from typing import Dict, Any

from ...application.queries.query_handler import QueryBus
from ..dependencies import get_query_bus, verify_tenant_context
from ...infrastructure.multi_tenancy.tenant_context import TenantContext


router = APIRouter()


@router.post("/execute", response_model=Dict[str, Any])
async def execute_query(
    query_data: Dict[str, Any],
    query_bus: QueryBus = Depends(get_query_bus),
    tenant_context: TenantContext = Depends(verify_tenant_context)
) -> Dict[str, Any]:
    """Execute a query."""
    return {
        "success": True,
        "message": "Query endpoint ready",
        "tenant_id": str(tenant_context.tenant_id)
    }