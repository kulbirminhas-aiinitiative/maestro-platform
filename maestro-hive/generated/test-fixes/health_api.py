"""
Health Check API Endpoint

A simple REST API endpoint for health monitoring and service status checks.
"""

from fastapi import FastAPI, Response
from pydantic import BaseModel
from datetime import datetime
import os
import psutil
from typing import Optional

app = FastAPI(
    title="Health Check API",
    description="Service health monitoring endpoint",
    version="1.0.0"
)


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    version: str
    service: str
    uptime_seconds: Optional[float] = None
    memory_usage_mb: Optional[float] = None


class DetailedHealthResponse(HealthResponse):
    """Detailed health check with system metrics."""
    cpu_percent: Optional[float] = None
    disk_usage_percent: Optional[float] = None


# Track service start time
SERVICE_START_TIME = datetime.utcnow()
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")
SERVICE_NAME = os.getenv("SERVICE_NAME", "health-check-service")


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Basic Health Check",
    description="Returns basic health status of the service",
    tags=["Health"]
)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    Returns:
        HealthResponse: Service health status with timestamp
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version=SERVICE_VERSION,
        service=SERVICE_NAME
    )


@app.get(
    "/health/detailed",
    response_model=DetailedHealthResponse,
    summary="Detailed Health Check",
    description="Returns detailed health status including system metrics",
    tags=["Health"]
)
async def detailed_health_check() -> DetailedHealthResponse:
    """
    Detailed health check with system metrics.

    Returns:
        DetailedHealthResponse: Service health with CPU, memory, and disk metrics
    """
    uptime = (datetime.utcnow() - SERVICE_START_TIME).total_seconds()
    process = psutil.Process()
    memory_mb = process.memory_info().rss / (1024 * 1024)

    return DetailedHealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version=SERVICE_VERSION,
        service=SERVICE_NAME,
        uptime_seconds=round(uptime, 2),
        memory_usage_mb=round(memory_mb, 2),
        cpu_percent=psutil.cpu_percent(interval=0.1),
        disk_usage_percent=psutil.disk_usage('/').percent
    )


@app.get(
    "/health/ready",
    summary="Readiness Check",
    description="Kubernetes-style readiness probe",
    tags=["Health"]
)
async def readiness_check(response: Response):
    """
    Readiness probe for container orchestration.

    Returns:
        dict: Ready status
    """
    # Add custom readiness checks here (e.g., database connectivity)
    is_ready = True

    if not is_ready:
        response.status_code = 503
        return {"status": "not_ready", "timestamp": datetime.utcnow().isoformat()}

    return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}


@app.get(
    "/health/live",
    summary="Liveness Check",
    description="Kubernetes-style liveness probe",
    tags=["Health"]
)
async def liveness_check():
    """
    Liveness probe for container orchestration.

    Returns:
        dict: Alive status
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
