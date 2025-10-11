import { act, renderHook } from '@testing-library/react'
import { useBoardStore } from '@/stores/board.store'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'

// Mock dependencies
jest.mock('@/lib/api')
jest.mock('react-hot-toast')

const mockApi = api as jest.Mocked<typeof api>
const mockToast = toast as jest.Mocked<typeof toast>

const mockBoard = {
  id: 'board-1',
  name: 'Test Board',
  description: 'Test description',
  workspaceId: 'workspace-1',
  isPrivate: false,
  settings: {},
  viewSettings: {},
  position: 0,
  createdAt: '2023-01-01T00:00:00Z',
  updatedAt: '2023-01-01T00:00:00Z',
  columns: [],
  items: [],
  members: [],
}

describe('useBoardStore', () => {
  beforeEach(() => {
    // Reset store before each test
    useBoardStore.setState({
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
    })

    jest.clearAllMocks()
  })

  describe('fetchBoards', () => {
    it('fetches boards successfully', async () => {
      const mockResponse = {
        data: [mockBoard],
        meta: {
          pagination: {
            page: 1,
            limit: 20,
            total: 1,
            totalPages: 1,
            hasNext: false,
            hasPrev: false,
          },
        },
      }

      mockApi.boards.list.mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useBoardStore())

      await act(async () => {
        await result.current.fetchBoards('workspace-1')
      })

      expect(result.current.boards).toEqual([mockBoard])
      expect(result.current.loading.boards).toBe(false)
      expect(result.current.errors.boards).toBe(null)
    })

    it('handles fetch error', async () => {
      const error = new Error('Failed to fetch boards')
      mockApi.boards.list.mockRejectedValue(error)

      const { result } = renderHook(() => useBoardStore())

      await act(async () => {
        await result.current.fetchBoards('workspace-1')
      })

      expect(result.current.boards).toEqual([])
      expect(result.current.loading.boards).toBe(false)
      expect(result.current.errors.boards).toBe('Failed to fetch boards')
      expect(mockToast.error).toHaveBeenCalledWith('Failed to fetch boards')
    })

    it('sets loading state during fetch', async () => {
      let resolvePromise: (value: any) => void
      const promise = new Promise((resolve) => {
        resolvePromise = resolve
      })

      mockApi.boards.list.mockReturnValue(promise as any)

      const { result } = renderHook(() => useBoardStore())

      act(() => {
        result.current.fetchBoards('workspace-1')
      })

      expect(result.current.loading.boards).toBe(true)

      await act(async () => {
        resolvePromise!({
          data: [mockBoard],
          meta: { pagination: { page: 1, limit: 20, total: 1, totalPages: 1, hasNext: false, hasPrev: false } },
        })
        await promise
      })

      expect(result.current.loading.boards).toBe(false)
    })
  })

  describe('fetchBoardById', () => {
    it('fetches board by id successfully', async () => {
      const mockResponse = { data: mockBoard }
      mockApi.boards.get.mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useBoardStore())

      await act(async () => {
        await result.current.fetchBoardById('board-1')
      })

      expect(result.current.currentBoard).toEqual(mockBoard)
      expect(result.current.columns).toEqual([])
      expect(result.current.items).toEqual([])
      expect(result.current.loading.currentBoard).toBe(false)
    })

    it('handles fetch board error', async () => {
      const error = new Error('Board not found')
      mockApi.boards.get.mockRejectedValue(error)

      const { result } = renderHook(() => useBoardStore())

      await act(async () => {
        await result.current.fetchBoardById('board-1')
      })

      expect(result.current.currentBoard).toBe(null)
      expect(result.current.errors.currentBoard).toBe('Board not found')
      expect(mockToast.error).toHaveBeenCalledWith('Board not found')
    })
  })

  describe('createBoard', () => {
    it('creates board successfully', async () => {
      const createData = {
        name: 'New Board',
        description: 'New description',
        isPrivate: false,
      }

      const mockResponse = { data: mockBoard }
      mockApi.boards.create.mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useBoardStore())

      let createdBoard: any
      await act(async () => {
        createdBoard = await result.current.createBoard('workspace-1', createData)
      })

      expect(createdBoard).toEqual(mockBoard)
      expect(result.current.boards).toContain(mockBoard)
      expect(mockToast.success).toHaveBeenCalledWith('Board created successfully!')
    })

    it('handles create error', async () => {
      const error = new Error('Failed to create board')
      mockApi.boards.create.mockRejectedValue(error)

      const { result } = renderHook(() => useBoardStore())

      let createdBoard: any
      await act(async () => {
        createdBoard = await result.current.createBoard('workspace-1', {
          name: 'New Board',
        })
      })

      expect(createdBoard).toBe(null)
      expect(result.current.errors.creating).toBe('Failed to create board')
      expect(mockToast.error).toHaveBeenCalledWith('Failed to create board')
    })
  })

  describe('updateBoard', () => {
    it('updates board successfully', async () => {
      const updatedBoard = { ...mockBoard, name: 'Updated Board' }
      const mockResponse = { data: updatedBoard }
      mockApi.boards.update.mockResolvedValue(mockResponse)

      const { result } = renderHook(() => useBoardStore())

      // Set initial state
      act(() => {
        result.current.setCurrentBoard(mockBoard)
        useBoardStore.setState({ boards: [mockBoard] })
      })

      let updatedResult: any
      await act(async () => {
        updatedResult = await result.current.updateBoard('board-1', { name: 'Updated Board' })
      })

      expect(updatedResult).toEqual(updatedBoard)
      expect(result.current.currentBoard?.name).toBe('Updated Board')
      expect(mockToast.success).toHaveBeenCalledWith('Board updated successfully!')
    })
  })

  describe('deleteBoard', () => {
    it('deletes board successfully', async () => {
      mockApi.boards.delete.mockResolvedValue({} as any)

      const { result } = renderHook(() => useBoardStore())

      // Set initial state
      act(() => {
        result.current.setCurrentBoard(mockBoard)
        useBoardStore.setState({ boards: [mockBoard] })
      })

      await act(async () => {
        await result.current.deleteBoard('board-1')
      })

      expect(result.current.boards).toEqual([])
      expect(result.current.currentBoard).toBe(null)
      expect(mockToast.success).toHaveBeenCalledWith('Board deleted successfully!')
    })
  })

  describe('setCurrentBoard', () => {
    it('sets current board and related data', () => {
      const { result } = renderHook(() => useBoardStore())

      const boardWithData = {
        ...mockBoard,
        columns: [{ id: 'col-1', name: 'Column 1' }],
        items: [{ id: 'item-1', name: 'Item 1' }],
      }

      act(() => {
        result.current.setCurrentBoard(boardWithData as any)
      })

      expect(result.current.currentBoard).toEqual(boardWithData)
      expect(result.current.columns).toEqual(boardWithData.columns)
      expect(result.current.items).toEqual(boardWithData.items)
      expect(result.current.selectedItems).toEqual([])
    })
  })

  describe('item selection', () => {
    it('toggles item selection', () => {
      const { result } = renderHook(() => useBoardStore())

      act(() => {
        result.current.toggleItemSelection('item-1')
      })

      expect(result.current.selectedItems).toEqual(['item-1'])

      act(() => {
        result.current.toggleItemSelection('item-1')
      })

      expect(result.current.selectedItems).toEqual([])
    })

    it('clears selection', () => {
      const { result } = renderHook(() => useBoardStore())

      act(() => {
        result.current.setSelectedItems(['item-1', 'item-2'])
      })

      expect(result.current.selectedItems).toEqual(['item-1', 'item-2'])

      act(() => {
        result.current.clearSelection()
      })

      expect(result.current.selectedItems).toEqual([])
    })
  })

  describe('real-time updates', () => {
    it('handles board_updated event', () => {
      const { result } = renderHook(() => useBoardStore())

      act(() => {
        result.current.setCurrentBoard(mockBoard)
        useBoardStore.setState({ boards: [mockBoard] })
      })

      act(() => {
        result.current.handleRealTimeUpdate('board_updated', {
          boardId: 'board-1',
          changes: { name: 'Updated Name' },
        })
      })

      expect(result.current.currentBoard?.name).toBe('Updated Name')
    })

    it('handles board_deleted event', () => {
      const { result } = renderHook(() => useBoardStore())

      act(() => {
        result.current.setCurrentBoard(mockBoard)
        useBoardStore.setState({ boards: [mockBoard] })
      })

      act(() => {
        result.current.handleRealTimeUpdate('board_deleted', {
          boardId: 'board-1',
        })
      })

      expect(result.current.boards).toEqual([])
      expect(result.current.currentBoard).toBe(null)
    })
  })
})