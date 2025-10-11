"""
Multi-Tenancy Manager

Tenant isolation, resource quotas, and data segregation.
"""

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class TenantTier(str, Enum):
    """Tenant subscription tiers"""

    FREE = "free"
    STARTER = "starter"
    PROFESSIONAL = "professional"
    ENTERPRISE = "enterprise"


class ResourceQuota(BaseModel):
    """Resource usage quotas for a tenant"""

    # Models
    max_models: int = Field(10, description="Maximum number of models")
    max_model_size_mb: int = Field(1000, description="Maximum model size in MB")

    # Experiments
    max_experiments_per_month: int = Field(100, description="Experiments per month")

    # Data
    max_storage_gb: int = Field(10, description="Maximum storage in GB")
    max_datasets: int = Field(50, description="Maximum number of datasets")

    # Compute
    max_concurrent_training_jobs: int = Field(2, description="Concurrent training jobs")
    max_gpu_hours_per_month: int = Field(100, description="GPU hours per month")
    max_cpu_hours_per_month: int = Field(500, description="CPU hours per month")

    # API
    max_api_requests_per_day: int = Field(10000, description="API requests per day")
    max_api_requests_per_minute: int = Field(100, description="API rate limit")

    # Users
    max_users: int = Field(5, description="Maximum number of users")


class ResourceUsage(BaseModel):
    """Current resource usage for a tenant"""

    # Models
    num_models: int = 0
    total_model_size_mb: float = 0.0

    # Experiments
    experiments_this_month: int = 0

    # Data
    storage_used_gb: float = 0.0
    num_datasets: int = 0

    # Compute
    concurrent_training_jobs: int = 0
    gpu_hours_this_month: float = 0.0
    cpu_hours_this_month: float = 0.0

    # API
    api_requests_today: int = 0
    api_requests_this_minute: int = 0

    # Users
    num_users: int = 0

    # Timestamp
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class Tenant(BaseModel):
    """
    Tenant (organization) definition

    Provides isolated environment for each customer.
    """

    tenant_id: str
    name: str
    description: Optional[str] = None

    # Subscription
    tier: TenantTier = TenantTier.FREE
    is_active: bool = True

    # Quotas
    quota: ResourceQuota = Field(default_factory=ResourceQuota)
    usage: ResourceUsage = Field(default_factory=ResourceUsage)

    # Contact
    admin_email: str
    billing_email: Optional[str] = None

    # Metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Custom settings
    settings: dict[str, Any] = Field(default_factory=dict)


