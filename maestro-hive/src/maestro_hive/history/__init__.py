"""
Execution History Store Module

EPIC: MD-2500 - [MAESTRO] Sub-EPIC 7: Execution History Store

This module provides storage and retrieval of execution history for:
- RAG retrieval service integration
- Audit trail
- Learning from past executions

AC-1: pgvector for embeddings storage
AC-2: Efficient similarity queries
AC-3: Retention policy (configurable)
AC-4: Export capability for analysis
"""

from .models import ExecutionRecord, ExecutionStatus, QualityScores
from .store import ExecutionHistoryStore
from .retention import RetentionManager, RetentionConfig
from .export import ExportService, ExportFormat

__all__ = [
    "ExecutionRecord",
    "ExecutionStatus",
    "QualityScores",
    "ExecutionHistoryStore",
    "RetentionManager",
    "RetentionConfig",
    "ExportService",
    "ExportFormat",
]
