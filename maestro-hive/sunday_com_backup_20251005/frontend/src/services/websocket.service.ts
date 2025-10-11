import { io, Socket } from 'socket.io-client'
import { apiClient } from '@/lib/api'
import { Logger } from '@/lib/logger'
import { useBoardStore } from '@/stores/board.store'
import { useItemStore } from '@/stores/item.store'
import toast from 'react-hot-toast'

interface WebSocketMessage {
  type: string
  channel?: string
  data: any
  timestamp: string
}

interface UserPresence {
  userId: string
  username: string
  avatarUrl?: string
  cursor?: {
    x: number
    y: number
  }
  lastSeen: string
}

class WebSocketService {
  private socket: Socket | null = null
  private connected = false
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private presenceUsers = new Map<string, UserPresence>()
  private currentBoardId: string | null = null
  private currentWorkspaceId: string | null = null

  constructor() {
    this.connect()
  }

  private connect() {
    const token = apiClient.getToken()
    if (!token) {
      Logger.warn('No auth token available for WebSocket connection')
      return
    }

    const wsUrl = process.env.REACT_APP_WS_URL || process.env.VITE_WS_URL || 'ws://localhost:3001'
    Logger.info('Establishing WebSocket connection to:', wsUrl)

    this.socket = io(wsUrl, {
      auth: {
        token,
      },
      transports: ['websocket', 'polling'],
      timeout: 10000,
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: this.reconnectDelay,
      forceNew: false,
    })

    this.setupEventListeners()
  }

  private setupEventListeners() {
    if (!this.socket) return

    this.socket.on('connect', () => {
      Logger.info('WebSocket connected successfully')
      this.connected = true
      this.reconnectAttempts = 0

      // Rejoin channels if we were in any
      if (this.currentBoardId) {
        this.joinBoard(this.currentBoardId)
      }
      if (this.currentWorkspaceId) {
        this.joinWorkspace(this.currentWorkspaceId)
      }

      // Notify user of reconnection if this wasn't the initial connection
      if (this.reconnectAttempts > 0) {
        toast.success('Reconnected to real-time updates')
      }
    })

    this.socket.on('disconnect', (reason) => {
      Logger.warn('WebSocket disconnected:', reason)
      this.connected = false
      this.presenceUsers.clear()

      // Show user-friendly message for disconnect
      if (reason === 'io server disconnect') {
        toast.error('Connection lost. Attempting to reconnect...')
        this.handleReconnect()
      } else if (reason === 'transport close' || reason === 'transport error') {
        toast.error('Network issue detected. Reconnecting...')
      }
    })

    this.socket.on('connect_error', (error) => {
      Logger.error('WebSocket connection error:', error)
      this.handleReconnect()
    })

    this.socket.on('reconnect', (attemptNumber) => {
      Logger.info(`WebSocket reconnected after ${attemptNumber} attempts`)
      toast.success('Reconnected successfully!')
    })

    this.socket.on('reconnect_error', (error) => {
      Logger.error('WebSocket reconnection failed:', error)
    })

    this.socket.on('reconnect_failed', () => {
      Logger.error('WebSocket reconnection failed permanently')
      toast.error('Unable to reconnect. Please refresh the page.')
    })

    // Board events
    this.socket.on('board_created', this.handleBoardCreated.bind(this))
    this.socket.on('board_updated', this.handleBoardUpdated.bind(this))
    this.socket.on('board_deleted', this.handleBoardDeleted.bind(this))

    // Column events
    this.socket.on('column_created', this.handleColumnCreated.bind(this))
    this.socket.on('column_updated', this.handleColumnUpdated.bind(this))
    this.socket.on('column_deleted', this.handleColumnDeleted.bind(this))

    // Item events
    this.socket.on('item_created', this.handleItemCreated.bind(this))
    this.socket.on('item_updated', this.handleItemUpdated.bind(this))
    this.socket.on('item_deleted', this.handleItemDeleted.bind(this))

    // Member events
    this.socket.on('member_added', this.handleMemberAdded.bind(this))
    this.socket.on('member_removed', this.handleMemberRemoved.bind(this))
    this.socket.on('member_updated', this.handleMemberUpdated.bind(this))

    // Presence events
    this.socket.on('user_joined', this.handleUserJoined.bind(this))
    this.socket.on('user_left', this.handleUserLeft.bind(this))
    this.socket.on('user_presence_updated', this.handlePresenceUpdated.bind(this))

    // Cursor events
    this.socket.on('cursor_moved', this.handleCursorMoved.bind(this))

    // Error events
    this.socket.on('error', (error) => {
      console.error('WebSocket error:', error)
      toast.error('Real-time connection error')
    })

    // Custom message events
    this.socket.on('message', this.handleMessage.bind(this))
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)

