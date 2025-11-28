import { PrismaClient } from '@prisma/client';
import { logger } from './logger';

const isDevelopment = process.env.NODE_ENV === 'development';
const isTest = process.env.NODE_ENV === 'test';

export const prisma = new PrismaClient({
  log: isDevelopment ? ['query', 'info', 'warn', 'error'] : ['warn', 'error'],
  datasources: {
    db: {
      url: isTest ? process.env.DATABASE_URL_TEST : process.env.DATABASE_URL,
    },
  },
});

// Database connection health check
export const checkDatabaseHealth = async (): Promise<boolean> => {
  try {
    await prisma.$queryRaw`SELECT 1`;
    return true;
  } catch (error) {
    logger.error('Database health check failed:', error);
    return false;
  }
};

// Graceful shutdown
export const disconnectDatabase = async (): Promise<void> => {
  try {
    await prisma.$disconnect();
    logger.info('Database connection closed');
  } catch (error) {
    logger.error('Error closing database connection:', error);
  }
};

// Database middleware for logging
prisma.$use(async (params, next) => {
  const before = Date.now();
  const result = await next(params);
  const after = Date.now();

  if (isDevelopment) {
    logger.debug(`Query ${params.model}.${params.action} took ${after - before}ms`);
  }

  return result;
});

// Handle database connection errors
prisma.$on('error', (e) => {
  logger.error('Database error:', e);
});

export default prisma;