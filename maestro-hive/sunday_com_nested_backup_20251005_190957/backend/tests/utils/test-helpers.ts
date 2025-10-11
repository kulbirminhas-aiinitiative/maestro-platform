import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcrypt';
import jwt from 'jsonwebtoken';
import { config } from '../../src/config';

export const testPrisma = new PrismaClient({
  datasources: {
    db: {
      url: process.env.DATABASE_URL_TEST,
    },
  },
});

// Test data factories
export class TestDataFactory {
  /**
   * Create a test user
   */
  static async createUser(overrides: Partial<any> = {}) {
    const defaultUser = {
      email: `test-${Date.now()}@example.com`,
      emailVerified: true,
      passwordHash: await bcrypt.hash('testpassword123', 10),
      firstName: 'Test',
      lastName: 'User',
      timezone: 'UTC',
      locale: 'en',
      settings: {},
    };

    return testPrisma.user.create({
      data: { ...defaultUser, ...overrides },
    });
  }

  /**
   * Create a test organization
   */
  static async createOrganization(overrides: Partial<any> = {}) {
    const defaultOrg = {
      name: `Test Organization ${Date.now()}`,
      slug: `test-org-${Date.now()}`,
      settings: {},
      subscriptionPlan: 'free',
      subscriptionStatus: 'active',
    };

    return testPrisma.organization.create({
      data: { ...defaultOrg, ...overrides },
    });
  }

  /**
   * Create a test workspace
   */
  static async createWorkspace(organizationId: string, overrides: Partial<any> = {}) {
    const defaultWorkspace = {
      organizationId,
      name: `Test Workspace ${Date.now()}`,
      description: 'Test workspace for testing',
      color: '#6B7280',
      settings: {},
      isPrivate: false,
    };

    return testPrisma.workspace.create({
      data: { ...defaultWorkspace, ...overrides },
    });
  }

  /**
   * Create a test board
   */
  static async createBoard(workspaceId: string, createdBy: string, overrides: Partial<any> = {}) {
    const defaultBoard = {
      workspaceId,
      name: `Test Board ${Date.now()}`,
      description: 'Test board for testing',
      settings: {},
      viewSettings: {},
      isPrivate: false,
      createdBy,
    };

    return testPrisma.board.create({
      data: { ...defaultBoard, ...overrides },
    });
  }

  /**
   * Create board columns
   */
  static async createBoardColumns(boardId: string, count: number = 3) {
    const columns = [
      { name: 'To Do', columnType: 'status', position: 0 },
      { name: 'In Progress', columnType: 'status', position: 1 },
      { name: 'Done', columnType: 'status', position: 2 },
    ];

    return Promise.all(
      columns.slice(0, count).map(column =>
        testPrisma.boardColumn.create({
          data: {
            boardId,
            ...column,
            settings: {},
            validationRules: {},
            isRequired: false,
            isVisible: true,
          },
        })
      )
    );
  }

  /**
   * Create a test item
   */
  static async createItem(boardId: string, createdBy: string, overrides: Partial<any> = {}) {
    const defaultItem = {
      boardId,
      name: `Test Item ${Date.now()}`,
      description: 'Test item for testing',
      itemData: {},
      position: Math.random() * 1000,
      createdBy,
    };

    return testPrisma.item.create({
      data: { ...defaultItem, ...overrides },
    });
  }

  /**
   * Create organization membership
   */
  static async createOrganizationMember(
    organizationId: string,
    userId: string,
    role: string = 'member'
  ) {
    return testPrisma.organizationMember.create({
      data: {
        organizationId,
        userId,
        role,
        status: 'active',
        joinedAt: new Date(),
      },
    });
  }

  /**
   * Create workspace membership
   */
  static async createWorkspaceMember(
    workspaceId: string,
    userId: string,
    role: string = 'member'
  ) {
    return testPrisma.workspaceMember.create({
      data: {
        workspaceId,
        userId,
        role,
        permissions: {},
      },
    });
  }

  /**
   * Create board membership
   */
  static async createBoardMember(
    boardId: string,
    userId: string,
    role: string = 'member'
  ) {
    return testPrisma.boardMember.create({
      data: {
        boardId,
        userId,
        role,
        permissions: {},
      },
    });
  }

