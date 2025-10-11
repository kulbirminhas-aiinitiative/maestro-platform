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
  organizationId: string;
  color?: string;
  isPrivate?: boolean;
  settings?: Record<string, any>;
}

export interface UpdateWorkspaceData {
  name?: string;
  description?: string;
  color?: string;
  isPrivate?: boolean;
  settings?: Record<string, any>;
}

export interface CreateBoardData {
  name: string;
  description?: string;
  workspaceId: string;
  templateId?: string;
  folderId?: string;
  isPrivate?: boolean;
  settings?: Record<string, any>;
  columns?: CreateBoardColumnData[];
}

export interface UpdateBoardData {
  name?: string;
  description?: string;
  folderId?: string;
  isPrivate?: boolean;
  settings?: Record<string, any>;
  position?: number;
}

export interface CreateBoardColumnData {
  name: string;
  color?: string;
  position?: number;
  settings?: Record<string, any>;
}

export interface UpdateBoardColumnData {
  name?: string;
  color?: string;
  position?: number;
  settings?: Record<string, any>;
}

export interface CreateItemData {
  name: string;
  description?: string;
  boardId: string;
  parentId?: string;
  itemData?: Record<string, any>;
  position?: number;
  assigneeIds?: string[];
}

export interface UpdateItemData {
  name?: string;
  description?: string;
  parentId?: string;
  itemData?: Record<string, any>;
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

export interface ItemSort {
  field: 'position' | 'created_at' | 'updated_at' | 'name' | 'due_date';
  direction: 'asc' | 'desc';
}

export interface PaginationOptions {
  limit?: number;
  cursor?: string;
  search?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  pagination: {
    nextCursor?: string | null;
    hasMore: boolean;
    totalCount: number;
  };
}

export interface WorkspaceWithDetails {
  id: string;
  organizationId: string;
  name: string;
  description?: string;
  color?: string;
  isPrivate: boolean;
  settings: Record<string, any>;
  createdAt: Date;
  updatedAt: Date;
  organization: {
    id: string;
    name: string;
    slug: string;
  };
  members: Array<{
    id: string;
    role: string;
    permissions: Record<string, any>;
    user: {
      id: string;
      email: string;
      firstName?: string;
      lastName?: string;
      avatarUrl?: string;
    };
    createdAt: Date;
  }>;
  boards?: Array<{
    id: string;
    name: string;
    description?: string;
    isPrivate: boolean;
    createdAt: Date;
    creator?: {
      id: string;
      firstName?: string;
      lastName?: string;
      avatarUrl?: string;
    };
    stats?: {
      itemCount: number;
      memberCount: number;
    };
  }>;
  recentBoards?: Array<{
    id: string;
    name: string;
    isPrivate: boolean;
    createdAt: Date;
  }>;
  folders?: Array<{
    id: string;
    name: string;
    color?: string;
    position: number;
  }>;
  stats: {
    boardCount: number;
    memberCount: number;
  };
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

// ============================================================================
// TIME TRACKING TYPES
// ============================================================================

export interface CreateTimeEntryData {
  itemId?: string;
  boardId?: string;
  description?: string;
  billable?: boolean;
  metadata?: Record<string, any>;
}

export interface UpdateTimeEntryData {
  description?: string;
  duration?: number;
  billable?: boolean;
  metadata?: Record<string, any>;
}

export interface TimeEntryFilter {
  userId?: string;
  itemId?: string;
  boardId?: string;
  billable?: boolean;
  isRunning?: boolean;
  startDate?: string;
  endDate?: string;
}

// ============================================================================
// ANALYTICS TYPES (EXTENDED)
// ============================================================================

export interface AnalyticsFilter {
  organizationId?: string;
  workspaceId?: string;
  boardId?: string;
  userId?: string;
  startDate?: Date;
  endDate?: Date;
  metrics?: string[];
  groupBy?: string;
  filters?: Record<string, any>;
}

export interface AnalyticsMetrics {
  organizationId: string;
  period: string;
  dateRange: {
    start: Date;
    end: Date;
  };
  userMetrics: {
    totalUsers: number;
    activeUsers: number;
    userGrowth: number;
  };
  workspaceMetrics: {
    totalWorkspaces: number;
    averageBoardsPerWorkspace: number;
  };
  itemMetrics: {
    totalItems: number;
    completedItems: number;
    completionRate: number;
  };
  timeMetrics: {
    totalTimeSpent: number;
    averageTimePerUser: number;
  };
  collaborationMetrics: {
    totalComments: number;
    totalFiles: number;
    averageCommentsPerItem: number;
  };
  generatedAt: Date;
}

export interface BoardAnalytics {
  boardId: string;
  period: string;
  dateRange: {
    start: Date;
    end: Date;
  };
  itemMetrics: {
    totalItems: number;
    completedItems: number;
    inProgressItems: number;
    createdInPeriod: number;
    completedInPeriod: number;
    completionRate: number;
  };
  activityMetrics: {
    totalActivities: number;
    uniqueActiveUsers: number;
    commentsCount: number;
    filesUploadedCount: number;
  };
  memberMetrics: {
    totalMembers: number;
    adminCount: number;
    memberCount: number;
  };
  timeMetrics: {
    totalTimeSpent: number;
    billableTime: number;
    timeEntriesCount: number;
    averageSessionDuration: number;
  };
  velocityMetrics: {
    velocityData: Array<{
      period: string;
      completed: number;
    }>;
    averageVelocity: number;
    trend: 'up' | 'down' | 'stable';
  };
  generatedAt: Date;
}

export interface UserActivityReport {
  userId: string;
  period: string;
  dateRange: {
    start: Date;
    end: Date;
  };
  activitySummary: {
    itemsCreated: number;
    itemsCompleted: number;
    commentsPosted: number;
    collaborations: number;
  };
  itemsWorked: any[];
  timeSpent: {
    totalTime: number;
    billableTime: number;
    projectBreakdown: any[];
  };
  collaborationMetrics: {
    boardsCollaboratedOn: number;
    usersCollaboratedWith: number;
    commentsReceived: number;
  };
  productivityTrends: {
    weeklyTrends: any[];
    productivityScore: number;
  };
  generatedAt: Date;
}

export interface TeamProductivityReport {
  workspaceId: string;
  period: string;
  dateRange: {
    start: Date;
    end: Date;
  };
  teamOverview: {
    totalMembers: number;
    activeMembers: number;
    totalBoards: number;
    totalItems: number;
    completedItems: number;
  };
  memberPerformance: any[];
  boardsProgress: any[];
  timeDistribution: {
    totalTime: number;
    byMember: any[];
    byProject: any[];
  };
  collaborationInsights: {
    communicationIndex: number;
    crossBoardCollaboration: number;
    responseTime: number;
  };
  generatedAt: Date;
}

// ============================================================================
// WEBHOOK TYPES (EXTENDED)
// ============================================================================

export interface CreateWebhookData {
  url: string;
  events: string[];
  organizationId?: string;
  workspaceId?: string;
  boardId?: string;
  description?: string;
  contentType?: 'application/json' | 'application/x-www-form-urlencoded';
  headers?: Record<string, string>;
}

export interface UpdateWebhookData {
  url?: string;
  events?: string[];
  description?: string;
  isActive?: boolean;
  contentType?: 'application/json' | 'application/x-www-form-urlencoded';
  headers?: Record<string, string>;
}

export interface WebhookEvent {
  type: string;
  data: Record<string, any>;
  timestamp: Date;
}

export interface WebhookDelivery {
  id: string;
  webhookId: string;
  eventType: string;
  payload: Record<string, any>;
  status: 'pending' | 'delivered' | 'failed';
  attempt: number;
  responseStatus?: number;
  responseHeaders?: string;
  responseBody?: string;
  errorMessage?: string;
  createdAt: Date;
  deliveredAt?: Date;
  failedAt?: Date;
}