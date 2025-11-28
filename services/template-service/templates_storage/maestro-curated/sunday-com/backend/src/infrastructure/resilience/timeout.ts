/**
 * Timeout Pattern Implementation
 *
 * Prevents operations from hanging indefinitely by enforcing time limits.
 * Throws TimeoutError if operation exceeds specified duration.
 *
 * ADR-006 Compliant: Resilience Patterns
 */

export class TimeoutError extends Error {
  constructor(message: string, public readonly timeoutMs: number) {
    super(message);
    this.name = 'TimeoutError';
  }
}

export interface TimeoutConfig {
  timeoutMs: number;
  abortController?: boolean;  // Use AbortController if available
}

/**
 * Execute function with timeout protection
 */
export async function withTimeout<T>(
  fn: () => Promise<T>,
  config: TimeoutConfig,
  context?: string
): Promise<T> {
  const { timeoutMs } = config;

  return new Promise<T>(async (resolve, reject) => {
    const timeoutId = setTimeout(() => {
      reject(
        new TimeoutError(
          `Operation timed out after ${timeoutMs}ms${context ? ` for ${context}` : ''}`,
          timeoutMs
        )
      );
    }, timeoutMs);

    try {
      const result = await fn();
      clearTimeout(timeoutId);
      resolve(result);
    } catch (error) {
      clearTimeout(timeoutId);
      reject(error);
    }
  });
}

/**
 * Execute function with timeout and AbortSignal support
 */
export async function withTimeoutAndAbort<T>(
  fn: (signal: AbortSignal) => Promise<T>,
  config: TimeoutConfig,
  context?: string
): Promise<T> {
  const { timeoutMs } = config;
  const abortController = new AbortController();

  const timeoutPromise = new Promise<never>((_, reject) => {
    setTimeout(() => {
      abortController.abort();
      reject(
        new TimeoutError(
          `Operation timed out after ${timeoutMs}ms${context ? ` for ${context}` : ''}`,
          timeoutMs
        )
      );
    }, timeoutMs);
  });

  try {
    const result = await Promise.race([
      fn(abortController.signal),
      timeoutPromise
    ]);
    return result;
  } catch (error) {
    abortController.abort();
    throw error;
  }
}

/**
 * Timeout decorator for class methods
 */
export function Timeout(timeoutMs: number) {
  return function (
    target: any,
    propertyKey: string,
    descriptor: PropertyDescriptor
  ) {
    const originalMethod = descriptor.value;

    descriptor.value = async function (...args: any[]) {
      return withTimeout(
        () => originalMethod.apply(this, args),
        { timeoutMs },
        `${target.constructor.name}.${propertyKey}`
      );
    };

    return descriptor;
  };
}

/**
 * Default timeout configurations for common operations
 */
export const defaultTimeoutConfigs: Record<string, TimeoutConfig> = {
  database_query: {
    timeoutMs: 5000,    // 5 seconds
    abortController: false
  },
  database_transaction: {
    timeoutMs: 30000,   // 30 seconds
    abortController: false
  },
  cache_operation: {
    timeoutMs: 2000,    // 2 seconds
    abortController: false
  },
  external_api: {
    timeoutMs: 10000,   // 10 seconds
    abortController: true
  },
  file_upload: {
    timeoutMs: 60000,   // 60 seconds
    abortController: true
  },
  websocket_message: {
    timeoutMs: 5000,    // 5 seconds
    abortController: false
  },
  background_job: {
    timeoutMs: 300000,  // 5 minutes
    abortController: true
  }
};

/**
 * Timeout with multiple stages
 * Useful for operations with different phases that need different timeouts
 */
export class StagedTimeout {
  private stages: Array<{ name: string; timeoutMs: number }> = [];
  private currentStage: number = 0;

  addStage(name: string, timeoutMs: number): StagedTimeout {
    this.stages.push({ name, timeoutMs });
    return this;
  }

  async executeStage<T>(fn: () => Promise<T>): Promise<T> {
    if (this.currentStage >= this.stages.length) {
      throw new Error('No more stages available');
    }

    const stage = this.stages[this.currentStage];
    this.currentStage++;

    return withTimeout(
      fn,
      { timeoutMs: stage.timeoutMs },
      stage.name
    );
  }

  reset(): void {
    this.currentStage = 0;
  }

  getTotalTimeout(): number {
    return this.stages.reduce((sum, stage) => sum + stage.timeoutMs, 0);
  }
}

/**
 * Adaptive timeout - adjusts based on historical performance
 */
export class AdaptiveTimeout {
  private executionTimes: number[] = [];
  private readonly maxSamples: number = 100;

  constructor(
    private baseTimeoutMs: number,
    private percentile: number = 95
  ) {}

  /**
   * Execute with adaptive timeout
   */
  async execute<T>(fn: () => Promise<T>, context?: string): Promise<T> {
    const startTime = Date.now();
    const currentTimeout = this.getAdaptiveTimeout();

    try {
      const result = await withTimeout(
        fn,
        { timeoutMs: currentTimeout },
        context
      );

      // Record successful execution time
      const executionTime = Date.now() - startTime;
      this.recordExecutionTime(executionTime);

      return result;
    } catch (error) {
      if (error instanceof TimeoutError) {
        // Don't record timeout as execution time
        throw error;
      }

      const executionTime = Date.now() - startTime;
      this.recordExecutionTime(executionTime);
      throw error;
    }
  }

  /**
   * Calculate adaptive timeout based on percentile
   */
  private getAdaptiveTimeout(): number {
    if (this.executionTimes.length === 0) {
      return this.baseTimeoutMs;
    }

    const sorted = [...this.executionTimes].sort((a, b) => a - b);
    const index = Math.floor(sorted.length * (this.percentile / 100));
    const percentileValue = sorted[index];

    // Add 50% buffer to percentile value
    return Math.max(this.baseTimeoutMs, percentileValue * 1.5);
  }

  /**
   * Record execution time
   */
  private recordExecutionTime(time: number): void {
    this.executionTimes.push(time);

    // Keep only recent samples
    if (this.executionTimes.length > this.maxSamples) {
      this.executionTimes.shift();
    }
  }

  /**
   * Get current timeout value
   */
  getCurrentTimeout(): number {
    return this.getAdaptiveTimeout();
  }

  /**
   * Reset execution history
   */
  reset(): void {
    this.executionTimes = [];
  }
}
