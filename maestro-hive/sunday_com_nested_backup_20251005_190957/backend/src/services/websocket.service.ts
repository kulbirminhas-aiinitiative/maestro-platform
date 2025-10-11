import { Server as SocketIOServer, Socket } from 'socket.io';
import { Logger } from '@/config/logger';
import { CollaborationService } from './collaboration.service';
import { EnhancedCollaborationService } from './collaboration-enhanced.service';
import { prisma } from '@/config/database';
import { verify } from 'jsonwebtoken';
import { config } from '@/config';

interface AuthenticatedSocket extends Socket {
  userId?: string;
  user?: {
    id: string;
    email: string;
    firstName?: string;
    lastName?: string;
    avatarUrl?: string;
  };
  currentBoardId?: string;
}

interface SocketUser {
  id: string;
  email: string;
  firstName?: string;
  lastName?: string;
  avatarUrl?: string;
}

export class WebSocketService {
  private static io: SocketIOServer;

  /**
   * Initialize WebSocket service
   */
  static initialize(io: SocketIOServer): void {
    this.io = io;

    // Authentication middleware
    io.use(async (socket: AuthenticatedSocket, next) => {
      try {
        const token = socket.handshake.auth.token;

        if (!token) {
          return next(new Error('Authentication token required'));
        }

        // Verify JWT token
        const decoded = verify(token, config.jwt.secret) as any;

        // Get user from database
        const user = await prisma.user.findUnique({
          where: { id: decoded.sub },
          select: {
            id: true,
            email: true,
            firstName: true,
            lastName: true,
            avatarUrl: true,
          },
        });

        if (!user) {
          return next(new Error('User not found'));
        }

        socket.userId = user.id;
        socket.user = user;

        Logger.websocket(`User ${user.email} connected with socket ${socket.id}`);
        next();
      } catch (error) {
        Logger.error('WebSocket authentication failed', error as Error);
        next(new Error('Authentication failed'));
      }
    });

    // Connection handling
    io.on('connection', (socket: AuthenticatedSocket) => {
      this.handleConnection(socket);
    });

    Logger.api('WebSocket service initialized');
  }

