import { useCallback, useState } from 'react'
import type { Item, BoardColumn } from '@/types'

interface DragData {
  type: 'item' | 'column'
  id: string
  data: Item | BoardColumn
  sourceColumnId?: string
}

interface DropResult {
  targetColumnId: string
  targetPosition?: number
  targetType: 'column' | 'item'
}

interface UseDragAndDropOptions {
  onDrop?: (dragData: DragData, dropResult: DropResult) => void
  onDragStart?: (dragData: DragData) => void
  onDragEnd?: () => void
  disabled?: boolean
}

export function useDragAndDrop({
  onDrop,
  onDragStart,
  onDragEnd,
  disabled = false
}: UseDragAndDropOptions = {}) {
  const [draggedItem, setDraggedItem] = useState<DragData | null>(null)
  const [draggedOverId, setDraggedOverId] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)

  // Create draggable props for an element
  const createDraggableProps = useCallback((
    type: 'item' | 'column',
    id: string,
    data: Item | BoardColumn,
    sourceColumnId?: string
  ) => {
    if (disabled) return {}

    const dragData: DragData = { type, id, data, sourceColumnId }

    return {
      draggable: true,
      onDragStart: (e: React.DragEvent) => {
        e.dataTransfer.effectAllowed = 'move'
        e.dataTransfer.setData('application/json', JSON.stringify(dragData))

        // Create a custom drag image
        const dragImage = e.currentTarget.cloneNode(true) as HTMLElement
        dragImage.style.transform = 'rotate(5deg)'
        dragImage.style.opacity = '0.8'
        dragImage.style.width = `${e.currentTarget.getBoundingClientRect().width}px`
        e.dataTransfer.setDragImage(dragImage, 0, 0)

        setDraggedItem(dragData)
        setIsDragging(true)
        onDragStart?.(dragData)
      },
      onDragEnd: (e: React.DragEvent) => {
        setDraggedItem(null)
        setDraggedOverId(null)
        setIsDragging(false)
        onDragEnd?.()
      }
    }
  }, [disabled, onDragStart, onDragEnd])

  // Create drop zone props for an element
  const createDropZoneProps = useCallback((
    targetId: string,
    targetType: 'column' | 'item',
    position?: number
  ) => {
    if (disabled) return {}

    return {
      onDragOver: (e: React.DragEvent) => {
        e.preventDefault()
        e.dataTransfer.dropEffect = 'move'
        setDraggedOverId(targetId)
      },
      onDragEnter: (e: React.DragEvent) => {
        e.preventDefault()
        setDraggedOverId(targetId)
      },
      onDragLeave: (e: React.DragEvent) => {
        // Only clear if we're actually leaving the element
        if (!e.currentTarget.contains(e.relatedTarget as Node)) {
          setDraggedOverId(null)
        }
      },
      onDrop: (e: React.DragEvent) => {
        e.preventDefault()

        try {
          const dragDataStr = e.dataTransfer.getData('application/json')
          if (!dragDataStr) return

          const dragData: DragData = JSON.parse(dragDataStr)

          const dropResult: DropResult = {
            targetColumnId: targetType === 'column' ? targetId : targetId,
            targetPosition: position,
            targetType
          }

          // Don't allow dropping on self
          if (dragData.id === targetId) return

          onDrop?.(dragData, dropResult)
        } catch (error) {
          console.error('Error handling drop:', error)
        } finally {
          setDraggedOverId(null)
          setDraggedItem(null)
          setIsDragging(false)
        }
      }
    }
  }, [disabled, onDrop])

  // Helper to check if an element is being dragged over
  const isDraggedOver = useCallback((id: string) => {
    return draggedOverId === id
  }, [draggedOverId])

  // Helper to check if an element is being dragged
  const isDraggedElement = useCallback((id: string) => {
    return draggedItem?.id === id
  }, [draggedItem])

  // Helper to get drag overlay style
  const getDragOverlayStyle = useCallback((id: string) => {
    if (!isDraggedOver(id)) return {}

    return {
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      borderColor: 'rgba(59, 130, 246, 0.5)',
      borderWidth: '2px',
      borderStyle: 'dashed'
    }
  }, [isDraggedOver])

  // Helper to get dragged element style
  const getDraggedElementStyle = useCallback((id: string) => {
    if (!isDraggedElement(id)) return {}

    return {
      opacity: 0.5,
      transform: 'rotate(5deg)'
    }
  }, [isDraggedElement])

  return {
    // State
    draggedItem,
    draggedOverId,
    isDragging,

    // Prop creators
    createDraggableProps,
    createDropZoneProps,

    // Helpers
    isDraggedOver,
    isDraggedElement,
    getDragOverlayStyle,
    getDraggedElementStyle,

    // Manual state control
    setDraggedItem,
    setDraggedOverId,
    setIsDragging
  }
}

// Specialized hook for board items
export function useItemDragAndDrop({
  onMoveItem,
  disabled = false
}: {
  onMoveItem?: (itemId: string, targetColumnId: string, targetPosition?: number) => void
  disabled?: boolean
} = {}) {
  return useDragAndDrop({
    onDrop: (dragData, dropResult) => {
      if (dragData.type === 'item') {
        onMoveItem?.(dragData.id, dropResult.targetColumnId, dropResult.targetPosition)
      }
    },
    disabled
  })
}

// Specialized hook for board columns
export function useColumnDragAndDrop({
  onMoveColumn,
  disabled = false
}: {
  onMoveColumn?: (columnId: string, targetPosition: number) => void
  disabled?: boolean
} = {}) {
  return useDragAndDrop({
    onDrop: (dragData, dropResult) => {
      if (dragData.type === 'column' && dropResult.targetPosition !== undefined) {
        onMoveColumn?.(dragData.id, dropResult.targetPosition)
      }
    },
    disabled
  })
}

export default useDragAndDrop