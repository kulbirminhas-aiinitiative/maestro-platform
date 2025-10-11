/**
 * End-to-End Tests for Workspace Management
 * Tests complete user workflows in the browser
 * NOTE: These tests assume Workspace UI is implemented (currently shows "Coming Soon")
 */

import { test, expect } from '@playwright/test';
import { TestDataFactory } from '../helpers/test-data-factory';

// Test configuration
const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:3000';
const API_BASE_URL = process.env.E2E_API_URL || 'http://localhost:3001';

test.describe('Workspace Management E2E', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the application
    await page.goto(BASE_URL);
  });

  test.describe('User Onboarding and Workspace Creation', () => {
    test('complete user registration and first workspace setup', async ({ page }) => {
      const userData = TestDataFactory.createUser({
        email: `test-${Date.now()}@example.com`,
        firstName: 'John',
        lastName: 'Doe',
      });

      // Step 1: User Registration
      await page.goto(`${BASE_URL}/register`);

      await page.fill('[data-testid="first-name-input"]', userData.firstName);
      await page.fill('[data-testid="last-name-input"]', userData.lastName);
      await page.fill('[data-testid="email-input"]', userData.email);
      await page.fill('[data-testid="password-input"]', 'SecurePassword123');
      await page.fill('[data-testid="confirm-password-input"]', 'SecurePassword123');

      // Submit registration
      await page.click('[data-testid="register-button"]');

      // Verify redirection to verification page
      await expect(page).toHaveURL(new RegExp(`${BASE_URL}/verify-email`));
      await expect(page.locator('[data-testid="verification-message"]')).toContainText(
        'Please check your email to verify your account'
      );

      // Step 2: Simulate email verification (for testing, we'll direct navigate)
      // In real scenario, user would click email link
      await page.goto(`${BASE_URL}/login`);

      // Step 3: User Login
      await page.fill('[data-testid="email-input"]', userData.email);
      await page.fill('[data-testid="password-input"]', 'SecurePassword123');
      await page.click('[data-testid="login-button"]');

      // Verify successful login and redirection to dashboard
      await expect(page).toHaveURL(new RegExp(`${BASE_URL}/dashboard`));
      await expect(page.locator('[data-testid="user-avatar"]')).toBeVisible();

      // Step 4: First-time user should see workspace creation prompt
      await expect(page.locator('[data-testid="create-first-workspace"]')).toBeVisible();
      await expect(page.locator('[data-testid="workspace-creation-prompt"]')).toContainText(
        'Create your first workspace to get started'
      );

      // Step 5: Create first workspace
      await page.click('[data-testid="create-first-workspace"]');

      // Verify workspace creation modal opens
      await expect(page.locator('[data-testid="workspace-creation-modal"]')).toBeVisible();

      await page.fill('[data-testid="workspace-name-input"]', 'My First Workspace');
      await page.fill(
        '[data-testid="workspace-description-input"]',
        'This is my first workspace for project management'
      );

      // Select workspace template
      await page.click('[data-testid="workspace-template-selector"]');
      await page.click('[data-testid="template-option-team"]');

      await page.click('[data-testid="create-workspace-button"]');

      // Step 6: Verify workspace creation success
      await expect(page.locator('[data-testid="workspace-creation-success"]')).toBeVisible();
      await expect(page.locator('[data-testid="workspace-creation-success"]')).toContainText(
        'Workspace created successfully!'
      );

      // Close success message
      await page.click('[data-testid="success-message-close"]');

      // Step 7: Verify redirection to workspace page
      await expect(page).toHaveURL(new RegExp(`${BASE_URL}/workspace/`));
      await expect(page.locator('[data-testid="workspace-title"]')).toContainText('My First Workspace');
      await expect(page.locator('[data-testid="workspace-description"]')).toContainText(
        'This is my first workspace for project management'
      );

      // Step 8: Verify workspace navigation in sidebar
      await expect(page.locator('[data-testid="sidebar-workspace-list"]')).toBeVisible();
      await expect(
        page.locator('[data-testid="sidebar-workspace-item"]').first()
      ).toContainText('My First Workspace');

      // Step 9: Verify initial board creation prompt
      await expect(page.locator('[data-testid="create-first-board"]')).toBeVisible();
      await expect(page.locator('[data-testid="board-creation-prompt"]')).toContainText(
        'Create your first board to start organizing your work'
      );
    });

    test('user can create multiple workspaces and switch between them', async ({ page }) => {
      // Pre-requisite: Login with existing user
      await loginAsTestUser(page);

      // Step 1: Navigate to workspace creation
      await page.click('[data-testid="sidebar-add-workspace"]');
      await expect(page.locator('[data-testid="workspace-creation-modal"]')).toBeVisible();

      // Step 2: Create first workspace
      await page.fill('[data-testid="workspace-name-input"]', 'Marketing Team');
      await page.fill('[data-testid="workspace-description-input"]', 'Workspace for marketing projects');
      await page.click('[data-testid="create-workspace-button"]');

      // Wait for creation and navigation
      await expect(page).toHaveURL(new RegExp(`${BASE_URL}/workspace/`));
      await expect(page.locator('[data-testid="workspace-title"]')).toContainText('Marketing Team');

      const marketingWorkspaceUrl = page.url();

      // Step 3: Create second workspace
      await page.click('[data-testid="sidebar-add-workspace"]');
      await page.fill('[data-testid="workspace-name-input"]', 'Development Team');
      await page.fill('[data-testid="workspace-description-input"]', 'Workspace for development projects');
      await page.click('[data-testid="create-workspace-button"]');

      await expect(page).toHaveURL(new RegExp(`${BASE_URL}/workspace/`));
      await expect(page.locator('[data-testid="workspace-title"]')).toContainText('Development Team');

      const developmentWorkspaceUrl = page.url();

      // Step 4: Verify both workspaces appear in sidebar
      const workspaceItems = page.locator('[data-testid="sidebar-workspace-item"]');
      await expect(workspaceItems).toHaveCount(2);

      // Step 5: Switch between workspaces
      await page.click('[data-testid="sidebar-workspace-item"]').first();
      await expect(page.locator('[data-testid="workspace-title"]')).toContainText('Marketing Team');

      await page.click('[data-testid="sidebar-workspace-item"]').nth(1);
      await expect(page.locator('[data-testid="workspace-title"]')).toContainText('Development Team');

      // Step 6: Verify workspace URLs are different
      expect(marketingWorkspaceUrl).not.toBe(developmentWorkspaceUrl);

      // Step 7: Verify workspace switching via dropdown menu
      await page.click('[data-testid="workspace-switcher-dropdown"]');
      await expect(page.locator('[data-testid="workspace-dropdown-menu"]')).toBeVisible();

      const dropdownItems = page.locator('[data-testid="workspace-dropdown-item"]');
      await expect(dropdownItems).toHaveCount(2);

      await dropdownItems.first().click();
      await expect(page.locator('[data-testid="workspace-title"]')).toContainText('Marketing Team');
    });
  });

  test.describe('Workspace Settings and Management', () => {
    test('workspace owner can update workspace settings', async ({ page }) => {
      // Pre-requisite: Login and create workspace
      await loginAsTestUser(page);
      const workspaceId = await createTestWorkspace(page, 'Settings Test Workspace');

      // Step 1: Navigate to workspace settings
      await page.click('[data-testid="workspace-settings-button"]');
      await expect(page.locator('[data-testid="workspace-settings-modal"]')).toBeVisible();

      // Step 2: Update workspace general settings
      await page.click('[data-testid="settings-tab-general"]');

      await page.fill('[data-testid="workspace-name-input"]', 'Updated Workspace Name');
      await page.fill(
        '[data-testid="workspace-description-input"]',
        'This workspace has been updated for testing'
      );

      // Step 3: Update workspace visibility
      await page.click('[data-testid="workspace-visibility-private"]');
      await expect(page.locator('[data-testid="workspace-visibility-private"]')).toBeChecked();

      // Step 4: Save changes
      await page.click('[data-testid="save-workspace-settings"]');

      // Verify success notification
      await expect(page.locator('[data-testid="settings-save-success"]')).toBeVisible();
      await expect(page.locator('[data-testid="settings-save-success"]')).toContainText(
        'Workspace settings updated successfully'
      );

      // Step 5: Close settings modal
      await page.click('[data-testid="settings-modal-close"]');

      // Step 6: Verify changes are reflected in UI
      await expect(page.locator('[data-testid="workspace-title"]')).toContainText('Updated Workspace Name');
      await expect(page.locator('[data-testid="workspace-description"]')).toContainText(
        'This workspace has been updated for testing'
      );

      // Step 7: Verify changes persist after page reload
      await page.reload();
      await expect(page.locator('[data-testid="workspace-title"]')).toContainText('Updated Workspace Name');
    });

    test('workspace owner can configure workspace permissions', async ({ page }) => {
      await loginAsTestUser(page);
      const workspaceId = await createTestWorkspace(page, 'Permissions Test Workspace');

      // Step 1: Open workspace settings
      await page.click('[data-testid="workspace-settings-button"]');
      await page.click('[data-testid="settings-tab-permissions"]');

      // Step 2: Configure member permissions
      await page.click('[data-testid="member-can-create-boards-toggle"]');
      await page.click('[data-testid="member-can-invite-users-toggle"]');

      // Step 3: Configure board permissions
      await page.selectOption('[data-testid="default-board-permission"]', 'edit');

      // Step 4: Configure workspace join settings
      await page.click('[data-testid="allow-domain-join-toggle"]');
      await page.fill('[data-testid="allowed-domains-input"]', 'example.com, company.com');

      // Step 5: Save permission changes
      await page.click('[data-testid="save-permission-settings"]');

      await expect(page.locator('[data-testid="permission-save-success"]')).toBeVisible();
    });
  });

  test.describe('Workspace Member Management', () => {
    test('workspace owner can invite and manage members', async ({ page }) => {
      await loginAsTestUser(page);
      const workspaceId = await createTestWorkspace(page, 'Team Management Workspace');

      // Step 1: Open member management
      await page.click('[data-testid="workspace-members-tab"]');
      await expect(page.locator('[data-testid="members-list"]')).toBeVisible();

      // Verify current user is listed as owner
      await expect(page.locator('[data-testid="member-role-owner"]')).toBeVisible();

      // Step 2: Invite new member
      await page.click('[data-testid="invite-member-button"]');
      await expect(page.locator('[data-testid="invite-member-modal"]')).toBeVisible();

      await page.fill('[data-testid="invite-email-input"]', 'newmember@example.com');
      await page.selectOption('[data-testid="invite-role-select"]', 'MEMBER');
      await page.fill('[data-testid="invite-message-input"]', 'Welcome to our workspace!');

      await page.click('[data-testid="send-invitation-button"]');

      // Step 3: Verify invitation sent
      await expect(page.locator('[data-testid="invitation-sent-success"]')).toBeVisible();
      await expect(page.locator('[data-testid="invitation-sent-success"]')).toContainText(
        'Invitation sent to newmember@example.com'
      );

      // Step 4: Verify pending invitation appears in list
      await expect(page.locator('[data-testid="pending-invitations"]')).toBeVisible();
      await expect(page.locator('[data-testid="pending-invitation-item"]')).toContainText(
        'newmember@example.com'
      );

      // Step 5: Invite multiple members at once
      await page.click('[data-testid="invite-member-button"]');
      await page.fill(
        '[data-testid="invite-email-input"]',
        'user1@example.com, user2@example.com, user3@example.com'
      );
      await page.selectOption('[data-testid="invite-role-select"]', 'MEMBER');
      await page.click('[data-testid="send-invitation-button"]');

      // Verify multiple invitations sent
      await expect(page.locator('[data-testid="invitation-sent-success"]')).toContainText(
        '3 invitations sent successfully'
      );

      // Step 6: Manage existing member (simulate accepted invitation)
      // First, add a mock member to the workspace via API
      await addMockMemberToWorkspace(page, workspaceId, 'existingmember@example.com', 'MEMBER');

      await page.reload();

      // Find the member in the list
      const memberRow = page.locator('[data-testid="member-row"]', {
        hasText: 'existingmember@example.com',
      });

      // Step 7: Change member role
      await memberRow.locator('[data-testid="member-actions-menu"]').click();
      await page.click('[data-testid="change-role-option"]');

      await page.selectOption('[data-testid="new-role-select"]', 'ADMIN');
      await page.click('[data-testid="confirm-role-change"]');

      await expect(page.locator('[data-testid="role-change-success"]')).toBeVisible();

      // Step 8: Remove member
      await memberRow.locator('[data-testid="member-actions-menu"]').click();
      await page.click('[data-testid="remove-member-option"]');

      // Confirm removal
      await expect(page.locator('[data-testid="remove-member-confirmation"]')).toBeVisible();
      await page.click('[data-testid="confirm-remove-member"]');

      await expect(page.locator('[data-testid="member-removed-success"]')).toBeVisible();

      // Verify member no longer appears in list
      await expect(
        page.locator('[data-testid="member-row"]', { hasText: 'existingmember@example.com' })
      ).toHaveCount(0);
    });

    test('workspace member can accept invitation and access workspace', async ({ page, context }) => {
      // Step 1: Create workspace as owner
      await loginAsTestUser(page);
      const workspaceId = await createTestWorkspace(page, 'Invitation Test Workspace');

      // Step 2: Invite new member
      await page.click('[data-testid="workspace-members-tab"]');
      await page.click('[data-testid="invite-member-button"]');
      await page.fill('[data-testid="invite-email-input"]', 'invitee@example.com');
      await page.selectOption('[data-testid="invite-role-select"]', 'MEMBER');
      await page.click('[data-testid="send-invitation-button"]');

      // Step 3: Create new browser context for invited user
      const inviteeContext = await context.browser().newContext();
      const inviteePage = await inviteeContext.newPage();

      // Step 4: Register invited user
      await inviteePage.goto(`${BASE_URL}/register`);
      await inviteePage.fill('[data-testid="first-name-input"]', 'Jane');
      await inviteePage.fill('[data-testid="last-name-input"]', 'Smith');
      await inviteePage.fill('[data-testid="email-input"]', 'invitee@example.com');
      await inviteePage.fill('[data-testid="password-input"]', 'SecurePassword123');
      await inviteePage.fill('[data-testid="confirm-password-input"]', 'SecurePassword123');
      await inviteePage.click('[data-testid="register-button"]');

      // Step 5: Login as invited user
      await inviteePage.goto(`${BASE_URL}/login`);
      await inviteePage.fill('[data-testid="email-input"]', 'invitee@example.com');
      await inviteePage.fill('[data-testid="password-input"]', 'SecurePassword123');
      await inviteePage.click('[data-testid="login-button"]');

      // Step 6: Verify pending workspace invitation notification
      await expect(inviteePage.locator('[data-testid="pending-invitations-notification"]')).toBeVisible();
      await expect(inviteePage.locator('[data-testid="invitation-count"]')).toContainText('1');

      // Step 7: View and accept invitation
      await inviteePage.click('[data-testid="pending-invitations-notification"]');
      await expect(inviteePage.locator('[data-testid="invitations-modal"]')).toBeVisible();

      const invitationItem = inviteePage.locator('[data-testid="invitation-item"]').first();
      await expect(invitationItem).toContainText('Invitation Test Workspace');
      await expect(invitationItem).toContainText('MEMBER');

      await invitationItem.locator('[data-testid="accept-invitation-button"]').click();

      // Step 8: Verify successful acceptance
      await expect(inviteePage.locator('[data-testid="invitation-accepted-success"]')).toBeVisible();
      await expect(inviteePage.locator('[data-testid="invitation-accepted-success"]')).toContainText(
        'Successfully joined Invitation Test Workspace'
      );

      // Step 9: Verify workspace appears in sidebar
      await expect(inviteePage.locator('[data-testid="sidebar-workspace-list"]')).toBeVisible();
      await expect(
        inviteePage.locator('[data-testid="sidebar-workspace-item"]', {
          hasText: 'Invitation Test Workspace',
        })
      ).toBeVisible();

      // Step 10: Navigate to workspace
      await inviteePage.click(
        '[data-testid="sidebar-workspace-item"]',
        { hasText: 'Invitation Test Workspace' }
      );

      await expect(inviteePage).toHaveURL(new RegExp(`${BASE_URL}/workspace/${workspaceId}`));
      await expect(inviteePage.locator('[data-testid="workspace-title"]')).toContainText(
        'Invitation Test Workspace'
      );

      // Step 11: Verify member permissions (should see workspace but not admin features)
      await expect(inviteePage.locator('[data-testid="workspace-content"]')).toBeVisible();
      await expect(inviteePage.locator('[data-testid="workspace-settings-button"]')).toHaveCount(0); // No admin access

      await inviteeContext.close();
    });
  });

  test.describe('Workspace and Board Integration', () => {
    test('user can create and manage boards within workspace', async ({ page }) => {
      await loginAsTestUser(page);
      const workspaceId = await createTestWorkspace(page, 'Board Integration Workspace');

      // Step 1: Create first board
      await page.click('[data-testid="create-board-button"]');
      await expect(page.locator('[data-testid="board-creation-modal"]')).toBeVisible();

      await page.fill('[data-testid="board-name-input"]', 'Sprint Planning Board');
      await page.fill('[data-testid="board-description-input"]', 'Board for sprint planning activities');
      await page.selectOption('[data-testid="board-template-select"]', 'scrum');

      await page.click('[data-testid="create-board-button"]');

      // Step 2: Verify board creation and navigation
      await expect(page).toHaveURL(new RegExp(`${BASE_URL}/board/`));
      await expect(page.locator('[data-testid="board-title"]')).toContainText('Sprint Planning Board');

      // Step 3: Navigate back to workspace
      await page.click('[data-testid="breadcrumb-workspace"]');
      await expect(page).toHaveURL(new RegExp(`${BASE_URL}/workspace/${workspaceId}`));

      // Step 4: Verify board appears in workspace board list
      await expect(page.locator('[data-testid="workspace-boards-list"]')).toBeVisible();
      await expect(
        page.locator('[data-testid="board-card"]', { hasText: 'Sprint Planning Board' })
      ).toBeVisible();

      // Step 5: Create multiple boards
      const boardNames = ['Backlog Management', 'Bug Tracking', 'Feature Development'];

      for (const boardName of boardNames) {
        await page.click('[data-testid="create-board-button"]');
        await page.fill('[data-testid="board-name-input"]', boardName);
        await page.selectOption('[data-testid="board-template-select"]', 'kanban');
        await page.click('[data-testid="create-board-button"]');

        // Navigate back to workspace
        await page.click('[data-testid="breadcrumb-workspace"]');
      }

      // Step 6: Verify all boards appear in workspace
      const boardCards = page.locator('[data-testid="board-card"]');
      await expect(boardCards).toHaveCount(4); // Including the first board

      // Step 7: Filter and search boards
      await page.fill('[data-testid="board-search-input"]', 'Sprint');
      await expect(
        page.locator('[data-testid="board-card"]', { hasText: 'Sprint Planning Board' })
      ).toBeVisible();
      await expect(boardCards).toHaveCount(1);

      // Clear search
      await page.fill('[data-testid="board-search-input"]', '');
      await expect(boardCards).toHaveCount(4);

      // Step 8: Sort boards
      await page.selectOption('[data-testid="board-sort-select"]', 'name-asc');

      const sortedBoardTitles = await page.locator('[data-testid="board-card-title"]').allTextContents();
      expect(sortedBoardTitles).toEqual([
        'Backlog Management',
        'Bug Tracking',
        'Feature Development',
        'Sprint Planning Board'
      ].sort());
    });
  });

  test.describe('Workspace Deletion and Data Management', () => {
    test('workspace owner can delete workspace with confirmation', async ({ page }) => {
      await loginAsTestUser(page);
      const workspaceId = await createTestWorkspace(page, 'Deletion Test Workspace');

      // Create some boards to verify cascading deletion
      await createTestBoard(page, 'Test Board 1');
      await createTestBoard(page, 'Test Board 2');

      // Navigate back to workspace
      await page.click('[data-testid="breadcrumb-workspace"]');

      // Step 1: Attempt to delete workspace
      await page.click('[data-testid="workspace-settings-button"]');
      await page.click('[data-testid="settings-tab-danger"]');

      await expect(page.locator('[data-testid="danger-zone"]')).toBeVisible();
      await page.click('[data-testid="delete-workspace-button"]');

      // Step 2: Verify deletion confirmation modal
      await expect(page.locator('[data-testid="delete-confirmation-modal"]')).toBeVisible();
      await expect(page.locator('[data-testid="deletion-warning"]')).toContainText(
        'This action cannot be undone. All boards and data will be permanently deleted.'
      );

      // Step 3: Verify workspace name confirmation required
      await page.fill('[data-testid="confirmation-workspace-name"]', 'Wrong Name');
      await expect(page.locator('[data-testid="confirm-delete-button"]')).toBeDisabled();

      await page.fill('[data-testid="confirmation-workspace-name"]', 'Deletion Test Workspace');
      await expect(page.locator('[data-testid="confirm-delete-button"]')).toBeEnabled();

      // Step 4: Complete deletion
      await page.click('[data-testid="confirm-delete-button"]');

      // Step 5: Verify deletion success and redirection
      await expect(page.locator('[data-testid="workspace-deleted-success"]')).toBeVisible();
      await expect(page).toHaveURL(new RegExp(`${BASE_URL}/dashboard`));

      // Step 6: Verify workspace no longer appears in sidebar
      await expect(
        page.locator('[data-testid="sidebar-workspace-item"]', {
          hasText: 'Deletion Test Workspace',
        })
      ).toHaveCount(0);

      // Step 7: Verify direct access to workspace URL returns 404
      await page.goto(`${BASE_URL}/workspace/${workspaceId}`);
      await expect(page.locator('[data-testid="workspace-not-found"]')).toBeVisible();
    });
  });
});

