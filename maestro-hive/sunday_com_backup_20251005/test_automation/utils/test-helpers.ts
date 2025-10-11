import { Page, expect } from '@playwright/test';

/**
 * Test Helper Utilities
 * QA Engineer: Reusable Test Functions
 */

export class TestHelpers {
  constructor(private page: Page) {}

  // Authentication helpers
  async login(email: string = 'test@sunday.com', password: string = 'TestPassword123!') {
    await this.page.goto('/login');
    await this.page.fill('[data-testid="email-input"]', email);
    await this.page.fill('[data-testid="password-input"]', password);
    await this.page.click('[data-testid="login-button"]');
    await this.page.waitForURL('/dashboard');
  }

  async logout() {
    await this.page.click('[data-testid="user-menu"]');
    await this.page.click('[data-testid="logout-button"]');
    await this.page.waitForURL('/login');
  }

  // Board management helpers
  async createBoard(name: string, description?: string) {
    await this.page.goto('/boards');
    await this.page.click('[data-testid="create-board-button"]');
    await this.page.fill('[data-testid="board-name-input"]', name);

    if (description) {
      await this.page.fill('[data-testid="board-description-input"]', description);
    }

    await this.page.click('[data-testid="board-create-submit"]');
    await this.page.waitForURL(/\/board\/[a-zA-Z0-9-]+/);

    return this.page.url().split('/').pop(); // Return board ID
  }

  async navigateToBoard(boardId?: string) {
    if (boardId) {
      await this.page.goto(`/board/${boardId}`);
    } else {
      await this.page.goto('/boards');
      await this.page.click('[data-testid="board-item"]').first();
    }
    await this.page.waitForSelector('[data-testid="board-content"]');
  }

  // Item management helpers
  async createItem(name: string, options: {
    description?: string;
    column?: string;
    priority?: 'low' | 'medium' | 'high';
    assignee?: string;
    dueDate?: string;
    labels?: string[];
  } = {}) {
    const column = options.column || 'todo';

    await this.page.click(`[data-testid="add-item-${column}"]`);
    await this.page.fill('[data-testid="item-name-input"]', name);

    if (options.description) {
      await this.page.fill('[data-testid="item-description-input"]', options.description);
    }

    if (options.priority) {
      await this.page.selectOption('[data-testid="item-priority"]', options.priority);
    }

    if (options.dueDate) {
      await this.page.fill('[data-testid="due-date-input"]', options.dueDate);
    }

    if (options.labels) {
      for (const label of options.labels) {
        await this.page.click('[data-testid="add-label-button"]');
        await this.page.fill('[data-testid="label-input"]', label);
        await this.page.click('[data-testid="label-save"]');
      }
    }

    await this.page.click('[data-testid="item-save-button"]');
    await expect(this.page.locator(`[data-testid="item-${name}"]`)).toBeVisible();
  }

  async editItem(itemName: string, updates: {
    name?: string;
    description?: string;
    status?: string;
    priority?: string;
    comment?: string;
  }) {
    await this.page.click(`[data-testid="item-${itemName}"]`);
    await this.page.waitForSelector('[data-testid="item-details-modal"]');

    if (updates.name) {
      await this.page.fill('[data-testid="item-name-edit"]', updates.name);
    }

    if (updates.description) {
      await this.page.fill('[data-testid="item-description-edit"]', updates.description);
    }

    if (updates.status) {
      await this.page.selectOption('[data-testid="item-status-select"]', updates.status);
    }

    if (updates.priority) {
      await this.page.selectOption('[data-testid="item-priority-select"]', updates.priority);
    }

    if (updates.comment) {
      await this.page.fill('[data-testid="comment-input"]', updates.comment);
      await this.page.click('[data-testid="comment-submit"]');
    }

    await this.page.click('[data-testid="item-details-save"]');
    await this.page.click('[data-testid="close-modal"]');
  }

