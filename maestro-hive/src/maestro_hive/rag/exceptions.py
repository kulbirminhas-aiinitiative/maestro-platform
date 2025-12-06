"""
RAG Service Exceptions.

EPIC: MD-2499
"""


class RAGError(Exception):
    """Base exception for RAG service errors."""
    pass


class EmbeddingError(RAGError):
    """Error generating embeddings."""
    pass


class StorageError(RAGError):
    """Error with storage operations."""
    pass


class RetrievalError(RAGError):
    """Error during retrieval operations."""
    pass


class PatternExtractionError(RAGError):
    """Error extracting patterns from results."""
    pass
