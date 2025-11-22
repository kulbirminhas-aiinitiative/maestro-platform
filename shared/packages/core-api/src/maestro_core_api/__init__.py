"""
MAESTRO Core API Library

Enterprise-grade FastAPI framework with built-in security, monitoring,
rate limiting, and standardized patterns used by companies like Microsoft, Netflix, and Uber.

Usage:
    from maestro_core_api import MaestroAPI, APIConfig

    # Create application with enterprise defaults
    config = APIConfig(
        title="My Service API",
        service_name="my-service",
        version="1.0.0"
    )

    app = MaestroAPI(config)

    @app.get("/health")
    async def health_check():
        return {"status": "healthy"}

    if __name__ == "__main__":
        app.run()
"""

from .app import MaestroAPI
from .config import APIConfig, CORSConfig, SecurityConfig, RateLimitConfig
from .middleware import (
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
    MetricsMiddleware
)
from .auth import JWTAuth, APIKeyAuth
from .exceptions import (
    APIException,
    ValidationException,
    AuthenticationException,
    AuthorizationException,
    RateLimitException
)
from .responses import (
    APIResponse,
    ErrorResponse,
    SuccessResponse,
    PaginatedResponse
)
from .dependencies import (
    get_current_user,
    require_auth,
    require_role,
    get_db_session
)
from .health import create_health_routes, HealthCheck
from .admin import create_admin_routes, get_system_stats
# UTCP support - optional dependency
try:
    from .utcp_adapter import UTCPManualGenerator, UTCPToolExecutor
    from .utcp_registry import UTCPServiceRegistry, ServiceInfo
    _UTCP_AVAILABLE = True
except ImportError:
    _UTCP_AVAILABLE = False
    # Placeholder classes for when UTCP is not available
    UTCPManualGenerator = None
    UTCPToolExecutor = None
    UTCPServiceRegistry = None
    ServiceInfo = None

__version__ = "1.0.0"
__all__ = [
    # Core classes
    "MaestroAPI",
    "APIConfig",
    "CORSConfig",
    "SecurityConfig",
    "RateLimitConfig",

    # Middleware
    "RequestLoggingMiddleware",
    "SecurityHeadersMiddleware",
    "MetricsMiddleware",

    # Authentication
    "JWTAuth",
    "APIKeyAuth",

    # Exceptions
    "APIException",
    "ValidationException",
    "AuthenticationException",
    "AuthorizationException",
    "RateLimitException",

    # Responses
    "APIResponse",
    "ErrorResponse",
    "SuccessResponse",
    "PaginatedResponse",

    # Dependencies
    "get_current_user",
    "require_auth",
    "require_role",
    "get_db_session",

    # Health & Admin
    "create_health_routes",
    "HealthCheck",
    "create_admin_routes",
    "get_system_stats",

    # UTCP Support
    "UTCPManualGenerator",
    "UTCPToolExecutor",
    "UTCPServiceRegistry",
    "ServiceInfo",
]