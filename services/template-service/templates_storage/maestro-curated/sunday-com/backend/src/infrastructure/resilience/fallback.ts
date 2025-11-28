/**
 * Fallback Pattern Implementation
 *
 * Provides alternative responses when primary operations fail.
 * Enables graceful degradation of service functionality.
 *
 * ADR-006 Compliant: Resilience Patterns
 */

export interface FallbackConfig<T> {
  fallbackFn: () => Promise<T> | T;
  fallbackOnErrors?: string[];      // Specific errors that trigger fallback
  cacheFallback?: boolean;          // Whether to use cached result as fallback
  logFallback?: boolean;            // Whether to log fallback usage
}

/**
 * Execute function with fallback on failure
 */
export async function withFallback<T>(
  primaryFn: () => Promise<T>,
  config: FallbackConfig<T>,
  context?: string
): Promise<T> {
  const { fallbackFn, fallbackOnErrors, logFallback = true } = config;

  try {
    return await primaryFn();
  } catch (error) {
    const err = error as Error;

    // Check if error should trigger fallback
    if (fallbackOnErrors && fallbackOnErrors.length > 0) {
      const shouldFallback = fallbackOnErrors.some(
        errorType =>
          err.name === errorType || err.message.includes(errorType)
      );

      if (!shouldFallback) {
        throw error;
      }
    }

    if (logFallback) {
      console.warn(
        `Primary operation failed${context ? ` for ${context}` : ''}, using fallback. Error: ${err.message}`
      );
    }

    // Execute fallback
    const result = await fallbackFn();
    return result;
  }
}

/**
 * Fallback decorator for class methods
 */
export function Fallback<T>(fallbackFn: () => Promise<T> | T) {
  return function (
    target: any,
    propertyKey: string,
    descriptor: PropertyDescriptor
  ) {
    const originalMethod = descriptor.value;

    descriptor.value = async function (...args: any[]) {
      return withFallback(
        () => originalMethod.apply(this, args),
        { fallbackFn },
        `${target.constructor.name}.${propertyKey}`
      );
    };

    return descriptor;
  };
}

/**
 * Cached fallback - uses last successful result as fallback
 */
export class CachedFallback<T> {
  private lastSuccessfulResult?: T;
  private lastSuccessTime?: Date;

  constructor(
    private maxAge: number = 300000  // 5 minutes default
  ) {}

  async execute(
    primaryFn: () => Promise<T>,
    defaultFallback?: T,
    context?: string
  ): Promise<T> {
    try {
      const result = await primaryFn();
      this.lastSuccessfulResult = result;
      this.lastSuccessTime = new Date();
      return result;
    } catch (error) {
      const err = error as Error;

      // Check if cached result is still valid
      if (this.lastSuccessfulResult && this.isCacheValid()) {
        console.warn(
          `Using cached fallback${context ? ` for ${context}` : ''}. Error: ${err.message}`
        );
        return this.lastSuccessfulResult;
      }

      // Use default fallback if provided
      if (defaultFallback !== undefined) {
        console.warn(
          `Using default fallback${context ? ` for ${context}` : ''}. Error: ${err.message}`
        );
        return defaultFallback;
      }

      throw error;
    }
  }

  private isCacheValid(): boolean {
    if (!this.lastSuccessTime) {
      return false;
    }

    const age = Date.now() - this.lastSuccessTime.getTime();
    return age <= this.maxAge;
  }

  clearCache(): void {
    this.lastSuccessfulResult = undefined;
    this.lastSuccessTime = undefined;
  }

  getLastResult(): T | undefined {
    return this.lastSuccessfulResult;
  }
}

/**
 * Multi-level fallback - tries multiple fallback strategies in order
 */
export class MultiLevelFallback<T> {
  private fallbacks: Array<() => Promise<T> | T> = [];

  addFallback(fallbackFn: () => Promise<T> | T): MultiLevelFallback<T> {
    this.fallbacks.push(fallbackFn);
    return this;
  }

  async execute(
    primaryFn: () => Promise<T>,
    context?: string
  ): Promise<T> {
    // Try primary function
    try {
      return await primaryFn();
    } catch (primaryError) {
      console.warn(
        `Primary operation failed${context ? ` for ${context}` : ''}: ${(primaryError as Error).message}`
      );

      // Try each fallback in order
      for (let i = 0; i < this.fallbacks.length; i++) {
        try {
          console.log(
            `Trying fallback level ${i + 1}/${this.fallbacks.length}${context ? ` for ${context}` : ''}`
          );
          const result = await this.fallbacks[i]();
          console.log(
            `Fallback level ${i + 1} succeeded${context ? ` for ${context}` : ''}`
          );
          return result;
        } catch (fallbackError) {
          console.warn(
            `Fallback level ${i + 1} failed${context ? ` for ${context}` : ''}: ${(fallbackError as Error).message}`
          );

          // If this was the last fallback, throw
          if (i === this.fallbacks.length - 1) {
            throw new Error(
              `All fallback levels exhausted${context ? ` for ${context}` : ''}. Last error: ${(fallbackError as Error).message}`
            );
          }
        }
      }

      // If no fallbacks, throw original error
      throw primaryError;
    }
  }
}

/**
 * Conditional fallback - chooses fallback strategy based on error type
 */
export class ConditionalFallback<T> {
  private fallbackMap: Map<string, () => Promise<T> | T> = new Map();
  private defaultFallback?: () => Promise<T> | T;

  /**
   * Register fallback for specific error type
   */
  onError(
    errorType: string,
    fallbackFn: () => Promise<T> | T
  ): ConditionalFallback<T> {
    this.fallbackMap.set(errorType, fallbackFn);
    return this;
  }

  /**
   * Set default fallback for unmatched errors
   */
  otherwise(fallbackFn: () => Promise<T> | T): ConditionalFallback<T> {
    this.defaultFallback = fallbackFn;
    return this;
  }

  /**
   * Execute with conditional fallback
   */
  async execute(
    primaryFn: () => Promise<T>,
    context?: string
  ): Promise<T> {
    try {
      return await primaryFn();
    } catch (error) {
      const err = error as Error;

      // Find matching fallback
      for (const [errorType, fallbackFn] of this.fallbackMap.entries()) {
        if (err.name === errorType || err.message.includes(errorType)) {
          console.warn(
            `Using conditional fallback for '${errorType}'${context ? ` in ${context}` : ''}`
          );
          return await fallbackFn();
        }
      }

      // Use default fallback if available
      if (this.defaultFallback) {
        console.warn(
          `Using default fallback${context ? ` for ${context}` : ''}`
        );
        return await this.defaultFallback();
      }

      // No fallback available
      throw error;
    }
  }
}

/**
 * Default fallback values for common data types
 */
export const defaultFallbackValues = {
  emptyArray: <T>(): T[] => [],
  emptyObject: <T extends object>(): T => ({} as T),
  emptyString: (): string => '',
  zero: (): number => 0,
  false: (): boolean => false,
  null: (): null => null
};

/**
 * Common fallback configurations
 */
export const commonFallbackConfigs = {
  useCache: <T>(cachedValue: T): FallbackConfig<T> => ({
    fallbackFn: () => cachedValue,
    logFallback: true
  }),

  useDefault: <T>(defaultValue: T): FallbackConfig<T> => ({
    fallbackFn: () => defaultValue,
    logFallback: true
  }),

  useEmpty: <T>(): FallbackConfig<T[]> => ({
    fallbackFn: () => [] as T[],
    logFallback: true
  })
};
