"""
MD-2334: AI Security & Robustness
EU AI Act Article 15 Compliance

This module provides security and robustness features for AI systems:
- Error resilience and graceful degradation
- Adversarial attack detection and mitigation
- Model drift monitoring
- Security audit logging
- Recovery and rollback mechanisms
- Operational runbook generation
"""

from .error_resilience import (
    ErrorResilienceManager,
    CircuitBreaker,
    RetryPolicy,
    ErrorCategory,
    ResilienceLevel,
)
from .adversarial_detection import (
    AdversarialDetector,
    InputValidator,
    AttackType,
    ThreatLevel,
    DetectionResult,
)
from .model_drift_monitor import (
    ModelDriftMonitor,
    DriftType,
    DriftSeverity,
    PerformanceMetric,
    DriftAlert,
)
from .security_audit import (
    SecurityAuditLogger,
    AuditEvent,
    AuditCategory,
    ComplianceReport,
)
from .recovery_manager import (
    RecoveryManager,
    RecoveryAction,
    RollbackPoint,
    IncidentResponse,
)
from .runbook_generator import (
    RunbookGenerator,
    OperationalProcedure,
    IncidentPlaybook,
    RunbookSection,
)

__all__ = [
    # Error Resilience
    "ErrorResilienceManager",
    "CircuitBreaker",
    "RetryPolicy",
    "ErrorCategory",
    "ResilienceLevel",
    # Adversarial Detection
    "AdversarialDetector",
    "InputValidator",
    "AttackType",
    "ThreatLevel",
    "DetectionResult",
    # Model Drift
    "ModelDriftMonitor",
    "DriftType",
    "DriftSeverity",
    "PerformanceMetric",
    "DriftAlert",
    # Security Audit
    "SecurityAuditLogger",
    "AuditEvent",
    "AuditCategory",
    "ComplianceReport",
    # Recovery
    "RecoveryManager",
    "RecoveryAction",
    "RollbackPoint",
    "IncidentResponse",
    # Runbook
    "RunbookGenerator",
    "OperationalProcedure",
    "IncidentPlaybook",
    "RunbookSection",
]

__version__ = "1.0.0"
__author__ = "Maestro Platform"
__compliance__ = "EU AI Act Article 15"
