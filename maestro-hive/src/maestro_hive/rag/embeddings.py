"""
Embedding Providers for RAG Service.

Handles text-to-vector conversion for semantic similarity search.
Supports multiple providers with graceful fallback.

EPIC: MD-2499
"""

import hashlib
import logging
from abc import ABC, abstractmethod
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from maestro_hive.rag.exceptions import EmbeddingError

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            EmbeddingError: If embedding generation fails
        """
        pass

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Default implementation calls embed() for each text.
        Override for more efficient batch processing.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        return [self.embed(text) for text in texts]


class LocalEmbedding(EmbeddingProvider):
    """
    Local embedding provider using sentence-transformers.

    No external API required - runs entirely locally.
    Default model: all-MiniLM-L6-v2 (384 dimensions)
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: Optional[str] = None,
    ):
        """
        Initialize local embedding provider.

        Args:
            model_name: Name of sentence-transformer model
            device: Device to run on ('cpu', 'cuda', or None for auto)
        """
        self.model_name = model_name
        self._model = None
        self._device = device
        self._dimension: Optional[int] = None

    def _load_model(self) -> Any:
        """Lazy load the model on first use."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(
                    self.model_name,
                    device=self._device,
                )
                # Get dimension from a test embedding
                test_embedding = self._model.encode(["test"])[0]
                self._dimension = len(test_embedding)
                logger.info(
                    f"Loaded embedding model {self.model_name} "
                    f"(dim={self._dimension})"
                )
            except ImportError:
                raise EmbeddingError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
            except Exception as e:
                raise EmbeddingError(f"Failed to load model {self.model_name}: {e}")
        return self._model

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        if self._dimension is None:
            self._load_model()
        return self._dimension or 384  # Default for MiniLM

    def embed(self, text: str) -> List[float]:
        """Generate embedding for text."""
        try:
            model = self._load_model()
            embedding = model.encode([text], convert_to_numpy=True)[0]
            return embedding.tolist()
        except EmbeddingError:
            raise
        except Exception as e:
            raise EmbeddingError(f"Embedding generation failed: {e}")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch of texts."""
        if not texts:
            return []
        try:
            model = self._load_model()
            embeddings = model.encode(texts, convert_to_numpy=True)
            return [e.tolist() for e in embeddings]
        except EmbeddingError:
            raise
        except Exception as e:
            raise EmbeddingError(f"Batch embedding failed: {e}")


class SimpleEmbedding(EmbeddingProvider):
    """
    Simple TF-IDF-like embedding for testing/fallback.

    Uses character n-grams for basic similarity without external dependencies.
    """

    def __init__(self, dimension: int = 256):
        """Initialize with specified dimension."""
        self._dim = dimension

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        return self._dim

    def embed(self, text: str) -> List[float]:
        """Generate simple hash-based embedding."""
        # Normalize text
        text = text.lower().strip()

        # Generate character n-grams (2-4 grams)
        ngrams = []
        for n in range(2, 5):
            for i in range(len(text) - n + 1):
                ngrams.append(text[i : i + n])

        # Hash each n-gram to a dimension
        embedding = [0.0] * self._dim
        for ngram in ngrams:
            # Use hash to get consistent index
            idx = int(hashlib.md5(ngram.encode()).hexdigest(), 16) % self._dim
            embedding[idx] += 1.0

        # Normalize to unit vector
        magnitude = sum(x * x for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding


class EmbeddingCache:
    """
    LRU cache for computed embeddings.

    Reduces API calls and computation for repeated queries.
    """

    def __init__(self, max_size: int = 1000):
        """
        Initialize cache.

        Args:
            max_size: Maximum number of embeddings to cache
        """
        self.max_size = max_size
        self._cache: OrderedDict[str, List[float]] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def _make_key(self, text: str, provider_name: str) -> str:
        """Create cache key from text and provider."""
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return f"{provider_name}:{text_hash}"

    def get(
        self,
        text: str,
        provider: EmbeddingProvider,
    ) -> Optional[List[float]]:
        """
        Get cached embedding if available.

        Args:
            text: Original text
            provider: Embedding provider used

        Returns:
            Cached embedding or None
        """
        key = self._make_key(text, provider.__class__.__name__)
        if key in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]
        self._misses += 1
        return None

    def put(
        self,
        text: str,
        provider: EmbeddingProvider,
        embedding: List[float],
    ) -> None:
        """
        Store embedding in cache.

        Args:
            text: Original text
            provider: Embedding provider used
            embedding: Computed embedding
        """
        key = self._make_key(text, provider.__class__.__name__)

        # Remove oldest if at capacity
        while len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)

        self._cache[key] = embedding

    def clear(self) -> None:
        """Clear all cached embeddings."""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    @property
    def hit_rate(self) -> float:
        """Return cache hit rate (0.0-1.0)."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def size(self) -> int:
        """Return current cache size."""
        return len(self._cache)

    def stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        return {
            "size": self.size,
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
        }


class CachedEmbeddingProvider(EmbeddingProvider):
    """
    Wrapper that adds caching to any embedding provider.
    """

    def __init__(
        self,
        provider: EmbeddingProvider,
        cache: Optional[EmbeddingCache] = None,
    ):
        """
        Initialize cached provider.

        Args:
            provider: Underlying embedding provider
            cache: Cache instance (creates new if None)
        """
        self._provider = provider
        self._cache = cache or EmbeddingCache()

    @property
    def dimension(self) -> int:
        """Return embedding dimension from underlying provider."""
        return self._provider.dimension

    def embed(self, text: str) -> List[float]:
        """Get embedding from cache or compute."""
        # Check cache first
        cached = self._cache.get(text, self._provider)
        if cached is not None:
            return cached

        # Compute and cache
        embedding = self._provider.embed(text)
        self._cache.put(text, self._provider, embedding)
        return embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Get batch embeddings with caching."""
        results: List[Optional[List[float]]] = [None] * len(texts)
        to_compute: List[tuple[int, str]] = []

        # Check cache for each
        for i, text in enumerate(texts):
            cached = self._cache.get(text, self._provider)
            if cached is not None:
                results[i] = cached
            else:
                to_compute.append((i, text))

        # Compute missing embeddings in batch
        if to_compute:
            indices, texts_to_compute = zip(*to_compute)
            computed = self._provider.embed_batch(list(texts_to_compute))

            for idx, text, embedding in zip(indices, texts_to_compute, computed):
                self._cache.put(text, self._provider, embedding)
                results[idx] = embedding

        return [r for r in results if r is not None]

    @property
    def cache_stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        return self._cache.stats()
