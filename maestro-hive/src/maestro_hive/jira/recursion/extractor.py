"""
Acceptance Criteria Extractor for JIRA Sub-EPIC Recursion.

Implements AC-2: Extract ACs from entire hierarchy.

Parses EPIC descriptions to extract acceptance criteria using
multiple patterns and aggregates them across the hierarchy.
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Pattern, Tuple

from .models import AcceptanceCriterion, ACStatus, EpicNode

logger = logging.getLogger(__name__)


@dataclass
class ExtractionPattern:
    """
    A pattern for extracting acceptance criteria.

    Attributes:
        name: Pattern name for logging
        regex: Compiled regex pattern
        id_group: Group index for AC ID (or None to auto-generate)
        desc_group: Group index for AC description
        priority: Lower number = higher priority
    """
    name: str
    regex: Pattern
    id_group: Optional[int]
    desc_group: int
    priority: int = 10


class AcceptanceCriteriaExtractor:
    """
    Extracts acceptance criteria from EPIC descriptions.

    Supports multiple extraction patterns:
    1. AC-N: Description format
    2. Bullet points under "Acceptance Criteria" heading
    3. Checkbox items [x] or [ ]
    4. Numbered lists under requirement sections

    Attributes:
        min_length: Minimum AC description length (default: 5)
        max_length: Maximum AC description length (default: 500)
        patterns: List of extraction patterns (ordered by priority)
        custom_patterns: Additional user-defined patterns
    """

    def __init__(
        self,
        min_length: int = 5,
        max_length: int = 500,
        custom_patterns: Optional[List[ExtractionPattern]] = None,
    ):
        """
        Initialize the extractor.

        Args:
            min_length: Minimum AC description length
            max_length: Maximum AC description length
            custom_patterns: Additional extraction patterns
        """
        self.min_length = min_length
        self.max_length = max_length
        self.custom_patterns = custom_patterns or []

        # Default patterns ordered by specificity
        self.patterns = self._build_default_patterns()

    def _build_default_patterns(self) -> List[ExtractionPattern]:
        """Build the default extraction patterns."""
        return [
            # Pattern 1: AC-N: Description (most specific)
            ExtractionPattern(
                name="ac_numbered",
                regex=re.compile(
                    r'AC-(\d+):\s*(.+?)(?=(?:AC-\d+:|$))',
                    re.IGNORECASE | re.DOTALL
                ),
                id_group=1,
                desc_group=2,
                priority=1,
            ),

            # Pattern 2: Acceptance Criteria section with bullets
            ExtractionPattern(
                name="ac_section_bullets",
                regex=re.compile(
                    r'(?:acceptance\s+criteria?)[\s:]*\n((?:[*\-]\s*.+?\n?)+)',
                    re.IGNORECASE | re.DOTALL
                ),
                id_group=None,
                desc_group=1,
                priority=2,
            ),

            # Pattern 3: Checkbox items [x] or [ ]
            ExtractionPattern(
                name="checkbox",
                regex=re.compile(
                    r'\[[\sx]\]\s*(.+?)(?=\n|\[[\sx]\]|$)',
                    re.IGNORECASE
                ),
                id_group=None,
                desc_group=1,
                priority=3,
            ),

            # Pattern 4: Numbered list after "Requirements" or similar
            ExtractionPattern(
                name="requirements_numbered",
                regex=re.compile(
                    r'(?:requirements?|objectives?|gaps?\s+to\s+address)[\s:]*\n((?:\d+[.)]\s*.+?\n?)+)',
                    re.IGNORECASE | re.DOTALL
                ),
                id_group=None,
                desc_group=1,
                priority=4,
            ),

            # Pattern 5: Stand-alone bullet points that look like criteria
            ExtractionPattern(
                name="criteria_bullets",
                regex=re.compile(
                    r'(?:^|\n)[*\-]\s*((?:implement|create|add|fix|ensure|verify|validate|support|handle).+?)(?=\n|$)',
                    re.IGNORECASE
                ),
                id_group=None,
                desc_group=1,
                priority=5,
            ),
        ]

    def extract(
        self,
        description: str,
        source_epic: Optional[str] = None,
    ) -> List[AcceptanceCriterion]:
        """
        Extract acceptance criteria from a description.

        Tries patterns in priority order, stopping when criteria are found.

        Args:
            description: EPIC description text
            source_epic: EPIC key for attribution

        Returns:
            List of extracted acceptance criteria
        """
        if not description:
            return []

        # Try patterns in priority order
        all_patterns = sorted(
            self.patterns + self.custom_patterns,
            key=lambda p: p.priority
        )

        for pattern in all_patterns:
            criteria = self._extract_with_pattern(pattern, description, source_epic)
            if criteria:
                logger.debug(
                    f"Extracted {len(criteria)} ACs from {source_epic or 'description'} "
                    f"using pattern '{pattern.name}'"
                )
                return criteria

        logger.debug(f"No acceptance criteria found in {source_epic or 'description'}")
        return []

    def _extract_with_pattern(
        self,
        pattern: ExtractionPattern,
        description: str,
        source_epic: Optional[str],
    ) -> List[AcceptanceCriterion]:
        """Extract criteria using a specific pattern."""
        criteria = []

        matches = pattern.regex.finditer(description)

        for i, match in enumerate(matches, 1):
            # Get AC ID
            if pattern.id_group is not None:
                ac_id = f"AC-{match.group(pattern.id_group)}"
            else:
                ac_id = f"AC-{i}"

            # Get description
            raw_desc = match.group(pattern.desc_group)

            # For section matches, we need to extract individual items
            if pattern.name in ("ac_section_bullets", "requirements_numbered"):
                section_criteria = self._extract_from_section(raw_desc, source_epic)
                criteria.extend(section_criteria)
            else:
                # Clean and validate description
                clean_desc = self._clean_description(raw_desc)
                if self._is_valid_description(clean_desc):
                    criteria.append(AcceptanceCriterion(
                        id=ac_id,
                        description=clean_desc,
                        status=ACStatus.PENDING,
                        source_epic=source_epic,
                    ))

        return criteria

    def _extract_from_section(
        self,
        section_text: str,
        source_epic: Optional[str],
    ) -> List[AcceptanceCriterion]:
        """Extract individual items from a section of bullets or numbers."""
        criteria = []

        # Pattern for bullet items
        bullet_pattern = re.compile(r'[*\-]\s*(.+?)(?=\n[*\-]|\n\n|$)', re.DOTALL)

        # Pattern for numbered items
        numbered_pattern = re.compile(r'\d+[.)]\s*(.+?)(?=\n\d+[.)]|\n\n|$)', re.DOTALL)

        # Try bullets first
        for i, match in enumerate(bullet_pattern.finditer(section_text), 1):
            clean_desc = self._clean_description(match.group(1))
            if self._is_valid_description(clean_desc):
                criteria.append(AcceptanceCriterion(
                    id=f"AC-{i}",
                    description=clean_desc,
                    status=ACStatus.PENDING,
                    source_epic=source_epic,
                ))

        # If no bullets, try numbered items
        if not criteria:
            for i, match in enumerate(numbered_pattern.finditer(section_text), 1):
                clean_desc = self._clean_description(match.group(1))
                if self._is_valid_description(clean_desc):
                    criteria.append(AcceptanceCriterion(
                        id=f"AC-{i}",
                        description=clean_desc,
                        status=ACStatus.PENDING,
                        source_epic=source_epic,
                    ))

        return criteria

    def _clean_description(self, raw: str) -> str:
        """Clean and normalize an AC description."""
        # Remove excess whitespace
        cleaned = re.sub(r'\s+', ' ', raw)
        # Strip leading/trailing whitespace
        cleaned = cleaned.strip()
        # Remove trailing punctuation if duplicated
        cleaned = re.sub(r'[.,:;]+$', '', cleaned)
        # Truncate if too long
        if len(cleaned) > self.max_length:
            cleaned = cleaned[:self.max_length] + "..."
        return cleaned

    def _is_valid_description(self, desc: str) -> bool:
        """Check if a description is valid as an AC."""
        if not desc:
            return False
        if len(desc) < self.min_length:
            return False
        # Skip if it's just a heading or label
        if desc.endswith(":"):
            return False
        # Skip if it's mostly non-alphanumeric
        alpha_ratio = sum(1 for c in desc if c.isalnum()) / len(desc)
        if alpha_ratio < 0.5:
            return False
        return True

    def extract_from_hierarchy(
        self,
        root: EpicNode,
    ) -> List[AcceptanceCriterion]:
        """
        Extract all acceptance criteria from an EPIC hierarchy.

        Traverses the hierarchy and aggregates all ACs, ensuring
        proper source attribution.

        Args:
            root: Root EpicNode of the hierarchy

        Returns:
            Aggregated list of all ACs with unique IDs
        """
        all_criteria = []
        seen_ids: Dict[str, int] = {}

        def process_node(node: EpicNode) -> None:
            # Extract from this node's description
            node_criteria = self.extract(node.description, node.key)

            # Store on the node
            node.acceptance_criteria = node_criteria

            # Add to aggregate with disambiguation
            for ac in node_criteria:
                # Make ID unique across hierarchy
                base_id = ac.id
                if base_id in seen_ids:
                    seen_ids[base_id] += 1
                    ac.id = f"{node.key}:{base_id}"
                else:
                    seen_ids[base_id] = 1

                all_criteria.append(ac)

            # Recurse to children
            for child in node.children:
                process_node(child)

        process_node(root)

        logger.info(f"Extracted {len(all_criteria)} total ACs from hierarchy")
        return all_criteria

    def merge_duplicates(
        self,
        criteria: List[AcceptanceCriterion],
    ) -> List[AcceptanceCriterion]:
        """
        Merge duplicate acceptance criteria.

        Criteria are considered duplicates if their descriptions
        are similar (>80% similarity).

        Args:
            criteria: List of criteria to deduplicate

        Returns:
            Deduplicated list with merged sources
        """
        if len(criteria) <= 1:
            return criteria

        merged = []
        used = set()

        for i, ac1 in enumerate(criteria):
            if i in used:
                continue

            # Find similar criteria
            similar = [ac1]
            for j, ac2 in enumerate(criteria[i + 1:], i + 1):
                if j in used:
                    continue
                if self._is_similar(ac1.description, ac2.description):
                    similar.append(ac2)
                    used.add(j)

            # Merge if duplicates found
            if len(similar) > 1:
                sources = [ac.source_epic for ac in similar if ac.source_epic]
                merged_ac = AcceptanceCriterion(
                    id=ac1.id,
                    description=ac1.description,
                    status=ac1.status,
                    source_epic=", ".join(set(sources)) if sources else None,
                )
                merged.append(merged_ac)
            else:
                merged.append(ac1)

            used.add(i)

        return merged

    def _is_similar(self, desc1: str, desc2: str, threshold: float = 0.8) -> bool:
        """Check if two descriptions are similar."""
        # Normalize
        d1 = desc1.lower().strip()
        d2 = desc2.lower().strip()

        if d1 == d2:
            return True

        # Simple word overlap similarity
        words1 = set(d1.split())
        words2 = set(d2.split())

        if not words1 or not words2:
            return False

        intersection = words1 & words2
        union = words1 | words2
        similarity = len(intersection) / len(union)

        return similarity >= threshold

    def add_custom_pattern(self, pattern: ExtractionPattern) -> None:
        """Add a custom extraction pattern."""
        self.custom_patterns.append(pattern)

    def to_dict(self) -> Dict[str, Any]:
        """Convert extractor state to dictionary."""
        return {
            "min_length": self.min_length,
            "max_length": self.max_length,
            "pattern_count": len(self.patterns) + len(self.custom_patterns),
            "pattern_names": [p.name for p in self.patterns + self.custom_patterns],
        }
