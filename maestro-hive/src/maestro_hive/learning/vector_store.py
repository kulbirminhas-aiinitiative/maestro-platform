#!/usr/bin/env python3
"""
Vector Store: Manages embeddings for semantic search and retrieval.

This module handles:
- Embedding generation for text content
- Vector storage and indexing
- Semantic search operations
- Context retrieval for RAG
"""

import hashlib
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import uuid

logger = logging.getLogger(__name__)


class EmbeddingModel(Enum):
    """Supported embedding models."""
    OPENAI_ADA = "text-embedding-ada-002"
    OPENAI_3_SMALL = "text-embedding-3-small"
    OPENAI_3_LARGE = "text-embedding-3-large"
    LOCAL_SENTENCE = "sentence-transformers"
    MOCK = "mock-embeddings"


class IndexType(Enum):
    """Types of vector indices."""
    FLAT = "flat"              # Exact search (brute force)
    HNSW = "hnsw"              # Hierarchical Navigable Small World
    IVF = "ivf"                # Inverted File Index
    LSH = "lsh"                # Locality Sensitive Hashing


@dataclass
class Document:
    """A document to be embedded and stored."""
    doc_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Embedding:
    """An embedding vector with metadata."""
    embedding_id: str
    doc_id: str
    vector: List[float]
    dimensions: int
    model: EmbeddingModel
    content_hash: str
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SearchResult:
    """A search result from vector similarity search."""
    doc_id: str
    score: float  # similarity score (0-1)
    content: str
    metadata: Dict[str, Any]
    distance: float  # raw distance


@dataclass
class IndexStats:
    """Statistics about the vector index."""
    total_documents: int
    total_embeddings: int
    index_type: IndexType
    dimensions: int
    model: EmbeddingModel
    memory_usage_mb: float


