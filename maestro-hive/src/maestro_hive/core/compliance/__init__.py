"""
Core Compliance Module
======================

Provides compliance validation, audit logging, and input sanitization
for core services and CLI operations.

EPIC: MD-2801 - Core Services & CLI Compliance (Batch 2)

Components:
    - ComplianceValidator: Pre/post execution compliance validation
    - AuditLogger: Structured audit logging for CLI operations
    - InputSanitizer: Input validation and security sanitization
    - StateComplianceAuditor: State checkpoint integrity validation
"""

from .compliance_validator import (
    ComplianceValidator,
    ValidationResult,
    ValidationLevel,
    ComplianceReport,
    get_compliance_validator,
)
from .audit_logger import (
    AuditLogger,
    AuditEntry,
    AuditLevel,
    get_audit_logger,
)
from .input_sanitizer import (
    InputSanitizer,
    SanitizationResult,
    SecurityWarning,
    SanitizationPattern,
)
from .state_auditor import (
    StateComplianceAuditor,
    AuditResult,
    IntegrityStatus,
)

__all__ = [
    # Compliance Validator
    "ComplianceValidator",
    "ValidationResult",
    "ValidationLevel",
    "ComplianceReport",
    "get_compliance_validator",
    # Audit Logger
    "AuditLogger",
    "AuditEntry",
    "AuditLevel",
    "get_audit_logger",
    # Input Sanitizer
    "InputSanitizer",
    "SanitizationResult",
    "SecurityWarning",
    "SanitizationPattern",
    # State Auditor
    "StateComplianceAuditor",
    "AuditResult",
    "IntegrityStatus",
]

__version__ = "1.0.0"
