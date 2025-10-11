import { Router } from 'express';
import { body, param, query } from 'express-validator';
import { AuthenticatedRequest } from '@/types';
import { EnhancedCollaborationService } from '@/services/collaboration-enhanced.service';
import { authenticateToken } from '@/middleware/auth';
import { validationMiddleware } from '@/middleware/express-validation';
import { Logger } from '@/config/logger';

const router = Router();

// Apply authentication to all routes
router.use(authenticateToken);

// ============================================================================
// PRESENCE ROUTES
// ============================================================================

/**
 * GET /collaboration/presence/board/:boardId
 * Get active users on a board
 */
router.get(
  '/presence/board/:boardId',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const activeUsers = await EnhancedCollaborationService.getActiveUsers(boardId);

      res.json({
        data: {
          boardId,
          activeUsers,
          count: activeUsers.length,
        },
      });
    } catch (error) {
      Logger.error('Get board presence failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get board presence',
        },
      });
    }
  }
);

/**
 * POST /collaboration/presence/board/:boardId
 * Join board presence
 */
router.post(
  '/presence/board/:boardId',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    body('socketId').isString().withMessage('Socket ID required'),
    body('userState').optional().isObject().withMessage('User state must be an object'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const { socketId, userState } = req.body;
      const user = req.user!;

      await EnhancedCollaborationService.trackPresence(
        user.id,
        `${user.firstName || ''} ${user.lastName || ''}`.trim() || user.email,
        boardId,
        socketId,
        user.avatarUrl,
        userState
      );

      res.status(201).json({
        data: {
          message: 'Presence tracked successfully',
          boardId,
          userId: user.id,
        },
      });
    } catch (error) {
      Logger.error('Track presence failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to track presence',
        },
      });
    }
  }
);

// ============================================================================
// CURSOR ROUTES
// ============================================================================

/**
 * PUT /collaboration/cursor/board/:boardId
 * Update cursor position
 */
router.put(
  '/cursor/board/:boardId',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    body('x').isNumeric().withMessage('X coordinate required'),
    body('y').isNumeric().withMessage('Y coordinate required'),
    body('itemId').optional().isUUID().withMessage('Valid item ID required'),
    body('field').optional().isString().withMessage('Field must be a string'),
    body('selection').optional().isObject().withMessage('Selection must be an object'),
    body('selection.start').optional().isInt({ min: 0 }).withMessage('Selection start must be non-negative'),
    body('selection.end').optional().isInt({ min: 0 }).withMessage('Selection end must be non-negative'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const { x, y, itemId, field, selection } = req.body;
      const userId = req.user!.id;

      await EnhancedCollaborationService.updateCursorAdvanced(userId, boardId, {
        x: parseFloat(x),
        y: parseFloat(y),
        itemId,
        field,
        selection,
      });

      res.json({
        data: {
          message: 'Cursor updated successfully',
          boardId,
          userId,
        },
      });
    } catch (error) {
      Logger.error('Update cursor failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to update cursor',
        },
      });
    }
  }
);

// ============================================================================
// LOCKING ROUTES
// ============================================================================

/**
 * POST /collaboration/lock/item/:itemId/field/:field
 * Lock item field for editing
 */
router.post(
  '/lock/item/:itemId/field/:field',
  [
    param('itemId').isUUID().withMessage('Valid item ID required'),
    param('field').isString().withMessage('Field name required'),
    body('duration').optional().isInt({ min: 1000, max: 600000 }).withMessage('Duration must be between 1s and 10min'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { itemId, field } = req.params;
      const { duration = 300000 } = req.body; // 5 minutes default
      const user = req.user!;

      const result = await EnhancedCollaborationService.lockItemField(
        itemId,
        field,
        user.id,
        `${user.firstName || ''} ${user.lastName || ''}`.trim() || user.email,
        duration
      );

      if (result.success) {
        res.status(201).json({
          data: {
            message: 'Field locked successfully',
            itemId,
            field,
            lockType: result.lockType,
          },
        });
      } else {
        res.status(409).json({
          error: {
            type: 'conflict',
            message: `Field is already locked by ${result.lockedBy}`,
            details: {
              lockedBy: result.lockedBy,
              lockType: result.lockType,
            },
          },
        });
      }
    } catch (error) {
      Logger.error('Lock item field failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to lock field',
        },
      });
    }
  }
);

