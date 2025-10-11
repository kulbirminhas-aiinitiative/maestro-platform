import { Router } from 'express';
import { body, param, query } from 'express-validator';
import { AuthenticatedRequest } from '@/types';
import { WorkspaceService } from '@/services/workspace.service';
import { authenticateToken } from '@/middleware/auth';
import { validationMiddleware } from '@/middleware/express-validation';
import { Logger } from '@/config/logger';

const router = Router();

// Apply authentication to all routes
router.use(authenticateToken);

// ============================================================================
// WORKSPACE ROUTES
// ============================================================================

/**
 * GET /workspaces/:organizationId
 * Get all workspaces for an organization
 */
router.get(
  '/:organizationId',
  [
    param('organizationId').isUUID().withMessage('Valid organization ID required'),
    query('limit').optional().isInt({ min: 1, max: 100 }).withMessage('Limit must be between 1 and 100'),
    query('cursor').optional().isString(),
    query('search').optional().isString().trim(),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { organizationId } = req.params;
      const { limit, cursor, search } = req.query;

      const result = await WorkspaceService.getWorkspaces(
        organizationId,
        {
          limit: limit ? parseInt(limit as string) : undefined,
          cursor: cursor as string,
          search: search as string,
        }
      );

      res.json({
        data: result.data,
        meta: result.pagination,
      });
    } catch (error) {
      Logger.error('Get workspaces failed', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to get workspaces',
        },
      });
    }
  }
);

/**
 * GET /workspaces/workspace/:workspaceId
 * Get workspace by ID
 */
router.get(
  '/workspace/:workspaceId',
  [
    param('workspaceId').isUUID().withMessage('Valid workspace ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { workspaceId } = req.params;
      const userId = req.user!.id;

      const workspace = await WorkspaceService.getWorkspaceById(workspaceId, userId);

      res.json({
        data: workspace,
      });
    } catch (error) {
      Logger.error('Get workspace failed', error as Error);

      if ((error as Error).message === 'Workspace not found') {
        res.status(404).json({
          error: {
            type: 'not_found',
            message: 'Workspace not found',
          },
        });
      } else {
        res.status(500).json({
          error: {
            type: 'internal_error',
            message: 'Failed to get workspace',
          },
        });
      }
    }
  }
);

/**
 * POST /workspaces
 * Create a new workspace
 */
router.post(
  '/',
  [
    body('name').isString().trim().isLength({ min: 1, max: 100 }).withMessage('Name is required and must be between 1-100 characters'),
    body('description').optional().isString().trim().isLength({ max: 500 }).withMessage('Description must be less than 500 characters'),
    body('organizationId').isUUID().withMessage('Valid organization ID required'),
    body('color').optional().isString().matches(/^#[0-9A-Fa-f]{6}$/).withMessage('Color must be a valid hex color'),
    body('isPrivate').optional().isBoolean().withMessage('isPrivate must be a boolean'),
    body('settings').optional().isObject().withMessage('Settings must be an object'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const userId = req.user!.id;
      const workspaceData = req.body;

      const workspace = await WorkspaceService.createWorkspace(workspaceData, userId);

      res.status(201).json({
        data: workspace,
      });
    } catch (error) {
      Logger.error('Create workspace failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('permission')) {
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
            message: 'Failed to create workspace',
          },
        });
      }
    }
  }
);

/**
 * PUT /workspaces/:workspaceId
 * Update workspace
 */
