import { Router } from 'express';
import { OrganizationService } from '@/services/organization.service';
import { validate } from '@/middleware/validation';
import {
  authenticateToken,
  organizationContext,
  requirePermissions,
  requireRole,
  rateLimit,
} from '@/middleware/auth';
import { Logger } from '@/config/logger';
import {
  createOrganizationSchema,
  updateOrganizationSchema,
  inviteMemberSchema,
  paginationSchema,
  uuidSchema,
} from '@/middleware/express-validation';
import { AuthenticatedRequest } from '@/types';

const router = Router();

/**
 * @route   GET /api/v1/organizations
 * @desc    Get user's organizations
 * @access  Private
 */
router.get(
  '/',
  authenticateToken,
  validate(paginationSchema, 'query'),
  async (req: AuthenticatedRequest, res) => {
    try {
      const { page, limit } = req.query as any;
      const result = await OrganizationService.getUserOrganizations(
        req.user!.id,
        page,
        limit
      );

      res.json({
        data: result.data,
        meta: { pagination: result.meta },
      });
    } catch (error) {
      Logger.error('Failed to get user organizations', error as Error);

      res.status(500).json({
        error: {
          type: 'get_organizations_failed',
          message: 'Failed to get organizations',
        },
      });
    }
  }
);

/**
 * @route   POST /api/v1/organizations
 * @desc    Create a new organization
 * @access  Private
 */
router.post(
  '/',
  authenticateToken,
  rateLimit(5, 60 * 60 * 1000), // 5 organizations per hour
  validate(createOrganizationSchema),
  async (req: AuthenticatedRequest, res) => {
    try {
      const organization = await OrganizationService.create(req.body, req.user!.id);

      res.status(201).json({
        data: { organization },
      });
    } catch (error) {
      Logger.error('Organization creation failed', error as Error);

      res.status(400).json({
        error: {
          type: 'organization_creation_failed',
          message: error instanceof Error ? error.message : 'Failed to create organization',
        },
      });
    }
  }
);

/**
 * @route   GET /api/v1/organizations/:organizationId
 * @desc    Get organization details
 * @access  Private
 */
router.get(
  '/:organizationId',
  authenticateToken,
  organizationContext(),
  requirePermissions('org:read'),
  validate({ organizationId: uuidSchema }, 'params'),
  async (req: AuthenticatedRequest, res) => {
    try {
      const { organizationId } = req.params;
      const includeMembers = req.query.include?.includes('members');
      const includeWorkspaces = req.query.include?.includes('workspaces');

      const organization = await OrganizationService.getById(
        organizationId,
        includeMembers,
        includeWorkspaces
      );

      if (!organization) {
        return res.status(404).json({
          error: {
            type: 'not_found',
            message: 'Organization not found',
          },
        });
      }

      res.json({
        data: { organization },
      });
    } catch (error) {
      Logger.error('Failed to get organization', error as Error);

      res.status(500).json({
        error: {
          type: 'get_organization_failed',
          message: 'Failed to get organization',
        },
      });
    }
  }
);

/**
 * @route   PUT /api/v1/organizations/:organizationId
 * @desc    Update organization
 * @access  Private
 */
router.put(
  '/:organizationId',
  authenticateToken,
  organizationContext(),
  requirePermissions('org:write'),
  validate({ organizationId: uuidSchema }, 'params'),
  validate(updateOrganizationSchema),
  async (req: AuthenticatedRequest, res) => {
    try {
      const { organizationId } = req.params;
      const organization = await OrganizationService.update(organizationId, req.body);

      res.json({
        data: { organization },
      });
    } catch (error) {
      Logger.error('Organization update failed', error as Error);

      res.status(400).json({
        error: {
          type: 'organization_update_failed',
          message: error instanceof Error ? error.message : 'Failed to update organization',
        },
      });
    }
  }
);

/**
 * @route   DELETE /api/v1/organizations/:organizationId
 * @desc    Delete organization
 * @access  Private
 */
router.delete(
  '/:organizationId',
  authenticateToken,
  organizationContext(),
  requireRole('owner'),
  validate({ organizationId: uuidSchema }, 'params'),
  async (req: AuthenticatedRequest, res) => {
    try {
      const { organizationId } = req.params;
      await OrganizationService.delete(organizationId);

      res.status(204).send();
    } catch (error) {
      Logger.error('Organization deletion failed', error as Error);

      res.status(500).json({
        error: {
          type: 'organization_deletion_failed',
          message: 'Failed to delete organization',
        },
      });
    }
  }
);

