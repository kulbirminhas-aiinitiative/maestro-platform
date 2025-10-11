import { Prisma } from '@prisma/client';
import { prisma } from '@/config/database';
import { Logger } from '@/config/logger';
import { RedisService } from '@/config/redis';
import {
  CreateWorkspaceData,
  UpdateWorkspaceData,
  WorkspaceWithDetails,
  PaginationOptions,
  PaginatedResponse,
} from '@/types';

export class WorkspaceService {
  /**
   * Get all workspaces for an organization
   */
  static async getWorkspaces(
    organizationId: string,
    options: PaginationOptions = {}
  ): Promise<PaginatedResponse<WorkspaceWithDetails>> {
    try {
      const { limit = 20, cursor, search } = options;

      const where: Prisma.WorkspaceWhereInput = {
        organizationId,
        deletedAt: null,
        ...(search && {
          OR: [
            { name: { contains: search, mode: 'insensitive' } },
            { description: { contains: search, mode: 'insensitive' } },
          ],
        }),
      };

      const whereWithCursor = cursor
        ? { ...where, id: { gt: cursor } }
        : where;

      const [workspaces, totalCount] = await Promise.all([
        prisma.workspace.findMany({
          where: whereWithCursor,
          include: {
            organization: true,
            members: {
              include: {
                user: {
                  select: {
                    id: true,
                    email: true,
                    firstName: true,
                    lastName: true,
                    avatarUrl: true,
                  },
                },
              },
            },
            boards: {
              where: { deletedAt: null },
              select: {
                id: true,
                name: true,
                isPrivate: true,
                createdAt: true,
              },
              orderBy: { createdAt: 'desc' },
              take: 5, // Show recent boards
            },
            _count: {
              select: {
                boards: {
                  where: { deletedAt: null },
                },
                members: true,
              },
            },
          },
          orderBy: { createdAt: 'asc' },
          take: limit + 1,
        }),
        cursor ? undefined : prisma.workspace.count({ where }),
      ]);

      const hasMore = workspaces.length > limit;
      const items = hasMore ? workspaces.slice(0, -1) : workspaces;
      const nextCursor = hasMore ? workspaces[workspaces.length - 2].id : null;

      return {
        data: items.map(workspace => ({
          id: workspace.id,
          organizationId: workspace.organizationId,
          name: workspace.name,
          description: workspace.description,
          color: workspace.color,
          isPrivate: workspace.isPrivate,
          settings: workspace.settings as Record<string, any>,
          createdAt: workspace.createdAt,
          updatedAt: workspace.updatedAt,
          organization: {
            id: workspace.organization.id,
            name: workspace.organization.name,
            slug: workspace.organization.slug,
          },
          members: workspace.members.map(member => ({
            id: member.id,
            role: member.role,
            permissions: member.permissions as Record<string, any>,
            user: {
              id: member.user.id,
              email: member.user.email,
              firstName: member.user.firstName,
              lastName: member.user.lastName,
              avatarUrl: member.user.avatarUrl,
            },
            createdAt: member.createdAt,
          })),
          recentBoards: workspace.boards.map(board => ({
            id: board.id,
            name: board.name,
            isPrivate: board.isPrivate,
            createdAt: board.createdAt,
          })),
          stats: {
            boardCount: workspace._count.boards,
            memberCount: workspace._count.members,
          },
        })),
        pagination: {
          nextCursor,
          hasMore,
          totalCount: totalCount || 0,
        },
      };
    } catch (error) {
      Logger.error('Failed to get workspaces', error as Error);
      throw error;
    }
  }

