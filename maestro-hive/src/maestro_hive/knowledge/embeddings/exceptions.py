"""
Embedding Pipeline Exceptions.

EPIC: MD-2557
"""


class EmbeddingError(Exception):
    """Base exception for embedding pipeline errors."""
    pass


class ProviderError(EmbeddingError):
    """Error from embedding provider."""
    pass


class ChunkingError(EmbeddingError):
    """Error during document chunking."""
    pass


class CacheError(EmbeddingError):
    """Error with embedding cache."""
    pass


class RateLimitError(ProviderError):
    """Rate limit exceeded by provider."""

    def __init__(self, message: str, retry_after: float = 60.0):
        super().__init__(message)
        self.retry_after = retry_after
