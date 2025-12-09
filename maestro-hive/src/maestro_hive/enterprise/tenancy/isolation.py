"""
Tenant Isolation with Row-Level Security.

Implements PostgreSQL RLS policies for secure multi-tenant data isolation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from enum import Enum
import asyncio


class IsolationLevel(Enum):
    """Tenant isolation levels."""
    STRICT = "strict"  # Full RLS enforcement
    SHARED = "shared"  # Shared tables with tenant column
    HYBRID = "hybrid"  # Mix of strict and shared


@dataclass
class RLSPolicy:
    """Row-level security policy definition."""
    name: str
    table_name: str
    policy_type: str  # PERMISSIVE or RESTRICTIVE
    command: str  # ALL, SELECT, INSERT, UPDATE, DELETE
    using_expression: str
    with_check_expression: Optional[str] = None
    roles: List[str] = field(default_factory=lambda: ["PUBLIC"])
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class TenantTable:
    """Table configuration for multi-tenancy."""
    name: str
    tenant_column: str = "tenant_id"
    has_rls: bool = False
    policies: List[RLSPolicy] = field(default_factory=list)


class TenantRLS:
    """
    Row-Level Security manager for tenant isolation.

    Implements PostgreSQL RLS policies to enforce data isolation
    between tenants at the database level.
    """

    def __init__(self, connection_pool=None):
        """
        Initialize RLS manager.

        Args:
            connection_pool: asyncpg connection pool
        """
        self.pool = connection_pool
        self._tenant_tables: Dict[str, TenantTable] = {}
        self._current_tenant: Optional[str] = None

    async def setup_rls_for_table(
        self,
        table_name: str,
        tenant_column: str = "tenant_id",
        policy_name: Optional[str] = None,
    ) -> RLSPolicy:
        """
        Enable RLS and create tenant isolation policy for table.

        Args:
            table_name: Table to protect
            tenant_column: Column containing tenant ID
            policy_name: Custom policy name

        Returns:
            Created RLSPolicy
        """
        policy_name = policy_name or f"tenant_isolation_{table_name}"

        # Enable RLS on table
        enable_rls_sql = f"""
            ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY;
            ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY;
        """

        # Create tenant isolation policy
        policy_sql = f"""
            CREATE POLICY {policy_name}
            ON {table_name}
            FOR ALL
            TO PUBLIC
            USING ({tenant_column}::text = current_setting('app.current_tenant', true))
            WITH CHECK ({tenant_column}::text = current_setting('app.current_tenant', true));
        """

        if self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute(enable_rls_sql)
                await conn.execute(policy_sql)

        policy = RLSPolicy(
            name=policy_name,
            table_name=table_name,
            policy_type="PERMISSIVE",
            command="ALL",
            using_expression=f"{tenant_column}::text = current_setting('app.current_tenant', true)",
            with_check_expression=f"{tenant_column}::text = current_setting('app.current_tenant', true)",
        )

        # Track table configuration
        self._tenant_tables[table_name] = TenantTable(
            name=table_name,
            tenant_column=tenant_column,
            has_rls=True,
            policies=[policy],
        )

        return policy

    async def set_tenant_context(self, tenant_id: str) -> None:
        """
        Set current tenant for database session.

        This sets a session variable that RLS policies use
        to filter data to the current tenant.

        Args:
            tenant_id: Tenant ID to set as current
        """
        self._current_tenant = tenant_id

        if self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    f"SET LOCAL app.current_tenant = '{tenant_id}'"
                )

    async def clear_tenant_context(self) -> None:
        """Clear current tenant context."""
        self._current_tenant = None

        if self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute("RESET app.current_tenant")

    def get_current_tenant(self) -> Optional[str]:
        """Get currently set tenant ID."""
        return self._current_tenant

    async def create_admin_bypass_role(
        self,
        role_name: str = "tenant_admin",
    ) -> None:
        """
        Create role that bypasses RLS for admin operations.

        Args:
            role_name: Name of admin role
        """
        sql = f"""
            CREATE ROLE {role_name} NOLOGIN;
            ALTER ROLE {role_name} SET row_security = off;
        """

        if self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute(sql)

    async def grant_table_access(
        self,
        table_name: str,
        role_name: str,
        privileges: List[str] = None,
    ) -> None:
        """
        Grant table access to role.

        Args:
            table_name: Table name
            role_name: Role to grant to
            privileges: List of privileges (default: SELECT, INSERT, UPDATE, DELETE)
        """
        privileges = privileges or ["SELECT", "INSERT", "UPDATE", "DELETE"]
        privs = ", ".join(privileges)

        if self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute(
                    f"GRANT {privs} ON {table_name} TO {role_name}"
                )

    async def list_policies(self, table_name: str) -> List[Dict[str, Any]]:
        """
        List RLS policies for table.

        Args:
            table_name: Table name

        Returns:
            List of policy information
        """
        sql = """
            SELECT polname, polcmd, polpermissive, polroles, polqual, polwithcheck
            FROM pg_policy
            WHERE polrelid = %s::regclass;
        """

        if self.pool:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(sql, table_name)
                return [dict(row) for row in rows]

        return []

    async def drop_policy(self, table_name: str, policy_name: str) -> bool:
        """
        Drop RLS policy from table.

        Args:
            table_name: Table name
            policy_name: Policy to drop

        Returns:
            True if dropped successfully
        """
        sql = f"DROP POLICY IF EXISTS {policy_name} ON {table_name}"

        if self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute(sql)
                return True

        return False

    async def disable_rls(self, table_name: str) -> None:
        """
        Disable RLS on table.

        Args:
            table_name: Table name
        """
        sql = f"""
            ALTER TABLE {table_name} DISABLE ROW LEVEL SECURITY;
            ALTER TABLE {table_name} NO FORCE ROW LEVEL SECURITY;
        """

        if self.pool:
            async with self.pool.acquire() as conn:
                await conn.execute(sql)

        if table_name in self._tenant_tables:
            self._tenant_tables[table_name].has_rls = False

    def get_protected_tables(self) -> List[str]:
        """Get list of RLS-protected tables."""
        return [
            name for name, table in self._tenant_tables.items()
            if table.has_rls
        ]


class TenantIsolationMiddleware:
    """
    Middleware for automatic tenant context setting.

    Extracts tenant ID from request headers or JWT and
    sets database context automatically.
    """

    TENANT_HEADER = "X-Tenant-ID"

    def __init__(self, rls_manager: TenantRLS):
        """Initialize middleware."""
        self.rls = rls_manager

    async def __call__(self, request, call_next):
        """
        Process request with tenant context.

        Args:
            request: HTTP request
            call_next: Next middleware/handler
        """
        tenant_id = self._extract_tenant_id(request)

        if tenant_id:
            await self.rls.set_tenant_context(tenant_id)

        try:
            response = await call_next(request)
            return response
        finally:
            if tenant_id:
                await self.rls.clear_tenant_context()

    def _extract_tenant_id(self, request) -> Optional[str]:
        """Extract tenant ID from request."""
        # Try header first
        tenant_id = request.headers.get(self.TENANT_HEADER)
        if tenant_id:
            return tenant_id

        # Try JWT claims
        if hasattr(request, "state") and hasattr(request.state, "user"):
            return getattr(request.state.user, "tenant_id", None)

        return None
