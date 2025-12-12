#!/usr/bin/env python3
"""
RAG Connector: Retrieval-Augmented Generation integration for personas.

This module provides RAG (Retrieval-Augmented Generation) connectivity for
personas, enabling knowledge-enhanced decision making through external
knowledge base integration.

Related EPIC: MD-3026 - RAG Persona Integration
"""

import json
import logging
import hashlib
import asyncio
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod
import time

logger = logging.getLogger(__name__)


class RAGProviderType(Enum):
    """Supported RAG provider types."""
    PINECONE = "pinecone"
    WEAVIATE = "weaviate"
    QDRANT = "qdrant"
    CHROMA = "chroma"
    FAISS = "faiss"
    ELASTICSEARCH = "elasticsearch"
    MILVUS = "milvus"
    CUSTOM = "custom"


class QueryStrategy(Enum):
    """Strategies for querying the knowledge base."""
    SEMANTIC = "semantic"       # Pure semantic similarity
    KEYWORD = "keyword"         # Keyword-based matching
    HYBRID = "hybrid"           # Combined semantic + keyword
    MMR = "mmr"                 # Maximum Marginal Relevance
    RERANKED = "reranked"       # Initial retrieval + reranking


class ConnectionStatus(Enum):
    """RAG provider connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    DEGRADED = "degraded"


@dataclass
class RAGConfig:
    """Configuration for RAG connector."""
    provider_type: RAGProviderType = RAGProviderType.CHROMA
    api_key: Optional[str] = None
    api_endpoint: Optional[str] = None
    index_name: str = "maestro_personas"
    namespace: str = "default"
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    similarity_metric: str = "cosine"  # cosine, euclidean, dot_product
    default_top_k: int = 10
    max_top_k: int = 100
    min_similarity_threshold: float = 0.7
    query_strategy: QueryStrategy = QueryStrategy.HYBRID
    timeout_seconds: float = 30.0
    retry_attempts: int = 3
    retry_delay_seconds: float = 1.0
    cache_enabled: bool = True
    cache_ttl_seconds: int = 3600
    batch_size: int = 100
    enable_compression: bool = False
    metadata_filters_enabled: bool = True


@dataclass
class EmbeddingVector:
    """Represents an embedding vector with metadata."""
    vector_id: str
    embedding: List[float]
    text_content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    source: str = "unknown"

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        return len(self.embedding)


@dataclass
class RetrievalResult:
    """Result from a knowledge retrieval query."""
    result_id: str
    content: str
    similarity_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_document: Optional[str] = None
    chunk_index: int = 0
    relevance_explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class RetrievalContext:
    """Context returned from RAG retrieval."""
    query: str
    query_embedding: Optional[List[float]]
    results: List[RetrievalResult]
    total_results: int
    retrieval_time_ms: float
    strategy_used: QueryStrategy
    filters_applied: Dict[str, Any] = field(default_factory=dict)
    reranked: bool = False
    truncated: bool = False

    @property
    def best_result(self) -> Optional[RetrievalResult]:
        """Get the highest-scoring result."""
        if self.results:
            return self.results[0]
        return None

    @property
    def average_score(self) -> float:
        """Calculate average similarity score."""
        if not self.results:
            return 0.0
        return sum(r.similarity_score for r in self.results) / len(self.results)

    def get_context_text(self, max_results: int = 5, separator: str = "\n\n") -> str:
        """Combine top results into context text."""
        texts = [r.content for r in self.results[:max_results]]
        return separator.join(texts)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "query": self.query,
            "results": [r.to_dict() for r in self.results],
            "total_results": self.total_results,
            "retrieval_time_ms": self.retrieval_time_ms,
            "strategy_used": self.strategy_used.value,
            "filters_applied": self.filters_applied,
            "reranked": self.reranked,
            "truncated": self.truncated,
            "average_score": self.average_score
        }


@dataclass
class IndexStats:
    """Statistics about a knowledge index."""
    index_name: str
    total_vectors: int
    dimension: int
    namespaces: List[str]
    index_fullness: float  # 0.0 to 1.0
    last_updated: Optional[str] = None
    provider_info: Dict[str, Any] = field(default_factory=dict)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @abstractmethod
    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for single text."""
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return embedding dimension."""
        pass


class MockEmbeddingProvider(EmbeddingProvider):
    """Mock embedding provider for testing."""

    def __init__(self, dimension: int = 1536):
        self._dimension = dimension
        self._cache: Dict[str, List[float]] = {}

    def embed_text(self, text: str) -> List[float]:
        """Generate deterministic mock embedding."""
        if text in self._cache:
            return self._cache[text]

        # Create deterministic embedding from text hash
        text_hash = hashlib.sha256(text.encode()).hexdigest()
        embedding = []
        for i in range(0, min(len(text_hash), self._dimension * 2), 2):
            # Convert hex pairs to float values between -1 and 1
            value = (int(text_hash[i:i+2], 16) - 128) / 128.0
            embedding.append(value)

        # Pad or truncate to dimension
        while len(embedding) < self._dimension:
            embedding.append(0.0)
        embedding = embedding[:self._dimension]

        # Normalize
        magnitude = sum(x * x for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        self._cache[text] = embedding
        return embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch of texts."""
        return [self.embed_text(text) for text in texts]

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        return self._dimension


