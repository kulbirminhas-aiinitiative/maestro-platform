"""
Health Check API Endpoint

A simple REST API endpoint for health monitoring and system status checks.
Provides basic health status, version information, and system metrics.
"""

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import os
import platform
import psutil

app = FastAPI(
    title="Health Check API",
    description="Simple health check endpoint for monitoring system status",
    version="1.0.0"
)

class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    version: str
    uptime_seconds: Optional[float] = None

class DetailedHealthResponse(BaseModel):
    """Detailed health check response with system metrics."""
    status: str
    timestamp: str
    version: str
    system: dict
    checks: dict

# Track application start time
APP_START_TIME = datetime.utcnow()
APP_VERSION = "1.0.0"

@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Basic health check endpoint.

    Returns:
        HealthResponse: Basic health status with timestamp and version.
    """
    uptime = (datetime.utcnow() - APP_START_TIME).total_seconds()

    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat() + "Z",
        version=APP_VERSION,
        uptime_seconds=round(uptime, 2)
    )

@app.get("/health/ready", tags=["Health"])
async def readiness_check():
    """
    Kubernetes-style readiness probe endpoint.

    Returns:
        JSONResponse: Readiness status for load balancer routing.
    """
    return JSONResponse(
        content={
            "status": "ready",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        status_code=200
    )

@app.get("/health/live", tags=["Health"])
async def liveness_check():
    """
    Kubernetes-style liveness probe endpoint.

    Returns:
        JSONResponse: Liveness status indicating process is running.
    """
    return JSONResponse(
        content={
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        },
        status_code=200
    )

@app.get("/health/detailed", response_model=DetailedHealthResponse, tags=["Health"])
async def detailed_health_check():
    """
    Detailed health check with system metrics.

    Returns:
        DetailedHealthResponse: Comprehensive health status with system info.
    """
    uptime = (datetime.utcnow() - APP_START_TIME).total_seconds()

    # System information
    system_info = {
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "hostname": platform.node(),
        "cpu_count": os.cpu_count()
    }

    # Health checks
    checks = {
        "api": "passing",
        "memory": "passing",
        "disk": "passing"
    }

    # Memory check
    try:
        memory = psutil.virtual_memory()
        system_info["memory_percent"] = memory.percent
        if memory.percent > 90:
            checks["memory"] = "warning"
    except Exception:
        checks["memory"] = "unknown"

    # Disk check
    try:
        disk = psutil.disk_usage('/')
        system_info["disk_percent"] = disk.percent
        if disk.percent > 90:
            checks["disk"] = "warning"
    except Exception:
        checks["disk"] = "unknown"

    # Determine overall status
    status = "healthy"
    if any(v == "warning" for v in checks.values()):
        status = "degraded"
    if any(v == "critical" for v in checks.values()):
        status = "unhealthy"

    return DetailedHealthResponse(
        status=status,
        timestamp=datetime.utcnow().isoformat() + "Z",
        version=APP_VERSION,
        system=system_info,
        checks=checks
    )

@app.get("/", tags=["Root"])
async def root():
    """Root endpoint redirecting to health check."""
    return {"message": "Health Check API", "health_endpoint": "/health"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
