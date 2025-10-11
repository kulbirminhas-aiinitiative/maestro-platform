import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'
import api from '@/lib/api'
import type {
  BoardAnalytics,
  OrganizationAnalytics,
  AnalyticsData,
  ApiError,
} from '@/types'

interface AnalyticsStoreState {
  // State
  boardAnalytics: Record<string, BoardAnalytics>
  organizationAnalytics: Record<string, OrganizationAnalytics>
  dashboardOverview: AnalyticsData | null
  customReports: Record<string, any>

  // Loading states
  loading: {
    boardAnalytics: Record<string, boolean>
    organizationAnalytics: Record<string, boolean>
    dashboardOverview: boolean
    customReport: boolean
    export: boolean
  }

  // Error states
  errors: {
    boardAnalytics: Record<string, string | null>
    organizationAnalytics: Record<string, string | null>
    dashboardOverview: string | null
    customReport: string | null
    export: string | null
  }

  // Cache settings
  cacheTimeout: number
  lastFetched: Record<string, number>
}

interface AnalyticsStoreActions {
  // Board analytics
  fetchBoardAnalytics: (boardId: string, params?: any) => Promise<void>
  getBoardAnalytics: (boardId: string) => BoardAnalytics | null

  // User analytics
  fetchUserActivity: (userId: string, params?: any) => Promise<any>

  // Team analytics
  fetchTeamProductivity: (workspaceId: string, params?: any) => Promise<any>

  // Organization analytics
  fetchOrganizationAnalytics: (orgId: string, params?: any) => Promise<void>
  getOrganizationAnalytics: (orgId: string) => OrganizationAnalytics | null

  // Dashboard overview
  fetchDashboardOverview: (params?: any) => Promise<void>

  // Custom reports
  generateCustomReport: (data: any) => Promise<any>

  // Data export
  exportData: (params?: any) => Promise<void>

  // Cache management
  invalidateCache: (key?: string) => void
  isCacheValid: (key: string) => boolean

  // Utility actions
  clearErrors: () => void
  reset: () => void
}

type AnalyticsStore = AnalyticsStoreState & AnalyticsStoreActions

const initialState: AnalyticsStoreState = {
  boardAnalytics: {},
  organizationAnalytics: {},
  dashboardOverview: null,
  customReports: {},
  loading: {
    boardAnalytics: {},
    organizationAnalytics: {},
    dashboardOverview: false,
    customReport: false,
    export: false,
  },
  errors: {
    boardAnalytics: {},
    organizationAnalytics: {},
    dashboardOverview: null,
    customReport: null,
    export: null,
  },
  cacheTimeout: 5 * 60 * 1000, // 5 minutes
  lastFetched: {},
}

