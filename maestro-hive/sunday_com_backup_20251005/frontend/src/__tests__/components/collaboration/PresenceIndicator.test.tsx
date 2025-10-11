import React from 'react'
import { render, screen } from '@testing-library/react'
import { PresenceIndicator } from '@/components/collaboration/PresenceIndicator'
import { useBoardPresence } from '@/hooks/useWebSocket'

// Mock the hook
jest.mock('@/hooks/useWebSocket')

const mockUseBoardPresence = useBoardPresence as jest.MockedFunction<typeof useBoardPresence>

const mockPresenceUsers = [
  {
    userId: 'user-1',
    username: 'John Doe',
    avatarUrl: 'https://example.com/avatar1.jpg',
    lastSeen: '2023-01-01T12:00:00Z',
  },
  {
    userId: 'user-2',
    username: 'Jane Smith',
    avatarUrl: 'https://example.com/avatar2.jpg',
    lastSeen: '2023-01-01T12:01:00Z',
  },
  {
    userId: 'user-3',
    username: 'Bob Johnson',
    lastSeen: '2023-01-01T12:02:00Z',
  },
]

const mockCursors = [
  {
    userId: 'user-1',
    username: 'John Doe',
    x: 100,
    y: 200,
    timestamp: '2023-01-01T12:00:00Z',
  },
  {
    userId: 'user-2',
    username: 'Jane Smith',
    x: 300,
    y: 150,
    timestamp: '2023-01-01T12:01:00Z',
  },
]