/**
 * @route   GET /api/v1/organizations/:organizationId/members
 * @desc    Get organization members
 * @access  Private
 */
router.get(
  '/:organizationId/members',
  authenticateToken,
  organizationContext(),
  requirePermissions('org:read'),
  validate({ organizationId: uuidSchema }, 'params'),
  validate(paginationSchema, 'query'),
  async (req: AuthenticatedRequest, res) => {
    try {
      const { organizationId } = req.params;
      const { page, limit } = req.query as any;

      const result = await OrganizationService.getMembers(organizationId, page, limit);

      res.json({
        data: result.data,
        meta: { pagination: result.meta },
      });
    } catch (error) {
      Logger.error('Failed to get organization members', error as Error);

      res.status(500).json({
        error: {
          type: 'get_members_failed',
          message: 'Failed to get organization members',
        },
      });
    }
  }
);

/**
 * @route   POST /api/v1/organizations/:organizationId/members
 * @desc    Invite member to organization
 * @access  Private
 */
router.post(
  '/:organizationId/members',
  authenticateToken,
  organizationContext(),
  requirePermissions('user:invite'),
  validate({ organizationId: uuidSchema }, 'params'),
  validate(inviteMemberSchema),
  async (req: AuthenticatedRequest, res) => {
    try {
      const { organizationId } = req.params;
      const { email, role } = req.body;

      const membership = await OrganizationService.inviteMember(
        organizationId,
        email,
        role,
        req.user!.id
      );

      res.status(201).json({
        data: { membership },
      });
    } catch (error) {
      Logger.error('Member invitation failed', error as Error);

      res.status(400).json({
        error: {
          type: 'member_invitation_failed',
          message: error instanceof Error ? error.message : 'Failed to invite member',
        },
      });
    }
  }
);

/**
 * @route   PUT /api/v1/organizations/:organizationId/members/:userId
 * @desc    Update member role
 * @access  Private
 */
router.put(
  '/:organizationId/members/:userId',
  authenticateToken,
  organizationContext(),
  requirePermissions('user:manage'),
  validate({ organizationId: uuidSchema, userId: uuidSchema }, 'params'),
  async (req: AuthenticatedRequest, res) => {
    try {
      const { organizationId, userId } = req.params;
      const { role } = req.body;

      if (!role || !['owner', 'admin', 'member'].includes(role)) {
        return res.status(400).json({
          error: {
            type: 'validation_error',
            message: 'Valid role is required (owner, admin, member)',
          },
        });
      }

      const membership = await OrganizationService.updateMemberRole(
        organizationId,
        userId,
        role
      );

      res.json({
        data: { membership },
      });
    } catch (error) {
      Logger.error('Member role update failed', error as Error);

      res.status(400).json({
        error: {
          type: 'member_role_update_failed',
          message: error instanceof Error ? error.message : 'Failed to update member role',
        },
      });
    }
  }
);

/**
 * @route   DELETE /api/v1/organizations/:organizationId/members/:userId
 * @desc    Remove member from organization
 * @access  Private
 */
router.delete(
  '/:organizationId/members/:userId',
  authenticateToken,
  organizationContext(),
  requirePermissions('user:manage'),
  validate({ organizationId: uuidSchema, userId: uuidSchema }, 'params'),
  async (req: AuthenticatedRequest, res) => {
    try {
      const { organizationId, userId } = req.params;

      await OrganizationService.removeMember(organizationId, userId);

      res.status(204).send();
    } catch (error) {
      Logger.error('Member removal failed', error as Error);

      res.status(400).json({
        error: {
          type: 'member_removal_failed',
          message: error instanceof Error ? error.message : 'Failed to remove member',
        },
      });
    }
  }
);

/**
 * @route   GET /api/v1/organizations/:organizationId/stats
 * @desc    Get organization statistics
 * @access  Private
 */
router.get(
  '/:organizationId/stats',
  authenticateToken,
  organizationContext(),
  requirePermissions('analytics:read'),
  validate({ organizationId: uuidSchema }, 'params'),
  async (req: AuthenticatedRequest, res) => {
    try {
      const { organizationId } = req.params;
      const stats = await OrganizationService.getStatistics(organizationId);

      res.json({
        data: { stats },
      });
    } catch (error) {
      Logger.error('Failed to get organization statistics', error as Error);

      res.status(500).json({
        error: {
          type: 'get_stats_failed',
          message: 'Failed to get organization statistics',
        },
      });
    }
  }
);

export default router;