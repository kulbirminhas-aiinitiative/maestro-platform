import { PrismaClient } from '@prisma/client';
import { config } from '../src/config';

// Global test setup
declare global {
  var __PRISMA__: PrismaClient;
  var __TEST_DB_URL__: string;
}

beforeAll(async () => {
  // Set test environment
  process.env.NODE_ENV = 'test';
  process.env.DATABASE_URL = process.env.DATABASE_URL_TEST || 'postgresql://test:test@localhost:5432/sunday_test';

  // Initialize test database
  if (!global.__PRISMA__) {
    global.__PRISMA__ = new PrismaClient({
      datasources: {
        db: {
          url: process.env.DATABASE_URL_TEST,
        },
      },
    });
  }
});

afterAll(async () => {
  if (global.__PRISMA__) {
    await global.__PRISMA__.$disconnect();
  }
});

// Increase timeout for database operations
jest.setTimeout(30000);