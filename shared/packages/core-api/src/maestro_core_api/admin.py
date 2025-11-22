"""
Admin and monitoring endpoints for MAESTRO APIs.

Provides administrative endpoints for monitoring, metrics, and service information.
"""

import asyncio
import gc
import os
import psutil
import sys
from datetime import datetime
from typing import Dict, Any
from fastapi import FastAPI, Depends, HTTPException, status
from maestro_core_logging import get_logger

def _get_logger():
    try:
        from maestro_core_logging import get_logger
        return get_logger(__name__)
    except:
        import logging
        return logging.getLogger(__name__)

logger = type("LazyLogger", (), {"__getattr__": lambda self, name: getattr(_get_logger(), name)})()


def get_system_stats() -> Dict[str, Any]:
    """
    Get current system statistics.

    Returns:
        Dictionary with CPU, memory, and disk statistics
    """
    try:
        process = psutil.Process(os.getpid())

        return {
            "cpu": {
                "percent": psutil.cpu_percent(interval=0.1),
                "count": psutil.cpu_count(),
                "process_percent": process.cpu_percent()
            },
            "memory": {
                "total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "available_gb": round(psutil.virtual_memory().available / (1024**3), 2),
                "percent": psutil.virtual_memory().percent,
                "process_mb": round(process.memory_info().rss / (1024**2), 2)
            },
            "disk": {
                "total_gb": round(psutil.disk_usage('/').total / (1024**3), 2),
                "free_gb": round(psutil.disk_usage('/').free / (1024**3), 2),
                "percent": psutil.disk_usage('/').percent
            }
        }
    except Exception as e:
        logger.error(f"Failed to get system stats: {e}")
        return {}


def get_process_info() -> Dict[str, Any]:
    """
    Get current process information.

    Returns:
        Dictionary with process details
    """
    try:
        process = psutil.Process(os.getpid())

        return {
            "pid": process.pid,
            "name": process.name(),
            "status": process.status(),
            "create_time": datetime.fromtimestamp(process.create_time()).isoformat(),
            "num_threads": process.num_threads(),
            "open_files": len(process.open_files()),
            "connections": len(process.connections())
        }
    except Exception as e:
        logger.error(f"Failed to get process info: {e}")
        return {"error": str(e)}


def create_admin_routes(
    app: FastAPI,
    require_auth: Any = None
) -> None:
    """
    Add administrative endpoints to FastAPI application.

    Args:
        app: FastAPI application instance
        require_auth: Optional authentication dependency

    Adds endpoints:
        - GET /admin/stats - System statistics
        - GET /admin/info - Service information
        - POST /admin/gc - Trigger garbage collection
        - GET /admin/config - Configuration (sanitized)
    """

    # Use auth dependency if provided, otherwise no auth
    auth_dep = [Depends(require_auth)] if require_auth else []

    @app.get(
        "/admin/stats",
        tags=["Admin"],
        summary="System Statistics",
        description="Get current system resource usage",
        dependencies=auth_dep
    )
    async def get_stats():
        """Get system and process statistics."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "system": get_system_stats(),
            "process": get_process_info(),
            "python": {
                "version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "implementation": sys.implementation.name,
                "gc_stats": {
                    "collections": gc.get_count(),
                    "threshold": gc.get_threshold()
                }
            }
        }

    @app.get(
        "/admin/info",
        tags=["Admin"],
        summary="Service Information",
        description="Get service configuration and runtime info",
        dependencies=auth_dep
    )
    async def get_info():
        """Get service information."""
        return {
            "service": getattr(app, 'title', 'Unknown Service'),
            "version": getattr(app, 'version', '1.0.0'),
            "environment": os.getenv("ENVIRONMENT", "development"),
            "uptime": get_uptime(),
            "endpoints": len(app.routes),
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        }

    @app.post(
        "/admin/gc",
        tags=["Admin"],
        summary="Trigger Garbage Collection",
        description="Manually trigger Python garbage collection",
        dependencies=auth_dep
    )
    async def trigger_gc():
        """Trigger garbage collection."""
        try:
            collected = gc.collect()
            logger.info(f"Garbage collection completed", objects_collected=collected)
            return {
                "success": True,
                "objects_collected": collected,
                "gc_stats": {
                    "collections": gc.get_count(),
                    "threshold": gc.get_threshold()
                }
            }
        except Exception as e:
            logger.error(f"Garbage collection failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Garbage collection failed: {str(e)}"
            )

    @app.get(
        "/admin/config",
        tags=["Admin"],
        summary="Configuration",
        description="Get sanitized service configuration",
        dependencies=auth_dep
    )
    async def get_config():
        """Get sanitized configuration (secrets removed)."""
        # Get environment variables (sanitized)
        env_vars = {
            k: "***REDACTED***" if any(secret in k.lower() for secret in ["secret", "key", "password", "token"]) else v
            for k, v in os.environ.items()
            if k.startswith("MAESTRO_")
        }

        return {
            "environment_variables": env_vars,
            "settings": {
                "debug": getattr(app, 'debug', False),
                "title": getattr(app, 'title', 'Unknown'),
                "version": getattr(app, 'version', '1.0.0')
            }
        }

    logger.info("Admin routes registered")


def get_uptime() -> str:
    """Get process uptime as human-readable string."""
    try:
        process = psutil.Process(os.getpid())
        create_time = datetime.fromtimestamp(process.create_time())
        uptime = datetime.now() - create_time

        days = uptime.days
        hours, remainder = divmod(uptime.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{seconds}s")

        return " ".join(parts)
    except Exception:
        return "unknown"


# Export all
__all__ = [
    "create_admin_routes",
    "get_system_stats",
    "get_process_info",
    "get_uptime",
]