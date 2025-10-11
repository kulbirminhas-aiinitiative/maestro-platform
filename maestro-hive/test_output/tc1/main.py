"""
FastAPI Health Check Endpoint

This module provides a simple health check endpoint for monitoring service availability.
"""

from fastapi import FastAPI
from datetime import datetime
from typing import Dict

app = FastAPI(
    title="Health Check API",
    description="Simple health check endpoint for service monitoring",
    version="1.0.0"
)


@app.get("/health", response_model=Dict[str, str])
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.

    Returns:
        dict: JSON object containing status and current timestamp

    Example:
        {
            "status": "ok",
            "timestamp": "2025-10-09T12:34:56.789012"
        }
    """
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat()
    }
