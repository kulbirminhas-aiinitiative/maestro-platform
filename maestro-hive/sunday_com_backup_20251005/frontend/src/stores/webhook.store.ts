import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'
import api from '@/lib/api'
import type {
  Webhook,
  CreateWebhookData,
  UpdateWebhookData,
  WebhookDelivery,
  ApiError,
} from '@/types'

interface WebhookStoreState {
  // State
  webhooks: Webhook[]
  deliveries: Record<string, WebhookDelivery[]>
  availableEvents: string[]

  // Loading states
  loading: {
    webhooks: boolean
    deliveries: Record<string, boolean>
    creating: boolean
    updating: boolean
    deleting: boolean
    testing: boolean
    retrying: boolean
  }

  // Error states
  errors: {
    webhooks: string | null
    deliveries: Record<string, string | null>
    creating: string | null
    updating: string | null
    deleting: string | null
    testing: string | null
    retrying: string | null
  }

  // Filters
  currentScope: {
    organizationId?: string
    workspaceId?: string
    boardId?: string
  }
}

interface WebhookStoreActions {
  // Webhook CRUD
  createWebhook: (data: CreateWebhookData) => Promise<Webhook>
  fetchWebhooks: (scope?: {
    organizationId?: string
    workspaceId?: string
    boardId?: string
  }) => Promise<void>
  getWebhook: (id: string) => Promise<Webhook>
  updateWebhook: (id: string, data: UpdateWebhookData) => Promise<void>
  deleteWebhook: (id: string) => Promise<void>

  // Webhook testing
  testWebhook: (id: string) => Promise<void>

  // Delivery management
  fetchDeliveries: (webhookId: string) => Promise<void>
  retryDelivery: (deliveryId: string) => Promise<void>

  // Utility actions
  setScope: (scope: {
    organizationId?: string
    workspaceId?: string
    boardId?: string
  }) => void
  clearErrors: () => void
  reset: () => void
}

type WebhookStore = WebhookStoreState & WebhookStoreActions

// Available webhook events
const WEBHOOK_EVENTS = [
  'item.created',
  'item.updated',
  'item.deleted',
  'item.moved',
  'item.status_changed',
  'item.assigned',
  'item.unassigned',
  'board.created',
  'board.updated',
  'board.deleted',
  'board.member_added',
  'board.member_removed',
  'column.created',
  'column.updated',
  'column.deleted',
  'comment.created',
  'comment.updated',
  'comment.deleted',
  'file.uploaded',
  'file.deleted',
  'time_entry.started',
  'time_entry.stopped',
  'time_entry.created',
  'time_entry.updated',
  'time_entry.deleted',
  'workspace.created',
  'workspace.updated',
  'workspace.deleted',
  'workspace.member_added',
  'workspace.member_removed',
]

const initialState: WebhookStoreState = {
  webhooks: [],
  deliveries: {},
  availableEvents: WEBHOOK_EVENTS,
  loading: {
    webhooks: false,
    deliveries: {},
    creating: false,
    updating: false,
    deleting: false,
    testing: false,
    retrying: false,
  },
  errors: {
    webhooks: null,
    deliveries: {},
    creating: null,
    updating: null,
    deleting: null,
    testing: null,
    retrying: null,
  },
  currentScope: {},
}

