"""
Pricing Models

Pricing catalogs and calculators for different cloud resources.
"""

from typing import Dict, Optional
from pydantic import BaseModel, Field
from enum import Enum

from .cost_models import ResourceType


class PricingModel(str, Enum):
    """Pricing models"""
    ON_DEMAND = "on_demand"
    RESERVED = "reserved"
    SPOT = "spot"
    COMMITTED_USE = "committed_use"


class ComputePricing(BaseModel):
    """Pricing for compute resources"""
    resource_type: ResourceType
    price_per_hour: float = Field(..., ge=0, description="USD per hour")
    pricing_model: PricingModel = PricingModel.ON_DEMAND

    # Resource specs (for reference)
    vcpu: Optional[int] = None
    memory_gb: Optional[float] = None
    gpu_memory_gb: Optional[float] = None

    # Discounts
    discount_1_year: Optional[float] = Field(default=None, description="% discount for 1-year commitment")
    discount_3_year: Optional[float] = Field(default=None, description="% discount for 3-year commitment")

    # Region
    region: str = "us-east-1"


class StoragePricing(BaseModel):
    """Pricing for storage"""
    storage_type: ResourceType
    price_per_gb_month: float = Field(..., ge=0, description="USD per GB per month")
    region: str = "us-east-1"

    # Additional costs
    read_price_per_1k: Optional[float] = Field(default=None, description="USD per 1K read requests")
    write_price_per_1k: Optional[float] = Field(default=None, description="USD per 1K write requests")


class NetworkPricing(BaseModel):
    """Pricing for network data transfer"""
    price_per_gb: float = Field(..., ge=0, description="USD per GB")
    direction: str = Field(..., description="egress, ingress, inter-region")
    region: str = "us-east-1"


