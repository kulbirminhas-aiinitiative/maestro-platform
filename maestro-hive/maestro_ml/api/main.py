"""
Maestro ML Platform REST API

Main FastAPI application providing unified REST API for MLOps operations.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from datetime import datetime
import mlflow
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from .config import settings
from .v1 import models as models_v1
from .v1 import model_cards as model_cards_v1
from .v1 import features as features_v1
from .schemas.common import HealthResponse, ErrorResponse
from .middleware import RateLimitMiddleware, PrometheusMetricsMiddleware, set_app_info


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    description=settings.app_description,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics middleware (first, to track all requests)
app.add_middleware(PrometheusMetricsMiddleware)

# Rate limiting middleware
# Anonymous: 60 req/min, 1000 req/hour
# Authenticated: 300 req/min (5x), 5000 req/hour (5x)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=60,
    requests_per_hour=1000,
    authenticated_multiplier=5,
    exclude_paths=["/health", "/docs", "/redoc", "/openapi.json", "/", "/metrics"]
)

# Set application info for Prometheus
set_app_info(
    version=settings.app_version,
    environment=getattr(settings, 'environment', 'production')
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_server_error",
            message=str(exc),
            details={"path": request.url.path}
        ).dict()
    )


# Prometheus metrics endpoint
@app.get("/metrics", tags=["system"])
async def metrics():
    """
    Prometheus metrics endpoint

    Exposes metrics in Prometheus format for scraping.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# Health check
@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check():
    """
    Health check endpoint

    Returns service status and dependent service availability.
    """
    services = {}

    # Check MLflow
    try:
        mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
        client = mlflow.tracking.MlflowClient()
        client.search_registered_models(max_results=1)
        services["mlflow"] = "healthy"
    except Exception as e:
        services["mlflow"] = f"unhealthy: {str(e)}"

    # Check PDF service
    try:
        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{settings.pdf_service_url}/health", timeout=2) as resp:
                if resp.status == 200:
                    services["pdf_generator"] = "healthy"
                else:
                    services["pdf_generator"] = f"unhealthy: status {resp.status}"
    except Exception as e:
        services["pdf_generator"] = f"unhealthy: {str(e)}"

    overall_status = "healthy" if all(s == "healthy" for s in services.values()) else "degraded"

    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        timestamp=datetime.utcnow(),
        services=services
    )


# Include routers
app.include_router(models_v1.router, prefix="/api/v1")
app.include_router(model_cards_v1.router, prefix="/api/v1")
app.include_router(features_v1.router, prefix="/api/v1")


# Root endpoint
@app.get("/", tags=["system"])
async def root():
    """Root endpoint with API information"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": settings.app_description,
        "docs": "/docs",
        "health": "/health",
        "api": {
            "v1": "/api/v1"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
