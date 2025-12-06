"""
Embedding Pipeline Orchestrator.

EPIC: MD-2557
AC-4: Batch processing for bulk ingestion
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

from maestro_hive.knowledge.embeddings.cache import (
    CacheEntry,
    ContentCache,
    InMemoryCache,
)
from maestro_hive.knowledge.embeddings.chunker import DocumentChunker, SemanticChunker
from maestro_hive.knowledge.embeddings.exceptions import EmbeddingError, ProviderError
from maestro_hive.knowledge.embeddings.models import (
    Chunk,
    ChunkMetadata,
    Document,
    EmbeddedChunk,
    EmbeddedDocument,
    PipelineConfig,
)
from maestro_hive.knowledge.embeddings.providers import (
    EmbeddingProvider,
    SimpleHashEmbeddingProvider,
)

logger = logging.getLogger(__name__)


class EmbeddingPipeline:
    """
    Main orchestrator for the embedding pipeline.

    Coordinates document chunking, embedding generation, caching,
    and batch processing.

    AC-4: Provides batch processing for bulk ingestion.
    AC-5: Supports incremental updates via content cache.
    """

    def __init__(
        self,
        provider: Optional[EmbeddingProvider] = None,
        chunker: Optional[DocumentChunker] = None,
        cache: Optional[ContentCache] = None,
        config: Optional[PipelineConfig] = None,
    ):
        """
        Initialize embedding pipeline.

        Args:
            provider: Embedding provider (defaults to SimpleHashEmbeddingProvider)
            chunker: Document chunker (defaults to SemanticChunker)
            cache: Content cache (defaults to InMemoryCache)
            config: Pipeline configuration
        """
        self._provider = provider or SimpleHashEmbeddingProvider()
        self._chunker = chunker or SemanticChunker()
        self._cache = cache or InMemoryCache()
        self._config = config or PipelineConfig()

        logger.info(
            f"EmbeddingPipeline initialized with "
            f"provider={self._provider.provider_name}, "
            f"chunker={self._chunker.strategy_name}"
        )

    def process_document(
        self,
        document: Document,
        force_reprocess: bool = False,
    ) -> EmbeddedDocument:
        """
        Process a single document into embeddings.

        Args:
            document: Document to process
            force_reprocess: Skip cache check if True

        Returns:
            EmbeddedDocument with all chunk embeddings

        Raises:
            EmbeddingError: If processing fails
        """
        try:
            # Check cache for incremental update (AC-5)
            content_hash = document.content_hash()
            if not force_reprocess and self._config.cache_enabled:
                if not self._cache.has_changed(document.id, content_hash):
                    logger.info(f"Document {document.id} unchanged, skipping embedding")
                    # Return cached result would require storing full embeddings
                    # For now, raise to indicate no change
                    return self._create_unchanged_result(document, content_hash)

            # Chunk the document (AC-2)
            chunks = self._chunker.chunk(document.content)
            logger.debug(f"Document {document.id} split into {len(chunks)} chunks")

            # Generate embeddings
            embedded_chunks = self._embed_chunks(document, chunks)

            # Create result
            embedded_doc = EmbeddedDocument(
                id=str(uuid4()),
                document_id=document.id,
                chunks=embedded_chunks,
                provider=self._provider.provider_name,
                model=self._provider.model_name,
                processed_at=datetime.utcnow(),
                metadata=document.metadata,
                content_hash=content_hash,
            )

            # Update cache
            if self._config.cache_enabled:
                self._cache.put(
                    CacheEntry(
                        content_hash=content_hash,
                        document_id=document.id,
                        embedded_at=embedded_doc.processed_at,
                        provider=self._provider.provider_name,
                        model=self._provider.model_name,
                        chunk_count=len(embedded_chunks),
                        metadata=document.metadata,
                    )
                )

            logger.info(
                f"Document {document.id} embedded: "
                f"{len(embedded_chunks)} chunks, "
                f"dim={self._provider.dimension}"
            )

            return embedded_doc

        except Exception as e:
            raise EmbeddingError(f"Failed to process document {document.id}: {e}")

    def process_batch(
        self,
        documents: List[Document],
        max_concurrent: int = 4,
        force_reprocess: bool = False,
    ) -> List[EmbeddedDocument]:
        """
        Process multiple documents in parallel.

        AC-4: Batch processing for bulk ingestion.

        Args:
            documents: List of documents to process
            max_concurrent: Maximum concurrent processing
            force_reprocess: Skip cache check if True

        Returns:
            List of EmbeddedDocument (may be fewer if some unchanged)
        """
        if not documents:
            return []

        results: List[EmbeddedDocument] = []
        errors: List[tuple[str, Exception]] = []

        # Use thread pool for parallel processing
        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = {
                executor.submit(
                    self.process_document, doc, force_reprocess
                ): doc.id
                for doc in documents
            }

            for future in as_completed(futures):
                doc_id = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    errors.append((doc_id, e))
                    logger.warning(f"Failed to process {doc_id}: {e}")

        logger.info(
            f"Batch complete: {len(results)} processed, "
            f"{len(errors)} errors"
        )

        return results

    def process_incremental(
        self,
        document: Document,
    ) -> Optional[EmbeddedDocument]:
        """
        Process only if content has changed since last embedding.

        AC-5: Incremental updates - don't re-embed unchanged content.

        Args:
            document: Document to process

        Returns:
            EmbeddedDocument if changed, None if unchanged
        """
        content_hash = document.content_hash()

        if not self._cache.has_changed(document.id, content_hash):
            logger.debug(f"Document {document.id} unchanged")
            return None

        return self.process_document(document, force_reprocess=True)

    def _embed_chunks(
        self,
        document: Document,
        chunks: List[Chunk],
    ) -> List[EmbeddedChunk]:
        """Generate embeddings for chunks."""
        embedded_chunks = []
        total_chunks = len(chunks)

        # Batch embedding if supported
        if hasattr(self._provider, "embed_batch") and len(chunks) > 1:
            try:
                texts = [c.content for c in chunks]
                embeddings = self._provider.embed_batch(texts)

                for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                    metadata = ChunkMetadata(
                        source=document.source,
                        domain=document.domain,
                        timestamp=datetime.utcnow(),
                        content_type=document.content_type,
                        chunk_index=i,
                        total_chunks=total_chunks,
                        parent_id=document.id,
                        custom=document.metadata,
                    )

                    embedded_chunks.append(
                        EmbeddedChunk(
                            chunk_id=str(uuid4()),
                            content=chunk.content,
                            embedding=embedding,
                            position=i,
                            metadata=metadata,
                        )
                    )

                return embedded_chunks

            except Exception as e:
                logger.warning(f"Batch embedding failed, falling back to single: {e}")

        # Fall back to single embedding
        for i, chunk in enumerate(chunks):
            try:
                embedding = self._provider.embed(chunk.content)

                metadata = ChunkMetadata(
                    source=document.source,
                    domain=document.domain,
                    timestamp=datetime.utcnow(),
                    content_type=document.content_type,
                    chunk_index=i,
                    total_chunks=total_chunks,
                    parent_id=document.id,
                    custom=document.metadata,
                )

                embedded_chunks.append(
                    EmbeddedChunk(
                        chunk_id=str(uuid4()),
                        content=chunk.content,
                        embedding=embedding,
                        position=i,
                        metadata=metadata,
                    )
                )

            except ProviderError as e:
                logger.error(f"Failed to embed chunk {i}: {e}")
                raise

        return embedded_chunks

    def _create_unchanged_result(
        self,
        document: Document,
        content_hash: str,
    ) -> EmbeddedDocument:
        """Create result for unchanged document."""
        return EmbeddedDocument(
            id=str(uuid4()),
            document_id=document.id,
            chunks=[],  # No chunks - document unchanged
            provider=self._provider.provider_name,
            model=self._provider.model_name,
            processed_at=datetime.utcnow(),
            metadata={"unchanged": True, **document.metadata},
            content_hash=content_hash,
        )

    def health_check(self) -> Dict[str, Any]:
        """Check pipeline health."""
        try:
            # Test embedding
            test_embedding = self._provider.embed("health check")
            embedding_ok = len(test_embedding) == self._provider.dimension

            return {
                "status": "healthy" if embedding_ok else "degraded",
                "provider": self._provider.provider_name,
                "model": self._provider.model_name,
                "dimension": self._provider.dimension,
                "cache_size": self._cache.size(),
                "cache_enabled": self._config.cache_enabled,
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    @property
    def provider(self) -> EmbeddingProvider:
        """Get the embedding provider."""
        return self._provider

    @property
    def chunker(self) -> DocumentChunker:
        """Get the document chunker."""
        return self._chunker

    @property
    def cache(self) -> ContentCache:
        """Get the content cache."""
        return self._cache

    @property
    def config(self) -> PipelineConfig:
        """Get the pipeline configuration."""
        return self._config


def create_pipeline(
    provider_type: str = "simple",
    chunker_type: str = "semantic",
    cache_type: str = "memory",
    config: Optional[PipelineConfig] = None,
    **kwargs: Any,
) -> EmbeddingPipeline:
    """
    Factory function to create a configured pipeline.

    Args:
        provider_type: Provider type ('openai', 'local', 'simple')
        chunker_type: Chunker type ('semantic', 'fixed', 'code')
        cache_type: Cache type ('memory', 'file')
        config: Pipeline configuration
        **kwargs: Additional provider/chunker configuration

    Returns:
        Configured EmbeddingPipeline
    """
    from maestro_hive.knowledge.embeddings.providers import create_provider
    from maestro_hive.knowledge.embeddings.chunker import create_chunker
    from maestro_hive.knowledge.embeddings.cache import InMemoryCache, FileCache

    provider = create_provider(provider_type, **kwargs.get("provider_config", {}))
    chunker = create_chunker(chunker_type, **kwargs.get("chunker_config", {}))

    if cache_type == "memory":
        cache = InMemoryCache(**kwargs.get("cache_config", {}))
    elif cache_type == "file":
        cache = FileCache(**kwargs.get("cache_config", {}))
    else:
        cache = InMemoryCache()

    return EmbeddingPipeline(
        provider=provider,
        chunker=chunker,
        cache=cache,
        config=config,
    )
