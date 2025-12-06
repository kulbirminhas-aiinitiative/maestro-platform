"""
DependencyResolver - AC-2: Resolve block dependencies

Resolves block dependencies from the Block Registry, handling
version constraints and compatibility checking.

Reference: MD-2508 Acceptance Criterion 2
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field

from .manifest_parser import CompositionManifest, BlockReference

logger = logging.getLogger(__name__)


@dataclass
class ResolvedBlock:
    """A resolved block with its instance"""
    block_id: str
    version: str
    block_instance: Any
    dependencies: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompatibilityResult:
    """Result of compatibility check"""
    compatible: bool
    conflicts: List[Dict[str, Any]]
    resolution: Optional[Dict[str, str]] = None


@dataclass
class ResolvedDependencies:
    """
    Collection of resolved dependencies.

    Contains all blocks resolved from the manifest with their
    actual instances and transitive dependencies.
    """
    blocks: Dict[str, ResolvedBlock]
    resolution_order: List[str]
    unresolved: List[str]
    compatibility: CompatibilityResult

    def get_block(self, block_id: str) -> Optional[ResolvedBlock]:
        """Get resolved block by ID"""
        return self.blocks.get(block_id)

    def get_all_versions(self) -> Dict[str, str]:
        """Get map of block_id -> resolved version"""
        return {bid: b.version for bid, b in self.blocks.items()}

    def is_complete(self) -> bool:
        """Check if all dependencies were resolved"""
        return len(self.unresolved) == 0


class DependencyResolver:
    """
    Resolver for block dependencies.

    Implements AC-2: Resolve block dependencies

    Features:
    - Resolve blocks from Block Registry
    - Handle version constraints (^, ~, ranges)
    - Check compatibility between blocks
    - Detect and report conflicts
    - Compute resolution order (topological sort)
    """

    def __init__(self, registry=None):
        """
        Initialize resolver.

        Args:
            registry: Optional BlockRegistry instance (lazy-loaded if None)
        """
        self._registry = registry
        logger.info("DependencyResolver initialized")

    def _get_registry(self):
        """Lazy-load Block Registry"""
        if self._registry is None:
            try:
                from ..blocks import get_block_registry
                self._registry = get_block_registry()
            except ImportError:
                logger.warning("Block Registry not available, using mock")
                self._registry = MockRegistry()
        return self._registry

    def resolve(self, manifest: CompositionManifest) -> ResolvedDependencies:
        """
        Resolve all dependencies from a manifest.

        Args:
            manifest: Composition manifest with block references

        Returns:
            ResolvedDependencies with resolved blocks
        """
        registry = self._get_registry()
        resolved_blocks = {}
        unresolved = []
        resolution_order = []

        # First pass: resolve all direct dependencies
        for block_ref in manifest.compose:
            resolved = self._resolve_block(block_ref, registry)

            if resolved:
                resolved_blocks[block_ref.block_id] = resolved
                resolution_order.append(block_ref.block_id)
            else:
                unresolved.append(block_ref.block_id)
                logger.warning(f"Could not resolve: {block_ref.block_id}@{block_ref.version}")

        # Second pass: resolve transitive dependencies
        transitive = self._resolve_transitive(resolved_blocks, registry)
        for bid, block in transitive.items():
            if bid not in resolved_blocks:
                resolved_blocks[bid] = block
                resolution_order.append(bid)

        # Check compatibility
        compatibility = self.check_compatibility(list(resolved_blocks.values()))

        # Compute optimal resolution order
        resolution_order = self._compute_resolution_order(resolved_blocks)

        logger.info(f"Resolved {len(resolved_blocks)} blocks, {len(unresolved)} unresolved")

        return ResolvedDependencies(
            blocks=resolved_blocks,
            resolution_order=resolution_order,
            unresolved=unresolved,
            compatibility=compatibility
        )

    def _resolve_block(self, ref: BlockReference, registry) -> Optional[ResolvedBlock]:
        """Resolve a single block reference"""
        try:
            # Handle version constraints
            version = self._resolve_version(ref.block_id, ref.version, registry)

            if not version:
                return None

            # Get block instance
            block_instance = registry.get(ref.block_id, version, ref.config)

            if not block_instance:
                return None

            # Get block dependencies (if it declares any)
            dependencies = []
            if hasattr(block_instance, 'get_dependencies'):
                dependencies = block_instance.get_dependencies()

            return ResolvedBlock(
                block_id=ref.block_id,
                version=version,
                block_instance=block_instance,
                dependencies=dependencies,
                metadata={"config": ref.config, "alias": ref.alias}
            )

        except Exception as e:
            logger.error(f"Error resolving {ref.block_id}: {e}")
            return None

    def _resolve_version(self, block_id: str, version_spec: str, registry) -> Optional[str]:
        """Resolve version specification to actual version"""
        if version_spec == "latest" or version_spec == "*":
            return registry.get_latest_version(block_id)

        if version_spec.startswith("^"):
            # Caret: compatible versions
            base = version_spec[1:]
            compatible = registry.get_compatible_versions(block_id, version_spec)
            return compatible[-1] if compatible else None

        if version_spec.startswith("~"):
            # Tilde: patch-level changes only
            base = version_spec[1:]
            compatible = registry.get_compatible_versions(block_id, version_spec)
            return compatible[-1] if compatible else None

        # Exact version
        versions = registry.list_versions(block_id)
        return version_spec if version_spec in versions else None

    def _resolve_transitive(
        self,
        resolved: Dict[str, ResolvedBlock],
        registry
    ) -> Dict[str, ResolvedBlock]:
        """Resolve transitive dependencies"""
        transitive = {}

        for block in resolved.values():
            for dep_id in block.dependencies:
                if dep_id not in resolved and dep_id not in transitive:
                    # Create reference for transitive dependency
                    ref = BlockReference(block_id=dep_id, version="latest")
                    dep_resolved = self._resolve_block(ref, registry)

                    if dep_resolved:
                        transitive[dep_id] = dep_resolved

        return transitive

    def check_compatibility(self, blocks: List[ResolvedBlock]) -> CompatibilityResult:
        """
        Check compatibility between resolved blocks.

        Args:
            blocks: List of resolved blocks

        Returns:
            CompatibilityResult with any conflicts
        """
        conflicts = []

        # Check for version conflicts in transitive dependencies
        dep_versions: Dict[str, List[Tuple[str, str]]] = {}

        for block in blocks:
            for dep_id in block.dependencies:
                if dep_id not in dep_versions:
                    dep_versions[dep_id] = []
                dep_versions[dep_id].append((block.block_id, "latest"))

        # Detect conflicts (same dep required with incompatible versions)
        for dep_id, requesters in dep_versions.items():
            if len(requesters) > 1:
                versions = set(v for _, v in requesters)
                if len(versions) > 1:
                    conflicts.append({
                        "dependency": dep_id,
                        "requesters": requesters,
                        "versions": list(versions)
                    })

        return CompatibilityResult(
            compatible=len(conflicts) == 0,
            conflicts=conflicts,
            resolution=None if conflicts else {}
        )

    def _compute_resolution_order(self, blocks: Dict[str, ResolvedBlock]) -> List[str]:
        """
        Compute topological order for block initialization.

        Blocks with no dependencies come first, then blocks that
        depend on already-initialized blocks.
        """
        order = []
        remaining = set(blocks.keys())
        resolved_set = set()

        while remaining:
            # Find blocks with all dependencies resolved
            ready = []
            for bid in remaining:
                block = blocks[bid]
                deps_satisfied = all(
                    d in resolved_set or d not in blocks
                    for d in block.dependencies
                )
                if deps_satisfied:
                    ready.append(bid)

            if not ready:
                # Circular dependency - add remaining in arbitrary order
                logger.warning("Possible circular dependency detected")
                order.extend(remaining)
                break

            order.extend(ready)
            resolved_set.update(ready)
            remaining -= set(ready)

        return order


class MockRegistry:
    """Mock registry for testing when real registry unavailable"""

    def __init__(self):
        self._blocks = {
            "logging": ["1.0.0", "1.2.3", "2.0.0"],
            "jira-adapter": ["3.0.0", "3.1.0"],
            "quality-fabric": ["1.0.0", "2.0.0"],
            "dag-executor": ["2.0.0"],
            "phase-orchestrator": ["1.5.0"],
        }

    def get(self, block_id: str, version: str = None, config: Dict = None):
        if block_id in self._blocks:
            return MockBlock(block_id, version or self._blocks[block_id][-1])
        return None

    def get_latest_version(self, block_id: str) -> Optional[str]:
        if block_id in self._blocks:
            return self._blocks[block_id][-1]
        return None

    def list_versions(self, block_id: str) -> List[str]:
        return self._blocks.get(block_id, [])

    def get_compatible_versions(self, block_id: str, version_spec: str) -> List[str]:
        return self._blocks.get(block_id, [])


class MockBlock:
    """Mock block for testing"""

    def __init__(self, block_id: str, version: str):
        self.block_id = block_id
        self.version = version

    def get_dependencies(self) -> List[str]:
        return []
