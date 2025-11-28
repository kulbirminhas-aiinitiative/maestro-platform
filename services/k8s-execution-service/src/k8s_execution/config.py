#!/usr/bin/env python3
"""
Maestro K8s Execution Service - Configuration
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings"""

    # Service Configuration
    service_name: str = "k8s-execution-service"
    service_port: int = 8004
    environment: str = "development"

    # Kubernetes Configuration
    k8s_in_cluster: bool = False
    k8s_namespace_prefix: str = "quality-fabric"
    k8s_ttl_minutes: int = 60
    k8s_cleanup_interval_minutes: int = 10

    # Resource Limits
    default_cpu_limit: str = "1000m"
    default_memory_limit: str = "1Gi"
    default_cpu_request: str = "100m"
    default_memory_request: str = "256Mi"

    # Execution Configuration
    default_timeout_minutes: int = 30
    max_concurrent_environments: int = 10
    max_retries: int = 3

    # Redis Configuration
    redis_host: str = "maestro-redis"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0

    # Redis Streams Configuration
    stream_k8s_jobs: str = "maestro:streams:k8s:jobs"
    stream_k8s_results: str = "maestro:streams:k8s:results"
    stream_k8s_status: str = "maestro:streams:k8s:status"

    # Consumer Groups
    consumer_group_k8s: str = "maestro-k8s-workers"
    consumer_name: str = "worker-1"

    # PostgreSQL Configuration (optional)
    postgres_host: str = "maestro-postgres"
    postgres_port: int = 5432
    postgres_db: str = "maestro_k8s"
    postgres_user: str = "maestro"
    postgres_password: str = "change_me"

    # Database Images
    postgres_image: str = "postgres:15-alpine"
    mysql_image: str = "mysql:8.0"
    redis_image: str = "redis:7-alpine"
    mongodb_image: str = "mongo:7"

    # Logging Configuration
    log_level: str = "INFO"
    log_format: str = "json"

    # API Configuration
    api_prefix: str = "/api/v1/k8s-execution"
    enable_cors: bool = True
    cors_origins: list = ["*"]

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


def get_namespace_name(execution_id: str) -> str:
    """Get K8s namespace name for execution"""
    return f"{settings.k8s_namespace_prefix}-{execution_id}"


def get_stream_names() -> dict:
    """Get all stream names"""
    return {
        "k8s_jobs": settings.stream_k8s_jobs,
        "k8s_results": settings.stream_k8s_results,
        "k8s_status": settings.stream_k8s_status
    }


def get_resource_limits() -> dict:
    """Get default resource limits"""
    return {
        "cpu_limit": settings.default_cpu_limit,
        "memory_limit": settings.default_memory_limit,
        "cpu_request": settings.default_cpu_request,
        "memory_request": settings.default_memory_request
    }
