"""
Adapter Registry Service (MD-2112)

Provides dynamic routing to the correct adapter based on configuration.
Supports multiple task and document management systems through a unified API.
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Type, Union

from .interfaces import (
    ITaskAdapter,
    IDocumentAdapter,
    AdapterResult
)

logger = logging.getLogger(__name__)


@dataclass
class AdapterConfig:
    """Configuration for an adapter"""
    adapter_type: str  # 'task' or 'document'
    adapter_name: str  # e.g., 'jira', 'confluence'
    enabled: bool = True
    is_default: bool = False
    config: Dict[str, Any] = field(default_factory=dict)


class AdapterRegistry:
    """
    Central registry for task and document adapters.

    Features:
    - Register/unregister adapters dynamically
    - Route requests to appropriate adapter
    - Support default adapters per type
    - Health monitoring for all adapters

    Usage:
        registry = AdapterRegistry()
        registry.register_task_adapter(JiraAdapter())
        registry.register_document_adapter(ConfluenceAdapter())

        # Get specific adapter
        jira = registry.get_task_adapter('jira')

        # Get default adapter
        default_task = registry.get_default_task_adapter()
    """

    def __init__(self):
        """Initialize the adapter registry"""
        self._task_adapters: Dict[str, ITaskAdapter] = {}
        self._document_adapters: Dict[str, IDocumentAdapter] = {}
        self._default_task_adapter: Optional[str] = None
        self._default_document_adapter: Optional[str] = None
        self._configs: Dict[str, AdapterConfig] = {}

        logger.info("AdapterRegistry initialized")

    def register_task_adapter(
        self,
        adapter: ITaskAdapter,
        is_default: bool = False,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a task adapter.

        Args:
            adapter: Task adapter instance
            is_default: Set as default task adapter
            config: Optional configuration
        """
        name = adapter.adapter_name
        self._task_adapters[name] = adapter
        self._configs[f"task:{name}"] = AdapterConfig(
            adapter_type='task',
            adapter_name=name,
            is_default=is_default,
            config=config or {}
        )

        if is_default or self._default_task_adapter is None:
            self._default_task_adapter = name

        logger.info(f"Task adapter registered: {name} (default={is_default})")

    def register_document_adapter(
        self,
        adapter: IDocumentAdapter,
        is_default: bool = False,
        config: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Register a document adapter.

        Args:
            adapter: Document adapter instance
            is_default: Set as default document adapter
            config: Optional configuration
        """
        name = adapter.adapter_name
        self._document_adapters[name] = adapter
        self._configs[f"document:{name}"] = AdapterConfig(
            adapter_type='document',
            adapter_name=name,
            is_default=is_default,
            config=config or {}
        )

        if is_default or self._default_document_adapter is None:
            self._default_document_adapter = name

        logger.info(f"Document adapter registered: {name} (default={is_default})")

    def unregister_task_adapter(self, name: str) -> bool:
        """
        Unregister a task adapter.

        Args:
            name: Adapter name

        Returns:
            True if adapter was removed
        """
        if name in self._task_adapters:
            del self._task_adapters[name]
            del self._configs[f"task:{name}"]

            if self._default_task_adapter == name:
                self._default_task_adapter = (
                    next(iter(self._task_adapters.keys()), None)
                )

            logger.info(f"Task adapter unregistered: {name}")
            return True
        return False

    def unregister_document_adapter(self, name: str) -> bool:
        """
        Unregister a document adapter.

        Args:
            name: Adapter name

        Returns:
            True if adapter was removed
        """
        if name in self._document_adapters:
            del self._document_adapters[name]
            del self._configs[f"document:{name}"]

            if self._default_document_adapter == name:
                self._default_document_adapter = (
                    next(iter(self._document_adapters.keys()), None)
                )

            logger.info(f"Document adapter unregistered: {name}")
            return True
        return False

    def get_task_adapter(self, name: str) -> Optional[ITaskAdapter]:
        """
        Get a task adapter by name.

        Args:
            name: Adapter name

        Returns:
            Task adapter or None
        """
        return self._task_adapters.get(name)

    def get_document_adapter(self, name: str) -> Optional[IDocumentAdapter]:
        """
        Get a document adapter by name.

        Args:
            name: Adapter name

        Returns:
            Document adapter or None
        """
        return self._document_adapters.get(name)

    def get_default_task_adapter(self) -> Optional[ITaskAdapter]:
        """Get the default task adapter"""
        if self._default_task_adapter:
            return self._task_adapters.get(self._default_task_adapter)
        return None

    def get_default_document_adapter(self) -> Optional[IDocumentAdapter]:
        """Get the default document adapter"""
        if self._default_document_adapter:
            return self._document_adapters.get(self._default_document_adapter)
        return None

    def set_default_task_adapter(self, name: str) -> bool:
        """
        Set the default task adapter.

        Args:
            name: Adapter name

        Returns:
            True if set successfully
        """
        if name in self._task_adapters:
            self._default_task_adapter = name
            logger.info(f"Default task adapter set: {name}")
            return True
        return False

    def set_default_document_adapter(self, name: str) -> bool:
        """
        Set the default document adapter.

        Args:
            name: Adapter name

        Returns:
            True if set successfully
        """
        if name in self._document_adapters:
            self._default_document_adapter = name
            logger.info(f"Default document adapter set: {name}")
            return True
        return False

    def list_task_adapters(self) -> List[str]:
        """List all registered task adapter names"""
        return list(self._task_adapters.keys())

    def list_document_adapters(self) -> List[str]:
        """List all registered document adapter names"""
        return list(self._document_adapters.keys())

    def get_config(self, adapter_type: str, name: str) -> Optional[AdapterConfig]:
        """
        Get adapter configuration.

        Args:
            adapter_type: 'task' or 'document'
            name: Adapter name

        Returns:
            Adapter configuration or None
        """
        return self._configs.get(f"{adapter_type}:{name}")

    async def health_check_all(self) -> Dict[str, AdapterResult]:
        """
        Run health check on all adapters.

        Returns:
            Dict mapping adapter names to health results
        """
        results = {}

        for name, adapter in self._task_adapters.items():
            try:
                results[f"task:{name}"] = await adapter.health_check()
            except Exception as e:
                results[f"task:{name}"] = AdapterResult(
                    success=False,
                    error=str(e)
                )

        for name, adapter in self._document_adapters.items():
            try:
                results[f"document:{name}"] = await adapter.health_check()
            except Exception as e:
                results[f"document:{name}"] = AdapterResult(
                    success=False,
                    error=str(e)
                )

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        return {
            'task_adapters': {
                'count': len(self._task_adapters),
                'names': list(self._task_adapters.keys()),
                'default': self._default_task_adapter
            },
            'document_adapters': {
                'count': len(self._document_adapters),
                'names': list(self._document_adapters.keys()),
                'default': self._default_document_adapter
            }
        }


# Singleton instance
_registry: Optional[AdapterRegistry] = None


def get_adapter_registry() -> AdapterRegistry:
    """Get the default adapter registry instance"""
    global _registry
    if _registry is None:
        _registry = AdapterRegistry()
    return _registry


def reset_adapter_registry() -> None:
    """Reset the adapter registry (for testing)"""
    global _registry
    _registry = None
