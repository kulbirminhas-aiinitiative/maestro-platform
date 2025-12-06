"""
Embedding Providers for the Knowledge Store.

EPIC: MD-2557
AC-1: Support multiple embedding models (OpenAI, Claude, local)
"""

import hashlib
import logging
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from maestro_hive.knowledge.embeddings.exceptions import ProviderError, RateLimitError

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers.

    AC-1: Defines common interface for multiple providers.
    """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model name/identifier."""
        pass

    @property
    def provider_name(self) -> str:
        """Return the provider name."""
        return self.__class__.__name__

    @abstractmethod
    def embed(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector

        Raises:
            ProviderError: If embedding generation fails
        """
        pass

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Default implementation calls embed() for each text.
        Override for batch API support.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        return [self.embed(text) for text in texts]


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """
    OpenAI embedding provider.

    AC-1: Supports text-embedding-3-small and text-embedding-3-large models.
    """

    DEFAULT_MODEL = "text-embedding-3-small"
    DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        dimensions: Optional[int] = None,
    ):
        """
        Initialize OpenAI embedding provider.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: Model to use
            dimensions: Optional dimension reduction (text-embedding-3 only)
        """
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._model = model
        self._dimensions = dimensions or self.DIMENSIONS.get(model, 1536)
        self._client = None

    def _get_client(self) -> Any:
        """Lazy load OpenAI client."""
        if self._client is None:
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=self._api_key)
                logger.info(f"Initialized OpenAI client for model {self._model}")
            except ImportError:
                raise ProviderError(
                    "openai package not installed. "
                    "Install with: pip install openai"
                )
            except Exception as e:
                raise ProviderError(f"Failed to initialize OpenAI client: {e}")
        return self._client

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        return self._dimensions

    @property
    def model_name(self) -> str:
        """Return model name."""
        return self._model

    def embed(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        try:
            client = self._get_client()
            response = client.embeddings.create(
                model=self._model,
                input=text,
                dimensions=self._dimensions if "text-embedding-3" in self._model else None,
            )
            return response.data[0].embedding
        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower():
                raise RateLimitError(f"OpenAI rate limit: {e}")
            raise ProviderError(f"OpenAI embedding failed: {e}")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch of texts."""
        if not texts:
            return []
        try:
            client = self._get_client()
            response = client.embeddings.create(
                model=self._model,
                input=texts,
                dimensions=self._dimensions if "text-embedding-3" in self._model else None,
            )
            # Sort by index to ensure order matches input
            sorted_data = sorted(response.data, key=lambda x: x.index)
            return [item.embedding for item in sorted_data]
        except Exception as e:
            error_msg = str(e)
            if "rate_limit" in error_msg.lower():
                raise RateLimitError(f"OpenAI rate limit: {e}")
            raise ProviderError(f"OpenAI batch embedding failed: {e}")


class LocalEmbeddingProvider(EmbeddingProvider):
    """
    Local embedding provider using sentence-transformers.

    AC-1: Provides local model support without API dependency.
    """

    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: Optional[str] = None,
    ):
        """
        Initialize local embedding provider.

        Args:
            model_name: Sentence-transformer model name
            device: Device to run on ('cpu', 'cuda', or None for auto)
        """
        self._model_name = model_name
        self._device = device
        self._model = None
        self._dimension: Optional[int] = None

    def _load_model(self) -> Any:
        """Lazy load the sentence-transformer model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(
                    self._model_name,
                    device=self._device,
                )
                # Get dimension from test embedding
                test_embedding = self._model.encode(["test"])[0]
                self._dimension = len(test_embedding)
                logger.info(
                    f"Loaded local model {self._model_name} "
                    f"(dim={self._dimension}, device={self._device or 'auto'})"
                )
            except ImportError:
                raise ProviderError(
                    "sentence-transformers not installed. "
                    "Install with: pip install sentence-transformers"
                )
            except Exception as e:
                raise ProviderError(f"Failed to load model {self._model_name}: {e}")
        return self._model

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        if self._dimension is None:
            self._load_model()
        return self._dimension or 384  # Default for MiniLM

    @property
    def model_name(self) -> str:
        """Return model name."""
        return self._model_name

    def embed(self, text: str) -> List[float]:
        """Generate embedding using local model."""
        try:
            model = self._load_model()
            embedding = model.encode([text], convert_to_numpy=True)[0]
            return embedding.tolist()
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Local embedding failed: {e}")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for batch of texts."""
        if not texts:
            return []
        try:
            model = self._load_model()
            embeddings = model.encode(texts, convert_to_numpy=True)
            return [e.tolist() for e in embeddings]
        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Local batch embedding failed: {e}")


class SimpleHashEmbeddingProvider(EmbeddingProvider):
    """
    Simple hash-based embedding for testing/fallback.

    Uses character n-grams for basic similarity without external dependencies.
    """

    def __init__(self, dimension: int = 256):
        """Initialize with specified dimension."""
        self._dim = dimension

    @property
    def dimension(self) -> int:
        """Return embedding dimension."""
        return self._dim

    @property
    def model_name(self) -> str:
        """Return model name."""
        return "simple-hash"

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
            idx = int(hashlib.md5(ngram.encode()).hexdigest(), 16) % self._dim
            embedding[idx] += 1.0

        # Normalize to unit vector
        magnitude = sum(x * x for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding


def create_provider(
    provider_type: str,
    **kwargs: Any,
) -> EmbeddingProvider:
    """
    Factory function to create embedding providers.

    Args:
        provider_type: Type of provider ('openai', 'local', 'simple')
        **kwargs: Provider-specific configuration

    Returns:
        Configured EmbeddingProvider instance

    Raises:
        ValueError: If provider type is unknown
    """
    providers = {
        "openai": OpenAIEmbeddingProvider,
        "local": LocalEmbeddingProvider,
        "simple": SimpleHashEmbeddingProvider,
    }

    if provider_type not in providers:
        raise ValueError(
            f"Unknown provider type: {provider_type}. "
            f"Available: {list(providers.keys())}"
        )

    return providers[provider_type](**kwargs)
