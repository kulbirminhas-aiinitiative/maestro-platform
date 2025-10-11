import { Router } from 'express';
import { param, body, query, validationResult } from 'express-validator';
import { ItemService } from '@/services/item.service';
import { FileService } from '@/services/file.service';
import { authenticate, authorize } from '@/middleware/auth';
import { rateLimit } from '@/middleware/rate-limit';
import { Logger } from '@/config/logger';
import { handleValidationErrors } from '@/middleware/validation';

const router = Router();

// Apply authentication to all item routes
router.use(authenticate);

// ============================================================================
// ITEM CRUD OPERATIONS
// ============================================================================

/**
 * @route   GET /api/items/:itemId
 * @desc    Get item by ID
 * @access  Private
 */
router.get(
  '/:itemId',
  [
    param('itemId')
      .isUUID()
      .withMessage('Valid item ID is required'),
    query('includeComments')
      .optional()
      .isBoolean()
      .withMessage('includeComments must be a boolean'),
    query('includeChildren')
      .optional()
      .isBoolean()
      .withMessage('includeChildren must be a boolean'),
    query('includeDependencies')
      .optional()
      .isBoolean()
      .withMessage('includeDependencies must be a boolean'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { itemId } = req.params;
      const userId = req.user!.id;
      const {
        includeComments = false,
        includeChildren = false,
        includeDependencies = false,
      } = req.query;

      const item = await ItemService.getItem(itemId, userId);

      res.json({
        success: true,
        data: item,
      });
    } catch (error) {
      Logger.error('Get item failed', error as Error);
      const statusCode = (error as Error).message.includes('not found') ||
                        (error as Error).message.includes('Access denied') ? 404 : 500;
      res.status(statusCode).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   PUT /api/items/:itemId
 * @desc    Update item
 * @access  Private
 */
router.put(
  '/:itemId',
  rateLimit({ max: 200, windowMs: 60000 }), // 200 requests per minute
  [
    param('itemId')
      .isUUID()
      .withMessage('Valid item ID is required'),
    body('name')
      .optional()
      .trim()
      .isLength({ min: 1, max: 200 })
      .withMessage('Item name must be between 1 and 200 characters'),
    body('description')
      .optional()
      .trim()
      .isLength({ max: 5000 })
      .withMessage('Description must not exceed 5000 characters'),
    body('parentId')
      .optional()
      .isUUID()
      .withMessage('Parent ID must be a valid UUID'),
    body('position')
      .optional()
      .isNumeric()
      .withMessage('Position must be a number'),
    body('itemData')
      .optional()
      .isObject()
      .withMessage('Item data must be an object'),
    body('assigneeIds')
      .optional()
      .isArray()
      .withMessage('Assignee IDs must be an array'),
    body('assigneeIds.*')
      .optional()
      .isUUID()
      .withMessage('Each assignee ID must be a valid UUID'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { itemId } = req.params;
      const userId = req.user!.id;
      const updateData = req.body;

      const item = await ItemService.updateItem(itemId, userId, updateData);

      res.json({
        success: true,
        data: item,
        message: 'Item updated successfully',
      });
    } catch (error) {
      Logger.error('Update item failed', error as Error);
      const statusCode = (error as Error).message.includes('Access denied') ? 403 : 400;
      res.status(statusCode).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   DELETE /api/items/:itemId
 * @desc    Delete item
 * @access  Private
 */
router.delete(
  '/:itemId',
  rateLimit({ max: 50, windowMs: 60000 }), // 50 requests per minute
  [
    param('itemId')
      .isUUID()
      .withMessage('Valid item ID is required'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { itemId } = req.params;
      const userId = req.user!.id;

      await ItemService.deleteItem(itemId, userId);

      res.json({
        success: true,
        message: 'Item deleted successfully',
      });
    } catch (error) {
      Logger.error('Delete item failed', error as Error);
      const statusCode = (error as Error).message.includes('Access denied') ? 403 : 400;
      res.status(statusCode).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   POST /api/items/:itemId/duplicate
 * @desc    Duplicate item
 * @access  Private
 */
router.post(
  '/:itemId/duplicate',
  rateLimit({ max: 20, windowMs: 60000 }), // 20 requests per minute
  [
    param('itemId')
      .isUUID()
      .withMessage('Valid item ID is required'),
    body('name')
      .optional()
      .trim()
      .isLength({ min: 1, max: 200 })
      .withMessage('Item name must be between 1 and 200 characters'),
    body('includeChildren')
      .optional()
      .isBoolean()
      .withMessage('includeChildren must be a boolean'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { itemId } = req.params;
      const userId = req.user!.id;
      const { name, includeChildren = false } = req.body;

      const duplicatedItem = await ItemService.duplicateItem(
        itemId,
        userId,
        name,
        includeChildren
      );

      res.status(201).json({
        success: true,
        data: duplicatedItem,
        message: 'Item duplicated successfully',
      });
    } catch (error) {
      Logger.error('Duplicate item failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

// ============================================================================
// ITEM MOVEMENT AND POSITIONING
// ============================================================================

/**
 * @route   PUT /api/items/:itemId/move
 * @desc    Move item to different position or parent
 * @access  Private
 */
router.put(
  '/:itemId/move',
  rateLimit({ max: 100, windowMs: 60000 }), // 100 requests per minute
  [
    param('itemId')
      .isUUID()
      .withMessage('Valid item ID is required'),
    body('targetPosition')
      .isNumeric()
      .withMessage('Target position is required and must be a number'),
    body('targetParentId')
      .optional()
      .isUUID()
      .withMessage('Target parent ID must be a valid UUID'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { itemId } = req.params;
      const userId = req.user!.id;
      const { targetPosition, targetParentId } = req.body;

      const result = await ItemService.moveItem(
        itemId,
        userId,
        targetPosition,
        targetParentId
      );

      res.json({
        success: true,
        data: result,
        message: 'Item moved successfully',
      });
    } catch (error) {
      Logger.error('Move item failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

// ============================================================================
// BULK OPERATIONS
// ============================================================================

/**
 * @route   PUT /api/items/bulk/update
 * @desc    Bulk update items
 * @access  Private
 */
router.put(
  '/bulk/update',
  rateLimit({ max: 20, windowMs: 60000 }), // 20 requests per minute
  [
    body('itemIds')
      .isArray({ min: 1, max: 50 })
      .withMessage('Item IDs must be an array with 1-50 items'),
    body('itemIds.*')
      .isUUID()
      .withMessage('Each item ID must be a valid UUID'),
    body('updates')
      .isObject()
      .withMessage('Updates must be an object'),
    body('updates.itemData')
      .optional()
      .isObject()
      .withMessage('Item data must be an object'),
    body('updates.assigneeIds')
      .optional()
      .isArray()
      .withMessage('Assignee IDs must be an array'),
    body('updates.assigneeIds.*')
      .optional()
      .isUUID()
      .withMessage('Each assignee ID must be a valid UUID'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const userId = req.user!.id;
      const { itemIds, updates } = req.body;

      const result = await ItemService.bulkUpdateItems(userId, {
        itemIds,
        updates,
      });

      res.json({
        success: true,
        data: result,
        message: 'Bulk update completed',
      });
    } catch (error) {
      Logger.error('Bulk update items failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   PUT /api/items/bulk/move
 * @desc    Bulk move items
 * @access  Private
 */
router.put(
  '/bulk/move',
  rateLimit({ max: 10, windowMs: 60000 }), // 10 requests per minute
  [
    body('itemMoves')
      .isArray({ min: 1, max: 50 })
      .withMessage('Item moves must be an array with 1-50 items'),
    body('itemMoves.*.itemId')
      .isUUID()
      .withMessage('Item ID must be a valid UUID'),
    body('itemMoves.*.targetPosition')
      .isNumeric()
      .withMessage('Target position must be a number'),
    body('itemMoves.*.targetParentId')
      .optional()
      .isUUID()
      .withMessage('Target parent ID must be a valid UUID'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const userId = req.user!.id;
      const { itemMoves } = req.body;

      const result = await ItemService.bulkMoveItems(userId, itemMoves);

      res.json({
        success: true,
        data: result,
        message: 'Bulk move completed',
      });
    } catch (error) {
      Logger.error('Bulk move items failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

// ============================================================================
// ITEM ASSIGNMENTS
// ============================================================================

/**
 * @route   POST /api/items/:itemId/assignments
 * @desc    Add assignment to item
 * @access  Private
 */
router.post(
  '/:itemId/assignments',
  rateLimit({ max: 100, windowMs: 60000 }), // 100 requests per minute
  [
    param('itemId')
      .isUUID()
      .withMessage('Valid item ID is required'),
    body('assigneeId')
      .isUUID()
      .withMessage('Valid assignee ID is required'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { itemId } = req.params;
      const userId = req.user!.id;
      const { assigneeId } = req.body;

      const assignment = await ItemService.addAssignment(itemId, userId, assigneeId);

      res.status(201).json({
        success: true,
        data: assignment,
        message: 'Assignment added successfully',
      });
    } catch (error) {
      Logger.error('Add assignment failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   DELETE /api/items/:itemId/assignments/:assigneeId
 * @desc    Remove assignment from item
 * @access  Private
 */
router.delete(
  '/:itemId/assignments/:assigneeId',
  rateLimit({ max: 100, windowMs: 60000 }), // 100 requests per minute
  [
    param('itemId')
      .isUUID()
      .withMessage('Valid item ID is required'),
    param('assigneeId')
      .isUUID()
      .withMessage('Valid assignee ID is required'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { itemId, assigneeId } = req.params;
      const userId = req.user!.id;

      await ItemService.removeAssignment(itemId, userId, assigneeId);

      res.json({
        success: true,
        message: 'Assignment removed successfully',
      });
    } catch (error) {
      Logger.error('Remove assignment failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

// ============================================================================
// ITEM DEPENDENCIES
// ============================================================================

/**
 * @route   POST /api/items/:itemId/dependencies
 * @desc    Create item dependency
 * @access  Private
 */
router.post(
  '/:itemId/dependencies',
  rateLimit({ max: 50, windowMs: 60000 }), // 50 requests per minute
  [
    param('itemId')
      .isUUID()
      .withMessage('Valid item ID is required'),
    body('successorId')
      .isUUID()
      .withMessage('Valid successor ID is required'),
    body('dependencyType')
      .optional()
      .isIn(['blocks', 'depends_on', 'related', 'subtask'])
      .withMessage('Invalid dependency type'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { itemId } = req.params;
      const userId = req.user!.id;
      const { successorId, dependencyType = 'blocks' } = req.body;

      const dependency = await ItemService.createDependency(
        itemId,
        successorId,
        userId,
        dependencyType
      );

      res.status(201).json({
        success: true,
        data: dependency,
        message: 'Dependency created successfully',
      });
    } catch (error) {
      Logger.error('Create dependency failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   DELETE /api/items/dependencies/:dependencyId
 * @desc    Remove item dependency
 * @access  Private
 */
router.delete(
  '/dependencies/:dependencyId',
  rateLimit({ max: 50, windowMs: 60000 }), // 50 requests per minute
  [
    param('dependencyId')
      .isUUID()
      .withMessage('Valid dependency ID is required'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { dependencyId } = req.params;
      const userId = req.user!.id;

      await ItemService.removeDependency(dependencyId, userId);

      res.json({
        success: true,
        message: 'Dependency removed successfully',
      });
    } catch (error) {
      Logger.error('Remove dependency failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

// ============================================================================
// ITEM FILES AND ATTACHMENTS
// ============================================================================

/**
 * @route   GET /api/items/:itemId/files
 * @desc    Get item files
 * @access  Private
 */
router.get(
  '/:itemId/files',
  [
    param('itemId')
      .isUUID()
      .withMessage('Valid item ID is required'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { itemId } = req.params;
      const userId = req.user!.id;

      const files = await FileService.getEntityFiles('item', itemId, userId);

      res.json({
        success: true,
        data: files,
      });
    } catch (error) {
      Logger.error('Get item files failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   POST /api/items/:itemId/files
 * @desc    Attach file to item
 * @access  Private
 */
router.post(
  '/:itemId/files',
  rateLimit({ max: 20, windowMs: 60000 }), // 20 requests per minute
  [
    param('itemId')
      .isUUID()
      .withMessage('Valid item ID is required'),
    body('fileId')
      .isUUID()
      .withMessage('Valid file ID is required'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { itemId } = req.params;
      const userId = req.user!.id;
      const { fileId } = req.body;

      await FileService.attachFile(fileId, 'item', itemId, userId);

      res.status(201).json({
        success: true,
        message: 'File attached successfully',
      });
    } catch (error) {
      Logger.error('Attach file to item failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   DELETE /api/items/:itemId/files/:fileId
 * @desc    Detach file from item
 * @access  Private
 */
router.delete(
  '/:itemId/files/:fileId',
  rateLimit({ max: 50, windowMs: 60000 }), // 50 requests per minute
  [
    param('itemId')
      .isUUID()
      .withMessage('Valid item ID is required'),
    param('fileId')
      .isUUID()
      .withMessage('Valid file ID is required'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { itemId, fileId } = req.params;
      const userId = req.user!.id;

      await FileService.detachFile(fileId, 'item', itemId, userId);

      res.json({
        success: true,
        message: 'File detached successfully',
      });
    } catch (error) {
      Logger.error('Detach file from item failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

// ============================================================================
// ITEM SEARCH
// ============================================================================

/**
 * @route   GET /api/items/search
 * @desc    Search items
 * @access  Private
 */
router.get(
  '/search',
  [
    query('q')
      .trim()
      .isLength({ min: 1, max: 100 })
      .withMessage('Search query must be between 1 and 100 characters'),
    query('workspaceId')
      .optional()
      .isUUID()
      .withMessage('Workspace ID must be a valid UUID'),
    query('limit')
      .optional()
      .isInt({ min: 1, max: 50 })
      .withMessage('Limit must be between 1 and 50'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const userId = req.user!.id;
      const { q: query, workspaceId, limit = 20 } = req.query;

      const items = await ItemService.searchItems(
        userId,
        query as string,
        workspaceId as string,
        parseInt(limit as string)
      );

      res.json({
        success: true,
        data: items,
      });
    } catch (error) {
      Logger.error('Search items failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

// ============================================================================
// ITEM CHILDREN
// ============================================================================

/**
 * @route   GET /api/items/:itemId/children
 * @desc    Get item children
 * @access  Private
 */
router.get(
  '/:itemId/children',
  [
    param('itemId')
      .isUUID()
      .withMessage('Valid item ID is required'),
    query('page')
      .optional()
      .isInt({ min: 1 })
      .withMessage('Page must be a positive integer'),
    query('limit')
      .optional()
      .isInt({ min: 1, max: 100 })
      .withMessage('Limit must be between 1 and 100'),
    query('sortBy')
      .optional()
      .isIn(['position', 'created_at', 'updated_at', 'name'])
      .withMessage('Invalid sort field'),
    query('sortOrder')
      .optional()
      .isIn(['asc', 'desc'])
      .withMessage('Sort order must be asc or desc'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { itemId } = req.params;
      const userId = req.user!.id;

      const page = parseInt(req.query.page as string) || 1;
      const limit = parseInt(req.query.limit as string) || 50;
      const { sortBy = 'position', sortOrder = 'asc' } = req.query;

      // Get the item first to get its board ID
      const item = await ItemService.getItem(itemId, userId);

      const filter = { parentId: itemId };
      const sort = [{ field: sortBy as string, direction: sortOrder as 'asc' | 'desc' }];

      const result = await ItemService.getBoardItems(
        item.boardId,
        userId,
        filter,
        sort,
        page,
        limit
      );

      res.json({
        success: true,
        data: result.data,
        meta: result.meta,
      });
    } catch (error) {
      Logger.error('Get item children failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   POST /api/items/:itemId/children
 * @desc    Create child item
 * @access  Private
 */
router.post(
  '/:itemId/children',
  rateLimit({ max: 100, windowMs: 60000 }), // 100 requests per minute
  [
    param('itemId')
      .isUUID()
      .withMessage('Valid item ID is required'),
    body('name')
      .trim()
      .isLength({ min: 1, max: 200 })
      .withMessage('Item name must be between 1 and 200 characters'),
    body('description')
      .optional()
      .trim()
      .isLength({ max: 5000 })
      .withMessage('Description must not exceed 5000 characters'),
    body('position')
      .optional()
      .isNumeric()
      .withMessage('Position must be a number'),
    body('itemData')
      .optional()
      .isObject()
      .withMessage('Item data must be an object'),
    body('assigneeIds')
      .optional()
      .isArray()
      .withMessage('Assignee IDs must be an array'),
    body('assigneeIds.*')
      .optional()
      .isUUID()
      .withMessage('Each assignee ID must be a valid UUID'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { itemId } = req.params;
      const userId = req.user!.id;
      const { name, description, position, itemData, assigneeIds } = req.body;

      // Get the parent item to get its board ID
      const parentItem = await ItemService.getItem(itemId, userId);

      const childItem = await ItemService.createItem(
        parentItem.boardId,
        userId,
        {
          name,
          description,
          parentId: itemId,
          position,
          itemData,
          assigneeIds,
        }
      );

      res.status(201).json({
        success: true,
        data: childItem,
        message: 'Child item created successfully',
      });
    } catch (error) {
      Logger.error('Create child item failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

export default router;