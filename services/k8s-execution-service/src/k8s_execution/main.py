#!/usr/bin/env python3
"""
Maestro K8s Execution Service - Main Application
Ephemeral production-parity testing environments
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from k8s_execution.api import router
from k8s_execution.message_handler import MessageHandler
from k8s_execution.config import settings
from k8s_execution.engine import KubernetesExecutionEngine

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
message_handler = None
k8s_engine = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    global message_handler, k8s_engine

    # Startup
    logger.info("Starting Maestro K8s Execution Service...")
    logger.info(f"Service port: {settings.service_port}")
    logger.info(f"K8s in-cluster: {settings.k8s_in_cluster}")

    # Initialize K8s engine
    k8s_engine = KubernetesExecutionEngine()
    logger.info("K8s Execution Engine initialized")

    # Initialize message handler
    message_handler = MessageHandler(settings, k8s_engine)
    await message_handler.start()

    logger.info("K8s Execution Service started successfully")

    yield

    # Shutdown
    logger.info("Shutting down K8s Execution Service...")
    if message_handler:
        await message_handler.stop()

    # Cleanup orphaned environments
    if k8s_engine and k8s_engine.k8s_available:
        await k8s_engine.cleanup_orphaned_environments()

    logger.info("K8s Execution Service shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Maestro K8s Execution Service",
    description="Ephemeral production-parity testing environments on Kubernetes",
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
    k8s_status = "available" if k8s_engine and k8s_engine.k8s_available else "unavailable"
    return {
        "status": "healthy",
        "service": "k8s-execution-service",
        "version": "1.0.0",
        "kubernetes": k8s_status,
        "message_handler_running": message_handler.is_running if message_handler else False,
        "active_environments": len(k8s_engine.execution_contexts) if k8s_engine else 0
    }


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint"""
    return {
        "service": "Maestro K8s Execution Service",
        "version": "1.0.0",
        "description": "Ephemeral production-parity testing environments on Kubernetes",
        "capabilities": [
            "Isolated K8s namespaces per test",
            "Full application stack provisioning",
            "Database and Redis support",
            "Automatic cleanup",
            "Parallel execution",
            "Resource quotas"
        ],
        "endpoints": {
            "health": "/health",
            "api": "/api/v1/k8s-execution",
            "docs": "/docs",
            "openapi": "/openapi.json"
        }
    }


# Metrics endpoint
@app.get("/metrics", tags=["monitoring"])
async def metrics():
    """Metrics endpoint for Prometheus"""
    if k8s_engine:
        return {
            "active_environments": len(k8s_engine.execution_contexts),
            "total_executions": getattr(k8s_engine, 'total_executions', 0),
            "successful_executions": getattr(k8s_engine, 'successful_executions', 0),
            "failed_executions": getattr(k8s_engine, 'failed_executions', 0)
        }
    return {"status": "not_initialized"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "k8s_execution.main:app",
        host="0.0.0.0",
        port=settings.service_port,
        reload=False,
        log_level=settings.log_level.lower()
    )
