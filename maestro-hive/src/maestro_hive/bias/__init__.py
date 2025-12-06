"""
Bias Detection and Mitigation Module (MD-2157)

EU AI Act Compliance - Article 10

This module provides bias detection and mitigation capabilities for the
Maestro DDE (Decision & Delivery Engine) to ensure fairness in:
- Task assignment
- Agent evaluation
- Quality scoring

Components:
- BiasAuditLogger: Records decisions for audit trails
- FairnessWeightCalculator: Computes fairness-adjusted weights
- AdaptiveScorer: Replaces hard thresholds with adaptive scoring
- CoolingOffManager: Manages agent selection cooling-off periods
- BiasIncidentReporter: Handles bias incident reporting
- FairnessAuditor: Performs periodic fairness audits
- BiasService: Main orchestration service
"""

from .models import (
    BiasVector,
    BiasSeverity,
    BiasVectorType,
    AuditRecord,
    AuditEventType,
    FairnessWeight,
    CoolingOffPeriod,
    BiasIncident,
    IncidentStatus,
    FairnessAuditResult,
    AdaptiveThreshold
)

from .audit_logger import BiasAuditLogger, get_audit_logger
from .fairness_weights import FairnessWeightCalculator, get_fairness_calculator
from .adaptive_scorer import AdaptiveScorer, get_adaptive_scorer
from .cooling_off import CoolingOffManager, get_cooling_off_manager
from .incident_reporter import BiasIncidentReporter, get_incident_reporter
from .fairness_auditor import FairnessAuditor, get_fairness_auditor
from .bias_service import BiasService, get_bias_service

__all__ = [
    # Models
    'BiasVector',
    'BiasSeverity',
    'BiasVectorType',
    'AuditRecord',
    'AuditEventType',
    'FairnessWeight',
    'CoolingOffPeriod',
    'BiasIncident',
    'IncidentStatus',
    'FairnessAuditResult',
    'AdaptiveThreshold',

    # Components
    'BiasAuditLogger',
    'get_audit_logger',
    'FairnessWeightCalculator',
    'get_fairness_calculator',
    'AdaptiveScorer',
    'get_adaptive_scorer',
    'CoolingOffManager',
    'get_cooling_off_manager',
    'BiasIncidentReporter',
    'get_incident_reporter',
    'FairnessAuditor',
    'get_fairness_auditor',
    'BiasService',
    'get_bias_service'
]
