/**
 * Resilience Patterns for Sunday.com Backend
 *
 * ADR-006 Compliant Implementation
 *
 * This module provides enterprise-grade resilience patterns:
 * - Circuit Breaker: Prevents cascading failures
 * - Retry with Exponential Backoff: Handles transient failures
 * - Timeout: Prevents hanging operations
 * - Fallback: Graceful degradation
 *
 * @module infrastructure/resilience
 */

// Circuit Breaker
export {
  CircuitBreaker,
  CircuitBreakerRegistry,
  circuitBreakerRegistry,
  defaultCircuitBreakerConfigs
} from './circuit-breaker';

// Retry
export {
  withRetry,
  withRetryAndJitter,
  Retry,
  defaultRetryConfigs,
  type RetryConfig,
  type RetryMetrics
} from './retry';

// Timeout
export {
  withTimeout,
  withTimeoutAndAbort,
  Timeout,
  TimeoutError,
  StagedTimeout,
  AdaptiveTimeout,
  defaultTimeoutConfigs,
  type TimeoutConfig
} from './timeout';

// Fallback
export {
  withFallback,
  Fallback,
  CachedFallback,
  MultiLevelFallback,
  ConditionalFallback,
  defaultFallbackValues,
  commonFallbackConfigs,
  type FallbackConfig
} from './fallback';

/**
 * Combined resilience wrapper
 * Applies multiple resilience patterns in a single operation
 */
import { CircuitBreaker } from './circuit-breaker';
import { withRetry, RetryConfig } from './retry';
import { withTimeout, TimeoutConfig } from './timeout';
import { withFallback, FallbackConfig } from './fallback';

export interface ResilientOperationConfig<T> {
  circuitBreaker?: CircuitBreaker;
  retry?: RetryConfig;
  timeout?: TimeoutConfig;
  fallback?: FallbackConfig<T>;
  context?: string;
}

/**
 * Execute operation with full resilience stack
 */
export async function executeResilient<T>(
  operation: () => Promise<T>,
  config: ResilientOperationConfig<T>
): Promise<T> {
  const { circuitBreaker, retry, timeout, fallback, context } = config;

  let wrappedOperation = operation;

  // Wrap with timeout (innermost)
  if (timeout) {
    const originalOp = wrappedOperation;
    wrappedOperation = () => withTimeout(originalOp, timeout, context);
  }

  // Wrap with retry
  if (retry) {
    const originalOp = wrappedOperation;
    wrappedOperation = () => withRetry(originalOp, retry, context);
  }

  // Wrap with circuit breaker
  if (circuitBreaker) {
    const originalOp = wrappedOperation;
    wrappedOperation = () => circuitBreaker.execute(originalOp);
  }

  // Wrap with fallback (outermost)
  if (fallback) {
    return withFallback(wrappedOperation, fallback, context);
  }

  return wrappedOperation();
}