export const useWebhookStore = create<WebhookStore>()(
  subscribeWithSelector(
    immer((set, get) => ({
      ...initialState,

      // Webhook CRUD
      createWebhook: async (data: CreateWebhookData) => {
        set((state) => {
          state.loading.creating = true
          state.errors.creating = null
        })

        try {
          const response = await api.webhooks.create(data)
          set((state) => {
            state.webhooks.unshift(response.data)
            state.loading.creating = false
          })
          return response.data
        } catch (error) {
          const apiError = error as ApiError
          set((state) => {
            state.errors.creating = apiError.error?.message || 'Failed to create webhook'
            state.loading.creating = false
          })
          throw error
        }
      },

      fetchWebhooks: async (scope) => {
        set((state) => {
          state.loading.webhooks = true
          state.errors.webhooks = null
          if (scope) {
            state.currentScope = scope
          }
        })

        try {
          let response
          const currentScope = scope || get().currentScope

          if (currentScope.boardId) {
            response = await api.webhooks.listByBoard(currentScope.boardId)
          } else if (currentScope.workspaceId) {
            response = await api.webhooks.listByWorkspace(currentScope.workspaceId)
          } else if (currentScope.organizationId) {
            response = await api.webhooks.listByOrganization(currentScope.organizationId)
          } else {
            throw new Error('No scope specified for webhook fetching')
          }

          set((state) => {
            state.webhooks = response.data
            state.loading.webhooks = false
          })
        } catch (error) {
          const apiError = error as ApiError
          set((state) => {
            state.errors.webhooks = apiError.error?.message || 'Failed to fetch webhooks'
            state.loading.webhooks = false
          })
        }
      },

      getWebhook: async (id: string) => {
        try {
          const response = await api.webhooks.get(id)
          return response.data
        } catch (error) {
          const apiError = error as ApiError
          throw new Error(apiError.error?.message || 'Failed to fetch webhook')
        }
      },

      updateWebhook: async (id: string, data: UpdateWebhookData) => {
        set((state) => {
          state.loading.updating = true
          state.errors.updating = null
        })

        try {
          const response = await api.webhooks.update(id, data)
          set((state) => {
            const index = state.webhooks.findIndex(webhook => webhook.id === id)
            if (index !== -1) {
              state.webhooks[index] = response.data
            }
            state.loading.updating = false
          })
        } catch (error) {
          const apiError = error as ApiError
          set((state) => {
            state.errors.updating = apiError.error?.message || 'Failed to update webhook'
            state.loading.updating = false
          })
          throw error
        }
      },

      deleteWebhook: async (id: string) => {
        set((state) => {
          state.loading.deleting = true
          state.errors.deleting = null
        })

        try {
          await api.webhooks.delete(id)
          set((state) => {
            state.webhooks = state.webhooks.filter(webhook => webhook.id !== id)
            // Also remove deliveries for this webhook
            delete state.deliveries[id]
            state.loading.deleting = false
          })
        } catch (error) {
          const apiError = error as ApiError
          set((state) => {
            state.errors.deleting = apiError.error?.message || 'Failed to delete webhook'
            state.loading.deleting = false
          })
          throw error
        }
      },

      // Webhook testing
      testWebhook: async (id: string) => {
        set((state) => {
          state.loading.testing = true
          state.errors.testing = null
        })

        try {
          await api.webhooks.test(id)
          set((state) => {
            state.loading.testing = false
          })
        } catch (error) {
          const apiError = error as ApiError
          set((state) => {
            state.errors.testing = apiError.error?.message || 'Failed to test webhook'
            state.loading.testing = false
          })
          throw error
        }
      },

      // Delivery management
      fetchDeliveries: async (webhookId: string) => {
        set((state) => {
          state.loading.deliveries[webhookId] = true
          state.errors.deliveries[webhookId] = null
        })

        try {
          const response = await api.webhooks.getDeliveries(webhookId)
          set((state) => {
            state.deliveries[webhookId] = response.data
            state.loading.deliveries[webhookId] = false
          })
        } catch (error) {
          const apiError = error as ApiError
          set((state) => {
            state.errors.deliveries[webhookId] =
              apiError.error?.message || 'Failed to fetch deliveries'
            state.loading.deliveries[webhookId] = false
          })
        }
      },

      retryDelivery: async (deliveryId: string) => {
        set((state) => {
          state.loading.retrying = true
          state.errors.retrying = null
        })

        try {
          await api.webhooks.retryDelivery(deliveryId)
          set((state) => {
            state.loading.retrying = false
          })
          // Refresh deliveries for all webhooks to update status
          Object.keys(get().deliveries).forEach(webhookId => {
            get().fetchDeliveries(webhookId)
          })
        } catch (error) {
          const apiError = error as ApiError
          set((state) => {
            state.errors.retrying = apiError.error?.message || 'Failed to retry delivery'
            state.loading.retrying = false
          })
          throw error
        }
      },

      // Utility actions
      setScope: (scope) => {
        set((state) => {
          state.currentScope = scope
        })
      },

      clearErrors: () => {
        set((state) => {
          state.errors = {
            webhooks: null,
            deliveries: {},
            creating: null,
            updating: null,
            deleting: null,
            testing: null,
            retrying: null,
          }
        })
      },

      reset: () => {
        set(() => ({ ...initialState }))
      },
    }))
  )
)

// Helper functions
export const getWebhookEventsForScope = (scope: 'organization' | 'workspace' | 'board') => {
  const allEvents = WEBHOOK_EVENTS

  switch (scope) {
    case 'board':
      return allEvents
    case 'workspace':
      return allEvents.filter(event =>
        !event.startsWith('organization.') &&
        !event.startsWith('subscription.')
      )
    case 'organization':
      return allEvents
    default:
      return allEvents
  }
}

export const getWebhookEventDescription = (eventType: string): string => {
  const descriptions: Record<string, string> = {
    'item.created': 'When a new item is created',
    'item.updated': 'When an item is updated',
    'item.deleted': 'When an item is deleted',
    'item.moved': 'When an item is moved between columns',
    'item.status_changed': 'When an item status changes',
    'item.assigned': 'When an item is assigned to a user',
    'item.unassigned': 'When an item is unassigned from a user',
    'board.created': 'When a new board is created',
    'board.updated': 'When a board is updated',
    'board.deleted': 'When a board is deleted',
    'board.member_added': 'When a member is added to a board',
    'board.member_removed': 'When a member is removed from a board',
    'column.created': 'When a new column is created',
    'column.updated': 'When a column is updated',
    'column.deleted': 'When a column is deleted',
    'comment.created': 'When a new comment is created',
    'comment.updated': 'When a comment is updated',
    'comment.deleted': 'When a comment is deleted',
    'file.uploaded': 'When a file is uploaded',
    'file.deleted': 'When a file is deleted',
    'time_entry.started': 'When a timer is started',
    'time_entry.stopped': 'When a timer is stopped',
    'time_entry.created': 'When a time entry is created',
    'time_entry.updated': 'When a time entry is updated',
    'time_entry.deleted': 'When a time entry is deleted',
    'workspace.created': 'When a new workspace is created',
    'workspace.updated': 'When a workspace is updated',
    'workspace.deleted': 'When a workspace is deleted',
    'workspace.member_added': 'When a member is added to a workspace',
    'workspace.member_removed': 'When a member is removed from a workspace',
  }

  return descriptions[eventType] || eventType
}