/**
 * Template Learning Service Tests
 * AC-1: Three learning tables with proper indexes
 * AC-3: RAG retrieval queries return relevant results
 * AC-4: Quality threshold filters low-confidence data
 * AC-5: Learning stores populated during LEARNING mode
 * EPIC: MD-2490
 */

import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { TemplateLearningService } from '../src/learning/templateLearning.service';
import { EmbeddingPipelineService, LocalEmbeddingProvider } from '../src/learning/embeddingPipeline.service';
import { LearningStoreConfig, LearningModeContext, TemplateExecution } from '../src/learning/types';

// Mock database client
const createMockDb = () => ({
  query: jest.fn().mockResolvedValue({ rows: [] }),
});

const defaultConfig: LearningStoreConfig = {
  embeddingApiUrl: 'http://localhost/embeddings',
  embeddingModel: 'test-model',
  embeddingDimensions: 1536,
  confidenceThreshold: 0.7,
  similarityThreshold: 0.8,
  maxResults: 10,
  pruneThreshold: 0.3,
};

const learningContext: LearningModeContext = {
  mode: 'learning',
  sessionId: 'test-session',
  captureEnabled: true,
};

const inferenceContext: LearningModeContext = {
  mode: 'inference',
  sessionId: 'test-session',
  captureEnabled: false,
};

