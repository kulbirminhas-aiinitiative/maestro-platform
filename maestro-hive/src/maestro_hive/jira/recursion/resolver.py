"""
EPIC Link Resolver for JIRA Sub-EPIC Recursion.

Implements AC-4: Support JIRA Epic Link and parent fields.

Handles resolution of EPIC relationships through multiple JIRA fields:
- Epic Link custom field (customfield_10014 by default)
- Parent field (standard hierarchical relationship)
- Issue links (relates to, blocks, etc.)
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Set, Tuple

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


@dataclass
class ResolvedLink:
    """
    A resolved EPIC link.

    Attributes:
        key: EPIC key
        summary: EPIC summary
        link_type: How the link was found (parent, epic_link, issue_link)
        direction: "child" if this EPIC is a child of the source
        issue_type: JIRA issue type name
    """
    key: str
    summary: str = ""
    link_type: str = "unknown"  # parent, epic_link, issue_link
    direction: str = "child"  # child, parent, related
    issue_type: str = ""


class EpicLinkResolver:
    """
    Resolves EPIC relationships via Epic Link and parent fields.

    Supports multiple methods of finding EPIC children:
    1. Parent field - Standard JIRA hierarchical relationship
    2. Epic Link field - Custom field linking issues to EPICs
    3. Issue Links - "parent of", "is parent of" relationships

    Attributes:
        jira_client: JIRA API client
        epic_link_field_id: Custom field ID for Epic Link
        use_parent_field: Whether to check parent field
        use_epic_link: Whether to check Epic Link field
        use_issue_links: Whether to check issue links
        epic_issue_types: Issue type names considered as EPICs
    """

    def __init__(
        self,
        jira_client: JiraClientProtocol,
        epic_link_field_id: str = "customfield_10014",
        use_parent_field: bool = True,
        use_epic_link: bool = True,
        use_issue_links: bool = True,
        epic_issue_types: Optional[List[str]] = None,
    ):
        """
        Initialize the resolver.

        Args:
            jira_client: JIRA API client
            epic_link_field_id: Custom field ID for Epic Link
            use_parent_field: Check parent field for children
            use_epic_link: Check Epic Link field for children
            use_issue_links: Check issue links for children
            epic_issue_types: Issue types to consider as EPICs
        """
        self.jira_client = jira_client
        self.epic_link_field_id = epic_link_field_id
        self.use_parent_field = use_parent_field
        self.use_epic_link = use_epic_link
        self.use_issue_links = use_issue_links
        self.epic_issue_types = epic_issue_types or ["Epic", "Initiative", "Sub-task"]

        # Cache for resolved links
        self._cache: Dict[str, List[ResolvedLink]] = {}

    async def get_children(self, epic_key: str) -> List[ResolvedLink]:
        """
        Get all child EPIC keys for a given EPIC.

        Checks multiple relationship types and deduplicates results.

        Args:
            epic_key: Source EPIC key

        Returns:
            List of resolved child links
        """
        # Check cache
        if epic_key in self._cache:
            return self._cache[epic_key]

        children: List[ResolvedLink] = []
        seen_keys: Set[str] = set()

        # Method 1: Query for issues with parent = epic_key
        if self.use_parent_field:
            parent_children = await self._get_children_by_parent(epic_key)
            for child in parent_children:
                if child.key not in seen_keys:
                    seen_keys.add(child.key)
                    children.append(child)

        # Method 2: Query for issues with Epic Link = epic_key
        if self.use_epic_link:
            epic_link_children = await self._get_children_by_epic_link(epic_key)
            for child in epic_link_children:
                if child.key not in seen_keys:
                    seen_keys.add(child.key)
                    children.append(child)

        # Method 3: Check issue links on the EPIC itself
        if self.use_issue_links:
            issue_link_children = await self._get_children_by_issue_links(epic_key)
            for child in issue_link_children:
                if child.key not in seen_keys:
                    seen_keys.add(child.key)
                    children.append(child)

        # Cache result
        self._cache[epic_key] = children

        logger.debug(f"Resolved {len(children)} children for {epic_key}")
        return children

    async def get_parent(self, epic_key: str) -> Optional[ResolvedLink]:
        """
        Get the parent EPIC of a given EPIC.

        Args:
            epic_key: Child EPIC key

        Returns:
            Parent link if found, None otherwise
        """
        try:
            result = await self.jira_client.get_issue(
                epic_key,
                fields=["parent", self.epic_link_field_id, "issuelinks"]
            )

            if not result.success:
                return None

            data = result.data

            # Check parent field
            parent_key = data.get("parent")
            if parent_key:
                if isinstance(parent_key, dict):
                    parent_key = parent_key.get("key")
                if parent_key:
                    return ResolvedLink(
                        key=parent_key,
                        link_type="parent",
                        direction="parent"
                    )

            # Check Epic Link field
            epic_link = data.get(self.epic_link_field_id)
            if epic_link:
                if isinstance(epic_link, dict):
                    epic_link = epic_link.get("key")
                if epic_link:
                    return ResolvedLink(
                        key=epic_link,
                        link_type="epic_link",
                        direction="parent"
                    )

            return None

        except Exception as e:
            logger.warning(f"Failed to get parent for {epic_key}: {e}")
            return None

    async def _get_children_by_parent(self, epic_key: str) -> List[ResolvedLink]:
        """Query for issues with parent field = epic_key."""
        children = []

        try:
            result = await self.jira_client.search_issues(
                jql=f'parent = {epic_key}',
                max_results=100,
                fields=["key", "summary", "issuetype"]
            )

            if result.success:
                for issue in result.data.get("issues", []):
                    issue_type = issue.get("fields", {}).get("issuetype", {}).get("name", "")
                    children.append(ResolvedLink(
                        key=issue["key"],
                        summary=issue.get("summary", ""),
                        link_type="parent",
                        direction="child",
                        issue_type=issue_type,
                    ))

        except Exception as e:
            logger.warning(f"Failed to query children by parent for {epic_key}: {e}")

        return children

    async def _get_children_by_epic_link(self, epic_key: str) -> List[ResolvedLink]:
        """Query for issues with Epic Link field = epic_key."""
        children = []

        try:
            # Use the Epic Link custom field in JQL
            jql = f'"{self.epic_link_field_id}" = {epic_key}'

            result = await self.jira_client.search_issues(
                jql=jql,
                max_results=100,
                fields=["key", "summary", "issuetype"]
            )

            if result.success:
                for issue in result.data.get("issues", []):
                    issue_type = issue.get("fields", {}).get("issuetype", {}).get("name", "")
                    children.append(ResolvedLink(
                        key=issue["key"],
                        summary=issue.get("summary", ""),
                        link_type="epic_link",
                        direction="child",
                        issue_type=issue_type,
                    ))

        except Exception as e:
            # Epic Link query might fail if field doesn't exist
            logger.debug(f"Epic Link query failed for {epic_key}: {e}")

        return children

    async def _get_children_by_issue_links(self, epic_key: str) -> List[ResolvedLink]:
        """Check issue links on the EPIC for parent-child relationships."""
        children = []

        try:
            result = await self.jira_client.get_issue(
                epic_key,
                fields=["issuelinks"]
            )

            if not result.success:
                return children

            data = result.data
            issue_links = data.get("issuelinks", [])

            # Link type names that indicate parent-child relationships
            parent_link_types = {
                "parent of", "is parent of", "epic-child",
                "contains", "has child"
            }
            child_link_types = {
                "child of", "is child of", "epic-parent",
                "contained by", "has parent"
            }

            for link in issue_links:
                link_type_name = link.get("type", {}).get("name", "").lower()

                # Outward link - this EPIC is parent of outward issue
                if any(pt in link_type_name for pt in parent_link_types):
                    outward = link.get("outwardIssue", {})
                    if outward:
                        issue_type = outward.get("fields", {}).get("issuetype", {}).get("name", "")
                        children.append(ResolvedLink(
                            key=outward.get("key"),
                            summary=outward.get("fields", {}).get("summary", ""),
                            link_type="issue_link",
                            direction="child",
                            issue_type=issue_type,
                        ))

                # Inward link with reversed direction - inward issue is child
                if any(ct in link_type_name for ct in child_link_types):
                    inward = link.get("inwardIssue", {})
                    if inward:
                        issue_type = inward.get("fields", {}).get("issuetype", {}).get("name", "")
                        children.append(ResolvedLink(
                            key=inward.get("key"),
                            summary=inward.get("fields", {}).get("summary", ""),
                            link_type="issue_link",
                            direction="child",
                            issue_type=issue_type,
                        ))

        except Exception as e:
            logger.warning(f"Failed to get issue links for {epic_key}: {e}")

        return children

    def is_epic_type(self, issue_type: str) -> bool:
        """
        Check if an issue type is considered an EPIC.

        Args:
            issue_type: Issue type name

        Returns:
            True if this is an EPIC-like issue type
        """
        return issue_type.lower() in [t.lower() for t in self.epic_issue_types]

    def clear_cache(self) -> None:
        """Clear the resolution cache."""
        self._cache.clear()

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "cached_epics": len(self._cache),
            "total_cached_children": sum(len(v) for v in self._cache.values()),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert resolver state to dictionary."""
        return {
            "epic_link_field_id": self.epic_link_field_id,
            "use_parent_field": self.use_parent_field,
            "use_epic_link": self.use_epic_link,
            "use_issue_links": self.use_issue_links,
            "epic_issue_types": self.epic_issue_types,
            "cache_stats": self.get_cache_stats(),
        }
