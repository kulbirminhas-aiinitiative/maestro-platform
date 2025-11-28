/**
 * Metrics Middleware for Express
 *
 * Automatically collects HTTP request metrics for all routes.
 */

import { Request, Response, NextFunction } from 'express';
import { recordHttpRequest } from '../infrastructure/metrics';

/**
 * Metrics collection middleware
 */
export function metricsMiddleware(
  req: Request,
  res: Response,
  next: NextFunction
): void {
  const start = Date.now();

  // Get request size
  const requestSize = req.headers['content-length']
    ? parseInt(req.headers['content-length'], 10)
    : 0;

  // Capture original end function
  const originalEnd = res.end;

  // Override res.end to capture response metrics
  res.end = function (
    this: Response,
    ...args: any[]
  ): Response {
    // Calculate duration
    const durationSeconds = (Date.now() - start) / 1000;

    // Get response size
    const responseSize = res.getHeader('content-length')
      ? parseInt(res.getHeader('content-length') as string, 10)
      : 0;

    // Get route pattern (if available)
    const route = req.route?.path || req.path;

    // Record metrics
    recordHttpRequest(
      req.method,
      route,
      res.statusCode,
      durationSeconds,
      requestSize,
      responseSize
    );

    // Call original end
    return originalEnd.apply(this, args);
  };

  next();
}

/**
 * Metrics endpoint handler
 */
export async function metricsEndpoint(
  req: Request,
  res: Response
): Promise<void> {
  try {
    const { getMetrics } = await import('../infrastructure/metrics');
    const metrics = await getMetrics();

    res.set('Content-Type', 'text/plain; version=0.0.4; charset=utf-8');
    res.send(metrics);
  } catch (error) {
    console.error('Error generating metrics:', error);
    res.status(500).send('Error generating metrics');
  }
}
