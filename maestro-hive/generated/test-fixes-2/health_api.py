"""
Health Check API Endpoint

A production-ready health check API service that provides system status information.
"""

import os
import time
import socket
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Response, status
from pydantic import BaseModel

# Application metadata
APP_NAME = "Health Check API"
APP_VERSION = "1.0.0"
START_TIME = time.time()

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="Health check API endpoint for service monitoring"
)


class HealthStatus(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    version: str
    uptime_seconds: float
    hostname: str
    service: str
    checks: Optional[dict] = None


class DetailedHealthStatus(HealthStatus):
    """Extended health check with component details."""
    components: dict


def get_uptime() -> float:
    """Calculate service uptime in seconds."""
    return round(time.time() - START_TIME, 2)


def get_hostname() -> str:
    """Get the current hostname."""
    return socket.gethostname()


def check_component_health() -> dict:
    """
    Check health of various components.
    Extend this function to add database, cache, or other service checks.
    """
    components = {
        "api": {
            "status": "healthy",
            "response_time_ms": 0
        }
    }

    # Example: Add database check
    # try:
    #     start = time.time()
    #     # db.execute("SELECT 1")
    #     components["database"] = {
    #         "status": "healthy",
    #         "response_time_ms": round((time.time() - start) * 1000, 2)
    #     }
    # except Exception as e:
    #     components["database"] = {"status": "unhealthy", "error": str(e)}

    return components


@app.get(
    "/health",
    response_model=HealthStatus,
    summary="Basic health check",
    description="Returns basic health status of the service",
    tags=["Health"]
)
async def health_check() -> HealthStatus:
    """
    Basic health check endpoint.

    Returns:
        HealthStatus: Basic service health information
    """
    return HealthStatus(
        status="healthy",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=APP_VERSION,
        uptime_seconds=get_uptime(),
        hostname=get_hostname(),
        service=APP_NAME
    )


@app.get(
    "/health/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    description="Kubernetes liveness probe - returns 200 if service is running",
    tags=["Health"]
)
async def liveness_probe(response: Response):
    """
    Liveness probe for container orchestration.

    Returns 200 OK if the service is running.
    """
    return {"status": "alive"}


@app.get(
    "/health/ready",
    summary="Readiness probe",
    description="Kubernetes readiness probe - returns 200 if service is ready to accept traffic",
    tags=["Health"]
)
async def readiness_probe(response: Response):
    """
    Readiness probe for container orchestration.

    Returns 200 OK if the service is ready to handle requests.
    Returns 503 if the service is not ready.
    """
    # Add readiness checks here (e.g., database connection, cache connection)
    is_ready = True

    if is_ready:
        return {"status": "ready"}
    else:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not_ready"}


@app.get(
    "/health/detailed",
    response_model=DetailedHealthStatus,
    summary="Detailed health check",
    description="Returns detailed health status including component checks",
    tags=["Health"]
)
async def detailed_health_check() -> DetailedHealthStatus:
    """
    Detailed health check with component status.

    Returns:
        DetailedHealthStatus: Detailed health information including component status
    """
    components = check_component_health()

    # Determine overall status based on components
    overall_status = "healthy"
    for component_name, component_status in components.items():
        if component_status.get("status") != "healthy":
            overall_status = "degraded"
            break

    return DetailedHealthStatus(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=APP_VERSION,
        uptime_seconds=get_uptime(),
        hostname=get_hostname(),
        service=APP_NAME,
        components=components
    )


@app.get(
    "/",
    summary="Root endpoint",
    description="Returns basic service information",
    tags=["Info"]
)
async def root():
    """Root endpoint with service information."""
    return {
        "service": APP_NAME,
        "version": APP_VERSION,
        "docs": "/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")

    uvicorn.run(
        "health_api:app",
        host=host,
        port=port,
        reload=os.getenv("ENV", "development") == "development"
    )
