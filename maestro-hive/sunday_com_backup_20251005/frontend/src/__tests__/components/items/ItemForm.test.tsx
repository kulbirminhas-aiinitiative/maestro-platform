import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ItemForm } from '@/components/items/ItemForm'
import { useItemStore } from '@/stores/item.store'
import { useBoardStore } from '@/stores/board.store'
import { Item } from '@/types'

jest.mock('@/stores/item.store')
jest.mock('@/stores/board.store')

const mockUseItemStore = useItemStore as jest.MockedFunction<typeof useItemStore>
const mockUseBoardStore = useBoardStore as jest.MockedFunction<typeof useBoardStore>

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
      {component}
    </QueryClientProvider>
  )
}

const mockItemStore = {
  createItem: jest.fn(),
  updateItem: jest.fn(),
  loading: {
    items: false,
    currentItem: false,
    creating: false,
    updating: false,
    deleting: false,
    bulkOperations: false,
  },
}

const mockBoardStore = {
  columns: [
    {
      id: 'col-1',
      name: 'To Do',
      columnType: 'status',
      settings: { statusValue: 'todo' },
    },
  ],
  currentBoard: {
    id: 'board-1',
    members: [
      {
        id: 'member-1',
        user: {
          id: 'user-1',
          fullName: 'John Doe',
          avatarUrl: 'https://example.com/avatar.jpg',
        },
      },
    ],
  },
}

const mockItem: Item = {
  id: 'item-1',
  boardId: 'board-1',
  name: 'Test Task',
  description: 'Test description',
  data: {
    status: 'todo',
    priority: 'medium',
    labels: ['urgent', 'frontend'],
  },
  position: 1,
  createdAt: '2023-01-01T00:00:00Z',
  updatedAt: '2023-01-01T00:00:00Z',
  assignees: [
    {
      id: 'user-1',
      fullName: 'John Doe',
      avatarUrl: 'https://example.com/avatar.jpg',
    },
  ],
}

