"""
Tenant Context Management.

Provides request-scoped tenant context using context variables.
"""

import contextvars
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum


# Context variable for current tenant
_current_tenant: contextvars.ContextVar[Optional["TenantContext"]] = contextvars.ContextVar(
    "current_tenant", default=None
)


class TenantPlan(Enum):
    """Tenant subscription plans."""
    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


@dataclass
class TenantLimits:
    """Resource limits for tenant plan."""
    max_users: int = 5
    max_workflows: int = 10
    max_api_calls_per_day: int = 1000
    max_storage_gb: int = 1
    features: List[str] = field(default_factory=list)

    @classmethod
    def for_plan(cls, plan: TenantPlan) -> "TenantLimits":
        """Get limits for subscription plan."""
        limits = {
            TenantPlan.FREE: cls(
                max_users=5,
                max_workflows=10,
                max_api_calls_per_day=1000,
                max_storage_gb=1,
                features=["basic_workflows"],
            ),
            TenantPlan.STARTER: cls(
                max_users=25,
                max_workflows=100,
                max_api_calls_per_day=10000,
                max_storage_gb=10,
                features=["basic_workflows", "api_access", "email_support"],
            ),
            TenantPlan.PROFESSIONAL: cls(
                max_users=100,
                max_workflows=1000,
                max_api_calls_per_day=100000,
                max_storage_gb=100,
                features=["basic_workflows", "api_access", "priority_support", "sso", "audit_logs"],
            ),
            TenantPlan.ENTERPRISE: cls(
                max_users=-1,  # Unlimited
                max_workflows=-1,
                max_api_calls_per_day=-1,
                max_storage_gb=-1,
                features=["all"],
            ),
        }
        return limits.get(plan, limits[TenantPlan.FREE])


@dataclass
class TenantContext:
    """
    Tenant context for request processing.

    Stores tenant-specific information for the current request,
    accessible via context variables.
    """

    tenant_id: str
    tenant_name: str
    plan: TenantPlan = TenantPlan.FREE
    limits: TenantLimits = field(default_factory=TenantLimits)
    settings: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        """Initialize limits based on plan if not provided."""
        if not self.limits.features:
            self.limits = TenantLimits.for_plan(self.plan)

    def has_feature(self, feature: str) -> bool:
        """
        Check if tenant has access to feature.

        Args:
            feature: Feature name

        Returns:
            True if feature is available
        """
        if "all" in self.limits.features:
            return True
        return feature in self.limits.features

    def check_limit(self, resource: str, current_value: int) -> bool:
        """
        Check if resource limit is exceeded.

        Args:
            resource: Resource name (users, workflows, etc.)
            current_value: Current usage

        Returns:
            True if within limits
        """
        limit_map = {
            "users": self.limits.max_users,
            "workflows": self.limits.max_workflows,
            "api_calls": self.limits.max_api_calls_per_day,
            "storage": self.limits.max_storage_gb,
        }

        limit = limit_map.get(resource)
        if limit is None:
            return True  # Unknown resource, allow

        if limit == -1:
            return True  # Unlimited

        return current_value < limit

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        Get tenant setting.

        Args:
            key: Setting key
            default: Default value

        Returns:
            Setting value
        """
        return self.settings.get(key, default)


def get_current_tenant() -> Optional[TenantContext]:
    """
    Get current tenant context.

    Returns:
        TenantContext or None if not set
    """
    return _current_tenant.get()


def set_current_tenant(tenant: TenantContext) -> contextvars.Token:
    """
    Set current tenant context.

    Args:
        tenant: Tenant context to set

    Returns:
        Token for resetting context
    """
    return _current_tenant.set(tenant)


def clear_current_tenant(token: Optional[contextvars.Token] = None) -> None:
    """
    Clear current tenant context.

    Args:
        token: Token from set_current_tenant
    """
    if token:
        _current_tenant.reset(token)
    else:
        _current_tenant.set(None)


class TenantContextManager:
    """
    Context manager for tenant context.

    Usage:
        async with TenantContextManager(tenant):
            # Request processing with tenant context
            pass
    """

    def __init__(self, tenant: TenantContext):
        """Initialize with tenant context."""
        self.tenant = tenant
        self._token: Optional[contextvars.Token] = None

    def __enter__(self) -> TenantContext:
        """Enter context, setting tenant."""
        self._token = set_current_tenant(self.tenant)
        return self.tenant

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context, clearing tenant."""
        clear_current_tenant(self._token)

    async def __aenter__(self) -> TenantContext:
        """Async enter."""
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async exit."""
        self.__exit__(exc_type, exc_val, exc_tb)


def require_tenant() -> TenantContext:
    """
    Get current tenant, raising if not set.

    Returns:
        TenantContext

    Raises:
        ValueError: If no tenant context is set
    """
    tenant = get_current_tenant()
    if tenant is None:
        raise ValueError("No tenant context set")
    return tenant


def require_feature(feature: str) -> TenantContext:
    """
    Require tenant with specific feature.

    Args:
        feature: Required feature

    Returns:
        TenantContext

    Raises:
        ValueError: If tenant lacks feature
    """
    tenant = require_tenant()
    if not tenant.has_feature(feature):
        raise ValueError(f"Tenant does not have access to feature: {feature}")
    return tenant
