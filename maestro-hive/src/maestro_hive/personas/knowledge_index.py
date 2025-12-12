#!/usr/bin/env python3
"""
Knowledge Index Manager: RAG storage and document management.

This module provides comprehensive knowledge index management for RAG systems,
including document ingestion, chunking, indexing, and lifecycle management.

Related EPIC: MD-3026 - RAG Persona Integration
"""

import json
import logging
import hashlib
import asyncio
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Callable, Iterator, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
from abc import ABC, abstractmethod
import re
import time

from .rag_connector import (
    RAGConnector,
    RAGConfig,
    EmbeddingVector,
    IndexStats,
    get_rag_connector,
    reset_rag_connector
)

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Types of documents that can be indexed."""
    TEXT = "text"
    MARKDOWN = "markdown"
    CODE = "code"
    JSON = "json"
    HTML = "html"
    PDF = "pdf"
    DOCX = "docx"
    STRUCTURED = "structured"


class ChunkingStrategy(Enum):
    """Strategies for chunking documents."""
    FIXED_SIZE = "fixed_size"           # Fixed character/token count
    SENTENCE = "sentence"               # Sentence-based splitting
    PARAGRAPH = "paragraph"             # Paragraph-based splitting
    SEMANTIC = "semantic"               # Semantic similarity-based
    RECURSIVE = "recursive"             # Recursive character splitting
    CODE_AWARE = "code_aware"           # Code structure-aware splitting
    HYBRID = "hybrid"                   # Combination of strategies


class IndexStatus(Enum):
    """Status of a knowledge index."""
    ACTIVE = "active"
    BUILDING = "building"
    UPDATING = "updating"
    STALE = "stale"
    ERROR = "error"
    ARCHIVED = "archived"


@dataclass
class IndexConfig:
    """Configuration for knowledge index."""
    index_name: str = "maestro_knowledge"
    namespace: str = "default"
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE
    chunk_size: int = 500  # Characters or tokens depending on strategy
    chunk_overlap: int = 50
    min_chunk_size: int = 100
    max_chunk_size: int = 2000
    embedding_batch_size: int = 100
    enable_metadata_extraction: bool = True
    preserve_structure: bool = True
    deduplicate_chunks: bool = True
    dedup_threshold: float = 0.95
    auto_refresh_hours: int = 24
    max_documents: int = 100000
    max_chunks_per_document: int = 1000
    retention_days: int = 365


@dataclass
class Document:
    """A document to be indexed."""
    document_id: str
    content: str
    document_type: DocumentType = DocumentType.TEXT
    title: Optional[str] = None
    source: Optional[str] = None
    author: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    persona_ids: List[str] = field(default_factory=list)  # Associated personas

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            **asdict(self),
            "document_type": self.document_type.value
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        """Create document from dictionary."""
        if "document_type" in data and isinstance(data["document_type"], str):
            data["document_type"] = DocumentType(data["document_type"])
        return cls(**data)

    @property
    def content_hash(self) -> str:
        """Get hash of document content."""
        return hashlib.sha256(self.content.encode()).hexdigest()


@dataclass
class DocumentChunk:
    """A chunk of a document."""
    chunk_id: str
    document_id: str
    content: str
    chunk_index: int
    start_position: int
    end_position: int
    token_count: int
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None

    def to_embedding_vector(self) -> EmbeddingVector:
        """Convert to EmbeddingVector for storage."""
        if self.embedding is None:
            raise ValueError("Chunk has no embedding")

        return EmbeddingVector(
            vector_id=self.chunk_id,
            embedding=self.embedding,
            text_content=self.content,
            metadata={
                **self.metadata,
                "document_id": self.document_id,
                "chunk_index": self.chunk_index
            },
            source=self.metadata.get("source", "unknown")
        )


@dataclass
class IndexedDocument:
    """Record of an indexed document."""
    document_id: str
    document_hash: str
    title: Optional[str]
    source: Optional[str]
    chunk_count: int
    indexed_at: str
    updated_at: str
    status: str = "active"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IndexingResult:
    """Result of an indexing operation."""
    success: bool
    documents_processed: int
    chunks_created: int
    chunks_indexed: int
    documents_failed: int
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class IndexHealth:
    """Health status of a knowledge index."""
    index_name: str
    status: IndexStatus
    total_documents: int
    total_chunks: int
    index_size_mb: float
    last_updated: Optional[str]
    stale_documents: int
    error_count: int
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            **asdict(self),
            "status": self.status.value
        }


class DocumentChunker:
    """Splits documents into chunks for indexing."""

    def __init__(
        self,
        strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        min_chunk_size: int = 100,
        max_chunk_size: int = 2000
    ):
        self.strategy = strategy
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

        # Separators for recursive splitting (in order of preference)
        self._separators = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""]

    def chunk_document(self, document: Document) -> List[DocumentChunk]:
        """Split a document into chunks."""
        if self.strategy == ChunkingStrategy.FIXED_SIZE:
            return self._chunk_fixed_size(document)
        elif self.strategy == ChunkingStrategy.SENTENCE:
            return self._chunk_by_sentence(document)
        elif self.strategy == ChunkingStrategy.PARAGRAPH:
            return self._chunk_by_paragraph(document)
        elif self.strategy == ChunkingStrategy.RECURSIVE:
            return self._chunk_recursive(document)
        elif self.strategy == ChunkingStrategy.CODE_AWARE:
            return self._chunk_code_aware(document)
        else:
            return self._chunk_recursive(document)

    def _chunk_fixed_size(self, document: Document) -> List[DocumentChunk]:
        """Split into fixed-size chunks."""
        chunks = []
        content = document.content
        position = 0
        chunk_index = 0

        while position < len(content):
            end = min(position + self.chunk_size, len(content))

            # Try to break at word boundary
            if end < len(content):
                last_space = content.rfind(" ", position, end)
                if last_space > position + self.chunk_size // 2:
                    end = last_space

            chunk_content = content[position:end].strip()

            if len(chunk_content) >= self.min_chunk_size:
                chunk = DocumentChunk(
                    chunk_id=f"{document.document_id}_chunk_{chunk_index}",
                    document_id=document.document_id,
                    content=chunk_content,
                    chunk_index=chunk_index,
                    start_position=position,
                    end_position=end,
                    token_count=self._estimate_tokens(chunk_content),
                    metadata={
                        "title": document.title,
                        "source": document.source,
                        **document.metadata
                    }
                )
                chunks.append(chunk)
                chunk_index += 1

            position = max(position + 1, end - self.chunk_overlap)

        return chunks

    def _chunk_by_sentence(self, document: Document) -> List[DocumentChunk]:
        """Split by sentences, grouping to target size."""
        sentences = re.split(r'(?<=[.!?])\s+', document.content)
        return self._group_segments(document, sentences)

    def _chunk_by_paragraph(self, document: Document) -> List[DocumentChunk]:
        """Split by paragraphs."""
        paragraphs = document.content.split("\n\n")
        return self._group_segments(document, paragraphs)

    def _chunk_recursive(self, document: Document) -> List[DocumentChunk]:
        """Recursively split text using hierarchical separators."""
        texts = self._split_recursive(document.content, self._separators)

        chunks = []
        chunk_index = 0
        current_position = 0

        for text in texts:
            text = text.strip()
            if len(text) >= self.min_chunk_size:
                # Find actual position in document
                start_pos = document.content.find(text, current_position)
                if start_pos == -1:
                    start_pos = current_position

                chunk = DocumentChunk(
                    chunk_id=f"{document.document_id}_chunk_{chunk_index}",
                    document_id=document.document_id,
                    content=text,
                    chunk_index=chunk_index,
                    start_position=start_pos,
                    end_position=start_pos + len(text),
                    token_count=self._estimate_tokens(text),
                    metadata={
                        "title": document.title,
                        "source": document.source,
                        **document.metadata
                    }
                )
                chunks.append(chunk)
                chunk_index += 1
                current_position = start_pos + len(text)

        return chunks

    def _split_recursive(
        self,
        text: str,
        separators: List[str]
    ) -> List[str]:
        """Recursively split text."""
        if not separators:
            return [text]

        separator = separators[0]
        remaining_separators = separators[1:]

        if not separator:
            # Character-level split as last resort
            return [text[i:i+self.chunk_size] for i in range(0, len(text), self.chunk_size)]

        splits = text.split(separator)
        result = []
        current_chunk = ""

        for split in splits:
            potential_chunk = current_chunk + separator + split if current_chunk else split

            if len(potential_chunk) <= self.chunk_size:
                current_chunk = potential_chunk
            else:
                if current_chunk:
                    if len(current_chunk) <= self.max_chunk_size:
                        result.append(current_chunk)
                    else:
                        # Recursively split large chunks
                        result.extend(self._split_recursive(current_chunk, remaining_separators))

                if len(split) <= self.chunk_size:
                    current_chunk = split
                else:
                    # Split is too large, recurse with remaining separators
                    result.extend(self._split_recursive(split, remaining_separators))
                    current_chunk = ""

        if current_chunk:
            result.append(current_chunk)

        return result

    def _chunk_code_aware(self, document: Document) -> List[DocumentChunk]:
        """Split code preserving structure."""
        content = document.content
        chunks = []
        chunk_index = 0

        # Split by function/class definitions for Python
        pattern = r'((?:def |class |async def )[^\n]+:(?:\n(?:[ \t]+[^\n]*|\n))*)'
        blocks = re.split(pattern, content)

        current_position = 0
        for block in blocks:
            block = block.strip()
            if len(block) >= self.min_chunk_size:
                start_pos = content.find(block, current_position)
                if start_pos == -1:
                    start_pos = current_position

                # If block is too large, sub-chunk it
                if len(block) > self.max_chunk_size:
                    sub_chunks = self._chunk_fixed_size(Document(
                        document_id=document.document_id,
                        content=block,
                        metadata=document.metadata
                    ))
                    for sub in sub_chunks:
                        sub.chunk_index = chunk_index
                        sub.chunk_id = f"{document.document_id}_chunk_{chunk_index}"
                        sub.start_position += start_pos
                        sub.end_position += start_pos
                        chunks.append(sub)
                        chunk_index += 1
                else:
                    chunk = DocumentChunk(
                        chunk_id=f"{document.document_id}_chunk_{chunk_index}",
                        document_id=document.document_id,
                        content=block,
                        chunk_index=chunk_index,
                        start_position=start_pos,
                        end_position=start_pos + len(block),
                        token_count=self._estimate_tokens(block),
                        metadata={
                            "title": document.title,
                            "source": document.source,
                            "type": "code_block",
                            **document.metadata
                        }
                    )
                    chunks.append(chunk)
                    chunk_index += 1

                current_position = start_pos + len(block)

        return chunks

    def _group_segments(
        self,
        document: Document,
        segments: List[str]
    ) -> List[DocumentChunk]:
        """Group segments into chunks of target size."""
        chunks = []
        chunk_index = 0
        current_content = ""
        current_start = 0
        position = 0

        for segment in segments:
            segment = segment.strip()
            if not segment:
                continue

            potential = current_content + "\n\n" + segment if current_content else segment

            if len(potential) <= self.chunk_size:
                if not current_content:
                    current_start = position
                current_content = potential
            else:
                # Save current chunk
                if current_content and len(current_content) >= self.min_chunk_size:
                    chunk = DocumentChunk(
                        chunk_id=f"{document.document_id}_chunk_{chunk_index}",
                        document_id=document.document_id,
                        content=current_content,
                        chunk_index=chunk_index,
                        start_position=current_start,
                        end_position=position,
                        token_count=self._estimate_tokens(current_content),
                        metadata={
                            "title": document.title,
                            "source": document.source,
                            **document.metadata
                        }
                    )
                    chunks.append(chunk)
                    chunk_index += 1

                current_content = segment
                current_start = position

            position += len(segment) + 2  # Account for separator

        # Add remaining content
        if current_content and len(current_content) >= self.min_chunk_size:
            chunk = DocumentChunk(
                chunk_id=f"{document.document_id}_chunk_{chunk_index}",
                document_id=document.document_id,
                content=current_content,
                chunk_index=chunk_index,
                start_position=current_start,
                end_position=len(document.content),
                token_count=self._estimate_tokens(current_content),
                metadata={
                    "title": document.title,
                    "source": document.source,
                    **document.metadata
                }
            )
            chunks.append(chunk)

        return chunks

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count."""
        return int(len(text) / 4)