class VectorStore(ABC):
    """Abstract base class for vector stores."""

    @abstractmethod
    async def upsert(self, vectors: List[EmbeddingVector]) -> int:
        """Insert or update vectors."""
        pass

    @abstractmethod
    async def query(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        namespace: str = "default"
    ) -> List[RetrievalResult]:
        """Query for similar vectors."""
        pass

    @abstractmethod
    async def delete(self, vector_ids: List[str]) -> int:
        """Delete vectors by ID."""
        pass

    @abstractmethod
    async def get_stats(self) -> IndexStats:
        """Get index statistics."""
        pass


class InMemoryVectorStore(VectorStore):
    """In-memory vector store for development and testing."""

    def __init__(self, index_name: str = "default", dimension: int = 1536):
        self.index_name = index_name
        self.dimension = dimension
        self._vectors: Dict[str, Dict[str, EmbeddingVector]] = {}  # namespace -> {id -> vector}
        self._lock = threading.Lock()
        self._created_at = datetime.utcnow().isoformat()

    async def upsert(self, vectors: List[EmbeddingVector], namespace: str = "default") -> int:
        """Insert or update vectors."""
        with self._lock:
            if namespace not in self._vectors:
                self._vectors[namespace] = {}

            for vec in vectors:
                if len(vec.embedding) != self.dimension:
                    raise ValueError(
                        f"Vector dimension mismatch: expected {self.dimension}, "
                        f"got {len(vec.embedding)}"
                    )
                self._vectors[namespace][vec.vector_id] = vec

            return len(vectors)

    async def query(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        namespace: str = "default"
    ) -> List[RetrievalResult]:
        """Query for similar vectors using cosine similarity."""
        if namespace not in self._vectors:
            return []

        results = []

        with self._lock:
            for vec_id, vec in self._vectors[namespace].items():
                # Apply metadata filters if provided
                if filters:
                    if not self._matches_filters(vec.metadata, filters):
                        continue

                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_vector, vec.embedding)

                results.append(RetrievalResult(
                    result_id=vec_id,
                    content=vec.text_content,
                    similarity_score=similarity,
                    metadata=vec.metadata,
                    source_document=vec.source
                ))

        # Sort by similarity (descending) and take top_k
        results.sort(key=lambda x: x.similarity_score, reverse=True)
        return results[:top_k]

    async def delete(self, vector_ids: List[str], namespace: str = "default") -> int:
        """Delete vectors by ID."""
        deleted = 0
        with self._lock:
            if namespace in self._vectors:
                for vid in vector_ids:
                    if vid in self._vectors[namespace]:
                        del self._vectors[namespace][vid]
                        deleted += 1
        return deleted

    async def get_stats(self) -> IndexStats:
        """Get index statistics."""
        with self._lock:
            total_vectors = sum(len(vecs) for vecs in self._vectors.values())
            namespaces = list(self._vectors.keys())

            return IndexStats(
                index_name=self.index_name,
                total_vectors=total_vectors,
                dimension=self.dimension,
                namespaces=namespaces,
                index_fullness=0.0,  # In-memory has no limit
                last_updated=self._created_at,
                provider_info={"type": "in_memory", "version": "1.0"}
            )

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(x * x for x in vec1) ** 0.5
        magnitude2 = sum(x * x for x in vec2) ** 0.5

        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0

        return dot_product / (magnitude1 * magnitude2)

    def _matches_filters(self, metadata: Dict[str, Any], filters: Dict[str, Any]) -> bool:
        """Check if metadata matches all filters."""
        for key, value in filters.items():
            if key not in metadata:
                return False

            if isinstance(value, dict):
                # Handle operators like $eq, $ne, $in, $gt, $lt
                for op, op_value in value.items():
                    if op == "$eq" and metadata[key] != op_value:
                        return False
                    elif op == "$ne" and metadata[key] == op_value:
                        return False
                    elif op == "$in" and metadata[key] not in op_value:
                        return False
                    elif op == "$gt" and not (metadata[key] > op_value):
                        return False
                    elif op == "$lt" and not (metadata[key] < op_value):
                        return False
            else:
                if metadata[key] != value:
                    return False

        return True

    def clear(self, namespace: Optional[str] = None) -> int:
        """Clear vectors from the store."""
        with self._lock:
            if namespace:
                count = len(self._vectors.get(namespace, {}))
                self._vectors[namespace] = {}
                return count
            else:
                count = sum(len(vecs) for vecs in self._vectors.values())
                self._vectors.clear()
                return count


