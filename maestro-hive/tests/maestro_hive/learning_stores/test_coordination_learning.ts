/**
 * Coordination Learning Service Tests
 * AC-3: RAG retrieval queries return relevant results
 * AC-4: Quality threshold filters low-confidence data
 * AC-5: Learning stores populated during LEARNING mode
 * EPIC: MD-2490
 */

import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { CoordinationLearningService } from '../src/learning/coordinationLearning.service';
import { EmbeddingPipelineService, LocalEmbeddingProvider } from '../src/learning/embeddingPipeline.service';
import { LearningStoreConfig, LearningModeContext } from '../src/learning/types';

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

describe('CoordinationLearningService', () => {
  let service: CoordinationLearningService;
  let mockDb: ReturnType<typeof createMockDb>;
  let embeddings: EmbeddingPipelineService;

  beforeEach(() => {
    mockDb = createMockDb();
    embeddings = new EmbeddingPipelineService(new LocalEmbeddingProvider(1536));
    service = new CoordinationLearningService(mockDb, embeddings, defaultConfig);
  });

  describe('recordPattern', () => {
    const pattern = {
      complexityText: 'Multi-service API integration with authentication',
      teamComposition: ['architect', 'backend-dev', 'security-specialist'],
      executionMode: 'parallel' as const,
      successRate: 0.92,
      avgTimeMs: 45000,
      confidence: 0.95,
    };

    it('should record pattern in learning mode (AC-5)', async () => {
      mockDb.query.mockResolvedValueOnce({ rows: [{ ...pattern, id: 'uuid-1' }] });

      const result = await service.recordPattern(pattern, learningContext);

      expect(mockDb.query).toHaveBeenCalled();
      expect(result).toBeDefined();
    });

    it('should not record in inference mode (AC-5)', async () => {
      const inferenceContext = { ...learningContext, mode: 'inference' as const };
      const result = await service.recordPattern(pattern, inferenceContext);

      expect(mockDb.query).not.toHaveBeenCalled();
      expect(result).toBeNull();
    });

    it('should filter low-confidence data (AC-4)', async () => {
      const lowConfidencePattern = { ...pattern, confidence: 0.5 };
      const result = await service.recordPattern(lowConfidencePattern, learningContext);

      expect(mockDb.query).not.toHaveBeenCalled();
      expect(result).toBeNull();
    });

    it('should store team composition as JSON', async () => {
      mockDb.query.mockResolvedValueOnce({ rows: [{ ...pattern, id: 'uuid-1' }] });

      await service.recordPattern(pattern, learningContext);

      const queryCall = mockDb.query.mock.calls[0];
      expect(queryCall[1]).toContain(JSON.stringify(pattern.teamComposition));
    });
  });

  describe('getRecommendations', () => {
    it('should return coordination recommendations (AC-3)', async () => {
      mockDb.query.mockResolvedValueOnce({
        rows: [
          {
            team_composition: '["architect", "backend-dev"]',
            execution_mode: 'parallel',
            expected_success_rate: 0.88,
            expected_time_ms: 50000,
            similarity: 0.91,
            confidence: 0.9,
          },
        ],
      });

      const recommendations = await service.getRecommendations({
        complexityText: 'API integration task',
      });

      expect(recommendations).toHaveLength(1);
      expect(recommendations[0].executionMode).toBe('parallel');
      expect(recommendations[0].teamComposition).toEqual(['architect', 'backend-dev']);
      expect(recommendations[0].expectedSuccessRate).toBe(0.88);
    });

    it('should apply similarity threshold (AC-3)', async () => {
      await service.getRecommendations({ complexityText: 'test' });

      const queryCall = mockDb.query.mock.calls[0];
      expect(queryCall[1]).toContain(defaultConfig.similarityThreshold);
    });
  });

  describe('recommendExecutionMode', () => {
    it('should recommend execution mode based on similar patterns', async () => {
      mockDb.query.mockResolvedValueOnce({
        rows: [
          {
            execution_mode: 'parallel',
            avg_success_rate: 0.9,
            avg_time_ms: 40000,
            count: 15,
            avg_similarity: 0.88,
          },
        ],
      });

      const recommendation = await service.recommendExecutionMode('Complex multi-step task');

      expect(recommendation).toBeDefined();
      expect(recommendation!.mode).toBe('parallel');
      expect(recommendation!.confidence).toBe(0.88);
      expect(recommendation!.reason).toContain('15 similar patterns');
    });

    it('should return null when no similar patterns found', async () => {
      mockDb.query.mockResolvedValueOnce({ rows: [] });

      const recommendation = await service.recommendExecutionMode('Unknown task type');

      expect(recommendation).toBeNull();
    });
  });

  describe('findSimilarPatterns', () => {
    it('should return similar coordination patterns', async () => {
      mockDb.query.mockResolvedValueOnce({
        rows: [
          {
            id: 'uuid-1',
            complexityText: 'Similar API task',
            teamComposition: '["architect", "dev"]',
            executionMode: 'sequential',
            successRate: 0.85,
            avgTimeMs: 60000,
            confidence: 0.9,
            similarity: 0.87,
            distance: 0.13,
          },
        ],
      });

      const results = await service.findSimilarPatterns('API integration');

      expect(results).toHaveLength(1);
      expect(results[0].similarity).toBe(0.87);
      expect(results[0].item.executionMode).toBe('sequential');
    });
  });

  describe('getExecutionModeStats', () => {
    it('should return statistics for all execution modes', async () => {
      mockDb.query.mockResolvedValueOnce({
        rows: [
          { execution_mode: 'parallel', total: 50, avg_success_rate: 0.88, avg_time_ms: 45000 },
          { execution_mode: 'sequential', total: 30, avg_success_rate: 0.82, avg_time_ms: 75000 },
          { execution_mode: 'hybrid', total: 20, avg_success_rate: 0.85, avg_time_ms: 55000 },
        ],
      });

      const stats = await service.getExecutionModeStats();

      expect(stats).toHaveLength(3);
      expect(stats[0].mode).toBe('parallel');
      expect(stats[0].avgSuccessRate).toBe(0.88);
    });
  });

  describe('getTeamEffectiveness', () => {
    it('should return effectiveness for a team composition', async () => {
      mockDb.query.mockResolvedValueOnce({
        rows: [{ success_rate: 0.9, avg_time_ms: 50000, count: 25 }],
      });

      const effectiveness = await service.getTeamEffectiveness(['architect', 'dev']);

      expect(effectiveness).toBeDefined();
      expect(effectiveness!.successRate).toBe(0.9);
      expect(effectiveness!.patternCount).toBe(25);
    });

    it('should return null for unknown team', async () => {
      mockDb.query.mockResolvedValueOnce({ rows: [{ count: 0 }] });

      const effectiveness = await service.getTeamEffectiveness(['unknown-agent']);

      expect(effectiveness).toBeNull();
    });
  });

  describe('getHealth', () => {
    it('should return healthy status when index exists', async () => {
      mockDb.query
        .mockResolvedValueOnce({ rows: [{ count: 300, last_updated: new Date() }] })
        .mockResolvedValueOnce({ rows: [{ indexname: 'idx_coordination_embedding' }] });

      const health = await service.getHealth();

      expect(health.recordCount).toBe(300);
      expect(health.indexStatus).toBe('healthy');
    });

    it('should return missing status when no index', async () => {
      mockDb.query
        .mockResolvedValueOnce({ rows: [{ count: 100 }] })
        .mockResolvedValueOnce({ rows: [] });

      const health = await service.getHealth();

      expect(health.indexStatus).toBe('missing');
    });
  });
});
