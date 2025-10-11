import { Request, Response, NextFunction } from 'express';
import { Logger } from '@/config/logger';
import { PrismaClientKnownRequestError, PrismaClientValidationError } from '@prisma/client/runtime/library';
import { MulterError } from 'multer';
import { ApiError } from '@/types';

interface EnhancedApiError extends Error {
  statusCode?: number;
  isOperational?: boolean;
  code?: string;
  details?: any;
}

/**
 * Enhanced global error handler middleware with comprehensive error handling
 */
export const enhancedErrorHandler = (
  error: EnhancedApiError,
  req: Request,
  res: Response,
  next: NextFunction
): void => {
  // Generate unique error ID for tracking
  const errorId = Math.random().toString(36).substring(2, 15);

  // Log the error with full context
  Logger.error('Enhanced error handler', {
    errorId,
    error: {
      name: error.name,
      message: error.message,
      stack: error.stack,
      code: error.code,
    },
    request: {
      method: req.method,
      url: req.url,
      path: req.path,
      query: req.query,
      body: sanitizeForLogging(req.body),
      headers: {
        'user-agent': req.headers['user-agent'],
        'x-request-id': req.headers['x-request-id'],
        'x-forwarded-for': req.headers['x-forwarded-for'],
        'content-type': req.headers['content-type'],
      },
      ip: req.ip,
    },
  });

  // Default error response
  let statusCode = 500;
  let message = 'Internal server error';
  let type = 'internal_error';
  let details: any = undefined;

  // Handle custom API errors
  if (error.statusCode) {
    statusCode = error.statusCode;
    message = error.message;
    type = getErrorType(error);
    details = error.details;
  }

  // Handle Prisma database errors
  if (error instanceof PrismaClientKnownRequestError) {
    const prismaError = handlePrismaError(error);
    statusCode = prismaError.statusCode;
    message = prismaError.message;
    type = prismaError.type;
    details = prismaError.details;
  }

  if (error instanceof PrismaClientValidationError) {
    statusCode = 400;
    message = 'Invalid data format provided to database';
    type = 'validation_error';
    details = {
      prismaError: error.message,
      hint: 'Check data types and required fields',
    };
  }

  // Handle JWT authentication errors
  if (error.name === 'JsonWebTokenError') {
    statusCode = 401;
    message = 'Invalid authentication token provided';
    type = 'authentication_error';
    details = { reason: 'malformed_token' };
  }

  if (error.name === 'TokenExpiredError') {
    statusCode = 401;
    message = 'Authentication token has expired';
    type = 'authentication_error';
    details = { reason: 'expired_token' };
  }

  if (error.name === 'NotBeforeError') {
    statusCode = 401;
    message = 'Authentication token not yet valid';
    type = 'authentication_error';
    details = { reason: 'token_not_active' };
  }

  // Handle validation errors
  if (error.name === 'ValidationError') {
    statusCode = 422;
    message = error.message;
    type = 'validation_error';
    details = error.details;
  }

  // Handle Multer file upload errors
  if (error instanceof MulterError) {
    const multerError = handleMulterError(error);
    statusCode = multerError.statusCode;
    message = multerError.message;
    type = multerError.type;
    details = multerError.details;
  }

  // Handle rate limiting errors
  if (error.name === 'TooManyRequestsError' || error.message.includes('rate limit')) {
    statusCode = 429;
    message = 'Rate limit exceeded. Please try again later';
    type = 'rate_limit_exceeded';
    details = { retryAfter: 60 };
  }

  // Handle permission/authorization errors
  if (error.name === 'ForbiddenError' || error.message.includes('Access denied')) {
    statusCode = 403;
    message = error.message || 'Access denied to this resource';
    type = 'forbidden';
  }

  // Handle not found errors
  if (error.name === 'NotFoundError' || error.message.includes('not found')) {
    statusCode = 404;
    message = error.message || 'Requested resource not found';
    type = 'not_found';
  }

  // Handle conflict errors
  if (error.name === 'ConflictError') {
    statusCode = 409;
    message = error.message || 'Resource conflict detected';
    type = 'conflict';
  }

  // Handle network/timeout errors
  if (error.name === 'TimeoutError' || error.code === 'ETIMEDOUT') {
    statusCode = 504;
    message = 'Request timeout - operation took too long';
    type = 'timeout_error';
  }

  // Handle syntax errors (malformed JSON, etc.)
  if (error instanceof SyntaxError && error.message.includes('JSON')) {
    statusCode = 400;
    message = 'Invalid JSON format in request body';
    type = 'syntax_error';
    details = { hint: 'Check JSON syntax and formatting' };
  }

  // Build comprehensive error response
  const response: any = {
    error: {
      id: errorId,
      type,
      message,
      timestamp: new Date().toISOString(),
      requestId: req.headers['x-request-id'],
    },
  };

  // Include additional details if available
  if (details) {
    response.error.details = details;
  }

  // Include helpful information for client
  response.error.path = req.path;
  response.error.method = req.method;

  // Include suggestions for common errors
  if (statusCode === 404) {
    response.error.suggestions = getRouteSuggestions(req.path);
  }

  if (statusCode === 401) {
    response.error.hints = [
      'Ensure you have included a valid Authorization header',
      'Check if your token has expired',
      'Verify the token format is correct (Bearer <token>)',
    ];
  }

  if (statusCode === 403) {
    response.error.hints = [
      'Check if you have the required permissions',
      'Verify you are accessing the correct resource',
      'Contact an administrator if you believe this is an error',
    ];
  }

  // Include stack trace and raw error in development
  if (process.env.NODE_ENV === 'development') {
    response.error.stack = error.stack;
    response.error.raw = {
      name: error.name,
      code: error.code,
      statusCode: error.statusCode,
    };
  }

  // Set security headers
  res.set({
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
  });

  // Set cache headers for error responses
  res.set({
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0',
  });

  res.status(statusCode).json(response);
};

