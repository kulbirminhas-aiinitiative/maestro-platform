import { Router } from 'express';
import { body, param, query } from 'express-validator';
import { AuthenticatedRequest } from '@/types';
import { BoardService } from '@/services/board.service';
import { authenticateToken } from '@/middleware/auth';
import { validationMiddleware } from '@/middleware/express-validation';
import { Logger } from '@/config/logger';

const router = Router();

// Apply authentication to all routes
router.use(authenticateToken);

// ============================================================================
// BOARD ROUTES
// ============================================================================

/**
 * GET /boards/workspace/:workspaceId
 * Get all boards for a workspace
 */
router.get(
  '/workspace/:workspaceId',
  [
    param('workspaceId').isUUID().withMessage('Valid workspace ID required'),
    query('page').optional().isInt({ min: 1 }).withMessage('Page must be a positive integer'),
    query('limit').optional().isInt({ min: 1, max: 100 }).withMessage('Limit must be between 1 and 100'),
    query('folderId').optional().isUUID().withMessage('Valid folder ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { workspaceId } = req.params;
      const { page, limit, folderId } = req.query;
      const userId = req.user!.id;

      const result = await BoardService.getByWorkspace(
        workspaceId,
        userId,
        page ? parseInt(page as string) : 1,
        limit ? parseInt(limit as string) : 20,
        folderId as string
      );

      res.json({
        data: result.data,
        meta: result.meta,
      });
    } catch (error) {
      Logger.error('Get workspace boards failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get boards',
        },
      });
    }
  }
);

/**
 * GET /boards/:boardId
 * Get board by ID with optional includes
 */
router.get(
  '/:boardId',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    query('includeColumns').optional().isBoolean(),
    query('includeItems').optional().isBoolean(),
    query('includeMembers').optional().isBoolean(),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const { includeColumns, includeItems, includeMembers } = req.query;
      const userId = req.user!.id;

      const board = await BoardService.getById(
        boardId,
        userId,
        includeColumns === 'true',
        includeItems === 'true',
        includeMembers === 'true'
      );

      if (!board) {
        return res.status(404).json({
          error: {
            type: 'not_found',
            message: 'Board not found',
          },
        });
      }

      res.json({
        data: board,
      });
    } catch (error) {
      Logger.error('Get board failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get board',
        },
      });
    }
  }
);

/**
 * POST /boards
 * Create a new board
 */
router.post(
  '/',
  [
    body('name').isString().trim().isLength({ min: 1, max: 100 }).withMessage('Name is required and must be between 1-100 characters'),
    body('description').optional().isString().trim().isLength({ max: 500 }).withMessage('Description must be less than 500 characters'),
    body('workspaceId').isUUID().withMessage('Valid workspace ID required'),
    body('templateId').optional().isUUID().withMessage('Valid template ID required'),
    body('folderId').optional().isUUID().withMessage('Valid folder ID required'),
    body('isPrivate').optional().isBoolean().withMessage('isPrivate must be a boolean'),
    body('settings').optional().isObject().withMessage('Settings must be an object'),
    body('columns').optional().isArray().withMessage('Columns must be an array'),
    body('columns.*.name').optional().isString().trim().isLength({ min: 1, max: 50 }).withMessage('Column name is required and must be between 1-50 characters'),
    body('columns.*.color').optional().isString().matches(/^#[0-9A-Fa-f]{6}$/).withMessage('Column color must be a valid hex color'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const userId = req.user!.id;
      const boardData = req.body;

      const board = await BoardService.create(boardData, userId);

      res.status(201).json({
        data: board,
      });
    } catch (error) {
      Logger.error('Create board failed', error as Error);

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
            message: 'Failed to create board',
          },
        });
      }
    }
  }
);

/**
 * PUT /boards/:boardId
 * Update board
 */
router.put(
  '/:boardId',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    body('name').optional().isString().trim().isLength({ min: 1, max: 100 }).withMessage('Name must be between 1-100 characters'),
    body('description').optional().isString().trim().isLength({ max: 500 }).withMessage('Description must be less than 500 characters'),
    body('folderId').optional().isUUID().withMessage('Valid folder ID required'),
    body('isPrivate').optional().isBoolean().withMessage('isPrivate must be a boolean'),
    body('settings').optional().isObject().withMessage('Settings must be an object'),
    body('position').optional().isInt({ min: 0 }).withMessage('Position must be a non-negative integer'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const userId = req.user!.id;
      const updateData = req.body;

      const board = await BoardService.update(boardId, updateData, userId);

      res.json({
        data: board,
      });
    } catch (error) {
      Logger.error('Update board failed', error as Error);

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
            message: 'Failed to update board',
          },
        });
      }
    }
  }
);

