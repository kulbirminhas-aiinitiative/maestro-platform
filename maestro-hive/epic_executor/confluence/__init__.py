"""
Confluence Integration for EPIC Executor.

Provides document publishing and template rendering for compliance documents.
"""

from .publisher import ConfluencePublisher, ConfluenceConfig

__all__ = [
    "ConfluencePublisher",
    "ConfluenceConfig",
]