// Helper functions
async function loginAsTestUser(page) {
  const userData = {
    email: 'testuser@example.com',
    password: 'SecurePassword123',
  };

  // Register user if not exists (ignore errors if already exists)
  try {
    await page.goto(`${BASE_URL}/register`);
    await page.fill('[data-testid="first-name-input"]', 'Test');
    await page.fill('[data-testid="last-name-input"]', 'User');
    await page.fill('[data-testid="email-input"]', userData.email);
    await page.fill('[data-testid="password-input"]', userData.password);
    await page.fill('[data-testid="confirm-password-input"]', userData.password);
    await page.click('[data-testid="register-button"]');
  } catch (error) {
    // User might already exist, continue to login
  }

  // Login
  await page.goto(`${BASE_URL}/login`);
  await page.fill('[data-testid="email-input"]', userData.email);
  await page.fill('[data-testid="password-input"]', userData.password);
  await page.click('[data-testid="login-button"]');

  await expect(page).toHaveURL(new RegExp(`${BASE_URL}/dashboard`));
}

async function createTestWorkspace(page, workspaceName) {
  await page.click('[data-testid="create-workspace-button"]');
  await page.fill('[data-testid="workspace-name-input"]', workspaceName);
  await page.fill('[data-testid="workspace-description-input"]', `Description for ${workspaceName}`);
  await page.click('[data-testid="create-workspace-button"]');

  await expect(page).toHaveURL(new RegExp(`${BASE_URL}/workspace/`));

  // Extract workspace ID from URL
  const url = page.url();
  const workspaceId = url.split('/workspace/')[1];
  return workspaceId;
}

async function createTestBoard(page, boardName) {
  await page.click('[data-testid="create-board-button"]');
  await page.fill('[data-testid="board-name-input"]', boardName);
  await page.selectOption('[data-testid="board-template-select"]', 'kanban');
  await page.click('[data-testid="create-board-button"]');

  await expect(page).toHaveURL(new RegExp(`${BASE_URL}/board/`));
}

async function addMockMemberToWorkspace(page, workspaceId, email, role) {
  // This would typically make an API call to add a member
  // For testing purposes, we'll simulate this
  await page.evaluate(
    ({ workspaceId, email, role }) => {
      // Mock API call to add member
      fetch(`${API_BASE_URL}/api/workspaces/${workspaceId}/members`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('authToken')}`,
        },
        body: JSON.stringify({ email, role }),
      });
    },
    { workspaceId, email, role }
  );
}