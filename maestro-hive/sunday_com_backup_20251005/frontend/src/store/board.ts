import { create } from 'zustand'
import { devtools } from 'zustand/middleware'
import type {
  Board,
  BoardColumn,
  Item,
  CreateBoardData,
  UpdateItemData,
  CreateItemData,
  ViewSettings,
  ItemFilter,
  ItemSort
} from '@/types'
import { api } from '@/lib/api'

interface BoardState {
  // Current board data
  currentBoard: Board | null
  columns: BoardColumn[]
  items: Item[]

  // UI state
  loading: boolean
  error: string | null
  selectedItems: Set<string>
  viewSettings: ViewSettings

  // Drag and drop state
  draggedItem: Item | null
  draggedOverColumn: string | null

  // Filters and sorting
  filters: ItemFilter
  sorting: ItemSort[]

  // Real-time collaboration
  onlineUsers: string[]
  userCursors: Record<string, { x: number; y: number; user: string }>

  // Actions
  loadBoard: (boardId: string) => Promise<void>
  createBoard: (workspaceId: string, data: CreateBoardData) => Promise<Board>
  updateBoard: (boardId: string, data: Partial<Board>) => Promise<void>
  deleteBoard: (boardId: string) => Promise<void>

  // Column actions
  createColumn: (boardId: string, column: Partial<BoardColumn>) => Promise<void>
  updateColumn: (columnId: string, data: Partial<BoardColumn>) => Promise<void>
  deleteColumn: (columnId: string) => Promise<void>
  reorderColumns: (columnIds: string[]) => Promise<void>

  // Item actions
  createItem: (data: CreateItemData) => Promise<Item>
  updateItem: (itemId: string, data: UpdateItemData) => Promise<void>
  deleteItem: (itemId: string) => Promise<void>
  moveItem: (itemId: string, targetColumnId: string, targetPosition?: number) => Promise<void>
  bulkUpdateItems: (itemIds: string[], data: Partial<UpdateItemData>) => Promise<void>

  // Selection actions
  selectItem: (itemId: string) => void
  selectMultipleItems: (itemIds: string[]) => void
  clearSelection: () => void

  // View actions
  updateViewSettings: (settings: Partial<ViewSettings>) => void
  updateFilters: (filters: Partial<ItemFilter>) => void
  updateSorting: (sorting: ItemSort[]) => void

  // Drag and drop actions
  setDraggedItem: (item: Item | null) => void
  setDraggedOverColumn: (columnId: string | null) => void

  // Real-time actions
  updateOnlineUsers: (users: string[]) => void
  updateUserCursor: (userId: string, position: { x: number; y: number }) => void

  // Utility actions
  reset: () => void
  setError: (error: string | null) => void
  setLoading: (loading: boolean) => void
}