  async moveItem(itemName: string, fromColumn: string, toColumn: string) {
    const item = this.page.locator(`[data-testid="column-${fromColumn}"] [data-testid="item-${itemName}"]`);
    const targetColumn = this.page.locator(`[data-testid="column-${toColumn}"]`);

    await item.dragTo(targetColumn);

    // Verify item moved
    await expect(this.page.locator(`[data-testid="column-${toColumn}"]`)).toContainText(itemName);
    await expect(this.page.locator(`[data-testid="column-${fromColumn}"]`)).not.toContainText(itemName);
  }

  // Collaboration helpers
  async addComment(itemName: string, comment: string) {
    await this.page.click(`[data-testid="item-${itemName}"]`);
    await this.page.fill('[data-testid="comment-input"]', comment);
    await this.page.click('[data-testid="comment-submit"]');
    await expect(this.page.locator('[data-testid="comment-list"]')).toContainText(comment);
    await this.page.click('[data-testid="close-modal"]');
  }

  async uploadFile(itemName: string, filePath: string) {
    await this.page.click(`[data-testid="item-${itemName}"]`);
    await this.page.setInputFiles('[data-testid="file-upload-input"]', filePath);
    await expect(this.page.locator('[data-testid="file-list"]')).toContainText(filePath.split('/').pop() || '');
    await this.page.click('[data-testid="close-modal"]');
  }

  // Utility helpers
  async waitForRealTimeUpdate(timeout: number = 2000) {
    await this.page.waitForTimeout(timeout);
  }

  async verifyItemInColumn(itemName: string, columnName: string) {
    await expect(this.page.locator(`[data-testid="column-${columnName}"]`)).toContainText(itemName);
  }

  async verifyItemNotInColumn(itemName: string, columnName: string) {
    await expect(this.page.locator(`[data-testid="column-${columnName}"]`)).not.toContainText(itemName);
  }

  async takeScreenshot(name: string) {
    await this.page.screenshot({ path: `test-results/screenshots/${name}.png` });
  }

  async measurePerformance(action: () => Promise<void>) {
    const startTime = Date.now();
    await action();
    const endTime = Date.now();
    return endTime - startTime;
  }

  // Search and filter helpers
  async searchItems(query: string) {
    await this.page.click('[data-testid="search-button"]');
    await this.page.fill('[data-testid="search-input"]', query);
    await this.page.waitForTimeout(500); // Wait for search to process
  }

  async clearSearch() {
    await this.page.click('[data-testid="clear-search"]');
  }

  async filterByPriority(priority: 'low' | 'medium' | 'high') {
    await this.page.click('[data-testid="filter-button"]');
    await this.page.click(`[data-testid="filter-priority-${priority}"]`);
    await this.page.waitForTimeout(500);
  }

  async clearFilters() {
    await this.page.click('[data-testid="clear-filters"]');
  }

  // Mobile helpers
  async setMobileViewport() {
    await this.page.setViewportSize({ width: 375, height: 667 });
  }

  async setDesktopViewport() {
    await this.page.setViewportSize({ width: 1920, height: 1080 });
  }

  async openMobileMenu() {
    await this.page.click('[data-testid="mobile-menu-toggle"]');
  }

  async switchMobileColumn(columnName: string) {
    await this.page.click(`[data-testid="mobile-tab-${columnName}"]`);
  }

  // Validation helpers
  async verifyBoardExists(boardName: string) {
    await this.page.goto('/boards');
    await expect(this.page.locator('[data-testid="board-list"]')).toContainText(boardName);
  }

  async verifyUserLoggedIn() {
    await expect(this.page.locator('[data-testid="user-avatar"]')).toBeVisible();
  }

  async verifyUserLoggedOut() {
    await expect(this.page.locator('[data-testid="login-form"]')).toBeVisible();
  }

  async verifyNotification(message: string) {
    await expect(this.page.locator('[data-testid="notification"]')).toContainText(message);
  }

