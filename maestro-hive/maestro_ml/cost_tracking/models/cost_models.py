"""
Cost Tracking Data Models

Models for tracking training costs, inference costs, and resource usage.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum


class ResourceType(str, Enum):
    """Types of compute resources"""
    # GPUs
    GPU_T4 = "gpu_t4"
    GPU_V100 = "gpu_v100"
    GPU_A100 = "gpu_a100"
    GPU_H100 = "gpu_h100"

    # CPUs
    CPU_SMALL = "cpu_small"    # 2 vCPU, 8GB RAM
    CPU_MEDIUM = "cpu_medium"  # 4 vCPU, 16GB RAM
    CPU_LARGE = "cpu_large"    # 8 vCPU, 32GB RAM
    CPU_XLARGE = "cpu_xlarge"  # 16 vCPU, 64GB RAM

    # TPUs
    TPU_V3 = "tpu_v3"
    TPU_V4 = "tpu_v4"

    # Storage
    STORAGE_SSD = "storage_ssd"
    STORAGE_HDD = "storage_hdd"
    STORAGE_S3 = "storage_s3"

    # Network
    NETWORK_EGRESS = "network_egress"
    NETWORK_INGRESS = "network_ingress"


class ComputeResource(BaseModel):
    """Specification of a compute resource"""
    resource_type: ResourceType
    quantity: int = Field(default=1, description="Number of resources (e.g., # of GPUs)")

    # Specs
    vcpu: Optional[int] = None
    memory_gb: Optional[float] = None
    gpu_memory_gb: Optional[float] = None

    # Location
    region: str = Field(default="us-east-1")
    zone: Optional[str] = None


class ResourceUsage(BaseModel):
    """Resource usage record"""
    resource: ComputeResource
    start_time: datetime
    end_time: datetime

    # Usage metrics
    duration_seconds: float
    duration_hours: float

    # GPU utilization (if applicable)
    avg_gpu_utilization: Optional[float] = Field(default=None, ge=0, le=100)
    avg_memory_utilization: Optional[float] = Field(default=None, ge=0, le=100)

    # Associated entity
    job_id: Optional[str] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None

    # Metadata
    tags: Dict[str, str] = Field(default_factory=dict)


class TrainingCost(BaseModel):
    """Cost breakdown for a training job"""
    job_id: str
    model_name: str
    model_version: str

    # Time
    start_time: datetime
    end_time: datetime
    duration_hours: float

    # Resources used
    resources: List[ResourceUsage] = Field(default_factory=list)

    # Cost breakdown
    compute_cost: float = Field(..., ge=0, description="Cost of compute resources")
    storage_cost: float = Field(default=0.0, ge=0, description="Storage costs")
    network_cost: float = Field(default=0.0, ge=0, description="Data transfer costs")
    total_cost: float = Field(..., ge=0, description="Total cost")

    # Cost efficiency metrics
    cost_per_epoch: Optional[float] = None
    cost_per_sample: Optional[float] = None

    # Dataset info
    dataset_name: Optional[str] = None
    dataset_size_gb: Optional[float] = None
    num_samples: Optional[int] = None
    num_epochs: Optional[int] = None

    # Additional metadata
    framework: Optional[str] = None  # tensorflow, pytorch, etc.
    metadata: Dict[str, Any] = Field(default_factory=dict)


class InferenceCost(BaseModel):
    """Cost tracking for model inference"""
    model_name: str
    model_version: str

    # Time period
    start_time: datetime
    end_time: datetime
    duration_hours: float

    # Inference metrics
    total_requests: int = Field(..., ge=0)
    successful_requests: int = Field(..., ge=0)
    failed_requests: int = Field(default=0, ge=0)

    # Resource usage
    resources: List[ResourceUsage] = Field(default_factory=list)

    # Cost breakdown
    compute_cost: float = Field(..., ge=0)
    storage_cost: float = Field(default=0.0, ge=0)
    network_cost: float = Field(default=0.0, ge=0)
    total_cost: float = Field(..., ge=0)

    # Cost efficiency metrics
    cost_per_request: float = Field(..., ge=0)
    cost_per_1k_requests: float = Field(..., ge=0)

    # Performance metrics
    avg_latency_ms: Optional[float] = None
    p95_latency_ms: Optional[float] = None

    # Deployment info
    deployment_id: Optional[str] = None
    endpoint: Optional[str] = None


class CostBreakdown(BaseModel):
    """Detailed cost breakdown"""
    # By resource type
    compute_cost: float = 0.0
    storage_cost: float = 0.0
    network_cost: float = 0.0

    # By operation
    training_cost: float = 0.0
    inference_cost: float = 0.0
    data_processing_cost: float = 0.0

    # By time period
    daily_cost: float = 0.0
    weekly_cost: float = 0.0
    monthly_cost: float = 0.0

    # Total
    total_cost: float = 0.0


class CostSummary(BaseModel):
    """Cost summary for a model or project"""
    model_name: Optional[str] = None
    project_name: Optional[str] = None

    # Time range
    start_time: datetime
    end_time: datetime
    duration_days: float

    # Cost breakdown
    breakdown: CostBreakdown

    # Training costs
    total_training_jobs: int = 0
    total_training_hours: float = 0.0
    total_training_cost: float = 0.0

    # Inference costs
    total_inference_requests: int = 0
    total_inference_hours: float = 0.0
    total_inference_cost: float = 0.0

    # Efficiency metrics
    avg_cost_per_day: float = 0.0
    avg_cost_per_training_job: Optional[float] = None
    avg_cost_per_1k_requests: Optional[float] = None

    # Budget tracking
    budget_allocated: Optional[float] = None
    budget_used: Optional[float] = None
    budget_remaining: Optional[float] = None
    budget_utilization_pct: Optional[float] = None

    # Trend
    cost_trend: Optional[str] = Field(default=None, description="increasing, stable, decreasing")


class BudgetAlert(BaseModel):
    """Alert for budget threshold crossings"""
    alert_id: str
    model_name: Optional[str] = None
    project_name: Optional[str] = None

    # Budget info
    budget_allocated: float
    budget_used: float
    budget_remaining: float
    utilization_pct: float

    # Alert properties
    threshold_pct: float = Field(..., description="Threshold that was crossed (e.g., 80, 90, 100)")
    severity: str = Field(..., description="warning, critical")

    message: str
    triggered_at: datetime = Field(default_factory=datetime.utcnow)

    # Time period
    period_start: datetime
    period_end: datetime


class CostEstimate(BaseModel):
    """Estimated cost for a planned operation"""
    operation: str = Field(..., description="training, inference, data_processing")

    # Estimated resources
    estimated_resources: List[ComputeResource] = Field(default_factory=list)
    estimated_duration_hours: float

    # Cost estimates
    estimated_compute_cost: float
    estimated_storage_cost: float = 0.0
    estimated_network_cost: float = 0.0
    estimated_total_cost: float

    # Confidence
    confidence_level: str = Field(default="medium", description="low, medium, high")

    # Assumptions
    assumptions: List[str] = Field(default_factory=list)

    # Comparison
    historical_similar_jobs: Optional[int] = None
    avg_historical_cost: Optional[float] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
