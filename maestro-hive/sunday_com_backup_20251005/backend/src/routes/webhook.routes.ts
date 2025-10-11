import { Router } from 'express';
import { body, param, query } from 'express-validator';
import { AuthenticatedRequest } from '@/types';
import { WebhookService } from '@/services/webhook.service';
import { authenticateToken } from '@/middleware/auth';
import { validationMiddleware } from '@/middleware/express-validation';
import { Logger } from '@/config/logger';

const router = Router();

// Apply authentication to all routes
router.use(authenticateToken);

// ============================================================================
// WEBHOOK ROUTES
// ============================================================================

/**
 * POST /webhooks
 * Create a new webhook
 */
router.post(
  '/',
  [
    body('url').isURL().withMessage('Valid URL is required'),
    body('events').isArray({ min: 1 }).withMessage('At least one event type is required'),
    body('events.*').isString().withMessage('Each event must be a string'),
    body('organizationId').optional().isUUID().withMessage('Valid organization ID required'),
    body('workspaceId').optional().isUUID().withMessage('Valid workspace ID required'),
    body('boardId').optional().isUUID().withMessage('Valid board ID required'),
    body('description').optional().isString().trim().isLength({ max: 500 }).withMessage('Description must be less than 500 characters'),
    body('contentType').optional().isIn(['application/json', 'application/x-www-form-urlencoded']).withMessage('Content type must be application/json or application/x-www-form-urlencoded'),
    body('headers').optional().isObject().withMessage('Headers must be an object'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const userId = req.user!.id;
      const webhookData = req.body;

      // Ensure at least one resource ID is provided
      if (!webhookData.organizationId && !webhookData.workspaceId && !webhookData.boardId) {
        return res.status(400).json({
          error: {
            type: 'validation_error',
            message: 'At least one of organizationId, workspaceId, or boardId is required',
          },
        });
      }

      const webhook = await WebhookService.create(webhookData, userId);

      res.status(201).json({
        data: webhook,
      });
    } catch (error) {
      Logger.error('Create webhook failed', error as Error);

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
            message: 'Failed to create webhook',
          },
        });
      }
    }
  }
);

/**
 * GET /webhooks/:webhookId
 * Get webhook by ID
 */
router.get(
  '/:webhookId',
  [
    param('webhookId').isUUID().withMessage('Valid webhook ID required'),
    query('includeDeliveries').optional().isBoolean().withMessage('IncludeDeliveries must be a boolean'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { webhookId } = req.params;
      const { includeDeliveries } = req.query;
      const userId = req.user!.id;

      const webhook = await WebhookService.getById(
        webhookId,
        userId,
        includeDeliveries === 'true'
      );

      if (!webhook) {
        return res.status(404).json({
          error: {
            type: 'not_found',
            message: 'Webhook not found',
          },
        });
      }

      res.json({
        data: webhook,
      });
    } catch (error) {
      Logger.error('Get webhook failed', error as Error);

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
            message: 'Failed to get webhook',
          },
        });
      }
    }
  }
);

/**
 * GET /webhooks/organizations/:organizationId
 * Get webhooks for an organization
 */
router.get(
  '/organizations/:organizationId',
  [
    param('organizationId').isUUID().withMessage('Valid organization ID required'),
    query('page').optional().isInt({ min: 1 }).withMessage('Page must be a positive integer'),
    query('limit').optional().isInt({ min: 1, max: 100 }).withMessage('Limit must be between 1 and 100'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { organizationId } = req.params;
      const { page, limit } = req.query;
      const userId = req.user!.id;

      const result = await WebhookService.getByResource(
        'organization',
        organizationId,
        userId,
        page ? parseInt(page as string) : 1,
        limit ? parseInt(limit as string) : 20
      );

      res.json({
        data: result.data,
        meta: result.meta,
      });
    } catch (error) {
      Logger.error('Get organization webhooks failed', error as Error);

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
            message: 'Failed to get organization webhooks',
          },
        });
      }
    }
  }
);

/**
 * GET /webhooks/workspaces/:workspaceId
 * Get webhooks for a workspace
 */
router.get(
  '/workspaces/:workspaceId',
  [
    param('workspaceId').isUUID().withMessage('Valid workspace ID required'),
    query('page').optional().isInt({ min: 1 }).withMessage('Page must be a positive integer'),
    query('limit').optional().isInt({ min: 1, max: 100 }).withMessage('Limit must be between 1 and 100'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { workspaceId } = req.params;
      const { page, limit } = req.query;
      const userId = req.user!.id;

      const result = await WebhookService.getByResource(
        'workspace',
        workspaceId,
        userId,
        page ? parseInt(page as string) : 1,
        limit ? parseInt(limit as string) : 20
      );

      res.json({
        data: result.data,
        meta: result.meta,
      });
    } catch (error) {
      Logger.error('Get workspace webhooks failed', error as Error);

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
            message: 'Failed to get workspace webhooks',
          },
        });
      }
    }
  }
);

