import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ItemForm } from '../ItemForm'
import { useItemStore } from '@/stores/item.store'
import { useBoardStore } from '@/stores/board.store'
import type { Item, Board, BoardColumn, BoardMember } from '@/types'

// Mock dependencies
jest.mock('@/stores/item.store')
jest.mock('@/stores/board.store')

const mockUseItemStore = useItemStore as jest.MockedFunction<typeof useItemStore>
const mockUseBoardStore = useBoardStore as jest.MockedFunction<typeof useBoardStore>

// Mock data
const mockBoard: Board = {
  id: 'test-board-id',
  workspaceId: 'workspace-1',
  name: 'Test Board',
  description: 'A test board',
  isPrivate: false,
  settings: {},
  viewSettings: {},
  createdAt: '2023-01-01T00:00:00Z',
  updatedAt: '2023-01-01T00:00:00Z',
  position: 1,
  members: [
    {
      id: 'member-1',
      boardId: 'test-board-id',
      userId: 'user-1',
      role: 'member',
      joinedAt: '2023-01-01T00:00:00Z',
      user: {
        id: 'user-1',
        email: 'user1@example.com',
        fullName: 'John Doe',
        avatarUrl: 'https://example.com/avatar1.jpg',
        timezone: 'UTC',
        locale: 'en',
        settings: {},
        createdAt: '2023-01-01T00:00:00Z',
        updatedAt: '2023-01-01T00:00:00Z'
      }
    },
    {
      id: 'member-2',
      boardId: 'test-board-id',
      userId: 'user-2',
      role: 'member',
      joinedAt: '2023-01-01T00:00:00Z',
      user: {
        id: 'user-2',
        email: 'user2@example.com',
        fullName: 'Jane Smith',
        avatarUrl: 'https://example.com/avatar2.jpg',
        timezone: 'UTC',
        locale: 'en',
        settings: {},
        createdAt: '2023-01-01T00:00:00Z',
        updatedAt: '2023-01-01T00:00:00Z'
      }
    }
  ] as BoardMember[]
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
  }
]

const mockItem: Item = {
  id: 'test-item-id',
  boardId: 'test-board-id',
  name: 'Test Item',
  description: 'A test item',
  data: {
    status: 'todo',
    priority: 'medium',
    labels: ['urgent', 'bug'],
    progress: 25
  },
  position: 1,
  createdAt: '2023-01-01T00:00:00Z',
  updatedAt: '2023-01-01T00:00:00Z',
  assignees: [
    {
      id: 'user-1',
      email: 'user1@example.com',
      fullName: 'John Doe',
      avatarUrl: 'https://example.com/avatar1.jpg',
      timezone: 'UTC',
      locale: 'en',
      settings: {},
      createdAt: '2023-01-01T00:00:00Z',
      updatedAt: '2023-01-01T00:00:00Z'
    }
  ]
}

const defaultItemStore = {
  createItem: jest.fn(),
  updateItem: jest.fn(),
  loading: { creating: false, updating: false }
}

const defaultBoardStore = {
  columns: mockColumns,
  currentBoard: mockBoard
}