  /**
   * Handle new socket connection
   */
  private static handleConnection(socket: AuthenticatedSocket): void {
    const user = socket.user!;

    Logger.websocket(`User ${user.email} connected`);

    // ========================================================================
    // BOARD EVENTS
    // ========================================================================

    /**
     * Join board room for real-time updates
     */
    socket.on('join_board', async (data: { boardId: string }) => {
      try {
        const { boardId } = data;

        // Verify user has access to board
        const hasAccess = await this.verifyBoardAccess(user.id, boardId);
        if (!hasAccess) {
          socket.emit('error', { message: 'Access denied to board' });
          return;
        }

        // Leave previous board room if any
        if (socket.currentBoardId) {
          await this.handleLeaveBoardCleanup(socket, socket.currentBoardId);
        }

        // Join new board room
        socket.join(`board:${boardId}`);
        socket.currentBoardId = boardId;

        // Track presence
        await EnhancedCollaborationService.trackPresence(
          user.id,
          `${user.firstName || ''} ${user.lastName || ''}`.trim() || user.email,
          boardId,
          socket.id,
          user.avatarUrl
        );

        socket.emit('board_joined', { boardId, timestamp: new Date() });

        Logger.websocket(`User ${user.email} joined board ${boardId}`);
      } catch (error) {
        Logger.error('Failed to join board', error as Error);
        socket.emit('error', { message: 'Failed to join board' });
      }
    });

    /**
     * Leave board room
     */
    socket.on('leave_board', async (data: { boardId: string }) => {
      try {
        const { boardId } = data;
        await this.handleLeaveBoardCleanup(socket, boardId);
        socket.emit('board_left', { boardId, timestamp: new Date() });
      } catch (error) {
        Logger.error('Failed to leave board', error as Error);
      }
    });

    // ========================================================================
    // ITEM EVENTS
    // ========================================================================

    /**
     * Join item room for detailed collaboration
     */
    socket.on('join_item', async (data: { itemId: string }) => {
      try {
        const { itemId } = data;

        // Verify access to item
        const hasAccess = await this.verifyItemAccess(user.id, itemId);
        if (!hasAccess) {
          socket.emit('error', { message: 'Access denied to item' });
          return;
        }

        socket.join(`item:${itemId}`);
        socket.emit('item_joined', { itemId, timestamp: new Date() });

        Logger.websocket(`User ${user.email} joined item ${itemId}`);
      } catch (error) {
        Logger.error('Failed to join item', error as Error);
        socket.emit('error', { message: 'Failed to join item' });
      }
    });

    /**
     * Leave item room
     */
    socket.on('leave_item', async (data: { itemId: string }) => {
      try {
        const { itemId } = data;
        socket.leave(`item:${itemId}`);
        socket.emit('item_left', { itemId, timestamp: new Date() });
      } catch (error) {
        Logger.error('Failed to leave item', error as Error);
      }
    });

    // ========================================================================
    // COLLABORATION EVENTS
    // ========================================================================

    /**
     * Update cursor position
     */
    socket.on('cursor_update', async (data: {
      boardId: string;
      x: number;
      y: number;
      itemId?: string;
      field?: string;
      selection?: { start: number; end: number };
    }) => {
      try {
        await EnhancedCollaborationService.updateCursorAdvanced(
          user.id,
          data.boardId,
          {
            x: data.x,
            y: data.y,
            itemId: data.itemId,
            field: data.field,
            selection: data.selection,
          }
        );
      } catch (error) {
        Logger.error('Failed to update cursor', error as Error);
      }
    });

    /**
     * Lock item field for editing
     */
    socket.on('lock_field', async (data: {
      itemId: string;
      field: string;
      duration?: number;
    }) => {
      try {
        const result = await EnhancedCollaborationService.lockItemField(
          data.itemId,
          data.field,
          user.id,
          `${user.firstName || ''} ${user.lastName || ''}`.trim() || user.email,
          data.duration
        );

        socket.emit('lock_result', {
          itemId: data.itemId,
          field: data.field,
          success: result.success,
          lockedBy: result.lockedBy,
          timestamp: new Date(),
        });
      } catch (error) {
        Logger.error('Failed to lock field', error as Error);
        socket.emit('error', { message: 'Failed to lock field' });
      }
    });

    /**
     * Release item field lock
     */
    socket.on('unlock_field', async (data: {
      itemId: string;
      field: string;
    }) => {
      try {
        const released = await EnhancedCollaborationService.unlockItemField(
          data.itemId,
          data.field,
          user.id
        );

        socket.emit('unlock_result', {
          itemId: data.itemId,
          field: data.field,
          success: released,
          timestamp: new Date(),
        });
      } catch (error) {
        Logger.error('Failed to unlock field', error as Error);
        socket.emit('error', { message: 'Failed to unlock field' });
      }
    });

    /**
     * Handle typing indicators
     */
    socket.on('typing', async (data: {
      itemId: string;
      isTyping: boolean;
    }) => {
      try {
        await CollaborationService.handleTyping(
          user.id,
          `${user.firstName || ''} ${user.lastName || ''}`.trim() || user.email,
          data.itemId,
          data.isTyping
        );
      } catch (error) {
        Logger.error('Failed to handle typing', error as Error);
      }
    });

    /**
     * Process collaborative operation
     */
    socket.on('operation', async (data: {
      id: string;
      type: 'insert' | 'delete' | 'retain' | 'update';
      itemId: string;
      field: string;
      position?: number;
      content?: string;
      length?: number;
      clientId: string;
    }) => {
      try {
        const operation = {
          ...data,
          userId: user.id,
          timestamp: new Date(),
        };

        const result = await EnhancedCollaborationService.processOperation(operation);

        socket.emit('operation_result', {
          operationId: data.id,
          success: result.success,
          transformedOperation: result.transformedOperation,
          conflicts: result.conflicts,
          timestamp: new Date(),
        });
      } catch (error) {
        Logger.error('Failed to process operation', error as Error);
        socket.emit('error', { message: 'Failed to process operation' });
      }
    });

    // ========================================================================
    // ACTIVITY TRACKING
    // ========================================================================

    /**
     * Track user activity
     */
    socket.on('activity', async (data: {
      boardId: string;
      action: string;
      itemId?: string;
      data?: Record<string, any>;
    }) => {
      try {
        await CollaborationService.trackActivity(
          user.id,
          data.boardId,
          data.action,
          data.data,
          data.itemId
        );
      } catch (error) {
        Logger.error('Failed to track activity', error as Error);
      }
    });

    // ========================================================================
    // PRESENCE MANAGEMENT
    // ========================================================================

    /**
     * Update user state
     */
    socket.on('update_state', async (data: {
      boardId: string;
      userState: Record<string, any>;
    }) => {
      try {
        await EnhancedCollaborationService.trackPresence(
          user.id,
          `${user.firstName || ''} ${user.lastName || ''}`.trim() || user.email,
          data.boardId,
          socket.id,
          user.avatarUrl,
          data.userState
        );
      } catch (error) {
        Logger.error('Failed to update user state', error as Error);
      }
    });

    // ========================================================================
    // DISCONNECT HANDLING
    // ========================================================================

    /**
     * Handle socket disconnection
     */
    socket.on('disconnect', async (reason) => {
      try {
        Logger.websocket(`User ${user.email} disconnected: ${reason}`);

        // Cleanup presence and locks
        if (socket.currentBoardId) {
          await this.handleLeaveBoardCleanup(socket, socket.currentBoardId);
        }

        // Release all user locks
        await EnhancedCollaborationService.releaseUserLocks(user.id);

        // Cleanup socket tracking
        await CollaborationService.handleDisconnection(socket.id);
      } catch (error) {
        Logger.error('Failed to handle disconnect cleanup', error as Error);
      }
    });

    // ========================================================================
    // ERROR HANDLING
    // ========================================================================

    socket.on('error', (error) => {
      Logger.error('Socket error', error);
    });
  }

