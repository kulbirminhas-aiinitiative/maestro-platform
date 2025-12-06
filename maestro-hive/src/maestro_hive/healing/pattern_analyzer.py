"""
Failure Pattern Analyzer for Self-Healing Mechanism.

Analyzes execution history to identify recurring failure patterns
and builds a pattern database for automated fixes.

Implements AC-1: Failure pattern recognition from execution history
"""

import re
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json

from .models import (
    FailureType,
    FailurePattern,
    COMMON_PATTERNS,
)

logger = logging.getLogger(__name__)


class FailurePatternAnalyzer:
    """
    Analyzes execution history to detect and categorize failure patterns.

    This component:
    1. Processes execution history records
    2. Extracts error signatures and context
    3. Clusters similar failures
    4. Maintains a pattern database
    5. Provides pattern matching for new failures
    """

    def __init__(
        self,
        min_samples: int = 5,
        confidence_threshold: float = 0.7,
        pattern_ttl_days: int = 30,
    ):
        """
        Initialize the pattern analyzer.

        Args:
            min_samples: Minimum occurrences to create a pattern
            confidence_threshold: Minimum confidence for pattern matching
            pattern_ttl_days: Days before patterns expire
        """
        self.min_samples = min_samples
        self.confidence_threshold = confidence_threshold
        self.pattern_ttl_days = pattern_ttl_days

        # Pattern storage
        self.patterns: Dict[str, FailurePattern] = {}
        self.pattern_occurrences: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # Load common patterns
        self._load_common_patterns()

    def _load_common_patterns(self) -> None:
        """Load predefined common patterns."""
        for pattern_key, pattern in COMMON_PATTERNS.items():
            self.patterns[pattern.pattern_id] = pattern
            logger.debug(f"Loaded common pattern: {pattern_key}")

    def analyze_failure(
        self,
        error_message: str,
        context: Dict[str, Any],
        execution_id: Optional[str] = None,
    ) -> List[FailurePattern]:
        """
        Analyze a failure and find matching patterns.

        Args:
            error_message: The error message to analyze
            context: Additional context (file, line, stack trace, etc.)
            execution_id: Optional execution identifier

        Returns:
            List of matching patterns, sorted by confidence
        """
        matches: List[Tuple[FailurePattern, float]] = []

        # Classify failure type
        failure_type = self._classify_failure(error_message)

        # Check against existing patterns
        for pattern in self.patterns.values():
            if pattern.matches(error_message):
                # Calculate match confidence
                confidence = self._calculate_confidence(pattern, error_message, context)
                if confidence >= self.confidence_threshold:
                    matches.append((pattern, confidence))

        # Check if we should create a new pattern
        signature = FailurePattern.generate_signature(error_message, context)
        self._record_occurrence(signature, error_message, context, failure_type)

        # Sort by confidence
        matches.sort(key=lambda x: x[1], reverse=True)

        # Update pattern stats
        for pattern, confidence in matches:
            pattern.last_seen = datetime.utcnow()
            pattern.frequency += 1

        return [pattern for pattern, _ in matches]

    def _classify_failure(self, error_message: str) -> FailureType:
        """Classify the type of failure from the error message."""
        error_lower = error_message.lower()

        if any(kw in error_lower for kw in ["syntaxerror", "indentationerror", "parseerror"]):
            return FailureType.SYNTAX

        if any(kw in error_lower for kw in ["typeerror", "valueerror", "keyerror", "attributeerror", "nameerror"]):
            return FailureType.RUNTIME

        if any(kw in error_lower for kw in ["assertionerror", "failed", "expected", "actual"]):
            return FailureType.LOGIC

        if any(kw in error_lower for kw in ["modulenotfounderror", "importerror", "dependency"]):
            return FailureType.DEPENDENCY

        if any(kw in error_lower for kw in ["config", "environment", "setting"]):
            return FailureType.CONFIGURATION

        if any(kw in error_lower for kw in ["timeout", "timed out", "deadline"]):
            return FailureType.TIMEOUT

        if any(kw in error_lower for kw in ["memory", "disk", "resource", "oom"]):
            return FailureType.RESOURCE

        return FailureType.UNKNOWN

    def _calculate_confidence(
        self,
        pattern: FailurePattern,
        error_message: str,
        context: Dict[str, Any],
    ) -> float:
        """
        Calculate confidence score for a pattern match.

        Factors:
        - Pattern base confidence
        - Error message similarity
        - Context overlap
        - Historical success rate
        """
        base_confidence = pattern.confidence_score

        # Error message similarity (Jaccard similarity on tokens)
        error_tokens = set(re.findall(r'\w+', error_message.lower()))
        pattern_tokens = set()
        for example in pattern.examples:
            pattern_tokens.update(re.findall(r'\w+', example.lower()))

        if pattern_tokens:
            jaccard = len(error_tokens & pattern_tokens) / len(error_tokens | pattern_tokens)
            similarity_boost = jaccard * 0.2
        else:
            similarity_boost = 0

        # Frequency boost (more occurrences = more reliable)
        frequency_boost = min(pattern.frequency / 100, 0.1)

        confidence = min(base_confidence + similarity_boost + frequency_boost, 1.0)
        return confidence

    def _record_occurrence(
        self,
        signature: str,
        error_message: str,
        context: Dict[str, Any],
        failure_type: FailureType,
    ) -> None:
        """
        Record a failure occurrence for pattern learning.

        If enough occurrences accumulate, a new pattern is created.
        """
        occurrence = {
            "error_message": error_message,
            "context": context,
            "failure_type": failure_type,
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.pattern_occurrences[signature].append(occurrence)

        # Check if we should create a new pattern
        if len(self.pattern_occurrences[signature]) >= self.min_samples:
            if signature not in [p.signature for p in self.patterns.values()]:
                self._create_pattern_from_occurrences(signature)

    def _create_pattern_from_occurrences(self, signature: str) -> Optional[FailurePattern]:
        """
        Create a new pattern from accumulated occurrences.
        """
        occurrences = self.pattern_occurrences[signature]
        if not occurrences:
            return None

        # Find common elements
        first = occurrences[0]
        failure_type = first["failure_type"]

        # Build regex from common tokens
        common_tokens = set(re.findall(r'\w+', first["error_message"]))
        for occ in occurrences[1:]:
            occ_tokens = set(re.findall(r'\w+', occ["error_message"]))
            common_tokens &= occ_tokens

        if common_tokens:
            regex_parts = [re.escape(token) for token in sorted(common_tokens)]
            error_regex = ".*".join(regex_parts[:5])  # Use top 5 tokens
        else:
            error_regex = signature

        pattern = FailurePattern(
            pattern_id=f"learned-{signature}",
            pattern_type=failure_type,
            signature=signature,
            error_regex=error_regex,
            frequency=len(occurrences),
            confidence_score=0.6,  # Start with modest confidence
            last_seen=datetime.utcnow(),
            examples=[occ["error_message"] for occ in occurrences[:5]],
        )

        self.patterns[pattern.pattern_id] = pattern
        logger.info(f"Created new pattern: {pattern.pattern_id} (frequency: {pattern.frequency})")

        return pattern

    def get_patterns(
        self,
        failure_type: Optional[FailureType] = None,
        min_confidence: float = 0.0,
    ) -> List[FailurePattern]:
        """
        Get patterns matching criteria.

        Args:
            failure_type: Filter by failure type
            min_confidence: Minimum confidence score

        Returns:
            List of matching patterns
        """
        patterns = list(self.patterns.values())

        if failure_type:
            patterns = [p for p in patterns if p.pattern_type == failure_type]

        patterns = [p for p in patterns if p.confidence_score >= min_confidence]

        # Clean up old patterns
        cutoff = datetime.utcnow() - timedelta(days=self.pattern_ttl_days)
        patterns = [
            p for p in patterns
            if not p.last_seen or p.last_seen > cutoff or p.pattern_id.startswith("builtin-")
        ]

        return sorted(patterns, key=lambda p: p.confidence_score, reverse=True)

    def update_pattern_confidence(
        self,
        pattern_id: str,
        success: bool,
        delta: float = 0.05,
    ) -> None:
        """
        Update pattern confidence based on fix outcome.

        Args:
            pattern_id: The pattern to update
            success: Whether the fix was successful
            delta: Confidence adjustment amount
        """
        if pattern_id not in self.patterns:
            return

        pattern = self.patterns[pattern_id]

        if success:
            pattern.confidence_score = min(pattern.confidence_score + delta, 1.0)
        else:
            pattern.confidence_score = max(pattern.confidence_score - delta, 0.0)

        logger.debug(
            f"Updated pattern {pattern_id} confidence: {pattern.confidence_score:.2f}"
        )

    def export_patterns(self) -> List[Dict[str, Any]]:
        """Export all patterns for persistence."""
        return [pattern.to_dict() for pattern in self.patterns.values()]

    def import_patterns(self, patterns_data: List[Dict[str, Any]]) -> int:
        """
        Import patterns from persistence.

        Returns:
            Number of patterns imported
        """
        count = 0
        for data in patterns_data:
            try:
                pattern = FailurePattern.from_dict(data)
                self.patterns[pattern.pattern_id] = pattern
                count += 1
            except Exception as e:
                logger.warning(f"Failed to import pattern: {e}")

        return count

    def get_statistics(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        patterns = list(self.patterns.values())
        return {
            "total_patterns": len(patterns),
            "builtin_patterns": len([p for p in patterns if p.pattern_id.startswith("builtin-")]),
            "learned_patterns": len([p for p in patterns if p.pattern_id.startswith("learned-")]),
            "by_type": {
                ft.value: len([p for p in patterns if p.pattern_type == ft])
                for ft in FailureType
            },
            "avg_confidence": (
                sum(p.confidence_score for p in patterns) / len(patterns)
                if patterns else 0
            ),
            "pending_patterns": len([
                sig for sig, occs in self.pattern_occurrences.items()
                if len(occs) < self.min_samples
            ]),
        }
