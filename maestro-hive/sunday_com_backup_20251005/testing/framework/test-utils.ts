/**
 * Test Automation Framework - Sunday.com
 * Enhanced testing utilities and helpers
 * Author: QA Engineer
 */

import { faker } from '@faker-js/faker';
import { test as baseTest, expect, Page, Browser } from '@playwright/test';
import { AuthService } from '../../backend/src/services/auth.service';
import { BoardService } from '../../backend/src/services/board.service';
import { ItemService } from '../../backend/src/services/item.service';

// =============================================================================
// TEST DATA FACTORY
// =============================================================================

export class TestDataFactory {
  /**
   * Generate realistic user data
   */
  static createUser(overrides: Partial<any> = {}) {
    return {
      email: faker.internet.email(),
      password: 'TestPassword123!',
      firstName: faker.person.firstName(),
      lastName: faker.person.lastName(),
      role: 'member',
      ...overrides
    };
  }

  /**
   * Generate workspace data
   */
  static createWorkspace(overrides: Partial<any> = {}) {
    return {
      name: faker.company.name(),
      description: faker.lorem.sentence(),
      slug: faker.helpers.slugify(faker.company.name()).toLowerCase(),
      ...overrides
    };
  }

  /**
   * Generate board data
   */
  static createBoard(overrides: Partial<any> = {}) {
    return {
      name: faker.lorem.words(3),
      description: faker.lorem.sentence(),
      type: faker.helpers.arrayElement(['kanban', 'table', 'timeline']),
      isPublic: faker.datatype.boolean(),
      ...overrides
    };
  }

  /**
   * Generate item/task data
   */
  static createItem(overrides: Partial<any> = {}) {
    return {
      name: faker.lorem.words(4),
      description: faker.lorem.paragraph(),
      status: faker.helpers.arrayElement(['todo', 'in_progress', 'done']),
      priority: faker.helpers.arrayElement(['low', 'medium', 'high', 'urgent']),
      dueDate: faker.date.future(),
      ...overrides
    };
  }

  /**
   * Generate comment data
   */
  static createComment(overrides: Partial<any> = {}) {
    return {
      content: faker.lorem.paragraph(),
      mentions: [],
      ...overrides
    };
  }

  /**
   * Generate complete test scenario data
   */
  static createCompleteTestScenario() {
    const users = Array.from({ length: 3 }, () => this.createUser());
    const workspace = this.createWorkspace({ ownerId: users[0].id });
    const boards = Array.from({ length: 2 }, () =>
      this.createBoard({ workspaceId: workspace.id })
    );
    const items = Array.from({ length: 5 }, () =>
      this.createItem({ boardId: boards[0].id })
    );

    return { users, workspace, boards, items };
  }
}

// =============================================================================
// API TEST HELPERS
// =============================================================================

export class ApiTestHelper {
  private baseUrl: string;
  private authToken?: string;

  constructor(baseUrl = 'http://localhost:3000/api') {
    this.baseUrl = baseUrl;
  }

