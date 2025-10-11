import { create } from 'zustand'
import { subscribeWithSelector } from 'zustand/middleware'
import { immer } from 'zustand/middleware/immer'
import api from '@/lib/api'
import type {
  TimeEntry,
  ActiveTimer,
  CreateTimeEntryData,
  UpdateTimeEntryData,
  TimeEntryFilter,
  TimeStatistics,
  ApiError,
} from '@/types'

interface TimeStoreState {
  // State
  activeTimer: ActiveTimer | null
  timeEntries: TimeEntry[]
  statistics: TimeStatistics | null

  // Loading states
  loading: {
    activeTimer: boolean
    timeEntries: boolean
    statistics: boolean
    starting: boolean
    stopping: boolean
    creating: boolean
    updating: boolean
    deleting: boolean
  }

  // Error states
  errors: {
    activeTimer: string | null
    timeEntries: string | null
    statistics: string | null
    starting: string | null
    stopping: string | null
    creating: string | null
    updating: string | null
    deleting: string | null
  }

  // Filters
  currentFilter: TimeEntryFilter
}

interface TimeStoreActions {
  // Timer actions
  startTimer: (data: CreateTimeEntryData) => Promise<void>
  stopTimer: () => Promise<void>
  getActiveTimer: () => Promise<void>

  // Time entry actions
  createTimeEntry: (data: CreateTimeEntryData) => Promise<void>
  fetchTimeEntries: (filter?: TimeEntryFilter) => Promise<void>
  updateTimeEntry: (id: string, data: UpdateTimeEntryData) => Promise<void>
  deleteTimeEntry: (id: string) => Promise<void>

  // Statistics
  fetchStatistics: (filter?: TimeEntryFilter) => Promise<void>

  // Filter actions
  setFilter: (filter: Partial<TimeEntryFilter>) => void
  clearFilter: () => void

  // Utility actions
  clearErrors: () => void
  reset: () => void
}

type TimeStore = TimeStoreState & TimeStoreActions

const initialState: TimeStoreState = {
  activeTimer: null,
  timeEntries: [],
  statistics: null,
  loading: {
    activeTimer: false,
    timeEntries: false,
    statistics: false,
    starting: false,
    stopping: false,
    creating: false,
    updating: false,
    deleting: false,
  },
  errors: {
    activeTimer: null,
    timeEntries: null,
    statistics: null,
    starting: null,
    stopping: null,
    creating: null,
    updating: null,
    deleting: null,
  },
  currentFilter: {},
}

