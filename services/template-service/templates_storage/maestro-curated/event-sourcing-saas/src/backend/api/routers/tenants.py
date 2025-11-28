"""Tenant management API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request
from uuid import UUID, uuid4
from datetime import datetime
from typing import List

from ...infrastructure.multi_tenancy.tenant_repository import Tenant, TenantRepository


router = APIRouter()


async def get_tenant_repository(request: Request) -> TenantRepository:
    """Get tenant repository."""
    return TenantRepository(request.app.state.db_pool)


@router.post("/", response_model=Tenant)
async def create_tenant(
    tenant_data: dict,
    repo: TenantRepository = Depends(get_tenant_repository)
) -> Tenant:
    """Create a new tenant."""
    tenant = Tenant(
        tenant_id=uuid4(),
        tenant_name=tenant_data["tenant_name"],
        subscription_tier=tenant_data.get("subscription_tier", "standard"),
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        settings=tenant_data.get("settings", {})
    )

    return await repo.create(tenant)


@router.get("/{tenant_id}", response_model=Tenant)
async def get_tenant(
    tenant_id: UUID,
    repo: TenantRepository = Depends(get_tenant_repository)
) -> Tenant:
    """Get tenant by ID."""
    tenant = await repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.put("/{tenant_id}", response_model=Tenant)
async def update_tenant(
    tenant_id: UUID,
    tenant_data: dict,
    repo: TenantRepository = Depends(get_tenant_repository)
) -> Tenant:
    """Update tenant."""
    tenant = await repo.get_by_id(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    tenant.tenant_name = tenant_data.get("tenant_name", tenant.tenant_name)
    tenant.subscription_tier = tenant_data.get("subscription_tier", tenant.subscription_tier)
    tenant.settings = tenant_data.get("settings", tenant.settings)

    return await repo.update(tenant)


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: UUID,
    repo: TenantRepository = Depends(get_tenant_repository)
) -> dict:
    """Delete tenant (soft delete)."""
    success = await repo.delete(tenant_id)
    if not success:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {"success": True, "message": "Tenant deleted"}