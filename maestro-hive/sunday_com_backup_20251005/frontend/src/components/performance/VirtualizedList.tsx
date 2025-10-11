import React, { useState, useEffect, useRef, useMemo } from 'react'
import { FixedSizeList as List, VariableSizeList } from 'react-window'
import { LoadingScreen } from '@/components/ui/LoadingScreen'
import clsx from 'clsx'

interface VirtualizedListProps<T> {
  items: T[]
  itemHeight?: number | ((index: number) => number)
  height: number
  width?: number | string
  renderItem: (props: { item: T; index: number; style: React.CSSProperties }) => React.ReactNode
  className?: string
  isLoading?: boolean
  loadingMessage?: string
  emptyMessage?: string
  onScroll?: (scrollOffset: number) => void
  overscan?: number
}

export const VirtualizedList = <T,>({
  items,
  itemHeight = 60,
  height,
  width = '100%',
  renderItem,
  className,
  isLoading = false,
  loadingMessage = 'Loading...',
  emptyMessage = 'No items to display',
  onScroll,
  overscan = 5,
}: VirtualizedListProps<T>) => {
  const listRef = useRef<any>(null)

  const ListComponent = typeof itemHeight === 'function' ? VariableSizeList : List

  const Row = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const item = items[index]
    return (
      <div style={style}>
        {renderItem({ item, index, style })}
      </div>
    )
  }

  const handleScroll = ({ scrollOffset }: { scrollOffset: number }) => {
    if (onScroll) {
      onScroll(scrollOffset)
    }
  }

  if (isLoading) {
    return (
      <div className={clsx('flex items-center justify-center', className)} style={{ height }}>
        <LoadingScreen message={loadingMessage} />
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className={clsx('flex items-center justify-center text-gray-500', className)} style={{ height }}>
        <p>{emptyMessage}</p>
      </div>
    )
  }

  return (
    <div className={className}>
      <ListComponent
        ref={listRef}
        height={height}
        width={width}
        itemCount={items.length}
        itemSize={itemHeight}
        onScroll={handleScroll}
        overscanCount={overscan}
      >
        {Row}
      </ListComponent>
    </div>
  )
}

// Infinite scrolling wrapper
interface InfiniteVirtualizedListProps<T> extends Omit<VirtualizedListProps<T>, 'items'> {
  items: T[]
  hasMore: boolean
  loadMore: () => Promise<void>
  threshold?: number
}

export const InfiniteVirtualizedList = <T,>({
  items,
  hasMore,
  loadMore,
  threshold = 200,
  ...props
}: InfiniteVirtualizedListProps<T>) => {
  const [isLoadingMore, setIsLoadingMore] = useState(false)

  const handleScroll = async (scrollOffset: number) => {
    if (props.onScroll) {
      props.onScroll(scrollOffset)
    }

    // Check if we need to load more items
    const scrollHeight = items.length * (typeof props.itemHeight === 'number' ? props.itemHeight : 60)
    const containerHeight = props.height
    const scrollBottom = scrollOffset + containerHeight

    if (
      hasMore &&
      !isLoadingMore &&
      scrollHeight - scrollBottom < threshold
    ) {
      setIsLoadingMore(true)
      try {
        await loadMore()
      } finally {
        setIsLoadingMore(false)
      }
    }
  }

  return (
    <VirtualizedList
      {...props}
      items={items}
      onScroll={handleScroll}
    />
  )
}

// Grid virtualization for boards
interface VirtualizedGridProps<T> {
  items: T[]
  columnCount: number
  rowHeight: number
  columnWidth: number
  height: number
  width: number
  renderCell: (props: {
    item: T | undefined
    rowIndex: number
    columnIndex: number
    style: React.CSSProperties
  }) => React.ReactNode
  className?: string
}

export const VirtualizedGrid = <T,>({
  items,
  columnCount,
  rowHeight,
  columnWidth,
  height,
  width,
  renderCell,
  className,
}: VirtualizedGridProps<T>) => {
  const rowCount = Math.ceil(items.length / columnCount)

  const Cell = ({
    rowIndex,
    columnIndex,
    style,
  }: {
    rowIndex: number
    columnIndex: number
    style: React.CSSProperties
  }) => {
    const itemIndex = rowIndex * columnCount + columnIndex
    const item = items[itemIndex]

    return (
      <div style={style}>
        {renderCell({ item, rowIndex, columnIndex, style })}
      </div>
    )
  }

  return (
    <div className={className}>
      <List
        height={height}
        width={width}
        itemCount={rowCount}
        itemSize={rowHeight}
      >
        {({ index, style }) => (
          <div style={style} className="flex">
            {Array.from({ length: columnCount }, (_, columnIndex) => (
              <Cell
                key={columnIndex}
                rowIndex={index}
                columnIndex={columnIndex}
                style={{
                  width: columnWidth,
                  height: rowHeight,
                }}
              />
            ))}
          </div>
        )}
      </List>
    </div>
  )
}

export default VirtualizedList