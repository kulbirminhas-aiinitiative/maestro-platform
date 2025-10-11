"""
Training Cost Calculator

Calculate costs for ML model training jobs based on resource usage.
"""

from typing import List, Optional, Dict
from datetime import datetime, timedelta
from collections import defaultdict

from ..models.cost_models import (
    ComputeResource,
    ResourceUsage,
    TrainingCost,
    CostEstimate,
    ResourceType
)
from ..models.pricing_models import PricingCatalog


class TrainingCostCalculator:
    """
    Calculate training costs based on resource usage and pricing

    Example:
        >>> calculator = TrainingCostCalculator()
        >>> cost = calculator.calculate_job_cost(
        >>>     job_id="job_123",
        >>>     model_name="bert_classifier",
        >>>     model_version="v1.0",
        >>>     resources=[resource_usage],
        >>>     num_epochs=10,
        >>>     num_samples=100000
        >>> )
        >>> print(f"Total training cost: ${cost.total_cost:.2f}")
    """

    def __init__(self, pricing_catalog: Optional[PricingCatalog] = None):
        """
        Initialize calculator

        Args:
            pricing_catalog: Pricing catalog to use (defaults to AWS pricing)
        """
        self.pricing = pricing_catalog or PricingCatalog.default_aws_pricing()

        # Storage for tracking costs
        self.training_costs: Dict[str, TrainingCost] = {}

    def calculate_job_cost(
        self,
        job_id: str,
        model_name: str,
        model_version: str,
        resources: List[ResourceUsage],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        num_epochs: Optional[int] = None,
        num_samples: Optional[int] = None,
        dataset_name: Optional[str] = None,
        dataset_size_gb: Optional[float] = None,
        storage_gb: float = 0.0,
        network_egress_gb: float = 0.0,
        framework: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> TrainingCost:
        """
        Calculate total cost for a training job

        Args:
            job_id: Training job identifier
            model_name: Model being trained
            model_version: Model version
            resources: List of ResourceUsage records
            start_time: Job start time (inferred from resources if not provided)
            end_time: Job end time (inferred from resources if not provided)
            num_epochs: Number of training epochs
            num_samples: Number of training samples
            dataset_name: Dataset name
            dataset_size_gb: Dataset size in GB
            storage_gb: Storage used in GB
            network_egress_gb: Network data transfer in GB
            framework: ML framework used
            metadata: Additional metadata

        Returns:
            TrainingCost with complete cost breakdown
        """
        if not resources:
            raise ValueError("At least one ResourceUsage record is required")

        # Infer time range from resources
        if start_time is None:
            start_time = min(r.start_time for r in resources)
        if end_time is None:
            end_time = max(r.end_time for r in resources)

        duration_hours = (end_time - start_time).total_seconds() / 3600

        # Calculate compute costs
        compute_cost = self._calculate_compute_cost(resources)

        # Calculate storage costs
        storage_cost = self._calculate_storage_cost(storage_gb, duration_hours)

        # Calculate network costs
        network_cost = self._calculate_network_cost(network_egress_gb)

        # Total cost
        total_cost = compute_cost + storage_cost + network_cost

        # Cost efficiency metrics
        cost_per_epoch = None
        cost_per_sample = None

        if num_epochs and num_epochs > 0:
            cost_per_epoch = total_cost / num_epochs

        if num_samples and num_samples > 0:
            cost_per_sample = total_cost / num_samples

        training_cost = TrainingCost(
            job_id=job_id,
            model_name=model_name,
            model_version=model_version,
            start_time=start_time,
            end_time=end_time,
            duration_hours=duration_hours,
            resources=resources,
            compute_cost=compute_cost,
            storage_cost=storage_cost,
            network_cost=network_cost,
            total_cost=total_cost,
            cost_per_epoch=cost_per_epoch,
            cost_per_sample=cost_per_sample,
            dataset_name=dataset_name,
            dataset_size_gb=dataset_size_gb,
            num_samples=num_samples,
            num_epochs=num_epochs,
            framework=framework,
            metadata=metadata or {}
        )

        # Store for future reference
        self.training_costs[job_id] = training_cost

        return training_cost

    def create_resource_usage(
        self,
        resource_type: ResourceType,
        start_time: datetime,
        end_time: datetime,
        quantity: int = 1,
        job_id: Optional[str] = None,
        model_name: Optional[str] = None,
        model_version: Optional[str] = None,
        avg_gpu_utilization: Optional[float] = None,
        avg_memory_utilization: Optional[float] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> ResourceUsage:
        """
        Create a ResourceUsage record

        Args:
            resource_type: Type of resource
            start_time: When resource usage started
            end_time: When resource usage ended
            quantity: Number of resources
            job_id: Associated job ID
            model_name: Associated model
            model_version: Associated model version
            avg_gpu_utilization: Average GPU utilization %
            avg_memory_utilization: Average memory utilization %
            tags: Additional tags

        Returns:
            ResourceUsage record
        """
        duration = end_time - start_time
        duration_seconds = duration.total_seconds()
        duration_hours = duration_seconds / 3600

        # Create resource spec
        pricing_info = self.pricing.get_compute_price(resource_type)
        resource = ComputeResource(
            resource_type=resource_type,
            quantity=quantity,
            vcpu=pricing_info.vcpu if pricing_info else None,
            memory_gb=pricing_info.memory_gb if pricing_info else None,
            gpu_memory_gb=pricing_info.gpu_memory_gb if pricing_info else None
        )

        return ResourceUsage(
            resource=resource,
            start_time=start_time,
            end_time=end_time,
            duration_seconds=duration_seconds,
            duration_hours=duration_hours,
            avg_gpu_utilization=avg_gpu_utilization,
            avg_memory_utilization=avg_memory_utilization,
            job_id=job_id,
            model_name=model_name,
            model_version=model_version,
            tags=tags or {}
        )

    def estimate_training_cost(
        self,
        resource_type: ResourceType,
        estimated_hours: float,
        quantity: int = 1,
        num_epochs: Optional[int] = None,
        num_samples: Optional[int] = None,
        storage_gb: float = 0.0,
        network_egress_gb: float = 0.0,
        similar_jobs: Optional[List[TrainingCost]] = None
    ) -> CostEstimate:
        """
        Estimate cost for a planned training job

        Args:
            resource_type: Type of compute resource
            estimated_hours: Estimated training duration
            quantity: Number of resources
            num_epochs: Number of epochs
            num_samples: Number of samples
            storage_gb: Storage needed
            network_egress_gb: Network transfer
            similar_jobs: Historical similar jobs for comparison

        Returns:
            CostEstimate with projected costs
        """
        # Get pricing
        compute_pricing = self.pricing.get_compute_price(resource_type)
        if not compute_pricing:
            raise ValueError(f"No pricing found for {resource_type}")

        # Calculate estimated costs
        estimated_compute_cost = compute_pricing.price_per_hour * estimated_hours * quantity
        estimated_storage_cost = self._calculate_storage_cost(storage_gb, estimated_hours)
        estimated_network_cost = self._calculate_network_cost(network_egress_gb)
        estimated_total_cost = estimated_compute_cost + estimated_storage_cost + estimated_network_cost

        # Build resource spec
        resource = ComputeResource(
            resource_type=resource_type,
            quantity=quantity,
            vcpu=compute_pricing.vcpu,
            memory_gb=compute_pricing.memory_gb,
            gpu_memory_gb=compute_pricing.gpu_memory_gb
        )

        # Determine confidence level
        confidence = "medium"
        if similar_jobs and len(similar_jobs) >= 5:
            confidence = "high"
        elif not similar_jobs or len(similar_jobs) == 0:
            confidence = "low"

        # Historical comparison
        avg_historical_cost = None
        if similar_jobs:
            avg_historical_cost = sum(j.total_cost for j in similar_jobs) / len(similar_jobs)

        # Build assumptions
        assumptions = [
            f"Using {resource_type.value} at ${compute_pricing.price_per_hour:.3f}/hour",
            f"Estimated duration: {estimated_hours:.1f} hours",
            f"Quantity: {quantity} resource(s)"
        ]

        if num_epochs:
            assumptions.append(f"Training for {num_epochs} epochs")
        if num_samples:
            assumptions.append(f"Dataset size: {num_samples:,} samples")

        return CostEstimate(
            operation="training",
            estimated_resources=[resource],
            estimated_duration_hours=estimated_hours,
            estimated_compute_cost=estimated_compute_cost,
            estimated_storage_cost=estimated_storage_cost,
            estimated_network_cost=estimated_network_cost,
            estimated_total_cost=estimated_total_cost,
            confidence_level=confidence,
            assumptions=assumptions,
            historical_similar_jobs=len(similar_jobs) if similar_jobs else None,
            avg_historical_cost=avg_historical_cost
        )

    def _calculate_compute_cost(self, resources: List[ResourceUsage]) -> float:
        """Calculate total compute cost from resource usage"""
        total_cost = 0.0

        for usage in resources:
            pricing = self.pricing.get_compute_price(usage.resource.resource_type)
            if not pricing:
                continue

            # Base cost
            resource_cost = pricing.price_per_hour * usage.duration_hours * usage.resource.quantity

            # Apply utilization factor (if low utilization, flag it but still charge)
            # This is for informational purposes - actual billing is based on reserved time
            if usage.avg_gpu_utilization is not None and usage.avg_gpu_utilization < 50:
                # Could add warning here about low utilization
                pass

            total_cost += resource_cost

        return total_cost

    def _calculate_storage_cost(self, storage_gb: float, duration_hours: float) -> float:
        """Calculate storage cost"""
        if storage_gb <= 0:
            return 0.0

        # Use S3-like storage pricing
        storage_pricing = self.pricing.get_storage_price(ResourceType.STORAGE_S3)
        if not storage_pricing:
            return 0.0

        # Convert hourly to monthly, then calculate
        duration_months = duration_hours / (24 * 30)
        return storage_pricing.price_per_gb_month * storage_gb * duration_months

    def _calculate_network_cost(self, egress_gb: float) -> float:
        """Calculate network transfer cost"""
        if egress_gb <= 0:
            return 0.0

        network_pricing = self.pricing.get_network_price("egress")
        if not network_pricing:
            return 0.0

        return network_pricing.price_per_gb * egress_gb

    def get_job_cost(self, job_id: str) -> Optional[TrainingCost]:
        """Retrieve stored cost for a job"""
        return self.training_costs.get(job_id)

    def get_model_training_costs(
        self,
        model_name: str,
        model_version: Optional[str] = None
    ) -> List[TrainingCost]:
        """Get all training costs for a model"""
        costs = []
        for cost in self.training_costs.values():
            if cost.model_name == model_name:
                if model_version is None or cost.model_version == model_version:
                    costs.append(cost)
        return costs

    def get_total_training_cost(
        self,
        model_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> float:
        """
        Calculate total training costs

        Args:
            model_name: Filter by model (None = all models)
            start_time: Filter by start time
            end_time: Filter by end time

        Returns:
            Total cost in USD
        """
        total = 0.0

        for cost in self.training_costs.values():
            # Filter by model
            if model_name and cost.model_name != model_name:
                continue

            # Filter by time range
            if start_time and cost.end_time < start_time:
                continue
            if end_time and cost.start_time > end_time:
                continue

            total += cost.total_cost

        return total
