"""
Embedding Pipeline for Knowledge Store.

EPIC: MD-2557
"""

from maestro_hive.knowledge.embeddings.models import (
    Document,
    EmbeddedDocument,
    EmbeddedChunk,
    ChunkMetadata,
    Chunk,
    PipelineConfig,
)
from maestro_hive.knowledge.embeddings.providers import (
    EmbeddingProvider,
    OpenAIEmbeddingProvider,
    LocalEmbeddingProvider,
    SimpleHashEmbeddingProvider,
)
from maestro_hive.knowledge.embeddings.chunker import (
    DocumentChunker,
    SemanticChunker,
    FixedSizeChunker,
    CodeChunker,
)
from maestro_hive.knowledge.embeddings.cache import (
    ContentCache,
    InMemoryCache,
    FileCache,
)
from maestro_hive.knowledge.embeddings.pipeline import EmbeddingPipeline, create_pipeline
from maestro_hive.knowledge.embeddings.providers import create_provider
from maestro_hive.knowledge.embeddings.chunker import create_chunker
from maestro_hive.knowledge.embeddings.exceptions import (
    EmbeddingError,
    ProviderError,
    ChunkingError,
    CacheError,
    RateLimitError,
)

__all__ = [
    # Models
    "Document",
    "EmbeddedDocument",
    "EmbeddedChunk",
    "ChunkMetadata",
    "Chunk",
    "PipelineConfig",
    # Providers
    "EmbeddingProvider",
    "OpenAIEmbeddingProvider",
    "LocalEmbeddingProvider",
    "SimpleHashEmbeddingProvider",
    # Chunkers
    "DocumentChunker",
    "SemanticChunker",
    "FixedSizeChunker",
    "CodeChunker",
    # Cache
    "ContentCache",
    "InMemoryCache",
    "FileCache",
    # Pipeline
    "EmbeddingPipeline",
    "create_pipeline",
    # Factory functions
    "create_provider",
    "create_chunker",
    # Exceptions
    "EmbeddingError",
    "ProviderError",
    "ChunkingError",
    "CacheError",
    "RateLimitError",
]
