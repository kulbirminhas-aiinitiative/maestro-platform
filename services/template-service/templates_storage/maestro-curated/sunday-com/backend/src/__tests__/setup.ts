import { prisma } from '@/config/database';
import { redis } from '@/config/redis';

// Setup test environment
beforeAll(async () => {
  // Set test environment
  process.env.NODE_ENV = 'test';

  // You might want to seed test data here
  console.log('Test environment setup complete');
});

// Cleanup after all tests
afterAll(async () => {
  // Clean up database connections
  await prisma.$disconnect();
  await redis.quit();

  console.log('Test environment cleanup complete');
});

// Reset database state between tests (if needed)
beforeEach(async () => {
  // You might want to clear test data here
  // await prisma.$executeRaw`TRUNCATE TABLE organizations, users CASCADE`;
});

export {};