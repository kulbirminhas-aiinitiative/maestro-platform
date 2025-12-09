"""
Multi-Tenancy Module for enterprise features.

Provides:
- Row-level security (RLS) for PostgreSQL
- Per-tenant feature flags
- Tenant context management
"""

from .isolation import TenantRLS, TenantIsolationMiddleware
from .feature_flags import TenantFeatureFlags, FeatureFlag, FlagVariant
from .context import TenantContext, get_current_tenant

__all__ = [
    "TenantRLS",
    "TenantIsolationMiddleware",
    "TenantFeatureFlags",
    "FeatureFlag",
    "FlagVariant",
    "TenantContext",
    "get_current_tenant",
]
