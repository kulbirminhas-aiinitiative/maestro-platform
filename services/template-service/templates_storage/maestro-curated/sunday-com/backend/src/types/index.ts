import { Request } from 'express';
import { User } from '@prisma/client';

// ============================================================================
// API TYPES
// ============================================================================

export interface ApiResponse<T = any> {
  data?: T;
  error?: ApiError;
  meta?: {
    pagination?: PaginationMeta;
    total?: number;
    [key: string]: any;
  };
}

export interface ApiError {
  type: string;
  message: string;
  details?: Record<string, any>;
  requestId?: string;
  stack?: string;
}

export interface PaginationMeta {
  page: number;
  limit: number;
  total: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}

export interface CursorPaginationMeta {
  nextCursor?: string;
  hasMore: boolean;
  totalCount?: number;
}

// ============================================================================
// AUTH TYPES
// ============================================================================

export interface AuthenticatedRequest extends Request {
  user?: AuthUser;
  organization?: {
    id: string;
    role: string;
    permissions: string[];
  };
}

export interface AuthUser {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
  avatarUrl?: string;
  organizations: UserOrganization[];
}

export interface UserOrganization {
  id: string;
  name: string;
  role: string;
  permissions: string[];
}

export interface JwtPayload {
  sub: string; // user id
  email: string;
  iat: number;
  exp: number;
  orgId?: string;
  permissions?: string[];
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  firstName?: string;
  lastName?: string;
}

export interface AuthTokens {
  accessToken: string;
  refreshToken: string;
  expiresIn: number;
}

// ============================================================================
// PERMISSION TYPES
// ============================================================================

export interface Permission {
  resource: string;
  action: string;
  conditions?: Record<string, any>;
}

export interface RolePermissions {
  role: string;
  permissions: Permission[];
}

export interface UserPermissions {
  organization: {
    id: string;
    role: string;
    permissions: string[];
  };
  workspaces: Array<{
    id: string;
    role: string;
    permissions: string[];
  }>;
  boards: Array<{
    id: string;
    permissions: string[];
  }>;
}

// ============================================================================
// BUSINESS DOMAIN TYPES
// ============================================================================

export interface CreateOrganizationData {
  name: string;
  slug: string;
  domain?: string;
  settings?: Record<string, any>;
}

export interface CreateWorkspaceData {
  name: string;
  description?: string;
  color?: string;
  isPrivate?: boolean;
  settings?: Record<string, any>;
}

export interface CreateBoardData {
  name: string;
  description?: string;
  templateId?: string;
  folderId?: string;
  isPrivate?: boolean;
  settings?: Record<string, any>;
}

export interface CreateItemData {
  name: string;
  description?: string;
  parentId?: string;
  data?: Record<string, any>;
  position?: number;
  assigneeIds?: string[];
}

export interface UpdateItemData {
  name?: string;
  description?: string;
  data?: Record<string, any>;
  position?: number;
  assigneeIds?: string[];
}

export interface BulkUpdateItemsData {
  itemIds: string[];
  updates: Partial<UpdateItemData>;
}

export interface CreateCommentData {
  content: string;
  parentId?: string;
  mentions?: string[];
  attachments?: string[];
}

export interface CreateTimeEntryData {
  description?: string;
  startTime: Date;
  endTime?: Date;
  durationSeconds?: number;
  isBillable?: boolean;
}

// ============================================================================
// FILTER & SEARCH TYPES
// ============================================================================

export interface ItemFilter {
  parentId?: string;
  assigneeIds?: string[];
  status?: string[];
  dueDateFrom?: Date;
  dueDateTo?: Date;
  search?: string;
  tags?: string[];
}

export interface BoardFilter {
  name?: string;
  isPrivate?: boolean;
  folderId?: string;
  workspaceId?: string;
}

export interface WorkspaceFilter {
  name?: string;
  isPrivate?: boolean;
  organizationId?: string;
}

