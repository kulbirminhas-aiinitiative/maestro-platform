import { test as setup, expect } from '@playwright/test';

/**
 * Authentication Setup for E2E Tests
 * QA Engineer: Test Authentication Helper
 */

const authFile = 'auth.json';

setup('authenticate', async ({ page }) => {
  // Navigate to login page
  await page.goto('/login');

  // Wait for login form to be visible
  await page.waitForSelector('[data-testid="login-form"]');

  // Fill in credentials
  await page.fill('[data-testid="email-input"]', 'test@sunday.com');
  await page.fill('[data-testid="password-input"]', 'TestPassword123!');

  // Click login button
  await page.click('[data-testid="login-button"]');

  // Wait for successful login
  await page.waitForURL('/dashboard');

  // Verify user is logged in
  await expect(page.locator('[data-testid="user-avatar"]')).toBeVisible();

  // Save authentication state
  await page.context().storageState({ path: authFile });
});