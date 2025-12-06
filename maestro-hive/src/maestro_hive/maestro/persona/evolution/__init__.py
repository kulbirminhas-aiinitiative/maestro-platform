"""
Persona Evolution Module.

EPIC: MD-2556 - [PERSONA-ENGINE] Persona Evolution Algorithm - Learn and Improve

Provides evolution capabilities for personas including:
- AC-1: Execution outcomes feed into persona improvement suggestions
- AC-2: Human approval required before persona changes applied
- AC-3: Evolution metrics tracked (success rate improvement over time)
- AC-4: Capability matrix updated based on demonstrated performance
- AC-5: Integration with Learning Engine for feedback loop
"""

from .models import (
    ExecutionOutcome,
    ImprovementSuggestion,
    SuggestionCategory,
    SuggestionStatus,
    CapabilityScore,
    CapabilityMatrix,
    EvolutionMetrics,
    Trend,
)
from .outcome_collector import OutcomeCollector
from .improvement_suggester import ImprovementSuggester
from .approval_gate import ApprovalGate, ApprovalRequest, ApprovalDecision
from .capability_tracker import CapabilityTracker
from .metrics_tracker import MetricsTracker
from .evolution_engine import PersonaEvolutionEngine

__all__ = [
    # Models
    "ExecutionOutcome",
    "ImprovementSuggestion",
    "SuggestionCategory",
    "SuggestionStatus",
    "CapabilityScore",
    "CapabilityMatrix",
    "EvolutionMetrics",
    "Trend",
    # Components
    "OutcomeCollector",
    "ImprovementSuggester",
    "ApprovalGate",
    "ApprovalRequest",
    "ApprovalDecision",
    "CapabilityTracker",
    "MetricsTracker",
    # Engine
    "PersonaEvolutionEngine",
]
