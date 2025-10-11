import { create } from 'zustand'
import { devtools, subscribeWithSelector } from 'zustand/middleware'
import { produce } from 'immer'
import { Board, BoardColumn, Item, CreateBoardData, UpdateBoardData, PaginatedResponse, ApiResponse } from '@/types'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'

interface BoardState {
  // Data
  boards: Board[]
  currentBoard: Board | null
  columns: BoardColumn[]
  items: Item[]

  // UI State
  loading: {
    boards: boolean
    currentBoard: boolean
    creating: boolean
    updating: boolean
    deleting: boolean
  }
  errors: {
    boards: string | null
    currentBoard: string | null
    creating: string | null
    updating: string | null
    deleting: string | null
  }

  // Pagination
  pagination: {
    page: number
    limit: number
    total: number
    totalPages: number
    hasNext: boolean
    hasPrev: boolean
  }

  // Filters and sorting
  filters: {
    workspaceId?: string
    folderId?: string
    search?: string
  }

  // Selected items for bulk operations
  selectedItems: string[]

  // Actions
  setCurrentBoard: (board: Board | null) => void
  setFilters: (filters: Partial<BoardState['filters']>) => void
  setSelectedItems: (itemIds: string[]) => void
  toggleItemSelection: (itemId: string) => void
  clearSelection: () => void

  // API Actions
  fetchBoards: (workspaceId: string, params?: any) => Promise<void>
  fetchBoardById: (boardId: string, includeItems?: boolean) => Promise<void>
  createBoard: (workspaceId: string, data: CreateBoardData) => Promise<Board | null>
  updateBoard: (boardId: string, data: UpdateBoardData) => Promise<Board | null>
  deleteBoard: (boardId: string) => Promise<void>

  // Column actions
  createColumn: (boardId: string, data: any) => Promise<void>
  updateColumn: (columnId: string, data: any) => Promise<void>
  deleteColumn: (columnId: string) => Promise<void>
  reorderColumns: (boardId: string, columns: BoardColumn[]) => Promise<void>

  // Real-time updates
  handleRealTimeUpdate: (event: string, data: any) => void
}

