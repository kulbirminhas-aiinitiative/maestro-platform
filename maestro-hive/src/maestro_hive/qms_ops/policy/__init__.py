"""
QMS-OPS Policy Automation Package
==================================

Intelligent document and compliance management for QMS.

Modules:
- policy_engine: Document lifecycle and compliance management
"""

from .policy_engine import (
    PolicyEngine,
    Document,
    DocumentType,
    DocumentStatus,
    DocumentVersion,
    DocumentWorkflow,
    RegulatoryRequirement,
    ComplianceMapping,
    ComplianceChecker,
    ComplianceStatus,
    PolicyReview,
    ReviewResult,
)

__all__ = [
    "PolicyEngine",
    "Document",
    "DocumentType",
    "DocumentStatus",
    "DocumentVersion",
    "DocumentWorkflow",
    "RegulatoryRequirement",
    "ComplianceMapping",
    "ComplianceChecker",
    "ComplianceStatus",
    "PolicyReview",
    "ReviewResult",
]

__version__ = "1.0.0"
__epic__ = "MD-2414"
