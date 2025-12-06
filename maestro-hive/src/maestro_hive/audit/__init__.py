"""
Audit & Record Keeping Module for EU AI Act Article 12 Compliance.

This module provides comprehensive audit and record-keeping capabilities:
- AI decision logging with reasoning
- LLM input/output logging with PII masking
- Template usage tracking
- IP attribution (AI vs human)
- Retention policies with auto-archival
- Compliance audit service

EU AI Act Article 12 Requirements:
- Automatic logging of events during system operation
- Traceability of AI system functioning
- Logging capabilities appropriate to intended purpose
- Recording of relevant data for post-market monitoring
"""

from .models import (
    # Enums
    DecisionType,
    ContributorType,
    RetentionTier,
    PIIMaskingLevel,
    AuditEventType,

    # Data models
    DecisionCandidate,
    DecisionRecord,
    LLMCallRecord,
    TemplateUsageRecord,
    IPAttributionRecord,
    RetentionPolicy,
    AuditQueryResult,
    ComplianceReport
)

from .decision_logger import DecisionLogger
from .llm_logger import LLMCallLogger, PIIMasker
from .template_tracker import TemplateTracker
from .ip_attribution import IPAttributionTracker, Contribution
from .retention_manager import RetentionManager
from .audit_service import ComplianceAuditService


__all__ = [
    # Enums
    "DecisionType",
    "ContributorType",
    "RetentionTier",
    "PIIMaskingLevel",
    "AuditEventType",

    # Data models
    "DecisionCandidate",
    "DecisionRecord",
    "LLMCallRecord",
    "TemplateUsageRecord",
    "IPAttributionRecord",
    "RetentionPolicy",
    "AuditQueryResult",
    "ComplianceReport",

    # Services
    "DecisionLogger",
    "LLMCallLogger",
    "PIIMasker",
    "TemplateTracker",
    "IPAttributionTracker",
    "Contribution",
    "RetentionManager",
    "ComplianceAuditService"
]

__version__ = "1.0.0"
