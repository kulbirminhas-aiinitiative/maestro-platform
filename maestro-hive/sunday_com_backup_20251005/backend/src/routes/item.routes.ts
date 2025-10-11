import { Router } from 'express';
import { body, param, query } from 'express-validator';
import { AuthenticatedRequest } from '@/types';
import { ItemService } from '@/services/item.service';
import { authenticateToken } from '@/middleware/auth';
import { validationMiddleware } from '@/middleware/express-validation';
import { Logger } from '@/config/logger';

const router = Router();

// Apply authentication to all routes
router.use(authenticateToken);

// ============================================================================
// ITEM ROUTES
// ============================================================================

/**
 * GET /items/board/:boardId
 * Get all items for a board with filtering and sorting
 */
router.get(
  '/board/:boardId',
  [
    param('boardId').isUUID().withMessage('Valid board ID required'),
    query('page').optional().isInt({ min: 1 }).withMessage('Page must be a positive integer'),
    query('limit').optional().isInt({ min: 1, max: 100 }).withMessage('Limit must be between 1 and 100'),
    query('parentId').optional().isUUID().withMessage('Valid parent ID required'),
    query('assigneeIds').optional().isString(),
    query('status').optional().isString(),
    query('search').optional().isString().trim(),
    query('dueDateFrom').optional().isISO8601().withMessage('Valid ISO date required'),
    query('dueDateTo').optional().isISO8601().withMessage('Valid ISO date required'),
    query('sortBy').optional().isIn(['position', 'created_at', 'updated_at', 'name', 'due_date']).withMessage('Invalid sort field'),
    query('sortOrder').optional().isIn(['asc', 'desc']).withMessage('Sort order must be asc or desc'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { boardId } = req.params;
      const {
        page = 1,
        limit = 50,
        parentId,
        assigneeIds,
        status,
        search,
        dueDateFrom,
        dueDateTo,
        sortBy = 'position',
        sortOrder = 'asc',
      } = req.query;
      const userId = req.user!.id;

      // Parse filter parameters
      const filter: any = {};
      if (parentId !== undefined) filter.parentId = parentId === 'null' ? null : parentId;
      if (assigneeIds) filter.assigneeIds = (assigneeIds as string).split(',');
      if (status) filter.status = (status as string).split(',');
      if (search) filter.search = search as string;
      if (dueDateFrom) filter.dueDateFrom = new Date(dueDateFrom as string);
      if (dueDateTo) filter.dueDateTo = new Date(dueDateTo as string);

      const sort = [{
        field: sortBy as 'position' | 'created_at' | 'updated_at' | 'name' | 'due_date',
        direction: sortOrder as 'asc' | 'desc',
      }];

      const result = await ItemService.getByBoard(
        boardId,
        userId,
        filter,
        sort,
        parseInt(page as string),
        parseInt(limit as string)
      );

      res.json({
        data: result.data,
        meta: result.meta,
      });
    } catch (error) {
      Logger.error('Get board items failed', error as Error);

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
            message: 'Failed to get items',
          },
        });
      }
    }
  }
);

/**
 * GET /items/:itemId
 * Get item by ID with optional includes
 */
router.get(
  '/:itemId',
  [
    param('itemId').isUUID().withMessage('Valid item ID required'),
    query('includeComments').optional().isBoolean(),
    query('includeChildren').optional().isBoolean(),
    query('includeDependencies').optional().isBoolean(),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { itemId } = req.params;
      const { includeComments, includeChildren, includeDependencies } = req.query;
      const userId = req.user!.id;

      const item = await ItemService.getById(
        itemId,
        userId,
        includeComments === 'true',
        includeChildren === 'true',
        includeDependencies === 'true'
      );

      if (!item) {
        return res.status(404).json({
          error: {
            type: 'not_found',
            message: 'Item not found',
          },
        });
      }

      res.json({
        data: item,
      });
    } catch (error) {
      Logger.error('Get item failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get item',
        },
      });
    }
  }
);

/**
 * POST /items
 * Create a new item
 */
router.post(
  '/',
  [
    body('name').isString().trim().isLength({ min: 1, max: 200 }).withMessage('Name is required and must be between 1-200 characters'),
    body('description').optional().isString().trim().isLength({ max: 2000 }).withMessage('Description must be less than 2000 characters'),
    body('boardId').isUUID().withMessage('Valid board ID required'),
    body('parentId').optional().isUUID().withMessage('Valid parent ID required'),
    body('itemData').optional().isObject().withMessage('Item data must be an object'),
    body('position').optional().isNumeric().withMessage('Position must be a number'),
    body('assigneeIds').optional().isArray().withMessage('Assignee IDs must be an array'),
    body('assigneeIds.*').optional().isUUID().withMessage('Valid assignee ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const userId = req.user!.id;
      const itemData = req.body;

      const item = await ItemService.create(itemData, userId);

      res.status(201).json({
        data: item,
      });
    } catch (error) {
      Logger.error('Create item failed', error as Error);

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
            message: 'Failed to create item',
          },
        });
      }
    }
  }
);

/**
 * PUT /items/:itemId
 * Update item
 */
