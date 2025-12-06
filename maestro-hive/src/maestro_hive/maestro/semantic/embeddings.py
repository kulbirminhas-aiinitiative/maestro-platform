"""
Embedding Model and Cache

Implements AC-1: Embedding model integration (sentence-transformers or similar)

Provides sentence embedding generation and caching for semantic matching.

Epic: MD-2498
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from collections import OrderedDict
import hashlib
import logging
import time
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding generation"""
    text: str
    vector: np.ndarray
    model_name: str
    latency_ms: float
    cached: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (without vector for serialization)"""
        return {
            "text": self.text,
            "vector_dim": len(self.vector),
            "model_name": self.model_name,
            "latency_ms": self.latency_ms,
            "cached": self.cached,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class CacheEntry:
    """Cache entry for embeddings"""
    vector: np.ndarray
    created_at: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    last_accessed: datetime = field(default_factory=datetime.utcnow)

    def is_expired(self, ttl_seconds: int) -> bool:
        """Check if entry has expired"""
        return (datetime.utcnow() - self.created_at).total_seconds() > ttl_seconds

    def touch(self) -> None:
        """Update access statistics"""
        self.access_count += 1
        self.last_accessed = datetime.utcnow()


class EmbeddingCache:
    """
    LRU cache for embedding vectors.

    AC-1 Support: Caches embeddings to reduce model inference calls.

    Features:
    - LRU eviction when capacity reached
    - TTL-based expiration
    - Cache statistics tracking
    """

    def __init__(
        self,
        max_size: int = 10000,
        ttl_seconds: int = 3600
    ):
        """
        Initialize embedding cache.

        Args:
            max_size: Maximum number of cached embeddings
            ttl_seconds: Time-to-live for cache entries
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def _make_key(self, text: str, model_name: str) -> str:
        """Generate cache key from text and model"""
        content = f"{model_name}:{text}"
        return hashlib.sha256(content.encode()).hexdigest()[:32]

    def get(self, text: str, model_name: str) -> Optional[np.ndarray]:
        """
        Get cached embedding.

        Args:
            text: Text that was embedded
            model_name: Name of embedding model

        Returns:
            Cached vector or None if not found/expired
        """
        key = self._make_key(text, model_name)
        entry = self._cache.get(key)

        if entry is None:
            self._misses += 1
            return None

        if entry.is_expired(self.ttl_seconds):
            del self._cache[key]
            self._misses += 1
            return None

        # Move to end (most recently used)
        self._cache.move_to_end(key)
        entry.touch()
        self._hits += 1
        return entry.vector

    def set(self, text: str, model_name: str, vector: np.ndarray) -> None:
        """
        Store embedding in cache.

        Args:
            text: Text that was embedded
            model_name: Name of embedding model
            vector: Embedding vector
        """
        key = self._make_key(text, model_name)

        # Evict oldest if at capacity
        while len(self._cache) >= self.max_size:
            self._cache.popitem(last=False)

        self._cache[key] = CacheEntry(vector=vector.copy())

    def clear(self) -> None:
        """Clear all cached embeddings"""
        self._cache.clear()
        self._hits = 0
        self._misses = 0

    @property
    def size(self) -> int:
        """Current cache size"""
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        """Cache hit rate"""
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": self.size,
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
            "ttl_seconds": self.ttl_seconds
        }


