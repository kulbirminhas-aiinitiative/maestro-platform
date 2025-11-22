"""
API configuration using Pydantic Settings for validation and environment management.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from pydantic_settings import BaseSettings


class CORSConfig(BaseModel):
    """CORS configuration."""
    allow_origins: List[str] = Field(default=["*"])
    allow_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    allow_headers: List[str] = Field(default=["*"])
    allow_credentials: bool = Field(default=True)
    expose_headers: List[str] = Field(default=[])
    max_age: int = Field(default=600)


class SecurityConfig(BaseModel):
    """Security configuration."""
    jwt_secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=30)
    jwt_refresh_token_expire_days: int = Field(default=7)

    # API Key settings
    api_key_header_name: str = Field(default="X-API-Key")
    api_key_query_param: str = Field(default="api_key")

    # Password hashing
    password_hash_schemes: List[str] = Field(default=["bcrypt"])
    password_hash_deprecated: List[str] = Field(default=["auto"])

    # Security headers
    enable_security_headers: bool = Field(default=True)
    hsts_max_age: int = Field(default=31536000)  # 1 year

    @validator('jwt_secret_key')
    def validate_jwt_secret(cls, v):
        """Ensure JWT secret is strong enough."""
        if len(v) < 32:
            raise ValueError('JWT secret key must be at least 32 characters')
        return v


class RateLimitConfig(BaseModel):
    """Rate limiting configuration."""
    enabled: bool = Field(default=True)
    default_rate: str = Field(default="100/minute")  # Format: "requests/time_window"
    storage_uri: str = Field(default="memory://")  # Redis: "redis://localhost:6379"

    # Per-endpoint rate limits
    endpoint_limits: Dict[str, str] = Field(default_factory=dict)

    # Per-user rate limits (if authentication enabled)
    per_user_limits: Dict[str, str] = Field(default_factory=dict)


class DatabaseConfig(BaseModel):
    """Database configuration."""
    url: Optional[str] = Field(default=None)
    pool_size: int = Field(default=5)
    max_overflow: int = Field(default=10)
    pool_timeout: int = Field(default=30)
    pool_recycle: int = Field(default=3600)
    echo: bool = Field(default=False)


class MonitoringConfig(BaseModel):
    """Monitoring and metrics configuration."""
    enable_metrics: bool = Field(default=True)
    metrics_path: str = Field(default="/metrics")
    enable_tracing: bool = Field(default=True)
    jaeger_endpoint: Optional[str] = Field(default=None)
    prometheus_multiproc_dir: Optional[str] = Field(default=None)


class APIConfig(BaseSettings):
    """
    Main API configuration with environment variable support.

    Environment variables can be used by prefixing with MAESTRO_API_
    Example: MAESTRO_API_TITLE="My API"
    """

    # Basic API information
    title: str = Field(..., description="API title")
    description: str = Field(default="MAESTRO API", description="API description")
    version: str = Field(default="1.0.0", description="API version")
    service_name: str = Field(..., description="Service name for logging/tracing")

    # Server configuration
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=False)
    reload: bool = Field(default=False)
    workers: int = Field(default=1)

    # API settings
    api_prefix: str = Field(default="/api/v1")
    docs_url: str = Field(default="/docs")
    redoc_url: str = Field(default="/redoc")
    openapi_url: str = Field(default="/openapi.json")
    include_admin_routes: bool = Field(default=True)

    # Environment
    environment: str = Field(default="development")

    # Sub-configurations
    cors: CORSConfig = Field(default_factory=CORSConfig)
    security: SecurityConfig
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)

    # Feature flags
    enable_authentication: bool = Field(default=True)
    enable_authorization: bool = Field(default=True)
    enable_rate_limiting: bool = Field(default=True)
    enable_request_logging: bool = Field(default=True)
    enable_metrics: bool = Field(default=True)

    # Timeouts and limits
    request_timeout: int = Field(default=30)
    max_request_size: int = Field(default=10 * 1024 * 1024)  # 10MB

    class Config:
        env_prefix = "MAESTRO_API_"
        env_nested_delimiter = "__"
        case_sensitive = False

    @validator('environment')
    def validate_environment(cls, v):
        """Validate environment values."""
        allowed = {'development', 'staging', 'production', 'test'}
        if v.lower() not in allowed:
            raise ValueError(f'Environment must be one of: {allowed}')
        return v.lower()

    @validator('port')
    def validate_port(cls, v):
        """Validate port range."""
        if not 1 <= v <= 65535:
            raise ValueError('Port must be between 1 and 65535')
        return v

    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"