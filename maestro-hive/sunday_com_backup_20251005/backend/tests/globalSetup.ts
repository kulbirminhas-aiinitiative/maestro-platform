import { PrismaClient } from '@prisma/client';
import { execSync } from 'child_process';

export default async function globalSetup() {
  console.log('🔧 Setting up test environment...');

  // Ensure test database environment
  process.env.NODE_ENV = 'test';

  const testDatabaseUrl = process.env.DATABASE_URL_TEST;
  if (!testDatabaseUrl) {
    throw new Error('DATABASE_URL_TEST environment variable is required for tests');
  }

  // Set the database URL for Prisma
  process.env.DATABASE_URL = testDatabaseUrl;

  console.log('📄 Running database migrations...');
  try {
    // Deploy migrations to test database
    execSync('npx prisma migrate deploy', {
      env: { ...process.env, DATABASE_URL: testDatabaseUrl },
      stdio: 'inherit',
    });
    console.log('✅ Database migrations completed');
  } catch (error) {
    console.error('❌ Database migration failed:', error);
    throw error;
  }

  // Initialize Prisma client for cleanup
  const prisma = new PrismaClient({
    datasources: {
      db: {
        url: testDatabaseUrl,
      },
    },
  });

  console.log('🧹 Cleaning test database...');
  try {
    // Clean up any existing test data
    await prisma.$transaction([
      prisma.activityLog.deleteMany(),
      prisma.automationExecution.deleteMany(),
      prisma.automationRule.deleteMany(),
      prisma.webhookDelivery.deleteMany(),
      prisma.webhook.deleteMany(),
      prisma.fileAttachment.deleteMany(),
      prisma.file.deleteMany(),
      prisma.timeEntry.deleteMany(),
      prisma.comment.deleteMany(),
      prisma.itemDependency.deleteMany(),
      prisma.itemAssignment.deleteMany(),
      prisma.item.deleteMany(),
      prisma.boardMember.deleteMany(),
      prisma.boardColumn.deleteMany(),
      prisma.board.deleteMany(),
      prisma.folder.deleteMany(),
      prisma.workspaceMember.deleteMany(),
      prisma.workspace.deleteMany(),
      prisma.organizationMember.deleteMany(),
      prisma.organization.deleteMany(),
      prisma.user.deleteMany(),
      prisma.boardTemplate.deleteMany(),
    ]);
    console.log('✅ Test database cleaned');
  } catch (error) {
    console.error('❌ Database cleanup failed:', error);
  } finally {
    await prisma.$disconnect();
  }

  console.log('🚀 Test environment ready!');
}