/**
 * DELETE /boards/:boardId
 * Delete board (soft delete)
 */
router.delete(
  '/:boardId',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const userId = req.user!.id;

      await BoardService.delete(boardId, userId);

      res.status(204).send();
    } catch (error) {
      Logger.error('Delete board failed', error as Error);

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
            message: 'Failed to delete board',
          },
        });
      }
    }
  }
);

/**
 * GET /boards/:boardId/statistics
 * Get board statistics
 */
router.get(
  '/:boardId/statistics',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;

      const statistics = await BoardService.getStatistics(boardId);

      res.json({
        data: statistics,
      });
    } catch (error) {
      Logger.error('Get board statistics failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get board statistics',
        },
      });
    }
  }
);

// ============================================================================
// BOARD COLUMN ROUTES
// ============================================================================

/**
 * POST /boards/:boardId/columns
 * Create board column
 */
router.post(
  '/:boardId/columns',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    body('name').isString().trim().isLength({ min: 1, max: 50 }).withMessage('Name is required and must be between 1-50 characters'),
    body('color').optional().isString().matches(/^#[0-9A-Fa-f]{6}$/).withMessage('Color must be a valid hex color'),
    body('position').optional().isInt({ min: 0 }).withMessage('Position must be a non-negative integer'),
    body('settings').optional().isObject().withMessage('Settings must be an object'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const userId = req.user!.id;
      const columnData = req.body;

      const column = await BoardService.createColumn(boardId, columnData, userId);

      res.status(201).json({
        data: column,
      });
    } catch (error) {
      Logger.error('Create board column failed', error as Error);

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
            message: 'Failed to create column',
          },
        });
      }
    }
  }
);

/**
 * PUT /boards/columns/:columnId
 * Update board column
 */
router.put(
  '/columns/:columnId',
  [
    param('columnId').isUUID().withMessage('Valid column ID required'),
    body('name').optional().isString().trim().isLength({ min: 1, max: 50 }).withMessage('Name must be between 1-50 characters'),
    body('color').optional().isString().matches(/^#[0-9A-Fa-f]{6}$/).withMessage('Color must be a valid hex color'),
    body('position').optional().isInt({ min: 0 }).withMessage('Position must be a non-negative integer'),
    body('settings').optional().isObject().withMessage('Settings must be an object'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { columnId } = req.params;
      const userId = req.user!.id;
      const updateData = req.body;

      const column = await BoardService.updateColumn(columnId, updateData, userId);

      res.json({
        data: column,
      });
    } catch (error) {
      Logger.error('Update board column failed', error as Error);

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
            message: 'Failed to update column',
          },
        });
      }
    }
  }
);

/**
 * DELETE /boards/columns/:columnId
 * Delete board column
 */
router.delete(
  '/columns/:columnId',
  [
    param('columnId').isUUID().withMessage('Valid column ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { columnId } = req.params;
      const userId = req.user!.id;

      await BoardService.deleteColumn(columnId, userId);

      res.status(204).send();
    } catch (error) {
      Logger.error('Delete board column failed', error as Error);

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
            message: 'Failed to delete column',
          },
        });
      }
    }
  }
);

// ============================================================================
// BOARD MEMBER ROUTES
// ============================================================================

/**
 * GET /boards/:boardId/members
 * Get board members
 */
router.get(
  '/:boardId/members',
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

      const result = await BoardService.getMembers(
        boardId,
        page ? parseInt(page as string) : 1,
        limit ? parseInt(limit as string) : 20
      );

      res.json({
        data: result.data,
        meta: result.meta,
      });
    } catch (error) {
      Logger.error('Get board members failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get board members',
        },
      });
    }
  }
);

/**
 * POST /boards/:boardId/members
 * Add member to board
 */
