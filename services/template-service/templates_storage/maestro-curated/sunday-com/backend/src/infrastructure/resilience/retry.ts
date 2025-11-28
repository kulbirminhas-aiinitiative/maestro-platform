/**
 * Retry with Exponential Backoff Pattern
 *
 * Automatically retries failed operations with increasing delays.
 * Prevents overwhelming failing services while giving them time to recover.
 *
 * ADR-006 Compliant: Resilience Patterns
 */

export interface RetryConfig {
  maxRetries: number;           // Maximum number of retry attempts
  initialDelay: number;         // Initial delay in milliseconds
  maxDelay: number;             // Maximum delay in milliseconds
  backoffMultiplier: number;    // Multiplier for exponential backoff (default: 2)
  retryableErrors?: string[];   // List of retryable error types/messages
}

export interface RetryMetrics {
  attempts: number;
  totalDelay: number;
  success: boolean;
  finalError?: Error;
}

/**
 * Sleep for specified milliseconds
 */
function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Check if error is retryable
 */
function isRetryableError(error: Error, retryableErrors?: string[]): boolean {
  if (!retryableErrors || retryableErrors.length === 0) {
    return true; // Retry all errors by default
  }

  return retryableErrors.some(
    errorType =>
      error.name === errorType ||
      error.message.includes(errorType)
  );
}

/**
 * Execute function with retry logic and exponential backoff
 */
export async function withRetry<T>(
  fn: () => Promise<T>,
  config: RetryConfig,
  context?: string
): Promise<T> {
  const {
    maxRetries,
    initialDelay,
    maxDelay,
    backoffMultiplier = 2,
    retryableErrors
  } = config;

  let lastError: Error;
  let delay = initialDelay;
  let totalDelay = 0;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      // First attempt or retry after delay
      if (attempt > 0) {
        await sleep(delay);
        totalDelay += delay;

        console.log(
          `Retry attempt ${attempt}/${maxRetries}${context ? ` for ${context}` : ''} after ${delay}ms delay`
        );
      }

      const result = await fn();

      if (attempt > 0) {
        console.log(
          `Retry successful after ${attempt} attempts (total delay: ${totalDelay}ms)${context ? ` for ${context}` : ''}`
        );
      }

      return result;
    } catch (error) {
      lastError = error as Error;

      // Check if error is retryable
      if (!isRetryableError(lastError, retryableErrors)) {
        throw new Error(
          `Non-retryable error${context ? ` for ${context}` : ''}: ${lastError.message}`
        );
      }

      // Last attempt failed
      if (attempt === maxRetries) {
        throw new Error(
          `Max retries (${maxRetries}) exceeded${context ? ` for ${context}` : ''}. Last error: ${lastError.message}`
        );
      }

      // Calculate next delay with exponential backoff
      delay = Math.min(delay * backoffMultiplier, maxDelay);
    }
  }

  throw lastError!;
}

/**
 * Retry decorator for class methods
 */
export function Retry(config: RetryConfig) {
  return function (
    target: any,
    propertyKey: string,
    descriptor: PropertyDescriptor
  ) {
    const originalMethod = descriptor.value;

    descriptor.value = async function (...args: any[]) {
      return withRetry(
        () => originalMethod.apply(this, args),
        config,
        `${target.constructor.name}.${propertyKey}`
      );
    };

    return descriptor;
  };
}

/**
 * Default retry configurations for common scenarios
 */
export const defaultRetryConfigs: Record<string, RetryConfig> = {
  database: {
    maxRetries: 3,
    initialDelay: 1000,    // 1 second
    maxDelay: 10000,       // 10 seconds
    backoffMultiplier: 2,
    retryableErrors: [
      'ECONNREFUSED',
      'ETIMEDOUT',
      'ECONNRESET',
      'EPIPE'
    ]
  },
  cache: {
    maxRetries: 2,
    initialDelay: 500,     // 0.5 seconds
    maxDelay: 5000,        // 5 seconds
    backoffMultiplier: 2,
    retryableErrors: [
      'ECONNREFUSED',
      'ETIMEDOUT'
    ]
  },
  external_api: {
    maxRetries: 3,
    initialDelay: 2000,    // 2 seconds
    maxDelay: 30000,       // 30 seconds
    backoffMultiplier: 2,
    retryableErrors: [
      'ECONNREFUSED',
      'ETIMEDOUT',
      'ENOTFOUND',
      '429',  // Too Many Requests
      '503',  // Service Unavailable
      '504'   // Gateway Timeout
    ]
  },
  file_operation: {
    maxRetries: 2,
    initialDelay: 1000,
    maxDelay: 5000,
    backoffMultiplier: 2,
    retryableErrors: [
      'EBUSY',
      'EMFILE',
      'ENFILE'
    ]
  }
};

/**
 * Retry with jitter to prevent thundering herd
 */
export async function withRetryAndJitter<T>(
  fn: () => Promise<T>,
  config: RetryConfig,
  jitterFactor: number = 0.1,
  context?: string
): Promise<T> {
  const configWithJitter = {
    ...config,
    initialDelay: config.initialDelay * (1 + Math.random() * jitterFactor)
  };

  return withRetry(fn, configWithJitter, context);
}
