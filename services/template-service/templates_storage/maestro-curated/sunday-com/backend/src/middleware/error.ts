import { Request, Response, NextFunction } from 'express';
import { Logger } from '@/config/logger';
import { ApiError } from '@/types';

/**
 * Global error handling middleware
 */
export const errorHandler = (
  error: Error,
  req: Request,
  res: Response,
  next: NextFunction
): void => {
  Logger.error('Unhandled error', error, {
    method: req.method,
    url: req.url,
    headers: req.headers,
    body: req.body,
    params: req.params,
    query: req.query,
  });

  // Default error response
  const apiError: ApiError = {
    type: 'internal_error',
    message: 'An unexpected error occurred',
    requestId: req.headers['x-request-id'] as string,
  };

  // Add stack trace in development
  if (process.env.NODE_ENV === 'development') {
    apiError.stack = error.stack;
  }

  res.status(500).json({ error: apiError });
};

/**
 * 404 Not Found handler
 */
export const notFoundHandler = (req: Request, res: Response): void => {
  res.status(404).json({
    error: {
      type: 'not_found',
      message: `Route ${req.method} ${req.path} not found`,
    },
  });
};

/**
 * Async error wrapper to catch async errors in route handlers
 */
export const asyncHandler = (fn: Function) => {
  return (req: Request, res: Response, next: NextFunction) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
};

/**
 * Custom application errors
 */
export class AppError extends Error {
  public statusCode: number;
  public type: string;
  public isOperational: boolean;

  constructor(message: string, statusCode = 500, type = 'internal_error') {
    super(message);
    this.statusCode = statusCode;
    this.type = type;
    this.isOperational = true;

    Error.captureStackTrace(this, this.constructor);
  }
}

/**
 * Validation error
 */
export class ValidationError extends AppError {
  constructor(message: string, details?: any) {
    super(message, 422, 'validation_error');
    this.name = 'ValidationError';
  }
}

/**
 * Authentication error
 */
export class AuthenticationError extends AppError {
  constructor(message: string) {
    super(message, 401, 'authentication_error');
    this.name = 'AuthenticationError';
  }
}

/**
 * Authorization error
 */
export class AuthorizationError extends AppError {
  constructor(message: string) {
    super(message, 403, 'authorization_error');
    this.name = 'AuthorizationError';
  }
}

/**
 * Not found error
 */
export class NotFoundError extends AppError {
  constructor(message: string) {
    super(message, 404, 'not_found');
    this.name = 'NotFoundError';
  }
}

/**
 * Conflict error
 */
export class ConflictError extends AppError {
  constructor(message: string) {
    super(message, 409, 'conflict');
    this.name = 'ConflictError';
  }
}

/**
 * Rate limit error
 */
export class RateLimitError extends AppError {
  constructor(message: string) {
    super(message, 429, 'rate_limit_exceeded');
    this.name = 'RateLimitError';
  }
}