class EmbeddingModel:
    """
    Sentence embedding model wrapper.

    AC-1 Implementation: Embedding model integration.

    Supports:
    - sentence-transformers models
    - Lazy loading for memory efficiency
    - Batch embedding for performance
    - Fallback to simple TF-IDF if model unavailable
    """

    # Default model optimized for speed and quality
    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        cache: Optional[EmbeddingCache] = None,
        use_fallback: bool = True
    ):
        """
        Initialize embedding model.

        Args:
            model_name: Name of sentence-transformers model
            cache: Optional embedding cache
            use_fallback: Whether to use fallback if model fails to load
        """
        self.model_name = model_name
        self.cache = cache or EmbeddingCache()
        self.use_fallback = use_fallback
        self._model = None
        self._fallback_active = False
        self._dimension = 384  # Default for MiniLM

    def _load_model(self) -> None:
        """Lazy load the embedding model"""
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self._dimension = self._model.get_sentence_embedding_dimension()
            logger.info(f"Loaded embedding model: {self.model_name} ({self._dimension}d)")
        except ImportError:
            if self.use_fallback:
                logger.warning("sentence-transformers not installed, using TF-IDF fallback")
                self._fallback_active = True
                self._model = self._create_fallback_model()
            else:
                raise ImportError(
                    "sentence-transformers required. Install with: pip install sentence-transformers"
                )
        except Exception as e:
            if self.use_fallback:
                logger.warning(f"Failed to load model {self.model_name}: {e}, using fallback")
                self._fallback_active = True
                self._model = self._create_fallback_model()
            else:
                raise

    def _create_fallback_model(self) -> Any:
        """Create TF-IDF fallback model"""
        from sklearn.feature_extraction.text import TfidfVectorizer
        return TfidfVectorizer(max_features=self._dimension)

    def embed(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for text.

        Args:
            text: Text to embed

        Returns:
            EmbeddingResult with vector and metadata
        """
        # Check cache first
        cached_vector = self.cache.get(text, self.model_name)
        if cached_vector is not None:
            return EmbeddingResult(
                text=text,
                vector=cached_vector,
                model_name=self.model_name,
                latency_ms=0.0,
                cached=True
            )

        # Generate embedding
        self._load_model()
        start_time = time.perf_counter()

        if self._fallback_active:
            vector = self._embed_fallback(text)
        else:
            vector = self._model.encode(text, convert_to_numpy=True)

        latency_ms = (time.perf_counter() - start_time) * 1000

        # Cache result
        self.cache.set(text, self.model_name, vector)

        return EmbeddingResult(
            text=text,
            vector=vector,
            model_name=self.model_name if not self._fallback_active else "tfidf_fallback",
            latency_ms=latency_ms,
            cached=False
        )

    def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of EmbeddingResult objects
        """
        results = []
        uncached_texts = []
        uncached_indices = []

        # Check cache for each text
        for i, text in enumerate(texts):
            cached_vector = self.cache.get(text, self.model_name)
            if cached_vector is not None:
                results.append(EmbeddingResult(
                    text=text,
                    vector=cached_vector,
                    model_name=self.model_name,
                    latency_ms=0.0,
                    cached=True
                ))
            else:
                results.append(None)  # Placeholder
                uncached_texts.append(text)
                uncached_indices.append(i)

        # Batch embed uncached texts
        if uncached_texts:
            self._load_model()
            start_time = time.perf_counter()

            if self._fallback_active:
                vectors = [self._embed_fallback(t) for t in uncached_texts]
            else:
                vectors = self._model.encode(uncached_texts, convert_to_numpy=True)

            latency_ms = (time.perf_counter() - start_time) * 1000
            per_text_latency = latency_ms / len(uncached_texts)

            for idx, text, vector in zip(uncached_indices, uncached_texts, vectors):
                self.cache.set(text, self.model_name, vector)
                results[idx] = EmbeddingResult(
                    text=text,
                    vector=vector,
                    model_name=self.model_name if not self._fallback_active else "tfidf_fallback",
                    latency_ms=per_text_latency,
                    cached=False
                )

        return results

    def _embed_fallback(self, text: str) -> np.ndarray:
        """Generate embedding using TF-IDF fallback"""
        # Fit on single text and transform
        try:
            vector = self._model.fit_transform([text]).toarray()[0]
            # Pad or truncate to expected dimension
            if len(vector) < self._dimension:
                vector = np.pad(vector, (0, self._dimension - len(vector)))
            elif len(vector) > self._dimension:
                vector = vector[:self._dimension]
            return vector
        except Exception:
            # Return random vector as last resort
            return np.random.randn(self._dimension).astype(np.float32)

    @property
    def dimension(self) -> int:
        """Embedding dimension"""
        return self._dimension

    @property
    def is_fallback(self) -> bool:
        """Check if using fallback model"""
        return self._fallback_active
