"""
Health check endpoints for MAESTRO APIs.

Provides standard health and readiness endpoints for monitoring and orchestration.
"""

import asyncio
import platform
import sys
from datetime import datetime
from typing import Callable, Dict, List, Optional
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from maestro_core_logging import get_logger

from .responses import HealthResponse

def _get_logger():
    try:
        from maestro_core_logging import get_logger
        return get_logger(__name__)
    except:
        import logging
        return logging.getLogger(__name__)

logger = type("LazyLogger", (), {"__getattr__": lambda self, name: getattr(_get_logger(), name)})()


class HealthCheck:
    """
    Health check configuration and execution.

    Allows registering custom health checks for dependencies like databases, caches, etc.
    """

    def __init__(self):
        """Initialize health check manager."""
        self._checks: Dict[str, Callable] = {}
        self._last_check_time: Optional[datetime] = None
        self._last_check_result: Dict = {}

    def register_check(self, name: str, check_func: Callable) -> None:
        """
        Register a health check function.

        Args:
            name: Name of the check (e.g., "database", "redis")
            check_func: Async or sync function that returns True if healthy

        Example:
            >>> health = HealthCheck()
            >>> async def check_db():
            ...     # Check database connection
            ...     return True
            >>> health.register_check("database", check_db)
        """
        self._checks[name] = check_func
        logger.info(f"Registered health check: {name}")

    async def run_checks(self) -> Dict[str, str]:
        """
        Run all registered health checks.

        Returns:
            Dictionary mapping check names to status ("healthy" or "unhealthy")
        """
        results = {}

        for name, check_func in self._checks.items():
            try:
                if asyncio.iscoroutinefunction(check_func):
                    result = await check_func()
                else:
                    result = check_func()

                results[name] = "healthy" if result else "unhealthy"
            except Exception as e:
                logger.error(f"Health check {name} failed", error=str(e))
                results[name] = "unhealthy"

        self._last_check_time = datetime.utcnow()
        self._last_check_result = results
        return results

    def get_last_check_result(self) -> Dict:
        """Get the last check result without re-running checks."""
        return {
            "checks": self._last_check_result,
            "last_check_time": self._last_check_time.isoformat() if self._last_check_time else None
        }


def create_health_routes(
    app: FastAPI,
    service_version: str = "1.0.0",
    health_check: Optional[HealthCheck] = None
) -> None:
    """
    Add standard health check routes to FastAPI application.

    Args:
        app: FastAPI application instance
        service_version: Version string to include in health response
        health_check: Optional HealthCheck instance for custom checks

    Adds endpoints:
        - GET /health - Simple health check
        - GET /health/live - Liveness probe (Kubernetes)
        - GET /health/ready - Readiness probe (Kubernetes)
        - GET /health/detailed - Detailed health with component checks
    """
    health_manager = health_check or HealthCheck()

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["Health"],
        summary="Health Check",
        description="Simple health check endpoint"
    )
    async def health():
        """Simple health check endpoint."""
        return HealthResponse(
            status="healthy",
            version=service_version,
            timestamp=datetime.utcnow().isoformat()
        )

    @app.get(
        "/health/live",
        status_code=status.HTTP_200_OK,
        tags=["Health"],
        summary="Liveness Probe",
        description="Kubernetes liveness probe endpoint"
    )
    async def liveness():
        """
        Liveness probe for Kubernetes.

        Returns 200 if service is alive (process is running).
        """
        return {"status": "alive"}

    @app.get(
        "/health/ready",
        tags=["Health"],
        summary="Readiness Probe",
        description="Kubernetes readiness probe endpoint"
    )
    async def readiness():
        """
        Readiness probe for Kubernetes.

        Returns 200 if service is ready to accept traffic.
        Runs all registered health checks.
        """
        checks = await health_manager.run_checks()

        # Service is ready if all checks pass
        all_healthy = all(status == "healthy" for status in checks.values())

        if all_healthy:
            return JSONResponse(
                status_code=status.HTTP_200_OK,
                content={"status": "ready", "checks": checks}
            )
        else:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"status": "not_ready", "checks": checks}
            )

    @app.get(
        "/health/detailed",
        response_model=HealthResponse,
        tags=["Health"],
        summary="Detailed Health Check",
        description="Detailed health check with component status"
    )
    async def detailed_health():
        """
        Detailed health check with component status.

        Includes:
        - Service version
        - Python version
        - Platform information
        - Individual component checks
        """
        checks = await health_manager.run_checks()

        # Overall health
        all_healthy = all(status == "healthy" for status in checks.values())
        overall_status = "healthy" if all_healthy else "degraded"

        return HealthResponse(
            status=overall_status,
            version=service_version,
            timestamp=datetime.utcnow().isoformat(),
            checks={
                **checks,
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "platform": platform.system(),
                "architecture": platform.machine()
            }
        )

    logger.info("Health check routes registered")


# Export all
__all__ = [
    "HealthCheck",
    "create_health_routes",
]