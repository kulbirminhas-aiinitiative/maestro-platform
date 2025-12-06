"""
Capability Registry API Module

JIRA: MD-2066 (part of MD-2042)
"""

from .capability_routes import router, init_registry, create_app

__all__ = ["router", "init_registry", "create_app"]
