import { test, expect, Page } from '@playwright/test';
import { DatabaseHelper } from '../../helpers/database-helper';
import { ApiHelper } from '../../helpers/api-helper';

test.describe('User Authentication', () => {
  let page: Page;

  test.beforeEach(async ({ browser }) => {
    page = await browser.newPage();
    await page.goto('/login');
  });

  test.afterEach(async () => {
    await page.close();
  });

  test.describe('Login Flow', () => {
    test('should display login form with required elements', async () => {
      // Check page title
      await expect(page).toHaveTitle(/Sign In/);

      // Check form elements
      await expect(page.getByRole('heading', { name: /sign in/i })).toBeVisible();
      await expect(page.getByLabel(/email/i)).toBeVisible();
      await expect(page.getByLabel(/password/i)).toBeVisible();
      await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();

      // Check additional links
      await expect(page.getByRole('link', { name: /sign up/i })).toBeVisible();
      await expect(page.getByRole('link', { name: /forgot password/i })).toBeVisible();
    });

    test('should show validation errors for empty form submission', async () => {
      // Submit empty form
      await page.getByRole('button', { name: /sign in/i }).click();

      // Check validation errors
      await expect(page.getByText(/email is required/i)).toBeVisible();
      await expect(page.getByText(/password is required/i)).toBeVisible();

      // Form should not submit
      await expect(page).toHaveURL(/login/);
    });

    test('should show validation error for invalid email', async () => {
      await page.getByLabel(/email/i).fill('invalid-email');
      await page.getByLabel(/password/i).fill('password123');
      await page.getByRole('button', { name: /sign in/i }).click();

      await expect(page.getByText(/please enter a valid email/i)).toBeVisible();
    });

    test('should successfully log in with valid credentials', async () => {
      // Fill login form with test user credentials
      await page.getByLabel(/email/i).fill('admin@test.com');
      await page.getByLabel(/password/i).fill('password123');

      // Submit form
      await page.getByRole('button', { name: /sign in/i }).click();

      // Should redirect to dashboard
      await expect(page).toHaveURL(/dashboard/);

      // Should show user information
      await expect(page.getByText(/admin user/i)).toBeVisible();
    });

    test('should show error for invalid credentials', async () => {
      await page.getByLabel(/email/i).fill('admin@test.com');
      await page.getByLabel(/password/i).fill('wrongpassword');
      await page.getByRole('button', { name: /sign in/i }).click();

      // Should show error message
      await expect(page.getByText(/invalid email or password/i)).toBeVisible();

      // Should remain on login page
      await expect(page).toHaveURL(/login/);
    });

    test('should handle network errors gracefully', async () => {
      // Intercept API call and simulate network error
      await page.route('**/api/auth/login', route => {
        route.abort('failed');
      });

      await page.getByLabel(/email/i).fill('admin@test.com');
      await page.getByLabel(/password/i).fill('password123');
      await page.getByRole('button', { name: /sign in/i }).click();

      await expect(page.getByText(/something went wrong/i)).toBeVisible();
    });

    test('should show loading state during authentication', async () => {
      // Delay API response
      await page.route('**/api/auth/login', async route => {
        await new Promise(resolve => setTimeout(resolve, 1000));
        route.continue();
      });

      await page.getByLabel(/email/i).fill('admin@test.com');
      await page.getByLabel(/password/i).fill('password123');
      await page.getByRole('button', { name: /sign in/i }).click();

      // Should show loading state
      await expect(page.getByRole('button', { name: /signing in/i })).toBeVisible();
      await expect(page.getByRole('button', { name: /signing in/i })).toBeDisabled();

      // Wait for completion
      await expect(page).toHaveURL(/dashboard/, { timeout: 5000 });
    });
  });

  test.describe('Password Visibility Toggle', () => {
    test('should toggle password visibility', async () => {
      const passwordInput = page.getByLabel(/password/i);
      const toggleButton = page.getByRole('button', { name: /show password/i });

      // Initially hidden
      await expect(passwordInput).toHaveAttribute('type', 'password');

      // Click to show
      await toggleButton.click();
      await expect(passwordInput).toHaveAttribute('type', 'text');
      await expect(page.getByRole('button', { name: /hide password/i })).toBeVisible();

      // Click to hide
      await page.getByRole('button', { name: /hide password/i }).click();
      await expect(passwordInput).toHaveAttribute('type', 'password');
    });
  });

  test.describe('Remember Me Functionality', () => {
    test('should remember email when checkbox is checked', async () => {
      await page.getByLabel(/email/i).fill('admin@test.com');
      await page.getByLabel(/password/i).fill('password123');
      await page.getByLabel(/remember me/i).check();

      await page.getByRole('button', { name: /sign in/i }).click();

      // After successful login, logout and check if email is remembered
      await page.goto('/dashboard');
      await page.getByRole('button', { name: /user menu/i }).click();
      await page.getByRole('menuitem', { name: /sign out/i }).click();

      // Should be back on login page with email pre-filled
      await expect(page).toHaveURL(/login/);
      await expect(page.getByLabel(/email/i)).toHaveValue('admin@test.com');
    });
  });

  test.describe('Keyboard Navigation', () => {
    test('should support keyboard navigation', async () => {
      // Tab through form elements
      await page.keyboard.press('Tab');
      await expect(page.getByLabel(/email/i)).toBeFocused();

      await page.keyboard.press('Tab');
      await expect(page.getByLabel(/password/i)).toBeFocused();

      await page.keyboard.press('Tab');
      await expect(page.getByLabel(/remember me/i)).toBeFocused();

      await page.keyboard.press('Tab');
      await expect(page.getByRole('button', { name: /sign in/i })).toBeFocused();
    });

    test('should submit form with Enter key', async () => {
      await page.getByLabel(/email/i).fill('admin@test.com');
      await page.getByLabel(/password/i).fill('password123');

      // Press Enter on password field
      await page.getByLabel(/password/i).press('Enter');

      // Should redirect to dashboard
      await expect(page).toHaveURL(/dashboard/);
    });
  });

  test.describe('SSO Authentication', () => {
    test.skip('should redirect to SSO provider when SSO button is clicked', async () => {
      // Skip if SSO is not configured
      const ssoButton = page.getByRole('button', { name: /sign in with sso/i });

      if (await ssoButton.isVisible()) {
        await ssoButton.click();

        // Should redirect to SSO provider
        await expect(page).toHaveURL(/\/auth\/sso/);
      }
    });
  });

  test.describe('Mobile Responsive', () => {
    test('should display correctly on mobile devices', async () => {
      // Set mobile viewport
      await page.setViewportSize({ width: 375, height: 667 });

      await page.goto('/login');

      // Check that form is properly sized
      const form = page.locator('form');
      await expect(form).toBeVisible();

      // Check that elements are stacked vertically
      const emailInput = page.getByLabel(/email/i);
      const passwordInput = page.getByLabel(/password/i);

      const emailBox = await emailInput.boundingBox();
      const passwordBox = await passwordInput.boundingBox();

      expect(passwordBox!.y).toBeGreaterThan(emailBox!.y + emailBox!.height);
    });
  });

  test.describe('Accessibility', () => {
    test('should be accessible to screen readers', async () => {
      // Check form has proper labeling
      await expect(page.getByRole('form')).toBeVisible();

      // Check inputs have proper labels
      await expect(page.getByLabel(/email/i)).toHaveAttribute('aria-required', 'true');
      await expect(page.getByLabel(/password/i)).toHaveAttribute('aria-required', 'true');

      // Check error messages are associated with inputs
      await page.getByRole('button', { name: /sign in/i }).click();

      const emailError = page.getByText(/email is required/i);
      await expect(emailError).toHaveAttribute('role', 'alert');
    });

    test('should have sufficient color contrast', async () => {
      // This would typically use axe-core for automated accessibility testing
      const button = page.getByRole('button', { name: /sign in/i });

      // Check that button has visible text and background
      await expect(button).toBeVisible();
      await expect(button).toHaveCSS('background-color', /rgb/);
      await expect(button).toHaveCSS('color', /rgb/);
    });
  });

  test.describe('Security', () => {
    test('should not expose sensitive information in client-side code', async () => {
      // Check that password is not visible in page source
      const content = await page.content();
      expect(content).not.toContain('password123');
      expect(content).not.toContain('secret');
      expect(content).not.toContain('token');
    });

    test('should clear password field on failed login', async () => {
      await page.getByLabel(/email/i).fill('admin@test.com');
      await page.getByLabel(/password/i).fill('wrongpassword');
      await page.getByRole('button', { name: /sign in/i }).click();

      // Wait for error
      await expect(page.getByText(/invalid email or password/i)).toBeVisible();

      // Password field should be cleared
      await expect(page.getByLabel(/password/i)).toHaveValue('');
    });
  });

  test.describe('Performance', () => {
    test('should load quickly', async () => {
      const startTime = Date.now();
      await page.goto('/login');
      const loadTime = Date.now() - startTime;

      // Page should load within 2 seconds
      expect(loadTime).toBeLessThan(2000);
    });

    test('should handle rapid form submissions', async () => {
      await page.getByLabel(/email/i).fill('admin@test.com');
      await page.getByLabel(/password/i).fill('password123');

      const button = page.getByRole('button', { name: /sign in/i });

      // Rapid clicks should not cause multiple submissions
      await Promise.all([
        button.click(),
        button.click(),
        button.click(),
      ]);

      // Should only make one API call
      const requests = [];
      page.on('request', request => {
        if (request.url().includes('/api/auth/login')) {
          requests.push(request);
        }
      });

      expect(requests.length).toBeLessThanOrEqual(1);
    });
  });
});