  /**
   * Get workspace by ID
   */
  static async getWorkspaceById(
    workspaceId: string,
    userId: string
  ): Promise<WorkspaceWithDetails> {
    try {
      // Check cache first
      const cacheKey = `workspace:${workspaceId}`;
      const cached = await RedisService.getCache(cacheKey);

      if (cached) {
        Logger.api(`Workspace cache hit: ${workspaceId}`);
        return cached;
      }

      const workspace = await prisma.workspace.findFirst({
        where: {
          id: workspaceId,
          deletedAt: null,
          OR: [
            { isPrivate: false },
            {
              members: {
                some: { userId },
              },
            },
          ],
        },
        include: {
          organization: true,
          members: {
            include: {
              user: {
                select: {
                  id: true,
                  email: true,
                  firstName: true,
                  lastName: true,
                  avatarUrl: true,
                },
              },
            },
          },
          boards: {
            where: { deletedAt: null },
            include: {
              creator: {
                select: {
                  id: true,
                  firstName: true,
                  lastName: true,
                  avatarUrl: true,
                },
              },
              _count: {
                select: {
                  items: {
                    where: { deletedAt: null },
                  },
                  members: true,
                },
              },
            },
            orderBy: { createdAt: 'desc' },
          },
          folders: {
            orderBy: { position: 'asc' },
          },
          _count: {
            select: {
              boards: {
                where: { deletedAt: null },
              },
              members: true,
            },
          },
        },
      });

      if (!workspace) {
        throw new Error('Workspace not found');
      }

      const result: WorkspaceWithDetails = {
        id: workspace.id,
        organizationId: workspace.organizationId,
        name: workspace.name,
        description: workspace.description,
        color: workspace.color,
        isPrivate: workspace.isPrivate,
        settings: workspace.settings as Record<string, any>,
        createdAt: workspace.createdAt,
        updatedAt: workspace.updatedAt,
        organization: {
          id: workspace.organization.id,
          name: workspace.organization.name,
          slug: workspace.organization.slug,
        },
        members: workspace.members.map(member => ({
          id: member.id,
          role: member.role,
          permissions: member.permissions as Record<string, any>,
          user: {
            id: member.user.id,
            email: member.user.email,
            firstName: member.user.firstName,
            lastName: member.user.lastName,
            avatarUrl: member.user.avatarUrl,
          },
          createdAt: member.createdAt,
        })),
        boards: workspace.boards.map(board => ({
          id: board.id,
          name: board.name,
          description: board.description,
          isPrivate: board.isPrivate,
          createdAt: board.createdAt,
          creator: {
            id: board.creator.id,
            firstName: board.creator.firstName,
            lastName: board.creator.lastName,
            avatarUrl: board.creator.avatarUrl,
          },
          stats: {
            itemCount: board._count.items,
            memberCount: board._count.members,
          },
        })),
        folders: workspace.folders.map(folder => ({
          id: folder.id,
          name: folder.name,
          color: folder.color,
          position: folder.position,
        })),
        stats: {
          boardCount: workspace._count.boards,
          memberCount: workspace._count.members,
        },
      };

      // Cache for 30 minutes
      await RedisService.setCache(cacheKey, result, 1800);

      return result;
    } catch (error) {
      Logger.error('Failed to get workspace', error as Error);
      throw error;
    }
  }

  /**
   * Create a new workspace
   */
  static async createWorkspace(
    data: CreateWorkspaceData,
    userId: string
  ): Promise<WorkspaceWithDetails> {
    try {
      // Check if user has permission to create workspace in organization
      const membership = await prisma.organizationMember.findUnique({
        where: {
          organizationId_userId: {
            organizationId: data.organizationId,
            userId,
          },
        },
      });

      if (!membership || !['owner', 'admin'].includes(membership.role)) {
        throw new Error('Insufficient permissions to create workspace');
      }

      const workspace = await prisma.workspace.create({
        data: {
          organizationId: data.organizationId,
          name: data.name,
          description: data.description,
          color: data.color || '#6B7280',
          isPrivate: data.isPrivate || false,
          settings: data.settings || {},
          members: {
            create: {
              userId,
              role: 'admin',
            },
          },
        },
        include: {
          organization: true,
          members: {
            include: {
              user: {
                select: {
                  id: true,
                  email: true,
                  firstName: true,
                  lastName: true,
                  avatarUrl: true,
                },
              },
            },
          },
        },
      });

      Logger.api(`Workspace created: ${workspace.name}`, {
        workspaceId: workspace.id,
        userId,
      });

      // Invalidate organization cache
      await RedisService.deleteCache(`organization:${data.organizationId}`);

      return {
        id: workspace.id,
        organizationId: workspace.organizationId,
        name: workspace.name,
        description: workspace.description,
        color: workspace.color,
        isPrivate: workspace.isPrivate,
        settings: workspace.settings as Record<string, any>,
        createdAt: workspace.createdAt,
        updatedAt: workspace.updatedAt,
        organization: {
          id: workspace.organization.id,
          name: workspace.organization.name,
          slug: workspace.organization.slug,
        },
        members: workspace.members.map(member => ({
          id: member.id,
          role: member.role,
          permissions: member.permissions as Record<string, any>,
          user: {
            id: member.user.id,
            email: member.user.email,
            firstName: member.user.firstName,
            lastName: member.user.lastName,
            avatarUrl: member.user.avatarUrl,
          },
          createdAt: member.createdAt,
        })),
        boards: [],
        folders: [],
        stats: {
          boardCount: 0,
          memberCount: 1,
        },
      };
    } catch (error) {
      Logger.error('Failed to create workspace', error as Error);
      throw error;
    }
  }

