import { Router } from 'express';
import { body, param, query } from 'express-validator';
import { AuthenticatedRequest } from '@/types';
import { CommentService } from '@/services/comment.service';
import { authenticateToken } from '@/middleware/auth';
import { validationMiddleware } from '@/middleware/express-validation';
import { Logger } from '@/config/logger';

const router = Router();

// Apply authentication to all routes
router.use(authenticateToken);

// ============================================================================
// COMMENT ROUTES
// ============================================================================

/**
 * GET /comments/item/:itemId
 * Get all comments for an item
 */
router.get(
  '/item/:itemId',
  [
    param('itemId').isUUID().withMessage('Valid item ID required'),
    query('page').optional().isInt({ min: 1 }).withMessage('Page must be a positive integer'),
    query('limit').optional().isInt({ min: 1, max: 100 }).withMessage('Limit must be between 1 and 100'),
    query('includeReplies').optional().isBoolean().withMessage('includeReplies must be a boolean'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { itemId } = req.params;
      const { page, limit, includeReplies } = req.query;
      const userId = req.user!.id;

      const result = await CommentService.getByItem(
        itemId,
        userId,
        page ? parseInt(page as string) : 1,
        limit ? parseInt(limit as string) : 20,
        includeReplies === 'true'
      );

      res.json({
        data: result.data,
        meta: result.meta,
      });
    } catch (error) {
      Logger.error('Get item comments failed', error as Error);

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
            message: 'Failed to get comments',
          },
        });
      }
    }
  }
);

/**
 * GET /comments/:commentId
 * Get comment by ID
 */
router.get(
  '/:commentId',
  [
    param('commentId').isUUID().withMessage('Valid comment ID required'),
    query('includeReplies').optional().isBoolean().withMessage('includeReplies must be a boolean'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { commentId } = req.params;
      const { includeReplies } = req.query;
      const userId = req.user!.id;

      const comment = await CommentService.getById(
        commentId,
        userId,
        includeReplies === 'true'
      );

      if (!comment) {
        return res.status(404).json({
          error: {
            type: 'not_found',
            message: 'Comment not found',
          },
        });
      }

      res.json({
        data: comment,
      });
    } catch (error) {
      Logger.error('Get comment failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get comment',
        },
      });
    }
  }
);

/**
 * POST /comments/:itemId
 * Create a new comment on an item
 */
router.post(
  '/:itemId',
  [
    param('itemId').isUUID().withMessage('Valid item ID required'),
    body('content').isString().trim().isLength({ min: 1, max: 2000 }).withMessage('Content is required and must be between 1-2000 characters'),
    body('parentId').optional().isUUID().withMessage('Valid parent comment ID required'),
    body('mentions').optional().isArray().withMessage('Mentions must be an array'),
    body('mentions.*').optional().isUUID().withMessage('Valid user ID required for mentions'),
    body('attachments').optional().isArray().withMessage('Attachments must be an array'),
    body('attachments.*').optional().isString().withMessage('Attachment must be a string'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { itemId } = req.params;
      const userId = req.user!.id;
      const commentData = req.body;

      const comment = await CommentService.create(itemId, commentData, userId);

      res.status(201).json({
        data: comment,
      });
    } catch (error) {
      Logger.error('Create comment failed', error as Error);

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
            message: 'Failed to create comment',
          },
        });
      }
    }
  }
);

/**
 * PUT /comments/:commentId
 * Update a comment
 */
router.put(
  '/:commentId',
  [
    param('commentId').isUUID().withMessage('Valid comment ID required'),
    body('content').isString().trim().isLength({ min: 1, max: 2000 }).withMessage('Content is required and must be between 1-2000 characters'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { commentId } = req.params;
      const { content } = req.body;
      const userId = req.user!.id;

      const comment = await CommentService.update(commentId, content, userId);

      res.json({
        data: comment,
      });
    } catch (error) {
      Logger.error('Update comment failed', error as Error);

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
            message: 'Failed to update comment',
          },
        });
      }
    }
  }
);

/**
 * DELETE /comments/:commentId
 * Delete a comment
 */
router.delete(
  '/:commentId',
  [
    param('commentId').isUUID().withMessage('Valid comment ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { commentId } = req.params;
      const userId = req.user!.id;

      await CommentService.delete(commentId, userId);

      res.status(204).send();
    } catch (error) {
      Logger.error('Delete comment failed', error as Error);

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
            message: 'Failed to delete comment',
          },
        });
      }
    }
  }
);

// ============================================================================
// COMMENT REACTIONS
// ============================================================================

/**
 * POST /comments/:commentId/reactions
 * Add reaction to a comment
 */
router.post(
  '/:commentId/reactions',
  [
    param('commentId').isUUID().withMessage('Valid comment ID required'),
    body('emoji').isString().trim().isLength({ min: 1, max: 10 }).withMessage('Emoji is required and must be between 1-10 characters'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { commentId } = req.params;
      const { emoji } = req.body;
      const userId = req.user!.id;

      await CommentService.addReaction(commentId, emoji, userId);

      res.status(201).json({
        data: {
          message: 'Reaction added successfully',
        },
      });
    } catch (error) {
      Logger.error('Add comment reaction failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('not found') || errorMessage.includes('access denied')) {
        res.status(404).json({
          error: {
            type: 'not_found',
            message: 'Comment not found or access denied',
          },
        });
      } else if (errorMessage.includes('already exists')) {
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
            message: 'Failed to add reaction',
          },
        });
      }
    }
  }
);

/**
 * DELETE /comments/:commentId/reactions/:emoji
 * Remove reaction from a comment
 */
router.delete(
  '/:commentId/reactions/:emoji',
  [
    param('commentId').isUUID().withMessage('Valid comment ID required'),
    param('emoji').isString().trim().isLength({ min: 1, max: 10 }).withMessage('Valid emoji required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { commentId, emoji } = req.params;
      const userId = req.user!.id;

      await CommentService.removeReaction(commentId, decodeURIComponent(emoji), userId);

      res.status(204).send();
    } catch (error) {
      Logger.error('Remove comment reaction failed', error as Error);

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
            message: 'Failed to remove reaction',
          },
        });
      }
    }
  }
);

// ============================================================================
// COMMENT STATISTICS
// ============================================================================

/**
 * GET /comments/item/:itemId/stats
 * Get comment statistics for an item
 */
router.get(
  '/item/:itemId/stats',
  [
    param('itemId').isUUID().withMessage('Valid item ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { itemId } = req.params;

      const stats = await CommentService.getItemCommentStats(itemId);

      res.json({
        data: stats,
      });
    } catch (error) {
      Logger.error('Get comment statistics failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get comment statistics',
        },
      });
    }
  }
);

export default router;