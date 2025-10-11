import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { TimeTracker } from '../TimeTracker'
import { useTimeStore } from '@/stores/time.store'
import { useAuth } from '@/hooks/useAuth'
import type { Item, ActiveTimer } from '@/types'

// Mock the stores and hooks
jest.mock('@/stores/time.store')
jest.mock('@/hooks/useAuth')

const mockUseTimeStore = useTimeStore as jest.MockedFunction<typeof useTimeStore>
const mockUseAuth = useAuth as jest.MockedFunction<typeof useAuth>

const mockItem: Item = {
  id: 'item-1',
  boardId: 'board-1',
  name: 'Test Item',
  description: 'Test description',
  data: { status: 'todo' },
  position: 1,
  createdAt: '2023-01-01T00:00:00Z',
  updatedAt: '2023-01-01T00:00:00Z',
  timeEntries: [],
}

const mockActiveTimer: ActiveTimer = {
  id: 'timer-1',
  itemId: 'item-1',
  boardId: 'board-1',
  description: 'Working on test',
  startTime: '2023-01-01T10:00:00Z',
  billable: true,
}

const mockTimeStore = {
  activeTimer: null,
  loading: {
    starting: false,
    stopping: false,
    creating: false,
  },
  errors: {
    starting: null,
    stopping: null,
    creating: null,
  },
  startTimer: jest.fn(),
  stopTimer: jest.fn(),
  getActiveTimer: jest.fn(),
  createTimeEntry: jest.fn(),
}

