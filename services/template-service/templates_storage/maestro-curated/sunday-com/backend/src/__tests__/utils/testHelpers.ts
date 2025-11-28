import { prisma } from '@/config/database';
import { AuthService } from '@/services/auth.service';
import { OrganizationService } from '@/services/organization.service';
import bcrypt from 'bcryptjs';
import { nanoid } from 'nanoid';

export interface TestUser {
  id: string;
  email: string;
  firstName: string;
  lastName: string;
  passwordHash: string;
  tokens?: {
    accessToken: string;
    refreshToken: string;
    expiresIn: number;
  };
}

export interface TestOrganization {
  id: string;
  name: string;
  slug: string;
  description?: string;
  members?: Array<{
    userId: string;
    role: string;
    status: string;
  }>;
}

export interface TestWorkspace {
  id: string;
  name: string;
  organizationId: string;
}

export interface TestBoard {
  id: string;
  name: string;
  workspaceId: string;
}

export interface TestItem {
  id: string;
  name: string;
  boardId: string;
  status?: string;
  assigneeId?: string;
}

/**
 * Test data factory for creating consistent test data
 */
export class TestDataFactory {
  /**
   * Create a test user with specified properties
   */
  static async createUser(userData: Partial<TestUser> = {}): Promise<TestUser> {
    const defaultPassword = 'TestPassword123!';
    const passwordHash = await bcrypt.hash(defaultPassword, 12);

    const user = await prisma.user.create({
      data: {
        email: userData.email || `test-${nanoid(8)}@example.com`,
        firstName: userData.firstName || 'Test',
        lastName: userData.lastName || 'User',
        passwordHash,
        emailVerified: true,
        timezone: 'UTC',
        locale: 'en',
        settings: {},
      },
    });

    return {
      id: user.id,
      email: user.email,
      firstName: user.firstName,
      lastName: user.lastName,
      passwordHash: user.passwordHash,
    };
  }

  /**
   * Create a test user with authentication tokens
   */
  static async createAuthenticatedUser(userData: Partial<TestUser> = {}): Promise<TestUser> {
    const user = await this.createUser(userData);

    // Generate tokens
    const tokens = await AuthService.generateTokens({
      id: user.id,
      email: user.email,
    });

    return {
      ...user,
      tokens,
    };
  }

  /**
   * Create a test organization with owner
   */
  static async createOrganization(
    organizationData: Partial<TestOrganization> = {},
    ownerId?: string
  ): Promise<TestOrganization> {
    let owner: TestUser;

    if (ownerId) {
      const existingUser = await prisma.user.findUnique({ where: { id: ownerId } });
      if (!existingUser) {
        throw new Error('Owner user not found');
      }
      owner = {
        id: existingUser.id,
        email: existingUser.email,
        firstName: existingUser.firstName,
        lastName: existingUser.lastName,
        passwordHash: existingUser.passwordHash,
      };
    } else {
      owner = await this.createUser();
    }

    const orgSlug = organizationData.slug || `test-org-${nanoid(8)}`;

    const organization = await OrganizationService.create(
      {
        name: organizationData.name || 'Test Organization',
        slug: orgSlug,
        description: organizationData.description || 'A test organization',
        settings: {},
      },
      owner.id
    );

    return {
      id: organization.id,
      name: organization.name,
      slug: organization.slug,
      description: organization.description || undefined,
      members: organization.members?.map(member => ({
        userId: member.userId,
        role: member.role,
        status: member.status,
      })),
    };
  }

  /**
   * Create a test workspace
   */
  static async createWorkspace(
    workspaceData: Partial<TestWorkspace> = {},
    organizationId?: string
  ): Promise<TestWorkspace> {
    let orgId = organizationId;

    if (!orgId) {
      const org = await this.createOrganization();
      orgId = org.id;
    }

    const workspace = await prisma.workspace.create({
      data: {
        name: workspaceData.name || 'Test Workspace',
        organizationId: orgId,
        description: 'A test workspace',
        settings: {},
        visibility: 'private',
      },
    });

    return {
      id: workspace.id,
      name: workspace.name,
      organizationId: workspace.organizationId,
    };
  }

  /**
   * Create a test board
   */
  static async createBoard(
    boardData: Partial<TestBoard> = {},
    workspaceId?: string
  ): Promise<TestBoard> {
    let wsId = workspaceId;

    if (!wsId) {
      const workspace = await this.createWorkspace();
      wsId = workspace.id;
    }

    const board = await prisma.board.create({
      data: {
        name: boardData.name || 'Test Board',
        workspaceId: wsId,
        description: 'A test board',
        settings: {},
        columnOrder: [],
      },
    });

    return {
      id: board.id,
      name: board.name,
      workspaceId: board.workspaceId,
    };
  }

