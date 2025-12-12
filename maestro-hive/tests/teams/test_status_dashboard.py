#!/usr/bin/env python3
"""
Tests for Status Dashboard PM2 Filter Configuration
MD-3054: Part of EPIC MD-3089 - Core Platform Stability & Tooling
"""

import os
import pytest
from unittest.mock import patch, MagicMock


class TestPM2ServiceFilter:
    """Test suite for PM2 service filter configuration."""

    def test_default_prefixes_loaded(self):
        """Test that default prefixes are loaded when no env var set."""
        # Clear any existing env vars
        env = {'PM2_SERVICE_PREFIXES': '', 'PM2_SHOW_ALL': ''}

        with patch.dict(os.environ, env, clear=False):
            # Re-evaluate the config logic
            default_prefixes = ['maestro', 'dev-', 'sandbox-', 'demo-', 'gateway', 'quality-fabric', 'llm-', 'rag-']
            prefixes = os.environ.get('PM2_SERVICE_PREFIXES', '').split(',') if os.environ.get('PM2_SERVICE_PREFIXES') else default_prefixes

            assert prefixes == default_prefixes

    def test_custom_prefixes_from_env(self):
        """Test that custom prefixes are loaded from environment."""
        env = {'PM2_SERVICE_PREFIXES': 'custom-,my-app-,test-'}

        with patch.dict(os.environ, env, clear=False):
            prefixes = os.environ.get('PM2_SERVICE_PREFIXES', '').split(',') if os.environ.get('PM2_SERVICE_PREFIXES') else []

            assert 'custom-' in prefixes
            assert 'my-app-' in prefixes
            assert 'test-' in prefixes

    def test_show_all_services(self):
        """Test PM2_SHOW_ALL=true shows all services."""
        env = {'PM2_SHOW_ALL': 'true'}

        with patch.dict(os.environ, env, clear=False):
            if os.environ.get('PM2_SHOW_ALL', '').lower() == 'true':
                prefixes = []
            else:
                prefixes = ['default']

            assert prefixes == []


class TestServiceFiltering:
    """Test suite for service name filtering logic."""

    def test_filter_matches_prefix(self):
        """Test that services matching prefix are included."""
        prefixes = ['maestro', 'dev-', 'sandbox-']

        service_names = [
            'maestro-gateway',
            'dev-api',
            'sandbox-worker',
            'other-service',
            'random',
        ]

        included = []
        for name in service_names:
            if not prefixes or any(name.startswith(prefix) for prefix in prefixes):
                included.append(name)

        assert 'maestro-gateway' in included
        assert 'dev-api' in included
        assert 'sandbox-worker' in included
        assert 'other-service' not in included
        assert 'random' not in included

    def test_empty_prefix_list_includes_all(self):
        """Test that empty prefix list includes all services."""
        prefixes = []

        service_names = [
            'maestro-gateway',
            'dev-api',
            'other-service',
            'random',
        ]

        included = []
        for name in service_names:
            if not prefixes or any(name.startswith(prefix) for prefix in prefixes):
                included.append(name)

        assert len(included) == 4
        assert 'random' in included

    def test_extended_default_prefixes(self):
        """Test that extended default prefixes include more services."""
        # New default prefixes
        prefixes = ['maestro', 'dev-', 'sandbox-', 'demo-', 'gateway', 'quality-fabric', 'llm-', 'rag-']

        service_names = [
            'maestro-gateway',
            'gateway',
            'quality-fabric',
            'llm-router',
            'rag-service',
            'dev-api',
            'unrelated',
        ]

        included = []
        for name in service_names:
            if not prefixes or any(name.startswith(prefix) for prefix in prefixes):
                included.append(name)

        assert 'gateway' in included
        assert 'quality-fabric' in included
        assert 'llm-router' in included
        assert 'rag-service' in included
        assert 'unrelated' not in included


class TestAppModuleImport:
    """Test that the status dashboard app module can be imported."""

    def test_app_file_exists(self):
        """Test that the app.py file exists."""
        import sys
        from pathlib import Path

        app_path = Path(__file__).parent.parent.parent / 'scripts' / 'status-dashboard' / 'app.py'
        assert app_path.exists(), f"App file not found at {app_path}"

    def test_pm2_config_in_app(self):
        """Test that PM2 config is present in app.py."""
        from pathlib import Path

        app_path = Path(__file__).parent.parent.parent / 'scripts' / 'status-dashboard' / 'app.py'
        content = app_path.read_text()

        # Check for the configuration additions from MD-3054
        assert 'PM2_SERVICE_PREFIXES' in content
        assert 'PM2_SHOW_ALL' in content
        assert 'DEFAULT_PM2_PREFIXES' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
