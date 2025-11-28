import { prisma } from '@/config/database';
import { RedisService } from '@/config/redis';
import { Logger } from '@/config/logger';
import {
  CreateOrganizationData,
  PaginatedResult,
  PaginationMeta,
} from '@/types';
import { Organization, OrganizationMember, User, Workspace } from '@prisma/client';

type OrganizationWithRelations = Organization & {
  members?: Array<OrganizationMember & { user: User }>;
  workspaces?: Workspace[];
  _count?: {
    members: number;
    workspaces: number;
  };
};

export class OrganizationService {
  /**
   * Create a new organization
   */
  static async create(
    data: CreateOrganizationData,
    creatorId: string
  ): Promise<OrganizationWithRelations> {
    try {
      // Check if slug is already taken
      const existingOrg = await prisma.organization.findUnique({
        where: { slug: data.slug },
      });

      if (existingOrg) {
        throw new Error('Organization slug is already taken');
      }

      // Create organization with creator as owner
      const organization = await prisma.organization.create({
        data: {
          ...data,
          members: {
            create: {
              userId: creatorId,
              role: 'owner',
              status: 'active',
              joinedAt: new Date(),
            },
          },
        },
        include: {
          members: {
            include: {
              user: true,
            },
          },
          _count: {
            select: {
              members: true,
              workspaces: true,
            },
          },
        },
      });

      Logger.business(`Organization created: ${organization.name}`, {
        organizationId: organization.id,
        creatorId,
      });

      return organization;
    } catch (error) {
      Logger.error('Organization creation failed', error as Error);
      throw error;
    }
  }

  /**
   * Get organization by ID
   */
  static async getById(
    organizationId: string,
    includeMembers = false,
    includeWorkspaces = false
  ): Promise<OrganizationWithRelations | null> {
    try {
      const organization = await prisma.organization.findUnique({
        where: { id: organizationId, deletedAt: null },
        include: {
          members: includeMembers
            ? {
                include: {
                  user: true,
                },
                where: {
                  status: 'active',
                },
              }
            : false,
          workspaces: includeWorkspaces
            ? {
                where: {
                  deletedAt: null,
                },
                orderBy: {
                  name: 'asc',
                },
              }
            : false,
          _count: {
            select: {
              members: true,
              workspaces: true,
            },
          },
        },
      });

      return organization;
    } catch (error) {
      Logger.error('Failed to get organization', error as Error);
      throw error;
    }
  }

  /**
   * Get organizations for a user
   */
  static async getUserOrganizations(
    userId: string,
    page = 1,
    limit = 20
  ): Promise<PaginatedResult<OrganizationWithRelations>> {
    try {
      const offset = (page - 1) * limit;

      const [organizations, total] = await Promise.all([
        prisma.organization.findMany({
          where: {
            deletedAt: null,
            members: {
              some: {
                userId,
                status: 'active',
              },
            },
          },
          include: {
            _count: {
              select: {
                members: true,
                workspaces: true,
              },
            },
          },
          orderBy: {
            name: 'asc',
          },
          skip: offset,
          take: limit,
        }),
        prisma.organization.count({
          where: {
            deletedAt: null,
            members: {
              some: {
                userId,
                status: 'active',
              },
            },
          },
        }),
      ]);

      const meta: PaginationMeta = {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
        hasNext: page * limit < total,
        hasPrev: page > 1,
      };

      return { data: organizations, meta };
    } catch (error) {
      Logger.error('Failed to get user organizations', error as Error);
      throw error;
    }
  }

  /**
   * Update organization
   */
  static async update(
    organizationId: string,
    data: Partial<CreateOrganizationData>
  ): Promise<OrganizationWithRelations> {
    try {
      // If updating slug, check if it's available
      if (data.slug) {
        const existingOrg = await prisma.organization.findFirst({
          where: {
            slug: data.slug,
            id: { not: organizationId },
          },
        });

        if (existingOrg) {
          throw new Error('Organization slug is already taken');
        }
      }

      const organization = await prisma.organization.update({
        where: { id: organizationId },
        data,
        include: {
          _count: {
            select: {
              members: true,
              workspaces: true,
            },
          },
        },
      });

      // Invalidate related caches
      await this.invalidateCaches(organizationId);

      Logger.business(`Organization updated: ${organization.name}`, {
        organizationId,
      });

      return organization;
    } catch (error) {
      Logger.error('Organization update failed', error as Error);
      throw error;
    }
  }