class QueryCache:
    """Cache for RAG query results."""

    def __init__(self, ttl_seconds: int = 3600, max_size: int = 1000):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._cache: Dict[str, Tuple[RetrievalContext, datetime]] = {}
        self._lock = threading.Lock()

    def _make_key(self, query: str, top_k: int, filters: Optional[Dict]) -> str:
        """Create cache key from query parameters."""
        key_data = {
            "query": query,
            "top_k": top_k,
            "filters": json.dumps(filters, sort_keys=True) if filters else ""
        }
        return hashlib.sha256(json.dumps(key_data, sort_keys=True).encode()).hexdigest()

    def get(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict] = None
    ) -> Optional[RetrievalContext]:
        """Get cached result if available and not expired."""
        key = self._make_key(query, top_k, filters)

        with self._lock:
            if key in self._cache:
                context, cached_at = self._cache[key]
                if datetime.utcnow() - cached_at < timedelta(seconds=self.ttl_seconds):
                    return context
                else:
                    # Expired, remove from cache
                    del self._cache[key]

        return None

    def set(
        self,
        query: str,
        top_k: int,
        filters: Optional[Dict],
        context: RetrievalContext
    ) -> None:
        """Cache a query result."""
        key = self._make_key(query, top_k, filters)

        with self._lock:
            # Evict if at capacity (simple LRU: just clear oldest)
            if len(self._cache) >= self.max_size:
                oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k][1])
                del self._cache[oldest_key]

            self._cache[key] = (context, datetime.utcnow())

    def clear(self) -> int:
        """Clear all cached results."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds
            }


class RAGConnector:
    """
    Main RAG connector for persona knowledge retrieval.

    Provides a unified interface for connecting to various vector stores
    and retrieving relevant context for persona-based decision making.
    """

    def __init__(
        self,
        config: Optional[RAGConfig] = None,
        embedding_provider: Optional[EmbeddingProvider] = None,
        vector_store: Optional[VectorStore] = None
    ):
        self.config = config or RAGConfig()
        self._embedding_provider = embedding_provider or MockEmbeddingProvider(
            dimension=self.config.embedding_dimension
        )
        self._vector_store = vector_store or InMemoryVectorStore(
            index_name=self.config.index_name,
            dimension=self.config.embedding_dimension
        )
        self._cache = QueryCache(
            ttl_seconds=self.config.cache_ttl_seconds
        ) if self.config.cache_enabled else None

        self._status = ConnectionStatus.DISCONNECTED
        self._last_error: Optional[str] = None
        self._query_count = 0
        self._total_latency_ms = 0.0
        self._lock = threading.Lock()

        logger.info(
            f"RAGConnector initialized with provider={self.config.provider_type.value}, "
            f"strategy={self.config.query_strategy.value}"
        )

    @property
    def status(self) -> ConnectionStatus:
        """Get current connection status."""
        return self._status

    @property
    def is_connected(self) -> bool:
        """Check if connected to vector store."""
        return self._status == ConnectionStatus.CONNECTED

    async def connect(self) -> bool:
        """
        Establish connection to the vector store.

        Returns:
            True if connection successful, False otherwise.
        """
        self._status = ConnectionStatus.CONNECTING
        logger.info(f"Connecting to RAG provider: {self.config.provider_type.value}")

        try:
            # Verify connection by getting stats
            stats = await self._vector_store.get_stats()

            self._status = ConnectionStatus.CONNECTED
            logger.info(
                f"Connected to RAG provider. Index: {stats.index_name}, "
                f"Vectors: {stats.total_vectors}"
            )
            return True

        except Exception as e:
            self._status = ConnectionStatus.ERROR
            self._last_error = str(e)
            logger.error(f"Failed to connect to RAG provider: {e}")
            return False

    async def disconnect(self) -> None:
        """Disconnect from the vector store."""
        self._status = ConnectionStatus.DISCONNECTED
        logger.info("Disconnected from RAG provider")

    async def retrieve(
        self,
        query: str,
        persona_id: Optional[str] = None,
        top_k: Optional[int] = None,
        min_score: Optional[float] = None,
        filters: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
        use_cache: bool = True
    ) -> RetrievalContext:
        """
        Retrieve relevant knowledge for a query.

        Args:
            query: The query text to search for.
            persona_id: Optional persona ID to filter results.
            top_k: Number of results to return.
            min_score: Minimum similarity score threshold.
            filters: Additional metadata filters.
            namespace: Vector store namespace to search.
            use_cache: Whether to use cached results.

        Returns:
            RetrievalContext with query results.
        """
        start_time = time.time()
        top_k = top_k or self.config.default_top_k
        min_score = min_score or self.config.min_similarity_threshold
        namespace = namespace or self.config.namespace

        # Build filters
        combined_filters = filters.copy() if filters else {}
        if persona_id:
            combined_filters["persona_id"] = persona_id

        # Check cache
        if use_cache and self._cache:
            cached = self._cache.get(query, top_k, combined_filters)
            if cached:
                logger.debug(f"Cache hit for query: {query[:50]}...")
                return cached

        # Generate query embedding
        query_embedding = self._embedding_provider.embed_text(query)

        # Execute retrieval based on strategy
        if self.config.query_strategy == QueryStrategy.SEMANTIC:
            results = await self._semantic_search(
                query_embedding, top_k, combined_filters, namespace
            )
        elif self.config.query_strategy == QueryStrategy.HYBRID:
            results = await self._hybrid_search(
                query, query_embedding, top_k, combined_filters, namespace
            )
        elif self.config.query_strategy == QueryStrategy.MMR:
            results = await self._mmr_search(
                query_embedding, top_k, combined_filters, namespace
            )
        else:
            results = await self._semantic_search(
                query_embedding, top_k, combined_filters, namespace
            )

        # Filter by minimum score
        filtered_results = [r for r in results if r.similarity_score >= min_score]

        # Create context
        retrieval_time = (time.time() - start_time) * 1000

        context = RetrievalContext(
            query=query,
            query_embedding=query_embedding,
            results=filtered_results,
            total_results=len(filtered_results),
            retrieval_time_ms=retrieval_time,
            strategy_used=self.config.query_strategy,
            filters_applied=combined_filters,
            reranked=False,
            truncated=len(results) > len(filtered_results)
        )

        # Update stats
        with self._lock:
            self._query_count += 1
            self._total_latency_ms += retrieval_time

        # Cache result
        if use_cache and self._cache:
            self._cache.set(query, top_k, combined_filters, context)

        logger.debug(
            f"Retrieved {len(filtered_results)} results for query in {retrieval_time:.2f}ms"
        )

        return context

    async def _semantic_search(
        self,
        query_vector: List[float],
        top_k: int,
        filters: Dict[str, Any],
        namespace: str
    ) -> List[RetrievalResult]:
        """Pure semantic similarity search."""
        return await self._vector_store.query(
            query_vector=query_vector,
            top_k=top_k,
            filters=filters if filters else None,
            namespace=namespace
        )

    async def _hybrid_search(
        self,
        query_text: str,
        query_vector: List[float],
        top_k: int,
        filters: Dict[str, Any],
        namespace: str
    ) -> List[RetrievalResult]:
        """
        Hybrid search combining semantic and keyword matching.

        Uses semantic search as base, then boosts results with keyword matches.
        """
        # Get semantic results (fetch more than needed for re-ranking)
        semantic_results = await self._vector_store.query(
            query_vector=query_vector,
            top_k=top_k * 2,
            filters=filters if filters else None,
            namespace=namespace
        )

        # Extract keywords from query (simple tokenization)
        keywords = set(query_text.lower().split())
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
                      "have", "has", "had", "do", "does", "did", "will", "would", "could",
                      "should", "may", "might", "must", "shall", "can", "of", "in", "to",
                      "for", "with", "on", "at", "by", "from", "as", "into", "through"}
        keywords = keywords - stop_words

        # Boost scores for keyword matches
        for result in semantic_results:
            content_lower = result.content.lower()
            keyword_matches = sum(1 for kw in keywords if kw in content_lower)

            # Boost score based on keyword matches (up to 20% boost)
            if keywords:
                keyword_boost = min(0.2, 0.05 * keyword_matches)
                result.similarity_score = min(1.0, result.similarity_score + keyword_boost)

        # Re-sort by adjusted scores
        semantic_results.sort(key=lambda x: x.similarity_score, reverse=True)

        return semantic_results[:top_k]

    async def _mmr_search(
        self,
        query_vector: List[float],
        top_k: int,
        filters: Dict[str, Any],
        namespace: str,
        lambda_param: float = 0.5
    ) -> List[RetrievalResult]:
        """
        Maximum Marginal Relevance search for diversity.

        Balances relevance with diversity to avoid redundant results.
        """
        # Get more candidates than needed
        candidates = await self._vector_store.query(
            query_vector=query_vector,
            top_k=top_k * 3,
            filters=filters if filters else None,
            namespace=namespace
        )

        if not candidates:
            return []

        # MMR selection
        selected: List[RetrievalResult] = []
        remaining = candidates.copy()

        # Always select the most relevant first
        selected.append(remaining.pop(0))

        while len(selected) < top_k and remaining:
            best_score = -float("inf")
            best_idx = 0

            for i, candidate in enumerate(remaining):
                # Relevance to query
                relevance = candidate.similarity_score

                # Similarity to already selected (using score as proxy)
                max_similarity = max(
                    abs(candidate.similarity_score - s.similarity_score)
                    for s in selected
                )
                diversity = 1 - max_similarity

                # MMR score
                mmr_score = lambda_param * relevance + (1 - lambda_param) * diversity

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i

            selected.append(remaining.pop(best_idx))

        return selected

    async def index_knowledge(
        self,
        documents: List[Dict[str, Any]],
        namespace: Optional[str] = None,
        batch_size: Optional[int] = None
    ) -> int:
        """
        Index documents into the knowledge base.

        Args:
            documents: List of documents with 'id', 'content', and optional 'metadata'.
            namespace: Target namespace for indexing.
            batch_size: Number of documents per batch.

        Returns:
            Number of documents indexed.
        """
        namespace = namespace or self.config.namespace
        batch_size = batch_size or self.config.batch_size

        total_indexed = 0

        # Process in batches
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]

            # Extract texts and generate embeddings
            texts = [doc.get("content", "") for doc in batch]
            embeddings = self._embedding_provider.embed_batch(texts)

            # Create embedding vectors
            vectors = []
            for doc, embedding in zip(batch, embeddings):
                vector = EmbeddingVector(
                    vector_id=doc.get("id", hashlib.sha256(doc["content"].encode()).hexdigest()[:16]),
                    embedding=embedding,
                    text_content=doc.get("content", ""),
                    metadata=doc.get("metadata", {}),
                    source=doc.get("source", "unknown")
                )
                vectors.append(vector)

            # Upsert to vector store
            indexed = await self._vector_store.upsert(vectors, namespace)
            total_indexed += indexed

            logger.debug(f"Indexed batch of {indexed} documents")

        logger.info(f"Total documents indexed: {total_indexed}")
        return total_indexed

    async def delete_knowledge(
        self,
        document_ids: List[str],
        namespace: Optional[str] = None
    ) -> int:
        """
        Delete documents from the knowledge base.

        Args:
            document_ids: List of document IDs to delete.
            namespace: Namespace to delete from.

        Returns:
            Number of documents deleted.
        """
        namespace = namespace or self.config.namespace
        deleted = await self._vector_store.delete(document_ids, namespace)
        logger.info(f"Deleted {deleted} documents from namespace '{namespace}'")
        return deleted

    async def get_index_stats(self) -> IndexStats:
        """Get statistics about the knowledge index."""
        return await self._vector_store.get_stats()

    def get_metrics(self) -> Dict[str, Any]:
        """Get connector metrics."""
        with self._lock:
            avg_latency = (
                self._total_latency_ms / self._query_count
                if self._query_count > 0 else 0.0
            )

            return {
                "status": self._status.value,
                "provider_type": self.config.provider_type.value,
                "query_strategy": self.config.query_strategy.value,
                "query_count": self._query_count,
                "average_latency_ms": avg_latency,
                "cache_enabled": self.config.cache_enabled,
                "cache_stats": self._cache.stats() if self._cache else None,
                "last_error": self._last_error
            }

    def clear_cache(self) -> int:
        """Clear the query cache."""
        if self._cache:
            return self._cache.clear()
        return 0


# Module-level singleton instance
_default_connector: Optional[RAGConnector] = None
_connector_lock = threading.Lock()


def get_rag_connector(config: Optional[RAGConfig] = None) -> RAGConnector:
    """
    Get or create the default RAG connector instance.

    Args:
        config: Optional configuration for new connector.

    Returns:
        RAGConnector instance.
    """
    global _default_connector

    with _connector_lock:
        if _default_connector is None:
            _default_connector = RAGConnector(config=config)
        return _default_connector


def reset_rag_connector() -> None:
    """Reset the default RAG connector instance."""
    global _default_connector

    with _connector_lock:
        _default_connector = None


async def retrieve_context(
    query: str,
    persona_id: Optional[str] = None,
    top_k: int = 10
) -> RetrievalContext:
    """
    Convenience function for quick context retrieval.

    Args:
        query: The query text.
        persona_id: Optional persona ID filter.
        top_k: Number of results.

    Returns:
        RetrievalContext with results.
    """
    connector = get_rag_connector()
    if not connector.is_connected:
        await connector.connect()

    return await connector.retrieve(
        query=query,
        persona_id=persona_id,
        top_k=top_k
    )