export interface SortOption {
  field: string;
  direction: 'asc' | 'desc';
}

export interface SearchQuery {
  query: string;
  filters?: Record<string, any>;
  sort?: SortOption[];
  limit?: number;
  offset?: number;
}

// ============================================================================
// WEBSOCKET TYPES
// ============================================================================

export interface WebSocketMessage {
  type: string;
  channel?: string;
  data?: any;
  timestamp?: string;
}

export interface WebSocketSubscription {
  channel: string;
  userId: string;
  connectionId: string;
  subscriptionId: string;
  filters?: Record<string, any>;
}

export interface UserPresence {
  userId: string;
  username: string;
  avatarUrl?: string;
  cursor?: {
    x: number;
    y: number;
  };
  lastSeen: Date;
}

// ============================================================================
// WEBHOOK TYPES
// ============================================================================

export interface WebhookPayload {
  event: string;
  timestamp: string;
  data: Record<string, any>;
}

export interface WebhookConfig {
  url: string;
  events: string[];
  secret: string;
  active: boolean;
  filters?: Record<string, any>;
}

// ============================================================================
// ANALYTICS TYPES
// ============================================================================

export interface AnalyticsEvent {
  eventType: string;
  userId: string;
  organizationId: string;
  workspaceId?: string;
  boardId?: string;
  itemId?: string;
  properties?: Record<string, any>;
  timestamp?: Date;
}

export interface AnalyticsQuery {
  startDate: Date;
  endDate: Date;
  organizationId: string;
  workspaceId?: string;
  boardId?: string;
  metrics: string[];
  groupBy?: string[];
}

export interface AnalyticsResult {
  metrics: Record<string, number>;
  trends: Array<{
    date: string;
    values: Record<string, number>;
  }>;
}

// ============================================================================
// FILE UPLOAD TYPES
// ============================================================================

export interface FileUploadData {
  originalName: string;
  mimeType: string;
  fileSize: number;
  buffer: Buffer;
}

export interface UploadedFile {
  id: string;
  originalName: string;
  fileKey: string;
  fileSize: number;
  mimeType?: string;
  url: string;
  thumbnailUrl?: string;
}

// ============================================================================
// AUTOMATION TYPES
// ============================================================================

export interface AutomationTrigger {
  type: string;
  conditions: Record<string, any>;
}

export interface AutomationAction {
  type: string;
  parameters: Record<string, any>;
}

export interface AutomationRuleData {
  name: string;
  description?: string;
  trigger: AutomationTrigger;
  conditions?: Record<string, any>;
  actions: AutomationAction[];
  isEnabled?: boolean;
}

// ============================================================================
// VALIDATION TYPES
// ============================================================================

export interface ValidationError {
  field: string;
  message: string;
  value?: any;
}

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
}

// ============================================================================
// HEALTH CHECK TYPES
// ============================================================================

export interface HealthCheckResult {
  status: 'healthy' | 'unhealthy' | 'degraded';
  timestamp: string;
  services: {
    database: boolean;
    redis: boolean;
    elasticsearch?: boolean;
    clickhouse?: boolean;
  };
  version: string;
  uptime: number;
}

// ============================================================================
// EXPORT UTILITY TYPES
// ============================================================================

export type WithId<T> = T & { id: string };
export type WithTimestamps<T> = T & {
  createdAt: Date;
  updatedAt: Date;
};
export type WithSoftDelete<T> = T & { deletedAt?: Date | null };

export type CreateModel<T> = Omit<T, 'id' | 'createdAt' | 'updatedAt'>;
export type UpdateModel<T> = Partial<Omit<T, 'id' | 'createdAt' | 'updatedAt'>>;

export type PaginatedResult<T> = {
  data: T[];
  meta: PaginationMeta;
};

export type CursorPaginatedResult<T> = {
  data: T[];
  meta: CursorPaginationMeta;
};