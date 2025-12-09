"""
Adversarial Attack Detection for AI Systems
EU AI Act Article 15 Compliance - Security

Detects and mitigates adversarial inputs to AI models.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
import hashlib
import re


class AttackType(Enum):
    """Types of adversarial attacks."""
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    DATA_POISONING = "data_poisoning"
    EVASION = "evasion"
    MODEL_EXTRACTION = "model_extraction"
    MEMBERSHIP_INFERENCE = "membership_inference"
    INPUT_MANIPULATION = "input_manipulation"
    DENIAL_OF_SERVICE = "denial_of_service"


class ThreatLevel(Enum):
    """Threat severity levels."""
    NONE = (0, "none")
    LOW = (1, "low")
    MEDIUM = (2, "medium")
    HIGH = (3, "high")
    CRITICAL = (4, "critical")

    def __init__(self, order: int, label: str):
        self._order = order
        self._label = label

    def __lt__(self, other):
        if isinstance(other, ThreatLevel):
            return self._order < other._order
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, ThreatLevel):
            return self._order > other._order
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, ThreatLevel):
            return self._order <= other._order
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, ThreatLevel):
            return self._order >= other._order
        return NotImplemented

    @property
    def value(self) -> str:
        return self._label


@dataclass
class DetectionResult:
    """Result of adversarial detection analysis."""
    is_adversarial: bool
    threat_level: ThreatLevel
    attack_types: List[AttackType]
    confidence: float
    details: Dict[str, Any]
    recommendations: List[str]
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_adversarial": self.is_adversarial,
            "threat_level": self.threat_level.value,
            "attack_types": [at.value for at in self.attack_types],
            "confidence": self.confidence,
            "details": self.details,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class ValidationRule:
    """A single validation rule."""
    name: str
    pattern: Optional[str] = None
    check_function: Optional[Callable[[str], bool]] = None
    attack_type: AttackType = AttackType.INPUT_MANIPULATION
    severity: ThreatLevel = ThreatLevel.MEDIUM
    description: str = ""


class InputValidator:
    """
    Validates inputs for potential adversarial content.

    Provides:
    - Pattern-based detection
    - Statistical anomaly detection
    - Content policy enforcement
    """

    INJECTION_PATTERNS = [
        r"ignore\s+(previous|above|all)\s+(instructions?|prompts?)",
        r"disregard\s+(previous|above|all)\s+(instructions?|prompts?)",
        r"forget\s+(previous|above|all)\s+(instructions?|prompts?)",
        r"you\s+are\s+now\s+[a-z]+",
        r"pretend\s+(you\s+are|to\s+be)",
        r"act\s+as\s+(if|a)",
        r"new\s+instructions?:",
        r"system\s*:?\s*prompt",
        r"\[\s*system\s*\]",
        r"<\s*system\s*>",
    ]

    JAILBREAK_PATTERNS = [
        r"dan\s*mode",
        r"developer\s+mode",
        r"no\s+restrictions?",
        r"without\s+(any\s+)?restrictions?",
        r"bypass\s+(safety|filter|moderation)",
        r"ignore\s+(safety|ethical|content)\s+(guidelines?|policies?)",
        r"hypothetically",
        r"roleplay\s+as",
    ]

    def __init__(self):
        self.rules: List[ValidationRule] = []
        self._setup_default_rules()
        self._blocked_hashes: Set[str] = set()

    def _setup_default_rules(self) -> None:
        """Set up default validation rules."""
        for pattern in self.INJECTION_PATTERNS:
            self.rules.append(ValidationRule(
                name=f"injection_{pattern[:20]}",
                pattern=pattern,
                attack_type=AttackType.PROMPT_INJECTION,
                severity=ThreatLevel.HIGH,
                description="Potential prompt injection attempt",
            ))

        for pattern in self.JAILBREAK_PATTERNS:
            self.rules.append(ValidationRule(
                name=f"jailbreak_{pattern[:20]}",
                pattern=pattern,
                attack_type=AttackType.JAILBREAK,
                severity=ThreatLevel.HIGH,
                description="Potential jailbreak attempt",
            ))

    def add_rule(self, rule: ValidationRule) -> None:
        """Add a custom validation rule."""
        self.rules.append(rule)

    def block_input_hash(self, input_text: str) -> None:
        """Block a specific input by hash."""
        input_hash = hashlib.sha256(input_text.encode()).hexdigest()
        self._blocked_hashes.add(input_hash)

    def validate(self, input_text: str) -> DetectionResult:
        """Validate input for adversarial content."""
        violations: List[ValidationRule] = []
        input_lower = input_text.lower()

        # Check blocked hashes
        input_hash = hashlib.sha256(input_text.encode()).hexdigest()
        if input_hash in self._blocked_hashes:
            return DetectionResult(
                is_adversarial=True,
                threat_level=ThreatLevel.CRITICAL,
                attack_types=[AttackType.INPUT_MANIPULATION],
                confidence=1.0,
                details={"reason": "Input hash is blocked"},
                recommendations=["This input has been explicitly blocked"],
            )

        # Check pattern rules
        for rule in self.rules:
            if rule.pattern:
                if re.search(rule.pattern, input_lower, re.IGNORECASE):
                    violations.append(rule)
            if rule.check_function:
                if rule.check_function(input_text):
                    violations.append(rule)

        if not violations:
            return DetectionResult(
                is_adversarial=False,
                threat_level=ThreatLevel.NONE,
                attack_types=[],
                confidence=0.95,
                details={"rules_checked": len(self.rules)},
                recommendations=[],
            )

        # Determine overall threat level
        max_severity = max(v.severity for v in violations)
        attack_types = list(set(v.attack_type for v in violations))

        return DetectionResult(
            is_adversarial=True,
            threat_level=max_severity,
            attack_types=attack_types,
            confidence=min(0.9 + len(violations) * 0.02, 0.99),
            details={
                "violations": [{"name": v.name, "description": v.description} for v in violations],
                "violation_count": len(violations),
            },
            recommendations=[
                "Block or sanitize the input",
                "Log this attempt for security review",
                "Consider rate limiting the source",
            ],
        )


class AdversarialDetector:
    """
    Comprehensive adversarial attack detection system.

    Provides:
    - Input validation
    - Statistical anomaly detection
    - Rate limiting for DoS protection
    - Attack pattern learning
    """

    def __init__(
        self,
        sensitivity: float = 0.8,
        rate_limit_window_seconds: int = 60,
        rate_limit_max_requests: int = 100,
    ):
        self.sensitivity = sensitivity
        self.input_validator = InputValidator()
        self.rate_limit_window = rate_limit_window_seconds
        self.rate_limit_max = rate_limit_max_requests
        self._request_history: Dict[str, List[datetime]] = {}
        self._detection_history: List[DetectionResult] = []
        self._known_attack_signatures: Dict[str, AttackType] = {}

    def register_attack_signature(self, signature: str, attack_type: AttackType) -> None:
        """Register a known attack signature."""
        self._known_attack_signatures[signature.lower()] = attack_type

    def _check_rate_limit(self, source_id: str) -> Optional[DetectionResult]:
        """Check if source is rate limited."""
        now = datetime.utcnow()
        cutoff = now.timestamp() - self.rate_limit_window

        if source_id not in self._request_history:
            self._request_history[source_id] = []

        # Clean old requests
        self._request_history[source_id] = [
            dt for dt in self._request_history[source_id]
            if dt.timestamp() > cutoff
        ]

        if len(self._request_history[source_id]) >= self.rate_limit_max:
            return DetectionResult(
                is_adversarial=True,
                threat_level=ThreatLevel.HIGH,
                attack_types=[AttackType.DENIAL_OF_SERVICE],
                confidence=0.95,
                details={
                    "reason": "Rate limit exceeded",
                    "requests_in_window": len(self._request_history[source_id]),
                    "limit": self.rate_limit_max,
                },
                recommendations=[
                    "Throttle requests from this source",
                    "Implement CAPTCHA verification",
                ],
            )

        self._request_history[source_id].append(now)
        return None

    def _check_known_signatures(self, input_text: str) -> Optional[AttackType]:
        """Check for known attack signatures."""
        input_lower = input_text.lower()
        for signature, attack_type in self._known_attack_signatures.items():
            if signature in input_lower:
                return attack_type
        return None

    def _calculate_entropy(self, text: str) -> float:
        """Calculate Shannon entropy of text."""
        if not text:
            return 0.0

        import math
        char_freq: Dict[str, int] = {}
        for char in text:
            char_freq[char] = char_freq.get(char, 0) + 1

        entropy = 0.0
        text_len = len(text)
        for freq in char_freq.values():
            prob = freq / text_len
            entropy -= prob * math.log2(prob)

        return entropy

    def _detect_anomalies(self, input_text: str) -> Dict[str, Any]:
        """Detect statistical anomalies in input."""
        anomalies = {}

        # Check for unusual character distribution
        entropy = self._calculate_entropy(input_text)
        if entropy < 2.0 and len(input_text) > 50:
            anomalies["low_entropy"] = {
                "value": entropy,
                "threshold": 2.0,
                "description": "Unusually low character diversity",
            }

        # Check for excessive length
        if len(input_text) > 10000:
            anomalies["excessive_length"] = {
                "value": len(input_text),
                "threshold": 10000,
                "description": "Input exceeds maximum expected length",
            }

        # Check for high special character ratio
        special_chars = sum(1 for c in input_text if not c.isalnum() and not c.isspace())
        special_ratio = special_chars / max(len(input_text), 1)
        if special_ratio > 0.3:
            anomalies["high_special_char_ratio"] = {
                "value": special_ratio,
                "threshold": 0.3,
                "description": "Unusually high ratio of special characters",
            }

        # Check for repeated patterns
        if len(input_text) > 100:
            for pattern_len in [10, 20, 50]:
                if len(input_text) >= pattern_len * 3:
                    pattern = input_text[:pattern_len]
                    count = input_text.count(pattern)
                    if count > 5:
                        anomalies["repeated_pattern"] = {
                            "pattern_length": pattern_len,
                            "count": count,
                            "description": "Suspicious repeated pattern detected",
                        }
                        break

        return anomalies

    def analyze(
        self,
        input_text: str,
        source_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        """
        Analyze input for adversarial content.

        Args:
            input_text: The input to analyze
            source_id: Identifier for the input source (for rate limiting)
            context: Additional context for analysis

        Returns:
            DetectionResult with analysis findings
        """
        # Rate limit check
        if source_id:
            rate_limit_result = self._check_rate_limit(source_id)
            if rate_limit_result:
                self._detection_history.append(rate_limit_result)
                return rate_limit_result

        # Check known signatures
        known_attack = self._check_known_signatures(input_text)
        if known_attack:
            result = DetectionResult(
                is_adversarial=True,
                threat_level=ThreatLevel.CRITICAL,
                attack_types=[known_attack],
                confidence=0.99,
                details={"reason": "Known attack signature detected"},
                recommendations=["Block input immediately", "Alert security team"],
            )
            self._detection_history.append(result)
            return result

        # Input validation
        validation_result = self.input_validator.validate(input_text)

        # Anomaly detection
        anomalies = self._detect_anomalies(input_text)

        # Combine results
        if validation_result.is_adversarial:
            validation_result.details["anomalies"] = anomalies
            self._detection_history.append(validation_result)
            return validation_result

        if anomalies:
            result = DetectionResult(
                is_adversarial=len(anomalies) >= 2,  # Multiple anomalies = suspicious
                threat_level=ThreatLevel.MEDIUM if len(anomalies) >= 2 else ThreatLevel.LOW,
                attack_types=[AttackType.INPUT_MANIPULATION] if anomalies else [],
                confidence=0.6 + len(anomalies) * 0.1,
                details={"anomalies": anomalies},
                recommendations=[
                    "Monitor this input source",
                    "Apply additional validation",
                ] if anomalies else [],
            )
            self._detection_history.append(result)
            return result

        # Clean input
        result = DetectionResult(
            is_adversarial=False,
            threat_level=ThreatLevel.NONE,
            attack_types=[],
            confidence=0.95,
            details={"status": "clean"},
            recommendations=[],
        )
        self._detection_history.append(result)
        return result

    def get_threat_summary(self) -> Dict[str, Any]:
        """Get summary of detected threats."""
        recent = [d for d in self._detection_history
                 if (datetime.utcnow() - d.timestamp).total_seconds() < 3600]

        threat_counts = {}
        for level in ThreatLevel:
            threat_counts[level.value] = sum(1 for d in recent if d.threat_level == level)

        attack_counts = {}
        for attack in AttackType:
            attack_counts[attack.value] = sum(
                1 for d in recent
                for at in d.attack_types
                if at == attack
            )

        return {
            "period": "1h",
            "total_checks": len(recent),
            "adversarial_detections": sum(1 for d in recent if d.is_adversarial),
            "threat_level_distribution": threat_counts,
            "attack_type_distribution": attack_counts,
            "sensitivity": self.sensitivity,
        }
