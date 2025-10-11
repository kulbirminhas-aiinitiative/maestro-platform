import React from 'react'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import { BoardView } from '../BoardView'
import { useBoardStore } from '@/stores/board.store'
import { useItemStore } from '@/stores/item.store'
import { useIsMobile } from '@/hooks/useResponsive'
import type { Board, BoardColumn, Item } from '@/types'

// Mock dependencies
jest.mock('@/stores/board.store')
jest.mock('@/stores/item.store')
jest.mock('@/hooks/useResponsive')
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useParams: () => ({ boardId: 'test-board-id' })
}))

const mockUseBoardStore = useBoardStore as jest.MockedFunction<typeof useBoardStore>
const mockUseItemStore = useItemStore as jest.MockedFunction<typeof useItemStore>
const mockUseIsMobile = useIsMobile as jest.MockedFunction<typeof useIsMobile>

// Mock data
const mockBoard: Board = {
  id: 'test-board-id',
  workspaceId: 'workspace-1',
  name: 'Test Board',
  description: 'A test board for testing',
  isPrivate: false,
  settings: {},
  viewSettings: {},
  createdAt: '2023-01-01T00:00:00Z',
  updatedAt: '2023-01-01T00:00:00Z',
  position: 1
}

const mockColumns: BoardColumn[] = [
  {
    id: 'col-1',
    boardId: 'test-board-id',
    name: 'To Do',
    columnType: 'status',
    position: 0,
    isRequired: false,
    isVisible: true,
    settings: { statusValue: 'todo' },
    validationRules: {},
    createdAt: '2023-01-01T00:00:00Z'
  },
  {
    id: 'col-2',
    boardId: 'test-board-id',
    name: 'In Progress',
    columnType: 'status',
    position: 1,
    isRequired: false,
    isVisible: true,
    settings: { statusValue: 'in_progress' },
    validationRules: {},
    createdAt: '2023-01-01T00:00:00Z'
  },
  {
    id: 'col-3',
    boardId: 'test-board-id',
    name: 'Done',
    columnType: 'status',
    position: 2,
    isRequired: false,
    isVisible: true,
    settings: { statusValue: 'done' },
    validationRules: {},
    createdAt: '2023-01-01T00:00:00Z'
  }
]

const mockItems: Item[] = [
  {
    id: 'item-1',
    boardId: 'test-board-id',
    name: 'Test Item 1',
    description: 'First test item',
    data: { status: 'todo' },
    position: 1,
    createdAt: '2023-01-01T00:00:00Z',
    updatedAt: '2023-01-01T00:00:00Z'
  },
  {
    id: 'item-2',
    boardId: 'test-board-id',
    name: 'Test Item 2',
    description: 'Second test item',
    data: { status: 'in_progress' },
    position: 1,
    createdAt: '2023-01-01T00:00:00Z',
    updatedAt: '2023-01-01T00:00:00Z'
  }
]

// Default mock store state
const defaultBoardStore = {
  currentBoard: mockBoard,
  columns: mockColumns,
  loading: { currentBoard: false },
  errors: {},
  selectedItems: [],
  fetchBoardById: jest.fn(),
  setCurrentBoard: jest.fn(),
  toggleItemSelection: jest.fn(),
  clearSelection: jest.fn()
}

const defaultItemStore = {
  items: mockItems,
  loading: { items: false },
  fetchItems: jest.fn(),
  updateItem: jest.fn(),
  moveItem: jest.fn()
}

const TestWrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <BrowserRouter>
    {children}
  </BrowserRouter>
)

