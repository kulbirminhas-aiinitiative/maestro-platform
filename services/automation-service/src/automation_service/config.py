#!/usr/bin/env python3
"""
Maestro Automation Service - Configuration
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Service Configuration
    service_name: str = "automation-service"
    service_port: int = 8003
    environment: str = "development"

    # Redis Configuration
    redis_host: str = "maestro-redis"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0

    # Redis Streams Configuration
    stream_automation_jobs: str = "maestro:streams:automation:jobs"
    stream_test_healing: str = "maestro:streams:automation:healing"
    stream_error_monitoring: str = "maestro:streams:automation:errors"
    stream_validation: str = "maestro:streams:automation:validation"
    stream_results: str = "maestro:streams:automation:results"

    # Consumer Groups
    consumer_group_automation: str = "maestro-automation-workers"
    consumer_group_healing: str = "maestro-healing-workers"
    consumer_group_monitoring: str = "maestro-monitoring-workers"
    consumer_name: str = "worker-1"

    # PostgreSQL Configuration
    postgres_host: str = "maestro-postgres"
    postgres_port: int = 5432
    postgres_db: str = "maestro_automation"
    postgres_user: str = "maestro"
    postgres_password: str = "change_me"

    # Healing Configuration
    default_confidence_threshold: float = 0.75
    max_concurrent_repairs: int = 3
    healing_timeout: int = 300  # seconds
    max_healing_attempts: int = 3

    # Monitoring Configuration
    error_monitor_interval: int = 30  # seconds
    health_check_interval: int = 60  # seconds

    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"  # json or text

    # API Configuration
    api_prefix: str = "/api/automation"
    enable_cors: bool = True
    cors_origins: list = ["*"]

    # PyPI Configuration (for package dependencies)
    pypi_index_url: str = "http://maestro-nexus:8081/repository/pypi-group/simple"
    pypi_trusted_host: str = "maestro-nexus"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()


def get_redis_url() -> str:
    """Get Redis connection URL"""
    if settings.redis_password:
        return f"redis://:{settings.redis_password}@{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"
    return f"redis://{settings.redis_host}:{settings.redis_port}/{settings.redis_db}"


def get_postgres_url() -> str:
    """Get PostgreSQL connection URL"""
    return (
        f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


def get_stream_names() -> dict:
    """Get all stream names"""
    return {
        "automation_jobs": settings.stream_automation_jobs,
        "test_healing": settings.stream_test_healing,
        "error_monitoring": settings.stream_error_monitoring,
        "validation": settings.stream_validation,
        "results": settings.stream_results
    }


def get_consumer_groups() -> dict:
    """Get all consumer groups"""
    return {
        "automation_workers": settings.consumer_group_automation,
        "healing_workers": settings.consumer_group_healing,
        "monitoring_workers": settings.consumer_group_monitoring
    }