describe('TimeTracker', () => {
  beforeEach(() => {
    jest.clearAllMocks()

    mockUseAuth.mockReturnValue({
      user: {
        id: 'user-1',
        email: 'test@example.com',
        fullName: 'Test User',
        firstName: 'Test',
        lastName: 'User',
        timezone: 'UTC',
        locale: 'en',
        settings: {},
        createdAt: '2023-01-01T00:00:00Z',
        updatedAt: '2023-01-01T00:00:00Z',
      },
      isAuthenticated: true,
      login: jest.fn(),
      logout: jest.fn(),
      register: jest.fn(),
      updateProfile: jest.fn(),
      loading: false,
    })

    mockUseTimeStore.mockReturnValue(mockTimeStore)
  })

  it('renders time tracker with track time button', () => {
    render(<TimeTracker />)

    expect(screen.getByText('Time Tracking')).toBeInTheDocument()
    expect(screen.getByText('Track Time')).toBeInTheDocument()
  })

  it('shows description input when track time is clicked', () => {
    render(<TimeTracker />)

    fireEvent.click(screen.getByText('Track Time'))

    expect(screen.getByPlaceholderText('What are you working on?')).toBeInTheDocument()
    expect(screen.getByText('Start Timer')).toBeInTheDocument()
    expect(screen.getByText('Manual Entry')).toBeInTheDocument()
  })

  it('starts timer with correct data', async () => {
    render(<TimeTracker item={mockItem} boardId="board-1" />)

    fireEvent.click(screen.getByText('Track Time'))

    const descriptionInput = screen.getByPlaceholderText('What are you working on?')
    fireEvent.change(descriptionInput, { target: { value: 'Working on feature' } })

    const billableCheckbox = screen.getByLabelText('Billable')
    fireEvent.click(billableCheckbox)

    fireEvent.click(screen.getByText('Start Timer'))

    await waitFor(() => {
      expect(mockTimeStore.startTimer).toHaveBeenCalledWith({
        itemId: 'item-1',
        boardId: 'board-1',
        description: 'Working on feature',
        billable: true,
        metadata: {
          itemName: 'Test Item',
          boardName: undefined,
          startedBy: 'user-1',
        },
      })
    })
  })

  it('shows active timer with elapsed time', () => {
    const activeTimerStore = {
      ...mockTimeStore,
      activeTimer: mockActiveTimer,
    }
    mockUseTimeStore.mockReturnValue(activeTimerStore)

    // Mock Date.now to return a fixed time
    const mockNow = new Date('2023-01-01T10:05:30Z').getTime()
    jest.spyOn(Date, 'now').mockReturnValue(mockNow)

    render(<TimeTracker item={mockItem} />)

    expect(screen.getByText('Time Tracking')).toBeInTheDocument()
    expect(screen.getByText('5:30')).toBeInTheDocument() // 5 minutes 30 seconds
    expect(screen.getByText('Stop Timer')).toBeInTheDocument()
  })

  it('shows warning when timer is running for different item', () => {
    const activeTimerStore = {
      ...mockTimeStore,
      activeTimer: { ...mockActiveTimer, itemId: 'different-item' },
    }
    mockUseTimeStore.mockReturnValue(activeTimerStore)

    render(<TimeTracker item={mockItem} />)

    expect(screen.getByText('Timer running for another item')).toBeInTheDocument()
    expect(screen.getByText('Working on test')).toBeInTheDocument()
  })

  it('stops timer when stop button is clicked', async () => {
    const activeTimerStore = {
      ...mockTimeStore,
      activeTimer: mockActiveTimer,
    }
    mockUseTimeStore.mockReturnValue(activeTimerStore)

    render(<TimeTracker item={mockItem} />)

    fireEvent.click(screen.getByText('Stop Timer'))

    await waitFor(() => {
      expect(mockTimeStore.stopTimer).toHaveBeenCalled()
    })
  })

  it('creates manual time entry', async () => {
    render(<TimeTracker item={mockItem} boardId="board-1" />)

    fireEvent.click(screen.getByText('Track Time'))

    const descriptionInput = screen.getByPlaceholderText('What are you working on?')
    fireEvent.change(descriptionInput, { target: { value: 'Manual entry' } })

    fireEvent.click(screen.getByText('Manual Entry'))

    await waitFor(() => {
      expect(mockTimeStore.createTimeEntry).toHaveBeenCalledWith({
        itemId: 'item-1',
        boardId: 'board-1',
        description: 'Manual entry',
        billable: false,
      })
    })
  })

  it('shows recent time entries for item', () => {
    const itemWithTimeEntries: Item = {
      ...mockItem,
      timeEntries: [
        {
          id: 'entry-1',
          itemId: 'item-1',
          userId: 'user-1',
          description: 'Recent work',
          startTime: '2023-01-01T09:00:00Z',
          endTime: '2023-01-01T10:00:00Z',
          durationSeconds: 3600,
          isBillable: true,
          createdAt: '2023-01-01T09:00:00Z',
          updatedAt: '2023-01-01T10:00:00Z',
          item: mockItem,
          user: {
            id: 'user-1',
            email: 'test@example.com',
            fullName: 'Test User',
            firstName: 'Test',
            lastName: 'User',
            timezone: 'UTC',
            locale: 'en',
            settings: {},
            createdAt: '2023-01-01T00:00:00Z',
            updatedAt: '2023-01-01T00:00:00Z',
          },
        },
      ],
    }

    render(<TimeTracker item={itemWithTimeEntries} />)

    expect(screen.getByText('Recent Entries')).toBeInTheDocument()
    expect(screen.getByText('Recent work')).toBeInTheDocument()
    expect(screen.getByText('1:00:00')).toBeInTheDocument() // 1 hour
  })

  it('shows loading state when starting timer', () => {
    const loadingStore = {
      ...mockTimeStore,
      loading: { ...mockTimeStore.loading, starting: true },
    }
    mockUseTimeStore.mockReturnValue(loadingStore)

    render(<TimeTracker />)

    fireEvent.click(screen.getByText('Track Time'))

    expect(screen.getByText('Starting...')).toBeInTheDocument()
  })

  it('shows error message when timer operations fail', () => {
    const errorStore = {
      ...mockTimeStore,
      errors: { ...mockTimeStore.errors, starting: 'Failed to start timer' },
    }
    mockUseTimeStore.mockReturnValue(errorStore)

    render(<TimeTracker />)

    expect(screen.getByText('Failed to start timer')).toBeInTheDocument()
  })

  it('calls onTimerUpdate when timer state changes', () => {
    const onTimerUpdate = jest.fn()

    render(<TimeTracker onTimerUpdate={onTimerUpdate} />)

    expect(onTimerUpdate).toHaveBeenCalledWith(false)

    // Change to active timer
    const activeTimerStore = {
      ...mockTimeStore,
      activeTimer: mockActiveTimer,
    }
    mockUseTimeStore.mockReturnValue(activeTimerStore)

    render(<TimeTracker onTimerUpdate={onTimerUpdate} />)

    expect(onTimerUpdate).toHaveBeenCalledWith(true)
  })

  it('fetches active timer on mount', () => {
    render(<TimeTracker />)

    expect(mockTimeStore.getActiveTimer).toHaveBeenCalled()
  })

  it('formats elapsed time correctly', () => {
    const activeTimerStore = {
      ...mockTimeStore,
      activeTimer: mockActiveTimer,
    }
    mockUseTimeStore.mockReturnValue(activeTimerStore)

    // Test different time intervals
    const testCases = [
      { now: '2023-01-01T10:00:30Z', expected: '0:30' }, // 30 seconds
      { now: '2023-01-01T10:02:15Z', expected: '2:15' }, // 2 minutes 15 seconds
      { now: '2023-01-01T11:30:45Z', expected: '1:30:45' }, // 1 hour 30 minutes 45 seconds
    ]

    testCases.forEach(({ now, expected }) => {
      jest.spyOn(Date, 'now').mockReturnValue(new Date(now).getTime())

      render(<TimeTracker item={mockItem} />)

      expect(screen.getByText(expected)).toBeInTheDocument()
    })
  })

  afterEach(() => {
    jest.restoreAllMocks()
  })
})