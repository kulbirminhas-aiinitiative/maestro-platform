import { Router } from 'express';
import { param, body, query, validationResult } from 'express-validator';
import { BoardService } from '@/services/board.service';
import { ItemService } from '@/services/item.service';
import { authenticate, authorize } from '@/middleware/auth';
import { rateLimit } from '@/middleware/rate-limit';
import { Logger } from '@/config/logger';
import { handleValidationErrors } from '@/middleware/validation';

const router = Router();

// Apply authentication to all board routes
router.use(authenticate);

// ============================================================================
// BOARD CRUD OPERATIONS
// ============================================================================

/**
 * @route   POST /api/boards
 * @desc    Create a new board
 * @access  Private
 */
router.post(
  '/',
  rateLimit({ max: 50, windowMs: 60000 }), // 50 requests per minute
  [
    body('workspaceId')
      .isUUID()
      .withMessage('Valid workspace ID is required'),
    body('name')
      .trim()
      .isLength({ min: 1, max: 100 })
      .withMessage('Board name must be between 1 and 100 characters'),
    body('description')
      .optional()
      .trim()
      .isLength({ max: 500 })
      .withMessage('Description must not exceed 500 characters'),
    body('templateId')
      .optional()
      .isUUID()
      .withMessage('Template ID must be a valid UUID'),
    body('isPrivate')
      .optional()
      .isBoolean()
      .withMessage('isPrivate must be a boolean'),
    body('folderId')
      .optional()
      .isUUID()
      .withMessage('Folder ID must be a valid UUID'),
    body('settings')
      .optional()
      .isObject()
      .withMessage('Settings must be an object'),
    body('columns')
      .optional()
      .isArray()
      .withMessage('Columns must be an array'),
    body('columns.*.name')
      .optional()
      .trim()
      .isLength({ min: 1, max: 50 })
      .withMessage('Column name must be between 1 and 50 characters'),
    body('columns.*.color')
      .optional()
      .matches(/^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/)
      .withMessage('Column color must be a valid hex color'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { workspaceId, name, description, templateId, isPrivate, folderId, settings, columns } = req.body;
      const userId = req.user!.id;

      const board = await BoardService.createBoard(
        workspaceId,
        userId,
        {
          name,
          description,
          templateId,
          isPrivate,
          folderId,
          settings,
          columns,
        }
      );

      res.status(201).json({
        success: true,
        data: board,
        message: 'Board created successfully',
      });
    } catch (error) {
      Logger.error('Create board failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   GET /api/boards/:boardId
 * @desc    Get board by ID
 * @access  Private
 */
router.get(
  '/:boardId',
  [
    param('boardId')
      .isUUID()
      .withMessage('Valid board ID is required'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { boardId } = req.params;
      const userId = req.user!.id;

      const board = await BoardService.getBoard(boardId, userId);

      res.json({
        success: true,
        data: board,
      });
    } catch (error) {
      Logger.error('Get board failed', error as Error);
      const statusCode = (error as Error).message.includes('not found') ||
                        (error as Error).message.includes('access denied') ? 404 : 500;
      res.status(statusCode).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   PUT /api/boards/:boardId
 * @desc    Update board
 * @access  Private
 */
router.put(
  '/:boardId',
  rateLimit({ max: 100, windowMs: 60000 }), // 100 requests per minute
  [
    param('boardId')
      .isUUID()
      .withMessage('Valid board ID is required'),
    body('name')
      .optional()
      .trim()
      .isLength({ min: 1, max: 100 })
      .withMessage('Board name must be between 1 and 100 characters'),
    body('description')
      .optional()
      .trim()
      .isLength({ max: 500 })
      .withMessage('Description must not exceed 500 characters'),
    body('isPrivate')
      .optional()
      .isBoolean()
      .withMessage('isPrivate must be a boolean'),
    body('folderId')
      .optional()
      .isUUID()
      .withMessage('Folder ID must be a valid UUID'),
    body('settings')
      .optional()
      .isObject()
      .withMessage('Settings must be an object'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { boardId } = req.params;
      const userId = req.user!.id;
      const updateData = req.body;

      const board = await BoardService.updateBoard(boardId, userId, updateData);

      res.json({
        success: true,
        data: board,
        message: 'Board updated successfully',
      });
    } catch (error) {
      Logger.error('Update board failed', error as Error);
      const statusCode = (error as Error).message.includes('Permission denied') ? 403 : 400;
      res.status(statusCode).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   DELETE /api/boards/:boardId
 * @desc    Delete board
 * @access  Private
 */
router.delete(
  '/:boardId',
  rateLimit({ max: 20, windowMs: 60000 }), // 20 requests per minute
  [
    param('boardId')
      .isUUID()
      .withMessage('Valid board ID is required'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { boardId } = req.params;
      const userId = req.user!.id;

      await BoardService.deleteBoard(boardId, userId);

      res.json({
        success: true,
        message: 'Board deleted successfully',
      });
    } catch (error) {
      Logger.error('Delete board failed', error as Error);
      const statusCode = (error as Error).message.includes('Permission denied') ? 403 : 400;
      res.status(statusCode).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   POST /api/boards/:boardId/duplicate
 * @desc    Duplicate board
 * @access  Private
 */
router.post(
  '/:boardId/duplicate',
  rateLimit({ max: 10, windowMs: 60000 }), // 10 requests per minute
  [
    param('boardId')
      .isUUID()
      .withMessage('Valid board ID is required'),
    body('name')
      .trim()
      .isLength({ min: 1, max: 100 })
      .withMessage('Board name must be between 1 and 100 characters'),
    body('targetWorkspaceId')
      .optional()
      .isUUID()
      .withMessage('Target workspace ID must be a valid UUID'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { boardId } = req.params;
      const { name, targetWorkspaceId } = req.body;
      const userId = req.user!.id;

      const duplicatedBoard = await BoardService.duplicateBoard(
        boardId,
        userId,
        name,
        targetWorkspaceId
      );

      res.status(201).json({
        success: true,
        data: duplicatedBoard,
        message: 'Board duplicated successfully',
      });
    } catch (error) {
      Logger.error('Duplicate board failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

// ============================================================================
// BOARD LISTING AND SEARCH
// ============================================================================

/**
 * @route   GET /api/workspaces/:workspaceId/boards
 * @desc    Get boards in workspace
 * @access  Private
 */
router.get(
  '/workspace/:workspaceId',
  [
    param('workspaceId')
      .isUUID()
      .withMessage('Valid workspace ID is required'),
    query('page')
      .optional()
      .isInt({ min: 1 })
      .withMessage('Page must be a positive integer'),
    query('limit')
      .optional()
      .isInt({ min: 1, max: 100 })
      .withMessage('Limit must be between 1 and 100'),
    query('name')
      .optional()
      .trim()
      .isLength({ max: 100 })
      .withMessage('Name filter must not exceed 100 characters'),
    query('folderId')
      .optional()
      .isUUID()
      .withMessage('Folder ID must be a valid UUID'),
    query('isPrivate')
      .optional()
      .isBoolean()
      .withMessage('isPrivate must be a boolean'),
    query('sortBy')
      .optional()
      .isIn(['name', 'createdAt', 'updatedAt', 'position'])
      .withMessage('Invalid sort field'),
    query('sortOrder')
      .optional()
      .isIn(['asc', 'desc'])
      .withMessage('Sort order must be asc or desc'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { workspaceId } = req.params;
      const userId = req.user!.id;

      const page = parseInt(req.query.page as string) || 1;
      const limit = parseInt(req.query.limit as string) || 20;
      const { name, folderId, isPrivate, sortBy = 'position', sortOrder = 'asc' } = req.query;

      const filter = {
        name: name as string,
        folderId: folderId === 'null' ? null : (folderId as string),
        isPrivate: isPrivate === 'true' ? true : isPrivate === 'false' ? false : undefined,
      };

      const sort = [{ field: sortBy as string, direction: sortOrder as 'asc' | 'desc' }];

      const result = await BoardService.getWorkspaceBoards(
        workspaceId,
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
      Logger.error('Get workspace boards failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   GET /api/boards/search
 * @desc    Search boards
 * @access  Private
 */
router.get(
  '/search',
  [
    query('q')
      .trim()
      .isLength({ min: 1, max: 100 })
      .withMessage('Search query must be between 1 and 100 characters'),
    query('organizationId')
      .optional()
      .isUUID()
      .withMessage('Organization ID must be a valid UUID'),
    query('limit')
      .optional()
      .isInt({ min: 1, max: 50 })
      .withMessage('Limit must be between 1 and 50'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const userId = req.user!.id;
      const { q: query, organizationId, limit = 10 } = req.query;

      const boards = await BoardService.searchBoards(
        userId,
        query as string,
        organizationId as string,
        parseInt(limit as string)
      );

      res.json({
        success: true,
        data: boards,
      });
    } catch (error) {
      Logger.error('Search boards failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

// ============================================================================
// BOARD ITEMS
// ============================================================================

/**
 * @route   GET /api/boards/:boardId/items
 * @desc    Get board items
 * @access  Private
 */
router.get(
  '/:boardId/items',
  [
    param('boardId')
      .isUUID()
      .withMessage('Valid board ID is required'),
    query('page')
      .optional()
      .isInt({ min: 1 })
      .withMessage('Page must be a positive integer'),
    query('limit')
      .optional()
      .isInt({ min: 1, max: 100 })
      .withMessage('Limit must be between 1 and 100'),
    query('parentId')
      .optional()
      .isUUID()
      .withMessage('Parent ID must be a valid UUID'),
    query('search')
      .optional()
      .trim()
      .isLength({ max: 100 })
      .withMessage('Search query must not exceed 100 characters'),
    query('assigneeIds')
      .optional()
      .custom((value) => {
        if (typeof value === 'string') {
          const ids = value.split(',');
          return ids.every(id => id.match(/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i));
        }
        return true;
      })
      .withMessage('Assignee IDs must be valid UUIDs'),
    query('status')
      .optional()
      .custom((value) => {
        if (typeof value === 'string') {
          const statuses = value.split(',');
          return statuses.every(status => typeof status === 'string' && status.length <= 50);
        }
        return true;
      })
      .withMessage('Invalid status values'),
    query('sortBy')
      .optional()
      .isIn(['position', 'created_at', 'updated_at', 'name', 'due_date'])
      .withMessage('Invalid sort field'),
    query('sortOrder')
      .optional()
      .isIn(['asc', 'desc'])
      .withMessage('Sort order must be asc or desc'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { boardId } = req.params;
      const userId = req.user!.id;

      const page = parseInt(req.query.page as string) || 1;
      const limit = parseInt(req.query.limit as string) || 50;
      const { parentId, search, assigneeIds, status, sortBy = 'position', sortOrder = 'asc' } = req.query;

      const filter = {
        parentId: parentId === 'null' ? null : (parentId as string),
        search: search as string,
        assigneeIds: assigneeIds ? (assigneeIds as string).split(',') : undefined,
        status: status ? (status as string).split(',') : undefined,
      };

      const sort = [{ field: sortBy as string, direction: sortOrder as 'asc' | 'desc' }];

      const result = await ItemService.getBoardItems(
        boardId,
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
      Logger.error('Get board items failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   POST /api/boards/:boardId/items
 * @desc    Create item in board
 * @access  Private
 */
router.post(
  '/:boardId/items',
  rateLimit({ max: 100, windowMs: 60000 }), // 100 requests per minute
  [
    param('boardId')
      .isUUID()
      .withMessage('Valid board ID is required'),
    body('name')
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
      const { boardId } = req.params;
      const userId = req.user!.id;
      const { name, description, parentId, position, itemData, assigneeIds } = req.body;

      const item = await ItemService.createItem(
        boardId,
        userId,
        {
          name,
          description,
          parentId,
          position,
          itemData,
          assigneeIds,
        }
      );

      res.status(201).json({
        success: true,
        data: item,
        message: 'Item created successfully',
      });
    } catch (error) {
      Logger.error('Create item failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

// ============================================================================
// BOARD MEMBER MANAGEMENT
// ============================================================================

/**
 * @route   GET /api/boards/:boardId/members
 * @desc    Get board members
 * @access  Private
 */
router.get(
  '/:boardId/members',
  [
    param('boardId')
      .isUUID()
      .withMessage('Valid board ID is required'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { boardId } = req.params;
      const userId = req.user!.id;

      const board = await BoardService.getBoard(boardId, userId);

      res.json({
        success: true,
        data: board.members,
      });
    } catch (error) {
      Logger.error('Get board members failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   POST /api/boards/:boardId/members
 * @desc    Add board member
 * @access  Private
 */
router.post(
  '/:boardId/members',
  rateLimit({ max: 50, windowMs: 60000 }), // 50 requests per minute
  [
    param('boardId')
      .isUUID()
      .withMessage('Valid board ID is required'),
    body('userId')
      .isUUID()
      .withMessage('Valid user ID is required'),
    body('role')
      .optional()
      .isIn(['owner', 'admin', 'member', 'viewer'])
      .withMessage('Invalid role'),
    body('customPermissions')
      .optional()
      .isObject()
      .withMessage('Custom permissions must be an object'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { boardId } = req.params;
      const userId = req.user!.id;
      const { userId: memberUserId, role = 'member', customPermissions } = req.body;

      const member = await BoardService.addBoardMember(
        boardId,
        userId,
        memberUserId,
        role,
        customPermissions
      );

      res.status(201).json({
        success: true,
        data: member,
        message: 'Member added successfully',
      });
    } catch (error) {
      Logger.error('Add board member failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   PUT /api/boards/:boardId/members/:memberUserId
 * @desc    Update board member
 * @access  Private
 */
router.put(
  '/:boardId/members/:memberUserId',
  rateLimit({ max: 50, windowMs: 60000 }), // 50 requests per minute
  [
    param('boardId')
      .isUUID()
      .withMessage('Valid board ID is required'),
    param('memberUserId')
      .isUUID()
      .withMessage('Valid member user ID is required'),
    body('role')
      .optional()
      .isIn(['owner', 'admin', 'member', 'viewer'])
      .withMessage('Invalid role'),
    body('customPermissions')
      .optional()
      .isObject()
      .withMessage('Custom permissions must be an object'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { boardId, memberUserId } = req.params;
      const userId = req.user!.id;
      const { role, customPermissions } = req.body;

      const member = await BoardService.updateBoardMember(
        boardId,
        userId,
        memberUserId,
        role,
        customPermissions
      );

      res.json({
        success: true,
        data: member,
        message: 'Member updated successfully',
      });
    } catch (error) {
      Logger.error('Update board member failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   DELETE /api/boards/:boardId/members/:memberUserId
 * @desc    Remove board member
 * @access  Private
 */
router.delete(
  '/:boardId/members/:memberUserId',
  rateLimit({ max: 50, windowMs: 60000 }), // 50 requests per minute
  [
    param('boardId')
      .isUUID()
      .withMessage('Valid board ID is required'),
    param('memberUserId')
      .isUUID()
      .withMessage('Valid member user ID is required'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { boardId, memberUserId } = req.params;
      const userId = req.user!.id;

      await BoardService.removeBoardMember(boardId, userId, memberUserId);

      res.json({
        success: true,
        message: 'Member removed successfully',
      });
    } catch (error) {
      Logger.error('Remove board member failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

// ============================================================================
// BOARD COLUMN MANAGEMENT
// ============================================================================

/**
 * @route   POST /api/boards/:boardId/columns
 * @desc    Create board column
 * @access  Private
 */
router.post(
  '/:boardId/columns',
  rateLimit({ max: 50, windowMs: 60000 }), // 50 requests per minute
  [
    param('boardId')
      .isUUID()
      .withMessage('Valid board ID is required'),
    body('name')
      .trim()
      .isLength({ min: 1, max: 50 })
      .withMessage('Column name must be between 1 and 50 characters'),
    body('color')
      .optional()
      .matches(/^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/)
      .withMessage('Color must be a valid hex color'),
    body('position')
      .optional()
      .isNumeric()
      .withMessage('Position must be a number'),
    body('settings')
      .optional()
      .isObject()
      .withMessage('Settings must be an object'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { boardId } = req.params;
      const userId = req.user!.id;
      const { name, color, position, settings } = req.body;

      const column = await BoardService.createColumn(
        boardId,
        userId,
        {
          name,
          color,
          position,
          settings,
        }
      );

      res.status(201).json({
        success: true,
        data: column,
        message: 'Column created successfully',
      });
    } catch (error) {
      Logger.error('Create board column failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   PUT /api/boards/:boardId/columns/:columnId
 * @desc    Update board column
 * @access  Private
 */
router.put(
  '/:boardId/columns/:columnId',
  rateLimit({ max: 100, windowMs: 60000 }), // 100 requests per minute
  [
    param('boardId')
      .isUUID()
      .withMessage('Valid board ID is required'),
    param('columnId')
      .isUUID()
      .withMessage('Valid column ID is required'),
    body('name')
      .optional()
      .trim()
      .isLength({ min: 1, max: 50 })
      .withMessage('Column name must be between 1 and 50 characters'),
    body('color')
      .optional()
      .matches(/^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/)
      .withMessage('Color must be a valid hex color'),
    body('settings')
      .optional()
      .isObject()
      .withMessage('Settings must be an object'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { columnId } = req.params;
      const userId = req.user!.id;
      const updateData = req.body;

      const column = await BoardService.updateColumn(columnId, userId, updateData);

      res.json({
        success: true,
        data: column,
        message: 'Column updated successfully',
      });
    } catch (error) {
      Logger.error('Update board column failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   DELETE /api/boards/:boardId/columns/:columnId
 * @desc    Delete board column
 * @access  Private
 */
router.delete(
  '/:boardId/columns/:columnId',
  rateLimit({ max: 20, windowMs: 60000 }), // 20 requests per minute
  [
    param('boardId')
      .isUUID()
      .withMessage('Valid board ID is required'),
    param('columnId')
      .isUUID()
      .withMessage('Valid column ID is required'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { columnId } = req.params;
      const userId = req.user!.id;

      await BoardService.deleteColumn(columnId, userId);

      res.json({
        success: true,
        message: 'Column deleted successfully',
      });
    } catch (error) {
      Logger.error('Delete board column failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

/**
 * @route   PUT /api/boards/:boardId/columns/reorder
 * @desc    Reorder board columns
 * @access  Private
 */
router.put(
  '/:boardId/columns/reorder',
  rateLimit({ max: 50, windowMs: 60000 }), // 50 requests per minute
  [
    param('boardId')
      .isUUID()
      .withMessage('Valid board ID is required'),
    body('columnOrders')
      .isArray({ min: 1 })
      .withMessage('Column orders must be a non-empty array'),
    body('columnOrders.*.id')
      .isUUID()
      .withMessage('Column ID must be a valid UUID'),
    body('columnOrders.*.position')
      .isNumeric()
      .withMessage('Position must be a number'),
    handleValidationErrors,
  ],
  async (req, res) => {
    try {
      const { boardId } = req.params;
      const userId = req.user!.id;
      const { columnOrders } = req.body;

      const columns = await BoardService.reorderColumns(boardId, userId, columnOrders);

      res.json({
        success: true,
        data: columns,
        message: 'Columns reordered successfully',
      });
    } catch (error) {
      Logger.error('Reorder board columns failed', error as Error);
      res.status(400).json({
        success: false,
        message: (error as Error).message,
      });
    }
  }
);

export default router;