describe('ItemForm', () => {
  const defaultProps = {
    isOpen: true,
    onClose: jest.fn(),
    boardId: 'board-1',
  }

  beforeEach(() => {
    mockUseItemStore.mockReturnValue(mockItemStore as any)
    mockUseBoardStore.mockReturnValue(mockBoardStore as any)
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  it('renders create form when no item is provided', () => {
    renderWithProviders(<ItemForm {...defaultProps} />)

    expect(screen.getByText('Create New Item')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Enter item name...')).toBeInTheDocument()
    expect(screen.getByText('Create Item')).toBeInTheDocument()
  })

  it('renders edit form when item is provided', () => {
    renderWithProviders(<ItemForm {...defaultProps} item={mockItem} />)

    expect(screen.getByText('Edit Item')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Test Task')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Test description')).toBeInTheDocument()
    expect(screen.getByText('Update Item')).toBeInTheDocument()
  })

  it('validates required fields', async () => {
    const user = userEvent.setup()
    renderWithProviders(<ItemForm {...defaultProps} />)

    const submitButton = screen.getByText('Create Item')
    await user.click(submitButton)

    expect(screen.getByText('Name is required')).toBeInTheDocument()
  })

  it('creates new item on form submission', async () => {
    const user = userEvent.setup()
    mockItemStore.createItem.mockResolvedValue(mockItem)

    renderWithProviders(<ItemForm {...defaultProps} />)

    // Fill form
    await user.type(screen.getByPlaceholderText('Enter item name...'), 'New Task')
    await user.type(screen.getByPlaceholderText('Enter item description...'), 'New description')

    // Submit form
    await user.click(screen.getByText('Create Item'))

    await waitFor(() => {
      expect(mockItemStore.createItem).toHaveBeenCalledWith('board-1', {
        name: 'New Task',
        description: 'New description',
        boardId: 'board-1',
        itemData: {
          status: 'todo',
          priority: 'medium',
          dueDate: null,
          labels: [],
          progress: 0,
        },
        assigneeIds: [],
      })
    })
  })

  it('updates existing item on form submission', async () => {
    const user = userEvent.setup()
    mockItemStore.updateItem.mockResolvedValue(mockItem)

    renderWithProviders(<ItemForm {...defaultProps} item={mockItem} />)

    // Modify name
    const nameInput = screen.getByDisplayValue('Test Task')
    await user.clear(nameInput)
    await user.type(nameInput, 'Updated Task')

    // Submit form
    await user.click(screen.getByText('Update Item'))

    await waitFor(() => {
      expect(mockItemStore.updateItem).toHaveBeenCalledWith('item-1', {
        name: 'Updated Task',
        description: 'Test description',
        itemData: expect.any(Object),
        assigneeIds: ['user-1'],
      })
    })
  })

  it('handles priority selection', async () => {
    const user = userEvent.setup()
    renderWithProviders(<ItemForm {...defaultProps} />)

    // Find and click priority select
    const prioritySelect = screen.getByText('Select priority')
    await user.click(prioritySelect)

    // Select high priority
    await user.click(screen.getByText('High'))

    // Verify selection
    expect(screen.getByText('High')).toBeInTheDocument()
  })

  it('handles status selection', async () => {
    const user = userEvent.setup()
    renderWithProviders(<ItemForm {...defaultProps} />)

    // Find and click status select
    const statusSelect = screen.getByText('Select status')
    await user.click(statusSelect)

    // Select in progress status
    await user.click(screen.getByText('In Progress'))

    // Verify selection
    expect(screen.getByText('In Progress')).toBeInTheDocument()
  })

  it('handles due date input', async () => {
    const user = userEvent.setup()
    renderWithProviders(<ItemForm {...defaultProps} />)

    const dueDateInput = screen.getByLabelText('Due Date')
    await user.type(dueDateInput, '2023-12-25')

    expect(dueDateInput).toHaveValue('2023-12-25')
  })

  it('handles progress input', async () => {
    const user = userEvent.setup()
    renderWithProviders(<ItemForm {...defaultProps} />)

    const progressInput = screen.getByLabelText('Progress (%)')
    await user.clear(progressInput)
    await user.type(progressInput, '75')

    expect(progressInput).toHaveValue(75)
  })

  it('handles label addition and removal', async () => {
    const user = userEvent.setup()
    renderWithProviders(<ItemForm {...defaultProps} />)

    // Add new label
    await user.click(screen.getByText('Add Label'))

    const labelInput = screen.getByPlaceholderText('Enter label...')
    await user.type(labelInput, 'new-label')
    await user.click(screen.getByText('Add'))

    // Verify label was added
    expect(screen.getByText('new-label')).toBeInTheDocument()

    // Remove label
    const removeButton = screen.getByTitle('Remove label')
    await user.click(removeButton)

    // Verify label was removed
    expect(screen.queryByText('new-label')).not.toBeInTheDocument()
  })

  it('handles assignee selection', async () => {
    const user = userEvent.setup()
    renderWithProviders(<ItemForm {...defaultProps} />)

    // Find assignee button
    const assigneeButton = screen.getByText('John Doe')
    await user.click(assigneeButton)

    // Verify assignee was added
    expect(screen.getByText('John Doe')).toBeInTheDocument()
  })

  it('closes form on cancel', async () => {
    const user = userEvent.setup()
    const onClose = jest.fn()

    renderWithProviders(<ItemForm {...defaultProps} onClose={onClose} />)

    await user.click(screen.getByText('Cancel'))

    expect(onClose).toHaveBeenCalled()
  })

  it('shows loading state during submission', async () => {
    const user = userEvent.setup()
    mockItemStore.createItem.mockImplementation(() => new Promise(() => {})) // Never resolves

    renderWithProviders(<ItemForm {...defaultProps} />)

    await user.type(screen.getByPlaceholderText('Enter item name...'), 'Test Task')
    await user.click(screen.getByText('Create Item'))

    expect(screen.getByText('Saving...')).toBeInTheDocument()
  })

  it('populates form with existing item data', () => {
    renderWithProviders(<ItemForm {...defaultProps} item={mockItem} />)

    expect(screen.getByDisplayValue('Test Task')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Test description')).toBeInTheDocument()
    expect(screen.getByText('urgent')).toBeInTheDocument()
    expect(screen.getByText('frontend')).toBeInTheDocument()
  })
})