router.post(
  '/:boardId/members',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    body('userId').isUUID().withMessage('Valid user ID required'),
    body('role').optional().isIn(['member', 'admin']).withMessage('Role must be member or admin'),
    body('permissions').optional().isObject().withMessage('Permissions must be an object'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const { userId, role = 'member', permissions = {} } = req.body;
      const addedBy = req.user!.id;

      const member = await BoardService.addMember(boardId, userId, role, permissions, addedBy);

      res.status(201).json({
        data: member,
      });
    } catch (error) {
      Logger.error('Add board member failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('Access denied')) {
        res.status(403).json({
          error: {
            type: 'forbidden',
            message: errorMessage,
          },
        });
      } else if (errorMessage.includes('already a member')) {
        res.status(409).json({
          error: {
            type: 'conflict',
            message: errorMessage,
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to add member',
          },
        });
      }
    }
  }
);

/**
 * DELETE /boards/:boardId/members/:userId
 * Remove member from board
 */
router.delete(
  '/:boardId/members/:userId',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    param('userId').isUUID().withMessage('Valid user ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId, userId } = req.params;
      const removedBy = req.user!.id;

      await BoardService.removeMember(boardId, userId, removedBy);

      res.status(204).send();
    } catch (error) {
      Logger.error('Remove board member failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('Access denied')) {
        res.status(403).json({
          error: {
            type: 'forbidden',
            message: errorMessage,
          },
        });
      } else if (errorMessage.includes('last admin')) {
        res.status(409).json({
          error: {
            type: 'conflict',
            message: errorMessage,
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to remove member',
          },
        });
      }
    }
  }
);

/**
 * PUT /boards/:boardId/members/:userId
 * Update board member role and permissions
 */
router.put(
  '/:boardId/members/:userId',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    param('userId').isUUID().withMessage('Valid user ID required'),
    body('role').optional().isIn(['member', 'admin']).withMessage('Role must be member or admin'),
    body('permissions').optional().isObject().withMessage('Permissions must be an object'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId, userId } = req.params;
      const { role, permissions } = req.body;
      const updatedBy = req.user!.id;

      const member = await BoardService.updateMember(boardId, userId, role, permissions, updatedBy);

      res.json({
        data: member,
      });
    } catch (error) {
      Logger.error('Update board member failed', error as Error);

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
            message: 'Failed to update member',
          },
        });
      }
    }
  }
);

// ============================================================================
// ADVANCED BOARD OPERATIONS
// ============================================================================

/**
 * POST /boards/:boardId/share
 * Share board with multiple users
 */
router.post(
  '/:boardId/share',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    body('userIds').isArray({ min: 1, max: 50 }).withMessage('UserIds must be an array with 1-50 items'),
    body('userIds.*').isUUID().withMessage('All user IDs must be valid UUIDs'),
    body('permissions').optional().isArray().withMessage('Permissions must be an array'),
    body('permissions.*').optional().isIn(['read', 'write', 'admin']).withMessage('Invalid permission type'),
    body('message').optional().isString().isLength({ max: 500 }).withMessage('Message must be less than 500 characters'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const { userIds, permissions = ['read'], message } = req.body;
      const sharedBy = req.user!.id;

      let sharedWithCount = 0;
      const failedUsers: Array<{ userId: string; error: string }> = [];

      // Add each user to the board
      for (const userId of userIds) {
        try {
          await BoardService.addMember(boardId, userId, 'member', {}, sharedBy);
          sharedWithCount++;
        } catch (error) {
          failedUsers.push({
            userId,
            error: (error as Error).message,
          });
        }
      }

      res.json({
        data: {
          sharedWithCount,
          failedUsers,
          totalRequested: userIds.length,
        },
      });
    } catch (error) {
      Logger.error('Share board failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to share board',
        },
      });
    }
  }
);

/**
 * POST /boards/:boardId/duplicate
 * Duplicate board with optional items and members
 */
router.post(
  '/:boardId/duplicate',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    body('name').isString().trim().isLength({ min: 1, max: 100 }).withMessage('Name is required and must be between 1-100 characters'),
    body('workspaceId').optional().isUUID().withMessage('Valid workspace ID required'),
    body('includeItems').optional().isBoolean().withMessage('includeItems must be a boolean'),
    body('includeMembers').optional().isBoolean().withMessage('includeMembers must be a boolean'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const { name, workspaceId, includeItems = true, includeMembers = false } = req.body;
      const userId = req.user!.id;

      // Use the enhanced duplication service
      const duplicatedBoard = await BoardService.duplicateBoard(
        boardId,
        {
          name,
          workspaceId,
          includeItems,
          includeMembers,
        },
        userId
      );

      res.status(201).json({
        data: duplicatedBoard,
      });
    } catch (error) {
      Logger.error('Duplicate board failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to duplicate board',
        },
      });
    }
  }
);

