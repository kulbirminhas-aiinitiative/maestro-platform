"""
AI Transparency Module - MD-2792

Provides AI transparency configuration, agent registry management,
disclosure engine, and agent image management for EU AI Act compliance.
"""

from .config import TransparencyConfig, TransparencyLevel, DisclosureFormat
from .agent_registry import AgentRegistry, AgentConfig
from .disclosure_engine import DisclosureEngine, DisclosureResult
from .agent_image_manager import AgentImageManager, ImageConfig

__all__ = [
    # Configuration
    "TransparencyConfig",
    "TransparencyLevel",
    "DisclosureFormat",
    # Agent Registry
    "AgentRegistry",
    "AgentConfig",
    # Disclosure Engine
    "DisclosureEngine",
    "DisclosureResult",
    # Image Management
    "AgentImageManager",
    "ImageConfig",
]

__version__ = "1.0.0"