class DocumentRegistry:
    """Registry for tracking indexed documents."""

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path
        self._documents: Dict[str, IndexedDocument] = {}
        self._lock = threading.Lock()

        if storage_path and storage_path.exists():
            self._load()

    def register(self, document: Document, chunk_count: int) -> IndexedDocument:
        """Register an indexed document."""
        now = datetime.utcnow().isoformat()

        indexed = IndexedDocument(
            document_id=document.document_id,
            document_hash=document.content_hash,
            title=document.title,
            source=document.source,
            chunk_count=chunk_count,
            indexed_at=now,
            updated_at=now,
            metadata=document.metadata
        )

        with self._lock:
            self._documents[document.document_id] = indexed

        self._save()
        return indexed

    def get(self, document_id: str) -> Optional[IndexedDocument]:
        """Get indexed document record."""
        with self._lock:
            return self._documents.get(document_id)

    def exists(self, document_id: str) -> bool:
        """Check if document is indexed."""
        with self._lock:
            return document_id in self._documents

    def needs_update(self, document: Document) -> bool:
        """Check if document needs re-indexing."""
        with self._lock:
            if document.document_id not in self._documents:
                return True

            indexed = self._documents[document.document_id]
            return indexed.document_hash != document.content_hash

    def remove(self, document_id: str) -> bool:
        """Remove document from registry."""
        with self._lock:
            if document_id in self._documents:
                del self._documents[document_id]
                self._save()
                return True
            return False

    def list_all(self) -> List[IndexedDocument]:
        """List all indexed documents."""
        with self._lock:
            return list(self._documents.values())

    def count(self) -> int:
        """Get total document count."""
        with self._lock:
            return len(self._documents)

    def _save(self) -> None:
        """Save registry to disk."""
        if not self.storage_path:
            return

        try:
            data = {
                doc_id: asdict(doc)
                for doc_id, doc in self._documents.items()
            }
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            self.storage_path.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save document registry: {e}")

    def _load(self) -> None:
        """Load registry from disk."""
        if not self.storage_path or not self.storage_path.exists():
            return

        try:
            data = json.loads(self.storage_path.read_text())
            self._documents = {
                doc_id: IndexedDocument(**doc_data)
                for doc_id, doc_data in data.items()
            }
        except Exception as e:
            logger.error(f"Failed to load document registry: {e}")


