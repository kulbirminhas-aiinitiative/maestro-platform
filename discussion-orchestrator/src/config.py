"""
Configuration management for the Discussion Orchestrator service.

Loads environment variables and provides configuration settings for the service.
"""

import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Service Configuration
    service_name: str = "discussion-orchestrator"
    service_port: int = 5000
    log_level: str = "INFO"
    environment: str = "development"

    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    redis_db: int = 0
    redis_max_connections: int = 10
    redis_socket_timeout: int = 5
    redis_socket_connect_timeout: int = 5

    # Execution Platform Integration
    execution_platform_url: str = "http://localhost:8000"
    execution_platform_timeout: int = 30

    # CORS Configuration
    cors_origins: str = "http://localhost:4300,http://localhost:3000"

    # Session Configuration
    session_timeout: int = 3600  # 1 hour in seconds
    max_message_length: int = 10000
    max_participants: int = 20

    # WebSocket Configuration
    websocket_ping_interval: int = 30
    websocket_ping_timeout: int = 10

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    def get_redis_config(self) -> dict:
        """Get Redis connection configuration."""
        return {
            "url": self.redis_url,
            "db": self.redis_db,
            "max_connections": self.redis_max_connections,
            "socket_timeout": self.redis_socket_timeout,
            "socket_connect_timeout": self.redis_socket_connect_timeout,
            "decode_responses": True
        }

    def configure_logging(self) -> None:
        """Configure application logging."""
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper()),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        logger.info(f"Logging configured with level: {self.log_level}")


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings: Application settings singleton
    """
    return Settings()


# Redis key patterns
class RedisKeys:
    """Redis key patterns for discussion data."""

    @staticmethod
    def discussion_session(discussion_id: str) -> str:
        """Key for discussion session metadata."""
        return f"discussion:{discussion_id}:session"

    @staticmethod
    def discussion_messages(discussion_id: str) -> str:
        """Key for discussion messages list."""
        return f"discussion:{discussion_id}:messages"

    @staticmethod
    def discussion_state(discussion_id: str) -> str:
        """Key for discussion state."""
        return f"discussion:{discussion_id}:state"

    @staticmethod
    def discussion_participants(discussion_id: str) -> str:
        """Key for discussion participants."""
        return f"discussion:{discussion_id}:participants"

    @staticmethod
    def discussion_lock(discussion_id: str) -> str:
        """Key for discussion lock."""
        return f"discussion:{discussion_id}:lock"

    @staticmethod
    def active_discussions() -> str:
        """Key for set of active discussion IDs."""
        return "discussions:active"

    @staticmethod
    def user_discussions(user_id: str) -> str:
        """Key for user's discussion list."""
        return f"user:{user_id}:discussions"


# Export settings instance
settings = get_settings()