  /**
   * Create a complete test setup with user, org, workspace, and board
   */
  static async createCompleteSetup() {
    const user = await this.createUser();
    const organization = await this.createOrganization();
    const workspace = await this.createWorkspace(organization.id);
    const board = await this.createBoard(workspace.id, user.id);

    // Create memberships
    await this.createOrganizationMember(organization.id, user.id, 'admin');
    await this.createWorkspaceMember(workspace.id, user.id, 'admin');
    await this.createBoardMember(board.id, user.id, 'admin');

    // Create board columns
    const columns = await this.createBoardColumns(board.id);

    return {
      user,
      organization,
      workspace,
      board,
      columns,
    };
  }
}

// Authentication helpers
export class AuthHelper {
  /**
   * Generate JWT token for user
   */
  static generateToken(userId: string, email: string): string {
    return jwt.sign(
      {
        sub: userId,
        email,
        iat: Math.floor(Date.now() / 1000),
        exp: Math.floor(Date.now() / 1000) + 3600, // 1 hour
      },
      config.jwt.secret
    );
  }

  /**
   * Create authorization header
   */
  static createAuthHeader(token: string): { Authorization: string } {
    return { Authorization: `Bearer ${token}` };
  }

  /**
   * Create authenticated request context
   */
  static async createAuthenticatedContext() {
    const user = await TestDataFactory.createUser();
    const token = this.generateToken(user.id, user.email);
    const headers = this.createAuthHeader(token);

    return { user, token, headers };
  }
}

// Database helpers
export class DatabaseHelper {
  /**
   * Clean all test data
   */
  static async cleanDatabase() {
    await testPrisma.$transaction([
      testPrisma.activityLog.deleteMany(),
      testPrisma.automationExecution.deleteMany(),
      testPrisma.automationRule.deleteMany(),
      testPrisma.webhookDelivery.deleteMany(),
      testPrisma.webhook.deleteMany(),
      testPrisma.fileAttachment.deleteMany(),
      testPrisma.file.deleteMany(),
      testPrisma.timeEntry.deleteMany(),
      testPrisma.comment.deleteMany(),
      testPrisma.itemDependency.deleteMany(),
      testPrisma.itemAssignment.deleteMany(),
      testPrisma.item.deleteMany(),
      testPrisma.boardMember.deleteMany(),
      testPrisma.boardColumn.deleteMany(),
      testPrisma.board.deleteMany(),
      testPrisma.folder.deleteMany(),
      testPrisma.workspaceMember.deleteMany(),
      testPrisma.workspace.deleteMany(),
      testPrisma.organizationMember.deleteMany(),
      testPrisma.organization.deleteMany(),
      testPrisma.user.deleteMany(),
      testPrisma.boardTemplate.deleteMany(),
    ]);
  }

  /**
   * Reset auto-increment sequences
   */
  static async resetSequences() {
    // Note: This is PostgreSQL specific
    // For other databases, implement accordingly
    const tableNames = [
      'users', 'organizations', 'workspaces', 'boards', 'items',
      'comments', 'files', 'automation_rules', 'webhooks'
    ];

    for (const tableName of tableNames) {
      try {
        await testPrisma.$executeRawUnsafe(`
          SELECT setval(pg_get_serial_sequence('${tableName}', 'id'), 1, false);
        `);
      } catch (error) {
        // Ignore errors for tables without auto-increment
      }
    }
  }

  /**
   * Get database stats for debugging
   */
  static async getDatabaseStats() {
    const stats = await testPrisma.$transaction([
      testPrisma.user.count(),
      testPrisma.organization.count(),
      testPrisma.workspace.count(),
      testPrisma.board.count(),
      testPrisma.item.count(),
    ]);

    return {
      users: stats[0],
      organizations: stats[1],
      workspaces: stats[2],
      boards: stats[3],
      items: stats[4],
    };
  }
}

// API test helpers
export class ApiTestHelper {
  /**
   * Check if response has correct API structure
   */
  static expectValidApiResponse(response: any, expectedData?: any) {
    expect(response).toHaveProperty('data');

    if (expectedData) {
      expect(response.data).toMatchObject(expectedData);
    }
  }

