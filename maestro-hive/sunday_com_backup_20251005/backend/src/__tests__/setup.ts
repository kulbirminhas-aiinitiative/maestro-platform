import { PrismaClient, Decimal } from '@prisma/client';
import { DeepMockProxy, mockDeep, mockReset } from 'jest-mock-extended';
import Redis from 'ioredis';

// Mock Prisma Client
export const prismaMock = mockDeep<PrismaClient>() as unknown as DeepMockProxy<PrismaClient>;

// Mock Redis Client
export const redisMock = mockDeep<Redis>();

// Mock the Prisma client
jest.mock('@/config/database', () => ({
  prisma: prismaMock,
}));

// Mock Redis
jest.mock('@/config/redis', () => ({
  redis: redisMock,
  RedisService: {
    getCache: jest.fn(),
    setCache: jest.fn(),
    deleteCache: jest.fn(),
    deleteCachePattern: jest.fn(),
    setHash: jest.fn(),
    getHashField: jest.fn(),
    getAllHashFields: jest.fn(),
    deleteHashField: jest.fn(),
    setIfNotExists: jest.fn(),
    getKeysByPattern: jest.fn(),
    checkHealth: jest.fn().mockResolvedValue(true),
  },
}));

// Mock Socket.IO
jest.mock('@/server', () => ({
  io: {
    to: jest.fn(() => ({
      emit: jest.fn(),
    })),
    in: jest.fn(() => ({
      fetchSockets: jest.fn(() => Promise.resolve([])),
    })),
    emit: jest.fn(),
  },
}));

// Mock Logger
jest.mock('@/config/logger', () => ({
  Logger: {
    api: jest.fn(),
    business: jest.fn(),
    error: jest.fn(),
    websocket: jest.fn(),
    automation: jest.fn(),
  },
  logger: {
    info: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
    debug: jest.fn(),
    http: jest.fn(),
  },
}));

// Mock file services that require AWS
jest.mock('@/services/file.service', () => ({
  FileService: {
    initialize: jest.fn(),
    uploadFile: jest.fn(),
    getFile: jest.fn(),
    deleteFile: jest.fn(),
    getItemFiles: jest.fn(),
    getPresignedUploadUrl: jest.fn(),
    confirmUpload: jest.fn(),
    cleanupOrphanedFiles: jest.fn(),
  },
}));

// Mock AI service that requires OpenAI
jest.mock('@/services/ai.service', () => ({
  AIService: {
    initialize: jest.fn(),
    generateTaskSuggestions: jest.fn(),
    autoTagItem: jest.fn(),
    analyzeWorkloadDistribution: jest.fn(),
    suggestTaskScheduling: jest.fn(),
    detectProjectRisks: jest.fn(),
  },
}));

// Setup test environment
beforeAll(async () => {
  // Set test environment
  process.env.NODE_ENV = 'test';
  process.env.JWT_SECRET = 'test-jwt-secret';
  process.env.JWT_REFRESH_SECRET = 'test-refresh-secret';
  process.env.SESSION_SECRET = 'test-session-secret';
  process.env.WEBHOOK_SECRET = 'test-webhook-secret';
  process.env.DATABASE_URL = 'postgresql://test:test@localhost:5432/test';

  console.log('Test environment setup complete');
});

// Reset mocks between tests
beforeEach(() => {
  mockReset(prismaMock);
  mockReset(redisMock);
  jest.clearAllMocks();
});

// Cleanup after all tests
afterAll(async () => {
  console.log('Test environment cleanup complete');
});

// Test utilities
export const mockUser = {
  id: 'test-user-id',
  email: 'test@example.com',
  firstName: 'Test',
  lastName: 'User',
  password: 'hashedpassword',
  emailVerified: true,
  isActive: true,
  lastLoginAt: new Date(),
  createdAt: new Date(),
  updatedAt: new Date(),
  deletedAt: null,
};

export const mockOrganization = {
  id: 'test-org-id',
  name: 'Test Organization',
  slug: 'test-org',
  domain: 'test.com',
  isActive: true,
  settings: {},
  createdAt: new Date(),
  updatedAt: new Date(),
  deletedAt: null,
};

export const mockWorkspace = {
  id: 'test-workspace-id',
  name: 'Test Workspace',
  description: 'Test workspace description',
  organizationId: 'test-org-id',
  color: '#blue',
  isPrivate: false,
  settings: {},
  createdAt: new Date(),
  updatedAt: new Date(),
  deletedAt: null,
};

export const mockBoard = {
  id: 'test-board-id',
  name: 'Test Board',
  description: 'Test board description',
  workspaceId: 'test-workspace-id',
  templateId: null,
  folderId: null,
  isPrivate: false,
  settings: {},
  position: 1,
  createdBy: 'test-user-id',
  createdAt: new Date(),
  updatedAt: new Date(),
  deletedAt: null,
};

export const mockItem = {
  id: 'test-item-id',
  name: 'Test Item',
  description: 'Test item description',
  boardId: 'test-board-id',
  parentId: null,
  itemData: { status: 'In Progress' },
  position: new Decimal(1),
  createdBy: 'test-user-id',
  createdAt: new Date(),
  updatedAt: new Date(),
  deletedAt: null,
};

export {};