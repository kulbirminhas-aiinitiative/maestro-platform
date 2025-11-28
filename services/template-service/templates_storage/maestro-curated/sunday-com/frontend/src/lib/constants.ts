export const APP_NAME = 'Sunday.com'
export const APP_DESCRIPTION = 'Modern Work Management Platform for Teams'

// API Configuration
export const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:3000'
export const GRAPHQL_ENDPOINT = `${API_BASE_URL}/graphql`
export const WS_ENDPOINT = API_BASE_URL.replace(/^http/, 'ws') + '/ws'

// Authentication
export const TOKEN_STORAGE_KEY = 'sunday_auth_token'
export const REFRESH_TOKEN_STORAGE_KEY = 'sunday_refresh_token'
export const USER_STORAGE_KEY = 'sunday_user'

// Pagination
export const DEFAULT_PAGE_SIZE = 20
export const MAX_PAGE_SIZE = 100

// File uploads
export const MAX_FILE_SIZE = 10 * 1024 * 1024 // 10MB
export const ALLOWED_FILE_TYPES = [
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
  'application/pdf',
  'text/plain',
  'text/csv',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
]

// Colors
export const BRAND_COLORS = {
  primary: '#3b82f6',
  secondary: '#6b7280',
  success: '#10b981',
  warning: '#f59e0b',
  error: '#ef4444',
  info: '#3b82f6',
}

export const STATUS_COLORS = {
  todo: '#6b7280',
  'in-progress': '#3b82f6',
  review: '#f59e0b',
  done: '#10b981',
  blocked: '#ef4444',
  cancelled: '#6b7280',
}

export const PRIORITY_COLORS = {
  low: '#10b981',
  medium: '#f59e0b',
  high: '#ef4444',
  urgent: '#dc2626',
}

// Board view types
export const BOARD_VIEWS = [
  { value: 'table', label: 'Table', icon: 'table' },
  { value: 'kanban', label: 'Kanban', icon: 'kanban' },
  { value: 'timeline', label: 'Timeline', icon: 'timeline' },
  { value: 'calendar', label: 'Calendar', icon: 'calendar' },
  { value: 'chart', label: 'Chart', icon: 'chart' },
] as const

// Column types
export const COLUMN_TYPES = [
  { value: 'text', label: 'Text', icon: 'text' },
  { value: 'number', label: 'Number', icon: 'number' },
  { value: 'status', label: 'Status', icon: 'status' },
  { value: 'date', label: 'Date', icon: 'date' },
  { value: 'people', label: 'People', icon: 'people' },
  { value: 'timeline', label: 'Timeline', icon: 'timeline' },
  { value: 'files', label: 'Files', icon: 'files' },
  { value: 'checkbox', label: 'Checkbox', icon: 'checkbox' },
  { value: 'rating', label: 'Rating', icon: 'rating' },
  { value: 'email', label: 'Email', icon: 'email' },
  { value: 'phone', label: 'Phone', icon: 'phone' },
  { value: 'url', label: 'URL', icon: 'url' },
] as const

// Organization roles
export const ORGANIZATION_ROLES = [
  { value: 'owner', label: 'Owner', description: 'Full access to organization settings and billing' },
  { value: 'admin', label: 'Admin', description: 'Manage organization, workspaces, and members' },
  { value: 'member', label: 'Member', description: 'Access to assigned workspaces and boards' },
] as const

// Workspace roles
export const WORKSPACE_ROLES = [
  { value: 'admin', label: 'Admin', description: 'Manage workspace settings and members' },
  { value: 'member', label: 'Member', description: 'Create and edit boards and items' },
  { value: 'viewer', label: 'Viewer', description: 'View-only access to boards and items' },
] as const

// Board roles
export const BOARD_ROLES = [
  { value: 'admin', label: 'Admin', description: 'Manage board settings and permissions' },
  { value: 'member', label: 'Member', description: 'Create and edit items' },
  { value: 'viewer', label: 'Viewer', description: 'View-only access to board' },
] as const

// Subscription plans
export const SUBSCRIPTION_PLANS = [
  {
    id: 'free',
    name: 'Free',
    price: 0,
    billing: 'Forever',
    features: [
      'Up to 3 boards',
      '2 team members',
      'Basic templates',
      'Mobile app',
      'Community support',
    ],
    limits: {
      boards: 3,
      members: 2,
      storage: '100MB',
      integrations: false,
      advancedFeatures: false,
    },
  },
  {
    id: 'pro',
    name: 'Pro',
    price: 8,
    billing: 'per user/month',
    features: [
      'Unlimited boards',
      'Unlimited members',
      'Advanced templates',
      'Time tracking',
      'Calendar view',
      'Dashboard view',
      'Guest access',
      'Priority support',
    ],
    limits: {
      boards: Infinity,
      members: Infinity,
      storage: '100GB',
      integrations: true,
      advancedFeatures: true,
    },
  },
  {
    id: 'enterprise',
    name: 'Enterprise',
    price: 16,
    billing: 'per user/month',
    features: [
      'Everything in Pro',
      'Advanced security',
      'Single sign-on (SSO)',
      'Advanced analytics',
      'Custom integrations',
      'Dedicated support',
      'SLA guarantee',
    ],
    limits: {
      boards: Infinity,
      members: Infinity,
      storage: '1TB',
      integrations: true,
      advancedFeatures: true,
    },
  },
] as const

