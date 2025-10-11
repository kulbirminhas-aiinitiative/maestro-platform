import React, { useEffect, useState, useCallback, memo } from 'react'
import { useParams } from 'react-router-dom'
import { useBoardStore } from '@/stores/board.store'
import { useItemStore } from '@/stores/item.store'
import { useIsMobile } from '@/hooks/useResponsive'
import { useDebounce, useMemoizedValue, useMemoizedCallback, useRenderPerformance } from '@/hooks/usePerformance'
import { BoardColumn, Item } from '@/types'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Avatar } from '@/components/ui/Avatar'
import { LoadingScreen } from '@/components/ui/LoadingScreen'
import { ItemForm } from '@/components/items/ItemForm'
import { ColumnHeader } from './ColumnHeader'
import { ItemCard } from './ItemCard'
import { PresenceIndicator } from '@/components/collaboration/PresenceIndicator'
import { MobileDrawer } from '@/components/layout/ResponsiveLayout'
import { Plus, Users, Calendar, MoreHorizontal, Filter, Layout } from 'lucide-react'
import clsx from 'clsx'

interface BoardViewProps {
  className?: string
}

// Memoized column component for better performance
const MemoizedColumn = memo<{
  column: BoardColumn
  items: Item[]
  selectedItems: string[]
  onCreateItem: (columnId: string) => void
  onEditItem: (item: Item) => void
  onSelectItem: (itemId: string, event: React.MouseEvent) => void
  onDragEnd: (itemId: string, sourceColumnId: string, destColumnId: string, newIndex: number) => void
}>(({ column, items, selectedItems, onCreateItem, onEditItem, onSelectItem, onDragEnd }) => {
  const sortedItems = useMemoizedValue(
    () => items.sort((a, b) => Number(a.position) - Number(b.position)),
    [items]
  )

  return (
    <div className="flex-shrink-0 w-80">
      <Card className="h-full flex flex-col">
        <ColumnHeader
          column={column}
          itemCount={items.length}
          onAddItem={() => onCreateItem(column.id)}
        />

        <div className="flex-1 p-4 space-y-3 min-h-[200px]">
          {sortedItems.map((item, index) => (
            <div
              key={item.id}
              draggable
              onDragStart={(e) => {
                e.dataTransfer.setData('text/plain', item.id)
                e.dataTransfer.setData('source-column', column.id)
              }}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault()
                const draggedItemId = e.dataTransfer.getData('text/plain')
                const sourceColumnId = e.dataTransfer.getData('source-column')
                if (draggedItemId !== item.id) {
                  onDragEnd(draggedItemId, sourceColumnId, column.id, index)
                }
              }}
              className="cursor-move"
            >
              <ItemCard
                item={item}
                isSelected={selectedItems.includes(item.id)}
                onSelect={(event) => onSelectItem(item.id, event)}
                onEdit={() => onEditItem(item)}
              />
            </div>
          ))}

          {/* Drop zone for empty column */}
          <div
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault()
              const draggedItemId = e.dataTransfer.getData('text/plain')
              const sourceColumnId = e.dataTransfer.getData('source-column')
              onDragEnd(draggedItemId, sourceColumnId, column.id, items.length)
            }}
            className="min-h-[50px]"
          >
            {items.length === 0 && (
              <div className="flex items-center justify-center h-32 border-2 border-dashed border-gray-300 rounded-lg">
                <div className="text-center">
                  <p className="text-sm text-gray-500 mb-2">No items in this column</p>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => onCreateItem(column.id)}
                    className="flex items-center space-x-1"
                  >
                    <Plus className="h-4 w-4" />
                    <span>Add Item</span>
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>
      </Card>
    </div>
  )
})

MemoizedColumn.displayName = 'MemoizedColumn'

// Memoized mobile column tabs for better performance
const MemoizedMobileColumnTabs = memo<{
  columns: BoardColumn[]
  selectedColumnId: string | null
  itemsByColumn: Record<string, Item[]>
  onSelectColumn: (columnId: string) => void
}>(({ columns, selectedColumnId, itemsByColumn, onSelectColumn }) => {
  return (
    <div className="bg-white border-b border-gray-200 px-4 py-2">
      <div className="flex space-x-1 overflow-x-auto">
        {columns.map((column) => (
          <Button
            key={column.id}
            variant={selectedColumnId === column.id ? 'default' : 'ghost'}
            size="sm"
            onClick={() => onSelectColumn(column.id)}
            className="flex-shrink-0"
          >
            {column.name}
            <Badge variant="secondary" className="ml-2 text-xs">
              {itemsByColumn[column.id]?.length || 0}
            </Badge>
          </Button>
        ))}
      </div>
    </div>
  )
})

MemoizedMobileColumnTabs.displayName = 'MemoizedMobileColumnTabs'

