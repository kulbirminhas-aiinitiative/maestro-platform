"""
QMS-OPS CAPA & NC Management Package
====================================

AI-Powered CAPA (Corrective and Preventive Action) and 
Non-Conformance Management System.

Modules:
- capa_manager: CAPA lifecycle management
- nc_tracker: Non-Conformance tracking
- root_cause_analyzer: AI-powered root cause analysis
- effectiveness_predictor: CAPA effectiveness prediction

Regulatory Compliance:
- ISO 13485:2016 Clause 8.5 (Improvement)
- FDA 21 CFR 820.100 (CAPA)
- EU MDR Article 10 (Post-Market Surveillance)
"""

from .capa_manager import (
    CAPA,
    CAPAAction,
    CAPAStatus,
    CAPAType,
    CAPAManager,
    CAPAWorkflow,
    Priority,
)

from .nc_tracker import (
    NonConformance,
    NCStatus,
    NCSeverity,
    NCCategory,
    NCTracker,
    NCWorkflow,
    ContainmentAction,
)

from .root_cause_analyzer import (
    RootCauseAnalyzer,
    AnalysisMethod,
    CauseCategory,
    RootCauseResult,
    FiveWhysAnalyzer,
    FishboneAnalyzer,
)

from .effectiveness_predictor import (
    EffectivenessPredictor,
    EffectivenessRating,
    EffectivenessPrediction,
    SimilarCAPAFinder,
)

__all__ = [
    # CAPA Manager
    "CAPA",
    "CAPAAction",
    "CAPAStatus",
    "CAPAType",
    "CAPAManager",
    "CAPAWorkflow",
    "Priority",
    # NC Tracker
    "NonConformance",
    "NCStatus",
    "NCSeverity",
    "NCCategory",
    "NCTracker",
    "NCWorkflow",
    "ContainmentAction",
    # Root Cause Analyzer
    "RootCauseAnalyzer",
    "AnalysisMethod",
    "CauseCategory",
    "RootCauseResult",
    "FiveWhysAnalyzer",
    "FishboneAnalyzer",
    # Effectiveness Predictor
    "EffectivenessPredictor",
    "EffectivenessRating",
    "EffectivenessPrediction",
    "SimilarCAPAFinder",
]

__version__ = "1.0.0"
__epic__ = "MD-2403"