export const useTimeStore = create<TimeStore>()(
  subscribeWithSelector(
    immer((set, get) => ({
      ...initialState,

      // Timer actions
      startTimer: async (data: CreateTimeEntryData) => {
        set((state) => {
          state.loading.starting = true
          state.errors.starting = null
        })

        try {
          const response = await api.time.start(data)
          set((state) => {
            state.activeTimer = response.data
            state.loading.starting = false
          })
        } catch (error) {
          const apiError = error as ApiError
          set((state) => {
            state.errors.starting = apiError.error?.message || 'Failed to start timer'
            state.loading.starting = false
          })
          throw error
        }
      },

      stopTimer: async () => {
        set((state) => {
          state.loading.stopping = true
          state.errors.stopping = null
        })

        try {
          const response = await api.time.stop()
          set((state) => {
            state.activeTimer = null
            state.loading.stopping = false
            // Add the completed entry to the list
            if (response.data) {
              state.timeEntries.unshift(response.data)
            }
          })
        } catch (error) {
          const apiError = error as ApiError
          set((state) => {
            state.errors.stopping = apiError.error?.message || 'Failed to stop timer'
            state.loading.stopping = false
          })
          throw error
        }
      },

      getActiveTimer: async () => {
        set((state) => {
          state.loading.activeTimer = true
          state.errors.activeTimer = null
        })

        try {
          const response = await api.time.getActive()
          set((state) => {
            state.activeTimer = response.data
            state.loading.activeTimer = false
          })
        } catch (error) {
          const apiError = error as ApiError
          set((state) => {
            state.errors.activeTimer = apiError.error?.message || 'Failed to fetch active timer'
            state.loading.activeTimer = false
          })
        }
      },

      // Time entry actions
      createTimeEntry: async (data: CreateTimeEntryData) => {
        set((state) => {
          state.loading.creating = true
          state.errors.creating = null
        })

        try {
          const response = await api.time.createEntry(data)
          set((state) => {
            state.timeEntries.unshift(response.data)
            state.loading.creating = false
          })
        } catch (error) {
          const apiError = error as ApiError
          set((state) => {
            state.errors.creating = apiError.error?.message || 'Failed to create time entry'
            state.loading.creating = false
          })
          throw error
        }
      },

      fetchTimeEntries: async (filter?: TimeEntryFilter) => {
        set((state) => {
          state.loading.timeEntries = true
          state.errors.timeEntries = null
          if (filter) {
            state.currentFilter = { ...state.currentFilter, ...filter }
          }
        })

        try {
          const response = await api.time.listEntries(get().currentFilter)
          set((state) => {
            state.timeEntries = response.data
            state.loading.timeEntries = false
          })
        } catch (error) {
          const apiError = error as ApiError
          set((state) => {
            state.errors.timeEntries = apiError.error?.message || 'Failed to fetch time entries'
            state.loading.timeEntries = false
          })
        }
      },

      updateTimeEntry: async (id: string, data: UpdateTimeEntryData) => {
        set((state) => {
          state.loading.updating = true
          state.errors.updating = null
        })

        try {
          const response = await api.time.updateEntry(id, data)
          set((state) => {
            const index = state.timeEntries.findIndex(entry => entry.id === id)
            if (index !== -1) {
              state.timeEntries[index] = response.data
            }
            state.loading.updating = false
          })
        } catch (error) {
          const apiError = error as ApiError
          set((state) => {
            state.errors.updating = apiError.error?.message || 'Failed to update time entry'
            state.loading.updating = false
          })
          throw error
        }
      },

      deleteTimeEntry: async (id: string) => {
        set((state) => {
          state.loading.deleting = true
          state.errors.deleting = null
        })

        try {
          await api.time.deleteEntry(id)
          set((state) => {
            state.timeEntries = state.timeEntries.filter(entry => entry.id !== id)
            state.loading.deleting = false
          })
        } catch (error) {
          const apiError = error as ApiError
          set((state) => {
            state.errors.deleting = apiError.error?.message || 'Failed to delete time entry'
            state.loading.deleting = false
          })
          throw error
        }
      },

      // Statistics
      fetchStatistics: async (filter?: TimeEntryFilter) => {
        set((state) => {
          state.loading.statistics = true
          state.errors.statistics = null
        })

        try {
          const statsFilter = filter || get().currentFilter
          const response = await api.time.getStatistics(statsFilter)
          set((state) => {
            state.statistics = response.data
            state.loading.statistics = false
          })
        } catch (error) {
          const apiError = error as ApiError
          set((state) => {
            state.errors.statistics = apiError.error?.message || 'Failed to fetch statistics'
            state.loading.statistics = false
          })
        }
      },

      // Filter actions
      setFilter: (filter: Partial<TimeEntryFilter>) => {
        set((state) => {
          state.currentFilter = { ...state.currentFilter, ...filter }
        })
      },

      clearFilter: () => {
        set((state) => {
          state.currentFilter = {}
        })
      },

      // Utility actions
      clearErrors: () => {
        set((state) => {
          Object.keys(state.errors).forEach((key) => {
            state.errors[key as keyof typeof state.errors] = null
          })
        })
      },

      reset: () => {
        set(() => ({ ...initialState }))
      },
    }))
  )
)

// Subscribe to timer changes and emit events
useTimeStore.subscribe(
  (state) => state.activeTimer,
  (activeTimer, previousActiveTimer) => {
    // Emit timer started event
    if (activeTimer && !previousActiveTimer) {
      window.dispatchEvent(new CustomEvent('timer:started', { detail: activeTimer }))
    }

    // Emit timer stopped event
    if (!activeTimer && previousActiveTimer) {
      window.dispatchEvent(new CustomEvent('timer:stopped', { detail: previousActiveTimer }))
    }
  }
)