  /**
   * Create a test item/task
   */
  static async createItem(
    itemData: Partial<TestItem> = {},
    boardId?: string
  ): Promise<TestItem> {
    let bId = boardId;

    if (!bId) {
      const board = await this.createBoard();
      bId = board.id;
    }

    const item = await prisma.item.create({
      data: {
        name: itemData.name || 'Test Task',
        boardId: bId,
        description: 'A test task',
        status: itemData.status || 'not_started',
        position: 1,
        fieldValues: {},
        assigneeId: itemData.assigneeId,
      },
    });

    return {
      id: item.id,
      name: item.name,
      boardId: item.boardId,
      status: item.status || undefined,
      assigneeId: item.assigneeId || undefined,
    };
  }

  /**
   * Create a complete test hierarchy (org -> workspace -> board -> items)
   */
  static async createTestHierarchy(options: {
    users?: number;
    workspaces?: number;
    boards?: number;
    items?: number;
  } = {}) {
    const userCount = options.users || 3;
    const workspaceCount = options.workspaces || 2;
    const boardCount = options.boards || 3;
    const itemCount = options.items || 10;

    // Create users
    const users = await Promise.all(
      Array(userCount).fill(0).map(() => this.createUser())
    );

    // Create organization with first user as owner
    const organization = await this.createOrganization({}, users[0].id);

    // Add other users to organization
    for (let i = 1; i < users.length; i++) {
      await OrganizationService.inviteMember(
        organization.id,
        users[i].email,
        i === 1 ? 'admin' : 'member',
        users[0].id
      );
    }

    // Create workspaces
    const workspaces = await Promise.all(
      Array(workspaceCount).fill(0).map((_, i) =>
        this.createWorkspace(
          { name: `Test Workspace ${i + 1}` },
          organization.id
        )
      )
    );

    // Create boards
    const boards = [];
    for (const workspace of workspaces) {
      const workspaceBoards = await Promise.all(
        Array(boardCount).fill(0).map((_, i) =>
          this.createBoard(
            { name: `Test Board ${i + 1}` },
            workspace.id
          )
        )
      );
      boards.push(...workspaceBoards);
    }

    // Create items
    const items = [];
    for (const board of boards) {
      const boardItems = await Promise.all(
        Array(itemCount).fill(0).map((_, i) =>
          this.createItem(
            {
              name: `Test Task ${i + 1}`,
              assigneeId: users[i % users.length].id,
              status: ['not_started', 'in_progress', 'completed'][i % 3],
            },
            board.id
          )
        )
      );
      items.push(...boardItems);
    }

    return {
      users,
      organization,
      workspaces,
      boards,
      items,
    };
  }
}

/**
 * Database cleanup utilities
 */
export class TestCleanup {
  /**
   * Clean up all test data
   */
  static async cleanupAll(): Promise<void> {
    // Delete in reverse dependency order
    await prisma.activityLog.deleteMany({});
    await prisma.itemFieldValue.deleteMany({});
    await prisma.item.deleteMany({});
    await prisma.boardColumn.deleteMany({});
    await prisma.board.deleteMany({});
    await prisma.workspace.deleteMany({});
    await prisma.organizationMember.deleteMany({});
    await prisma.organization.deleteMany({});
    await prisma.user.deleteMany({});
  }

  /**
   * Clean up test users by email pattern
   */
  static async cleanupTestUsers(): Promise<void> {
    await prisma.user.deleteMany({
      where: {
        email: {
          contains: 'test-',
        },
      },
    });
  }

  /**
   * Clean up specific organization and all related data
   */
  static async cleanupOrganization(organizationId: string): Promise<void> {
    // Get all workspaces
    const workspaces = await prisma.workspace.findMany({
      where: { organizationId },
      include: {
        boards: {
          include: {
            items: true,
          },
        },
      },
    });

    // Clean up items
    for (const workspace of workspaces) {
      for (const board of workspace.boards) {
        await prisma.item.deleteMany({
          where: { boardId: board.id },
        });
      }
    }

    // Clean up boards
    await prisma.board.deleteMany({
      where: {
        workspace: {
          organizationId,
        },
      },
    });

    // Clean up workspaces
    await prisma.workspace.deleteMany({
      where: { organizationId },
    });

    // Clean up organization members
    await prisma.organizationMember.deleteMany({
      where: { organizationId },
    });

    // Clean up organization
    await prisma.organization.delete({
      where: { id: organizationId },
    });
  }
}

/**
 * Mock utilities for external services
 */
export class TestMocks {
  /**
   * Mock Redis service
   */
  static mockRedisService() {
    const RedisService = require('@/config/redis').RedisService;

    return {
      setCache: jest.spyOn(RedisService, 'setCache').mockResolvedValue(undefined),
      getCache: jest.spyOn(RedisService, 'getCache').mockResolvedValue(null),
      deleteCache: jest.spyOn(RedisService, 'deleteCache').mockResolvedValue(undefined),
      deleteCachePattern: jest.spyOn(RedisService, 'deleteCachePattern').mockResolvedValue(undefined),
    };
  }