  /**
   * Update workspace
   */
  static async updateWorkspace(
    workspaceId: string,
    data: UpdateWorkspaceData,
    userId: string
  ): Promise<WorkspaceWithDetails> {
    try {
      // Check permissions
      const member = await prisma.workspaceMember.findUnique({
        where: {
          workspaceId_userId: {
            workspaceId,
            userId,
          },
        },
      });

      if (!member || !['admin', 'owner'].includes(member.role)) {
        throw new Error('Insufficient permissions to update workspace');
      }

      const workspace = await prisma.workspace.update({
        where: { id: workspaceId },
        data: {
          ...(data.name && { name: data.name }),
          ...(data.description !== undefined && { description: data.description }),
          ...(data.color && { color: data.color }),
          ...(data.isPrivate !== undefined && { isPrivate: data.isPrivate }),
          ...(data.settings && { settings: data.settings }),
        },
        include: {
          organization: true,
          members: {
            include: {
              user: {
                select: {
                  id: true,
                  email: true,
                  firstName: true,
                  lastName: true,
                  avatarUrl: true,
                },
              },
            },
          },
          boards: {
            where: { deletedAt: null },
            include: {
              creator: {
                select: {
                  id: true,
                  firstName: true,
                  lastName: true,
                  avatarUrl: true,
                },
              },
              _count: {
                select: {
                  items: {
                    where: { deletedAt: null },
                  },
                  members: true,
                },
              },
            },
          },
          folders: {
            orderBy: { position: 'asc' },
          },
          _count: {
            select: {
              boards: {
                where: { deletedAt: null },
              },
              members: true,
            },
          },
        },
      });

      Logger.api(`Workspace updated: ${workspace.name}`, {
        workspaceId,
        userId,
      });

      // Invalidate cache
      await RedisService.deleteCache(`workspace:${workspaceId}`);

      const result: WorkspaceWithDetails = {
        id: workspace.id,
        organizationId: workspace.organizationId,
        name: workspace.name,
        description: workspace.description,
        color: workspace.color,
        isPrivate: workspace.isPrivate,
        settings: workspace.settings as Record<string, any>,
        createdAt: workspace.createdAt,
        updatedAt: workspace.updatedAt,
        organization: {
          id: workspace.organization.id,
          name: workspace.organization.name,
          slug: workspace.organization.slug,
        },
        members: workspace.members.map(member => ({
          id: member.id,
          role: member.role,
          permissions: member.permissions as Record<string, any>,
          user: {
            id: member.user.id,
            email: member.user.email,
            firstName: member.user.firstName,
            lastName: member.user.lastName,
            avatarUrl: member.user.avatarUrl,
          },
          createdAt: member.createdAt,
        })),
        boards: workspace.boards.map(board => ({
          id: board.id,
          name: board.name,
          description: board.description,
          isPrivate: board.isPrivate,
          createdAt: board.createdAt,
          creator: {
            id: board.creator.id,
            firstName: board.creator.firstName,
            lastName: board.creator.lastName,
            avatarUrl: board.creator.avatarUrl,
          },
          stats: {
            itemCount: board._count.items,
            memberCount: board._count.members,
          },
        })),
        folders: workspace.folders.map(folder => ({
          id: folder.id,
          name: folder.name,
          color: folder.color,
          position: folder.position,
        })),
        stats: {
          boardCount: workspace._count.boards,
          memberCount: workspace._count.members,
        },
      };

      return result;
    } catch (error) {
      Logger.error('Failed to update workspace', error as Error);
      throw error;
    }
  }

