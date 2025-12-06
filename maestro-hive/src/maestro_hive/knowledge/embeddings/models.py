"""
Data Models for Embedding Pipeline.

EPIC: MD-2557
AC-3: Metadata preserved with embeddings (source, timestamp, domain)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import hashlib


@dataclass
class ChunkMetadata:
    """
    Metadata for an embedded chunk.

    AC-3: Preserves source, timestamp, and domain information.
    """
    source: str  # Origin path/URL
    domain: str  # code, documentation, execution, etc.
    timestamp: datetime  # When processed
    content_type: str  # python, markdown, json, etc.
    chunk_index: int  # Position in document
    total_chunks: int  # Total chunks in document
    parent_id: str  # Reference to parent document
    custom: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "domain": self.domain,
            "timestamp": self.timestamp.isoformat(),
            "content_type": self.content_type,
            "chunk_index": self.chunk_index,
            "total_chunks": self.total_chunks,
            "parent_id": self.parent_id,
            "custom": self.custom,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ChunkMetadata":
        """Create from dictionary."""
        return cls(
            source=data["source"],
            domain=data["domain"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            content_type=data["content_type"],
            chunk_index=data["chunk_index"],
            total_chunks=data["total_chunks"],
            parent_id=data["parent_id"],
            custom=data.get("custom", {}),
        )


@dataclass
class Chunk:
    """A chunk of document content ready for embedding."""
    content: str
    start_position: int
    end_position: int
    metadata: Optional[ChunkMetadata] = None


@dataclass
class Document:
    """
    A document to be embedded.

    Represents raw content from various sources (files, URLs, logs).
    """
    id: str
    content: str
    source: str  # file path, URL, etc.
    domain: str  # code, documentation, execution
    content_type: str  # python, markdown, json
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

    def content_hash(self) -> str:
        """
        Generate SHA-256 hash of content for change detection.

        Used by AC-5 (incremental updates).
        """
        content_bytes = self.content.encode("utf-8")
        return hashlib.sha256(content_bytes).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source,
            "domain": self.domain,
            "content_type": self.content_type,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Document":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            content=data["content"],
            source=data["source"],
            domain=data["domain"],
            content_type=data["content_type"],
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if data.get("updated_at")
                else None
            ),
        )


@dataclass
class EmbeddedChunk:
    """A chunk with its embedding vector."""
    chunk_id: str
    content: str
    embedding: List[float]
    position: int
    metadata: ChunkMetadata


@dataclass
class EmbeddedDocument:
    """
    A fully embedded document with all chunks.

    AC-3: Contains all metadata from source document.
    """
    id: str
    document_id: str
    chunks: List[EmbeddedChunk]
    provider: str  # Which provider generated embeddings
    model: str  # Which model was used
    processed_at: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)
    content_hash: Optional[str] = None  # For incremental updates

    @property
    def chunk_count(self) -> int:
        """Return number of chunks."""
        return len(self.chunks)

    @property
    def total_embedding_dimension(self) -> int:
        """Return embedding dimension."""
        if self.chunks:
            return len(self.chunks[0].embedding)
        return 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "document_id": self.document_id,
            "chunks": [
                {
                    "chunk_id": c.chunk_id,
                    "content": c.content,
                    "embedding": c.embedding,
                    "position": c.position,
                    "metadata": c.metadata.to_dict(),
                }
                for c in self.chunks
            ],
            "provider": self.provider,
            "model": self.model,
            "processed_at": self.processed_at.isoformat(),
            "metadata": self.metadata,
            "content_hash": self.content_hash,
        }


@dataclass
class PipelineConfig:
    """Configuration for the embedding pipeline."""
    batch_size: int = 100
    max_retries: int = 3
    timeout_seconds: float = 30.0
    cache_enabled: bool = True
    fallback_providers: List[str] = field(default_factory=list)
    chunk_overlap: int = 50
    max_chunk_size: int = 512
