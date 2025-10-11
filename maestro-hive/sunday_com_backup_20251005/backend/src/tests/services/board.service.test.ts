import { describe, it, expect, beforeEach, afterEach, vi, beforeAll, afterAll } from 'vitest';
import { BoardService } from '@/services/board.service';
import { prisma } from '@/config/database';
import { RedisService } from '@/config/redis';

// Mock dependencies
vi.mock('@/config/database', () => ({
  prisma: {
    board: {
      create: vi.fn(),
      findFirst: vi.fn(),
      findUnique: vi.fn(),
      findMany: vi.fn(),
      update: vi.fn(),
      count: vi.fn(),
    },
    boardMember: {
      create: vi.fn(),
      findFirst: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      count: vi.fn(),
    },
    boardColumn: {
      create: vi.fn(),
      findFirst: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      findMany: vi.fn(),
    },
    workspace: {
      findFirst: vi.fn(),
    },
    user: {
      findUnique: vi.fn(),
    },
    $transaction: vi.fn(),
  },
}));

vi.mock('@/config/redis', () => ({
  RedisService: {
    setCache: vi.fn(),
    getCache: vi.fn(),
    deleteCache: vi.fn(),
    deleteCachePattern: vi.fn(),
  },
}));

vi.mock('@/config/logger', () => ({
  Logger: {
    api: vi.fn(),
    error: vi.fn(),
  },
}));

