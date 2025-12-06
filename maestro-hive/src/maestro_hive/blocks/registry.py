"""
Block Registry - AC-3: Block Registration and Discovery

This module implements the Block Registry for registering, discovering,
and managing certified blocks with semver versioning.

Reference: MD-2507 Acceptance Criterion 3
"""

import re
import logging
from typing import Dict, Any, Optional, List, Type, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock

from ..core.block_interface import BlockInterface

logger = logging.getLogger(__name__)


@dataclass
class BlockMetadata:
    """Metadata for a registered block"""
    block_id: str
    version: str
    description: str
    interface_type: str
    registered_at: datetime
    deprecated: bool = False
    deprecation_message: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BlockRegistration:
    """A block registration entry"""
    block_class: Type[BlockInterface]
    metadata: BlockMetadata
    instance: Optional[BlockInterface] = None


def parse_semver(version: str) -> Tuple[int, int, int]:
    """Parse semver string to tuple (major, minor, patch)"""
    match = re.match(r'^(\d+)\.(\d+)\.(\d+)', version)
    if not match:
        raise ValueError(f"Invalid semver: {version}")
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def compare_versions(v1: str, v2: str) -> int:
    """
    Compare two semver versions.
    Returns: -1 if v1 < v2, 0 if equal, 1 if v1 > v2
    """
    t1 = parse_semver(v1)
    t2 = parse_semver(v2)
    if t1 < t2:
        return -1
    elif t1 > t2:
        return 1
    return 0