// Default board templates
export const BOARD_TEMPLATES = [
  {
    id: 'project-management',
    name: 'Project Management',
    description: 'Manage projects from start to finish',
    category: 'Project Management',
    columns: [
      { name: 'Task', type: 'text' },
      { name: 'Status', type: 'status' },
      { name: 'Owner', type: 'people' },
      { name: 'Due Date', type: 'date' },
      { name: 'Priority', type: 'status' },
    ],
  },
  {
    id: 'kanban-board',
    name: 'Kanban Board',
    description: 'Visualize work in progress',
    category: 'Agile',
    columns: [
      { name: 'Task', type: 'text' },
      { name: 'Status', type: 'status' },
      { name: 'Assignee', type: 'people' },
      { name: 'Priority', type: 'status' },
    ],
  },
  {
    id: 'bug-tracking',
    name: 'Bug Tracking',
    description: 'Track and resolve issues',
    category: 'Development',
    columns: [
      { name: 'Bug', type: 'text' },
      { name: 'Status', type: 'status' },
      { name: 'Severity', type: 'status' },
      { name: 'Assigned To', type: 'people' },
      { name: 'Found Date', type: 'date' },
      { name: 'Fixed Date', type: 'date' },
    ],
  },
  {
    id: 'content-calendar',
    name: 'Content Calendar',
    description: 'Plan and schedule content',
    category: 'Marketing',
    columns: [
      { name: 'Content', type: 'text' },
      { name: 'Status', type: 'status' },
      { name: 'Author', type: 'people' },
      { name: 'Publish Date', type: 'date' },
      { name: 'Platform', type: 'status' },
    ],
  },
  {
    id: 'sales-pipeline',
    name: 'Sales Pipeline',
    description: 'Track leads and opportunities',
    category: 'Sales',
    columns: [
      { name: 'Lead', type: 'text' },
      { name: 'Stage', type: 'status' },
      { name: 'Value', type: 'number' },
      { name: 'Owner', type: 'people' },
      { name: 'Expected Close', type: 'date' },
    ],
  },
] as const

// Keyboard shortcuts
export const KEYBOARD_SHORTCUTS = {
  // Global
  'cmd+k': 'Open command palette',
  'cmd+/': 'Show keyboard shortcuts',
  'cmd+shift+n': 'Create new board',
  'cmd+shift+t': 'Create new task',

  // Navigation
  'g h': 'Go to home',
  'g w': 'Go to workspaces',
  'g s': 'Go to settings',

  // Board
  'n': 'New item',
  'e': 'Edit selected item',
  'd': 'Delete selected item',
  'c': 'Comment on selected item',

  // Selection
  'j': 'Select next item',
  'k': 'Select previous item',
  'shift+j': 'Extend selection down',
  'shift+k': 'Extend selection up',
  'cmd+a': 'Select all items',
  'escape': 'Clear selection',
} as const

// WebSocket events
export const WS_EVENTS = {
  // Connection
  CONNECT: 'connect',
  DISCONNECT: 'disconnect',
  AUTH: 'auth',
  AUTH_SUCCESS: 'auth_success',
  AUTH_FAILED: 'auth_failed',

  // Subscriptions
  SUBSCRIBE: 'subscribe',
  UNSUBSCRIBE: 'unsubscribe',
  SUBSCRIBED: 'subscribed',
  UNSUBSCRIBED: 'unsubscribed',

  // Board events
  BOARD_UPDATE: 'board_update',
  ITEM_CREATED: 'item_created',
  ITEM_UPDATED: 'item_updated',
  ITEM_DELETED: 'item_deleted',

  // User presence
  USER_JOINED: 'user_joined',
  USER_LEFT: 'user_left',
  CURSOR_MOVED: 'cursor_moved',
  USER_TYPING: 'user_typing',

  // Comments
  COMMENT_ADDED: 'comment_added',
  COMMENT_UPDATED: 'comment_updated',
  COMMENT_DELETED: 'comment_deleted',
} as const

// Local storage keys
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'sunday_auth_token',
  REFRESH_TOKEN: 'sunday_refresh_token',
  USER: 'sunday_user',
  THEME: 'sunday_theme',
  SIDEBAR_COLLAPSED: 'sunday_sidebar_collapsed',
  RECENT_BOARDS: 'sunday_recent_boards',
  BOARD_VIEW_SETTINGS: 'sunday_board_view_settings',
} as const

// Query keys for React Query
export const QUERY_KEYS = {
  // Auth
  CURRENT_USER: ['auth', 'current-user'],

  // Organizations
  ORGANIZATIONS: ['organizations'],
  ORGANIZATION: (id: string) => ['organizations', id],
  ORGANIZATION_MEMBERS: (id: string) => ['organizations', id, 'members'],

  // Workspaces
  WORKSPACES: (orgId: string) => ['organizations', orgId, 'workspaces'],
  WORKSPACE: (id: string) => ['workspaces', id],
  WORKSPACE_MEMBERS: (id: string) => ['workspaces', id, 'members'],

  // Boards
  BOARDS: (workspaceId: string) => ['workspaces', workspaceId, 'boards'],
  BOARD: (id: string) => ['boards', id],
  BOARD_ITEMS: (id: string) => ['boards', id, 'items'],

  // Items
  ITEM: (id: string) => ['items', id],
  ITEM_COMMENTS: (id: string) => ['items', id, 'comments'],

  // Files
  FILES: ['files'],
  FILE: (id: string) => ['files', id],
} as const