export const BoardView: React.FC<BoardViewProps> = memo(({ className }) => {
  const { boardId } = useParams<{ boardId: string }>()
  const isMobile = useIsMobile()
  const [showItemForm, setShowItemForm] = useState(false)
  const [selectedColumnId, setSelectedColumnId] = useState<string | null>(null)
  const [editingItem, setEditingItem] = useState<Item | null>(null)
  const [selectedItemForMobile, setSelectedItemForMobile] = useState<Item | null>(null)

  // Performance tracking in development
  useRenderPerformance('BoardView', process.env.NODE_ENV === 'development')

  const {
    currentBoard,
    columns,
    loading,
    errors,
    selectedItems,
    fetchBoardById,
    setCurrentBoard,
    toggleItemSelection,
    clearSelection,
  } = useBoardStore()

  const {
    items,
    loading: itemLoading,
    fetchItems,
    updateItem,
    moveItem,
  } = useItemStore()

  // Debounce search functionality for better performance
  const debouncedBoardId = useDebounce(boardId, 300)

  // Fetch board data with debounced board ID
  useEffect(() => {
    if (debouncedBoardId) {
      fetchBoardById(debouncedBoardId, true)
      fetchItems(debouncedBoardId)
    }

    return () => {
      setCurrentBoard(null)
    }
  }, [debouncedBoardId, fetchBoardById, fetchItems, setCurrentBoard])

  // Initialize selected column for mobile
  useEffect(() => {
    if (isMobile && columns.length > 0 && !selectedColumnId) {
      setSelectedColumnId(columns[0].id)
    }
  }, [isMobile, columns, selectedColumnId])

  // Memoized expensive calculation: Group items by column
  const itemsByColumn = useMemoizedValue(() => {
    const grouped: Record<string, Item[]> = {}

    // Initialize with empty arrays for all columns
    columns.forEach(column => {
      grouped[column.id] = []
    })

    // Group items by their status or column
    items.forEach(item => {
      const status = item.data?.status || 'todo'
      const column = columns.find(col =>
        col.columnType === 'status' &&
        col.settings?.statusValue === status
      ) || columns[0]

      if (column && grouped[column.id]) {
        grouped[column.id].push(item)
      }
    })

    return grouped
  }, [items, columns])

  // Memoized callbacks for better performance
  const handleDragEnd = useMemoizedCallback((
    itemId: string,
    sourceColumnId: string,
    destColumnId: string,
    newIndex: number
  ) => {
    const item = items.find(item => item.id === itemId)
    if (!item) return

    const destItems = itemsByColumn[destColumnId] || []
    let newPosition: number

    if (destItems.length === 0) {
      newPosition = 1
    } else if (newIndex === 0) {
      newPosition = Number(destItems[0].position) - 1
    } else if (newIndex >= destItems.length) {
      newPosition = Number(destItems[destItems.length - 1].position) + 1
    } else {
      const prevItem = destItems[newIndex - 1]
      const nextItem = destItems[newIndex]
      newPosition = (Number(prevItem.position) + Number(nextItem.position)) / 2
    }

    let statusUpdate = {}
    if (sourceColumnId !== destColumnId) {
      const destColumn = columns.find(col => col.id === destColumnId)
      if (destColumn?.columnType === 'status') {
        statusUpdate = {
          data: {
            ...item.data,
            status: destColumn.settings?.statusValue || 'todo'
          }
        }
      }
    }

    updateItem(itemId, {
      position: newPosition,
      ...statusUpdate,
    })
  }, [items, itemsByColumn, columns, updateItem])

  const handleCreateItem = useMemoizedCallback((columnId: string) => {
    setSelectedColumnId(columnId)
    setShowItemForm(true)
  }, [])

  const handleEditItem = useMemoizedCallback((item: Item) => {
    setEditingItem(item)
    setShowItemForm(true)
  }, [])

  const handleSelectItem = useMemoizedCallback((itemId: string, event: React.MouseEvent) => {
    if (event.ctrlKey || event.metaKey) {
      toggleItemSelection(itemId)
    } else {
      clearSelection()
      toggleItemSelection(itemId)
    }
  }, [toggleItemSelection, clearSelection])

  const handleCloseItemForm = useMemoizedCallback(() => {
    setShowItemForm(false)
    setEditingItem(null)
    setSelectedColumnId(null)
  }, [])

  // Loading state
  if (loading.currentBoard || itemLoading.items) {
    return <LoadingScreen message="Loading board..." />
  }

  // Error state
  if (errors.currentBoard) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Error loading board
          </h3>
          <p className="text-gray-500 mb-4">{errors.currentBoard}</p>
          <Button onClick={() => boardId && fetchBoardById(boardId, true)}>
            Try Again
          </Button>
        </div>
      </div>
    )
  }

  // Board not found
  if (!currentBoard) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Board not found
          </h3>
          <p className="text-gray-500">
            The board you're looking for doesn't exist or you don't have access to it.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className={clsx('flex flex-col h-full', className)}>
      {/* Board Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <h1 className="text-2xl font-bold text-gray-900">
              {currentBoard.name}
            </h1>
            {currentBoard.description && (
              <p className="text-gray-500">{currentBoard.description}</p>
            )}
          </div>

          <div className="flex items-center space-x-4">
            {/* Real-time Presence */}
            <PresenceIndicator boardId={boardId!} />

            {/* Selected items actions */}
            {selectedItems.length > 0 && (
              <div className="flex items-center space-x-2">
                <Badge variant="secondary">
                  {selectedItems.length} selected
                </Badge>
                <Button size="sm" variant="outline">
                  Bulk Edit
                </Button>
                <Button size="sm" variant="outline">
                  Delete
                </Button>
              </div>
            )}

            <Button size="sm" className="flex items-center space-x-1">
              <MoreHorizontal className="h-4 w-4" />
              <span>More</span>
            </Button>
          </div>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="flex-1 overflow-hidden">
        {isMobile ? (
          // Mobile: Single column view with tabs
          <div className="flex flex-col h-full">
            {/* Column selector tabs */}
            <MemoizedMobileColumnTabs
              columns={columns}
              selectedColumnId={selectedColumnId}
              itemsByColumn={itemsByColumn}
              onSelectColumn={setSelectedColumnId}
            />

            {/* Selected column items */}
            <div className="flex-1 overflow-y-auto p-4">
              {selectedColumnId && columns.find(col => col.id === selectedColumnId) && (
                <div className="space-y-3">
                  <Button
                    onClick={() => handleCreateItem(selectedColumnId)}
                    className="w-full flex items-center justify-center space-x-2"
                  >
                    <Plus className="h-4 w-4" />
                    <span>Add Item</span>
                  </Button>

                  {itemsByColumn[selectedColumnId]?.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => setSelectedItemForMobile(item)}
                    >
                      <ItemCard
                        item={item}
                        isSelected={selectedItems.includes(item.id)}
                        onSelect={(event) => handleSelectItem(item.id, event)}
                        onEdit={() => setSelectedItemForMobile(item)}
                      />
                    </div>
                  ))}

                  {itemsByColumn[selectedColumnId]?.length === 0 && (
                    <div className="flex items-center justify-center h-32 border-2 border-dashed border-gray-300 rounded-lg">
                      <div className="text-center">
                        <p className="text-sm text-gray-500 mb-2">
                          No items in this column
                        </p>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleCreateItem(selectedColumnId)}
                          className="flex items-center space-x-1"
                        >
                          <Plus className="h-4 w-4" />
                          <span>Add Item</span>
                        </Button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ) : (
          // Desktop: Traditional kanban view
          <div className="flex h-full">
            <div className="flex space-x-6 p-6 overflow-x-auto">
              {columns.map((column) => (
                <MemoizedColumn
                  key={column.id}
                  column={column}
                  items={itemsByColumn[column.id] || []}
                  selectedItems={selectedItems}
                  onCreateItem={handleCreateItem}
                  onEditItem={handleEditItem}
                  onSelectItem={handleSelectItem}
                  onDragEnd={handleDragEnd}
                />
              ))}

              {/* Add Column Button */}
              <div className="flex-shrink-0 w-80">
                <Button
                  variant="outline"
                  className="w-full h-16 border-dashed border-gray-300 text-gray-500 hover:border-gray-400 hover:text-gray-600"
                >
                  <Plus className="h-5 w-5 mr-2" />
                  Add Column
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Item Form Modal */}
      {showItemForm && (
        <ItemForm
          isOpen={showItemForm}
          onClose={handleCloseItemForm}
          boardId={boardId!}
          columnId={selectedColumnId}
          item={editingItem}
        />
      )}

      {/* Mobile Item Details Drawer */}
      {isMobile && selectedItemForMobile && (
        <MobileDrawer
          isOpen={!!selectedItemForMobile}
          onClose={() => setSelectedItemForMobile(null)}
          title={selectedItemForMobile.name}
        >
          <div className="space-y-4">
            {selectedItemForMobile.description && (
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Description</h4>
                <p className="text-gray-700">{selectedItemForMobile.description}</p>
              </div>
            )}

            <div>
              <h4 className="font-medium text-gray-900 mb-2">Status</h4>
              <Badge variant="secondary">
                {selectedItemForMobile.data?.status || 'No status'}
              </Badge>
            </div>

            {selectedItemForMobile.assignees && selectedItemForMobile.assignees.length > 0 && (
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Assignees</h4>
                <div className="flex flex-wrap gap-2">
                  {selectedItemForMobile.assignees.map((assignee) => (
                    <div key={assignee.id} className="flex items-center space-x-2">
                      <Avatar
                        src={assignee.avatarUrl}
                        alt={assignee.fullName}
                        size="sm"
                      />
                      <span className="text-sm text-gray-700">{assignee.fullName}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex space-x-2">
              <Button
                onClick={() => {
                  setEditingItem(selectedItemForMobile)
                  setShowItemForm(true)
                  setSelectedItemForMobile(null)
                }}
                className="flex-1"
              >
                Edit
              </Button>
              <Button
                variant="outline"
                onClick={() => setSelectedItemForMobile(null)}
                className="flex-1"
              >
                Close
              </Button>
            </div>
          </div>
        </MobileDrawer>
      )}
    </div>
  )
})

BoardView.displayName = 'BoardView'