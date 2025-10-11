import { PrismaClient } from '@prisma/client';

export class DatabaseHelper {
  private static prisma: PrismaClient;

  static async getPrismaClient(): Promise<PrismaClient> {
    if (!this.prisma) {
      this.prisma = new PrismaClient({
        datasources: {
          db: {
            url: process.env.TEST_DATABASE_URL || 'postgresql://test:test@localhost:5432/sunday_test',
          },
        },
      });
    }
    return this.prisma;
  }

  /**
   * Setup test database schema and initial data
   */
  static async setupTestDatabase(): Promise<void> {
    const prisma = await this.getPrismaClient();

    try {
      // Run migrations
      const { execSync } = require('child_process');
      execSync('npx prisma migrate deploy', {
        env: {
          ...process.env,
          DATABASE_URL: process.env.TEST_DATABASE_URL,
        },
        cwd: '../../backend',
      });

      console.log('✅ Database migrations completed');
    } catch (error) {
      console.error('❌ Database setup failed:', error);
      throw error;
    }
  }

  /**
   * Seed test data for E2E tests
   */
  static async seedTestData(): Promise<void> {
    const prisma = await this.getPrismaClient();

    try {
      // Clean existing data first
      await this.cleanupTestData();

      // Create test users
      const testUsers = await Promise.all([
        prisma.user.create({
          data: {
            email: 'admin@test.com',
            firstName: 'Admin',
            lastName: 'User',
            passwordHash: '$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewE0Wz5y5L9.k/hS', // password123
            emailVerified: true,
            timezone: 'UTC',
            locale: 'en',
          },
        }),
        prisma.user.create({
          data: {
            email: 'manager@test.com',
            firstName: 'Project',
            lastName: 'Manager',
            passwordHash: '$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewE0Wz5y5L9.k/hS', // password123
            emailVerified: true,
            timezone: 'UTC',
            locale: 'en',
          },
        }),
        prisma.user.create({
          data: {
            email: 'member@test.com',
            firstName: 'Team',
            lastName: 'Member',
            passwordHash: '$2a$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewE0Wz5y5L9.k/hS', // password123
            emailVerified: true,
            timezone: 'UTC',
            locale: 'en',
          },
        }),
      ]);

      // Create test organization
      const testOrg = await prisma.organization.create({
        data: {
          name: 'Test Organization',
          slug: 'test-org',
          description: 'A test organization for E2E tests',
          settings: {},
          members: {
            create: [
              {
                userId: testUsers[0].id,
                role: 'owner',
                status: 'active',
                joinedAt: new Date(),
              },
              {
                userId: testUsers[1].id,
                role: 'admin',
                status: 'active',
                joinedAt: new Date(),
              },
              {
                userId: testUsers[2].id,
                role: 'member',
                status: 'active',
                joinedAt: new Date(),
              },
            ],
          },
        },
      });

      // Create test workspaces
      const testWorkspaces = await Promise.all([
        prisma.workspace.create({
          data: {
            name: 'Test Workspace 1',
            organizationId: testOrg.id,
            description: 'First test workspace',
            settings: {},
            visibility: 'private',
          },
        }),
        prisma.workspace.create({
          data: {
            name: 'Test Workspace 2',
            organizationId: testOrg.id,
            description: 'Second test workspace',
            settings: {},
            visibility: 'private',
          },
        }),
      ]);

      // Create test boards
      const testBoards = await Promise.all([
        prisma.board.create({
          data: {
            name: 'Project Management Board',
            workspaceId: testWorkspaces[0].id,
            description: 'A board for project management testing',
            settings: {},
            columnOrder: ['status', 'priority', 'assignee', 'due_date'],
          },
        }),
        prisma.board.create({
          data: {
            name: 'Bug Tracking Board',
            workspaceId: testWorkspaces[0].id,
            description: 'A board for bug tracking testing',
            settings: {},
            columnOrder: ['status', 'severity', 'assignee'],
          },
        }),
      ]);

      // Create test items
      await Promise.all([
        prisma.item.create({
          data: {
            name: 'Setup user authentication',
            boardId: testBoards[0].id,
            description: 'Implement user login and registration',
            status: 'in_progress',
            position: 1,
            fieldValues: {
              priority: 'high',
              due_date: '2024-12-31',
            },
            assigneeId: testUsers[1].id,
          },
        }),
        prisma.item.create({
          data: {
            name: 'Create dashboard UI',
            boardId: testBoards[0].id,
            description: 'Design and implement the main dashboard',
            status: 'not_started',
            position: 2,
            fieldValues: {
              priority: 'medium',
            },
            assigneeId: testUsers[2].id,
          },
        }),
        prisma.item.create({
          data: {
            name: 'Fix login redirect bug',
            boardId: testBoards[1].id,
            description: 'Users not redirected after successful login',
            status: 'open',
            position: 1,
            fieldValues: {
              severity: 'critical',
            },
            assigneeId: testUsers[0].id,
          },
        }),
      ]);

      console.log('✅ Test data seeded successfully');
      console.log(`📊 Created: ${testUsers.length} users, 1 organization, ${testWorkspaces.length} workspaces, ${testBoards.length} boards`);

    } catch (error) {
      console.error('❌ Test data seeding failed:', error);
      throw error;
    }
  }

