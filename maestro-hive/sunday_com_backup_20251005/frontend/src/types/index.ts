// User types
export interface User {
  id: string
  email: string
  firstName?: string
  lastName?: string
  fullName: string
  avatarUrl?: string
  timezone: string
  locale: string
  settings: Record<string, any>
  lastLoginAt?: string
  createdAt: string
  updatedAt: string
  organizations?: UserOrganization[]
}

export interface UserOrganization {
  id: string
  name: string
  role: OrganizationRole
  permissions: string[]
}

// Organization types
export interface Organization {
  id: string
  name: string
  slug: string
  domain?: string
  settings: Record<string, any>
  subscriptionPlan: SubscriptionPlan
  subscriptionStatus: SubscriptionStatus
  createdAt: string
  updatedAt: string
  _count?: {
    members: number
    workspaces: number
  }
  members?: OrganizationMember[]
  workspaces?: Workspace[]
}

export interface OrganizationMember {
  id: string
  role: OrganizationRole
  status: MembershipStatus
  joinedAt?: string
  createdAt: string
  user: User
}

export type OrganizationRole = 'owner' | 'admin' | 'member'
export type SubscriptionPlan = 'free' | 'pro' | 'enterprise'
export type SubscriptionStatus = 'active' | 'cancelled' | 'past_due'
export type MembershipStatus = 'active' | 'invited' | 'suspended'

// Workspace types
export interface Workspace {
  id: string
  organizationId: string
  name: string
  description?: string
  color: string
  isPrivate: boolean
  settings: Record<string, any>
  createdAt: string
  updatedAt: string
  organization?: Organization
  boards?: Board[]
  members?: WorkspaceMember[]
}

export interface WorkspaceMember {
  id: string
  workspaceId: string
  userId: string
  role: WorkspaceRole
  joinedAt: string
  user: User
}

export type WorkspaceRole = 'admin' | 'member' | 'viewer'

// Board types
export interface Board {
  id: string
  workspaceId: string
  name: string
  description?: string
  settings: Record<string, any>
  viewSettings: Record<string, any>
  isPrivate: boolean
  folderId?: string
  position?: number
  createdAt: string
  updatedAt: string
  workspace?: Workspace
  folder?: Folder
  columns?: BoardColumn[]
  items?: Item[]
  members?: BoardMember[]
  createdBy?: User
}

export interface BoardColumn {
  id: string
  boardId: string
  name: string
  columnType: ColumnType
  settings: Record<string, any>
  validationRules: Record<string, any>
  position: number
  isRequired: boolean
  isVisible: boolean
  createdAt: string
}

export interface BoardMember {
  id: string
  boardId: string
  userId: string
  role: BoardRole
  joinedAt: string
  user: User
}

export type ColumnType =
  | 'text'
  | 'number'
  | 'status'
  | 'date'
  | 'people'
  | 'timeline'
  | 'files'
  | 'checkbox'
  | 'rating'
  | 'email'
  | 'phone'
  | 'url'

export type BoardRole = 'admin' | 'member' | 'viewer'

// Item types
export interface Item {
  id: string
  boardId: string
  parentId?: string
  name: string
  description?: string
  data: Record<string, any>
  position: number
  createdAt: string
  updatedAt: string
  board?: Board
  parent?: Item
  assignees?: User[]
  dependencies?: ItemDependency[]
  comments?: Comment[]
  attachments?: FileAttachment[]
  timeEntries?: TimeEntry[]
  subtasks?: Item[]
  createdBy?: User
}

export interface ItemDependency {
  id: string
  predecessorId: string
  successorId: string
  dependencyType: DependencyType
  createdAt: string
  predecessor: Item
  successor: Item
  createdBy: User
}

export type DependencyType = 'blocks' | 'related'

