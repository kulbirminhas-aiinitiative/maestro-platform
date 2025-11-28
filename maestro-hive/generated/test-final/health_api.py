"""
Health Check API Endpoint

A simple health check API for monitoring service availability and status.
Provides endpoints for basic health checks and detailed system information.

Author: Marcus (Backend Developer)
Version: 1.0.0
"""

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any
import platform
import os
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Health Check API",
    description="Service health monitoring endpoint for checking service availability, readiness, and liveness.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Health",
            "description": "Health check endpoints for monitoring service status"
        }
    ]
)

# Response models
class HealthResponse(BaseModel):
    """Health check response model"""
    status: str = Field(..., description="Service health status", example="healthy")
    timestamp: str = Field(..., description="ISO 8601 timestamp", example="2024-01-15T10:30:00.000000")
    service: str = Field(..., description="Service name", example="health-check-api")
    version: str = Field(..., description="API version", example="1.0.0")

class DetailedHealthResponse(BaseModel):
    """Detailed health check response with system info"""
    status: str = Field(..., description="Service health status", example="healthy")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="API version")
    uptime_seconds: Optional[float] = Field(None, description="Service uptime in seconds")
    system: Dict[str, Any] = Field(..., description="System information")

class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    timestamp: str = Field(..., description="ISO 8601 timestamp")

class ReadinessResponse(BaseModel):
    """Readiness probe response"""
    ready: bool = Field(..., description="Whether service is ready to accept traffic")

class LivenessResponse(BaseModel):
    """Liveness probe response"""
    alive: bool = Field(..., description="Whether service is alive")

# Service configuration
SERVICE_NAME = os.getenv("SERVICE_NAME", "health-check-api")
SERVICE_VERSION = os.getenv("SERVICE_VERSION", "1.0.0")

# Track startup time
_startup_time = datetime.utcnow()
logger.info(f"Service {SERVICE_NAME} v{SERVICE_VERSION} initialized")

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    responses={
        200: {"description": "Service is healthy"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def health_check():
    """
    Basic health check endpoint.

    Returns the service status, timestamp, and version information.
    Use this endpoint for load balancer health checks and basic monitoring.

    **Response Codes:**
    - 200: Service is healthy and operational
    - 500: Internal error occurred
    """
    try:
        logger.debug("Health check requested")
        return HealthResponse(
            status="healthy",
            timestamp=datetime.utcnow().isoformat(),
            service=SERVICE_NAME,
            version=SERVICE_VERSION
        )
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "Health check failed",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.get(
    "/health/detailed",
    response_model=DetailedHealthResponse,
    tags=["Health"],
    responses={
        200: {"description": "Detailed health information"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def detailed_health_check():
    """
    Detailed health check endpoint.

    Returns comprehensive health information including system details
    and uptime. Use this for detailed monitoring and diagnostics.

    **Response Codes:**
    - 200: Successfully retrieved detailed health info
    - 500: Internal error occurred
    """
    try:
        current_time = datetime.utcnow()
        uptime = (current_time - _startup_time).total_seconds()

        logger.debug(f"Detailed health check requested, uptime: {uptime:.2f}s")

        return DetailedHealthResponse(
            status="healthy",
            timestamp=current_time.isoformat(),
            service=SERVICE_NAME,
            version=SERVICE_VERSION,
            uptime_seconds=round(uptime, 2),
            system={
                "platform": platform.system(),
                "python_version": platform.python_version(),
                "hostname": platform.node(),
                "processor": platform.processor() or "unknown",
                "pid": os.getpid()
            }
        )
    except Exception as e:
        logger.error(f"Detailed health check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalError",
                "message": "Detailed health check failed",
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@app.get(
    "/ready",
    response_model=ReadinessResponse,
    tags=["Health"],
    responses={
        200: {"description": "Service is ready"},
        503: {"model": ErrorResponse, "description": "Service not ready"}
    }
)
async def readiness_check():
    """
    Kubernetes-style readiness probe.

    Returns 200 if the service is ready to accept traffic.
    Use this for Kubernetes readiness probes.

    **Response Codes:**
    - 200: Service is ready to accept traffic
    - 503: Service is not ready
    """
    # Add custom readiness checks here (database, cache, etc.)
    return ReadinessResponse(ready=True)

@app.get(
    "/live",
    response_model=LivenessResponse,
    tags=["Health"],
    responses={
        200: {"description": "Service is alive"},
        503: {"model": ErrorResponse, "description": "Service not alive"}
    }
)
async def liveness_check():
    """
    Kubernetes-style liveness probe.

    Returns 200 if the service is alive and running.
    Use this for Kubernetes liveness probes.

    **Response Codes:**
    - 200: Service is alive
    - 503: Service is not alive
    """
    return LivenessResponse(alive=True)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler for unhandled errors"""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    logger.info(f"Starting {SERVICE_NAME} on {host}:{port}")
    uvicorn.run(app, host=host, port=port)