export const useBoardStore = create<BoardState>()(
  devtools(
    (set, get) => ({
      // Initial state
      currentBoard: null,
      columns: [],
      items: [],
      loading: false,
      error: null,
      selectedItems: new Set(),
      viewSettings: {
        view: 'kanban',
        filters: {},
        sorts: [],
        groupBy: undefined,
        columns: undefined,
      },
      draggedItem: null,
      draggedOverColumn: null,
      filters: {},
      sorting: [],
      onlineUsers: [],
      userCursors: {},

      // Board actions
      loadBoard: async (boardId: string) => {
        set({ loading: true, error: null })
        try {
          const response = await api.boards.get(boardId, {
            include: ['columns', 'items', 'members']
          })
          const board = response.data

          set({
            currentBoard: board,
            columns: board.columns || [],
            items: board.items || [],
            loading: false,
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to load board',
            loading: false
          })
        }
      },

      createBoard: async (workspaceId: string, data: CreateBoardData) => {
        set({ loading: true, error: null })
        try {
          const response = await api.boards.create(workspaceId, data)
          set({ loading: false })
          return response.data
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to create board',
            loading: false
          })
          throw error
        }
      },

      updateBoard: async (boardId: string, data: Partial<Board>) => {
        try {
          await api.boards.update(boardId, data)
          const currentBoard = get().currentBoard
          if (currentBoard && currentBoard.id === boardId) {
            set({ currentBoard: { ...currentBoard, ...data } })
          }
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'Failed to update board' })
        }
      },

      deleteBoard: async (boardId: string) => {
        set({ loading: true, error: null })
        try {
          await api.boards.delete(boardId)
          set({
            currentBoard: null,
            columns: [],
            items: [],
            loading: false
          })
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to delete board',
            loading: false
          })
        }
      },

      // Column actions
      createColumn: async (boardId: string, columnData: Partial<BoardColumn>) => {
        try {
          const response = await api.post(`/api/v1/boards/${boardId}/columns`, columnData)
          const newColumn = response.data
          set((state) => ({
            columns: [...state.columns, newColumn]
          }))
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'Failed to create column' })
        }
      },

      updateColumn: async (columnId: string, data: Partial<BoardColumn>) => {
        try {
          await api.put(`/api/v1/columns/${columnId}`, data)
          set((state) => ({
            columns: state.columns.map(col =>
              col.id === columnId ? { ...col, ...data } : col
            )
          }))
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'Failed to update column' })
        }
      },

      deleteColumn: async (columnId: string) => {
        try {
          await api.delete(`/api/v1/columns/${columnId}`)
          set((state) => ({
            columns: state.columns.filter(col => col.id !== columnId),
            items: state.items.filter(item =>
              !item.data.columnId || item.data.columnId !== columnId
            )
          }))
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'Failed to delete column' })
        }
      },

      reorderColumns: async (columnIds: string[]) => {
        const currentBoard = get().currentBoard
        if (!currentBoard) return

        try {
          await api.put(`/api/v1/boards/${currentBoard.id}/columns/reorder`, { columnIds })
          set((state) => ({
            columns: columnIds.map((id, index) => {
              const column = state.columns.find(col => col.id === id)
              return column ? { ...column, position: index } : column!
            }).filter(Boolean)
          }))
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'Failed to reorder columns' })
        }
      },

      // Item actions
      createItem: async (data: CreateItemData) => {
        const currentBoard = get().currentBoard
        if (!currentBoard) throw new Error('No board selected')

        try {
          const response = await api.items.create(currentBoard.id, data)
          const newItem = response.data
          set((state) => ({
            items: [...state.items, newItem]
          }))
          return newItem
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'Failed to create item' })
          throw error
        }
      },

      updateItem: async (itemId: string, data: UpdateItemData) => {
        try {
          await api.items.update(itemId, data)
          set((state) => ({
            items: state.items.map(item =>
              item.id === itemId ? { ...item, ...data } : item
            )
          }))
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'Failed to update item' })
        }
      },

      deleteItem: async (itemId: string) => {
        try {
          await api.items.delete(itemId)
          set((state) => ({
            items: state.items.filter(item => item.id !== itemId),
            selectedItems: new Set([...state.selectedItems].filter(id => id !== itemId))
          }))
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'Failed to delete item' })
        }
      },

      moveItem: async (itemId: string, targetColumnId: string, targetPosition?: number) => {
        try {
          const updateData = {
            data: { columnId: targetColumnId },
            position: targetPosition
          }
          await api.items.update(itemId, updateData)

          set((state) => ({
            items: state.items.map(item =>
              item.id === itemId
                ? {
                    ...item,
                    data: { ...item.data, columnId: targetColumnId },
                    position: targetPosition ?? item.position
                  }
                : item
            )
          }))
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'Failed to move item' })
        }
      },

      bulkUpdateItems: async (itemIds: string[], data: Partial<UpdateItemData>) => {
        try {
          await api.items.bulkUpdate({ itemIds, data })
          set((state) => ({
            items: state.items.map(item =>
              itemIds.includes(item.id) ? { ...item, ...data } : item
            )
          }))
        } catch (error) {
          set({ error: error instanceof Error ? error.message : 'Failed to bulk update items' })
        }
      },

      // Selection actions
      selectItem: (itemId: string) => {
        set((state) => ({
          selectedItems: new Set([...state.selectedItems, itemId])
        }))
      },

      selectMultipleItems: (itemIds: string[]) => {
        set({ selectedItems: new Set(itemIds) })
      },

      clearSelection: () => {
        set({ selectedItems: new Set() })
      },

      // View actions
      updateViewSettings: (settings: Partial<ViewSettings>) => {
        set((state) => ({
          viewSettings: { ...state.viewSettings, ...settings }
        }))
      },

      updateFilters: (filters: Partial<ItemFilter>) => {
        set((state) => ({
          filters: { ...state.filters, ...filters }
        }))
      },

      updateSorting: (sorting: ItemSort[]) => {
        set({ sorting })
      },

      // Drag and drop actions
      setDraggedItem: (item: Item | null) => {
        set({ draggedItem: item })
      },

      setDraggedOverColumn: (columnId: string | null) => {
        set({ draggedOverColumn: columnId })
      },

      // Real-time actions
      updateOnlineUsers: (users: string[]) => {
        set({ onlineUsers: users })
      },

      updateUserCursor: (userId: string, position: { x: number; y: number }) => {
        set((state) => ({
          userCursors: {
            ...state.userCursors,
            [userId]: { ...position, user: userId }
          }
        }))
      },

      // Utility actions
      reset: () => {
        set({
          currentBoard: null,
          columns: [],
          items: [],
          loading: false,
          error: null,
          selectedItems: new Set(),
          draggedItem: null,
          draggedOverColumn: null,
          filters: {},
          sorting: [],
          onlineUsers: [],
          userCursors: {},
        })
      },

      setError: (error: string | null) => {
        set({ error })
      },

      setLoading: (loading: boolean) => {
        set({ loading })
      },
    }),
    {
      name: 'board-store',
      partialize: (state) => ({
        viewSettings: state.viewSettings,
        filters: state.filters,
        sorting: state.sorting,
      }),
    }
  )
)

export default useBoardStore