describe('TemplateLearningService', () => {
  let service: TemplateLearningService;
  let mockDb: ReturnType<typeof createMockDb>;
  let embeddings: EmbeddingPipelineService;

  beforeEach(() => {
    mockDb = createMockDb();
    embeddings = new EmbeddingPipelineService(new LocalEmbeddingProvider(1536));
    service = new TemplateLearningService(mockDb, embeddings, defaultConfig);
  });

  describe('recordExecution', () => {
    const execution = {
      requirementHash: 'abc123',
      requirementText: 'Create a REST API endpoint',
      templateId: 'api-template-v1',
      success: true,
      qualityScore: 85.5,
      confidence: 0.9,
    };

    it('should record execution in learning mode (AC-5)', async () => {
      mockDb.query.mockResolvedValueOnce({ rows: [{ ...execution, id: 'uuid-1', createdAt: new Date() }] });

      const result = await service.recordExecution(execution, learningContext);

      expect(mockDb.query).toHaveBeenCalled();
      expect(result).toBeDefined();
    });

    it('should not record in inference mode (AC-5)', async () => {
      const result = await service.recordExecution(execution, inferenceContext);

      expect(mockDb.query).not.toHaveBeenCalled();
      expect(result).toBeNull();
    });

    it('should not record when capture is disabled (AC-5)', async () => {
      const disabledContext = { ...learningContext, captureEnabled: false };
      const result = await service.recordExecution(execution, disabledContext);

      expect(mockDb.query).not.toHaveBeenCalled();
      expect(result).toBeNull();
    });

    it('should filter low-confidence data (AC-4)', async () => {
      const lowConfidenceExecution = { ...execution, confidence: 0.5 };
      const result = await service.recordExecution(lowConfidenceExecution, learningContext);

      expect(mockDb.query).not.toHaveBeenCalled();
      expect(result).toBeNull();
    });

    it('should generate embedding for requirement text', async () => {
      const embedSpy = jest.spyOn(embeddings, 'embed');
      mockDb.query.mockResolvedValueOnce({ rows: [{ ...execution, id: 'uuid-1' }] });

      await service.recordExecution(execution, learningContext);

      expect(embedSpy).toHaveBeenCalledWith(execution.requirementText);
    });
  });

  describe('getRecommendations', () => {
    it('should return template recommendations (AC-3)', async () => {
      mockDb.query.mockResolvedValueOnce({
        rows: [
          {
            template_id: 'api-template-v1',
            success_count: 8,
            total_count: 10,
            avg_quality: 85.0,
            avg_confidence: 0.9,
            similarity: 0.95,
          },
        ],
      });

      const recommendations = await service.getRecommendations({
        requirementText: 'Create a REST API',
      });

      expect(recommendations).toHaveLength(1);
      expect(recommendations[0].templateId).toBe('api-template-v1');
      expect(recommendations[0].successRate).toBe(0.8);
      expect(recommendations[0].similarity).toBe(0.95);
    });

    it('should apply confidence threshold (AC-4)', async () => {
      await service.getRecommendations({ requirementText: 'test' });

      const queryCall = mockDb.query.mock.calls[0];
      expect(queryCall[1]).toContain(defaultConfig.confidenceThreshold);
    });

    it('should apply similarity threshold (AC-3)', async () => {
      await service.getRecommendations({ requirementText: 'test' });

      const queryCall = mockDb.query.mock.calls[0];
      expect(queryCall[1]).toContain(defaultConfig.similarityThreshold);
    });

    it('should respect limit parameter', async () => {
      await service.getRecommendations({ requirementText: 'test', limit: 5 });

      const queryCall = mockDb.query.mock.calls[0];
      expect(queryCall[1]).toContain(5);
    });

    it('should generate embedding for query text', async () => {
      const embedSpy = jest.spyOn(embeddings, 'embed');

      await service.getRecommendations({ requirementText: 'test query' });

      expect(embedSpy).toHaveBeenCalledWith('test query');
    });
  });

  describe('findSimilarExecutions', () => {
    it('should return similar executions with similarity scores', async () => {
      mockDb.query.mockResolvedValueOnce({
        rows: [
          {
            id: 'uuid-1',
            requirementHash: 'hash1',
            requirementText: 'Similar requirement',
            templateId: 'template-1',
            success: true,
            qualityScore: 90,
            confidence: 0.95,
            similarity: 0.92,
            distance: 0.08,
          },
        ],
      });

      const results = await service.findSimilarExecutions('test requirement');

      expect(results).toHaveLength(1);
      expect(results[0].similarity).toBe(0.92);
      expect(results[0].item.templateId).toBe('template-1');
    });

    it('should filter by template ID when provided', async () => {
      await service.findSimilarExecutions('test', 'specific-template');

      const queryCall = mockDb.query.mock.calls[0];
      expect(queryCall[1]).toContain('specific-template');
    });
  });

  describe('getTemplateStats', () => {
    it('should return statistics for a template', async () => {
      mockDb.query.mockResolvedValueOnce({
        rows: [{ total: 100, success_count: 85, avg_quality: 88.5, avg_confidence: 0.92 }],
      });

      const stats = await service.getTemplateStats('template-1');

      expect(stats).toBeDefined();
      expect(stats!.totalExecutions).toBe(100);
      expect(stats!.successRate).toBe(0.85);
      expect(stats!.avgQualityScore).toBe(88.5);
    });

    it('should return null for unknown template', async () => {
      mockDb.query.mockResolvedValueOnce({ rows: [{ total: 0 }] });

      const stats = await service.getTemplateStats('unknown-template');

      expect(stats).toBeNull();
    });
  });

  describe('pruneOldData', () => {
    it('should delete low-confidence and old data', async () => {
      mockDb.query.mockResolvedValueOnce({ rows: [{ count: 15 }] });

      const deleted = await service.pruneOldData(90);

      expect(deleted).toBe(15);
      expect(mockDb.query).toHaveBeenCalled();
    });
  });

  describe('getHealth', () => {
    it('should return healthy status when index exists (AC-1)', async () => {
      mockDb.query
        .mockResolvedValueOnce({ rows: [{ count: 1000, last_updated: new Date() }] })
        .mockResolvedValueOnce({ rows: [{ indexname: 'idx_template_embedding' }] });

      const health = await service.getHealth();

      expect(health.recordCount).toBe(1000);
      expect(health.indexStatus).toBe('healthy');
    });

    it('should return missing status when index does not exist', async () => {
      mockDb.query
        .mockResolvedValueOnce({ rows: [{ count: 100 }] })
        .mockResolvedValueOnce({ rows: [] });

      const health = await service.getHealth();

      expect(health.indexStatus).toBe('missing');
    });
  });
});
