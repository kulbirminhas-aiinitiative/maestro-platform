"""
Tests for Embedding Pipeline Module.

EPIC: MD-2557
Tests for AC-1 through AC-5 implementation.
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from maestro_hive.knowledge.embeddings.models import (
    ChunkMetadata,
    Document,
    EmbeddedDocument,
    PipelineConfig,
    Chunk,
    EmbeddedChunk,
)
from maestro_hive.knowledge.embeddings.providers import (
    EmbeddingProvider,
    SimpleHashEmbeddingProvider,
    OpenAIEmbeddingProvider,
    LocalEmbeddingProvider,
)
from maestro_hive.knowledge.embeddings.chunker import (
    DocumentChunker,
    FixedSizeChunker,
    SemanticChunker,
    CodeChunker,
)
from maestro_hive.knowledge.embeddings.cache import (
    ContentCache,
    InMemoryCache,
    FileCache,
    CacheEntry,
)
from maestro_hive.knowledge.embeddings.pipeline import EmbeddingPipeline


class TestEmbeddingProviders:
    """Tests for embedding providers (AC-1)."""

    def test_simple_hash_provider(self):
        """Test SimpleHashEmbeddingProvider creates valid embeddings."""
        provider = SimpleHashEmbeddingProvider(dimension=128)

        embedding = provider.embed("Hello, world!")

        assert len(embedding) == 128
        assert all(isinstance(x, float) for x in embedding)
        assert provider.model_name == "simple-hash"
        assert provider.dimension == 128

    def test_simple_hash_consistency(self):
        """Test same input produces same embedding."""
        provider = SimpleHashEmbeddingProvider()

        emb1 = provider.embed("test content")
        emb2 = provider.embed("test content")

        assert emb1 == emb2

    def test_simple_hash_batch(self):
        """Test batch embedding works."""
        provider = SimpleHashEmbeddingProvider()

        texts = ["hello", "world", "test"]
        embeddings = provider.embed_batch(texts)

        assert len(embeddings) == 3
        assert all(len(e) == provider.dimension for e in embeddings)

    def test_openai_provider_init(self):
        """Test OpenAI provider initialization (AC-1)."""
        provider = OpenAIEmbeddingProvider(
            api_key="test-key",
            model="text-embedding-3-small"
        )

        assert provider.model_name == "text-embedding-3-small"
        assert provider.dimension == 1536

    def test_local_provider_init(self):
        """Test local provider initialization (AC-1)."""
        provider = LocalEmbeddingProvider(
            model_name="all-MiniLM-L6-v2"
        )

        assert provider.model_name == "all-MiniLM-L6-v2"

    def test_provider_interface(self):
        """Test all providers implement required interface (AC-1)."""
        # Only test providers that don't require external dependencies
        providers = [
            SimpleHashEmbeddingProvider(),
            OpenAIEmbeddingProvider(api_key="test"),
        ]

        for provider in providers:
            assert hasattr(provider, "embed")
            assert hasattr(provider, "embed_batch")
            assert hasattr(provider, "dimension")
            assert hasattr(provider, "model_name")
            assert hasattr(provider, "provider_name")

        # LocalEmbeddingProvider requires sentence-transformers
        local_provider = LocalEmbeddingProvider()
        assert hasattr(local_provider, "embed")
        assert hasattr(local_provider, "embed_batch")
        assert hasattr(local_provider, "model_name")


class TestDocumentChunkers:
    """Tests for document chunking (AC-2)."""

    def test_fixed_size_chunker(self):
        """Test FixedSizeChunker creates fixed-size chunks."""
        chunker = FixedSizeChunker(chunk_size=100, overlap=10)
        content = "word " * 100  # 500 characters

        chunks = chunker.chunk(content)

        assert len(chunks) > 1
        assert all(isinstance(c, Chunk) for c in chunks)
        assert chunker.strategy_name == "fixed_size"

    def test_semantic_chunker(self):
        """Test SemanticChunker respects paragraph boundaries (AC-2)."""
        chunker = SemanticChunker(max_chunk_size=50)
        content = """
First paragraph with some content.

Second paragraph with more content.