// Comment types
export interface Comment {
  id: string
  itemId: string
  parentId?: string
  userId: string
  content: string
  contentType: ContentType
  isEdited: boolean
  createdAt: string
  updatedAt: string
  item: Item
  parent?: Comment
  user: User
  mentions?: User[]
  attachments?: FileAttachment[]
  replies?: Comment[]
}

export type ContentType = 'text' | 'markdown'

// File types
export interface File {
  id: string
  originalName: string
  fileKey: string
  fileSize: number
  mimeType?: string
  thumbnailKey?: string
  createdAt: string
  uploadedBy: User
}

export interface FileAttachment {
  id: string
  fileId: string
  entityType: string
  entityId: string
  attachedAt: string
  file: File
  attachedBy: User
}

// Time tracking types
export interface TimeEntry {
  id: string
  itemId: string
  userId: string
  description?: string
  startTime: string
  endTime?: string
  durationSeconds?: number
  isBillable: boolean
  createdAt: string
  updatedAt: string
  item: Item
  user: User
}

// Folder types
export interface Folder {
  id: string
  workspaceId: string
  parentId?: string
  name: string
  color?: string
  position: number
  createdAt: string
  updatedAt: string
  workspace: Workspace
  parent?: Folder
  children?: Folder[]
  boards?: Board[]
}

// API Response types
export interface ApiResponse<T> {
  data: T
  meta?: any
}

export interface PaginatedResponse<T> {
  data: T[]
  meta: {
    pagination: {
      page: number
      limit: number
      total: number
      totalPages: number
      hasNext: boolean
      hasPrev: boolean
    }
  }
}

export interface ApiError {
  error: {
    type: string
    message: string
    details?: Record<string, any>
    requestId?: string
  }
}

// Authentication types
export interface AuthTokens {
  accessToken: string
  refreshToken: string
  expiresIn: number
}

export interface LoginCredentials {
  email: string
  password: string
}

export interface RegisterData {
  email: string
  password: string
  firstName?: string
  lastName?: string
}

// Form types
export interface CreateOrganizationData {
  name: string
  slug: string
  domain?: string
  settings?: Record<string, any>
}

export interface UpdateOrganizationData {
  name?: string
  domain?: string
  settings?: Record<string, any>
}

export interface InviteMemberData {
  email: string
  role?: OrganizationRole
  message?: string
}

export interface CreateWorkspaceData {
  name: string
  description?: string
  color?: string
  isPrivate?: boolean
  settings?: Record<string, any>
}

export interface CreateBoardData {
  name: string
  description?: string
  templateId?: string
  folderId?: string
  settings?: Record<string, any>
}

export interface CreateItemData {
  name: string
  description?: string
  parentId?: string
  data?: Record<string, any>
  position?: number
  assigneeIds?: string[]
}

export interface UpdateItemData {
  name?: string
  description?: string
  data?: Record<string, any>
  position?: number
  assigneeIds?: string[]
}

// Filter and sort types
export interface ItemFilter {
  parentId?: string
  assigneeIds?: string[]
  status?: string[]
  dueDateFrom?: string
  dueDateTo?: string
  search?: string
}

export interface ItemSort {
  field: ItemSortField
  direction: SortDirection
}

export type ItemSortField = 'position' | 'created_at' | 'updated_at' | 'due_date' | 'name'
export type SortDirection = 'asc' | 'desc'

// Real-time types
export interface WebSocketMessage {
  type: string
  channel?: string
  data: any
  timestamp: string
}

export interface UserPresence {
  userId: string
  username: string
  avatarUrl?: string
  cursor?: {
    x: number
    y: number
  }
  lastSeen: string
}

// UI State types
export interface UIState {
  theme: 'light' | 'dark' | 'system'
  sidebarCollapsed: boolean
  activeWorkspace?: string
  activeBoard?: string
  selectedItems: string[]
  loading: Record<string, boolean>
  errors: Record<string, string>
}

// View types
export type BoardView = 'table' | 'kanban' | 'timeline' | 'calendar' | 'chart'

