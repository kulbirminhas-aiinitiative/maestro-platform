"""
Data models for JIRA Sub-EPIC Recursion.

Provides structured data types for recursive EPIC traversal including
nodes, results, configuration, and acceptance criteria.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class ACStatus(str, Enum):
    """Status of an acceptance criterion."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SATISFIED = "satisfied"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class AcceptanceCriterion:
    """
    An acceptance criterion extracted from an EPIC.

    Attributes:
        id: Unique identifier (e.g., "AC-1")
        description: Full description of the criterion
        status: Current status
        source_epic: EPIC key this AC came from
        implementation_file: File implementing this AC (if known)
        test_file: Test file verifying this AC (if known)
    """
    id: str
    description: str
    status: ACStatus = ACStatus.PENDING
    source_epic: Optional[str] = None
    implementation_file: Optional[str] = None
    test_file: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "source_epic": self.source_epic,
            "implementation_file": self.implementation_file,
            "test_file": self.test_file,
        }


@dataclass
class EpicNode:
    """
    A node in the EPIC hierarchy tree.

    Represents a single EPIC with its children and acceptance criteria.
    Supports tree traversal and aggregation operations.

    Attributes:
        key: JIRA issue key (e.g., "MD-2493")
        summary: EPIC summary/title
        description: Full EPIC description
        children: List of child EpicNodes (Sub-EPICs)
        acceptance_criteria: ACs extracted from this EPIC
        parent_key: Parent EPIC key if this is a Sub-EPIC
        depth: Depth in the hierarchy (root = 0)
        labels: JIRA labels
        status: Current JIRA status
    """
    key: str
    summary: str
    description: str = ""
    children: List["EpicNode"] = field(default_factory=list)
    acceptance_criteria: List[AcceptanceCriterion] = field(default_factory=list)
    parent_key: Optional[str] = None
    depth: int = 0
    labels: List[str] = field(default_factory=list)
    status: str = "To Do"

    def add_child(self, child: "EpicNode") -> None:
        """Add a child node to this EPIC."""
        child.parent_key = self.key
        child.depth = self.depth + 1
        self.children.append(child)

    def get_all_descendants(self) -> List["EpicNode"]:
        """Get all descendant EPICs (depth-first)."""
        descendants = []
        for child in self.children:
            descendants.append(child)
            descendants.extend(child.get_all_descendants())
        return descendants

    def get_all_acceptance_criteria(self) -> List[AcceptanceCriterion]:
        """
        Get all acceptance criteria from this node and all descendants.

        Returns:
            Aggregated list of all ACs with source_epic set
        """
        all_acs = []

        # Add this node's ACs
        for ac in self.acceptance_criteria:
            ac.source_epic = self.key
            all_acs.append(ac)

        # Recursively add children's ACs
        for child in self.children:
            all_acs.extend(child.get_all_acceptance_criteria())

        return all_acs

    def count_epics(self) -> int:
        """Count total EPICs in this subtree (including self)."""
        return 1 + sum(child.count_epics() for child in self.children)

    def max_depth(self) -> int:
        """Get maximum depth of the subtree."""
        if not self.children:
            return self.depth
        return max(child.max_depth() for child in self.children)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation (recursive)."""
        return {
            "key": self.key,
            "summary": self.summary,
            "description": self.description[:200] + "..." if len(self.description) > 200 else self.description,
            "parent_key": self.parent_key,
            "depth": self.depth,
            "labels": self.labels,
            "status": self.status,
            "acceptance_criteria": [ac.to_dict() for ac in self.acceptance_criteria],
            "children": [child.to_dict() for child in self.children],
            "children_count": len(self.children),
            "total_descendants": len(self.get_all_descendants()),
        }

    def __repr__(self) -> str:
        return f"EpicNode(key={self.key!r}, children={len(self.children)}, acs={len(self.acceptance_criteria)})"


@dataclass
class RecursionResult:
    """
    Result of recursive Sub-EPIC fetching.

    Contains the complete hierarchy tree along with statistics
    and any issues encountered during traversal.

    Attributes:
        root: Root EpicNode with full hierarchy
        total_epics: Total number of EPICs in hierarchy
        total_acs: Total acceptance criteria count
        circular_refs_detected: Keys where circular refs were found
        max_depth_reached: Maximum depth traversed
        duration_ms: Time taken to fetch hierarchy
        errors: Any errors encountered during fetching
    """
    root: EpicNode
    total_epics: int = 0
    total_acs: int = 0
    circular_refs_detected: List[str] = field(default_factory=list)
    max_depth_reached: int = 0
    duration_ms: float = 0.0
    errors: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Calculate statistics after initialization."""
        if self.root:
            self.total_epics = self.root.count_epics()
            self.total_acs = len(self.root.get_all_acceptance_criteria())
            self.max_depth_reached = self.root.max_depth()

    @property
    def success(self) -> bool:
        """Check if fetching was successful."""
        return self.root is not None and len(self.errors) == 0

    @property
    def all_acceptance_criteria(self) -> List[AcceptanceCriterion]:
        """Get all acceptance criteria from the hierarchy."""
        if self.root:
            return self.root.get_all_acceptance_criteria()
        return []

    @property
    def all_epic_keys(self) -> List[str]:
        """Get all EPIC keys in the hierarchy."""
        if not self.root:
            return []
        keys = [self.root.key]
        for desc in self.root.get_all_descendants():
            keys.append(desc.key)
        return keys

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "root": self.root.to_dict() if self.root else None,
            "total_epics": self.total_epics,
            "total_acs": self.total_acs,
            "circular_refs_detected": self.circular_refs_detected,
            "max_depth_reached": self.max_depth_reached,
            "duration_ms": self.duration_ms,
            "errors": self.errors,
            "success": self.success,
            "all_epic_keys": self.all_epic_keys,
        }


