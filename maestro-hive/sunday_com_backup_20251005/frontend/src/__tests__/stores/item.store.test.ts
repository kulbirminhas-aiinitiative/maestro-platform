import { renderHook, act, waitFor } from '@testing-library/react'
import { useItemStore } from '@/stores/item.store'
import { api } from '@/lib/api'
import { Item, CreateItemData, UpdateItemData } from '@/types'
import toast from 'react-hot-toast'

// Mock the API
jest.mock('@/lib/api')
jest.mock('react-hot-toast')

const mockApi = api as jest.Mocked<typeof api>
const mockToast = toast as jest.Mocked<typeof toast>

const mockItem: Item = {
  id: 'item-1',
  boardId: 'board-1',
  name: 'Test Item',
  description: 'Test description',
  data: { status: 'todo', priority: 'medium' },
  position: 1,
  createdAt: '2023-01-01T00:00:00Z',
  updatedAt: '2023-01-01T00:00:00Z',
}

const mockItems: Item[] = [
  mockItem,
  {
    id: 'item-2',
    boardId: 'board-1',
    name: 'Test Item 2',
    description: 'Test description 2',
    data: { status: 'in_progress' },
    position: 2,
    createdAt: '2023-01-02T00:00:00Z',
    updatedAt: '2023-01-02T00:00:00Z',
  },
]

