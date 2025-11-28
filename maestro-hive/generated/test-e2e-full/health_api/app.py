"""
Health Check API Service
A simple FastAPI application providing health check endpoints.
"""

from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import os

app = FastAPI(
    title="Health Check API",
    description="Simple health check endpoint service",
    version="1.0.0"
)


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: str
    version: str
    service: str


class ReadinessResponse(BaseModel):
    """Readiness check response model."""
    ready: bool
    checks: dict


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """
    Basic health check endpoint.
    Returns service status and metadata.
    """
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        version=os.getenv("APP_VERSION", "1.0.0"),
        service="health-api"
    )


@app.get("/ready", response_model=ReadinessResponse, tags=["Health"])
async def readiness_check():
    """
    Readiness check endpoint.
    Returns whether the service is ready to accept traffic.
    """
    return ReadinessResponse(
        ready=True,
        checks={
            "api": "ok",
            "dependencies": "ok"
        }
    )


@app.get("/live", tags=["Health"])
async def liveness_check():
    """
    Liveness check endpoint.
    Simple endpoint for container orchestration liveness probes.
    """
    return {"alive": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
