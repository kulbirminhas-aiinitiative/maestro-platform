module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  displayName: 'E2E Tests',
  roots: ['<rootDir>/src'],
  testMatch: ['**/__tests__/**/*.e2e.test.ts', '**/?(*.)+(e2e).test.ts'],
  transform: {
    '^.+\\.ts$': 'ts-jest',
  },
  collectCoverageFrom: [
    'src/**/*.{ts,js}',
    '!src/**/*.d.ts',
    '!src/**/*.test.ts',
    '!src/**/*.spec.ts',
    '!src/**/*.e2e.test.ts',
    '!src/__tests__/**/*',
  ],
  coverageDirectory: 'coverage-e2e',
  coverageReporters: ['text', 'lcov', 'html'],
  setupFilesAfterEnv: ['<rootDir>/src/__tests__/e2e-setup.ts'],
  moduleNameMapping: {
    '^@/(.*)$': '<rootDir>/src/$1',
  },
  testTimeout: 30000, // Longer timeout for E2E tests
  verbose: true,
  detectOpenHandles: true,
  forceExit: true,
  maxWorkers: 1, // Run E2E tests sequentially
  // Only run tests with specific patterns for E2E
  testPathIgnorePatterns: [
    '/node_modules/',
    '/__tests__/.*\\.test\\.ts$', // Ignore unit tests
    '/__tests__/.*\\.spec\\.ts$', // Ignore spec tests
  ],
};