describe('PresenceIndicator', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('should render connection status when connected', () => {
    mockUseBoardPresence.mockReturnValue({
      isConnected: true,
      presenceUsers: [],
      cursors: [],
    })

    render(<PresenceIndicator boardId="board-1" />)

    expect(screen.getByText('Live')).toBeInTheDocument()
    expect(screen.getByTestId('wifi-icon') || screen.getByLabelText(/live/i)).toBeInTheDocument()
  })

  it('should render connection status when disconnected', () => {
    mockUseBoardPresence.mockReturnValue({
      isConnected: false,
      presenceUsers: [],
      cursors: [],
    })

    render(<PresenceIndicator boardId="board-1" />)

    expect(screen.getByText('Offline')).toBeInTheDocument()
  })

  it('should render presence users when available', () => {
    mockUseBoardPresence.mockReturnValue({
      isConnected: true,
      presenceUsers: mockPresenceUsers,
      cursors: [],
    })

    render(<PresenceIndicator boardId="board-1" />)

    expect(screen.getByText('3 viewing')).toBeInTheDocument()

    // Check if avatars are rendered for users with avatarUrl
    const johnAvatar = screen.getByAltText('John Doe')
    expect(johnAvatar).toBeInTheDocument()
    expect(johnAvatar).toHaveAttribute('src', 'https://example.com/avatar1.jpg')

    const janeAvatar = screen.getByAltText('Jane Smith')
    expect(janeAvatar).toBeInTheDocument()
    expect(janeAvatar).toHaveAttribute('src', 'https://example.com/avatar2.jpg')

    const bobAvatar = screen.getByAltText('Bob Johnson')
    expect(bobAvatar).toBeInTheDocument()
  })

  it('should show overflow count when more than 5 users', () => {
    const manyUsers = Array.from({ length: 8 }, (_, i) => ({
      userId: `user-${i + 1}`,
      username: `User ${i + 1}`,
      avatarUrl: `https://example.com/avatar${i + 1}.jpg`,
      lastSeen: '2023-01-01T12:00:00Z',
    }))

    mockUseBoardPresence.mockReturnValue({
      isConnected: true,
      presenceUsers: manyUsers,
      cursors: [],
    })

    render(<PresenceIndicator boardId="board-1" />)

    expect(screen.getByText('8 viewing')).toBeInTheDocument()
    expect(screen.getByText('+3')).toBeInTheDocument()
  })

  it('should not render user section when no users are present', () => {
    mockUseBoardPresence.mockReturnValue({
      isConnected: true,
      presenceUsers: [],
      cursors: [],
    })

    render(<PresenceIndicator boardId="board-1" />)

    expect(screen.queryByText('viewing')).not.toBeInTheDocument()
  })

  it('should render collaborative cursors', () => {
    mockUseBoardPresence.mockReturnValue({
      isConnected: true,
      presenceUsers: [],
      cursors: mockCursors,
    })

    render(<PresenceIndicator boardId="board-1" />)

    // Check if cursor usernames are rendered
    expect(screen.getByText('John Doe')).toBeInTheDocument()
    expect(screen.getByText('Jane Smith')).toBeInTheDocument()
  })

  it('should handle users with and without avatars', () => {
    const mixedUsers = [
      {
        userId: 'user-1',
        username: 'John Doe',
        avatarUrl: 'https://example.com/avatar1.jpg',
        lastSeen: '2023-01-01T12:00:00Z',
      },
      {
        userId: 'user-2',
        username: 'Jane Smith',
        lastSeen: '2023-01-01T12:01:00Z',
      },
    ]

    mockUseBoardPresence.mockReturnValue({
      isConnected: true,
      presenceUsers: mixedUsers,
      cursors: [],
    })

    render(<PresenceIndicator boardId="board-1" />)

    expect(screen.getByText('2 viewing')).toBeInTheDocument()

    const johnAvatar = screen.getByAltText('John Doe')
    expect(johnAvatar).toBeInTheDocument()
    expect(johnAvatar).toHaveAttribute('src', 'https://example.com/avatar1.jpg')

    const janeAvatar = screen.getByAltText('Jane Smith')
    expect(janeAvatar).toBeInTheDocument()
    // Should render a default avatar when no avatarUrl is provided
  })

  it('should pass correct boardId to useBoardPresence hook', () => {
    mockUseBoardPresence.mockReturnValue({
      isConnected: true,
      presenceUsers: [],
      cursors: [],
    })

    render(<PresenceIndicator boardId="test-board-123" />)

    expect(mockUseBoardPresence).toHaveBeenCalledWith('test-board-123')
  })

  it('should apply custom className', () => {
    mockUseBoardPresence.mockReturnValue({
      isConnected: true,
      presenceUsers: [],
      cursors: [],
    })

    const { container } = render(
      <PresenceIndicator boardId="board-1" className="custom-class" />
    )

    expect(container.firstChild).toHaveClass('custom-class')
  })

  describe('CollaborativeCursor', () => {
    it('should position cursors correctly', () => {
      mockUseBoardPresence.mockReturnValue({
        isConnected: true,
        presenceUsers: [],
        cursors: [
          {
            userId: 'user-1',
            username: 'John Doe',
            x: 150,
            y: 250,
            timestamp: '2023-01-01T12:00:00Z',
          },
        ],
      })

      render(<PresenceIndicator boardId="board-1" />)

      const cursorElement = screen.getByText('John Doe').closest('[style*="left: 150"]')
      expect(cursorElement).toBeInTheDocument()
      expect(cursorElement).toHaveStyle('left: 150px')
      expect(cursorElement).toHaveStyle('top: 250px')
    })

    it('should generate consistent colors for user cursors', () => {
      mockUseBoardPresence.mockReturnValue({
        isConnected: true,
        presenceUsers: [],
        cursors: [
          {
            userId: 'user-1',
            username: 'John Doe',
            x: 100,
            y: 200,
            timestamp: '2023-01-01T12:00:00Z',
          },
        ],
      })

      const { rerender } = render(<PresenceIndicator boardId="board-1" />)

      const firstRenderCursor = screen.getByText('John Doe').closest('div')
      const firstRenderClass = firstRenderCursor?.className

      // Re-render and check if the color class is consistent
      rerender(<PresenceIndicator boardId="board-1" />)

      const secondRenderCursor = screen.getByText('John Doe').closest('div')
      const secondRenderClass = secondRenderCursor?.className

      expect(firstRenderClass).toBe(secondRenderClass)
    })
  })
})