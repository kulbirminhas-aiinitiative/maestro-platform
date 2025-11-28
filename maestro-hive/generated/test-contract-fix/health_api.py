"""
Health Check API Endpoint

Provides a simple health check endpoint for service monitoring and orchestration.

Features:
- Basic health status check
- Service information (version, timestamp)
- Optional dependency health checks
- Prometheus-compatible metrics endpoint

Author: Requirement Analyst
Date: 2025-11-22
Version: 1.0.0
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from enum import Enum

from fastapi import FastAPI, APIRouter, Response, status
from pydantic import BaseModel, Field


# ============================================================================
# Data Models
# ============================================================================

class HealthStatus(str, Enum):
    """Service health status values."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class DependencyHealth(BaseModel):
    """Health status of a service dependency."""
    name: str = Field(..., description="Name of the dependency")
    status: HealthStatus = Field(..., description="Health status of the dependency")
    response_time_ms: Optional[float] = Field(None, description="Response time in milliseconds")
    message: Optional[str] = Field(None, description="Additional status message")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: HealthStatus = Field(..., description="Overall service health status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    uptime_seconds: Optional[float] = Field(None, description="Service uptime in seconds")
    dependencies: Optional[List[DependencyHealth]] = Field(
        None,
        description="Health status of dependencies"
    )
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional health details"
    )


class ReadinessResponse(BaseModel):
    """Readiness check response for Kubernetes."""
    ready: bool = Field(..., description="Whether service is ready to receive traffic")
    message: str = Field(..., description="Readiness status message")


class LivenessResponse(BaseModel):
    """Liveness check response for Kubernetes."""
    alive: bool = Field(..., description="Whether service is alive")
    message: str = Field(..., description="Liveness status message")


# ============================================================================
# Health Check Service
# ============================================================================

class HealthCheckService:
    """Service for managing health check state and dependencies."""

    def __init__(
        self,
        service_name: str = "health-api",
        version: str = "1.0.0"
    ):
        self.service_name = service_name
        self.version = version
        self.start_time = datetime.now(timezone.utc)
        self._dependencies: Dict[str, callable] = {}

    def register_dependency(self, name: str, check_func: callable) -> None:
        """Register a dependency health check function.

        Args:
            name: Name of the dependency
            check_func: Async function that returns (status, response_time_ms, message)
        """
        self._dependencies[name] = check_func

    async def check_dependencies(self) -> List[DependencyHealth]:
        """Check health of all registered dependencies."""
        results = []

        for name, check_func in self._dependencies.items():
            try:
                status, response_time, message = await check_func()
                results.append(DependencyHealth(
                    name=name,
                    status=status,
                    response_time_ms=response_time,
                    message=message
                ))
            except Exception as e:
                results.append(DependencyHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"Check failed: {str(e)}"
                ))

        return results

    def get_uptime(self) -> float:
        """Get service uptime in seconds."""
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()

    async def get_health_status(self, include_dependencies: bool = False) -> HealthResponse:
        """Get comprehensive health status."""
        dependencies = None
        overall_status = HealthStatus.HEALTHY

        if include_dependencies and self._dependencies:
            dependencies = await self.check_dependencies()

            # Determine overall status based on dependencies
            if any(d.status == HealthStatus.UNHEALTHY for d in dependencies):
                overall_status = HealthStatus.UNHEALTHY
            elif any(d.status == HealthStatus.DEGRADED for d in dependencies):
                overall_status = HealthStatus.DEGRADED

        return HealthResponse(
            status=overall_status,
            service=self.service_name,
            version=self.version,
            timestamp=datetime.now(timezone.utc).isoformat(),
            uptime_seconds=self.get_uptime(),
            dependencies=dependencies
        )


# ============================================================================
# API Router
# ============================================================================

def create_health_router(
    service: Optional[HealthCheckService] = None,
    prefix: str = "/health"
) -> APIRouter:
    """Create a health check API router.

    Args:
        service: Optional HealthCheckService instance. Creates default if None.
        prefix: URL prefix for health endpoints

    Returns:
        FastAPI APIRouter with health check endpoints
    """

    if service is None:
        service = HealthCheckService()

    router = APIRouter(prefix=prefix, tags=["Health"])

    @router.get(
        "",
        response_model=HealthResponse,
        summary="Health Check",
        description="Get service health status with optional dependency checks"
    )
    async def health_check(
        include_dependencies: bool = False
    ) -> HealthResponse:
        """
        Perform a health check on the service.

        Returns the current health status including:
        - Service status (healthy/degraded/unhealthy)
        - Service metadata (name, version)
        - Uptime information
        - Optional dependency health status
        """
        return await service.get_health_status(include_dependencies)

    @router.get(
        "/ready",
        response_model=ReadinessResponse,
        summary="Readiness Check",
        description="Kubernetes-style readiness probe"
    )
    async def readiness_check(response: Response) -> ReadinessResponse:
        """
        Check if service is ready to receive traffic.

        This endpoint is designed for Kubernetes readiness probes.
        Returns 200 if ready, 503 if not ready.
        """
        health = await service.get_health_status(include_dependencies=True)

        if health.status == HealthStatus.HEALTHY:
            return ReadinessResponse(ready=True, message="Service is ready")
        else:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
            return ReadinessResponse(
                ready=False,
                message=f"Service status: {health.status.value}"
            )

    @router.get(
        "/live",
        response_model=LivenessResponse,
        summary="Liveness Check",
        description="Kubernetes-style liveness probe"
    )
    async def liveness_check() -> LivenessResponse:
        """
        Check if service is alive.

        This endpoint is designed for Kubernetes liveness probes.
        Always returns 200 if the service is responding.
        """
        return LivenessResponse(alive=True, message="Service is alive")

    @router.get(
        "/metrics",
        summary="Prometheus Metrics",
        description="Expose basic metrics in Prometheus format"
    )
    async def metrics() -> Response:
        """
        Expose service metrics in Prometheus format.

        Returns basic metrics including:
        - service_up: Whether service is running (1/0)
        - service_uptime_seconds: Time since service started
        """
        uptime = service.get_uptime()

        metrics_text = f"""# HELP service_up Whether the service is up
# TYPE service_up gauge
service_up{{service="{service.service_name}"}} 1

# HELP service_uptime_seconds Time since service started
# TYPE service_uptime_seconds counter
service_uptime_seconds{{service="{service.service_name}"}} {uptime:.2f}

# HELP service_info Service metadata
# TYPE service_info gauge
service_info{{service="{service.service_name}",version="{service.version}"}} 1
"""
        return Response(
            content=metrics_text,
            media_type="text/plain; version=0.0.4"
        )

    return router


# ============================================================================
# Standalone Application
# ============================================================================

def create_app(
    service_name: str = "health-api",
    version: str = "1.0.0"
) -> FastAPI:
    """Create a FastAPI application with health check endpoints.

    Args:
        service_name: Name of the service
        version: Service version

    Returns:
        FastAPI application instance
    """
    app = FastAPI(
        title=f"{service_name} Health API",
        description="Health check API for service monitoring",
        version=version
    )

    health_service = HealthCheckService(service_name=service_name, version=version)
    health_router = create_health_router(service=health_service)

    app.include_router(health_router)

    # Root redirect to health
    @app.get("/", include_in_schema=False)
    async def root():
        return {"message": "Health API", "health_endpoint": "/health"}

    return app


# Create default application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
