"""
Knowledge Store Module for Maestro Platform.

Provides infrastructure for converting, storing, and retrieving
knowledge as semantic embeddings.

EPIC: MD-2557 - Embedding Pipeline
"""

from maestro_hive.knowledge.embeddings import (
    EmbeddingPipeline,
    EmbeddingProvider,
    OpenAIEmbeddingProvider,
    LocalEmbeddingProvider,
    DocumentChunker,
    SemanticChunker,
    FixedSizeChunker,
    CodeChunker,
    ContentCache,
    FileCache,
    InMemoryCache,
    Document,
    EmbeddedDocument,
    EmbeddedChunk,
    ChunkMetadata,
    PipelineConfig,
)

__all__ = [
    # Pipeline
    "EmbeddingPipeline",
    # Providers
    "EmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "LocalEmbeddingProvider",
    # Chunkers
    "DocumentChunker",
    "SemanticChunker",
    "FixedSizeChunker",
    "CodeChunker",
    # Cache
    "ContentCache",
    "FileCache",
    "InMemoryCache",
    # Models
    "Document",
    "EmbeddedDocument",
    "EmbeddedChunk",
    "ChunkMetadata",
    "PipelineConfig",
]

__version__ = "1.0.0"
