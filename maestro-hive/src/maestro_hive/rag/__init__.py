"""
RAG Retrieval Service for Maestro Platform.

Query past executions to learn from successes and failures,
injecting context into persona prompts for improved execution quality.

EPIC: MD-2499 - Sub-EPIC 6: RAG Retrieval Service
"""

from maestro_hive.rag.models import (
    ExecutionRecord,
    ExecutionOutcome,
    RetrievalResult,
    SuccessPattern,
    FailurePattern,
    PatternSummary,
    FormattedContext,
    RetrievalConfig,
    ContextConfig,
)
from maestro_hive.rag.embeddings import (
    EmbeddingProvider,
    LocalEmbedding,
    SimpleEmbedding,
    EmbeddingCache,
    CachedEmbeddingProvider,
)
from maestro_hive.rag.storage import (
    StorageBackend,
    InMemoryStorage,
    FileStorage,
)
from maestro_hive.rag.retrieval_service import RetrievalService
from maestro_hive.rag.pattern_extractor import PatternExtractor
from maestro_hive.rag.context_formatter import ContextFormatter
from maestro_hive.rag.exceptions import (
    RAGError,
    EmbeddingError,
    StorageError,
    RetrievalError,
    PatternExtractionError,
)

__all__ = [
    # Models
    "ExecutionRecord",
    "ExecutionOutcome",
    "RetrievalResult",
    "SuccessPattern",
    "FailurePattern",
    "PatternSummary",
    "FormattedContext",
    "RetrievalConfig",
    "ContextConfig",
    # Embeddings
    "EmbeddingProvider",
    "LocalEmbedding",
    "SimpleEmbedding",
    "EmbeddingCache",
    "CachedEmbeddingProvider",
    # Storage
    "StorageBackend",
    "InMemoryStorage",
    "FileStorage",
    # Services
    "RetrievalService",
    "PatternExtractor",
    "ContextFormatter",
    # Exceptions
    "RAGError",
    "EmbeddingError",
    "StorageError",
    "RetrievalError",
    "PatternExtractionError",
]

__version__ = "1.0.0"
