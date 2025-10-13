"""
Tri-Modal Graph Visualization API - Main Application

FastAPI application integrating all three streams (DDE, BDV, ACC) with convergence layer.

Usage:
    # Development
    uvicorn tri_modal_api_main:app --reload --port 8000

    # Production
    uvicorn tri_modal_api_main:app --host 0.0.0.0 --port 8000 --workers 4

Integration with Maestro Platform:
    - Mount this FastAPI app into existing Maestro API server
    - Or run as standalone service on different port
    - Serves graph visualization data to frontend

Author: Claude Code Implementation
Date: 2025-10-13
Version: 1.0.0
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import Dict, Any
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ============================================================================
# Lifespan Management
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager for startup and shutdown."""
    # Startup
    logger.info("Starting Tri-Modal Graph Visualization API")
    logger.info("Initializing DDE, BDV, ACC, and Convergence APIs")

    # TODO: Initialize database connections if needed
    # TODO: Start background tasks for monitoring

    yield

    # Shutdown
    logger.info("Shutting down Tri-Modal Graph Visualization API")
    # TODO: Close database connections
    # TODO: Stop background tasks


# ============================================================================
# FastAPI Application
# ============================================================================

app = FastAPI(
    title="Tri-Modal Graph Visualization API",
    description="""
    REST and WebSocket API for DDF Tri-Modal Framework visualization.

    Three independent validation streams:
    - **DDE** (Dependency-Driven Execution): "Built Right" - Interface-first execution
    - **BDV** (Behavior-Driven Validation): "Built the Right Thing" - Gherkin scenarios
    - **ACC** (Architectural Conformance Checking): "Built to Last" - Architecture rules

    **Deployment Rule**: Deploy ONLY when DDE ✅ AND BDV ✅ AND ACC ✅
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)


# ============================================================================
# CORS Middleware
# ============================================================================

# Configure CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://localhost:8080",  # Alternative frontend port
        # Add production frontend URLs here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Register API Routers
# ============================================================================

try:
    from dde.api import router as dde_router
    app.include_router(dde_router)
    logger.info("✓ DDE API registered")
except ImportError as e:
    logger.warning(f"⚠ DDE API not available: {e}")

try:
    from bdv.api import router as bdv_router
    app.include_router(bdv_router)
    logger.info("✓ BDV API registered")
except ImportError as e:
    logger.warning(f"⚠ BDV API not available: {e}")

try:
    from acc.api import router as acc_router
    app.include_router(acc_router)
    logger.info("✓ ACC API registered")
except ImportError as e:
    logger.warning(f"⚠ ACC API not available: {e}")

try:
    from tri_audit.api import router as convergence_router
    app.include_router(convergence_router)
    logger.info("✓ Convergence API registered")
except ImportError as e:
    logger.warning(f"⚠ Convergence API not available: {e}")


# ============================================================================
# Root and Health Check Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Tri-Modal Graph Visualization API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/api/docs",
        "streams": {
            "dde": "/api/v1/dde",
            "bdv": "/api/v1/bdv",
            "acc": "/api/v1/acc",
            "convergence": "/api/v1/convergence"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "timestamp": "2025-10-13T00:00:00Z"
    }


@app.get("/api/v1/status")
async def api_status():
    """Detailed API status with all stream availability."""
    status = {
        "api_version": "1.0.0",
        "streams": {}
    }

    # Check DDE availability
    try:
        from dde.api import router as dde_router
        status["streams"]["dde"] = {"available": True, "endpoint": "/api/v1/dde"}
    except ImportError:
        status["streams"]["dde"] = {"available": False, "error": "Module not found"}

    # Check BDV availability
    try:
        from bdv.api import router as bdv_router
        status["streams"]["bdv"] = {"available": True, "endpoint": "/api/v1/bdv"}
    except ImportError:
        status["streams"]["bdv"] = {"available": False, "error": "Module not found"}

    # Check ACC availability
    try:
        from acc.api import router as acc_router
        status["streams"]["acc"] = {"available": True, "endpoint": "/api/v1/acc"}
    except ImportError:
        status["streams"]["acc"] = {"available": False, "error": "Module not found"}

    # Check Convergence availability
    try:
        from tri_audit.api import router as convergence_router
        status["streams"]["convergence"] = {"available": True, "endpoint": "/api/v1/convergence"}
    except ImportError:
        status["streams"]["convergence"] = {"available": False, "error": "Module not found"}

    return status


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Custom HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler for unexpected errors."""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "detail": str(exc)
        }
    )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "tri_modal_api_main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