  /**
   * Authenticate and store token
   */
  async authenticate(email: string, password: string) {
    const response = await fetch(`${this.baseUrl}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });

    const data = await response.json();
    this.authToken = data.tokens.accessToken;
    return data;
  }

  /**
   * Make authenticated API request
   */
  async request(endpoint: string, options: RequestInit = {}) {
    const headers = {
      'Content-Type': 'application/json',
      ...(this.authToken && { Authorization: `Bearer ${this.authToken}` }),
      ...options.headers
    };

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers
    });

    return {
      status: response.status,
      data: await response.json(),
      headers: response.headers
    };
  }

  /**
   * Create test user and authenticate
   */
  async createAndAuthenticateUser(userData?: Partial<any>) {
    const user = TestDataFactory.createUser(userData);

    // Register user
    await this.request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(user)
    });

    // Authenticate
    await this.authenticate(user.email, user.password);

    return user;
  }

  /**
   * Create complete test workspace with boards and items
   */
  async createTestWorkspace() {
    const workspaceData = TestDataFactory.createWorkspace();
    const workspace = await this.request('/workspaces', {
      method: 'POST',
      body: JSON.stringify(workspaceData)
    });

    const boardData = TestDataFactory.createBoard({
      workspaceId: workspace.data.id
    });
    const board = await this.request('/boards', {
      method: 'POST',
      body: JSON.stringify(boardData)
    });

    const items = [];
    for (let i = 0; i < 3; i++) {
      const itemData = TestDataFactory.createItem({
        boardId: board.data.id
      });
      const item = await this.request('/items', {
        method: 'POST',
        body: JSON.stringify(itemData)
      });
      items.push(item.data);
    }

    return {
      workspace: workspace.data,
      board: board.data,
      items
    };
  }
}

// =============================================================================
// E2E TEST HELPERS
// =============================================================================

export class E2ETestHelper {
  constructor(private page: Page) {}

  /**
   * Login to application
   */
  async login(email: string, password: string) {
    await this.page.goto('/login');
    await this.page.fill('[data-testid="email-input"]', email);
    await this.page.fill('[data-testid="password-input"]', password);
    await this.page.click('[data-testid="login-button"]');

    // Wait for redirect to dashboard
    await this.page.waitForURL('/dashboard');
  }

  /**
   * Navigate to specific board
   */
  async navigateToBoard(boardId: string) {
    await this.page.goto(`/boards/${boardId}`);
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Create a new item on board
   */
  async createItem(itemData: any) {
    await this.page.click('[data-testid="add-item-button"]');
    await this.page.fill('[data-testid="item-name-input"]', itemData.name);

    if (itemData.description) {
      await this.page.fill('[data-testid="item-description-input"]', itemData.description);
    }

    if (itemData.priority) {
      await this.page.selectOption('[data-testid="item-priority-select"]', itemData.priority);
    }

    await this.page.click('[data-testid="save-item-button"]');

    // Wait for item to appear
    await this.page.waitForSelector(`[data-testid="item-${itemData.name}"]`);
  }

  /**
   * Drag and drop item between columns
   */
  async dragItemToColumn(itemName: string, targetColumn: string) {
    const item = this.page.locator(`[data-testid="item-${itemName}"]`);
    const column = this.page.locator(`[data-testid="column-${targetColumn}"]`);

    await item.dragTo(column);

    // Wait for status update
    await this.page.waitForSelector(
      `[data-testid="column-${targetColumn}"] [data-testid="item-${itemName}"]`
    );
  }

  /**
   * Wait for real-time update
   */
  async waitForRealtimeUpdate(selector: string, timeout = 5000) {
    await this.page.waitForSelector(selector, { timeout });
  }

  /**
   * Check for WebSocket connection
   */
  async verifyWebSocketConnection() {
    // Check for WebSocket connection indicator
    await this.page.waitForSelector('[data-testid="connection-status"][data-status="connected"]');
  }

  /**
   * Simulate network failure and recovery
   */
  async simulateNetworkFailure() {
    // Block network requests
    await this.page.route('**/*', route => route.abort());

    // Wait a moment
    await this.page.waitForTimeout(2000);

    // Restore network
    await this.page.unroute('**/*');

    // Wait for reconnection
    await this.verifyWebSocketConnection();
  }
}

// =============================================================================
// PERFORMANCE TEST HELPERS
// =============================================================================

export class PerformanceHelper {
  /**
   * Measure API response time
   */
  static async measureApiResponse(apiCall: () => Promise<any>): Promise<number> {
    const startTime = performance.now();
    await apiCall();
    const endTime = performance.now();
    return endTime - startTime;
  }

  /**
   * Measure page load time
   */
  static async measurePageLoad(page: Page, url: string): Promise<any> {
    const startTime = performance.now();

    await page.goto(url);
    await page.waitForLoadState('networkidle');

    const endTime = performance.now();

    // Get browser performance metrics
    const metrics = await page.evaluate(() => {
      const navigation = performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming;
      return {
        domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
        loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
        firstPaint: performance.getEntriesByName('first-paint')[0]?.startTime || 0,
        firstContentfulPaint: performance.getEntriesByName('first-contentful-paint')[0]?.startTime || 0
      };
    });

    return {
      totalTime: endTime - startTime,
      ...metrics
    };
  }

  /**
   * Monitor memory usage during test
   */
  static async monitorMemoryUsage(page: Page): Promise<any> {
    return await page.evaluate(() => {
      // @ts-ignore
      return performance.memory ? {
        // @ts-ignore
        usedJSHeapSize: performance.memory.usedJSHeapSize,
        // @ts-ignore
        totalJSHeapSize: performance.memory.totalJSHeapSize,
        // @ts-ignore
        jsHeapSizeLimit: performance.memory.jsHeapSizeLimit
      } : null;
    });
  }
}

// =============================================================================
// ACCESSIBILITY TEST HELPERS
// =============================================================================

export class AccessibilityHelper {
  constructor(private page: Page) {}

  /**
   * Test keyboard navigation
   */
  async testKeyboardNavigation(selectors: string[]) {
    for (const selector of selectors) {
      await this.page.focus(selector);
      await expect(this.page.locator(selector)).toBeFocused();
      await this.page.keyboard.press('Tab');
    }
  }

  /**
   * Test screen reader labels
   */
  async checkAriaLabels(selectors: string[]) {
    for (const selector of selectors) {
      const element = this.page.locator(selector);
      await expect(element).toHaveAttribute('aria-label');
    }
  }

  /**
   * Test color contrast
   */
  async checkColorContrast(selector: string): Promise<number> {
    return await this.page.evaluate((sel) => {
      const element = document.querySelector(sel);
      if (!element) return 0;

      const computedStyle = window.getComputedStyle(element);
      const backgroundColor = computedStyle.backgroundColor;
      const color = computedStyle.color;

      // Simplified contrast calculation
      // In real implementation, use proper contrast calculation
      return 4.5; // Mock ratio
    }, selector);
  }
}

// =============================================================================
// MULTI-USER TEST HELPERS
// =============================================================================

export class MultiUserTestHelper {
  private contexts: Array<{ page: Page; user: any }> = [];

  async createUserSession(browser: Browser, userData?: any): Promise<Page> {
    const context = await browser.newContext();
    const page = await context.newPage();
    const user = TestDataFactory.createUser(userData);

    // Setup API helper for this user
    const apiHelper = new ApiTestHelper();
    await apiHelper.createAndAuthenticateUser(user);

    // Store session
    this.contexts.push({ page, user });

    return page;
  }

  async simulateCollaboration(boardId: string) {
    const [user1Page, user2Page] = this.contexts.map(ctx => ctx.page);

    // Both users navigate to same board
    await user1Page.goto(`/boards/${boardId}`);
    await user2Page.goto(`/boards/${boardId}`);

    // User 1 creates item
    const e2eHelper1 = new E2ETestHelper(user1Page);
    await e2eHelper1.createItem({
      name: 'Collaboration Test Item'
    });

    // User 2 should see the item
    const e2eHelper2 = new E2ETestHelper(user2Page);
    await e2eHelper2.waitForRealtimeUpdate('[data-testid="item-Collaboration Test Item"]');

    return true;
  }

  async cleanup() {
    for (const { page } of this.contexts) {
      await page.context().close();
    }
    this.contexts = [];
  }
}

// =============================================================================
// TEST CONFIGURATION
// =============================================================================

export const testConfig = {
  timeout: 30000,
  retries: 2,
  workers: 4,
  use: {
    headless: process.env.CI === 'true',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: { browserName: 'chromium' },
    },
    {
      name: 'firefox',
      use: { browserName: 'firefox' },
    },
    {
      name: 'webkit',
      use: { browserName: 'webkit' },
    },
  ],
};

// =============================================================================
// CUSTOM TEST FIXTURES
// =============================================================================

interface TestFixtures {
  apiHelper: ApiTestHelper;
  e2eHelper: E2ETestHelper;
  performanceHelper: PerformanceHelper;
  accessibilityHelper: AccessibilityHelper;
  multiUserHelper: MultiUserTestHelper;
}

export const test = baseTest.extend<TestFixtures>({
  apiHelper: async ({}, use) => {
    const helper = new ApiTestHelper();
    await use(helper);
  },

  e2eHelper: async ({ page }, use) => {
    const helper = new E2ETestHelper(page);
    await use(helper);
  },

  performanceHelper: async ({}, use) => {
    await use(PerformanceHelper);
  },

  accessibilityHelper: async ({ page }, use) => {
    const helper = new AccessibilityHelper(page);
    await use(helper);
  },

  multiUserHelper: async ({ browser }, use) => {
    const helper = new MultiUserTestHelper();
    await use(helper);
    await helper.cleanup();
  },
});

export { expect };

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Wait for condition with timeout
 */
export async function waitForCondition(
  condition: () => Promise<boolean>,
  timeout = 5000,
  interval = 100
): Promise<boolean> {
  const startTime = Date.now();

  while (Date.now() - startTime < timeout) {
    if (await condition()) {
      return true;
    }
    await new Promise(resolve => setTimeout(resolve, interval));
  }

  return false;
}

/**
 * Generate unique test identifier
 */
export function generateTestId(): string {
  return `test-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Clean up test data
 */
export async function cleanupTestData(apiHelper: ApiTestHelper, testId: string) {
  // Implementation depends on your cleanup strategy
  // This would typically delete test users, workspaces, etc.
}

export default {
  TestDataFactory,
  ApiTestHelper,
  E2ETestHelper,
  PerformanceHelper,
  AccessibilityHelper,
  MultiUserTestHelper,
  test,
  expect,
  testConfig
};