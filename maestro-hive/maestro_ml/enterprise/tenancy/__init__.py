"""
Multi-Tenancy Package

Provides tenant isolation and management capabilities.
"""

# Try to import, but handle missing classes gracefully
try:
    from .tenant_manager import (
        TenantManager,
        Tenant,
        TenantStatus
    )
except ImportError as e:
    # If specific imports fail, define minimal stubs
    TenantManager = None
    Tenant = None
    TenantStatus = None

try:
    from .tenant_isolation import (
        TenantContext,
        TenantIsolationMiddleware,
        tenant_context,
        apply_tenant_filter,
        setup_tenant_isolation,
        TenantAwareQueryMixin,
        enforce_tenant_on_create,
        verify_tenant_access,
        require_tenant_context
    )
except ImportError:
    # If tenant_isolation module doesn't fully work, use None
    TenantContext = None
    TenantIsolationMiddleware = None
    tenant_context = None
    apply_tenant_filter = None
    setup_tenant_isolation = None
    TenantAwareQueryMixin = None
    enforce_tenant_on_create = None
    verify_tenant_access = None
    require_tenant_context = None

__all__ = [
    # Tenant management
    "TenantManager",
    "Tenant",
    "TenantStatus",
    # Tenant isolation
    "TenantContext",
    "TenantIsolationMiddleware",
    "tenant_context",
    "apply_tenant_filter",
    "setup_tenant_isolation",
    "TenantAwareQueryMixin",
    "enforce_tenant_on_create",
    "verify_tenant_access",
    "require_tenant_context"
]
