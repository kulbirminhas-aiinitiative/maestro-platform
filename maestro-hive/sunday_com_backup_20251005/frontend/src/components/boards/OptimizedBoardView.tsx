import React, { useCallback, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useBoardStore } from '@/stores/board.store'
import { useItemStore } from '@/stores/item.store'
import { useDebounce, useVirtualList, useRenderPerformance, useBatchUpdate } from '@/hooks/usePerformance'
import { useWebSocket } from '@/hooks/useWebSocket'
import { BoardColumn, Item } from '@/types'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Input } from '@/components/ui/Input'
import { LoadingScreen } from '@/components/ui/LoadingScreen'
import { ItemCard } from './ItemCard'
import { ItemForm } from '@/components/items/ItemForm'
import { VirtualizedList } from '@/components/performance/VirtualizedList'
import {
  Plus,
  Search,
  Filter,
  MoreHorizontal,
  Grid,
  List,
  ArrowUpDown,
} from 'lucide-react'
import clsx from 'clsx'

interface OptimizedBoardViewProps {
  className?: string
}

interface FilterState {
  search: string
  status: string[]
  priority: string[]
  assignees: string[]
  labels: string[]
}

interface SortState {
  field: 'name' | 'createdAt' | 'updatedAt' | 'priority' | 'dueDate'
  direction: 'asc' | 'desc'
}

