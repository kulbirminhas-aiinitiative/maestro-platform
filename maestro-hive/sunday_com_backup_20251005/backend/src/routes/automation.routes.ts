import { Router } from 'express';
import { body, param, query } from 'express-validator';
import { AuthenticatedRequest } from '@/types';
import { AutomationService } from '@/services/automation.service';
import { authenticateToken } from '@/middleware/auth';
import { validationMiddleware } from '@/middleware/express-validation';
import { Logger } from '@/config/logger';

const router = Router();

// Apply authentication to all routes
router.use(authenticateToken);

// ============================================================================
// AUTOMATION RULE MANAGEMENT
// ============================================================================

/**
 * POST /automation/rules
 * Create a new automation rule
 */
router.post(
  '/rules',
  [
    body('name').isString().trim().isLength({ min: 1, max: 100 }).withMessage('Name is required and must be between 1-100 characters'),
    body('description').optional().isString().trim().isLength({ max: 500 }).withMessage('Description must be less than 500 characters'),
    body('trigger').isObject().withMessage('Trigger configuration is required'),
    body('trigger.type').isString().trim().withMessage('Trigger type is required'),
    body('trigger.conditions').isObject().withMessage('Trigger conditions are required'),
    body('conditions').optional().isObject().withMessage('Conditions must be an object'),
    body('actions').isArray({ min: 1 }).withMessage('At least one action is required'),
    body('actions.*.type').isString().trim().withMessage('Action type is required'),
    body('actions.*.parameters').isObject().withMessage('Action parameters are required'),
    body('isEnabled').optional().isBoolean().withMessage('isEnabled must be a boolean'),
    body('organizationId').isUUID().withMessage('Valid organization ID required'),
    body('boardId').optional().isUUID().withMessage('Valid board ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const userId = req.user!.id;
      const ruleData = req.body;

      const rule = await AutomationService.createRule(
        ruleData,
        userId,
        ruleData.organizationId,
        ruleData.boardId
      );

      res.status(201).json({
        data: rule,
      });
    } catch (error) {
      Logger.error('Create automation rule failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('Invalid')) {
        res.status(400).json({
          error: {
            type: 'validation_error',
            message: errorMessage,
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to create automation rule',
          },
        });
      }
    }
  }
);

/**
 * GET /automation/rules
 * Get automation rules for an organization or board
 */
router.get(
  '/rules',
  [
    query('organizationId').isUUID().withMessage('Valid organization ID required'),
    query('boardId').optional().isUUID().withMessage('Valid board ID required'),
    query('includeDisabled').optional().isBoolean().withMessage('includeDisabled must be a boolean'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { organizationId, boardId, includeDisabled = false } = req.query;

      const rules = await AutomationService.getRules(
        organizationId as string,
        boardId as string,
        includeDisabled === 'true'
      );

      res.json({
        data: rules,
        meta: {
          total: rules.length,
          enabled: rules.filter(r => r.isEnabled).length,
          disabled: rules.filter(r => !r.isEnabled).length,
        },
      });
    } catch (error) {
      Logger.error('Get automation rules failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get automation rules',
        },
      });
    }
  }
);

/**
 * PUT /automation/rules/:ruleId
 * Update an automation rule
 */
