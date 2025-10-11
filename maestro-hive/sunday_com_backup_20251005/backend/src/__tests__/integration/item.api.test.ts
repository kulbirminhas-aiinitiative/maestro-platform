import request from 'supertest';
import { Express } from 'express';
import { PrismaClient } from '@prisma/client';
import { mockDeep, mockReset, DeepMockProxy } from 'jest-mock-extended';

import app from '../../server';
import { prisma } from '../../config/database';
import { RedisService } from '../../config/redis';

// Mock external dependencies
jest.mock('../../config/database', () => ({
  prisma: mockDeep<PrismaClient>(),
}));

jest.mock('../../config/redis');

const mockPrisma = prisma as DeepMockProxy<PrismaClient>;
const mockRedis = RedisService as jest.Mocked<typeof RedisService>;

describe('Item API Integration Tests', () => {
  let testApp: Express;
  let authToken: string;
  let testUser: any;
  let testBoard: any;
  let testItem: any;

  beforeAll(async () => {
    testApp = app;

    testUser = {
      id: 'user-uuid-123',
      email: 'test@example.com',
      firstName: 'Test',
      lastName: 'User',
    };

    testBoard = {
      id: 'board-uuid-123',
      name: 'Test Board',
      workspaceId: 'workspace-uuid-123',
    };

    testItem = {
      id: 'item-uuid-123',
      name: 'Test Item',
      description: 'Test item description',
      boardId: testBoard.id,
      parentId: null,
      itemData: {
        status: 'To Do',
        priority: 'Medium',
      },
      position: 1.0,
      createdBy: testUser.id,
      createdAt: new Date(),
      updatedAt: new Date(),
      deletedAt: null,
      assignments: [],
      creator: testUser,
      _count: {
        comments: 0,
        children: 0,
        dependencies: 0,
      },
    };

    authToken = 'Bearer test-jwt-token';
  });

  beforeEach(() => {
    mockReset(mockPrisma);
    jest.clearAllMocks();

    // Default auth middleware mock
    jest.spyOn(require('../../middleware/auth'), 'authenticateToken').mockImplementation((req, res, next) => {
      req.user = testUser;
      next();
    });
  });

  describe('GET /api/v1/items/board/:boardId', () => {
    it('should get items for board successfully', async () => {
      // Mock board access check
      mockPrisma.board.findUnique.mockResolvedValue(testBoard);
      mockPrisma.boardMember.findUnique.mockResolvedValue({
        id: 'member-1',
        boardId: testBoard.id,
        userId: testUser.id,
        role: 'member',
      });

      // Mock items query
      mockPrisma.item.findMany.mockResolvedValue([testItem]);
      mockPrisma.item.count.mockResolvedValue(1);

      const response = await request(testApp)
        .get(`/api/v1/items/board/${testBoard.id}`)
        .set('Authorization', authToken)
        .expect(200);

      expect(response.body).toEqual({
        data: [testItem],
        meta: {
          page: 1,
          limit: 50,
          total: 1,
          totalPages: 1,
          hasNext: false,
          hasPrev: false,
        },
      });
    });

    it('should handle filtering parameters', async () => {
      mockPrisma.board.findUnique.mockResolvedValue(testBoard);
      mockPrisma.boardMember.findUnique.mockResolvedValue({
        id: 'member-1',
        boardId: testBoard.id,
        userId: testUser.id,
        role: 'member',
      });

      mockPrisma.item.findMany.mockResolvedValue([]);
      mockPrisma.item.count.mockResolvedValue(0);

      await request(testApp)
        .get(`/api/v1/items/board/${testBoard.id}`)
        .query({
          status: 'In Progress',
          assigneeIds: testUser.id,
          search: 'test',
          sortBy: 'name',
          sortOrder: 'desc',
        })
        .set('Authorization', authToken)
        .expect(200);

      expect(mockPrisma.item.findMany).toHaveBeenCalledWith(
        expect.objectContaining({
          where: expect.objectContaining({
            boardId: testBoard.id,
            deletedAt: null,
          }),
          orderBy: expect.arrayContaining([
            { name: 'desc' },
          ]),
        })
      );
    });

    it('should require board access', async () => {
      mockPrisma.board.findUnique.mockResolvedValue(null);

      await request(testApp)
        .get(`/api/v1/items/board/${testBoard.id}`)
        .set('Authorization', authToken)
        .expect(404);
    });
  });

  describe('POST /api/v1/items/board/:boardId', () => {
    const newItemData = {
      name: 'New Test Item',
      description: 'New item description',
      itemData: {
        status: 'To Do',
        priority: 'High',
      },
      assigneeIds: [testUser.id],
    };

    it('should create item successfully', async () => {
      // Mock board access check
      mockPrisma.board.findUnique.mockResolvedValue(testBoard);
      mockPrisma.boardMember.findUnique.mockResolvedValue({
        id: 'member-1',
        boardId: testBoard.id,
        userId: testUser.id,
        role: 'member',
      });

      // Mock item creation
      const createdItem = {
        ...testItem,
        ...newItemData,
        id: 'new-item-uuid',
        assignments: [
          {
            id: 'assignment-1',
            itemId: 'new-item-uuid',
            userId: testUser.id,
            user: testUser,
          },
        ],
      };

      mockPrisma.item.create.mockResolvedValue(createdItem);

      // Mock activity logging dependencies
      mockPrisma.board.findUnique.mockResolvedValue({
        ...testBoard,
        workspace: {
          id: 'workspace-uuid-123',
          organizationId: 'org-uuid-123',
        },
      });
      mockPrisma.activityLog.create.mockResolvedValue({} as any);

      const response = await request(testApp)
        .post(`/api/v1/items/board/${testBoard.id}`)
        .set('Authorization', authToken)
        .send(newItemData)
        .expect(201);

      expect(response.body.data).toEqual(
        expect.objectContaining({
          name: newItemData.name,
          description: newItemData.description,
          itemData: newItemData.itemData,
        })
      );

      expect(mockPrisma.item.create).toHaveBeenCalledWith(
        expect.objectContaining({
          data: expect.objectContaining({
            name: newItemData.name,
            description: newItemData.description,
            boardId: testBoard.id,
            createdBy: testUser.id,
          }),
        })
      );
    });

    it('should validate required fields', async () => {
      await request(testApp)
        .post(`/api/v1/items/board/${testBoard.id}`)
        .set('Authorization', authToken)
        .send({
          description: 'Missing name',
        })
        .expect(400);
    });

    it('should handle board access denial', async () => {
      mockPrisma.board.findUnique.mockResolvedValue(null);

      await request(testApp)
        .post(`/api/v1/items/board/${testBoard.id}`)
        .set('Authorization', authToken)
        .send(newItemData)
        .expect(404);
    });

    it('should calculate position automatically', async () => {
      mockPrisma.board.findUnique.mockResolvedValue(testBoard);
      mockPrisma.boardMember.findUnique.mockResolvedValue({
        id: 'member-1',
        boardId: testBoard.id,
        userId: testUser.id,
        role: 'member',
      });

      // Mock position calculation
      mockPrisma.item.findFirst.mockResolvedValue({
        ...testItem,
        position: 5.0,
      });

      mockPrisma.item.create.mockResolvedValue({
        ...testItem,
        position: 6.0,
      });

      mockPrisma.board.findUnique.mockResolvedValue({
        ...testBoard,
        workspace: {
          id: 'workspace-uuid-123',
          organizationId: 'org-uuid-123',
        },
      });
      mockPrisma.activityLog.create.mockResolvedValue({} as any);

      await request(testApp)
        .post(`/api/v1/items/board/${testBoard.id}`)
        .set('Authorization', authToken)
        .send(newItemData)
        .expect(201);

      expect(mockPrisma.item.create).toHaveBeenCalledWith(
        expect.objectContaining({
          data: expect.objectContaining({
            position: expect.any(Object), // Decimal object
          }),
        })
      );
    });
  });

  describe('GET /api/v1/items/:itemId', () => {
    it('should get item by ID successfully', async () => {
      mockPrisma.item.findUnique.mockResolvedValue(testItem);
      mockPrisma.board.findUnique.mockResolvedValue(testBoard);
      mockPrisma.boardMember.findUnique.mockResolvedValue({
        id: 'member-1',
        boardId: testBoard.id,
        userId: testUser.id,
        role: 'member',
      });

      const response = await request(testApp)
        .get(`/api/v1/items/${testItem.id}`)
        .set('Authorization', authToken)
        .expect(200);

      expect(response.body.data).toEqual(testItem);
    });

    it('should include related data based on query parameters', async () => {
      const itemWithRelations = {
        ...testItem,
        comments: [],
        attachments: [],
        dependencies: [],
      };

      mockPrisma.item.findUnique.mockResolvedValue(itemWithRelations);
      mockPrisma.board.findUnique.mockResolvedValue(testBoard);
      mockPrisma.boardMember.findUnique.mockResolvedValue({
        id: 'member-1',
        boardId: testBoard.id,
        userId: testUser.id,
        role: 'member',
      });

      await request(testApp)
        .get(`/api/v1/items/${testItem.id}`)
        .query({ include: 'comments,attachments,dependencies' })
        .set('Authorization', authToken)
        .expect(200);

      expect(mockPrisma.item.findUnique).toHaveBeenCalledWith(
        expect.objectContaining({
          include: expect.objectContaining({
            comments: expect.any(Object),
          }),
        })
      );
    });

    it('should handle item not found', async () => {
      mockPrisma.item.findUnique.mockResolvedValue(null);

      await request(testApp)
        .get('/api/v1/items/non-existent-item')
        .set('Authorization', authToken)
        .expect(404);
    });
  });

  describe('PUT /api/v1/items/:itemId', () => {
    const updateData = {
      name: 'Updated Item Name',
      description: 'Updated description',
      itemData: {
        status: 'In Progress',
        priority: 'High',
      },
    };

    it('should update item successfully', async () => {
      mockPrisma.item.findUnique.mockResolvedValue(testItem);
      mockPrisma.board.findUnique.mockResolvedValue(testBoard);
      mockPrisma.boardMember.findUnique.mockResolvedValue({
        id: 'member-1',
        boardId: testBoard.id,
        userId: testUser.id,
        role: 'member',
      });

      const updatedItem = {
        ...testItem,
        ...updateData,
      };

      mockPrisma.item.update.mockResolvedValue(updatedItem);

      // Mock activity logging
      mockPrisma.board.findUnique.mockResolvedValue({
        ...testBoard,
        workspace: {
          id: 'workspace-uuid-123',
          organizationId: 'org-uuid-123',
        },
      });
      mockPrisma.activityLog.create.mockResolvedValue({} as any);

      const response = await request(testApp)
        .put(`/api/v1/items/${testItem.id}`)
        .set('Authorization', authToken)
        .send(updateData)
        .expect(200);

      expect(response.body.data).toEqual(
        expect.objectContaining({
          name: updateData.name,
          description: updateData.description,
        })
      );

      expect(mockPrisma.item.update).toHaveBeenCalledWith(
        expect.objectContaining({
          where: { id: testItem.id },
          data: expect.objectContaining(updateData),
        })
      );
    });

    it('should handle item not found', async () => {
      mockPrisma.item.findUnique.mockResolvedValue(null);

      await request(testApp)
        .put(`/api/v1/items/${testItem.id}`)
        .set('Authorization', authToken)
        .send(updateData)
        .expect(404);
    });

    it('should require board access', async () => {
      mockPrisma.item.findUnique.mockResolvedValue(testItem);
      mockPrisma.board.findUnique.mockResolvedValue(testBoard);
      mockPrisma.boardMember.findUnique.mockResolvedValue(null);

      await request(testApp)
        .put(`/api/v1/items/${testItem.id}`)
        .set('Authorization', authToken)
        .send(updateData)
        .expect(403);
    });
  });

  describe('DELETE /api/v1/items/:itemId', () => {
    it('should delete item successfully', async () => {
      mockPrisma.item.findUnique.mockResolvedValue(testItem);
      mockPrisma.board.findUnique.mockResolvedValue(testBoard);
      mockPrisma.boardMember.findUnique.mockResolvedValue({
        id: 'member-1',
        boardId: testBoard.id,
        userId: testUser.id,
        role: 'member',
      });

      mockPrisma.item.update.mockResolvedValue({
        ...testItem,
        deletedAt: new Date(),
      });

      // Mock activity logging
      mockPrisma.board.findUnique.mockResolvedValue({
        ...testBoard,
        workspace: {
          id: 'workspace-uuid-123',
          organizationId: 'org-uuid-123',
        },
      });
      mockPrisma.activityLog.create.mockResolvedValue({} as any);

      await request(testApp)
        .delete(`/api/v1/items/${testItem.id}`)
        .set('Authorization', authToken)
        .expect(204);

      expect(mockPrisma.item.update).toHaveBeenCalledWith(
        expect.objectContaining({
          where: { id: testItem.id },
          data: { deletedAt: expect.any(Date) },
        })
      );
    });

    it('should handle item not found', async () => {
      mockPrisma.item.findUnique.mockResolvedValue(null);

      await request(testApp)
        .delete(`/api/v1/items/${testItem.id}`)
        .set('Authorization', authToken)
        .expect(404);
    });
  });

  describe('PUT /api/v1/items/:itemId/move', () => {
    const moveData = {
      position: 2.5,
      parentId: null,
    };

    it('should move item successfully', async () => {
      mockPrisma.item.findUnique.mockResolvedValue(testItem);
      mockPrisma.board.findUnique.mockResolvedValue(testBoard);
      mockPrisma.boardMember.findUnique.mockResolvedValue({
        id: 'member-1',
        boardId: testBoard.id,
        userId: testUser.id,
        role: 'member',
      });

      // Mock items that need position updates
      mockPrisma.item.findMany.mockResolvedValue([
        {
          id: 'item-2',
          position: 3.0,
        },
        {
          id: 'item-3',
          position: 4.0,
        },
      ]);

      // Mock position updates
      mockPrisma.item.update
        .mockResolvedValueOnce({
          id: 'item-2',
          position: 4.0,
        })
        .mockResolvedValueOnce({
          id: 'item-3',
          position: 5.0,
        })
        .mockResolvedValueOnce({
          ...testItem,
          position: 2.5,
        });

      // Mock activity logging
      mockPrisma.board.findUnique.mockResolvedValue({
        ...testBoard,
        workspace: {
          id: 'workspace-uuid-123',
          organizationId: 'org-uuid-123',
        },
      });
      mockPrisma.activityLog.create.mockResolvedValue({} as any);
      mockRedis.deleteCachePattern.mockResolvedValue(undefined);

      const response = await request(testApp)
        .put(`/api/v1/items/${testItem.id}/move`)
        .set('Authorization', authToken)
        .send(moveData)
        .expect(200);

      expect(response.body.data.item).toEqual(
        expect.objectContaining({
          position: 2.5,
        })
      );

      expect(response.body.data.affectedItems).toHaveLength(2);
    });

    it('should validate position parameter', async () => {
      await request(testApp)
        .put(`/api/v1/items/${testItem.id}/move`)
        .set('Authorization', authToken)
        .send({
          position: 'invalid',
        })
        .expect(400);
    });

    it('should handle cross-board moves', async () => {
      const targetBoard = {
        id: 'target-board-uuid',
        name: 'Target Board',
        workspaceId: 'workspace-uuid-123',
      };

      mockPrisma.item.findUnique.mockResolvedValue(testItem);
      mockPrisma.board.findUnique
        .mockResolvedValueOnce(testBoard) // Current board
        .mockResolvedValueOnce(targetBoard); // Target board

      mockPrisma.boardMember.findUnique
        .mockResolvedValueOnce({
          id: 'member-1',
          boardId: testBoard.id,
          userId: testUser.id,
          role: 'member',
        })
        .mockResolvedValueOnce({
          id: 'member-2',
          boardId: targetBoard.id,
          userId: testUser.id,
          role: 'member',
        });

      mockPrisma.item.findMany.mockResolvedValue([]);
      mockPrisma.item.update.mockResolvedValue({
        ...testItem,
        boardId: targetBoard.id,
        position: 1.0,
      });

      // Mock activity logging
      mockPrisma.board.findUnique.mockResolvedValue({
        ...testBoard,
        workspace: {
          id: 'workspace-uuid-123',
          organizationId: 'org-uuid-123',
        },
      });
      mockPrisma.activityLog.create.mockResolvedValue({} as any);
      mockRedis.deleteCachePattern.mockResolvedValue(undefined);

      await request(testApp)
        .put(`/api/v1/items/${testItem.id}/move`)
        .set('Authorization', authToken)
        .send({
          position: 1.0,
          boardId: targetBoard.id,
        })
        .expect(200);

      expect(mockPrisma.item.update).toHaveBeenCalledWith(
        expect.objectContaining({
          where: { id: testItem.id },
          data: expect.objectContaining({
            boardId: targetBoard.id,
          }),
        })
      );
    });
  });

  describe('PUT /api/v1/items/bulk/update', () => {
    const bulkUpdateData = {
      itemIds: ['item-1', 'item-2'],
      updates: {
        itemData: {
          status: 'In Progress',
        },
        assigneeIds: [testUser.id],
      },
    };

    it('should bulk update items successfully', async () => {
      // Mock items retrieval
      mockPrisma.item.findMany.mockResolvedValue([
        { ...testItem, id: 'item-1' },
        { ...testItem, id: 'item-2' },
      ]);

      // Mock board access checks
      mockPrisma.board.findUnique.mockResolvedValue(testBoard);
      mockPrisma.boardMember.findUnique.mockResolvedValue({
        id: 'member-1',
        boardId: testBoard.id,
        userId: testUser.id,
        role: 'member',
      });

      // Mock bulk updates
      mockPrisma.item.update
        .mockResolvedValueOnce({ ...testItem, id: 'item-1' })
        .mockResolvedValueOnce({ ...testItem, id: 'item-2' });

      // Mock assignment updates
      mockPrisma.itemAssignment.deleteMany.mockResolvedValue({ count: 0 });
      mockPrisma.itemAssignment.createMany.mockResolvedValue({ count: 2 });

      // Mock activity logging
      mockPrisma.board.findUnique.mockResolvedValue({
        ...testBoard,
        workspace: {
          id: 'workspace-uuid-123',
          organizationId: 'org-uuid-123',
        },
      });
      mockPrisma.activityLog.create.mockResolvedValue({} as any);

      const response = await request(testApp)
        .put('/api/v1/items/bulk/update')
        .set('Authorization', authToken)
        .send(bulkUpdateData)
        .expect(200);

      expect(response.body.data.updatedCount).toBe(2);
      expect(response.body.data.errors).toHaveLength(0);
    });

    it('should validate item IDs', async () => {
      await request(testApp)
        .put('/api/v1/items/bulk/update')
        .set('Authorization', authToken)
        .send({
          itemIds: ['invalid-uuid'],
          updates: {},
        })
        .expect(400);
    });

    it('should handle partial failures gracefully', async () => {
      mockPrisma.item.findMany.mockResolvedValue([
        { ...testItem, id: 'item-1' },
      ]);

      // Mock one successful update, one not found
      mockPrisma.board.findUnique.mockResolvedValue(testBoard);
      mockPrisma.boardMember.findUnique.mockResolvedValue({
        id: 'member-1',
        boardId: testBoard.id,
        userId: testUser.id,
        role: 'member',
      });

      mockPrisma.item.update.mockResolvedValueOnce({ ...testItem, id: 'item-1' });

      // Mock activity logging
      mockPrisma.board.findUnique.mockResolvedValue({
        ...testBoard,
        workspace: {
          id: 'workspace-uuid-123',
          organizationId: 'org-uuid-123',
        },
      });
      mockPrisma.activityLog.create.mockResolvedValue({} as any);

      const response = await request(testApp)
        .put('/api/v1/items/bulk/update')
        .set('Authorization', authToken)
        .send(bulkUpdateData)
        .expect(200);

      expect(response.body.data.updatedCount).toBe(1);
      expect(response.body.data.errors).toHaveLength(1);
    });
  });

  describe('POST /api/v1/items/:itemId/dependencies', () => {
    const dependencyData = {
      predecessorId: 'predecessor-item-uuid',
      dependencyType: 'blocks',
    };

    it('should add dependency successfully', async () => {
      mockPrisma.item.findUnique
        .mockResolvedValueOnce(testItem) // successor item
        .mockResolvedValueOnce({ ...testItem, id: 'predecessor-item-uuid' }); // predecessor item

      mockPrisma.board.findUnique.mockResolvedValue(testBoard);
      mockPrisma.boardMember.findUnique.mockResolvedValue({
        id: 'member-1',
        boardId: testBoard.id,
        userId: testUser.id,
        role: 'member',
      });

      // Mock circular dependency check
      mockPrisma.$queryRaw.mockResolvedValue([{ exists: false }]);

      mockPrisma.itemDependency.create.mockResolvedValue({
        id: 'dependency-uuid',
        predecessorId: dependencyData.predecessorId,
        successorId: testItem.id,
        dependencyType: dependencyData.dependencyType,
        createdBy: testUser.id,
        createdAt: new Date(),
      });

      await request(testApp)
        .post(`/api/v1/items/${testItem.id}/dependencies`)
        .set('Authorization', authToken)
        .send(dependencyData)
        .expect(201);

      expect(mockPrisma.itemDependency.create).toHaveBeenCalledWith(
        expect.objectContaining({
          data: expect.objectContaining({
            predecessorId: dependencyData.predecessorId,
            successorId: testItem.id,
            dependencyType: dependencyData.dependencyType,
          }),
        })
      );
    });

    it('should prevent circular dependencies', async () => {
      mockPrisma.item.findUnique
        .mockResolvedValueOnce(testItem)
        .mockResolvedValueOnce({ ...testItem, id: 'predecessor-item-uuid' });

      mockPrisma.board.findUnique.mockResolvedValue(testBoard);
      mockPrisma.boardMember.findUnique.mockResolvedValue({
        id: 'member-1',
        boardId: testBoard.id,
        userId: testUser.id,
        role: 'member',
      });

      // Mock circular dependency detection
      mockPrisma.$queryRaw.mockResolvedValue([{ exists: true }]);

      await request(testApp)
        .post(`/api/v1/items/${testItem.id}/dependencies`)
        .set('Authorization', authToken)
        .send(dependencyData)
        .expect(409);
    });

    it('should validate predecessor exists', async () => {
      mockPrisma.item.findUnique
        .mockResolvedValueOnce(testItem)
        .mockResolvedValueOnce(null); // Predecessor not found

      await request(testApp)
        .post(`/api/v1/items/${testItem.id}/dependencies`)
        .set('Authorization', authToken)
        .send(dependencyData)
        .expect(404);
    });
  });

  describe('Error Handling', () => {
    it('should handle database errors gracefully', async () => {
      mockPrisma.item.findUnique.mockRejectedValue(new Error('Database connection failed'));

      await request(testApp)
        .get(`/api/v1/items/${testItem.id}`)
        .set('Authorization', authToken)
        .expect(500);
    });

    it('should handle validation errors properly', async () => {
      await request(testApp)
        .post(`/api/v1/items/board/${testBoard.id}`)
        .set('Authorization', authToken)
        .send({
          name: '', // Empty name
          itemData: 'invalid-json',
        })
        .expect(400);
    });
  });
});