"""
Logging configuration module using Pydantic for validation.
"""

from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, field_validator


class LogLevel(str, Enum):
    """Standard log levels following RFC 5424."""
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"
    TRACE = "TRACE"


class LogFormat(str, Enum):
    """Supported log output formats."""
    JSON = "json"          # Production - structured JSON
    CONSOLE = "console"    # Development - human readable
    RICH = "rich"         # Development - colored and formatted


class OpenTelemetryConfig(BaseModel):
    """OpenTelemetry configuration for distributed tracing."""
    enabled: bool = False  # Disabled by default to avoid dependency issues
    service_name: str = Field(default="maestro-service", min_length=1)
    service_version: str = "unknown"
    service_namespace: str = "maestro"
    otlp_endpoint: Optional[str] = None
    headers: Dict[str, str] = Field(default_factory=dict)
    resource_attributes: Dict[str, str] = Field(default_factory=dict)


class LoggingConfig(BaseModel):
    """Enterprise logging configuration with validation."""

    # Basic configuration
    service_name: str = Field(..., min_length=1, description="Service identifier")
    environment: str = Field(default="development", description="Environment (dev/staging/prod)")
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Minimum log level")
    log_format: LogFormat = Field(default=LogFormat.JSON, description="Output format")

    # Output configuration
    enable_console: bool = Field(default=True, description="Log to console/stdout")
    enable_file: bool = Field(default=False, description="Log to file")
    file_path: Optional[str] = Field(default=None, description="Log file path")
    file_rotation: str = Field(default="1 day", description="File rotation interval")
    file_retention: str = Field(default="30 days", description="File retention period")

    # Advanced features
    include_caller_info: bool = Field(default=True, description="Include file/line info")
    include_timestamp: bool = Field(default=True, description="Include timestamps")
    timestamp_format: str = Field(default="iso", description="Timestamp format")

    # Security and compliance
    mask_sensitive_data: bool = Field(default=True, description="Mask sensitive fields")
    sensitive_fields: List[str] = Field(
        default_factory=lambda: ["password", "token", "secret", "key", "auth"],
        description="Fields to mask in logs"
    )

    # Performance
    async_logging: bool = Field(default=False, description="Enable async logging")
    buffer_size: int = Field(default=1000, description="Async buffer size")

    # OpenTelemetry integration
    opentelemetry: OpenTelemetryConfig = Field(default_factory=OpenTelemetryConfig)

    # Custom processors
    custom_processors: List[str] = Field(default_factory=list, description="Custom processor names")

    @field_validator('environment')
    @classmethod
    def validate_environment(cls, v):
        """Validate environment values."""
        allowed = {'development', 'dev', 'staging', 'stage', 'production', 'prod', 'test'}
        if v.lower() not in allowed:
            raise ValueError(f'Environment must be one of: {allowed}')
        return v.lower()

    @field_validator('log_format')
    @classmethod
    def validate_format_for_environment(cls, v, info):
        """Ensure production uses structured logging."""
        env = info.data.get('environment', '').lower()
        if env in ('production', 'prod') and v != LogFormat.JSON:
            raise ValueError('Production environment must use JSON format')
        return v

    @field_validator('file_path')
    @classmethod
    def validate_file_path(cls, v, info):
        """Validate file path when file logging is enabled."""
        if info.data.get('enable_file') and not v:
            raise ValueError('file_path is required when enable_file is True')
        return v

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment in ('production', 'prod')

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment in ('development', 'dev')

    def should_mask_field(self, field_name: str) -> bool:
        """Check if a field should be masked."""
        if not self.mask_sensitive_data:
            return False
        return any(sensitive in field_name.lower() for sensitive in self.sensitive_fields)