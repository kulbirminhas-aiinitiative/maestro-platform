import { test, expect } from '@playwright/test';

/**
 * Critical User Journey Tests
 * QA Engineer: End-to-End Test Suite
 * Priority: Critical features that must work for MVP
 */

test.describe('Critical User Journeys', () => {

  test.beforeEach(async ({ page }) => {
    // Ensure we start from dashboard
    await page.goto('/dashboard');
    await expect(page.locator('[data-testid="dashboard-header"]')).toBeVisible();
  });

  test('TC-E2E-001: Complete board creation and management flow', async ({ page }) => {
    // Step 1: Navigate to boards page
    await page.click('[data-testid="nav-boards"]');
    await expect(page).toHaveURL('/boards');

    // Step 2: Create new board
    await page.click('[data-testid="create-board-button"]');
    await page.fill('[data-testid="board-name-input"]', 'E2E Test Board');
    await page.fill('[data-testid="board-description-input"]', 'Board created by E2E test');
    await page.click('[data-testid="board-create-submit"]');

    // Step 3: Verify board creation and navigation
    await expect(page).toHaveURL(/\/board\/[a-zA-Z0-9-]+/);
    await expect(page.locator('[data-testid="board-title"]')).toContainText('E2E Test Board');

    // Step 4: Verify default columns exist
    await expect(page.locator('[data-testid="column-todo"]')).toBeVisible();
    await expect(page.locator('[data-testid="column-in-progress"]')).toBeVisible();
    await expect(page.locator('[data-testid="column-done"]')).toBeVisible();

    // Step 5: Add first item
    await page.click('[data-testid="add-item-todo"]');
    await page.fill('[data-testid="item-name-input"]', 'Test Task 1');
    await page.fill('[data-testid="item-description-input"]', 'This is our first test task');
    await page.click('[data-testid="item-save-button"]');

    // Step 6: Verify item creation
    await expect(page.locator('[data-testid="item-Test Task 1"]')).toBeVisible();
    await expect(page.locator('[data-testid="column-todo"]')).toContainText('Test Task 1');

    // Step 7: Test drag and drop
    const todoColumn = page.locator('[data-testid="column-todo"]');
    const inProgressColumn = page.locator('[data-testid="column-in-progress"]');
    const taskItem = page.locator('[data-testid="item-Test Task 1"]');

    await taskItem.dragTo(inProgressColumn);

    // Step 8: Verify item moved
    await expect(page.locator('[data-testid="column-in-progress"]')).toContainText('Test Task 1');
    await expect(page.locator('[data-testid="column-todo"]')).not.toContainText('Test Task 1');
  });

  test('TC-E2E-002: Complete task lifecycle management', async ({ page }) => {
    // Step 1: Navigate to existing board or create one
    await page.click('[data-testid="nav-boards"]');
    await page.click('[data-testid="board-item"]').first();

    // Step 2: Create detailed task
    await page.click('[data-testid="add-item-todo"]');
    await page.fill('[data-testid="item-name-input"]', 'Complete Project Setup');
    await page.fill('[data-testid="item-description-input"]', 'Set up project infrastructure and dependencies');

    // Add due date
    await page.click('[data-testid="item-due-date"]');
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    await page.fill('[data-testid="due-date-input"]', tomorrow.toISOString().split('T')[0]);

    // Add priority
    await page.selectOption('[data-testid="item-priority"]', 'high');

    // Add labels
    await page.click('[data-testid="add-label-button"]');
    await page.fill('[data-testid="label-input"]', 'setup');
    await page.click('[data-testid="label-save"]');

    await page.click('[data-testid="item-save-button"]');

    // Step 3: Verify task details
    const taskCard = page.locator('[data-testid="item-Complete Project Setup"]');
    await expect(taskCard).toBeVisible();
    await expect(taskCard.locator('[data-testid="priority-high"]')).toBeVisible();
    await expect(taskCard.locator('[data-testid="label-setup"]')).toBeVisible();

    // Step 4: Edit task details
    await taskCard.click();
    await page.waitForSelector('[data-testid="item-details-modal"]');

    // Add comment
    await page.fill('[data-testid="comment-input"]', 'Starting work on this task');
    await page.click('[data-testid="comment-submit"]');

    // Verify comment added
    await expect(page.locator('[data-testid="comment-list"]')).toContainText('Starting work on this task');

    // Update status to in progress
    await page.selectOption('[data-testid="item-status-select"]', 'in_progress');
    await page.click('[data-testid="item-details-save"]');

    // Step 5: Verify status change
    await page.click('[data-testid="close-modal"]');
    await expect(page.locator('[data-testid="column-in-progress"]')).toContainText('Complete Project Setup');

    // Step 6: Complete task
    const inProgressTask = page.locator('[data-testid="column-in-progress"] [data-testid="item-Complete Project Setup"]');
    await inProgressTask.dragTo(page.locator('[data-testid="column-done"]'));

    // Step 7: Verify completion
    await expect(page.locator('[data-testid="column-done"]')).toContainText('Complete Project Setup');
  });

  test('TC-E2E-003: Real-time collaboration simulation', async ({ page, context }) => {
    // Note: This test simulates multi-user collaboration with multiple browser contexts

    // Step 1: Open board in first context
    await page.goto('/boards');
    await page.click('[data-testid="board-item"]').first();
    const boardUrl = page.url();

    // Step 2: Open second browser context (simulating second user)
    const secondContext = await context.browser()?.newContext();
    const secondPage = await secondContext?.newPage();

    if (secondPage) {
      await secondPage.goto(boardUrl);

      // Step 3: Verify both users see the same board
      await expect(page.locator('[data-testid="board-title"]')).toBeVisible();
      await expect(secondPage.locator('[data-testid="board-title"]')).toBeVisible();

      // Step 4: First user creates item
      await page.click('[data-testid="add-item-todo"]');
      await page.fill('[data-testid="item-name-input"]', 'Collaborative Task');
      await page.click('[data-testid="item-save-button"]');

      // Step 5: Second user should see the new item (real-time update)
      await secondPage.waitForTimeout(1000); // Allow for real-time sync
      await expect(secondPage.locator('[data-testid="item-Collaborative Task"]')).toBeVisible();

      // Step 6: Second user edits the item
      await secondPage.click('[data-testid="item-Collaborative Task"]');
      await secondPage.fill('[data-testid="comment-input"]', 'I can see this task!');
      await secondPage.click('[data-testid="comment-submit"]');
      await secondPage.click('[data-testid="close-modal"]');

      // Step 7: First user should see the comment
      await page.click('[data-testid="item-Collaborative Task"]');
      await expect(page.locator('[data-testid="comment-list"]')).toContainText('I can see this task!');

      await secondContext?.close();
    }
  });

  test('TC-E2E-004: Board sharing and permissions', async ({ page }) => {
    // Step 1: Navigate to board
    await page.goto('/boards');
    await page.click('[data-testid="board-item"]').first();

    // Step 2: Open sharing dialog
    await page.click('[data-testid="board-settings-button"]');
    await page.click('[data-testid="share-board-option"]');

    // Step 3: Generate share link
    await page.click('[data-testid="generate-share-link"]');

    // Step 4: Verify share link created
    await expect(page.locator('[data-testid="share-link-input"]')).toBeVisible();
    const shareLink = await page.locator('[data-testid="share-link-input"]').inputValue();
    expect(shareLink).toContain('/shared/');

    // Step 5: Set permissions
    await page.selectOption('[data-testid="share-permissions"]', 'view');
    await page.click('[data-testid="save-share-settings"]');

    // Step 6: Test anonymous access (new incognito context)
    const incognitoContext = await page.context().browser()?.newContext();
    const incognitoPage = await incognitoContext?.newPage();

    if (incognitoPage) {
      await incognitoPage.goto(shareLink);

      // Should see board content but no edit capabilities
      await expect(incognitoPage.locator('[data-testid="board-title"]')).toBeVisible();
      await expect(incognitoPage.locator('[data-testid="add-item-button"]')).not.toBeVisible();

      await incognitoContext?.close();
    }
  });

  test('TC-E2E-005: Search and filter functionality', async ({ page }) => {
    // Step 1: Navigate to board with multiple items
    await page.goto('/boards');
    await page.click('[data-testid="board-item"]').first();

    // Step 2: Create test items for filtering
    const testItems = [
      { name: 'Frontend Bug Fix', priority: 'high', assignee: 'John Doe' },
      { name: 'Backend API Enhancement', priority: 'medium', assignee: 'Jane Smith' },
      { name: 'Database Migration', priority: 'low', assignee: 'John Doe' }
    ];

    for (const item of testItems) {
      await page.click('[data-testid="add-item-todo"]');
      await page.fill('[data-testid="item-name-input"]', item.name);
      await page.selectOption('[data-testid="item-priority"]', item.priority);
      await page.click('[data-testid="item-save-button"]');
    }

    // Step 3: Test search functionality
    await page.click('[data-testid="search-button"]');
    await page.fill('[data-testid="search-input"]', 'Frontend');

    await expect(page.locator('[data-testid="item-Frontend Bug Fix"]')).toBeVisible();
    await expect(page.locator('[data-testid="item-Backend API Enhancement"]')).not.toBeVisible();

    // Step 4: Clear search
    await page.click('[data-testid="clear-search"]');
    await expect(page.locator('[data-testid="item-Backend API Enhancement"]')).toBeVisible();

    // Step 5: Test filter by priority
    await page.click('[data-testid="filter-button"]');
    await page.click('[data-testid="filter-priority-high"]');

    await expect(page.locator('[data-testid="item-Frontend Bug Fix"]')).toBeVisible();
    await expect(page.locator('[data-testid="item-Backend API Enhancement"]')).not.toBeVisible();

    // Step 6: Clear filters
    await page.click('[data-testid="clear-filters"]');
    await expect(page.locator('[data-testid="item-Backend API Enhancement"]')).toBeVisible();
  });

  test('TC-E2E-006: Mobile responsiveness validation', async ({ page }) => {
    // Step 1: Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 }); // iPhone SE

    // Step 2: Navigate to dashboard
    await page.goto('/dashboard');

    // Step 3: Verify mobile navigation
    await expect(page.locator('[data-testid="mobile-menu-toggle"]')).toBeVisible();
    await page.click('[data-testid="mobile-menu-toggle"]');
    await expect(page.locator('[data-testid="mobile-nav-menu"]')).toBeVisible();

    // Step 4: Navigate to boards on mobile
    await page.click('[data-testid="mobile-nav-boards"]');
    await expect(page).toHaveURL('/boards');

    // Step 5: Open board in mobile view
    await page.click('[data-testid="board-item"]').first();

    // Step 6: Verify mobile board layout
    await expect(page.locator('[data-testid="mobile-column-tabs"]')).toBeVisible();

    // Step 7: Test mobile column switching
    await page.click('[data-testid="mobile-tab-in-progress"]');
    await expect(page.locator('[data-testid="mobile-column-content"]')).toBeVisible();

    // Step 8: Test mobile item creation
    await page.click('[data-testid="mobile-add-item"]');
    await expect(page.locator('[data-testid="mobile-item-form"]')).toBeVisible();
  });

  test('TC-E2E-007: Performance validation', async ({ page }) => {
    // Step 1: Navigate to boards page
    await page.goto('/boards');

    // Step 2: Measure page load performance
    const loadTime = await page.evaluate(() => {
      return performance.timing.loadEventEnd - performance.timing.navigationStart;
    });

    expect(loadTime).toBeLessThan(3000); // Page should load in < 3 seconds

    // Step 3: Navigate to board and measure rendering
    const startTime = Date.now();
    await page.click('[data-testid="board-item"]').first();
    await page.waitForSelector('[data-testid="board-content"]');
    const renderTime = Date.now() - startTime;

    expect(renderTime).toBeLessThan(2000); // Board should render in < 2 seconds

    // Step 4: Test interaction responsiveness
    const interactionStart = Date.now();
    await page.click('[data-testid="add-item-todo"]');
    await page.waitForSelector('[data-testid="item-form"]');
    const interactionTime = Date.now() - interactionStart;

    expect(interactionTime).toBeLessThan(500); // Interactions should respond in < 500ms
  });

  test('TC-E2E-008: Error handling and recovery', async ({ page }) => {
    // Step 1: Test network error simulation
    await page.route('**/api/**', route => route.abort());

    // Step 2: Try to perform action that requires API
    await page.goto('/boards');
    await page.click('[data-testid="create-board-button"]');
    await page.fill('[data-testid="board-name-input"]', 'Network Error Test');
    await page.click('[data-testid="board-create-submit"]');

    // Step 3: Verify error handling
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
    await expect(page.locator('[data-testid="error-message"]')).toContainText('network');

    // Step 4: Restore network and retry
    await page.unroute('**/api/**');
    await page.click('[data-testid="retry-button"]');

    // Step 5: Verify recovery
    await expect(page).toHaveURL(/\/board\/[a-zA-Z0-9-]+/);
  });

});