export const useBoardStore = create<BoardState>()(
  devtools(
    subscribeWithSelector(
      (set, get) => ({
        // Initial state
        boards: [],
        currentBoard: null,
        columns: [],
        items: [],

        loading: {
          boards: false,
          currentBoard: false,
          creating: false,
          updating: false,
          deleting: false,
        },

        errors: {
          boards: null,
          currentBoard: null,
          creating: null,
          updating: null,
          deleting: null,
        },

        pagination: {
          page: 1,
          limit: 20,
          total: 0,
          totalPages: 0,
          hasNext: false,
          hasPrev: false,
        },

        filters: {},
        selectedItems: [],

        // Actions
        setCurrentBoard: (board) => {
          set(produce((state) => {
            state.currentBoard = board
            state.columns = board?.columns || []
            state.items = board?.items || []
            state.selectedItems = []
          }))
        },

        setFilters: (newFilters) => {
          set(produce((state) => {
            state.filters = { ...state.filters, ...newFilters }
          }))
        },

        setSelectedItems: (itemIds) => {
          set(produce((state) => {
            state.selectedItems = itemIds
          }))
        },

        toggleItemSelection: (itemId) => {
          set(produce((state) => {
            const index = state.selectedItems.indexOf(itemId)
            if (index === -1) {
              state.selectedItems.push(itemId)
            } else {
              state.selectedItems.splice(index, 1)
            }
          }))
        },

        clearSelection: () => {
          set(produce((state) => {
            state.selectedItems = []
          }))
        },

        // API Actions
        fetchBoards: async (workspaceId, params = {}) => {
          set(produce((state) => {
            state.loading.boards = true
            state.errors.boards = null
          }))

          try {
            const response = await api.boards.list(workspaceId, {
              page: get().pagination.page,
              limit: get().pagination.limit,
              ...get().filters,
              ...params,
            }) as PaginatedResponse<Board>

            set(produce((state) => {
              state.boards = response.data
              state.pagination = response.meta.pagination
              state.loading.boards = false
            }))
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to fetch boards'
            set(produce((state) => {
              state.errors.boards = errorMessage
              state.loading.boards = false
            }))
            toast.error(errorMessage)
          }
        },

        fetchBoardById: async (boardId, includeItems = true) => {
          set(produce((state) => {
            state.loading.currentBoard = true
            state.errors.currentBoard = null
          }))

          try {
            const response = await api.boards.get(boardId, {
              includeColumns: true,
              includeItems,
              includeMembers: true,
            }) as ApiResponse<Board>

            set(produce((state) => {
              state.currentBoard = response.data
              state.columns = response.data.columns || []
              state.items = response.data.items || []
              state.loading.currentBoard = false
            }))
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to fetch board'
            set(produce((state) => {
              state.errors.currentBoard = errorMessage
              state.loading.currentBoard = false
            }))
            toast.error(errorMessage)
          }
        },

        createBoard: async (workspaceId, data) => {
          set(produce((state) => {
            state.loading.creating = true
            state.errors.creating = null
          }))

          try {
            const response = await api.boards.create(workspaceId, data) as ApiResponse<Board>

            set(produce((state) => {
              state.boards.unshift(response.data)
              state.loading.creating = false
            }))

            toast.success('Board created successfully!')
            return response.data
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to create board'
            set(produce((state) => {
              state.errors.creating = errorMessage
              state.loading.creating = false
            }))
            toast.error(errorMessage)
            return null
          }
        },

        updateBoard: async (boardId, data) => {
          set(produce((state) => {
            state.loading.updating = true
            state.errors.updating = null
          }))

          try {
            const response = await api.boards.update(boardId, data) as ApiResponse<Board>

            set(produce((state) => {
              // Update in boards list
              const index = state.boards.findIndex(b => b.id === boardId)
              if (index !== -1) {
                state.boards[index] = response.data
              }

              // Update current board if it's the same
              if (state.currentBoard?.id === boardId) {
                state.currentBoard = response.data
              }

              state.loading.updating = false
            }))

            toast.success('Board updated successfully!')
            return response.data
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to update board'
            set(produce((state) => {
              state.errors.updating = errorMessage
              state.loading.updating = false
            }))
            toast.error(errorMessage)
            return null
          }
        },

        deleteBoard: async (boardId) => {
          set(produce((state) => {
            state.loading.deleting = true
            state.errors.deleting = null
          }))

          try {
            await api.boards.delete(boardId)

            set(produce((state) => {
              state.boards = state.boards.filter(b => b.id !== boardId)
              if (state.currentBoard?.id === boardId) {
                state.currentBoard = null
                state.columns = []
                state.items = []
              }
              state.loading.deleting = false
            }))

            toast.success('Board deleted successfully!')
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to delete board'
            set(produce((state) => {
              state.errors.deleting = errorMessage
              state.loading.deleting = false
            }))
            toast.error(errorMessage)
          }
        },

        // Column actions
        createColumn: async (boardId, data) => {
          try {
            const response = await api.post(`/api/v1/boards/${boardId}/columns`, data) as ApiResponse<BoardColumn>

            set(produce((state) => {
              state.columns.push(response.data)
              state.columns.sort((a, b) => a.position - b.position)
            }))

            toast.success('Column created successfully!')
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to create column'
            toast.error(errorMessage)
          }
        },

        updateColumn: async (columnId, data) => {
          try {
            const response = await api.put(`/api/v1/columns/${columnId}`, data) as ApiResponse<BoardColumn>

            set(produce((state) => {
              const index = state.columns.findIndex(c => c.id === columnId)
              if (index !== -1) {
                state.columns[index] = response.data
              }
            }))

            toast.success('Column updated successfully!')
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to update column'
            toast.error(errorMessage)
          }
        },

        deleteColumn: async (columnId) => {
          try {
            await api.delete(`/api/v1/columns/${columnId}`)

            set(produce((state) => {
              state.columns = state.columns.filter(c => c.id !== columnId)
            }))

            toast.success('Column deleted successfully!')
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to delete column'
            toast.error(errorMessage)
          }
        },

        reorderColumns: async (boardId, columns) => {
          // Optimistically update the UI
          set(produce((state) => {
            state.columns = columns
          }))

          try {
            // Update positions on the server
            await Promise.all(
              columns.map((column, index) =>
                api.put(`/api/v1/columns/${column.id}`, { position: index })
              )
            )
          } catch (error) {
            // Revert on error by refetching
            get().fetchBoardById(boardId, false)
            const errorMessage = error instanceof Error ? error.message : 'Failed to reorder columns'
            toast.error(errorMessage)
          }
        },

        // Real-time updates
        handleRealTimeUpdate: (event, data) => {
          switch (event) {
            case 'board_updated':
              set(produce((state) => {
                if (state.currentBoard?.id === data.boardId) {
                  // Merge updates
                  Object.assign(state.currentBoard, data.changes)
                }

                const index = state.boards.findIndex(b => b.id === data.boardId)
                if (index !== -1) {
                  Object.assign(state.boards[index], data.changes)
                }
              }))
              break

            case 'board_deleted':
              set(produce((state) => {
                state.boards = state.boards.filter(b => b.id !== data.boardId)
                if (state.currentBoard?.id === data.boardId) {
                  state.currentBoard = null
                  state.columns = []
                  state.items = []
                }
              }))
              break

            case 'column_created':
              set(produce((state) => {
                if (state.currentBoard?.id === data.column.boardId) {
                  state.columns.push(data.column)
                  state.columns.sort((a, b) => a.position - b.position)
                }
              }))
              break

            case 'column_updated':
              set(produce((state) => {
                const index = state.columns.findIndex(c => c.id === data.column.id)
                if (index !== -1) {
                  state.columns[index] = data.column
                }
              }))
              break

            case 'column_deleted':
              set(produce((state) => {
                state.columns = state.columns.filter(c => c.id !== data.columnId)
              }))
              break
          }
        },
      })
    ),
    { name: 'board-store' }
  )
)