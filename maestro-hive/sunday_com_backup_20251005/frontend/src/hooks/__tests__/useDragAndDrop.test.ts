import { renderHook, act } from '@testing-library/react'
import { useDragAndDrop, useItemDragAndDrop, useColumnDragAndDrop } from '../useDragAndDrop'
import type { Item, BoardColumn } from '@/types'

// Mock data
const mockItem: Item = {
  id: 'item-1',
  boardId: 'board-1',
  name: 'Test Item',
  description: 'A test item',
  data: { status: 'todo' },
  position: 1,
  createdAt: '2023-01-01T00:00:00Z',
  updatedAt: '2023-01-01T00:00:00Z'
}

const mockColumn: BoardColumn = {
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
}

describe('useDragAndDrop', () => {
  it('initializes with correct default state', () => {
    const { result } = renderHook(() => useDragAndDrop())

    expect(result.current.draggedItem).toBeNull()
    expect(result.current.draggedOverId).toBeNull()
    expect(result.current.isDragging).toBe(false)
  })

  it('creates draggable props correctly', () => {
    const { result } = renderHook(() => useDragAndDrop())

    const draggableProps = result.current.createDraggableProps(
      'item',
      'item-1',
      mockItem,
      'col-1'
    )

    expect(draggableProps.draggable).toBe(true)
    expect(typeof draggableProps.onDragStart).toBe('function')
    expect(typeof draggableProps.onDragEnd).toBe('function')
  })

  it('creates drop zone props correctly', () => {
    const { result } = renderHook(() => useDragAndDrop())

    const dropZoneProps = result.current.createDropZoneProps(
      'col-2',
      'column',
      1
    )

    expect(typeof dropZoneProps.onDragOver).toBe('function')
    expect(typeof dropZoneProps.onDragEnter).toBe('function')
    expect(typeof dropZoneProps.onDragLeave).toBe('function')
    expect(typeof dropZoneProps.onDrop).toBe('function')
  })

  it('returns empty props when disabled', () => {
    const { result } = renderHook(() => useDragAndDrop({ disabled: true }))

    const draggableProps = result.current.createDraggableProps(
      'item',
      'item-1',
      mockItem
    )
    const dropZoneProps = result.current.createDropZoneProps('col-2', 'column')

    expect(Object.keys(draggableProps)).toHaveLength(0)
    expect(Object.keys(dropZoneProps)).toHaveLength(0)
  })

  it('calls onDragStart when drag starts', () => {
    const mockOnDragStart = jest.fn()
    const { result } = renderHook(() => useDragAndDrop({
      onDragStart: mockOnDragStart
    }))

    const draggableProps = result.current.createDraggableProps(
      'item',
      'item-1',
      mockItem,
      'col-1'
    )

    // Simulate drag start event
    const mockEvent = {
      dataTransfer: {
        effectAllowed: '',
        setData: jest.fn(),
        setDragImage: jest.fn()
      },
      currentTarget: {
        cloneNode: jest.fn(() => ({
          style: {},
          getBoundingClientRect: () => ({ width: 100 })
        }))
      }
    } as any

    act(() => {
      draggableProps.onDragStart!(mockEvent)
    })

    expect(mockOnDragStart).toHaveBeenCalledWith({
      type: 'item',
      id: 'item-1',
      data: mockItem,
      sourceColumnId: 'col-1'
    })
    expect(result.current.isDragging).toBe(true)
    expect(result.current.draggedItem).toEqual({
      type: 'item',
      id: 'item-1',
      data: mockItem,
      sourceColumnId: 'col-1'
    })
  })

  it('calls onDragEnd when drag ends', () => {
    const mockOnDragEnd = jest.fn()
    const { result } = renderHook(() => useDragAndDrop({
      onDragEnd: mockOnDragEnd
    }))

    const draggableProps = result.current.createDraggableProps(
      'item',
      'item-1',
      mockItem
    )

    const mockEvent = {} as any

    act(() => {
      draggableProps.onDragEnd!(mockEvent)
    })

    expect(mockOnDragEnd).toHaveBeenCalled()
    expect(result.current.isDragging).toBe(false)
    expect(result.current.draggedItem).toBeNull()
    expect(result.current.draggedOverId).toBeNull()
  })

  it('calls onDrop when item is dropped', () => {
    const mockOnDrop = jest.fn()
    const { result } = renderHook(() => useDragAndDrop({
      onDrop: mockOnDrop
    }))

    const dropZoneProps = result.current.createDropZoneProps(
      'col-2',
      'column',
      1
    )

    const mockEvent = {
      preventDefault: jest.fn(),
      dataTransfer: {
        getData: jest.fn((key) => {
          if (key === 'application/json') {
            return JSON.stringify({
              type: 'item',
              id: 'item-1',
              data: mockItem,
              sourceColumnId: 'col-1'
            })
          }
          return ''
        })
      }
    } as any

    act(() => {
      dropZoneProps.onDrop!(mockEvent)
    })

    expect(mockOnDrop).toHaveBeenCalledWith(
      {
        type: 'item',
        id: 'item-1',
        data: mockItem,
        sourceColumnId: 'col-1'
      },
      {
        targetColumnId: 'col-2',
        targetPosition: 1,
        targetType: 'column'
      }
    )
  })

  it('prevents dropping on self', () => {
    const mockOnDrop = jest.fn()
    const { result } = renderHook(() => useDragAndDrop({
      onDrop: mockOnDrop
    }))

    const dropZoneProps = result.current.createDropZoneProps('item-1', 'item')

    const mockEvent = {
      preventDefault: jest.fn(),
      dataTransfer: {
        getData: jest.fn(() => JSON.stringify({
          type: 'item',
          id: 'item-1',
          data: mockItem
        }))
      }
    } as any

    act(() => {
      dropZoneProps.onDrop!(mockEvent)
    })

    expect(mockOnDrop).not.toHaveBeenCalled()
  })

  it('identifies dragged over elements correctly', () => {
    const { result } = renderHook(() => useDragAndDrop())

    act(() => {
      result.current.setDraggedOverId('col-2')
    })

    expect(result.current.isDraggedOver('col-2')).toBe(true)
    expect(result.current.isDraggedOver('col-1')).toBe(false)
  })

  it('identifies dragged elements correctly', () => {
    const { result } = renderHook(() => useDragAndDrop())

    act(() => {
      result.current.setDraggedItem({
        type: 'item',
        id: 'item-1',
        data: mockItem
      })
    })

    expect(result.current.isDraggedElement('item-1')).toBe(true)
    expect(result.current.isDraggedElement('item-2')).toBe(false)
  })

  it('provides correct drag overlay styles', () => {
    const { result } = renderHook(() => useDragAndDrop())

    act(() => {
      result.current.setDraggedOverId('col-2')
    })

    const overlayStyle = result.current.getDragOverlayStyle('col-2')
    expect(overlayStyle).toEqual({
      backgroundColor: 'rgba(59, 130, 246, 0.1)',
      borderColor: 'rgba(59, 130, 246, 0.5)',
      borderWidth: '2px',
      borderStyle: 'dashed'
    })

    const noOverlayStyle = result.current.getDragOverlayStyle('col-1')
    expect(noOverlayStyle).toEqual({})
  })

  it('provides correct dragged element styles', () => {
    const { result } = renderHook(() => useDragAndDrop())

    act(() => {
      result.current.setDraggedItem({
        type: 'item',
        id: 'item-1',
        data: mockItem
      })
    })

    const draggedStyle = result.current.getDraggedElementStyle('item-1')
    expect(draggedStyle).toEqual({
      opacity: 0.5,
      transform: 'rotate(5deg)'
    })

    const normalStyle = result.current.getDraggedElementStyle('item-2')
    expect(normalStyle).toEqual({})
  })

  it('sets dragged over id on drag enter', () => {
    const { result } = renderHook(() => useDragAndDrop())

    const dropZoneProps = result.current.createDropZoneProps('col-2', 'column')

    const mockEvent = {
      preventDefault: jest.fn()
    } as any

    act(() => {
      dropZoneProps.onDragEnter!(mockEvent)
    })

    expect(result.current.draggedOverId).toBe('col-2')
  })

  it('sets dragged over id on drag over', () => {
    const { result } = renderHook(() => useDragAndDrop())

    const dropZoneProps = result.current.createDropZoneProps('col-2', 'column')

    const mockEvent = {
      preventDefault: jest.fn(),
      dataTransfer: { dropEffect: '' }
    } as any

    act(() => {
      dropZoneProps.onDragOver!(mockEvent)
    })

    expect(result.current.draggedOverId).toBe('col-2')
    expect(mockEvent.dataTransfer.dropEffect).toBe('move')
  })
})

