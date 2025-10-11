import React, { useEffect, useState, useCallback } from 'react'
import { useParams } from 'react-router-dom'
import { useBoardStore } from '@/stores/board.store'
import { useItemStore } from '@/stores/item.store'
import { useIsMobile } from '@/hooks/useResponsive'
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
import { useBoardPresence } from '@/hooks/useWebSocket'
import { MobileDrawer } from '@/components/layout/ResponsiveLayout'
import { TimeTracker } from '@/components/time/TimeTracker'
import { AnalyticsDashboard } from '@/components/analytics/AnalyticsDashboard'
import { Plus, Users, Calendar, MoreHorizontal, Filter, Layout, BarChart3, Clock, X } from 'lucide-react'
import clsx from 'clsx'

interface BoardViewProps {
  className?: string
}

export const BoardView: React.FC<BoardViewProps> = ({ className }) => {
  const { boardId } = useParams<{ boardId: string }>()
  const isMobile = useIsMobile()
  const [showItemForm, setShowItemForm] = useState(false)
  const [selectedColumnId, setSelectedColumnId] = useState<string | null>(null)
  const [editingItem, setEditingItem] = useState<Item | null>(null)
  const [showMobileFilters, setShowMobileFilters] = useState(false)
  const [selectedItemForMobile, setSelectedItemForMobile] = useState<Item | null>(null)
  const [showAnalytics, setShowAnalytics] = useState(false)
  const [showTimeTracker, setShowTimeTracker] = useState(false)

  // Real-time collaboration
  const { isConnected: wsConnected, presenceUsers, cursors } = useBoardPresence(boardId || '')

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

  // Fetch board data on mount
  useEffect(() => {
    if (boardId) {
      fetchBoardById(boardId, true)
      fetchItems(boardId)
    }

    return () => {
      setCurrentBoard(null)
    }
  }, [boardId, fetchBoardById, fetchItems, setCurrentBoard])

  // Initialize selected column for mobile
  useEffect(() => {
    if (isMobile && columns.length > 0 && !selectedColumnId) {
      setSelectedColumnId(columns[0].id)
    }
  }, [isMobile, columns, selectedColumnId])

  // Group items by status/column
  const itemsByColumn = React.useMemo(() => {
    const grouped: Record<string, Item[]> = {}

    // Initialize with empty arrays for all columns
    columns.forEach(column => {
      grouped[column.id] = []
    })

    // Group items by their status or column
    items.forEach(item => {
      // Determine which column this item belongs to based on status
      const status = item.data?.status || 'todo'
      const column = columns.find(col =>
        col.columnType === 'status' &&
        col.settings?.statusValue === status
      ) || columns[0] // Default to first column

      if (column && grouped[column.id]) {
        grouped[column.id].push(item)
      }
    })

    // Sort items within each column by position
    Object.keys(grouped).forEach(columnId => {
      grouped[columnId].sort((a, b) => Number(a.position) - Number(b.position))
    })

    return grouped
  }, [items, columns])

  // Handle drag end (simplified drag and drop without external library)
  const handleDragEnd = useCallback((itemId: string, sourceColumnId: string, destColumnId: string, newIndex: number) => {
    // Find the item being moved
    const item = items.find(item => item.id === itemId)
    if (!item) return

    // Calculate new position
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

    // Update item status if moving between columns
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

    // Update the item
    updateItem(itemId, {
      position: newPosition,
      ...statusUpdate,
    })
  }, [items, itemsByColumn, columns, updateItem])

  // Handle item creation
  const handleCreateItem = useCallback((columnId: string) => {
    setSelectedColumnId(columnId)
    setShowItemForm(true)
  }, [])

  // Handle item editing
  const handleEditItem = useCallback((item: Item) => {
    setEditingItem(item)
    setShowItemForm(true)
  }, [])

  // Handle bulk selection
  const handleSelectItem = useCallback((itemId: string, event: React.MouseEvent) => {
    if (event.ctrlKey || event.metaKey) {
      toggleItemSelection(itemId)
    } else {
      clearSelection()
      toggleItemSelection(itemId)
    }
  }, [toggleItemSelection, clearSelection])

  if (loading.currentBoard || itemLoading.items) {
    return <LoadingScreen message="Loading board..." />
  }

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
            {/* Real-time Connection Status */}
            <div className="flex items-center space-x-2">
              <div className={clsx(
                'w-2 h-2 rounded-full',
                wsConnected ? 'bg-green-500' : 'bg-red-500'
              )} />
              <span className="text-sm text-gray-500">
                {wsConnected ? 'Live' : 'Offline'}
              </span>
            </div>

            {/* Real-time Presence */}
            <PresenceIndicator boardId={boardId!} presenceUsers={presenceUsers} />

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

            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowTimeTracker(!showTimeTracker)}
              className="flex items-center space-x-1"
            >
              <Clock className="h-4 w-4" />
              <span>Time</span>
            </Button>

            <Button
              size="sm"
              variant="outline"
              onClick={() => setShowAnalytics(!showAnalytics)}
              className="flex items-center space-x-1"
            >
              <BarChart3 className="h-4 w-4" />
              <span>Analytics</span>
            </Button>

            <Button
              size="sm"
              className="flex items-center space-x-1"
            >
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
            <div className="bg-white border-b border-gray-200 px-4 py-2">
              <div className="flex space-x-1 overflow-x-auto">
                {columns.map((column) => (
                  <Button
                    key={column.id}
                    variant={selectedColumnId === column.id ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => setSelectedColumnId(column.id)}
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

            {/* Selected column items */}
            <div className="flex-1 overflow-y-auto p-4">
              {selectedColumnId && columns.find(col => col.id === selectedColumnId) && (
                <div className="space-y-3">
                  {/* Add item button */}
                  <Button
                    onClick={() => handleCreateItem(selectedColumnId)}
                    className="w-full flex items-center justify-center space-x-2"
                  >
                    <Plus className="h-4 w-4" />
                    <span>Add Item</span>
                  </Button>

                  {/* Items */}
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

                  {/* Empty state */}
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
                <div
                  key={column.id}
                  className="flex-shrink-0 w-80"
                >
                  <Card className="h-full flex flex-col">
                    {/* Column Header */}
                    <ColumnHeader
                      column={column}
                      itemCount={itemsByColumn[column.id]?.length || 0}
                      onAddItem={() => handleCreateItem(column.id)}
                    />

                    {/* Column Items */}
                    <div className="flex-1 p-4 space-y-3 min-h-[200px]">
                      {itemsByColumn[column.id]?.map((item, index) => (
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
                              handleDragEnd(draggedItemId, sourceColumnId, column.id, index)
                            }
                          }}
                          className="cursor-move"
                        >
                          <ItemCard
                            item={item}
                            isSelected={selectedItems.includes(item.id)}
                            onSelect={(event) => handleSelectItem(item.id, event)}
                            onEdit={() => handleEditItem(item)}
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
                          handleDragEnd(draggedItemId, sourceColumnId, column.id, itemsByColumn[column.id]?.length || 0)
                        }}
                        className="min-h-[50px]"
                      >
                        {/* Empty state */}
                        {itemsByColumn[column.id]?.length === 0 && (
                          <div className="flex items-center justify-center h-32 border-2 border-dashed border-gray-300 rounded-lg">
                            <div className="text-center">
                              <p className="text-sm text-gray-500 mb-2">
                                No items in this column
                              </p>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => handleCreateItem(column.id)}
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
          onClose={() => {
            setShowItemForm(false)
            setEditingItem(null)
            setSelectedColumnId(null)
          }}
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
            {/* Item details */}
            {selectedItemForMobile.description && (
              <div>
                <h4 className="font-medium text-gray-900 mb-2">Description</h4>
                <p className="text-gray-700">{selectedItemForMobile.description}</p>
              </div>
            )}

            {/* Status */}
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Status</h4>
              <Badge variant="secondary">
                {selectedItemForMobile.data?.status || 'No status'}
              </Badge>
            </div>

            {/* Assignees */}
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

            {/* Actions */}
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

      {/* Analytics Panel */}
      {showAnalytics && (
        <div className="border-t border-gray-200 bg-gray-50">
          <div className="max-w-7xl mx-auto p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-medium text-gray-900">Board Analytics</h3>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowAnalytics(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <AnalyticsDashboard
              boardId={boardId}
              className="bg-white rounded-lg"
            />
          </div>
        </div>
      )}

      {/* Time Tracking Panel */}
      {showTimeTracker && (
        <div className="border-t border-gray-200 bg-gray-50">
          <div className="max-w-7xl mx-auto p-6">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-medium text-gray-900">Time Tracking</h3>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowTimeTracker(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
            <TimeTracker
              boardId={boardId}
              className="bg-white rounded-lg"
            />
          </div>
        </div>
      )}

      {/* Collaborative Cursors */}
      {cursors.length > 0 && (
        <div className="fixed inset-0 pointer-events-none z-50">
          {cursors.map((cursor) => (
            <div
              key={cursor.userId}
              className="absolute transition-all duration-100 ease-out"
              style={{
                left: cursor.x,
                top: cursor.y,
                transform: 'translate(-2px, -2px)',
              }}
            >
              {/* Cursor pointer */}
              <svg
                width="16"
                height="16"
                viewBox="0 0 16 16"
                fill="none"
                className="drop-shadow-sm text-blue-500"
              >
                <path
                  d="M0 0L0 11L4 7L7 7L0 0Z"
                  fill="currentColor"
                />
              </svg>

              {/* Username label */}
              <div className="absolute top-4 left-2 px-2 py-1 rounded bg-blue-500 text-white text-xs font-medium whitespace-nowrap">
                {cursor.username}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}