export const useAnalyticsStore = create<AnalyticsStore>()(
  subscribeWithSelector(
    immer((set, get) => ({
      ...initialState,

      // Board analytics
      fetchBoardAnalytics: async (boardId: string, params?: any) => {
        const cacheKey = `board_${boardId}`

        // Check cache first
        if (get().isCacheValid(cacheKey) && get().boardAnalytics[boardId]) {
          return
        }

        set((state) => {
          state.loading.boardAnalytics[boardId] = true
          state.errors.boardAnalytics[boardId] = null
        })

        try {
          const response = await api.analytics.getBoardAnalytics(boardId, params)
          set((state) => {
            state.boardAnalytics[boardId] = response.data
            state.loading.boardAnalytics[boardId] = false
            state.lastFetched[cacheKey] = Date.now()
          })
        } catch (error) {
          const apiError = error as ApiError
          set((state) => {
            state.errors.boardAnalytics[boardId] =
              apiError.error?.message || 'Failed to fetch board analytics'
            state.loading.boardAnalytics[boardId] = false
          })
        }
      },

      getBoardAnalytics: (boardId: string) => {
        return get().boardAnalytics[boardId] || null
      },

      // User analytics
      fetchUserActivity: async (userId: string, params?: any) => {
        try {
          const response = await api.analytics.getUserActivity(userId, params)
          return response.data
        } catch (error) {
          const apiError = error as ApiError
          throw new Error(apiError.error?.message || 'Failed to fetch user activity')
        }
      },

      // Team analytics
      fetchTeamProductivity: async (workspaceId: string, params?: any) => {
        try {
          const response = await api.analytics.getTeamProductivity(workspaceId, params)
          return response.data
        } catch (error) {
          const apiError = error as ApiError
          throw new Error(apiError.error?.message || 'Failed to fetch team productivity')
        }
      },

      // Organization analytics
      fetchOrganizationAnalytics: async (orgId: string, params?: any) => {
        const cacheKey = `org_${orgId}`

        // Check cache first
        if (get().isCacheValid(cacheKey) && get().organizationAnalytics[orgId]) {
          return
        }

        set((state) => {
          state.loading.organizationAnalytics[orgId] = true
          state.errors.organizationAnalytics[orgId] = null
        })

        try {
          const response = await api.analytics.getOrganizationAnalytics(orgId, params)
          set((state) => {
            state.organizationAnalytics[orgId] = response.data
            state.loading.organizationAnalytics[orgId] = false
            state.lastFetched[cacheKey] = Date.now()
          })
        } catch (error) {
          const apiError = error as ApiError
          set((state) => {
            state.errors.organizationAnalytics[orgId] =
              apiError.error?.message || 'Failed to fetch organization analytics'
            state.loading.organizationAnalytics[orgId] = false
          })
        }
      },

      getOrganizationAnalytics: (orgId: string) => {
        return get().organizationAnalytics[orgId] || null
      },

      // Dashboard overview
      fetchDashboardOverview: async (params?: any) => {
        const cacheKey = 'dashboard_overview'

        // Check cache first
        if (get().isCacheValid(cacheKey) && get().dashboardOverview) {
          return
        }

        set((state) => {
          state.loading.dashboardOverview = true
          state.errors.dashboardOverview = null
        })

        try {
          const response = await api.analytics.getDashboardOverview(params)
          set((state) => {
            state.dashboardOverview = response.data
            state.loading.dashboardOverview = false
            state.lastFetched[cacheKey] = Date.now()
          })
        } catch (error) {
          const apiError = error as ApiError
          set((state) => {
            state.errors.dashboardOverview =
              apiError.error?.message || 'Failed to fetch dashboard overview'
            state.loading.dashboardOverview = false
          })
        }
      },

      // Custom reports
      generateCustomReport: async (data: any) => {
        set((state) => {
          state.loading.customReport = true
          state.errors.customReport = null
        })

        try {
          const response = await api.analytics.generateCustomReport(data)
          const reportId = `custom_${Date.now()}`
          set((state) => {
            state.customReports[reportId] = response.data
            state.loading.customReport = false
          })
          return { id: reportId, data: response.data }
        } catch (error) {
          const apiError = error as ApiError
          set((state) => {
            state.errors.customReport =
              apiError.error?.message || 'Failed to generate custom report'
            state.loading.customReport = false
          })
          throw error
        }
      },

      // Data export
      exportData: async (params?: any) => {
        set((state) => {
          state.loading.export = true
          state.errors.export = null
        })

        try {
          const response = await api.analytics.exportData(params)
          set((state) => {
            state.loading.export = false
          })

          // Create a download link
          const blob = new Blob([response.data], {
            type: params?.format === 'csv' ? 'text/csv' : 'application/json'
          })
          const url = window.URL.createObjectURL(blob)
          const a = document.createElement('a')
          a.style.display = 'none'
          a.href = url
          a.download = `analytics_export_${new Date().toISOString().split('T')[0]}.${params?.format || 'json'}`
          document.body.appendChild(a)
          a.click()
          window.URL.revokeObjectURL(url)
          document.body.removeChild(a)
        } catch (error) {
          const apiError = error as ApiError
          set((state) => {
            state.errors.export =
              apiError.error?.message || 'Failed to export data'
            state.loading.export = false
          })
          throw error
        }
      },

      // Cache management
      invalidateCache: (key?: string) => {
        set((state) => {
          if (key) {
            delete state.lastFetched[key]
            // Clear related data
            if (key.startsWith('board_')) {
              const boardId = key.replace('board_', '')
              delete state.boardAnalytics[boardId]
            } else if (key.startsWith('org_')) {
              const orgId = key.replace('org_', '')
              delete state.organizationAnalytics[orgId]
            } else if (key === 'dashboard_overview') {
              state.dashboardOverview = null
            }
          } else {
            // Clear all cache
            state.lastFetched = {}
            state.boardAnalytics = {}
            state.organizationAnalytics = {}
            state.dashboardOverview = null
          }
        })
      },

      isCacheValid: (key: string) => {
        const lastFetched = get().lastFetched[key]
        if (!lastFetched) return false
        return Date.now() - lastFetched < get().cacheTimeout
      },

      // Utility actions
      clearErrors: () => {
        set((state) => {
          state.errors = {
            boardAnalytics: {},
            organizationAnalytics: {},
            dashboardOverview: null,
            customReport: null,
            export: null,
          }
        })
      },

      reset: () => {
        set(() => ({ ...initialState }))
      },
    }))
  )
)

// Auto-refresh analytics data every 10 minutes
let refreshInterval: NodeJS.Timeout | null = null

export const startAnalyticsAutoRefresh = () => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }

  refreshInterval = setInterval(() => {
    const store = useAnalyticsStore.getState()

    // Refresh dashboard overview if it exists
    if (store.dashboardOverview) {
      store.fetchDashboardOverview()
    }

    // Refresh board analytics that were recently viewed
    Object.keys(store.boardAnalytics).forEach(boardId => {
      const cacheKey = `board_${boardId}`
      if (store.lastFetched[cacheKey] && Date.now() - store.lastFetched[cacheKey] > 10 * 60 * 1000) {
        store.fetchBoardAnalytics(boardId)
      }
    })
  }, 10 * 60 * 1000) // 10 minutes
}

export const stopAnalyticsAutoRefresh = () => {
  if (refreshInterval) {
    clearInterval(refreshInterval)
    refreshInterval = null
  }
}