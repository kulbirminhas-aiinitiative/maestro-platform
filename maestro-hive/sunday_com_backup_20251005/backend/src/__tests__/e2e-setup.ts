import { PrismaClient } from '@prisma/client';
import { createServer } from 'http';
import { Express } from 'express';
import app from '@/server';
import { config } from '@/config';

// E2E test database instance
const prisma = new PrismaClient({
  datasourceUrl: config.database.testUrl || process.env.DATABASE_URL_TEST,
});

let server: any;
let testApp: Express;

beforeAll(async () => {
  // Set test environment
  process.env.NODE_ENV = 'test';
  process.env.JWT_SECRET = 'test-jwt-secret-for-e2e';
  process.env.JWT_REFRESH_SECRET = 'test-refresh-secret-for-e2e';
  process.env.SESSION_SECRET = 'test-session-secret-for-e2e';
  process.env.WEBHOOK_SECRET = 'test-webhook-secret-for-e2e';

  // Initialize test application
  testApp = app;

  // Start test server
  server = createServer(testApp);
  await new Promise<void>((resolve) => {
    server.listen(0, () => {
      console.log(`E2E test server started on port ${server.address().port}`);
      resolve();
    });
  });

  // Clean and prepare test database
  await cleanDatabase();
  await seedTestData();

  console.log('E2E test environment setup complete');
}, 60000);

afterAll(async () => {
  // Clean up test data
  await cleanDatabase();

  // Close database connections
  await prisma.$disconnect();

  // Close test server
  if (server) {
    await new Promise<void>((resolve) => {
      server.close(() => {
        console.log('E2E test server closed');
        resolve();
      });
    });
  }

  console.log('E2E test environment cleanup complete');
}, 30000);

beforeEach(async () => {
  // Clean data between tests but keep seed data
  await cleanTransientData();
});

/**
 * Clean all data from test database
 */
async function cleanDatabase(): Promise<void> {
  const tablenames = await prisma.$queryRaw<
    Array<{ tablename: string }>
  >`SELECT tablename FROM pg_tables WHERE schemaname='public'`;

  const tables = tablenames
    .map(({ tablename }) => tablename)
    .filter((name) => name !== '_prisma_migrations')
    .map((name) => `"public"."${name}"`)
    .join(', ');

  try {
    await prisma.$executeRawUnsafe(`TRUNCATE TABLE ${tables} CASCADE;`);
  } catch (error) {
    console.log('Error cleaning database:', error);
  }
}

/**
 * Clean transient data between tests
 */
async function cleanTransientData(): Promise<void> {
  // Remove data created during tests but keep seed data
  try {
    await prisma.activityLog.deleteMany({});
    await prisma.notification.deleteMany({});
    await prisma.automationExecution.deleteMany({});
    await prisma.timeEntry.deleteMany({});
    await prisma.comment.deleteMany({});
    await prisma.item.deleteMany({
      where: {
        name: {
          contains: 'Test',
        },
      },
    });
  } catch (error) {
    console.log('Error cleaning transient data:', error);
  }
}

/**
 * Seed essential test data
 */
async function seedTestData(): Promise<void> {
  try {
    // Create test users
    const testUser1 = await prisma.user.create({
      data: {
        email: 'user1@test.com',
        password: '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewYe.CvLHzfxNs5C', // 'password123'
        firstName: 'Test',
        lastName: 'User1',
        emailVerified: true,
        isActive: true,
      },
    });

    const testUser2 = await prisma.user.create({
      data: {
        email: 'user2@test.com',
        password: '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewYe.CvLHzfxNs5C',
        firstName: 'Test',
        lastName: 'User2',
        emailVerified: true,
        isActive: true,
      },
    });

    // Create test organization
    const testOrg = await prisma.organization.create({
      data: {
        name: 'Test Organization',
        slug: 'test-org',
        isActive: true,
        settings: {},
      },
    });

    // Add users to organization
    await prisma.organizationMember.createMany({
      data: [
        {
          organizationId: testOrg.id,
          userId: testUser1.id,
          role: 'admin',
          permissions: { all: true },
        },
        {
          organizationId: testOrg.id,
          userId: testUser2.id,
          role: 'member',
          permissions: { read: true, write: true },
        },
      ],
    });

    // Create test workspace
    const testWorkspace = await prisma.workspace.create({
      data: {
        name: 'Test Workspace',
        description: 'E2E test workspace',
        organizationId: testOrg.id,
        color: '#3B82F6',
        isPrivate: false,
        settings: {},
      },
    });

    // Add users to workspace
    await prisma.workspaceMember.createMany({
      data: [
        {
          workspaceId: testWorkspace.id,
          userId: testUser1.id,
          role: 'admin',
          permissions: { all: true },
        },
        {
          workspaceId: testWorkspace.id,
          userId: testUser2.id,
          role: 'member',
          permissions: { read: true, write: true },
        },
      ],
    });

    // Create test board
    const testBoard = await prisma.board.create({
      data: {
        name: 'Test Board',
        description: 'E2E test board',
        workspaceId: testWorkspace.id,
        createdBy: testUser1.id,
        isPrivate: false,
        settings: {},
        position: 1,
      },
    });

    // Add users to board
    await prisma.boardMember.createMany({
      data: [
        {
          boardId: testBoard.id,
          userId: testUser1.id,
          role: 'admin',
          permissions: { all: true },
        },
        {
          boardId: testBoard.id,
          userId: testUser2.id,
          role: 'member',
          permissions: { read: true, write: true },
        },
      ],
    });

    // Create board columns
    await prisma.boardColumn.createMany({
      data: [
        {
          boardId: testBoard.id,
          name: 'To Do',
          columnType: 'status',
          position: 0,
          settings: { color: '#EF4444' },
        },
        {
          boardId: testBoard.id,
          name: 'In Progress',
          columnType: 'status',
          position: 1,
          settings: { color: '#F59E0B' },
        },
        {
          boardId: testBoard.id,
          name: 'Done',
          columnType: 'status',
          position: 2,
          settings: { color: '#10B981' },
        },
      ],
    });

    console.log('E2E test data seeded successfully');
  } catch (error) {
    console.error('Error seeding test data:', error);
    throw error;
  }
}

// Export test utilities
export { prisma, testApp, server };

// Test data getters
export const getTestUser1 = () => ({ email: 'user1@test.com', password: 'password123' });
export const getTestUser2 = () => ({ email: 'user2@test.com', password: 'password123' });

export default {
  prisma,
  testApp,
  server,
  getTestUser1,
  getTestUser2,
};