/**
 * Timeout and Fallback Pattern Tests
 */

import {
  withTimeout,
  TimeoutError,
  defaultTimeoutConfigs
} from '../../../../infrastructure/resilience/timeout';

import {
  withFallback,
  CachedFallback,
  MultiLevelFallback,
  ConditionalFallback
} from '../../../../infrastructure/resilience/fallback';

describe('Timeout Pattern', () => {
  describe('withTimeout', () => {
    it('should succeed if operation completes within timeout', async () => {
      const operation = async () => {
        await new Promise(resolve => setTimeout(resolve, 50));
        return 'success';
      };

      const result = await withTimeout(operation, { timeoutMs: 200 });
      expect(result).toBe('success');
    });

    it('should throw TimeoutError if operation exceeds timeout', async () => {
      const operation = async () => {
        await new Promise(resolve => setTimeout(resolve, 200));
        return 'success';
      };

      await expect(
        withTimeout(operation, { timeoutMs: 50 })
      ).rejects.toThrow(TimeoutError);
    });

    it('should include timeout value in error message', async () => {
      const operation = async () => {
        await new Promise(resolve => setTimeout(resolve, 200));
        return 'success';
      };

      try {
        await withTimeout(operation, { timeoutMs: 50 }, 'test-operation');
        fail('Should have thrown TimeoutError');
      } catch (error) {
        expect(error).toBeInstanceOf(TimeoutError);
        expect((error as TimeoutError).message).toContain('50ms');
        expect((error as TimeoutError).message).toContain('test-operation');
      }
    });
  });

  describe('defaultTimeoutConfigs', () => {
    it('should have configurations for common operations', () => {
      expect(defaultTimeoutConfigs).toHaveProperty('database_query');
      expect(defaultTimeoutConfigs).toHaveProperty('cache_operation');
      expect(defaultTimeoutConfigs).toHaveProperty('external_api');

      expect(defaultTimeoutConfigs.database_query.timeoutMs).toBe(5000);
      expect(defaultTimeoutConfigs.cache_operation.timeoutMs).toBe(2000);
    });
  });
});

