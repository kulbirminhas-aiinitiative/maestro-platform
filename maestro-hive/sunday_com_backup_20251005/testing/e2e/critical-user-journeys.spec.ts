/**
 * Critical User Journeys E2E Tests
 * Sunday.com - Work Management Platform
 *
 * These tests validate the most important user workflows
 * Status: Ready for execution once BoardPage and WorkspacePage are implemented
 */

import { test, expect } from '../framework/test-utils';
import { TestDataFactory } from '../framework/test-utils';

test.describe('Critical User Journeys', () => {
  let testUser: any;
  let testWorkspace: any;
  let testBoard: any;

  test.beforeEach(async ({ apiHelper, page }) => {
    // Create test user and authenticate
    testUser = await apiHelper.createAndAuthenticateUser({
      email: 'journey-test@example.com',
      firstName: 'Journey',
      lastName: 'Tester'
    });

    // Create test workspace with board
    const workspaceData = await apiHelper.createTestWorkspace();
    testWorkspace = workspaceData.workspace;
    testBoard = workspaceData.board;
  });

  test.describe('New User Onboarding Journey', () => {
    test('P0: Complete new user setup and first project creation', async ({
      page,
      e2eHelper,
      apiHelper
    }) => {
      // Step 1: User registers and logs in
      await page.goto('/register');

      const newUser = TestDataFactory.createUser({
        email: 'onboarding-test@example.com'
      });

      await page.fill('[data-testid="email-input"]', newUser.email);
      await page.fill('[data-testid="password-input"]', newUser.password);
      await page.fill('[data-testid="first-name-input"]', newUser.firstName);
      await page.fill('[data-testid="last-name-input"]', newUser.lastName);
      await page.click('[data-testid="register-button"]');

      // Should redirect to login or dashboard
      await page.waitForURL(/\/(login|dashboard)/);

      // If redirected to login, complete login
      if (page.url().includes('/login')) {
        await e2eHelper.login(newUser.email, newUser.password);
      }

      // Step 2: User should be on dashboard
      await expect(page).toHaveURL('/dashboard');
      await expect(page.locator('[data-testid="welcome-message"]')).toBeVisible();

      // Step 3: Create first workspace
      await page.click('[data-testid="create-workspace-button"]');

      const workspaceName = 'My First Workspace';
      await page.fill('[data-testid="workspace-name-input"]', workspaceName);
      await page.fill('[data-testid="workspace-description-input"]', 'Getting started with Sunday.com');
      await page.click('[data-testid="save-workspace-button"]');

      // Should navigate to new workspace
      await page.waitForURL(/\/workspace\/[^\/]+/);
      await expect(page.locator('h1')).toContainText(workspaceName);

      // Step 4: Create first board
      await page.click('[data-testid="create-board-button"]');

      const boardName = 'My First Project';
      await page.fill('[data-testid="board-name-input"]', boardName);
      await page.selectOption('[data-testid="board-type-select"]', 'kanban');
      await page.click('[data-testid="save-board-button"]');

      // Should navigate to board page
      await page.waitForURL(/\/boards\/[^\/]+/);
      await expect(page.locator('h1')).toContainText(boardName);

      // Step 5: Create first task
      await e2eHelper.createItem({
        name: 'My First Task',
        description: 'This is my first task in Sunday.com',
        priority: 'medium'
      });

      // Verify task was created
      await expect(page.locator('[data-testid="item-My First Task"]')).toBeVisible();

      // Step 6: Move task to different column
      await e2eHelper.dragItemToColumn('My First Task', 'in_progress');

      // Verify task moved
      await expect(
        page.locator('[data-testid="column-in_progress"] [data-testid="item-My First Task"]')
      ).toBeVisible();
    });

    test('P0: User can invite team members and collaborate', async ({
      page,
      e2eHelper,
      apiHelper,
      multiUserHelper,
      browser
    }) => {
      // Setup: Navigate to test workspace
      await e2eHelper.login(testUser.email, testUser.password);
      await page.goto(`/workspace/${testWorkspace.id}`);

      // Step 1: Invite team member
      await page.click('[data-testid="invite-member-button"]');

      const inviteEmail = 'colleague@example.com';
      await page.fill('[data-testid="invite-email-input"]', inviteEmail);
      await page.selectOption('[data-testid="member-role-select"]', 'member');
      await page.click('[data-testid="send-invite-button"]');

      // Verify invitation sent
      await expect(page.locator('[data-testid="invite-success-message"]')).toBeVisible();

      // Step 2: Simulate team member joining (create second user session)
      const memberPage = await multiUserHelper.createUserSession(browser, {
        email: inviteEmail,
        firstName: 'Team',
        lastName: 'Member'
      });

      // Member accepts invite and joins workspace
      const memberE2EHelper = new (await import('../framework/test-utils')).E2ETestHelper(memberPage);
      await memberE2EHelper.login(inviteEmail, 'TestPassword123!');

      // Step 3: Both users work on same board
      await e2eHelper.navigateToBoard(testBoard.id);
      await memberE2EHelper.navigateToBoard(testBoard.id);

      // Verify both users can see WebSocket connection
      await e2eHelper.verifyWebSocketConnection();
      await memberE2EHelper.verifyWebSocketConnection();

      // Step 4: Real-time collaboration test
      await multiUserHelper.simulateCollaboration(testBoard.id);

      // Verify both users see updates
      await expect(
        page.locator('[data-testid="item-Collaboration Test Item"]')
      ).toBeVisible();

      await expect(
        memberPage.locator('[data-testid="item-Collaboration Test Item"]')
      ).toBeVisible();
    });
  });

  test.describe('Daily Work Management Journey', () => {
    test('P0: Complete task management workflow', async ({
      page,
      e2eHelper
    }) => {
      // Setup: Login and navigate to board
      await e2eHelper.login(testUser.email, testUser.password);
      await e2eHelper.navigateToBoard(testBoard.id);

      // Step 1: View existing tasks
      await expect(page.locator('[data-testid="board-view"]')).toBeVisible();
      await expect(page.locator('[data-testid="column-todo"]')).toBeVisible();
      await expect(page.locator('[data-testid="column-in_progress"]')).toBeVisible();
      await expect(page.locator('[data-testid="column-done"]')).toBeVisible();

      // Step 2: Create multiple tasks with different priorities
      const tasks = [
        { name: 'High Priority Bug Fix', priority: 'high', description: 'Critical bug in production' },
        { name: 'Feature Development', priority: 'medium', description: 'New user feature' },
        { name: 'Documentation Update', priority: 'low', description: 'Update API docs' }
      ];

      for (const task of tasks) {
        await e2eHelper.createItem(task);
        await expect(page.locator(`[data-testid="item-${task.name}"]`)).toBeVisible();
      }

      // Step 3: Work through tasks (move them through workflow)
      // Start with high priority task
      await e2eHelper.dragItemToColumn('High Priority Bug Fix', 'in_progress');
      await expect(
        page.locator('[data-testid="column-in_progress"] [data-testid="item-High Priority Bug Fix"]')
      ).toBeVisible();

      // Complete the task
      await e2eHelper.dragItemToColumn('High Priority Bug Fix', 'done');
      await expect(
        page.locator('[data-testid="column-done"] [data-testid="item-High Priority Bug Fix"]')
      ).toBeVisible();

      // Step 4: Add details to task
      await page.click('[data-testid="item-Feature Development"]');
      await page.waitForSelector('[data-testid="item-detail-modal"]');

      // Add comment
      await page.fill('[data-testid="comment-input"]', 'Starting work on this feature');
      await page.click('[data-testid="add-comment-button"]');

      // Verify comment appears
      await expect(page.locator('[data-testid="comment-text"]')).toContainText('Starting work on this feature');

      // Set due date
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      await page.fill('[data-testid="due-date-input"]', tomorrow.toISOString().split('T')[0]);

      // Assign to self
      await page.selectOption('[data-testid="assignee-select"]', testUser.id);

      // Save changes
      await page.click('[data-testid="save-item-button"]');
      await page.click('[data-testid="close-modal-button"]');

      // Step 5: Use filters and search
      await page.fill('[data-testid="search-input"]', 'Feature');
      await page.waitForTimeout(500); // Debounce

      // Should only show feature task
      await expect(page.locator('[data-testid="item-Feature Development"]')).toBeVisible();
      await expect(page.locator('[data-testid="item-Documentation Update"]')).not.toBeVisible();

      // Clear search
      await page.fill('[data-testid="search-input"]', '');

      // Filter by priority
      await page.selectOption('[data-testid="priority-filter"]', 'high');
      await expect(page.locator('[data-testid="item-High Priority Bug Fix"]')).toBeVisible();
      await expect(page.locator('[data-testid="item-Feature Development"]')).not.toBeVisible();
    });

    test('P1: File attachment and management workflow', async ({
      page,
      e2eHelper
    }) => {
      // Setup: Create task for file testing
      await e2eHelper.login(testUser.email, testUser.password);
      await e2eHelper.navigateToBoard(testBoard.id);

      await e2eHelper.createItem({
        name: 'Task with Attachments',
        description: 'Testing file upload functionality'
      });

      // Open task details
      await page.click('[data-testid="item-Task with Attachments"]');
      await page.waitForSelector('[data-testid="item-detail-modal"]');

      // Step 1: Upload file
      const fileInput = page.locator('[data-testid="file-upload-input"]');

      // Create test file (in real test, use actual file)
      const testFile = 'test-document.txt';
      await fileInput.setInputFiles({
        name: testFile,
        mimeType: 'text/plain',
        buffer: Buffer.from('This is a test document content')
      });

      // Wait for upload to complete
      await expect(page.locator('[data-testid="upload-progress"]')).toBeVisible();
      await expect(page.locator('[data-testid="upload-complete"]')).toBeVisible();

      // Step 2: Verify file appears in attachments
      await expect(page.locator(`[data-testid="attachment-${testFile}"]`)).toBeVisible();

      // Step 3: Download file
      const downloadPromise = page.waitForEvent('download');
      await page.click(`[data-testid="download-${testFile}"]`);
      const download = await downloadPromise;

      expect(download.suggestedFilename()).toBe(testFile);

      // Step 4: Delete file
      await page.click(`[data-testid="delete-${testFile}"]`);
      await page.click('[data-testid="confirm-delete-button"]');

      // Verify file removed
      await expect(page.locator(`[data-testid="attachment-${testFile}"]`)).not.toBeVisible();
    });
  });

  test.describe('Real-time Collaboration Journey', () => {
    test('P0: Multi-user real-time collaboration', async ({
      browser,
      multiUserHelper
    }) => {
      // Create multiple user sessions
      const user1Page = await multiUserHelper.createUserSession(browser, {
        email: 'user1@test.com',
        firstName: 'User',
        lastName: 'One'
      });

      const user2Page = await multiUserHelper.createUserSession(browser, {
        email: 'user2@test.com',
        firstName: 'User',
        lastName: 'Two'
      });

      const user1Helper = new (await import('../framework/test-utils')).E2ETestHelper(user1Page);
      const user2Helper = new (await import('../framework/test-utils')).E2ETestHelper(user2Page);

      // Both users navigate to same board
      await user1Helper.navigateToBoard(testBoard.id);
      await user2Helper.navigateToBoard(testBoard.id);

      // Verify presence indicators
      await expect(user1Page.locator('[data-testid="user-presence-indicator"]')).toBeVisible();
      await expect(user2Page.locator('[data-testid="user-presence-indicator"]')).toBeVisible();

      // Step 1: User 1 creates item
      await user1Helper.createItem({
        name: 'Real-time Test Item',
        description: 'Testing real-time updates'
      });

      // Step 2: User 2 should see item immediately
      await user2Helper.waitForRealtimeUpdate('[data-testid="item-Real-time Test Item"]');
      await expect(user2Page.locator('[data-testid="item-Real-time Test Item"]')).toBeVisible();

      // Step 3: User 2 updates item status
      await user2Helper.dragItemToColumn('Real-time Test Item', 'in_progress');

      // Step 4: User 1 should see status change
      await user1Helper.waitForRealtimeUpdate(
        '[data-testid="column-in_progress"] [data-testid="item-Real-time Test Item"]'
      );

      // Step 5: User 1 adds comment
      await user1Page.click('[data-testid="item-Real-time Test Item"]');
      await user1Page.fill('[data-testid="comment-input"]', 'Added by User 1');
      await user1Page.click('[data-testid="add-comment-button"]');

      // Step 6: User 2 should see comment (if modal is open)
      if (await user2Page.locator('[data-testid="item-detail-modal"]').isVisible()) {
        await user2Helper.waitForRealtimeUpdate('[data-testid="comment-text"]');
        await expect(user2Page.locator('[data-testid="comment-text"]')).toContainText('Added by User 1');
      }

      // Step 7: Test conflict resolution
      // Both users try to edit same item simultaneously
      await user1Page.click('[data-testid="edit-item-button"]');
      await user2Page.click('[data-testid="item-Real-time Test Item"]');

      // User 1 updates title
      await user1Page.fill('[data-testid="item-name-input"]', 'Updated by User 1');
      await user1Page.click('[data-testid="save-item-button"]');

      // User 2 should see update or conflict resolution
      await user2Helper.waitForRealtimeUpdate('[data-testid="item-Updated by User 1"]');
    });

    test('P1: Network interruption and recovery', async ({
      page,
      e2eHelper
    }) => {
      // Setup
      await e2eHelper.login(testUser.email, testUser.password);
      await e2eHelper.navigateToBoard(testBoard.id);

      // Verify initial connection
      await e2eHelper.verifyWebSocketConnection();

      // Create item while connected
      await e2eHelper.createItem({
        name: 'Pre-disconnect Item',
        description: 'Created before network issue'
      });

      // Simulate network failure
      await e2eHelper.simulateNetworkFailure();

      // Verify connection status shows disconnected
      await expect(
        page.locator('[data-testid="connection-status"][data-status="disconnected"]')
      ).toBeVisible();

      // Try to create item while disconnected (should be queued)
      await e2eHelper.createItem({
        name: 'Offline Item',
        description: 'Created while offline'
      });

      // Verify offline indicator
      await expect(page.locator('[data-testid="offline-indicator"]')).toBeVisible();

      // Network recovers (already handled in simulateNetworkFailure)
      await expect(
        page.locator('[data-testid="connection-status"][data-status="connected"]')
      ).toBeVisible();

      // Verify offline item syncs
      await expect(page.locator('[data-testid="item-Offline Item"]')).toBeVisible();
    });
  });

  test.describe('Error Handling Journey', () => {
    test('P1: Graceful error handling and recovery', async ({
      page,
      e2eHelper,
      apiHelper
    }) => {
      await e2eHelper.login(testUser.email, testUser.password);
      await e2eHelper.navigateToBoard(testBoard.id);

      // Test 1: Handle API errors gracefully
      // Intercept API call to return error
      await page.route('**/api/items', route => {
        if (route.request().method() === 'POST') {
          route.fulfill({
            status: 500,
            contentType: 'application/json',
            body: JSON.stringify({ error: 'Internal server error' })
          });
        } else {
          route.continue();
        }
      });

      // Try to create item (should fail gracefully)
      await page.click('[data-testid="add-item-button"]');
      await page.fill('[data-testid="item-name-input"]', 'Error Test Item');
      await page.click('[data-testid="save-item-button"]');

      // Should show error message
      await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
      await expect(page.locator('[data-testid="error-message"]')).toContainText('server error');

      // Should have retry option
      await expect(page.locator('[data-testid="retry-button"]')).toBeVisible();

      // Restore API
      await page.unroute('**/api/items');

      // Retry should work
      await page.click('[data-testid="retry-button"]');
      await expect(page.locator('[data-testid="item-Error Test Item"]')).toBeVisible();

      // Test 2: Handle permission errors
      // Mock unauthorized response
      await page.route('**/api/boards/*/items', route => {
        route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({ error: 'Insufficient permissions' })
        });
      });

      await page.click('[data-testid="add-item-button"]');
      await page.fill('[data-testid="item-name-input"]', 'Permission Test Item');
      await page.click('[data-testid="save-item-button"]');

      // Should show permission error
      await expect(page.locator('[data-testid="permission-error"]')).toBeVisible();
    });
  });
});

