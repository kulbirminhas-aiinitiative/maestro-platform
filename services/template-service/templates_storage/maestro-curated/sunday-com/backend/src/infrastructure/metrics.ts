/**
 * Prometheus Metrics for Sunday.com Backend
 *
 * Provides comprehensive monitoring and observability through Prometheus metrics.
 * Tracks HTTP requests, database operations, cache hits, circuit breaker states, etc.
 *
 * Metrics endpoint: GET /metrics
 */

import { Registry, Counter, Histogram, Gauge, collectDefaultMetrics } from 'prom-client';

/**
 * Prometheus Registry
 */
export const register = new Registry();

/**
 * Collect default Node.js metrics (CPU, memory, event loop, etc.)
 */
collectDefaultMetrics({
  register,
  prefix: 'sunday_',
  gcDurationBuckets: [0.001, 0.01, 0.1, 1, 2, 5]
});

/**
 * HTTP Request Metrics
 */
export const httpRequestCounter = new Counter({
  name: 'sunday_http_requests_total',
  help: 'Total number of HTTP requests',
  labelNames: ['method', 'route', 'status'],
  registers: [register]
});

export const httpRequestDuration = new Histogram({
  name: 'sunday_http_request_duration_seconds',
  help: 'HTTP request duration in seconds',
  labelNames: ['method', 'route', 'status'],
  buckets: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10],
  registers: [register]
});

export const httpRequestSize = new Histogram({
  name: 'sunday_http_request_size_bytes',
  help: 'HTTP request size in bytes',
  labelNames: ['method', 'route'],
  buckets: [100, 1000, 5000, 10000, 50000, 100000, 500000, 1000000],
  registers: [register]
});

export const httpResponseSize = new Histogram({
  name: 'sunday_http_response_size_bytes',
  help: 'HTTP response size in bytes',
  labelNames: ['method', 'route'],
  buckets: [100, 1000, 5000, 10000, 50000, 100000, 500000, 1000000],
  registers: [register]
});

/**
 * Database Metrics
 */
export const dbQueryCounter = new Counter({
  name: 'sunday_db_queries_total',
  help: 'Total number of database queries',
  labelNames: ['operation', 'model'],
  registers: [register]
});

export const dbQueryDuration = new Histogram({
  name: 'sunday_db_query_duration_seconds',
  help: 'Database query duration in seconds',
  labelNames: ['operation', 'model'],
  buckets: [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1],
  registers: [register]
});

export const dbConnectionPool = new Gauge({
  name: 'sunday_db_connection_pool',
  help: 'Database connection pool status',
  labelNames: ['state'], // active, idle, waiting
  registers: [register]
});

export const dbErrorCounter = new Counter({
  name: 'sunday_db_errors_total',
  help: 'Total number of database errors',
  labelNames: ['error_type'],
  registers: [register]
});

/**
 * Cache Metrics
 */
export const cacheHitCounter = new Counter({
  name: 'sunday_cache_hits_total',
  help: 'Total number of cache hits',
  labelNames: ['cache_name'],
  registers: [register]
});

export const cacheMissCounter = new Counter({
  name: 'sunday_cache_misses_total',
  help: 'Total number of cache misses',
  labelNames: ['cache_name'],
  registers: [register]
});

export const cacheOperationDuration = new Histogram({
  name: 'sunday_cache_operation_duration_seconds',
  help: 'Cache operation duration in seconds',
  labelNames: ['operation', 'cache_name'],
  buckets: [0.001, 0.005, 0.01, 0.025, 0.05, 0.1],
  registers: [register]
});

/**
 * Circuit Breaker Metrics
 */
export const circuitBreakerState = new Gauge({
  name: 'sunday_circuit_breaker_state',
  help: 'Circuit breaker state (0=closed, 1=half-open, 2=open)',
  labelNames: ['circuit_name'],
  registers: [register]
});

export const circuitBreakerFailures = new Counter({
  name: 'sunday_circuit_breaker_failures_total',
  help: 'Total number of circuit breaker failures',
  labelNames: ['circuit_name'],
  registers: [register]
});

export const circuitBreakerSuccesses = new Counter({
  name: 'sunday_circuit_breaker_successes_total',
  help: 'Total number of circuit breaker successes',
  labelNames: ['circuit_name'],
  registers: [register]
});

