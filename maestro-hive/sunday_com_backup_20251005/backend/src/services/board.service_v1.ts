import { prisma } from '@/config/database';
import { RedisService } from '@/config/redis';
import { Logger } from '@/config/logger';
import { io } from '@/server';
import {
  CreateBoardData,
  UpdateBoardData,
  CreateBoardColumnData,
  UpdateBoardColumnData,
  PaginatedResult,
  PaginationMeta,
} from '@/types';
import { Board, BoardColumn, BoardMember, User, Item, Prisma } from '@prisma/client';

type BoardWithRelations = Board & {
  columns?: BoardColumn[];
  items?: Array<Item & { assignments: Array<{ user: User }> }>;
  members?: Array<BoardMember & { user: User }>;
  creator?: User;
  _count?: {
    items: number;
    members: number;
    columns: number;
  };
};

export class BoardService {
  /**
   * Create a new board
   */
  static async create(
    data: CreateBoardData,
    creatorId: string
  ): Promise<BoardWithRelations> {
    try {
      // Check if user has access to workspace
      const workspace = await prisma.workspace.findUnique({
        where: { id: data.workspaceId },
        include: {
          members: {
            where: { userId: creatorId },
          },
        },
      });

      if (!workspace) {
        throw new Error('Workspace not found');
      }

      if (workspace.isPrivate && workspace.members.length === 0) {
        throw new Error('Access denied to private workspace');
      }

      // Create board with creator as admin
      const board = await prisma.board.create({
        data: {
          ...data,
          createdBy: creatorId,
          members: {
            create: {
              userId: creatorId,
              role: 'admin',
            },
          },
          columns: data.columns
            ? {
                create: data.columns.map((column, index) => ({
                  ...column,
                  position: index,
                })),
              }
            : undefined,
        },
        include: {
          columns: {
            orderBy: { position: 'asc' },
          },
          members: {
            include: {
              user: true,
            },
          },
          creator: true,
          _count: {
            select: {
              items: true,
              members: true,
              columns: true,
            },
          },
        },
      });

      // Emit real-time event
      io.to(`workspace:${data.workspaceId}`).emit('board_created', {
        board: {
          id: board.id,
          name: board.name,
          workspaceId: board.workspaceId,
        },
        user: {
          id: creatorId,
          name: board.creator?.firstName || 'Unknown',
        },
      });

      Logger.business(`Board created: ${board.name}`, {
        boardId: board.id,
        workspaceId: data.workspaceId,
        creatorId,
      });

      return board;
    } catch (error) {
      Logger.error('Board creation failed', error as Error);
      throw error;
    }
  }

  /**
   * Get board by ID with optional includes
   */
  static async getById(
    boardId: string,
    userId: string,
    includeColumns = true,
    includeItems = false,
    includeMembers = false
  ): Promise<BoardWithRelations | null> {
    try {
      const cacheKey = `board:${boardId}:${includeColumns}:${includeItems}:${includeMembers}`;
      const cached = await RedisService.getCache(cacheKey);
      if (cached) {
        return cached;
      }

      const board = await prisma.board.findFirst({
        where: {
          id: boardId,
          deletedAt: null,
          OR: [
            { isPrivate: false },
            {
              members: {
                some: { userId },
              },
            },
            {
              workspace: {
                members: {
                  some: { userId },
                },
              },
            },
          ],
        },
        include: {
          columns: includeColumns
            ? {
                orderBy: { position: 'asc' },
              }
            : false,
          items: includeItems
            ? {
                where: { deletedAt: null },
                include: {
                  assignments: {
                    include: {
                      user: true,
                    },
                  },
                },
                orderBy: { position: 'asc' },
              }
            : false,
          members: includeMembers
            ? {
                include: {
                  user: true,
                },
                orderBy: { role: 'asc' },
              }
            : false,
          creator: true,
          _count: {
            select: {
              items: {
                where: { deletedAt: null },
              },
              members: true,
              columns: true,
            },
          },
        },
      });

      if (board) {
        await RedisService.setCache(cacheKey, board, 300); // 5 minutes
      }

      return board;
    } catch (error) {
      Logger.error('Failed to get board', error as Error);
      throw error;
    }
  }