/**
 * DELETE /collaboration/lock/item/:itemId/field/:field
 * Release item field lock
 */
router.delete(
  '/lock/item/:itemId/field/:field',
  [
    param('itemId').isUUID().withMessage('Valid item ID required'),
    param('field').isString().withMessage('Field name required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { itemId, field } = req.params;
      const userId = req.user!.id;

      const released = await EnhancedCollaborationService.unlockItemField(itemId, field, userId);

      if (released) {
        res.status(204).send();
      } else {
        res.status(404).json({
          error: {
            type: 'not_found',
            message: 'Lock not found or not owned by user',
          },
        });
      }
    } catch (error) {
      Logger.error('Unlock item field failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to unlock field',
        },
      });
    }
  }
);

// ============================================================================
// OPERATION ROUTES
// ============================================================================

/**
 * POST /collaboration/operation
 * Process collaborative operation
 */
router.post(
  '/operation',
  [
    body('id').isString().withMessage('Operation ID required'),
    body('type').isIn(['insert', 'delete', 'retain', 'update']).withMessage('Valid operation type required'),
    body('itemId').isUUID().withMessage('Valid item ID required'),
    body('field').isString().withMessage('Field name required'),
    body('position').optional().isInt({ min: 0 }).withMessage('Position must be non-negative'),
    body('content').optional().isString().withMessage('Content must be a string'),
    body('length').optional().isInt({ min: 1 }).withMessage('Length must be positive'),
    body('clientId').isString().withMessage('Client ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const operationData = req.body;
      const userId = req.user!.id;

      const operation = {
        ...operationData,
        userId,
        timestamp: new Date(),
      };

      const result = await EnhancedCollaborationService.processOperation(operation);

      if (result.success) {
        res.status(201).json({
          data: {
            transformedOperation: result.transformedOperation,
            conflicts: result.conflicts,
            hasConflicts: result.conflicts.length > 0,
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'operation_failed',
            message: 'Failed to process operation',
          },
        });
      }
    } catch (error) {
      Logger.error('Process operation failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to process operation',
        },
      });
    }
  }
);

// ============================================================================
// ACTIVITY ROUTES
// ============================================================================

/**
 * GET /collaboration/activity/board/:boardId
 * Get board activity feed
 */
router.get(
  '/activity/board/:boardId',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    query('limit').optional().isInt({ min: 1, max: 100 }).withMessage('Limit must be between 1 and 100'),
    query('offset').optional().isInt({ min: 0 }).withMessage('Offset must be non-negative'),
    query('includeOperations').optional().isBoolean().withMessage('Include operations must be boolean'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const { limit = 50, offset = 0, includeOperations = false } = req.query;

      const activity = await EnhancedCollaborationService.getBoardActivityAdvanced(
        boardId,
        parseInt(limit as string),
        parseInt(offset as string),
        includeOperations === 'true'
      );

      res.json({
        data: {
          boardId,
          ...activity,
          meta: {
            limit: parseInt(limit as string),
            offset: parseInt(offset as string),
            includeOperations: includeOperations === 'true',
          },
        },
      });
    } catch (error) {
      Logger.error('Get board activity failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get board activity',
        },
      });
    }
  }
);

// ============================================================================
// TYPING ROUTES
// ============================================================================

/**
 * PUT /collaboration/typing/item/:itemId
 * Update typing status
 */