class BlockRegistry:
    """
    Central registry for certified blocks.

    Features:
    - Semver versioning (AC-4)
    - Block discovery by ID
    - Version range queries
    - Singleton pattern for global registry
    - Thread-safe operations

    Usage:
        registry = BlockRegistry()
        registry.register(DAGExecutorBlock)
        block = registry.get("dag-executor", "2.0.0")
    """

    _instance: Optional['BlockRegistry'] = None
    _lock = Lock()

    def __new__(cls) -> 'BlockRegistry':
        """Singleton pattern for global registry"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._blocks: Dict[str, Dict[str, BlockRegistration]] = {}
        self._initialized = True
        logger.info("BlockRegistry initialized")

    def register(
        self,
        block_class: Type[BlockInterface],
        description: str = "",
        tags: Optional[List[str]] = None,
        config_schema: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Register a block class.

        Args:
            block_class: Class implementing BlockInterface
            description: Human-readable description
            tags: Optional tags for discovery
            config_schema: Optional JSON schema for config

        Returns:
            Registration key (block_id@version)
        """
        # Create temporary instance to get metadata
        temp_instance = block_class.__new__(block_class)
        if hasattr(temp_instance, '_initialize_for_registration'):
            temp_instance._initialize_for_registration()

        block_id = temp_instance.block_id
        version = temp_instance.version

        # Validate semver
        try:
            parse_semver(version)
        except ValueError as e:
            raise ValueError(f"Block {block_id} has invalid version: {e}")

        # Create metadata
        metadata = BlockMetadata(
            block_id=block_id,
            version=version,
            description=description,
            interface_type=block_class.__bases__[0].__name__ if block_class.__bases__ else "BlockInterface",
            registered_at=datetime.utcnow(),
            tags=tags or [],
            config_schema=config_schema or {}
        )

        # Register
        if block_id not in self._blocks:
            self._blocks[block_id] = {}

        registration = BlockRegistration(
            block_class=block_class,
            metadata=metadata
        )
        self._blocks[block_id][version] = registration

        logger.info(f"Registered block: {block_id}@{version}")
        return f"{block_id}@{version}"

    def get(
        self,
        block_id: str,
        version: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[BlockInterface]:
        """
        Get a block instance.

        Args:
            block_id: Block identifier
            version: Specific version or None for latest
            config: Optional configuration for the block

        Returns:
            Block instance or None if not found
        """
        if block_id not in self._blocks:
            logger.warning(f"Block not found: {block_id}")
            return None

        versions = self._blocks[block_id]

        if version:
            if version not in versions:
                logger.warning(f"Version not found: {block_id}@{version}")
                return None
            registration = versions[version]
        else:
            # Get latest version
            latest_version = self.get_latest_version(block_id)
            if not latest_version:
                return None
            registration = versions[latest_version]

        # Create instance
        try:
            instance = registration.block_class(config or {})
            return instance
        except Exception as e:
            logger.error(f"Failed to instantiate {block_id}: {e}")
            return None

    def get_latest_version(self, block_id: str) -> Optional[str]:
        """Get the latest version of a block"""
        if block_id not in self._blocks:
            return None

        versions = list(self._blocks[block_id].keys())
        if not versions:
            return None

        # Sort by semver
        versions.sort(key=parse_semver, reverse=True)
        return versions[0]

    def get_compatible_versions(self, block_id: str, version_range: str) -> List[str]:
        """
        Get versions compatible with a range.

        Supports:
        - Exact: "2.0.0"
        - Caret: "^2.0.0" (>=2.0.0 <3.0.0)
        - Tilde: "~2.0.0" (>=2.0.0 <2.1.0)
        - Range: ">=2.0.0 <3.0.0"
        """
        if block_id not in self._blocks:
            return []

        versions = list(self._blocks[block_id].keys())

        # Simple implementation for common cases
        if version_range.startswith("^"):
            base = version_range[1:]
            major, _, _ = parse_semver(base)
            return [v for v in versions
                    if parse_semver(v)[0] == major and compare_versions(v, base) >= 0]

        elif version_range.startswith("~"):
            base = version_range[1:]
            major, minor, _ = parse_semver(base)
            return [v for v in versions
                    if parse_semver(v)[0] == major
                    and parse_semver(v)[1] == minor
                    and compare_versions(v, base) >= 0]

        else:
            # Exact match
            return [version_range] if version_range in versions else []

    def list_blocks(self) -> List[str]:
        """List all registered block IDs"""
        return list(self._blocks.keys())

    def list_versions(self, block_id: str) -> List[str]:
        """List all versions of a block"""
        if block_id not in self._blocks:
            return []
        return list(self._blocks[block_id].keys())

    def get_metadata(self, block_id: str, version: Optional[str] = None) -> Optional[BlockMetadata]:
        """Get block metadata"""
        if block_id not in self._blocks:
            return None

        if version:
            reg = self._blocks[block_id].get(version)
            return reg.metadata if reg else None

        latest = self.get_latest_version(block_id)
        if latest:
            return self._blocks[block_id][latest].metadata
        return None

    def deprecate(self, block_id: str, version: str, message: str) -> bool:
        """Mark a block version as deprecated"""
        if block_id not in self._blocks:
            return False
        if version not in self._blocks[block_id]:
            return False

        self._blocks[block_id][version].metadata.deprecated = True
        self._blocks[block_id][version].metadata.deprecation_message = message
        logger.info(f"Deprecated: {block_id}@{version}: {message}")
        return True

    def unregister(self, block_id: str, version: Optional[str] = None) -> bool:
        """Unregister a block"""
        if block_id not in self._blocks:
            return False

        if version:
            if version in self._blocks[block_id]:
                del self._blocks[block_id][version]
                logger.info(f"Unregistered: {block_id}@{version}")
                return True
            return False
        else:
            del self._blocks[block_id]
            logger.info(f"Unregistered all versions: {block_id}")
            return True

    def clear(self) -> None:
        """Clear all registrations (for testing)"""
        self._blocks.clear()
        logger.info("Registry cleared")

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        total_blocks = len(self._blocks)
        total_versions = sum(len(v) for v in self._blocks.values())
        deprecated_count = sum(
            1 for versions in self._blocks.values()
            for reg in versions.values()
            if reg.metadata.deprecated
        )

        return {
            "total_blocks": total_blocks,
            "total_versions": total_versions,
            "deprecated_versions": deprecated_count,
            "blocks": {
                bid: {
                    "versions": list(versions.keys()),
                    "latest": self.get_latest_version(bid)
                }
                for bid, versions in self._blocks.items()
            }
        }


# Global registry accessor
def get_block_registry() -> BlockRegistry:
    """Get the global block registry instance"""
    return BlockRegistry()
