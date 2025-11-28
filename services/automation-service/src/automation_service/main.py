#!/usr/bin/env python3
"""
Maestro Automation Service (CARS) - Main Application
Continuous Auto-Repair Service for autonomous error detection and healing
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from automation_service.api_endpoints import router
from automation_service.message_handler import MessageHandler
from automation_service.config import settings

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global message handler
message_handler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global message_handler

    # Startup
    logger.info("Starting Maestro Automation Service (CARS)...")
    logger.info(f"Service port: {settings.service_port}")
    logger.info(f"Redis: {settings.redis_host}:{settings.redis_port}")

    # Initialize message handler
    message_handler = MessageHandler(settings)
    await message_handler.start()

    logger.info("CARS started successfully")

    yield

    # Shutdown
    logger.info("Shutting down CARS...")
    if message_handler:
        await message_handler.stop()
    logger.info("CARS shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Maestro Automation Service (CARS)",
    description="Continuous Auto-Repair Service - Autonomous error detection and healing",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "automation-service",
        "version": "1.0.0",
        "message_handler_running": message_handler.is_running if message_handler else False
    }


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint"""
    return {
        "service": "Maestro Automation Service (CARS)",
        "version": "1.0.0",
        "description": "Continuous Auto-Repair Service for autonomous error detection and healing",
        "endpoints": {
            "health": "/health",
            "api": "/api/automation",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }


# Metrics endpoint (for Prometheus)
@app.get("/metrics", tags=["monitoring"])
async def metrics():
    """Metrics endpoint for Prometheus"""
    if message_handler:
        stats = await message_handler.get_statistics()
        return {
            "active_orchestrators": stats.get("active_orchestrators", 0),
            "total_jobs_processed": stats.get("total_jobs_processed", 0),
            "total_errors_detected": stats.get("total_errors_detected", 0),
            "successful_repairs": stats.get("successful_repairs", 0),
            "failed_repairs": stats.get("failed_repairs", 0),
            "success_rate": stats.get("success_rate", 0.0)
        }
    return {"status": "not_initialized"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "automation_service.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=False,
        log_level=settings.log_level.lower()
    )
