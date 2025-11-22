"""
Service Registry for Quality Fabric
Manages service registration, discovery, and health monitoring
"""

import asyncio
import logging
import os
import toml
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
from enum import Enum
import uuid

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    """Service status enumeration"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    STOPPING = "stopping"
    DEREGISTERED = "deregistered"


class ServiceInstance:
    """Represents a registered service instance"""

    def __init__(
        self,
        service_name: str,
        service_id: str,
        host: str,
        port: int,
        path: str,
        status: ServiceStatus = ServiceStatus.STARTING,
        capabilities: List[str] = None,
        metadata: Dict = None
    ):
        self.service_name = service_name
        self.service_id = service_id
        self.host = host
        self.port = port
        self.path = path
        self.endpoint = f"http://{host}:{port}"
        self.status = status
        self.capabilities = capabilities or []
        self.metadata = metadata or {}
        self.last_heartbeat = datetime.utcnow()
        self.registration_time = datetime.utcnow()


class ServiceRegistry:
    """
    Service registry manages the lifecycle of all Quality Fabric services
    """

    def __init__(self, config_path: Optional[Path] = None, heartbeat_timeout: int = 90):
        self.services: Dict[str, ServiceInstance] = {}
        self.service_registrations: Dict[str, str] = {}  # service_id -> registration_id
        self.heartbeat_timeout = heartbeat_timeout
        self._lock = asyncio.Lock()
        self.config = self._load_config(config_path)

    def _load_config(self, config_path: Optional[Path] = None) -> Dict:
        """Load service configuration from pyproject.toml"""
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "pyproject.toml"

        try:
            config_data = toml.load(config_path)
            return config_data.get("tool", {}).get("quality_fabric", {})
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}")
            return {}

    def get_service_config(self, service_name: str) -> Optional[Dict]:
        """Get configuration for a specific service"""
        services = self.config.get("services", {})
        return services.get(service_name)

    async def register_service(
        self,
        service_name: str,
        host: Optional[str] = None,
        port: Optional[int] = None,
        path: Optional[str] = None,
        capabilities: List[str] = None,
        metadata: Dict = None
    ) -> Dict[str, any]:
        """Register a new service"""
        async with self._lock:
            # Get config if not provided
            service_config = self.get_service_config(service_name) or {}
            host = host or service_config.get("host", "0.0.0.0")
            port = port or service_config.get("port", 8000)
            path = path or service_config.get("path", os.getenv('QUALITY_FABRIC_ROOT', os.getcwd()))

            # Generate unique service ID
            service_id = f"{service_name}-{uuid.uuid4().hex[:8]}"
            registration_id = f"reg-{uuid.uuid4().hex[:8]}"

            # Create service instance
            service_instance = ServiceInstance(
                service_name=service_name,
                service_id=service_id,
                host=host,
                port=port,
                path=path,
                status=ServiceStatus.HEALTHY,
                capabilities=capabilities or [],
                metadata=metadata or {}
            )

            # Store service
            self.services[service_id] = service_instance
            self.service_registrations[service_id] = registration_id

            logger.info(
                f"Service registered: {service_name} (ID: {service_id}) "
                f"at {service_instance.endpoint}"
            )

            return {
                "service_id": service_id,
                "registration_id": registration_id,
                "status": "registered",
                "endpoint": service_instance.endpoint,
                "heartbeat_interval": 30,
                "next_heartbeat": (datetime.utcnow() + timedelta(seconds=30)).isoformat()
            }

    async def process_heartbeat(
        self,
        service_id: str,
        status: Optional[ServiceStatus] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, any]:
        """Process service heartbeat"""
        async with self._lock:
            if service_id not in self.services:
                raise ValueError(f"Service {service_id} not registered")

            service = self.services[service_id]
            service.last_heartbeat = datetime.utcnow()

            if status:
                service.status = status

            if metadata:
                service.metadata.update(metadata)

            logger.debug(f"Heartbeat processed for {service_id}, status: {service.status}")

            return {
                "status": "acknowledged",
                "next_heartbeat": (datetime.utcnow() + timedelta(seconds=30)).isoformat()
            }

    async def deregister_service(self, service_id: str) -> None:
        """Deregister a service"""
        async with self._lock:
            if service_id not in self.services:
                raise ValueError(f"Service {service_id} not registered")

            service = self.services[service_id]
            service.status = ServiceStatus.DEREGISTERED

            # Remove from active services
            del self.services[service_id]
            if service_id in self.service_registrations:
                del self.service_registrations[service_id]

            logger.info(f"Service deregistered: {service.service_name} ({service_id})")

    async def list_services(
        self,
        status: Optional[str] = None,
        capability: Optional[str] = None
    ) -> List[Dict[str, any]]:
        """List services with optional filtering"""
        async with self._lock:
            services = []

            for service in self.services.values():
                # Apply status filter
                if status and service.status.value != status:
                    continue

                # Apply capability filter
                if capability and capability not in service.capabilities:
                    continue

                services.append({
                    "service_name": service.service_name,
                    "service_id": service.service_id,
                    "status": service.status.value,
                    "endpoint": service.endpoint,
                    "host": service.host,
                    "port": service.port,
                    "path": service.path,
                    "capabilities": service.capabilities,
                    "last_heartbeat": service.last_heartbeat.isoformat(),
                    "registration_time": service.registration_time.isoformat(),
                    "metadata": service.metadata
                })

            return services

    async def get_service_instances(self, service_name: str) -> List[Dict[str, any]]:
        """Get all instances of a specific service"""
        async with self._lock:
            instances = []

            for service in self.services.values():
                if service.service_name == service_name:
                    instances.append({
                        "service_id": service.service_id,
                        "status": service.status.value,
                        "endpoint": service.endpoint,
                        "host": service.host,
                        "port": service.port,
                        "path": service.path,
                        "capabilities": service.capabilities,
                        "last_heartbeat": service.last_heartbeat.isoformat(),
                        "metadata": service.metadata
                    })

            return instances

    async def get_healthy_service(self, service_name: str) -> Optional[ServiceInstance]:
        """Get a healthy instance of a service"""
        async with self._lock:
            healthy_services = [
                service for service in self.services.values()
                if service.service_name == service_name
                and service.status == ServiceStatus.HEALTHY
            ]

            if not healthy_services:
                return None

            # Return first healthy service
            return healthy_services[0]

    async def get_service_by_capability(self, capability: str) -> List[ServiceInstance]:
        """Get services that have a specific capability"""
        async with self._lock:
            matching_services = [
                service for service in self.services.values()
                if capability in service.capabilities
                and service.status == ServiceStatus.HEALTHY
            ]

            return matching_services

    async def check_service_health(self) -> Dict[str, any]:
        """Check service health based on heartbeat timeouts"""
        async with self._lock:
            current_time = datetime.utcnow()
            timeout_threshold = current_time - timedelta(seconds=self.heartbeat_timeout)

            unhealthy_services = []
            healthy_count = 0
            total_count = len(self.services)

            for service_id, service in self.services.items():
                if service.last_heartbeat < timeout_threshold:
                    if service.status != ServiceStatus.UNHEALTHY:
                        service.status = ServiceStatus.UNHEALTHY
                        unhealthy_services.append(service_id)
                        logger.warning(
                            f"Service marked unhealthy: {service.service_name} ({service_id}) "
                            f"- Last heartbeat: {service.last_heartbeat.isoformat()}"
                        )
                else:
                    if service.status == ServiceStatus.UNHEALTHY:
                        service.status = ServiceStatus.HEALTHY
                        logger.info(
                            f"Service recovered: {service.service_name} ({service_id})"
                        )

                if service.status == ServiceStatus.HEALTHY:
                    healthy_count += 1

            return {
                "total_services": total_count,
                "healthy_services": healthy_count,
                "unhealthy_services": total_count - healthy_count,
                "newly_unhealthy": unhealthy_services,
                "timestamp": current_time.isoformat()
            }

    async def get_registry_metrics(self) -> Dict[str, any]:
        """Get registry metrics"""
        async with self._lock:
            status_counts = {}
            capability_counts = {}

            for service in self.services.values():
                # Count by status
                status = service.status.value
                status_counts[status] = status_counts.get(status, 0) + 1

                # Count by capabilities
                for capability in service.capabilities:
                    capability_counts[capability] = capability_counts.get(capability, 0) + 1

            return {
                "total_services": len(self.services),
                "status_distribution": status_counts,
                "capability_distribution": capability_counts,
                "registration_count": len(self.service_registrations),
                "heartbeat_timeout_seconds": self.heartbeat_timeout
            }


# Global service registry instance
_registry_instance: Optional[ServiceRegistry] = None


def get_service_registry() -> ServiceRegistry:
    """Get or create the global service registry instance"""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = ServiceRegistry()
    return _registry_instance