export const OptimizedBoardView: React.FC<OptimizedBoardViewProps> = ({ className }) => {
  const { boardId } = useParams<{ boardId: string }>()
  const [viewMode, setViewMode] = useState<'kanban' | 'list'>('kanban')
  const [showItemForm, setShowItemForm] = useState(false)
  const [selectedColumnId, setSelectedColumnId] = useState<string | null>(null)
  const [editingItem, setEditingItem] = useState<Item | null>(null)

  // Performance monitoring in development
  useRenderPerformance('OptimizedBoardView', process.env.NODE_ENV === 'development')

  // State management
  const [filters, setFilters] = useBatchUpdate<FilterState>({
    search: '',
    status: [],
    priority: [],
    assignees: [],
    labels: [],
  })

  const [sortConfig, setSortConfig] = useState<SortState>({
    field: 'createdAt',
    direction: 'desc',
  })

  // Debounced search for better performance
  const debouncedSearch = useDebounce(filters.search, 300)

  // Store hooks
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
    updateItem,
    createItem,
  } = useItemStore()

  // WebSocket for real-time updates
  useWebSocket(boardId)

  // Memoized computed values for performance
  const filteredAndSortedItems = useMemo(() => {
    let filtered = items

    // Apply search filter
    if (debouncedSearch) {
      const searchLower = debouncedSearch.toLowerCase()
      filtered = filtered.filter(item =>
        item.name.toLowerCase().includes(searchLower) ||
        (item.description && item.description.toLowerCase().includes(searchLower))
      )
    }

    // Apply status filter
    if (filters.status.length > 0) {
      filtered = filtered.filter(item =>
        filters.status.includes(item.data?.status || 'todo')
      )
    }

    // Apply priority filter
    if (filters.priority.length > 0) {
      filtered = filtered.filter(item =>
        filters.priority.includes(item.data?.priority || 'medium')
      )
    }

    // Apply assignee filter
    if (filters.assignees.length > 0) {
      filtered = filtered.filter(item =>
        item.assignees?.some(assignee =>
          filters.assignees.includes(assignee.id)
        )
      )
    }

    // Apply label filter
    if (filters.labels.length > 0) {
      filtered = filtered.filter(item =>
        item.data?.labels?.some(label =>
          filters.labels.includes(label)
        )
      )
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aVal: any
      let bVal: any

      switch (sortConfig.field) {
        case 'name':
          aVal = a.name
          bVal = b.name
          break
        case 'createdAt':
          aVal = new Date(a.createdAt)
          bVal = new Date(b.createdAt)
          break
        case 'updatedAt':
          aVal = new Date(a.updatedAt)
          bVal = new Date(b.updatedAt)
          break
        case 'priority':
          const priorityOrder = { low: 1, medium: 2, high: 3 }
          aVal = priorityOrder[a.data?.priority as keyof typeof priorityOrder] || 2
          bVal = priorityOrder[b.data?.priority as keyof typeof priorityOrder] || 2
          break
        case 'dueDate':
          aVal = a.data?.dueDate ? new Date(a.data.dueDate) : new Date('9999-12-31')
          bVal = b.data?.dueDate ? new Date(b.data.dueDate) : new Date('9999-12-31')
          break
        default:
          return 0
      }

      if (aVal < bVal) return sortConfig.direction === 'asc' ? -1 : 1
      if (aVal > bVal) return sortConfig.direction === 'asc' ? 1 : -1
      return 0
    })

    return filtered
  }, [items, debouncedSearch, filters, sortConfig])

  // Group items by column for kanban view
  const itemsByColumn = useMemo(() => {
    const grouped: Record<string, Item[]> = {}

    columns.forEach(column => {
      grouped[column.id] = []
    })

    filteredAndSortedItems.forEach(item => {
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
  }, [filteredAndSortedItems, columns])

  // Optimized event handlers
  const handleSearch = useCallback((value: string) => {
    setFilters({ search: value })
  }, [setFilters])

  const handleSort = useCallback((field: SortState['field']) => {
    setSortConfig(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'asc' ? 'desc' : 'asc',
    }))
  }, [])

  const handleCreateItem = useCallback((columnId: string) => {
    setSelectedColumnId(columnId)
    setShowItemForm(true)
  }, [])

  const handleEditItem = useCallback((item: Item) => {
    setEditingItem(item)
    setShowItemForm(true)
  }, [])

  const handleDragEnd = useCallback(async (
    itemId: string,
    sourceColumnId: string,
    destColumnId: string,
    newIndex: number
  ) => {
    const item = items.find(i => i.id === itemId)
    if (!item) return

    const destColumn = columns.find(col => col.id === destColumnId)
    if (!destColumn) return

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

    const updateData: any = {
      position: newPosition,
    }

    if (sourceColumnId !== destColumnId && destColumn.columnType === 'status') {
      updateData.data = {
        ...item.data,
        status: destColumn.settings?.statusValue || 'todo',
      }
    }

    await updateItem(itemId, updateData)
  }, [items, columns, itemsByColumn, updateItem])

  // Loading states
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
        </div>
      </div>
    )
  }

  return (
    <div className={clsx('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold text-gray-900">
            {currentBoard.name}
          </h1>
          <div className="flex items-center space-x-2">
            <Button
              variant={viewMode === 'kanban' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('kanban')}
            >
              <Grid className="h-4 w-4 mr-1" />
              Kanban
            </Button>
            <Button
              variant={viewMode === 'list' ? 'default' : 'outline'}
              size="sm"
              onClick={() => setViewMode('list')}
            >
              <List className="h-4 w-4 mr-1" />
              List
            </Button>
          </div>
        </div>

        {/* Filters and Search */}
        <div className="flex items-center space-x-4">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <Input
              placeholder="Search items..."
              value={filters.search}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-10"
            />
          </div>

          <Button variant="outline" size="sm">
            <Filter className="h-4 w-4 mr-1" />
            Filters
            {(filters.status.length + filters.priority.length + filters.assignees.length + filters.labels.length) > 0 && (
              <Badge variant="secondary" className="ml-2">
                {filters.status.length + filters.priority.length + filters.assignees.length + filters.labels.length}
              </Badge>
            )}
          </Button>

          <Button variant="outline" size="sm" onClick={() => handleSort('name')}>
            <ArrowUpDown className="h-4 w-4 mr-1" />
            Sort
          </Button>
        </div>

        {/* Stats */}
        <div className="flex items-center space-x-6 mt-4 text-sm text-gray-600">
          <span>{filteredAndSortedItems.length} items</span>
          <span>{columns.length} columns</span>
          <span>{currentBoard.members?.length || 0} members</span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {viewMode === 'kanban' ? (
          <KanbanView
            columns={columns}
            itemsByColumn={itemsByColumn}
            onCreateItem={handleCreateItem}
            onEditItem={handleEditItem}
            onDragEnd={handleDragEnd}
          />
        ) : (
          <ListView
            items={filteredAndSortedItems}
            onEditItem={handleEditItem}
            sortConfig={sortConfig}
            onSort={handleSort}
          />
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
    </div>
  )
}

// Kanban View Component
interface KanbanViewProps {
  columns: BoardColumn[]
  itemsByColumn: Record<string, Item[]>
  onCreateItem: (columnId: string) => void
  onEditItem: (item: Item) => void
  onDragEnd: (itemId: string, sourceColumnId: string, destColumnId: string, newIndex: number) => void
}

const KanbanView: React.FC<KanbanViewProps> = React.memo(({
  columns,
  itemsByColumn,
  onCreateItem,
  onEditItem,
  onDragEnd,
}) => {
  return (
    <div className="flex h-full overflow-x-auto p-6 space-x-6">
      {columns.map((column) => (
        <KanbanColumn
          key={column.id}
          column={column}
          items={itemsByColumn[column.id] || []}
          onCreateItem={onCreateItem}
          onEditItem={onEditItem}
          onDragEnd={onDragEnd}
        />
      ))}
    </div>
  )
})

// Kanban Column Component
interface KanbanColumnProps {
  column: BoardColumn
  items: Item[]
  onCreateItem: (columnId: string) => void
  onEditItem: (item: Item) => void
  onDragEnd: (itemId: string, sourceColumnId: string, destColumnId: string, newIndex: number) => void
}

const KanbanColumn: React.FC<KanbanColumnProps> = React.memo(({
  column,
  items,
  onCreateItem,
  onEditItem,
  onDragEnd,
}) => {
  const renderItem = useCallback(({ item, index, style }: any) => (
    <div style={style} className="px-3 pb-3">
      <ItemCard
        item={item}
        isSelected={false}
        onSelect={() => {}}
        onEdit={() => onEditItem(item)}
        draggable
        onDragStart={(e) => {
          e.dataTransfer.setData('text/plain', item.id)
          e.dataTransfer.setData('source-column', column.id)
        }}
      />
    </div>
  ), [column.id, onEditItem])

  return (
    <Card className="w-80 flex-shrink-0 flex flex-col">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h3 className="font-medium text-gray-900">{column.name}</h3>
          <Badge variant="secondary">{items.length}</Badge>
        </div>
        <Button
          size="sm"
          variant="ghost"
          onClick={() => onCreateItem(column.id)}
          className="w-full mt-2 justify-start text-left"
        >
          <Plus className="h-4 w-4 mr-2" />
          Add item
        </Button>
      </div>

      <div className="flex-1 min-h-0">
        {items.length > 20 ? (
          <VirtualizedList
            items={items}
            itemHeight={120}
            height={600}
            renderItem={renderItem}
            className="h-full"
          />
        ) : (
          <div className="p-3 space-y-3">
            {items.map((item) => (
              <ItemCard
                key={item.id}
                item={item}
                isSelected={false}
                onSelect={() => {}}
                onEdit={() => onEditItem(item)}
                draggable
                onDragStart={(e) => {
                  e.dataTransfer.setData('text/plain', item.id)
                  e.dataTransfer.setData('source-column', column.id)
                }}
              />
            ))}
          </div>
        )}

        {items.length === 0 && (
          <div className="flex items-center justify-center h-32 text-gray-500">
            <p className="text-sm">No items in this column</p>
          </div>
        )}
      </div>
    </Card>
  )
})

// List View Component
interface ListViewProps {
  items: Item[]
  onEditItem: (item: Item) => void
  sortConfig: SortState
  onSort: (field: SortState['field']) => void
}

const ListView: React.FC<ListViewProps> = React.memo(({
  items,
  onEditItem,
  sortConfig,
  onSort,
}) => {
  const renderItem = useCallback(({ item, index, style }: any) => (
    <div style={style} className="border-b border-gray-200">
      <div className="p-4 hover:bg-gray-50 cursor-pointer" onClick={() => onEditItem(item)}>
        <div className="flex items-center justify-between">
          <div className="flex-1 min-w-0">
            <h4 className="text-sm font-medium text-gray-900 truncate">
              {item.name}
            </h4>
            {item.description && (
              <p className="text-sm text-gray-500 truncate mt-1">
                {item.description}
              </p>
            )}
            <div className="flex items-center space-x-4 mt-2">
              <Badge variant="outline" className="text-xs">
                {item.data?.status || 'todo'}
              </Badge>
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
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  ), [onEditItem])

  return (
    <div className="h-full">
      <VirtualizedList
        items={items}
        itemHeight={100}
        height={600}
        renderItem={renderItem}
        className="h-full"
        emptyMessage="No items match your filters"
      />
    </div>
  )
})

export default OptimizedBoardView