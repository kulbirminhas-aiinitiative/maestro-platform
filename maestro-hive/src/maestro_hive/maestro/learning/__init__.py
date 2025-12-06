"""
Maestro Learning Module - RAG-based Learning Loop

EPIC: MD-2499 - RAG Retrieval Service
EPIC: MD-2500 - Execution History Store
EPIC: MD-2564 - Outcome Capture

Provides:
- RAG retrieval from past executions
- Execution history storage (pgvector)
- Pattern extraction and matching
- Outcome capture with failure categorization
- Human feedback integration
"""

from .rag import RAGRetrievalService
from .history import ExecutionHistoryStore
from .outcome_capture import (
    OutcomeResult,
    FailureCategory,
    FeedbackRating,
    ResourceUsage,
    FailureDetails,
    ExecutionContext,
    HumanFeedback,
    CapturedOutcome,
    KnowledgeStorePersistence,
    OutcomeCaptureService,
)

__all__ = [
    "RAGRetrievalService",
    "ExecutionHistoryStore",
    # MD-2564 - Outcome Capture
    "OutcomeResult",
    "FailureCategory",
    "FeedbackRating",
    "ResourceUsage",
    "FailureDetails",
    "ExecutionContext",
    "HumanFeedback",
    "CapturedOutcome",
    "KnowledgeStorePersistence",
    "OutcomeCaptureService",
]
