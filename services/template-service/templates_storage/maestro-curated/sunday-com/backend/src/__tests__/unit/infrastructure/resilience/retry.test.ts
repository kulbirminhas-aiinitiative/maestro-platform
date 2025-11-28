/**
 * Retry with Exponential Backoff Tests
 */

import { withRetry, withRetryAndJitter, defaultRetryConfigs } from '../../../../infrastructure/resilience/retry';

describe('withRetry', () => {
  it('should succeed on first attempt', async () => {
    const operation = jest.fn().mockResolvedValue('success');

    const result = await withRetry(operation, {
      maxRetries: 3,
      initialDelay: 100,
      maxDelay: 1000,
      backoffMultiplier: 2
    });

    expect(result).toBe('success');
    expect(operation).toHaveBeenCalledTimes(1);
  });

  it('should retry on failure and eventually succeed', async () => {
    const operation = jest
      .fn()
      .mockRejectedValueOnce(new Error('fail1'))
      .mockRejectedValueOnce(new Error('fail2'))
      .mockResolvedValue('success');

    const result = await withRetry(operation, {
      maxRetries: 3,
      initialDelay: 10,
      maxDelay: 1000,
      backoffMultiplier: 2
    });

    expect(result).toBe('success');
    expect(operation).toHaveBeenCalledTimes(3);
  });

  it('should throw after max retries exceeded', async () => {
    const operation = jest.fn().mockRejectedValue(new Error('persistent failure'));

    await expect(
      withRetry(operation, {
        maxRetries: 2,
        initialDelay: 10,
        maxDelay: 1000,
        backoffMultiplier: 2
      })
    ).rejects.toThrow(/Max retries \(2\) exceeded/);

    expect(operation).toHaveBeenCalledTimes(3); // initial + 2 retries
  });

  it('should respect retryable errors', async () => {
    const error = new Error('ECONNREFUSED');

    const operation = jest.fn().mockRejectedValue(error);

    await expect(
      withRetry(operation, {
        maxRetries: 2,
        initialDelay: 10,
        maxDelay: 1000,
        backoffMultiplier: 2,
        retryableErrors: ['ECONNREFUSED']
      })
    ).rejects.toThrow(/Max retries/);

    expect(operation).toHaveBeenCalledTimes(3);
  });

  it('should not retry non-retryable errors', async () => {
    const error = new Error('ValidationError');

    const operation = jest.fn().mockRejectedValue(error);

    await expect(
      withRetry(operation, {
        maxRetries: 2,
        initialDelay: 10,
        maxDelay: 1000,
        backoffMultiplier: 2,
        retryableErrors: ['ECONNREFUSED']
      })
    ).rejects.toThrow(/Non-retryable error/);

    expect(operation).toHaveBeenCalledTimes(1); // Only initial attempt
  });

  it('should use exponential backoff', async () => {
    const operation = jest
      .fn()
      .mockRejectedValueOnce(new Error('fail1'))
      .mockRejectedValueOnce(new Error('fail2'))
      .mockResolvedValue('success');

    const startTime = Date.now();

    await withRetry(operation, {
      maxRetries: 2,
      initialDelay: 100,
      maxDelay: 1000,
      backoffMultiplier: 2
    });

    const duration = Date.now() - startTime;

    // First retry: 100ms, Second retry: 200ms
    // Total should be at least 300ms
    expect(duration).toBeGreaterThanOrEqual(280); // Allow some variance
  });

  it('should cap delay at maxDelay', async () => {
    const operation = jest
      .fn()
      .mockRejectedValueOnce(new Error('fail1'))
      .mockRejectedValueOnce(new Error('fail2'))
      .mockResolvedValue('success');

    const startTime = Date.now();

    await withRetry(operation, {
      maxRetries: 2,
      initialDelay: 500,
      maxDelay: 600,
      backoffMultiplier: 4
    });

    const duration = Date.now() - startTime;

    // First retry: 500ms, Second retry: 600ms (capped from 2000ms)
    // Total should be around 1100ms, not 2500ms
    expect(duration).toBeGreaterThanOrEqual(1000);
    expect(duration).toBeLessThan(1500);
  });
});

describe('withRetryAndJitter', () => {
  it('should add jitter to initial delay', async () => {
    const operation = jest
      .fn()
      .mockRejectedValueOnce(new Error('fail'))
      .mockResolvedValue('success');

    // Run multiple times to test jitter variance
    const durations: number[] = [];

    for (let i = 0; i < 3; i++) {
      const start = Date.now();

      await withRetryAndJitter(
        operation,
        {
          maxRetries: 1,
          initialDelay: 100,
          maxDelay: 1000,
          backoffMultiplier: 2
        },
        0.2 // 20% jitter
      );

      durations.push(Date.now() - start);
      operation.mockClear();
    }

    // Durations should vary due to jitter
    const unique = new Set(durations.map(d => Math.floor(d / 10)));
    expect(unique.size).toBeGreaterThan(1);
  });
});

describe('defaultRetryConfigs', () => {
  it('should have configurations for common scenarios', () => {
    expect(defaultRetryConfigs).toHaveProperty('database');
    expect(defaultRetryConfigs).toHaveProperty('cache');
    expect(defaultRetryConfigs).toHaveProperty('external_api');
    expect(defaultRetryConfigs).toHaveProperty('file_operation');

    expect(defaultRetryConfigs.database.maxRetries).toBe(3);
    expect(defaultRetryConfigs.cache.maxRetries).toBe(2);
  });
});
