"""
Inference Cost Tracker

Track costs for model inference/serving operations.
"""

from typing import List, Optional, Dict
from datetime import datetime, timedelta
from collections import defaultdict

from ..models.cost_models import (
    ComputeResource,
    ResourceUsage,
    InferenceCost,
    ResourceType
)
from ..models.pricing_models import PricingCatalog


class InferenceCostTracker:
    """
    Track inference costs for deployed models

    Example:
        >>> tracker = InferenceCostTracker()
        >>> tracker.record_requests(
        >>>     model_name="fraud_detector",
        >>>     model_version="v2.1",
        >>>     num_requests=1000,
        >>>     timestamp=datetime.utcnow()
        >>> )
        >>> cost = tracker.calculate_period_cost(
        >>>     model_name="fraud_detector",
        >>>     model_version="v2.1",
        >>>     start_time=datetime.utcnow() - timedelta(hours=24),
        >>>     end_time=datetime.utcnow()
        >>> )
    """

    def __init__(self, pricing_catalog: Optional[PricingCatalog] = None):
        """
        Initialize tracker

        Args:
            pricing_catalog: Pricing catalog (defaults to AWS)
        """
        self.pricing = pricing_catalog or PricingCatalog.default_aws_pricing()

        # Track request counts: {model_name: {model_version: [(timestamp, count)]}}
        self.request_history: Dict[str, Dict[str, List[tuple]]] = defaultdict(lambda: defaultdict(list))

        # Track resource usage for deployments
        self.deployment_resources: Dict[str, ResourceUsage] = {}

        # Store calculated costs
        self.inference_costs: Dict[str, InferenceCost] = {}

    def record_requests(
        self,
        model_name: str,
        model_version: str,
        num_requests: int,
        successful: Optional[int] = None,
        failed: Optional[int] = None,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Record inference requests for a model

        Args:
            model_name: Model identifier
            model_version: Model version
            num_requests: Total number of requests
            successful: Number of successful requests
            failed: Number of failed requests
            timestamp: When requests occurred
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        if successful is None:
            successful = num_requests - (failed or 0)

        self.request_history[model_name][model_version].append({
            "timestamp": timestamp,
            "total": num_requests,
            "successful": successful,
            "failed": failed or 0
        })

    def start_deployment(
        self,
        deployment_id: str,
        model_name: str,
        model_version: str,
        resource_type: ResourceType,
        quantity: int = 1,
        start_time: Optional[datetime] = None
    ) -> None:
        """
        Start tracking a model deployment

        Args:
            deployment_id: Deployment identifier
            model_name: Model being deployed
            model_version: Model version
            resource_type: Type of compute resource
            quantity: Number of resources (e.g., # of instances)
            start_time: Deployment start time
        """
        if start_time is None:
            start_time = datetime.utcnow()

        # Get pricing info for resource specs
        pricing_info = self.pricing.get_compute_price(resource_type)
        resource = ComputeResource(
            resource_type=resource_type,
            quantity=quantity,
            vcpu=pricing_info.vcpu if pricing_info else None,
            memory_gb=pricing_info.memory_gb if pricing_info else None,
            gpu_memory_gb=pricing_info.gpu_memory_gb if pricing_info else None
        )

        # Create placeholder ResourceUsage (end_time will be set when deployment stops)
        usage = ResourceUsage(
            resource=resource,
            start_time=start_time,
            end_time=start_time,  # Placeholder, will be updated
            duration_seconds=0.0,
            duration_hours=0.0,
            job_id=deployment_id,
            model_name=model_name,
            model_version=model_version
        )

        self.deployment_resources[deployment_id] = usage

    def stop_deployment(
        self,
        deployment_id: str,
        end_time: Optional[datetime] = None
    ) -> Optional[ResourceUsage]:
        """
        Stop tracking a deployment

        Args:
            deployment_id: Deployment identifier
            end_time: When deployment stopped

        Returns:
            Updated ResourceUsage or None if deployment not found
        """
        if deployment_id not in self.deployment_resources:
            return None

        if end_time is None:
            end_time = datetime.utcnow()

        usage = self.deployment_resources[deployment_id]
        duration = end_time - usage.start_time
        usage.end_time = end_time
        usage.duration_seconds = duration.total_seconds()
        usage.duration_hours = usage.duration_seconds / 3600

        return usage

    def calculate_period_cost(
        self,
        model_name: str,
        model_version: str,
        start_time: datetime,
        end_time: datetime,
        resource_usage: Optional[List[ResourceUsage]] = None,
        deployment_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        avg_latency_ms: Optional[float] = None,
        p95_latency_ms: Optional[float] = None,
        storage_gb: float = 0.0,
        network_egress_gb: float = 0.0
    ) -> InferenceCost:
        """
        Calculate inference cost for a time period

        Args:
            model_name: Model identifier
            model_version: Model version
            start_time: Period start
            end_time: Period end
            resource_usage: List of ResourceUsage (if None, looks up from deployments)
            deployment_id: Deployment ID
            endpoint: API endpoint
            avg_latency_ms: Average latency
            p95_latency_ms: P95 latency
            storage_gb: Storage used
            network_egress_gb: Network transfer

        Returns:
            InferenceCost with complete breakdown
        """
        duration_hours = (end_time - start_time).total_seconds() / 3600

        # Get request counts for period
        total_requests = 0
        successful_requests = 0
        failed_requests = 0

        if model_name in self.request_history and model_version in self.request_history[model_name]:
            for record in self.request_history[model_name][model_version]:
                if start_time <= record["timestamp"] <= end_time:
                    total_requests += record["total"]
                    successful_requests += record["successful"]
                    failed_requests += record["failed"]

        # Get resource usage
        if resource_usage is None:
            resource_usage = []
            # Look up deployment resources if deployment_id provided
            if deployment_id and deployment_id in self.deployment_resources:
                resource_usage = [self.deployment_resources[deployment_id]]

        # Calculate costs
        compute_cost = self._calculate_compute_cost(resource_usage)
        storage_cost = self._calculate_storage_cost(storage_gb, duration_hours)
        network_cost = self._calculate_network_cost(network_egress_gb)
        total_cost = compute_cost + storage_cost + network_cost

        # Cost efficiency metrics
        cost_per_request = total_cost / total_requests if total_requests > 0 else 0.0
        cost_per_1k_requests = cost_per_request * 1000

        cost_id = f"{model_name}_{model_version}_{start_time.strftime('%Y%m%d%H%M%S')}"

        inference_cost = InferenceCost(
            model_name=model_name,
            model_version=model_version,
            start_time=start_time,
            end_time=end_time,
            duration_hours=duration_hours,
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            resources=resource_usage,
            compute_cost=compute_cost,
            storage_cost=storage_cost,
            network_cost=network_cost,
            total_cost=total_cost,
            cost_per_request=cost_per_request,
            cost_per_1k_requests=cost_per_1k_requests,
            deployment_id=deployment_id,
            endpoint=endpoint,
            avg_latency_ms=avg_latency_ms,
            p95_latency_ms=p95_latency_ms
        )

        self.inference_costs[cost_id] = inference_cost
        return inference_cost

    def _calculate_compute_cost(self, resources: List[ResourceUsage]) -> float:
        """Calculate compute cost from resource usage"""
        total_cost = 0.0

        for usage in resources:
            pricing = self.pricing.get_compute_price(usage.resource.resource_type)
            if not pricing:
                continue

            resource_cost = pricing.price_per_hour * usage.duration_hours * usage.resource.quantity
            total_cost += resource_cost

        return total_cost

    def _calculate_storage_cost(self, storage_gb: float, duration_hours: float) -> float:
        """Calculate storage cost"""
        if storage_gb <= 0:
            return 0.0

        storage_pricing = self.pricing.get_storage_price(ResourceType.STORAGE_S3)
        if not storage_pricing:
            return 0.0

        duration_months = duration_hours / (24 * 30)
        return storage_pricing.price_per_gb_month * storage_gb * duration_months

    def _calculate_network_cost(self, egress_gb: float) -> float:
        """Calculate network cost"""
        if egress_gb <= 0:
            return 0.0

        network_pricing = self.pricing.get_network_price("egress")
        if not network_pricing:
            return 0.0

        return network_pricing.price_per_gb * egress_gb

    def get_model_inference_costs(
        self,
        model_name: str,
        model_version: Optional[str] = None
    ) -> List[InferenceCost]:
        """Get all inference costs for a model"""
        costs = []
        for cost in self.inference_costs.values():
            if cost.model_name == model_name:
                if model_version is None or cost.model_version == model_version:
                    costs.append(cost)
        return costs

    def get_total_inference_cost(
        self,
        model_name: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> float:
        """Calculate total inference costs"""
        total = 0.0

        for cost in self.inference_costs.values():
            if model_name and cost.model_name != model_name:
                continue

            if start_time and cost.end_time < start_time:
                continue
            if end_time and cost.start_time > end_time:
                continue

            total += cost.total_cost

        return total

    def get_total_requests(
        self,
        model_name: str,
        model_version: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, int]:
        """Get total request counts for a model"""
        total = 0
        successful = 0
        failed = 0

        versions = [model_version] if model_version else list(self.request_history.get(model_name, {}).keys())

        for version in versions:
            if model_name not in self.request_history or version not in self.request_history[model_name]:
                continue

            for record in self.request_history[model_name][version]:
                # Filter by time if provided
                if start_time and record["timestamp"] < start_time:
                    continue
                if end_time and record["timestamp"] > end_time:
                    continue

                total += record["total"]
                successful += record["successful"]
                failed += record["failed"]

        return {
            "total": total,
            "successful": successful,
            "failed": failed
        }
