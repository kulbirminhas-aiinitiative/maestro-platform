import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BoardView } from '@/components/boards/BoardView'
import { useBoardStore } from '@/stores/board.store'
import { useItemStore } from '@/stores/item.store'
import { Board, BoardColumn, Item } from '@/types'

// Mock the stores
jest.mock('@/stores/board.store')
jest.mock('@/stores/item.store')
jest.mock('@/services/websocket.service')

const mockUseBoardStore = useBoardStore as jest.MockedFunction<typeof useBoardStore>
const mockUseItemStore = useItemStore as jest.MockedFunction<typeof useItemStore>

const createQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: { retry: false },
    mutations: { retry: false },
  },
})

const renderWithProviders = (component: React.ReactElement) => {
  const queryClient = createQueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/boards/board-1']}>
        {component}
      </MemoryRouter>
    </QueryClientProvider>
  )
}

const mockBoard: Board = {
  id: 'board-1',
  name: 'Test Board',
  description: 'A test board',
  workspaceId: 'workspace-1',
  isPrivate: false,
  settings: {},
  viewSettings: {},
  position: 0,
  createdAt: '2023-01-01T00:00:00Z',
  updatedAt: '2023-01-01T00:00:00Z',
  columns: [],
  items: [],
  members: [],
}

const mockColumns: BoardColumn[] = [
  {
    id: 'col-1',
    boardId: 'board-1',
    name: 'To Do',
    columnType: 'status',
    settings: { statusValue: 'todo' },
    validationRules: {},
    position: 0,
    isRequired: false,
    isVisible: true,
    createdAt: '2023-01-01T00:00:00Z',
  },
  {
    id: 'col-2',
    boardId: 'board-1',
    name: 'In Progress',
    columnType: 'status',
    settings: { statusValue: 'in_progress' },
    validationRules: {},
    position: 1,
    isRequired: false,
    isVisible: true,
    createdAt: '2023-01-01T00:00:00Z',
  },
  {
    id: 'col-3',
    boardId: 'board-1',
    name: 'Done',
    columnType: 'status',
    settings: { statusValue: 'done' },
    validationRules: {},
    position: 2,
    isRequired: false,
    isVisible: true,
    createdAt: '2023-01-01T00:00:00Z',
  },
]

const mockItems: Item[] = [
  {
    id: 'item-1',
    boardId: 'board-1',
    name: 'Task 1',
    description: 'First task',
    data: { status: 'todo' },
    position: 1,
    createdAt: '2023-01-01T00:00:00Z',
    updatedAt: '2023-01-01T00:00:00Z',
  },
  {
    id: 'item-2',
    boardId: 'board-1',
    name: 'Task 2',
    description: 'Second task',
    data: { status: 'in_progress' },
    position: 2,
    createdAt: '2023-01-01T00:00:00Z',
    updatedAt: '2023-01-01T00:00:00Z',
  },
]

const mockBoardStore = {
  currentBoard: mockBoard,
  columns: mockColumns,
  loading: {
    boards: false,
    currentBoard: false,
    creating: false,
    updating: false,
    deleting: false,
  },
  errors: {
    boards: null,
    currentBoard: null,
    creating: null,
    updating: null,
    deleting: null,
  },
  selectedItems: [],
  fetchBoardById: jest.fn(),
  setCurrentBoard: jest.fn(),
  toggleItemSelection: jest.fn(),
  clearSelection: jest.fn(),
}

const mockItemStore = {
  items: mockItems,
  loading: {
    items: false,
    currentItem: false,
    creating: false,
    updating: false,
    deleting: false,
    bulkOperations: false,
  },
  fetchItems: jest.fn(),
  updateItem: jest.fn(),
  moveItem: jest.fn(),
}