describe('useItemStore', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    // Reset store state
    useItemStore.setState({
      items: [],
      currentItem: null,
      loading: {
        items: false,
        currentItem: false,
        creating: false,
        updating: false,
        deleting: false,
        bulkOperations: false,
      },
      errors: {
        items: null,
        currentItem: null,
        creating: null,
        updating: null,
        deleting: null,
        bulkOperations: null,
      },
      pagination: {
        page: 1,
        limit: 50,
        total: 0,
        totalPages: 0,
        hasNext: false,
        hasPrev: false,
      },
      filters: {},
      sorts: [{ field: 'position', direction: 'asc' }],
      draggedItem: null,
      dragOverColumn: null,
    })
  })

  describe('Basic Actions', () => {
    it('should set current item', () => {
      const { result } = renderHook(() => useItemStore())

      act(() => {
        result.current.setCurrentItem(mockItem)
      })

      expect(result.current.currentItem).toEqual(mockItem)
    })

    it('should set filters', () => {
      const { result } = renderHook(() => useItemStore())

      act(() => {
        result.current.setFilters({ status: 'todo' })
      })

      expect(result.current.filters).toEqual({ status: 'todo' })
    })

    it('should set sorts', () => {
      const { result } = renderHook(() => useItemStore())

      const newSorts = [{ field: 'name', direction: 'desc' as const }]

      act(() => {
        result.current.setSorts(newSorts)
      })

      expect(result.current.sorts).toEqual(newSorts)
    })

    it('should set dragged item', () => {
      const { result } = renderHook(() => useItemStore())

      act(() => {
        result.current.setDraggedItem(mockItem)
      })

      expect(result.current.draggedItem).toEqual(mockItem)
    })

    it('should set drag over column', () => {
      const { result } = renderHook(() => useItemStore())

      act(() => {
        result.current.setDragOverColumn('column-1')
      })

      expect(result.current.dragOverColumn).toBe('column-1')
    })
  })

  describe('API Actions', () => {
    describe('fetchItems', () => {
      it('should fetch items successfully', async () => {
        const mockResponse = {
          data: mockItems,
          meta: {
            pagination: {
              page: 1,
              limit: 50,
              total: 2,
              totalPages: 1,
              hasNext: false,
              hasPrev: false,
            },
          },
        }

        mockApi.items.list.mockResolvedValueOnce(mockResponse)

        const { result } = renderHook(() => useItemStore())

        await act(async () => {
          await result.current.fetchItems('board-1')
        })

        expect(result.current.items).toEqual(mockItems)
        expect(result.current.pagination).toEqual(mockResponse.meta.pagination)
        expect(result.current.loading.items).toBe(false)
        expect(result.current.errors.items).toBeNull()
      })

      it('should handle fetch items error', async () => {
        const errorMessage = 'Failed to fetch items'
        mockApi.items.list.mockRejectedValueOnce(new Error(errorMessage))

        const { result } = renderHook(() => useItemStore())

        await act(async () => {
          await result.current.fetchItems('board-1')
        })

        expect(result.current.items).toEqual([])
        expect(result.current.loading.items).toBe(false)
        expect(result.current.errors.items).toBe(errorMessage)
        expect(mockToast.error).toHaveBeenCalledWith(errorMessage)
      })

      it('should set loading state during fetch', async () => {
        let resolvePromise: (value: any) => void
        const promise = new Promise((resolve) => {
          resolvePromise = resolve
        })

        mockApi.items.list.mockReturnValueOnce(promise as any)

        const { result } = renderHook(() => useItemStore())

        act(() => {
          result.current.fetchItems('board-1')
        })

        expect(result.current.loading.items).toBe(true)

        await act(async () => {
          resolvePromise!({
            data: mockItems,
            meta: { pagination: { page: 1, limit: 50, total: 2, totalPages: 1, hasNext: false, hasPrev: false } },
          })
          await promise
        })

        expect(result.current.loading.items).toBe(false)
      })
    })

    describe('fetchItemById', () => {
      it('should fetch item by id successfully', async () => {
        const mockResponse = { data: mockItem }
        mockApi.items.get.mockResolvedValueOnce(mockResponse)

        const { result } = renderHook(() => useItemStore())

        await act(async () => {
          await result.current.fetchItemById('item-1')
        })

        expect(result.current.currentItem).toEqual(mockItem)
        expect(result.current.loading.currentItem).toBe(false)
        expect(result.current.errors.currentItem).toBeNull()
      })

      it('should handle fetch item by id error', async () => {
        const errorMessage = 'Failed to fetch item'
        mockApi.items.get.mockRejectedValueOnce(new Error(errorMessage))

        const { result } = renderHook(() => useItemStore())

        await act(async () => {
          await result.current.fetchItemById('item-1')
        })

        expect(result.current.currentItem).toBeNull()
        expect(result.current.loading.currentItem).toBe(false)
        expect(result.current.errors.currentItem).toBe(errorMessage)
        expect(mockToast.error).toHaveBeenCalledWith(errorMessage)
      })
    })

    describe('createItem', () => {
      it('should create item successfully', async () => {
        const createData: CreateItemData = {
          name: 'New Item',
          description: 'New description',
          boardId: 'board-1',
          itemData: { status: 'todo' },
        }

        const mockResponse = { data: mockItem }
        mockApi.items.create.mockResolvedValueOnce(mockResponse)

        const { result } = renderHook(() => useItemStore())

        let createdItem: Item | null = null
        await act(async () => {
          createdItem = await result.current.createItem('board-1', createData)
        })

        expect(createdItem).toEqual(mockItem)
        expect(result.current.items).toContain(mockItem)
        expect(result.current.loading.creating).toBe(false)
        expect(result.current.errors.creating).toBeNull()
        expect(mockToast.success).toHaveBeenCalledWith('Item created successfully!')
      })

      it('should handle create item error', async () => {
        const createData: CreateItemData = {
          name: 'New Item',
          boardId: 'board-1',
          itemData: {},
        }

        const errorMessage = 'Failed to create item'
        mockApi.items.create.mockRejectedValueOnce(new Error(errorMessage))

        const { result } = renderHook(() => useItemStore())

        let createdItem: Item | null = null
        await act(async () => {
          createdItem = await result.current.createItem('board-1', createData)
        })

        expect(createdItem).toBeNull()
        expect(result.current.loading.creating).toBe(false)
        expect(result.current.errors.creating).toBe(errorMessage)
        expect(mockToast.error).toHaveBeenCalledWith(errorMessage)
      })
    })

    describe('updateItem', () => {
      it('should update item successfully', async () => {
        const updatedItem = { ...mockItem, name: 'Updated Item' }
        const updateData: UpdateItemData = { name: 'Updated Item' }

        mockApi.items.update.mockResolvedValueOnce({ data: updatedItem })

        const { result } = renderHook(() => useItemStore())

        // Set initial items
        act(() => {
          result.current.setCurrentItem(mockItem)
          useItemStore.setState({ items: [mockItem] })
        })

        let resultItem: Item | null = null
        await act(async () => {
          resultItem = await result.current.updateItem('item-1', updateData)
        })

        expect(resultItem).toEqual(updatedItem)
        expect(result.current.items[0]).toEqual(updatedItem)
        expect(result.current.currentItem).toEqual(updatedItem)
        expect(result.current.loading.updating).toBe(false)
        expect(result.current.errors.updating).toBeNull()
        expect(mockToast.success).toHaveBeenCalledWith('Item updated successfully!')
      })

      it('should handle update item error', async () => {
        const updateData: UpdateItemData = { name: 'Updated Item' }
        const errorMessage = 'Failed to update item'
        mockApi.items.update.mockRejectedValueOnce(new Error(errorMessage))

        const { result } = renderHook(() => useItemStore())

        let resultItem: Item | null = null
        await act(async () => {
          resultItem = await result.current.updateItem('item-1', updateData)
        })

        expect(resultItem).toBeNull()
        expect(result.current.loading.updating).toBe(false)
        expect(result.current.errors.updating).toBe(errorMessage)
        expect(mockToast.error).toHaveBeenCalledWith(errorMessage)
      })
    })

    describe('deleteItem', () => {
      it('should delete item successfully', async () => {
        mockApi.items.delete.mockResolvedValueOnce(undefined)

        const { result } = renderHook(() => useItemStore())

        // Set initial items
        act(() => {
          result.current.setCurrentItem(mockItem)
          useItemStore.setState({ items: [mockItem] })
        })

        await act(async () => {
          await result.current.deleteItem('item-1')
        })

        expect(result.current.items).toEqual([])
        expect(result.current.currentItem).toBeNull()
        expect(result.current.loading.deleting).toBe(false)
        expect(result.current.errors.deleting).toBeNull()
        expect(mockToast.success).toHaveBeenCalledWith('Item deleted successfully!')
      })

      it('should handle delete item error', async () => {
        const errorMessage = 'Failed to delete item'
        mockApi.items.delete.mockRejectedValueOnce(new Error(errorMessage))

        const { result } = renderHook(() => useItemStore())

        await act(async () => {
          await result.current.deleteItem('item-1')
        })

        expect(result.current.loading.deleting).toBe(false)
        expect(result.current.errors.deleting).toBe(errorMessage)
        expect(mockToast.error).toHaveBeenCalledWith(errorMessage)
      })
    })

    describe('moveItem', () => {
      it('should move item successfully', async () => {
        const mockResponse = { data: { ...mockItem, position: 5 } }
        mockApi.items.update.mockResolvedValueOnce(mockResponse)

        const { result } = renderHook(() => useItemStore())

        // Set initial items
        act(() => {
          useItemStore.setState({ items: [mockItem] })
        })

        await act(async () => {
          await result.current.moveItem('item-1', 5)
        })

        expect(result.current.items[0].position).toBe(5)
        expect(mockApi.items.update).toHaveBeenCalledWith('item-1', { position: 5 })
      })

      it('should revert item position on move error', async () => {
        const errorMessage = 'Failed to move item'
        mockApi.items.update.mockRejectedValueOnce(new Error(errorMessage))

        const { result } = renderHook(() => useItemStore())

        // Set initial items
        act(() => {
          useItemStore.setState({ items: [mockItem] })
        })

        await act(async () => {
          await result.current.moveItem('item-1', 5)
        })

        // Should revert to original position
        expect(result.current.items[0].position).toBe(mockItem.position)
        expect(mockToast.error).toHaveBeenCalledWith(errorMessage)
      })
    })

    describe('bulk operations', () => {
      it('should bulk update items successfully', async () => {
        const mockResponse = {
          updatedCount: 2,
          errors: [],
        }
        mockApi.items.bulkUpdate.mockResolvedValueOnce(mockResponse)

        const { result } = renderHook(() => useItemStore())

        // Set initial items
        act(() => {
          useItemStore.setState({ items: mockItems })
        })

        await act(async () => {
          await result.current.bulkUpdateItems(['item-1', 'item-2'], { data: { status: 'done' } })
        })

        expect(result.current.loading.bulkOperations).toBe(false)
        expect(result.current.errors.bulkOperations).toBeNull()
        expect(mockToast.success).toHaveBeenCalledWith('2 items updated successfully!')
      })

      it('should bulk delete items successfully', async () => {
        const mockResponse = {
          deletedCount: 2,
          errors: [],
        }
        mockApi.items.bulkDelete.mockResolvedValueOnce(mockResponse)

        const { result } = renderHook(() => useItemStore())

        // Set initial items
        act(() => {
          useItemStore.setState({ items: mockItems })
        })

        await act(async () => {
          await result.current.bulkDeleteItems(['item-1', 'item-2'])
        })

        expect(result.current.items).toEqual([])
        expect(result.current.loading.bulkOperations).toBe(false)
        expect(result.current.errors.bulkOperations).toBeNull()
        expect(mockToast.success).toHaveBeenCalledWith('2 items deleted successfully!')
      })
    })
  })

  describe('Real-time Updates', () => {
    it('should handle item created event', () => {
      const { result } = renderHook(() => useItemStore())

      const newItem = { ...mockItem, id: 'item-new', name: 'New Item' }

      act(() => {
        result.current.handleRealTimeUpdate('item_created', { item: newItem })
      })

      expect(result.current.items).toContain(newItem)
    })

    it('should handle item updated event', () => {
      const { result } = renderHook(() => useItemStore())

      // Set initial items
      act(() => {
        useItemStore.setState({ items: [mockItem] })
      })

      act(() => {
        result.current.handleRealTimeUpdate('item_updated', {
          itemId: 'item-1',
          changes: {
            name: { new: 'Updated Name' },
            data: { new: { status: 'done' } },
          },
        })
      })

      expect(result.current.items[0].name).toBe('Updated Name')
      expect(result.current.items[0].data).toEqual({ status: 'done' })
    })

    it('should handle item deleted event', () => {
      const { result } = renderHook(() => useItemStore())

      // Set initial items
      act(() => {
        result.current.setCurrentItem(mockItem)
        useItemStore.setState({ items: [mockItem] })
      })

      act(() => {
        result.current.handleRealTimeUpdate('item_deleted', { itemId: 'item-1' })
      })

      expect(result.current.items).toEqual([])
      expect(result.current.currentItem).toBeNull()
    })

    it('should not add duplicate items on create event', () => {
      const { result } = renderHook(() => useItemStore())

      // Set initial items
      act(() => {
        useItemStore.setState({ items: [mockItem] })
      })

      act(() => {
        result.current.handleRealTimeUpdate('item_created', { item: mockItem })
      })

      // Should not duplicate the item
      expect(result.current.items).toHaveLength(1)
      expect(result.current.items[0]).toEqual(mockItem)
    })
  })

  describe('Sorting and Filtering', () => {
    it('should maintain sorted order when adding items', async () => {
      const item1 = { ...mockItem, id: 'item-1', position: 3 }
      const item2 = { ...mockItem, id: 'item-2', position: 1 }
      const item3 = { ...mockItem, id: 'item-3', position: 2 }

      const mockResponse = { data: item3 }
      mockApi.items.create.mockResolvedValueOnce(mockResponse)

      const { result } = renderHook(() => useItemStore())

      // Set initial items
      act(() => {
        useItemStore.setState({ items: [item1, item2] })
      })

      await act(async () => {
        await result.current.createItem('board-1', { name: 'Item 3', boardId: 'board-1', itemData: {} })
      })

      // Should be sorted by position
      expect(result.current.items.map(item => item.id)).toEqual(['item-2', 'item-3', 'item-1'])
    })
  })
})