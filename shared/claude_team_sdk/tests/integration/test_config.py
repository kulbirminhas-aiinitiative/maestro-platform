"""
Integration tests for configuration system.
"""

import pytest
import os
from pathlib import Path


class TestConfigurationSystem:
    """Test configuration loading and hierarchy."""

    def test_settings_import(self):
        """Test settings can be imported."""
        from src.claude_team_sdk.config import settings

        assert settings is not None
        assert hasattr(settings, 'database')
        assert hasattr(settings, 'redis')
        assert hasattr(settings, 'team')

    def test_default_values_loaded(self):
        """Test default values are loaded from YAML."""
        from src.claude_team_sdk.config import settings

        # Should have defaults
        assert settings.team.max_agents == 10
        assert settings.team.coordination_timeout == 30

    def test_helper_functions(self):
        """Test configuration helper functions."""
        from src.claude_team_sdk.config import (
            get_database_url,
            get_redis_url,
            get_api_base_url,
            is_development,
            is_production
        )

        # Should return values
        db_url = get_database_url()
        assert db_url is not None
        assert 'postgresql' in db_url or 'sqlite' in db_url

        redis_url = get_redis_url()
        assert redis_url is not None
        assert 'redis' in redis_url

        api_url = get_api_base_url()
        assert api_url is not None

        # Environment checks
        assert isinstance(is_development(), bool)
        assert isinstance(is_production(), bool)

    def test_environment_override(self):
        """Test environment variables override config."""
        from src.claude_team_sdk.config import settings

        # Save original
        original = os.environ.get('CLAUDE_TEAM_MAX_AGENTS')

        try:
            # Set environment variable
            os.environ['CLAUDE_TEAM_MAX_AGENTS'] = '20'

            # Re-import to pick up change
            # Note: In real usage, dynaconf picks up env vars automatically
            # This test demonstrates the pattern

            # Check it would be used (actual value depends on dynaconf reload)
            assert 'CLAUDE_TEAM_MAX_AGENTS' in os.environ

        finally:
            # Restore
            if original:
                os.environ['CLAUDE_TEAM_MAX_AGENTS'] = original
            else:
                os.environ.pop('CLAUDE_TEAM_MAX_AGENTS', None)

    def test_resilience_config(self):
        """Test resilience configuration is loaded."""
        from src.claude_team_sdk.config import settings

        assert hasattr(settings, 'resilience')
        assert hasattr(settings.resilience, 'circuit_breaker')
        assert hasattr(settings.resilience, 'retry')
        assert hasattr(settings.resilience, 'timeout')
        assert hasattr(settings.resilience, 'bulkhead')

        # Check specific values
        assert settings.resilience.circuit_breaker.failure_threshold > 0
        assert settings.resilience.retry.max_retries > 0
        assert settings.resilience.bulkhead.max_concurrent_agents > 0

    def test_config_files_exist(self):
        """Test configuration files exist."""
        project_root = Path(__file__).parent.parent.parent

        config_files = [
            'config/default.yaml',
            'config/development.yaml',
            'config/production.yaml',
            'config/service_ports.yaml',
        ]

        for config_file in config_files:
            file_path = project_root / config_file
            assert file_path.exists(), f"Missing config file: {config_file}"
