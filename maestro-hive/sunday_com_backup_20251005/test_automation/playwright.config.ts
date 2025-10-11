import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright Configuration for Sunday.com E2E Testing
 * QA Engineer: Test Automation Framework
 */

export default defineConfig({
  // Test directory
  testDir: './tests',

  // Timeout settings
  timeout: 30000,
  expect: {
    timeout: 5000
  },

  // Test execution settings
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,

  // Reporter configuration
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['line']
  ],

  // Global test settings
  use: {
    // Base URL for tests
    baseURL: process.env.BASE_URL || 'http://localhost:3000',

    // Browser settings
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',

    // Authentication storage
    storageState: 'auth.json',

    // Default timeout for actions
    actionTimeout: 10000,
    navigationTimeout: 30000,

    // Extra HTTP headers
    extraHTTPHeaders: {
      'Accept-Language': 'en-US,en;q=0.9',
    },
  },

  // Test projects for different browsers
  projects: [
    // Setup project - authentication
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },

    // Desktop Chrome
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
    },

    // Desktop Firefox
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
      dependencies: ['setup'],
    },

    // Desktop Safari
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
      dependencies: ['setup'],
    },

    // Mobile Chrome
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
      dependencies: ['setup'],
    },

    // Mobile Safari
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
      dependencies: ['setup'],
    },

    // Tablet
    {
      name: 'Tablet',
      use: { ...devices['iPad Pro'] },
      dependencies: ['setup'],
    },
  ],

  // Web server configuration
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },

  // Output directories
  outputDir: 'test-results',
});