"""
Configuration management for ML Pipeline
"""

import os
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings"""

    # API Settings
    API_HOST: str = Field(default="0.0.0.0", env="API_HOST")
    API_PORT: int = Field(default=8000, env="API_PORT")
    API_WORKERS: int = Field(default=4, env="API_WORKERS")

    # Logging
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )

    # Execution Settings
    MAX_PARALLEL_TASKS: int = Field(default=10, env="MAX_PARALLEL_TASKS")
    TASK_TIMEOUT: int = Field(default=3600, env="TASK_TIMEOUT")
    MAX_RETRIES: int = Field(default=3, env="MAX_RETRIES")
    RETRY_DELAY: int = Field(default=60, env="RETRY_DELAY")

    # Storage
    OUTPUT_DIR: str = Field(default="./output", env="OUTPUT_DIR")
    ARTIFACTS_DIR: str = Field(default="./artifacts", env="ARTIFACTS_DIR")
    LOGS_DIR: str = Field(default="./logs", env="LOGS_DIR")

    # Database (optional)
    DATABASE_URL: Optional[str] = Field(default=None, env="DATABASE_URL")

    # Redis (optional for caching/queue)
    REDIS_URL: Optional[str] = Field(default=None, env="REDIS_URL")

    # Monitoring
    ENABLE_METRICS: bool = Field(default=True, env="ENABLE_METRICS")
    METRICS_PORT: int = Field(default=9090, env="METRICS_PORT")

    # Security
    API_KEY: Optional[str] = Field(default=None, env="API_KEY")
    ENABLE_CORS: bool = Field(default=True, env="ENABLE_CORS")

    class Config:
        env_file = ".env"
        case_sensitive = True


def get_settings() -> Settings:
    """Get application settings"""
    return Settings()


# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "INFO"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "detailed",
            "filename": "logs/ml_pipeline.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "level": "DEBUG"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console", "file"]
    },
    "loggers": {
        "ml_pipeline": {
            "level": "DEBUG",
            "handlers": ["console", "file"],
            "propagate": False
        }
    }
}