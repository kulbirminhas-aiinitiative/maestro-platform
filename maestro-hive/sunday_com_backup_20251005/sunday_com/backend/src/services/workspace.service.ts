import { prisma } from '@/config/database';
import { Logger } from '@/config/logger';
import { RedisService } from '@/config/redis';
import {
  CreateWorkspaceData,
  PaginatedResult,
  WorkspaceFilter,
  SortOption,
  ApiError,
} from '@/types';
import { v4 as uuidv4 } from 'uuid';

export class WorkspaceService {
  /**
   * Create a new workspace
   */
  static async createWorkspace(
    organizationId: string,
    userId: string,
    data: CreateWorkspaceData
  ): Promise<any> {
    try {
      // Verify user has permission to create workspaces in organization
      const orgMember = await prisma.organizationMember.findFirst({
        where: {
          organizationId,
          userId,
          status: 'active',
          role: { in: ['owner', 'admin', 'member'] },
        },
      });

      if (!orgMember) {
        throw new Error('Organization not found or access denied');
      }

      // Check if workspace name already exists in organization
      const existingWorkspace = await prisma.workspace.findFirst({
        where: {
          organizationId,
          name: data.name,
          deletedAt: null,
        },
      });

      if (existingWorkspace) {
        throw new Error('Workspace with this name already exists');
      }

      // Create workspace
      const workspace = await prisma.workspace.create({
        data: {
          id: uuidv4(),
          organizationId,
          name: data.name,
          description: data.description,
          color: data.color || '#6B7280',
          settings: data.settings || {},
          isPrivate: data.isPrivate || false,
        },
        include: {
          organization: {
            select: { id: true, name: true, slug: true },
          },
          members: {
            include: {
              user: {
                select: { id: true, email: true, firstName: true, lastName: true, avatarUrl: true },
              },
            },
          },
          boards: {
            where: { deletedAt: null },
            select: { id: true, name: true, isPrivate: true },
            take: 10,
          },
          folders: {
            select: { id: true, name: true, color: true, position: true },
            orderBy: { position: 'asc' },
          },
        },
      });

      // Add creator as workspace admin
      await prisma.workspaceMember.create({
        data: {
          workspaceId: workspace.id,
          userId,
          role: 'admin',
          permissions: {
            canCreateBoards: true,
            canManageMembers: true,
            canManageSettings: true,
            canDeleteWorkspace: true,
          },
        },
      });

      // Create default folders
      await this.createDefaultFolders(workspace.id);

      Logger.api(`Workspace created: ${workspace.name}`, {
        workspaceId: workspace.id,
        organizationId,
        userId,
      });

      return workspace;
    } catch (error) {
      Logger.error('Workspace creation failed', error as Error);
      throw error;
    }
  }

