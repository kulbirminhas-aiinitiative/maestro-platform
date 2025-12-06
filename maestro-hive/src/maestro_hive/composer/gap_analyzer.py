"""
GapAnalyzer - AC-3: Identify gaps requiring generation

Analyzes resolved dependencies to identify missing functionality
that requires code generation rather than block composition.

Reference: MD-2508 Acceptance Criterion 3
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from .manifest_parser import CompositionManifest, GenerationSpec
from .dependency_resolver import ResolvedDependencies, ResolvedBlock

logger = logging.getLogger(__name__)


class GapType(str, Enum):
    """Types of gaps that can be identified"""
    MISSING_BLOCK = "missing_block"           # Block not found in registry
    INTERFACE_MISMATCH = "interface_mismatch" # Blocks exist but interfaces don't match
    CUSTOM_LOGIC = "custom_logic"             # Custom business logic needed
    ADAPTER = "adapter"                        # Adapter needed between blocks
    INTEGRATION = "integration"                # Integration code needed
    EXPLICIT = "explicit"                      # Explicitly declared in generate section


class GapSeverity(str, Enum):
    """Severity of identified gaps"""
    CRITICAL = "critical"   # Must be resolved before composition
    HIGH = "high"          # Should be resolved
    MEDIUM = "medium"      # Can be worked around
    LOW = "low"           # Nice to have


@dataclass
class BlockSuggestion:
    """Suggested block to fill a gap"""
    block_id: str
    version: str
    confidence: float
    reason: str


@dataclass
class Gap:
    """An identified gap requiring generation"""
    gap_id: str
    gap_type: GapType
    severity: GapSeverity
    description: str
    affected_blocks: List[str]
    interface_required: Optional[str] = None
    suggested_implementation: Optional[str] = None
    suggestions: List[BlockSuggestion] = field(default_factory=list)


@dataclass
class GapAnalysis:
    """
    Result of gap analysis.

    Contains all identified gaps categorized by type and severity.
    """
    gaps: List[Gap]
    total_gaps: int
    critical_count: int
    can_proceed: bool
    summary: Dict[str, int]

    def get_gaps_by_type(self, gap_type: GapType) -> List[Gap]:
        """Get all gaps of a specific type"""
        return [g for g in self.gaps if g.gap_type == gap_type]

    def get_critical_gaps(self) -> List[Gap]:
        """Get all critical gaps"""
        return [g for g in self.gaps if g.severity == GapSeverity.CRITICAL]

    def has_critical_gaps(self) -> bool:
        """Check if there are any critical gaps"""
        return self.critical_count > 0


class GapAnalyzer:
    """
    Analyzer for composition gaps.

    Implements AC-3: Identify gaps requiring generation

    Features:
    - Detect missing blocks
    - Identify interface mismatches
    - Analyze explicit generation requirements
    - Suggest existing blocks that might fill gaps
    - Categorize gaps by severity
    """

    def __init__(self, registry=None):
        """
        Initialize analyzer.

        Args:
            registry: Optional BlockRegistry for suggestions
        """
        self._registry = registry
        logger.info("GapAnalyzer initialized")

    def _get_registry(self):
        """Lazy-load Block Registry"""
        if self._registry is None:
            try:
                from ..blocks import get_block_registry
                self._registry = get_block_registry()
            except ImportError:
                logger.warning("Block Registry not available")
                self._registry = None
        return self._registry

    def analyze(
        self,
        manifest: CompositionManifest,
        resolved: ResolvedDependencies
    ) -> GapAnalysis:
        """
        Analyze composition for gaps.

        Args:
            manifest: Original composition manifest
            resolved: Resolved dependencies

        Returns:
            GapAnalysis with identified gaps
        """
        gaps = []

        # 1. Check for unresolved blocks (missing from registry)
        for block_id in resolved.unresolved:
            gap = Gap(
                gap_id=f"missing-{block_id}",
                gap_type=GapType.MISSING_BLOCK,
                severity=GapSeverity.CRITICAL,
                description=f"Block '{block_id}' not found in registry",
                affected_blocks=[block_id],
                suggestions=self._suggest_alternatives(block_id)
            )
            gaps.append(gap)

        # 2. Check for interface mismatches
        interface_gaps = self._analyze_interfaces(resolved)
        gaps.extend(interface_gaps)

        # 3. Process explicit generation requirements
        for gen_spec in manifest.generate:
            gap = Gap(
                gap_id=f"generate-{gen_spec.name}",
                gap_type=GapType.EXPLICIT,
                severity=GapSeverity.HIGH,
                description=f"Explicit generation required: {gen_spec.name}",
                affected_blocks=[],
                interface_required=gen_spec.interface,
                suggested_implementation=self._suggest_implementation(gen_spec)
            )
            gaps.append(gap)

        # 4. Check compatibility conflicts
        if not resolved.compatibility.compatible:
            for conflict in resolved.compatibility.conflicts:
                gap = Gap(
                    gap_id=f"conflict-{conflict['dependency']}",
                    gap_type=GapType.ADAPTER,
                    severity=GapSeverity.HIGH,
                    description=f"Version conflict for {conflict['dependency']}",
                    affected_blocks=[r[0] for r in conflict['requesters']]
                )
                gaps.append(gap)

        # Calculate summary
        summary = {
            "missing_block": len([g for g in gaps if g.gap_type == GapType.MISSING_BLOCK]),
            "interface_mismatch": len([g for g in gaps if g.gap_type == GapType.INTERFACE_MISMATCH]),
            "custom_logic": len([g for g in gaps if g.gap_type == GapType.CUSTOM_LOGIC]),
            "adapter": len([g for g in gaps if g.gap_type == GapType.ADAPTER]),
            "explicit": len([g for g in gaps if g.gap_type == GapType.EXPLICIT]),
        }

        critical_count = len([g for g in gaps if g.severity == GapSeverity.CRITICAL])

        # Can proceed if no critical gaps (or only explicit generations)
        non_explicit_critical = len([
            g for g in gaps
            if g.severity == GapSeverity.CRITICAL and g.gap_type != GapType.EXPLICIT
        ])

        logger.info(f"Gap analysis complete: {len(gaps)} gaps, {critical_count} critical")

        return GapAnalysis(
            gaps=gaps,
            total_gaps=len(gaps),
            critical_count=critical_count,
            can_proceed=non_explicit_critical == 0,
            summary=summary
        )

    def _analyze_interfaces(self, resolved: ResolvedDependencies) -> List[Gap]:
        """Analyze interface compatibility between resolved blocks"""
        gaps = []

        # Get all block instances
        blocks = list(resolved.blocks.values())

        for i, block_a in enumerate(blocks):
            for block_b in blocks[i+1:]:
                mismatch = self._check_interface_mismatch(block_a, block_b)
                if mismatch:
                    gaps.append(mismatch)

        return gaps

    def _check_interface_mismatch(
        self,
        block_a: ResolvedBlock,
        block_b: ResolvedBlock
    ) -> Optional[Gap]:
        """Check if two blocks have interface mismatches"""
        # Get interfaces if available
        instance_a = block_a.block_instance
        instance_b = block_b.block_instance

        if not instance_a or not instance_b:
            return None

        # Check if blocks declare required interfaces
        required_a = getattr(instance_a, 'required_interfaces', [])
        provided_b = getattr(instance_b, 'provided_interfaces', [])

        missing = set(required_a) - set(provided_b)

        if missing:
            return Gap(
                gap_id=f"interface-{block_a.block_id}-{block_b.block_id}",
                gap_type=GapType.INTERFACE_MISMATCH,
                severity=GapSeverity.HIGH,
                description=f"Interface mismatch: {block_a.block_id} requires {missing}",
                affected_blocks=[block_a.block_id, block_b.block_id],
                interface_required=str(missing)
            )

        return None

    def _suggest_alternatives(self, block_id: str) -> List[BlockSuggestion]:
        """Suggest alternative blocks for a missing block"""
        suggestions = []
        registry = self._get_registry()

        if not registry:
            return suggestions

        # Search for similar blocks
        all_blocks = registry.list_blocks()

        for bid in all_blocks:
            # Simple similarity check (could be enhanced with NLP)
            if self._is_similar(block_id, bid):
                latest = registry.get_latest_version(bid)
                suggestions.append(BlockSuggestion(
                    block_id=bid,
                    version=latest or "latest",
                    confidence=self._calculate_similarity(block_id, bid),
                    reason=f"Similar name to {block_id}"
                ))

        # Sort by confidence
        suggestions.sort(key=lambda s: s.confidence, reverse=True)
        return suggestions[:3]  # Top 3 suggestions

    def _is_similar(self, id_a: str, id_b: str) -> bool:
        """Check if two block IDs are similar"""
        # Normalize
        a = id_a.lower().replace("-", "").replace("_", "")
        b = id_b.lower().replace("-", "").replace("_", "")

        # Check substring match
        if a in b or b in a:
            return True

        # Check word overlap
        words_a = set(id_a.lower().replace("-", " ").replace("_", " ").split())
        words_b = set(id_b.lower().replace("-", " ").replace("_", " ").split())

        return len(words_a & words_b) > 0

    def _calculate_similarity(self, id_a: str, id_b: str) -> float:
        """Calculate similarity score between block IDs"""
        a = id_a.lower()
        b = id_b.lower()

        if a == b:
            return 1.0

        # Levenshtein-like scoring
        longer = max(len(a), len(b))
        if longer == 0:
            return 1.0

        # Count matching characters
        matches = sum(1 for ca, cb in zip(a, b) if ca == cb)
        return matches / longer

    def _suggest_implementation(self, gen_spec: GenerationSpec) -> Optional[str]:
        """Suggest implementation approach for a generation spec"""
        if gen_spec.interface:
            return f"Implement {gen_spec.interface} interface for {gen_spec.name}"

        if gen_spec.type == "adapter":
            return f"Create adapter class {gen_spec.name} with bridging logic"

        if gen_spec.type == "controller":
            return f"Create controller {gen_spec.name} with business logic methods"

        return f"Generate {gen_spec.type} component: {gen_spec.name}"

    def suggest_blocks(self, gap: Gap) -> List[BlockSuggestion]:
        """
        Suggest blocks that might fill a specific gap.

        Args:
            gap: Gap to find suggestions for

        Returns:
            List of block suggestions
        """
        if gap.gap_type == GapType.MISSING_BLOCK and gap.affected_blocks:
            return self._suggest_alternatives(gap.affected_blocks[0])

        return []
