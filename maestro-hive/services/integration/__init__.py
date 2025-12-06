"""
Integration Services Package (MD-2104)

Provides abstraction layer for external tools (JIRA, Confluence, Monday.com, etc.)
"""

from .interfaces import ITaskAdapter, IDocumentAdapter
from .adapter_registry import AdapterRegistry, get_adapter_registry

__all__ = [
    'ITaskAdapter',
    'IDocumentAdapter',
    'AdapterRegistry',
    'get_adapter_registry'
]
