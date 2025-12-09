/**
 * Embedding Pipeline Service Tests
 * AC-2: Embedding generation pipeline working
 * EPIC: MD-2490
 */

import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import {
  EmbeddingPipelineService,
  LocalEmbeddingProvider,
  OpenAIEmbeddingProvider,
} from '../src/learning/embeddingPipeline.service';

describe('LocalEmbeddingProvider', () => {
  let provider: LocalEmbeddingProvider;

  beforeEach(() => {
    provider = new LocalEmbeddingProvider(1536);
  });

  it('should generate embedding with correct dimensions', async () => {
    const embedding = await provider.generateEmbedding('test text');
    expect(embedding).toHaveLength(1536);
  });

  it('should generate normalized unit vectors', async () => {
    const embedding = await provider.generateEmbedding('test text');
    const magnitude = Math.sqrt(embedding.reduce((sum, v) => sum + v * v, 0));
    expect(magnitude).toBeCloseTo(1.0, 5);
  });

  it('should generate deterministic embeddings for same text', async () => {
    const embedding1 = await provider.generateEmbedding('hello world');
    const embedding2 = await provider.generateEmbedding('hello world');
    expect(embedding1).toEqual(embedding2);
  });

  it('should generate different embeddings for different text', async () => {
    const embedding1 = await provider.generateEmbedding('hello world');
    const embedding2 = await provider.generateEmbedding('goodbye world');
    expect(embedding1).not.toEqual(embedding2);
  });

  it('should handle batch embeddings', async () => {
    const texts = ['text1', 'text2', 'text3'];
    const embeddings = await provider.batchGenerateEmbeddings(texts);
    expect(embeddings).toHaveLength(3);
    embeddings.forEach(emb => expect(emb).toHaveLength(1536));
  });
});

describe('EmbeddingPipelineService', () => {
  let service: EmbeddingPipelineService;
  let provider: LocalEmbeddingProvider;

  beforeEach(() => {
    provider = new LocalEmbeddingProvider(1536);
    service = new EmbeddingPipelineService(provider, {
      cacheTtlMs: 60000,
      maxCacheSize: 100,
    });
  });

  describe('embed', () => {
    it('should return embedding for text', async () => {
      const embedding = await service.embed('test text');
      expect(embedding).toHaveLength(1536);
    });

    it('should cache embeddings', async () => {
      const spy = jest.spyOn(provider, 'generateEmbedding');
      
      await service.embed('cached text');
      await service.embed('cached text');
      
      expect(spy).toHaveBeenCalledTimes(1);
    });

    it('should return cached embedding for repeated calls', async () => {
      const embedding1 = await service.embed('test');
      const embedding2 = await service.embed('test');
      expect(embedding1).toEqual(embedding2);
    });
  });

  describe('embedBatch', () => {
    it('should return embeddings for multiple texts', async () => {
      const texts = ['text1', 'text2', 'text3'];
      const embeddings = await service.embedBatch(texts);
      expect(embeddings).toHaveLength(3);
    });

    it('should use cache for already embedded texts', async () => {
      await service.embed('pre-cached');
      const spy = jest.spyOn(provider, 'batchGenerateEmbeddings');
      
      await service.embedBatch(['pre-cached', 'new-text']);
      
      const callArg = spy.mock.calls[0]?.[0];
      expect(callArg).toEqual(['new-text']);
    });
  });

  describe('cosineSimilarity', () => {
    it('should return 1 for identical vectors', () => {
      const vec = [0.5, 0.5, 0.5, 0.5];
      expect(service.cosineSimilarity(vec, vec)).toBeCloseTo(1.0, 5);
    });

    it('should return 0 for orthogonal vectors', () => {
      const vec1 = [1, 0, 0, 0];
      const vec2 = [0, 1, 0, 0];
      expect(service.cosineSimilarity(vec1, vec2)).toBeCloseTo(0, 5);
    });

    it('should return -1 for opposite vectors', () => {
      const vec1 = [1, 0, 0, 0];
      const vec2 = [-1, 0, 0, 0];
      expect(service.cosineSimilarity(vec1, vec2)).toBeCloseTo(-1, 5);
    });

    it('should throw for mismatched dimensions', () => {
      expect(() => service.cosineSimilarity([1, 2], [1, 2, 3])).toThrow();
    });
  });

  describe('euclideanDistance', () => {
    it('should return 0 for identical vectors', () => {
      const vec = [1, 2, 3];
      expect(service.euclideanDistance(vec, vec)).toBe(0);
    });

    it('should calculate correct distance', () => {
      const vec1 = [0, 0, 0];
      const vec2 = [3, 4, 0];
      expect(service.euclideanDistance(vec1, vec2)).toBe(5);
    });

    it('should throw for mismatched dimensions', () => {
      expect(() => service.euclideanDistance([1, 2], [1, 2, 3])).toThrow();
    });
  });

  describe('cache management', () => {
    it('should report cache stats', () => {
      const stats = service.getCacheStats();
      expect(stats).toHaveProperty('size');
      expect(stats).toHaveProperty('maxSize');
    });

    it('should clear cache', async () => {
      await service.embed('test');
      expect(service.getCacheStats().size).toBeGreaterThan(0);
      
      service.clearCache();
      expect(service.getCacheStats().size).toBe(0);
    });

    it('should evict oldest entries when cache is full', async () => {
      const smallCacheService = new EmbeddingPipelineService(provider, {
        maxCacheSize: 2,
      });

      await smallCacheService.embed('text1');
      await smallCacheService.embed('text2');
      await smallCacheService.embed('text3');

      expect(smallCacheService.getCacheStats().size).toBe(2);
    });
  });
});
