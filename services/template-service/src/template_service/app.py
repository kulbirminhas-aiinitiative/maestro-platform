#!/usr/bin/env python3
"""
MAESTRO Central Registry Service
Enterprise service registry and asset management system

This service maintains a central registry of all services, their ports, dependencies,
and assets to prevent conflicts and ensure proper orchestration.
"""

import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

import aiofiles
import asyncpg
import structlog
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator
from prometheus_client import generate_latest
import redis.asyncio as redis
import yaml

# Import template registry components
from .routers.health import router as health_router
from .routers.templates import router as templates_router
from .routers.admin import router as admin_router
from .routers.quality import router as quality_router
from .routers.workflow import router as workflow_router
from .routers.auth import router as auth_router
from .git_manager import GitManager
from .cache_manager import CacheManager
from .seeder import run_seeder
from . import dependencies
from . import metrics as metrics_module

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Initialize metrics (using centralized metrics module to avoid duplication)
metrics_module.get_metrics()

# Configuration
SERVICE_NAME = "central-registry"
SERVICE_VERSION = "1.0.0"
SERVICE_PORT = int(os.getenv("CENTRAL_REGISTRY_PORT", "9600"))
# Get DATABASE_URL and strip SQLAlchemy dialect if present (+asyncpg)
_db_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
if not _db_url:
    _db_url = f"postgresql://{os.getenv('REGISTRY_USER', 'maestro_registry_user')}:{os.getenv('REGISTRY_PASSWORD', 'changeme_registry_password')}@127.0.0.1:5432/{os.getenv('REGISTRY_DB', 'maestro_registry')}"
# Strip SQLAlchemy dialect prefix if present
DATABASE_URL = _db_url.replace("postgresql+asyncpg://", "postgresql://")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Security
security = HTTPBearer()

# Models
class ServiceDependency(BaseModel):
    """Service dependency specification."""
    name: str
    version: str
    type: str  # "database", "service", "external"
    required: bool = True
    health_endpoint: Optional[str] = None

class ServiceAsset(BaseModel):
    """Service asset specification."""
    name: str
    type: str  # "database", "queue", "volume", "config"
    provider: str  # "postgresql", "redis", "rabbitmq", "filesystem"
    config: Dict[str, Any] = {}
    shared: bool = False

class ServiceRegistration(BaseModel):
    """Service registration model."""
    name: str = Field(..., pattern=r'^[a-z][a-z0-9-]*[a-z0-9]$')
    version: str = Field(..., pattern=r'^\d+\.\d+\.\d+$')
    port: int = Field(..., ge=1000, le=65535)
    type: str  # "api-gateway", "core-service", "utility", "monitoring"
    description: str
    health_endpoint: str = "/health"
    metrics_endpoint: str = "/metrics"
    dependencies: List[ServiceDependency] = []
    assets: List[ServiceAsset] = []
    startup_priority: int = Field(default=5, ge=1, le=10)
    environment: str = Field(default="development")
    owner_team: str
    repository_url: Optional[str] = None
    documentation_url: Optional[str] = None
    tags: List[str] = []

    @field_validator('port')
    @classmethod
    def validate_port_range(cls, v):
        """Validate port is in allowed range."""
        # Reserved ranges for different service types
        if 1000 <= v <= 1999:
            raise ValueError("Ports 1000-1999 reserved for system services")
        if 8000 <= v <= 8999:
            # API gateways and core services
            pass
        elif 9000 <= v <= 9999:
            # Application services
            pass
        elif 3000 <= v <= 4999:
            # Frontend and development services
            pass
        else:
            raise ValueError("Port must be in ranges: 3000-4999, 8000-8999, or 9000-9999")
        return v

class ServiceStatus(BaseModel):
    """Service status model."""
    name: str
    status: str  # "healthy", "unhealthy", "starting", "stopping", "unknown"
    last_health_check: datetime
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None