  /**
   * Handle leaving board cleanup
   */
  private static async handleLeaveBoardCleanup(
    socket: AuthenticatedSocket,
    boardId: string
  ): Promise<void> {
    try {
      socket.leave(`board:${boardId}`);

      if (socket.userId) {
        await CollaborationService.removePresence(socket.userId, boardId, socket.id);
      }

      socket.currentBoardId = undefined;
    } catch (error) {
      Logger.error('Failed to cleanup board leave', error as Error);
    }
  }

  /**
   * Verify user has access to board
   */
  private static async verifyBoardAccess(userId: string, boardId: string): Promise<boolean> {
    try {
      const board = await prisma.board.findFirst({
        where: {
          id: boardId,
          deletedAt: null,
          OR: [
            { isPrivate: false },
            {
              members: {
                some: { userId },
              },
            },
            {
              workspace: {
                members: {
                  some: { userId },
                },
              },
            },
          ],
        },
      });

      return !!board;
    } catch (error) {
      Logger.error('Failed to verify board access', error as Error);
      return false;
    }
  }

  /**
   * Verify user has access to item
   */
  private static async verifyItemAccess(userId: string, itemId: string): Promise<boolean> {
    try {
      const item = await prisma.item.findFirst({
        where: {
          id: itemId,
          deletedAt: null,
          board: {
            OR: [
              { isPrivate: false },
              {
                members: {
                  some: { userId },
                },
              },
              {
                workspace: {
                  members: {
                    some: { userId },
                  },
                },
              },
            ],
          },
        },
      });

      return !!item;
    } catch (error) {
      Logger.error('Failed to verify item access', error as Error);
      return false;
    }
  }

  /**
   * Broadcast message to board members
   */
  static broadcastToBoard(boardId: string, event: string, data: any, excludeSocketId?: string): void {
    try {
      if (excludeSocketId) {
        this.io.to(`board:${boardId}`).except(excludeSocketId).emit(event, {
          ...data,
          timestamp: new Date(),
        });
      } else {
        this.io.to(`board:${boardId}`).emit(event, {
          ...data,
          timestamp: new Date(),
        });
      }
    } catch (error) {
      Logger.error('Failed to broadcast to board', error as Error);
    }
  }

  /**
   * Broadcast message to item subscribers
   */
  static broadcastToItem(itemId: string, event: string, data: any, excludeSocketId?: string): void {
    try {
      if (excludeSocketId) {
        this.io.to(`item:${itemId}`).except(excludeSocketId).emit(event, {
          ...data,
          timestamp: new Date(),
        });
      } else {
        this.io.to(`item:${itemId}`).emit(event, {
          ...data,
          timestamp: new Date(),
        });
      }
    } catch (error) {
      Logger.error('Failed to broadcast to item', error as Error);
    }
  }

  /**
   * Get connected users count for a board
   */
  static async getBoardUsersCount(boardId: string): Promise<number> {
    try {
      const sockets = await this.io.in(`board:${boardId}`).fetchSockets();
      return sockets.length;
    } catch (error) {
      Logger.error('Failed to get board users count', error as Error);
      return 0;
    }
  }

  /**
   * Send message to specific user
   */
  static async sendToUser(userId: string, event: string, data: any): Promise<boolean> {
    try {
      const sockets = await this.io.fetchSockets();
      const userSocket = sockets.find(socket => (socket as any).userId === userId);

      if (userSocket) {
        userSocket.emit(event, {
          ...data,
          timestamp: new Date(),
        });
        return true;
      }

      return false;
    } catch (error) {
      Logger.error('Failed to send message to user', error as Error);
      return false;
    }
  }

  /**
   * Get online users for a board
   */
  static async getOnlineUsers(boardId: string): Promise<SocketUser[]> {
    try {
      const sockets = await this.io.in(`board:${boardId}`).fetchSockets();
      const users: SocketUser[] = [];

      for (const socket of sockets) {
        const socketUser = (socket as any).user;
        if (socketUser && !users.find(u => u.id === socketUser.id)) {
          users.push(socketUser);
        }
      }

      return users;
    } catch (error) {
      Logger.error('Failed to get online users', error as Error);
      return [];
    }
  }
}