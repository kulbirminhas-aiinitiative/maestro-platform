/**
 * Circuit Breaker Pattern Implementation
 *
 * Prevents cascading failures by stopping requests to failing services.
 * States: CLOSED (normal) -> OPEN (failing) -> HALF_OPEN (testing recovery)
 *
 * ADR-006 Compliant: Resilience Patterns
 */

enum CircuitState {
  CLOSED = 'CLOSED',
  OPEN = 'OPEN',
  HALF_OPEN = 'HALF_OPEN'
}

interface CircuitBreakerConfig {
  failureThreshold: number;      // Number of failures before opening
  successThreshold: number;      // Successes needed to close from half-open
  timeout: number;               // Time in ms before trying half-open
  resetTimeout?: number;         // Optional reset timeout
}

interface CircuitBreakerMetrics {
  failures: number;
  successes: number;
  state: CircuitState;
  lastFailureTime?: Date;
  lastStateChange: Date;
}

export class CircuitBreaker {
  private state: CircuitState = CircuitState.CLOSED;
  private failures: number = 0;
  private successes: number = 0;
  private lastFailureTime?: Date;
  private lastStateChange: Date = new Date();
  private nextAttempt: Date = new Date();

  constructor(
    private name: string,
    private config: CircuitBreakerConfig
  ) {}

  /**
   * Execute a function with circuit breaker protection
   */
  async execute<T>(fn: () => Promise<T>): Promise<T> {
    if (this.state === CircuitState.OPEN) {
      if (Date.now() < this.nextAttempt.getTime()) {
        throw new Error(
          `Circuit breaker '${this.name}' is OPEN. Service unavailable.`
        );
      }
      // Try half-open state
      this.setState(CircuitState.HALF_OPEN);
    }

    try {
      const result = await fn();
      this.onSuccess();
      return result;
    } catch (error) {
      this.onFailure();
      throw error;
    }
  }

  /**
   * Handle successful execution
   */
  private onSuccess(): void {
    this.failures = 0;

    if (this.state === CircuitState.HALF_OPEN) {
      this.successes++;
      if (this.successes >= this.config.successThreshold) {
        this.setState(CircuitState.CLOSED);
        this.successes = 0;
      }
    }
  }

  /**
   * Handle failed execution
   */
  private onFailure(): void {
    this.failures++;
    this.lastFailureTime = new Date();
    this.successes = 0;

    if (
      this.state === CircuitState.HALF_OPEN ||
      this.failures >= this.config.failureThreshold
    ) {
      this.setState(CircuitState.OPEN);
      this.nextAttempt = new Date(Date.now() + this.config.timeout);
    }
  }

  /**
   * Set circuit breaker state
   */
  private setState(newState: CircuitState): void {
    const oldState = this.state;
    this.state = newState;
    this.lastStateChange = new Date();

    console.log(
      `Circuit breaker '${this.name}' transitioned from ${oldState} to ${newState}`
    );
  }

  /**
   * Get current metrics
   */
  getMetrics(): CircuitBreakerMetrics {
    return {
      failures: this.failures,
      successes: this.successes,
      state: this.state,
      lastFailureTime: this.lastFailureTime,
      lastStateChange: this.lastStateChange
    };
  }

  /**
   * Get current state
   */
  getState(): CircuitState {
    return this.state;
  }

  /**
   * Manually reset circuit breaker
   */
  reset(): void {
    this.state = CircuitState.CLOSED;
    this.failures = 0;
    this.successes = 0;
    this.lastFailureTime = undefined;
    this.lastStateChange = new Date();
  }
}

/**
 * Circuit Breaker Registry
 * Manages multiple circuit breakers by name
 */
export class CircuitBreakerRegistry {
  private breakers: Map<string, CircuitBreaker> = new Map();

  /**
   * Get or create a circuit breaker
   */
  getOrCreate(name: string, config: CircuitBreakerConfig): CircuitBreaker {
    if (!this.breakers.has(name)) {
      this.breakers.set(name, new CircuitBreaker(name, config));
    }
    return this.breakers.get(name)!;
  }

  /**
   * Get all circuit breaker metrics
   */
  getAllMetrics(): Record<string, CircuitBreakerMetrics> {
    const metrics: Record<string, CircuitBreakerMetrics> = {};
    this.breakers.forEach((breaker, name) => {
      metrics[name] = breaker.getMetrics();
    });
    return metrics;
  }

  /**
   * Reset all circuit breakers
   */
  resetAll(): void {
    this.breakers.forEach(breaker => breaker.reset());
  }
}

// Global registry
export const circuitBreakerRegistry = new CircuitBreakerRegistry();

// Default configurations for common services
export const defaultCircuitBreakerConfigs: Record<string, CircuitBreakerConfig> = {
  database: {
    failureThreshold: 5,
    successThreshold: 2,
    timeout: 60000 // 60 seconds
  },
  cache: {
    failureThreshold: 3,
    successThreshold: 2,
    timeout: 30000 // 30 seconds
  },
  external_api: {
    failureThreshold: 3,
    successThreshold: 2,
    timeout: 30000 // 30 seconds
  }
};
