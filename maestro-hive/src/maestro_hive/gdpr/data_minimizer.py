"""
Data Minimizer - Minimize PII in LLM API calls

Implements AC-2: Implement data minimization for LLM API calls.
Ensures only necessary data is sent to LLM providers per GDPR Article 5(1)(c).

EPIC: MD-2156
Child Task: MD-2279 [Privacy-2]
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
import re
import hashlib


class PIICategory(Enum):
    """Categories of Personally Identifiable Information."""
    NAME = "name"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    SSN = "ssn"
    CREDIT_CARD = "credit_card"
    IP_ADDRESS = "ip_address"
    DATE_OF_BIRTH = "date_of_birth"
    PASSPORT = "passport"
    DRIVER_LICENSE = "driver_license"
    BIOMETRIC = "biometric"
    HEALTH_DATA = "health_data"
    FINANCIAL = "financial"
    LOCATION = "location"
    CUSTOM = "custom"


class MinimizationStrategy(Enum):
    """Strategy for handling detected PII."""
    REMOVE = "remove"
    MASK = "mask"
    HASH = "hash"
    GENERALIZE = "generalize"
    PSEUDONYMIZE = "pseudonymize"


@dataclass
class PIIMatch:
    """Represents a detected PII match."""
    category: PIICategory
    value: str
    start: int
    end: int
    confidence: float
    replacement: Optional[str] = None


@dataclass
class MinimizationResult:
    """Result of data minimization operation."""
    original_text: str
    minimized_text: str
    pii_detected: list[PIIMatch] = field(default_factory=list)
    pii_count: int = 0
    categories_found: set[PIICategory] = field(default_factory=set)
    processing_time_ms: float = 0
    strategy_applied: MinimizationStrategy = MinimizationStrategy.MASK

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/auditing."""
        return {
            "original_length": len(self.original_text),
            "minimized_length": len(self.minimized_text),
            "pii_count": self.pii_count,
            "categories_found": [c.value for c in self.categories_found],
            "processing_time_ms": self.processing_time_ms,
            "strategy_applied": self.strategy_applied.value,
            "pii_matches": [
                {
                    "category": m.category.value,
                    "start": m.start,
                    "end": m.end,
                    "confidence": m.confidence,
                }
                for m in self.pii_detected
            ],
        }


