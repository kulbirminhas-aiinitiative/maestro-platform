import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { UIState, BoardView, ViewSettings } from '@/types'

interface UIStore extends UIState {
  // Actions
  setTheme: (theme: 'light' | 'dark' | 'system') => void
  toggleSidebar: () => void
  setSidebarCollapsed: (collapsed: boolean) => void
  setActiveWorkspace: (workspaceId: string | undefined) => void
  setActiveBoard: (boardId: string | undefined) => void
  selectItems: (itemIds: string[]) => void
  toggleItemSelection: (itemId: string) => void
  clearSelection: () => void
  setLoading: (key: string, loading: boolean) => void
  setError: (key: string, error: string | null) => void
  clearErrors: () => void
}

export const useUIStore = create<UIStore>()(
  persist(
    (set, get) => ({
      theme: 'system',
      sidebarCollapsed: false,
      activeWorkspace: undefined,
      activeBoard: undefined,
      selectedItems: [],
      loading: {},
      errors: {},

      setTheme: (theme) => {
        set({ theme })

        // Apply theme to document
        const root = document.documentElement
        if (theme === 'dark') {
          root.classList.add('dark')
        } else if (theme === 'light') {
          root.classList.remove('dark')
        } else {
          // System theme
          const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
          if (prefersDark) {
            root.classList.add('dark')
          } else {
            root.classList.remove('dark')
          }
        }
      },

      toggleSidebar: () => {
        set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed }))
      },

      setSidebarCollapsed: (collapsed) => {
        set({ sidebarCollapsed: collapsed })
      },

      setActiveWorkspace: (workspaceId) => {
        set({
          activeWorkspace: workspaceId,
          activeBoard: undefined, // Clear active board when switching workspaces
        })
      },

      setActiveBoard: (boardId) => {
        set({ activeBoard: boardId })
      },

      selectItems: (itemIds) => {
        set({ selectedItems: itemIds })
      },

      toggleItemSelection: (itemId) => {
        set((state) => {
          const isSelected = state.selectedItems.includes(itemId)
          if (isSelected) {
            return {
              selectedItems: state.selectedItems.filter(id => id !== itemId)
            }
          } else {
            return {
              selectedItems: [...state.selectedItems, itemId]
            }
          }
        })
      },

      clearSelection: () => {
        set({ selectedItems: [] })
      },

      setLoading: (key, loading) => {
        set((state) => ({
          loading: {
            ...state.loading,
            [key]: loading,
          },
        }))
      },

      setError: (key, error) => {
        set((state) => ({
          errors: {
            ...state.errors,
            [key]: error,
          },
        }))
      },

      clearErrors: () => {
        set({ errors: {} })
      },
    }),
    {
      name: 'ui-storage',
      partialize: (state) => ({
        theme: state.theme,
        sidebarCollapsed: state.sidebarCollapsed,
        activeWorkspace: state.activeWorkspace,
        activeBoard: state.activeBoard,
      }),
    }
  )
)

// Board view settings store
interface BoardViewStore {
  viewSettings: Record<string, ViewSettings>
  setViewSettings: (boardId: string, settings: ViewSettings) => void
  getViewSettings: (boardId: string) => ViewSettings
}

export const useBoardViewStore = create<BoardViewStore>()(
  persist(
    (set, get) => ({
      viewSettings: {},

      setViewSettings: (boardId, settings) => {
        set((state) => ({
          viewSettings: {
            ...state.viewSettings,
            [boardId]: settings,
          },
        }))
      },

      getViewSettings: (boardId) => {
        const defaultSettings: ViewSettings = {
          view: 'table',
          filters: {},
          sorts: [],
          groupBy: undefined,
          columns: undefined,
        }

        return get().viewSettings[boardId] || defaultSettings
      },
    }),
    {
      name: 'board-view-storage',
    }
  )
)

// Helper hooks
export const useTheme = () => {
  const { theme, setTheme } = useUIStore()
  return { theme, setTheme }
}

export const useSidebar = () => {
  const { sidebarCollapsed, toggleSidebar, setSidebarCollapsed } = useUIStore()
  return { sidebarCollapsed, toggleSidebar, setSidebarCollapsed }
}

export const useActiveWorkspace = () => {
  const { activeWorkspace, setActiveWorkspace } = useUIStore()
  return { activeWorkspace, setActiveWorkspace }
}

export const useActiveBoard = () => {
  const { activeBoard, setActiveBoard } = useUIStore()
  return { activeBoard, setActiveBoard }
}

export const useItemSelection = () => {
  const { selectedItems, selectItems, toggleItemSelection, clearSelection } = useUIStore()
  return { selectedItems, selectItems, toggleItemSelection, clearSelection }
}

export const useLoading = () => {
  const { loading, setLoading } = useUIStore()
  return { loading, setLoading }
}

export const useErrors = () => {
  const { errors, setError, clearErrors } = useUIStore()
  return { errors, setError, clearErrors }
}