test.describe('Performance Journey Tests', () => {
  test('P2: Performance with large datasets', async ({
    page,
    e2eHelper,
    apiHelper,
    performanceHelper
  }) => {
    // Create board with many items via API
    const user = await apiHelper.createAndAuthenticateUser();
    const { board } = await apiHelper.createTestWorkspace();

    // Create 100 items
    const items = [];
    for (let i = 0; i < 100; i++) {
      const itemData = TestDataFactory.createItem({
        boardId: board.id,
        name: `Performance Test Item ${i}`
      });
      const response = await apiHelper.request('/items', {
        method: 'POST',
        body: JSON.stringify(itemData)
      });
      items.push(response.data);
    }

    // Measure page load time
    const metrics = await performanceHelper.measurePageLoad(page, `/boards/${board.id}`);

    // Performance assertions
    expect(metrics.totalTime).toBeLessThan(5000); // 5 seconds max
    expect(metrics.firstContentfulPaint).toBeLessThan(2000); // 2 seconds FCP

    // Test scrolling performance
    const startMemory = await performanceHelper.monitorMemoryUsage(page);

    // Scroll through all items
    for (let i = 0; i < 10; i++) {
      await page.mouse.wheel(0, 500);
      await page.waitForTimeout(100);
    }

    const endMemory = await performanceHelper.monitorMemoryUsage(page);

    // Memory shouldn't increase dramatically
    if (startMemory && endMemory) {
      const memoryIncrease = endMemory.usedJSHeapSize - startMemory.usedJSHeapSize;
      expect(memoryIncrease).toBeLessThan(50 * 1024 * 1024); // 50MB increase max
    }
  });
});

test.afterEach(async ({ page }, testInfo) => {
  // Capture screenshot on failure
  if (testInfo.status !== testInfo.expectedStatus) {
    await testInfo.attach('screenshot', {
      body: await page.screenshot(),
      contentType: 'image/png',
    });
  }
});

test.afterAll(async ({ apiHelper }) => {
  // Cleanup test data
  // Implementation depends on your cleanup strategy
});