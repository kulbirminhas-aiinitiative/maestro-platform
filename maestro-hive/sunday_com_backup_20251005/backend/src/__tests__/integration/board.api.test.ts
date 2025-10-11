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

describe('Board API Integration Tests', () => {
  let testApp: Express;
  let authToken: string;
  let testUser: any;
  let testWorkspace: any;
  let testBoard: any;

  beforeAll(async () => {
    testApp = app;

    // Mock user for authentication
    testUser = {
      id: 'user-uuid-123',
      email: 'test@example.com',
      firstName: 'Test',
      lastName: 'User',
    };

    testWorkspace = {
      id: 'workspace-uuid-123',
      name: 'Test Workspace',
      organizationId: 'org-uuid-123',
    };

    testBoard = {
      id: 'board-uuid-123',
      name: 'Test Board',
      description: 'Test board description',
      workspaceId: testWorkspace.id,
      isPrivate: false,
      createdBy: testUser.id,
      createdAt: new Date(),
      updatedAt: new Date(),
      deletedAt: null,
      columns: [
        {
          id: 'column-1',
          name: 'To Do',
          position: 0,
          boardId: 'board-uuid-123',
        },
        {
          id: 'column-2',
          name: 'In Progress',
          position: 1,
          boardId: 'board-uuid-123',
        },
      ],
      members: [],
      creator: testUser,
      _count: {
        items: 0,
        members: 1,
        columns: 2,
      },
    };

    // Mock JWT token
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

  describe('GET /api/v1/boards/workspace/:workspaceId', () => {
    it('should get boards for workspace successfully', async () => {
      // Mock database queries
      mockPrisma.board.findMany.mockResolvedValue([testBoard]);
      mockPrisma.board.count.mockResolvedValue(1);

      const response = await request(testApp)
        .get(`/api/v1/boards/workspace/${testWorkspace.id}`)
        .set('Authorization', authToken)
        .expect(200);

      expect(response.body).toEqual({
        data: [testBoard],
        meta: {
          page: 1,
          limit: 20,
          total: 1,
          totalPages: 1,
          hasNext: false,
          hasPrev: false,
        },
      });

      expect(mockPrisma.board.findMany).toHaveBeenCalledWith(
        expect.objectContaining({
          where: expect.objectContaining({
            workspaceId: testWorkspace.id,
            deletedAt: null,
          }),
        })
      );
    });

    it('should handle pagination parameters', async () => {
      mockPrisma.board.findMany.mockResolvedValue([]);
      mockPrisma.board.count.mockResolvedValue(0);

      await request(testApp)
        .get(`/api/v1/boards/workspace/${testWorkspace.id}`)
        .query({ page: 2, limit: 10 })
        .set('Authorization', authToken)
        .expect(200);

      expect(mockPrisma.board.findMany).toHaveBeenCalledWith(
        expect.objectContaining({
          skip: 10,
          take: 10,
        })
      );
    });

    it('should validate workspace ID parameter', async () => {
      await request(testApp)
        .get('/api/v1/boards/workspace/invalid-uuid')
        .set('Authorization', authToken)
        .expect(400);
    });
  });

  describe('GET /api/v1/boards/:boardId', () => {
    it('should get board by ID successfully', async () => {
      mockPrisma.board.findFirst.mockResolvedValue(testBoard);
      mockRedis.getCache.mockResolvedValue(null);
      mockRedis.setCache.mockResolvedValue(undefined);

      const response = await request(testApp)
        .get(`/api/v1/boards/${testBoard.id}`)
        .set('Authorization', authToken)
        .expect(200);

      expect(response.body).toEqual({
        data: testBoard,
      });

      expect(mockPrisma.board.findFirst).toHaveBeenCalledWith(
        expect.objectContaining({
          where: expect.objectContaining({
            id: testBoard.id,
            deletedAt: null,
          }),
        })
      );
    });

    it('should handle board not found', async () => {
      mockPrisma.board.findFirst.mockResolvedValue(null);
      mockRedis.getCache.mockResolvedValue(null);

      const response = await request(testApp)
        .get('/api/v1/boards/non-existent-board')
        .set('Authorization', authToken)
        .expect(404);

      expect(response.body.error.type).toBe('not_found');
    });

    it('should include related data based on query parameters', async () => {
      mockPrisma.board.findFirst.mockResolvedValue({
        ...testBoard,
        items: [],
        members: [{ id: 'member-1', userId: testUser.id, role: 'admin' }],
      });
      mockRedis.getCache.mockResolvedValue(null);

      await request(testApp)
        .get(`/api/v1/boards/${testBoard.id}`)
        .query({ includeItems: 'true', includeMembers: 'true' })
        .set('Authorization', authToken)
        .expect(200);

      expect(mockPrisma.board.findFirst).toHaveBeenCalledWith(
        expect.objectContaining({
          include: expect.objectContaining({
            items: expect.any(Object),
            members: expect.any(Object),
          }),
        })
      );
    });
  });

  describe('POST /api/v1/boards', () => {
    const newBoardData = {
      name: 'New Test Board',
      description: 'New board description',
      workspaceId: testWorkspace.id,
      isPrivate: false,
      columns: [
        { name: 'To Do' },
        { name: 'Done' },
      ],
    };

    it('should create board successfully', async () => {
      // Mock workspace access check
      mockPrisma.workspace.findUnique.mockResolvedValue({
        ...testWorkspace,
        members: [{ userId: testUser.id }],
      });

      // Mock board creation
      mockPrisma.board.create.mockResolvedValue({
        ...testBoard,
        ...newBoardData,
      });

      const response = await request(testApp)
        .post('/api/v1/boards')
        .set('Authorization', authToken)
        .send(newBoardData)
        .expect(201);

      expect(response.body.data).toEqual(
        expect.objectContaining({
          name: newBoardData.name,
          description: newBoardData.description,
          workspaceId: newBoardData.workspaceId,
        })
      );

      expect(mockPrisma.board.create).toHaveBeenCalledWith(
        expect.objectContaining({
          data: expect.objectContaining({
            name: newBoardData.name,
            description: newBoardData.description,
            workspaceId: newBoardData.workspaceId,
            createdBy: testUser.id,
          }),
        })
      );
    });

    it('should validate required fields', async () => {
      await request(testApp)
        .post('/api/v1/boards')
        .set('Authorization', authToken)
        .send({
          description: 'Missing name',
        })
        .expect(400);
    });

    it('should validate workspace access', async () => {
      mockPrisma.workspace.findUnique.mockResolvedValue(null);

      await request(testApp)
        .post('/api/v1/boards')
        .set('Authorization', authToken)
        .send(newBoardData)
        .expect(404);
    });

    it('should handle private workspace access denial', async () => {
      mockPrisma.workspace.findUnique.mockResolvedValue({
        ...testWorkspace,
        isPrivate: true,
        members: [], // User not a member
      });

      await request(testApp)
        .post('/api/v1/boards')
        .set('Authorization', authToken)
        .send(newBoardData)
        .expect(403);
    });
  });

  describe('PUT /api/v1/boards/:boardId', () => {
    const updateData = {
      name: 'Updated Board Name',
      description: 'Updated description',
    };

    it('should update board successfully', async () => {
      // Mock permission check
      mockPrisma.boardMember.findUnique.mockResolvedValue({
        id: 'member-1',
        boardId: testBoard.id,
        userId: testUser.id,
        role: 'admin',
      });

      // Mock board update
      mockPrisma.board.update.mockResolvedValue({
        ...testBoard,
        ...updateData,
      });

      mockRedis.deleteCachePattern.mockResolvedValue(undefined);

      const response = await request(testApp)
        .put(`/api/v1/boards/${testBoard.id}`)
        .set('Authorization', authToken)
        .send(updateData)
        .expect(200);

      expect(response.body.data).toEqual(
        expect.objectContaining({
          name: updateData.name,
          description: updateData.description,
        })
      );

      expect(mockPrisma.board.update).toHaveBeenCalledWith(
        expect.objectContaining({
          where: { id: testBoard.id },
          data: updateData,
        })
      );
    });

    it('should handle access denied', async () => {
      mockPrisma.boardMember.findUnique.mockResolvedValue(null);

      await request(testApp)
        .put(`/api/v1/boards/${testBoard.id}`)
        .set('Authorization', authToken)
        .send(updateData)
        .expect(403);
    });

    it('should validate update data', async () => {
      await request(testApp)
        .put(`/api/v1/boards/${testBoard.id}`)
        .set('Authorization', authToken)
        .send({ name: '' }) // Empty name
        .expect(400);
    });
  });

  describe('DELETE /api/v1/boards/:boardId', () => {
    it('should delete board successfully', async () => {
      // Mock admin permission check
      mockPrisma.boardMember.findUnique.mockResolvedValue({
        id: 'member-1',
        boardId: testBoard.id,
        userId: testUser.id,
        role: 'admin',
      });

      // Mock soft delete
      mockPrisma.board.update.mockResolvedValue({
        ...testBoard,
        deletedAt: new Date(),
      });

      mockRedis.deleteCachePattern.mockResolvedValue(undefined);

      await request(testApp)
        .delete(`/api/v1/boards/${testBoard.id}`)
        .set('Authorization', authToken)
        .expect(204);

      expect(mockPrisma.board.update).toHaveBeenCalledWith(
        expect.objectContaining({
          where: { id: testBoard.id },
          data: { deletedAt: expect.any(Date) },
        })
      );
    });

    it('should require admin permissions', async () => {
      mockPrisma.boardMember.findUnique.mockResolvedValue({
        id: 'member-1',
        boardId: testBoard.id,
        userId: testUser.id,
        role: 'member', // Not admin
      });

      await request(testApp)
        .delete(`/api/v1/boards/${testBoard.id}`)
        .set('Authorization', authToken)
        .expect(403);
    });
  });

  describe('POST /api/v1/boards/:boardId/share', () => {
    const shareData = {
      userIds: ['user-2', 'user-3'],
      permissions: ['read', 'write'],
      message: 'Welcome to the board!',
    };

    it('should share board with multiple users', async () => {
      // Mock admin permission check
      mockPrisma.boardMember.findUnique.mockResolvedValue({
        id: 'member-1',
        boardId: testBoard.id,
        userId: testUser.id,
        role: 'admin',
      });

      // Mock successful member additions
      mockPrisma.boardMember.create
        .mockResolvedValueOnce({
          id: 'member-2',
          boardId: testBoard.id,
          userId: 'user-2',
          role: 'member',
        })
        .mockResolvedValueOnce({
          id: 'member-3',
          boardId: testBoard.id,
          userId: 'user-3',
          role: 'member',
        });

      // Mock member existence checks
      mockPrisma.boardMember.findUnique
        .mockResolvedValueOnce(null) // user-2 not a member
        .mockResolvedValueOnce(null); // user-3 not a member

      mockRedis.deleteCachePattern.mockResolvedValue(undefined);

      const response = await request(testApp)
        .post(`/api/v1/boards/${testBoard.id}/share`)
        .set('Authorization', authToken)
        .send(shareData)
        .expect(200);

      expect(response.body.data).toEqual({
        sharedWithCount: 2,
        failedUsers: [],
        totalRequested: 2,
      });
    });

    it('should handle sharing failures gracefully', async () => {
      // Mock admin permission check
      mockPrisma.boardMember.findUnique
        .mockResolvedValueOnce({
          id: 'member-1',
          boardId: testBoard.id,
          userId: testUser.id,
          role: 'admin',
        })
        .mockResolvedValueOnce(null) // user-2 not a member
        .mockResolvedValueOnce({ // user-3 already a member
          id: 'existing-member',
          boardId: testBoard.id,
          userId: 'user-3',
          role: 'member',
        });

      // Mock one successful, one failed addition
      mockPrisma.boardMember.create
        .mockResolvedValueOnce({
          id: 'member-2',
          boardId: testBoard.id,
          userId: 'user-2',
          role: 'member',
        });

      const response = await request(testApp)
        .post(`/api/v1/boards/${testBoard.id}/share`)
        .set('Authorization', authToken)
        .send(shareData)
        .expect(200);

      expect(response.body.data.sharedWithCount).toBe(1);
      expect(response.body.data.failedUsers).toHaveLength(1);
    });

    it('should validate user IDs', async () => {
      await request(testApp)
        .post(`/api/v1/boards/${testBoard.id}/share`)
        .set('Authorization', authToken)
        .send({
          userIds: ['invalid-uuid'],
        })
        .expect(400);
    });
  });

  describe('POST /api/v1/boards/:boardId/duplicate', () => {
    const duplicateData = {
      name: 'Duplicated Board',
      includeItems: true,
      includeMembers: false,
    };

    it('should duplicate board successfully', async () => {
      // Mock original board retrieval
      mockPrisma.board.findFirst.mockResolvedValue(testBoard);

      // Mock workspace access check
      mockPrisma.workspace.findUnique.mockResolvedValue({
        ...testWorkspace,
        members: [{ userId: testUser.id }],
      });

      // Mock duplicated board creation
      mockPrisma.board.create.mockResolvedValue({
        ...testBoard,
        id: 'new-board-uuid',
        name: duplicateData.name,
        description: `Copy of ${testBoard.description}`,
      });

      const response = await request(testApp)
        .post(`/api/v1/boards/${testBoard.id}/duplicate`)
        .set('Authorization', authToken)
        .send(duplicateData)
        .expect(201);

      expect(response.body.data).toEqual(
        expect.objectContaining({
          name: duplicateData.name,
          description: `Copy of ${testBoard.description}`,
        })
      );

      expect(mockPrisma.board.create).toHaveBeenCalledWith(
        expect.objectContaining({
          data: expect.objectContaining({
            name: duplicateData.name,
            createdBy: testUser.id,
          }),
        })
      );
    });

    it('should handle original board not found', async () => {
      mockPrisma.board.findFirst.mockResolvedValue(null);

      await request(testApp)
        .post(`/api/v1/boards/${testBoard.id}/duplicate`)
        .set('Authorization', authToken)
        .send(duplicateData)
        .expect(404);
    });
  });

  describe('Authentication & Authorization', () => {
    it('should require authentication', async () => {
      // Remove auth mock
      jest.spyOn(require('../../middleware/auth'), 'authenticateToken').mockImplementation((req, res, next) => {
        res.status(401).json({ error: { type: 'authentication_error', message: 'Token required' } });
      });

      await request(testApp)
        .get(`/api/v1/boards/${testBoard.id}`)
        .expect(401);
    });

    it('should handle invalid tokens', async () => {
      jest.spyOn(require('../../middleware/auth'), 'authenticateToken').mockImplementation((req, res, next) => {
        res.status(401).json({ error: { type: 'authentication_error', message: 'Invalid token' } });
      });

      await request(testApp)
        .get(`/api/v1/boards/${testBoard.id}`)
        .set('Authorization', 'Bearer invalid-token')
        .expect(401);
    });
  });

  describe('Error Handling', () => {
    it('should handle database errors gracefully', async () => {
      mockPrisma.board.findFirst.mockRejectedValue(new Error('Database connection failed'));

      await request(testApp)
        .get(`/api/v1/boards/${testBoard.id}`)
        .set('Authorization', authToken)
        .expect(500);
    });

    it('should handle validation errors properly', async () => {
      await request(testApp)
        .post('/api/v1/boards')
        .set('Authorization', authToken)
        .send({
          name: 'a'.repeat(101), // Exceeds max length
          workspaceId: 'invalid-uuid',
        })
        .expect(400);
    });
  });
});