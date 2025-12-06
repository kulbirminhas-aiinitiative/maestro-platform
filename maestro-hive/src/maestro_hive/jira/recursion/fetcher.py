"""
Sub-EPIC Fetcher for JIRA Recursion.

Implements AC-1: Recursively fetch all Sub-EPICs under parent EPIC.

Core component that orchestrates recursive EPIC hierarchy fetching
using depth-first search with cycle detection.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Protocol, Set

from .models import (
    AcceptanceCriterion,
    EpicNode,
    RecursionConfig,
    RecursionResult,
)
from .detector import CircularReferenceDetector, DepthLimitDetector
from .resolver import EpicLinkResolver, ResolvedLink
from .extractor import AcceptanceCriteriaExtractor

logger = logging.getLogger(__name__)


class JiraClientProtocol(Protocol):
    """Protocol for JIRA client implementations."""

    async def get_issue(self, issue_key: str, fields: Optional[List[str]] = None) -> Any:
        """Get issue details."""
        ...

    async def search_issues(
        self, jql: str, max_results: int = 50, fields: Optional[List[str]] = None
    ) -> Any:
        """Search issues using JQL."""
        ...


class MaxDepthExceededError(Exception):
    """Raised when recursion depth exceeds configured maximum."""

    def __init__(self, epic_key: str, depth: int, max_depth: int):
        self.epic_key = epic_key
        self.depth = depth
        self.max_depth = max_depth
        super().__init__(
            f"Max depth {max_depth} exceeded at {epic_key} (depth: {depth})"
        )


class SubEpicFetcher:
    """
    Recursively fetches Sub-EPICs from JIRA hierarchy.

    Uses depth-first search with cycle detection to traverse
    the complete EPIC hierarchy. Supports configuration of
    max depth, parallel fetching, and caching.

    Attributes:
        jira_client: JIRA API client for fetching data
        config: Recursion configuration
        resolver: EPIC link resolver
        detector: Circular reference detector
        depth_detector: Depth limit detector
        extractor: Acceptance criteria extractor
    """

    def __init__(
        self,
        jira_client: JiraClientProtocol,
        config: Optional[RecursionConfig] = None,
    ):
        """
        Initialize the fetcher.

        Args:
            jira_client: Authenticated JIRA API client
            config: Optional recursion configuration
        """
        self.jira_client = jira_client
        self.config = config or RecursionConfig()

        # Validate config
        errors = self.config.validate()
        if errors:
            raise ValueError(f"Invalid config: {', '.join(errors)}")

        # Initialize components
        self.resolver = EpicLinkResolver(
            jira_client,
            epic_link_field_id=self.config.epic_link_field_id,
            use_parent_field=self.config.include_parent_field,
            use_epic_link=self.config.include_epic_link,
        )
        self.detector = CircularReferenceDetector(
            mode=self.config.circular_ref_handling
        )
        self.depth_detector = DepthLimitDetector(
            max_depth=self.config.max_depth
        )
        self.extractor = AcceptanceCriteriaExtractor()

        # Statistics
        self._api_calls = 0
        self._cache_hits = 0
        self._fetch_errors: List[str] = []

        # Node cache
        self._node_cache: Dict[str, EpicNode] = {}

    async def fetch_hierarchy(
        self,
        epic_key: str,
        on_node_fetched: Optional[Callable[[EpicNode], None]] = None,
    ) -> RecursionResult:
        """
        Fetch complete Sub-EPIC hierarchy.

        Performs depth-first traversal of the EPIC hierarchy,
        extracting acceptance criteria at each node.

        Args:
            epic_key: Root EPIC key (e.g., 'MD-2493')
            on_node_fetched: Optional callback for each fetched node

        Returns:
            RecursionResult with complete hierarchy tree

        Raises:
            RuntimeError: If API request fails for root EPIC
            MaxDepthExceededError: If recursion exceeds max_depth
        """
        start_time = time.time()

        # Reset state
        self.detector.reset()
        self.depth_detector.reset()
        self._api_calls = 0
        self._fetch_errors = []

        try:
            # Fetch root node
            root = await self._fetch_node(epic_key, depth=0)

            if root is None:
                return RecursionResult(
                    root=EpicNode(key=epic_key, summary="Failed to fetch"),
                    errors=[f"Failed to fetch root EPIC {epic_key}"],
                    duration_ms=(time.time() - start_time) * 1000,
                )

            if on_node_fetched:
                on_node_fetched(root)

            # Recursively fetch children
            await self._fetch_children_recursive(root, on_node_fetched)

            # Extract acceptance criteria from hierarchy
            all_acs = self.extractor.extract_from_hierarchy(root)

            duration_ms = (time.time() - start_time) * 1000

            result = RecursionResult(
                root=root,
                total_epics=root.count_epics(),
                total_acs=len(all_acs),
                circular_refs_detected=self.detector.circular_references,
                max_depth_reached=self.depth_detector.max_depth_reached,
                duration_ms=duration_ms,
                errors=self._fetch_errors,
            )

            logger.info(
                f"Fetched hierarchy for {epic_key}: "
                f"{result.total_epics} EPICs, {result.total_acs} ACs, "
                f"{len(result.circular_refs_detected)} circular refs, "
                f"{duration_ms:.0f}ms"
            )

            return result

        except Exception as e:
            logger.error(f"Error fetching hierarchy for {epic_key}: {e}")
            return RecursionResult(
                root=EpicNode(key=epic_key, summary="Error"),
                errors=[str(e)],
                duration_ms=(time.time() - start_time) * 1000,
            )

    async def _fetch_node(
        self,
        epic_key: str,
        depth: int = 0,
    ) -> Optional[EpicNode]:
        """
        Fetch a single EPIC node.

        Args:
            epic_key: EPIC key to fetch
            depth: Current depth in hierarchy

        Returns:
            EpicNode if successful, None on error
        """
        # Check cache
        if epic_key in self._node_cache:
            self._cache_hits += 1
            cached = self._node_cache[epic_key]
            cached.depth = depth
            return cached

        # Apply rate limiting delay if configured
        if self.config.request_delay_ms > 0:
            await asyncio.sleep(self.config.request_delay_ms / 1000)

        try:
            self._api_calls += 1

            result = await self.jira_client.get_issue(
                epic_key,
                fields=["summary", "description", "status", "labels", "parent"]
            )

            if not result.success:
                error_msg = f"Failed to fetch {epic_key}: {result.error}"
                logger.warning(error_msg)
                self._fetch_errors.append(error_msg)
                return None

            data = result.data

            # Extract description text
            description = data.get("description", "")
            if isinstance(description, dict):
                # Handle ADF format
                description = self._extract_text_from_adf(description)

            # Create node
            node = EpicNode(
                key=epic_key,
                summary=data.get("summary", ""),
                description=description,
                depth=depth,
                labels=data.get("labels", []),
                status=data.get("status", "Unknown"),
                parent_key=data.get("parent"),
            )

            # Extract acceptance criteria for this node
            node.acceptance_criteria = self.extractor.extract(
                description,
                source_epic=epic_key
            )

            # Cache the node
            self._node_cache[epic_key] = node

            return node

        except Exception as e:
            error_msg = f"Exception fetching {epic_key}: {e}"
            logger.warning(error_msg)
            self._fetch_errors.append(error_msg)
            return None

    async def _fetch_children_recursive(
        self,
        node: EpicNode,
        on_node_fetched: Optional[Callable[[EpicNode], None]] = None,
    ) -> None:
        """
        Recursively fetch children for a node.

        Uses depth-first traversal with cycle detection.

        Args:
            node: Parent node to fetch children for
            on_node_fetched: Optional callback for each fetched node
        """
        # Check circular reference
        if not self.detector.enter(node.key):
            logger.debug(f"Skipping {node.key} - circular reference detected")
            return

        # Check depth limit
        if not self.depth_detector.enter(node.key):
            logger.debug(f"Skipping children of {node.key} - max depth reached")
            self.detector.exit(node.key)
            return

        try:
            # Get children via resolver
            children_links = await self.resolver.get_children(node.key)

            if not children_links:
                return

            # Fetch children in parallel (limited concurrency)
            semaphore = asyncio.Semaphore(self.config.parallel_fetches)

            async def fetch_child(link: ResolvedLink) -> Optional[EpicNode]:
                async with semaphore:
                    # Skip if already visited
                    if self.detector.check(link.key):
                        return None

                    child_node = await self._fetch_node(
                        link.key,
                        depth=node.depth + 1
                    )

                    if child_node:
                        if on_node_fetched:
                            on_node_fetched(child_node)

                        # Recursively fetch grandchildren
                        await self._fetch_children_recursive(
                            child_node,
                            on_node_fetched
                        )

                    return child_node

            # Execute parallel fetches
            child_results = await asyncio.gather(
                *[fetch_child(link) for link in children_links],
                return_exceptions=True
            )

            # Add successful children to node
            for result in child_results:
                if isinstance(result, EpicNode):
                    node.add_child(result)
                elif isinstance(result, Exception):
                    self._fetch_errors.append(str(result))

        finally:
            self.depth_detector.exit()
            self.detector.exit(node.key)

    def _extract_text_from_adf(self, adf: Any) -> str:
        """Extract plain text from JIRA ADF (Atlassian Document Format)."""
        if not adf:
            return ""
        if isinstance(adf, str):
            return adf

        def extract_recursive(node: Any) -> str:
            if isinstance(node, dict):
                if node.get("type") == "text":
                    return node.get("text", "")
                content = node.get("content", [])
                return " ".join(extract_recursive(c) for c in content)
            elif isinstance(node, list):
                return " ".join(extract_recursive(c) for c in node)
            return ""

        return extract_recursive(adf).strip()

    def extract_all_acs(self, root: EpicNode) -> List[AcceptanceCriterion]:
        """
        Extract all acceptance criteria from hierarchy.

        Convenience method that delegates to the extractor.

        Args:
            root: Root EpicNode from fetch_hierarchy()

        Returns:
            List of all ACs with source EPIC attribution
        """
        return self.extractor.extract_from_hierarchy(root)

    def get_statistics(self) -> Dict[str, Any]:
        """Get fetching statistics."""
        return {
            "api_calls": self._api_calls,
            "cache_hits": self._cache_hits,
            "cached_nodes": len(self._node_cache),
            "fetch_errors": len(self._fetch_errors),
            "circular_refs_detected": len(self.detector.circular_references),
            "max_depth_reached": self.depth_detector.max_depth_reached,
            "resolver_cache": self.resolver.get_cache_stats(),
        }

    def clear_cache(self) -> None:
        """Clear all caches."""
        self._node_cache.clear()
        self.resolver.clear_cache()
        self.detector.clear_all()

    def to_dict(self) -> Dict[str, Any]:
        """Convert fetcher state to dictionary."""
        return {
            "config": self.config.to_dict(),
            "statistics": self.get_statistics(),
            "detector": self.detector.to_dict(),
            "depth_detector": self.depth_detector.to_dict(),
            "resolver": self.resolver.to_dict(),
            "extractor": self.extractor.to_dict(),
        }


async def fetch_subepics(
    jira_client: JiraClientProtocol,
    epic_key: str,
    max_depth: int = 10,
    circular_ref_handling: str = "warn",
) -> RecursionResult:
    """
    Convenience function to fetch Sub-EPIC hierarchy.

    Args:
        jira_client: JIRA API client
        epic_key: Root EPIC key
        max_depth: Maximum recursion depth
        circular_ref_handling: How to handle circular refs

    Returns:
        RecursionResult with complete hierarchy
    """
    config = RecursionConfig(
        max_depth=max_depth,
        circular_ref_handling=circular_ref_handling,
    )
    fetcher = SubEpicFetcher(jira_client, config)
    return await fetcher.fetch_hierarchy(epic_key)
