import React, { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useBoardStore } from '@/stores/board.store'
import { useItemStore } from '@/stores/item.store'
import { BoardColumn, Item } from '@/types'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { ItemCard } from '@/components/boards/ItemCard'
import { ItemForm } from '@/components/items/ItemForm'
import { LoadingScreen } from '@/components/ui/LoadingScreen'
import {
  Plus,
  Filter,
  Search,
  MoreVertical,
  ChevronLeft,
  ChevronRight,
  Grid,
  List,
} from 'lucide-react'
import clsx from 'clsx'

interface MobileBoardViewProps {
  className?: string
}

export const MobileBoardView: React.FC<MobileBoardViewProps> = ({ className }) => {
  const { boardId } = useParams<{ boardId: string }>()
  const [selectedColumnIndex, setSelectedColumnIndex] = useState(0)
  const [viewMode, setViewMode] = useState<'cards' | 'list'>('cards')
  const [showItemForm, setShowItemForm] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [showFilters, setShowFilters] = useState(false)

  const {
    currentBoard,
    columns,
    loading,
    errors,
    fetchBoardById,
  } = useBoardStore()

  const {
    items,
    loading: itemLoading,
    fetchItems,
  } = useItemStore()

  // Fetch data
  useEffect(() => {
    if (boardId) {
      fetchBoardById(boardId, true)
      fetchItems(boardId)
    }
  }, [boardId, fetchBoardById, fetchItems])

  // Group items by column
  const itemsByColumn = React.useMemo(() => {
    const grouped: Record<string, Item[]> = {}

    columns.forEach(column => {
      grouped[column.id] = []
    })

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

    // Sort items within each column
    Object.keys(grouped).forEach(columnId => {
      grouped[columnId].sort((a, b) => Number(a.position) - Number(b.position))
    })

    return grouped
  }, [items, columns])

  // Filter items based on search
  const filteredItems = React.useMemo(() => {
    if (!searchQuery) return itemsByColumn

    const filtered: Record<string, Item[]> = {}
    Object.entries(itemsByColumn).forEach(([columnId, columnItems]) => {
      filtered[columnId] = columnItems.filter(item =>
        item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (item.description && item.description.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    })

    return filtered
  }, [itemsByColumn, searchQuery])

  const selectedColumn = columns[selectedColumnIndex]
  const selectedColumnItems = selectedColumn ? filteredItems[selectedColumn.id] || [] : []

  if (loading.currentBoard || itemLoading.items) {
    return <LoadingScreen message="Loading board..." />
  }

  if (errors.currentBoard) {
    return (
      <div className="flex items-center justify-center h-64 p-4">
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
      <div className="flex items-center justify-center h-64 p-4">
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
    <div className={clsx('flex flex-col h-full bg-gray-50', className)}>
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between mb-3">
          <h1 className="text-lg font-semibold text-gray-900 truncate">
            {currentBoard.name}
          </h1>
          <Button variant="ghost" size="sm">
            <MoreVertical className="h-4 w-4" />
          </Button>
        </div>

        {/* Search */}
        <div className="relative mb-3">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search items..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        {/* Controls */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
            >
              <Filter className="h-4 w-4 mr-1" />
              Filters
            </Button>
          </div>

          <div className="flex items-center space-x-1 bg-gray-100 rounded-lg p-1">
            <Button
              variant={viewMode === 'cards' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('cards')}
              className="h-8 w-8 p-0"
            >
              <Grid className="h-4 w-4" />
            </Button>
            <Button
              variant={viewMode === 'list' ? 'default' : 'ghost'}
              size="sm"
              onClick={() => setViewMode('list')}
              className="h-8 w-8 p-0"
            >
              <List className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* Column Navigation */}
      <div className="bg-white border-b border-gray-200 px-4 py-2">
        <div className="flex items-center justify-between">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelectedColumnIndex(Math.max(0, selectedColumnIndex - 1))}
            disabled={selectedColumnIndex === 0}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          <div className="flex-1 text-center">
            <div className="flex items-center justify-center space-x-2">
              <h2 className="font-medium text-gray-900">
                {selectedColumn?.name || 'No columns'}
              </h2>
              <Badge variant="secondary" className="text-xs">
                {selectedColumnItems.length}
              </Badge>
            </div>
            <div className="text-xs text-gray-500 mt-1">
              {selectedColumnIndex + 1} of {columns.length}
            </div>
          </div>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setSelectedColumnIndex(Math.min(columns.length - 1, selectedColumnIndex + 1))}
            disabled={selectedColumnIndex === columns.length - 1}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>

        {/* Column Tabs */}
        <div className="flex space-x-1 mt-2 overflow-x-auto scrollbar-hide">
          {columns.map((column, index) => (
            <button
              key={column.id}
              onClick={() => setSelectedColumnIndex(index)}
              className={clsx(
                'flex-shrink-0 px-3 py-1 rounded-full text-sm font-medium transition-colors',
                index === selectedColumnIndex
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              )}
            >
              {column.name}
              <span className="ml-1 text-xs">
                ({(filteredItems[column.id] || []).length})
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {selectedColumn && (
          <div className="p-4">
            {/* Add Item Button */}
            <Button
              onClick={() => setShowItemForm(true)}
              className="w-full mb-4 justify-center"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Item to {selectedColumn.name}
            </Button>

            {/* Items */}
            {selectedColumnItems.length > 0 ? (
              <div className={clsx(
                viewMode === 'cards'
                  ? 'space-y-3'
                  : 'divide-y divide-gray-200'
              )}>
                {selectedColumnItems.map((item) => (
                  <div key={item.id}>
                    {viewMode === 'cards' ? (
                      <ItemCard
                        item={item}
                        isSelected={false}
                        onSelect={() => {}}
                        onEdit={() => {}}
                        className="touch-manipulation"
                      />
                    ) : (
                      <MobileItemListItem item={item} />
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                  <Plus className="h-8 w-8 text-gray-400" />
                </div>
                <h3 className="text-lg font-medium text-gray-900 mb-2">
                  No items yet
                </h3>
                <p className="text-gray-500 mb-4 max-w-sm">
                  {searchQuery
                    ? `No items match "${searchQuery}" in this column`
                    : `Get started by adding your first item to ${selectedColumn.name}`
                  }
                </p>
                {!searchQuery && (
                  <Button onClick={() => setShowItemForm(true)}>
                    <Plus className="h-4 w-4 mr-2" />
                    Add Item
                  </Button>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Item Form Modal */}
      {showItemForm && (
        <ItemForm
          isOpen={showItemForm}
          onClose={() => setShowItemForm(false)}
          boardId={boardId!}
          columnId={selectedColumn?.id}
        />
      )}
    </div>
  )
}

// Mobile list item component
const MobileItemListItem: React.FC<{ item: Item }> = ({ item }) => {
  return (
    <div className="py-3 px-2 hover:bg-gray-50 touch-manipulation">
      <div className="flex items-start space-x-3">
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-gray-900 truncate">
            {item.name}
          </h4>
          {item.description && (
            <p className="text-sm text-gray-500 line-clamp-2 mt-1">
              {item.description}
            </p>
          )}
          <div className="flex items-center space-x-2 mt-2">
            {item.data?.priority && (
              <Badge
                variant="outline"
                className={clsx(
                  'text-xs',
                  item.data.priority === 'high' && 'border-red-200 text-red-700',
                  item.data.priority === 'medium' && 'border-yellow-200 text-yellow-700',
                  item.data.priority === 'low' && 'border-green-200 text-green-700'
                )}
              >
                {item.data.priority}
              </Badge>
            )}
            {item.data?.dueDate && (
              <span className="text-xs text-gray-500">
                Due {new Date(item.data.dueDate).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
        <Button variant="ghost" size="sm">
          <MoreVertical className="h-4 w-4" />
        </Button>
      </div>
    </div>
  )
}

export default MobileBoardView