export const circuitBreakerStateChanges = new Counter({
  name: 'sunday_circuit_breaker_state_changes_total',
  help: 'Total number of circuit breaker state changes',
  labelNames: ['circuit_name', 'from_state', 'to_state'],
  registers: [register]
});

/**
 * WebSocket Metrics
 */
export const websocketConnections = new Gauge({
  name: 'sunday_websocket_connections',
  help: 'Current number of WebSocket connections',
  labelNames: ['room'],
  registers: [register]
});

export const websocketMessages = new Counter({
  name: 'sunday_websocket_messages_total',
  help: 'Total number of WebSocket messages',
  labelNames: ['event', 'direction'], // direction: incoming/outgoing
  registers: [register]
});

/**
 * Business Metrics
 */
export const activeUsers = new Gauge({
  name: 'sunday_active_users',
  help: 'Current number of active users',
  labelNames: ['tenant_id'],
  registers: [register]
});

export const taskOperations = new Counter({
  name: 'sunday_task_operations_total',
  help: 'Total number of task operations',
  labelNames: ['operation', 'board_type'],
  registers: [register]
});

export const boardViews = new Counter({
  name: 'sunday_board_views_total',
  help: 'Total number of board views',
  labelNames: ['board_type'],
  registers: [register]
});

export const automationExecutions = new Counter({
  name: 'sunday_automation_executions_total',
  help: 'Total number of automation executions',
  labelNames: ['automation_type', 'status'],
  registers: [register]
});

/**
 * Error Metrics
 */
export const errorCounter = new Counter({
  name: 'sunday_errors_total',
  help: 'Total number of errors',
  labelNames: ['error_type', 'severity'],
  registers: [register]
});

export const uncaughtExceptions = new Counter({
  name: 'sunday_uncaught_exceptions_total',
  help: 'Total number of uncaught exceptions',
  registers: [register]
});

/**
 * API Rate Limiting Metrics
 */
export const rateLimitExceeded = new Counter({
  name: 'sunday_rate_limit_exceeded_total',
  help: 'Total number of rate limit exceeded events',
  labelNames: ['endpoint', 'user_id'],
  registers: [register]
});

/**
 * External API Metrics
 */
export const externalApiCalls = new Counter({
  name: 'sunday_external_api_calls_total',
  help: 'Total number of external API calls',
  labelNames: ['service', 'status'],
  registers: [register]
});

export const externalApiDuration = new Histogram({
  name: 'sunday_external_api_duration_seconds',
  help: 'External API call duration in seconds',
  labelNames: ['service'],
  buckets: [0.1, 0.5, 1, 2, 5, 10, 30],
  registers: [register]
});

/**
 * Helper function to get all metrics
 */
export async function getMetrics(): Promise<string> {
  return register.metrics();
}

/**
 * Reset all metrics (useful for testing)
 */
export function resetMetrics(): void {
  register.resetMetrics();
}

/**
 * Record HTTP request metrics
 */
export function recordHttpRequest(
  method: string,
  route: string,
  status: number,
  durationSeconds: number,
  requestSize?: number,
  responseSize?: number
): void {
  httpRequestCounter.inc({ method, route, status });
  httpRequestDuration.observe({ method, route, status }, durationSeconds);

  if (requestSize !== undefined) {
    httpRequestSize.observe({ method, route }, requestSize);
  }

  if (responseSize !== undefined) {
    httpResponseSize.observe({ method, route }, responseSize);
  }
}

/**
 * Record database query metrics
 */
export function recordDbQuery(
  operation: string,
  model: string,
  durationSeconds: number
): void {
  dbQueryCounter.inc({ operation, model });
  dbQueryDuration.observe({ operation, model }, durationSeconds);
}

/**
 * Record cache operation metrics
 */
export function recordCacheOperation(
  hit: boolean,
  cacheName: string,
  durationSeconds?: number
): void {
  if (hit) {
    cacheHitCounter.inc({ cache_name: cacheName });
  } else {
    cacheMissCounter.inc({ cache_name: cacheName });
  }

  if (durationSeconds !== undefined) {
    cacheOperationDuration.observe(
      { operation: hit ? 'hit' : 'miss', cache_name: cacheName },
      durationSeconds
    );
  }
}
