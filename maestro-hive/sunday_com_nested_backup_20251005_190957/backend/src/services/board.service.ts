import { prisma } from '@/config/database';
import { Logger } from '@/config/logger';
import { RedisService } from '@/config/redis';
import {
  CreateBoardData,
  PaginatedResult,
  BoardFilter,
  SortOption,
  ApiError,
} from '@/types';
import { v4 as uuidv4 } from 'uuid';

export class BoardService {
  /**
   * Create a new board
   */
  static async createBoard(
    workspaceId: string,
    userId: string,
    data: CreateBoardData
  ): Promise<any> {
    try {
      // Verify workspace exists and user has access
      const workspace = await prisma.workspace.findFirst({
        where: {
          id: workspaceId,
          OR: [
            { isPrivate: false },
            {
              members: {
                some: {
                  userId: userId,
                  role: { in: ['admin', 'member'] },
                },
              },
            },
          ],
        },
      });

      if (!workspace) {
        throw new Error('Workspace not found or access denied');
      }

      // Get the next position for the board
      const lastBoard = await prisma.board.findFirst({
        where: { workspaceId },
        orderBy: { position: 'desc' },
      });
      const position = (lastBoard?.position || 0) + 1;

      // Create board
      const board = await prisma.board.create({
        data: {
          id: uuidv4(),
          workspaceId,
          name: data.name,
          description: data.description,
          templateId: data.templateId,
          settings: data.settings || {},
          isPrivate: data.isPrivate || false,
          folderId: data.folderId,
          position,
          createdBy: userId,
        },
        include: {
          workspace: {
            select: { id: true, name: true, organizationId: true },
          },
          folder: {
            select: { id: true, name: true },
          },
          members: {
            include: {
              user: {
                select: { id: true, email: true, firstName: true, lastName: true, avatarUrl: true },
              },
            },
          },
          columns: {
            orderBy: { position: 'asc' },
          },
        },
      });

      // Add creator as board owner
      await prisma.boardMember.create({
        data: {
          boardId: board.id,
          userId,
          role: 'owner',
          permissions: {
            canEdit: true,
            canDelete: true,
            canManageMembers: true,
            canManageSettings: true,
          },
        },
      });

      // Create default columns if using a template
      if (data.templateId) {
        await this.createDefaultColumnsFromTemplate(board.id, data.templateId);
      } else {
        await this.createDefaultColumns(board.id);
      }

      // Cache board data
      await RedisService.setCache(`board:${board.id}`, board, 300); // 5 minutes

      Logger.api(`Board created: ${board.name}`, { boardId: board.id, userId });

      return board;
    } catch (error) {
      Logger.error('Board creation failed', error as Error);
      throw error;
    }
  }

