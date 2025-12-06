"""
JIRA Sub-EPIC Recursion Module.

Implements recursive fetching of Sub-EPICs from JIRA hierarchies:
- AC-1: Recursively fetch all Sub-EPICs under parent EPIC
- AC-2: Extract ACs from entire hierarchy
- AC-3: Handle circular references gracefully
- AC-4: Support JIRA Epic Link and parent fields
"""

from .models import (
    EpicNode,
    RecursionResult,
    RecursionConfig,
    AcceptanceCriterion,
)
from .fetcher import SubEpicFetcher
from .detector import CircularReferenceDetector
from .resolver import EpicLinkResolver
from .extractor import AcceptanceCriteriaExtractor

__all__ = [
    "SubEpicFetcher",
    "CircularReferenceDetector",
    "EpicLinkResolver",
    "AcceptanceCriteriaExtractor",
    "EpicNode",
    "RecursionResult",
    "RecursionConfig",
    "AcceptanceCriterion",
]
