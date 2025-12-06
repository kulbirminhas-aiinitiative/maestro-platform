"""
RAG Retrieval Service.

Core service orchestrating vector similarity search over past executions.

EPIC: MD-2499
AC-1: Vector similarity search on requirement text
AC-2: Retrieve top-k similar executions
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from maestro_hive.rag.context_formatter import ContextFormatter
from maestro_hive.rag.embeddings import (
    CachedEmbeddingProvider,
    EmbeddingCache,
    EmbeddingProvider,
    SimpleEmbedding,
)
from maestro_hive.rag.exceptions import EmbeddingError, RetrievalError
from maestro_hive.rag.models import (
    ContextConfig,
    ExecutionOutcome,
    ExecutionRecord,
    FormattedContext,
    RetrievalConfig,
    RetrievalResult,
)
from maestro_hive.rag.pattern_extractor import PatternExtractor
from maestro_hive.rag.storage import InMemoryStorage, StorageBackend

logger = logging.getLogger(__name__)


class RetrievalService:
    """
    RAG Retrieval Service for querying past executions.

    Provides vector similarity search over execution history,
    pattern extraction, and context formatting for persona injection.
    """

    def __init__(
        self,
        embedding_provider: Optional[EmbeddingProvider] = None,
        storage: Optional[StorageBackend] = None,
        config: Optional[RetrievalConfig] = None,
    ):
        """
        Initialize retrieval service.

        Args:
            embedding_provider: Provider for text embeddings (defaults to SimpleEmbedding)
            storage: Backend for execution storage (defaults to InMemoryStorage)
            config: Service configuration
        """
        self._config = config or RetrievalConfig()

        # Setup embedding provider with caching if enabled
        provider = embedding_provider or SimpleEmbedding()
        if self._config.cache_embeddings:
            cache = EmbeddingCache(max_size=1000)
            self._embedding = CachedEmbeddingProvider(provider, cache)
        else:
            self._embedding = provider

        self._storage = storage or InMemoryStorage()
        self._pattern_extractor = PatternExtractor()
        self._context_formatter = ContextFormatter()

        logger.info(
            f"RetrievalService initialized with {type(provider).__name__} "
            f"embeddings and {type(self._storage).__name__} storage"
        )

    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        threshold: Optional[float] = None,
    ) -> List[RetrievalResult]:
        """
        Search for similar past executions.

        Implements AC-1 (vector similarity search) and AC-2 (top-k retrieval).

        Args:
            query: Requirement text to search for
            top_k: Maximum number of results (default from config)
            threshold: Minimum similarity threshold 0.0-1.0 (default from config)

        Returns:
            List of RetrievalResult ordered by similarity (descending)

        Raises:
            RetrievalError: If search fails
        """
        top_k = top_k or self._config.default_top_k
        threshold = threshold if threshold is not None else self._config.similarity_threshold

        try:
            # Generate query embedding
            query_embedding = self._embedding.embed(query)

            # Search storage
            matches = self._storage.search_by_embedding(
                query_embedding,
                top_k=min(top_k, self._config.max_results),
                threshold=threshold,
            )

            # Convert to RetrievalResult objects
            results = []
            for record, similarity in matches:
                results.append(
                    RetrievalResult(
                        execution=record,
                        similarity_score=similarity,
                        match_details={
                            "query": query[:100],  # Truncate for readability
                            "matched_text": record.requirement_text[:100],
                        },
                    )
                )

            logger.info(
                f"Search returned {len(results)} results "
                f"(query: '{query[:50]}...', threshold: {threshold})"
            )
            return results

        except EmbeddingError as e:
            logger.warning(f"Embedding failed, falling back to keyword search: {e}")
            return self._keyword_search(query, top_k)
        except Exception as e:
            raise RetrievalError(f"Search failed: {e}")

    def _keyword_search(
        self,
        query: str,
        top_k: int,
    ) -> List[RetrievalResult]:
        """
        Fallback keyword-based search when embeddings fail.

        Uses simple word overlap scoring.
        """
        query_words = set(query.lower().split())
        records = self._storage.list_all()
        scored = []

        for record in records:
            record_words = set(record.requirement_text.lower().split())
            overlap = len(query_words & record_words)
            total = len(query_words | record_words)
            similarity = overlap / total if total > 0 else 0.0

            if similarity > 0:
                scored.append((record, similarity))

        scored.sort(key=lambda x: x[1], reverse=True)

        return [
            RetrievalResult(
                execution=record,
                similarity_score=score,
                match_details={"method": "keyword", "query": query[:100]},
            )
            for record, score in scored[:top_k]
        ]

    def store_execution(
        self,
        execution_id: str,
        requirement_text: str,
        outcome: ExecutionOutcome,
        metadata: Optional[Dict[str, Any]] = None,
        phase_results: Optional[Dict[str, Any]] = None,
        duration_seconds: float = 0.0,
    ) -> ExecutionRecord:
        """
        Store an execution record for future retrieval.

        Generates embedding and persists to storage.

        Args:
            execution_id: Unique identifier for the execution
            requirement_text: The original requirement/task text
            outcome: Execution outcome (SUCCESS, PARTIAL, FAILURE)
            metadata: Additional metadata
            phase_results: Per-phase execution results
            duration_seconds: Total execution duration

        Returns:
            The stored ExecutionRecord

        Raises:
            RetrievalError: If storage fails
        """
        try:
            # Generate embedding for the requirement text
            embedding = self._embedding.embed(requirement_text)

            # Create record
            record = ExecutionRecord(
                execution_id=execution_id,
                requirement_text=requirement_text,
                outcome=outcome,
                timestamp=datetime.utcnow(),
                duration_seconds=duration_seconds,
                phase_results=phase_results or {},
                metadata=metadata or {},
                embedding=embedding,
            )

            # Store
            self._storage.store(record)

            logger.info(
                f"Stored execution {execution_id} "
                f"(outcome: {outcome.value}, embedding dim: {len(embedding)})"
            )
            return record

        except Exception as e:
            raise RetrievalError(f"Failed to store execution: {e}")

    def get_context(
        self,
        query: str,
        max_tokens: int = 2000,
        top_k: Optional[int] = None,
        config: Optional[ContextConfig] = None,
    ) -> FormattedContext:
        """
        Get formatted context for persona injection.

        Combines search, pattern extraction, and formatting
        into a single convenient method.

        Args:
            query: Requirement text
            max_tokens: Maximum tokens in output
            top_k: Number of similar executions to analyze
            config: Optional formatting configuration

        Returns:
            FormattedContext ready for persona injection
        """
        # Search for similar executions
        results = self.search(query, top_k=top_k or 10)

        if not results:
            return FormattedContext(
                formatted_text="No similar past executions found.",
                token_count=6,
                execution_count=0,
                patterns_included=0,
                truncated=False,
            )

        # Extract patterns
        patterns = self._pattern_extractor.extract_patterns(results)

        # Format context
        format_config = config or ContextConfig(max_tokens=max_tokens)
        context = self._context_formatter.format(patterns, format_config)

        return context

    def get_execution(self, execution_id: str) -> Optional[ExecutionRecord]:
        """Get a specific execution by ID."""
        return self._storage.get(execution_id)

    def list_executions(
        self,
        outcome: Optional[ExecutionOutcome] = None,
        limit: int = 100,
    ) -> List[ExecutionRecord]:
        """
        List stored executions, optionally filtered by outcome.

        Args:
            outcome: Filter by outcome (None for all)
            limit: Maximum number to return

        Returns:
            List of ExecutionRecord
        """
        records = self._storage.list_all()

        if outcome:
            records = [r for r in records if r.outcome == outcome]

        # Sort by timestamp (most recent first)
        records.sort(key=lambda r: r.timestamp, reverse=True)

        return records[:limit]

    def delete_execution(self, execution_id: str) -> bool:
        """Delete an execution record."""
        return self._storage.delete(execution_id)

    @property
    def execution_count(self) -> int:
        """Return total number of stored executions."""
        return self._storage.count()

    @property
    def config(self) -> RetrievalConfig:
        """Return service configuration."""
        return self._config


def create_retrieval_service(
    use_local_embeddings: bool = True,
    storage_path: Optional[str] = None,
    config: Optional[RetrievalConfig] = None,
) -> RetrievalService:
    """
    Factory function to create a configured RetrievalService.

    Args:
        use_local_embeddings: Use local sentence-transformers (True) or simple embeddings (False)
        storage_path: Path for file storage (None for in-memory)
        config: Service configuration

    Returns:
        Configured RetrievalService
    """
    from maestro_hive.rag.storage import FileStorage, InMemoryStorage

    # Setup embedding provider
    if use_local_embeddings:
        try:
            from maestro_hive.rag.embeddings import LocalEmbedding

            embedding = LocalEmbedding()
        except Exception:
            logger.warning("LocalEmbedding unavailable, using SimpleEmbedding")
            embedding = SimpleEmbedding()
    else:
        embedding = SimpleEmbedding()

    # Setup storage
    if storage_path:
        storage = FileStorage(path=storage_path)
    else:
        storage = InMemoryStorage()

    return RetrievalService(
        embedding_provider=embedding,
        storage=storage,
        config=config,
    )
