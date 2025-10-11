import { useEffect, useState, useCallback } from 'react'
import { webSocketService } from '@/services/websocket.service'
import { Logger } from '@/lib/logger'

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

interface CursorUpdate {
  userId: string
  username: string
  x: number
  y: number
  timestamp: string
}

export const useWebSocket = () => {
  const [isConnected, setIsConnected] = useState(webSocketService.isConnected())
  const [presenceUsers, setPresenceUsers] = useState<UserPresence[]>([])
  const [cursors, setCursors] = useState<Map<string, CursorUpdate>>(new Map())

  useEffect(() => {
    // Listen for presence updates
    const handlePresenceUpdate = (event: CustomEvent) => {
      setPresenceUsers(event.detail)
    }

    // Listen for cursor updates
    const handleCursorUpdate = (event: CustomEvent) => {
      const cursorData = event.detail
      setCursors(prev => new Map(prev.set(cursorData.userId, cursorData)))

      // Remove old cursor after 5 seconds
      setTimeout(() => {
        setCursors(prev => {
          const newMap = new Map(prev)
          newMap.delete(cursorData.userId)
          return newMap
        })
      }, 5000)
    }

    // Listen for connection status changes
    const handleConnectionChange = () => {
      setIsConnected(webSocketService.isConnected())
    }

    window.addEventListener('presence_update', handlePresenceUpdate as EventListener)
    window.addEventListener('cursor_update', handleCursorUpdate as EventListener)
    window.addEventListener('websocket_connected', handleConnectionChange)
    window.addEventListener('websocket_disconnected', handleConnectionChange)

    return () => {
      window.removeEventListener('presence_update', handlePresenceUpdate as EventListener)
      window.removeEventListener('cursor_update', handleCursorUpdate as EventListener)
      window.removeEventListener('websocket_connected', handleConnectionChange)
      window.removeEventListener('websocket_disconnected', handleConnectionChange)
    }
  }, [])

  const joinWorkspace = useCallback((workspaceId: string) => {
    webSocketService.joinWorkspace(workspaceId)
  }, [])

  const leaveWorkspace = useCallback((workspaceId: string) => {
    webSocketService.leaveWorkspace(workspaceId)
  }, [])

  const joinBoard = useCallback((boardId: string) => {
    webSocketService.joinBoard(boardId)
  }, [])

  const leaveBoard = useCallback((boardId: string) => {
    webSocketService.leaveBoard(boardId)
  }, [])

  const sendMessage = useCallback((channel: string, type: string, data: any) => {
    webSocketService.sendMessage(channel, type, data)
  }, [])

  const updateCursor = useCallback((x: number, y: number, boardId?: string) => {
    webSocketService.updateCursor(x, y, boardId)
  }, [])

  const updatePresence = useCallback((data: Partial<UserPresence>) => {
    webSocketService.updatePresence(data)
  }, [])

  return {
    isConnected,
    presenceUsers,
    cursors: Array.from(cursors.values()),
    joinWorkspace,
    leaveWorkspace,
    joinBoard,
    leaveBoard,
    sendMessage,
    updateCursor,
    updatePresence,
  }
}

export const useBoardPresence = (boardId: string) => {
  const { isConnected, presenceUsers, cursors, joinBoard, leaveBoard } = useWebSocket()

  useEffect(() => {
    if (boardId && isConnected) {
      joinBoard(boardId)

      // Start mouse tracking for collaborative cursors
      const stopTracking = webSocketService.startMouseTracking(boardId)

      return () => {
        leaveBoard(boardId)
        stopTracking?.()
      }
    }
  }, [boardId, isConnected, joinBoard, leaveBoard])

  return {
    isConnected,
    presenceUsers,
    cursors,
  }
}

export const useWorkspacePresence = (workspaceId: string) => {
  const { isConnected, presenceUsers, joinWorkspace, leaveWorkspace } = useWebSocket()

  useEffect(() => {
    if (workspaceId && isConnected) {
      joinWorkspace(workspaceId)

      return () => {
        leaveWorkspace(workspaceId)
      }
    }
  }, [workspaceId, isConnected, joinWorkspace, leaveWorkspace])

  return {
    isConnected,
    presenceUsers,
  }
}