"""
Configuration management using Dynaconf.

This module provides centralized configuration management with support for:
- Hierarchical configuration (default -> environment -> env vars)
- Environment-specific configs (development, production)
- Type-safe access to configuration values
"""

from pathlib import Path
from dynaconf import Dynaconf

# Get project root directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent

# Initialize Dynaconf
settings = Dynaconf(
    # Core settings
    envvar_prefix="CLAUDE_TEAM",  # Environment variables prefix
    root_path=PROJECT_ROOT,

    # Configuration files
    settings_files=[
        "config/default.yaml",  # Base configuration
        "config/development.yaml",  # Development overrides
        "config/production.yaml",  # Production overrides
    ],

    # Environment detection
    environments=True,
    env="development",  # Default environment
    env_switcher="ENVIRONMENT",  # Environment variable to switch environments

    # Additional features
    load_dotenv=True,  # Load .env file
    merge_enabled=True,  # Merge configurations

    # Validation
    validators=[],  # Can add validators here
)


def get_database_url() -> str:
    """Get database URL with fallback."""
    return settings.database.url or "postgresql://postgres:postgres@localhost:5432/claude_team_sdk"


def get_redis_url() -> str:
    """Get Redis URL with fallback."""
    return settings.redis.url or "redis://localhost:6379/0"


def get_api_base_url() -> str:
    """Get API base URL with fallback."""
    return settings.api.base_url or "http://localhost:4000"


def is_production() -> bool:
    """Check if running in production environment."""
    return settings.service.environment == "production"


def is_development() -> bool:
    """Check if running in development environment."""
    return settings.service.environment == "development"


# Convenience exports
__all__ = [
    "settings",
    "get_database_url",
    "get_redis_url",
    "get_api_base_url",
    "is_production",
    "is_development",
]
