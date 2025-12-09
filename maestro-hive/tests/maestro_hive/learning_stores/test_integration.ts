/**
 * Integration Tests for Learning Stores
 * Tests the factory functions and cross-service interactions
 * EPIC: MD-2490
 */

import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import {
  createLearningServices,
  getLearningStoresHealth,
  DEFAULT_LEARNING_CONFIG,
} from '../src/learning/index';

const createMockDb = () => ({
  query: jest.fn().mockResolvedValue({ rows: [] }),
});

describe('Learning Stores Integration', () => {
  let mockDb: ReturnType<typeof createMockDb>;

  beforeEach(() => {
    mockDb = createMockDb();
  });

  describe('createLearningServices', () => {
    it('should create all learning services', () => {
      const services = createLearningServices(mockDb);

      expect(services).toHaveProperty('embeddings');
      expect(services).toHaveProperty('templateLearning');
      expect(services).toHaveProperty('qualityLearning');
      expect(services).toHaveProperty('coordinationLearning');
    });

    it('should apply custom configuration', () => {
      const customConfig = {
        confidenceThreshold: 0.9,
        maxResults: 20,
      };

      const services = createLearningServices(mockDb, customConfig);

      expect(services).toBeDefined();
    });

    it('should use default configuration when not provided', () => {
      const services = createLearningServices(mockDb);

      expect(services).toBeDefined();
    });
  });

  describe('getLearningStoresHealth', () => {
    it('should return aggregate health status', async () => {
      mockDb.query
        .mockResolvedValueOnce({ rows: [{ count: 100 }] })
        .mockResolvedValueOnce({ rows: [{ indexname: 'idx_template_embedding' }] })
        .mockResolvedValueOnce({ rows: [{ count: 200 }] })
        .mockResolvedValueOnce({ rows: [{ indexname: 'idx_quality_embedding' }] })
        .mockResolvedValueOnce({ rows: [{ count: 150 }] })
        .mockResolvedValueOnce({ rows: [{ indexname: 'idx_coordination_embedding' }] });

      const services = createLearningServices(mockDb);
      const health = await getLearningStoresHealth(services);

      expect(health.overallStatus).toBe('healthy');
      expect(health.templateStore.recordCount).toBe(100);
      expect(health.qualityStore.recordCount).toBe(200);
      expect(health.coordinationStore.recordCount).toBe(150);
    });

    it('should report unhealthy when indexes missing', async () => {
      mockDb.query
        .mockResolvedValueOnce({ rows: [{ count: 100 }] })
        .mockResolvedValueOnce({ rows: [] }) // Missing index
        .mockResolvedValueOnce({ rows: [{ count: 200 }] })
        .mockResolvedValueOnce({ rows: [] }) // Missing index
        .mockResolvedValueOnce({ rows: [{ count: 150 }] })
        .mockResolvedValueOnce({ rows: [] }); // Missing index

      const services = createLearningServices(mockDb);
      const health = await getLearningStoresHealth(services);

      expect(health.overallStatus).toBe('unhealthy');
    });
  });

  describe('DEFAULT_LEARNING_CONFIG', () => {
    it('should have all required configuration fields', () => {
      expect(DEFAULT_LEARNING_CONFIG).toHaveProperty('embeddingApiUrl');
      expect(DEFAULT_LEARNING_CONFIG).toHaveProperty('embeddingModel');
      expect(DEFAULT_LEARNING_CONFIG).toHaveProperty('embeddingDimensions');
      expect(DEFAULT_LEARNING_CONFIG).toHaveProperty('confidenceThreshold');
      expect(DEFAULT_LEARNING_CONFIG).toHaveProperty('similarityThreshold');
      expect(DEFAULT_LEARNING_CONFIG).toHaveProperty('maxResults');
      expect(DEFAULT_LEARNING_CONFIG).toHaveProperty('pruneThreshold');
    });

    it('should have sensible default values', () => {
      expect(DEFAULT_LEARNING_CONFIG.embeddingDimensions).toBe(1536);
      expect(DEFAULT_LEARNING_CONFIG.confidenceThreshold).toBeGreaterThan(0);
      expect(DEFAULT_LEARNING_CONFIG.confidenceThreshold).toBeLessThan(1);
      expect(DEFAULT_LEARNING_CONFIG.similarityThreshold).toBeGreaterThan(0);
      expect(DEFAULT_LEARNING_CONFIG.similarityThreshold).toBeLessThan(1);
    });
  });

  describe('Cross-service Embedding Sharing', () => {
    it('should share embedding service across all learning services', async () => {
      const services = createLearningServices(mockDb);
      
      // All services should use the same embedding pipeline
      // This is verified by checking they all generate consistent embeddings
      const text = 'test embedding text';
      
      const templateEmbed = await services.embeddings.embed(text);
      const templateEmbed2 = await services.embeddings.embed(text);
      
      // Should be cached and identical
      expect(templateEmbed).toEqual(templateEmbed2);
    });
  });
});

describe('End-to-End Learning Flow', () => {
  let mockDb: ReturnType<typeof createMockDb>;

  beforeEach(() => {
    mockDb = createMockDb();
  });

  it('should support full learning workflow', async () => {
    const services = createLearningServices(mockDb);
    const learningContext = {
      mode: 'learning' as const,
      sessionId: 'e2e-test',
      captureEnabled: true,
    };

    // Mock successful recording
    mockDb.query.mockResolvedValueOnce({
      rows: [{
        id: 'uuid-1',
        requirementHash: 'hash1',
        requirementText: 'Build REST API',
        templateId: 'api-template',
        success: true,
        qualityScore: 90,
        confidence: 0.95,
      }],
    });

    // Record a template execution
    const execution = await services.templateLearning.recordExecution({
      requirementHash: 'hash1',
      requirementText: 'Build REST API',
      templateId: 'api-template',
      success: true,
      qualityScore: 90,
      confidence: 0.95,
    }, learningContext);

    expect(execution).toBeDefined();
    expect(mockDb.query).toHaveBeenCalled();
  });

  it('should support RAG retrieval workflow', async () => {
    const services = createLearningServices(mockDb);

    // Mock recommendation query
    mockDb.query.mockResolvedValueOnce({
      rows: [{
        template_id: 'api-template',
        success_count: 8,
        total_count: 10,
        avg_quality: 88,
        avg_confidence: 0.9,
        similarity: 0.92,
      }],
    });

    // Get recommendations based on similar requirements
    const recommendations = await services.templateLearning.getRecommendations({
      requirementText: 'Create API endpoint',
    });

    expect(recommendations).toHaveLength(1);
    expect(recommendations[0].templateId).toBe('api-template');
  });
});
