import request from 'supertest';
import { Express } from 'express';
import jwt from 'jsonwebtoken';
import { prismaMock } from '../setup';
import app from '@/server';
import { config } from '@/config';

// Mock external services
jest.mock('@/services/ai.service', () => ({
  AIService: {
    generateTaskSuggestions: jest.fn(),
    autoTagItem: jest.fn(),
    analyzeWorkloadDistribution: jest.fn(),
  },
}));

jest.mock('@/services/automation.service', () => ({
  AutomationService: {
    createRule: jest.fn(),
    getRules: jest.fn(),
    testRule: jest.fn(),
  },
}));

describe('API Integration Tests', () => {
  let testApp: Express;
  let authToken: string;
  let testUser: any;
  let testOrganization: any;
  let testWorkspace: any;
  let testBoard: any;

  beforeAll(() => {
    testApp = app;
  });

  beforeEach(() => {
    jest.clearAllMocks();

    // Setup test data
    testUser = {
      id: 'user-1',
      email: 'test@example.com',
      firstName: 'John',
      lastName: 'Doe',
      organizations: [
        {
          organizationId: 'org-1',
          role: 'admin',
        },
      ],
    };

    testOrganization = {
      id: 'org-1',
      name: 'Test Organization',
      slug: 'test-org',
    };

    testWorkspace = {
      id: 'workspace-1',
      name: 'Test Workspace',
      organizationId: 'org-1',
      members: [
        {
          userId: 'user-1',
          role: 'admin',
        },
      ],
    };

    testBoard = {
      id: 'board-1',
      name: 'Test Board',
      workspaceId: 'workspace-1',
      columns: [
        { id: 'col-1', name: 'To Do', position: 0 },
        { id: 'col-2', name: 'In Progress', position: 1 },
        { id: 'col-3', name: 'Done', position: 2 },
      ],
      members: [
        {
          userId: 'user-1',
          role: 'admin',
        },
      ],
      creator: testUser,
      _count: {
        items: 0,
        members: 1,
        columns: 3,
      },
    };

    // Generate auth token
    authToken = jwt.sign(
      { sub: testUser.id, email: testUser.email },
      config.security.jwtSecret,
      { expiresIn: '1h' }
    );

    // Mock authentication middleware
    prismaMock.user.findUnique.mockResolvedValue(testUser);
  });

  describe('Authentication', () => {
    it('should reject requests without token', async () => {
      const response = await request(testApp)
        .get('/api/v1/boards/board-1')
        .expect(401);

      expect(response.body.error.type).toBe('authentication_required');
    });

    it('should accept requests with valid token', async () => {
      prismaMock.board.findFirst.mockResolvedValue(testBoard);

      const response = await request(testApp)
        .get('/api/v1/boards/board-1')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body.data).toMatchObject({
        id: 'board-1',
        name: 'Test Board',
      });
    });
  });

  describe('Board Management', () => {
    it('should create a new board', async () => {
      prismaMock.workspace.findUnique.mockResolvedValue(testWorkspace);
      prismaMock.board.create.mockResolvedValue(testBoard);

      const boardData = {
        name: 'New Test Board',
        description: 'A board for testing',
        workspaceId: 'workspace-1',
        columns: [
          { name: 'To Do', color: '#ff0000' },
          { name: 'In Progress', color: '#ffff00' },
          { name: 'Done', color: '#00ff00' },
        ],
      };

      const response = await request(testApp)
        .post('/api/v1/boards')
        .set('Authorization', `Bearer ${authToken}`)
        .send(boardData)
        .expect(201);

      expect(response.body.data).toMatchObject({
        id: 'board-1',
        name: 'Test Board',
      });
    });

    it('should get board with items and members', async () => {
      const boardWithDetails = {
        ...testBoard,
        items: [
          {
            id: 'item-1',
            name: 'Test Item',
            assignments: [{ user: testUser }],
            _count: { comments: 2, children: 0, dependencies: 0 },
          },
        ],
        members: [
          {
            id: 'member-1',
            userId: 'user-1',
            role: 'admin',
            user: testUser,
          },
        ],
      };

      prismaMock.board.findFirst.mockResolvedValue(boardWithDetails);

      const response = await request(testApp)
        .get('/api/v1/boards/board-1')
        .set('Authorization', `Bearer ${authToken}`)
        .query({ includeItems: 'true', includeMembers: 'true' })
        .expect(200);

      expect(response.body.data).toMatchObject({
        id: 'board-1',
        name: 'Test Board',
        items: expect.any(Array),
        members: expect.any(Array),
      });
    });

    it('should update board', async () => {
      const updatedBoard = {
        ...testBoard,
        name: 'Updated Board Name',
        description: 'Updated description',
      };

      prismaMock.board.update.mockResolvedValue(updatedBoard);

      // Mock board access check
      const { BoardService } = require('@/services/board.service');
      BoardService.hasWriteAccess = jest.fn().mockResolvedValue(true);

      const response = await request(testApp)
        .put('/api/v1/boards/board-1')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          name: 'Updated Board Name',
          description: 'Updated description',
        })
        .expect(200);

      expect(response.body.data.name).toBe('Updated Board Name');
    });
  });

  describe('Item Management', () => {
    const testItem = {
      id: 'item-1',
      name: 'Test Item',
      description: 'A test item',
      boardId: 'board-1',
      assignments: [{ user: testUser }],
      creator: testUser,
      _count: { comments: 0, children: 0, dependencies: 0 },
    };

    it('should create a new item', async () => {
      // Mock board access check
      const { ItemService } = require('@/services/item.service');
      ItemService.checkBoardAccess = jest.fn().mockResolvedValue(true);

      prismaMock.item.create.mockResolvedValue(testItem);

      const itemData = {
        name: 'New Test Item',
        description: 'A new item for testing',
        boardId: 'board-1',
        itemData: {
          priority: 'high',
          status: 'todo',
        },
        assigneeIds: ['user-1'],
      };

      const response = await request(testApp)
        .post('/api/v1/items')
        .set('Authorization', `Bearer ${authToken}`)
        .send(itemData)
        .expect(201);

      expect(response.body.data).toMatchObject({
        id: 'item-1',
        name: 'Test Item',
      });
    });

    it('should get items for a board', async () => {
      // Mock board access check
      const { ItemService } = require('@/services/item.service');
      ItemService.getByBoard = jest.fn().mockResolvedValue({
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

      const response = await request(testApp)
        .get('/api/v1/items/board/board-1')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body.data).toHaveLength(1);
      expect(response.body.meta.total).toBe(1);
    });

    it('should update item', async () => {
      const updatedItem = {
        ...testItem,
        name: 'Updated Item Name',
        itemData: { status: 'in_progress' },
      };

      // Mock current item for change tracking
      prismaMock.item.findUnique.mockResolvedValue(testItem);
      prismaMock.item.update.mockResolvedValue(updatedItem);

      const { ItemService } = require('@/services/item.service');
      ItemService.checkBoardAccess = jest.fn().mockResolvedValue(true);

      const response = await request(testApp)
        .put('/api/v1/items/item-1')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          name: 'Updated Item Name',
          itemData: { status: 'in_progress' },
        })
        .expect(200);

      expect(response.body.data.name).toBe('Updated Item Name');
    });
  });

  describe('Comment Management', () => {
    const testComment = {
      id: 'comment-1',
      content: 'This is a test comment',
      itemId: 'item-1',
      userId: 'user-1',
      user: {
        id: 'user-1',
        firstName: 'John',
        lastName: 'Doe',
        avatarUrl: null,
      },
      mentions: [],
      _count: { replies: 0, reactions: 0 },
    };

    it('should create a comment', async () => {
      // Mock item access check
      const { CommentService } = require('@/services/comment.service');
      CommentService.checkItemAccess = jest.fn().mockResolvedValue(true);

      prismaMock.comment.create.mockResolvedValue(testComment);
      prismaMock.item.findUnique.mockResolvedValue({ boardId: 'board-1' });

      const response = await request(testApp)
        .post('/api/v1/comments/item-1')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          content: 'This is a test comment',
          mentions: ['user-2'],
        })
        .expect(201);

      expect(response.body.data).toMatchObject({
        id: 'comment-1',
        content: 'This is a test comment',
      });
    });

    it('should get comments for an item', async () => {
      // Mock item access check
      const { CommentService } = require('@/services/comment.service');
      CommentService.getByItem = jest.fn().mockResolvedValue({
        data: [testComment],
        meta: {
          page: 1,
          limit: 20,
          total: 1,
          totalPages: 1,
          hasNext: false,
          hasPrev: false,
        },
      });

      const response = await request(testApp)
        .get('/api/v1/comments/item/item-1')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body.data).toHaveLength(1);
      expect(response.body.data[0]).toMatchObject({
        id: 'comment-1',
        content: 'This is a test comment',
      });
    });

    it('should add reaction to comment', async () => {
      prismaMock.comment.findFirst.mockResolvedValue(testComment);
      prismaMock.commentReaction.findUnique.mockResolvedValue(null);
      prismaMock.commentReaction.create.mockResolvedValue({});
      prismaMock.commentReaction.groupBy.mockResolvedValue([
        { emoji: '👍', _count: { emoji: 1 } },
      ]);
      prismaMock.item.findUnique.mockResolvedValue({ boardId: 'board-1' });

      const response = await request(testApp)
        .post('/api/v1/comments/comment-1/reactions')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ emoji: '👍' })
        .expect(201);

      expect(response.body.data.message).toBe('Reaction added successfully');
    });
  });

  describe('AI Features', () => {
    it('should generate task suggestions', async () => {
      const { AIService } = require('@/services/ai.service');
      AIService.generateTaskSuggestions.mockResolvedValue([
        {
          title: 'Review code',
          description: 'Review the recent code changes',
          priority: 'medium',
          estimatedDuration: 30,
          tags: ['review', 'code'],
          confidence: 0.8,
        },
      ]);

      const response = await request(testApp)
        .post('/api/v1/ai/suggestions/tasks/board-1')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          context: 'Need to finish the sprint tasks',
          limit: 5,
        })
        .expect(200);

      expect(response.body.data.suggestions).toHaveLength(1);
      expect(response.body.data.suggestions[0]).toMatchObject({
        title: 'Review code',
        priority: 'medium',
      });
    });

    it('should auto-tag an item', async () => {
      prismaMock.item.findUnique.mockResolvedValue({
        name: 'Update API documentation',
        description: 'Need to update the REST API docs',
      });

      const { AIService } = require('@/services/ai.service');
      AIService.autoTagItem.mockResolvedValue({
        tags: ['documentation', 'api'],
        categories: ['development'],
        priority: 'medium',
        confidence: 0.9,
      });

      const response = await request(testApp)
        .post('/api/v1/ai/tags/item-1')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body.data).toMatchObject({
        tags: ['documentation', 'api'],
        priority: 'medium',
      });
    });
  });

  describe('Automation Features', () => {
    it('should create automation rule', async () => {
      const { AutomationService } = require('@/services/automation.service');
      AutomationService.createRule.mockResolvedValue({
        id: 'rule-1',
        name: 'Auto-assign urgent items',
        isEnabled: true,
      });

      const ruleData = {
        name: 'Auto-assign urgent items',
        description: 'Automatically assign urgent items to team lead',
        trigger: {
          type: 'item_created',
          conditions: {},
        },
        conditions: {
          priority: { equals: 'urgent' },
        },
        actions: [
          {
            type: 'assign_item',
            parameters: { userId: 'team-lead-id' },
          },
        ],
        organizationId: 'org-1',
        boardId: 'board-1',
      };

      const response = await request(testApp)
        .post('/api/v1/automation/rules')
        .set('Authorization', `Bearer ${authToken}`)
        .send(ruleData)
        .expect(201);

      expect(response.body.data).toMatchObject({
        id: 'rule-1',
        name: 'Auto-assign urgent items',
      });
    });

    it('should test automation rule', async () => {
      const { AutomationService } = require('@/services/automation.service');
      AutomationService.testRule.mockResolvedValue({
        triggered: true,
        conditionResults: { priority: true },
        simulatedActions: [
          {
            type: 'assign_item',
            parameters: { userId: 'user-1' },
            wouldExecute: true,
          },
        ],
      });

      const testContext = {
        entityType: 'item',
        entityId: 'item-1',
        action: 'item_created',
        userId: 'user-1',
        organizationId: 'org-1',
        newValues: { priority: 'urgent' },
      };

      const response = await request(testApp)
        .post('/api/v1/automation/rules/rule-1/test')
        .set('Authorization', `Bearer ${authToken}`)
        .send({ testContext })
        .expect(200);

      expect(response.body.data).toMatchObject({
        triggered: true,
        conditionResults: { priority: true },
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle validation errors', async () => {
      const response = await request(testApp)
        .post('/api/v1/boards')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          // Missing required fields
          description: 'A board without a name',
        })
        .expect(400);

      expect(response.body.error.type).toBe('validation_error');
    });

    it('should handle not found errors', async () => {
      prismaMock.board.findFirst.mockResolvedValue(null);

      const response = await request(testApp)
        .get('/api/v1/boards/nonexistent-board')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(404);

      expect(response.body.error.type).toBe('not_found');
    });

    it('should handle server errors gracefully', async () => {
      prismaMock.board.findFirst.mockRejectedValue(new Error('Database error'));

      const response = await request(testApp)
        .get('/api/v1/boards/board-1')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(500);

      expect(response.body.error.type).toBe('internal_error');
    });
  });

  describe('Health Check', () => {
    it('should return health status', async () => {
      const response = await request(testApp)
        .get('/health')
        .expect(200);

      expect(response.body).toMatchObject({
        status: expect.any(String),
        timestamp: expect.any(String),
        version: expect.any(String),
        uptime: expect.any(Number),
      });
    });
  });
});