  /**
   * Get board by ID
   */
  static async getBoard(boardId: string, userId: string): Promise<any> {
    try {
      // Try cache first
      const cached = await RedisService.getCache(`board:${boardId}`);
      if (cached) {
        // Verify access
        const hasAccess = await this.verifyBoardAccess(boardId, userId);
        if (!hasAccess) {
          throw new Error('Board not found or access denied');
        }
        return cached;
      }

      // Get from database
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
                  some: {
                    userId,
                    role: { in: ['admin', 'member'] },
                  },
                },
              },
            },
          ],
        },
        include: {
          workspace: {
            select: { id: true, name: true, organizationId: true },
          },
          folder: {
            select: { id: true, name: true },
          },
          members: {
            include: {
              user: {
                select: { id: true, email: true, firstName: true, lastName: true, avatarUrl: true },
              },
            },
          },
          columns: {
            orderBy: { position: 'asc' },
          },
          items: {
            where: { deletedAt: null },
            include: {
              assignments: {
                include: {
                  user: {
                    select: { id: true, firstName: true, lastName: true, avatarUrl: true },
                  },
                },
              },
            },
            orderBy: { position: 'asc' },
          },
        },
      });

      if (!board) {
        throw new Error('Board not found or access denied');
      }

      // Cache the result
      await RedisService.setCache(`board:${boardId}`, board, 300);

      return board;
    } catch (error) {
      Logger.error('Get board failed', error as Error);
      throw error;
    }
  }

  /**
   * Update board
   */
  static async updateBoard(
    boardId: string,
    userId: string,
    data: Partial<CreateBoardData>
  ): Promise<any> {
    try {
      // Verify user has permission to edit
      const hasPermission = await this.verifyBoardPermission(boardId, userId, 'canEdit');
      if (!hasPermission) {
        throw new Error('Permission denied');
      }

      const board = await prisma.board.update({
        where: { id: boardId },
        data: {
          ...data,
          updatedAt: new Date(),
        },
        include: {
          workspace: {
            select: { id: true, name: true, organizationId: true },
          },
          folder: {
            select: { id: true, name: true },
          },
          members: {
            include: {
              user: {
                select: { id: true, email: true, firstName: true, lastName: true, avatarUrl: true },
              },
            },
          },
          columns: {
            orderBy: { position: 'asc' },
          },
        },
      });

      // Invalidate cache
      await RedisService.deleteCache(`board:${boardId}`);

      Logger.api(`Board updated: ${board.name}`, { boardId, userId });

      return board;
    } catch (error) {
      Logger.error('Board update failed', error as Error);
      throw error;
    }
  }

  /**
   * Delete board (soft delete)
   */
  static async deleteBoard(boardId: string, userId: string): Promise<void> {
    try {
      // Verify user has permission to delete
      const hasPermission = await this.verifyBoardPermission(boardId, userId, 'canDelete');
      if (!hasPermission) {
        throw new Error('Permission denied');
      }

      await prisma.board.update({
        where: { id: boardId },
        data: { deletedAt: new Date() },
      });

      // Invalidate cache
      await RedisService.deleteCache(`board:${boardId}`);

      Logger.api(`Board deleted: ${boardId}`, { boardId, userId });
    } catch (error) {
      Logger.error('Board deletion failed', error as Error);
      throw error;
    }
  }

  /**
   * Get boards in workspace
   */
  static async getWorkspaceBoards(
    workspaceId: string,
    userId: string,
    filter: BoardFilter = {},
    sort: SortOption[] = [{ field: 'position', direction: 'asc' }],
    page: number = 1,
    limit: number = 20
  ): Promise<PaginatedResult<any>> {
    try {
      const offset = (page - 1) * limit;

      // Build where condition
      const where: any = {
        workspaceId,
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

      if (filter.folderId) {
        where.folderId = filter.folderId;
      }

      if (filter.isPrivate !== undefined) {
        where.isPrivate = filter.isPrivate;
      }

      // Build order by
      const orderBy = sort.map((s) => ({ [s.field]: s.direction }));

      const [boards, total] = await Promise.all([
        prisma.board.findMany({
          where,
          include: {
            folder: {
              select: { id: true, name: true },
            },
            members: {
              include: {
                user: {
                  select: { id: true, firstName: true, lastName: true, avatarUrl: true },
                },
              },
            },
            _count: {
              select: { items: true },
            },
          },
          orderBy,
          skip: offset,
          take: limit,
        }),
        prisma.board.count({ where }),
      ]);

      return {
        data: boards,
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
      Logger.error('Get workspace boards failed', error as Error);
      throw error;
    }
  }

  /**
   * Add member to board
   */
  static async addBoardMember(
    boardId: string,
    userId: string,
    memberUserId: string,
    role: string = 'member',
    permissions: Record<string, boolean> = {}
  ): Promise<any> {
    try {
      // Verify user has permission to manage members
      const hasPermission = await this.verifyBoardPermission(boardId, userId, 'canManageMembers');
      if (!hasPermission) {
        throw new Error('Permission denied');
      }

      // Check if member already exists
      const existingMember = await prisma.boardMember.findFirst({
        where: { boardId, userId: memberUserId },
      });

      if (existingMember) {
        throw new Error('User is already a member of this board');
      }

      const member = await prisma.boardMember.create({
        data: {
          boardId,
          userId: memberUserId,
          role,
          permissions: {
            canEdit: role === 'admin' || role === 'owner',
            canDelete: role === 'owner',
            canManageMembers: role === 'admin' || role === 'owner',
            canManageSettings: role === 'owner',
            ...permissions,
          },
        },
        include: {
          user: {
            select: { id: true, email: true, firstName: true, lastName: true, avatarUrl: true },
          },
        },
      });

      // Invalidate board cache
      await RedisService.deleteCache(`board:${boardId}`);

      Logger.api(`Board member added: ${memberUserId}`, { boardId, userId });

      return member;
    } catch (error) {
      Logger.error('Add board member failed', error as Error);
      throw error;
    }
  }

  /**
   * Remove member from board
   */
  static async removeBoardMember(
    boardId: string,
    userId: string,
    memberUserId: string
  ): Promise<void> {
    try {
      // Verify user has permission to manage members
      const hasPermission = await this.verifyBoardPermission(boardId, userId, 'canManageMembers');
      if (!hasPermission) {
        throw new Error('Permission denied');
      }

      // Cannot remove board owner
      const member = await prisma.boardMember.findFirst({
        where: { boardId, userId: memberUserId },
      });

      if (member?.role === 'owner') {
        throw new Error('Cannot remove board owner');
      }

      await prisma.boardMember.delete({
        where: {
          id: member?.id,
        },
      });

      // Invalidate board cache
      await RedisService.deleteCache(`board:${boardId}`);

      Logger.api(`Board member removed: ${memberUserId}`, { boardId, userId });
    } catch (error) {
      Logger.error('Remove board member failed', error as Error);
      throw error;
    }
  }

  /**
   * Create board column
   */
  static async createColumn(
    boardId: string,
    userId: string,
    data: {
      name: string;
      columnType: string;
      settings?: Record<string, any>;
      validationRules?: Record<string, any>;
      isRequired?: boolean;
      isVisible?: boolean;
    }
  ): Promise<any> {
    try {
      // Verify user has permission to edit
      const hasPermission = await this.verifyBoardPermission(boardId, userId, 'canEdit');
      if (!hasPermission) {
        throw new Error('Permission denied');
      }

      // Get next position
      const lastColumn = await prisma.boardColumn.findFirst({
        where: { boardId },
        orderBy: { position: 'desc' },
      });
      const position = (lastColumn?.position || 0) + 1;

      const column = await prisma.boardColumn.create({
        data: {
          id: uuidv4(),
          boardId,
          name: data.name,
          columnType: data.columnType,
          settings: data.settings || {},
          validationRules: data.validationRules || {},
          position,
          isRequired: data.isRequired || false,
          isVisible: data.isVisible !== false,
        },
      });

      // Invalidate board cache
      await RedisService.deleteCache(`board:${boardId}`);

      Logger.api(`Board column created: ${column.name}`, { boardId, columnId: column.id, userId });

      return column;
    } catch (error) {
      Logger.error('Create board column failed', error as Error);
      throw error;
    }
  }

  /**
   * Update board column
   */
  static async updateColumn(
    columnId: string,
    userId: string,
    data: Partial<{
      name: string;
      settings: Record<string, any>;
      validationRules: Record<string, any>;
      isRequired: boolean;
      isVisible: boolean;
      position: number;
    }>
  ): Promise<any> {
    try {
      // Get column to verify board access
      const column = await prisma.boardColumn.findUnique({
        where: { id: columnId },
        include: { board: true },
      });

      if (!column) {
        throw new Error('Column not found');
      }

      // Verify user has permission to edit
      const hasPermission = await this.verifyBoardPermission(column.boardId, userId, 'canEdit');
      if (!hasPermission) {
        throw new Error('Permission denied');
      }

      const updatedColumn = await prisma.boardColumn.update({
        where: { id: columnId },
        data: {
          ...data,
          updatedAt: new Date(),
        },
      });

      // Invalidate board cache
      await RedisService.deleteCache(`board:${column.boardId}`);

      Logger.api(`Board column updated: ${updatedColumn.name}`, {
        boardId: column.boardId,
        columnId,
        userId,
      });

      return updatedColumn;
    } catch (error) {
      Logger.error('Update board column failed', error as Error);
      throw error;
    }
  }

  /**
   * Delete board column
   */
  static async deleteColumn(columnId: string, userId: string): Promise<void> {
    try {
      // Get column to verify board access
      const column = await prisma.boardColumn.findUnique({
        where: { id: columnId },
        include: { board: true },
      });

      if (!column) {
        throw new Error('Column not found');
      }

      // Verify user has permission to edit
      const hasPermission = await this.verifyBoardPermission(column.boardId, userId, 'canEdit');
      if (!hasPermission) {
        throw new Error('Permission denied');
      }

      await prisma.boardColumn.delete({
        where: { id: columnId },
      });

      // Invalidate board cache
      await RedisService.deleteCache(`board:${column.boardId}`);

      Logger.api(`Board column deleted: ${columnId}`, {
        boardId: column.boardId,
        columnId,
        userId,
      });
    } catch (error) {
      Logger.error('Delete board column failed', error as Error);
      throw error;
    }
  }

  // ============================================================================
  // PRIVATE HELPER METHODS
  // ============================================================================

  /**
   * Verify board access for user
   */
  private static async verifyBoardAccess(boardId: string, userId: string): Promise<boolean> {
    try {
      const access = await prisma.board.findFirst({
        where: {
          id: boardId,
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
                  some: {
                    userId,
                    role: { in: ['admin', 'member'] },
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
   * Verify board permission for user
   */
  private static async verifyBoardPermission(
    boardId: string,
    userId: string,
    permission: string
  ): Promise<boolean> {
    try {
      const member = await prisma.boardMember.findFirst({
        where: { boardId, userId },
      });

      if (!member) {
        // Check workspace-level permission
        const board = await prisma.board.findUnique({
          where: { id: boardId },
          include: {
            workspace: {
              include: {
                members: {
                  where: { userId },
                },
              },
            },
          },
        });

        const workspaceMember = board?.workspace.members[0];
        if (workspaceMember?.role === 'admin') {
          return true;
        }

        return false;
      }

      // Check board-level permission
      const permissions = member.permissions as Record<string, boolean>;
      return permissions[permission] === true;
    } catch (error) {
      return false;
    }
  }

  /**
   * Create default columns for a new board
   */
  private static async createDefaultColumns(boardId: string): Promise<void> {
    const defaultColumns = [
      { name: 'Item', columnType: 'text', position: 1, isRequired: true },
      { name: 'Person', columnType: 'people', position: 2 },
      { name: 'Status', columnType: 'status', position: 3, settings: {
        options: [
          { label: 'Not Started', color: '#C4C4C4' },
          { label: 'Working on it', color: '#FDAC3A' },
          { label: 'Done', color: '#00C875' },
        ]
      }},
      { name: 'Priority', columnType: 'dropdown', position: 4, settings: {
        options: [
          { label: 'Critical', color: '#E2445C' },
          { label: 'High', color: '#FF642E' },
          { label: 'Medium', color: '#FDAC3A' },
          { label: 'Low', color: '#579BFC' },
        ]
      }},
      { name: 'Due Date', columnType: 'date', position: 5 },
    ];

    for (const column of defaultColumns) {
      await prisma.boardColumn.create({
        data: {
          id: uuidv4(),
          boardId,
          ...column,
        },
      });
    }
  }

  /**
   * Create columns from template
   */
  private static async createDefaultColumnsFromTemplate(
    boardId: string,
    templateId: string
  ): Promise<void> {
    try {
      const template = await prisma.boardTemplate.findUnique({
        where: { id: templateId },
      });

      if (!template) {
        // Fallback to default columns
        await this.createDefaultColumns(boardId);
        return;
      }

      const templateData = template.templateData as any;
      const columns = templateData.columns || [];

      for (const column of columns) {
        await prisma.boardColumn.create({
          data: {
            id: uuidv4(),
            boardId,
            name: column.name,
            columnType: column.columnType,
            settings: column.settings || {},
            validationRules: column.validationRules || {},
            position: column.position,
            isRequired: column.isRequired || false,
            isVisible: column.isVisible !== false,
          },
        });
      }
    } catch (error) {
      Logger.error('Create columns from template failed', error as Error);
      // Fallback to default columns
      await this.createDefaultColumns(boardId);
    }
  }
}