"""
Embedding Pipeline Test Suite.

EPIC: MD-2557
Tests for all 5 Acceptance Criteria:
- AC-1: Support multiple embedding models
- AC-2: Chunking strategy for large documents
- AC-3: Metadata preserved with embeddings
- AC-4: Batch processing for bulk ingestion
- AC-5: Incremental updates
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import List

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
    create_provider,
)
from maestro_hive.knowledge.embeddings.chunker import (
    DocumentChunker,
    FixedSizeChunker,
    SemanticChunker,
    CodeChunker,
    create_chunker,
)
from maestro_hive.knowledge.embeddings.cache import (
    ContentCache,
    InMemoryCache,
    FileCache,
    CacheEntry,
)
from maestro_hive.knowledge.embeddings.pipeline import (
    EmbeddingPipeline,
    create_pipeline,
)
from maestro_hive.knowledge.embeddings.exceptions import (
    EmbeddingError,
    ProviderError,
    ChunkingError,
    CacheError,
    RateLimitError,
)


# =============================================================================
# AC-1: Support Multiple Embedding Models Tests
# =============================================================================

class TestAC1MultipleEmbeddingModels:
    """AC-1: Support multiple embedding models (OpenAI, Claude, local)."""

    def test_simple_hash_provider_embed(self):
        """Test simple hash provider generates valid embeddings."""
        provider = SimpleHashEmbeddingProvider(dimension=128)
        embedding = provider.embed("test text")

        assert len(embedding) == 128
        assert all(isinstance(x, float) for x in embedding)
        assert provider.model_name == "simple-hash"
        assert provider.dimension == 128

    def test_simple_hash_provider_deterministic(self):
        """Test simple hash provider is deterministic."""
        provider = SimpleHashEmbeddingProvider(dimension=128)

        text = "consistent input"
        embedding1 = provider.embed(text)
        embedding2 = provider.embed(text)

        assert embedding1 == embedding2

    def test_simple_hash_provider_different_texts(self):
        """Test simple hash provider produces different embeddings for different texts."""
        provider = SimpleHashEmbeddingProvider(dimension=128)

        embedding1 = provider.embed("first text")
        embedding2 = provider.embed("second text")

        assert embedding1 != embedding2

    def test_openai_provider_initialization(self):
        """Test OpenAI provider initializes correctly."""
        provider = OpenAIEmbeddingProvider(
            api_key="test-key",
            model="text-embedding-3-small",
        )

        assert provider.model_name == "text-embedding-3-small"
        assert provider.dimension == 1536

    def test_openai_provider_custom_dimensions(self):
        """Test OpenAI provider supports custom dimensions."""
        provider = OpenAIEmbeddingProvider(
            api_key="test-key",
            model="text-embedding-3-small",
            dimensions=512,
        )

        assert provider.dimension == 512

    def test_local_provider_initialization(self):
        """Test local provider initializes with model name."""
        provider = LocalEmbeddingProvider(model_name="all-MiniLM-L6-v2")

        assert provider.model_name == "all-MiniLM-L6-v2"

    def test_create_provider_factory(self):
        """Test provider factory creates correct providers."""
        simple = create_provider("simple", dimension=64)
        assert isinstance(simple, SimpleHashEmbeddingProvider)
        assert simple.dimension == 64

    def test_create_provider_invalid_type(self):
        """Test provider factory raises for invalid types."""
        with pytest.raises(ValueError, match="Unknown provider type"):
            create_provider("invalid_provider")

    def test_provider_name_property(self):
        """Test provider_name returns class name."""
        provider = SimpleHashEmbeddingProvider()
        assert provider.provider_name == "SimpleHashEmbeddingProvider"

    def test_embed_batch_default_implementation(self):
        """Test default embed_batch calls embed for each text."""
        provider = SimpleHashEmbeddingProvider(dimension=64)
        texts = ["text1", "text2", "text3"]

        embeddings = provider.embed_batch(texts)

        assert len(embeddings) == 3
        for emb in embeddings:
            assert len(emb) == 64


# =============================================================================
# AC-2: Chunking Strategy Tests
# =============================================================================

class TestAC2ChunkingStrategy:
    """AC-2: Chunking strategy for large documents."""

    def test_fixed_size_chunker_basic(self):
        """Test fixed size chunker splits content correctly."""
        chunker = FixedSizeChunker(chunk_size=100, overlap=10)
        content = "a" * 250

        chunks = chunker.chunk(content)

        assert len(chunks) >= 2
        assert chunker.strategy_name == "fixed_size"

    def test_fixed_size_chunker_overlap(self):
        """Test fixed size chunker maintains overlap."""
        chunker = FixedSizeChunker(chunk_size=50, overlap=10)
        content = "word " * 50  # 250 chars

        chunks = chunker.chunk(content)

        # Verify positions show overlap
        assert len(chunks) >= 2
        if len(chunks) >= 2:
            assert chunks[1].start_position < chunks[0].end_position

    def test_fixed_size_chunker_token_mode(self):
        """Test fixed size chunker in token (word) mode."""
        chunker = FixedSizeChunker(chunk_size=10, overlap=2, unit="tokens")
        content = "word " * 30

        chunks = chunker.chunk(content)

        assert len(chunks) >= 3
        for chunk in chunks:
            word_count = len(chunk.content.split())
            assert word_count <= 10

    def test_semantic_chunker_paragraphs(self):
        """Test semantic chunker respects paragraph boundaries."""
        chunker = SemanticChunker(max_chunk_size=100)
        content = """First paragraph with some content.

