"""
QMS-OPS Continuous Improvement AI Engine
=========================================

AI-powered continuous improvement engine for pattern recognition,
recommendation generation, and initiative tracking.

Modules:
- pattern_analyzer: Cross-system pattern analysis
- recommendation_engine: AI-generated improvement recommendations
- initiative_tracker: Initiative tracking and effectiveness scoring
"""

from .pattern_analyzer import (
    PatternAnalyzer,
    PatternMatcher,
    TrendDetector,
    CorrelationAnalyzer,
    Pattern,
    PatternType,
    TrendDirection,
    QualityEvent,
    DataSource,
)

from .recommendation_engine import (
    RecommendationEngine,
    Recommendation,
    RecommendationType,
    ImplementationEffort,
    CostEstimate,
    ROICalculator,
    Priority,
)

from .initiative_tracker import (
    InitiativeTracker,
    Initiative,
    InitiativeStatus,
    Milestone,
    MetricMeasurement,
    EffectivenessRating,
    EffectivenessCalculator,
)

__all__ = [
    # Pattern Analyzer
    "PatternAnalyzer",
    "PatternMatcher",
    "TrendDetector",
    "CorrelationAnalyzer",
    "Pattern",
    "PatternType",
    "TrendDirection",
    "QualityEvent",
    "DataSource",
    # Recommendation Engine
    "RecommendationEngine",
    "Recommendation",
    "RecommendationType",
    "ImplementationEffort",
    "CostEstimate",
    "ROICalculator",
    "Priority",
    # Initiative Tracker
    "InitiativeTracker",
    "Initiative",
    "InitiativeStatus",
    "Milestone",
    "MetricMeasurement",
    "EffectivenessRating",
    "EffectivenessCalculator",
]

__version__ = "1.0.0"
__epic__ = "MD-2409"
