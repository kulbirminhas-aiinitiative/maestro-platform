"""
Pattern Extractor for RAG Service.

Analyzes retrieved executions to extract success and failure patterns.

EPIC: MD-2499
AC-3: Extract success/failure patterns
"""

import logging
import re
from collections import Counter, defaultdict
from typing import Any, Dict, List, Optional, Set
from uuid import uuid4

from maestro_hive.rag.exceptions import PatternExtractionError
from maestro_hive.rag.models import (
    ExecutionOutcome,
    FailurePattern,
    PatternSummary,
    RetrievalResult,
    SuccessPattern,
)

logger = logging.getLogger(__name__)


class PatternExtractor:
    """
    Extracts success and failure patterns from retrieved execution results.

    Analyzes execution metadata, phase results, and outcomes to identify
    reusable patterns and common failure modes.
    """

    def __init__(
        self,
        min_confidence: float = 0.6,
        max_patterns: int = 10,
    ):
        """
        Initialize pattern extractor.

        Args:
            min_confidence: Minimum confidence threshold for patterns
            max_patterns: Maximum patterns to return per category
        """
        self.min_confidence = min_confidence
        self.max_patterns = max_patterns

    def extract_patterns(
        self,
        results: List[RetrievalResult],
    ) -> PatternSummary:
        """
        Extract all patterns from retrieval results.

        Implements AC-3: Extract success/failure patterns.

        Args:
            results: List of similar execution results

        Returns:
            PatternSummary with success and failure patterns

        Raises:
            PatternExtractionError: If extraction fails
        """
        if not results:
            return PatternSummary(
                success_patterns=[],
                failure_patterns=[],
                total_executions_analyzed=0,
                confidence_score=0.0,
            )

        try:
            # Separate by outcome
            successes = [r for r in results if r.execution.outcome == ExecutionOutcome.SUCCESS]
            failures = [r for r in results if r.execution.outcome == ExecutionOutcome.FAILURE]
            partials = [r for r in results if r.execution.outcome == ExecutionOutcome.PARTIAL]

            # Extract patterns
            success_patterns = self._extract_success_patterns(successes)
            failure_patterns = self._extract_failure_patterns(failures + partials)

            # Calculate overall confidence
            total = len(results)
            confidence = self._calculate_confidence(results)

            summary = PatternSummary(
                success_patterns=success_patterns[: self.max_patterns],
                failure_patterns=failure_patterns[: self.max_patterns],
                total_executions_analyzed=total,
                confidence_score=confidence,
            )

            logger.info(
                f"Extracted {len(success_patterns)} success patterns, "
                f"{len(failure_patterns)} failure patterns from {total} executions"
            )

            return summary

        except Exception as e:
            raise PatternExtractionError(f"Pattern extraction failed: {e}")

    def get_success_patterns(
        self,
        results: List[RetrievalResult],
        min_confidence: Optional[float] = None,
    ) -> List[SuccessPattern]:
        """
        Extract only success patterns above confidence threshold.

        Args:
            results: Retrieval results to analyze
            min_confidence: Override minimum confidence

        Returns:
            List of SuccessPattern
        """
        min_conf = min_confidence if min_confidence is not None else self.min_confidence
        successes = [r for r in results if r.execution.outcome == ExecutionOutcome.SUCCESS]
        patterns = self._extract_success_patterns(successes)
        return [p for p in patterns if p.confidence >= min_conf]

    def get_failure_patterns(
        self,
        results: List[RetrievalResult],
        min_confidence: Optional[float] = None,
    ) -> List[FailurePattern]:
        """
        Extract only failure patterns above confidence threshold.

        Args:
            results: Retrieval results to analyze
            min_confidence: Override minimum confidence

        Returns:
            List of FailurePattern
        """
        min_conf = min_confidence if min_confidence is not None else self.min_confidence
        failures = [
            r
            for r in results
            if r.execution.outcome in (ExecutionOutcome.FAILURE, ExecutionOutcome.PARTIAL)
        ]
        patterns = self._extract_failure_patterns(failures)
        return [p for p in patterns if p.confidence >= min_conf]

    def _extract_success_patterns(
        self,
        results: List[RetrievalResult],
    ) -> List[SuccessPattern]:
        """Extract patterns from successful executions."""
        if not results:
            return []

        patterns: List[SuccessPattern] = []

        # Analyze phase patterns
        phase_success_counts: Counter[str] = Counter()
        phase_details: Dict[str, List[Dict]] = defaultdict(list)

        for result in results:
            execution = result.execution
            for phase_name, phase_result in execution.phase_results.items():
                if hasattr(phase_result, 'status') and phase_result.status == "passed":
                    phase_success_counts[phase_name] += 1
                    phase_details[phase_name].append({
                        "execution_id": execution.execution_id,
                        "score": getattr(phase_result, 'score', None),
                        "duration": getattr(phase_result, 'duration_seconds', 0),
                    })

        # Create patterns for commonly successful phases
        total = len(results)
        for phase_name, count in phase_success_counts.most_common():
            confidence = count / total if total > 0 else 0
            if confidence >= self.min_confidence:
                patterns.append(
                    SuccessPattern(
                        pattern_id=f"success-phase-{phase_name}-{uuid4().hex[:8]}",
                        description=f"Phase '{phase_name}' consistently passes",
                        frequency=count,
                        confidence=confidence,
                        context={
                            "phase_name": phase_name,
                            "success_rate": confidence,
                            "avg_duration": self._avg_duration(phase_details[phase_name]),
                        },
                        examples=[d["execution_id"] for d in phase_details[phase_name][:3]],
                    )
                )

        # Analyze metadata patterns
        metadata_patterns = self._analyze_metadata_patterns(results, is_success=True)
        patterns.extend(metadata_patterns)

        # Analyze duration patterns
        duration_pattern = self._analyze_duration_pattern(results, is_success=True)
        if duration_pattern:
            patterns.append(duration_pattern)

        return patterns

    def _extract_failure_patterns(
        self,
        results: List[RetrievalResult],
    ) -> List[FailurePattern]:
        """Extract patterns from failed/partial executions."""
        if not results:
            return []

        patterns: List[FailurePattern] = []

        # Analyze phase failures
        phase_failure_counts: Counter[str] = Counter()
        phase_errors: Dict[str, List[str]] = defaultdict(list)

        for result in results:
            execution = result.execution
            for phase_name, phase_result in execution.phase_results.items():
                if hasattr(phase_result, 'status') and phase_result.status == "failed":
                    phase_failure_counts[phase_name] += 1
                    error_msg = getattr(phase_result, 'error_message', None)
                    if error_msg:
                        phase_errors[phase_name].append(error_msg)

        # Create failure patterns
        total = len(results)
        for phase_name, count in phase_failure_counts.most_common():
            confidence = count / total if total > 0 else 0
            if confidence >= self.min_confidence:
                # Determine failure type from error messages
                errors = phase_errors.get(phase_name, [])
                failure_type = self._classify_failure_type(errors)
                mitigation = self._suggest_mitigation(failure_type, phase_name, errors)

                patterns.append(
                    FailurePattern(
                        pattern_id=f"failure-phase-{phase_name}-{uuid4().hex[:8]}",
                        description=f"Phase '{phase_name}' frequently fails",
                        failure_type=failure_type,
                        frequency=count,
                        confidence=confidence,
                        mitigation=mitigation,
                        context={
                            "phase_name": phase_name,
                            "failure_rate": confidence,
                            "common_errors": errors[:3],
                        },
                        examples=errors[:3],
                    )
                )

        # Analyze error message patterns
        error_patterns = self._analyze_error_patterns(results)
        patterns.extend(error_patterns)

        return patterns

    def _analyze_metadata_patterns(
        self,
        results: List[RetrievalResult],
        is_success: bool,
    ) -> List[SuccessPattern]:
        """Analyze metadata for common patterns."""
        patterns = []

        # Extract common metadata keys and values
        key_values: Dict[str, Counter] = defaultdict(Counter)
        for result in results:
            for key, value in result.execution.metadata.items():
                if isinstance(value, (str, int, float, bool)):
                    key_values[key][str(value)] += 1

        total = len(results)
        for key, value_counts in key_values.items():
            for value, count in value_counts.most_common(1):
                confidence = count / total if total > 0 else 0
                if confidence >= self.min_confidence:
                    patterns.append(
                        SuccessPattern(
                            pattern_id=f"metadata-{key}-{uuid4().hex[:8]}",
                            description=f"Successful executions commonly have {key}='{value}'",
                            frequency=count,
                            confidence=confidence,
                            context={"key": key, "value": value},
                            examples=[],
                        )
                    )

        return patterns

    def _analyze_error_patterns(
        self,
        results: List[RetrievalResult],
    ) -> List[FailurePattern]:
        """Analyze error messages for common patterns."""
        patterns = []

        # Collect all error messages
        all_errors: List[str] = []
        for result in results:
            for phase_result in result.execution.phase_results.values():
                error_msg = getattr(phase_result, 'error_message', None)
                if error_msg:
                    all_errors.append(error_msg)

        if not all_errors:
            return patterns

        # Find common error patterns using simple keyword extraction
        error_keywords = self._extract_error_keywords(all_errors)
        total = len(all_errors)

        for keyword, count in error_keywords.most_common(5):
            confidence = count / total if total > 0 else 0
            if confidence >= self.min_confidence:
                matching_errors = [e for e in all_errors if keyword.lower() in e.lower()]
                patterns.append(
                    FailurePattern(
                        pattern_id=f"error-keyword-{keyword[:20]}-{uuid4().hex[:8]}",
                        description=f"Common error pattern: '{keyword}'",
                        failure_type=self._classify_failure_type([keyword]),
                        frequency=count,
                        confidence=confidence,
                        mitigation=self._suggest_mitigation_for_keyword(keyword),
                        context={"keyword": keyword},
                        examples=matching_errors[:3],
                    )
                )

        return patterns

    def _analyze_duration_pattern(
        self,
        results: List[RetrievalResult],
        is_success: bool,
    ) -> Optional[SuccessPattern]:
        """Analyze execution duration patterns."""
        durations = [r.execution.duration_seconds for r in results if r.execution.duration_seconds > 0]

        if not durations:
            return None

        avg_duration = sum(durations) / len(durations)
        min_duration = min(durations)
        max_duration = max(durations)

        return SuccessPattern(
            pattern_id=f"duration-pattern-{uuid4().hex[:8]}",
            description=f"Average execution time: {avg_duration:.1f}s (range: {min_duration:.1f}s - {max_duration:.1f}s)",
            frequency=len(durations),
            confidence=0.8,  # Duration patterns are generally reliable
            context={
                "avg_seconds": avg_duration,
                "min_seconds": min_duration,
                "max_seconds": max_duration,
            },
            examples=[],
        )

    def _extract_error_keywords(self, errors: List[str]) -> Counter:
        """Extract significant keywords from error messages."""
        keywords: Counter = Counter()

        # Common error-indicating words
        significant_words = {
            "error", "failed", "timeout", "connection", "permission",
            "denied", "not found", "invalid", "missing", "exception",
            "null", "undefined", "overflow", "memory", "disk",
        }

        for error in errors:
            words = re.findall(r"\b\w+\b", error.lower())
            for word in words:
                if word in significant_words or len(word) > 6:
                    keywords[word] += 1

        return keywords

    def _classify_failure_type(self, errors: List[str]) -> str:
        """Classify the type of failure based on error messages."""
        error_text = " ".join(errors).lower()

        if "timeout" in error_text:
            return "timeout"
        elif "connection" in error_text or "network" in error_text:
            return "network_error"
        elif "permission" in error_text or "denied" in error_text:
            return "permission_error"
        elif "not found" in error_text or "missing" in error_text:
            return "resource_not_found"
        elif "memory" in error_text or "overflow" in error_text:
            return "resource_exhaustion"
        elif "test" in error_text or "assert" in error_text:
            return "test_failure"
        elif "build" in error_text or "compile" in error_text:
            return "build_error"
        else:
            return "unknown"

    def _suggest_mitigation(
        self,
        failure_type: str,
        phase_name: str,
        errors: List[str],
    ) -> str:
        """Suggest mitigation based on failure type."""
        mitigations = {
            "timeout": "Increase timeout limits or optimize slow operations",
            "network_error": "Check network connectivity and retry with backoff",
            "permission_error": "Verify credentials and access permissions",
            "resource_not_found": "Ensure required resources are created before execution",
            "resource_exhaustion": "Reduce memory usage or increase resource limits",
            "test_failure": "Review test assertions and fix failing test cases",
            "build_error": "Check build configuration and dependencies",
            "unknown": "Review error logs for specific failure cause",
        }
        return mitigations.get(failure_type, "Review execution logs for details")

    def _suggest_mitigation_for_keyword(self, keyword: str) -> str:
        """Suggest mitigation based on error keyword."""
        keyword_lower = keyword.lower()
        if "timeout" in keyword_lower:
            return "Consider increasing timeout or optimizing the operation"
        elif "memory" in keyword_lower:
            return "Check for memory leaks or increase memory allocation"
        elif "permission" in keyword_lower:
            return "Verify access permissions and credentials"
        elif "connection" in keyword_lower:
            return "Check network connectivity and service availability"
        else:
            return f"Investigate occurrences of '{keyword}' in error logs"

    def _calculate_confidence(self, results: List[RetrievalResult]) -> float:
        """Calculate overall confidence score for extracted patterns."""
        if not results:
            return 0.0

        # Weight by similarity scores
        total_similarity = sum(r.similarity_score for r in results)
        avg_similarity = total_similarity / len(results) if results else 0

        # Factor in result count (more results = higher confidence, up to a point)
        count_factor = min(len(results) / 10, 1.0)

        return avg_similarity * 0.7 + count_factor * 0.3

    @staticmethod
    def _avg_duration(details: List[Dict]) -> float:
        """Calculate average duration from detail list."""
        durations = [d.get("duration", 0) for d in details if d.get("duration", 0) > 0]
        return sum(durations) / len(durations) if durations else 0.0
