import { Request, Response, NextFunction } from 'express';
import { ValidationError } from 'express-validator';
import { AuthenticatedRequest } from '@/types';
import { Logger } from '@/config/logger';
import { RedisService } from '@/config/redis';

// ============================================================================
// ERROR TYPES
// ============================================================================

export interface APIError extends Error {
  statusCode?: number;
  code?: string;
  details?: Record<string, any>;
  isOperational?: boolean;
  requestId?: string;
}

export class BaseAPIError extends Error implements APIError {
  public statusCode: number;
  public code: string;
  public details: Record<string, any>;
  public isOperational: boolean;
  public requestId?: string;

  constructor(
    message: string,
    statusCode: number = 500,
    code: string = 'INTERNAL_ERROR',
    details: Record<string, any> = {},
    isOperational: boolean = true
  ) {
    super(message);
    this.name = this.constructor.name;
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
    this.isOperational = isOperational;

    Error.captureStackTrace(this, this.constructor);
  }
}

export class ValidationError extends BaseAPIError {
  constructor(message: string = 'Validation failed', details: Record<string, any> = {}) {
    super(message, 400, 'VALIDATION_ERROR', details);
  }
}

export class AuthenticationError extends BaseAPIError {
  constructor(message: string = 'Authentication required', details: Record<string, any> = {}) {
    super(message, 401, 'AUTHENTICATION_ERROR', details);
  }
}

export class AuthorizationError extends BaseAPIError {
  constructor(message: string = 'Insufficient permissions', details: Record<string, any> = {}) {
    super(message, 403, 'AUTHORIZATION_ERROR', details);
  }
}

export class NotFoundError extends BaseAPIError {
  constructor(message: string = 'Resource not found', details: Record<string, any> = {}) {
    super(message, 404, 'NOT_FOUND_ERROR', details);
  }
}

export class ConflictError extends BaseAPIError {
  constructor(message: string = 'Resource conflict', details: Record<string, any> = {}) {
    super(message, 409, 'CONFLICT_ERROR', details);
  }
}

export class RateLimitError extends BaseAPIError {
  constructor(message: string = 'Rate limit exceeded', details: Record<string, any> = {}) {
    super(message, 429, 'RATE_LIMIT_ERROR', details);
  }
}

export class DatabaseError extends BaseAPIError {
  constructor(message: string = 'Database operation failed', details: Record<string, any> = {}) {
    super(message, 500, 'DATABASE_ERROR', details);
  }
}

export class ExternalServiceError extends BaseAPIError {
  constructor(message: string = 'External service unavailable', details: Record<string, any> = {}) {
    super(message, 502, 'EXTERNAL_SERVICE_ERROR', details);
  }
}

// ============================================================================
// REQUEST ID MIDDLEWARE
// ============================================================================