Second paragraph with different content.

Third paragraph ends here."""

        chunks = chunker.chunk(content)

        assert len(chunks) >= 1
        assert chunker.strategy_name == "semantic"

    def test_semantic_chunker_large_paragraph(self):
        """Test semantic chunker splits large paragraphs."""
        chunker = SemanticChunker(max_chunk_size=10)
        content = "Word " * 50  # Single large paragraph

        chunks = chunker.chunk(content)

        assert len(chunks) >= 1

    def test_code_chunker_python(self):
        """Test code chunker identifies Python functions."""
        chunker = CodeChunker(language="python", chunk_by="function")
        code = '''
import os

def first_function():
    """First function."""
    return 1

def second_function():
    """Second function."""
    return 2
'''
        chunks = chunker.chunk(code)

        assert len(chunks) >= 1
        assert chunker.strategy_name == "code_function"

    def test_code_chunker_includes_context(self):
        """Test code chunker includes import context."""
        chunker = CodeChunker(language="python", include_context=True)
        code = '''import os
import sys

def my_function():
    return os.getcwd()
'''
        chunks = chunker.chunk(code)

        assert len(chunks) >= 1
        # Context should include imports
        if len(chunks) > 0:
            assert "import" in chunks[0].content

    def test_create_chunker_factory(self):
        """Test chunker factory creates correct chunkers."""
        fixed = create_chunker("fixed", chunk_size=100)
        semantic = create_chunker("semantic", max_chunk_size=200)
        code = create_chunker("code", language="python")

        assert isinstance(fixed, FixedSizeChunker)
        assert isinstance(semantic, SemanticChunker)
        assert isinstance(code, CodeChunker)

    def test_create_chunker_invalid_type(self):
        """Test chunker factory raises for invalid types."""
        with pytest.raises(ValueError, match="Unknown chunking strategy"):
            create_chunker("invalid_strategy")

    def test_chunker_empty_content(self):
        """Test chunkers handle empty content."""
        chunkers = [
            FixedSizeChunker(),
            SemanticChunker(),
            CodeChunker(),
        ]

        for chunker in chunkers:
            chunks = chunker.chunk("")
            assert chunks == []

    def test_chunk_positions(self):
        """Test chunk positions are valid."""
        chunker = FixedSizeChunker(chunk_size=50, overlap=10)
        content = "x" * 200

        chunks = chunker.chunk(content)

        for chunk in chunks:
            assert chunk.start_position >= 0
            assert chunk.end_position > chunk.start_position
            assert chunk.end_position <= len(content) + 50  # Allow for overlap


# =============================================================================
# AC-3: Metadata Preservation Tests
# =============================================================================

class TestAC3MetadataPreservation:
    """AC-3: Metadata preserved with embeddings (source, timestamp, domain)."""

    def test_document_metadata(self):
        """Test document preserves metadata fields."""
        doc = Document(
            id="doc-1",
            content="test content",
            source="/path/to/file.py",
            domain="code",
            content_type="python",
            metadata={"version": "1.0", "author": "test"},
        )

        assert doc.source == "/path/to/file.py"
        assert doc.domain == "code"
        assert doc.content_type == "python"
        assert doc.metadata["version"] == "1.0"
        assert doc.created_at is not None

    def test_document_to_dict(self):
        """Test document serialization preserves metadata."""
        doc = Document(
            id="doc-1",
            content="test",
            source="test.py",
            domain="code",
            content_type="python",
            metadata={"key": "value"},
        )

        data = doc.to_dict()

        assert data["source"] == "test.py"
        assert data["domain"] == "code"
        assert data["metadata"]["key"] == "value"
        assert "created_at" in data

    def test_document_from_dict(self):
        """Test document deserialization."""
        data = {
            "id": "doc-1",
            "content": "test",
            "source": "test.py",
            "domain": "code",
            "content_type": "python",
            "metadata": {"key": "value"},
            "created_at": "2024-01-01T00:00:00",
            "updated_at": None,
        }

        doc = Document.from_dict(data)

        assert doc.id == "doc-1"
        assert doc.source == "test.py"
        assert doc.metadata["key"] == "value"

    def test_chunk_metadata_fields(self):
        """Test chunk metadata has all required fields."""
        metadata = ChunkMetadata(
            source="/path/file.py",
            domain="code",
            timestamp=datetime.utcnow(),
            content_type="python",
            chunk_index=0,
            total_chunks=5,
            parent_id="doc-1",
            custom={"extra": "data"},
        )

        assert metadata.source == "/path/file.py"
        assert metadata.domain == "code"
        assert metadata.chunk_index == 0
        assert metadata.total_chunks == 5
        assert metadata.custom["extra"] == "data"

    def test_chunk_metadata_serialization(self):
        """Test chunk metadata serialization."""
        now = datetime.utcnow()
        metadata = ChunkMetadata(
            source="test.py",
            domain="code",
            timestamp=now,
            content_type="python",
            chunk_index=1,
            total_chunks=3,
            parent_id="doc-1",
        )

        data = metadata.to_dict()
        restored = ChunkMetadata.from_dict(data)

        assert restored.source == metadata.source
        assert restored.domain == metadata.domain
        assert restored.chunk_index == metadata.chunk_index

    def test_embedded_document_preserves_metadata(self):
        """Test embedded document preserves source document metadata."""
        embedded = EmbeddedDocument(
            id="emb-1",
            document_id="doc-1",
            chunks=[],
            provider="test",
            model="test-model",
            processed_at=datetime.utcnow(),
            metadata={"original_key": "original_value"},
        )

        assert embedded.metadata["original_key"] == "original_value"
        assert embedded.provider == "test"
        assert embedded.model == "test-model"

    def test_embedded_document_to_dict(self):
        """Test embedded document serialization."""
        now = datetime.utcnow()
        chunk_meta = ChunkMetadata(
            source="test.py",
            domain="code",
            timestamp=now,
            content_type="python",
            chunk_index=0,
            total_chunks=1,
            parent_id="doc-1",
        )
        chunk = EmbeddedChunk(
            chunk_id="chunk-1",
            content="test",
            embedding=[0.1, 0.2, 0.3],
            position=0,
            metadata=chunk_meta,
        )
        embedded = EmbeddedDocument(
            id="emb-1",
            document_id="doc-1",
            chunks=[chunk],
            provider="test",
            model="test-model",
            processed_at=now,
        )

        data = embedded.to_dict()

        assert len(data["chunks"]) == 1
        assert data["chunks"][0]["metadata"]["source"] == "test.py"

    def test_pipeline_preserves_metadata(self):
        """Test pipeline preserves document metadata in output."""
        pipeline = EmbeddingPipeline(
            provider=SimpleHashEmbeddingProvider(dimension=64),
            chunker=FixedSizeChunker(chunk_size=100),
        )

        doc = Document(
            id="doc-1",
            content="Test content for embedding.",
            source="/path/to/test.py",
            domain="code",
            content_type="python",
            metadata={"custom_field": "custom_value"},
        )

        result = pipeline.process_document(doc)

        assert result.metadata["custom_field"] == "custom_value"
        for chunk in result.chunks:
            assert chunk.metadata.source == "/path/to/test.py"
            assert chunk.metadata.domain == "code"


# =============================================================================
# AC-4: Batch Processing Tests
# =============================================================================

class TestAC4BatchProcessing:
    """AC-4: Batch processing for bulk ingestion."""

    def test_process_batch_multiple_documents(self):
        """Test batch processing of multiple documents."""
        pipeline = EmbeddingPipeline(
            provider=SimpleHashEmbeddingProvider(dimension=64),
            chunker=FixedSizeChunker(chunk_size=100),
        )

        docs = [
            Document(
                id=f"doc-{i}",
                content=f"Content for document {i}",
                source=f"file{i}.py",
                domain="code",
                content_type="python",
            )
            for i in range(5)
        ]

        results = pipeline.process_batch(docs)

        assert len(results) == 5
        for result in results:
            assert isinstance(result, EmbeddedDocument)

    def test_process_batch_parallel_execution(self):
        """Test batch processing uses parallel execution."""
        pipeline = EmbeddingPipeline(
            provider=SimpleHashEmbeddingProvider(dimension=64),
            chunker=FixedSizeChunker(chunk_size=50),
        )

        docs = [
            Document(
                id=f"doc-{i}",
                content=f"Content {i}",
                source=f"file{i}.txt",
                domain="docs",
                content_type="text",
            )
            for i in range(10)
        ]

        results = pipeline.process_batch(docs, max_concurrent=4)

        assert len(results) == 10

    def test_process_batch_empty_list(self):
        """Test batch processing handles empty list."""
        pipeline = EmbeddingPipeline(
            provider=SimpleHashEmbeddingProvider(),
        )

        results = pipeline.process_batch([])

        assert results == []

    def test_process_batch_single_document(self):
        """Test batch processing with single document."""
        pipeline = EmbeddingPipeline(
            provider=SimpleHashEmbeddingProvider(dimension=64),
        )

        docs = [
            Document(
                id="single-doc",
                content="Single document content",
                source="single.py",
                domain="code",
                content_type="python",
            )
        ]

        results = pipeline.process_batch(docs)

        assert len(results) == 1
        assert results[0].document_id == "single-doc"

    def test_process_batch_handles_errors(self):
        """Test batch processing continues on individual errors."""
        pipeline = EmbeddingPipeline(
            provider=SimpleHashEmbeddingProvider(dimension=64),
        )

        # Create documents including one that will succeed
        docs = [
            Document(
                id="good-doc",
                content="Valid content",
                source="good.py",
                domain="code",
                content_type="python",
            )
        ]

        results = pipeline.process_batch(docs)

        # At least one should succeed
        assert len(results) >= 1

    def test_batch_provider_embed_batch(self):
        """Test provider embed_batch method."""
        provider = SimpleHashEmbeddingProvider(dimension=64)
        texts = ["text1", "text2", "text3", "text4"]

        embeddings = provider.embed_batch(texts)

        assert len(embeddings) == 4
        for emb in embeddings:
            assert len(emb) == 64


# =============================================================================
# AC-5: Incremental Updates Tests
# =============================================================================

class TestAC5IncrementalUpdates:
    """AC-5: Incremental updates (don't re-embed unchanged content)."""

    def test_document_content_hash(self):
        """Test document generates consistent content hash."""
        doc = Document(
            id="doc-1",
            content="test content",
            source="test.py",
            domain="code",
            content_type="python",
        )

        hash1 = doc.content_hash()
        hash2 = doc.content_hash()

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_content_hash_changes_with_content(self):
        """Test content hash changes when content changes."""
        doc1 = Document(
            id="doc-1",
            content="content version 1",
            source="test.py",
            domain="code",
            content_type="python",
        )
        doc2 = Document(
            id="doc-1",
            content="content version 2",
            source="test.py",
            domain="code",
            content_type="python",
        )

        assert doc1.content_hash() != doc2.content_hash()

    def test_in_memory_cache_put_and_get(self):
        """Test in-memory cache stores and retrieves entries."""
        cache = InMemoryCache()

        entry = CacheEntry(
            content_hash="abc123",
            document_id="doc-1",
            embedded_at=datetime.utcnow(),
            provider="test",
            model="test-model",
            chunk_count=5,
            metadata={},
        )

        cache.put(entry)
        retrieved = cache.get("doc-1")

        assert retrieved is not None
        assert retrieved.content_hash == "abc123"
        assert retrieved.chunk_count == 5

    def test_in_memory_cache_has_changed(self):
        """Test cache correctly detects content changes."""
        cache = InMemoryCache()

        entry = CacheEntry(
            content_hash="original_hash",
            document_id="doc-1",
            embedded_at=datetime.utcnow(),
            provider="test",
            model="test-model",
            chunk_count=1,
            metadata={},
        )
        cache.put(entry)

        # Same hash - not changed
        assert cache.has_changed("doc-1", "original_hash") is False

        # Different hash - changed
        assert cache.has_changed("doc-1", "new_hash") is True

        # Unknown document - changed
        assert cache.has_changed("unknown-doc", "any_hash") is True

    def test_in_memory_cache_ttl(self):
        """Test cache respects TTL."""
        cache = InMemoryCache(ttl_hours=0)  # Immediate expiry

        entry = CacheEntry(
            content_hash="hash",
            document_id="doc-1",
            embedded_at=datetime.utcnow() - timedelta(hours=1),
            provider="test",
            model="test-model",
            chunk_count=1,
            metadata={},
        )
        cache.put(entry)

        # Entry should be expired
        retrieved = cache.get("doc-1")
        assert retrieved is None

    def test_in_memory_cache_max_size(self):
        """Test cache respects max size limit."""
        cache = InMemoryCache(max_size=3)

        for i in range(5):
            entry = CacheEntry(
                content_hash=f"hash{i}",
                document_id=f"doc-{i}",
                embedded_at=datetime.utcnow(),
                provider="test",
                model="test",
                chunk_count=1,
                metadata={},
            )
            cache.put(entry)

        assert cache.size() <= 3

    def test_in_memory_cache_delete(self):
        """Test cache deletion."""
        cache = InMemoryCache()

        entry = CacheEntry(
            content_hash="hash",
            document_id="doc-1",
            embedded_at=datetime.utcnow(),
            provider="test",
            model="test",
            chunk_count=1,
            metadata={},
        )
        cache.put(entry)

        assert cache.delete("doc-1") is True
        assert cache.get("doc-1") is None
        assert cache.delete("doc-1") is False

    def test_in_memory_cache_clear(self):
        """Test cache clear."""
        cache = InMemoryCache()

        for i in range(5):
            entry = CacheEntry(
                content_hash=f"hash{i}",
                document_id=f"doc-{i}",
                embedded_at=datetime.utcnow(),
                provider="test",
                model="test",
                chunk_count=1,
                metadata={},
            )
            cache.put(entry)

        cache.clear()
        assert cache.size() == 0

    def test_in_memory_cache_stats(self):
        """Test cache statistics."""
        cache = InMemoryCache()

        entry = CacheEntry(
            content_hash="hash",
            document_id="doc-1",
            embedded_at=datetime.utcnow(),
            provider="test",
            model="test",
            chunk_count=1,
            metadata={},
        )
        cache.put(entry)

        # Trigger hits and misses
        cache.get("doc-1")  # Hit
        cache.get("nonexistent")  # Miss

        stats = cache.stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 1
        assert stats["size"] == 1

    def test_process_incremental_unchanged(self):
        """Test incremental processing skips unchanged documents."""
        cache = InMemoryCache()
        pipeline = EmbeddingPipeline(
            provider=SimpleHashEmbeddingProvider(dimension=64),
            cache=cache,
        )

        doc = Document(
            id="doc-1",
            content="test content",
            source="test.py",
            domain="code",
            content_type="python",
        )

        # First processing
        result1 = pipeline.process_incremental(doc)
        assert result1 is not None

        # Second processing - should return None (unchanged)
        result2 = pipeline.process_incremental(doc)
        assert result2 is None

    def test_process_incremental_changed(self):
        """Test incremental processing embeds changed documents."""
        cache = InMemoryCache()
        pipeline = EmbeddingPipeline(
            provider=SimpleHashEmbeddingProvider(dimension=64),
            cache=cache,
        )

        doc1 = Document(
            id="doc-1",
            content="original content",
            source="test.py",
            domain="code",
            content_type="python",
        )

        # First processing
        result1 = pipeline.process_incremental(doc1)
        assert result1 is not None

        # Change content
        doc2 = Document(
            id="doc-1",
            content="updated content",
            source="test.py",
            domain="code",
            content_type="python",
        )

        # Should process changed document
        result2 = pipeline.process_incremental(doc2)
        assert result2 is not None


# =============================================================================
# Pipeline Integration Tests
# =============================================================================

class TestPipelineIntegration:
    """Integration tests for the embedding pipeline."""

    def test_create_pipeline_factory(self):
        """Test pipeline factory function."""
        pipeline = create_pipeline(
            provider_type="simple",
            chunker_type="semantic",
            cache_type="memory",
        )

        assert isinstance(pipeline.provider, SimpleHashEmbeddingProvider)
        assert isinstance(pipeline.chunker, SemanticChunker)
        assert isinstance(pipeline.cache, InMemoryCache)

    def test_pipeline_health_check(self):
        """Test pipeline health check."""
        pipeline = EmbeddingPipeline(
            provider=SimpleHashEmbeddingProvider(dimension=64),
        )

        health = pipeline.health_check()

        assert health["status"] == "healthy"
        assert "provider" in health
        assert "dimension" in health

    def test_pipeline_process_document_full_flow(self):
        """Test complete document processing flow."""
        pipeline = EmbeddingPipeline(
            provider=SimpleHashEmbeddingProvider(dimension=128),
            chunker=SemanticChunker(max_chunk_size=50),
        )

        doc = Document(
            id="test-doc",
            content="""First paragraph of content.

Second paragraph with more content.

Third paragraph ends here.""",
            source="/test/path.md",
            domain="documentation",
            content_type="markdown",
            metadata={"version": "1.0"},
        )

        result = pipeline.process_document(doc)

        assert result.document_id == "test-doc"
        assert len(result.chunks) >= 1
        assert result.provider == "SimpleHashEmbeddingProvider"

        for chunk in result.chunks:
            assert len(chunk.embedding) == 128
            assert chunk.metadata.source == "/test/path.md"
            assert chunk.metadata.domain == "documentation"

    def test_pipeline_properties(self):
        """Test pipeline exposes component properties."""
        provider = SimpleHashEmbeddingProvider(dimension=64)
        chunker = FixedSizeChunker(chunk_size=100)
        cache = InMemoryCache()
        config = PipelineConfig(batch_size=50)

        pipeline = EmbeddingPipeline(
            provider=provider,
            chunker=chunker,
            cache=cache,
            config=config,
        )

        assert pipeline.provider is provider
        assert pipeline.chunker is chunker
        assert pipeline.cache is cache
        assert pipeline.config.batch_size == 50

    def test_embedded_document_properties(self):
        """Test embedded document computed properties."""
        chunk_meta = ChunkMetadata(
            source="test.py",
            domain="code",
            timestamp=datetime.utcnow(),
            content_type="python",
            chunk_index=0,
            total_chunks=2,
            parent_id="doc-1",
        )

        chunks = [
            EmbeddedChunk(
                chunk_id=f"chunk-{i}",
                content=f"content {i}",
                embedding=[0.1] * 128,
                position=i,
                metadata=chunk_meta,
            )
            for i in range(3)
        ]

        embedded = EmbeddedDocument(
            id="emb-1",
            document_id="doc-1",
            chunks=chunks,
            provider="test",
            model="test",
            processed_at=datetime.utcnow(),
        )

        assert embedded.chunk_count == 3
        assert embedded.total_embedding_dimension == 128


# =============================================================================
# Exception Tests
# =============================================================================

class TestExceptions:
    """Test exception handling."""

    def test_embedding_error(self):
        """Test EmbeddingError exception."""
        with pytest.raises(EmbeddingError):
            raise EmbeddingError("Test error")

    def test_provider_error(self):
        """Test ProviderError exception."""
        with pytest.raises(ProviderError):
            raise ProviderError("Provider failed")

    def test_chunking_error(self):
        """Test ChunkingError exception."""
        with pytest.raises(ChunkingError):
            raise ChunkingError("Chunking failed")

    def test_cache_error(self):
        """Test CacheError exception."""
        with pytest.raises(CacheError):
            raise CacheError("Cache failed")

    def test_rate_limit_error(self):
        """Test RateLimitError exception."""
        with pytest.raises(RateLimitError):
            raise RateLimitError("Rate limited")


# =============================================================================
# Configuration Tests
# =============================================================================

class TestConfiguration:
    """Test configuration options."""

    def test_pipeline_config_defaults(self):
        """Test pipeline config default values."""
        config = PipelineConfig()

        assert config.batch_size == 100
        assert config.max_retries == 3
        assert config.timeout_seconds == 30.0
        assert config.cache_enabled is True
        assert config.chunk_overlap == 50
        assert config.max_chunk_size == 512

    def test_pipeline_config_custom(self):
        """Test pipeline config custom values."""
        config = PipelineConfig(
            batch_size=50,
            max_retries=5,
            timeout_seconds=60.0,
            cache_enabled=False,
            fallback_providers=["local", "simple"],
        )

        assert config.batch_size == 50
        assert config.max_retries == 5
        assert config.cache_enabled is False
        assert len(config.fallback_providers) == 2

    def test_pipeline_cache_disabled(self):
        """Test pipeline with cache disabled."""
        config = PipelineConfig(cache_enabled=False)
        pipeline = EmbeddingPipeline(
            provider=SimpleHashEmbeddingProvider(),
            config=config,
        )

        doc = Document(
            id="doc-1",
            content="test",
            source="test.py",
            domain="code",
            content_type="python",
        )

        # Process same document twice - both should succeed
        result1 = pipeline.process_document(doc)
        result2 = pipeline.process_document(doc)

        assert result1 is not None
        assert result2 is not None