describe('Fallback Pattern', () => {
  describe('withFallback', () => {
    it('should return primary result on success', async () => {
      const primary = jest.fn().mockResolvedValue('primary-result');
      const fallback = jest.fn().mockResolvedValue('fallback-result');

      const result = await withFallback(
        primary,
        { fallbackFn: fallback }
      );

      expect(result).toBe('primary-result');
      expect(primary).toHaveBeenCalledTimes(1);
      expect(fallback).not.toHaveBeenCalled();
    });

    it('should use fallback on primary failure', async () => {
      const primary = jest.fn().mockRejectedValue(new Error('primary failed'));
      const fallback = jest.fn().mockResolvedValue('fallback-result');

      const result = await withFallback(
        primary,
        { fallbackFn: fallback }
      );

      expect(result).toBe('fallback-result');
      expect(primary).toHaveBeenCalledTimes(1);
      expect(fallback).toHaveBeenCalledTimes(1);
    });

    it('should respect fallbackOnErrors filter', async () => {
      const primary = jest.fn().mockRejectedValue(new Error('ValidationError'));
      const fallback = jest.fn().mockResolvedValue('fallback-result');

      await expect(
        withFallback(
          primary,
          {
            fallbackFn: fallback,
            fallbackOnErrors: ['ECONNREFUSED', 'ETIMEDOUT']
          }
        )
      ).rejects.toThrow('ValidationError');

      expect(fallback).not.toHaveBeenCalled();
    });

    it('should use fallback for matching errors', async () => {
      const primary = jest.fn().mockRejectedValue(new Error('ETIMEDOUT'));
      const fallback = jest.fn().mockResolvedValue('fallback-result');

      const result = await withFallback(
        primary,
        {
          fallbackFn: fallback,
          fallbackOnErrors: ['ETIMEDOUT']
        }
      );

      expect(result).toBe('fallback-result');
      expect(fallback).toHaveBeenCalledTimes(1);
    });
  });

  describe('CachedFallback', () => {
    it('should cache successful results', async () => {
      const cachedFallback = new CachedFallback<string>(5000);
      const operation = jest.fn().mockResolvedValue('cached-value');

      const result1 = await cachedFallback.execute(operation);
      expect(result1).toBe('cached-value');
      expect(cachedFallback.getLastResult()).toBe('cached-value');
    });

    it('should use cached value on failure', async () => {
      const cachedFallback = new CachedFallback<string>(5000);

      const successOp = jest.fn().mockResolvedValue('cached-value');
      await cachedFallback.execute(successOp);

      const failOp = jest.fn().mockRejectedValue(new Error('failure'));
      const result = await cachedFallback.execute(failOp);

      expect(result).toBe('cached-value');
    });

    it('should throw if cache is invalid and no default', async () => {
      const cachedFallback = new CachedFallback<string>(100); // 100ms max age

      const successOp = jest.fn().mockResolvedValue('cached-value');
      await cachedFallback.execute(successOp);

      // Wait for cache to expire
      await new Promise(resolve => setTimeout(resolve, 150));

      const failOp = jest.fn().mockRejectedValue(new Error('failure'));

      await expect(
        cachedFallback.execute(failOp)
      ).rejects.toThrow('failure');
    });

    it('should use default fallback if cache expired', async () => {
      const cachedFallback = new CachedFallback<string>(100);

      const successOp = jest.fn().mockResolvedValue('cached-value');
      await cachedFallback.execute(successOp);

      await new Promise(resolve => setTimeout(resolve, 150));

      const failOp = jest.fn().mockRejectedValue(new Error('failure'));
      const result = await cachedFallback.execute(failOp, 'default-value');

      expect(result).toBe('default-value');
    });
  });

  describe('MultiLevelFallback', () => {
    it('should try fallbacks in order', async () => {
      const multiLevel = new MultiLevelFallback<string>();

      const fallback1 = jest.fn().mockRejectedValue(new Error('fallback1 failed'));
      const fallback2 = jest.fn().mockResolvedValue('fallback2-result');
      const fallback3 = jest.fn().mockResolvedValue('fallback3-result');

      multiLevel
        .addFallback(fallback1)
        .addFallback(fallback2)
        .addFallback(fallback3);

      const primary = jest.fn().mockRejectedValue(new Error('primary failed'));

      const result = await multiLevel.execute(primary);

      expect(result).toBe('fallback2-result');
      expect(primary).toHaveBeenCalledTimes(1);
      expect(fallback1).toHaveBeenCalledTimes(1);
      expect(fallback2).toHaveBeenCalledTimes(1);
      expect(fallback3).not.toHaveBeenCalled();
    });

    it('should throw if all fallbacks fail', async () => {
      const multiLevel = new MultiLevelFallback<string>();

      multiLevel
        .addFallback(() => Promise.reject(new Error('fallback1 failed')))
        .addFallback(() => Promise.reject(new Error('fallback2 failed')));

      const primary = jest.fn().mockRejectedValue(new Error('primary failed'));

      await expect(
        multiLevel.execute(primary)
      ).rejects.toThrow(/All fallback levels exhausted/);
    });
  });

  describe('ConditionalFallback', () => {
    it('should use specific fallback for matching error', async () => {
      const conditional = new ConditionalFallback<string>();

      conditional
        .onError('ECONNREFUSED', () => 'connection-fallback')
        .onError('ETIMEDOUT', () => 'timeout-fallback')
        .otherwise(() => 'default-fallback');

      const primary = jest.fn().mockRejectedValue(new Error('ETIMEDOUT'));

      const result = await conditional.execute(primary);

      expect(result).toBe('timeout-fallback');
    });

    it('should use default fallback for unmatched error', async () => {
      const conditional = new ConditionalFallback<string>();

      conditional
        .onError('ECONNREFUSED', () => 'connection-fallback')
        .otherwise(() => 'default-fallback');

      const primary = jest.fn().mockRejectedValue(new Error('UNKNOWN_ERROR'));

      const result = await conditional.execute(primary);

      expect(result).toBe('default-fallback');
    });

    it('should throw if no matching fallback', async () => {
      const conditional = new ConditionalFallback<string>();

      conditional.onError('ECONNREFUSED', () => 'connection-fallback');

      const primary = jest.fn().mockRejectedValue(new Error('UNKNOWN_ERROR'));

      await expect(
        conditional.execute(primary)
      ).rejects.toThrow('UNKNOWN_ERROR');
    });
  });
});
