"""
JIRA integration module for Maestro Hive.

This module provides JIRA API integration including:
- Sub-EPIC recursive fetching
- Acceptance criteria extraction from hierarchies
- Circular reference detection
"""

from .recursion import (
    SubEpicFetcher,
    CircularReferenceDetector,
    EpicLinkResolver,
    AcceptanceCriteriaExtractor,
    EpicNode,
    RecursionResult,
    RecursionConfig,
)

__all__ = [
    "SubEpicFetcher",
    "CircularReferenceDetector",
    "EpicLinkResolver",
    "AcceptanceCriteriaExtractor",
    "EpicNode",
    "RecursionResult",
    "RecursionConfig",
]