/**
 * Enhanced request validation middleware
 */
export const requestValidationMiddleware = (
  req: Request,
  res: Response,
  next: NextFunction
): void => {
  // Validate Content-Type for POST/PUT requests
  if (['POST', 'PUT', 'PATCH'].includes(req.method)) {
    const contentType = req.headers['content-type'];

    if (!contentType) {
      return res.status(400).json({
        error: {
          type: 'validation_error',
          message: 'Content-Type header is required',
          details: {
            expected: 'application/json',
            received: 'none',
          },
        },
      });
    }

    if (!contentType.includes('application/json') && !contentType.includes('multipart/form-data')) {
      return res.status(415).json({
        error: {
          type: 'unsupported_media_type',
          message: 'Unsupported Content-Type',
          details: {
            supported: ['application/json', 'multipart/form-data'],
            received: contentType,
          },
        },
      });
    }
  }

  // Validate request size
  const contentLength = req.headers['content-length'];
  if (contentLength && parseInt(contentLength) > 10 * 1024 * 1024) { // 10MB
    return res.status(413).json({
      error: {
        type: 'payload_too_large',
        message: 'Request payload too large',
        details: {
          maxSize: '10MB',
          received: `${Math.round(parseInt(contentLength) / 1024 / 1024)}MB`,
        },
      },
    });
  }

  next();
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Handle Prisma-specific errors with detailed messages
 */
function handlePrismaError(error: PrismaClientKnownRequestError): {
  statusCode: number;
  message: string;
  type: string;
  details?: any;
} {
  switch (error.code) {
    case 'P2002':
      return {
        statusCode: 409,
        message: 'A record with this information already exists',
        type: 'conflict',
        details: {
          constraint: error.meta?.target,
          fields: error.meta?.target,
          hint: 'Try using different values for the conflicting fields',
        },
      };

    case 'P2025':
      return {
        statusCode: 404,
        message: 'The requested record was not found',
        type: 'not_found',
        details: {
          cause: error.meta?.cause,
          hint: 'Verify the ID is correct and the record exists',
        },
      };

    case 'P2003':
      return {
        statusCode: 400,
        message: 'Invalid reference to related record',
        type: 'constraint_violation',
        details: {
          field: error.meta?.field_name,
          hint: 'Ensure the referenced record exists',
        },
      };

    case 'P2004':
      return {
        statusCode: 400,
        message: 'Database constraint violation',
        type: 'constraint_violation',
        details: { constraint: error.meta?.constraint },
      };

    case 'P2016':
      return {
        statusCode: 400,
        message: 'Query interpretation error',
        type: 'query_error',
        details: { hint: 'Check your query parameters and format' },
      };

    case 'P2021':
      return {
        statusCode: 500,
        message: 'Database table does not exist',
        type: 'database_error',
        details: { table: error.meta?.table },
      };

    case 'P2022':
      return {
        statusCode: 500,
        message: 'Database column does not exist',
        type: 'database_error',
        details: { column: error.meta?.column },
      };

    default:
      return {
        statusCode: 500,
        message: 'Database operation failed',
        type: 'database_error',
        details: {
          code: error.code,
          hint: 'Please try again or contact support if the issue persists',
        },
      };
  }
}

/**
 * Handle Multer file upload errors with detailed messages
 */
function handleMulterError(error: MulterError): {
  statusCode: number;
  message: string;
  type: string;
  details?: any;
} {
  switch (error.code) {
    case 'LIMIT_FILE_SIZE':
      return {
        statusCode: 413,
        message: 'File size exceeds the maximum allowed limit',
        type: 'file_too_large',
        details: {
          maxSize: '10MB',
          hint: 'Compress your file or upload a smaller version',
        },
      };

    case 'LIMIT_FILE_COUNT':
      return {
        statusCode: 400,
        message: 'Too many files uploaded',
        type: 'too_many_files',
        details: {
          maxFiles: 10,
          hint: 'Upload files in smaller batches',
        },
      };

    case 'LIMIT_FIELD_KEY':
      return {
        statusCode: 400,
        message: 'Field name too long',
        type: 'invalid_field',
        details: { hint: 'Use shorter field names' },
      };

    case 'LIMIT_FIELD_VALUE':
      return {
        statusCode: 400,
        message: 'Field value too long',
        type: 'invalid_field',
        details: { hint: 'Reduce the size of your form data' },
      };

    case 'LIMIT_FIELD_COUNT':
      return {
        statusCode: 400,
        message: 'Too many form fields',
        type: 'too_many_fields',
        details: { hint: 'Reduce the number of form fields' },
      };

    case 'LIMIT_UNEXPECTED_FILE':
      return {
        statusCode: 400,
        message: 'Unexpected file field in upload',
        type: 'unexpected_file',
        details: {
          field: error.field,
          hint: 'Check the file field name matches the expected field',
        },
      };

    default:
      return {
        statusCode: 400,
        message: 'File upload error',
        type: 'upload_error',
        details: { hint: 'Check your file format and try again' },
      };
  }
}

/**
 * Get error type from error object
 */
function getErrorType(error: EnhancedApiError): string {
  if (error.statusCode === 400) return 'bad_request';
  if (error.statusCode === 401) return 'authentication_error';
  if (error.statusCode === 403) return 'forbidden';
  if (error.statusCode === 404) return 'not_found';
  if (error.statusCode === 409) return 'conflict';
  if (error.statusCode === 422) return 'validation_error';
  if (error.statusCode === 429) return 'rate_limit_exceeded';
  if (error.statusCode === 500) return 'internal_error';
  return 'api_error';
}

/**
 * Sanitize sensitive data for logging
 */
function sanitizeForLogging(obj: any): any {
  if (!obj || typeof obj !== 'object') {
    return obj;
  }

  const sensitiveFields = [
    'password',
    'token',
    'accessToken',
    'refreshToken',
    'secret',
    'key',
    'authorization',
    'cookie',
    'session',
    'csrf',
  ];

  const sanitized = { ...obj };

  for (const field of sensitiveFields) {
    if (sanitized[field]) {
      sanitized[field] = '[REDACTED]';
    }
  }

  // Also check nested objects
  for (const [key, value] of Object.entries(sanitized)) {
    if (value && typeof value === 'object') {
      sanitized[key] = sanitizeForLogging(value);
    }
  }

  return sanitized;
}

/**
 * Get route suggestions for 404 errors
 */
function getRouteSuggestions(requestedPath: string): string[] {
  const commonRoutes = [
    '/api/v1/auth/login',
    '/api/v1/auth/register',
    '/api/v1/boards',
    '/api/v1/items',
    '/api/v1/workspaces',
    '/api/v1/organizations',
    '/api/v1/comments',
    '/api/v1/files',
    '/api/v1/ai',
    '/api/v1/automation',
    '/health',
  ];

  // Calculate similarity and return top matches
  return commonRoutes
    .map(route => ({
      route,
      similarity: calculateSimilarity(requestedPath.toLowerCase(), route.toLowerCase()),
    }))
    .filter(({ similarity }) => similarity > 0.3)
    .sort((a, b) => b.similarity - a.similarity)
    .slice(0, 3)
    .map(({ route }) => route);
}

/**
 * Calculate string similarity using Levenshtein distance
 */
function calculateSimilarity(str1: string, str2: string): number {
  const len1 = str1.length;
  const len2 = str2.length;

  if (len1 === 0) return len2 === 0 ? 1 : 0;
  if (len2 === 0) return 0;

  const matrix = Array(len1 + 1).fill(null).map(() => Array(len2 + 1).fill(null));

  for (let i = 0; i <= len1; i++) matrix[i][0] = i;
  for (let j = 0; j <= len2; j++) matrix[0][j] = j;

  for (let i = 1; i <= len1; i++) {
    for (let j = 1; j <= len2; j++) {
      const cost = str1[i - 1] === str2[j - 1] ? 0 : 1;
      matrix[i][j] = Math.min(
        matrix[i - 1][j] + 1,
        matrix[i][j - 1] + 1,
        matrix[i - 1][j - 1] + cost
      );
    }
  }

  const maxLen = Math.max(len1, len2);
  return (maxLen - matrix[len1][len2]) / maxLen;
}