  /**
   * Delete workspace
   */
  static async deleteWorkspace(workspaceId: string, userId: string): Promise<void> {
    try {
      // Check permissions
      const member = await prisma.workspaceMember.findUnique({
        where: {
          workspaceId_userId: {
            workspaceId,
            userId,
          },
        },
      });

      if (!member || member.role !== 'admin') {
        throw new Error('Insufficient permissions to delete workspace');
      }

      // Soft delete workspace and all related data
      await prisma.workspace.update({
        where: { id: workspaceId },
        data: { deletedAt: new Date() },
      });

      Logger.api(`Workspace deleted: ${workspaceId}`, { userId });

      // Invalidate caches
      await RedisService.deleteCache(`workspace:${workspaceId}`);
    } catch (error) {
      Logger.error('Failed to delete workspace', error as Error);
      throw error;
    }
  }

  /**
   * Add member to workspace
   */
  static async addMember(
    workspaceId: string,
    userId: string,
    newMemberEmail: string,
    role: string = 'member',
    addedBy: string
  ): Promise<void> {
    try {
      // Check if current user has permission
      const currentMember = await prisma.workspaceMember.findUnique({
        where: {
          workspaceId_userId: {
            workspaceId,
            userId: addedBy,
          },
        },
      });

      if (!currentMember || !['admin', 'owner'].includes(currentMember.role)) {
        throw new Error('Insufficient permissions to add members');
      }

      // Find user by email
      const user = await prisma.user.findUnique({
        where: { email: newMemberEmail.toLowerCase() },
      });

      if (!user) {
        throw new Error('User not found');
      }

      // Check if user is already a member
      const existingMember = await prisma.workspaceMember.findUnique({
        where: {
          workspaceId_userId: {
            workspaceId,
            userId: user.id,
          },
        },
      });

      if (existingMember) {
        throw new Error('User is already a member of this workspace');
      }

      // Add member
      await prisma.workspaceMember.create({
        data: {
          workspaceId,
          userId: user.id,
          role,
        },
      });

      Logger.api(`Member added to workspace: ${newMemberEmail}`, {
        workspaceId,
        addedBy,
      });

      // Invalidate cache
      await RedisService.deleteCache(`workspace:${workspaceId}`);
    } catch (error) {
      Logger.error('Failed to add workspace member', error as Error);
      throw error;
    }
  }

  /**
   * Remove member from workspace
   */
  static async removeMember(
    workspaceId: string,
    memberUserId: string,
    removedBy: string
  ): Promise<void> {
    try {
      // Check permissions
      const currentMember = await prisma.workspaceMember.findUnique({
        where: {
          workspaceId_userId: {
            workspaceId,
            userId: removedBy,
          },
        },
      });

      if (!currentMember || !['admin', 'owner'].includes(currentMember.role)) {
        throw new Error('Insufficient permissions to remove members');
      }

      // Remove member
      await prisma.workspaceMember.delete({
        where: {
          workspaceId_userId: {
            workspaceId,
            userId: memberUserId,
          },
        },
      });

      Logger.api(`Member removed from workspace`, {
        workspaceId,
        memberUserId,
        removedBy,
      });

      // Invalidate cache
      await RedisService.deleteCache(`workspace:${workspaceId}`);
    } catch (error) {
      Logger.error('Failed to remove workspace member', error as Error);
      throw error;
    }
  }

  /**
   * Update member role
   */
  static async updateMemberRole(
    workspaceId: string,
    memberUserId: string,
    newRole: string,
    updatedBy: string
  ): Promise<void> {
    try {
      // Check permissions
      const currentMember = await prisma.workspaceMember.findUnique({
        where: {
          workspaceId_userId: {
            workspaceId,
            userId: updatedBy,
          },
        },
      });

      if (!currentMember || !['admin', 'owner'].includes(currentMember.role)) {
        throw new Error('Insufficient permissions to update member roles');
      }

      // Update member role
      await prisma.workspaceMember.update({
        where: {
          workspaceId_userId: {
            workspaceId,
            userId: memberUserId,
          },
        },
        data: { role: newRole },
      });

      Logger.api(`Member role updated in workspace`, {
        workspaceId,
        memberUserId,
        newRole,
        updatedBy,
      });

      // Invalidate cache
      await RedisService.deleteCache(`workspace:${workspaceId}`);
    } catch (error) {
      Logger.error('Failed to update workspace member role', error as Error);
      throw error;
    }
  }
}