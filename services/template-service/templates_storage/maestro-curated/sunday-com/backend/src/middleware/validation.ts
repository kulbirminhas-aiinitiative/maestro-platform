import { Request, Response, NextFunction } from 'express';
import Joi from 'joi';
import { Logger } from '@/config/logger';

/**
 * Joi validation middleware factory
 */
export const validate = (schema: Joi.ObjectSchema, target: 'body' | 'params' | 'query' = 'body') => {
  return (req: Request, res: Response, next: NextFunction): void => {
    const { error, value } = schema.validate(req[target], {
      abortEarly: false,
      stripUnknown: true,
    });

    if (error) {
      const validationErrors = error.details.map((detail) => ({
        field: detail.path.join('.'),
        message: detail.message,
        value: detail.context?.value,
      }));

      Logger.api('Validation failed', { errors: validationErrors, target });

      res.status(422).json({
        error: {
          type: 'validation_error',
          message: 'Invalid input parameters',
          details: validationErrors,
        },
      });
      return;
    }

    // Replace the original data with validated/sanitized data
    req[target] = value;
    next();
  };
};

// ============================================================================
// COMMON VALIDATION SCHEMAS
// ============================================================================

// UUID validation
export const uuidSchema = Joi.string().uuid().required();
export const optionalUuidSchema = Joi.string().uuid().optional();

// Pagination schemas
export const paginationSchema = Joi.object({
  page: Joi.number().integer().min(1).default(1),
  limit: Joi.number().integer().min(1).max(100).default(20),
});

export const cursorPaginationSchema = Joi.object({
  cursor: Joi.string().optional(),
  limit: Joi.number().integer().min(1).max(100).default(20),
});

// Sort schema
export const sortSchema = Joi.object({
  field: Joi.string().required(),
  direction: Joi.string().valid('asc', 'desc').default('asc'),
});

// ============================================================================
// AUTH VALIDATION SCHEMAS
// ============================================================================

export const loginSchema = Joi.object({
  email: Joi.string().email().required(),
  password: Joi.string().min(8).required(),
});

export const registerSchema = Joi.object({
  email: Joi.string().email().required(),
  password: Joi.string().min(8).pattern(new RegExp('^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]')).required()
    .messages({
      'string.pattern.base': 'Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character',
    }),
  firstName: Joi.string().max(100).optional(),
  lastName: Joi.string().max(100).optional(),
});

export const refreshTokenSchema = Joi.object({
  refreshToken: Joi.string().required(),
});

export const forgotPasswordSchema = Joi.object({
  email: Joi.string().email().required(),
});

export const resetPasswordSchema = Joi.object({
  token: Joi.string().required(),
  password: Joi.string().min(8).pattern(new RegExp('^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]')).required(),
});

// ============================================================================
// ORGANIZATION VALIDATION SCHEMAS
// ============================================================================

export const createOrganizationSchema = Joi.object({
  name: Joi.string().min(1).max(255).required(),
  slug: Joi.string().min(3).max(100).pattern(/^[a-z0-9-]+$/).required()
    .messages({
      'string.pattern.base': 'Slug must contain only lowercase letters, numbers, and hyphens',
    }),
  domain: Joi.string().domain().optional(),
  settings: Joi.object().optional(),
});

export const updateOrganizationSchema = Joi.object({
  name: Joi.string().min(1).max(255).optional(),
  domain: Joi.string().domain().optional().allow(null),
  settings: Joi.object().optional(),
  subscriptionPlan: Joi.string().valid('free', 'pro', 'enterprise').optional(),
});

export const inviteMemberSchema = Joi.object({
  email: Joi.string().email().required(),
  role: Joi.string().valid('owner', 'admin', 'member').default('member'),
  message: Joi.string().max(500).optional(),
});

// ============================================================================
// WORKSPACE VALIDATION SCHEMAS
// ============================================================================