/**
 * GET /boards/:boardId/columns
 * Get all board columns
 */
router.get(
  '/:boardId/columns',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const userId = req.user!.id;

      const board = await BoardService.getById(boardId, userId, true, false, false);
      if (!board) {
        return res.status(404).json({
          error: {
            type: 'not_found',
            message: 'Board not found',
          },
        });
      }

      res.json({
        data: board.columns || [],
      });
    } catch (error) {
      Logger.error('Get board columns failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get board columns',
        },
      });
    }
  }
);

/**
 * PUT /boards/:boardId/columns/bulk
 * Bulk update board columns (create, update, delete)
 */
router.put(
  '/:boardId/columns/bulk',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    body('columns').isArray().withMessage('Columns must be an array'),
    body('columns.*.id').optional().isUUID().withMessage('Column ID must be a valid UUID'),
    body('columns.*.name').isString().trim().isLength({ min: 1, max: 50 }).withMessage('Column name is required and must be between 1-50 characters'),
    body('columns.*.position').isInt({ min: 0 }).withMessage('Position must be a non-negative integer'),
    body('columns.*._action').isIn(['create', 'update', 'delete']).withMessage('Action must be create, update, or delete'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const { columns } = req.body;
      const userId = req.user!.id;

      // Check permissions
      const hasAccess = await BoardService.hasWriteAccess(boardId, userId);
      if (!hasAccess) {
        return res.status(403).json({
          error: {
            type: 'forbidden',
            message: 'Access denied',
          },
        });
      }

      let created = 0;
      let updated = 0;
      let deleted = 0;
      const resultColumns = [];

      // Process each column operation
      for (const columnData of columns) {
        const { _action, id, ...data } = columnData;

        try {
          switch (_action) {
            case 'create':
              const newColumn = await BoardService.createColumn(boardId, data, userId);
              resultColumns.push(newColumn);
              created++;
              break;

            case 'update':
              if (!id) {
                throw new Error('Column ID required for update operation');
              }
              const updatedColumn = await BoardService.updateColumn(id, data, userId);
              resultColumns.push(updatedColumn);
              updated++;
              break;

            case 'delete':
              if (!id) {
                throw new Error('Column ID required for delete operation');
              }
              await BoardService.deleteColumn(id, userId);
              deleted++;
              break;

            default:
              throw new Error(`Invalid action: ${_action}`);
          }
        } catch (error) {
          Logger.error(`Bulk column operation failed for action ${_action}`, error as Error);
          // Continue with other operations
        }
      }

      res.json({
        data: resultColumns,
        changes: {
          created,
          updated,
          deleted,
        },
      });
    } catch (error) {
      Logger.error('Bulk update board columns failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to update board columns',
        },
      });
    }
  }
);

/**
 * GET /boards/:boardId/activity
 * Get board activity statistics
 */
router.get(
  '/:boardId/activity',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    query('startDate').optional().isISO8601().withMessage('Valid start date required'),
    query('endDate').optional().isISO8601().withMessage('Valid end date required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const { startDate, endDate } = req.query;

      // Default to last 30 days if no date range provided
      const end = endDate ? new Date(endDate as string) : new Date();
      const start = startDate ? new Date(startDate as string) : new Date(Date.now() - 30 * 24 * 60 * 60 * 1000);

      const statistics = await BoardService.getActivityStatistics(boardId, { start, end });

      res.json({
        data: statistics,
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

/**
 * POST /boards/:boardId/archive
 * Archive a board (soft delete with ability to restore)
 */
router.post(
  '/:boardId/archive',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const userId = req.user!.id;

      // Check permissions
      const hasAccess = await BoardService.hasAdminAccess(boardId, userId);
      if (!hasAccess) {
        return res.status(403).json({
          error: {
            type: 'forbidden',
            message: 'Access denied',
          },
        });
      }

      // Archive the board (soft delete)
      await BoardService.delete(boardId, userId);

      res.status(204).send();
    } catch (error) {
      Logger.error('Archive board failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to archive board',
        },
      });
    }
  }
);

export default router;