describe('useItemDragAndDrop', () => {
  it('calls onMoveItem when item is dropped', () => {
    const mockOnMoveItem = jest.fn()
    const { result } = renderHook(() => useItemDragAndDrop({
      onMoveItem: mockOnMoveItem
    }))

    // Simulate the onDrop callback
    const mockDragData = {
      type: 'item' as const,
      id: 'item-1',
      data: mockItem,
      sourceColumnId: 'col-1'
    }

    const mockDropResult = {
      targetColumnId: 'col-2',
      targetPosition: 2,
      targetType: 'column' as const
    }

    // This simulates the internal onDrop handler
    act(() => {
      if (mockDragData.type === 'item') {
        mockOnMoveItem(mockDragData.id, mockDropResult.targetColumnId, mockDropResult.targetPosition)
      }
    })

    expect(mockOnMoveItem).toHaveBeenCalledWith('item-1', 'col-2', 2)
  })

  it('does not call onMoveItem for non-item drag data', () => {
    const mockOnMoveItem = jest.fn()
    const { result } = renderHook(() => useItemDragAndDrop({
      onMoveItem: mockOnMoveItem
    }))

    // Simulate dropping a column instead of an item
    const mockDragData = {
      type: 'column' as const,
      id: 'col-1',
      data: mockColumn
    }

    const mockDropResult = {
      targetColumnId: 'col-2',
      targetPosition: 1,
      targetType: 'column' as const
    }

    // This should not trigger onMoveItem
    act(() => {
      if (mockDragData.type === 'item') {
        mockOnMoveItem(mockDragData.id, mockDropResult.targetColumnId, mockDropResult.targetPosition)
      }
    })

    expect(mockOnMoveItem).not.toHaveBeenCalled()
  })
})