@dataclass
class RecursionConfig:
    """
    Configuration for Sub-EPIC recursion behavior.

    Attributes:
        max_depth: Maximum recursion depth (default: 10)
        cache_ttl: Cache TTL in seconds (default: 300)
        parallel_fetches: Max concurrent JIRA API calls (default: 5)
        circular_ref_handling: How to handle circular refs ("warn", "skip", "error")
        include_epic_link: Check Epic Link custom field
        include_parent_field: Check JIRA parent field
        epic_link_field_id: Custom field ID for Epic Link
        rate_limit: Max API requests per second
        request_delay_ms: Delay between requests in ms
    """
    max_depth: int = 10
    cache_ttl: int = 300
    parallel_fetches: int = 5
    circular_ref_handling: str = "warn"  # warn, skip, error
    include_epic_link: bool = True
    include_parent_field: bool = True
    epic_link_field_id: str = "customfield_10014"
    rate_limit: int = 50
    request_delay_ms: int = 0

    def validate(self) -> List[str]:
        """Validate configuration, return list of errors."""
        errors = []

        if self.max_depth < 1 or self.max_depth > 100:
            errors.append(f"max_depth must be between 1 and 100, got {self.max_depth}")

        if self.cache_ttl < 0:
            errors.append(f"cache_ttl must be non-negative, got {self.cache_ttl}")

        if self.parallel_fetches < 1 or self.parallel_fetches > 20:
            errors.append(f"parallel_fetches must be between 1 and 20, got {self.parallel_fetches}")

        if self.circular_ref_handling not in ("warn", "skip", "error"):
            errors.append(f"circular_ref_handling must be 'warn', 'skip', or 'error'")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "max_depth": self.max_depth,
            "cache_ttl": self.cache_ttl,
            "parallel_fetches": self.parallel_fetches,
            "circular_ref_handling": self.circular_ref_handling,
            "include_epic_link": self.include_epic_link,
            "include_parent_field": self.include_parent_field,
            "epic_link_field_id": self.epic_link_field_id,
            "rate_limit": self.rate_limit,
            "request_delay_ms": self.request_delay_ms,
        }
