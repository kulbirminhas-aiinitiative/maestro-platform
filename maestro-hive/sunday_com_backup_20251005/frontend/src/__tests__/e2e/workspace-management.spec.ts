/**
 * End-to-End Tests for Workspace Management
 * Tests the complete user workflow for workspace management
 */

import { test, expect, Page, BrowserContext } from '@playwright/test';

test.describe('Workspace Management E2E Tests', () => {
  let page: Page;
  let context: BrowserContext;

  test.beforeEach(async ({ browser }) => {
    context = await browser.newContext();
    page = await context.newPage();

    // Login before each test
    await page.goto('/login');
    await page.fill('[data-testid="email-input"]', 'test@example.com');
    await page.fill('[data-testid="password-input"]', 'testPassword123!');
    await page.click('[data-testid="login-button"]');
    await page.waitForURL('/dashboard');
  });

  test.afterEach(async () => {
    await context.close();
  });

  test.describe('Workspace Creation', () => {
    test('should create a new workspace successfully', async () => {
      // Navigate to workspace creation
      await page.click('[data-testid="create-workspace-button"]');
      await expect(page).toHaveURL('/workspaces/new');

      // Fill workspace details
      await page.fill('[data-testid="workspace-name-input"]', 'Test Workspace');
      await page.fill('[data-testid="workspace-description-textarea"]', 'A test workspace for E2E testing');

      // Select organization
      await page.click('[data-testid="organization-select"]');
      await page.click('[data-testid="organization-option-1"]');

      // Set workspace settings
      await page.check('[data-testid="workspace-private-checkbox"]');

      // Create workspace
      await page.click('[data-testid="create-workspace-submit"]');

      // Wait for creation success
      await expect(page.locator('[data-testid="success-message"]')).toBeVisible();
      await expect(page.locator('[data-testid="success-message"]')).toContainText('Workspace created successfully');

      // Verify redirect to workspace page
      await expect(page).toHaveURL(/\/workspaces\/[a-zA-Z0-9-]+/);

      // Verify workspace details are displayed
      await expect(page.locator('[data-testid="workspace-title"]')).toContainText('Test Workspace');
      await expect(page.locator('[data-testid="workspace-description"]')).toContainText('A test workspace for E2E testing');
    });

    test('should validate required fields', async () => {
      await page.click('[data-testid="create-workspace-button"]');
      await expect(page).toHaveURL('/workspaces/new');

      // Try to submit without required fields
      await page.click('[data-testid="create-workspace-submit"]');

      // Check validation errors
      await expect(page.locator('[data-testid="name-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="name-error"]')).toContainText('Workspace name is required');

      await expect(page.locator('[data-testid="organization-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="organization-error"]')).toContainText('Please select an organization');
    });

    test('should handle creation errors gracefully', async () => {
      await page.click('[data-testid="create-workspace-button"]');

      // Mock API error response
      await page.route('**/api/v1/workspaces', route => {
        route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({
            error: 'Workspace name already exists'
          })
        });
      });

      // Fill form and submit
      await page.fill('[data-testid="workspace-name-input"]', 'Duplicate Workspace');
      await page.click('[data-testid="organization-select"]');
      await page.click('[data-testid="organization-option-1"]');
      await page.click('[data-testid="create-workspace-submit"]');

      // Check error message
      await expect(page.locator('[data-testid="error-message"]')).toBeVisible();
      await expect(page.locator('[data-testid="error-message"]')).toContainText('Workspace name already exists');
    });
  });

  test.describe('Workspace Listing', () => {
    test('should display user workspaces', async () => {
      await page.goto('/workspaces');

      // Wait for workspaces to load
      await expect(page.locator('[data-testid="workspace-list"]')).toBeVisible();

      // Check that at least one workspace is displayed
      const workspaceCards = page.locator('[data-testid="workspace-card"]');
      await expect(workspaceCards).toHaveCountGreaterThan(0);

      // Check workspace card content
      const firstWorkspace = workspaceCards.first();
      await expect(firstWorkspace.locator('[data-testid="workspace-name"]')).toBeVisible();
      await expect(firstWorkspace.locator('[data-testid="workspace-description"]')).toBeVisible();
      await expect(firstWorkspace.locator('[data-testid="workspace-member-count"]')).toBeVisible();
    });

    test('should filter workspaces by organization', async () => {
      await page.goto('/workspaces');

      // Open organization filter
      await page.click('[data-testid="organization-filter-button"]');
      await page.click('[data-testid="organization-filter-option-1"]');

      // Wait for filtered results
      await page.waitForResponse('**/api/v1/workspaces*');

      // Verify filter is applied
      await expect(page.locator('[data-testid="active-filter"]')).toContainText('Organization: Test Org');

      // Verify results are filtered
      const workspaceCards = page.locator('[data-testid="workspace-card"]');
      await expect(workspaceCards).toHaveCountGreaterThan(0);
    });

    test('should search workspaces by name', async () => {
      await page.goto('/workspaces');

      // Enter search term
      await page.fill('[data-testid="workspace-search-input"]', 'Test Workspace');
      await page.press('[data-testid="workspace-search-input"]', 'Enter');

      // Wait for search results
      await page.waitForResponse('**/api/v1/workspaces*');

      // Verify search results
      const workspaceCards = page.locator('[data-testid="workspace-card"]');
      const cardNames = workspaceCards.locator('[data-testid="workspace-name"]');

      // All results should contain search term
      const count = await workspaceCards.count();
      for (let i = 0; i < count; i++) {
        const name = await cardNames.nth(i).textContent();
        expect(name?.toLowerCase()).toContain('test workspace');
      }
    });

    test('should handle empty workspace list', async () => {
      // Mock empty response
      await page.route('**/api/v1/workspaces*', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            workspaces: [],
            pagination: {
              page: 1,
              limit: 10,
              total: 0,
              totalPages: 0
            }
          })
        });
      });

      await page.goto('/workspaces');

      // Check empty state
      await expect(page.locator('[data-testid="empty-workspaces"]')).toBeVisible();
      await expect(page.locator('[data-testid="empty-workspaces"]')).toContainText('No workspaces found');
      await expect(page.locator('[data-testid="create-first-workspace-button"]')).toBeVisible();
    });
  });

  test.describe('Workspace Navigation', () => {
    test('should navigate to workspace details', async () => {
      await page.goto('/workspaces');

      // Click on first workspace
      const firstWorkspace = page.locator('[data-testid="workspace-card"]').first();
      await firstWorkspace.click();

      // Verify navigation to workspace page
      await expect(page).toHaveURL(/\/workspaces\/[a-zA-Z0-9-]+/);

      // Verify workspace page content loads
      await expect(page.locator('[data-testid="workspace-header"]')).toBeVisible();
      await expect(page.locator('[data-testid="workspace-boards-section"]')).toBeVisible();
      await expect(page.locator('[data-testid="workspace-members-section"]')).toBeVisible();
    });

    test('should show workspace breadcrumb navigation', async () => {
      await page.goto('/workspaces');

      // Navigate to workspace
      const firstWorkspace = page.locator('[data-testid="workspace-card"]').first();
      const workspaceName = await firstWorkspace.locator('[data-testid="workspace-name"]').textContent();
      await firstWorkspace.click();

      // Check breadcrumb
      await expect(page.locator('[data-testid="breadcrumb"]')).toBeVisible();
      await expect(page.locator('[data-testid="breadcrumb-workspaces"]')).toContainText('Workspaces');
      await expect(page.locator('[data-testid="breadcrumb-current"]')).toContainText(workspaceName || '');

      // Test breadcrumb navigation
      await page.click('[data-testid="breadcrumb-workspaces"]');
      await expect(page).toHaveURL('/workspaces');
    });
  });

  test.describe('Workspace Settings', () => {
    test('should access workspace settings', async () => {
      await page.goto('/workspaces');

      // Navigate to workspace
      await page.locator('[data-testid="workspace-card"]').first().click();

      // Open settings
      await page.click('[data-testid="workspace-settings-button"]');

      // Verify settings modal or page opens
      await expect(page.locator('[data-testid="workspace-settings-modal"]')).toBeVisible();
      await expect(page.locator('[data-testid="settings-general-tab"]')).toBeVisible();
      await expect(page.locator('[data-testid="settings-members-tab"]')).toBeVisible();
      await expect(page.locator('[data-testid="settings-permissions-tab"]')).toBeVisible();
    });

    test('should update workspace details', async () => {
      await page.goto('/workspaces');
      await page.locator('[data-testid="workspace-card"]').first().click();
      await page.click('[data-testid="workspace-settings-button"]');

      // Update workspace name
      await page.fill('[data-testid="settings-name-input"]', 'Updated Workspace Name');
      await page.fill('[data-testid="settings-description-textarea"]', 'Updated description');

      // Save changes
      await page.click('[data-testid="save-settings-button"]');

      // Verify success message
      await expect(page.locator('[data-testid="settings-success-message"]')).toBeVisible();
      await expect(page.locator('[data-testid="settings-success-message"]')).toContainText('Workspace updated successfully');

      // Close settings and verify changes
      await page.click('[data-testid="close-settings-button"]');
      await expect(page.locator('[data-testid="workspace-title"]')).toContainText('Updated Workspace Name');
    });

    test('should manage workspace members', async () => {
      await page.goto('/workspaces');
      await page.locator('[data-testid="workspace-card"]').first().click();
      await page.click('[data-testid="workspace-settings-button"]');

      // Switch to members tab
      await page.click('[data-testid="settings-members-tab"]');

      // Verify members list
      await expect(page.locator('[data-testid="members-list"]')).toBeVisible();

      // Add new member
      await page.click('[data-testid="add-member-button"]');
      await page.fill('[data-testid="member-email-input"]', 'newmember@example.com');
      await page.click('[data-testid="member-role-select"]');
      await page.click('[data-testid="member-role-editor"]');
      await page.click('[data-testid="send-invitation-button"]');

      // Verify invitation sent
      await expect(page.locator('[data-testid="invitation-success"]')).toBeVisible();
      await expect(page.locator('[data-testid="invitation-success"]')).toContainText('Invitation sent successfully');
    });
  });

  test.describe('Workspace Deletion', () => {
    test('should delete workspace with confirmation', async () => {
      await page.goto('/workspaces');
      await page.locator('[data-testid="workspace-card"]').first().click();
      await page.click('[data-testid="workspace-settings-button"]');

      // Navigate to danger zone
      await page.click('[data-testid="settings-danger-tab"]');

      // Click delete button
      await page.click('[data-testid="delete-workspace-button"]');

      // Confirm deletion in modal
      await expect(page.locator('[data-testid="delete-confirmation-modal"]')).toBeVisible();
      await page.fill('[data-testid="delete-confirmation-input"]', 'DELETE');
      await page.click('[data-testid="confirm-delete-button"]');

      // Verify deletion success and redirect
      await expect(page.locator('[data-testid="deletion-success"]')).toBeVisible();
      await expect(page).toHaveURL('/workspaces');
    });

    test('should prevent deletion without proper confirmation', async () => {
      await page.goto('/workspaces');
      await page.locator('[data-testid="workspace-card"]').first().click();
      await page.click('[data-testid="workspace-settings-button"]');
      await page.click('[data-testid="settings-danger-tab"]');
      await page.click('[data-testid="delete-workspace-button"]');

      // Try to confirm without typing DELETE
      await page.click('[data-testid="confirm-delete-button"]');

      // Button should be disabled or show error
      await expect(page.locator('[data-testid="delete-confirmation-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="delete-confirmation-error"]')).toContainText('Please type DELETE to confirm');
    });
  });

  test.describe('Mobile Responsiveness', () => {
    test('should work correctly on mobile devices', async () => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });

      await page.goto('/workspaces');

      // Check mobile layout
      await expect(page.locator('[data-testid="mobile-workspace-list"]')).toBeVisible();

      // Test mobile navigation
      await page.click('[data-testid="mobile-menu-button"]');
      await expect(page.locator('[data-testid="mobile-nav-menu"]')).toBeVisible();

      // Test workspace card on mobile
      const workspaceCard = page.locator('[data-testid="workspace-card"]').first();
      await expect(workspaceCard).toBeVisible();

      // Test tap interaction
      await workspaceCard.tap();
      await expect(page).toHaveURL(/\/workspaces\/[a-zA-Z0-9-]+/);
    });
  });

  test.describe('Performance and Loading States', () => {
    test('should show loading states during API calls', async () => {
      // Slow down network to see loading states
      await page.route('**/api/v1/workspaces*', async route => {
        await new Promise(resolve => setTimeout(resolve, 2000));
        route.continue();
      });

      await page.goto('/workspaces');

      // Check loading state
      await expect(page.locator('[data-testid="workspaces-loading"]')).toBeVisible();
      await expect(page.locator('[data-testid="workspace-skeleton"]')).toBeVisible();

      // Wait for content to load
      await expect(page.locator('[data-testid="workspace-list"]')).toBeVisible();
      await expect(page.locator('[data-testid="workspaces-loading"]')).not.toBeVisible();
    });

    test('should handle API errors gracefully', async () => {
      // Mock API error
      await page.route('**/api/v1/workspaces*', route => {
        route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({
            error: 'Internal server error'
          })
        });
      });

      await page.goto('/workspaces');

      // Check error state
      await expect(page.locator('[data-testid="workspaces-error"]')).toBeVisible();
      await expect(page.locator('[data-testid="workspaces-error"]')).toContainText('Failed to load workspaces');

      // Test retry functionality
      await page.click('[data-testid="retry-button"]');
      await expect(page.locator('[data-testid="workspaces-loading"]')).toBeVisible();
    });
  });

  test.describe('Accessibility', () => {
    test('should be accessible via keyboard navigation', async () => {
      await page.goto('/workspaces');

      // Test keyboard navigation
      await page.keyboard.press('Tab');
      await expect(page.locator('[data-testid="create-workspace-button"]')).toBeFocused();

      await page.keyboard.press('Tab');
      await expect(page.locator('[data-testid="workspace-search-input"]')).toBeFocused();

      // Navigate to first workspace with keyboard
      await page.keyboard.press('Tab');
      await page.keyboard.press('Tab'); // Skip filter button
      await expect(page.locator('[data-testid="workspace-card"]').first()).toBeFocused();

      // Activate with Enter
      await page.keyboard.press('Enter');
      await expect(page).toHaveURL(/\/workspaces\/[a-zA-Z0-9-]+/);
    });

    test('should have proper ARIA labels and roles', async () => {
      await page.goto('/workspaces');

      // Check ARIA attributes
      await expect(page.locator('[data-testid="workspace-list"]')).toHaveAttribute('role', 'list');
      await expect(page.locator('[data-testid="workspace-card"]').first()).toHaveAttribute('role', 'listitem');

      // Check button labels
      await expect(page.locator('[data-testid="create-workspace-button"]')).toHaveAttribute('aria-label', 'Create new workspace');
      await expect(page.locator('[data-testid="workspace-search-input"]')).toHaveAttribute('aria-label', 'Search workspaces');
    });
  });
});