describe('BoardView', () => {
  beforeEach(() => {
    mockUseBoardStore.mockReturnValue(mockBoardStore as any)
    mockUseItemStore.mockReturnValue(mockItemStore as any)
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  it('renders board view with board name and description', () => {
    renderWithProviders(<BoardView />)

    expect(screen.getByText('Test Board')).toBeInTheDocument()
    expect(screen.getByText('A test board')).toBeInTheDocument()
  })

  it('renders all columns', () => {
    renderWithProviders(<BoardView />)

    expect(screen.getByText('To Do')).toBeInTheDocument()
    expect(screen.getByText('In Progress')).toBeInTheDocument()
    expect(screen.getByText('Done')).toBeInTheDocument()
  })

  it('renders items in correct columns', () => {
    renderWithProviders(<BoardView />)

    expect(screen.getByText('Task 1')).toBeInTheDocument()
    expect(screen.getByText('Task 2')).toBeInTheDocument()
  })

  it('shows loading state', () => {
    mockUseBoardStore.mockReturnValue({
      ...mockBoardStore,
      loading: { ...mockBoardStore.loading, currentBoard: true },
    } as any)

    renderWithProviders(<BoardView />)

    expect(screen.getByText('Loading board...')).toBeInTheDocument()
  })

  it('shows error state', () => {
    mockUseBoardStore.mockReturnValue({
      ...mockBoardStore,
      errors: { ...mockBoardStore.errors, currentBoard: 'Failed to load board' },
    } as any)

    renderWithProviders(<BoardView />)

    expect(screen.getByText('Error loading board')).toBeInTheDocument()
    expect(screen.getByText('Failed to load board')).toBeInTheDocument()
  })

  it('opens item form when clicking add item button', async () => {
    renderWithProviders(<BoardView />)

    const addButtons = screen.getAllByText('Add Item')
    fireEvent.click(addButtons[0])

    await waitFor(() => {
      expect(screen.getByText('Create New Item')).toBeInTheDocument()
    })
  })

  it('handles item selection', () => {
    renderWithProviders(<BoardView />)

    const task1 = screen.getByText('Task 1')
    fireEvent.click(task1)

    expect(mockBoardStore.toggleItemSelection).toHaveBeenCalledWith('item-1')
  })

  it('shows selected items count', () => {
    mockUseBoardStore.mockReturnValue({
      ...mockBoardStore,
      selectedItems: ['item-1', 'item-2'],
    } as any)

    renderWithProviders(<BoardView />)

    expect(screen.getByText('2 selected')).toBeInTheDocument()
    expect(screen.getByText('Bulk Edit')).toBeInTheDocument()
  })

  it('fetches board data on mount', () => {
    renderWithProviders(<BoardView />)

    expect(mockBoardStore.fetchBoardById).toHaveBeenCalledWith('board-1', true)
    expect(mockItemStore.fetchItems).toHaveBeenCalledWith('board-1')
  })

  it('handles drag and drop', () => {
    renderWithProviders(<BoardView />)

    const task1Element = screen.getByText('Task 1').closest('[draggable="true"]')

    if (task1Element) {
      // Simulate drag start
      const dragStartEvent = new Event('dragstart', { bubbles: true })
      Object.defineProperty(dragStartEvent, 'dataTransfer', {
        value: {
          setData: jest.fn(),
        },
      })
      fireEvent(task1Element, dragStartEvent)

      // Simulate drop
      const dropZone = screen.getByText('In Progress').closest('.flex-1')
      if (dropZone) {
        const dropEvent = new Event('drop', { bubbles: true })
        Object.defineProperty(dropEvent, 'dataTransfer', {
          value: {
            getData: jest.fn()
              .mockReturnValueOnce('item-1') // item id
              .mockReturnValueOnce('col-1'), // source column
          },
        })
        fireEvent(dropZone, dropEvent)

        expect(mockItemStore.updateItem).toHaveBeenCalled()
      }
    }
  })

  it('shows empty state for columns with no items', () => {
    // Mock items array with no items in 'done' status
    mockUseItemStore.mockReturnValue({
      ...mockItemStore,
      items: mockItems.filter(item => item.data?.status !== 'done'),
    } as any)

    renderWithProviders(<BoardView />)

    const doneColumn = screen.getByText('Done').closest('.flex-shrink-0')
    expect(doneColumn).toHaveTextContent('No items in this column')
  })

  it('shows add column button', () => {
    renderWithProviders(<BoardView />)

    expect(screen.getByText('Add Column')).toBeInTheDocument()
  })
})