router.put(
  '/typing/item/:itemId',
  [
    param('itemId').isUUID().withMessage('Valid item ID required'),
    body('isTyping').isBoolean().withMessage('Typing status required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { itemId } = req.params;
      const { isTyping } = req.body;
      const user = req.user!;

      // Use the original collaboration service for typing
      const { CollaborationService } = await import('@/services/collaboration.service');
      await CollaborationService.handleTyping(
        user.id,
        `${user.firstName || ''} ${user.lastName || ''}`.trim() || user.email,
        itemId,
        isTyping
      );

      res.json({
        data: {
          message: 'Typing status updated',
          itemId,
          userId: user.id,
          isTyping,
        },
      });
    } catch (error) {
      Logger.error('Update typing status failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to update typing status',
        },
      });
    }
  }
);

/**
 * GET /collaboration/typing/item/:itemId
 * Get typing users for item
 */
router.get(
  '/typing/item/:itemId',
  [
    param('itemId').isUUID().withMessage('Valid item ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { itemId } = req.params;

      // Use the original collaboration service for typing
      const { CollaborationService } = await import('@/services/collaboration.service');
      const typingUsers = await CollaborationService.getTypingUsers(itemId);

      res.json({
        data: {
          itemId,
          typingUsers,
          count: typingUsers.length,
        },
      });
    } catch (error) {
      Logger.error('Get typing users failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get typing users',
        },
      });
    }
  }
);

// ============================================================================
// CLEANUP ROUTES (ADMIN ONLY)
// ============================================================================

/**
 * POST /collaboration/cleanup
 * Trigger cleanup of expired collaboration data
 */
router.post(
  '/cleanup',
  // Note: In a real implementation, you'd add admin middleware here
  async (req: AuthenticatedRequest, res) => {
    try {
      await EnhancedCollaborationService.cleanupExpiredDataAdvanced();

      res.json({
        data: {
          message: 'Collaboration data cleanup completed',
          timestamp: new Date(),
        },
      });
    } catch (error) {
      Logger.error('Collaboration cleanup failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to cleanup collaboration data',
        },
      });
    }
  }
);

// ============================================================================
// ADVANCED COLLABORATION FEATURES
// ============================================================================

/**
 * POST /collaboration/session/board/:boardId
 * Create a shareable collaboration session
 */
router.post(
  '/session/board/:boardId',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    body('expiresIn').optional().isInt({ min: 1, max: 1440 }).withMessage('Expires in must be between 1 and 1440 minutes'),
    body('allowedUsers').optional().isArray().withMessage('Allowed users must be an array'),
    body('allowedUsers.*').optional().isUUID().withMessage('Each allowed user must be a valid UUID'),
    body('permissions').optional().isArray().withMessage('Permissions must be an array'),
    body('permissions.*').optional().isIn(['read', 'write', 'comment', 'admin']).withMessage('Invalid permission'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const { expiresIn, allowedUsers, permissions } = req.body;
      const userId = req.user!.id;

      // Use the original collaboration service for session management
      const { CollaborationService } = await import('@/services/collaboration.service');
      const session = await CollaborationService.createCollaborationSession(
        boardId,
        userId,
        {
          expiresIn,
          allowedUsers,
          permissions,
        }
      );

      res.status(201).json({
        data: session,
      });
    } catch (error) {
      Logger.error('Create collaboration session failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to create collaboration session',
        },
      });
    }
  }
);

/**
 * POST /collaboration/session/:sessionId/join
 * Join a collaboration session
 */
router.post(
  '/session/:sessionId/join',
  [
    param('sessionId').isString().withMessage('Session ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { sessionId } = req.params;
      const userId = req.user!.id;

      // Use the original collaboration service for session management
      const { CollaborationService } = await import('@/services/collaboration.service');
      const result = await CollaborationService.joinCollaborationSession(sessionId, userId);

      if (result.success) {
        res.json({
          data: result,
        });
      } else {
        res.status(403).json({
          error: {
            type: 'forbidden',
            message: result.error || 'Failed to join collaboration session',
          },
        });
      }
    } catch (error) {
      Logger.error('Join collaboration session failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to join collaboration session',
        },
      });
    }
  }
);

