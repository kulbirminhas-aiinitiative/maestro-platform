"""
Anonymizer - PII anonymization layer before LLM API calls

Implements AC-7: Add anonymization layer before LLM API calls.
Provides k-anonymity and differential privacy mechanisms.

EPIC: MD-2156
Child Task: MD-2284 [Privacy-7]
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Optional
import hashlib
import json
import random
import re
import string
import uuid


class AnonymizationMethod(Enum):
    """Methods for anonymizing data."""
    PSEUDONYMIZATION = "pseudonymization"
    GENERALIZATION = "generalization"
    SUPPRESSION = "suppression"
    PERTURBATION = "perturbation"
    TOKENIZATION = "tokenization"
    MASKING = "masking"
    HASHING = "hashing"


class DataType(Enum):
    """Types of data to anonymize."""
    NAME = "name"
    EMAIL = "email"
    PHONE = "phone"
    ADDRESS = "address"
    DATE = "date"
    NUMBER = "number"
    TEXT = "text"
    LOCATION = "location"
    IDENTIFIER = "identifier"


@dataclass
class AnonymizationConfig:
    """Configuration for anonymization behavior."""
    k_anonymity: int = 5
    epsilon: float = 1.0  # Differential privacy parameter
    default_method: AnonymizationMethod = AnonymizationMethod.PSEUDONYMIZATION
    preserve_format: bool = True
    reversible: bool = False
    salt: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "k_anonymity": self.k_anonymity,
            "epsilon": self.epsilon,
            "default_method": self.default_method.value,
            "preserve_format": self.preserve_format,
            "reversible": self.reversible,
        }


@dataclass
class AnonymizedValue:
    """Represents an anonymized value with metadata."""
    original_type: DataType
    method_used: AnonymizationMethod
    anonymized_value: str
    token: Optional[str] = None  # For reversible anonymization
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_type": self.original_type.value,
            "method_used": self.method_used.value,
            "anonymized_value": self.anonymized_value,
            "token": self.token,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class AnonymizationResult:
    """Result of an anonymization operation."""
    original_text: str
    anonymized_text: str
    values_anonymized: list[AnonymizedValue] = field(default_factory=list)
    processing_time_ms: float = 0
    config_used: Optional[AnonymizationConfig] = None

    @property
    def anonymization_count(self) -> int:
        """Count of values anonymized."""
        return len(self.values_anonymized)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "original_length": len(self.original_text),
            "anonymized_length": len(self.anonymized_text),
            "values_anonymized": [v.to_dict() for v in self.values_anonymized],
            "anonymization_count": self.anonymization_count,
            "processing_time_ms": self.processing_time_ms,
        }


class Anonymizer:
    """
    Provides anonymization layer for data before sending to LLM APIs.

    Implements multiple anonymization techniques:
    - K-anonymity: Ensures each record is indistinguishable from k-1 others
    - Pseudonymization: Replaces identifiers with artificial identifiers
    - Generalization: Reduces precision of data
    - Suppression: Removes sensitive data
    - Perturbation: Adds noise to numerical data
    """

    # Patterns for detecting PII
    PATTERNS: dict[DataType, str] = {
        DataType.EMAIL: r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        DataType.PHONE: r'\b(?:\+?1[-.\s]?)?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}\b',
        DataType.DATE: r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
        DataType.IDENTIFIER: r'\b[A-Z]{2,3}-\d{4,}\b',
    }

    # Name patterns (common first names, will match "John", "Jane", etc.)
    COMMON_NAMES = {
        "john", "jane", "michael", "sarah", "david", "emma", "james", "anna",
        "robert", "maria", "william", "lisa", "richard", "jennifer", "joseph",
        "elizabeth", "thomas", "susan", "charles", "jessica", "daniel", "karen",
    }

    def __init__(self, config: Optional[AnonymizationConfig] = None):
        """
        Initialize Anonymizer.

        Args:
            config: Anonymization configuration
        """
        self._config = config or AnonymizationConfig()
        self._token_map: dict[str, str] = {}  # For reversible anonymization
        self._reverse_map: dict[str, str] = {}
        self._salt = self._config.salt or uuid.uuid4().hex[:16]
        self._method_handlers: dict[AnonymizationMethod, Callable] = {
            AnonymizationMethod.PSEUDONYMIZATION: self._pseudonymize,
            AnonymizationMethod.GENERALIZATION: self._generalize,
            AnonymizationMethod.SUPPRESSION: self._suppress,
            AnonymizationMethod.PERTURBATION: self._perturb,
            AnonymizationMethod.TOKENIZATION: self._tokenize,
            AnonymizationMethod.MASKING: self._mask,
            AnonymizationMethod.HASHING: self._hash,
        }

    def _generate_pseudonym(self, data_type: DataType, length: int = 8) -> str:
        """Generate a pseudonym for a data type."""
        prefix = {
            DataType.NAME: "USER",
            DataType.EMAIL: "email",
            DataType.PHONE: "PHONE",
            DataType.ADDRESS: "ADDR",
            DataType.IDENTIFIER: "ID",
        }.get(data_type, "ANON")

        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        return f"[{prefix}_{suffix}]"

    def _pseudonymize(
        self,
        value: str,
        data_type: DataType,
    ) -> str:
        """Replace value with a pseudonym."""
        if value in self._token_map:
            return self._token_map[value]

        pseudonym = self._generate_pseudonym(data_type)

        if self._config.reversible:
            self._token_map[value] = pseudonym
            self._reverse_map[pseudonym] = value

        return pseudonym

    def _generalize(self, value: str, data_type: DataType) -> str:
        """Generalize a value to reduce precision."""
        if data_type == DataType.EMAIL:
            parts = value.split('@')
            if len(parts) == 2:
                domain = parts[1].split('.')
                if len(domain) >= 2:
                    return f"[EMAIL_AT_{domain[-2].upper()}_DOMAIN]"
            return "[EMAIL_ADDRESS]"

        if data_type == DataType.DATE:
            # Generalize to year only
            match = re.search(r'(\d{4}|\d{2})$', value)
            if match:
                year = match.group(1)
                if len(year) == 2:
                    year = f"20{year}" if int(year) < 50 else f"19{year}"
                return f"[YEAR_{year}]"
            return "[DATE]"

        if data_type == DataType.PHONE:
            return "[PHONE_NUMBER]"

        if data_type == DataType.ADDRESS:
            return "[ADDRESS]"

        return f"[{data_type.value.upper()}]"

    def _suppress(self, value: str, data_type: DataType) -> str:
        """Completely suppress a value."""
        return f"[{data_type.value.upper()}_REMOVED]"

    def _perturb(self, value: str, data_type: DataType) -> str:
        """Add noise to numerical values."""
        if data_type == DataType.NUMBER:
            try:
                num = float(value)
                # Add Laplace noise based on epsilon
                noise = random.gauss(0, 1 / self._config.epsilon)
                perturbed = num + noise
                return str(round(perturbed, 2))
            except ValueError:
                pass
        return self._pseudonymize(value, data_type)

    def _tokenize(self, value: str, data_type: DataType) -> str:
        """Replace with a token that can be reversed."""
        if value in self._token_map:
            return self._token_map[value]

        token = f"[TOKEN_{uuid.uuid4().hex[:8].upper()}]"
        self._token_map[value] = token
        self._reverse_map[token] = value

        return token

    def _mask(self, value: str, data_type: DataType) -> str:
        """Mask a value while preserving some structure."""
        if data_type == DataType.EMAIL:
            parts = value.split('@')
            if len(parts) == 2:
                local = parts[0]
                masked_local = local[0] + '*' * (len(local) - 1) if local else '*'
                return f"{masked_local}@{parts[1]}"

        if data_type == DataType.PHONE:
            digits = re.sub(r'\D', '', value)
            if len(digits) >= 4:
                return f"***-***-{digits[-4:]}"
            return "***-***-****"

        # Default masking
        if len(value) <= 2:
            return '*' * len(value)
        return value[0] + '*' * (len(value) - 2) + value[-1]

    def _hash(self, value: str, data_type: DataType) -> str:
        """Hash a value for consistent pseudonymization."""
        salted = f"{self._salt}{value}"
        hash_value = hashlib.sha256(salted.encode()).hexdigest()[:12]
        return f"[HASH_{hash_value.upper()}]"

    def detect_pii(self, text: str) -> list[tuple[DataType, str, int, int]]:
        """
        Detect PII in text.

        Args:
            text: Text to scan

        Returns:
            List of (data_type, value, start, end) tuples
        """
        detections: list[tuple[DataType, str, int, int]] = []

        # Check patterns
        for data_type, pattern in self.PATTERNS.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                detections.append((
                    data_type,
                    match.group(),
                    match.start(),
                    match.end(),
                ))

        # Check for names (simple heuristic)
        words = text.split()
        for i, word in enumerate(words):
            clean_word = re.sub(r'[^\w]', '', word).lower()
            if clean_word in self.COMMON_NAMES:
                start = text.find(word)
                if start >= 0:
                    detections.append((
                        DataType.NAME,
                        word,
                        start,
                        start + len(word),
                    ))

        # Sort by position (reverse for safe replacement)
        detections.sort(key=lambda x: x[2], reverse=True)

        return detections

    def anonymize(
        self,
        text: str,
        method: Optional[AnonymizationMethod] = None,
        data_types: Optional[list[DataType]] = None,
    ) -> AnonymizationResult:
        """
        Anonymize PII in text.

        Args:
            text: Text to anonymize
            method: Anonymization method to use
            data_types: Only process these data types (None = all)

        Returns:
            AnonymizationResult with anonymized text
        """
        import time
        start_time = time.time()

        effective_method = method or self._config.default_method
        handler = self._method_handlers.get(effective_method, self._pseudonymize)

        # Detect PII
        detections = self.detect_pii(text)

        # Filter by data types if specified
        if data_types:
            detections = [d for d in detections if d[0] in data_types]

        # Apply anonymization
        anonymized = text
        values_anonymized: list[AnonymizedValue] = []

        for data_type, value, start, end in detections:
            replacement = handler(value, data_type)

            # Create tracking record
            anon_value = AnonymizedValue(
                original_type=data_type,
                method_used=effective_method,
                anonymized_value=replacement,
                token=self._token_map.get(value) if self._config.reversible else None,
            )
            values_anonymized.append(anon_value)

            # Replace in text
            anonymized = anonymized[:start] + replacement + anonymized[end:]

        processing_time = (time.time() - start_time) * 1000

        return AnonymizationResult(
            original_text=text,
            anonymized_text=anonymized,
            values_anonymized=values_anonymized,
            processing_time_ms=processing_time,
            config_used=self._config,
        )

    def anonymize_for_llm(
        self,
        prompt: str,
        context: Optional[str] = None,
        system_prompt: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Anonymize data specifically for LLM API calls.

        Args:
            prompt: User prompt
            context: Optional context
            system_prompt: Optional system prompt

        Returns:
            Dictionary with anonymized components
        """
        result = {
            "prompt": self.anonymize(prompt),
            "context": self.anonymize(context) if context else None,
            "system_prompt": self.anonymize(system_prompt) if system_prompt else None,
            "metadata": {
                "timestamp": datetime.utcnow().isoformat(),
                "config": self._config.to_dict(),
                "total_anonymized": 0,
            },
        }

        # Count total anonymizations
        total = result["prompt"].anonymization_count
        if result["context"]:
            total += result["context"].anonymization_count
        if result["system_prompt"]:
            total += result["system_prompt"].anonymization_count

        result["metadata"]["total_anonymized"] = total

        return result

    def deanonymize(self, text: str) -> str:
        """
        Reverse anonymization for reversible methods.

        Args:
            text: Anonymized text

        Returns:
            Original text (where possible)
        """
        if not self._config.reversible:
            raise ValueError("Anonymization was not configured as reversible")

        result = text
        for token, original in self._reverse_map.items():
            result = result.replace(token, original)

        return result

    def get_k_anonymity_status(self) -> dict[str, Any]:
        """
        Check current k-anonymity status.

        Returns:
            Dictionary with k-anonymity metrics
        """
        # Count occurrences of each anonymized value
        value_counts: dict[str, int] = {}
        for token in self._token_map.values():
            value_counts[token] = value_counts.get(token, 0) + 1

        min_k = min(value_counts.values()) if value_counts else 0

        return {
            "configured_k": self._config.k_anonymity,
            "achieved_k": min_k,
            "compliant": min_k >= self._config.k_anonymity,
            "unique_values": len(value_counts),
        }

    def clear_token_map(self) -> None:
        """Clear the token map (for testing or privacy purposes)."""
        self._token_map.clear()
        self._reverse_map.clear()

    def export_token_map(self) -> str:
        """Export token map for backup (if reversible)."""
        if not self._config.reversible:
            raise ValueError("Token map only available for reversible anonymization")

        return json.dumps({
            "tokens": self._token_map,
            "reverse": self._reverse_map,
            "salt": self._salt,
            "exported_at": datetime.utcnow().isoformat(),
        }, indent=2)

    def import_token_map(self, json_data: str) -> None:
        """Import token map from backup."""
        data = json.loads(json_data)
        self._token_map = data.get("tokens", {})
        self._reverse_map = data.get("reverse", {})
        if "salt" in data:
            self._salt = data["salt"]

    def get_audit_log(self, result: AnonymizationResult) -> dict[str, Any]:
        """Generate audit log entry for anonymization operation."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": "anonymization",
            "input_length": len(result.original_text),
            "output_length": len(result.anonymized_text),
            "values_anonymized": result.anonymization_count,
            "method": result.config_used.default_method.value if result.config_used else None,
            "processing_time_ms": result.processing_time_ms,
            "data_types_found": list(set(
                v.original_type.value for v in result.values_anonymized
            )),
        }