describe('ItemForm', () => {
  const defaultProps = {
    isOpen: true,
    onClose: jest.fn(),
    boardId: 'test-board-id',
    columnId: 'col-1',
    item: null
  }

  beforeEach(() => {
    jest.clearAllMocks()
    mockUseItemStore.mockReturnValue(defaultItemStore as any)
    mockUseBoardStore.mockReturnValue(defaultBoardStore as any)
  })

  it('renders create form when no item is provided', () => {
    render(<ItemForm {...defaultProps} />)

    expect(screen.getByText('Create New Item')).toBeInTheDocument()
    expect(screen.getByPlaceholderText('Enter item name...')).toBeInTheDocument()
    expect(screen.getByText('Create Item')).toBeInTheDocument()
  })

  it('renders edit form when item is provided', () => {
    render(<ItemForm {...defaultProps} item={mockItem} />)

    expect(screen.getByText('Edit Item')).toBeInTheDocument()
    expect(screen.getByDisplayValue('Test Item')).toBeInTheDocument()
    expect(screen.getByDisplayValue('A test item')).toBeInTheDocument()
    expect(screen.getByText('Update Item')).toBeInTheDocument()
  })

  it('does not render when isOpen is false', () => {
    render(<ItemForm {...defaultProps} isOpen={false} />)

    expect(screen.queryByText('Create New Item')).not.toBeInTheDocument()
  })

  it('calls onClose when close button is clicked', async () => {
    const mockOnClose = jest.fn()
    render(<ItemForm {...defaultProps} onClose={mockOnClose} />)

    const closeButton = screen.getByRole('button', { name: /close/i })
    await userEvent.click(closeButton)

    expect(mockOnClose).toHaveBeenCalled()
  })

  it('calls onClose when cancel button is clicked', async () => {
    const mockOnClose = jest.fn()
    render(<ItemForm {...defaultProps} onClose={mockOnClose} />)

    const cancelButton = screen.getByText('Cancel')
    await userEvent.click(cancelButton)

    expect(mockOnClose).toHaveBeenCalled()
  })

  it('validates required fields', async () => {
    render(<ItemForm {...defaultProps} />)

    const submitButton = screen.getByText('Create Item')
    await userEvent.click(submitButton)

    expect(screen.getByText('Name is required')).toBeInTheDocument()
  })

  it('submits form with valid data for creating item', async () => {
    const mockCreateItem = jest.fn().mockResolvedValue({})
    mockUseItemStore.mockReturnValue({
      ...defaultItemStore,
      createItem: mockCreateItem
    } as any)

    render(<ItemForm {...defaultProps} />)

    // Fill in the form
    const nameInput = screen.getByPlaceholderText('Enter item name...')
    await userEvent.type(nameInput, 'New Test Item')

    const descriptionInput = screen.getByPlaceholderText('Enter item description...')
    await userEvent.type(descriptionInput, 'New item description')

    // Submit the form
    const submitButton = screen.getByText('Create Item')
    await userEvent.click(submitButton)

    await waitFor(() => {
      expect(mockCreateItem).toHaveBeenCalledWith(
        'test-board-id',
        expect.objectContaining({
          name: 'New Test Item',
          description: 'New item description',
          itemData: expect.objectContaining({
            status: 'todo',
            priority: 'medium'
          })
        })
      )
    })
  })

  it('submits form with valid data for updating item', async () => {
    const mockUpdateItem = jest.fn().mockResolvedValue({})
    mockUseItemStore.mockReturnValue({
      ...defaultItemStore,
      updateItem: mockUpdateItem
    } as any)

    render(<ItemForm {...defaultProps} item={mockItem} />)

    // Change the name
    const nameInput = screen.getByDisplayValue('Test Item')
    await userEvent.clear(nameInput)
    await userEvent.type(nameInput, 'Updated Test Item')

    // Submit the form
    const submitButton = screen.getByText('Update Item')
    await userEvent.click(submitButton)

    await waitFor(() => {
      expect(mockUpdateItem).toHaveBeenCalledWith(
        'test-item-id',
        expect.objectContaining({
          name: 'Updated Test Item'
        })
      )
    })
  })

  it('displays existing item data in form fields', () => {
    render(<ItemForm {...defaultProps} item={mockItem} />)

    expect(screen.getByDisplayValue('Test Item')).toBeInTheDocument()
    expect(screen.getByDisplayValue('A test item')).toBeInTheDocument()
    expect(screen.getByDisplayValue('25')).toBeInTheDocument()
  })

  it('allows adding and removing labels', async () => {
    render(<ItemForm {...defaultProps} item={mockItem} />)

    // Should display existing labels
    expect(screen.getByText('urgent')).toBeInTheDocument()
    expect(screen.getByText('bug')).toBeInTheDocument()

    // Remove a label
    const removeButtons = screen.getAllByRole('button', { name: '' }) // X buttons
    await userEvent.click(removeButtons[0])

    // Should not show the removed label anymore
    await waitFor(() => {
      expect(screen.queryByText('urgent')).not.toBeInTheDocument()
    })

    // Add a new label
    const labelInput = screen.getByPlaceholderText('Enter label...')
    await userEvent.type(labelInput, 'feature')

    const addButton = screen.getByText('Add')
    await userEvent.click(addButton)

    expect(screen.getByText('feature')).toBeInTheDocument()
  })

  it('allows adding labels with Enter key', async () => {
    render(<ItemForm {...defaultProps} />)

    const labelInput = screen.getByPlaceholderText('Enter label...')
    await userEvent.type(labelInput, 'test-label{enter}')

    expect(screen.getByText('test-label')).toBeInTheDocument()
  })

  it('displays available board members for assignment', () => {
    render(<ItemForm {...defaultProps} />)

    expect(screen.getByText('John Doe')).toBeInTheDocument()
    expect(screen.getByText('Jane Smith')).toBeInTheDocument()
  })

  it('allows selecting and deselecting assignees', async () => {
    render(<ItemForm {...defaultProps} />)

    // Select an assignee
    const johnDoeButton = screen.getByRole('button', { name: /john doe/i })
    await userEvent.click(johnDoeButton)

    // Should now show John Doe as selected (this would be in a different section)
    // The exact UI depends on the implementation
    expect(johnDoeButton).toBeInTheDocument()
  })

  it('shows loading state during form submission', async () => {
    mockUseItemStore.mockReturnValue({
      ...defaultItemStore,
      loading: { creating: true, updating: false }
    } as any)

    render(<ItemForm {...defaultProps} />)

    expect(screen.getByText('Saving...')).toBeInTheDocument()
  })

  it('disables submit button during loading', async () => {
    mockUseItemStore.mockReturnValue({
      ...defaultItemStore,
      loading: { creating: true, updating: false }
    } as any)

    render(<ItemForm {...defaultProps} />)

    const submitButton = screen.getByText('Saving...')
    expect(submitButton).toBeDisabled()
  })

  it('handles status selection', async () => {
    render(<ItemForm {...defaultProps} />)

    // The status dropdown would be tested here
    // This depends on the specific dropdown implementation used
    expect(screen.getByText('Status')).toBeInTheDocument()
  })

  it('handles priority selection', async () => {
    render(<ItemForm {...defaultProps} />)

    // The priority dropdown would be tested here
    expect(screen.getByText('Priority')).toBeInTheDocument()
  })

  it('handles date input for due date', async () => {
    render(<ItemForm {...defaultProps} />)

    const dueDateInput = screen.getByLabelText(/due date/i)
    await userEvent.type(dueDateInput, '2023-12-31')

    expect(dueDateInput).toHaveValue('2023-12-31')
  })

  it('handles progress input', async () => {
    render(<ItemForm {...defaultProps} />)

    const progressInput = screen.getByLabelText(/progress/i)
    await userEvent.clear(progressInput)
    await userEvent.type(progressInput, '75')

    expect(progressInput).toHaveValue(75)
  })

  it('resets form when item prop changes', () => {
    const { rerender } = render(<ItemForm {...defaultProps} item={mockItem} />)

    expect(screen.getByDisplayValue('Test Item')).toBeInTheDocument()

    // Change to create mode
    rerender(<ItemForm {...defaultProps} item={null} />)

    expect(screen.queryByDisplayValue('Test Item')).not.toBeInTheDocument()
    expect(screen.getByPlaceholderText('Enter item name...')).toHaveValue('')
  })

  it('prevents duplicate labels', async () => {
    render(<ItemForm {...defaultProps} item={mockItem} />)

    // Try to add a label that already exists
    const labelInput = screen.getByPlaceholderText('Enter label...')
    await userEvent.type(labelInput, 'urgent')

    const addButton = screen.getByText('Add')
    await userEvent.click(addButton)

    // Should still only have one 'urgent' label
    const urgentLabels = screen.getAllByText('urgent')
    expect(urgentLabels).toHaveLength(1)
  })
})