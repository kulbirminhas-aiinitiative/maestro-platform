"""
Health Check API Endpoint
=========================

A production-ready health check endpoint for service monitoring and orchestration.

Author: Marcus (Backend Developer)
Version: 1.0.0
"""

from fastapi import FastAPI, Response, status
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional
import os

app = FastAPI(
    title="Health Check API",
    description="Production-ready health check endpoint for service monitoring",
    version="1.0.0"
)


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    service: str
    version: str
    uptime_seconds: Optional[float] = None

    class Config:
        json_schema_extra = {
            "example": {
                "status": "healthy",
                "timestamp": "2025-11-22T12:00:00Z",
                "service": "health-check-api",
                "version": "1.0.0",
                "uptime_seconds": 3600.5
            }
        }


class DetailedHealthResponse(HealthResponse):
    """Detailed health check response with additional diagnostics."""
    environment: str
    dependencies: dict


# Track service start time for uptime calculation
SERVICE_START_TIME = datetime.now(timezone.utc)
SERVICE_NAME = os.getenv("SERVICE_NAME", "health-check-api")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Basic Health Check",
    description="Returns the basic health status of the service.",
    tags=["Health"]
)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    Returns a simple health status indicating the service is running.
    Use this endpoint for:
    - Kubernetes liveness probes
    - Load balancer health checks
    - Basic monitoring

    Returns:
        HealthResponse: Basic health status information
    """
    uptime = (datetime.now(timezone.utc) - SERVICE_START_TIME).total_seconds()

    return HealthResponse(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
        uptime_seconds=round(uptime, 2)
    )


@app.get(
    "/health/ready",
    response_model=DetailedHealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness Check",
    description="Returns detailed health status including dependency checks.",
    tags=["Health"]
)
async def readiness_check(response: Response) -> DetailedHealthResponse:
    """
    Readiness check endpoint with dependency verification.

    Returns detailed health status including checks for:
    - Database connectivity (placeholder)
    - Cache availability (placeholder)
    - External service dependencies (placeholder)

    Use this endpoint for:
    - Kubernetes readiness probes
    - Detailed monitoring dashboards
    - Troubleshooting

    Returns:
        DetailedHealthResponse: Detailed health status with dependency information
    """
    uptime = (datetime.now(timezone.utc) - SERVICE_START_TIME).total_seconds()

    # Dependency checks (placeholders - implement actual checks as needed)
    dependencies = {
        "database": {"status": "healthy", "latency_ms": 5},
        "cache": {"status": "healthy", "latency_ms": 1},
    }

    # Determine overall status based on dependencies
    all_healthy = all(
        dep.get("status") == "healthy"
        for dep in dependencies.values()
    )

    overall_status = "healthy" if all_healthy else "degraded"

    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return DetailedHealthResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
        uptime_seconds=round(uptime, 2),
        environment=ENVIRONMENT,
        dependencies=dependencies
    )


@app.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness Check",
    description="Minimal liveness probe endpoint.",
    tags=["Health"]
)
async def liveness_check():
    """
    Minimal liveness check endpoint.

    Returns a simple 200 OK response indicating the service process is alive.
    This is the lightest possible health check for high-frequency polling.

    Use this endpoint for:
    - Kubernetes liveness probes
    - High-frequency monitoring

    Returns:
        dict: Simple OK status
    """
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