router.put(
  '/:workspaceId',
  [
    param('workspaceId').isUUID().withMessage('Valid workspace ID required'),
    body('name').optional().isString().trim().isLength({ min: 1, max: 100 }).withMessage('Name must be between 1-100 characters'),
    body('description').optional().isString().trim().isLength({ max: 500 }).withMessage('Description must be less than 500 characters'),
    body('color').optional().isString().matches(/^#[0-9A-Fa-f]{6}$/).withMessage('Color must be a valid hex color'),
    body('isPrivate').optional().isBoolean().withMessage('isPrivate must be a boolean'),
    body('settings').optional().isObject().withMessage('Settings must be an object'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { workspaceId } = req.params;
      const userId = req.user!.id;
      const updateData = req.body;

      const workspace = await WorkspaceService.updateWorkspace(workspaceId, updateData, userId);

      res.json({
        data: workspace,
      });
    } catch (error) {
      Logger.error('Update workspace failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('permission')) {
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
            message: 'Failed to update workspace',
          },
        });
      }
    }
  }
);

/**
 * DELETE /workspaces/:workspaceId
 * Delete workspace
 */
router.delete(
  '/:workspaceId',
  [
    param('workspaceId').isUUID().withMessage('Valid workspace ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { workspaceId } = req.params;
      const userId = req.user!.id;

      await WorkspaceService.deleteWorkspace(workspaceId, userId);

      res.status(204).send();
    } catch (error) {
      Logger.error('Delete workspace failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('permission')) {
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
            message: 'Failed to delete workspace',
          },
        });
      }
    }
  }
);

// ============================================================================
// WORKSPACE MEMBER ROUTES
// ============================================================================

/**
 * POST /workspaces/:workspaceId/members
 * Add member to workspace
 */
router.post(
  '/:workspaceId/members',
  [
    param('workspaceId').isUUID().withMessage('Valid workspace ID required'),
    body('email').isEmail().normalizeEmail().withMessage('Valid email address required'),
    body('role').isIn(['member', 'admin']).withMessage('Role must be member or admin'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { workspaceId } = req.params;
      const { email, role } = req.body;
      const addedBy = req.user!.id;

      await WorkspaceService.addMember(workspaceId, req.user!.id, email, role, addedBy);

      res.status(201).json({
        data: {
          message: 'Member added successfully',
        },
      });
    } catch (error) {
      Logger.error('Add workspace member failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('permission')) {
        res.status(403).json({
          error: {
            type: 'forbidden',
            message: errorMessage,
          },
        });
      } else if (errorMessage.includes('not found')) {
        res.status(404).json({
          error: {
            type: 'not_found',
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
 * DELETE /workspaces/:workspaceId/members/:memberId
 * Remove member from workspace
 */
router.delete(
  '/:workspaceId/members/:memberId',
  [
    param('workspaceId').isUUID().withMessage('Valid workspace ID required'),
    param('memberId').isUUID().withMessage('Valid member ID required'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { workspaceId, memberId } = req.params;
      const removedBy = req.user!.id;

      await WorkspaceService.removeMember(workspaceId, memberId, removedBy);

      res.status(204).send();
    } catch (error) {
      Logger.error('Remove workspace member failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('permission')) {
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
            message: 'Failed to remove member',
          },
        });
      }
    }
  }
);

/**
 * PUT /workspaces/:workspaceId/members/:memberId/role
 * Update member role
 */
router.put(
  '/:workspaceId/members/:memberId/role',
  [
    param('workspaceId').isUUID().withMessage('Valid workspace ID required'),
    param('memberId').isUUID().withMessage('Valid member ID required'),
    body('role').isIn(['member', 'admin']).withMessage('Role must be member or admin'),
    validationMiddleware,
  ],
  async (req: AuthenticatedRequest, res) => {
    try {
      const { workspaceId, memberId } = req.params;
      const { role } = req.body;
      const updatedBy = req.user!.id;

      await WorkspaceService.updateMemberRole(workspaceId, memberId, role, updatedBy);

      res.json({
        data: {
          message: 'Member role updated successfully',
        },
      });
    } catch (error) {
      Logger.error('Update workspace member role failed', error as Error);

      const errorMessage = (error as Error).message;
      if (errorMessage.includes('permission')) {
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
            message: 'Failed to update member role',
          },
        });
      }
    }
  }
);

export default router;