Third paragraph with additional text.
        """.strip()

        chunks = chunker.chunk(content)

        assert len(chunks) >= 1
        assert chunker.strategy_name == "semantic"

    def test_code_chunker_python(self):
        """Test CodeChunker handles Python code (AC-2)."""
        chunker = CodeChunker(language="python")
        code = '''
import os

def hello():
    """Say hello."""
    print("Hello")

def world():
    """Say world."""
    print("World")

class MyClass:
    """A class."""
    def method(self):
        pass
'''

        chunks = chunker.chunk(code)

        assert len(chunks) >= 1
        assert "code" in chunker.strategy_name

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

    def test_chunker_preserves_positions(self):
        """Test chunkers track position information."""
        chunker = FixedSizeChunker(chunk_size=50, overlap=0)
        content = "a" * 100

        chunks = chunker.chunk(content)

        assert chunks[0].start_position == 0
        for chunk in chunks:
            assert chunk.start_position >= 0
            assert chunk.end_position > chunk.start_position


class TestContentCache:
    """Tests for content caching (AC-5)."""

    def test_in_memory_cache(self):
        """Test InMemoryCache basic operations."""
        cache = InMemoryCache()

        entry = CacheEntry(
            content_hash="abc123",
            document_id="doc1",
            embedded_at=datetime.utcnow(),
            provider="test",
            model="test-model",
            chunk_count=5,
            metadata={},
        )

        cache.put(entry)
        retrieved = cache.get("doc1")

        assert retrieved is not None
        assert retrieved.content_hash == "abc123"
        assert cache.size() == 1

    def test_in_memory_cache_has_changed(self):
        """Test incremental update detection (AC-5)."""
        cache = InMemoryCache()

        entry = CacheEntry(
            content_hash="abc123",
            document_id="doc1",
            embedded_at=datetime.utcnow(),
            provider="test",
            model="test-model",
            chunk_count=5,
            metadata={},
        )
        cache.put(entry)

        # Same hash - not changed
        assert not cache.has_changed("doc1", "abc123")

        # Different hash - changed
        assert cache.has_changed("doc1", "xyz789")

        # New document - changed
        assert cache.has_changed("doc2", "any_hash")

    def test_in_memory_cache_ttl(self):
        """Test cache TTL expiration."""
        cache = InMemoryCache(ttl_hours=0)  # Immediate expiration

        entry = CacheEntry(
            content_hash="abc123",
            document_id="doc1",
            embedded_at=datetime.utcnow() - timedelta(hours=1),
            provider="test",
            model="test-model",
            chunk_count=5,
            metadata={},
        )
        cache._cache["doc1"] = entry  # Bypass put to avoid refresh

        # Should return None due to TTL
        assert cache.get("doc1") is None

    def test_in_memory_cache_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = InMemoryCache(max_size=2)

        for i in range(3):
            entry = CacheEntry(
                content_hash=f"hash{i}",
                document_id=f"doc{i}",
                embedded_at=datetime.utcnow(),
                provider="test",
                model="test",
                chunk_count=1,
                metadata={},
            )
            cache.put(entry)

        # First entry should be evicted
        assert cache.get("doc0") is None
        assert cache.get("doc1") is not None
        assert cache.get("doc2") is not None
        assert cache.size() == 2

    def test_file_cache(self):
        """Test FileCache basic operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = FileCache(cache_dir=tmpdir)

            entry = CacheEntry(
                content_hash="abc123",
                document_id="doc1",
                embedded_at=datetime.utcnow(),
                provider="test",
                model="test-model",
                chunk_count=5,
                metadata={"key": "value"},
            )

            cache.put(entry)
            retrieved = cache.get("doc1")

            assert retrieved is not None
            assert retrieved.content_hash == "abc123"
            assert retrieved.metadata == {"key": "value"}


class TestChunkMetadata:
    """Tests for metadata preservation (AC-3)."""

    def test_metadata_creation(self):
        """Test ChunkMetadata creation and serialization."""
        metadata = ChunkMetadata(
            source="/path/to/file.py",
            domain="code",
            timestamp=datetime.utcnow(),
            content_type="python",
            chunk_index=0,
            total_chunks=5,
            parent_id="doc123",
            custom={"version": "1.0"},
        )

        data = metadata.to_dict()

        assert data["source"] == "/path/to/file.py"
        assert data["domain"] == "code"
        assert data["content_type"] == "python"
        assert data["custom"]["version"] == "1.0"

    def test_metadata_roundtrip(self):
        """Test metadata serialization/deserialization."""
        original = ChunkMetadata(
            source="test.md",
            domain="documentation",
            timestamp=datetime.utcnow(),
            content_type="markdown",
            chunk_index=1,
            total_chunks=3,
            parent_id="parent123",
        )

        data = original.to_dict()
        restored = ChunkMetadata.from_dict(data)

        assert restored.source == original.source
        assert restored.domain == original.domain
        assert restored.content_type == original.content_type


