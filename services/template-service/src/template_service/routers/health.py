"""
Health Check Router
System health and status endpoints
"""

from datetime import datetime
from fastapi import APIRouter, Depends
import asyncpg
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint

    Returns:
        Service health status
    """
    return {
        "status": "healthy",
        "service": "maestro-templates-registry",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/health/detailed")
async def detailed_health_check(db_pool=None, redis_client=None):
    """
    Detailed health check with component status

    Returns:
        Detailed health information for all components
    """
    health = {
        "status": "healthy",
        "service": "maestro-templates-registry",
        "version": "2.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "api": {"status": "healthy"},
            "database": {"status": "unknown"},
            "redis": {"status": "unknown"},
            "filesystem": {"status": "unknown"}
        }
    }

    # Check database
    if db_pool:
        try:
            async with db_pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
                health["components"]["database"]["status"] = "healthy"
        except Exception as e:
            health["components"]["database"]["status"] = "unhealthy"
            health["components"]["database"]["error"] = str(e)
            health["status"] = "degraded"

    # Check Redis
    if redis_client:
        try:
            await redis_client.ping()
            health["components"]["redis"]["status"] = "healthy"
        except Exception as e:
            health["components"]["redis"]["status"] = "unhealthy"
            health["components"]["redis"]["error"] = str(e)
            health["status"] = "degraded"

    # Check filesystem
    try:
        from pathlib import Path
        cache_dir = Path("/storage/cache")
        temp_dir = Path("/storage/temp")

        if cache_dir.exists() and temp_dir.exists():
            health["components"]["filesystem"]["status"] = "healthy"
        else:
            health["components"]["filesystem"]["status"] = "unhealthy"
            health["status"] = "degraded"
    except Exception as e:
        health["components"]["filesystem"]["status"] = "unhealthy"
        health["components"]["filesystem"]["error"] = str(e)
        health["status"] = "degraded"

    return health


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes readiness probe endpoint

    Returns:
        Ready status
    """
    return {"ready": True}


@router.get("/live")
async def liveness_check():
    """
    Kubernetes liveness probe endpoint

    Returns:
        Live status
    """
    return {"live": True}