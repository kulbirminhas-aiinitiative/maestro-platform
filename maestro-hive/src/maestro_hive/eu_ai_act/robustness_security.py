"""
Robustness & Security Module - EU AI Act Article 15 Compliance

Ensures AI system accuracy, robustness against errors, and
appropriate cybersecurity measures.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple
import hashlib
import statistics
import threading


class SecurityLevel(Enum):
    """Security classification levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatCategory(Enum):
    """Categories of security threats."""
    INPUT_MANIPULATION = "input_manipulation"
    MODEL_POISONING = "model_poisoning"
    DATA_EXFILTRATION = "data_exfiltration"
    ADVERSARIAL_ATTACK = "adversarial_attack"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DENIAL_OF_SERVICE = "denial_of_service"
    PRIVACY_BREACH = "privacy_breach"


class ValidationResult(Enum):
    """Result of input validation."""
    VALID = "valid"
    SUSPICIOUS = "suspicious"
    INVALID = "invalid"
    BLOCKED = "blocked"


@dataclass
class SecurityEvent:
    """Security event record."""
    event_id: str
    threat_category: ThreatCategory
    severity: SecurityLevel
    description: str
    source: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    blocked: bool = False
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InputValidation:
    """Input validation result."""
    input_hash: str
    result: ValidationResult
    confidence: float
    checks_passed: List[str]
    checks_failed: List[str]
    sanitized_input: Any = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AccuracyMetrics:
    """Accuracy metrics for AI system."""
    precision: float
    recall: float
    f1_score: float
    accuracy: float
    samples_evaluated: int
    evaluation_date: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary."""
        return {
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "accuracy": self.accuracy,
            "samples_evaluated": self.samples_evaluated
        }


@dataclass
class RobustnessTest:
    """Robustness test result."""
    test_id: str
    test_name: str
    perturbation_type: str
    original_output: Any
    perturbed_output: Any
    consistency_score: float  # 0-1, how consistent output is
    passed: bool
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SecurityAssessment:
    """Comprehensive security assessment."""
    assessment_id: str
    ai_system_id: str
    overall_security_level: SecurityLevel
    vulnerabilities_found: int
    critical_issues: int
    recommendations: List[str]
    accuracy_metrics: Optional[AccuracyMetrics] = None
    robustness_score: float = 0.0
    compliance_score: float = 0.0
    assessment_date: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "assessment_id": self.assessment_id,
            "ai_system_id": self.ai_system_id,
            "overall_security_level": self.overall_security_level.value,
            "vulnerabilities_found": self.vulnerabilities_found,
            "critical_issues": self.critical_issues,
            "recommendations": self.recommendations,
            "accuracy_metrics": self.accuracy_metrics.to_dict() if self.accuracy_metrics else None,
            "robustness_score": self.robustness_score,
            "compliance_score": self.compliance_score,
            "assessment_date": self.assessment_date.isoformat()
        }


class RobustnessSecurity:
    """
    Robustness & Security manager for EU AI Act Article 15 compliance.

    Ensures accuracy, robustness against errors, and cybersecurity
    throughout the AI system lifecycle.
    """

    def __init__(
        self,
        ai_system_id: str,
        security_level: SecurityLevel = SecurityLevel.HIGH,
        accuracy_threshold: float = 0.85,
        robustness_threshold: float = 0.9
    ):
        """
        Initialize robustness & security manager.

        Args:
            ai_system_id: Unique identifier for the AI system
            security_level: Required security level
            accuracy_threshold: Minimum acceptable accuracy
            robustness_threshold: Minimum robustness score
        """
        self.ai_system_id = ai_system_id
        self.security_level = security_level
        self.accuracy_threshold = accuracy_threshold
        self.robustness_threshold = robustness_threshold

        self._security_events: List[SecurityEvent] = []
        self._input_validations: List[InputValidation] = []
        self._accuracy_history: List[AccuracyMetrics] = []
        self._robustness_tests: List[RobustnessTest] = []
        self._validators: Dict[str, Callable] = {}
        self._event_counter = 0
        self._lock = threading.Lock()

        # Initialize default validators
        self._initialize_default_validators()

    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        with self._lock:
            self._event_counter += 1
            return f"SEC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{self._event_counter:04d}"

    def _hash_input(self, input_data: Any) -> str:
        """Create hash of input data."""
        data_str = str(input_data)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]

    def _initialize_default_validators(self) -> None:
        """Initialize default input validators."""
        # SQL injection check
        self.register_validator(
            "sql_injection",
            lambda x: not any(
                keyword in str(x).upper()
                for keyword in ["DROP", "DELETE", "INSERT", "UPDATE", "--", ";"]
            )
        )

        # Script injection check
        self.register_validator(
            "script_injection",
            lambda x: not any(
                tag in str(x).lower()
                for tag in ["<script", "javascript:", "onerror=", "onclick="]
            )
        )

        # Input length check
        self.register_validator(
            "input_length",
            lambda x: len(str(x)) <= 100000  # 100KB limit
        )

        # Encoding check
        self.register_validator(
            "valid_encoding",
            lambda x: isinstance(x, (str, int, float, list, dict, bool, type(None)))
        )

    def register_validator(
        self,
        name: str,
        validator: Callable[[Any], bool]
    ) -> None:
        """
        Register a custom input validator.

        Args:
            name: Validator name
            validator: Function that returns True if input is valid
        """
        self._validators[name] = validator

    def validate_input(
        self,
        input_data: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> InputValidation:
        """
        Validate input data against security checks.

        Args:
            input_data: Input to validate
            context: Additional context

        Returns:
            InputValidation result
        """
        input_hash = self._hash_input(input_data)
        checks_passed = []
        checks_failed = []

        for name, validator in self._validators.items():
            try:
                if validator(input_data):
                    checks_passed.append(name)
                else:
                    checks_failed.append(name)
            except Exception:
                checks_failed.append(f"{name} (error)")

        # Determine result
        if len(checks_failed) == 0:
            result = ValidationResult.VALID
            confidence = 1.0
        elif len(checks_failed) <= 1:
            result = ValidationResult.SUSPICIOUS
            confidence = 0.7
        else:
            result = ValidationResult.INVALID
            confidence = 0.3

        # Record security event if validation failed
        if result != ValidationResult.VALID:
            self._log_security_event(
                threat_category=ThreatCategory.INPUT_MANIPULATION,
                severity=SecurityLevel.MEDIUM if result == ValidationResult.SUSPICIOUS else SecurityLevel.HIGH,
                description=f"Input validation failed: {', '.join(checks_failed)}",
                source="input_validator",
                blocked=result == ValidationResult.INVALID,
                details={"checks_failed": checks_failed, "input_hash": input_hash}
            )

        validation = InputValidation(
            input_hash=input_hash,
            result=result,
            confidence=confidence,
            checks_passed=checks_passed,
            checks_failed=checks_failed
        )

        with self._lock:
            self._input_validations.append(validation)

        return validation

    def _log_security_event(
        self,
        threat_category: ThreatCategory,
        severity: SecurityLevel,
        description: str,
        source: str,
        blocked: bool = False,
        details: Optional[Dict[str, Any]] = None
    ) -> SecurityEvent:
        """Log a security event."""
        event = SecurityEvent(
            event_id=self._generate_event_id(),
            threat_category=threat_category,
            severity=severity,
            description=description,
            source=source,
            blocked=blocked,
            details=details or {}
        )

        with self._lock:
            self._security_events.append(event)

        return event

    def record_accuracy_metrics(
        self,
        true_positives: int,
        false_positives: int,
        true_negatives: int,
        false_negatives: int
    ) -> AccuracyMetrics:
        """
        Record accuracy metrics from evaluation.

        Args:
            true_positives: Count of true positives
            false_positives: Count of false positives
            true_negatives: Count of true negatives
            false_negatives: Count of false negatives

        Returns:
            AccuracyMetrics object
        """
        total = true_positives + false_positives + true_negatives + false_negatives

        precision = (
            true_positives / (true_positives + false_positives)
            if (true_positives + false_positives) > 0 else 0.0
        )
        recall = (
            true_positives / (true_positives + false_negatives)
            if (true_positives + false_negatives) > 0 else 0.0
        )
        f1 = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0 else 0.0
        )
        accuracy = (
            (true_positives + true_negatives) / total
            if total > 0 else 0.0
        )

        metrics = AccuracyMetrics(
            precision=precision,
            recall=recall,
            f1_score=f1,
            accuracy=accuracy,
            samples_evaluated=total
        )

        with self._lock:
            self._accuracy_history.append(metrics)

        return metrics

    def run_robustness_test(
        self,
        test_name: str,
        model_function: Callable[[Any], Any],
        original_input: Any,
        perturbation_function: Callable[[Any], Any],
        similarity_threshold: float = 0.9
    ) -> RobustnessTest:
        """
        Run a robustness test with input perturbations.

        Args:
            test_name: Name of the test
            model_function: Function to test (input -> output)
            original_input: Original input
            perturbation_function: Function to perturb input
            similarity_threshold: Threshold for consistency

        Returns:
            RobustnessTest result
        """
        test_id = f"ROB-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # Get original output
        original_output = model_function(original_input)

        # Get perturbed output
        perturbed_input = perturbation_function(original_input)
        perturbed_output = model_function(perturbed_input)

        # Calculate consistency score (simple string comparison)
        consistency = self._calculate_similarity(original_output, perturbed_output)
        passed = consistency >= similarity_threshold

        test = RobustnessTest(
            test_id=test_id,
            test_name=test_name,
            perturbation_type=perturbation_function.__name__,
            original_output=original_output,
            perturbed_output=perturbed_output,
            consistency_score=consistency,
            passed=passed
        )

        with self._lock:
            self._robustness_tests.append(test)

        return test

    def _calculate_similarity(self, output1: Any, output2: Any) -> float:
        """Calculate similarity between two outputs."""
        str1 = str(output1)
        str2 = str(output2)

        if str1 == str2:
            return 1.0

        # Simple Jaccard similarity for non-identical outputs
        set1 = set(str1.split())
        set2 = set(str2.split())

        if not set1 and not set2:
            return 1.0
        if not set1 or not set2:
            return 0.0

        intersection = len(set1.intersection(set2))
        union = len(set1.union(set2))
        return intersection / union if union > 0 else 0.0

    def detect_adversarial_input(
        self,
        input_data: Any,
        model_function: Callable[[Any], Tuple[Any, float]],
        perturbation_budget: float = 0.1
    ) -> Tuple[bool, float]:
        """
        Detect if input might be adversarial.

        Args:
            input_data: Input to check
            model_function: Function returning (output, confidence)
            perturbation_budget: Maximum perturbation to test

        Returns:
            Tuple of (is_adversarial, confidence_drop)
        """
        # Get original prediction
        original_output, original_conf = model_function(input_data)

        # Test with minor perturbations
        max_conf_drop = 0.0

        # If input is string, test character swaps
        if isinstance(input_data, str) and len(input_data) > 2:
            # Swap two characters
            chars = list(input_data)
            mid = len(chars) // 2
            chars[mid], chars[mid + 1] = chars[mid + 1], chars[mid]
            perturbed = "".join(chars)

            try:
                _, perturbed_conf = model_function(perturbed)
                conf_drop = original_conf - perturbed_conf
                max_conf_drop = max(max_conf_drop, conf_drop)
            except Exception:
                pass

        # If confidence drops significantly, input might be adversarial
        is_adversarial = max_conf_drop > perturbation_budget

        if is_adversarial:
            self._log_security_event(
                threat_category=ThreatCategory.ADVERSARIAL_ATTACK,
                severity=SecurityLevel.HIGH,
                description="Potential adversarial input detected",
                source="adversarial_detector",
                details={"confidence_drop": max_conf_drop, "input_hash": self._hash_input(input_data)}
            )

        return is_adversarial, max_conf_drop

    def perform_security_assessment(self) -> SecurityAssessment:
        """
        Perform comprehensive security assessment.

        Returns:
            SecurityAssessment with findings
        """
        assessment_id = f"SA-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # Count vulnerabilities
        high_severity_events = sum(
            1 for e in self._security_events
            if e.severity in [SecurityLevel.HIGH, SecurityLevel.CRITICAL]
        )
        critical_events = sum(
            1 for e in self._security_events
            if e.severity == SecurityLevel.CRITICAL
        )

        # Calculate robustness score
        if self._robustness_tests:
            robustness_score = statistics.mean(
                t.consistency_score for t in self._robustness_tests
            )
        else:
            robustness_score = 1.0  # No tests = assume robust

        # Get latest accuracy metrics
        latest_accuracy = self._accuracy_history[-1] if self._accuracy_history else None

        # Determine overall security level
        if critical_events > 0:
            overall_level = SecurityLevel.CRITICAL
        elif high_severity_events > 5:
            overall_level = SecurityLevel.HIGH
        elif high_severity_events > 0:
            overall_level = SecurityLevel.MEDIUM
        else:
            overall_level = SecurityLevel.LOW

        # Generate recommendations
        recommendations = []
        if high_severity_events > 0:
            recommendations.append("Review and address high-severity security events")
        if robustness_score < self.robustness_threshold:
            recommendations.append(f"Improve model robustness (current: {robustness_score:.2%})")
        if latest_accuracy and latest_accuracy.accuracy < self.accuracy_threshold:
            recommendations.append(f"Improve model accuracy (current: {latest_accuracy.accuracy:.2%})")
        if len(self._validators) < 5:
            recommendations.append("Add additional input validators")

        # Calculate compliance score
        accuracy_score = latest_accuracy.accuracy if latest_accuracy else 1.0
        security_score = 1.0 - (min(high_severity_events, 10) / 10)
        compliance_score = (accuracy_score + robustness_score + security_score) / 3

        assessment = SecurityAssessment(
            assessment_id=assessment_id,
            ai_system_id=self.ai_system_id,
            overall_security_level=overall_level,
            vulnerabilities_found=len(self._security_events),
            critical_issues=critical_events,
            recommendations=recommendations,
            accuracy_metrics=latest_accuracy,
            robustness_score=robustness_score,
            compliance_score=compliance_score
        )

        return assessment

    def get_security_events(
        self,
        threat_category: Optional[ThreatCategory] = None,
        min_severity: Optional[SecurityLevel] = None,
        limit: int = 100
    ) -> List[SecurityEvent]:
        """Get security events with filters."""
        events = self._security_events.copy()

        if threat_category:
            events = [e for e in events if e.threat_category == threat_category]

        if min_severity:
            severity_order = [SecurityLevel.LOW, SecurityLevel.MEDIUM,
                           SecurityLevel.HIGH, SecurityLevel.CRITICAL]
            min_index = severity_order.index(min_severity)
            events = [
                e for e in events
                if severity_order.index(e.severity) >= min_index
            ]

        # Return most recent first
        events.sort(key=lambda e: e.timestamp, reverse=True)
        return events[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Get security statistics."""
        threat_counts = {}
        for event in self._security_events:
            cat = event.threat_category.value
            threat_counts[cat] = threat_counts.get(cat, 0) + 1

        validation_results = {}
        for val in self._input_validations:
            result = val.result.value
            validation_results[result] = validation_results.get(result, 0) + 1

        return {
            "ai_system_id": self.ai_system_id,
            "security_level": self.security_level.value,
            "total_security_events": len(self._security_events),
            "events_by_threat": threat_counts,
            "total_validations": len(self._input_validations),
            "validation_results": validation_results,
            "robustness_tests_run": len(self._robustness_tests),
            "robustness_tests_passed": sum(1 for t in self._robustness_tests if t.passed),
            "accuracy_evaluations": len(self._accuracy_history),
            "latest_accuracy": (
                self._accuracy_history[-1].to_dict()
                if self._accuracy_history else None
            ),
            "statistics_timestamp": datetime.utcnow().isoformat()
        }
