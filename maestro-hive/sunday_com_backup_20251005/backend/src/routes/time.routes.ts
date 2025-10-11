import { Router } from 'express';
import { body, param, query } from 'express-validator';
import { AuthenticatedRequest } from '@/types';
import { TimeService } from '@/services/time.service';
import { authenticateToken } from '@/middleware/auth';
import { validationMiddleware } from '@/middleware/express-validation';
import { Logger } from '@/config/logger';

const router = Router();

// Apply authentication to all routes
router.use(authenticateToken);

// ============================================================================
// TIME TRACKING ROUTES
// ============================================================================

/**
 * POST /time/start
 * Start a new timer
 */
router.post(
  '/start',
  [
    body('itemId').optional().isUUID().withMessage('Valid item ID required'),
    body('boardId').optional().isUUID().withMessage('Valid board ID required'),
    body('description').optional().isString().trim().isLength({ max: 500 }).withMessage('Description must be less than 500 characters'),
    body('billable').optional().isBoolean().withMessage('Billable must be a boolean'),
    body('metadata').optional().isObject().withMessage('Metadata must be an object'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const userId = req.user!.id;
      const timerData = req.body;

      const timeEntry = await TimeService.startTimer(timerData, userId);

      res.status(201).json({
        data: timeEntry,
      });
    } catch (error) {
      Logger.error('Start timer failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('Access denied')) {
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
            message: 'Failed to start timer',
          },
        });
      }
    }
  }
);

/**
 * POST /time/stop
 * Stop the current running timer
 */
router.post(
  '/stop',
  async (req: AuthenticatedRequest, res) => {
    try {
      const userId = req.user!.id;

      const timeEntry = await TimeService.stopTimer(userId);

      if (!timeEntry) {
        return res.status(404).json({
          error: {
            type: 'not_found',
            message: 'No active timer found',
          },
        });
      }

      res.json({
        data: timeEntry,
      });
    } catch (error) {
      Logger.error('Stop timer failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to stop timer',
        },
      });
    }
  }
);

/**
 * GET /time/active
 * Get current active timer
 */
router.get(
  '/active',
  async (req: AuthenticatedRequest, res) => {
    try {
      const userId = req.user!.id;

      const activeTimer = await TimeService.getActiveTimer(userId);

      res.json({
        data: activeTimer,
      });
    } catch (error) {
      Logger.error('Get active timer failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get active timer',
        },
      });
    }
  }
);

/**
 * POST /time/entries
 * Create a manual time entry
 */
router.post(
  '/entries',
  [
    body('itemId').optional().isUUID().withMessage('Valid item ID required'),
    body('boardId').optional().isUUID().withMessage('Valid board ID required'),
    body('description').optional().isString().trim().isLength({ max: 500 }).withMessage('Description must be less than 500 characters'),
    body('duration').isInt({ min: 1 }).withMessage('Duration in seconds is required and must be positive'),
    body('date').isISO8601().withMessage('Valid date is required'),
    body('billable').optional().isBoolean().withMessage('Billable must be a boolean'),
    body('metadata').optional().isObject().withMessage('Metadata must be an object'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const userId = req.user!.id;
      const entryData = {
        ...req.body,
        date: new Date(req.body.date),
      };

      const timeEntry = await TimeService.create(entryData, userId);

      res.status(201).json({
        data: timeEntry,
      });
    } catch (error) {
      Logger.error('Create time entry failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('Access denied')) {
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
            message: 'Failed to create time entry',
          },
        });
      }
    }
  }
);

/**
 * GET /time/entries
 * Get time entries with filtering
 */
