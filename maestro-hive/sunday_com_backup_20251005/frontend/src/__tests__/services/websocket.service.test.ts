import { webSocketService } from '@/services/websocket.service'
import { useBoardStore } from '@/stores/board.store'
import { useItemStore } from '@/stores/item.store'
import { apiClient } from '@/lib/api'
import toast from 'react-hot-toast'

// Mock dependencies
jest.mock('@/stores/board.store')
jest.mock('@/stores/item.store')
jest.mock('@/lib/api')
jest.mock('react-hot-toast')
jest.mock('socket.io-client', () => ({
  io: jest.fn(() => ({
    on: jest.fn(),
    emit: jest.fn(),
    disconnect: jest.fn(),
    connected: true,
  })),
}))

const mockUseBoardStore = useBoardStore as jest.Mocked<typeof useBoardStore>
const mockUseItemStore = useItemStore as jest.Mocked<typeof useItemStore>
const mockApiClient = apiClient as jest.Mocked<typeof apiClient>

describe('WebSocketService', () => {
  let mockSocket: any

  beforeEach(() => {
    const { io } = require('socket.io-client')
    mockSocket = {
      on: jest.fn(),
      emit: jest.fn(),
      disconnect: jest.fn(),
      connected: true,
    }
    io.mockReturnValue(mockSocket)

    mockApiClient.getToken.mockReturnValue('test-token')

    // Mock store getState methods
    mockUseBoardStore.getState = jest.fn().mockReturnValue({
      handleRealTimeUpdate: jest.fn(),
    })

    mockUseItemStore.getState = jest.fn().mockReturnValue({
      handleRealTimeUpdate: jest.fn(),
    })
  })

  afterEach(() => {
    jest.clearAllMocks()
  })

  describe('connection', () => {
    it('connects to WebSocket server with auth token', () => {
      const { io } = require('socket.io-client')

      // Create new service instance to trigger connection
      new (require('@/services/websocket.service').constructor)()

      expect(io).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          auth: {
            token: 'test-token',
          },
          transports: ['websocket'],
          forceNew: true,
        })
      )
    })

    it('sets up event listeners on connection', () => {
      // Create new service instance
      new (require('@/services/websocket.service').constructor)()

      expect(mockSocket.on).toHaveBeenCalledWith('connect', expect.any(Function))
      expect(mockSocket.on).toHaveBeenCalledWith('disconnect', expect.any(Function))
      expect(mockSocket.on).toHaveBeenCalledWith('board_created', expect.any(Function))
      expect(mockSocket.on).toHaveBeenCalledWith('item_updated', expect.any(Function))
    })
  })

  describe('channel management', () => {
    it('joins workspace channel', () => {
      webSocketService.joinWorkspace('workspace-1')

      expect(mockSocket.emit).toHaveBeenCalledWith('join_workspace', {
        workspaceId: 'workspace-1',
      })
    })

    it('leaves workspace channel', () => {
      webSocketService.leaveWorkspace('workspace-1')

      expect(mockSocket.emit).toHaveBeenCalledWith('leave_workspace', {
        workspaceId: 'workspace-1',
      })
    })

    it('joins board channel', () => {
      webSocketService.joinBoard('board-1')

      expect(mockSocket.emit).toHaveBeenCalledWith('join_board', {
        boardId: 'board-1',
      })
    })

    it('leaves board channel', () => {
      webSocketService.leaveBoard('board-1')

      expect(mockSocket.emit).toHaveBeenCalledWith('leave_board', {
        boardId: 'board-1',
      })
    })
  })

  describe('cursor tracking', () => {
    it('updates cursor position', () => {
      webSocketService.updateCursor(100, 200, 'board-1')

      expect(mockSocket.emit).toHaveBeenCalledWith('cursor_move', {
        x: 100,
        y: 200,
        boardId: 'board-1',
        timestamp: expect.any(String),
      })
    })

    it('starts mouse tracking', () => {
      const stopTracking = webSocketService.startMouseTracking('board-1')

      expect(typeof stopTracking).toBe('function')

      // Test mouse move event
      const mouseMoveEvent = new MouseEvent('mousemove', {
        clientX: 150,
        clientY: 250,
      })

      document.dispatchEvent(mouseMoveEvent)

      // Should emit cursor update (throttled)
      setTimeout(() => {
        expect(mockSocket.emit).toHaveBeenCalledWith('cursor_move', expect.objectContaining({
          x: 150,
          y: 250,
          boardId: 'board-1',
        }))
      }, 150)

      // Clean up
      stopTracking()
    })
  })

  describe('event handling', () => {
    it('handles board_created event', () => {
      const mockBoardStore = {
        handleRealTimeUpdate: jest.fn(),
      }
      mockUseBoardStore.getState.mockReturnValue(mockBoardStore)

      // Simulate board_created event
      const eventData = {
        board: { id: 'board-1', name: 'New Board' },
        user: { id: 'user-1', name: 'John' },
      }

      // Get the event handler that was registered
      const boardCreatedHandler = mockSocket.on.mock.calls.find(
        call => call[0] === 'board_created'
      )?.[1]

      boardCreatedHandler?.(eventData)

      expect(mockBoardStore.handleRealTimeUpdate).toHaveBeenCalledWith(
        'board_created',
        eventData
      )
    })

    it('handles item_updated event', () => {
      const mockItemStore = {
        handleRealTimeUpdate: jest.fn(),
      }
      mockUseItemStore.getState.mockReturnValue(mockItemStore)

      const eventData = {
        itemId: 'item-1',
        changes: { name: { old: 'Old Name', new: 'New Name' } },
        updatedBy: 'user-1',
      }

      // Get the event handler
      const itemUpdatedHandler = mockSocket.on.mock.calls.find(
        call => call[0] === 'item_updated'
      )?.[1]

      itemUpdatedHandler?.(eventData)

      expect(mockItemStore.handleRealTimeUpdate).toHaveBeenCalledWith(
        'item_updated',
        eventData
      )
    })

    it('handles user presence events', () => {
      const userJoinedHandler = mockSocket.on.mock.calls.find(
        call => call[0] === 'user_joined'
      )?.[1]

      const userData = {
        userId: 'user-1',
        username: 'John Doe',
        avatarUrl: 'https://example.com/avatar.jpg',
      }

      // Mock window.dispatchEvent
      const dispatchEventSpy = jest.spyOn(window, 'dispatchEvent')

      userJoinedHandler?.(userData)

      expect(dispatchEventSpy).toHaveBeenCalledWith(
        expect.objectContaining({
          type: 'presence_update',
          detail: expect.arrayContaining([userData]),
        })
      )

      dispatchEventSpy.mockRestore()
    })
  })

  describe('presence management', () => {
    it('tracks user presence', () => {
      const service = webSocketService

      // Simulate user joined event
      const userJoinedHandler = mockSocket.on.mock.calls.find(
        call => call[0] === 'user_joined'
      )?.[1]

      const userData = {
        userId: 'user-1',
        username: 'John Doe',
      }

      userJoinedHandler?.(userData)

      const presenceUsers = service.getPresenceUsers()
      expect(presenceUsers).toContain(userData)
    })

    it('removes user presence on leave', () => {
      const service = webSocketService

      // Add user first
      const userJoinedHandler = mockSocket.on.mock.calls.find(
        call => call[0] === 'user_joined'
      )?.[1]

      userJoinedHandler?.({ userId: 'user-1', username: 'John' })

      // Remove user
      const userLeftHandler = mockSocket.on.mock.calls.find(
        call => call[0] === 'user_left'
      )?.[1]

      userLeftHandler?.({ userId: 'user-1' })

      const presenceUsers = service.getPresenceUsers()
      expect(presenceUsers).toHaveLength(0)
    })
  })

  describe('connection status', () => {
    it('returns connection status', () => {
      expect(webSocketService.isConnected()).toBe(true)
    })

    it('handles disconnect', () => {
      const disconnectHandler = mockSocket.on.mock.calls.find(
        call => call[0] === 'disconnect'
      )?.[1]

      disconnectHandler?.('transport close')

      // Connection status should be updated
      expect(webSocketService.isConnected()).toBe(false)
    })
  })

  describe('message sending', () => {
    it('sends custom messages', () => {
      webSocketService.sendMessage('board:board-1', 'custom_event', {
        data: 'test',
      })

      expect(mockSocket.emit).toHaveBeenCalledWith('message', {
        channel: 'board:board-1',
        type: 'custom_event',
        data: { data: 'test' },
        timestamp: expect.any(String),
      })
    })
  })

  describe('cleanup', () => {
    it('disconnects and cleans up', () => {
      webSocketService.disconnect()

      expect(mockSocket.disconnect).toHaveBeenCalled()
      expect(webSocketService.isConnected()).toBe(false)
      expect(webSocketService.getPresenceUsers()).toHaveLength(0)
    })
  })
})