  /**
   * Delete organization (soft delete)
   */
  static async delete(organizationId: string): Promise<void> {
    try {
      await prisma.organization.update({
        where: { id: organizationId },
        data: { deletedAt: new Date() },
      });

      // Invalidate related caches
      await this.invalidateCaches(organizationId);

      Logger.business(`Organization deleted`, { organizationId });
    } catch (error) {
      Logger.error('Organization deletion failed', error as Error);
      throw error;
    }
  }

  /**
   * Invite user to organization
   */
  static async inviteMember(
    organizationId: string,
    email: string,
    role: string,
    invitedBy: string
  ): Promise<OrganizationMember> {
    try {
      // Find or create user
      let user = await prisma.user.findUnique({
        where: { email: email.toLowerCase() },
      });

      if (!user) {
        user = await prisma.user.create({
          data: {
            email: email.toLowerCase(),
            emailVerified: false,
          },
        });
      }

      // Check if user is already a member
      const existingMembership = await prisma.organizationMember.findUnique({
        where: {
          organizationId_userId: {
            organizationId,
            userId: user.id,
          },
        },
      });

      if (existingMembership) {
        if (existingMembership.status === 'active') {
          throw new Error('User is already a member of this organization');
        } else {
          // Reactivate membership
          return await prisma.organizationMember.update({
            where: { id: existingMembership.id },
            data: {
              status: 'active',
              role,
              invitedBy,
              invitedAt: new Date(),
            },
          });
        }
      }

      // Create membership
      const membership = await prisma.organizationMember.create({
        data: {
          organizationId,
          userId: user.id,
          role,
          status: user.emailVerified ? 'active' : 'invited',
          invitedBy,
          invitedAt: new Date(),
          joinedAt: user.emailVerified ? new Date() : null,
        },
      });

      // TODO: Send invitation email

      Logger.business(`User invited to organization`, {
        organizationId,
        userId: user.id,
        email,
        role,
        invitedBy,
      });

      return membership;
    } catch (error) {
      Logger.error('Member invitation failed', error as Error);
      throw error;
    }
  }

  /**
   * Remove member from organization
   */
  static async removeMember(organizationId: string, userId: string): Promise<void> {
    try {
      // Check if user is the only owner
      const ownerCount = await prisma.organizationMember.count({
        where: {
          organizationId,
          role: 'owner',
          status: 'active',
        },
      });

      const memberToRemove = await prisma.organizationMember.findUnique({
        where: {
          organizationId_userId: {
            organizationId,
            userId,
          },
        },
      });

      if (memberToRemove?.role === 'owner' && ownerCount <= 1) {
        throw new Error('Cannot remove the last owner of the organization');
      }

      // Remove membership
      await prisma.organizationMember.delete({
        where: {
          organizationId_userId: {
            organizationId,
            userId,
          },
        },
      });

      // Invalidate user permissions cache
      await RedisService.deleteCachePattern(`permissions:${userId}:${organizationId}`);

      Logger.business(`Member removed from organization`, {
        organizationId,
        userId,
      });
    } catch (error) {
      Logger.error('Member removal failed', error as Error);
      throw error;
    }
  }

  /**
   * Update member role
   */
  static async updateMemberRole(
    organizationId: string,
    userId: string,
    newRole: string
  ): Promise<OrganizationMember> {
    try {
      // Check if downgrading the only owner
      if (newRole !== 'owner') {
        const ownerCount = await prisma.organizationMember.count({
          where: {
            organizationId,
            role: 'owner',
            status: 'active',
          },
        });

        const currentMember = await prisma.organizationMember.findUnique({
          where: {
            organizationId_userId: {
              organizationId,
              userId,
            },
          },
        });

        if (currentMember?.role === 'owner' && ownerCount <= 1) {
          throw new Error('Cannot change role of the last owner');
        }
      }

      const updatedMember = await prisma.organizationMember.update({
        where: {
          organizationId_userId: {
            organizationId,
            userId,
          },
        },
        data: { role: newRole },
      });

      // Invalidate user permissions cache
      await RedisService.deleteCachePattern(`permissions:${userId}:${organizationId}`);

      Logger.business(`Member role updated`, {
        organizationId,
        userId,
        newRole,
      });

      return updatedMember;
    } catch (error) {
      Logger.error('Member role update failed', error as Error);
      throw error;
    }
  }

