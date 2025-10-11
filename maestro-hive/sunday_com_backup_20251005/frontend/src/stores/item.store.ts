import { create } from 'zustand'
import { devtools, subscribeWithSelector } from 'zustand/middleware'
import { produce } from 'immer'
import { Item, CreateItemData, UpdateItemData, ItemFilter, ItemSort, PaginatedResponse, ApiResponse } from '@/types'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'

interface ItemState {
  // Data
  items: Item[]
  currentItem: Item | null

  // UI State
  loading: {
    items: boolean
    currentItem: boolean
    creating: boolean
    updating: boolean
    deleting: boolean
    bulkOperations: boolean
  }
  errors: {
    items: string | null
    currentItem: string | null
    creating: string | null
    updating: string | null
    deleting: string | null
    bulkOperations: string | null
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
  filters: ItemFilter
  sorts: ItemSort[]

  // Drag and drop state
  draggedItem: Item | null
  dragOverColumn: string | null

  // Actions
  setCurrentItem: (item: Item | null) => void
  setFilters: (filters: Partial<ItemFilter>) => void
  setSorts: (sorts: ItemSort[]) => void
  setDraggedItem: (item: Item | null) => void
  setDragOverColumn: (columnId: string | null) => void

  // API Actions
  fetchItems: (boardId: string, params?: any) => Promise<void>
  fetchItemById: (itemId: string, includeDetails?: boolean) => Promise<void>
  createItem: (boardId: string, data: CreateItemData) => Promise<Item | null>
  updateItem: (itemId: string, data: UpdateItemData) => Promise<Item | null>
  deleteItem: (itemId: string) => Promise<void>
  moveItem: (itemId: string, newPosition: number, newParentId?: string) => Promise<void>

  // Bulk operations
  bulkUpdateItems: (itemIds: string[], updates: Partial<UpdateItemData>) => Promise<void>
  bulkDeleteItems: (itemIds: string[]) => Promise<void>

  // Real-time updates
  handleRealTimeUpdate: (event: string, data: any) => void
}

export const useItemStore = create<ItemState>()(
  devtools(
    subscribeWithSelector(
      (set, get) => ({
        // Initial state
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

        // Actions
        setCurrentItem: (item) => {
          set(produce((state) => {
            state.currentItem = item
          }))
        },

        setFilters: (newFilters) => {
          set(produce((state) => {
            state.filters = { ...state.filters, ...newFilters }
          }))
        },

        setSorts: (sorts) => {
          set(produce((state) => {
            state.sorts = sorts
          }))
        },

        setDraggedItem: (item) => {
          set(produce((state) => {
            state.draggedItem = item
          }))
        },

        setDragOverColumn: (columnId) => {
          set(produce((state) => {
            state.dragOverColumn = columnId
          }))
        },

        // API Actions
        fetchItems: async (boardId, params = {}) => {
          set(produce((state) => {
            state.loading.items = true
            state.errors.items = null
          }))

          try {
            const response = await api.items.list(boardId, {
              page: get().pagination.page,
              limit: get().pagination.limit,
              ...get().filters,
              sorts: get().sorts,
              ...params,
            }) as PaginatedResponse<Item>

            set(produce((state) => {
              state.items = response.data
              state.pagination = response.meta.pagination
              state.loading.items = false
            }))
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to fetch items'
            set(produce((state) => {
              state.errors.items = errorMessage
              state.loading.items = false
            }))
            toast.error(errorMessage)
          }
        },

        fetchItemById: async (itemId, includeDetails = true) => {
          set(produce((state) => {
            state.loading.currentItem = true
            state.errors.currentItem = null
          }))

          try {
            const response = await api.items.get(itemId, {
              includeComments: includeDetails,
              includeChildren: includeDetails,
              includeDependencies: includeDetails,
            }) as ApiResponse<Item>

            set(produce((state) => {
              state.currentItem = response.data
              state.loading.currentItem = false
            }))
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to fetch item'
            set(produce((state) => {
              state.errors.currentItem = errorMessage
              state.loading.currentItem = false
            }))
            toast.error(errorMessage)
          }
        },

        createItem: async (boardId, data) => {
          set(produce((state) => {
            state.loading.creating = true
            state.errors.creating = null
          }))

          try {
            const response = await api.items.create(boardId, data) as ApiResponse<Item>

            set(produce((state) => {
              state.items.push(response.data)
              // Re-sort items to maintain order
              state.items.sort((a, b) => Number(a.position) - Number(b.position))
              state.loading.creating = false
            }))

            toast.success('Item created successfully!')
            return response.data
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to create item'
            set(produce((state) => {
              state.errors.creating = errorMessage
              state.loading.creating = false
            }))
            toast.error(errorMessage)
            return null
          }
        },

        updateItem: async (itemId, data) => {
          set(produce((state) => {
            state.loading.updating = true
            state.errors.updating = null
          }))

          try {
            const response = await api.items.update(itemId, data) as ApiResponse<Item>

            set(produce((state) => {
              // Update in items list
              const index = state.items.findIndex(item => item.id === itemId)
              if (index !== -1) {
                state.items[index] = response.data
              }

              // Update current item if it's the same
              if (state.currentItem?.id === itemId) {
                state.currentItem = response.data
              }

              state.loading.updating = false
            }))

            toast.success('Item updated successfully!')
            return response.data
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to update item'
            set(produce((state) => {
              state.errors.updating = errorMessage
              state.loading.updating = false
            }))
            toast.error(errorMessage)
            return null
          }
        },

        deleteItem: async (itemId) => {
          set(produce((state) => {
            state.loading.deleting = true
            state.errors.deleting = null
          }))

          try {
            await api.items.delete(itemId)

            set(produce((state) => {
              state.items = state.items.filter(item => item.id !== itemId)
              if (state.currentItem?.id === itemId) {
                state.currentItem = null
              }
              state.loading.deleting = false
            }))

            toast.success('Item deleted successfully!')
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to delete item'
            set(produce((state) => {
              state.errors.deleting = errorMessage
              state.loading.deleting = false
            }))
            toast.error(errorMessage)
          }
        },

        moveItem: async (itemId, newPosition, newParentId) => {
          const oldItem = get().items.find(item => item.id === itemId)
          if (!oldItem) return

          // Optimistically update the UI
          set(produce((state) => {
            const item = state.items.find(item => item.id === itemId)
            if (item) {
              item.position = newPosition
              if (newParentId !== undefined) {
                item.parentId = newParentId
              }
            }
            // Re-sort items
            state.items.sort((a, b) => Number(a.position) - Number(b.position))
          }))

          try {
            const updateData: UpdateItemData = { position: newPosition }
            if (newParentId !== undefined) {
              updateData.parentId = newParentId
            }

            await api.items.update(itemId, updateData)
          } catch (error) {
            // Revert on error
            set(produce((state) => {
              const item = state.items.find(item => item.id === itemId)
              if (item && oldItem) {
                item.position = oldItem.position
                item.parentId = oldItem.parentId
              }
              state.items.sort((a, b) => Number(a.position) - Number(b.position))
            }))

            const errorMessage = error instanceof Error ? error.message : 'Failed to move item'
            toast.error(errorMessage)
          }
        },

        // Bulk operations
        bulkUpdateItems: async (itemIds, updates) => {
          set(produce((state) => {
            state.loading.bulkOperations = true
            state.errors.bulkOperations = null
          }))

          try {
            const response = await api.items.bulkUpdate({
              itemIds,
              updates,
            }) as { updatedCount: number; errors: Array<{ itemId: string; error: string }> }

            // Optimistically update items that succeeded
            set(produce((state) => {
              const successfulIds = itemIds.filter(id =>
                !response.errors.some(err => err.itemId === id)
              )

              successfulIds.forEach(itemId => {
                const item = state.items.find(item => item.id === itemId)
                if (item) {
                  Object.assign(item, updates)
                }
              })

              state.loading.bulkOperations = false
            }))

            if (response.errors.length > 0) {
              toast.error(`${response.errors.length} items failed to update`)
            } else {
              toast.success(`${response.updatedCount} items updated successfully!`)
            }
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to bulk update items'
            set(produce((state) => {
              state.errors.bulkOperations = errorMessage
              state.loading.bulkOperations = false
            }))
            toast.error(errorMessage)
          }
        },

        bulkDeleteItems: async (itemIds) => {
          set(produce((state) => {
            state.loading.bulkOperations = true
            state.errors.bulkOperations = null
          }))

          try {
            const response = await api.items.bulkDelete({
              itemIds,
            }) as { deletedCount: number; errors: Array<{ itemId: string; error: string }> }

            // Remove successfully deleted items
            set(produce((state) => {
              const successfulIds = itemIds.filter(id =>
                !response.errors.some(err => err.itemId === id)
              )

              state.items = state.items.filter(item => !successfulIds.includes(item.id))
              state.loading.bulkOperations = false
            }))

            if (response.errors.length > 0) {
              toast.error(`${response.errors.length} items failed to delete`)
            } else {
              toast.success(`${response.deletedCount} items deleted successfully!`)
            }
          } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Failed to bulk delete items'
            set(produce((state) => {
              state.errors.bulkOperations = errorMessage
              state.loading.bulkOperations = false
            }))
            toast.error(errorMessage)
          }
        },

        // Real-time updates
        handleRealTimeUpdate: (event, data) => {
          switch (event) {
            case 'item_created':
              set(produce((state) => {
                const existingIndex = state.items.findIndex(item => item.id === data.item.id)
                if (existingIndex === -1) {
                  state.items.push(data.item)
                  state.items.sort((a, b) => Number(a.position) - Number(b.position))
                }
              }))
              break

            case 'item_updated':
              set(produce((state) => {
                const index = state.items.findIndex(item => item.id === data.itemId)
                if (index !== -1) {
                  // Apply changes
                  if (data.changes) {
                    Object.keys(data.changes).forEach(key => {
                      if (data.changes[key].new !== undefined) {
                        (state.items[index] as any)[key] = data.changes[key].new
                      }
                    })
                  }
                }

                // Update current item if it's the same
                if (state.currentItem?.id === data.itemId && data.changes) {
                  Object.keys(data.changes).forEach(key => {
                    if (data.changes[key].new !== undefined) {
                      (state.currentItem as any)[key] = data.changes[key].new
                    }
                  })
                }
              }))
              break

            case 'item_deleted':
              set(produce((state) => {
                state.items = state.items.filter(item => item.id !== data.itemId)
                if (state.currentItem?.id === data.itemId) {
                  state.currentItem = null
                }
              }))
              break
          }
        },
      })
    ),
    { name: 'item-store' }
  )
)