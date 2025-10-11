import { chromium, FullConfig } from '@playwright/test';
import { ApiHelper } from './helpers/api-helper';
import { DatabaseHelper } from './helpers/database-helper';

/**
 * Global setup for Playwright tests
 * This runs once before all tests across all workers
 */
async function globalSetup(config: FullConfig) {
  console.log('🚀 Starting global setup for E2E tests...');

  const baseURL = config.projects[0].use?.baseURL || 'http://localhost:3000';
  const apiURL = process.env.E2E_API_URL || 'http://localhost:4000';

  try {
    // 1. Setup test database
    console.log('📊 Setting up test database...');
    await DatabaseHelper.setupTestDatabase();

    // 2. Create test users and organizations
    console.log('👤 Creating test users and organizations...');
    await DatabaseHelper.seedTestData();

    // 3. Verify API is running
    console.log('🔗 Verifying API connection...');
    await ApiHelper.waitForAPI(apiURL, 30000);

    // 4. Verify frontend is running
    console.log('🌐 Verifying frontend connection...');
    const browser = await chromium.launch();
    const page = await browser.newPage();

    try {
      await page.goto(baseURL, {
        waitUntil: 'networkidle',
        timeout: 30000
      });
      console.log('✅ Frontend is accessible');
    } catch (error) {
      console.error('❌ Frontend is not accessible:', error);
      throw error;
    } finally {
      await browser.close();
    }

    // 5. Run pre-test health checks
    console.log('🏥 Running health checks...');
    await ApiHelper.healthCheck(apiURL);

    console.log('✅ Global setup completed successfully');

  } catch (error) {
    console.error('❌ Global setup failed:', error);
    throw error;
  }
}

export default globalSetup;