class KnowledgeIndexManager:
    """
    Manages knowledge indexing for RAG systems.

    Provides document ingestion, chunking, embedding, and index lifecycle
    management for persona knowledge bases.
    """

    def __init__(
        self,
        config: Optional[IndexConfig] = None,
        rag_connector: Optional[RAGConnector] = None,
        storage_path: Optional[Path] = None
    ):
        self.config = config or IndexConfig()
        self._rag_connector = rag_connector
        self._chunker = DocumentChunker(
            strategy=self.config.chunking_strategy,
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            min_chunk_size=self.config.min_chunk_size,
            max_chunk_size=self.config.max_chunk_size
        )

        registry_path = None
        if storage_path:
            registry_path = storage_path / "document_registry.json"
        self._registry = DocumentRegistry(storage_path=registry_path)

        self._status = IndexStatus.ACTIVE
        self._error_count = 0
        self._last_error: Optional[str] = None
        self._lock = threading.Lock()

        logger.info(
            f"KnowledgeIndexManager initialized for index '{self.config.index_name}' "
            f"with strategy={self.config.chunking_strategy.value}"
        )

    @property
    def rag_connector(self) -> RAGConnector:
        """Get or create RAG connector."""
        if self._rag_connector is None:
            self._rag_connector = get_rag_connector()
        return self._rag_connector

    @property
    def status(self) -> IndexStatus:
        """Get current index status."""
        return self._status

    async def index_document(
        self,
        document: Document,
        force_reindex: bool = False
    ) -> IndexingResult:
        """
        Index a single document.

        Args:
            document: Document to index.
            force_reindex: Whether to force re-indexing.

        Returns:
            IndexingResult with operation details.
        """
        return await self.index_documents([document], force_reindex=force_reindex)

    async def index_documents(
        self,
        documents: List[Document],
        force_reindex: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> IndexingResult:
        """
        Index multiple documents.

        Args:
            documents: Documents to index.
            force_reindex: Whether to force re-indexing.
            progress_callback: Optional callback for progress updates.

        Returns:
            IndexingResult with operation details.
        """
        start_time = time.time()
        self._status = IndexStatus.BUILDING

        total_chunks_created = 0
        total_chunks_indexed = 0
        documents_processed = 0
        documents_failed = 0
        errors: List[str] = []

        # Ensure connected
        if not self.rag_connector.is_connected:
            await self.rag_connector.connect()

        for i, document in enumerate(documents):
            try:
                # Check if update needed
                if not force_reindex and not self._registry.needs_update(document):
                    logger.debug(f"Skipping up-to-date document: {document.document_id}")
                    continue

                # Chunk the document
                chunks = self._chunker.chunk_document(document)
                total_chunks_created += len(chunks)

                if len(chunks) > self.config.max_chunks_per_document:
                    logger.warning(
                        f"Document {document.document_id} exceeds max chunks "
                        f"({len(chunks)} > {self.config.max_chunks_per_document})"
                    )
                    chunks = chunks[:self.config.max_chunks_per_document]

                # Generate embeddings in batches
                all_vectors = []
                for batch_start in range(0, len(chunks), self.config.embedding_batch_size):
                    batch = chunks[batch_start:batch_start + self.config.embedding_batch_size]

                    # Get embeddings
                    texts = [c.content for c in batch]
                    embeddings = self.rag_connector._embedding_provider.embed_batch(texts)

                    # Attach embeddings to chunks
                    for chunk, embedding in zip(batch, embeddings):
                        chunk.embedding = embedding
                        all_vectors.append(chunk.to_embedding_vector())

                # Index vectors
                indexed = await self.rag_connector._vector_store.upsert(
                    all_vectors, self.config.namespace
                )
                total_chunks_indexed += indexed

                # Update registry
                self._registry.register(document, len(chunks))
                documents_processed += 1

                # Progress callback
                if progress_callback:
                    progress_callback(i + 1, len(documents))

            except Exception as e:
                documents_failed += 1
                error_msg = f"Failed to index {document.document_id}: {str(e)}"
                errors.append(error_msg)
                logger.error(error_msg)

                with self._lock:
                    self._error_count += 1
                    self._last_error = error_msg

        duration = time.time() - start_time
        self._status = IndexStatus.ACTIVE if not errors else IndexStatus.ERROR

        result = IndexingResult(
            success=documents_failed == 0,
            documents_processed=documents_processed,
            chunks_created=total_chunks_created,
            chunks_indexed=total_chunks_indexed,
            documents_failed=documents_failed,
            errors=errors,
            duration_seconds=duration
        )

        logger.info(
            f"Indexing complete: {documents_processed} documents, "
            f"{total_chunks_indexed} chunks in {duration:.2f}s"
        )

        return result

    async def index_text(
        self,
        text: str,
        document_id: Optional[str] = None,
        title: Optional[str] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> IndexingResult:
        """
        Index a text string as a document.

        Args:
            text: Text content to index.
            document_id: Optional document ID.
            title: Optional title.
            source: Optional source.
            metadata: Optional metadata.

        Returns:
            IndexingResult.
        """
        doc_id = document_id or hashlib.sha256(text.encode()).hexdigest()[:16]

        document = Document(
            document_id=doc_id,
            content=text,
            title=title,
            source=source,
            metadata=metadata or {}
        )

        return await self.index_document(document)

    async def remove_document(self, document_id: str) -> bool:
        """
        Remove a document from the index.

        Args:
            document_id: Document ID to remove.

        Returns:
            True if removed successfully.
        """
        try:
            # Get chunk IDs for this document
            indexed = self._registry.get(document_id)
            if not indexed:
                return False

            chunk_ids = [
                f"{document_id}_chunk_{i}"
                for i in range(indexed.chunk_count)
            ]

            # Delete from vector store
            await self.rag_connector._vector_store.delete(
                chunk_ids, self.config.namespace
            )

            # Remove from registry
            self._registry.remove(document_id)

            logger.info(f"Removed document {document_id} and {len(chunk_ids)} chunks")
            return True

        except Exception as e:
            logger.error(f"Failed to remove document {document_id}: {e}")
            return False

    async def update_document(self, document: Document) -> IndexingResult:
        """
        Update an existing document.

        Args:
            document: Updated document.

        Returns:
            IndexingResult.
        """
        # Remove old version
        await self.remove_document(document.document_id)

        # Index new version
        return await self.index_document(document, force_reindex=True)

    async def clear_index(self, confirm: bool = False) -> int:
        """
        Clear all documents from the index.

        Args:
            confirm: Must be True to proceed.

        Returns:
            Number of documents removed.
        """
        if not confirm:
            raise ValueError("Must set confirm=True to clear index")

        documents = self._registry.list_all()
        count = 0

        for doc in documents:
            if await self.remove_document(doc.document_id):
                count += 1

        logger.info(f"Cleared {count} documents from index")
        return count

    async def get_health(self) -> IndexHealth:
        """
        Get health status of the index.

        Returns:
            IndexHealth with status details.
        """
        stats = await self.rag_connector.get_index_stats()
        documents = self._registry.list_all()

        # Check for stale documents
        stale_threshold = datetime.utcnow() - timedelta(
            hours=self.config.auto_refresh_hours
        )
        stale_count = sum(
            1 for doc in documents
            if datetime.fromisoformat(doc.updated_at) < stale_threshold
        )

        # Generate recommendations
        recommendations = []

        if stale_count > 0:
            recommendations.append(
                f"Consider refreshing {stale_count} stale documents"
            )

        if self._error_count > 5:
            recommendations.append(
                f"High error count ({self._error_count}). Check logs for details."
            )

        if stats.index_fullness > 0.8:
            recommendations.append(
                "Index is over 80% full. Consider archiving old documents."
            )

        return IndexHealth(
            index_name=self.config.index_name,
            status=self._status,
            total_documents=len(documents),
            total_chunks=stats.total_vectors,
            index_size_mb=0.0,  # Would need provider-specific calculation
            last_updated=max(
                (doc.updated_at for doc in documents),
                default=None
            ) if documents else None,
            stale_documents=stale_count,
            error_count=self._error_count,
            recommendations=recommendations
        )

    def get_document(self, document_id: str) -> Optional[IndexedDocument]:
        """Get document record by ID."""
        return self._registry.get(document_id)

    def list_documents(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[IndexedDocument]:
        """List indexed documents with pagination."""
        all_docs = self._registry.list_all()
        return all_docs[offset:offset + limit]

    def search_documents(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        source: Optional[str] = None
    ) -> List[IndexedDocument]:
        """
        Search indexed documents by metadata.

        Args:
            query: Search in title/source.
            tags: Filter by tags.
            source: Filter by source.

        Returns:
            Matching documents.
        """
        documents = self._registry.list_all()
        results = []

        for doc in documents:
            # Query filter
            if query:
                query_lower = query.lower()
                matches_query = (
                    (doc.title and query_lower in doc.title.lower()) or
                    (doc.source and query_lower in doc.source.lower())
                )
                if not matches_query:
                    continue

            # Source filter
            if source and doc.source != source:
                continue

            # Tags filter would need metadata parsing
            results.append(doc)

        return results

    def get_metrics(self) -> Dict[str, Any]:
        """Get index manager metrics."""
        with self._lock:
            return {
                "status": self._status.value,
                "index_name": self.config.index_name,
                "namespace": self.config.namespace,
                "chunking_strategy": self.config.chunking_strategy.value,
                "total_documents": self._registry.count(),
                "error_count": self._error_count,
                "last_error": self._last_error
            }


# Module-level singleton
_default_manager: Optional[KnowledgeIndexManager] = None
_manager_lock = threading.Lock()


def get_knowledge_index_manager(
    config: Optional[IndexConfig] = None
) -> KnowledgeIndexManager:
    """
    Get or create the default knowledge index manager.

    Args:
        config: Optional configuration.

    Returns:
        KnowledgeIndexManager instance.
    """
    global _default_manager

    with _manager_lock:
        if _default_manager is None:
            _default_manager = KnowledgeIndexManager(config=config)
        return _default_manager


def reset_knowledge_index_manager() -> None:
    """Reset the default knowledge index manager."""
    global _default_manager

    with _manager_lock:
        _default_manager = None


async def quick_index(
    texts: List[str],
    sources: Optional[List[str]] = None
) -> IndexingResult:
    """
    Convenience function for quick text indexing.

    Args:
        texts: List of texts to index.
        sources: Optional source labels.

    Returns:
        IndexingResult.
    """
    sources = sources or [None] * len(texts)
    manager = get_knowledge_index_manager()

    documents = [
        Document(
            document_id=hashlib.sha256(text.encode()).hexdigest()[:16],
            content=text,
            source=source
        )
        for text, source in zip(texts, sources)
    ]

    return await manager.index_documents(documents)
