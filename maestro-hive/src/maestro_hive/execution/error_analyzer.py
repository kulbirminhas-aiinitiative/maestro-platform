"""
Error Pattern Analyzer - Automated error analysis and classification.

This module provides the ErrorPatternAnalyzer class that classifies and
analyzes execution errors to suggest recovery strategies.

EPIC: MD-3027 - Self-Healing Execution Loop (Phase 3)
Task: MD-3029 - Implement ErrorPatternAnalyzer
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Pattern, Tuple

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of execution errors."""
    NETWORK = "network"
    TIMEOUT = "timeout"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RESOURCE = "resource"
    VALIDATION = "validation"
    CONFIGURATION = "configuration"
    DEPENDENCY = "dependency"
    TRANSIENT = "transient"
    PERMANENT = "permanent"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Severity levels for errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RecoverySuggestion(Enum):
    """Suggested recovery actions."""
    RETRY_IMMEDIATELY = "retry_immediately"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    REFRESH_CREDENTIALS = "refresh_credentials"
    CHECK_CONFIGURATION = "check_configuration"
    INSTALL_DEPENDENCY = "install_dependency"
    INCREASE_TIMEOUT = "increase_timeout"
    SCALE_RESOURCES = "scale_resources"
    MANUAL_INTERVENTION = "manual_intervention"
    SKIP_AND_CONTINUE = "skip_and_continue"
    ESCALATE_TO_JIRA = "escalate_to_jira"


@dataclass
class ErrorPattern:
    """Definition of an error pattern for matching."""
    pattern_id: str
    category: ErrorCategory
    severity: ErrorSeverity
    regex_patterns: List[str]
    keywords: List[str]
    recovery_suggestions: List[RecoverySuggestion]
    description: str
    is_transient: bool = False
    max_retries_effective: int = 3

    def __post_init__(self):
        """Compile regex patterns."""
        self._compiled_patterns: List[Pattern] = [
            re.compile(p, re.IGNORECASE) for p in self.regex_patterns
        ]


@dataclass
class ErrorAnalysisResult:
    """Result of analyzing an error."""
    error_hash: str
    error_type: str
    error_message: str
    category: ErrorCategory
    severity: ErrorSeverity
    recovery_suggestions: List[RecoverySuggestion]
    matched_pattern: Optional[str] = None
    is_transient: bool = False
    recommended_retries: int = 0
    similar_errors_count: int = 0
    confidence_score: float = 0.0
    analysis_timestamp: datetime = field(default_factory=datetime.utcnow)
    additional_context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "error_hash": self.error_hash,
            "error_type": self.error_type,
            "error_message": self.error_message[:200],
            "category": self.category.value,
            "severity": self.severity.value,
            "recovery_suggestions": [s.value for s in self.recovery_suggestions],
            "matched_pattern": self.matched_pattern,
            "is_transient": self.is_transient,
            "recommended_retries": self.recommended_retries,
            "similar_errors_count": self.similar_errors_count,
            "confidence_score": self.confidence_score,
            "analysis_timestamp": self.analysis_timestamp.isoformat(),
        }


