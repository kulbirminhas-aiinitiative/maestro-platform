import { Router } from 'express';
import { body, param, query } from 'express-validator';
import { AuthenticatedRequest } from '@/types';
import { AIService } from '@/services/ai.service';
import { authenticateToken } from '@/middleware/auth';
import { validationMiddleware } from '@/middleware/express-validation';
import { Logger } from '@/config/logger';
import { prisma } from '@/config/database';

const router = Router();

// Apply authentication to all routes
router.use(authenticateToken);

// ============================================================================
// AI TASK SUGGESTIONS
// ============================================================================

/**
 * POST /ai/suggestions/tasks/:boardId
 * Generate smart task suggestions for a board
 */
router.post(
  '/suggestions/tasks/:boardId',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    body('context').optional().isString().trim().isLength({ max: 1000 }).withMessage('Context must be less than 1000 characters'),
    body('limit').optional().isInt({ min: 1, max: 20 }).withMessage('Limit must be between 1 and 20'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const { context, limit = 5 } = req.body;
      const userId = req.user!.id;

      const suggestions = await AIService.generateTaskSuggestions(
        boardId,
        userId,
        context,
        limit
      );

      res.json({
        data: {
          suggestions,
          generatedAt: new Date().toISOString(),
        },
      });
    } catch (error) {
      Logger.error('Generate task suggestions failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('not available')) {
        res.status(503).json({
          error: {
            type: 'service_unavailable',
            message: 'AI service is currently unavailable',
          },
        });
      } else if (errorMessage.includes('Access denied')) {
        res.status(403).json({
          error: {
            type: 'forbidden',
            message: errorMessage,
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to generate task suggestions',
          },
        });
      }
    }
  }
);

// ============================================================================
// AI AUTO-TAGGING
// ============================================================================

/**
 * POST /ai/tags/:itemId
 * Auto-tag an item using AI analysis
 */
router.post(
  '/tags/:itemId',
  [
    param('itemId').isUUID().withMessage('Valid item ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { itemId } = req.params;

      // Get item details for tagging
      const item = await prisma.item.findUnique({
        where: { id: itemId },
        select: {
          name: true,
          description: true,
        },
      });

      if (!item) {
        return res.status(404).json({
          error: {
            type: 'not_found',
            message: 'Item not found',
          },
        });
      }

      const tagResult = await AIService.autoTagItem(
        itemId,
        item.name,
        item.description
      );

      res.json({
        data: {
          ...tagResult,
          analyzedAt: new Date().toISOString(),
        },
      });
    } catch (error) {
      Logger.error('Auto-tag item failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('not available')) {
        res.status(503).json({
          error: {
            type: 'service_unavailable',
            message: 'AI service is currently unavailable',
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to auto-tag item',
          },
        });
      }
    }
  }
);

// ============================================================================
// AI WORKLOAD ANALYSIS
// ============================================================================

/**
 * GET /ai/workload/:boardId
 * Analyze workload distribution and get recommendations
 */
router.get(
  '/workload/:boardId',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    query('timeframe').optional().isInt({ min: 1, max: 365 }).withMessage('Timeframe must be between 1 and 365 days'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const { timeframe = 30 } = req.query;

      const recommendations = await AIService.analyzeWorkloadDistribution(
        boardId,
        parseInt(timeframe as string)
      );

      res.json({
        data: {
          recommendations,
          timeframeDays: timeframe,
          analyzedAt: new Date().toISOString(),
        },
      });
    } catch (error) {
      Logger.error('Workload analysis failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('not available')) {
        res.status(503).json({
          error: {
            type: 'service_unavailable',
            message: 'AI service is currently unavailable',
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to analyze workload',
          },
        });
      }
    }
  }
);

// ============================================================================
// AI TASK SCHEDULING
// ============================================================================

/**
 * POST /ai/scheduling/:boardId
 * Get AI-powered task scheduling suggestions
 */
router.post(
  '/scheduling/:boardId',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    body('tasks').isArray({ min: 1 }).withMessage('Tasks array is required'),
    body('tasks.*.itemId').isUUID().withMessage('Valid item ID required'),
    body('tasks.*.estimatedHours').isFloat({ min: 0.1, max: 1000 }).withMessage('Estimated hours must be between 0.1 and 1000'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const { tasks } = req.body;
      const userId = req.user!.id;

      const suggestions = await AIService.suggestTaskScheduling(
        boardId,
        userId,
        tasks
      );

      res.json({
        data: {
          suggestions,
          totalTasks: tasks.length,
          generatedAt: new Date().toISOString(),
        },
      });
    } catch (error) {
      Logger.error('Task scheduling suggestion failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('not available')) {
        res.status(503).json({
          error: {
            type: 'service_unavailable',
            message: 'AI service is currently unavailable',
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to generate scheduling suggestions',
          },
        });
      }
    }
  }
);

// ============================================================================
// AI RISK DETECTION
// ============================================================================

/**
 * GET /ai/risks/:boardId
 * Detect potential project risks and blockers
 */
router.get(
  '/risks/:boardId',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;

      const risks = await AIService.detectProjectRisks(boardId);

      res.json({
        data: {
          risks,
          analyzedAt: new Date().toISOString(),
          riskCount: risks.length,
          highSeverityCount: risks.filter(r => r.severity === 'high').length,
        },
      });
    } catch (error) {
      Logger.error('Risk detection failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('not available')) {
        res.status(503).json({
          error: {
            type: 'service_unavailable',
            message: 'AI service is currently unavailable',
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to detect project risks',
          },
        });
      }
    }
  }
);

export default router;