class ConflictCheck(BaseModel):
    """Conflict check result."""
    has_conflicts: bool
    port_conflicts: List[Dict[str, Any]] = []
    asset_conflicts: List[Dict[str, Any]] = []
    dependency_issues: List[Dict[str, Any]] = []

class RegistryStats(BaseModel):
    """Registry statistics."""
    total_services: int
    active_services: int
    port_utilization: Dict[str, int]
    asset_utilization: Dict[str, int]
    dependency_graph_complexity: int
    health_score: float

# Database schema
CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    version VARCHAR(50) NOT NULL,
    port INTEGER NOT NULL,
    type VARCHAR(100) NOT NULL,
    description TEXT,
    health_endpoint VARCHAR(255) DEFAULT '/health',
    metrics_endpoint VARCHAR(255) DEFAULT '/metrics',
    startup_priority INTEGER DEFAULT 5,
    environment VARCHAR(50) DEFAULT 'development',
    owner_team VARCHAR(100) NOT NULL,
    repository_url VARCHAR(500),
    documentation_url VARCHAR(500),
    tags TEXT[], -- Array of tags
    config JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_seen TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS service_dependencies (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(255) REFERENCES services(name),
    dependency_name VARCHAR(255) NOT NULL,
    dependency_version VARCHAR(50) NOT NULL,
    dependency_type VARCHAR(100) NOT NULL,
    required BOOLEAN DEFAULT TRUE,
    health_endpoint VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS service_assets (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(255) REFERENCES services(name),
    asset_name VARCHAR(255) NOT NULL,
    asset_type VARCHAR(100) NOT NULL,
    provider VARCHAR(100) NOT NULL,
    config JSONB,
    shared BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS service_health (
    id SERIAL PRIMARY KEY,
    service_name VARCHAR(255) REFERENCES services(name),
    status VARCHAR(50) NOT NULL,
    response_time_ms FLOAT,
    error_message TEXT,
    checked_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS port_allocations (
    port INTEGER PRIMARY KEY,
    service_name VARCHAR(255) REFERENCES services(name),
    allocation_type VARCHAR(50) DEFAULT 'service',
    allocated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_services_type ON services(type);
CREATE INDEX IF NOT EXISTS idx_services_environment ON services(environment);
CREATE INDEX IF NOT EXISTS idx_port_allocations_service ON port_allocations(service_name);
CREATE INDEX IF NOT EXISTS idx_service_health_name ON service_health(service_name);
"""

# Global database pool and services
db_pool = None
redis_client = None
git_manager = None
cache_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global db_pool, redis_client, git_manager, cache_manager

    logger.info("Starting Central Registry Service", service=SERVICE_NAME, version=SERVICE_VERSION)

    # Initialize database with retry logic
    max_retries = 5
    retry_delay = 2  # seconds

    for attempt in range(max_retries):
        try:
            logger.info(f"Attempting database connection (attempt {attempt + 1}/{max_retries})")
            db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20, timeout=10)
            async with db_pool.acquire() as conn:
                await conn.execute(CREATE_TABLES_SQL)
            logger.info("Database initialized successfully")
            break  # Success, exit retry loop
        except Exception as e:
            logger.warning(
                "Database connection attempt failed",
                attempt=attempt + 1,
                max_retries=max_retries,
                error=str(e)
            )
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Exponential backoff
            else:
                logger.error("Failed to initialize database after all retries", error=str(e))
                raise

    # Initialize Redis
    try:
        redis_client = redis.from_url(REDIS_URL)
        await redis_client.ping()
        logger.info("Redis connected successfully")
    except Exception as e:
        logger.error("Failed to connect to Redis", error=str(e))
        # Redis is optional, continue without it
        redis_client = None

    # Initialize Git Manager
    try:
        git_manager = GitManager(temp_dir="/storage/temp")
        app.state.git_manager = git_manager
        logger.info("Git manager initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize Git manager", error=str(e))
        git_manager = None
        app.state.git_manager = None

    # Initialize Cache Manager
    try:
        if redis_client:
            cache_manager = CacheManager(
                redis_client=redis_client,
                cache_dir="/storage/cache",
                default_ttl_hours=24,
                max_cache_size_gb=10.0
            )
            app.state.cache_manager = cache_manager
            logger.info("Cache manager initialized successfully")
        else:
            logger.warning("Cache manager not initialized - Redis unavailable")
            cache_manager = None
            app.state.cache_manager = None
    except Exception as e:
        logger.error("Failed to initialize Cache manager", error=str(e))
        cache_manager = None
        app.state.cache_manager = None

    # Store db_pool and redis_client in app.state for router access
    app.state.db_pool = db_pool
    app.state.redis_client = redis_client

    # Set global dependencies for routers
    dependencies.set_dependencies(db_pool, redis_client, git_manager, cache_manager)

    # Auto-seed templates if enabled
    if os.getenv("AUTO_SEED_TEMPLATES", "true").lower() == "true":
        try:
            logger.info("Starting template auto-seeding")
            seed_report = await run_seeder(db_pool, git_manager)
            logger.info(
                "template_seeding_complete",
                total=seed_report.total_templates,
                added=seed_report.templates_added,
                updated=seed_report.templates_updated,
                skipped=seed_report.templates_skipped,
                failed=seed_report.templates_failed
            )
            if seed_report.errors:
                for error in seed_report.errors:
                    logger.warning("seed_error_detail", error=error)
        except Exception as e:
            logger.error("auto_seed_failed", error=str(e))
            # Don't fail startup if seeding fails

    # Start background tasks
    asyncio.create_task(health_check_monitor())
    asyncio.create_task(cleanup_stale_services())

    yield

    # Cleanup
    if db_pool:
        await db_pool.close()
    if redis_client:
        await redis_client.close()
    logger.info("Central Registry Service stopped", service=SERVICE_NAME)

# Dependency injection
async def get_db():
    """Get database connection."""
    if not db_pool:
        raise HTTPException(status_code=500, detail="Database not available")
    async with db_pool.acquire() as conn:
        yield conn

async def get_redis():
    """Get Redis connection."""
    return redis_client

async def get_git_manager():
    """Get Git manager."""
    return git_manager

async def get_cache_manager():
    """Get Cache manager."""
    return cache_manager

# FastAPI application
app = FastAPI(
    title="MAESTRO Template Registry & Service Discovery",
    description="""
## MAESTRO Central Registry Service

Enterprise-grade template registry and service discovery platform.

### Features
- **Template Library**: Browse and download 60+ production-ready templates
- **Service Registry**: Centralized service registration and discovery
- **Quality Metrics**: Track template quality, security, and performance scores
- **Search & Filter**: Advanced search with category, language, framework filters
- **API Access**: RESTful API for programmatic access
- **Web UI**: Modern web interface for template discovery

### Getting Started
1. Browse templates at the root URL (/)
2. Use API endpoints under /api/v1/templates
3. Download templates with one click
4. Integrate via API for automation

### Support
- Documentation: /docs
- Health Check: /health
- Metrics: /metrics
    """,
    version=SERVICE_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {"name": "templates", "description": "Template library operations"},
        {"name": "workflow", "description": "Workflow recommendations and approval"},
        {"name": "health", "description": "Health check and monitoring"},
        {"name": "admin", "description": "Administrative operations"},
        {"name": "quality", "description": "Quality metrics and analytics"},
    ],
)

# Middleware
# Allow all origins for template registry access (can be restricted via CORS_ORIGINS env var)
cors_origins = os.getenv("CORS_ORIGINS", "*")
if cors_origins == "*":
    cors_origins_list = ["*"]
else:
    cors_origins_list = cors_origins.split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def metrics_middleware(request, call_next):
    """Add metrics collection."""
    import time
    start_time = time.time()

    response = await call_next(request)

    # Record metrics
    duration = time.time() - start_time
    metrics_module.record_request(
        method=request.method,
        endpoint=request.url.path,
        status_code=response.status_code
    )
    metrics_module.observe_duration(
        method=request.method,
        endpoint=request.url.path,
        duration=duration
    )

    return response

# Include template registry routers
app.include_router(auth_router)  # Authentication router (must be first)
app.include_router(health_router)
app.include_router(templates_router)
app.include_router(workflow_router)
app.include_router(admin_router)
app.include_router(quality_router)

# Mount static files for frontend UI
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Root endpoint serves the frontend UI
@app.get("/")
async def serve_frontend():
    """Serve the template library frontend UI."""
    static_index = Path(__file__).parent / "static" / "index.html"
    if static_index.exists():
        return FileResponse(static_index)
    return {
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "message": "MAESTRO Central Registry Service",
        "documentation": "/docs",
        "template_ui": "/static/index.html (not found - create static/index.html)"
    }

# Core endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return generate_latest()

# Service registration endpoints
@app.post("/api/v1/services/register", response_model=Dict[str, Any])
async def register_service(
    service: ServiceRegistration,
    background_tasks: BackgroundTasks,
    db=Depends(get_db)
):
    """Register a new service or update existing registration."""
    logger.info("Registering service", service_name=service.name, port=service.port)

    # Check for conflicts
    conflicts = await check_conflicts(service, db)
    if conflicts.has_conflicts:
        logger.warning("Service registration conflicts detected",
                      service_name=service.name, conflicts=conflicts.dict())
        raise HTTPException(
            status_code=409,
            detail=f"Registration conflicts: {conflicts.dict()}"
        )

    try:
        # Register service
        await db.execute("""
            INSERT INTO services
            (name, version, port, type, description, health_endpoint, metrics_endpoint,
             startup_priority, environment, owner_team, repository_url, documentation_url, tags, config)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            ON CONFLICT (name) DO UPDATE SET
                version = EXCLUDED.version,
                port = EXCLUDED.port,
                type = EXCLUDED.type,
                description = EXCLUDED.description,
                health_endpoint = EXCLUDED.health_endpoint,
                metrics_endpoint = EXCLUDED.metrics_endpoint,
                startup_priority = EXCLUDED.startup_priority,
                environment = EXCLUDED.environment,
                owner_team = EXCLUDED.owner_team,
                repository_url = EXCLUDED.repository_url,
                documentation_url = EXCLUDED.documentation_url,
                tags = EXCLUDED.tags,
                config = EXCLUDED.config,
                updated_at = NOW()
        """, service.name, service.version, service.port, service.type, service.description,
            service.health_endpoint, service.metrics_endpoint, service.startup_priority,
            service.environment, service.owner_team, service.repository_url,
            service.documentation_url, service.tags, json.dumps({}))

        # Allocate port
        await db.execute("""
            INSERT INTO port_allocations (port, service_name)
            VALUES ($1, $2)
            ON CONFLICT (port) DO UPDATE SET
                service_name = EXCLUDED.service_name,
                allocated_at = NOW()
        """, service.port, service.name)

        # Register dependencies
        await db.execute("DELETE FROM service_dependencies WHERE service_name = $1", service.name)
        for dep in service.dependencies:
            await db.execute("""
                INSERT INTO service_dependencies
                (service_name, dependency_name, dependency_version, dependency_type, required, health_endpoint)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, service.name, dep.name, dep.version, dep.type, dep.required, dep.health_endpoint)

        # Register assets
        await db.execute("DELETE FROM service_assets WHERE service_name = $1", service.name)
        for asset in service.assets:
            await db.execute("""
                INSERT INTO service_assets
                (service_name, asset_name, asset_type, provider, config, shared)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, service.name, asset.name, asset.type, asset.provider,
               json.dumps(asset.config), asset.shared)

        # Update metrics
        metrics_module.set_active_services(await get_active_service_count(db))

        # Schedule background validation
        background_tasks.add_task(validate_service_integration, service.name)

        logger.info("Service registered successfully", service_name=service.name)

        return {
            "status": "registered",
            "service": service.name,
            "port": service.port,
            "registration_time": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error("Failed to register service", service_name=service.name, error=str(e))
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.get("/api/v1/services", response_model=List[Dict[str, Any]])
async def list_services(
    environment: Optional[str] = None,
    type: Optional[str] = None,
    db=Depends(get_db)
):
    """List all registered services with optional filtering."""
    query = "SELECT * FROM services WHERE 1=1"
    params = []

    if environment:
        query += f" AND environment = ${len(params) + 1}"
        params.append(environment)

    if type:
        query += f" AND type = ${len(params) + 1}"
        params.append(type)

    query += " ORDER BY startup_priority, name"

    rows = await db.fetch(query, *params)
    return [dict(row) for row in rows]

@app.get("/api/v1/services/{service_name}", response_model=Dict[str, Any])
async def get_service(service_name: str, db=Depends(get_db)):
    """Get detailed information about a specific service."""
    service = await db.fetchrow("SELECT * FROM services WHERE name = $1", service_name)
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # Get dependencies
    dependencies = await db.fetch(
        "SELECT * FROM service_dependencies WHERE service_name = $1", service_name
    )

    # Get assets
    assets = await db.fetch(
        "SELECT * FROM service_assets WHERE service_name = $1", service_name
    )

    # Get health status
    health = await db.fetchrow("""
        SELECT * FROM service_health
        WHERE service_name = $1
        ORDER BY checked_at DESC LIMIT 1
    """, service_name)

    return {
        "service": dict(service),
        "dependencies": [dict(dep) for dep in dependencies],
        "assets": [dict(asset) for asset in assets],
        "health": dict(health) if health else None
    }

@app.post("/api/v1/services/{service_name}/health")
async def update_service_health(
    service_name: str,
    status: ServiceStatus,
    db=Depends(get_db)
):
    """Update service health status."""
    await db.execute("""
        INSERT INTO service_health (service_name, status, response_time_ms, error_message)
        VALUES ($1, $2, $3, $4)
    """, service_name, status.status, status.response_time_ms, status.error_message)

    # Update last seen
    await db.execute(
        "UPDATE services SET last_seen = NOW() WHERE name = $1", service_name
    )

    return {"status": "updated"}

@app.post("/api/v1/conflicts/check", response_model=ConflictCheck)
async def check_service_conflicts(service: ServiceRegistration, db=Depends(get_db)):
    """Check for potential conflicts before service registration."""
    return await check_conflicts(service, db)

@app.get("/api/v1/ports", response_model=Dict[str, Any])
async def get_port_allocations(db=Depends(get_db)):
    """Get current port allocations."""
    allocations = await db.fetch("""
        SELECT pa.port, pa.service_name, pa.allocated_at, s.type, s.status
        FROM port_allocations pa
        LEFT JOIN services s ON pa.service_name = s.name
        ORDER BY pa.port
    """)

    port_ranges = {
        "system": {"start": 1000, "end": 1999, "allocated": []},
        "frontend": {"start": 3000, "end": 4999, "allocated": []},
        "api_gateway": {"start": 8000, "end": 8999, "allocated": []},
        "services": {"start": 9000, "end": 9999, "allocated": []}
    }

    for alloc in allocations:
        port = alloc['port']
        for range_name, range_info in port_ranges.items():
            if range_info['start'] <= port <= range_info['end']:
                port_ranges[range_name]['allocated'].append(dict(alloc))
                break

    return port_ranges

@app.get("/api/v1/stats", response_model=RegistryStats)
async def get_registry_stats(db=Depends(get_db)):
    """Get registry statistics and health metrics."""
    total_services = await db.fetchval("SELECT COUNT(*) FROM services")
    active_services = await db.fetchval("""
        SELECT COUNT(*) FROM services
        WHERE last_seen > NOW() - INTERVAL '5 minutes'
    """)

    port_stats = await db.fetch("""
        SELECT
            CASE
                WHEN port BETWEEN 1000 AND 1999 THEN 'system'
                WHEN port BETWEEN 3000 AND 4999 THEN 'frontend'
                WHEN port BETWEEN 8000 AND 8999 THEN 'api_gateway'
                WHEN port BETWEEN 9000 AND 9999 THEN 'services'
                ELSE 'other'
            END as range_type,
            COUNT(*) as count
        FROM port_allocations
        GROUP BY range_type
    """)

    asset_stats = await db.fetch("""
        SELECT asset_type, COUNT(*) as count
        FROM service_assets
        GROUP BY asset_type
    """)

    # Calculate health score
    healthy_services = await db.fetchval("""
        SELECT COUNT(DISTINCT service_name) FROM service_health
        WHERE status = 'healthy' AND checked_at > NOW() - INTERVAL '5 minutes'
    """)
    health_score = (healthy_services / max(active_services, 1)) * 100 if active_services > 0 else 0

    return RegistryStats(
        total_services=total_services,
        active_services=active_services,
        port_utilization={row['range_type']: row['count'] for row in port_stats},
        asset_utilization={row['asset_type']: row['count'] for row in asset_stats},
        dependency_graph_complexity=await get_dependency_complexity(db),
        health_score=health_score
    )

# Helper functions
async def check_conflicts(service: ServiceRegistration, db) -> ConflictCheck:
    """Check for various types of conflicts."""
    conflicts = ConflictCheck(has_conflicts=False)

    # Check port conflicts
    existing_port = await db.fetchrow("""
        SELECT service_name FROM port_allocations
        WHERE port = $1 AND service_name != $2
    """, service.port, service.name)

    if existing_port:
        conflicts.has_conflicts = True
        conflicts.port_conflicts.append({
            "port": service.port,
            "existing_service": existing_port['service_name'],
            "conflict_type": "port_already_allocated"
        })
        metrics_module.increment_port_conflicts()

    # Check asset conflicts (non-shared assets)
    for asset in service.assets:
        if not asset.shared:
            existing_asset = await db.fetchrow("""
                SELECT service_name FROM service_assets
                WHERE asset_name = $1 AND asset_type = $2
                AND service_name != $3 AND shared = FALSE
            """, asset.name, asset.type, service.name)

            if existing_asset:
                conflicts.has_conflicts = True
                conflicts.asset_conflicts.append({
                    "asset_name": asset.name,
                    "asset_type": asset.type,
                    "existing_service": existing_asset['service_name'],
                    "conflict_type": "non_shared_asset_conflict"
                })
                metrics_module.increment_asset_violations()

    return conflicts

async def get_active_service_count(db) -> int:
    """Get count of active services."""
    return await db.fetchval("""
        SELECT COUNT(*) FROM services
        WHERE last_seen > NOW() - INTERVAL '5 minutes'
    """)

async def get_dependency_complexity(db) -> int:
    """Calculate dependency graph complexity."""
    return await db.fetchval("SELECT COUNT(*) FROM service_dependencies")

async def validate_service_integration(service_name: str):
    """Background task to validate service integration."""
    # This would perform comprehensive validation
    logger.info("Validating service integration", service_name=service_name)

async def health_check_monitor():
    """Background task to monitor service health."""
    while True:
        try:
            # This would perform health checks on all registered services
            await asyncio.sleep(30)  # Check every 30 seconds
        except Exception as e:
            logger.error("Health check monitor error", error=str(e))

async def cleanup_stale_services():
    """Background task to cleanup stale service registrations."""
    while True:
        try:
            # Cleanup services not seen for 24 hours
            if db_pool:
                async with db_pool.acquire() as conn:
                    await conn.execute("""
                        DELETE FROM services
                        WHERE last_seen < NOW() - INTERVAL '24 hours'
                    """)
            await asyncio.sleep(3600)  # Run every hour
        except Exception as e:
            logger.error("Cleanup task error", error=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,  # Pass app object directly instead of string to avoid re-import
        host="0.0.0.0",
        port=SERVICE_PORT,
        reload=False,  # Disable reload to avoid duplicate metrics on restart
        log_config=None,
    )