class TenantManager:
    """
    Multi-tenancy manager

    Features:
    - Tenant isolation
    - Resource quotas
    - Usage tracking
    - Tier-based limits
    """

    def __init__(self):
        self.tenants: dict[str, Tenant] = {}
        self.logger = logger

        # Tier-based default quotas
        self.tier_quotas = {
            TenantTier.FREE: ResourceQuota(
                max_models=5,
                max_model_size_mb=500,
                max_experiments_per_month=50,
                max_storage_gb=5,
                max_datasets=20,
                max_concurrent_training_jobs=1,
                max_gpu_hours_per_month=10,
                max_cpu_hours_per_month=100,
                max_api_requests_per_day=1000,
                max_api_requests_per_minute=10,
                max_users=2,
            ),
            TenantTier.STARTER: ResourceQuota(
                max_models=20,
                max_model_size_mb=2000,
                max_experiments_per_month=200,
                max_storage_gb=50,
                max_datasets=100,
                max_concurrent_training_jobs=3,
                max_gpu_hours_per_month=100,
                max_cpu_hours_per_month=500,
                max_api_requests_per_day=10000,
                max_api_requests_per_minute=100,
                max_users=10,
            ),
            TenantTier.PROFESSIONAL: ResourceQuota(
                max_models=100,
                max_model_size_mb=10000,
                max_experiments_per_month=1000,
                max_storage_gb=500,
                max_datasets=500,
                max_concurrent_training_jobs=10,
                max_gpu_hours_per_month=1000,
                max_cpu_hours_per_month=5000,
                max_api_requests_per_day=100000,
                max_api_requests_per_minute=1000,
                max_users=50,
            ),
            TenantTier.ENTERPRISE: ResourceQuota(
                max_models=999999,
                max_model_size_mb=999999,
                max_experiments_per_month=999999,
                max_storage_gb=999999,
                max_datasets=999999,
                max_concurrent_training_jobs=100,
                max_gpu_hours_per_month=999999,
                max_cpu_hours_per_month=999999,
                max_api_requests_per_day=999999,
                max_api_requests_per_minute=10000,
                max_users=999999,
            ),
        }

    def create_tenant(
        self,
        tenant_id: str,
        name: str,
        admin_email: str,
        tier: TenantTier = TenantTier.FREE,
        **kwargs,
    ) -> Tenant:
        """
        Create a new tenant

        Args:
            tenant_id: Unique tenant identifier
            name: Tenant name
            admin_email: Administrator email
            tier: Subscription tier
            **kwargs: Additional tenant attributes

        Returns:
            Created tenant
        """
        if tenant_id in self.tenants:
            raise ValueError(f"Tenant {tenant_id} already exists")

        # Get default quota for tier
        quota = self.tier_quotas[tier]

        tenant = Tenant(
            tenant_id=tenant_id,
            name=name,
            admin_email=admin_email,
            tier=tier,
            quota=quota,
            **kwargs,
        )

        self.tenants[tenant_id] = tenant
        self.logger.info(f"Created tenant: {name} ({tenant_id}) - {tier.value}")

        return tenant

    def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Get tenant by ID"""
        return self.tenants.get(tenant_id)

    def update_tenant_tier(self, tenant_id: str, new_tier: TenantTier):
        """
        Update tenant subscription tier

        Args:
            tenant_id: Tenant ID
            new_tier: New subscription tier
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        old_tier = tenant.tier
        tenant.tier = new_tier
        tenant.quota = self.tier_quotas[new_tier]
        tenant.updated_at = datetime.utcnow()

        self.logger.info(
            f"Updated tenant {tenant_id} tier: {old_tier.value} → {new_tier.value}"
        )

    def check_quota(
        self, tenant_id: str, resource_type: str, requested_amount: float = 1.0
    ) -> tuple[bool, str]:
        """
        Check if tenant has available quota

        Args:
            tenant_id: Tenant ID
            resource_type: Type of resource (e.g., 'models', 'storage_gb')
            requested_amount: Amount requested

        Returns:
            (has_quota, reason) tuple
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            return False, "Tenant not found"

        if not tenant.is_active:
            return False, "Tenant is inactive"

        quota = tenant.quota
        usage = tenant.usage

        # Check specific resource
        if resource_type == "models":
            if usage.num_models + requested_amount > quota.max_models:
                return False, f"Model quota exceeded ({quota.max_models} max)"

        elif resource_type == "storage_gb":
            if usage.storage_used_gb + requested_amount > quota.max_storage_gb:
                return False, f"Storage quota exceeded ({quota.max_storage_gb}GB max)"

        elif resource_type == "experiments":
            if (
                usage.experiments_this_month + requested_amount
                > quota.max_experiments_per_month
            ):
                return (
                    False,
                    f"Monthly experiment quota exceeded ({quota.max_experiments_per_month} max)",
                )

        elif resource_type == "concurrent_training":
            if (
                usage.concurrent_training_jobs + requested_amount
                > quota.max_concurrent_training_jobs
            ):
                return (
                    False,
                    f"Concurrent training job quota exceeded ({quota.max_concurrent_training_jobs} max)",
                )

        elif resource_type == "gpu_hours":
            if (
                usage.gpu_hours_this_month + requested_amount
                > quota.max_gpu_hours_per_month
            ):
                return (
                    False,
                    f"Monthly GPU hours quota exceeded ({quota.max_gpu_hours_per_month}h max)",
                )

        elif resource_type == "api_request":
            if (
                usage.api_requests_today + requested_amount
                > quota.max_api_requests_per_day
            ):
                return (
                    False,
                    f"Daily API quota exceeded ({quota.max_api_requests_per_day} max)",
                )
            if (
                usage.api_requests_this_minute + requested_amount
                > quota.max_api_requests_per_minute
            ):
                return (
                    False,
                    f"API rate limit exceeded ({quota.max_api_requests_per_minute}/min max)",
                )

        elif resource_type == "users":
            if usage.num_users + requested_amount > quota.max_users:
                return False, f"User quota exceeded ({quota.max_users} max)"

        else:
            return False, f"Unknown resource type: {resource_type}"

        return True, "OK"

    def consume_quota(self, tenant_id: str, resource_type: str, amount: float = 1.0):
        """
        Consume tenant quota

        Args:
            tenant_id: Tenant ID
            resource_type: Resource type
            amount: Amount to consume
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Check quota first
        has_quota, reason = self.check_quota(tenant_id, resource_type, amount)
        if not has_quota:
            raise ValueError(f"Quota exceeded: {reason}")

        # Consume quota
        usage = tenant.usage

        if resource_type == "models":
            usage.num_models += int(amount)
        elif resource_type == "storage_gb":
            usage.storage_used_gb += amount
        elif resource_type == "experiments":
            usage.experiments_this_month += int(amount)
        elif resource_type == "concurrent_training":
            usage.concurrent_training_jobs += int(amount)
        elif resource_type == "gpu_hours":
            usage.gpu_hours_this_month += amount
        elif resource_type == "cpu_hours":
            usage.cpu_hours_this_month += amount
        elif resource_type == "api_request":
            usage.api_requests_today += int(amount)
            usage.api_requests_this_minute += int(amount)
        elif resource_type == "users":
            usage.num_users += int(amount)

        usage.last_updated = datetime.utcnow()

        self.logger.debug(f"Tenant {tenant_id} consumed {amount} {resource_type}")

    def release_quota(self, tenant_id: str, resource_type: str, amount: float = 1.0):
        """
        Release tenant quota (e.g., when deleting a model)

        Args:
            tenant_id: Tenant ID
            resource_type: Resource type
            amount: Amount to release
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        usage = tenant.usage

        if resource_type == "models":
            usage.num_models = max(0, usage.num_models - int(amount))
        elif resource_type == "storage_gb":
            usage.storage_used_gb = max(0.0, usage.storage_used_gb - amount)
        elif resource_type == "concurrent_training":
            usage.concurrent_training_jobs = max(
                0, usage.concurrent_training_jobs - int(amount)
            )
        elif resource_type == "users":
            usage.num_users = max(0, usage.num_users - int(amount))

        usage.last_updated = datetime.utcnow()

    def get_usage_report(self, tenant_id: str) -> dict[str, Any]:
        """
        Get tenant usage report

        Args:
            tenant_id: Tenant ID

        Returns:
            Usage report with percentages
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        quota = tenant.quota
        usage = tenant.usage

        def pct(used, max_val):
            if max_val == 0:
                return 0.0
            return (used / max_val) * 100

        return {
            "tenant_id": tenant_id,
            "tenant_name": tenant.name,
            "tier": tenant.tier.value,
            "usage": {
                "models": {
                    "used": usage.num_models,
                    "quota": quota.max_models,
                    "percentage": pct(usage.num_models, quota.max_models),
                },
                "storage_gb": {
                    "used": usage.storage_used_gb,
                    "quota": quota.max_storage_gb,
                    "percentage": pct(usage.storage_used_gb, quota.max_storage_gb),
                },
                "experiments_this_month": {
                    "used": usage.experiments_this_month,
                    "quota": quota.max_experiments_per_month,
                    "percentage": pct(
                        usage.experiments_this_month, quota.max_experiments_per_month
                    ),
                },
                "gpu_hours_this_month": {
                    "used": usage.gpu_hours_this_month,
                    "quota": quota.max_gpu_hours_per_month,
                    "percentage": pct(
                        usage.gpu_hours_this_month, quota.max_gpu_hours_per_month
                    ),
                },
                "api_requests_today": {
                    "used": usage.api_requests_today,
                    "quota": quota.max_api_requests_per_day,
                    "percentage": pct(
                        usage.api_requests_today, quota.max_api_requests_per_day
                    ),
                },
                "users": {
                    "used": usage.num_users,
                    "quota": quota.max_users,
                    "percentage": pct(usage.num_users, quota.max_users),
                },
            },
            "last_updated": usage.last_updated.isoformat(),
        }

    def list_tenants(self, active_only: bool = True) -> list[Tenant]:
        """
        List all tenants

        Args:
            active_only: Only return active tenants

        Returns:
            List of tenants
        """
        tenants = list(self.tenants.values())

        if active_only:
            tenants = [t for t in tenants if t.is_active]

        return tenants

    def deactivate_tenant(self, tenant_id: str, reason: str = ""):
        """
        Deactivate a tenant

        Args:
            tenant_id: Tenant ID
            reason: Reason for deactivation
        """
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        tenant.is_active = False
        tenant.updated_at = datetime.utcnow()

        self.logger.warning(f"Deactivated tenant {tenant_id}: {reason}")

    def reactivate_tenant(self, tenant_id: str):
        """Reactivate a tenant"""
        tenant = self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        tenant.is_active = True
        tenant.updated_at = datetime.utcnow()

        self.logger.info(f"Reactivated tenant {tenant_id}")
