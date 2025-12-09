#!/usr/bin/env python3
"""
RAG Client: Retrieval-Augmented Generation client for knowledge queries.

This module provides a client for querying knowledge bases using vector
similarity search with context window management and caching.
"""

import hashlib
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class IndexType(Enum):
    """Type of vector index."""
    CODEBASE = "codebase"
    DOCUMENTATION = "documentation"
    KNOWLEDGE_BASE = "knowledge_base"
    CONVERSATION = "conversation"


@dataclass
class Document:
    """A document in the knowledge base."""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    source: str = ""
    embedding: Optional[List[float]] = None
    chunk_index: int = 0
    total_chunks: int = 1
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class SearchResult:
    """Result from a similarity search."""
    document: Document
    score: float
    rank: int
    highlights: List[str] = field(default_factory=list)


@dataclass
class QueryContext:
    """Context assembled from search results."""
    question: str
    documents: List[Document]
    total_tokens: int
    context_text: str
    sources: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)


class CacheEntry:
    """Cache entry for query results."""

    def __init__(self, results: List[SearchResult], ttl_seconds: int = 300):
        self.results = results
        self.created_at = datetime.utcnow()
        self.ttl = timedelta(seconds=ttl_seconds)

    def is_valid(self) -> bool:
        """Check if cache entry is still valid."""
        return datetime.utcnow() - self.created_at < self.ttl