  /**
   * Get workspace by ID
   */
  static async getWorkspace(workspaceId: string, userId: string): Promise<any> {
    try {
      // Try cache first
      const cacheKey = `workspace:${workspaceId}:${userId}`;
      const cached = await RedisService.getCache(cacheKey);
      if (cached) {
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
            {
              organization: {
                members: {
                  some: {
                    userId,
                    status: 'active',
                    role: { in: ['owner', 'admin'] },
                  },
                },
              },
            },
          ],
        },
        include: {
          organization: {
            select: { id: true, name: true, slug: true, settings: true },
          },
          members: {
            include: {
              user: {
                select: { id: true, email: true, firstName: true, lastName: true, avatarUrl: true },
              },
            },
          },
          boards: {
            where: {
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
              folder: {
                select: { id: true, name: true, color: true },
              },
              members: {
                include: {
                  user: {
                    select: { id: true, firstName: true, lastName: true, avatarUrl: true },
                  },
                },
                take: 5,
              },
              _count: {
                select: { items: true },
              },
            },
            orderBy: [{ position: 'asc' }, { createdAt: 'desc' }],
          },
          folders: {
            include: {
              boards: {
                where: { deletedAt: null },
                select: { id: true, name: true, isPrivate: true },
              },
            },
            orderBy: { position: 'asc' },
          },
        },
      });

      if (!workspace) {
        throw new Error('Workspace not found or access denied');
      }

      // Cache the result
      await RedisService.setCache(cacheKey, workspace, 300); // 5 minutes

      return workspace;
    } catch (error) {
      Logger.error('Get workspace failed', error as Error);
      throw error;
    }
  }

  /**
   * Update workspace
   */
  static async updateWorkspace(
    workspaceId: string,
    userId: string,
    data: Partial<CreateWorkspaceData>
  ): Promise<any> {
    try {
      // Verify user has permission to edit
      const hasPermission = await this.verifyWorkspacePermission(
        workspaceId,
        userId,
        'canManageSettings'
      );
      if (!hasPermission) {
        throw new Error('Permission denied');
      }

      const workspace = await prisma.workspace.update({
        where: { id: workspaceId },
        data: {
          ...data,
          updatedAt: new Date(),
        },
        include: {
          organization: {
            select: { id: true, name: true, slug: true },
          },
          members: {
            include: {
              user: {
                select: { id: true, email: true, firstName: true, lastName: true, avatarUrl: true },
              },
            },
          },
          folders: {
            select: { id: true, name: true, color: true, position: true },
            orderBy: { position: 'asc' },
          },
        },
      });

      // Invalidate cache
      await RedisService.deleteCache(`workspace:${workspaceId}:*`);

      Logger.api(`Workspace updated: ${workspace.name}`, { workspaceId, userId });

      return workspace;
    } catch (error) {
      Logger.error('Workspace update failed', error as Error);
      throw error;
    }
  }

  /**
   * Delete workspace (soft delete)
   */
  static async deleteWorkspace(workspaceId: string, userId: string): Promise<void> {
    try {
      // Verify user has permission to delete
      const hasPermission = await this.verifyWorkspacePermission(
        workspaceId,
        userId,
        'canDeleteWorkspace'
      );
      if (!hasPermission) {
        throw new Error('Permission denied');
      }

      // Soft delete workspace and all its boards
      await prisma.$transaction(async (tx) => {
        // Delete all boards in workspace
        await tx.board.updateMany({
          where: { workspaceId, deletedAt: null },
          data: { deletedAt: new Date() },
        });

        // Delete workspace
        await tx.workspace.update({
          where: { id: workspaceId },
          data: { deletedAt: new Date() },
        });
      });

      // Invalidate cache
      await RedisService.deleteCache(`workspace:${workspaceId}:*`);

      Logger.api(`Workspace deleted: ${workspaceId}`, { workspaceId, userId });
    } catch (error) {
      Logger.error('Workspace deletion failed', error as Error);
      throw error;
    }
  }

  /**
   * Get organization workspaces
   */
  static async getOrganizationWorkspaces(
    organizationId: string,
    userId: string,
    filter: WorkspaceFilter = {},
    sort: SortOption[] = [{ field: 'name', direction: 'asc' }],
    page: number = 1,
    limit: number = 20
  ): Promise<PaginatedResult<any>> {
    try {
      // Verify user has access to organization
      const orgMember = await prisma.organizationMember.findFirst({
        where: {
          organizationId,
          userId,
          status: 'active',
        },
      });

      if (!orgMember) {
        throw new Error('Organization not found or access denied');
      }

      const offset = (page - 1) * limit;

      // Build where condition
      const where: any = {
        organizationId,
        deletedAt: null,
        OR: [
          { isPrivate: false },
          {
            members: {
              some: { userId },
            },
          },
        ],
      };

      if (filter.name) {
        where.name = { contains: filter.name, mode: 'insensitive' };
      }

      if (filter.isPrivate !== undefined) {
        where.isPrivate = filter.isPrivate;
      }

      // Build order by
      const orderBy = sort.map((s) => ({ [s.field]: s.direction }));

      const [workspaces, total] = await Promise.all([
        prisma.workspace.findMany({
          where,
          include: {
            members: {
              include: {
                user: {
                  select: { id: true, firstName: true, lastName: true, avatarUrl: true },
                },
              },
              take: 5,
            },
            _count: {
              select: { boards: true },
            },
          },
          orderBy,
          skip: offset,
          take: limit,
        }),
        prisma.workspace.count({ where }),
      ]);

      return {
        data: workspaces,
        meta: {
          page,
          limit,
          total,
          totalPages: Math.ceil(total / limit),
          hasNext: page * limit < total,
          hasPrev: page > 1,
        },
      };
    } catch (error) {
      Logger.error('Get organization workspaces failed', error as Error);
      throw error;
    }
  }

  /**
   * Add member to workspace
   */
  static async addWorkspaceMember(
    workspaceId: string,
    userId: string,
    memberUserId: string,
    role: string = 'member',
    permissions: Record<string, boolean> = {}
  ): Promise<any> {
    try {
      // Verify user has permission to manage members
      const hasPermission = await this.verifyWorkspacePermission(
        workspaceId,
        userId,
        'canManageMembers'
      );
      if (!hasPermission) {
        throw new Error('Permission denied');
      }

      // Check if member already exists
      const existingMember = await prisma.workspaceMember.findFirst({
        where: { workspaceId, userId: memberUserId },
      });

      if (existingMember) {
        throw new Error('User is already a member of this workspace');
      }

      const member = await prisma.workspaceMember.create({
        data: {
          workspaceId,
          userId: memberUserId,
          role,
          permissions: {
            canCreateBoards: role === 'admin' || permissions.canCreateBoards === true,
            canManageMembers: role === 'admin' || permissions.canManageMembers === true,
            canManageSettings: role === 'admin' || permissions.canManageSettings === true,
            canDeleteWorkspace: role === 'admin' || permissions.canDeleteWorkspace === true,
            ...permissions,
          },
        },
        include: {
          user: {
            select: { id: true, email: true, firstName: true, lastName: true, avatarUrl: true },
          },
        },
      });

      // Invalidate workspace cache
      await RedisService.deleteCache(`workspace:${workspaceId}:*`);

      Logger.api(`Workspace member added: ${memberUserId}`, { workspaceId, userId });

      return member;
    } catch (error) {
      Logger.error('Add workspace member failed', error as Error);
      throw error;
    }
  }

  /**
   * Remove member from workspace
   */
  static async removeWorkspaceMember(
    workspaceId: string,
    userId: string,
    memberUserId: string
  ): Promise<void> {
    try {
      // Verify user has permission to manage members
      const hasPermission = await this.verifyWorkspacePermission(
        workspaceId,
        userId,
        'canManageMembers'
      );
      if (!hasPermission) {
        throw new Error('Permission denied');
      }

      const member = await prisma.workspaceMember.findFirst({
        where: { workspaceId, userId: memberUserId },
      });

      if (!member) {
        throw new Error('Member not found');
      }

      await prisma.workspaceMember.delete({
        where: { id: member.id },
      });

      // Invalidate workspace cache
      await RedisService.deleteCache(`workspace:${workspaceId}:*`);

      Logger.api(`Workspace member removed: ${memberUserId}`, { workspaceId, userId });
    } catch (error) {
      Logger.error('Remove workspace member failed', error as Error);
      throw error;
    }
  }

  /**
   * Update member role and permissions
   */
  static async updateWorkspaceMember(
    workspaceId: string,
    userId: string,
    memberUserId: string,
    role?: string,
    permissions?: Record<string, boolean>
  ): Promise<any> {
    try {
      // Verify user has permission to manage members
      const hasPermission = await this.verifyWorkspacePermission(
        workspaceId,
        userId,
        'canManageMembers'
      );
      if (!hasPermission) {
        throw new Error('Permission denied');
      }

      const member = await prisma.workspaceMember.findFirst({
        where: { workspaceId, userId: memberUserId },
      });

      if (!member) {
        throw new Error('Member not found');
      }

      const updateData: any = {};
      if (role) {
        updateData.role = role;
      }
      if (permissions) {
        updateData.permissions = {
          ...member.permissions,
          ...permissions,
        };
      }

      const updatedMember = await prisma.workspaceMember.update({
        where: { id: member.id },
        data: updateData,
        include: {
          user: {
            select: { id: true, email: true, firstName: true, lastName: true, avatarUrl: true },
          },
        },
      });

      // Invalidate workspace cache
      await RedisService.deleteCache(`workspace:${workspaceId}:*`);

      Logger.api(`Workspace member updated: ${memberUserId}`, { workspaceId, userId });

      return updatedMember;
    } catch (error) {
      Logger.error('Update workspace member failed', error as Error);
      throw error;
    }
  }

  /**
   * Create folder in workspace
   */
  static async createFolder(
    workspaceId: string,
    userId: string,
    data: { name: string; color?: string }
  ): Promise<any> {
    try {
      // Verify user has access to workspace
      const hasAccess = await this.verifyWorkspaceAccess(workspaceId, userId);
      if (!hasAccess) {
        throw new Error('Workspace not found or access denied');
      }

      // Get next position
      const lastFolder = await prisma.folder.findFirst({
        where: { workspaceId },
        orderBy: { position: 'desc' },
      });
      const position = (lastFolder?.position || 0) + 1;

      const folder = await prisma.folder.create({
        data: {
          id: uuidv4(),
          workspaceId,
          name: data.name,
          color: data.color || '#6B7280',
          position,
        },
        include: {
          boards: {
            where: { deletedAt: null },
            select: { id: true, name: true, isPrivate: true },
          },
        },
      });

      // Invalidate workspace cache
      await RedisService.deleteCache(`workspace:${workspaceId}:*`);

      Logger.api(`Folder created: ${folder.name}`, { workspaceId, folderId: folder.id, userId });

      return folder;
    } catch (error) {
      Logger.error('Create folder failed', error as Error);
      throw error;
    }
  }

  /**
   * Update folder
   */
  static async updateFolder(
    folderId: string,
    userId: string,
    data: Partial<{ name: string; color: string; position: number }>
  ): Promise<any> {
    try {
      const folder = await prisma.folder.findUnique({
        where: { id: folderId },
        include: { workspace: true },
      });

      if (!folder) {
        throw new Error('Folder not found');
      }

      // Verify user has access to workspace
      const hasAccess = await this.verifyWorkspaceAccess(folder.workspaceId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      const updatedFolder = await prisma.folder.update({
        where: { id: folderId },
        data: {
          ...data,
          updatedAt: new Date(),
        },
        include: {
          boards: {
            where: { deletedAt: null },
            select: { id: true, name: true, isPrivate: true },
          },
        },
      });

      // Invalidate workspace cache
      await RedisService.deleteCache(`workspace:${folder.workspaceId}:*`);

      Logger.api(`Folder updated: ${updatedFolder.name}`, {
        workspaceId: folder.workspaceId,
        folderId,
        userId,
      });

      return updatedFolder;
    } catch (error) {
      Logger.error('Update folder failed', error as Error);
      throw error;
    }
  }

  /**
   * Delete folder
   */
  static async deleteFolder(folderId: string, userId: string): Promise<void> {
    try {
      const folder = await prisma.folder.findUnique({
        where: { id: folderId },
        include: { workspace: true },
      });

      if (!folder) {
        throw new Error('Folder not found');
      }

      // Verify user has access to workspace
      const hasAccess = await this.verifyWorkspaceAccess(folder.workspaceId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      // Move all boards to no folder
      await prisma.board.updateMany({
        where: { folderId },
        data: { folderId: null },
      });

      // Delete folder
      await prisma.folder.delete({
        where: { id: folderId },
      });

      // Invalidate workspace cache
      await RedisService.deleteCache(`workspace:${folder.workspaceId}:*`);

      Logger.api(`Folder deleted: ${folderId}`, {
        workspaceId: folder.workspaceId,
        folderId,
        userId,
      });
    } catch (error) {
      Logger.error('Delete folder failed', error as Error);
      throw error;
    }
  }

  // ============================================================================
  // PRIVATE HELPER METHODS
  // ============================================================================

  /**
   * Verify workspace access for user
   */
  private static async verifyWorkspaceAccess(workspaceId: string, userId: string): Promise<boolean> {
    try {
      const access = await prisma.workspace.findFirst({
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
            {
              organization: {
                members: {
                  some: {
                    userId,
                    status: 'active',
                    role: { in: ['owner', 'admin'] },
                  },
                },
              },
            },
          ],
        },
      });

      return !!access;
    } catch (error) {
      return false;
    }
  }

  /**
   * Verify workspace permission for user
   */
  private static async verifyWorkspacePermission(
    workspaceId: string,
    userId: string,
    permission: string
  ): Promise<boolean> {
    try {
      const member = await prisma.workspaceMember.findFirst({
        where: { workspaceId, userId },
      });

      if (!member) {
        // Check organization-level permission
        const workspace = await prisma.workspace.findUnique({
          where: { id: workspaceId },
          include: {
            organization: {
              include: {
                members: {
                  where: { userId, status: 'active' },
                },
              },
            },
          },
        });

        const orgMember = workspace?.organization.members[0];
        if (orgMember?.role === 'owner' || orgMember?.role === 'admin') {
          return true;
        }

        return false;
      }

      // Check workspace-level permission
      const permissions = member.permissions as Record<string, boolean>;
      return permissions[permission] === true;
    } catch (error) {
      return false;
    }
  }

  /**
   * Create default folders for a new workspace
   */
  private static async createDefaultFolders(workspaceId: string): Promise<void> {
    const defaultFolders = [
      { name: 'Getting Started', color: '#037F4C', position: 1 },
      { name: 'Current Projects', color: '#5559DF', position: 2 },
      { name: 'Archive', color: '#C4C4C4', position: 3 },
    ];

    for (const folder of defaultFolders) {
      await prisma.folder.create({
        data: {
          id: uuidv4(),
          workspaceId,
          ...folder,
        },
      });
    }
  }
}