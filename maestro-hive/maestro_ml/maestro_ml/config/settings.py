#!/usr/bin/env python3
"""
Configuration settings for Maestro ML Platform

Manages environment-based configuration for database, storage, and services.
"""

import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Pydantic v2 configuration - allow extra fields in .env for docker-compose
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,  # Allow case-insensitive matching
        extra='ignore'  # Ignore extra fields like MINIO_ROOT_USER, GRAFANA_ADMIN_USER
    )

    # Application
    APP_NAME: str = "Maestro ML Platform"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Database
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://maestro:maestro@localhost:5432/maestro_ml"
    )
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Object Storage (S3/MinIO)
    S3_ENDPOINT: Optional[str] = os.getenv("S3_ENDPOINT")  # For MinIO
    S3_BUCKET: str = os.getenv("S3_BUCKET", "maestro-artifacts")
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")

    # MLflow
    MLFLOW_TRACKING_URI: str = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    MLFLOW_ARTIFACT_ROOT: str = os.getenv("MLFLOW_ARTIFACT_ROOT", "s3://maestro-mlflow")

    # Feature Store (Feast)
    FEAST_REPO_PATH: str = os.getenv("FEAST_REPO_PATH", "./feast_repo")

    # API
    API_V1_PREFIX: str = "/api/v1"
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    CORS_ORIGINS: str = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://localhost:8000,https://localhost:8443"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string to list"""
        if isinstance(self.CORS_ORIGINS, str):
            return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
        return self.CORS_ORIGINS if self.CORS_ORIGINS else []

    # Authentication
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-jwt-secret-key")
    JWT_REFRESH_SECRET_KEY: str = os.getenv("JWT_REFRESH_SECRET_KEY", "your-jwt-refresh-secret-key")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ALGORITHM: str = "HS256"  # Deprecated, use JWT_ALGORITHM
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24)))  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # Encryption
    ENCRYPTION_KEY: str = os.getenv("ENCRYPTION_KEY", "your-encryption-key")
    API_SECRET_KEY: str = os.getenv("API_SECRET_KEY", "your-api-secret-key")

    # HTTPS
    API_HTTPS_PORT: int = int(os.getenv("API_HTTPS_PORT", "8443"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv("LOG_FORMAT", "json")

    # Feature Flags
    ENABLE_MULTI_TENANCY: bool = os.getenv("ENABLE_MULTI_TENANCY", "true").lower() == "true"
    ENABLE_AUDIT_LOGGING: bool = os.getenv("ENABLE_AUDIT_LOGGING", "true").lower() == "true"
    ENABLE_RATE_LIMITING: bool = os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true"

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
    RATE_LIMIT_BURST: int = int(os.getenv("RATE_LIMIT_BURST", "10"))

    # Database (PostgreSQL specific)
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "maestro")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "maestro")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "maestro_ml")

    # Redis specific
    REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")

    # Monitoring
    PROMETHEUS_PORT: int = int(os.getenv("PROMETHEUS_PORT", "9090"))
    GRAFANA_URL: str = os.getenv("GRAFANA_URL", "http://localhost:3001")

    # Meta-Model
    META_MODEL_PATH: str = os.getenv("META_MODEL_PATH", "./models/meta_model.pkl")
    META_MODEL_RETRAIN_DAYS: int = int(os.getenv("META_MODEL_RETRAIN_DAYS", "7"))

    # Metrics Collection
    METRICS_COLLECTION_INTERVAL: int = int(os.getenv("METRICS_COLLECTION_INTERVAL", "300"))  # 5 minutes


# Lazy-loaded settings instance (singleton pattern)
_settings_instance: Optional[Settings] = None


# Database testing configuration
class TestSettings(Settings):
    """Settings for testing"""
    DATABASE_URL: str = "sqlite+aiosqlite:///:memory:"
    ENVIRONMENT: str = "testing"
    DEBUG: bool = True


def get_settings() -> Settings:
    """Get settings based on environment (lazy-loaded singleton)"""
    global _settings_instance
    
    if _settings_instance is None:
        env = os.getenv("ENVIRONMENT", "development")
        if env == "testing":
            _settings_instance = TestSettings()
        else:
            _settings_instance = Settings()
    
    return _settings_instance
