import { act, renderHook } from '@testing-library/react'
import { useBoardStore } from '../board'
import { api } from '@/lib/api'
import type { Board, BoardColumn, Item, CreateItemData } from '@/types'

// Mock the API
jest.mock('@/lib/api', () => ({
  api: {
    boards: {
      get: jest.fn(),
      create: jest.fn(),
      update: jest.fn(),
      delete: jest.fn()
    },
    items: {
      create: jest.fn(),
      update: jest.fn(),
      delete: jest.fn(),
      bulkUpdate: jest.fn()
    },
    post: jest.fn(),
    put: jest.fn(),
    delete: jest.fn()
  }
}))

const mockApi = api as jest.Mocked<typeof api>

// Mock data
const mockBoard: Board = {
  id: 'board-1',
  workspaceId: 'workspace-1',
  name: 'Test Board',
  description: 'A test board',
  isPrivate: false,
  settings: {},
  viewSettings: {},
  createdAt: '2023-01-01T00:00:00Z',
  updatedAt: '2023-01-01T00:00:00Z',
  position: 1
}

const mockColumns: BoardColumn[] = [
  {
    id: 'col-1',
    boardId: 'board-1',
    name: 'To Do',
    columnType: 'status',
    position: 0,
    isRequired: false,
    isVisible: true,
    settings: { statusValue: 'todo' },
    validationRules: {},
    createdAt: '2023-01-01T00:00:00Z'
  },
  {
    id: 'col-2',
    boardId: 'board-1',
    name: 'Done',
    columnType: 'status',
    position: 1,
    isRequired: false,
    isVisible: true,
    settings: { statusValue: 'done' },
    validationRules: {},
    createdAt: '2023-01-01T00:00:00Z'
  }
]

const mockItems: Item[] = [
  {
    id: 'item-1',
    boardId: 'board-1',
    name: 'Test Item 1',
    description: 'First test item',
    data: { status: 'todo' },
    position: 1,
    createdAt: '2023-01-01T00:00:00Z',
    updatedAt: '2023-01-01T00:00:00Z'
  },
  {
    id: 'item-2',
    boardId: 'board-1',
    name: 'Test Item 2',
    description: 'Second test item',
    data: { status: 'done' },
    position: 1,
    createdAt: '2023-01-01T00:00:00Z',
    updatedAt: '2023-01-01T00:00:00Z'
  }
]