router.put(
  '/:itemId',
  [
    param('itemId').isUUID().withMessage('Valid item ID required'),
    body('name').optional().isString().trim().isLength({ min: 1, max: 200 }).withMessage('Name must be between 1-200 characters'),
    body('description').optional().isString().trim().isLength({ max: 2000 }).withMessage('Description must be less than 2000 characters'),
    body('parentId').optional().isUUID().withMessage('Valid parent ID required'),
    body('itemData').optional().isObject().withMessage('Item data must be an object'),
    body('position').optional().isNumeric().withMessage('Position must be a number'),
    body('assigneeIds').optional().isArray().withMessage('Assignee IDs must be an array'),
    body('assigneeIds.*').optional().isUUID().withMessage('Valid assignee ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { itemId } = req.params;
      const userId = req.user!.id;
      const updateData = req.body;

      const item = await ItemService.update(itemId, updateData, userId);

      res.json({
        data: item,
      });
    } catch (error) {
      Logger.error('Update item failed', error as Error);

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
            message: 'Failed to update item',
          },
        });
      }
    }
  }
);

/**
 * DELETE /items/:itemId
 * Delete item (soft delete)
 */
router.delete(
  '/:itemId',
  [
    param('itemId').isUUID().withMessage('Valid item ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { itemId } = req.params;
      const userId = req.user!.id;

      await ItemService.delete(itemId, userId);

      res.status(204).send();
    } catch (error) {
      Logger.error('Delete item failed', error as Error);

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
            message: 'Failed to delete item',
          },
        });
      }
    }
  }
);

// ============================================================================
// BULK OPERATIONS
// ============================================================================

/**
 * PUT /items/bulk/update
 * Bulk update items
 */
router.put(
  '/bulk/update',
  [
    body('itemIds').isArray({ min: 1 }).withMessage('Item IDs array is required'),
    body('itemIds.*').isUUID().withMessage('Valid item ID required'),
    body('updates').isObject().withMessage('Updates object is required'),
    body('updates.itemData').optional().isObject().withMessage('Item data must be an object'),
    body('updates.assigneeIds').optional().isArray().withMessage('Assignee IDs must be an array'),
    body('updates.assigneeIds.*').optional().isUUID().withMessage('Valid assignee ID required'),
    body('updates.parentId').optional().isUUID().withMessage('Valid parent ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { itemIds, updates } = req.body;
      const userId = req.user!.id;

      const result = await ItemService.bulkUpdate(itemIds, updates, userId);

      res.json({
        data: result,
      });
    } catch (error) {
      Logger.error('Bulk update items failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to bulk update items',
        },
      });
    }
  }
);

/**
 * DELETE /items/bulk/delete
 * Bulk delete items
 */
router.delete(
  '/bulk/delete',
  [
    body('itemIds').isArray({ min: 1 }).withMessage('Item IDs array is required'),
    body('itemIds.*').isUUID().withMessage('Valid item ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { itemIds } = req.body;
      const userId = req.user!.id;

      const result = await ItemService.bulkDelete(itemIds, userId);

      res.json({
        data: result,
      });
    } catch (error) {
      Logger.error('Bulk delete items failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to bulk delete items',
        },
      });
    }
  }
);

// ============================================================================
// ITEM DEPENDENCIES
// ============================================================================

/**
 * POST /items/:itemId/dependencies
 * Add dependency between items
 */
router.post(
  '/:itemId/dependencies',
  [
    param('itemId').isUUID().withMessage('Valid item ID required'),
    body('predecessorId').isUUID().withMessage('Valid predecessor ID required'),
    body('dependencyType').optional().isIn(['blocks', 'depends_on', 'related']).withMessage('Invalid dependency type'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { itemId } = req.params; // successor
      const { predecessorId, dependencyType = 'blocks' } = req.body;
      const userId = req.user!.id;

      await ItemService.addDependency(predecessorId, itemId, dependencyType, userId);

      res.status(201).json({
        data: {
          message: 'Dependency added successfully',
        },
      });
    } catch (error) {
      Logger.error('Add item dependency failed', error as Error);

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
      } else if (errorMessage.includes('circular')) {
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
            message: 'Failed to add dependency',
          },
        });
      }
    }
  }
);

/**
 * DELETE /items/:itemId/dependencies/:predecessorId
 * Remove dependency between items
 */
router.delete(
  '/:itemId/dependencies/:predecessorId',
  [
    param('itemId').isUUID().withMessage('Valid item ID required'),
    param('predecessorId').isUUID().withMessage('Valid predecessor ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { itemId, predecessorId } = req.params;
      const userId = req.user!.id;

      await ItemService.removeDependency(predecessorId, itemId, userId);

      res.status(204).send();
    } catch (error) {
      Logger.error('Remove item dependency failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to remove dependency',
        },
      });
    }
  }
);

/**
 * PUT /items/:itemId/move
 * Move item to new position/parent/board
 */
router.put(
  '/:itemId/move',
  [
    param('itemId').isUUID().withMessage('Valid item ID required'),
    body('position').isNumeric().withMessage('Position is required and must be a number'),
    body('parentId').optional().isUUID().withMessage('Valid parent ID required'),
    body('boardId').optional().isUUID().withMessage('Valid board ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { itemId } = req.params;
      const { position, parentId, boardId } = req.body;
      const userId = req.user!.id;

      const result = await ItemService.move(
        itemId,
        {
          position: parseFloat(position),
          parentId: parentId || null,
          boardId,
        },
        userId
      );

      res.json({
        data: {
          item: result.item,
          affectedItems: result.affectedItems,
        },
      });
    } catch (error) {
      Logger.error('Move item failed', error as Error);

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
            message: 'Failed to move item',
          },
        });
      }
    }
  }
);

export default router;