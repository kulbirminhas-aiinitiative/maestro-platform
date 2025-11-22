"""
Main MaestroAPI application class with enterprise features built-in.
"""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from typing import Any, Callable, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from maestro_core_logging import get_logger, configure_logging, FastAPILoggingMiddleware

from .config import APIConfig
from .middleware import (
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    MetricsMiddleware,
    RequestSizeMiddleware,
    TimeoutMiddleware
)
from .exceptions import APIException, api_exception_handler
from .health import create_health_routes
from .admin import create_admin_routes


class MaestroAPI:
    """
    Enterprise FastAPI application with built-in middleware, monitoring, and security.

    This class wraps FastAPI with enterprise-grade features commonly used by
    companies like Netflix, Uber, and Microsoft.
    """

    def __init__(self, config: APIConfig):
        """
        Initialize MaestroAPI with configuration.

        Args:
            config: API configuration
        """
        self.config = config
        self.logger = None
        self._app: Optional[FastAPI] = None
        self._limiter: Optional[Limiter] = None

        # Configure logging first
        self._configure_logging()

        # Create FastAPI app
        self._create_app()

        # Setup middleware
        self._setup_middleware()

        # Setup exception handlers
        self._setup_exception_handlers()

        # Setup default routes
        self._setup_default_routes()

    def _configure_logging(self) -> None:
        """Configure structured logging."""
        configure_logging(
            service_name=self.config.service_name,
            environment=self.config.environment,
            log_level="DEBUG" if self.config.debug else "INFO",
            log_format="console" if self.config.is_development() else "json"
        )
        self.logger = get_logger(f"maestro.api.{self.config.service_name}")
        self.logger.info("Logging configured", service=self.config.service_name)

    @asynccontextmanager
    async def lifespan(self, app: FastAPI):
        """Application lifespan management."""
        # Startup
        self.logger.info("Starting API server",
                        host=self.config.host,
                        port=self.config.port,
                        environment=self.config.environment)

        # Setup graceful shutdown
        self._setup_shutdown_handlers()

        yield

        # Shutdown
        self.logger.info("Shutting down API server")

    def _create_app(self) -> None:
        """Create FastAPI application instance."""
        self._app = FastAPI(
            title=self.config.title,
            description=self.config.description,
            version=self.config.version,
            docs_url=self.config.docs_url if not self.config.is_production() else None,
            redoc_url=self.config.redoc_url if not self.config.is_production() else None,
            openapi_url=self.config.openapi_url if not self.config.is_production() else None,
            lifespan=self.lifespan
        )

    def _setup_middleware(self) -> None:
        """Setup middleware stack in correct order."""
        # Security headers (first)
        if self.config.security.enable_security_headers:
            self._app.add_middleware(SecurityHeadersMiddleware, config=self.config.security)

        # Trusted hosts
        if self.config.is_production():
            # In production, restrict to known hosts
            trusted_hosts = ["localhost", "127.0.0.1"]
            self._app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

        # CORS
        self._app.add_middleware(
            CORSMiddleware,
            allow_origins=self.config.cors.allow_origins,
            allow_credentials=self.config.cors.allow_credentials,
            allow_methods=self.config.cors.allow_methods,
            allow_headers=self.config.cors.allow_headers,
            expose_headers=self.config.cors.expose_headers,
            max_age=self.config.cors.max_age,
        )

        # Request size limiting
        self._app.add_middleware(
            RequestSizeMiddleware,
            max_size=self.config.max_request_size
        )

        # Request timeout
        self._app.add_middleware(
            TimeoutMiddleware,
            timeout=self.config.request_timeout
        )

        # Compression
        self._app.add_middleware(GZipMiddleware, minimum_size=1000)

        # Metrics (before request logging)
        if self.config.enable_metrics:
            self._app.add_middleware(MetricsMiddleware, config=self.config.monitoring)

        # Request logging
        if self.config.enable_request_logging:
            self._app.add_middleware(RequestLoggingMiddleware)

        # Logging context disabled temporarily - middleware signature issue
        # TODO: Fix middleware to use proper ASGI signature (scope, receive, send)
        # self._app.add_middleware(FastAPILoggingMiddleware)

        # Rate limiting
        if self.config.enable_rate_limiting and self.config.rate_limit.enabled:
            self._setup_rate_limiting()

    def _setup_rate_limiting(self) -> None:
        """Setup rate limiting with SlowAPI."""
        self._limiter = Limiter(
            key_func=get_remote_address,
            storage_uri=self.config.rate_limit.storage_uri,
            default_limits=[self.config.rate_limit.default_rate]
        )

        # Add rate limit exception handler
        self._app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    def _setup_exception_handlers(self) -> None:
        """Setup custom exception handlers."""
        # Custom API exceptions
        self._app.add_exception_handler(APIException, api_exception_handler)

        # Global exception handler for unhandled exceptions
        @self._app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception):
            self.logger.error(
                "Unhandled exception",
                exception=str(exc),
                path=request.url.path,
                method=request.method,
                exc_info=True
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred"
                }
            )

    def _setup_default_routes(self) -> None:
        """Setup default health and admin routes."""
        # Health check routes
        create_health_routes(self._app, service_version=self.config.version)

        # Admin routes (if enabled)
        if self.config.include_admin_routes and not self.config.is_production():
            create_admin_routes(self._app)

        # Metrics endpoint
        if self.config.enable_metrics:
            @self._app.get(self.config.monitoring.metrics_path)
            async def metrics():
                from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
                return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    def _setup_shutdown_handlers(self) -> None:
        """Setup graceful shutdown handlers."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown")
            # Perform cleanup here if needed
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    # FastAPI delegation methods
    def get(self, path: str, **kwargs):
        """Add GET endpoint."""
        return self._app.get(path, **kwargs)

    def post(self, path: str, **kwargs):
        """Add POST endpoint."""
        return self._app.post(path, **kwargs)

    def put(self, path: str, **kwargs):
        """Add PUT endpoint."""
        return self._app.put(path, **kwargs)

    def delete(self, path: str, **kwargs):
        """Add DELETE endpoint."""
        return self._app.delete(path, **kwargs)

    def patch(self, path: str, **kwargs):
        """Add PATCH endpoint."""
        return self._app.patch(path, **kwargs)

    def include_router(self, router, **kwargs):
        """Include a router."""
        return self._app.include_router(router, **kwargs)

    def add_middleware(self, middleware_class, **kwargs):
        """Add middleware."""
        return self._app.add_middleware(middleware_class, **kwargs)

    def add_exception_handler(self, exc_class, handler):
        """Add exception handler."""
        return self._app.add_exception_handler(exc_class, handler)

    def mount(self, path: str, app, name: str = None):
        """Mount a sub-application."""
        return self._app.mount(path, app, name)

    @property
    def app(self) -> FastAPI:
        """Get the underlying FastAPI application."""
        return self._app

    def run(self, **kwargs) -> None:
        """
        Run the API server.

        Args:
            **kwargs: Additional arguments passed to uvicorn.run()
        """
        # Default uvicorn configuration
        uvicorn_config = {
            "app": self._app,
            "host": self.config.host,
            "port": self.config.port,
            "log_level": "debug" if self.config.debug else "info",
            "reload": self.config.reload and self.config.is_development(),
            "workers": 1 if self.config.reload else self.config.workers,
            "access_log": False,  # We handle logging in middleware
        }

        # Override with any provided kwargs
        uvicorn_config.update(kwargs)

        self.logger.info("Starting uvicorn server", **uvicorn_config)
        uvicorn.run(**uvicorn_config)