      Logger.info(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`)

      setTimeout(() => {
        this.connect()
      }, delay)
    } else {
      Logger.error('Max reconnection attempts reached')
      toast.error('Lost real-time connection. Please refresh the page.')
    }
  }

  // Channel management
  joinWorkspace(workspaceId: string) {
    if (!this.socket || !this.connected) {
      Logger.warn('Cannot join workspace: WebSocket not connected')
      return
    }

    this.currentWorkspaceId = workspaceId
    this.socket.emit('join_workspace', { workspaceId })
    Logger.info(`Joined workspace: ${workspaceId}`)
  }

  leaveWorkspace(workspaceId: string) {
    if (!this.socket || !this.connected) return

    this.socket.emit('leave_workspace', { workspaceId })
    if (this.currentWorkspaceId === workspaceId) {
      this.currentWorkspaceId = null
    }
    Logger.info(`Left workspace: ${workspaceId}`)
  }

  joinBoard(boardId: string) {
    if (!this.socket || !this.connected) {
      Logger.warn('Cannot join board: WebSocket not connected')
      return
    }

    // Leave current board if switching
    if (this.currentBoardId && this.currentBoardId !== boardId) {
      this.leaveBoard(this.currentBoardId)
    }

    this.currentBoardId = boardId
    this.socket.emit('join_board', { boardId })
    Logger.info(`Joined board: ${boardId}`)

    // Clear presence data when switching boards
    this.presenceUsers.clear()
  }

  leaveBoard(boardId: string) {
    if (!this.socket || !this.connected) return

    this.socket.emit('leave_board', { boardId })
    if (this.currentBoardId === boardId) {
      this.currentBoardId = null
      this.presenceUsers.clear()
    }
    Logger.info(`Left board: ${boardId}`)
  }

  // Presence and cursor tracking
  updateCursor(x: number, y: number, boardId?: string) {
    if (!this.socket || !this.connected) return

    this.socket.emit('cursor_move', {
      x,
      y,
      boardId: boardId || this.currentBoardId,
      timestamp: new Date().toISOString(),
    })
  }

  updatePresence(data: Partial<UserPresence>) {
    if (!this.socket || !this.connected) return

    this.socket.emit('presence_update', {
      ...data,
      boardId: this.currentBoardId,
      timestamp: new Date().toISOString(),
    })
  }

  // Event handlers
  private handleBoardCreated(data: any) {
    console.log('Board created:', data)
    useBoardStore.getState().handleRealTimeUpdate('board_created', data)

    if (data.user?.id !== this.getCurrentUserId()) {
      toast.success(`${data.user?.name} created a new board: ${data.board?.name}`)
    }
  }

  private handleBoardUpdated(data: any) {
    console.log('Board updated:', data)
    useBoardStore.getState().handleRealTimeUpdate('board_updated', data)

    if (data.updatedBy !== this.getCurrentUserId()) {
      toast.info('Board was updated by another user')
    }
  }

  private handleBoardDeleted(data: any) {
    console.log('Board deleted:', data)
    useBoardStore.getState().handleRealTimeUpdate('board_deleted', data)

    if (data.deletedBy !== this.getCurrentUserId()) {
      toast.error('Board was deleted by another user')
    }
  }

  private handleColumnCreated(data: any) {
    console.log('Column created:', data)
    useBoardStore.getState().handleRealTimeUpdate('column_created', data)
  }

  private handleColumnUpdated(data: any) {
    console.log('Column updated:', data)
    useBoardStore.getState().handleRealTimeUpdate('column_updated', data)
  }

  private handleColumnDeleted(data: any) {
    console.log('Column deleted:', data)
    useBoardStore.getState().handleRealTimeUpdate('column_deleted', data)
  }

  private handleItemCreated(data: any) {
    console.log('Item created:', data)
    useItemStore.getState().handleRealTimeUpdate('item_created', data)

    if (data.user?.id !== this.getCurrentUserId()) {
      toast.success(`${data.user?.name} created: ${data.item?.name}`)
    }
  }

  private handleItemUpdated(data: any) {
    console.log('Item updated:', data)
    useItemStore.getState().handleRealTimeUpdate('item_updated', data)

    if (data.updatedBy !== this.getCurrentUserId()) {
      // Show toast for significant changes
      const changes = data.changes || {}
      if (changes.status) {
        toast.info(`Item status changed to ${changes.status.new}`)
      }
    }
  }

  private handleItemDeleted(data: any) {
    console.log('Item deleted:', data)
    useItemStore.getState().handleRealTimeUpdate('item_deleted', data)

    if (data.deletedBy !== this.getCurrentUserId()) {
      toast.info('An item was deleted by another user')
    }
  }

  private handleMemberAdded(data: any) {
    console.log('Member added:', data)
    // Handle member added to board/workspace
  }

  private handleMemberRemoved(data: any) {
    console.log('Member removed:', data)
    // Handle member removed from board/workspace
  }

  private handleMemberUpdated(data: any) {
    console.log('Member updated:', data)
    // Handle member role/permissions updated
  }

  private handleUserJoined(data: any) {
    console.log('User joined:', data)
    this.presenceUsers.set(data.userId, data)
    this.emitPresenceUpdate()
  }

  private handleUserLeft(data: any) {
    console.log('User left:', data)
    this.presenceUsers.delete(data.userId)
    this.emitPresenceUpdate()
  }

  private handlePresenceUpdated(data: any) {
    console.log('Presence updated:', data)
    if (data.userId) {
      this.presenceUsers.set(data.userId, data)
      this.emitPresenceUpdate()
    }
  }

  private handleCursorMoved(data: any) {
    console.log('Cursor moved:', data)
    if (data.userId && data.userId !== this.getCurrentUserId()) {
      // Update cursor position for other users
      this.emitCursorUpdate(data)
    }
  }

  private handleMessage(data: WebSocketMessage) {
    console.log('WebSocket message:', data)
    // Handle custom messages
  }

  // Utility methods
  private getCurrentUserId(): string | null {
    try {
      // Get user ID from auth context or local storage
      const authData = localStorage.getItem('auth_user')
      if (authData) {
        const user = JSON.parse(authData)
        return user.id
      }
      return null
    } catch (error) {
      Logger.error('Failed to get current user ID:', error)
      return null
    }
  }

  private emitPresenceUpdate() {
    // Emit presence update to components that need it
    const presenceArray = Array.from(this.presenceUsers.values())
    window.dispatchEvent(new CustomEvent('presence_update', {
      detail: presenceArray
    }))
  }

  private emitCursorUpdate(data: any) {
    // Emit cursor update to components that need it
    window.dispatchEvent(new CustomEvent('cursor_update', {
      detail: data
    }))
  }

  // Public API
  isConnected(): boolean {
    return this.connected
  }

  getPresenceUsers(): UserPresence[] {
    return Array.from(this.presenceUsers.values())
  }

  sendMessage(channel: string, type: string, data: any) {
    if (!this.socket || !this.connected) return

    this.socket.emit('message', {
      channel,
      type,
      data,
      timestamp: new Date().toISOString(),
    })
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
      this.connected = false
      this.presenceUsers.clear()
    }
  }

  // Mouse tracking for collaborative cursors
  startMouseTracking(boardId: string) {
    if (!this.connected) return

    let lastUpdate = 0
    const throttleDelay = 100 // ms

    const handleMouseMove = (event: MouseEvent) => {
      const now = Date.now()
      if (now - lastUpdate < throttleDelay) return

      lastUpdate = now
      this.updateCursor(event.clientX, event.clientY, boardId)
    }

    document.addEventListener('mousemove', handleMouseMove)

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
    }
  }
}

// Create singleton instance
export const webSocketService = new WebSocketService()

// Export for use in React components
export default webSocketService