describe('BoardService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('createBoard', () => {
    const mockWorkspace = {
      id: 'workspace-1',
      name: 'Test Workspace',
      organization: {
        id: 'org-1',
        name: 'Test Organization',
      },
    };

    const mockBoardData = {
      name: 'Test Board',
      description: 'Test Description',
      isPrivate: false,
    };

    const mockCreatedBoard = {
      id: 'board-1',
      name: 'Test Board',
      description: 'Test Description',
      workspaceId: 'workspace-1',
      position: 1,
      createdBy: 'user-1',
      workspace: mockWorkspace,
      folder: null,
    };

    it('should create a board successfully', async () => {
      // Setup mocks
      (prisma.workspace.findFirst as any).mockResolvedValue(mockWorkspace);
      (prisma.board.findFirst as any).mockResolvedValue(null); // No existing boards
      (prisma.$transaction as any).mockImplementation(async (callback) => {
        return callback({
          board: {
            create: vi.fn().mockResolvedValue(mockCreatedBoard),
          },
          boardMember: {
            create: vi.fn().mockResolvedValue({}),
          },
        });
      });
      (BoardService.getBoard as any) = vi.fn().mockResolvedValue(mockCreatedBoard);
      (RedisService.setCache as any).mockResolvedValue(undefined);

      const result = await BoardService.createBoard('workspace-1', 'user-1', mockBoardData);

      expect(result).toEqual(mockCreatedBoard);
      expect(prisma.workspace.findFirst).toHaveBeenCalledWith({
        where: {
          id: 'workspace-1',
          OR: [
            { isPrivate: false },
            {
              members: {
                some: {
                  userId: 'user-1',
                  role: { in: ['admin', 'member'] },
                },
              },
            },
          ],
        },
        include: {
          organization: {
            select: { id: true, name: true },
          },
        },
      });
    });

    it('should throw error if workspace not found', async () => {
      (prisma.workspace.findFirst as any).mockResolvedValue(null);

      await expect(
        BoardService.createBoard('workspace-1', 'user-1', mockBoardData)
      ).rejects.toThrow('Workspace not found or access denied');
    });

    it('should calculate correct position for new board', async () => {
      const lastBoard = { position: 5 };
      (prisma.workspace.findFirst as any).mockResolvedValue(mockWorkspace);
      (prisma.board.findFirst as any).mockResolvedValue(lastBoard);

      const boardWithPosition = { ...mockCreatedBoard, position: 6 };
      (prisma.$transaction as any).mockImplementation(async (callback) => {
        return callback({
          board: {
            create: vi.fn().mockResolvedValue(boardWithPosition),
          },
          boardMember: {
            create: vi.fn().mockResolvedValue({}),
          },
        });
      });
      (BoardService.getBoard as any) = vi.fn().mockResolvedValue(boardWithPosition);

      const result = await BoardService.createBoard('workspace-1', 'user-1', mockBoardData);

      expect(result.position).toBe(6);
    });
  });

  describe('getBoard', () => {
    const mockBoard = {
      id: 'board-1',
      name: 'Test Board',
      workspaceId: 'workspace-1',
      isPrivate: false,
      deletedAt: null,
      workspace: { id: 'workspace-1', name: 'Test Workspace' },
      members: [],
      columns: [],
      items: [],
      createdByUser: { id: 'user-1', firstName: 'John', lastName: 'Doe' },
      _count: { items: 0, members: 1 },
    };

    it('should get board successfully with cache miss', async () => {
      (RedisService.getCache as any).mockResolvedValue(null);
      (prisma.board.findFirst as any).mockResolvedValue(mockBoard);
      (BoardService.getUserBoardRole as any) = vi.fn().mockResolvedValue({
        role: 'owner',
        permissions: { canEdit: true },
      });
      (RedisService.setCache as any).mockResolvedValue(undefined);

      const result = await BoardService.getBoard('board-1', 'user-1');

      expect(result).toEqual({
        ...mockBoard,
        userRole: { role: 'owner', permissions: { canEdit: true } },
        userPermissions: { canEdit: true },
      });
      expect(RedisService.getCache).toHaveBeenCalled();
      expect(prisma.board.findFirst).toHaveBeenCalled();
      expect(RedisService.setCache).toHaveBeenCalled();
    });

    it('should return cached board if available', async () => {
      const cachedBoard = { ...mockBoard, cached: true };
      (RedisService.getCache as any).mockResolvedValue(cachedBoard);

      const result = await BoardService.getBoard('board-1', 'user-1');

      expect(result).toEqual(cachedBoard);
      expect(prisma.board.findFirst).not.toHaveBeenCalled();
    });

    it('should throw error if board not found', async () => {
      (RedisService.getCache as any).mockResolvedValue(null);
      (prisma.board.findFirst as any).mockResolvedValue(null);

      await expect(
        BoardService.getBoard('board-1', 'user-1')
      ).rejects.toThrow('Board not found or access denied');
    });
  });

  describe('updateBoard', () => {
    const mockBoard = {
      id: 'board-1',
      name: 'Updated Board',
      description: 'Updated Description',
      workspaceId: 'workspace-1',
    };

    const updateData = {
      name: 'Updated Board',
      description: 'Updated Description',
    };

    it('should update board successfully', async () => {
      (BoardService.verifyBoardPermission as any) = vi.fn().mockResolvedValue(true);
      (prisma.board.findUnique as any).mockResolvedValue({
        name: 'Old Board',
        workspaceId: 'workspace-1',
      });
      (prisma.board.update as any).mockResolvedValue(mockBoard);
      (BoardService.invalidateBoardCaches as any) = vi.fn().mockResolvedValue(undefined);
      (BoardService.logBoardEvent as any) = vi.fn().mockResolvedValue(undefined);

      const result = await BoardService.updateBoard('board-1', 'user-1', updateData);

      expect(result).toEqual(mockBoard);
      expect(prisma.board.update).toHaveBeenCalledWith({
        where: { id: 'board-1' },
        data: {
          ...updateData,
          updatedAt: expect.any(Date),
        },
        include: expect.any(Object),
      });
    });

    it('should throw error if permission denied', async () => {
      (BoardService.verifyBoardPermission as any) = vi.fn().mockResolvedValue(false);

      await expect(
        BoardService.updateBoard('board-1', 'user-1', updateData)
      ).rejects.toThrow('Permission denied');
    });

    it('should throw error if board not found', async () => {
      (BoardService.verifyBoardPermission as any) = vi.fn().mockResolvedValue(true);
      (prisma.board.findUnique as any).mockResolvedValue(null);

      await expect(
        BoardService.updateBoard('board-1', 'user-1', updateData)
      ).rejects.toThrow('Board not found');
    });
  });

  describe('deleteBoard', () => {
    const mockBoard = {
      name: 'Test Board',
      workspaceId: 'workspace-1',
      _count: { items: 5 },
    };

    it('should delete board successfully', async () => {
      (BoardService.verifyBoardPermission as any) = vi.fn().mockResolvedValue(true);
      (prisma.board.findUnique as any).mockResolvedValue(mockBoard);
      (prisma.$transaction as any).mockImplementation(async (callback) => {
        return callback({
          item: {
            updateMany: vi.fn().mockResolvedValue({}),
          },
          board: {
            update: vi.fn().mockResolvedValue({}),
          },
        });
      });
      (BoardService.invalidateBoardCaches as any) = vi.fn().mockResolvedValue(undefined);
      (BoardService.logBoardEvent as any) = vi.fn().mockResolvedValue(undefined);

      await BoardService.deleteBoard('board-1', 'user-1');

      expect(prisma.$transaction).toHaveBeenCalled();
    });

    it('should throw error if permission denied', async () => {
      (BoardService.verifyBoardPermission as any) = vi.fn().mockResolvedValue(false);

      await expect(
        BoardService.deleteBoard('board-1', 'user-1')
      ).rejects.toThrow('Permission denied');
    });
  });

  describe('getWorkspaceBoards', () => {
    const mockBoards = [
      {
        id: 'board-1',
        name: 'Board 1',
        workspaceId: 'workspace-1',
        position: 1,
      },
      {
        id: 'board-2',
        name: 'Board 2',
        workspaceId: 'workspace-1',
        position: 2,
      },
    ];

    it('should get workspace boards with pagination', async () => {
      (BoardService.verifyWorkspaceAccess as any) = vi.fn().mockResolvedValue(true);
      (prisma.board.findMany as any).mockResolvedValue(mockBoards);
      (prisma.board.count as any).mockResolvedValue(2);

      const result = await BoardService.getWorkspaceBoards(
        'workspace-1',
        'user-1',
        {},
        [{ field: 'position', direction: 'asc' }],
        1,
        20
      );

      expect(result.data).toEqual(mockBoards);
      expect(result.meta).toEqual({
        page: 1,
        limit: 20,
        total: 2,
        totalPages: 1,
        hasNext: false,
        hasPrev: false,
      });
    });

    it('should apply filters correctly', async () => {
      (BoardService.verifyWorkspaceAccess as any) = vi.fn().mockResolvedValue(true);
      (prisma.board.findMany as any).mockResolvedValue([mockBoards[0]]);
      (prisma.board.count as any).mockResolvedValue(1);

      const filter = { name: 'Board 1', isPrivate: false };
      await BoardService.getWorkspaceBoards('workspace-1', 'user-1', filter);

      expect(prisma.board.findMany).toHaveBeenCalledWith({
        where: expect.objectContaining({
          workspaceId: 'workspace-1',
          deletedAt: null,
          name: { contains: 'Board 1', mode: 'insensitive' },
          isPrivate: false,
        }),
        include: expect.any(Object),
        orderBy: expect.any(Array),
        skip: 0,
        take: 20,
      });
    });

    it('should throw error if workspace access denied', async () => {
      (BoardService.verifyWorkspaceAccess as any) = vi.fn().mockResolvedValue(false);

      await expect(
        BoardService.getWorkspaceBoards('workspace-1', 'user-1')
      ).rejects.toThrow('Workspace not found or access denied');
    });
  });

  describe('addBoardMember', () => {
    const mockMember = {
      id: 'member-1',
      boardId: 'board-1',
      userId: 'user-2',
      role: 'member',
      permissions: { canEdit: true },
      user: {
        id: 'user-2',
        email: 'user2@example.com',
        firstName: 'Jane',
        lastName: 'Doe',
      },
    };

    it('should add board member successfully', async () => {
      (BoardService.verifyBoardPermission as any) = vi.fn().mockResolvedValue(true);
      (prisma.boardMember.findFirst as any).mockResolvedValue(null); // No existing member
      (prisma.user.findUnique as any).mockResolvedValue({ id: 'user-2' });
      (BoardService.getRolePermissions as any) = vi.fn().mockReturnValue({ canEdit: true });
      (prisma.boardMember.create as any).mockResolvedValue(mockMember);
      (BoardService.invalidateBoardCaches as any) = vi.fn().mockResolvedValue(undefined);
      (BoardService.logBoardEvent as any) = vi.fn().mockResolvedValue(undefined);

      const result = await BoardService.addBoardMember('board-1', 'user-1', 'user-2', 'member');

      expect(result).toEqual(mockMember);
      expect(prisma.boardMember.create).toHaveBeenCalledWith({
        data: {
          boardId: 'board-1',
          userId: 'user-2',
          role: 'member',
          permissions: { canEdit: true },
        },
        include: expect.any(Object),
      });
    });

    it('should throw error if user already a member', async () => {
      (BoardService.verifyBoardPermission as any) = vi.fn().mockResolvedValue(true);
      (prisma.boardMember.findFirst as any).mockResolvedValue(mockMember);

      await expect(
        BoardService.addBoardMember('board-1', 'user-1', 'user-2', 'member')
      ).rejects.toThrow('User is already a member of this board');
    });

    it('should throw error if user not found', async () => {
      (BoardService.verifyBoardPermission as any) = vi.fn().mockResolvedValue(true);
      (prisma.boardMember.findFirst as any).mockResolvedValue(null);
      (prisma.user.findUnique as any).mockResolvedValue(null);

      await expect(
        BoardService.addBoardMember('board-1', 'user-1', 'user-2', 'member')
      ).rejects.toThrow('User not found');
    });
  });

  describe('createColumn', () => {
    const mockColumn = {
      id: 'column-1',
      boardId: 'board-1',
      name: 'Test Column',
      columnType: 'text',
      position: 1,
      color: '#FF0000',
    };

    const columnData = {
      name: 'Test Column',
      color: '#FF0000',
    };

    it('should create column successfully', async () => {
      (BoardService.verifyBoardPermission as any) = vi.fn().mockResolvedValue(true);
      (prisma.boardColumn.findFirst as any).mockResolvedValue(null); // No existing columns
      (prisma.boardColumn.create as any).mockResolvedValue(mockColumn);
      (BoardService.invalidateBoardCaches as any) = vi.fn().mockResolvedValue(undefined);
      (BoardService.logBoardEvent as any) = vi.fn().mockResolvedValue(undefined);

      const result = await BoardService.createColumn('board-1', 'user-1', columnData);

      expect(result).toEqual(mockColumn);
      expect(prisma.boardColumn.create).toHaveBeenCalledWith({
        data: {
          id: expect.any(String),
          boardId: 'board-1',
          name: 'Test Column',
          columnType: 'text',
          settings: {},
          validationRules: {},
          position: 1,
          isRequired: false,
          isVisible: true,
          color: '#FF0000',
        },
      });
    });

    it('should calculate correct position when columns exist', async () => {
      const lastColumn = { position: 3 };
      (BoardService.verifyBoardPermission as any) = vi.fn().mockResolvedValue(true);
      (prisma.boardColumn.findFirst as any).mockResolvedValue(lastColumn);
      (prisma.boardColumn.create as any).mockResolvedValue({
        ...mockColumn,
        position: 4,
      });
      (BoardService.invalidateBoardCaches as any) = vi.fn().mockResolvedValue(undefined);
      (BoardService.logBoardEvent as any) = vi.fn().mockResolvedValue(undefined);

      const result = await BoardService.createColumn('board-1', 'user-1', columnData);

      expect(result.position).toBe(4);
    });

    it('should throw error if permission denied', async () => {
      (BoardService.verifyBoardPermission as any) = vi.fn().mockResolvedValue(false);

      await expect(
        BoardService.createColumn('board-1', 'user-1', columnData)
      ).rejects.toThrow('Permission denied');
    });
  });

  describe('reorderColumns', () => {
    const columnOrders = [
      { id: 'column-1', position: 2 },
      { id: 'column-2', position: 1 },
    ];

    const updatedColumns = [
      { id: 'column-1', position: 2 },
      { id: 'column-2', position: 1 },
    ];

    it('should reorder columns successfully', async () => {
      (BoardService.verifyBoardPermission as any) = vi.fn().mockResolvedValue(true);
      (prisma.$transaction as any).mockResolvedValue(updatedColumns);
      (BoardService.invalidateBoardCaches as any) = vi.fn().mockResolvedValue(undefined);
      (BoardService.logBoardEvent as any) = vi.fn().mockResolvedValue(undefined);

      const result = await BoardService.reorderColumns('board-1', 'user-1', columnOrders);

      expect(result).toEqual(updatedColumns);
      expect(prisma.$transaction).toHaveBeenCalled();
    });

    it('should throw error if permission denied', async () => {
      (BoardService.verifyBoardPermission as any) = vi.fn().mockResolvedValue(false);

      await expect(
        BoardService.reorderColumns('board-1', 'user-1', columnOrders)
      ).rejects.toThrow('Permission denied');
    });
  });
});