class TestEmbeddingPipeline:
    """Tests for the main pipeline (AC-4, AC-5)."""

    @pytest.fixture
    def pipeline(self):
        """Create a pipeline for testing."""
        return EmbeddingPipeline(
            provider=SimpleHashEmbeddingProvider(dimension=64),
            chunker=SemanticChunker(max_chunk_size=100),
            cache=InMemoryCache(),
            config=PipelineConfig(cache_enabled=True),
        )

    @pytest.fixture
    def sample_document(self):
        """Create a sample document."""
        return Document(
            id="doc1",
            content="This is a test document with some content.",
            source="/test/path.txt",
            domain="documentation",
            content_type="text",
        )

    def test_process_document(self, pipeline, sample_document):
        """Test basic document processing."""
        result = pipeline.process_document(sample_document)

        assert isinstance(result, EmbeddedDocument)
        assert result.document_id == "doc1"
        assert len(result.chunks) > 0
        assert result.provider == "SimpleHashEmbeddingProvider"

    def test_process_document_preserves_metadata(self, pipeline, sample_document):
        """Test that metadata is preserved in embedded chunks (AC-3)."""
        sample_document.metadata = {"project": "test", "version": 1}

        result = pipeline.process_document(sample_document)

        for chunk in result.chunks:
            assert chunk.metadata.source == sample_document.source
            assert chunk.metadata.domain == sample_document.domain

    def test_process_batch(self, pipeline):
        """Test batch processing (AC-4)."""
        documents = [
            Document(
                id=f"doc{i}",
                content=f"Content for document {i}. " * 10,
                source=f"/path/doc{i}.txt",
                domain="test",
                content_type="text",
            )
            for i in range(5)
        ]

        results = pipeline.process_batch(documents, max_concurrent=2)

        assert len(results) == 5
        assert all(isinstance(r, EmbeddedDocument) for r in results)

    def test_incremental_update(self, pipeline, sample_document):
        """Test incremental update skips unchanged content (AC-5)."""
        # First processing
        result1 = pipeline.process_document(sample_document)
        assert len(result1.chunks) > 0

        # Second processing - should detect no change
        result2 = pipeline.process_incremental(sample_document)
        assert result2 is None  # No change detected

        # Modify document
        sample_document.content = "New content that is different."
        result3 = pipeline.process_incremental(sample_document)
        assert result3 is not None  # Change detected

    def test_force_reprocess(self, pipeline, sample_document):
        """Test force reprocess bypasses cache."""
        # First processing
        pipeline.process_document(sample_document)

        # Force reprocess
        result = pipeline.process_document(sample_document, force_reprocess=True)

        assert len(result.chunks) > 0

    def test_health_check(self, pipeline):
        """Test pipeline health check."""
        health = pipeline.health_check()

        assert health["status"] == "healthy"
        assert "provider" in health
        assert "model" in health
        assert "dimension" in health

    def test_pipeline_properties(self, pipeline):
        """Test pipeline property accessors."""
        assert pipeline.provider is not None
        assert pipeline.chunker is not None
        assert pipeline.cache is not None
        assert pipeline.config is not None


class TestDocument:
    """Tests for Document model."""

    def test_document_content_hash(self):
        """Test content hash for change detection."""
        doc = Document(
            id="test",
            content="Hello, world!",
            source="test.txt",
            domain="test",
            content_type="text",
        )

        hash1 = doc.content_hash()
        hash2 = doc.content_hash()

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex

    def test_document_hash_changes(self):
        """Test hash changes when content changes."""
        doc = Document(
            id="test",
            content="Original content",
            source="test.txt",
            domain="test",
            content_type="text",
        )

        hash1 = doc.content_hash()
        doc.content = "Modified content"
        hash2 = doc.content_hash()

        assert hash1 != hash2

    def test_document_serialization(self):
        """Test document to_dict/from_dict."""
        original = Document(
            id="doc1",
            content="Test content",
            source="/path/file.txt",
            domain="documentation",
            content_type="markdown",
            metadata={"key": "value"},
        )

        data = original.to_dict()
        restored = Document.from_dict(data)

        assert restored.id == original.id
        assert restored.content == original.content
        assert restored.source == original.source
        assert restored.metadata == original.metadata


class TestIntegration:
    """Integration tests for the full pipeline."""

    def test_full_workflow(self):
        """Test complete embedding workflow."""
        # Initialize pipeline
        pipeline = EmbeddingPipeline(
            provider=SimpleHashEmbeddingProvider(dimension=128),
            chunker=SemanticChunker(max_chunk_size=200),
            cache=InMemoryCache(),
        )

        # Create documents
        documents = [
            Document(
                id=f"doc{i}",
                content=f"Document {i} content. " * 20,
                source=f"/path/{i}.txt",
                domain="test",
                content_type="text",
                metadata={"index": i},
            )
            for i in range(3)
        ]

        # Process batch
        results = pipeline.process_batch(documents)
        assert len(results) == 3

        # Verify embeddings
        for result in results:
            assert len(result.chunks) > 0
            for chunk in result.chunks:
                assert len(chunk.embedding) == 128
                assert chunk.metadata.domain == "test"

        # Test incremental - no change
        for doc in documents:
            incremental = pipeline.process_incremental(doc)
            assert incremental is None

        # Modify and reprocess
        documents[0].content = "New content for document 0."
        incremental = pipeline.process_incremental(documents[0])
        assert incremental is not None

        # Health check
        health = pipeline.health_check()
        assert health["status"] == "healthy"
        assert health["cache_size"] == 3  # 3 documents cached

    def test_code_embedding_workflow(self):
        """Test embedding code files."""
        pipeline = EmbeddingPipeline(
            provider=SimpleHashEmbeddingProvider(),
            chunker=CodeChunker(language="python"),
        )

        code = '''
def add(a, b):
    """Add two numbers."""
    return a + b

def multiply(a, b):
    """Multiply two numbers."""
    return a * b
'''

        doc = Document(
            id="code1",
            content=code,
            source="math.py",
            domain="code",
            content_type="python",
        )

        result = pipeline.process_document(doc)

        assert len(result.chunks) >= 1
        assert result.metadata.get("unchanged") is not True