router.put(
  '/rules/:ruleId',
  [
    param('ruleId').isUUID().withMessage('Valid rule ID required'),
    body('name').optional().isString().trim().isLength({ min: 1, max: 100 }).withMessage('Name must be between 1-100 characters'),
    body('description').optional().isString().trim().isLength({ max: 500 }).withMessage('Description must be less than 500 characters'),
    body('trigger').optional().isObject().withMessage('Trigger configuration must be an object'),
    body('trigger.type').optional().isString().trim().withMessage('Trigger type must be a string'),
    body('trigger.conditions').optional().isObject().withMessage('Trigger conditions must be an object'),
    body('conditions').optional().isObject().withMessage('Conditions must be an object'),
    body('actions').optional().isArray({ min: 1 }).withMessage('Actions must be an array with at least one action'),
    body('actions.*.type').optional().isString().trim().withMessage('Action type must be a string'),
    body('actions.*.parameters').optional().isObject().withMessage('Action parameters must be an object'),
    body('isEnabled').optional().isBoolean().withMessage('isEnabled must be a boolean'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { ruleId } = req.params;
      const userId = req.user!.id;
      const updates = req.body;

      const rule = await AutomationService.updateRule(ruleId, updates, userId);

      res.json({
        data: rule,
      });
    } catch (error) {
      Logger.error('Update automation rule failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('not found')) {
        res.status(404).json({
          error: {
            type: 'not_found',
            message: errorMessage,
          },
        });
      } else if (errorMessage.includes('Invalid')) {
        res.status(400).json({
          error: {
            type: 'validation_error',
            message: errorMessage,
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to update automation rule',
          },
        });
      }
    }
  }
);

/**
 * DELETE /automation/rules/:ruleId
 * Delete an automation rule
 */
router.delete(
  '/rules/:ruleId',
  [
    param('ruleId').isUUID().withMessage('Valid rule ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { ruleId } = req.params;
      const userId = req.user!.id;

      await AutomationService.deleteRule(ruleId, userId);

      res.status(204).send();
    } catch (error) {
      Logger.error('Delete automation rule failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('not found')) {
        res.status(404).json({
          error: {
            type: 'not_found',
            message: errorMessage,
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to delete automation rule',
          },
        });
      }
    }
  }
);

// ============================================================================
// AUTOMATION TESTING
// ============================================================================

/**
 * POST /automation/rules/:ruleId/test
 * Test an automation rule without executing actions
 */
router.post(
  '/rules/:ruleId/test',
  [
    param('ruleId').isUUID().withMessage('Valid rule ID required'),
    body('testContext').isObject().withMessage('Test context is required'),
    body('testContext.entityType').isIn(['item', 'board', 'user']).withMessage('Valid entity type required'),
    body('testContext.entityId').isUUID().withMessage('Valid entity ID required'),
    body('testContext.action').isString().trim().withMessage('Action is required'),
    body('testContext.userId').isUUID().withMessage('Valid user ID required'),
    body('testContext.organizationId').isUUID().withMessage('Valid organization ID required'),
    body('testContext.oldValues').optional().isObject().withMessage('Old values must be an object'),
    body('testContext.newValues').optional().isObject().withMessage('New values must be an object'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { ruleId } = req.params;
      const { testContext } = req.body;

      const testResult = await AutomationService.testRule(ruleId, testContext);

      res.json({
        data: {
          ...testResult,
          testedAt: new Date().toISOString(),
        },
      });
    } catch (error) {
      Logger.error('Test automation rule failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('not found')) {
        res.status(404).json({
          error: {
            type: 'not_found',
            message: errorMessage,
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to test automation rule',
          },
        });
      }
    }
  }
);

// ============================================================================
// AUTOMATION EXECUTION HISTORY
// ============================================================================

/**
 * GET /automation/executions
 * Get automation execution history
 */
router.get(
  '/executions',
  [
    query('organizationId').isUUID().withMessage('Valid organization ID required'),
    query('ruleId').optional().isUUID().withMessage('Valid rule ID required'),
    query('limit').optional().isInt({ min: 1, max: 100 }).withMessage('Limit must be between 1 and 100'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { organizationId, ruleId, limit = 50 } = req.query;

      const executions = await AutomationService.getExecutionHistory(
        organizationId as string,
        ruleId as string,
        parseInt(limit as string)
      );

      const successfulExecutions = executions.filter(e =>
        e.executedActions.every(a => a.success)
      );

      res.json({
        data: executions,
        meta: {
          total: executions.length,
          successful: successfulExecutions.length,
          failed: executions.length - successfulExecutions.length,
        },
      });
    } catch (error) {
      Logger.error('Get execution history failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get execution history',
        },
      });
    }
  }
);