  async verifyErrorMessage(message: string) {
    await expect(this.page.locator('[data-testid="error-message"]')).toContainText(message);
  }

  // Cleanup helpers
  async cleanupBoard(boardId: string) {
    await this.page.goto(`/board/${boardId}/settings`);
    await this.page.click('[data-testid="delete-board-button"]');
    await this.page.click('[data-testid="confirm-delete"]');
  }

  async cleanupAllTestBoards() {
    await this.page.goto('/boards');
    const testBoards = this.page.locator('[data-testid="board-item"][data-test-board="true"]');
    const count = await testBoards.count();

    for (let i = 0; i < count; i++) {
      await testBoards.nth(i).click();
      await this.page.click('[data-testid="board-settings"]');
      await this.page.click('[data-testid="delete-board-button"]');
      await this.page.click('[data-testid="confirm-delete"]');
      await this.page.goto('/boards');
    }
  }
}

// Data generation helpers
export class TestDataGenerator {
  static generateEmail(): string {
    return `test${Date.now()}@sunday.com`;
  }

  static generateBoardName(): string {
    return `Test Board ${Date.now()}`;
  }

  static generateItemName(): string {
    return `Test Item ${Date.now()}`;
  }

  static generateRandomString(length: number = 10): string {
    return Math.random().toString(36).substring(2, length + 2);
  }

  static generateFutureDate(daysFromNow: number = 7): string {
    const date = new Date();
    date.setDate(date.getDate() + daysFromNow);
    return date.toISOString().split('T')[0];
  }

  static generateTestBoard() {
    return {
      name: this.generateBoardName(),
      description: 'Generated test board',
      columns: [
        { name: 'To Do', type: 'status', color: '#gray' },
        { name: 'In Progress', type: 'status', color: '#blue' },
        { name: 'Review', type: 'status', color: '#yellow' },
        { name: 'Done', type: 'status', color: '#green' }
      ]
    };
  }

  static generateTestItem() {
    return {
      name: this.generateItemName(),
      description: 'Generated test item description',
      priority: ['low', 'medium', 'high'][Math.floor(Math.random() * 3)] as 'low' | 'medium' | 'high',
      dueDate: this.generateFutureDate(Math.floor(Math.random() * 30) + 1),
      labels: ['test', 'automation', 'qa']
    };
  }
}

// API helpers for test setup
export class APITestHelpers {
  static async authenticateAPI(request: any): Promise<string> {
    const response = await request.post('/api/auth/login', {
      data: {
        email: 'test@sunday.com',
        password: 'TestPassword123!'
      }
    });

    const data = await response.json();
    return data.token;
  }

  static async createTestBoard(request: any, token: string, boardData?: any) {
    const defaultBoard = TestDataGenerator.generateTestBoard();
    const board = { ...defaultBoard, ...boardData };

    const response = await request.post('/api/boards', {
      headers: { 'Authorization': `Bearer ${token}` },
      data: board
    });

    return await response.json();
  }

  static async createTestItem(request: any, token: string, boardId: string, itemData?: any) {
    const defaultItem = TestDataGenerator.generateTestItem();
    const item = {
      ...defaultItem,
      boardId,
      columnId: '1',
      status: 'todo',
      data: { status: 'todo', priority: defaultItem.priority },
      ...itemData
    };

    const response = await request.post('/api/items', {
      headers: { 'Authorization': `Bearer ${token}` },
      data: item
    });

    return await response.json();
  }

  static async cleanupTestData(request: any, token: string, resources: { boards?: string[], items?: string[] }) {
    if (resources.items) {
      for (const itemId of resources.items) {
        await request.delete(`/api/items/${itemId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
      }
    }

    if (resources.boards) {
      for (const boardId of resources.boards) {
        await request.delete(`/api/boards/${boardId}`, {
          headers: { 'Authorization': `Bearer ${token}` }
        });
      }
    }
  }
}