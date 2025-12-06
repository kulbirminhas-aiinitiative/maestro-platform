"""
Self-Healing Mechanism Module for Maestro Platform.

This module implements automatic failure detection and correction capabilities:
- Failure pattern recognition from execution history
- Auto-refactoring for common issues
- RAG-based feedback loop for code improvement
- User feedback integration

Target: Increase Self-Reflection capability from 15% to 80%
"""

from .models import (
    FailureType,
    ActionType,
    FailurePattern,
    HealingAction,
    HealingSession,
    UserFeedback,
)
from .pattern_analyzer import FailurePatternAnalyzer
from .auto_refactor import AutoRefactorEngine
from .rag_feedback import RAGFeedbackLoop
from .user_feedback import UserFeedbackIntegrator
from .healing_service import HealingService

__all__ = [
    # Models
    "FailureType",
    "ActionType",
    "FailurePattern",
    "HealingAction",
    "HealingSession",
    "UserFeedback",
    # Core Components
    "FailurePatternAnalyzer",
    "AutoRefactorEngine",
    "RAGFeedbackLoop",
    "UserFeedbackIntegrator",
    "HealingService",
]

__version__ = "1.0.0"
