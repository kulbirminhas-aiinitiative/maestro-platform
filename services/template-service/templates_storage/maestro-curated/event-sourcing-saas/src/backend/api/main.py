"""FastAPI application entry point."""
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import asyncpg
from typing import AsyncGenerator
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app
import time

from .dependencies import get_command_bus, get_query_bus, get_tenant_context
from .routers import commands, queries, tenants
from ..infrastructure.multi_tenancy.tenant_context import TenantContextMiddleware
from ..infrastructure.database.connection_pool import create_connection_pool
from ..infrastructure.resilience import circuit_breaker_manager

# Prometheus metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)
http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)
circuit_breaker_state = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=half_open, 2=open)',
    ['service']
)
db_pool_size = Gauge('db_pool_size', 'Database connection pool size')
db_pool_available = Gauge('db_pool_available', 'Available database connections')


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Lifespan context manager for startup and shutdown."""
    # Startup
    app.state.db_pool = await create_connection_pool()

    yield

    # Shutdown
    await app.state.db_pool.close()


app = FastAPI(
    title="Event Sourcing SaaS API",
    description="Multi-tenant SaaS with Event Sourcing and CQRS",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tenant context middleware
app.middleware("http")(TenantContextMiddleware())


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "Internal server error",
            "error": str(exc)
        }
    )


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect HTTP metrics."""
    start_time = time.time()

    response = await call_next(request)

    # Record metrics
    duration = time.time() - start_time
    http_requests_total.labels(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code
    ).inc()
    http_request_duration_seconds.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)

    return response


@app.get("/health")
async def health_check(request: Request):
    """Health check endpoint with dependency checks."""
    health_status = {"status": "healthy", "dependencies": {}}

    # Check database
    try:
        async with request.app.state.db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        health_status["dependencies"]["database"] = "healthy"
    except Exception as e:
        health_status["dependencies"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "degraded"

    # Check circuit breaker states
    breaker_states = circuit_breaker_manager.get_all_states()
    health_status["circuit_breakers"] = breaker_states

    return health_status


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Event Sourcing SaaS API",
        "version": "1.0.0",
        "status": "running"
    }


# Mount Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include routers
app.include_router(commands.router, prefix="/api/v1/commands", tags=["Commands"])
app.include_router(queries.router, prefix="/api/v1/queries", tags=["Queries"])
app.include_router(tenants.router, prefix="/api/v1/tenants", tags=["Tenants"])