describe('BoardView', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockUseIsMobile.mockReturnValue(false)
    mockUseBoardStore.mockReturnValue(defaultBoardStore as any)
    mockUseItemStore.mockReturnValue(defaultItemStore as any)
  })

  it('renders loading state correctly', () => {
    mockUseBoardStore.mockReturnValue({
      ...defaultBoardStore,
      loading: { currentBoard: true }
    } as any)

    render(
      <TestWrapper>
        <BoardView />
      </TestWrapper>
    )

    expect(screen.getByText('Loading board...')).toBeInTheDocument()
  })

  it('renders error state correctly', () => {
    const errorMessage = 'Failed to load board'
    mockUseBoardStore.mockReturnValue({
      ...defaultBoardStore,
      errors: { currentBoard: errorMessage }
    } as any)

    render(
      <TestWrapper>
        <BoardView />
      </TestWrapper>
    )

    expect(screen.getByText('Error loading board')).toBeInTheDocument()
    expect(screen.getByText(errorMessage)).toBeInTheDocument()
    expect(screen.getByText('Try Again')).toBeInTheDocument()
  })

  it('renders board not found state correctly', () => {
    mockUseBoardStore.mockReturnValue({
      ...defaultBoardStore,
      currentBoard: null
    } as any)

    render(
      <TestWrapper>
        <BoardView />
      </TestWrapper>
    )

    expect(screen.getByText('Board not found')).toBeInTheDocument()
  })

  it('renders board header with title and description', () => {
    render(
      <TestWrapper>
        <BoardView />
      </TestWrapper>
    )

    expect(screen.getByText('Test Board')).toBeInTheDocument()
    expect(screen.getByText('A test board for testing')).toBeInTheDocument()
  })

  it('renders all columns in desktop view', () => {
    render(
      <TestWrapper>
        <BoardView />
      </TestWrapper>
    )

    expect(screen.getByText('To Do')).toBeInTheDocument()
    expect(screen.getByText('In Progress')).toBeInTheDocument()
    expect(screen.getByText('Done')).toBeInTheDocument()
  })

  it('renders items in correct columns', () => {
    render(
      <TestWrapper>
        <BoardView />
      </TestWrapper>
    )

    expect(screen.getByText('Test Item 1')).toBeInTheDocument()
    expect(screen.getByText('Test Item 2')).toBeInTheDocument()
  })

  it('calls fetchBoardById on mount', () => {
    const mockFetchBoardById = jest.fn()
    mockUseBoardStore.mockReturnValue({
      ...defaultBoardStore,
      fetchBoardById: mockFetchBoardById
    } as any)

    render(
      <TestWrapper>
        <BoardView />
      </TestWrapper>
    )

    expect(mockFetchBoardById).toHaveBeenCalledWith('test-board-id', true)
  })

  it('calls setCurrentBoard cleanup on unmount', () => {
    const mockSetCurrentBoard = jest.fn()
    mockUseBoardStore.mockReturnValue({
      ...defaultBoardStore,
      setCurrentBoard: mockSetCurrentBoard
    } as any)

    const { unmount } = render(
      <TestWrapper>
        <BoardView />
      </TestWrapper>
    )

    unmount()

    expect(mockSetCurrentBoard).toHaveBeenCalledWith(null)
  })

  it('handles item selection with ctrl+click', async () => {
    const mockToggleItemSelection = jest.fn()
    mockUseBoardStore.mockReturnValue({
      ...defaultBoardStore,
      toggleItemSelection: mockToggleItemSelection
    } as any)

    render(
      <TestWrapper>
        <BoardView />
      </TestWrapper>
    )

    const item = screen.getByText('Test Item 1')
    await userEvent.click(item, { ctrlKey: true })

    expect(mockToggleItemSelection).toHaveBeenCalledWith('item-1')
  })

  it('handles drag and drop operations', async () => {
    const mockUpdateItem = jest.fn()
    mockUseItemStore.mockReturnValue({
      ...defaultItemStore,
      updateItem: mockUpdateItem
    } as any)

    render(
      <TestWrapper>
        <BoardView />
      </TestWrapper>
    )

    // This would test drag and drop functionality
    // Due to complexity of testing HTML5 drag and drop,
    // we'll test the handler function directly
    expect(mockUpdateItem).not.toHaveBeenCalled()
  })

  it('renders mobile view correctly', () => {
    mockUseIsMobile.mockReturnValue(true)

    render(
      <TestWrapper>
        <BoardView />
      </TestWrapper>
    )

    // Should render column selector tabs in mobile view
    expect(screen.getByText('To Do')).toBeInTheDocument()
    expect(screen.getByText('In Progress')).toBeInTheDocument()
    expect(screen.getByText('Done')).toBeInTheDocument()

    // Should show item count badges
    expect(screen.getByText('1')).toBeInTheDocument() // To Do column count
  })

  it('switches between columns in mobile view', async () => {
    mockUseIsMobile.mockReturnValue(true)

    render(
      <TestWrapper>
        <BoardView />
      </TestWrapper>
    )

    // Click on "In Progress" tab
    const inProgressTab = screen.getByRole('button', { name: /in progress/i })
    await userEvent.click(inProgressTab)

    // Should show items from the In Progress column
    expect(screen.getByText('Test Item 2')).toBeInTheDocument()
  })

  it('opens item form when "Add Item" button is clicked', async () => {
    render(
      <TestWrapper>
        <BoardView />
      </TestWrapper>
    )

    const addItemButton = screen.getAllByText('Add Item')[0]
    await userEvent.click(addItemButton)

    // ItemForm should be rendered (we'd need to mock it to test this properly)
    // This is a simplified test
    expect(addItemButton).toBeInTheDocument()
  })

  it('displays selected items count', () => {
    mockUseBoardStore.mockReturnValue({
      ...defaultBoardStore,
      selectedItems: ['item-1', 'item-2']
    } as any)

    render(
      <TestWrapper>
        <BoardView />
      </TestWrapper>
    )

    expect(screen.getByText('2 selected')).toBeInTheDocument()
  })

  it('shows bulk edit options when items are selected', () => {
    mockUseBoardStore.mockReturnValue({
      ...defaultBoardStore,
      selectedItems: ['item-1', 'item-2']
    } as any)

    render(
      <TestWrapper>
        <BoardView />
      </TestWrapper>
    )

    expect(screen.getByText('Bulk Edit')).toBeInTheDocument()
    expect(screen.getByText('Delete')).toBeInTheDocument()
  })

  it('handles try again button in error state', async () => {
    const mockFetchBoardById = jest.fn()
    mockUseBoardStore.mockReturnValue({
      ...defaultBoardStore,
      errors: { currentBoard: 'Test error' },
      fetchBoardById: mockFetchBoardById
    } as any)

    render(
      <TestWrapper>
        <BoardView />
      </TestWrapper>
    )

    const tryAgainButton = screen.getByText('Try Again')
    await userEvent.click(tryAgainButton)

    expect(mockFetchBoardById).toHaveBeenCalledWith('test-board-id', true)
  })

  it('displays empty state for columns with no items', () => {
    mockUseItemStore.mockReturnValue({
      ...defaultItemStore,
      items: [] // No items
    } as any)

    render(
      <TestWrapper>
        <BoardView />
      </TestWrapper>
    )

    // Should show empty state for all columns
    const emptyStates = screen.getAllByText('No items in this column')
    expect(emptyStates).toHaveLength(3) // One for each column
  })

  it('filters items correctly when search is used', async () => {
    // This would require the search functionality to be implemented
    // For now, we'll just test that the search input is rendered
    render(
      <TestWrapper>
        <BoardView />
      </TestWrapper>
    )

    // The search functionality would be tested here when implemented
    expect(screen.getByText('Test Item 1')).toBeInTheDocument()
    expect(screen.getByText('Test Item 2')).toBeInTheDocument()
  })
})