/**
 * GET /webhooks/boards/:boardId
 * Get webhooks for a board
 */
router.get(
  '/boards/:boardId',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    query('page').optional().isInt({ min: 1 }).withMessage('Page must be a positive integer'),
    query('limit').optional().isInt({ min: 1, max: 100 }).withMessage('Limit must be between 1 and 100'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const { page, limit } = req.query;
      const userId = req.user!.id;

      const result = await WebhookService.getByResource(
        'board',
        boardId,
        userId,
        page ? parseInt(page as string) : 1,
        limit ? parseInt(limit as string) : 20
      );

      res.json({
        data: result.data,
        meta: result.meta,
      });
    } catch (error) {
      Logger.error('Get board webhooks failed', error as Error);

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
            message: 'Failed to get board webhooks',
          },
        });
      }
    }
  }
);

/**
 * PUT /webhooks/:webhookId
 * Update webhook
 */
router.put(
  '/:webhookId',
  [
    param('webhookId').isUUID().withMessage('Valid webhook ID required'),
    body('url').optional().isURL().withMessage('Valid URL is required'),
    body('events').optional().isArray({ min: 1 }).withMessage('At least one event type is required'),
    body('events.*').optional().isString().withMessage('Each event must be a string'),
    body('description').optional().isString().trim().isLength({ max: 500 }).withMessage('Description must be less than 500 characters'),
    body('isActive').optional().isBoolean().withMessage('IsActive must be a boolean'),
    body('contentType').optional().isIn(['application/json', 'application/x-www-form-urlencoded']).withMessage('Content type must be application/json or application/x-www-form-urlencoded'),
    body('headers').optional().isObject().withMessage('Headers must be an object'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { webhookId } = req.params;
      const userId = req.user!.id;
      const updateData = req.body;

      const webhook = await WebhookService.update(webhookId, updateData, userId);

      res.json({
        data: webhook,
      });
    } catch (error) {
      Logger.error('Update webhook failed', error as Error);

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
            message: 'Failed to update webhook',
          },
        });
      }
    }
  }
);

/**
 * DELETE /webhooks/:webhookId
 * Delete webhook
 */
router.delete(
  '/:webhookId',
  [
    param('webhookId').isUUID().withMessage('Valid webhook ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { webhookId } = req.params;
      const userId = req.user!.id;

      await WebhookService.delete(webhookId, userId);

      res.status(204).send();
    } catch (error) {
      Logger.error('Delete webhook failed', error as Error);

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
            message: 'Failed to delete webhook',
          },
        });
      }
    }
  }
);

/**
 * POST /webhooks/:webhookId/test
 * Test webhook endpoint
 */
router.post(
  '/:webhookId/test',
  [
    param('webhookId').isUUID().withMessage('Valid webhook ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { webhookId } = req.params;
      const userId = req.user!.id;

      const testResult = await WebhookService.testWebhook(webhookId, userId);

      res.json({
        data: testResult,
      });
    } catch (error) {
      Logger.error('Test webhook failed', error as Error);

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
            message: 'Failed to test webhook',
          },
        });
      }
    }
  }
);

/**
 * GET /webhooks/:webhookId/deliveries
 * Get webhook deliveries
 */
router.get(
  '/:webhookId/deliveries',
  [
    param('webhookId').isUUID().withMessage('Valid webhook ID required'),
    query('page').optional().isInt({ min: 1 }).withMessage('Page must be a positive integer'),
    query('limit').optional().isInt({ min: 1, max: 100 }).withMessage('Limit must be between 1 and 100'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { webhookId } = req.params;
      const { page, limit } = req.query;
      const userId = req.user!.id;

      const result = await WebhookService.getDeliveries(
        webhookId,
        userId,
        page ? parseInt(page as string) : 1,
        limit ? parseInt(limit as string) : 50
      );

      res.json({
        data: result.data,
        meta: result.meta,
      });
    } catch (error) {
      Logger.error('Get webhook deliveries failed', error as Error);

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
            message: 'Failed to get webhook deliveries',
          },
        });
      }
    }
  }
);

/**
 * POST /webhooks/deliveries/:deliveryId/retry
 * Retry webhook delivery
 */
router.post(
  '/deliveries/:deliveryId/retry',
  [
    param('deliveryId').isUUID().withMessage('Valid delivery ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { deliveryId } = req.params;
      const userId = req.user!.id;

      await WebhookService.retryDelivery(deliveryId, userId);

      res.json({
        message: 'Delivery retry initiated',
      });
    } catch (error) {
      Logger.error('Retry webhook delivery failed', error as Error);

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
      } else if (errorMessage.includes('already successful') || errorMessage.includes('Maximum retry')) {
        res.status(400).json({
          error: {
            type: 'bad_request',
            message: errorMessage,
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to retry webhook delivery',
          },
        });
      }
    }
  }
);

export default router;