router.get(
  '/entries',
  [
    query('userId').optional().isUUID().withMessage('Valid user ID required'),
    query('itemId').optional().isUUID().withMessage('Valid item ID required'),
    query('boardId').optional().isUUID().withMessage('Valid board ID required'),
    query('billable').optional().isBoolean().withMessage('Billable must be a boolean'),
    query('isRunning').optional().isBoolean().withMessage('IsRunning must be a boolean'),
    query('startDate').optional().isISO8601().withMessage('Valid start date required'),
    query('endDate').optional().isISO8601().withMessage('Valid end date required'),
    query('page').optional().isInt({ min: 1 }).withMessage('Page must be a positive integer'),
    query('limit').optional().isInt({ min: 1, max: 100 }).withMessage('Limit must be between 1 and 100'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const userId = req.user!.id;
      const {
        userId: filterUserId,
        itemId,
        boardId,
        billable,
        isRunning,
        startDate,
        endDate,
        page,
        limit,
      } = req.query;

      const filter = {
        ...(filterUserId && { userId: filterUserId as string }),
        ...(itemId && { itemId: itemId as string }),
        ...(boardId && { boardId: boardId as string }),
        ...(billable !== undefined && { billable: billable === 'true' }),
        ...(isRunning !== undefined && { isRunning: isRunning === 'true' }),
        ...(startDate && { startDate: startDate as string }),
        ...(endDate && { endDate: endDate as string }),
      };

      const result = await TimeService.getTimeEntries(
        filter,
        userId,
        page ? parseInt(page as string) : 1,
        limit ? parseInt(limit as string) : 50
      );

      res.json({
        data: result.data,
        meta: result.meta,
      });
    } catch (error) {
      Logger.error('Get time entries failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get time entries',
        },
      });
    }
  }
);

/**
 * PUT /time/entries/:entryId
 * Update time entry
 */
router.put(
  '/entries/:entryId',
  [
    param('entryId').isUUID().withMessage('Valid time entry ID required'),
    body('description').optional().isString().trim().isLength({ max: 500 }).withMessage('Description must be less than 500 characters'),
    body('duration').optional().isInt({ min: 1 }).withMessage('Duration must be a positive integer'),
    body('billable').optional().isBoolean().withMessage('Billable must be a boolean'),
    body('metadata').optional().isObject().withMessage('Metadata must be an object'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { entryId } = req.params;
      const userId = req.user!.id;
      const updateData = req.body;

      const timeEntry = await TimeService.update(entryId, updateData, userId);

      res.json({
        data: timeEntry,
      });
    } catch (error) {
      Logger.error('Update time entry failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('not found')) {
        res.status(404).json({
          error: {
            type: 'not_found',
            message: errorMessage,
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
            message: 'Failed to update time entry',
          },
        });
      }
    }
  }
);

/**
 * DELETE /time/entries/:entryId
 * Delete time entry
 */
router.delete(
  '/entries/:entryId',
  [
    param('entryId').isUUID().withMessage('Valid time entry ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { entryId } = req.params;
      const userId = req.user!.id;

      await TimeService.delete(entryId, userId);

      res.status(204).send();
    } catch (error) {
      Logger.error('Delete time entry failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('not found')) {
        res.status(404).json({
          error: {
            type: 'not_found',
            message: errorMessage,
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
            message: 'Failed to delete time entry',
          },
        });
      }
    }
  }
);

/**
 * GET /time/statistics
 * Get time tracking statistics
 */
router.get(
  '/statistics',
  [
    query('startDate').optional().isISO8601().withMessage('Valid start date required'),
    query('endDate').optional().isISO8601().withMessage('Valid end date required'),
    query('boardId').optional().isUUID().withMessage('Valid board ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const userId = req.user!.id;
      const { startDate, endDate, boardId } = req.query;

      const statistics = await TimeService.getStatistics(
        userId,
        startDate ? new Date(startDate as string) : undefined,
        endDate ? new Date(endDate as string) : undefined,
        boardId as string
      );

      res.json({
        data: statistics,
      });
    } catch (error) {
      Logger.error('Get time statistics failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get time statistics',
        },
      });
    }
  }
);

export default router;