  /**
   * Clean up test data
   */
  static async cleanupTestData(): Promise<void> {
    const prisma = await this.getPrismaClient();

    try {
      // Delete in dependency order
      await prisma.item.deleteMany({});
      await prisma.boardColumn.deleteMany({});
      await prisma.board.deleteMany({});
      await prisma.workspace.deleteMany({});
      await prisma.organizationMember.deleteMany({});
      await prisma.organization.deleteMany({});
      await prisma.user.deleteMany({
        where: {
          email: {
            endsWith: '@test.com',
          },
        },
      });

      console.log('✅ Test data cleaned up');
    } catch (error) {
      console.error('❌ Test data cleanup failed:', error);
      // Don't throw to avoid masking test failures
    }
  }

  /**
   * Get test user by role
   */
  static async getTestUser(role: 'admin' | 'manager' | 'member') {
    const prisma = await this.getPrismaClient();

    const emailMap = {
      admin: 'admin@test.com',
      manager: 'manager@test.com',
      member: 'member@test.com',
    };

    return await prisma.user.findUnique({
      where: { email: emailMap[role] },
      include: {
        organizationMemberships: {
          include: {
            organization: true,
          },
        },
      },
    });
  }

  /**
   * Get test organization
   */
  static async getTestOrganization() {
    const prisma = await this.getPrismaClient();

    return await prisma.organization.findUnique({
      where: { slug: 'test-org' },
      include: {
        workspaces: {
          include: {
            boards: {
              include: {
                items: true,
              },
            },
          },
        },
      },
    });
  }

  /**
   * Create dynamic test data during tests
   */
  static async createTestBoard(name: string, workspaceId?: string) {
    const prisma = await this.getPrismaClient();

    let targetWorkspaceId = workspaceId;
    if (!targetWorkspaceId) {
      const org = await this.getTestOrganization();
      targetWorkspaceId = org?.workspaces[0]?.id;
    }

    if (!targetWorkspaceId) {
      throw new Error('No workspace available for test board creation');
    }

    return await prisma.board.create({
      data: {
        name,
        workspaceId: targetWorkspaceId,
        description: `Test board: ${name}`,
        settings: {},
        columnOrder: ['status', 'assignee'],
      },
    });
  }

  /**
   * Create test item in a board
   */
  static async createTestItem(name: string, boardId: string, assigneeId?: string) {
    const prisma = await this.getPrismaClient();

    return await prisma.item.create({
      data: {
        name,
        boardId,
        description: `Test item: ${name}`,
        status: 'not_started',
        position: Date.now(), // Use timestamp for unique positioning
        fieldValues: {},
        assigneeId,
      },
    });
  }

  /**
   * Close database connections
   */
  static async closeConnections(): Promise<void> {
    if (this.prisma) {
      await this.prisma.$disconnect();
    }
  }

  /**
   * Wait for database to be ready
   */
  static async waitForDatabase(timeoutMs = 30000): Promise<void> {
    const prisma = await this.getPrismaClient();
    const startTime = Date.now();

    while (Date.now() - startTime < timeoutMs) {
      try {
        await prisma.$queryRaw`SELECT 1`;
        console.log('✅ Database is ready');
        return;
      } catch (error) {
        console.log('⏳ Waiting for database...');
        await new Promise(resolve => setTimeout(resolve, 1000));
      }
    }

    throw new Error('Database not ready within timeout');
  }

  /**
   * Reset database to clean state
   */
  static async resetDatabase(): Promise<void> {
    const prisma = await this.getPrismaClient();

    try {
      await this.cleanupTestData();
      await this.seedTestData();
      console.log('✅ Database reset completed');
    } catch (error) {
      console.error('❌ Database reset failed:', error);
      throw error;
    }
  }
}