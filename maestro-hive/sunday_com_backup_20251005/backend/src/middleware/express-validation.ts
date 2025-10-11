import { Request, Response, NextFunction } from 'express';
import { validationResult } from 'express-validator';
import { Logger } from '@/config/logger';

/**
 * Express-validator middleware for handling validation results
 */
export const validationMiddleware = (
  req: Request,
  res: Response,
  next: NextFunction
): void => {
  const errors = validationResult(req);

  if (!errors.isEmpty()) {
    const formattedErrors = errors.array().map(error => ({
      field: error.type === 'field' ? error.path : error.type,
      message: error.msg,
      value: error.type === 'field' ? error.value : undefined,
      location: error.location,
    }));

    Logger.api('Express validation failed', {
      errors: formattedErrors,
      path: req.path,
      method: req.method,
    });

    res.status(400).json({
      error: {
        type: 'validation_error',
        message: 'Invalid input parameters',
        details: formattedErrors,
        requestId: req.headers['x-request-id'],
      },
    });
    return;
  }

  next();
};

/**
 * Enhanced validation middleware with custom error formatting
 */
export const enhancedValidationMiddleware = (
  req: Request,
  res: Response,
  next: NextFunction
): void => {
  const errors = validationResult(req);

  if (!errors.isEmpty()) {
    const errorsByField = errors.array().reduce((acc, error) => {
      const field = error.type === 'field' ? error.path : error.type;
      if (!acc[field]) {
        acc[field] = [];
      }
      acc[field].push({
        message: error.msg,
        value: error.type === 'field' ? error.value : undefined,
        code: error.type,
      });
      return acc;
    }, {} as Record<string, any[]>);

    Logger.api('Enhanced validation failed', {
      errorsByField,
      path: req.path,
      method: req.method,
      userAgent: req.headers['user-agent'],
    });

    res.status(400).json({
      error: {
        type: 'validation_error',
        message: 'Validation failed',
        fields: errorsByField,
        requestId: req.headers['x-request-id'],
        timestamp: new Date().toISOString(),
      },
    });
    return;
  }

  next();
};

/**
 * Sanitization middleware that cleans input data
 */
export const sanitizeMiddleware = (
  req: Request,
  res: Response,
  next: NextFunction
): void => {
  // Sanitize request body
  if (req.body && typeof req.body === 'object') {
    req.body = sanitizeObject(req.body);
  }

  // Sanitize query parameters
  if (req.query && typeof req.query === 'object') {
    req.query = sanitizeObject(req.query);
  }

  next();
};

/**
 * Recursively sanitize an object
 */
function sanitizeObject(obj: any): any {
  if (obj === null || obj === undefined) {
    return obj;
  }

  if (Array.isArray(obj)) {
    return obj.map(sanitizeObject);
  }

  if (typeof obj === 'object') {
    const sanitized: any = {};
    for (const [key, value] of Object.entries(obj)) {
      // Skip prototype pollution attempts
      if (key === '__proto__' || key === 'constructor' || key === 'prototype') {
        continue;
      }

      sanitized[key] = sanitizeObject(value);
    }
    return sanitized;
  }

  if (typeof obj === 'string') {
    // Basic XSS prevention - strip HTML tags
    return obj.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
              .replace(/<[^>]*>/g, '')
              .trim();
  }

  return obj;
}

export default validationMiddleware;