// ============================================================================
// AUTOMATION TRIGGERS (Internal API)
// ============================================================================

/**
 * POST /automation/trigger
 * Trigger automation rules (internal use)
 * This endpoint is called by other services when events occur
 */
router.post(
  '/trigger',
  [
    body('entityType').isIn(['item', 'board', 'user']).withMessage('Valid entity type required'),
    body('entityId').isUUID().withMessage('Valid entity ID required'),
    body('action').isString().trim().withMessage('Action is required'),
    body('userId').isUUID().withMessage('Valid user ID required'),
    body('organizationId').isUUID().withMessage('Valid organization ID required'),
    body('workspaceId').optional().isUUID().withMessage('Valid workspace ID required'),
    body('boardId').optional().isUUID().withMessage('Valid board ID required'),
    body('oldValues').optional().isObject().withMessage('Old values must be an object'),
    body('newValues').optional().isObject().withMessage('New values must be an object'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const triggerContext = req.body;

      // Execute automation triggers asynchronously
      AutomationService.executeTrigger(triggerContext).catch(error => {
        Logger.error('Automation trigger execution failed', error);
      });

      res.json({
        data: {
          message: 'Automation trigger queued for execution',
          triggeredAt: new Date().toISOString(),
        },
      });
    } catch (error) {
      Logger.error('Automation trigger failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to trigger automation',
        },
      });
    }
  }
);

// ============================================================================
// AUTOMATION STATISTICS
// ============================================================================

/**
 * GET /automation/stats
 * Get automation usage statistics
 */
router.get(
  '/stats',
  [
    query('organizationId').isUUID().withMessage('Valid organization ID required'),
    query('boardId').optional().isUUID().withMessage('Valid board ID required'),
    query('timeframe').optional().isInt({ min: 1, max: 365 }).withMessage('Timeframe must be between 1 and 365 days'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { organizationId, boardId, timeframe = 30 } = req.query;

      // Get automation statistics
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - parseInt(timeframe as string));

      const [rules, executions] = await Promise.all([
        AutomationService.getRules(organizationId as string, boardId as string, true),
        AutomationService.getExecutionHistory(organizationId as string, undefined, 1000),
      ]);

      const recentExecutions = executions.filter(e =>
        new Date(e.executedAt) >= startDate
      );

      const successfulExecutions = recentExecutions.filter(e =>
        e.executedActions.every(a => a.success)
      );

      const stats = {
        totalRules: rules.length,
        enabledRules: rules.filter(r => r.isEnabled).length,
        disabledRules: rules.filter(r => !r.isEnabled).length,
        executionsInPeriod: recentExecutions.length,
        successfulExecutions: successfulExecutions.length,
        failedExecutions: recentExecutions.length - successfulExecutions.length,
        successRate: recentExecutions.length > 0
          ? (successfulExecutions.length / recentExecutions.length) * 100
          : 0,
        mostTriggeredActions: this.getMostTriggeredActions(recentExecutions),
        timeframeDays: timeframe,
      };

      res.json({
        data: stats,
      });
    } catch (error) {
      Logger.error('Get automation stats failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get automation statistics',
        },
      });
    }
  }
);

// ============================================================================
// HELPER METHODS
// ============================================================================

/**
 * Get most triggered action types from executions
 */
function getMostTriggeredActions(executions: any[]): Array<{ type: string; count: number }> {
  const actionCounts = new Map<string, number>();

  executions.forEach(execution => {
    execution.executedActions.forEach((action: any) => {
      const count = actionCounts.get(action.type) || 0;
      actionCounts.set(action.type, count + 1);
    });
  });

  return Array.from(actionCounts.entries())
    .map(([type, count]) => ({ type, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, 10);
}

export default router;