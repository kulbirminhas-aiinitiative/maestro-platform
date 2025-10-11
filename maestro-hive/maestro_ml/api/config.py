"""
API Configuration Settings
"""

from pydantic import Field
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """API configuration settings"""

    # API Metadata
    app_name: str = "Maestro ML Platform API"
    app_version: str = "1.0.0"
    app_description: str = "Unified REST API for MLOps operations"

    # Server Configuration
    host: str = Field(default="0.0.0.0", env="API_HOST")
    port: int = Field(default=8000, env="API_PORT")
    debug: bool = Field(default=True, env="DEBUG")

    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8000"],
        env="CORS_ORIGINS"
    )

    # MLflow Configuration
    mlflow_tracking_uri: str = Field(
        default="http://localhost:5000",
        env="MLFLOW_TRACKING_URI"
    )
    mlflow_registry_uri: str = Field(
        default="http://localhost:5000",
        env="MLFLOW_REGISTRY_URI"
    )

    # Kubernetes Configuration
    kube_namespace: str = Field(default="ml-platform", env="KUBE_NAMESPACE")
    kube_config_path: str = Field(default="~/.kube/config", env="KUBE_CONFIG_PATH")

    # PDF Service Configuration
    pdf_service_url: str = Field(
        default="http://localhost:9550",
        env="PDF_SERVICE_URL"
    )

    # Authentication
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")

    # API Keys for service-to-service communication
    api_key_enabled: bool = Field(default=False, env="API_KEY_ENABLED")
    api_keys: List[str] = Field(default=[], env="API_KEYS")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_period: int = Field(default=60, env="RATE_LIMIT_PERIOD")  # seconds

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
