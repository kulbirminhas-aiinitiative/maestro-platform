/**
 * Circuit Breaker Tests
 */

import { CircuitBreaker, CircuitBreakerRegistry } from '../../../../infrastructure/resilience/circuit-breaker';

describe('CircuitBreaker', () => {
  let circuitBreaker: CircuitBreaker;

  beforeEach(() => {
    circuitBreaker = new CircuitBreaker('test-service', {
      failureThreshold: 3,
      successThreshold: 2,
      timeout: 1000
    });
  });

  describe('CLOSED state', () => {
    it('should execute operation successfully', async () => {
      const operation = jest.fn().mockResolvedValue('success');
      const result = await circuitBreaker.execute(operation);

      expect(result).toBe('success');
      expect(operation).toHaveBeenCalledTimes(1);
      expect(circuitBreaker.getState()).toBe('CLOSED');
    });

    it('should remain CLOSED on single failure', async () => {
      const operation = jest.fn().mockRejectedValue(new Error('failure'));

      await expect(circuitBreaker.execute(operation)).rejects.toThrow('failure');
      expect(circuitBreaker.getState()).toBe('CLOSED');
    });

    it('should transition to OPEN after reaching failure threshold', async () => {
      const operation = jest.fn().mockRejectedValue(new Error('failure'));

      // Fail 3 times (threshold)
      for (let i = 0; i < 3; i++) {
        await expect(circuitBreaker.execute(operation)).rejects.toThrow();
      }

      expect(circuitBreaker.getState()).toBe('OPEN');
      expect(operation).toHaveBeenCalledTimes(3);
    });
  });

  describe('OPEN state', () => {
    beforeEach(async () => {
      const operation = jest.fn().mockRejectedValue(new Error('failure'));

      // Trigger OPEN state
      for (let i = 0; i < 3; i++) {
        await expect(circuitBreaker.execute(operation)).rejects.toThrow();
      }
    });

    it('should reject immediately without calling operation', async () => {
      const operation = jest.fn().mockResolvedValue('success');

      await expect(circuitBreaker.execute(operation)).rejects.toThrow(
        /Circuit breaker.*is OPEN/
      );

      expect(operation).not.toHaveBeenCalled();
    });

    it('should transition to HALF_OPEN after timeout', async () => {
      const operation = jest.fn().mockResolvedValue('success');

      // Wait for timeout
      await new Promise(resolve => setTimeout(resolve, 1100));

      await circuitBreaker.execute(operation);
      expect(circuitBreaker.getState()).toBe('HALF_OPEN');
    });
  });

  describe('HALF_OPEN state', () => {
    beforeEach(async () => {
      const failingOp = jest.fn().mockRejectedValue(new Error('failure'));

      // Trigger OPEN state
      for (let i = 0; i < 3; i++) {
        await expect(circuitBreaker.execute(failingOp)).rejects.toThrow();
      }

      // Wait for timeout to transition to HALF_OPEN
      await new Promise(resolve => setTimeout(resolve, 1100));
    });

    it('should transition to CLOSED after success threshold', async () => {
      const operation = jest.fn().mockResolvedValue('success');

      // Need 2 successes (successThreshold)
      await circuitBreaker.execute(operation);
      expect(circuitBreaker.getState()).toBe('HALF_OPEN');

      await circuitBreaker.execute(operation);
      expect(circuitBreaker.getState()).toBe('CLOSED');
    });

    it('should transition back to OPEN on failure', async () => {
      const operation = jest.fn().mockRejectedValue(new Error('failure'));

      await expect(circuitBreaker.execute(operation)).rejects.toThrow();
      expect(circuitBreaker.getState()).toBe('OPEN');
    });
  });

  describe('reset', () => {
    it('should reset circuit breaker to CLOSED state', async () => {
      const operation = jest.fn().mockRejectedValue(new Error('failure'));

      // Trigger OPEN state
      for (let i = 0; i < 3; i++) {
        await expect(circuitBreaker.execute(operation)).rejects.toThrow();
      }

      expect(circuitBreaker.getState()).toBe('OPEN');

      circuitBreaker.reset();

      expect(circuitBreaker.getState()).toBe('CLOSED');
      expect(circuitBreaker.getMetrics().failures).toBe(0);
    });
  });

  describe('metrics', () => {
    it('should track failures', async () => {
      const operation = jest.fn().mockRejectedValue(new Error('failure'));

      await expect(circuitBreaker.execute(operation)).rejects.toThrow();
      await expect(circuitBreaker.execute(operation)).rejects.toThrow();

      const metrics = circuitBreaker.getMetrics();
      expect(metrics.failures).toBe(2);
      expect(metrics.state).toBe('CLOSED');
    });

    it('should track successes in HALF_OPEN state', async () => {
      const failingOp = jest.fn().mockRejectedValue(new Error('failure'));
      const successOp = jest.fn().mockResolvedValue('success');

      // Trigger OPEN state
      for (let i = 0; i < 3; i++) {
        await expect(circuitBreaker.execute(failingOp)).rejects.toThrow();
      }

      // Wait for HALF_OPEN
      await new Promise(resolve => setTimeout(resolve, 1100));

      await circuitBreaker.execute(successOp);

      const metrics = circuitBreaker.getMetrics();
      expect(metrics.successes).toBe(1);
      expect(metrics.state).toBe('HALF_OPEN');
    });
  });
});

describe('CircuitBreakerRegistry', () => {
  let registry: CircuitBreakerRegistry;

  beforeEach(() => {
    registry = new CircuitBreakerRegistry();
  });

  it('should create and retrieve circuit breakers', () => {
    const config = {
      failureThreshold: 3,
      successThreshold: 2,
      timeout: 1000
    };

    const cb1 = registry.getOrCreate('service1', config);
    const cb2 = registry.getOrCreate('service1', config);
    const cb3 = registry.getOrCreate('service2', config);

    expect(cb1).toBe(cb2); // Same instance
    expect(cb1).not.toBe(cb3); // Different instance
  });

  it('should get metrics for all circuit breakers', async () => {
    const config = {
      failureThreshold: 3,
      successThreshold: 2,
      timeout: 1000
    };

    const cb1 = registry.getOrCreate('service1', config);
    const cb2 = registry.getOrCreate('service2', config);

    const operation = jest.fn().mockRejectedValue(new Error('failure'));
    await expect(cb1.execute(operation)).rejects.toThrow();

    const metrics = registry.getAllMetrics();

    expect(metrics).toHaveProperty('service1');
    expect(metrics).toHaveProperty('service2');
    expect(metrics.service1.failures).toBe(1);
    expect(metrics.service2.failures).toBe(0);
  });

  it('should reset all circuit breakers', async () => {
    const config = {
      failureThreshold: 3,
      successThreshold: 2,
      timeout: 1000
    };

    const cb1 = registry.getOrCreate('service1', config);
    const operation = jest.fn().mockRejectedValue(new Error('failure'));

    for (let i = 0; i < 3; i++) {
      await expect(cb1.execute(operation)).rejects.toThrow();
    }

    expect(cb1.getState()).toBe('OPEN');

    registry.resetAll();

    expect(cb1.getState()).toBe('CLOSED');
  });
});
