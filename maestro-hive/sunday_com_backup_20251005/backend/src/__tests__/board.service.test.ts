import { prismaMock } from './setup';
import { BoardService } from '@/services/board.service';
import { RedisService } from '@/config/redis';

// Mock Redis
jest.mock('@/config/redis', () => ({
  RedisService: {
    getCache: jest.fn(),
    setCache: jest.fn(),
    deleteCache: jest.fn(),
    deleteCachePattern: jest.fn(),
  },
}));

// Mock Socket.io
jest.mock('@/server', () => ({
  io: {
    to: jest.fn(() => ({
      emit: jest.fn(),
    })),
  },
}));

describe('BoardService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('create', () => {
    it('should create a board successfully', async () => {
      const mockWorkspace = {
        id: 'workspace-1',
        members: [{ userId: 'user-1' }],
        isPrivate: false,
      };

      const mockBoard = {
        id: 'board-1',
        name: 'Test Board',
        workspaceId: 'workspace-1',
        createdBy: 'user-1',
        columns: [],
        members: [{
          id: 'member-1',
          userId: 'user-1',
          role: 'admin',
          user: { firstName: 'John' },
        }],
        creator: { firstName: 'John' },
        _count: { items: 0, members: 1, columns: 0 },
      };

      prismaMock.workspace.findUnique.mockResolvedValue(mockWorkspace as any);
      prismaMock.board.create.mockResolvedValue(mockBoard as any);

      const result = await BoardService.create({
        name: 'Test Board',
        workspaceId: 'workspace-1',
        description: 'Test description',
      }, 'user-1');

      expect(result.id).toBe('board-1');
      expect(result.name).toBe('Test Board');
      expect(prismaMock.board.create).toHaveBeenCalledWith({
        data: {
          name: 'Test Board',
          workspaceId: 'workspace-1',
          description: 'Test description',
          createdBy: 'user-1',
          members: {
            create: {
              userId: 'user-1',
              role: 'admin',
            },
          },
          columns: undefined,
        },
        include: expect.any(Object),
      });
    });

    it('should throw error if workspace not found', async () => {
      prismaMock.workspace.findUnique.mockResolvedValue(null);

      await expect(
        BoardService.create({
          name: 'Test Board',
          workspaceId: 'workspace-1',
        }, 'user-1')
      ).rejects.toThrow('Workspace not found');
    });

    it('should throw error if access denied to private workspace', async () => {
      const mockWorkspace = {
        id: 'workspace-1',
        members: [],
        isPrivate: true,
      };

      prismaMock.workspace.findUnique.mockResolvedValue(mockWorkspace as any);

      await expect(
        BoardService.create({
          name: 'Test Board',
          workspaceId: 'workspace-1',
        }, 'user-1')
      ).rejects.toThrow('Access denied to private workspace');
    });
  });

  describe('getById', () => {
    it('should return board when user has access', async () => {
      const mockBoard = {
        id: 'board-1',
        name: 'Test Board',
        isPrivate: false,
        deletedAt: null,
        columns: [],
        creator: { firstName: 'John' },
        _count: { items: 0, members: 1, columns: 0 },
      };

      (RedisService.getCache as jest.Mock).mockResolvedValue(null);
      prismaMock.board.findFirst.mockResolvedValue(mockBoard as any);
      (RedisService.setCache as jest.Mock).mockResolvedValue(undefined);

      const result = await BoardService.getById('board-1', 'user-1');

      expect(result).toEqual(mockBoard);
      expect(prismaMock.board.findFirst).toHaveBeenCalledWith({
        where: {
          id: 'board-1',
          deletedAt: null,
          OR: expect.any(Array),
        },
        include: expect.any(Object),
      });
    });

    it('should return cached board data', async () => {
      const mockBoard = { id: 'board-1', name: 'Test Board' };
      (RedisService.getCache as jest.Mock).mockResolvedValue(mockBoard);

      const result = await BoardService.getById('board-1', 'user-1');

      expect(result).toEqual(mockBoard);
      expect(prismaMock.board.findFirst).not.toHaveBeenCalled();
    });
  });

  describe('update', () => {
    it('should update board when user has write access', async () => {
      const mockUpdatedBoard = {
        id: 'board-1',
        name: 'Updated Board',
        columns: [],
        creator: { firstName: 'John' },
        _count: { items: 0, members: 1, columns: 0 },
      };

      // Mock hasWriteAccess to return true
      jest.spyOn(BoardService, 'hasWriteAccess').mockResolvedValue(true);
      prismaMock.board.update.mockResolvedValue(mockUpdatedBoard as any);

      const result = await BoardService.update('board-1', {
        name: 'Updated Board',
      }, 'user-1');

      expect(result.name).toBe('Updated Board');
      expect(BoardService.hasWriteAccess).toHaveBeenCalledWith('board-1', 'user-1');
    });

    it('should throw error when user lacks write access', async () => {
      jest.spyOn(BoardService, 'hasWriteAccess').mockResolvedValue(false);

      await expect(
        BoardService.update('board-1', { name: 'Updated Board' }, 'user-1')
      ).rejects.toThrow('Access denied');
    });
  });

  describe('delete', () => {
    it('should soft delete board when user has admin access', async () => {
      jest.spyOn(BoardService, 'hasAdminAccess').mockResolvedValue(true);
      prismaMock.board.update.mockResolvedValue({ id: 'board-1' } as any);

      await BoardService.delete('board-1', 'user-1');

      expect(prismaMock.board.update).toHaveBeenCalledWith({
        where: { id: 'board-1' },
        data: { deletedAt: expect.any(Date) },
      });
    });

    it('should throw error when user lacks admin access', async () => {
      jest.spyOn(BoardService, 'hasAdminAccess').mockResolvedValue(false);

      await expect(
        BoardService.delete('board-1', 'user-1')
      ).rejects.toThrow('Access denied');
    });
  });

  describe('createColumn', () => {
    it('should create column when user has write access', async () => {
      const mockColumn = {
        id: 'column-1',
        name: 'To Do',
        boardId: 'board-1',
        position: 1,
      };

      jest.spyOn(BoardService, 'hasWriteAccess').mockResolvedValue(true);
      jest.spyOn(BoardService as any, 'getNextColumnPosition').mockResolvedValue(1);
      prismaMock.boardColumn.create.mockResolvedValue(mockColumn as any);

      const result = await BoardService.createColumn('board-1', {
        name: 'To Do',
        color: '#blue',
      }, 'user-1');

      expect(result.name).toBe('To Do');
      expect(prismaMock.boardColumn.create).toHaveBeenCalledWith({
        data: {
          name: 'To Do',
          color: '#blue',
          boardId: 'board-1',
          position: 1,
        },
      });
    });
  });

  describe('addMember', () => {
    it('should add member when user has admin access', async () => {
      const mockMember = {
        id: 'member-1',
        boardId: 'board-1',
        userId: 'user-2',
        role: 'member',
      };

      jest.spyOn(BoardService, 'hasAdminAccess').mockResolvedValue(true);
      prismaMock.boardMember.findUnique.mockResolvedValue(null);
      prismaMock.boardMember.create.mockResolvedValue(mockMember as any);

      const result = await BoardService.addMember('board-1', 'user-2', 'member', {}, 'user-1');

      expect(result.userId).toBe('user-2');
      expect(result.role).toBe('member');
    });

    it('should throw error if user is already a member', async () => {
      jest.spyOn(BoardService, 'hasAdminAccess').mockResolvedValue(true);
      prismaMock.boardMember.findUnique.mockResolvedValue({ id: 'existing-member' } as any);

      await expect(
        BoardService.addMember('board-1', 'user-2', 'member', {}, 'user-1')
      ).rejects.toThrow('User is already a member of this board');
    });
  });

  describe('getStatistics', () => {
    it('should return board statistics', async () => {
      const mockStats = [{
        totalItems: BigInt(10),
        completedItems: BigInt(5),
        totalMembers: BigInt(3),
        totalColumns: BigInt(4),
        activeMembersToday: BigInt(2),
      }];

      prismaMock.$queryRaw.mockResolvedValue(mockStats);

      const result = await BoardService.getStatistics('board-1');

      expect(result.totalItems).toBe(10);
      expect(result.completedItems).toBe(5);
      expect(result.totalMembers).toBe(3);
      expect(result.totalColumns).toBe(4);
      expect(result.activeMembersToday).toBe(2);
    });
  });
});