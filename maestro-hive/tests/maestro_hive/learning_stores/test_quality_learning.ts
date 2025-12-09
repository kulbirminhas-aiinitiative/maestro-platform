/**
 * Quality Learning Service Tests
 * AC-3: RAG retrieval queries return relevant results
 * AC-4: Quality threshold filters low-confidence data
 * AC-5: Learning stores populated during LEARNING mode
 * EPIC: MD-2490
 */

import { describe, it, expect, beforeEach, jest } from '@jest/globals';
import { QualityLearningService } from '../src/learning/qualityLearning.service';
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

describe('QualityLearningService', () => {
  let service: QualityLearningService;
  let mockDb: ReturnType<typeof createMockDb>;
  let embeddings: EmbeddingPipelineService;

  beforeEach(() => {
    mockDb = createMockDb();
    embeddings = new EmbeddingPipelineService(new LocalEmbeddingProvider(1536));
    service = new QualityLearningService(mockDb, embeddings, defaultConfig);
  });

  describe('recordOutcome', () => {
    const outcome = {
      decisionId: 'decision-1',
      decisionType: 'architecture',
      decisionContext: 'Choosing between microservices and monolith',
      outcome: 'success' as const,
      qualityDelta: 5.5,
      confidence: 0.9,
    };

    it('should record outcome in learning mode (AC-5)', async () => {
      mockDb.query.mockResolvedValueOnce({ rows: [{ ...outcome, id: 'uuid-1' }] });

      const result = await service.recordOutcome(outcome, learningContext);

      expect(mockDb.query).toHaveBeenCalled();
      expect(result).toBeDefined();
    });

    it('should not record in inference mode (AC-5)', async () => {
      const inferenceContext = { ...learningContext, mode: 'inference' as const };
      const result = await service.recordOutcome(outcome, inferenceContext);

      expect(mockDb.query).not.toHaveBeenCalled();
      expect(result).toBeNull();
    });

    it('should filter low-confidence data (AC-4)', async () => {
      const lowConfidenceOutcome = { ...outcome, confidence: 0.5 };
      const result = await service.recordOutcome(lowConfidenceOutcome, learningContext);

      expect(mockDb.query).not.toHaveBeenCalled();
      expect(result).toBeNull();
    });
  });

  describe('checkForWarnings', () => {
    it('should return warnings for similar failed decisions (AC-3)', async () => {
      mockDb.query.mockResolvedValueOnce({
        rows: [
          {
            decision_type: 'architecture',
            similar_context: 'Previous microservices decision',
            previous_outcome: 'failure',
            quality_impact: -10.5,
            similarity: 0.92,
            occurrences: 3,
          },
        ],
      });

      const warnings = await service.checkForWarnings({
        contextText: 'Considering microservices architecture',
      });

      expect(warnings).toHaveLength(1);
      expect(warnings[0].decisionType).toBe('architecture');
      expect(warnings[0].qualityImpact).toBe(-10.5);
      expect(warnings[0].occurrences).toBe(3);
    });

    it('should filter by decision type when provided', async () => {
      await service.checkForWarnings({
        contextText: 'test',
        decisionType: 'architecture',
      });

      const queryCall = mockDb.query.mock.calls[0];
      expect(queryCall[1]).toContain('architecture');
    });

    it('should apply similarity threshold (AC-3)', async () => {
      await service.checkForWarnings({ contextText: 'test', threshold: 0.9 });

      const queryCall = mockDb.query.mock.calls[0];
      expect(queryCall[1]).toContain(0.9);
    });
  });

  describe('findSuccessfulDecisions', () => {
    it('should return successful decisions in similar contexts', async () => {
      mockDb.query.mockResolvedValueOnce({
        rows: [
          {
            id: 'uuid-1',
            decisionId: 'decision-1',
            decisionType: 'architecture',
            decisionContext: 'Successful microservices implementation',
            outcome: 'success',
            qualityDelta: 8.0,
            confidence: 0.95,
            similarity: 0.88,
            distance: 0.12,
          },
        ],
      });

      const results = await service.findSuccessfulDecisions('microservices decision');

      expect(results).toHaveLength(1);
      expect(results[0].item.outcome).toBe('success');
      expect(results[0].similarity).toBe(0.88);
    });
  });

  describe('getDecisionTypeStats', () => {
    it('should return statistics for a decision type', async () => {
      mockDb.query.mockResolvedValueOnce({
        rows: [{ total: 50, success_count: 40, avg_delta: 3.5, avg_confidence: 0.88 }],
      });

      const stats = await service.getDecisionTypeStats('architecture');

      expect(stats).toBeDefined();
      expect(stats!.totalDecisions).toBe(50);
      expect(stats!.successRate).toBe(0.8);
      expect(stats!.avgQualityDelta).toBe(3.5);
    });

    it('should return null for unknown decision type', async () => {
      mockDb.query.mockResolvedValueOnce({ rows: [{ total: 0 }] });

      const stats = await service.getDecisionTypeStats('unknown');

      expect(stats).toBeNull();
    });
  });

  describe('getQualityTrends', () => {
    it('should return daily quality trends', async () => {
      mockDb.query.mockResolvedValueOnce({
        rows: [
          { date: '2025-12-06', avg_delta: 4.5, success_rate: 0.85, count: 20 },
          { date: '2025-12-05', avg_delta: 3.2, success_rate: 0.78, count: 15 },
        ],
      });

      const trends = await service.getQualityTrends(30);

      expect(trends).toHaveLength(2);
      expect(trends[0].date).toBe('2025-12-06');
      expect(trends[0].avgQualityDelta).toBe(4.5);
    });
  });

  describe('getHealth', () => {
    it('should return healthy status when index exists', async () => {
      mockDb.query
        .mockResolvedValueOnce({ rows: [{ count: 500, last_updated: new Date() }] })
        .mockResolvedValueOnce({ rows: [{ indexname: 'idx_quality_embedding' }] });

      const health = await service.getHealth();

      expect(health.recordCount).toBe(500);
      expect(health.indexStatus).toBe('healthy');
    });
  });
});