class VectorStore:
    """
    Manages vector embeddings for semantic search.

    Implements:
    - embedding_generation: Create vector representations
    - context_retrieval: Find relevant context
    - history_indexing: Index past interactions
    - internal_doc_search: Search internal documentation
    """

    def __init__(
        self,
        model: EmbeddingModel = EmbeddingModel.MOCK,
        index_type: IndexType = IndexType.FLAT,
        dimensions: int = 1536
    ):
        """Initialize the vector store."""
        self.model = model
        self.index_type = index_type
        self.dimensions = dimensions

        # Storage
        self._documents: Dict[str, Document] = {}
        self._embeddings: Dict[str, Embedding] = {}
        self._vectors: List[Tuple[str, List[float]]] = []  # (embedding_id, vector)

        logger.info(
            f"VectorStore initialized: model={model.value}, "
            f"index={index_type.value}, dims={dimensions}"
        )

    async def add_document(self, document: Document) -> Embedding:
        """
        Add a document to the store.

        Generates embedding and indexes it for search.
        """
        logger.debug(f"Adding document: {document.doc_id}")

        # Store document
        self._documents[document.doc_id] = document

        # Generate embedding
        vector = await self._generate_embedding(document.content)

        # Create embedding record
        embedding = Embedding(
            embedding_id=str(uuid.uuid4()),
            doc_id=document.doc_id,
            vector=vector,
            dimensions=len(vector),
            model=self.model,
            content_hash=self._hash_content(document.content)
        )

        # Store embedding
        self._embeddings[embedding.embedding_id] = embedding
        self._vectors.append((embedding.embedding_id, vector))

        logger.info(f"Document {document.doc_id} indexed successfully")
        return embedding

    async def add_documents(self, documents: List[Document]) -> List[Embedding]:
        """Add multiple documents in batch."""
        embeddings = []
        for doc in documents:
            emb = await self.add_document(doc)
            embeddings.append(emb)
        return embeddings

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search for similar documents.

        Implements context_retrieval through semantic search.

        Args:
            query: Search query text
            top_k: Number of results to return
            filter_metadata: Optional metadata filters

        Returns:
            List of SearchResults sorted by relevance
        """
        logger.debug(f"Searching for: {query[:50]}...")

        # Generate query embedding
        query_vector = await self._generate_embedding(query)

        # Calculate similarities
        results = []
        for emb_id, doc_vector in self._vectors:
            embedding = self._embeddings[emb_id]
            document = self._documents.get(embedding.doc_id)

            if not document:
                continue

            # Apply metadata filter
            if filter_metadata:
                if not self._matches_filter(document.metadata, filter_metadata):
                    continue

            # Calculate cosine similarity
            similarity = self._cosine_similarity(query_vector, doc_vector)
            distance = 1 - similarity

            result = SearchResult(
                doc_id=document.doc_id,
                score=similarity,
                content=document.content,
                metadata=document.metadata,
                distance=distance
            )
            results.append(result)

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:top_k]

    async def history_indexing(
        self,
        history_items: List[Dict[str, Any]]
    ) -> int:
        """
        Index historical interactions.

        Implements history_indexing for learning from past executions.
        """
        indexed_count = 0

        for item in history_items:
            doc = Document(
                doc_id=f"history-{uuid.uuid4().hex[:8]}",
                content=str(item.get('content', '')),
                metadata={
                    'type': 'history',
                    'timestamp': item.get('timestamp', datetime.utcnow().isoformat()),
                    **item.get('metadata', {})
                },
                source='history'
            )

            await self.add_document(doc)
            indexed_count += 1

        logger.info(f"Indexed {indexed_count} history items")
        return indexed_count

    async def internal_doc_search(
        self,
        query: str,
        doc_types: Optional[List[str]] = None,
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        Search internal documentation.

        Implements internal_doc_search for finding relevant docs.
        """
        filter_metadata = {}
        if doc_types:
            filter_metadata['type'] = doc_types

        return await self.search(query, top_k=top_k, filter_metadata=filter_metadata)

    async def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.

        Implements embedding_generation.
        """
        if self.model == EmbeddingModel.MOCK:
            # Generate deterministic mock embedding based on text hash
            return self._mock_embedding(text)

        # For real models, would call external API
        # Example for OpenAI:
        # response = await openai.embeddings.create(
        #     model=self.model.value,
        #     input=text
        # )
        # return response.data[0].embedding

        # Default to mock for now
        return self._mock_embedding(text)

    def _mock_embedding(self, text: str) -> List[float]:
        """Generate a deterministic mock embedding for testing."""
        # Use text hash to create reproducible vectors
        text_hash = hashlib.sha256(text.encode()).digest()

        # Convert hash bytes to floats
        vector = []
        for i in range(self.dimensions):
            byte_idx = i % len(text_hash)
            value = (text_hash[byte_idx] - 128) / 128.0  # Normalize to [-1, 1]
            vector.append(value)

        # Normalize the vector
        magnitude = math.sqrt(sum(v * v for v in vector))
        if magnitude > 0:
            vector = [v / magnitude for v in vector]

        return vector

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(vec1) != len(vec2):
            raise ValueError("Vectors must have same dimensions")

        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _matches_filter(
        self,
        metadata: Dict[str, Any],
        filter_metadata: Dict[str, Any]
    ) -> bool:
        """Check if metadata matches filter criteria."""
        for key, value in filter_metadata.items():
            if key not in metadata:
                return False
            if isinstance(value, list):
                if metadata[key] not in value:
                    return False
            elif metadata[key] != value:
                return False
        return True

    def _hash_content(self, content: str) -> str:
        """Generate hash of content for deduplication."""
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def get_document(self, doc_id: str) -> Optional[Document]:
        """Retrieve a document by ID."""
        return self._documents.get(doc_id)

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document and its embedding."""
        if doc_id not in self._documents:
            return False

        # Remove document
        del self._documents[doc_id]

        # Find and remove embedding
        emb_to_remove = None
        for emb_id, embedding in self._embeddings.items():
            if embedding.doc_id == doc_id:
                emb_to_remove = emb_id
                break

        if emb_to_remove:
            del self._embeddings[emb_to_remove]
            self._vectors = [
                (eid, v) for eid, v in self._vectors if eid != emb_to_remove
            ]

        logger.info(f"Document {doc_id} deleted")
        return True

    def get_stats(self) -> IndexStats:
        """Get statistics about the vector store."""
        # Estimate memory usage
        vectors_memory = len(self._vectors) * self.dimensions * 8 / (1024 * 1024)
        docs_memory = sum(len(d.content) for d in self._documents.values()) / (1024 * 1024)

        return IndexStats(
            total_documents=len(self._documents),
            total_embeddings=len(self._embeddings),
            index_type=self.index_type,
            dimensions=self.dimensions,
            model=self.model,
            memory_usage_mb=vectors_memory + docs_memory
        )

    def clear(self) -> None:
        """Clear all documents and embeddings."""
        self._documents.clear()
        self._embeddings.clear()
        self._vectors.clear()
        logger.info("Vector store cleared")


# Factory function
def create_vector_store(
    model: EmbeddingModel = EmbeddingModel.MOCK,
    index_type: IndexType = IndexType.FLAT,
    dimensions: int = 1536
) -> VectorStore:
    """Create a new VectorStore instance."""
    return VectorStore(model=model, index_type=index_type, dimensions=dimensions)