  /**
   * Get boards for a workspace
   */
  static async getByWorkspace(
    workspaceId: string,
    userId: string,
    page = 1,
    limit = 20,
    folderId?: string
  ): Promise<PaginatedResult<BoardWithRelations>> {
    try {
      const offset = (page - 1) * limit;

      const whereClause: Prisma.BoardWhereInput = {
        workspaceId,
        deletedAt: null,
        ...(folderId !== undefined && { folderId }),
        OR: [
          { isPrivate: false },
          {
            members: {
              some: { userId },
            },
          },
        ],
      };

      const [boards, total] = await Promise.all([
        prisma.board.findMany({
          where: whereClause,
          include: {
            creator: true,
            _count: {
              select: {
                items: {
                  where: { deletedAt: null },
                },
                members: true,
                columns: true,
              },
            },
          },
          orderBy: [
            { position: 'asc' },
            { createdAt: 'desc' },
          ],
          skip: offset,
          take: limit,
        }),
        prisma.board.count({
          where: whereClause,
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

      return { data: boards, meta };
    } catch (error) {
      Logger.error('Failed to get workspace boards', error as Error);
      throw error;
    }
  }

  /**
   * Update board
   */
  static async update(
    boardId: string,
    data: UpdateBoardData,
    userId: string
  ): Promise<BoardWithRelations> {
    try {
      // Check permissions
      const hasAccess = await this.hasWriteAccess(boardId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      const board = await prisma.board.update({
        where: { id: boardId },
        data,
        include: {
          columns: {
            orderBy: { position: 'asc' },
          },
          creator: true,
          _count: {
            select: {
              items: {
                where: { deletedAt: null },
              },
              members: true,
              columns: true,
            },
          },
        },
      });

      // Invalidate caches
      await this.invalidateCaches(boardId);

      // Emit real-time event
      io.to(`board:${boardId}`).emit('board_updated', {
        boardId,
        changes: data,
        updatedBy: userId,
      });

      Logger.business(`Board updated: ${board.name}`, {
        boardId,
        userId,
      });

      return board;
    } catch (error) {
      Logger.error('Board update failed', error as Error);
      throw error;
    }
  }

  /**
   * Delete board (soft delete)
   */
  static async delete(boardId: string, userId: string): Promise<void> {
    try {
      // Check permissions
      const hasAccess = await this.hasAdminAccess(boardId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      await prisma.board.update({
        where: { id: boardId },
        data: { deletedAt: new Date() },
      });

      // Invalidate caches
      await this.invalidateCaches(boardId);

      // Emit real-time event
      io.to(`board:${boardId}`).emit('board_deleted', {
        boardId,
        deletedBy: userId,
      });

      Logger.business(`Board deleted`, { boardId, userId });
    } catch (error) {
      Logger.error('Board deletion failed', error as Error);
      throw error;
    }
  }

  /**
   * Create board column
   */
  static async createColumn(
    boardId: string,
    data: CreateBoardColumnData,
    userId: string
  ): Promise<BoardColumn> {
    try {
      // Check permissions
      const hasAccess = await this.hasWriteAccess(boardId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      // Get position
      const position = data.position !== undefined
        ? data.position
        : await this.getNextColumnPosition(boardId);

      const column = await prisma.boardColumn.create({
        data: {
          ...data,
          boardId,
          position,
        },
      });

      // Invalidate caches
      await this.invalidateCaches(boardId);

      // Emit real-time event
      io.to(`board:${boardId}`).emit('column_created', {
        column,
        createdBy: userId,
      });

      Logger.business(`Board column created: ${column.name}`, {
        boardId,
        columnId: column.id,
        userId,
      });

      return column;
    } catch (error) {
      Logger.error('Board column creation failed', error as Error);
      throw error;
    }
  }

  /**
   * Update board column
   */
  static async updateColumn(
    columnId: string,
    data: UpdateBoardColumnData,
    userId: string
  ): Promise<BoardColumn> {
    try {
      // Get column to check board permissions
      const existingColumn = await prisma.boardColumn.findUnique({
        where: { id: columnId },
      });

      if (!existingColumn) {
        throw new Error('Column not found');
      }

      // Check permissions
      const hasAccess = await this.hasWriteAccess(existingColumn.boardId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      const column = await prisma.boardColumn.update({
        where: { id: columnId },
        data,
      });

      // Invalidate caches
      await this.invalidateCaches(existingColumn.boardId);

      // Emit real-time event
      io.to(`board:${existingColumn.boardId}`).emit('column_updated', {
        column,
        changes: data,
        updatedBy: userId,
      });

      Logger.business(`Board column updated: ${column.name}`, {
        boardId: existingColumn.boardId,
        columnId,
        userId,
      });

      return column;
    } catch (error) {
      Logger.error('Board column update failed', error as Error);
      throw error;
    }
  }

  /**
   * Delete board column
   */
  static async deleteColumn(columnId: string, userId: string): Promise<void> {
    try {
      // Get column to check board permissions
      const existingColumn = await prisma.boardColumn.findUnique({
        where: { id: columnId },
      });

      if (!existingColumn) {
        throw new Error('Column not found');
      }

      // Check permissions
      const hasAccess = await this.hasWriteAccess(existingColumn.boardId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      await prisma.boardColumn.delete({
        where: { id: columnId },
      });

      // Invalidate caches
      await this.invalidateCaches(existingColumn.boardId);

      // Emit real-time event
      io.to(`board:${existingColumn.boardId}`).emit('column_deleted', {
        columnId,
        boardId: existingColumn.boardId,
        deletedBy: userId,
      });

      Logger.business(`Board column deleted`, {
        boardId: existingColumn.boardId,
        columnId,
        userId,
      });
    } catch (error) {
      Logger.error('Board column deletion failed', error as Error);
      throw error;
    }
  }

  /**
   * Add member to board
   */
  static async addMember(
    boardId: string,
    userId: string,
    role: string = 'member',
    permissions: Record<string, any> = {},
    addedBy: string
  ): Promise<BoardMember> {
    try {
      // Check permissions
      const hasAccess = await this.hasAdminAccess(boardId, addedBy);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      // Check if user is already a member
      const existingMember = await prisma.boardMember.findUnique({
        where: {
          boardId_userId: {
            boardId,
            userId,
          },
        },
      });

      if (existingMember) {
        throw new Error('User is already a member of this board');
      }

      const member = await prisma.boardMember.create({
        data: {
          boardId,
          userId,
          role,
          permissions,
        },
      });

      // Invalidate caches
      await this.invalidateCaches(boardId);

      // Emit real-time event
      io.to(`board:${boardId}`).emit('member_added', {
        boardId,
        member: {
          id: member.id,
          userId,
          role,
        },
        addedBy,
      });

      Logger.business(`Member added to board`, {
        boardId,
        userId,
        role,
        addedBy,
      });

      return member;
    } catch (error) {
      Logger.error('Add board member failed', error as Error);
      throw error;
    }
  }

  /**
   * Remove member from board
   */
  static async removeMember(
    boardId: string,
    userId: string,
    removedBy: string
  ): Promise<void> {
    try {
      // Check permissions
      const hasAccess = await this.hasAdminAccess(boardId, removedBy);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      // Check if user is the only admin
      const adminCount = await prisma.boardMember.count({
        where: {
          boardId,
          role: 'admin',
        },
      });

      const memberToRemove = await prisma.boardMember.findUnique({
        where: {
          boardId_userId: {
            boardId,
            userId,
          },
        },
      });

      if (memberToRemove?.role === 'admin' && adminCount <= 1) {
        throw new Error('Cannot remove the last admin of the board');
      }

      await prisma.boardMember.delete({
        where: {
          boardId_userId: {
            boardId,
            userId,
          },
        },
      });

      // Invalidate caches
      await this.invalidateCaches(boardId);

      // Emit real-time event
      io.to(`board:${boardId}`).emit('member_removed', {
        boardId,
        userId,
        removedBy,
      });

      Logger.business(`Member removed from board`, {
        boardId,
        userId,
        removedBy,
      });
    } catch (error) {
      Logger.error('Remove board member failed', error as Error);
      throw error;
    }
  }

  /**
   * Update member role and permissions
   */
  static async updateMember(
    boardId: string,
    userId: string,
    role?: string,
    permissions?: Record<string, any>,
    updatedBy?: string
  ): Promise<BoardMember> {
    try {
      // Check permissions
      if (updatedBy) {
        const hasAccess = await this.hasAdminAccess(boardId, updatedBy);
        if (!hasAccess) {
          throw new Error('Access denied');
        }
      }

      const updateData: any = {};
      if (role) updateData.role = role;
      if (permissions) updateData.permissions = permissions;

      const member = await prisma.boardMember.update({
        where: {
          boardId_userId: {
            boardId,
            userId,
          },
        },
        data: updateData,
      });

      // Invalidate caches
      await this.invalidateCaches(boardId);

      // Emit real-time event
      io.to(`board:${boardId}`).emit('member_updated', {
        boardId,
        userId,
        role,
        updatedBy,
      });

      Logger.business(`Board member updated`, {
        boardId,
        userId,
        role,
        updatedBy,
      });

      return member;
    } catch (error) {
      Logger.error('Update board member failed', error as Error);
      throw error;
    }
  }

  /**
   * Get board members
   */
  static async getMembers(
    boardId: string,
    page = 1,
    limit = 20
  ): Promise<PaginatedResult<BoardMember & { user: User }>> {
    try {
      const offset = (page - 1) * limit;

      const [members, total] = await Promise.all([
        prisma.boardMember.findMany({
          where: { boardId },
          include: {
            user: true,
          },
          orderBy: [
            { role: 'asc' }, // admins first
            { user: { firstName: 'asc' } },
          ],
          skip: offset,
          take: limit,
        }),
        prisma.boardMember.count({
          where: { boardId },
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
      Logger.error('Failed to get board members', error as Error);
      throw error;
    }
  }

  /**
   * Get board statistics
   */
  static async getStatistics(boardId: string): Promise<{
    totalItems: number;
    completedItems: number;
    totalMembers: number;
    totalColumns: number;
    activeMembersToday: number;
  }> {
    try {
      const [stats] = await prisma.$queryRaw<Array<{
        totalItems: bigint;
        completedItems: bigint;
        totalMembers: bigint;
        totalColumns: bigint;
        activeMembersToday: bigint;
      }>>`
        SELECT
          COUNT(DISTINCT i.id) as "totalItems",
          COUNT(DISTINCT CASE
            WHEN JSON_EXTRACT(i.item_data, '$.status') = 'Done'
            THEN i.id
          END) as "completedItems",
          COUNT(DISTINCT bm.user_id) as "totalMembers",
          COUNT(DISTINCT bc.id) as "totalColumns",
          COUNT(DISTINCT CASE
            WHEN al.created_at >= CURRENT_DATE
            THEN al.user_id
          END) as "activeMembersToday"
        FROM boards b
        LEFT JOIN items i ON b.id = i.board_id AND i.deleted_at IS NULL
        LEFT JOIN board_members bm ON b.id = bm.board_id
        LEFT JOIN board_columns bc ON b.id = bc.board_id
        LEFT JOIN activity_log al ON b.id = al.board_id
        WHERE b.id = ${boardId}
      `;

      return {
        totalItems: Number(stats.totalItems),
        completedItems: Number(stats.completedItems),
        totalMembers: Number(stats.totalMembers),
        totalColumns: Number(stats.totalColumns),
        activeMembersToday: Number(stats.activeMembersToday),
      };
    } catch (error) {
      Logger.error('Failed to get board statistics', error as Error);
      throw error;
    }
  }

  // ============================================================================
  // PERMISSION HELPERS
  // ============================================================================

  /**
   * Check if user has read access to board
   */
  static async hasReadAccess(boardId: string, userId: string): Promise<boolean> {
    try {
      const board = await prisma.board.findUnique({
        where: { id: boardId, deletedAt: null },
        include: {
          members: {
            where: { userId },
          },
          workspace: {
            include: {
              members: {
                where: { userId },
              },
            },
          },
        },
      });

      if (!board) return false;

      // Board members have access
      if (board.members.length > 0) return true;

      // If board is not private, workspace members have access
      if (!board.isPrivate && board.workspace.members.length > 0) return true;

      return false;
    } catch (error) {
      Logger.error('Failed to check board read access', error as Error);
      return false;
    }
  }

  /**
   * Check if user has write access to board
   */
  static async hasWriteAccess(boardId: string, userId: string): Promise<boolean> {
    try {
      const member = await prisma.boardMember.findUnique({
        where: {
          boardId_userId: {
            boardId,
            userId,
          },
        },
      });

      return !!member;
    } catch (error) {
      Logger.error('Failed to check board write access', error as Error);
      return false;
    }
  }

  /**
   * Check if user has admin access to board
   */
  static async hasAdminAccess(boardId: string, userId: string): Promise<boolean> {
    try {
      const member = await prisma.boardMember.findUnique({
        where: {
          boardId_userId: {
            boardId,
            userId,
          },
        },
      });

      return !!member && member.role === 'admin';
    } catch (error) {
      Logger.error('Failed to check board admin access', error as Error);
      return false;
    }
  }

  // ============================================================================
  // PRIVATE METHODS
  // ============================================================================

  /**
   * Get next column position
   */
  private static async getNextColumnPosition(boardId: string): Promise<number> {
    const lastColumn = await prisma.boardColumn.findFirst({
      where: { boardId },
      orderBy: { position: 'desc' },
      select: { position: true },
    });

    return (lastColumn?.position || 0) + 1;
  }

  /**
   * Invalidate related caches
   */
  private static async invalidateCaches(boardId: string): Promise<void> {
    await Promise.all([
      RedisService.deleteCachePattern(`board:${boardId}:*`),
      RedisService.deleteCachePattern(`permissions:*:board:${boardId}`),
    ]);
  }
}