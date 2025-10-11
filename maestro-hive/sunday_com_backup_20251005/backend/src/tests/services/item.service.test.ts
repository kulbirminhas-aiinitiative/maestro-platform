import { describe, it, expect, beforeEach, vi } from 'vitest';
import { ItemService } from '@/services/item.service';
import { prisma } from '@/config/database';
import { RedisService } from '@/config/redis';

// Mock dependencies
vi.mock('@/config/database', () => ({
  prisma: {
    item: {
      create: vi.fn(),
      findFirst: vi.fn(),
      findUnique: vi.fn(),
      findMany: vi.fn(),
      update: vi.fn(),
      count: vi.fn(),
      updateMany: vi.fn(),
    },
    itemAssignment: {
      create: vi.fn(),
      findFirst: vi.fn(),
      delete: vi.fn(),
      deleteMany: vi.fn(),
    },
    itemDependency: {
      create: vi.fn(),
      findFirst: vi.fn(),
      delete: vi.fn(),
    },
    board: {
      findUnique: vi.fn(),
    },
    user: {
      findUnique: vi.fn(),
    },
    activityLog: {
      create: vi.fn(),
    },
    $transaction: vi.fn(),
    $queryRaw: vi.fn(),
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
    business: vi.fn(),
  },
}));

vi.mock('@/server', () => ({
  io: {
    to: vi.fn().mockReturnThis(),
    emit: vi.fn(),
    except: vi.fn().mockReturnThis(),
  },
}));

