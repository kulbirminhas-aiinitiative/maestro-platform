"""
QMS-OPS Automated Compliance Audit System
==========================================

This module provides automated compliance auditing capabilities for
Quality Management Systems (QMS) operations.

Components:
- AuditCore: Core audit scheduling and execution
- RuleEngine: Configurable compliance rule engine
- ReportGenerator: Audit report generation (PDF/HTML)
"""

from .audit_core import AuditCore, AuditExecutor, AuditScheduler, AuditLogger
from .rule_engine import RuleEngine, Rule, RuleResult, Severity
from .report_generator import ReportGenerator, AuditReport, AuditFinding

__version__ = "1.0.0"
__all__ = [
    "AuditCore",
    "AuditExecutor",
    "AuditScheduler",
    "AuditLogger",
    "RuleEngine",
    "Rule",
    "RuleResult",
    "Severity",
    "ReportGenerator",
    "AuditReport",
    "AuditFinding",
]