  /**
   * Mock logger service
   */
  static mockLogger() {
    const Logger = require('@/config/logger').Logger;

    return {
      error: jest.spyOn(Logger, 'error').mockImplementation(() => {}),
      warn: jest.spyOn(Logger, 'warn').mockImplementation(() => {}),
      info: jest.spyOn(Logger, 'info').mockImplementation(() => {}),
      debug: jest.spyOn(Logger, 'debug').mockImplementation(() => {}),
      business: jest.spyOn(Logger, 'business').mockImplementation(() => {}),
    };
  }

  /**
   * Mock email service
   */
  static mockEmailService() {
    // When email service is implemented
    return {
      sendEmail: jest.fn().mockResolvedValue(true),
      sendInvitation: jest.fn().mockResolvedValue(true),
      sendPasswordReset: jest.fn().mockResolvedValue(true),
    };
  }

  /**
   * Restore all mocks
   */
  static restoreAll() {
    jest.restoreAllMocks();
  }
}

/**
 * API testing utilities
 */
export class ApiTestHelpers {
  /**
   * Create authorization header for authenticated requests
   */
  static createAuthHeader(token: string): Record<string, string> {
    return {
      Authorization: `Bearer ${token}`,
    };
  }

  /**
   * Create test request with authentication
   */
  static authenticatedRequest(request: any, token: string) {
    return request.set('Authorization', `Bearer ${token}`);
  }

  /**
   * Assert API response structure
   */
  static assertApiResponse(response: any, expectedStatus: number) {
    expect(response.status).toBe(expectedStatus);

    if (expectedStatus >= 200 && expectedStatus < 300) {
      expect(response.body).toHaveProperty('success', true);
      expect(response.body).toHaveProperty('data');
    } else {
      expect(response.body).toHaveProperty('success', false);
      expect(response.body).toHaveProperty('error');
    }
  }

  /**
   * Assert paginated response structure
   */
  static assertPaginatedResponse(response: any) {
    this.assertApiResponse(response, 200);

    expect(response.body.data).toHaveProperty('data');
    expect(response.body.data).toHaveProperty('meta');
    expect(response.body.data.meta).toHaveProperty('page');
    expect(response.body.data.meta).toHaveProperty('limit');
    expect(response.body.data.meta).toHaveProperty('total');
    expect(response.body.data.meta).toHaveProperty('totalPages');
    expect(response.body.data.meta).toHaveProperty('hasNext');
    expect(response.body.data.meta).toHaveProperty('hasPrev');
  }
}

/**
 * Performance testing utilities
 */
export class PerformanceTestHelpers {
  /**
   * Measure execution time of a function
   */
  static async measureExecutionTime<T>(
    fn: () => Promise<T>
  ): Promise<{ result: T; duration: number }> {
    const start = process.hrtime.bigint();
    const result = await fn();
    const end = process.hrtime.bigint();
    const duration = Number(end - start) / 1_000_000; // Convert to milliseconds

    return { result, duration };
  }

  /**
   * Assert execution time is within threshold
   */
  static assertExecutionTime(duration: number, maxMs: number) {
    expect(duration).toBeLessThan(maxMs);
  }

  /**
   * Create large dataset for performance testing
   */
  static async createLargeDataset(options: {
    organizations?: number;
    usersPerOrg?: number;
    workspacesPerOrg?: number;
    boardsPerWorkspace?: number;
    itemsPerBoard?: number;
  } = {}) {
    const {
      organizations = 5,
      usersPerOrg = 20,
      workspacesPerOrg = 5,
      boardsPerWorkspace = 10,
      itemsPerBoard = 100,
    } = options;

    const results = [];

    for (let i = 0; i < organizations; i++) {
      const hierarchy = await TestDataFactory.createTestHierarchy({
        users: usersPerOrg,
        workspaces: workspacesPerOrg,
        boards: boardsPerWorkspace,
        items: itemsPerBoard,
      });
      results.push(hierarchy);
    }

    return results;
  }
}

/**
 * WebSocket testing utilities
 */
export class WebSocketTestHelpers {
  /**
   * Create a mock WebSocket connection
   */
  static createMockSocket() {
    return {
      id: nanoid(),
      emit: jest.fn(),
      on: jest.fn(),
      join: jest.fn(),
      leave: jest.fn(),
      disconnect: jest.fn(),
      connected: true,
      handshake: {
        auth: {},
        headers: {},
      },
    };
  }

  /**
   * Create multiple mock socket connections
   */
  static createMockSockets(count: number) {
    return Array(count).fill(0).map(() => this.createMockSocket());
  }

  /**
   * Simulate real-time event
   */
  static simulateRealtimeEvent(socket: any, event: string, data: any) {
    socket.emit(event, data);
  }
}