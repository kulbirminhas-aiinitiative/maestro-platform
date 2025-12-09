"""
Privacy Compliance Library for GDPR and AI Act

This package provides privacy compliance features for the Maestro platform:
- DPIA (Data Protection Impact Assessment) management
- Data minimization for LLM API calls
- User consent management
- Data retention and auto-deletion
- Right to erasure (RTBF) handling
- Cross-border transfer documentation
- PII anonymization layer

EPIC: MD-2156 - [Compliance] Personal Data & Privacy (GDPR/AI Act)
"""

from .dpia_manager import DPIAManager, DPIAStatus, DPIAReport
from .data_minimizer import DataMinimizer, MinimizationResult
from .consent_manager import ConsentManager, ConsentRecord, ConsentType
from .retention_manager import RetentionManager, RetentionPolicy
from .erasure_handler import ErasureHandler, ErasureRequest, ErasureStatus
from .transfer_documenter import TransferDocumenter, TransferRecord
from .anonymizer import Anonymizer, AnonymizationConfig

__all__ = [
    "DPIAManager",
    "DPIAStatus",
    "DPIAReport",
    "DataMinimizer",
    "MinimizationResult",
    "ConsentManager",
    "ConsentRecord",
    "ConsentType",
    "RetentionManager",
    "RetentionPolicy",
    "ErasureHandler",
    "ErasureRequest",
    "ErasureStatus",
    "TransferDocumenter",
    "TransferRecord",
    "Anonymizer",
    "AnonymizationConfig",
]

__version__ = "1.0.0"
