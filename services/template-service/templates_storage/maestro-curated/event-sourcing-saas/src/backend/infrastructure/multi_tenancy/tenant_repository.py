"""Tenant repository for tenant management."""
from typing import Optional
from uuid import UUID
import asyncpg
from asyncpg.pool import Pool
from pydantic import BaseModel
from datetime import datetime


class Tenant(BaseModel):
    """Tenant model."""

    tenant_id: UUID
    tenant_name: str
    subscription_tier: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    settings: dict = {}


class TenantRepository:
    """Repository for tenant operations."""

    def __init__(self, pool: Pool):
        self.pool = pool

    async def get_by_id(self, tenant_id: UUID) -> Optional[Tenant]:
        """Get tenant by ID."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT tenant_id, tenant_name, subscription_tier,
                       is_active, created_at, updated_at, settings
                FROM tenants
                WHERE tenant_id = $1
                """,
                tenant_id
            )

            if row:
                return Tenant(**dict(row))
            return None

    async def create(self, tenant: Tenant) -> Tenant:
        """Create a new tenant."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO tenants (
                    tenant_id, tenant_name, subscription_tier,
                    is_active, created_at, updated_at, settings
                ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                tenant.tenant_id,
                tenant.tenant_name,
                tenant.subscription_tier,
                tenant.is_active,
                tenant.created_at,
                tenant.updated_at,
                tenant.settings
            )

            return tenant

    async def update(self, tenant: Tenant) -> Tenant:
        """Update tenant."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE tenants
                SET tenant_name = $2, subscription_tier = $3,
                    is_active = $4, updated_at = $5, settings = $6
                WHERE tenant_id = $1
                """,
                tenant.tenant_id,
                tenant.tenant_name,
                tenant.subscription_tier,
                tenant.is_active,
                datetime.utcnow(),
                tenant.settings
            )

            return tenant

    async def delete(self, tenant_id: UUID) -> bool:
        """Soft delete tenant."""
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE tenants
                SET is_active = false, updated_at = $2
                WHERE tenant_id = $1
                """,
                tenant_id,
                datetime.utcnow()
            )

            return result == "UPDATE 1"