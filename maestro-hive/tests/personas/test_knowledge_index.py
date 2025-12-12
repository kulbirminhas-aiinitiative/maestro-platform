#!/usr/bin/env python3
"""
Tests for Knowledge Index Manager module.

Related EPIC: MD-3026 - RAG Persona Integration
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from typing import List

from maestro_hive.personas.knowledge_index import (
    KnowledgeIndexManager,
    IndexConfig,
    IndexStatus,
    Document,
    DocumentType,
    DocumentChunk,
    IndexedDocument,
    IndexingResult,
    IndexHealth,
    ChunkingStrategy,
    DocumentChunker,
    DocumentRegistry,
    get_knowledge_index_manager,
    reset_knowledge_index_manager,
    quick_index,
)
from maestro_hive.personas.rag_connector import reset_rag_connector


class TestIndexConfig:
    """Tests for IndexConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = IndexConfig()

        assert config.index_name == "maestro_knowledge"
        assert config.namespace == "default"
        assert config.chunking_strategy == ChunkingStrategy.RECURSIVE
        assert config.chunk_size == 500
        assert config.chunk_overlap == 50
        assert config.embedding_batch_size == 100

    def test_custom_config(self):
        """Test custom configuration."""
        config = IndexConfig(
            index_name="custom_index",
            chunking_strategy=ChunkingStrategy.SENTENCE,
            chunk_size=200
        )

        assert config.index_name == "custom_index"
        assert config.chunking_strategy == ChunkingStrategy.SENTENCE
        assert config.chunk_size == 200


class TestDocument:
    """Tests for Document dataclass."""

    def test_create_document(self):
        """Test creating a document."""
        doc = Document(
            document_id="doc_001",
            content="This is the document content.",
            document_type=DocumentType.TEXT,
            title="Test Document",
            source="test.txt"
        )

        assert doc.document_id == "doc_001"
        assert doc.content == "This is the document content."
        assert doc.document_type == DocumentType.TEXT
        assert doc.title == "Test Document"

    def test_content_hash(self):
        """Test content hash property."""
        doc = Document(
            document_id="doc_001",
            content="Test content"
        )

        hash1 = doc.content_hash

        # Same content should produce same hash
        doc2 = Document(
            document_id="doc_002",
            content="Test content"
        )

        assert hash1 == doc2.content_hash

        # Different content should produce different hash
        doc3 = Document(
            document_id="doc_003",
            content="Different content"
        )

        assert hash1 != doc3.content_hash

    def test_to_dict(self):
        """Test converting to dictionary."""
        doc = Document(
            document_id="doc_001",
            content="content",
            document_type=DocumentType.MARKDOWN,
            tags=["tag1", "tag2"]
        )

        data = doc.to_dict()

        assert data["document_id"] == "doc_001"
        assert data["document_type"] == "markdown"
        assert "tag1" in data["tags"]

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "document_id": "doc_001",
            "content": "content",
            "document_type": "code",
            "title": "Test"
        }

        doc = Document.from_dict(data)

        assert doc.document_id == "doc_001"
        assert doc.document_type == DocumentType.CODE


class TestDocumentChunk:
    """Tests for DocumentChunk dataclass."""

    def test_create_chunk(self):
        """Test creating a chunk."""
        chunk = DocumentChunk(
            chunk_id="chunk_001",
            document_id="doc_001",
            content="Chunk content",
            chunk_index=0,
            start_position=0,
            end_position=13,
            token_count=3
        )

        assert chunk.chunk_id == "chunk_001"
        assert chunk.document_id == "doc_001"
        assert chunk.chunk_index == 0

    def test_to_embedding_vector_without_embedding(self):
        """Test that to_embedding_vector raises without embedding."""
        chunk = DocumentChunk(
            chunk_id="chunk_001",
            document_id="doc_001",
            content="content",
            chunk_index=0,
            start_position=0,
            end_position=7,
            token_count=1
        )

        with pytest.raises(ValueError):
            chunk.to_embedding_vector()

    def test_to_embedding_vector_with_embedding(self):
        """Test converting to embedding vector."""
        chunk = DocumentChunk(
            chunk_id="chunk_001",
            document_id="doc_001",
            content="content",
            chunk_index=0,
            start_position=0,
            end_position=7,
            token_count=1,
            embedding=[0.1, 0.2, 0.3]
        )

        vector = chunk.to_embedding_vector()

        assert vector.vector_id == "chunk_001"
        assert vector.text_content == "content"
        assert vector.embedding == [0.1, 0.2, 0.3]


