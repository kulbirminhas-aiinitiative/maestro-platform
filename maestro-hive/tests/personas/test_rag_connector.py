#!/usr/bin/env python3
"""
Tests for RAG Connector module.

Related EPIC: MD-3026 - RAG Persona Integration
"""

import pytest
import asyncio
from typing import List
from datetime import datetime

from maestro_hive.personas.rag_connector import (
    RAGConnector,
    RAGConfig,
    RAGProviderType,
    QueryStrategy,
    ConnectionStatus,
    EmbeddingVector,
    RetrievalResult,
    RetrievalContext,
    IndexStats,
    MockEmbeddingProvider,
    InMemoryVectorStore,
    QueryCache,
    get_rag_connector,
    reset_rag_connector,
    retrieve_context,
)


class TestRAGConfig:
    """Tests for RAGConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = RAGConfig()

        assert config.provider_type == RAGProviderType.CHROMA
        assert config.index_name == "maestro_personas"
        assert config.namespace == "default"
        assert config.embedding_dimension == 1536
        assert config.query_strategy == QueryStrategy.HYBRID
        assert config.default_top_k == 10
        assert config.cache_enabled is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = RAGConfig(
            provider_type=RAGProviderType.PINECONE,
            index_name="custom_index",
            embedding_dimension=768,
            query_strategy=QueryStrategy.SEMANTIC,
            default_top_k=20
        )

        assert config.provider_type == RAGProviderType.PINECONE
        assert config.index_name == "custom_index"
        assert config.embedding_dimension == 768
        assert config.query_strategy == QueryStrategy.SEMANTIC
        assert config.default_top_k == 20


class TestMockEmbeddingProvider:
    """Tests for MockEmbeddingProvider."""

    def test_embed_text(self):
        """Test single text embedding."""
        provider = MockEmbeddingProvider(dimension=384)
        embedding = provider.embed_text("Hello world")

        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)

    def test_embed_text_deterministic(self):
        """Test that embeddings are deterministic."""
        provider = MockEmbeddingProvider(dimension=384)

        emb1 = provider.embed_text("test text")
        emb2 = provider.embed_text("test text")

        assert emb1 == emb2

    def test_embed_text_different_texts(self):
        """Test that different texts produce different embeddings."""
        provider = MockEmbeddingProvider(dimension=384)

        emb1 = provider.embed_text("first text")
        emb2 = provider.embed_text("second text")

        assert emb1 != emb2

    def test_embed_batch(self):
        """Test batch embedding."""
        provider = MockEmbeddingProvider(dimension=768)
        texts = ["text 1", "text 2", "text 3"]

        embeddings = provider.embed_batch(texts)

        assert len(embeddings) == 3
        assert all(len(emb) == 768 for emb in embeddings)

    def test_dimension_property(self):
        """Test dimension property."""
        provider = MockEmbeddingProvider(dimension=1024)
        assert provider.dimension == 1024

    def test_embedding_normalization(self):
        """Test that embeddings are normalized."""
        provider = MockEmbeddingProvider(dimension=384)
        embedding = provider.embed_text("test")

        magnitude = sum(x * x for x in embedding) ** 0.5
        assert abs(magnitude - 1.0) < 0.01  # Should be approximately unit length


class TestEmbeddingVector:
    """Tests for EmbeddingVector dataclass."""

    def test_create_embedding_vector(self):
        """Test creating an embedding vector."""
        vector = EmbeddingVector(
            vector_id="vec_001",
            embedding=[0.1, 0.2, 0.3],
            text_content="Sample text",
            metadata={"source": "test"}
        )

        assert vector.vector_id == "vec_001"
        assert len(vector.embedding) == 3
        assert vector.text_content == "Sample text"
        assert vector.metadata["source"] == "test"

    def test_dimension_property(self):
        """Test dimension property."""
        vector = EmbeddingVector(
            vector_id="vec_001",
            embedding=[0.1] * 768,
            text_content="test"
        )

        assert vector.dimension == 768


class TestInMemoryVectorStore:
    """Tests for InMemoryVectorStore."""

    @pytest.fixture
    def store(self):
        """Create a test store."""
        return InMemoryVectorStore(index_name="test_index", dimension=384)

    @pytest.fixture
    def sample_vectors(self):
        """Create sample vectors."""
        provider = MockEmbeddingProvider(dimension=384)

        return [
            EmbeddingVector(
                vector_id=f"vec_{i}",
                embedding=provider.embed_text(f"Document {i} content"),
                text_content=f"Document {i} content",
                metadata={"doc_num": i, "category": "test"}
            )
            for i in range(10)
        ]

    @pytest.mark.asyncio
    async def test_upsert_vectors(self, store, sample_vectors):
        """Test upserting vectors."""
        count = await store.upsert(sample_vectors, namespace="test")

        assert count == 10

    @pytest.mark.asyncio
    async def test_query_vectors(self, store, sample_vectors):
        """Test querying vectors."""
        await store.upsert(sample_vectors, namespace="test")

        provider = MockEmbeddingProvider(dimension=384)
        query_vector = provider.embed_text("Document 5 content")

        results = await store.query(
            query_vector=query_vector,
            top_k=3,
            namespace="test"
        )

        assert len(results) == 3
        assert all(isinstance(r, RetrievalResult) for r in results)
        assert all(r.similarity_score >= 0 for r in results)

    @pytest.mark.asyncio
    async def test_query_with_filters(self, store, sample_vectors):
        """Test querying with metadata filters."""
        await store.upsert(sample_vectors, namespace="test")

        provider = MockEmbeddingProvider(dimension=384)
        query_vector = provider.embed_text("test query")

        # Filter by doc_num > 5
        results = await store.query(
            query_vector=query_vector,
            top_k=10,
            filters={"doc_num": {"$gt": 5}},
            namespace="test"
        )

        assert len(results) <= 4  # Only docs 6, 7, 8, 9

    @pytest.mark.asyncio
    async def test_delete_vectors(self, store, sample_vectors):
        """Test deleting vectors."""
        await store.upsert(sample_vectors, namespace="test")

        deleted = await store.delete(["vec_0", "vec_1", "vec_2"], namespace="test")

        assert deleted == 3

    @pytest.mark.asyncio
    async def test_get_stats(self, store, sample_vectors):
        """Test getting stats."""
        await store.upsert(sample_vectors, namespace="test")

        stats = await store.get_stats()

        assert stats.index_name == "test_index"
        assert stats.total_vectors == 10
        assert stats.dimension == 384
        assert "test" in stats.namespaces

    def test_clear_namespace(self, store):
        """Test clearing a namespace."""
        # Manually add some vectors
        store._vectors["test"] = {"v1": None, "v2": None}

        count = store.clear(namespace="test")

        assert count == 2
        assert store._vectors["test"] == {}

    def test_clear_all(self, store):
        """Test clearing all namespaces."""
        store._vectors["ns1"] = {"v1": None, "v2": None}
        store._vectors["ns2"] = {"v3": None}

        count = store.clear()

        assert count == 3
        assert len(store._vectors) == 0


class TestQueryCache:
    """Tests for QueryCache."""

    @pytest.fixture
    def cache(self):
        """Create a test cache."""
        return QueryCache(ttl_seconds=60, max_size=10)

    def test_set_and_get(self, cache):
        """Test setting and getting cached values."""
        context = RetrievalContext(
            query="test query",
            query_embedding=None,
            results=[],
            total_results=0,
            retrieval_time_ms=10.0,
            strategy_used=QueryStrategy.SEMANTIC
        )

        cache.set("test query", 10, None, context)
        cached = cache.get("test query", 10, None)

        assert cached is not None
        assert cached.query == "test query"

    def test_cache_miss(self, cache):
        """Test cache miss returns None."""
        result = cache.get("nonexistent", 10, None)
        assert result is None

    def test_cache_eviction(self):
        """Test cache eviction when at capacity."""
        cache = QueryCache(ttl_seconds=60, max_size=3)

        for i in range(5):
            context = RetrievalContext(
                query=f"query {i}",
                query_embedding=None,
                results=[],
                total_results=0,
                retrieval_time_ms=10.0,
                strategy_used=QueryStrategy.SEMANTIC
            )
            cache.set(f"query {i}", 10, None, context)

        # Should only have 3 items
        stats = cache.stats()
        assert stats["size"] == 3

    def test_cache_clear(self, cache):
        """Test clearing the cache."""
        context = RetrievalContext(
            query="test",
            query_embedding=None,
            results=[],
            total_results=0,
            retrieval_time_ms=10.0,
            strategy_used=QueryStrategy.SEMANTIC
        )

        cache.set("test", 10, None, context)
        count = cache.clear()

        assert count == 1
        assert cache.get("test", 10, None) is None


class TestRAGConnector:
    """Tests for RAGConnector."""

    @pytest.fixture
    def connector(self):
        """Create a test connector."""
        reset_rag_connector()
        config = RAGConfig(
            provider_type=RAGProviderType.CHROMA,
            embedding_dimension=384
        )
        return RAGConnector(config=config)

    @pytest.mark.asyncio
    async def test_connect(self, connector):
        """Test connecting to the store."""
        result = await connector.connect()

        assert result is True
        assert connector.status == ConnectionStatus.CONNECTED
        assert connector.is_connected is True

    @pytest.mark.asyncio
    async def test_disconnect(self, connector):
        """Test disconnecting."""
        await connector.connect()
        await connector.disconnect()

        assert connector.status == ConnectionStatus.DISCONNECTED
        assert connector.is_connected is False

    @pytest.mark.asyncio
    async def test_index_knowledge(self, connector):
        """Test indexing documents."""
        await connector.connect()

        documents = [
            {"id": "doc1", "content": "Python is a programming language"},
            {"id": "doc2", "content": "JavaScript is used for web development"},
            {"id": "doc3", "content": "Machine learning uses algorithms"},
        ]

        indexed = await connector.index_knowledge(documents)

        assert indexed == 3

    @pytest.mark.asyncio
    async def test_retrieve(self, connector):
        """Test retrieving context."""
        await connector.connect()

        # Index some documents first
        documents = [
            {"id": "doc1", "content": "Python is a great programming language"},
            {"id": "doc2", "content": "JavaScript is essential for web development"},
            {"id": "doc3", "content": "Machine learning enables intelligent systems"},
        ]
        await connector.index_knowledge(documents)

        # Retrieve
        context = await connector.retrieve(
            query="What programming language should I learn?",
            top_k=2
        )

        assert context is not None
        assert isinstance(context, RetrievalContext)
        assert context.query == "What programming language should I learn?"
        assert len(context.results) <= 2

    @pytest.mark.asyncio
    async def test_retrieve_with_persona_filter(self, connector):
        """Test retrieving with persona ID filter."""
        await connector.connect()

        documents = [
            {"id": "doc1", "content": "Content for persona A", "metadata": {"persona_id": "persona_a"}},
            {"id": "doc2", "content": "Content for persona B", "metadata": {"persona_id": "persona_b"}},
        ]
        await connector.index_knowledge(documents)

        context = await connector.retrieve(
            query="test query",
            persona_id="persona_a",
            top_k=5
        )

        assert context is not None

    @pytest.mark.asyncio
    async def test_retrieve_with_cache(self, connector):
        """Test that caching works."""
        await connector.connect()

        documents = [
            {"id": "doc1", "content": "Test document content"},
        ]
        await connector.index_knowledge(documents)

        # First query
        context1 = await connector.retrieve("test query", use_cache=True)

        # Second query (should hit cache)
        context2 = await connector.retrieve("test query", use_cache=True)

        # Both should return valid results
        assert context1 is not None
        assert context2 is not None

    @pytest.mark.asyncio
    async def test_delete_knowledge(self, connector):
        """Test deleting documents."""
        await connector.connect()

        documents = [
            {"id": "doc1", "content": "Document 1"},
            {"id": "doc2", "content": "Document 2"},
        ]
        await connector.index_knowledge(documents)

        deleted = await connector.delete_knowledge(["doc1"])

        assert deleted == 1

    @pytest.mark.asyncio
    async def test_get_index_stats(self, connector):
        """Test getting index stats."""
        await connector.connect()

        stats = await connector.get_index_stats()

        assert isinstance(stats, IndexStats)
        assert stats.dimension == 384

    def test_get_metrics(self, connector):
        """Test getting connector metrics."""
        metrics = connector.get_metrics()

        assert "status" in metrics
        assert "provider_type" in metrics
        assert "query_count" in metrics

    def test_clear_cache(self, connector):
        """Test clearing cache."""
        connector.clear_cache()  # Should not raise


class TestRetrievalResult:
    """Tests for RetrievalResult."""

    def test_to_dict(self):
        """Test converting to dictionary."""
        result = RetrievalResult(
            result_id="r1",
            content="Test content",
            similarity_score=0.85,
            metadata={"key": "value"},
            source_document="source.txt"
        )

        data = result.to_dict()

        assert data["result_id"] == "r1"
        assert data["content"] == "Test content"
        assert data["similarity_score"] == 0.85


class TestRetrievalContext:
    """Tests for RetrievalContext."""

    def test_best_result(self):
        """Test getting best result."""
        context = RetrievalContext(
            query="test",
            query_embedding=None,
            results=[
                RetrievalResult("r1", "content 1", 0.8),
                RetrievalResult("r2", "content 2", 0.9),
            ],
            total_results=2,
            retrieval_time_ms=10.0,
            strategy_used=QueryStrategy.SEMANTIC
        )

        # Results should be sorted by score, so best is first
        assert context.best_result.result_id == "r1"

    def test_average_score(self):
        """Test calculating average score."""
        context = RetrievalContext(
            query="test",
            query_embedding=None,
            results=[
                RetrievalResult("r1", "content", 0.8),
                RetrievalResult("r2", "content", 0.6),
            ],
            total_results=2,
            retrieval_time_ms=10.0,
            strategy_used=QueryStrategy.SEMANTIC
        )

        assert context.average_score == 0.7

    def test_get_context_text(self):
        """Test combining results into context text."""
        context = RetrievalContext(
            query="test",
            query_embedding=None,
            results=[
                RetrievalResult("r1", "First paragraph", 0.9),
                RetrievalResult("r2", "Second paragraph", 0.8),
            ],
            total_results=2,
            retrieval_time_ms=10.0,
            strategy_used=QueryStrategy.SEMANTIC
        )

        text = context.get_context_text(max_results=2, separator="\n\n")

        assert "First paragraph" in text
        assert "Second paragraph" in text

    def test_to_dict(self):
        """Test converting to dictionary."""
        context = RetrievalContext(
            query="test",
            query_embedding=None,
            results=[],
            total_results=0,
            retrieval_time_ms=10.0,
            strategy_used=QueryStrategy.HYBRID
        )

        data = context.to_dict()

        assert data["query"] == "test"
        assert data["strategy_used"] == "hybrid"


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_rag_connector(self):
        """Test getting default connector."""
        reset_rag_connector()
        connector = get_rag_connector()

        assert connector is not None
        assert isinstance(connector, RAGConnector)

    def test_get_rag_connector_singleton(self):
        """Test that connector is singleton."""
        reset_rag_connector()
        connector1 = get_rag_connector()
        connector2 = get_rag_connector()

        assert connector1 is connector2

    def test_reset_rag_connector(self):
        """Test resetting connector."""
        connector1 = get_rag_connector()
        reset_rag_connector()
        connector2 = get_rag_connector()

        assert connector1 is not connector2

    @pytest.mark.asyncio
    async def test_retrieve_context_function(self):
        """Test convenience retrieve function."""
        reset_rag_connector()

        context = await retrieve_context(
            query="test query",
            top_k=5
        )

        assert context is not None
        assert isinstance(context, RetrievalContext)
