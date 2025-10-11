#!/usr/bin/env python3
"""
Maestro ML Platform - Self-aware ML development platform with meta-learning

A platform that learns from past ML projects to optimize team composition,
artifact reuse, and development velocity.
"""

__version__ = "0.1.0"
__author__ = "Maestro ML Team"

# Lazy import to avoid circular dependencies and import errors during testing
def get_settings():
    """Get application settings (lazy loaded)"""
    from maestro_ml.config.settings import get_settings as _get_settings
    return _get_settings()

__all__ = ["get_settings", "__version__"]
