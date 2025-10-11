import { prismaMock } from './setup';
import { ItemService } from '@/services/item.service';
import { RedisService } from '@/config/redis';
import { Decimal } from '@prisma/client/runtime/library';

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

// Mock BoardService
jest.mock('@/services/board.service', () => ({
  BoardService: {
    hasReadAccess: jest.fn(),
  },
}));

describe('ItemService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('create', () => {
    it('should create an item successfully', async () => {
      const mockItem = {
        id: 'item-1',
        name: 'Test Item',
        description: 'Test description',
        boardId: 'board-1',
        position: new Decimal(1),
        createdBy: 'user-1',
        assignments: [],
        parent: null,
        creator: { firstName: 'John' },
        _count: { comments: 0, children: 0, dependencies: 0 },
      };

      // Mock board access check
      jest.spyOn(ItemService as any, 'checkBoardAccess').mockResolvedValue(true);
      jest.spyOn(ItemService as any, 'getNextPosition').mockResolvedValue(new Decimal(1));
      prismaMock.item.create.mockResolvedValue(mockItem as any);

      // Mock activity logging
      jest.spyOn(ItemService as any, 'logActivity').mockResolvedValue(undefined);

      const result = await ItemService.create({
        name: 'Test Item',
        description: 'Test description',
        boardId: 'board-1',
      }, 'user-1');

      expect(result.id).toBe('item-1');
      expect(result.name).toBe('Test Item');
      expect(prismaMock.item.create).toHaveBeenCalledWith({
        data: {
          name: 'Test Item',
          description: 'Test description',
          boardId: 'board-1',
          parentId: undefined,
          itemData: {},
          position: new Decimal(1),
          createdBy: 'user-1',
          assignments: undefined,
        },
        include: expect.any(Object),
      });
    });

    it('should create an item with assignees', async () => {
      const mockItem = {
        id: 'item-1',
        name: 'Test Item',
        boardId: 'board-1',
        position: new Decimal(1),
        createdBy: 'user-1',
        assignments: [
          { userId: 'user-2', user: { firstName: 'Jane' } }
        ],
        parent: null,
        creator: { firstName: 'John' },
        _count: { comments: 0, children: 0, dependencies: 0 },
      };

      jest.spyOn(ItemService as any, 'checkBoardAccess').mockResolvedValue(true);
      jest.spyOn(ItemService as any, 'getNextPosition').mockResolvedValue(new Decimal(1));
      prismaMock.item.create.mockResolvedValue(mockItem as any);
      jest.spyOn(ItemService as any, 'logActivity').mockResolvedValue(undefined);

      const result = await ItemService.create({
        name: 'Test Item',
        boardId: 'board-1',
        assigneeIds: ['user-2'],
      }, 'user-1');

      expect(result.assignments).toHaveLength(1);
      expect(result.assignments![0].userId).toBe('user-2');
    });

    it('should throw error if access denied to board', async () => {
      jest.spyOn(ItemService as any, 'checkBoardAccess').mockResolvedValue(false);

      await expect(
        ItemService.create({
          name: 'Test Item',
          boardId: 'board-1',
        }, 'user-1')
      ).rejects.toThrow('Access denied to board');
    });
  });

  describe('getById', () => {
    it('should return item when user has access', async () => {
      const mockItem = {
        id: 'item-1',
        name: 'Test Item',
        deletedAt: null,
        board: {
          isPrivate: false,
          members: [{ userId: 'user-1' }],
        },
        assignments: [],
        parent: null,
        creator: { firstName: 'John' },
        _count: { comments: 0, children: 0, dependencies: 0 },
      };

      (RedisService.getCache as jest.Mock).mockResolvedValue(null);
      prismaMock.item.findFirst.mockResolvedValue(mockItem as any);
      (RedisService.setCache as jest.Mock).mockResolvedValue(undefined);

      const result = await ItemService.getById('item-1', 'user-1');

      expect(result).toEqual(mockItem);
      expect(prismaMock.item.findFirst).toHaveBeenCalledWith({
        where: {
          id: 'item-1',
          deletedAt: null,
          board: {
            OR: expect.any(Array),
          },
        },
        include: expect.any(Object),
      });
    });

    it('should return cached item data', async () => {
      const mockItem = { id: 'item-1', name: 'Test Item' };
      (RedisService.getCache as jest.Mock).mockResolvedValue(mockItem);

      const result = await ItemService.getById('item-1', 'user-1');

      expect(result).toEqual(mockItem);
      expect(prismaMock.item.findFirst).not.toHaveBeenCalled();
    });
  });

  describe('update', () => {
    it('should update item successfully', async () => {
      const mockCurrentItem = {
        id: 'item-1',
        name: 'Original Item',
        description: 'Original description',
        boardId: 'board-1',
        itemData: { status: 'In Progress' },
        assignments: [{ userId: 'user-2' }],
      };

      const mockUpdatedItem = {
        id: 'item-1',
        name: 'Updated Item',
        description: 'Updated description',
        boardId: 'board-1',
        itemData: { status: 'Done' },
        assignments: [{ userId: 'user-3', user: { firstName: 'Alice' } }],
        parent: null,
        creator: { firstName: 'John' },
        _count: { comments: 0, children: 0, dependencies: 0 },
      };

      prismaMock.item.findUnique.mockResolvedValue(mockCurrentItem as any);
      jest.spyOn(ItemService as any, 'checkBoardAccess').mockResolvedValue(true);
      prismaMock.item.update.mockResolvedValue(mockUpdatedItem as any);
      jest.spyOn(ItemService as any, 'logActivity').mockResolvedValue(undefined);
      jest.spyOn(ItemService as any, 'invalidateCaches').mockResolvedValue(undefined);

      const result = await ItemService.update('item-1', {
        name: 'Updated Item',
        description: 'Updated description',
        itemData: { status: 'Done' },
        assigneeIds: ['user-3'],
      }, 'user-1');

      expect(result.name).toBe('Updated Item');
      expect(result.description).toBe('Updated description');
    });

    it('should throw error if item not found', async () => {
      prismaMock.item.findUnique.mockResolvedValue(null);

      await expect(
        ItemService.update('item-1', { name: 'Updated Item' }, 'user-1')
      ).rejects.toThrow('Item not found');
    });

    it('should throw error if access denied', async () => {
      const mockItem = { id: 'item-1', boardId: 'board-1', assignments: [] };
      prismaMock.item.findUnique.mockResolvedValue(mockItem as any);
      jest.spyOn(ItemService as any, 'checkBoardAccess').mockResolvedValue(false);

      await expect(
        ItemService.update('item-1', { name: 'Updated Item' }, 'user-1')
      ).rejects.toThrow('Access denied');
    });
  });

  describe('delete', () => {
    it('should soft delete item successfully', async () => {
      const mockItem = {
        id: 'item-1',
        boardId: 'board-1',
        itemData: { status: 'In Progress' },
      };

      prismaMock.item.findUnique.mockResolvedValue(mockItem as any);
      jest.spyOn(ItemService as any, 'checkBoardAccess').mockResolvedValue(true);
      prismaMock.item.update.mockResolvedValue({ id: 'item-1' } as any);
      jest.spyOn(ItemService as any, 'logActivity').mockResolvedValue(undefined);
      jest.spyOn(ItemService as any, 'invalidateCaches').mockResolvedValue(undefined);

      await ItemService.delete('item-1', 'user-1');

      expect(prismaMock.item.update).toHaveBeenCalledWith({
        where: { id: 'item-1' },
        data: { deletedAt: expect.any(Date) },
      });
    });
  });

  describe('bulkUpdate', () => {
    it('should update multiple items successfully', async () => {
      jest.spyOn(ItemService, 'update')
        .mockResolvedValueOnce({ id: 'item-1' } as any)
        .mockResolvedValueOnce({ id: 'item-2' } as any);

      const result = await ItemService.bulkUpdate(
        ['item-1', 'item-2'],
        { itemData: { status: 'Done' } },
        'user-1'
      );

      expect(result.updatedCount).toBe(2);
      expect(result.errors).toHaveLength(0);
      expect(ItemService.update).toHaveBeenCalledTimes(2);
    });

    it('should handle partial failures', async () => {
      jest.spyOn(ItemService, 'update')
        .mockResolvedValueOnce({ id: 'item-1' } as any)
        .mockRejectedValueOnce(new Error('Access denied'));

      const result = await ItemService.bulkUpdate(
        ['item-1', 'item-2'],
        { itemData: { status: 'Done' } },
        'user-1'
      );

      expect(result.updatedCount).toBe(1);
      expect(result.errors).toHaveLength(1);
      expect(result.errors[0].itemId).toBe('item-2');
      expect(result.errors[0].error).toBe('Access denied');
    });
  });

  describe('bulkDelete', () => {
    it('should delete multiple items successfully', async () => {
      jest.spyOn(ItemService, 'delete')
        .mockResolvedValueOnce(undefined)
        .mockResolvedValueOnce(undefined);

      const result = await ItemService.bulkDelete(['item-1', 'item-2'], 'user-1');

      expect(result.deletedCount).toBe(2);
      expect(result.errors).toHaveLength(0);
    });
  });

  describe('addDependency', () => {
    it('should add dependency successfully', async () => {
      const mockPredecessor = { id: 'item-1', boardId: 'board-1' };
      const mockSuccessor = { id: 'item-2', boardId: 'board-1' };

      prismaMock.item.findUnique
        .mockResolvedValueOnce(mockPredecessor as any)
        .mockResolvedValueOnce(mockSuccessor as any);

      jest.spyOn(ItemService as any, 'checkBoardAccess').mockResolvedValue(true);
      jest.spyOn(ItemService as any, 'checkCircularDependency').mockResolvedValue(false);
      prismaMock.itemDependency.create.mockResolvedValue({ id: 'dep-1' } as any);
      jest.spyOn(ItemService as any, 'invalidateCaches').mockResolvedValue(undefined);

      await ItemService.addDependency('item-1', 'item-2', 'blocks', 'user-1');

      expect(prismaMock.itemDependency.create).toHaveBeenCalledWith({
        data: {
          predecessorId: 'item-1',
          successorId: 'item-2',
          dependencyType: 'blocks',
          createdBy: 'user-1',
        },
      });
    });

    it('should throw error if circular dependency detected', async () => {
      const mockPredecessor = { id: 'item-1', boardId: 'board-1' };
      const mockSuccessor = { id: 'item-2', boardId: 'board-1' };

      prismaMock.item.findUnique
        .mockResolvedValueOnce(mockPredecessor as any)
        .mockResolvedValueOnce(mockSuccessor as any);

      jest.spyOn(ItemService as any, 'checkBoardAccess').mockResolvedValue(true);
      jest.spyOn(ItemService as any, 'checkCircularDependency').mockResolvedValue(true);

      await expect(
        ItemService.addDependency('item-1', 'item-2', 'blocks', 'user-1')
      ).rejects.toThrow('Creating this dependency would create a circular dependency');
    });
  });

  describe('getByBoard', () => {
    it('should return filtered and sorted items', async () => {
      const mockItems = [
        {
          id: 'item-1',
          name: 'Item 1',
          position: new Decimal(1),
          assignments: [],
          parent: null,
          creator: { firstName: 'John' },
          _count: { comments: 0, children: 0, dependencies: 0 },
        },
        {
          id: 'item-2',
          name: 'Item 2',
          position: new Decimal(2),
          assignments: [],
          parent: null,
          creator: { firstName: 'Jane' },
          _count: { comments: 1, children: 0, dependencies: 0 },
        },
      ];

      jest.spyOn(ItemService as any, 'checkBoardAccess').mockResolvedValue(true);
      prismaMock.item.findMany.mockResolvedValue(mockItems as any);
      prismaMock.item.count.mockResolvedValue(2);

      const result = await ItemService.getByBoard(
        'board-1',
        'user-1',
        { search: 'Item' },
        [{ field: 'position', direction: 'asc' }],
        1,
        10
      );

      expect(result.data).toHaveLength(2);
      expect(result.meta.total).toBe(2);
      expect(result.meta.page).toBe(1);
    });

    it('should throw error if access denied to board', async () => {
      jest.spyOn(ItemService as any, 'checkBoardAccess').mockResolvedValue(false);

      await expect(
        ItemService.getByBoard('board-1', 'user-1')
      ).rejects.toThrow('Access denied to board');
    });
  });
});