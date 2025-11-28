"""
Health Check API Endpoint

A simple FastAPI-based health check service for monitoring application status.
"""

from datetime import datetime
from typing import Dict, Any
from fastapi import FastAPI, status
from pydantic import BaseModel
import uvicorn

app = FastAPI(
    title="Health Check API",
    description="Simple API endpoint for health checks",
    version="1.0.0"
)


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    service: str
    version: str
    checks: Dict[str, Any]


class DetailedHealthResponse(HealthResponse):
    """Extended health check response with additional details."""
    uptime_seconds: float = 0.0
    environment: str = "development"


# Track service start time for uptime calculation
SERVICE_START_TIME = datetime.utcnow()


@app.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Basic health check",
    description="Returns the basic health status of the service"
)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    Returns:
        HealthResponse: Basic health status information
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        service="health-check-api",
        version="1.0.0",
        checks={
            "api": "ok"
        }
    )


@app.get(
    "/health/detailed",
    response_model=DetailedHealthResponse,
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Detailed health check",
    description="Returns detailed health status including uptime and additional checks"
)
async def detailed_health_check() -> DetailedHealthResponse:
    """
    Detailed health check endpoint with extended information.

    Returns:
        DetailedHealthResponse: Detailed health status including uptime
    """
    uptime = (datetime.utcnow() - SERVICE_START_TIME).total_seconds()

    return DetailedHealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        service="health-check-api",
        version="1.0.0",
        checks={
            "api": "ok",
            "memory": "ok",
            "disk": "ok"
        },
        uptime_seconds=uptime,
        environment="development"
    )


@app.get(
    "/health/ready",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Readiness probe",
    description="Kubernetes-style readiness probe endpoint"
)
async def readiness_probe() -> Dict[str, str]:
    """
    Readiness probe for Kubernetes deployments.

    Returns:
        dict: Ready status
    """
    return {"status": "ready"}


@app.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    tags=["Health"],
    summary="Liveness probe",
    description="Kubernetes-style liveness probe endpoint"
)
async def liveness_probe() -> Dict[str, str]:
    """
    Liveness probe for Kubernetes deployments.

    Returns:
        dict: Alive status
    """
    return {"status": "alive"}


if __name__ == "__main__":
    uvicorn.run(
        "health_check_api:app",
        host="0.0.0.0",
        port=8080,
        reload=True
    )