describe('ItemService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('createItem', () => {
    const mockBoardAccess = vi.fn();
    const mockItemData = {
      name: 'Test Item',
      description: 'Test Description',
      boardId: 'board-1',
      parentId: null,
      itemData: { status: 'Not Started' },
      assigneeIds: ['user-2', 'user-3'],
    };

    const mockCreatedItem = {
      id: 'item-1',
      name: 'Test Item',
      description: 'Test Description',
      boardId: 'board-1',
      parentId: null,
      position: 1,
      createdBy: 'user-1',
      board: { id: 'board-1', name: 'Test Board', workspaceId: 'workspace-1' },
      parent: null,
      children: [],
      createdByUser: { id: 'user-1', firstName: 'John', lastName: 'Doe' },
    };

    beforeEach(() => {
      // Mock BoardService methods
      (ItemService as any).checkBoardAccess = mockBoardAccess;
      (ItemService as any).getNextPosition = vi.fn().mockResolvedValue(1);
      (ItemService as any).invalidateCaches = vi.fn().mockResolvedValue(undefined);
      (ItemService as any).logActivity = vi.fn().mockResolvedValue(undefined);
    });

    it('should create item successfully', async () => {
      mockBoardAccess.mockResolvedValue(true);
      (prisma.item.create as any).mockResolvedValue(mockCreatedItem);

      const result = await ItemService.createItem('board-1', 'user-1', mockItemData);

      expect(result).toEqual(mockCreatedItem);
      expect(prisma.item.create).toHaveBeenCalledWith({
        data: {
          id: expect.any(String),
          boardId: 'board-1',
          parentId: null,
          name: 'Test Item',
          description: 'Test Description',
          itemData: { status: 'Not Started' },
          position: 1,
          createdBy: 'user-1',
        },
        include: expect.any(Object),
      });
    });

    it('should throw error if board access denied', async () => {
      mockBoardAccess.mockResolvedValue(false);

      await expect(
        ItemService.createItem('board-1', 'user-1', mockItemData)
      ).rejects.toThrow('Board not found or access denied');
    });

    it('should validate parent item if provided', async () => {
      const itemDataWithParent = { ...mockItemData, parentId: 'parent-1' };
      const mockParent = { id: 'parent-1', boardId: 'board-1', deletedAt: null };

      mockBoardAccess.mockResolvedValue(true);
      (prisma.item.findFirst as any).mockResolvedValue(mockParent);
      (prisma.item.create as any).mockResolvedValue({
        ...mockCreatedItem,
        parentId: 'parent-1',
      });

      await ItemService.createItem('board-1', 'user-1', itemDataWithParent);

      expect(prisma.item.findFirst).toHaveBeenCalledWith({
        where: {
          id: 'parent-1',
          boardId: 'board-1',
          deletedAt: null,
        },
      });
    });

    it('should throw error if parent item not found', async () => {
      const itemDataWithParent = { ...mockItemData, parentId: 'parent-1' };

      mockBoardAccess.mockResolvedValue(true);
      (prisma.item.findFirst as any).mockResolvedValue(null);

      await expect(
        ItemService.createItem('board-1', 'user-1', itemDataWithParent)
      ).rejects.toThrow('Parent item not found');
    });
  });

  describe('getItem', () => {
    const mockItem = {
      id: 'item-1',
      name: 'Test Item',
      boardId: 'board-1',
      deletedAt: null,
      assignments: [],
      parent: null,
      children: [],
      dependencies: [],
      comments: [],
      createdByUser: { id: 'user-1', firstName: 'John', lastName: 'Doe' },
      _count: { comments: 0, children: 0, dependencies: 0 },
    };

    beforeEach(() => {
      (ItemService as any).checkBoardAccess = vi.fn().mockResolvedValue(true);
      (ItemService as any).getUserItemPermissions = vi.fn().mockResolvedValue({
        canRead: true,
        canEdit: true,
      });
    });

    it('should get item successfully with cache miss', async () => {
      (RedisService.getCache as any).mockResolvedValue(null);
      (prisma.item.findFirst as any).mockResolvedValue(mockItem);
      (RedisService.setCache as any).mockResolvedValue(undefined);

      const result = await ItemService.getItem('item-1', 'user-1');

      expect(result).toEqual({
        ...mockItem,
        userPermissions: { canRead: true, canEdit: true },
      });
      expect(RedisService.getCache).toHaveBeenCalled();
      expect(prisma.item.findFirst).toHaveBeenCalled();
      expect(RedisService.setCache).toHaveBeenCalled();
    });

    it('should return cached item if available', async () => {
      const cachedItem = { ...mockItem, cached: true };
      (RedisService.getCache as any).mockResolvedValue(cachedItem);

      const result = await ItemService.getItem('item-1', 'user-1');

      expect(result).toEqual(cachedItem);
      expect(prisma.item.findFirst).not.toHaveBeenCalled();
    });

    it('should throw error if item not found', async () => {
      (RedisService.getCache as any).mockResolvedValue(null);
      (prisma.item.findFirst as any).mockResolvedValue(null);

      await expect(
        ItemService.getItem('item-1', 'user-1')
      ).rejects.toThrow('Item not found');
    });

    it('should throw error if board access denied', async () => {
      const mockItemForAccessCheck = { ...mockItem };
      (RedisService.getCache as any).mockResolvedValue(null);
      (prisma.item.findFirst as any).mockResolvedValue(mockItemForAccessCheck);
      (ItemService as any).checkBoardAccess = vi.fn().mockResolvedValue(false);

      await expect(
        ItemService.getItem('item-1', 'user-1')
      ).rejects.toThrow('Access denied');
    });
  });

  describe('updateItem', () => {
    const mockCurrentItem = {
      id: 'item-1',
      name: 'Old Item',
      boardId: 'board-1',
      parentId: null,
      deletedAt: null,
      assignments: [{ userId: 'user-2' }],
    };

    const updateData = {
      name: 'Updated Item',
      description: 'Updated Description',
      itemData: { status: 'In Progress' },
      assigneeIds: ['user-3'],
    };

    const mockUpdatedItem = {
      ...mockCurrentItem,
      name: 'Updated Item',
      description: 'Updated Description',
      itemData: { status: 'In Progress' },
    };

    beforeEach(() => {
      (ItemService as any).checkBoardAccess = vi.fn().mockResolvedValue(true);
      (ItemService as any).invalidateCaches = vi.fn().mockResolvedValue(undefined);
      (ItemService as any).logActivity = vi.fn().mockResolvedValue(undefined);
    });

    it('should update item successfully', async () => {
      (prisma.item.findUnique as any).mockResolvedValue(mockCurrentItem);
      (prisma.item.update as any).mockResolvedValue(mockUpdatedItem);

      const result = await ItemService.updateItem('item-1', 'user-1', updateData);

      expect(result).toEqual(mockUpdatedItem);
      expect(prisma.item.update).toHaveBeenCalledWith({
        where: { id: 'item-1' },
        data: expect.objectContaining({
          name: 'Updated Item',
          description: 'Updated Description',
          itemData: { status: 'In Progress' },
          updatedAt: expect.any(Date),
        }),
        include: expect.any(Object),
      });
    });

    it('should throw error if item not found', async () => {
      (prisma.item.findUnique as any).mockResolvedValue(null);

      await expect(
        ItemService.updateItem('item-1', 'user-1', updateData)
      ).rejects.toThrow('Item not found');
    });

    it('should throw error if board access denied', async () => {
      (prisma.item.findUnique as any).mockResolvedValue(mockCurrentItem);
      (ItemService as any).checkBoardAccess = vi.fn().mockResolvedValue(false);

      await expect(
        ItemService.updateItem('item-1', 'user-1', updateData)
      ).rejects.toThrow('Access denied');
    });

    it('should validate parent change', async () => {
      const updateWithParent = { ...updateData, parentId: 'parent-1' };
      const mockParent = { id: 'parent-1', boardId: 'board-1', deletedAt: null };

      (prisma.item.findUnique as any).mockResolvedValue(mockCurrentItem);
      (prisma.item.findFirst as any).mockResolvedValue(mockParent);
      (ItemService as any).checkCircularDependency = vi.fn().mockResolvedValue(false);
      (prisma.item.update as any).mockResolvedValue({
        ...mockUpdatedItem,
        parentId: 'parent-1',
      });

      await ItemService.updateItem('item-1', 'user-1', updateWithParent);

      expect(prisma.item.findFirst).toHaveBeenCalledWith({
        where: {
          id: 'parent-1',
          boardId: 'board-1',
          deletedAt: null,
        },
      });
    });

    it('should prevent circular parent-child relationship', async () => {
      const updateWithParent = { ...updateData, parentId: 'parent-1' };
      const mockParent = { id: 'parent-1', boardId: 'board-1', deletedAt: null };

      (prisma.item.findUnique as any).mockResolvedValue(mockCurrentItem);
      (prisma.item.findFirst as any).mockResolvedValue(mockParent);
      (ItemService as any).checkCircularDependency = vi.fn().mockResolvedValue(true);

      await expect(
        ItemService.updateItem('item-1', 'user-1', updateWithParent)
      ).rejects.toThrow('Cannot create circular parent-child relationship');
    });
  });

  describe('deleteItem', () => {
    const mockItem = {
      id: 'item-1',
      name: 'Test Item',
      boardId: 'board-1',
      deletedAt: null,
      _count: { children: 2 },
    };

    beforeEach(() => {
      (ItemService as any).checkBoardAccess = vi.fn().mockResolvedValue(true);
      (ItemService as any).softDeleteItemTree = vi.fn().mockResolvedValue(undefined);
      (ItemService as any).invalidateCaches = vi.fn().mockResolvedValue(undefined);
      (ItemService as any).logActivity = vi.fn().mockResolvedValue(undefined);
    });

    it('should delete item successfully', async () => {
      (prisma.item.findUnique as any).mockResolvedValue(mockItem);

      await ItemService.deleteItem('item-1', 'user-1');

      expect(ItemService.softDeleteItemTree).toHaveBeenCalledWith('item-1');
    });

    it('should throw error if item not found', async () => {
      (prisma.item.findUnique as any).mockResolvedValue(null);

      await expect(
        ItemService.deleteItem('item-1', 'user-1')
      ).rejects.toThrow('Item not found');
    });

    it('should throw error if board access denied', async () => {
      (prisma.item.findUnique as any).mockResolvedValue(mockItem);
      (ItemService as any).checkBoardAccess = vi.fn().mockResolvedValue(false);

      await expect(
        ItemService.deleteItem('item-1', 'user-1')
      ).rejects.toThrow('Access denied');
    });
  });

  describe('addAssignment', () => {
    const mockItem = {
      id: 'item-1',
      boardId: 'board-1',
    };

    const mockAssignment = {
      id: 'assignment-1',
      itemId: 'item-1',
      userId: 'user-2',
      assignedBy: 'user-1',
      user: {
        id: 'user-2',
        firstName: 'Jane',
        lastName: 'Doe',
        avatarUrl: null,
      },
    };

    beforeEach(() => {
      (ItemService as any).checkBoardAccess = vi.fn().mockResolvedValue(true);
      (ItemService as any).invalidateCaches = vi.fn().mockResolvedValue(undefined);
      (ItemService as any).logActivity = vi.fn().mockResolvedValue(undefined);
    });

    it('should add assignment successfully', async () => {
      (prisma.item.findUnique as any).mockResolvedValue(mockItem);
      (prisma.itemAssignment.findFirst as any).mockResolvedValue(null);
      (prisma.user.findUnique as any).mockResolvedValue({ id: 'user-2' });
      (ItemService as any).checkBoardAccess = vi.fn()
        .mockResolvedValueOnce(true) // For item access
        .mockResolvedValueOnce(true); // For assignee access
      (prisma.itemAssignment.create as any).mockResolvedValue(mockAssignment);

      const result = await ItemService.addAssignment('item-1', 'user-1', 'user-2');

      expect(result).toEqual(mockAssignment);
      expect(prisma.itemAssignment.create).toHaveBeenCalledWith({
        data: {
          itemId: 'item-1',
          userId: 'user-2',
          assignedBy: 'user-1',
        },
        include: expect.any(Object),
      });
    });

    it('should throw error if item not found', async () => {
      (prisma.item.findUnique as any).mockResolvedValue(null);

      await expect(
        ItemService.addAssignment('item-1', 'user-1', 'user-2')
      ).rejects.toThrow('Item not found');
    });

    it('should throw error if assignment already exists', async () => {
      (prisma.item.findUnique as any).mockResolvedValue(mockItem);
      (prisma.itemAssignment.findFirst as any).mockResolvedValue(mockAssignment);

      await expect(
        ItemService.addAssignment('item-1', 'user-1', 'user-2')
      ).rejects.toThrow('User is already assigned to this item');
    });

    it('should throw error if assignee not found', async () => {
      (prisma.item.findUnique as any).mockResolvedValue(mockItem);
      (prisma.itemAssignment.findFirst as any).mockResolvedValue(null);
      (prisma.user.findUnique as any).mockResolvedValue(null);

      await expect(
        ItemService.addAssignment('item-1', 'user-1', 'user-2')
      ).rejects.toThrow('Assignee not found');
    });
  });

  describe('createDependency', () => {
    const mockPredecessor = {
      id: 'item-1',
      boardId: 'board-1',
      deletedAt: null,
    };

    const mockSuccessor = {
      id: 'item-2',
      boardId: 'board-1',
      deletedAt: null,
    };

    const mockDependency = {
      id: 'dependency-1',
      predecessorId: 'item-1',
      successorId: 'item-2',
      dependencyType: 'blocks',
      createdBy: 'user-1',
      predecessor: { id: 'item-1', name: 'Item 1' },
      successor: { id: 'item-2', name: 'Item 2' },
    };

    beforeEach(() => {
      (ItemService as any).checkBoardAccess = vi.fn().mockResolvedValue(true);
      (ItemService as any).checkCircularDependency = vi.fn().mockResolvedValue(false);
      (ItemService as any).invalidateCaches = vi.fn().mockResolvedValue(undefined);
      (ItemService as any).logActivity = vi.fn().mockResolvedValue(undefined);
    });

    it('should create dependency successfully', async () => {
      (prisma.item.findUnique as any)
        .mockResolvedValueOnce(mockPredecessor)
        .mockResolvedValueOnce(mockSuccessor);
      (prisma.itemDependency.findFirst as any).mockResolvedValue(null);
      (prisma.itemDependency.create as any).mockResolvedValue(mockDependency);

      const result = await ItemService.createDependency(
        'item-1',
        'item-2',
        'user-1',
        'blocks'
      );

      expect(result).toEqual(mockDependency);
      expect(prisma.itemDependency.create).toHaveBeenCalledWith({
        data: {
          predecessorId: 'item-1',
          successorId: 'item-2',
          dependencyType: 'blocks',
          createdBy: 'user-1',
        },
        include: expect.any(Object),
      });
    });

    it('should throw error if one item not found', async () => {
      (prisma.item.findUnique as any)
        .mockResolvedValueOnce(mockPredecessor)
        .mockResolvedValueOnce(null);

      await expect(
        ItemService.createDependency('item-1', 'item-2', 'user-1', 'blocks')
      ).rejects.toThrow('One or both items not found');
    });

    it('should throw error if dependency already exists', async () => {
      (prisma.item.findUnique as any)
        .mockResolvedValueOnce(mockPredecessor)
        .mockResolvedValueOnce(mockSuccessor);
      (prisma.itemDependency.findFirst as any).mockResolvedValue(mockDependency);

      await expect(
        ItemService.createDependency('item-1', 'item-2', 'user-1', 'blocks')
      ).rejects.toThrow('Dependency already exists');
    });

    it('should throw error if circular dependency detected', async () => {
      (prisma.item.findUnique as any)
        .mockResolvedValueOnce(mockPredecessor)
        .mockResolvedValueOnce(mockSuccessor);
      (prisma.itemDependency.findFirst as any).mockResolvedValue(null);
      (ItemService as any).checkCircularDependency = vi.fn().mockResolvedValue(true);

      await expect(
        ItemService.createDependency('item-1', 'item-2', 'user-1', 'blocks')
      ).rejects.toThrow('Would create circular dependency');
    });
  });

  describe('moveItem', () => {
    const mockCurrentItem = {
      id: 'item-1',
      name: 'Test Item',
      boardId: 'board-1',
      parentId: null,
      position: 2,
      assignments: [],
      parent: null,
      creator: { id: 'user-1', firstName: 'John', lastName: 'Doe' },
    };

    const mockItemsToUpdate = [
      { id: 'item-2', position: 1 },
      { id: 'item-3', position: 2 },
    ];

    const mockUpdatedItem = {
      ...mockCurrentItem,
      position: 1,
      _count: { comments: 0, children: 0, dependencies: 0 },
    };

    beforeEach(() => {
      (ItemService as any).checkBoardAccess = vi.fn().mockResolvedValue(true);
      (ItemService as any).checkCircularDependency = vi.fn().mockResolvedValue(false);
      (ItemService as any).logActivity = vi.fn().mockResolvedValue(undefined);
      (ItemService as any).invalidateCaches = vi.fn().mockResolvedValue(undefined);
    });

    it('should move item successfully', async () => {
      (prisma.item.findUnique as any).mockResolvedValue(mockCurrentItem);
      (prisma.item.findMany as any).mockResolvedValue(mockItemsToUpdate);
      (prisma.item.update as any)
        .mockResolvedValueOnce({ id: 'item-2', position: 2 })
        .mockResolvedValueOnce({ id: 'item-3', position: 3 })
        .mockResolvedValueOnce(mockUpdatedItem);

      const result = await ItemService.moveItem('item-1', 'user-1', 1, null);

      expect(result.item).toEqual(mockUpdatedItem);
      expect(result.affectedItems).toHaveLength(2);
      expect(prisma.item.update).toHaveBeenCalledTimes(3); // 2 for affected items + 1 for moved item
    });

    it('should throw error if item not found', async () => {
      (prisma.item.findUnique as any).mockResolvedValue(null);

      await expect(
        ItemService.moveItem('item-1', 'user-1', 1, null)
      ).rejects.toThrow('Item not found');
    });

    it('should validate target parent if specified', async () => {
      const mockTargetParent = { id: 'parent-1', boardId: 'board-1', deletedAt: null };

      (prisma.item.findUnique as any).mockResolvedValue(mockCurrentItem);
      (prisma.item.findFirst as any).mockResolvedValue(mockTargetParent);
      (prisma.item.findMany as any).mockResolvedValue([]);
      (prisma.item.update as any).mockResolvedValue({
        ...mockUpdatedItem,
        parentId: 'parent-1',
      });

      await ItemService.moveItem('item-1', 'user-1', 1, 'parent-1');

      expect(prisma.item.findFirst).toHaveBeenCalledWith({
        where: {
          id: 'parent-1',
          boardId: 'board-1',
          deletedAt: null,
        },
      });
    });

    it('should prevent circular parent-child relationship', async () => {
      const mockTargetParent = { id: 'parent-1', boardId: 'board-1', deletedAt: null };

      (prisma.item.findUnique as any).mockResolvedValue(mockCurrentItem);
      (prisma.item.findFirst as any).mockResolvedValue(mockTargetParent);
      (ItemService as any).checkCircularDependency = vi.fn().mockResolvedValue(true);

      await expect(
        ItemService.moveItem('item-1', 'user-1', 1, 'parent-1')
      ).rejects.toThrow('Cannot create circular parent-child relationship');
    });
  });

  describe('bulkUpdateItems', () => {
    const mockItems = [
      { id: 'item-1', boardId: 'board-1', name: 'Item 1', deletedAt: null },
      { id: 'item-2', boardId: 'board-1', name: 'Item 2', deletedAt: null },
    ];

    const bulkUpdateData = {
      itemIds: ['item-1', 'item-2'],
      updates: {
        itemData: { status: 'In Progress' },
      },
    };

    beforeEach(() => {
      (ItemService as any).checkBoardAccess = vi.fn().mockResolvedValue(true);
      (ItemService as any).invalidateCaches = vi.fn().mockResolvedValue(undefined);
      (ItemService as any).logActivity = vi.fn().mockResolvedValue(undefined);
    });

    it('should bulk update items successfully', async () => {
      (prisma.item.findUnique as any)
        .mockResolvedValueOnce(mockItems[0])
        .mockResolvedValueOnce(mockItems[1]);
      (prisma.item.update as any)
        .mockResolvedValueOnce({ ...mockItems[0], itemData: { status: 'In Progress' } })
        .mockResolvedValueOnce({ ...mockItems[1], itemData: { status: 'In Progress' } });

      const result = await ItemService.bulkUpdateItems('user-1', bulkUpdateData);

      expect(result).toHaveLength(2);
      expect(prisma.item.update).toHaveBeenCalledTimes(2);
    });

    it('should handle mixed permissions gracefully', async () => {
      (prisma.item.findUnique as any)
        .mockResolvedValueOnce(mockItems[0])
        .mockResolvedValueOnce(mockItems[1]);
      (ItemService as any).checkBoardAccess = vi.fn()
        .mockResolvedValueOnce(true)  // First item allowed
        .mockResolvedValueOnce(false); // Second item denied
      (prisma.item.update as any)
        .mockResolvedValueOnce({ ...mockItems[0], itemData: { status: 'In Progress' } });

      const result = await ItemService.bulkUpdateItems('user-1', bulkUpdateData);

      expect(result).toHaveLength(1); // Only first item updated
      expect(prisma.item.update).toHaveBeenCalledTimes(1);
    });
  });
});