  /**
   * Get organization members
   */
  static async getMembers(
    organizationId: string,
    page = 1,
    limit = 20
  ): Promise<PaginatedResult<OrganizationMember & { user: User }>> {
    try {
      const offset = (page - 1) * limit;

      const [members, total] = await Promise.all([
        prisma.organizationMember.findMany({
          where: {
            organizationId,
            status: 'active',
          },
          include: {
            user: true,
          },
          orderBy: [
            { role: 'asc' }, // owners first
            { user: { firstName: 'asc' } },
          ],
          skip: offset,
          take: limit,
        }),
        prisma.organizationMember.count({
          where: {
            organizationId,
            status: 'active',
          },
        }),
      ]);

      const meta: PaginationMeta = {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
        hasNext: page * limit < total,
        hasPrev: page > 1,
      };

      return { data: members, meta };
    } catch (error) {
      Logger.error('Failed to get organization members', error as Error);
      throw error;
    }
  }

  /**
   * Check if user has access to organization
   */
  static async hasAccess(organizationId: string, userId: string): Promise<boolean> {
    try {
      const membership = await prisma.organizationMember.findUnique({
        where: {
          organizationId_userId: {
            organizationId,
            userId,
          },
        },
      });

      return !!membership && membership.status === 'active';
    } catch (error) {
      Logger.error('Failed to check organization access', error as Error);
      return false;
    }
  }

  /**
   * Get organization statistics
   */
  static async getStatistics(organizationId: string): Promise<{
    totalMembers: number;
    totalWorkspaces: number;
    totalBoards: number;
    totalItems: number;
    activeUsers30d: number;
  }> {
    try {
      const [stats] = await prisma.$queryRaw<Array<{
        totalMembers: bigint;
        totalWorkspaces: bigint;
        totalBoards: bigint;
        totalItems: bigint;
        activeUsers30d: bigint;
      }>>`
        SELECT
          COUNT(DISTINCT om.user_id) as "totalMembers",
          COUNT(DISTINCT w.id) as "totalWorkspaces",
          COUNT(DISTINCT b.id) as "totalBoards",
          COUNT(DISTINCT i.id) as "totalItems",
          COUNT(DISTINCT CASE
            WHEN al.created_at >= NOW() - INTERVAL '30 days'
            THEN al.user_id
          END) as "activeUsers30d"
        FROM organizations o
        LEFT JOIN organization_members om ON o.id = om.organization_id AND om.status = 'active'
        LEFT JOIN workspaces w ON o.id = w.organization_id AND w.deleted_at IS NULL
        LEFT JOIN boards b ON w.id = b.workspace_id AND b.deleted_at IS NULL
        LEFT JOIN items i ON b.id = i.board_id AND i.deleted_at IS NULL
        LEFT JOIN activity_log al ON o.id = al.organization_id
        WHERE o.id = ${organizationId}
      `;

      return {
        totalMembers: Number(stats.totalMembers),
        totalWorkspaces: Number(stats.totalWorkspaces),
        totalBoards: Number(stats.totalBoards),
        totalItems: Number(stats.totalItems),
        activeUsers30d: Number(stats.activeUsers30d),
      };
    } catch (error) {
      Logger.error('Failed to get organization statistics', error as Error);
      throw error;
    }
  }

  // ============================================================================
  // PRIVATE METHODS
  // ============================================================================

  /**
   * Invalidate related caches
   */
  private static async invalidateCaches(organizationId: string): Promise<void> {
    await Promise.all([
      RedisService.deleteCachePattern(`org:${organizationId}:*`),
      RedisService.deleteCachePattern(`permissions:*:${organizationId}`),
    ]);
  }
}