# Default error patterns
DEFAULT_ERROR_PATTERNS: List[ErrorPattern] = [
    ErrorPattern(
        pattern_id="network_connection",
        category=ErrorCategory.NETWORK,
        severity=ErrorSeverity.MEDIUM,
        regex_patterns=[
            r"connection\s*(refused|reset|timed?\s*out)",
            r"network\s*(is\s+)?unreachable",
            r"no\s+route\s+to\s+host",
            r"name\s+or\s+service\s+not\s+known",
            r"temporary\s+failure\s+in\s+name\s+resolution",
        ],
        keywords=["ConnectionError", "ConnectionRefused", "NetworkError", "socket"],
        recovery_suggestions=[
            RecoverySuggestion.RETRY_WITH_BACKOFF,
            RecoverySuggestion.CHECK_CONFIGURATION,
        ],
        description="Network connectivity issues",
        is_transient=True,
        max_retries_effective=5,
    ),
    ErrorPattern(
        pattern_id="timeout",
        category=ErrorCategory.TIMEOUT,
        severity=ErrorSeverity.MEDIUM,
        regex_patterns=[
            r"timed?\s*out",
            r"deadline\s+exceeded",
            r"operation\s+took\s+too\s+long",
            r"request\s+timeout",
        ],
        keywords=["TimeoutError", "asyncio.TimeoutError", "ReadTimeout", "ConnectTimeout"],
        recovery_suggestions=[
            RecoverySuggestion.RETRY_WITH_BACKOFF,
            RecoverySuggestion.INCREASE_TIMEOUT,
        ],
        description="Operation timeout",
        is_transient=True,
        max_retries_effective=3,
    ),
    ErrorPattern(
        pattern_id="auth_failure",
        category=ErrorCategory.AUTHENTICATION,
        severity=ErrorSeverity.HIGH,
        regex_patterns=[
            r"401\s*unauthorized",
            r"authentication\s+(failed|required)",
            r"invalid\s+(token|credentials|api\s*key)",
            r"expired\s+(token|session)",
        ],
        keywords=["AuthenticationError", "Unauthorized", "401", "InvalidToken"],
        recovery_suggestions=[
            RecoverySuggestion.REFRESH_CREDENTIALS,
            RecoverySuggestion.CHECK_CONFIGURATION,
        ],
        description="Authentication failure",
        is_transient=False,
        max_retries_effective=1,
    ),
    ErrorPattern(
        pattern_id="permission_denied",
        category=ErrorCategory.AUTHORIZATION,
        severity=ErrorSeverity.HIGH,
        regex_patterns=[
            r"403\s*forbidden",
            r"permission\s+denied",
            r"access\s+denied",
            r"not\s+authorized",
        ],
        keywords=["PermissionError", "Forbidden", "403", "AccessDenied"],
        recovery_suggestions=[
            RecoverySuggestion.MANUAL_INTERVENTION,
            RecoverySuggestion.ESCALATE_TO_JIRA,
        ],
        description="Authorization/permission failure",
        is_transient=False,
        max_retries_effective=0,
    ),
    ErrorPattern(
        pattern_id="resource_exhaustion",
        category=ErrorCategory.RESOURCE,
        severity=ErrorSeverity.HIGH,
        regex_patterns=[
            r"out\s+of\s+memory",
            r"memory\s+(error|limit|exceeded)",
            r"disk\s+(full|space)",
            r"too\s+many\s+(open\s+)?files",
            r"resource\s+(limit|quota)\s+exceeded",
        ],
        keywords=["MemoryError", "OSError", "ResourceExhausted", "QuotaExceeded"],
        recovery_suggestions=[
            RecoverySuggestion.SCALE_RESOURCES,
            RecoverySuggestion.ESCALATE_TO_JIRA,
        ],
        description="Resource exhaustion",
        is_transient=False,
        max_retries_effective=0,
    ),
    ErrorPattern(
        pattern_id="validation_error",
        category=ErrorCategory.VALIDATION,
        severity=ErrorSeverity.MEDIUM,
        regex_patterns=[
            r"validation\s+(error|failed)",
            r"invalid\s+(input|value|format|type)",
            r"missing\s+required\s+(field|parameter)",
            r"schema\s+validation\s+failed",
        ],
        keywords=["ValidationError", "ValueError", "TypeError", "InvalidInput"],
        recovery_suggestions=[
            RecoverySuggestion.CHECK_CONFIGURATION,
            RecoverySuggestion.MANUAL_INTERVENTION,
        ],
        description="Input validation failure",
        is_transient=False,
        max_retries_effective=0,
    ),
    ErrorPattern(
        pattern_id="dependency_missing",
        category=ErrorCategory.DEPENDENCY,
        severity=ErrorSeverity.HIGH,
        regex_patterns=[
            r"module\s+not\s+found",
            r"import\s+error",
            r"no\s+module\s+named",
            r"package\s+not\s+installed",
            r"command\s+not\s+found",
        ],
        keywords=["ModuleNotFoundError", "ImportError", "PackageNotFound"],
        recovery_suggestions=[
            RecoverySuggestion.INSTALL_DEPENDENCY,
            RecoverySuggestion.CHECK_CONFIGURATION,
        ],
        description="Missing dependency",
        is_transient=False,
        max_retries_effective=0,
    ),
    ErrorPattern(
        pattern_id="rate_limit",
        category=ErrorCategory.TRANSIENT,
        severity=ErrorSeverity.LOW,
        regex_patterns=[
            r"429\s*too\s+many\s+requests",
            r"rate\s+limit\s+(exceeded|reached)",
            r"throttl(ed|ing)",
            r"quota\s+exceeded",
        ],
        keywords=["RateLimitError", "TooManyRequests", "429", "Throttled"],
        recovery_suggestions=[
            RecoverySuggestion.RETRY_WITH_BACKOFF,
        ],
        description="Rate limiting",
        is_transient=True,
        max_retries_effective=5,
    ),
    ErrorPattern(
        pattern_id="server_error",
        category=ErrorCategory.TRANSIENT,
        severity=ErrorSeverity.MEDIUM,
        regex_patterns=[
            r"500\s*internal\s+server\s+error",
            r"502\s*bad\s+gateway",
            r"503\s*service\s+unavailable",
            r"504\s*gateway\s+timeout",
        ],
        keywords=["ServerError", "InternalServerError", "500", "502", "503", "504"],
        recovery_suggestions=[
            RecoverySuggestion.RETRY_WITH_BACKOFF,
            RecoverySuggestion.ESCALATE_TO_JIRA,
        ],
        description="Server error (5xx)",
        is_transient=True,
        max_retries_effective=3,
    ),
]


