"""
UTCP Service Registry - Central discovery hub for UTCP-enabled services.

This module provides service discovery and tool calling capabilities across
a distributed microservices architecture using the Universal Tool Calling Protocol.
"""

import asyncio
from typing import Any, Dict, List, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field

import httpx
from utcp.utcp_client import UtcpClient

from maestro_core_logging import get_logger

logger = get_logger(__name__)


@dataclass
class ServiceInfo:
    """Information about a registered UTCP service."""

    name: str
    base_url: str
    manual_url: str
    manual: Optional[Dict[str, Any]] = None
    last_health_check: Optional[datetime] = None
    is_healthy: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: Set[str] = field(default_factory=set)


class UTCPServiceRegistry:
    """
    Central registry for UTCP-enabled microservices.

    Features:
    - Automatic service discovery from URLs
    - Health monitoring
    - Tool catalog aggregation
    - Dynamic UTCP client management
    - Tag-based service filtering

    Example:
        >>> registry = UTCPServiceRegistry()
        >>> await registry.discover_services([
        ...     "http://workflow-engine:8001",
        ...     "http://intelligence-service:8002"
        ... ])
        >>> tools = registry.list_available_tools()
        >>> result = await registry.call_tool("workflow_engine.execute", {"req": "..."})
    """

    def __init__(
        self,
        health_check_interval: int = 60,
        request_timeout: int = 30,
        auto_health_check: bool = True
    ):
        """
        Initialize service registry.

        Args:
            health_check_interval: Seconds between health checks
            request_timeout: HTTP request timeout in seconds
            auto_health_check: Enable automatic health monitoring
        """
        self.services: Dict[str, ServiceInfo] = {}
        self.utcp_client: Optional[UtcpClient] = None
        self.health_check_interval = health_check_interval
        self.request_timeout = request_timeout
        self.auto_health_check = auto_health_check
        self._health_check_task: Optional[asyncio.Task] = None

        # Connection pooling for better performance (QUICK WIN #1)
        self.http_client = httpx.AsyncClient(
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20
            ),
            timeout=httpx.Timeout(self.request_timeout, connect=5.0),
            http2=True  # Enable HTTP/2 for multiplexing
        )

        logger.info("UTCP Service Registry initialized with connection pooling")

    async def register_service(
        self,
        name: str,
        base_url: str,
        manual_url: Optional[str] = None,
        tags: Optional[Set[str]] = None
    ) -> ServiceInfo:
        """
        Register a service with the registry.

        Args:
            name: Service name (unique identifier)
            base_url: Base URL of the service
            manual_url: URL to UTCP manual (defaults to {base_url}/utcp-manual.json)
            tags: Optional tags for service categorization

        Returns:
            ServiceInfo object for registered service

        Raises:
            ValueError: If service cannot be registered
        """
        if manual_url is None:
            manual_url = f"{base_url.rstrip('/')}/utcp-manual.json"

        logger.info("Registering service", name=name, base_url=base_url)

        # Fetch the manual
        try:
            manual = await self._fetch_manual(manual_url)

            service_info = ServiceInfo(
                name=name,
                base_url=base_url.rstrip('/'),
                manual_url=manual_url,
                manual=manual,
                last_health_check=datetime.utcnow(),
                is_healthy=True,
                metadata=manual.get("metadata", {}),
                tags=tags or set()
            )

            self.services[name] = service_info

            # Refresh UTCP client with new service
            await self._refresh_client()

            logger.info(
                "Service registered successfully",
                name=name,
                tool_count=len(manual.get("tools", []))
            )

            return service_info

        except Exception as e:
            logger.error("Failed to register service", name=name, error=str(e))
            raise ValueError(f"Cannot register service '{name}': {e}")

    async def discover_services(
        self,
        service_urls: List[str],
        fail_on_error: bool = False
    ) -> List[ServiceInfo]:
        """
        Auto-discover services from URLs.

        Attempts to fetch UTCP manual from each URL and register the service.

        Args:
            service_urls: List of base URLs to discover
            fail_on_error: Raise exception if any discovery fails

        Returns:
            List of successfully registered services
        """
        logger.info("Starting service discovery", url_count=len(service_urls))

        discovered = []
        errors = []

        for url in service_urls:
            try:
                manual_url = f"{url.rstrip('/')}/utcp-manual.json"
                manual = await self._fetch_manual(manual_url)

                service_name = manual.get("metadata", {}).get("name", url.split("://")[-1].split(":")[0])

                service_info = await self.register_service(
                    name=service_name,
                    base_url=url,
                    manual_url=manual_url
                )

                discovered.append(service_info)

            except Exception as e:
                error_msg = f"Failed to discover service at {url}: {e}"
                logger.warning(error_msg)
                errors.append(error_msg)

                if fail_on_error:
                    raise

        logger.info(
            "Service discovery completed",
            discovered=len(discovered),
            failed=len(errors)
        )

        return discovered

    async def unregister_service(self, name: str) -> None:
        """
        Unregister a service from the registry.

        Args:
            name: Service name to unregister
        """
        if name in self.services:
            del self.services[name]
            await self._refresh_client()
            logger.info("Service unregistered", name=name)
        else:
            logger.warning("Attempted to unregister unknown service", name=name)

    async def _fetch_manual(self, manual_url: str) -> Dict[str, Any]:
        """Fetch UTCP manual from URL using pooled connection."""
        response = await self.http_client.get(manual_url)
        response.raise_for_status()
        return response.json()

    async def _refresh_client(self) -> None:
        """Recreate UTCP client with updated service list."""
        if not self.services:
            self.utcp_client = None
            return

        # Build call templates from all services
        call_templates = []

        for service in self.services.values():
            if not service.is_healthy or not service.manual:
                continue

            # Extract templates from service manual
            service_templates = service.manual.get("manual_call_templates", [])

            for template in service_templates:
                # Namespace template with service name
                namespaced_template = {
                    **template,
                    "name": f"{service.name}_{template['name']}",
                    "url": template.get("url", "").replace("${BASE_URL}", service.base_url)
                }
                call_templates.append(namespaced_template)

        # Create UTCP client
        config = {
            "manual_call_templates": call_templates
        }

        self.utcp_client = await UtcpClient.create(config)

        logger.debug(
            "UTCP client refreshed",
            service_count=len(self.services),
            template_count=len(call_templates)
        )

    async def call_tool(
        self,
        tool_name: str,
        tool_args: Dict[str, Any],
        timeout: Optional[int] = None
    ) -> Any:
        """
        Call a tool via UTCP protocol.

        Args:
            tool_name: Fully qualified tool name (service.tool_name)
            tool_args: Arguments to pass to the tool
            timeout: Optional timeout override

        Returns:
            Tool execution result

        Raises:
            RuntimeError: If no services are registered
            ValueError: If tool not found
        """
        if not self.utcp_client:
            raise RuntimeError("No services registered in UTCP client")

        logger.info("Calling tool via UTCP", tool=tool_name, args_keys=list(tool_args.keys()))

        try:
            result = await self.utcp_client.call_tool(tool_name, tool_args)

            logger.info("Tool call successful", tool=tool_name)
            return result

        except Exception as e:
            logger.error("Tool call failed", tool=tool_name, error=str(e))
            raise

    def list_available_tools(
        self,
        service_name: Optional[str] = None,
        tags: Optional[Set[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        List all available tools from registered services.

        Args:
            service_name: Filter by specific service
            tags: Filter by service tags

        Returns:
            List of tool definitions
        """
        tools = []

        for service in self.services.values():
            # Apply filters
            if service_name and service.name != service_name:
                continue

            if tags and not (tags & service.tags):
                continue

            if not service.is_healthy or not service.manual:
                continue

            # Extract tools from service manual
            service_tools = service.manual.get("tools", [])

            for tool in service_tools:
                # Add service context to tool
                enriched_tool = {
                    **tool,
                    "service": {
                        "name": service.name,
                        "base_url": service.base_url,
                        "tags": list(service.tags)
                    }
                }
                tools.append(enriched_tool)

        return tools

    def get_service(self, name: str) -> Optional[ServiceInfo]:
        """Get service information by name."""
        return self.services.get(name)

    def list_services(
        self,
        healthy_only: bool = False,
        tags: Optional[Set[str]] = None
    ) -> List[ServiceInfo]:
        """
        List all registered services.

        Args:
            healthy_only: Only return healthy services
            tags: Filter by tags

        Returns:
            List of service information objects
        """
        services = list(self.services.values())

        if healthy_only:
            services = [s for s in services if s.is_healthy]

        if tags:
            services = [s for s in services if tags & s.tags]

        return services

    async def health_check(self, service_name: Optional[str] = None) -> Dict[str, bool]:
        """
        Perform health check on services.

        Args:
            service_name: Check specific service, or all if None

        Returns:
            Dictionary mapping service names to health status
        """
        services_to_check = (
            [self.services[service_name]] if service_name
            else list(self.services.values())
        )

        results = {}

        for service in services_to_check:
            try:
                # Try to fetch health endpoint
                health_url = f"{service.base_url}/health"
                response = await self.http_client.get(health_url, timeout=10)

                is_healthy = response.status_code == 200

                service.is_healthy = is_healthy
                service.last_health_check = datetime.utcnow()
                results[service.name] = is_healthy

            except Exception as e:
                logger.warning(
                    "Health check failed",
                    service=service.name,
                    error=str(e)
                )
                service.is_healthy = False
                service.last_health_check = datetime.utcnow()
                results[service.name] = False

        return results

    async def start_health_monitoring(self) -> None:
        """Start background health monitoring task."""
        if self._health_check_task:
            logger.warning("Health monitoring already running")
            return

        async def monitor():
            while True:
                try:
                    await self.health_check()
                    await asyncio.sleep(self.health_check_interval)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("Health monitoring error", error=str(e))

        self._health_check_task = asyncio.create_task(monitor())
        logger.info("Health monitoring started", interval=self.health_check_interval)

    async def stop_health_monitoring(self) -> None:
        """Stop background health monitoring task."""
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
            self._health_check_task = None
            logger.info("Health monitoring stopped")

    async def cleanup(self) -> None:
        """Cleanup resources including HTTP client connections."""
        await self.stop_health_monitoring()
        await self.http_client.aclose()  # Close connection pool
        self.services.clear()
        self.utcp_client = None
        logger.info("Registry cleanup completed")