"""
Verification & Validation Module.

EPIC: MD-2521 - [SDLC-Phase7] Verification & Validation - Quality Gates, Compliance, and Audit

This module provides comprehensive V&V capabilities:

1. Quality Gate Engine (AC-1)
   - Configurable gates with pass/fail thresholds
   - Policy-based enforcement (mandatory, advisory, blocking)
   - Gate result caching for performance
   - CI/CD pipeline integration

2. Compliance Checker (AC-2)
   - Rule-based validation engine
   - Standard templates (SOC2, GDPR, HIPAA patterns)
   - Evidence collection and linking
   - Remediation guidance generation

3. Audit Trail Generator (AC-3)
   - Immutable event logging
   - SHA-256 hash chain verification
   - Retention policy enforcement
   - Export formats (JSON, CSV)

4. Validation Report Builder (AC-4)
   - Traceability matrix generation
   - Coverage analysis (requirements to tests)
   - Gap identification
   - Executive summary with metrics
"""

from .gates import (
    GateEngine,
    GatePolicy,
    GateResult,
    GateStatus,
    GateType,
    QualityGate,
    BUILTIN_GATES,
    create_standard_policy,
    test_coverage_evaluator,
    test_pass_rate_evaluator,
    code_complexity_evaluator,
    security_scan_evaluator,
)

from .compliance import (
    ComplianceChecker,
    ComplianceReport,
    ComplianceRule,
    ComplianceStandard,
    Evidence,
    RemediationGuidance,
    RuleResult,
    RuleSeverity,
    RuleStatus,
    SOC2_RULES,
    GDPR_RULES,
    create_compliance_checker_with_defaults,
)

from .audit import (
    AuditEntry,
    AuditOutcome,
    AuditTrail,
    EventType,
    RetentionPolicy,
    create_audit_trail_with_defaults,
)

from .report import (
    CoverageGap,
    CoverageStatus,
    ReportBuilder,
    Requirement,
    TestCase,
    TraceabilityLink,
    TraceabilityMatrix,
    ValidationReport,
    ValidationStatus,
)

__version__ = "1.0.0"

__all__ = [
    # Gates (AC-1)
    "GateEngine",
    "GatePolicy",
    "GateResult",
    "GateStatus",
    "GateType",
    "QualityGate",
    "BUILTIN_GATES",
    "create_standard_policy",
    "test_coverage_evaluator",
    "test_pass_rate_evaluator",
    "code_complexity_evaluator",
    "security_scan_evaluator",
    # Compliance (AC-2)
    "ComplianceChecker",
    "ComplianceReport",
    "ComplianceRule",
    "ComplianceStandard",
    "Evidence",
    "RemediationGuidance",
    "RuleResult",
    "RuleSeverity",
    "RuleStatus",
    "SOC2_RULES",
    "GDPR_RULES",
    "create_compliance_checker_with_defaults",
    # Audit (AC-3)
    "AuditEntry",
    "AuditOutcome",
    "AuditTrail",
    "EventType",
    "RetentionPolicy",
    "create_audit_trail_with_defaults",
    # Report (AC-4)
    "CoverageGap",
    "CoverageStatus",
    "ReportBuilder",
    "Requirement",
    "TestCase",
    "TraceabilityLink",
    "TraceabilityMatrix",
    "ValidationReport",
    "ValidationStatus",
]