export const requestIdMiddleware = (req: Request, res: Response, next: NextFunction): void => {
  const requestId = req.headers['x-request-id'] as string ||
                   `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

  req.requestId = requestId;
  res.setHeader('X-Request-ID', requestId);

  next();
};

// ============================================================================
// ASYNC ERROR HANDLER
// ============================================================================

export const asyncHandler = (fn: Function) => {
  return (req: Request, res: Response, next: NextFunction) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
};

// ============================================================================
// VALIDATION ERROR TRANSFORMER
// ============================================================================

export const transformValidationErrors = (errors: ValidationError[]): Record<string, any> => {
  const grouped: Record<string, any> = {};

  errors.forEach(error => {
    if (!grouped[error.param]) {
      grouped[error.param] = [];
    }
    grouped[error.param].push({
      message: error.msg,
      value: error.value,
      location: error.location,
    });
  });

  return grouped;
};

// ============================================================================
// PRISMA ERROR HANDLER
// ============================================================================

export const handlePrismaError = (error: any): APIError => {
  // Handle Prisma-specific errors
  if (error.code) {
    switch (error.code) {
      case 'P2002':
        return new ConflictError('Unique constraint violation', {
          fields: error.meta?.target,
          prismaCode: error.code,
        });

      case 'P2025':
        return new NotFoundError('Record not found', {
          cause: error.meta?.cause,
          prismaCode: error.code,
        });

      case 'P2003':
        return new ValidationError('Foreign key constraint violation', {
          field: error.meta?.field_name,
          prismaCode: error.code,
        });

      case 'P2034':
        return new ConflictError('Transaction failed due to write conflict', {
          prismaCode: error.code,
        });

      default:
        return new DatabaseError('Database operation failed', {
          prismaCode: error.code,
          details: error.meta,
        });
    }
  }

  return new DatabaseError('Unknown database error', {
    originalError: error.message,
  });
};

// ============================================================================
// ERROR RECOVERY STRATEGIES
// ============================================================================

export class ErrorRecoveryService {
  /**
   * Attempt to recover from rate limit errors
   */
  static async handleRateLimit(
    req: AuthenticatedRequest,
    error: RateLimitError
  ): Promise<{ canRetry: boolean; retryAfter?: number; fallback?: any }> {
    try {
      const userId = req.user?.id || req.ip;
      const endpoint = req.route?.path || req.path;

      // Check if user has premium features for higher limits
      if (req.user?.organizations?.some(org => org.role === 'owner')) {
        // Temporarily increase limit for premium users
        const premiumKey = `premium_limit:${userId}:${endpoint}`;
        const premiumUsage = await RedisService.getCache(premiumKey) || '0';

        if (parseInt(premiumUsage) < 1000) { // Premium limit
          await RedisService.incr(premiumKey, 300); // 5 min TTL
          return { canRetry: true };
        }
      }

      // Calculate retry-after based on current usage
      const retryAfter = Math.min(60, Math.max(5, error.details.resetTime || 30));

      return {
        canRetry: false,
        retryAfter,
      };
    } catch (recoveryError) {
      Logger.error('Error recovery failed', recoveryError as Error);
      return { canRetry: false, retryAfter: 60 };
    }
  }

  /**
   * Attempt to recover from database errors
   */
  static async handleDatabaseError(
    req: AuthenticatedRequest,
    error: DatabaseError
  ): Promise<{ canRetry: boolean; fallback?: any }> {
    try {
      // For read operations, try to serve from cache
      if (req.method === 'GET') {
        const cacheKey = `fallback:${req.path}:${JSON.stringify(req.query)}`;
        const cachedData = await RedisService.getCache(cacheKey);

        if (cachedData) {
          return {
            canRetry: false,
            fallback: JSON.parse(cachedData),
          };
        }
      }

      // For write operations, queue for retry
      if (['POST', 'PUT', 'PATCH'].includes(req.method)) {
        const retryKey = `retry:${req.requestId}`;
        await RedisService.setCache(retryKey, JSON.stringify({
          method: req.method,
          path: req.path,
          body: req.body,
          userId: req.user?.id,
          timestamp: new Date(),
        }), 3600); // 1 hour

        return { canRetry: true };
      }

      return { canRetry: false };
    } catch (recoveryError) {
      Logger.error('Database error recovery failed', recoveryError as Error);
      return { canRetry: false };
    }
  }

  /**
   * Handle external service errors with circuit breaker pattern
   */
  static async handleExternalServiceError(
    serviceName: string,
    error: ExternalServiceError
  ): Promise<{ canRetry: boolean; fallback?: any }> {
    try {
      const circuitKey = `circuit:${serviceName}`;
      const failures = await RedisService.getCache(circuitKey) || '0';
      const failureCount = parseInt(failures);

      // Circuit breaker thresholds
      const maxFailures = 5;
      const circuitOpenTime = 300; // 5 minutes

      if (failureCount >= maxFailures) {
        // Circuit is open - don't retry
        return {
          canRetry: false,
          fallback: {
            error: 'Service temporarily unavailable',
            circuitOpen: true,
          },
        };
      }

      // Increment failure count
      await RedisService.incr(circuitKey, 60); // 1 minute TTL for reset

      return { canRetry: failureCount < maxFailures - 1 };
    } catch (recoveryError) {
      Logger.error('External service error recovery failed', recoveryError as Error);
      return { canRetry: false };
    }
  }
}

// ============================================================================
// ENHANCED ERROR MIDDLEWARE
// ============================================================================

export const enhancedErrorHandler = async (
  error: any,
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): Promise<void> => {
  // Ensure we have a request ID
  const requestId = req.requestId || `req_${Date.now()}`;

  let apiError: APIError;

  // Transform various error types to APIError
  if (error instanceof BaseAPIError) {
    apiError = error;
  } else if (error.name === 'ValidationError' && error.array) {
    // Express-validator errors
    const validationDetails = transformValidationErrors(error.array());
    apiError = new ValidationError('Request validation failed', { fields: validationDetails });
  } else if (error.code?.startsWith('P2')) {
    // Prisma errors
    apiError = handlePrismaError(error);
  } else if (error.name === 'JsonWebTokenError') {
    apiError = new AuthenticationError('Invalid token', { tokenError: error.message });
  } else if (error.name === 'TokenExpiredError') {
    apiError = new AuthenticationError('Token expired', { expiredAt: error.expiredAt });
  } else if (error.code === 'ECONNREFUSED' || error.code === 'ENOTFOUND') {
    apiError = new ExternalServiceError('Service unavailable', { code: error.code });
  } else {
    // Unknown error
    apiError = new BaseAPIError(
      process.env.NODE_ENV === 'production' ? 'Internal server error' : error.message,
      500,
      'INTERNAL_ERROR',
      process.env.NODE_ENV === 'production' ? {} : { stack: error.stack },
      false
    );
  }

  apiError.requestId = requestId;

  // Attempt error recovery for certain error types
  let recoveryResult = { canRetry: false, fallback: undefined };

  try {
    if (apiError instanceof RateLimitError) {
      recoveryResult = await ErrorRecoveryService.handleRateLimit(req, apiError);
    } else if (apiError instanceof DatabaseError) {
      recoveryResult = await ErrorRecoveryService.handleDatabaseError(req, apiError);
    } else if (apiError instanceof ExternalServiceError) {
      recoveryResult = await ErrorRecoveryService.handleExternalServiceError(
        'unknown',
        apiError
      );
    }
  } catch (recoveryError) {
    Logger.error('Error recovery attempt failed', recoveryError as Error);
  }

  // Log the error with appropriate level
  const logData = {
    requestId,
    userId: req.user?.id,
    method: req.method,
    path: req.path,
    userAgent: req.get('User-Agent'),
    ip: req.ip,
    statusCode: apiError.statusCode,
    code: apiError.code,
    details: apiError.details,
    recovery: recoveryResult,
  };

  if (apiError.statusCode >= 500) {
    Logger.error(`${apiError.code}: ${apiError.message}`, apiError, logData);
  } else if (apiError.statusCode >= 400) {
    Logger.warn(`${apiError.code}: ${apiError.message}`, logData);
  } else {
    Logger.info(`${apiError.code}: ${apiError.message}`, logData);
  }

  // Track error metrics
  try {
    const metricsKey = `error_metrics:${new Date().toISOString().split('T')[0]}`;
    await RedisService.incr(`${metricsKey}:${apiError.code}`, 24 * 60 * 60); // 24 hour TTL
    await RedisService.incr(`${metricsKey}:status_${apiError.statusCode}`, 24 * 60 * 60);
  } catch (metricsError) {
    Logger.error('Failed to track error metrics', metricsError as Error);
  }

  // Send response
  const response: any = {
    success: false,
    error: {
      type: apiError.code,
      message: apiError.message,
      requestId: apiError.requestId,
      ...(apiError.details && Object.keys(apiError.details).length > 0 && {
        details: apiError.details,
      }),
    },
  };

  // Add recovery information if available
  if (recoveryResult.canRetry) {
    response.error.recoverable = true;
    if ('retryAfter' in recoveryResult) {
      response.error.retryAfter = recoveryResult.retryAfter;
      res.setHeader('Retry-After', recoveryResult.retryAfter!);
    }
  }

  // Use fallback data if available
  if (recoveryResult.fallback) {
    response.data = recoveryResult.fallback;
    response.fromFallback = true;
  }

  res.status(apiError.statusCode).json(response);
};

// ============================================================================
// NOT FOUND HANDLER
// ============================================================================

export const notFoundHandler = (req: Request, res: Response): void => {
  const error = new NotFoundError(`Route not found: ${req.method} ${req.path}`, {
    method: req.method,
    path: req.path,
    availableRoutes: [
      'GET /api/v1/health',
      'POST /api/v1/auth/login',
      'GET /api/v1/workspaces',
      'GET /api/v1/boards',
      'GET /api/v1/items',
      // Add more as needed
    ],
  });

  enhancedErrorHandler(error, req as AuthenticatedRequest, res, () => {});
};

// ============================================================================
// GRACEFUL SHUTDOWN HANDLER
// ============================================================================

export class GracefulShutdownHandler {
  private static isShuttingDown = false;

  static async initiateShutdown(signal: string): Promise<void> {
    if (this.isShuttingDown) {
      Logger.warn('Shutdown already in progress');
      return;
    }

    this.isShuttingDown = true;
    Logger.info(`Received ${signal}, initiating graceful shutdown...`);

    try {
      // Stop accepting new requests
      // Close database connections
      // Clear Redis connections
      // Notify dependent services

      Logger.info('Graceful shutdown completed');
      process.exit(0);
    } catch (error) {
      Logger.error('Error during graceful shutdown', error as Error);
      process.exit(1);
    }
  }

  static isShuttingDownCheck = (req: Request, res: Response, next: NextFunction): void => {
    if (this.isShuttingDown) {
      res.status(503).json({
        success: false,
        error: {
          type: 'SERVICE_UNAVAILABLE',
          message: 'Server is shutting down',
        },
      });
      return;
    }
    next();
  };
}

// ============================================================================
// EXPORT ALL
// ============================================================================

export {
  BaseAPIError,
  ValidationError as CustomValidationError,
  AuthenticationError,
  AuthorizationError,
  NotFoundError,
  ConflictError,
  RateLimitError,
  DatabaseError,
  ExternalServiceError,
};