class TestDocumentChunker:
    """Tests for DocumentChunker."""

    @pytest.fixture
    def sample_document(self):
        """Create a sample document."""
        return Document(
            document_id="doc_001",
            content="""This is the first paragraph with some content.

This is the second paragraph. It has multiple sentences. Here is another one.

This is the third paragraph with more information.

Finally, this is the last paragraph.""",
            title="Test Doc"
        )

    @pytest.fixture
    def code_document(self):
        """Create a sample code document."""
        return Document(
            document_id="code_001",
            content="""def hello_world():
    print("Hello, World!")
    return True

class MyClass:
    def __init__(self, value):
        self.value = value

    def get_value(self):
        return self.value

def another_function(x, y):
    result = x + y
    return result
""",
            document_type=DocumentType.CODE,
            title="Code Sample"
        )

    def test_chunk_fixed_size(self, sample_document):
        """Test fixed-size chunking."""
        chunker = DocumentChunker(
            strategy=ChunkingStrategy.FIXED_SIZE,
            chunk_size=100,
            chunk_overlap=20,
            min_chunk_size=20
        )

        chunks = chunker.chunk_document(sample_document)

        assert len(chunks) > 0
        assert all(isinstance(c, DocumentChunk) for c in chunks)
        assert all(c.document_id == "doc_001" for c in chunks)

    def test_chunk_by_paragraph(self, sample_document):
        """Test paragraph-based chunking."""
        chunker = DocumentChunker(
            strategy=ChunkingStrategy.PARAGRAPH,
            chunk_size=200,
            min_chunk_size=10
        )

        chunks = chunker.chunk_document(sample_document)

        assert len(chunks) > 0

    def test_chunk_by_sentence(self, sample_document):
        """Test sentence-based chunking."""
        chunker = DocumentChunker(
            strategy=ChunkingStrategy.SENTENCE,
            chunk_size=100,
            min_chunk_size=10
        )

        chunks = chunker.chunk_document(sample_document)

        assert len(chunks) > 0

    def test_chunk_recursive(self, sample_document):
        """Test recursive chunking."""
        chunker = DocumentChunker(
            strategy=ChunkingStrategy.RECURSIVE,
            chunk_size=100,
            min_chunk_size=20
        )

        chunks = chunker.chunk_document(sample_document)

        assert len(chunks) > 0
        # All chunks should be within max size
        for chunk in chunks:
            assert len(chunk.content) <= chunker.max_chunk_size

    def test_chunk_code_aware(self, code_document):
        """Test code-aware chunking."""
        chunker = DocumentChunker(
            strategy=ChunkingStrategy.CODE_AWARE,
            chunk_size=200,
            min_chunk_size=20
        )

        chunks = chunker.chunk_document(code_document)

        assert len(chunks) > 0

    def test_chunk_indices_sequential(self, sample_document):
        """Test that chunk indices are sequential."""
        chunker = DocumentChunker(
            strategy=ChunkingStrategy.FIXED_SIZE,
            chunk_size=50,
            min_chunk_size=10
        )

        chunks = chunker.chunk_document(sample_document)

        indices = [c.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_chunk_id_format(self, sample_document):
        """Test chunk ID format."""
        chunker = DocumentChunker(
            strategy=ChunkingStrategy.PARAGRAPH,
            chunk_size=200,
            min_chunk_size=10
        )

        chunks = chunker.chunk_document(sample_document)

        for chunk in chunks:
            assert chunk.chunk_id.startswith("doc_001_chunk_")


class TestDocumentRegistry:
    """Tests for DocumentRegistry."""

    @pytest.fixture
    def registry(self, tmp_path):
        """Create a test registry."""
        storage_path = tmp_path / "registry.json"
        return DocumentRegistry(storage_path=storage_path)

    @pytest.fixture
    def sample_document(self):
        """Create a sample document."""
        return Document(
            document_id="doc_001",
            content="Test content",
            title="Test Document",
            source="test.txt"
        )

    def test_register_document(self, registry, sample_document):
        """Test registering a document."""
        indexed = registry.register(sample_document, chunk_count=5)

        assert indexed.document_id == "doc_001"
        assert indexed.chunk_count == 5
        assert indexed.title == "Test Document"

    def test_get_document(self, registry, sample_document):
        """Test getting a registered document."""
        registry.register(sample_document, chunk_count=5)

        result = registry.get("doc_001")

        assert result is not None
        assert result.document_id == "doc_001"

    def test_get_nonexistent(self, registry):
        """Test getting a non-existent document."""
        result = registry.get("nonexistent")
        assert result is None

    def test_exists(self, registry, sample_document):
        """Test checking if document exists."""
        registry.register(sample_document, chunk_count=5)

        assert registry.exists("doc_001") is True
        assert registry.exists("doc_002") is False

    def test_needs_update_new(self, registry, sample_document):
        """Test needs_update for new document."""
        assert registry.needs_update(sample_document) is True

    def test_needs_update_unchanged(self, registry, sample_document):
        """Test needs_update for unchanged document."""
        registry.register(sample_document, chunk_count=5)

        assert registry.needs_update(sample_document) is False

    def test_needs_update_changed(self, registry, sample_document):
        """Test needs_update for changed document."""
        registry.register(sample_document, chunk_count=5)

        # Modify content
        modified_doc = Document(
            document_id="doc_001",
            content="Modified content"
        )

        assert registry.needs_update(modified_doc) is True

    def test_remove(self, registry, sample_document):
        """Test removing a document."""
        registry.register(sample_document, chunk_count=5)

        result = registry.remove("doc_001")

        assert result is True
        assert registry.exists("doc_001") is False

    def test_list_all(self, registry):
        """Test listing all documents."""
        for i in range(3):
            doc = Document(
                document_id=f"doc_{i}",
                content=f"Content {i}"
            )
            registry.register(doc, chunk_count=i + 1)

        all_docs = registry.list_all()

        assert len(all_docs) == 3

    def test_count(self, registry):
        """Test counting documents."""
        for i in range(5):
            doc = Document(
                document_id=f"doc_{i}",
                content=f"Content {i}"
            )
            registry.register(doc, chunk_count=1)

        assert registry.count() == 5


class TestKnowledgeIndexManager:
    """Tests for KnowledgeIndexManager."""

    @pytest.fixture
    def manager(self, tmp_path):
        """Create a test manager."""
        reset_rag_connector()
        reset_knowledge_index_manager()
        config = IndexConfig(
            index_name="test_index",
            chunk_size=100,
            min_chunk_size=20
        )
        return KnowledgeIndexManager(
            config=config,
            storage_path=tmp_path
        )

    @pytest.fixture
    def sample_documents(self):
        """Create sample documents."""
        return [
            Document(
                document_id="doc_001",
                content="This is the first document with substantial content about Python programming.",
                title="Python Guide"
            ),
            Document(
                document_id="doc_002",
                content="This is the second document about JavaScript and web development.",
                title="JavaScript Guide"
            ),
        ]

    @pytest.mark.asyncio
    async def test_index_document(self, manager, sample_documents):
        """Test indexing a single document."""
        result = await manager.index_document(sample_documents[0])

        assert result.success is True
        assert result.documents_processed == 1
        assert result.chunks_created > 0

    @pytest.mark.asyncio
    async def test_index_documents(self, manager, sample_documents):
        """Test indexing multiple documents."""
        result = await manager.index_documents(sample_documents)

        assert result.success is True
        assert result.documents_processed == 2
        assert result.chunks_indexed > 0

    @pytest.mark.asyncio
    async def test_index_documents_with_progress(self, manager, sample_documents):
        """Test indexing with progress callback."""
        progress_calls = []

        def callback(current, total):
            progress_calls.append((current, total))

        result = await manager.index_documents(
            sample_documents,
            progress_callback=callback
        )

        assert len(progress_calls) == 2
        assert progress_calls[-1] == (2, 2)

    @pytest.mark.asyncio
    async def test_index_text(self, manager):
        """Test indexing plain text."""
        result = await manager.index_text(
            text="This is some text to index. It should be chunked and stored.",
            title="Quick Text",
            source="inline"
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_remove_document(self, manager, sample_documents):
        """Test removing a document."""
        await manager.index_documents(sample_documents)

        result = await manager.remove_document("doc_001")

        assert result is True
        assert manager.get_document("doc_001") is None

    @pytest.mark.asyncio
    async def test_update_document(self, manager, sample_documents):
        """Test updating a document."""
        await manager.index_document(sample_documents[0])

        updated_doc = Document(
            document_id="doc_001",
            content="This is updated content for the document.",
            title="Updated Python Guide"
        )

        result = await manager.update_document(updated_doc)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_clear_index(self, manager, sample_documents):
        """Test clearing the index."""
        await manager.index_documents(sample_documents)

        # Should require confirmation
        with pytest.raises(ValueError):
            await manager.clear_index()

        count = await manager.clear_index(confirm=True)

        assert count == 2

    @pytest.mark.asyncio
    async def test_get_health(self, manager, sample_documents):
        """Test getting index health."""
        await manager.index_documents(sample_documents)

        health = await manager.get_health()

        assert isinstance(health, IndexHealth)
        assert health.status == IndexStatus.ACTIVE
        assert health.total_documents == 2

    def test_get_document(self, manager):
        """Test getting a document record."""
        result = manager.get_document("nonexistent")
        assert result is None

    def test_list_documents(self, manager):
        """Test listing documents with pagination."""
        docs = manager.list_documents(limit=10, offset=0)
        assert isinstance(docs, list)

    def test_search_documents(self, manager):
        """Test searching documents."""
        results = manager.search_documents(query="python")
        assert isinstance(results, list)

    def test_get_metrics(self, manager):
        """Test getting metrics."""
        metrics = manager.get_metrics()

        assert "status" in metrics
        assert "index_name" in metrics
        assert "chunking_strategy" in metrics

    def test_status_property(self, manager):
        """Test status property."""
        assert manager.status == IndexStatus.ACTIVE


class TestIndexingResult:
    """Tests for IndexingResult dataclass."""

    def test_to_dict(self):
        """Test converting to dictionary."""
        result = IndexingResult(
            success=True,
            documents_processed=5,
            chunks_created=25,
            chunks_indexed=25,
            documents_failed=0,
            duration_seconds=2.5
        )

        data = result.to_dict()

        assert data["success"] is True
        assert data["documents_processed"] == 5
        assert data["chunks_created"] == 25


class TestIndexHealth:
    """Tests for IndexHealth dataclass."""

    def test_to_dict(self):
        """Test converting to dictionary."""
        health = IndexHealth(
            index_name="test",
            status=IndexStatus.ACTIVE,
            total_documents=100,
            total_chunks=1000,
            index_size_mb=50.0,
            last_updated="2025-12-09T00:00:00Z",
            stale_documents=5,
            error_count=0,
            recommendations=["Consider refreshing stale documents"]
        )

        data = health.to_dict()

        assert data["index_name"] == "test"
        assert data["status"] == "active"
        assert data["total_documents"] == 100


class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_knowledge_index_manager(self):
        """Test getting default manager."""
        reset_knowledge_index_manager()
        manager = get_knowledge_index_manager()

        assert manager is not None
        assert isinstance(manager, KnowledgeIndexManager)

    def test_get_knowledge_index_manager_singleton(self):
        """Test that manager is singleton."""
        reset_knowledge_index_manager()
        manager1 = get_knowledge_index_manager()
        manager2 = get_knowledge_index_manager()

        assert manager1 is manager2

    def test_reset_knowledge_index_manager(self):
        """Test resetting manager."""
        manager1 = get_knowledge_index_manager()
        reset_knowledge_index_manager()
        manager2 = get_knowledge_index_manager()

        assert manager1 is not manager2

    @pytest.mark.asyncio
    async def test_quick_index(self):
        """Test convenience indexing function."""
        reset_knowledge_index_manager()
        reset_rag_connector()

        result = await quick_index(
            texts=["First text", "Second text", "Third text"],
            sources=["src1", "src2", "src3"]
        )

        assert result is not None
        assert isinstance(result, IndexingResult)
