import { defineConfig, devices } from '@playwright/test';

/**
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './tests',

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,

  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results.json' }],
    ['junit', { outputFile: 'test-results.xml' }],
    process.env.CI ? ['github'] : ['list'],
  ],

  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Take screenshot on failure */
    screenshot: 'only-on-failure',

    /* Record video on failure */
    video: 'retain-on-failure',

    /* Default timeout for actions */
    actionTimeout: 30000,

    /* Default timeout for navigation */
    navigationTimeout: 30000,
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'setup',
      testMatch: /.*\.setup\.ts/,
    },

    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
    },

    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
      dependencies: ['setup'],
    },

    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
      dependencies: ['setup'],
    },

    /* Test against mobile viewports. */
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
      dependencies: ['setup'],
    },

    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
      dependencies: ['setup'],
    },

    /* Test against branded browsers. */
    {
      name: 'Microsoft Edge',
      use: { ...devices['Desktop Edge'], channel: 'msedge' },
      dependencies: ['setup'],
    },

    {
      name: 'Google Chrome',
      use: { ...devices['Desktop Chrome'], channel: 'chrome' },
      dependencies: ['setup'],
    },
  ],

  /* Run your local dev server before starting the tests */
  webServer: [
    {
      command: 'npm run dev',
      port: 3000,
      cwd: '../frontend',
      reuseExistingServer: !process.env.CI,
      env: {
        NODE_ENV: 'test',
      },
    },
    {
      command: 'npm run dev',
      port: 4000,
      cwd: '../backend',
      reuseExistingServer: !process.env.CI,
      env: {
        NODE_ENV: 'test',
        DATABASE_URL: process.env.TEST_DATABASE_URL || 'postgresql://test:test@localhost:5432/sunday_test',
        REDIS_URL: process.env.TEST_REDIS_URL || 'redis://localhost:6379/1',
      },
    },
  ],

  /* Global test timeout */
  timeout: 60000,

  /* Global setup and teardown */
  globalSetup: require.resolve('./global-setup.ts'),
  globalTeardown: require.resolve('./global-teardown.ts'),

  /* Expect defaults */
  expect: {
    /* Timeout for expect() assertions */
    timeout: 10000,

    /* Screenshot comparison threshold */
    threshold: 0.2,
  },

  /* Test directory patterns */
  testMatch: [
    'tests/**/*.test.ts',
    'tests/**/*.spec.ts',
  ],

  /* Ignore certain patterns */
  testIgnore: [
    'tests/helpers/**',
    'tests/fixtures/**',
  ],
});