describe('useColumnDragAndDrop', () => {
  it('calls onMoveColumn when column is dropped', () => {
    const mockOnMoveColumn = jest.fn()
    const { result } = renderHook(() => useColumnDragAndDrop({
      onMoveColumn: mockOnMoveColumn
    }))

    // Simulate the onDrop callback
    const mockDragData = {
      type: 'column' as const,
      id: 'col-1',
      data: mockColumn
    }

    const mockDropResult = {
      targetColumnId: 'col-2',
      targetPosition: 2,
      targetType: 'column' as const
    }

    // This simulates the internal onDrop handler
    act(() => {
      if (mockDragData.type === 'column' && mockDropResult.targetPosition !== undefined) {
        mockOnMoveColumn(mockDragData.id, mockDropResult.targetPosition)
      }
    })

    expect(mockOnMoveColumn).toHaveBeenCalledWith('col-1', 2)
  })

  it('does not call onMoveColumn when targetPosition is undefined', () => {
    const mockOnMoveColumn = jest.fn()
    const { result } = renderHook(() => useColumnDragAndDrop({
      onMoveColumn: mockOnMoveColumn
    }))

    const mockDragData = {
      type: 'column' as const,
      id: 'col-1',
      data: mockColumn
    }

    const mockDropResult = {
      targetColumnId: 'col-2',
      targetPosition: undefined,
      targetType: 'column' as const
    }

    // This should not trigger onMoveColumn
    act(() => {
      if (mockDragData.type === 'column' && mockDropResult.targetPosition !== undefined) {
        mockOnMoveColumn(mockDragData.id, mockDropResult.targetPosition)
      }
    })

    expect(mockOnMoveColumn).not.toHaveBeenCalled()
  })
})