class ErrorPatternAnalyzer:
    """
    Analyzes errors and classifies them into categories with recovery suggestions.

    This analyzer:
    - Matches errors against known patterns
    - Classifies by category and severity
    - Suggests recovery strategies
    - Tracks error frequency for learning

    Example:
        >>> analyzer = ErrorPatternAnalyzer()
        >>> result = await analyzer.analyze(
        ...     ConnectionError("Connection refused"),
        ...     traceback_str
        ... )
        >>> print(result.category, result.recovery_suggestions)
    """

    def __init__(
        self,
        patterns: Optional[List[ErrorPattern]] = None,
        enable_learning: bool = True,
    ):
        """
        Initialize the error analyzer.

        Args:
            patterns: Custom error patterns (uses defaults if None)
            enable_learning: Whether to track error frequencies
        """
        self.patterns = patterns or DEFAULT_ERROR_PATTERNS
        self.enable_learning = enable_learning
        self._error_history: Dict[str, List[datetime]] = {}
        self._pattern_match_counts: Dict[str, int] = {}

        logger.info(f"ErrorPatternAnalyzer initialized with {len(self.patterns)} patterns")

    def _compute_error_hash(
        self,
        error_type: str,
        error_message: str,
    ) -> str:
        """Compute a hash for error deduplication."""
        # Normalize the error message
        normalized = re.sub(r'\d+', 'N', error_message.lower())
        normalized = re.sub(r'0x[0-9a-f]+', 'ADDR', normalized)
        normalized = re.sub(r'[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}', 'UUID', normalized)

        content = f"{error_type}:{normalized}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _match_pattern(
        self,
        error_type: str,
        error_message: str,
        traceback: Optional[str],
    ) -> Tuple[Optional[ErrorPattern], float]:
        """
        Match error against known patterns.

        Returns:
            Tuple of (matched pattern, confidence score)
        """
        best_match: Optional[ErrorPattern] = None
        best_score = 0.0

        full_text = f"{error_type} {error_message} {traceback or ''}"

        for pattern in self.patterns:
            score = 0.0
            matches = 0

            # Check regex patterns
            for compiled in pattern._compiled_patterns:
                if compiled.search(full_text):
                    matches += 1
                    score += 0.3

            # Check keywords
            for keyword in pattern.keywords:
                if keyword.lower() in full_text.lower():
                    matches += 1
                    score += 0.2

            # Check error type directly
            if error_type in pattern.keywords:
                score += 0.5

            # Normalize score
            total_checks = len(pattern._compiled_patterns) + len(pattern.keywords)
            if total_checks > 0:
                score = min(1.0, score)

            if score > best_score:
                best_score = score
                best_match = pattern

        return best_match, best_score

    def _get_similar_error_count(self, error_hash: str) -> int:
        """Get count of similar errors seen recently."""
        if not self.enable_learning:
            return 0

        history = self._error_history.get(error_hash, [])
        # Count errors in last hour
        cutoff = datetime.utcnow()
        recent = [ts for ts in history if (cutoff - ts).total_seconds() < 3600]
        return len(recent)

    def _record_error(self, error_hash: str) -> None:
        """Record error occurrence for learning."""
        if not self.enable_learning:
            return

        if error_hash not in self._error_history:
            self._error_history[error_hash] = []

        self._error_history[error_hash].append(datetime.utcnow())

        # Prune old entries (keep last 100)
        if len(self._error_history[error_hash]) > 100:
            self._error_history[error_hash] = self._error_history[error_hash][-100:]

    async def analyze(
        self,
        exception: Exception,
        traceback: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ErrorAnalysisResult:
        """
        Analyze an exception and return classification results.

        Args:
            exception: The exception to analyze
            traceback: Optional traceback string
            context: Additional context information

        Returns:
            ErrorAnalysisResult with classification and suggestions
        """
        error_type = type(exception).__name__
        error_message = str(exception)
        error_hash = self._compute_error_hash(error_type, error_message)

        # Match against patterns
        matched_pattern, confidence = self._match_pattern(
            error_type, error_message, traceback
        )

        # Get similar error count
        similar_count = self._get_similar_error_count(error_hash)

        # Record this error
        self._record_error(error_hash)

        # Build result
        if matched_pattern:
            result = ErrorAnalysisResult(
                error_hash=error_hash,
                error_type=error_type,
                error_message=error_message,
                category=matched_pattern.category,
                severity=matched_pattern.severity,
                recovery_suggestions=matched_pattern.recovery_suggestions,
                matched_pattern=matched_pattern.pattern_id,
                is_transient=matched_pattern.is_transient,
                recommended_retries=matched_pattern.max_retries_effective,
                similar_errors_count=similar_count,
                confidence_score=confidence,
                additional_context=context or {},
            )

            # Track pattern matches
            self._pattern_match_counts[matched_pattern.pattern_id] = (
                self._pattern_match_counts.get(matched_pattern.pattern_id, 0) + 1
            )
        else:
            # Unknown error
            result = ErrorAnalysisResult(
                error_hash=error_hash,
                error_type=error_type,
                error_message=error_message,
                category=ErrorCategory.UNKNOWN,
                severity=ErrorSeverity.MEDIUM,
                recovery_suggestions=[
                    RecoverySuggestion.RETRY_WITH_BACKOFF,
                    RecoverySuggestion.ESCALATE_TO_JIRA,
                ],
                is_transient=False,
                recommended_retries=1,
                similar_errors_count=similar_count,
                confidence_score=0.0,
                additional_context=context or {},
            )

        logger.info(
            f"Analyzed error: {error_type} -> {result.category.value} "
            f"(confidence: {result.confidence_score:.2f})"
        )

        return result

    def get_statistics(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return {
            "patterns_count": len(self.patterns),
            "unique_errors_seen": len(self._error_history),
            "pattern_match_counts": dict(self._pattern_match_counts),
            "learning_enabled": self.enable_learning,
        }

    def add_pattern(self, pattern: ErrorPattern) -> None:
        """Add a custom error pattern."""
        self.patterns.append(pattern)
        logger.info(f"Added error pattern: {pattern.pattern_id}")

    def clear_history(self) -> None:
        """Clear error history."""
        self._error_history.clear()
        self._pattern_match_counts.clear()


# Singleton instance
_default_analyzer: Optional[ErrorPatternAnalyzer] = None


def get_error_analyzer() -> ErrorPatternAnalyzer:
    """Get or create the default ErrorPatternAnalyzer instance."""
    global _default_analyzer
    if _default_analyzer is None:
        _default_analyzer = ErrorPatternAnalyzer()
    return _default_analyzer


def reset_error_analyzer() -> None:
    """Reset the default analyzer instance."""
    global _default_analyzer
    _default_analyzer = None