describe('Board Store', () => {
  beforeEach(() => {
    jest.clearAllMocks()

    // Reset the store state
    const { result } = renderHook(() => useBoardStore())
    act(() => {
      result.current.reset()
    })
  })

  describe('loadBoard', () => {
    it('loads board data successfully', async () => {
      mockApi.boards.get.mockResolvedValue({
        data: {
          ...mockBoard,
          columns: mockColumns,
          items: mockItems
        }
      })

      const { result } = renderHook(() => useBoardStore())

      await act(async () => {
        await result.current.loadBoard('board-1')
      })

      expect(mockApi.boards.get).toHaveBeenCalledWith('board-1', {
        include: ['columns', 'items', 'members']
      })
      expect(result.current.currentBoard).toEqual(mockBoard)
      expect(result.current.columns).toEqual(mockColumns)
      expect(result.current.items).toEqual(mockItems)
      expect(result.current.loading).toBe(false)
      expect(result.current.error).toBeNull()
    })

    it('handles load board error', async () => {
      const errorMessage = 'Failed to load board'
      mockApi.boards.get.mockRejectedValue(new Error(errorMessage))

      const { result } = renderHook(() => useBoardStore())

      await act(async () => {
        await result.current.loadBoard('board-1')
      })

      expect(result.current.currentBoard).toBeNull()
      expect(result.current.loading).toBe(false)
      expect(result.current.error).toBe(errorMessage)
    })

    it('sets loading state during board load', async () => {
      let resolvePromise: (value: any) => void
      const promise = new Promise((resolve) => {
        resolvePromise = resolve
      })
      mockApi.boards.get.mockReturnValue(promise as any)

      const { result } = renderHook(() => useBoardStore())

      act(() => {
        result.current.loadBoard('board-1')
      })

      expect(result.current.loading).toBe(true)
      expect(result.current.error).toBeNull()

      await act(async () => {
        resolvePromise({ data: mockBoard })
      })

      expect(result.current.loading).toBe(false)
    })
  })

  describe('createBoard', () => {
    it('creates board successfully', async () => {
      const newBoard = { ...mockBoard, id: 'new-board' }
      mockApi.boards.create.mockResolvedValue({ data: newBoard })

      const { result } = renderHook(() => useBoardStore())

      let createdBoard: Board
      await act(async () => {
        createdBoard = await result.current.createBoard('workspace-1', {
          name: 'New Board',
          description: 'New board description'
        })
      })

      expect(mockApi.boards.create).toHaveBeenCalledWith('workspace-1', {
        name: 'New Board',
        description: 'New board description'
      })
      expect(createdBoard!).toEqual(newBoard)
      expect(result.current.loading).toBe(false)
    })

    it('handles create board error', async () => {
      const errorMessage = 'Failed to create board'
      mockApi.boards.create.mockRejectedValue(new Error(errorMessage))

      const { result } = renderHook(() => useBoardStore())

      await act(async () => {
        try {
          await result.current.createBoard('workspace-1', {
            name: 'New Board'
          })
        } catch (error) {
          // Expected to throw
        }
      })

      expect(result.current.error).toBe(errorMessage)
      expect(result.current.loading).toBe(false)
    })
  })

  describe('createItem', () => {
    it('creates item successfully', async () => {
      const newItem: Item = {
        id: 'new-item',
        boardId: 'board-1',
        name: 'New Item',
        description: 'New item description',
        data: { status: 'todo' },
        position: 1,
        createdAt: '2023-01-01T00:00:00Z',
        updatedAt: '2023-01-01T00:00:00Z'
      }

      mockApi.items.create.mockResolvedValue({ data: newItem })

      const { result } = renderHook(() => useBoardStore())

      // Set up initial state
      act(() => {
        result.current.currentBoard = mockBoard
        result.current.items = mockItems
      })

      const createData: CreateItemData = {
        name: 'New Item',
        description: 'New item description',
        data: { status: 'todo' }
      }

      let createdItem: Item
      await act(async () => {
        createdItem = await result.current.createItem(createData)
      })

      expect(mockApi.items.create).toHaveBeenCalledWith('board-1', createData)
      expect(createdItem!).toEqual(newItem)
      expect(result.current.items).toContain(newItem)
    })

    it('throws error when no board is selected', async () => {
      const { result } = renderHook(() => useBoardStore())

      await act(async () => {
        try {
          await result.current.createItem({
            name: 'New Item'
          })
        } catch (error) {
          expect(error).toEqual(new Error('No board selected'))
        }
      })
    })
  })

  describe('updateItem', () => {
    it('updates item successfully', async () => {
      mockApi.items.update.mockResolvedValue({})

      const { result } = renderHook(() => useBoardStore())

      // Set up initial state
      act(() => {
        result.current.items = mockItems
      })

      await act(async () => {
        await result.current.updateItem('item-1', {
          name: 'Updated Item'
        })
      })

      expect(mockApi.items.update).toHaveBeenCalledWith('item-1', {
        name: 'Updated Item'
      })

      const updatedItem = result.current.items.find(item => item.id === 'item-1')
      expect(updatedItem?.name).toBe('Updated Item')
    })
  })

  describe('moveItem', () => {
    it('moves item successfully', async () => {
      mockApi.items.update.mockResolvedValue({})

      const { result } = renderHook(() => useBoardStore())

      // Set up initial state
      act(() => {
        result.current.items = mockItems
      })

      await act(async () => {
        await result.current.moveItem('item-1', 'col-2', 2)
      })

      expect(mockApi.items.update).toHaveBeenCalledWith('item-1', {
        data: { columnId: 'col-2' },
        position: 2
      })

      const movedItem = result.current.items.find(item => item.id === 'item-1')
      expect(movedItem?.data.columnId).toBe('col-2')
      expect(movedItem?.position).toBe(2)
    })
  })

  describe('deleteItem', () => {
    it('deletes item successfully', async () => {
      mockApi.items.delete.mockResolvedValue({})

      const { result } = renderHook(() => useBoardStore())

      // Set up initial state
      act(() => {
        result.current.items = mockItems
        result.current.selectedItems = new Set(['item-1'])
      })

      await act(async () => {
        await result.current.deleteItem('item-1')
      })

      expect(mockApi.items.delete).toHaveBeenCalledWith('item-1')
      expect(result.current.items).not.toContain(
        expect.objectContaining({ id: 'item-1' })
      )
      expect(result.current.selectedItems.has('item-1')).toBe(false)
    })
  })

  describe('selection management', () => {
    it('selects item', () => {
      const { result } = renderHook(() => useBoardStore())

      act(() => {
        result.current.selectItem('item-1')
      })

      expect(result.current.selectedItems.has('item-1')).toBe(true)
    })

    it('selects multiple items', () => {
      const { result } = renderHook(() => useBoardStore())

      act(() => {
        result.current.selectMultipleItems(['item-1', 'item-2'])
      })

      expect(result.current.selectedItems.has('item-1')).toBe(true)
      expect(result.current.selectedItems.has('item-2')).toBe(true)
    })

    it('clears selection', () => {
      const { result } = renderHook(() => useBoardStore())

      act(() => {
        result.current.selectMultipleItems(['item-1', 'item-2'])
        result.current.clearSelection()
      })

      expect(result.current.selectedItems.size).toBe(0)
    })
  })

  describe('filters and view settings', () => {
    it('updates filters', () => {
      const { result } = renderHook(() => useBoardStore())

      act(() => {
        result.current.updateFilters({
          status: ['todo', 'in_progress'],
          assigneeIds: ['user-1']
        })
      })

      expect(result.current.filters.status).toEqual(['todo', 'in_progress'])
      expect(result.current.filters.assigneeIds).toEqual(['user-1'])
    })

    it('updates view settings', () => {
      const { result } = renderHook(() => useBoardStore())

      act(() => {
        result.current.updateViewSettings({
          view: 'list',
          groupBy: 'status'
        })
      })

      expect(result.current.viewSettings.view).toBe('list')
      expect(result.current.viewSettings.groupBy).toBe('status')
    })

    it('updates sorting', () => {
      const { result } = renderHook(() => useBoardStore())

      const sorting = [
        { field: 'created_at' as const, direction: 'desc' as const }
      ]

      act(() => {
        result.current.updateSorting(sorting)
      })

      expect(result.current.sorting).toEqual(sorting)
    })
  })

  describe('drag and drop', () => {
    it('sets dragged item', () => {
      const { result } = renderHook(() => useBoardStore())

      act(() => {
        result.current.setDraggedItem(mockItems[0])
      })

      expect(result.current.draggedItem).toEqual(mockItems[0])
    })

    it('sets dragged over column', () => {
      const { result } = renderHook(() => useBoardStore())

      act(() => {
        result.current.setDraggedOverColumn('col-2')
      })

      expect(result.current.draggedOverColumn).toBe('col-2')
    })
  })

  describe('real-time collaboration', () => {
    it('updates online users', () => {
      const { result } = renderHook(() => useBoardStore())

      act(() => {
        result.current.updateOnlineUsers(['user-1', 'user-2'])
      })

      expect(result.current.onlineUsers).toEqual(['user-1', 'user-2'])
    })

    it('updates user cursor', () => {
      const { result } = renderHook(() => useBoardStore())

      act(() => {
        result.current.updateUserCursor('user-1', { x: 100, y: 200 })
      })

      expect(result.current.userCursors['user-1']).toEqual({
        x: 100,
        y: 200,
        user: 'user-1'
      })
    })
  })

  describe('utility functions', () => {
    it('resets store state', () => {
      const { result } = renderHook(() => useBoardStore())

      // Set some state
      act(() => {
        result.current.currentBoard = mockBoard
        result.current.items = mockItems
        result.current.selectedItems = new Set(['item-1'])
        result.current.setError('Test error')
      })

      // Reset
      act(() => {
        result.current.reset()
      })

      expect(result.current.currentBoard).toBeNull()
      expect(result.current.items).toEqual([])
      expect(result.current.selectedItems.size).toBe(0)
      expect(result.current.error).toBeNull()
    })

    it('sets error', () => {
      const { result } = renderHook(() => useBoardStore())

      act(() => {
        result.current.setError('Test error')
      })

      expect(result.current.error).toBe('Test error')
    })

    it('sets loading', () => {
      const { result } = renderHook(() => useBoardStore())

      act(() => {
        result.current.setLoading(true)
      })

      expect(result.current.loading).toBe(true)
    })
  })

  describe('bulk operations', () => {
    it('bulk updates items successfully', async () => {
      mockApi.items.bulkUpdate.mockResolvedValue({})

      const { result } = renderHook(() => useBoardStore())

      // Set up initial state
      act(() => {
        result.current.items = mockItems
      })

      const updateData = { data: { status: 'in_progress' } }

      await act(async () => {
        await result.current.bulkUpdateItems(['item-1', 'item-2'], updateData)
      })

      expect(mockApi.items.bulkUpdate).toHaveBeenCalledWith({
        itemIds: ['item-1', 'item-2'],
        data: updateData
      })

      // Check that items were updated in the state
      const updatedItems = result.current.items.filter(item =>
        ['item-1', 'item-2'].includes(item.id)
      )
      updatedItems.forEach(item => {
        expect(item.data.status).toBe('in_progress')
      })
    })
  })
})