class PricingCatalog(BaseModel):
    """Complete pricing catalog"""
    # Compute pricing
    compute_pricing: Dict[str, ComputePricing] = Field(default_factory=dict)

    # Storage pricing
    storage_pricing: Dict[str, StoragePricing] = Field(default_factory=dict)

    # Network pricing
    network_pricing: Dict[str, NetworkPricing] = Field(default_factory=dict)

    # Metadata
    effective_date: str
    currency: str = "USD"
    provider: str = Field(default="aws", description="aws, gcp, azure, on-prem")

    @classmethod
    def default_aws_pricing(cls) -> "PricingCatalog":
        """Create default AWS-like pricing catalog"""
        return cls(
            effective_date="2025-01-01",
            currency="USD",
            provider="aws",
            compute_pricing={
                # GPUs (approximate AWS p3/p4 pricing)
                "gpu_t4": ComputePricing(
                    resource_type=ResourceType.GPU_T4,
                    price_per_hour=0.526,
                    vcpu=4,
                    memory_gb=61,
                    gpu_memory_gb=16,
                    discount_1_year=30.0,
                    discount_3_year=50.0
                ),
                "gpu_v100": ComputePricing(
                    resource_type=ResourceType.GPU_V100,
                    price_per_hour=3.06,
                    vcpu=8,
                    memory_gb=61,
                    gpu_memory_gb=16,
                    discount_1_year=30.0,
                    discount_3_year=50.0
                ),
                "gpu_a100": ComputePricing(
                    resource_type=ResourceType.GPU_A100,
                    price_per_hour=5.12,
                    vcpu=16,
                    memory_gb=244,
                    gpu_memory_gb=40,
                    discount_1_year=35.0,
                    discount_3_year=55.0
                ),
                "gpu_h100": ComputePricing(
                    resource_type=ResourceType.GPU_H100,
                    price_per_hour=8.50,
                    vcpu=24,
                    memory_gb=384,
                    gpu_memory_gb=80,
                    discount_1_year=35.0,
                    discount_3_year=55.0
                ),

                # CPUs (approximate AWS t3/m5/c5 pricing)
                "cpu_small": ComputePricing(
                    resource_type=ResourceType.CPU_SMALL,
                    price_per_hour=0.083,
                    vcpu=2,
                    memory_gb=8
                ),
                "cpu_medium": ComputePricing(
                    resource_type=ResourceType.CPU_MEDIUM,
                    price_per_hour=0.166,
                    vcpu=4,
                    memory_gb=16
                ),
                "cpu_large": ComputePricing(
                    resource_type=ResourceType.CPU_LARGE,
                    price_per_hour=0.333,
                    vcpu=8,
                    memory_gb=32
                ),
                "cpu_xlarge": ComputePricing(
                    resource_type=ResourceType.CPU_XLARGE,
                    price_per_hour=0.666,
                    vcpu=16,
                    memory_gb=64
                ),

                # TPUs (approximate GCP pricing)
                "tpu_v3": ComputePricing(
                    resource_type=ResourceType.TPU_V3,
                    price_per_hour=8.00,
                    vcpu=96,
                    memory_gb=335
                ),
                "tpu_v4": ComputePricing(
                    resource_type=ResourceType.TPU_V4,
                    price_per_hour=11.00,
                    vcpu=112,
                    memory_gb=624
                ),
            },
            storage_pricing={
                "storage_ssd": StoragePricing(
                    storage_type=ResourceType.STORAGE_SSD,
                    price_per_gb_month=0.10,
                    read_price_per_1k=0.01,
                    write_price_per_1k=0.01
                ),
                "storage_hdd": StoragePricing(
                    storage_type=ResourceType.STORAGE_HDD,
                    price_per_gb_month=0.045,
                    read_price_per_1k=0.005,
                    write_price_per_1k=0.005
                ),
                "storage_s3": StoragePricing(
                    storage_type=ResourceType.STORAGE_S3,
                    price_per_gb_month=0.023,
                    read_price_per_1k=0.0004,
                    write_price_per_1k=0.005
                ),
            },
            network_pricing={
                "egress": NetworkPricing(
                    price_per_gb=0.09,
                    direction="egress"
                ),
                "ingress": NetworkPricing(
                    price_per_gb=0.00,  # Typically free
                    direction="ingress"
                ),
                "inter_region": NetworkPricing(
                    price_per_gb=0.02,
                    direction="inter-region"
                ),
            }
        )

    @classmethod
    def default_gcp_pricing(cls) -> "PricingCatalog":
        """Create default GCP-like pricing catalog"""
        return cls(
            effective_date="2025-01-01",
            currency="USD",
            provider="gcp",
            compute_pricing={
                # GPUs
                "gpu_t4": ComputePricing(
                    resource_type=ResourceType.GPU_T4,
                    price_per_hour=0.35,
                    gpu_memory_gb=16
                ),
                "gpu_v100": ComputePricing(
                    resource_type=ResourceType.GPU_V100,
                    price_per_hour=2.48,
                    gpu_memory_gb=16
                ),
                "gpu_a100": ComputePricing(
                    resource_type=ResourceType.GPU_A100,
                    price_per_hour=3.67,
                    gpu_memory_gb=40
                ),

                # TPUs
                "tpu_v3": ComputePricing(
                    resource_type=ResourceType.TPU_V3,
                    price_per_hour=8.00
                ),
                "tpu_v4": ComputePricing(
                    resource_type=ResourceType.TPU_V4,
                    price_per_hour=11.00
                ),

                # CPUs
                "cpu_small": ComputePricing(
                    resource_type=ResourceType.CPU_SMALL,
                    price_per_hour=0.076,
                    vcpu=2,
                    memory_gb=8
                ),
                "cpu_medium": ComputePricing(
                    resource_type=ResourceType.CPU_MEDIUM,
                    price_per_hour=0.152,
                    vcpu=4,
                    memory_gb=16
                ),
                "cpu_large": ComputePricing(
                    resource_type=ResourceType.CPU_LARGE,
                    price_per_hour=0.304,
                    vcpu=8,
                    memory_gb=32
                ),
                "cpu_xlarge": ComputePricing(
                    resource_type=ResourceType.CPU_XLARGE,
                    price_per_hour=0.608,
                    vcpu=16,
                    memory_gb=64
                ),
            },
            storage_pricing={
                "storage_ssd": StoragePricing(
                    storage_type=ResourceType.STORAGE_SSD,
                    price_per_gb_month=0.17
                ),
                "storage_hdd": StoragePricing(
                    storage_type=ResourceType.STORAGE_HDD,
                    price_per_gb_month=0.04
                ),
                "storage_s3": StoragePricing(
                    storage_type=ResourceType.STORAGE_S3,
                    price_per_gb_month=0.020
                ),
            },
            network_pricing={
                "egress": NetworkPricing(
                    price_per_gb=0.12,
                    direction="egress"
                ),
                "ingress": NetworkPricing(
                    price_per_gb=0.00,
                    direction="ingress"
                ),
            }
        )

    def get_compute_price(self, resource_type: ResourceType) -> Optional[ComputePricing]:
        """Get pricing for a compute resource"""
        return self.compute_pricing.get(resource_type.value)

    def get_storage_price(self, storage_type: ResourceType) -> Optional[StoragePricing]:
        """Get pricing for storage"""
        return self.storage_pricing.get(storage_type.value)

    def get_network_price(self, direction: str = "egress") -> Optional[NetworkPricing]:
        """Get pricing for network transfer"""
        return self.network_pricing.get(direction)