class DataMinimizer:
    """
    Minimizes personal data before sending to LLM APIs.

    Implements GDPR Article 5(1)(c) - Data Minimization:
    Personal data shall be adequate, relevant and limited to what is
    necessary in relation to the purposes for which they are processed.
    """

    # PII detection patterns
    PII_PATTERNS: dict[PIICategory, tuple[str, float]] = {
        PIICategory.EMAIL: (
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            0.95
        ),
        PIICategory.PHONE: (
            r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
            0.85
        ),
        PIICategory.SSN: (
            r'\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b',
            0.90
        ),
        PIICategory.CREDIT_CARD: (
            r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b',
            0.95
        ),
        PIICategory.IP_ADDRESS: (
            r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
            0.80
        ),
        PIICategory.DATE_OF_BIRTH: (
            r'\b(?:0?[1-9]|1[0-2])[/-](?:0?[1-9]|[12]\d|3[01])[/-](?:19|20)\d{2}\b',
            0.75
        ),
    }

    def __init__(
        self,
        default_strategy: MinimizationStrategy = MinimizationStrategy.MASK,
        custom_patterns: Optional[dict[str, tuple[str, float]]] = None,
    ):
        """
        Initialize Data Minimizer.

        Args:
            default_strategy: Default strategy for handling PII
            custom_patterns: Additional custom PII patterns
        """
        self._default_strategy = default_strategy
        self._custom_patterns = custom_patterns or {}
        self._category_strategies: dict[PIICategory, MinimizationStrategy] = {}
        self._salt = hashlib.sha256(str(datetime.utcnow()).encode()).hexdigest()[:16]

    def set_strategy(
        self,
        category: PIICategory,
        strategy: MinimizationStrategy,
    ) -> None:
        """Set minimization strategy for a specific PII category."""
        self._category_strategies[category] = strategy

    def detect_pii(self, text: str) -> list[PIIMatch]:
        """
        Detect PII in text.

        Args:
            text: Text to scan for PII

        Returns:
            List of detected PII matches
        """
        matches: list[PIIMatch] = []

        # Check standard patterns
        for category, (pattern, confidence) in self.PII_PATTERNS.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matches.append(PIIMatch(
                    category=category,
                    value=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=confidence,
                ))

        # Check custom patterns
        for name, (pattern, confidence) in self._custom_patterns.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                matches.append(PIIMatch(
                    category=PIICategory.CUSTOM,
                    value=match.group(),
                    start=match.start(),
                    end=match.end(),
                    confidence=confidence,
                ))

        # Sort by position (reverse) for safe replacement
        matches.sort(key=lambda m: m.start, reverse=True)

        return matches

    def _mask_value(self, value: str, category: PIICategory) -> str:
        """Mask a PII value."""
        if category == PIICategory.EMAIL:
            parts = value.split('@')
            if len(parts) == 2:
                return f"{parts[0][0]}***@{parts[1]}"
            return "***@***.***"

        if category == PIICategory.PHONE:
            return "***-***-" + value[-4:]

        if category == PIICategory.CREDIT_CARD:
            return "****-****-****-" + value[-4:]

        if category == PIICategory.SSN:
            return "***-**-" + value[-4:]

        # Default masking
        if len(value) <= 4:
            return "*" * len(value)
        return value[0] + "*" * (len(value) - 2) + value[-1]

    def _hash_value(self, value: str) -> str:
        """Hash a PII value for pseudonymization."""
        salted = f"{self._salt}{value}"
        return f"[HASH:{hashlib.sha256(salted.encode()).hexdigest()[:12]}]"

    def _generalize_value(self, value: str, category: PIICategory) -> str:
        """Generalize a PII value."""
        if category == PIICategory.DATE_OF_BIRTH:
            # Keep only year
            match = re.search(r'(19|20)\d{2}', value)
            if match:
                return f"[YEAR:{match.group()}]"
            return "[DATE_REMOVED]"

        if category == PIICategory.IP_ADDRESS:
            # Keep first two octets
            parts = value.split('.')
            if len(parts) == 4:
                return f"{parts[0]}.{parts[1]}.x.x"
            return "[IP_REMOVED]"

        if category == PIICategory.PHONE:
            return "[PHONE_NUMBER]"

        return f"[{category.value.upper()}_REMOVED]"

    def _apply_strategy(
        self,
        value: str,
        category: PIICategory,
        strategy: MinimizationStrategy,
    ) -> str:
        """Apply minimization strategy to a value."""
        if strategy == MinimizationStrategy.REMOVE:
            return f"[{category.value.upper()}_REMOVED]"

        if strategy == MinimizationStrategy.MASK:
            return self._mask_value(value, category)

        if strategy == MinimizationStrategy.HASH:
            return self._hash_value(value)

        if strategy == MinimizationStrategy.GENERALIZE:
            return self._generalize_value(value, category)

        if strategy == MinimizationStrategy.PSEUDONYMIZE:
            return self._hash_value(value)

        return f"[{category.value.upper()}_REMOVED]"

    def minimize(
        self,
        text: str,
        strategy: Optional[MinimizationStrategy] = None,
        categories: Optional[list[PIICategory]] = None,
    ) -> MinimizationResult:
        """
        Minimize PII in text.

        Args:
            text: Text to minimize
            strategy: Override strategy for this operation
            categories: Only process these categories (None = all)

        Returns:
            MinimizationResult with minimized text and metadata
        """
        import time
        start_time = time.time()

        effective_strategy = strategy or self._default_strategy

        # Detect all PII
        matches = self.detect_pii(text)

        # Filter by categories if specified
        if categories:
            matches = [m for m in matches if m.category in categories]

        # Apply minimization
        minimized = text
        categories_found: set[PIICategory] = set()

        for match in matches:
            # Get category-specific strategy if set
            cat_strategy = self._category_strategies.get(
                match.category,
                effective_strategy,
            )

            replacement = self._apply_strategy(
                match.value,
                match.category,
                cat_strategy,
            )
            match.replacement = replacement

            # Replace in text
            minimized = minimized[:match.start] + replacement + minimized[match.end:]
            categories_found.add(match.category)

        processing_time = (time.time() - start_time) * 1000

        return MinimizationResult(
            original_text=text,
            minimized_text=minimized,
            pii_detected=matches,
            pii_count=len(matches),
            categories_found=categories_found,
            processing_time_ms=processing_time,
            strategy_applied=effective_strategy,
        )

    def minimize_for_llm(
        self,
        prompt: str,
        context: Optional[str] = None,
        preserve_structure: bool = True,
    ) -> dict[str, Any]:
        """
        Minimize data specifically for LLM API calls.

        Args:
            prompt: User prompt to minimize
            context: Optional context to minimize
            preserve_structure: Keep text structure intact

        Returns:
            Dictionary with minimized prompt and context
        """
        result = {
            "prompt": self.minimize(prompt),
            "context": self.minimize(context) if context else None,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "total_pii_removed": 0,
            }
        }

        result["metadata"]["total_pii_removed"] = result["prompt"].pii_count
        if result["context"]:
            result["metadata"]["total_pii_removed"] += result["context"].pii_count

        return result

    def add_custom_pattern(
        self,
        name: str,
        pattern: str,
        confidence: float = 0.8,
    ) -> None:
        """Add a custom PII detection pattern."""
        # Validate pattern
        try:
            re.compile(pattern)
        except re.error as e:
            raise ValueError(f"Invalid regex pattern: {e}")

        if not 0 <= confidence <= 1:
            raise ValueError("Confidence must be between 0 and 1")

        self._custom_patterns[name] = (pattern, confidence)

    def get_audit_log(self, result: MinimizationResult) -> dict[str, Any]:
        """Generate audit log entry for minimization operation."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": "data_minimization",
            "input_length": len(result.original_text),
            "output_length": len(result.minimized_text),
            "pii_detected_count": result.pii_count,
            "categories": [c.value for c in result.categories_found],
            "strategy": result.strategy_applied.value,
            "processing_time_ms": result.processing_time_ms,
        }
