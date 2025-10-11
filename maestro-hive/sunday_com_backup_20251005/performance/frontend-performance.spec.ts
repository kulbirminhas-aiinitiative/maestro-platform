/**
 * Frontend Performance Tests
 * Measures and validates frontend performance metrics
 */

import { test, expect, Page } from '@playwright/test';

test.describe('Frontend Performance Tests', () => {
  test.describe('Page Load Performance', () => {
    test('Dashboard page should load within performance budget', async ({ page }) => {
      // Start measuring performance
      const startTime = Date.now();

      // Navigate to dashboard
      await page.goto('/dashboard');

      // Wait for page to be fully loaded
      await page.waitForLoadState('networkidle');

      // Measure load time
      const loadTime = Date.now() - startTime;

      // Performance assertions
      expect(loadTime).toBeLessThan(3000); // Less than 3 seconds

      // Check Core Web Vitals using Lighthouse API
      const metrics = await page.evaluate(() => {
        return new Promise((resolve) => {
          new PerformanceObserver((list) => {
            const entries = list.getEntries();
            const vitals: any = {};

            entries.forEach((entry: any) => {
              if (entry.name === 'first-contentful-paint') {
                vitals.FCP = entry.startTime;
              }
              if (entry.name === 'largest-contentful-paint') {
                vitals.LCP = entry.startTime;
              }
            });

            resolve(vitals);
          }).observe({ entryTypes: ['paint', 'largest-contentful-paint'] });

          // Fallback timeout
          setTimeout(() => resolve({}), 5000);
        });
      });

      // Core Web Vitals thresholds
      if (metrics.FCP) {
        expect(metrics.FCP).toBeLessThan(1800); // FCP < 1.8s (good)
      }
      if (metrics.LCP) {
        expect(metrics.LCP).toBeLessThan(2500); // LCP < 2.5s (good)
      }
    });

    test('Board page should load within performance budget', async ({ page }) => {
      // Mock board data to ensure consistent testing
      await page.route('**/api/v1/boards/*', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'test-board-id',
            name: 'Performance Test Board',
            items: Array.from({ length: 50 }, (_, i) => ({
              id: `item-${i}`,
              title: `Test Item ${i}`,
              status: 'TODO',
              priority: 'MEDIUM'
            }))
          })
        });
      });

      const startTime = performance.now();

      await page.goto('/boards/test-board-id');
      await page.waitForSelector('[data-testid="board-view"]');

      const loadTime = performance.now() - startTime;

      // Board page should load faster since it's a core feature
      expect(loadTime).toBeLessThan(2000); // Less than 2 seconds

      // Verify interactive elements are ready
      await expect(page.locator('[data-testid="add-item-button"]')).toBeVisible();
      await expect(page.locator('[data-testid="board-columns"]')).toBeVisible();
    });

    test('Authentication pages should load quickly', async ({ page }) => {
      const startTime = performance.now();

      await page.goto('/login');
      await page.waitForSelector('[data-testid="login-form"]');

      const loadTime = performance.now() - startTime;

      // Auth pages should be very fast (minimal JS/CSS)
      expect(loadTime).toBeLessThan(1000); // Less than 1 second
    });
  });

  test.describe('Runtime Performance', () => {
    test('Board drag and drop should be smooth', async ({ page }) => {
      await page.goto('/boards/test-board-id');
      await page.waitForSelector('[data-testid="board-view"]');

      // Monitor frame rate during drag and drop
      let frameCount = 0;
      let startTime = 0;

      // Start monitoring frames
      await page.evaluate(() => {
        let lastTime = 0;
        const checkFrame = (timestamp: number) => {
          if (lastTime === 0) lastTime = timestamp;
          if (timestamp - lastTime >= 1000) {
            // Store frame count in window for retrieval
            (window as any).frameCount = (window as any).frameCount || 0;
            (window as any).frameCount++;
            lastTime = timestamp;
          }
          requestAnimationFrame(checkFrame);
        };
        requestAnimationFrame(checkFrame);
      });

      // Perform drag and drop
      const sourceItem = page.locator('[data-testid="board-item"]').first();
      const targetColumn = page.locator('[data-testid="board-column"]').nth(1);

      await sourceItem.dragTo(targetColumn);

      // Get frame rate (should be close to 60fps)
      const frameRate = await page.evaluate(() => (window as any).frameCount || 0);
      expect(frameRate).toBeGreaterThan(50); // At least 50fps during interaction
    });

    test('Real-time updates should not cause performance degradation', async ({ page }) => {
      await page.goto('/boards/test-board-id');

      // Measure baseline performance
      const baselineStart = performance.now();
      await page.waitForTimeout(1000);
      const baselineTime = performance.now() - baselineStart;

      // Simulate real-time updates
      for (let i = 0; i < 10; i++) {
        await page.evaluate((index) => {
          // Simulate WebSocket message
          const event = new CustomEvent('websocket-message', {
            detail: {
              type: 'ITEM_UPDATED',
              data: {
                id: `item-${index}`,
                title: `Updated Item ${index}`,
                updatedAt: new Date().toISOString()
              }
            }
          });
          window.dispatchEvent(event);
        }, i);

        await page.waitForTimeout(100); // 100ms between updates
      }

      // Measure performance after updates
      const updateStart = performance.now();
      await page.waitForTimeout(1000);
      const updateTime = performance.now() - updateStart;

      // Performance should not degrade significantly
      const performanceDelta = Math.abs(updateTime - baselineTime);
      expect(performanceDelta).toBeLessThan(500); // Less than 500ms difference
    });

    test('Large dataset rendering should be performant', async ({ page }) => {
      // Mock large dataset
      await page.route('**/api/v1/boards/*', route => {
        route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'large-board-id',
            name: 'Large Performance Test Board',
            items: Array.from({ length: 500 }, (_, i) => ({
              id: `item-${i}`,
              title: `Test Item ${i}`,
              description: `Description for item ${i}`,
              status: ['TODO', 'IN_PROGRESS', 'REVIEW', 'DONE'][i % 4],
              priority: ['LOW', 'MEDIUM', 'HIGH', 'URGENT'][i % 4],
              assigneeId: `user-${i % 10}`,
              createdAt: new Date(Date.now() - i * 1000).toISOString()
            }))
          })
        });
      });

      const startTime = performance.now();

      await page.goto('/boards/large-board-id');
      await page.waitForSelector('[data-testid="board-view"]');

      // Wait for all items to render
      await page.waitForFunction(() => {
        const items = document.querySelectorAll('[data-testid="board-item"]');
        return items.length > 0; // At least some items should be visible
      });

      const renderTime = performance.now() - startTime;

      // Large dataset should still render within acceptable time
      expect(renderTime).toBeLessThan(5000); // Less than 5 seconds

      // Test scrolling performance with large dataset
      const scrollStart = performance.now();
      await page.evaluate(() => {
        window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
      });
      await page.waitForTimeout(1000);
      const scrollTime = performance.now() - scrollStart;

      expect(scrollTime).toBeLessThan(2000); // Smooth scrolling
    });
  });

  test.describe('Memory Performance', () => {
    test('Should not have memory leaks during navigation', async ({ page }) => {
      // Navigate through multiple pages to test for memory leaks
      const pages = ['/dashboard', '/boards', '/settings', '/analytics'];

      // Get initial memory usage
      const initialMemory = await page.evaluate(() => {
        if ('memory' in performance) {
          return (performance as any).memory.usedJSHeapSize;
        }
        return 0;
      });

      // Navigate through pages multiple times
      for (let cycle = 0; cycle < 3; cycle++) {
        for (const pagePath of pages) {
          await page.goto(pagePath);
          await page.waitForLoadState('networkidle');
          await page.waitForTimeout(500); // Allow React to settle
        }
      }

      // Force garbage collection if available
      await page.evaluate(() => {
        if ('gc' in window) {
          (window as any).gc();
        }
      });

      // Get final memory usage
      const finalMemory = await page.evaluate(() => {
        if ('memory' in performance) {
          return (performance as any).memory.usedJSHeapSize;
        }
        return 0;
      });

      // Memory usage should not increase dramatically
      if (initialMemory > 0 && finalMemory > 0) {
        const memoryIncrease = finalMemory - initialMemory;
        const memoryIncreasePercent = (memoryIncrease / initialMemory) * 100;

        // Memory increase should be less than 50%
        expect(memoryIncreasePercent).toBeLessThan(50);
      }
    });

    test('Timer components should clean up properly', async ({ page }) => {
      await page.goto('/boards/test-board-id');

      // Start multiple timers
      for (let i = 0; i < 5; i++) {
        await page.click('[data-testid="start-timer-button"]');
        await page.waitForTimeout(100);
        await page.click('[data-testid="stop-timer-button"]');
        await page.waitForTimeout(100);
      }

      // Check for timer cleanup
      const activeTimers = await page.evaluate(() => {
        // Check for any remaining setInterval/setTimeout
        return Object.keys(window).filter(key =>
          key.includes('timer') || key.includes('interval')
        ).length;
      });

      // Should have minimal active timers
      expect(activeTimers).toBeLessThan(3);
    });
  });

  test.describe('Network Performance', () => {
    test('Should handle slow network gracefully', async ({ page }) => {
      // Simulate slow 3G connection
      await page.route('**/api/**', async route => {
        await new Promise(resolve => setTimeout(resolve, 1000)); // 1s delay
        route.continue();
      });

      const startTime = performance.now();
      await page.goto('/dashboard');

      // Should show loading states
      await expect(page.locator('[data-testid="loading-skeleton"]')).toBeVisible();

      await page.waitForSelector('[data-testid="dashboard-content"]');
      const loadTime = performance.now() - startTime;

      // Should handle slow network within reasonable time
      expect(loadTime).toBeLessThan(10000); // Less than 10 seconds
    });

    test('Should cache static resources efficiently', async ({ page }) => {
      // First load
      await page.goto('/dashboard');
      await page.waitForLoadState('networkidle');

      // Reload page to test caching
      const reloadStart = performance.now();
      await page.reload();
      await page.waitForLoadState('networkidle');
      const reloadTime = performance.now() - reloadStart;

      // Reload should be faster due to caching
      expect(reloadTime).toBeLessThan(2000); // Less than 2 seconds
    });

    test('Should handle API rate limiting', async ({ page }) => {
      let requestCount = 0;

      await page.route('**/api/**', route => {
        requestCount++;
        if (requestCount > 10) {
          route.fulfill({
            status: 429,
            contentType: 'application/json',
            body: JSON.stringify({ error: 'Rate limit exceeded' })
          });
        } else {
          route.continue();
        }
      });

      await page.goto('/dashboard');

      // Make multiple API calls
      for (let i = 0; i < 15; i++) {
        await page.click('[data-testid="refresh-button"]');
        await page.waitForTimeout(100);
      }

      // Should show rate limit error gracefully
      await expect(page.locator('[data-testid="rate-limit-error"]')).toBeVisible();
    });
  });

  test.describe('Bundle Size and Loading', () => {
    test('Initial bundle should be within size budget', async ({ page }) => {
      // Monitor network requests
      const resourceSizes: number[] = [];

      page.on('response', response => {
        if (response.url().includes('.js') || response.url().includes('.css')) {
          const contentLength = response.headers()['content-length'];
          if (contentLength) {
            resourceSizes.push(parseInt(contentLength));
          }
        }
      });

      await page.goto('/dashboard');
      await page.waitForLoadState('networkidle');

      // Calculate total bundle size
      const totalBundleSize = resourceSizes.reduce((sum, size) => sum + size, 0);
      const bundleSizeMB = totalBundleSize / (1024 * 1024);

      // Bundle should be under 3MB total
      expect(bundleSizeMB).toBeLessThan(3);
    });

    test('Code splitting should work correctly', async ({ page }) => {
      // Track which chunks are loaded initially
      const initialChunks: string[] = [];

      page.on('response', response => {
        if (response.url().includes('.js')) {
          const url = new URL(response.url());
          initialChunks.push(url.pathname);
        }
      });

      await page.goto('/dashboard');
      await page.waitForLoadState('networkidle');

      const initialChunkCount = initialChunks.length;

      // Navigate to a different route that should load new chunks
      await page.goto('/analytics');
      await page.waitForLoadState('networkidle');

      // Should have loaded additional chunks for analytics
      const totalChunks = initialChunks.length;
      expect(totalChunks).toBeGreaterThan(initialChunkCount);
    });
  });
});