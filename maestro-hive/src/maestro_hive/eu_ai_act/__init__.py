"""
EU AI Act & GDPR Compliance Module (MD-2332)

Umbrella module for EU AI Act Articles 10-17, 52, 53 compliance.
Covers Transparency, Privacy, Fairness, Oversight, Security, and QMS.
"""

from .data_governance import DataGovernance, DatasetQualityReport, BiasReport
from .technical_documentation import TechnicalDocumentation, DocumentationType
from .record_keeper import RecordKeeper, AuditEvent, AuditEventType
from .transparency_manager import TransparencyManager, TransparencyReport
from .human_oversight import HumanOversight, OversightRequest, OversightStatus
from .robustness_security import RobustnessSecurity, SecurityAssessment
from .ai_disclosure import AIDisclosure, DisclosureType, DisclosureRecord
from .sandbox_framework import SandboxFramework, SandboxSession, SandboxStatus

__all__ = [
    # Data Governance (Article 10)
    "DataGovernance",
    "DatasetQualityReport",
    "BiasReport",
    # Technical Documentation (Article 11)
    "TechnicalDocumentation",
    "DocumentationType",
    # Record Keeping (Article 12)
    "RecordKeeper",
    "AuditEvent",
    "AuditEventType",
    # Transparency (Article 13)
    "TransparencyManager",
    "TransparencyReport",
    # Human Oversight (Article 14)
    "HumanOversight",
    "OversightRequest",
    "OversightStatus",
    # Robustness & Security (Article 15)
    "RobustnessSecurity",
    "SecurityAssessment",
    # AI Disclosure (Article 52)
    "AIDisclosure",
    "DisclosureType",
    "DisclosureRecord",
    # Sandbox Framework (Article 53)
    "SandboxFramework",
    "SandboxSession",
    "SandboxStatus",
]

__version__ = "1.0.0"