/**
 * GET /collaboration/metrics/board/:boardId
 * Get collaboration metrics for a board
 */
router.get(
  '/metrics/board/:boardId',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;

      // Use the original collaboration service for metrics
      const { CollaborationService } = await import('@/services/collaboration.service');
      const metrics = await CollaborationService.getCollaborationMetrics(boardId);

      res.json({
        data: {
          boardId,
          metrics,
          timestamp: new Date(),
        },
      });
    } catch (error) {
      Logger.error('Get collaboration metrics failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get collaboration metrics',
        },
      });
    }
  }
);

/**
 * POST /collaboration/conflict/resolve
 * Resolve edit conflict
 */
router.post(
  '/conflict/resolve',
  [
    body('itemId').isUUID().withMessage('Valid item ID required'),
    body('field').isString().withMessage('Field name required'),
    body('localValue').exists().withMessage('Local value required'),
    body('currentValue').exists().withMessage('Current value required'),
    body('timestamp').isISO8601().withMessage('Valid timestamp required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { itemId, field, localValue, currentValue, timestamp } = req.body;
      const userId = req.user!.id;

      // Use the original collaboration service for conflict resolution
      const { CollaborationService } = await import('@/services/collaboration.service');
      const result = await CollaborationService.handleEditConflict(
        itemId,
        userId,
        field,
        localValue,
        currentValue,
        new Date(timestamp)
      );

      res.json({
        data: result,
      });
    } catch (error) {
      Logger.error('Resolve conflict failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to resolve conflict',
        },
      });
    }
  }
);

/**
 * PUT /collaboration/selection/board/:boardId
 * Update user selection
 */
router.put(
  '/selection/board/:boardId',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    body('itemIds').isArray().withMessage('Item IDs must be an array'),
    body('itemIds.*').isUUID().withMessage('Each item ID must be valid'),
    body('startPosition').optional().isObject().withMessage('Start position must be an object'),
    body('startPosition.x').optional().isNumeric().withMessage('Start position X must be numeric'),
    body('startPosition.y').optional().isNumeric().withMessage('Start position Y must be numeric'),
    body('endPosition').optional().isObject().withMessage('End position must be an object'),
    body('endPosition.x').optional().isNumeric().withMessage('End position X must be numeric'),
    body('endPosition.y').optional().isNumeric().withMessage('End position Y must be numeric'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const { itemIds, startPosition, endPosition } = req.body;
      const userId = req.user!.id;

      // Use the original collaboration service for selection tracking
      const { CollaborationService } = await import('@/services/collaboration.service');
      await CollaborationService.updateUserSelection(userId, boardId, {
        itemIds,
        startPosition,
        endPosition,
      });

      res.json({
        data: {
          message: 'Selection updated successfully',
          boardId,
          userId,
        },
      });
    } catch (error) {
      Logger.error('Update selection failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to update selection',
        },
      });
    }
  }
);

/**
 * POST /collaboration/bulk-edit/check
 * Check for conflicts before bulk edit
 */
router.post(
  '/bulk-edit/check',
  [
    body('itemIds').isArray({ min: 1 }).withMessage('Item IDs array required'),
    body('itemIds.*').isUUID().withMessage('Each item ID must be valid'),
    body('changes').isObject().withMessage('Changes object required'),
    body('boardId').isUUID().withMessage('Valid board ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { itemIds, changes, boardId } = req.body;
      const userId = req.user!.id;

      // Use the original collaboration service for bulk edit handling
      const { CollaborationService } = await import('@/services/collaboration.service');
      const result = await CollaborationService.handleBulkEdit(itemIds, changes, userId, boardId);

      res.json({
        data: result,
      });
    } catch (error) {
      Logger.error('Bulk edit check failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to check bulk edit conflicts',
        },
      });
    }
  }
);

export default router;