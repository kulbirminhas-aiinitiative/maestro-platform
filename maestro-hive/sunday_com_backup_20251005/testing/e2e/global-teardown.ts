import { DatabaseHelper } from './helpers/database-helper';

/**
 * Global teardown for Playwright tests
 * This runs once after all tests across all workers
 */
async function globalTeardown() {
  console.log('🧹 Starting global teardown for E2E tests...');

  try {
    // 1. Clean up test data
    console.log('🗑️ Cleaning up test data...');
    await DatabaseHelper.cleanupTestData();

    // 2. Close database connections
    console.log('🔌 Closing database connections...');
    await DatabaseHelper.closeConnections();

    // 3. Generate test reports
    console.log('📊 Generating test reports...');
    // Additional report generation logic can go here

    console.log('✅ Global teardown completed successfully');

  } catch (error) {
    console.error('❌ Global teardown failed:', error);
    // Don't throw error to avoid masking test failures
  }
}

export default globalTeardown;