export const createWorkspaceSchema = Joi.object({
  name: Joi.string().min(1).max(255).required(),
  description: Joi.string().max(1000).optional(),
  color: Joi.string().pattern(/^#[0-9A-Fa-f]{6}$/).default('#6B7280'),
  isPrivate: Joi.boolean().default(false),
  settings: Joi.object().optional(),
});

export const updateWorkspaceSchema = Joi.object({
  name: Joi.string().min(1).max(255).optional(),
  description: Joi.string().max(1000).optional().allow(null),
  color: Joi.string().pattern(/^#[0-9A-Fa-f]{6}$/).optional(),
  isPrivate: Joi.boolean().optional(),
  settings: Joi.object().optional(),
});

// ============================================================================
// BOARD VALIDATION SCHEMAS
// ============================================================================

export const createBoardSchema = Joi.object({
  name: Joi.string().min(1).max(255).required(),
  description: Joi.string().max(1000).optional(),
  templateId: Joi.string().uuid().optional(),
  folderId: Joi.string().uuid().optional(),
  isPrivate: Joi.boolean().default(false),
  settings: Joi.object().optional(),
});

export const updateBoardSchema = Joi.object({
  name: Joi.string().min(1).max(255).optional(),
  description: Joi.string().max(1000).optional().allow(null),
  folderId: Joi.string().uuid().optional().allow(null),
  isPrivate: Joi.boolean().optional(),
  settings: Joi.object().optional(),
  viewSettings: Joi.object().optional(),
});

export const createBoardColumnSchema = Joi.object({
  name: Joi.string().min(1).max(255).required(),
  columnType: Joi.string().valid(
    'text', 'number', 'status', 'date', 'people', 'timeline', 'files', 'checkbox', 'rating', 'email', 'phone', 'url'
  ).required(),
  settings: Joi.object().optional(),
  validationRules: Joi.object().optional(),
  position: Joi.number().integer().min(0).required(),
  isRequired: Joi.boolean().default(false),
  isVisible: Joi.boolean().default(true),
});

// ============================================================================
// ITEM VALIDATION SCHEMAS
// ============================================================================

export const createItemSchema = Joi.object({
  name: Joi.string().min(1).max(500).required(),
  description: Joi.string().max(10000).optional(),
  parentId: Joi.string().uuid().optional(),
  data: Joi.object().optional(),
  position: Joi.number().optional(),
  assigneeIds: Joi.array().items(Joi.string().uuid()).optional(),
});

export const updateItemSchema = Joi.object({
  name: Joi.string().min(1).max(500).optional(),
  description: Joi.string().max(10000).optional().allow(null),
  parentId: Joi.string().uuid().optional().allow(null),
  data: Joi.object().optional(),
  position: Joi.number().optional(),
  assigneeIds: Joi.array().items(Joi.string().uuid()).optional(),
});

export const bulkUpdateItemsSchema = Joi.object({
  itemIds: Joi.array().items(Joi.string().uuid()).min(1).max(100).required(),
  updates: Joi.object({
    data: Joi.object().optional(),
    assigneeIds: Joi.array().items(Joi.string().uuid()).optional(),
    position: Joi.number().optional(),
  }).min(1).required(),
});

export const itemFilterSchema = Joi.object({
  parentId: Joi.string().uuid().optional(),
  assigneeIds: Joi.array().items(Joi.string().uuid()).optional(),
  status: Joi.array().items(Joi.string()).optional(),
  dueDateFrom: Joi.date().optional(),
  dueDateTo: Joi.date().optional(),
  search: Joi.string().max(255).optional(),
  tags: Joi.array().items(Joi.string()).optional(),
});

// ============================================================================
// COMMENT VALIDATION SCHEMAS
// ============================================================================

export const createCommentSchema = Joi.object({
  content: Joi.string().min(1).max(10000).required(),
  parentId: Joi.string().uuid().optional(),
  mentions: Joi.array().items(Joi.string().uuid()).optional(),
  attachments: Joi.array().items(Joi.string().uuid()).optional(),
});

export const updateCommentSchema = Joi.object({
  content: Joi.string().min(1).max(10000).required(),
});

// ============================================================================
// TIME TRACKING VALIDATION SCHEMAS
// ============================================================================

export const createTimeEntrySchema = Joi.object({
  description: Joi.string().max(500).optional(),
  startTime: Joi.date().required(),
  endTime: Joi.date().optional(),
  durationSeconds: Joi.number().integer().min(0).optional(),
  isBillable: Joi.boolean().default(false),
});

export const updateTimeEntrySchema = Joi.object({
  description: Joi.string().max(500).optional(),
  startTime: Joi.date().optional(),
  endTime: Joi.date().optional(),
  durationSeconds: Joi.number().integer().min(0).optional(),
  isBillable: Joi.boolean().optional(),
});

// ============================================================================
// WEBHOOK VALIDATION SCHEMAS
// ============================================================================

export const createWebhookSchema = Joi.object({
  url: Joi.string().uri().required(),
  events: Joi.array().items(Joi.string()).min(1).required(),
  secret: Joi.string().min(16).required(),
  filters: Joi.object().optional(),
});

export const updateWebhookSchema = Joi.object({
  url: Joi.string().uri().optional(),
  events: Joi.array().items(Joi.string()).min(1).optional(),
  secret: Joi.string().min(16).optional(),
  isActive: Joi.boolean().optional(),
  filters: Joi.object().optional(),
});

// ============================================================================
// AUTOMATION VALIDATION SCHEMAS
// ============================================================================

export const createAutomationRuleSchema = Joi.object({
  name: Joi.string().min(1).max(255).required(),
  description: Joi.string().max(1000).optional(),
  triggerConfig: Joi.object().required(),
  conditionConfig: Joi.object().optional(),
  actionConfig: Joi.object().required(),
  isEnabled: Joi.boolean().default(true),
});

export const updateAutomationRuleSchema = Joi.object({
  name: Joi.string().min(1).max(255).optional(),
  description: Joi.string().max(1000).optional(),
  triggerConfig: Joi.object().optional(),
  conditionConfig: Joi.object().optional(),
  actionConfig: Joi.object().optional(),
  isEnabled: Joi.boolean().optional(),
});

// ============================================================================
// FILE UPLOAD VALIDATION SCHEMAS
// ============================================================================

export const fileUploadSchema = Joi.object({
  entityType: Joi.string().valid('item', 'comment', 'board').required(),
  entityId: Joi.string().uuid().required(),
});