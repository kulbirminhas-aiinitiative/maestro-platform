import { PrismaClient } from '@prisma/client';

export default async function globalTeardown() {
  console.log('🧹 Cleaning up test environment...');

  const testDatabaseUrl = process.env.DATABASE_URL_TEST;
  if (!testDatabaseUrl) {
    console.log('No test database URL found, skipping cleanup');
    return;
  }

  const prisma = new PrismaClient({
    datasources: {
      db: {
        url: testDatabaseUrl,
      },
    },
  });

  try {
    // Clean up test data after all tests
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
    console.log('✅ Test cleanup completed');
  } catch (error) {
    console.error('❌ Test cleanup failed:', error);
  } finally {
    await prisma.$disconnect();
  }
}