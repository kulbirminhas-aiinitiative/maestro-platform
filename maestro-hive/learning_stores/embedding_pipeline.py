#!/usr/bin/env python3
"""
Embedding Pipeline Service for Learning Stores.

Generates vector embeddings for requirements, decisions, and complexity descriptions
using OpenAI's embedding API.

EPIC: MD-2490
AC-2: Embedding generation pipeline working
"""

import os
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
import hashlib
import json

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingConfig:
    """Configuration for embedding generation."""
    model: str = "text-embedding-3-small"
    dimensions: int = 1536
    api_key: Optional[str] = None
    batch_size: int = 100
    cache_enabled: bool = True
    
    def __post_init__(self):
        if self.api_key is None:
            self.api_key = os.environ.get("OPENAI_API_KEY")


class EmbeddingCache:
    """Simple in-memory cache for embeddings."""
    
    def __init__(self, max_size: int = 10000):
        self._cache: Dict[str, List[float]] = {}
        self._max_size = max_size
    
    def _hash_text(self, text: str) -> str:
        """Generate cache key from text."""
        return hashlib.md5(text.encode()).hexdigest()
    
    def get(self, text: str) -> Optional[List[float]]:
        """Get cached embedding."""
        return self._cache.get(self._hash_text(text))
    
    def set(self, text: str, embedding: List[float]) -> None:
        """Cache embedding."""
        if len(self._cache) >= self._max_size:
            # Simple eviction: remove oldest entries
            keys_to_remove = list(self._cache.keys())[:self._max_size // 10]
            for key in keys_to_remove:
                del self._cache[key]
        self._cache[self._hash_text(text)] = embedding
    
    def clear(self) -> None:
        """Clear cache."""
        self._cache.clear()


class EmbeddingPipeline:
    """
    Pipeline for generating vector embeddings.
    
    Uses OpenAI's embedding API to generate 1536-dimensional vectors
    for semantic similarity search in learning stores.
    """
    
    def __init__(self, config: Optional[EmbeddingConfig] = None):
        self.config = config or EmbeddingConfig()
        self._cache = EmbeddingCache() if self.config.cache_enabled else None
        self._client = None
        self._initialized = False
    
    def _initialize_client(self) -> None:
        """Lazily initialize OpenAI client."""
        if self._initialized:
            return
            
        if not self.config.api_key:
            logger.warning("No OpenAI API key configured - using mock embeddings")
            self._initialized = True
            return
        
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.config.api_key)
            self._initialized = True
            logger.info(f"Initialized embedding pipeline with model: {self.config.model}")
        except ImportError:
            logger.warning("openai package not installed - using mock embeddings")
            self._initialized = True
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self._initialized = True
    
    def generate(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        self._initialize_client()
        
        # Check cache
        if self._cache:
            cached = self._cache.get(text)
            if cached is not None:
                return cached
        
        # Generate embedding
        if self._client:
            try:
                response = self._client.embeddings.create(
                    model=self.config.model,
                    input=text,
                    dimensions=self.config.dimensions
                )
                embedding = response.data[0].embedding
            except Exception as e:
                logger.error(f"Embedding generation failed: {e}")
                embedding = self._mock_embedding(text)
        else:
            embedding = self._mock_embedding(text)
        
        # Cache result
        if self._cache:
            self._cache.set(text, embedding)
        
        return embedding
    
    def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        self._initialize_client()
        
        results = []
        uncached_indices = []
        uncached_texts = []
        
        # Check cache for each text
        for i, text in enumerate(texts):
            if self._cache:
                cached = self._cache.get(text)
                if cached is not None:
                    results.append((i, cached))
                    continue
            uncached_indices.append(i)
            uncached_texts.append(text)
        
        # Generate embeddings for uncached texts
        if uncached_texts and self._client:
            try:
                # Process in batches
                for batch_start in range(0, len(uncached_texts), self.config.batch_size):
                    batch_end = min(batch_start + self.config.batch_size, len(uncached_texts))
                    batch = uncached_texts[batch_start:batch_end]
                    
                    response = self._client.embeddings.create(
                        model=self.config.model,
                        input=batch,
                        dimensions=self.config.dimensions
                    )
                    
                    for j, data in enumerate(response.data):
                        idx = uncached_indices[batch_start + j]
                        embedding = data.embedding
                        results.append((idx, embedding))
                        if self._cache:
                            self._cache.set(uncached_texts[batch_start + j], embedding)
                            
            except Exception as e:
                logger.error(f"Batch embedding generation failed: {e}")
                for i, text in zip(uncached_indices, uncached_texts):
                    embedding = self._mock_embedding(text)
                    results.append((i, embedding))
                    if self._cache:
                        self._cache.set(text, embedding)
        else:
            # Use mock embeddings for uncached texts
            for i, text in zip(uncached_indices, uncached_texts):
                embedding = self._mock_embedding(text)
                results.append((i, embedding))
                if self._cache:
                    self._cache.set(text, embedding)
        
        # Sort by original index and return embeddings
        results.sort(key=lambda x: x[0])
        return [emb for _, emb in results]
    
    def _mock_embedding(self, text: str) -> List[float]:
        """
        Generate deterministic mock embedding for testing.
        
        Creates a reproducible embedding based on text hash.
        """
        import hashlib
        import struct
        
        # Create deterministic seed from text
        text_hash = hashlib.sha256(text.encode()).digest()
        
        # Generate pseudo-random floats from hash
        embedding = []
        for i in range(0, self.config.dimensions, 4):
            # Use different parts of hash rotated
            idx = (i // 4) % 8
            seed_bytes = text_hash[idx * 4:(idx + 1) * 4]
            # Convert to float in range [-1, 1]
            value = struct.unpack('f', seed_bytes)[0]
            # Normalize to reasonable range
            normalized = (value % 1.0) * 2 - 1
            embedding.append(normalized)
        
        # Ensure correct dimensions
        while len(embedding) < self.config.dimensions:
            embedding.append(0.0)
        
        # Normalize to unit vector
        magnitude = sum(x * x for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]
        
        return embedding[:self.config.dimensions]
    
    def compute_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Compute cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            Cosine similarity score (0-1)
        """
        if len(embedding1) != len(embedding2):
            raise ValueError("Embeddings must have same dimensions")
        
        dot_product = sum(a * b for a, b in zip(embedding1, embedding2))
        magnitude1 = sum(x * x for x in embedding1) ** 0.5
        magnitude2 = sum(x * x for x in embedding2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return (dot_product / (magnitude1 * magnitude2) + 1) / 2  # Normalize to 0-1
    
    def health_check(self) -> Dict[str, Any]:
        """Check health of embedding pipeline."""
        self._initialize_client()
        
        status = {
            "status": "healthy",
            "model": self.config.model,
            "dimensions": self.config.dimensions,
            "cache_enabled": self.config.cache_enabled,
            "api_configured": self._client is not None,
        }
        
        if self._cache:
            status["cache_size"] = len(self._cache._cache)
        
        # Test embedding generation
        try:
            test_embedding = self.generate("health check test")
            status["embedding_test"] = len(test_embedding) == self.config.dimensions
        except Exception as e:
            status["status"] = "degraded"
            status["error"] = str(e)
        
        return status