export interface ViewSettings {
  view: BoardView
  filters: ItemFilter
  sorts: ItemSort[]
  groupBy?: string
  columns?: string[]
}

// Analytics types
export interface AnalyticsData {
  totalItems: number
  completedItems: number
  activeUsers: number
  averageCompletionTime?: number
  productivityScore?: number
  trends: AnalyticsTrend[]
}

export interface AnalyticsTrend {
  date: string
  value: number
  metric: string
}

// Extended Analytics types
export interface BoardAnalytics {
  boardId: string
  boardName: string
  totalItems: number
  completedItems: number
  completionRate: number
  averageTimeToComplete: number
  velocity: VelocityMetrics
  memberActivity: MemberActivity[]
  itemDistribution: StatusDistribution[]
  trends: AnalyticsTrend[]
}

export interface VelocityMetrics {
  itemsCompletedLastWeek: number
  itemsCompletedThisWeek: number
  averageCompletionTime: number
  velocity: number
}

export interface MemberActivity {
  userId: string
  userName: string
  itemsCreated: number
  itemsCompleted: number
  timeSpent: number
  activityScore: number
}

export interface StatusDistribution {
  status: string
  count: number
  percentage: number
}

export interface OrganizationAnalytics {
  organizationId: string
  period: string
  dateRange: {
    start: string
    end: string
  }
  userMetrics: {
    totalUsers: number
    activeUsers: number
    userGrowth: number
  }
  workspaceMetrics: {
    totalWorkspaces: number
    averageBoardsPerWorkspace: number
  }
  itemMetrics: {
    totalItems: number
    completedItems: number
    completionRate: number
  }
  engagementMetrics: {
    averageSessionLength: number
    dailyActiveUsers: number
    monthlyActiveUsers: number
  }
}

// Time Tracking types
export interface ActiveTimer {
  id: string
  itemId?: string
  boardId?: string
  description?: string
  startTime: string
  billable: boolean
  metadata?: Record<string, any>
}

export interface CreateTimeEntryData {
  itemId?: string
  boardId?: string
  description?: string
  billable?: boolean
  metadata?: Record<string, any>
}

export interface UpdateTimeEntryData {
  description?: string
  duration?: number
  billable?: boolean
  metadata?: Record<string, any>
}

export interface TimeEntryFilter {
  userId?: string
  itemId?: string
  boardId?: string
  billable?: boolean
  isRunning?: boolean
  startDate?: string
  endDate?: string
}

export interface TimeStatistics {
  totalTime: number
  billableTime: number
  totalEntries: number
  averageSessionDuration: number
  topBoards: {
    boardId: string
    boardName: string
    timeSpent: number
  }[]
  topItems: {
    itemId: string
    itemName: string
    timeSpent: number
  }[]
  dailyBreakdown: {
    date: string
    totalTime: number
    billableTime: number
  }[]
}

// Webhook types
export interface Webhook {
  id: string
  name: string
  url: string
  events: string[]
  isActive: boolean
  secret: string
  organizationId?: string
  workspaceId?: string
  boardId?: string
  createdAt: string
  updatedAt: string
  lastDeliveryAt?: string
  deliveryCount: number
  failureCount: number
}

export interface CreateWebhookData {
  name: string
  url: string
  events: string[]
  isActive?: boolean
  organizationId?: string
  workspaceId?: string
  boardId?: string
}

export interface UpdateWebhookData {
  name?: string
  url?: string
  events?: string[]
  isActive?: boolean
}

export interface WebhookDelivery {
  id: string
  webhookId: string
  eventType: string
  status: 'pending' | 'success' | 'failed' | 'retrying'
  responseStatus?: number
  responseTime?: number
  errorMessage?: string
  payload: Record<string, any>
  createdAt: string
  deliveredAt?: string
  retryCount: number
}

export interface WebhookEvent {
  type: string
  data: Record<string, any>
  timestamp: string
  source: string
  organizationId?: string
  workspaceId?: string
  boardId?: string
  userId?: string
}