class RAGClient:
    """
    Retrieval-Augmented Generation client.

    Provides vector similarity search, context window management,
    multi-index support, and caching for efficient knowledge retrieval.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        default_index: str = "default",
        max_context_tokens: int = 4000,
        cache_ttl_seconds: int = 300
    ):
        """
        Initialize the RAG client.

        Args:
            endpoint: RAG service endpoint URL
            api_key: API key for authentication
            default_index: Default index to query
            max_context_tokens: Maximum tokens for context window
            cache_ttl_seconds: Cache TTL in seconds
        """
        self.endpoint = endpoint or "http://localhost:8001"
        self.api_key = api_key
        self.default_index = default_index
        self.max_context_tokens = max_context_tokens
        self.cache_ttl = cache_ttl_seconds

        self._indices: Dict[str, List[Document]] = {default_index: []}
        self._cache: Dict[str, CacheEntry] = {}
        self._document_counter = 0

        logger.info(f"RAGClient initialized with endpoint: {self.endpoint}")

    def add_document(
        self,
        doc: Document,
        index: Optional[str] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ) -> str:
        """
        Add a document to the knowledge base.

        Args:
            doc: Document to add
            index: Target index (uses default if not specified)
            chunk_size: Size of text chunks for embedding
            chunk_overlap: Overlap between chunks

        Returns:
            Document ID
        """
        index = index or self.default_index

        if index not in self._indices:
            self._indices[index] = []

        # Chunk document if needed
        if len(doc.content) > chunk_size:
            chunks = self._chunk_text(doc.content, chunk_size, chunk_overlap)
            for i, chunk in enumerate(chunks):
                chunk_doc = Document(
                    id=f"{doc.id}_chunk_{i}",
                    content=chunk,
                    metadata={**doc.metadata, "parent_id": doc.id},
                    source=doc.source,
                    chunk_index=i,
                    total_chunks=len(chunks)
                )
                chunk_doc.embedding = self._generate_embedding(chunk)
                self._indices[index].append(chunk_doc)
        else:
            doc.embedding = self._generate_embedding(doc.content)
            self._indices[index].append(doc)

        # Invalidate relevant cache entries
        self._invalidate_cache(index)

        logger.info(f"Document added: {doc.id} to index '{index}'")
        return doc.id

    def delete_document(self, doc_id: str, index: Optional[str] = None) -> bool:
        """
        Remove a document from the knowledge base.

        Args:
            doc_id: Document ID to remove
            index: Index to remove from (searches all if not specified)

        Returns:
            True if document was found and removed
        """
        indices_to_search = [index] if index else list(self._indices.keys())

        for idx in indices_to_search:
            if idx not in self._indices:
                continue

            # Remove document and its chunks
            original_count = len(self._indices[idx])
            self._indices[idx] = [
                d for d in self._indices[idx]
                if d.id != doc_id and d.metadata.get("parent_id") != doc_id
            ]

            if len(self._indices[idx]) < original_count:
                self._invalidate_cache(idx)
                logger.info(f"Document removed: {doc_id} from index '{idx}'")
                return True

        return False

    def query(
        self,
        question: str,
        index: Optional[str] = None,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        use_cache: bool = True
    ) -> List[SearchResult]:
        """
        Query the knowledge base.

        Args:
            question: Natural language question
            index: Index to query (uses default if not specified)
            top_k: Number of results to return
            filters: Metadata filters to apply
            use_cache: Whether to use cached results

        Returns:
            List of SearchResults sorted by relevance
        """
        index = index or self.default_index
        cache_key = self._cache_key(question, index, filters)

        # Check cache
        if use_cache and cache_key in self._cache:
            entry = self._cache[cache_key]
            if entry.is_valid():
                logger.debug(f"Cache hit for query: {question[:50]}...")
                return entry.results[:top_k]

        # Generate query embedding
        query_embedding = self._generate_embedding(question)

        # Search index
        results = self._similarity_search(
            query_embedding,
            index,
            top_k * 2,  # Get more for filtering
            filters
        )

        # Apply filters if specified
        if filters:
            results = self._apply_filters(results, filters)

        # Trim to top_k
        results = results[:top_k]

        # Cache results
        if use_cache:
            self._cache[cache_key] = CacheEntry(results, self.cache_ttl)

        logger.debug(f"Query returned {len(results)} results")
        return results

    def get_context(
        self,
        question: str,
        index: Optional[str] = None,
        max_tokens: Optional[int] = None,
        top_k: int = 10
    ) -> QueryContext:
        """
        Get context for a question optimized for LLM consumption.

        Args:
            question: Natural language question
            index: Index to query
            max_tokens: Maximum context tokens (uses default if not specified)
            top_k: Maximum documents to consider

        Returns:
            QueryContext with assembled context
        """
        max_tokens = max_tokens or self.max_context_tokens

        results = self.query(question, index, top_k)

        # Assemble context within token limit
        documents: List[Document] = []
        context_parts: List[str] = []
        total_tokens = 0
        sources: List[str] = []

        for result in results:
            doc = result.document
            doc_tokens = self._estimate_tokens(doc.content)

            if total_tokens + doc_tokens > max_tokens:
                # Try to fit a truncated version
                available = max_tokens - total_tokens
                if available > 100:
                    truncated = self._truncate_to_tokens(doc.content, available)
                    context_parts.append(truncated)
                    total_tokens += self._estimate_tokens(truncated)
                break

            documents.append(doc)
            context_parts.append(doc.content)
            total_tokens += doc_tokens

            if doc.source and doc.source not in sources:
                sources.append(doc.source)

        context_text = "\n\n---\n\n".join(context_parts)

        return QueryContext(
            question=question,
            documents=documents,
            total_tokens=total_tokens,
            context_text=context_text,
            sources=sources,
            metadata={
                "results_considered": len(results),
                "documents_included": len(documents),
                "index": index or self.default_index
            }
        )

    def list_indices(self) -> List[Dict[str, Any]]:
        """List all available indices."""
        return [
            {
                "name": name,
                "document_count": len(docs),
                "total_chunks": sum(1 for d in docs if d.chunk_index > 0)
            }
            for name, docs in self._indices.items()
        ]

    def create_index(self, name: str, index_type: IndexType = IndexType.KNOWLEDGE_BASE) -> bool:
        """
        Create a new index.

        Args:
            name: Index name
            index_type: Type of index

        Returns:
            True if created, False if already exists
        """
        if name in self._indices:
            return False

        self._indices[name] = []
        logger.info(f"Index created: {name} ({index_type.value})")
        return True

    def delete_index(self, name: str) -> bool:
        """
        Delete an index.

        Args:
            name: Index name to delete

        Returns:
            True if deleted
        """
        if name not in self._indices or name == self.default_index:
            return False

        del self._indices[name]
        self._invalidate_cache(name)
        logger.info(f"Index deleted: {name}")
        return True

    def clear_cache(self) -> None:
        """Clear all cached query results."""
        self._cache.clear()
        logger.info("Cache cleared")

    def _generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text.

        In production, this would call an embedding API.
        Here we use a simple hash-based mock embedding.
        """
        # Mock embedding using hash (production would use real embeddings)
        hash_bytes = hashlib.sha256(text.encode()).digest()
        # Convert to normalized floats
        embedding = [b / 255.0 for b in hash_bytes[:128]]
        return embedding

    def _similarity_search(
        self,
        query_embedding: List[float],
        index: str,
        top_k: int,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """Perform similarity search on an index."""
        if index not in self._indices:
            return []

        scored_docs: List[Tuple[float, Document]] = []

        for doc in self._indices[index]:
            if doc.embedding is None:
                continue

            # Cosine similarity
            score = self._cosine_similarity(query_embedding, doc.embedding)
            scored_docs.append((score, doc))

        # Sort by score descending
        scored_docs.sort(key=lambda x: x[0], reverse=True)

        results = []
        for rank, (score, doc) in enumerate(scored_docs[:top_k], 1):
            results.append(SearchResult(
                document=doc,
                score=score,
                rank=rank,
                highlights=self._extract_highlights(doc.content)
            ))

        return results

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        if len(a) != len(b):
            return 0.0

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def _apply_filters(
        self,
        results: List[SearchResult],
        filters: Dict[str, Any]
    ) -> List[SearchResult]:
        """Apply metadata filters to search results."""
        filtered = []

        for result in results:
            metadata = result.document.metadata
            match = True

            for key, value in filters.items():
                if key not in metadata:
                    match = False
                    break
                if isinstance(value, list):
                    if metadata[key] not in value:
                        match = False
                        break
                elif metadata[key] != value:
                    match = False
                    break

            if match:
                filtered.append(result)

        return filtered

    def _chunk_text(
        self,
        text: str,
        chunk_size: int,
        overlap: int
    ) -> List[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk.rfind('.')
                if last_period > chunk_size * 0.5:
                    chunk = chunk[:last_period + 1]
                    end = start + last_period + 1

            chunks.append(chunk.strip())
            start = end - overlap

        return chunks

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        # Rough estimation: ~4 characters per token
        return len(text) // 4

    def _truncate_to_tokens(self, text: str, max_tokens: int) -> str:
        """Truncate text to fit within token limit."""
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text

        truncated = text[:max_chars]
        last_period = truncated.rfind('.')
        if last_period > max_chars * 0.5:
            truncated = truncated[:last_period + 1]

        return truncated + "..."

    def _extract_highlights(self, text: str, max_highlights: int = 3) -> List[str]:
        """Extract key sentences as highlights."""
        sentences = text.split('.')
        return [s.strip() + '.' for s in sentences[:max_highlights] if s.strip()]

    def _cache_key(
        self,
        question: str,
        index: str,
        filters: Optional[Dict[str, Any]]
    ) -> str:
        """Generate cache key for a query."""
        key_parts = [question, index, json.dumps(filters or {}, sort_keys=True)]
        return hashlib.md5("|".join(key_parts).encode()).hexdigest()

    def _invalidate_cache(self, index: str) -> None:
        """Invalidate cache entries for an index."""
        keys_to_remove = [
            k for k, v in self._cache.items()
            if not v.is_valid()
        ]
        for key in keys_to_remove:
            del self._cache[key]


# Convenience function
def create_rag_client(**kwargs) -> RAGClient:
    """Create a new RAGClient instance."""
    return RAGClient(**kwargs)
