#!/usr/bin/env python3
"""
Configuration management
"""

# Lazy imports - don't execute at module load time
def get_settings():
    """Lazy-load settings"""
    from maestro_ml.config.settings import get_settings as _get_settings
    return _get_settings()

def get_settings_class():
    """Get Settings class for type hints"""
    from maestro_ml.config.settings import Settings
    return Settings

def get_test_settings_class():
    """Get TestSettings class"""
    from maestro_ml.config.settings import TestSettings
    return TestSettings

__all__ = ["get_settings", "get_settings_class", "get_test_settings_class"]