  /**
   * Check if response has error structure
   */
  static expectApiError(response: any, errorType?: string) {
    expect(response).toHaveProperty('error');
    expect(response.error).toHaveProperty('type');
    expect(response.error).toHaveProperty('message');

    if (errorType) {
      expect(response.error.type).toBe(errorType);
    }
  }

  /**
   * Check paginated response structure
   */
  static expectPaginatedResponse(response: any) {
    expect(response).toHaveProperty('data');
    expect(response).toHaveProperty('meta');
    expect(response.meta).toHaveProperty('page');
    expect(response.meta).toHaveProperty('limit');
    expect(response.meta).toHaveProperty('total');
    expect(response.meta).toHaveProperty('totalPages');
    expect(response.meta).toHaveProperty('hasNext');
    expect(response.meta).toHaveProperty('hasPrev');
  }
}

// Mock helpers
export class MockHelper {
  /**
   * Mock Redis service
   */
  static mockRedisService() {
    const mockRedis = {
      getCache: jest.fn(),
      setCache: jest.fn(),
      deleteCache: jest.fn(),
      setHash: jest.fn(),
      getHashField: jest.fn(),
      getAllHashFields: jest.fn(),
      deleteHashField: jest.fn(),
      setIfNotExists: jest.fn(),
      getKeysByPattern: jest.fn(),
      deleteCachePattern: jest.fn(),
    };

    jest.doMock('../../src/config/redis', () => ({
      RedisService: mockRedis,
    }));

    return mockRedis;
  }

  /**
   * Mock Socket.IO
   */
  static mockSocketIO() {
    const mockIO = {
      to: jest.fn().mockReturnThis(),
      emit: jest.fn(),
      in: jest.fn().mockReturnThis(),
      fetchSockets: jest.fn().mockResolvedValue([]),
      except: jest.fn().mockReturnThis(),
    };

    jest.doMock('../../src/server', () => ({
      io: mockIO,
    }));

    return mockIO;
  }

  /**
   * Mock external services
   */
  static mockExternalServices() {
    // Mock email service
    const mockEmailService = {
      sendEmail: jest.fn().mockResolvedValue(true),
    };

    // Mock file storage
    const mockFileStorage = {
      uploadFile: jest.fn().mockResolvedValue({ fileKey: 'test-key', url: 'test-url' }),
      deleteFile: jest.fn().mockResolvedValue(true),
    };

    return {
      emailService: mockEmailService,
      fileStorage: mockFileStorage,
    };
  }
}

// Test assertion helpers
export class TestAssertions {
  /**
   * Assert user object structure
   */
  static expectUserObject(user: any) {
    expect(user).toHaveProperty('id');
    expect(user).toHaveProperty('email');
    expect(user).toHaveProperty('firstName');
    expect(user).toHaveProperty('lastName');
    expect(user).toHaveProperty('createdAt');
    expect(user).not.toHaveProperty('passwordHash');
  }

  /**
   * Assert board object structure
   */
  static expectBoardObject(board: any) {
    expect(board).toHaveProperty('id');
    expect(board).toHaveProperty('name');
    expect(board).toHaveProperty('workspaceId');
    expect(board).toHaveProperty('createdBy');
    expect(board).toHaveProperty('createdAt');
  }

  /**
   * Assert item object structure
   */
  static expectItemObject(item: any) {
    expect(item).toHaveProperty('id');
    expect(item).toHaveProperty('name');
    expect(item).toHaveProperty('boardId');
    expect(item).toHaveProperty('position');
    expect(item).toHaveProperty('createdBy');
    expect(item).toHaveProperty('createdAt');
  }

  /**
   * Assert timestamp is recent (within last minute)
   */
  static expectRecentTimestamp(timestamp: string | Date) {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    expect(diffMs).toBeLessThan(60000); // Less than 1 minute
  }

  /**
   * Assert UUID format
   */
  static expectValidUUID(uuid: string) {
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    expect(uuid).toMatch(uuidRegex);
  }
}