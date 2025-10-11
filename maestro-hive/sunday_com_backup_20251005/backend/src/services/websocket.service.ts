import { Server as SocketIOServer, Socket } from 'socket.io';
import jwt from 'jsonwebtoken';
import { prisma } from '@/config/database';
import { Logger } from '@/config/logger';
import { config } from '@/config';
import { CollaborationService } from './collaboration.service';
import { JwtPayload } from '@/types';

interface AuthenticatedSocket extends Socket {
  userId?: string;
  userEmail?: string;
  userName?: string;
  organizationId?: string;
}

interface SocketData {
  userId: string;
  userEmail: string;
  userName: string;
  organizationId: string;
}

export class WebSocketService {
  private static io: SocketIOServer;
  private static connectedUsers = new Map<string, AuthenticatedSocket>();

  /**
   * Initialize WebSocket service with Socket.IO server
   */
  static initialize(io: SocketIOServer): void {
    this.io = io;
    this.setupMiddleware();
    this.setupEventHandlers();
    Logger.websocket('WebSocket service initialized');
  }

  /**
   * Setup authentication and other middleware
   */
  private static setupMiddleware(): void {
    // Authentication middleware
    this.io.use(async (socket: AuthenticatedSocket, next) => {
      try {
        const token = socket.handshake.auth.token ||
          socket.handshake.headers.authorization?.replace('Bearer ', '');

        if (!token) {
          return next(new Error('Authentication token required'));
        }

        // Verify JWT token
        const decoded = jwt.verify(token, config.security.jwtSecret) as JwtPayload;

        // Get user details from database
        const user = await prisma.user.findUnique({
          where: { id: decoded.sub },
          select: {
            id: true,
            email: true,
            firstName: true,
            lastName: true,
            organizations: {
              select: {
                organizationId: true,
                role: true,
              },
              take: 1, // Get primary organization
            },
          },
        });

        if (!user) {
          return next(new Error('User not found'));
        }

        // Attach user data to socket
        socket.userId = user.id;
        socket.userEmail = user.email;
        socket.userName = `${user.firstName} ${user.lastName}`.trim();
        socket.organizationId = user.organizations[0]?.organizationId;

        Logger.websocket(`WebSocket authenticated: ${user.email} (${socket.id})`);
        next();
      } catch (error) {
        Logger.error('WebSocket authentication failed', error as Error);
        next(new Error('Authentication failed'));
      }
    });

    // Rate limiting middleware
    this.io.use((socket, next) => {
      // Add rate limiting logic here if needed
      next();
    });
  }

  /**
   * Setup WebSocket event handlers
   */
  private static setupEventHandlers(): void {
    this.io.on('connection', (socket: AuthenticatedSocket) => {
      this.handleConnection(socket);
    });
  }

  /**
   * Handle new WebSocket connection
   */
  private static handleConnection(socket: AuthenticatedSocket): void {
    Logger.websocket(`Client connected: ${socket.userEmail} (${socket.id})`);

    // Store connection
    if (socket.userId) {
      this.connectedUsers.set(socket.userId, socket);
    }

    // Setup connection-specific event handlers
    this.setupSocketEventHandlers(socket);

    // Handle disconnection
    socket.on('disconnect', (reason) => {
      this.handleDisconnection(socket, reason);
    });
  }

  /**
   * Setup event handlers for a specific socket
   */
  private static setupSocketEventHandlers(socket: AuthenticatedSocket): void {
    // Board subscription management
    socket.on('join_board', async (data: { boardId: string }) => {
      await this.handleJoinBoard(socket, data.boardId);
    });

    socket.on('leave_board', async (data: { boardId: string }) => {
      await this.handleLeaveBoard(socket, data.boardId);
    });

    // Item subscription management
    socket.on('join_item', (data: { itemId: string }) => {
      this.handleJoinItem(socket, data.itemId);
    });

    socket.on('leave_item', (data: { itemId: string }) => {
      this.handleLeaveItem(socket, data.itemId);
    });

    // Collaboration features
    socket.on('cursor_move', (data: { boardId: string; cursor: { x: number; y: number } }) => {
      this.handleCursorMove(socket, data);
    });

    socket.on('typing_start', (data: { itemId: string }) => {
      this.handleTypingStart(socket, data.itemId);
    });

    socket.on('typing_stop', (data: { itemId: string }) => {
      this.handleTypingStop(socket, data.itemId);
    });

    // Item editing locks
    socket.on('lock_item', async (data: { itemId: string }) => {
      await this.handleItemLock(socket, data.itemId);
    });

    socket.on('unlock_item', async (data: { itemId: string }) => {
      await this.handleItemUnlock(socket, data.itemId);
    });

    // Activity tracking
    socket.on('track_activity', (data: {
      boardId: string;
      action: string;
      itemId?: string;
      data?: Record<string, any>
    }) => {
      this.handleActivityTracking(socket, data);
    });

    // Ping/Pong for connection health
    socket.on('ping', () => {
      socket.emit('pong', { timestamp: Date.now() });
    });

    // Error handling
    socket.on('error', (error) => {
      Logger.error('WebSocket client error', error);
    });
  }

  /**
   * Handle joining a board
   */
  private static async handleJoinBoard(socket: AuthenticatedSocket, boardId: string): Promise<void> {
    try {
      if (!socket.userId || !socket.userName) {
        socket.emit('error', { message: 'User not authenticated' });
        return;
      }

      // Check if user has access to the board
      const hasAccess = await this.checkBoardAccess(boardId, socket.userId);
      if (!hasAccess) {
        socket.emit('error', { message: 'Access denied to board' });
        return;
      }

      const roomName = `board:${boardId}`;
      socket.join(roomName);

      // Track user presence
      await CollaborationService.trackPresence(
        socket.userId,
        socket.userName,
        boardId,
        socket.id,
        undefined // avatarUrl - could be added from user data
      );

      socket.emit('board_joined', {
        boardId,
        joinedAt: new Date().toISOString(),
      });

      Logger.websocket(`User ${socket.userEmail} joined board ${boardId}`);
    } catch (error) {
      Logger.error('Failed to join board', error as Error);
      socket.emit('error', { message: 'Failed to join board' });
    }
  }

  /**
   * Handle leaving a board
   */
  private static async handleLeaveBoard(socket: AuthenticatedSocket, boardId: string): Promise<void> {
    try {
      if (!socket.userId) return;

      const roomName = `board:${boardId}`;
      socket.leave(roomName);

      // Remove user presence
      await CollaborationService.removePresence(socket.userId, boardId, socket.id);

      socket.emit('board_left', {
        boardId,
        leftAt: new Date().toISOString(),
      });

      Logger.websocket(`User ${socket.userEmail} left board ${boardId}`);
    } catch (error) {
      Logger.error('Failed to leave board', error as Error);
    }
  }

  /**
   * Handle joining an item for detailed updates
   */
  private static handleJoinItem(socket: AuthenticatedSocket, itemId: string): void {
    const roomName = `item:${itemId}`;
    socket.join(roomName);

    socket.emit('item_joined', {
      itemId,
      joinedAt: new Date().toISOString(),
    });

    Logger.websocket(`User ${socket.userEmail} joined item ${itemId}`);
  }

  /**
   * Handle leaving an item
   */
  private static handleLeaveItem(socket: AuthenticatedSocket, itemId: string): void {
    const roomName = `item:${itemId}`;
    socket.leave(roomName);

    socket.emit('item_left', {
      itemId,
      leftAt: new Date().toISOString(),
    });

    Logger.websocket(`User ${socket.userEmail} left item ${itemId}`);
  }

  /**
   * Handle cursor movement
   */
  private static async handleCursorMove(
    socket: AuthenticatedSocket,
    data: { boardId: string; cursor: { x: number; y: number } }
  ): Promise<void> {
    try {
      if (!socket.userId) return;

      await CollaborationService.updateCursor(
        socket.userId,
        data.boardId,
        data.cursor
      );

      // Broadcast to other users in the board (excluding sender)
      socket.to(`board:${data.boardId}`).emit('cursor_updated', {
        userId: socket.userId,
        userName: socket.userName,
        cursor: data.cursor,
        timestamp: new Date().toISOString(),
      });
    } catch (error) {
      Logger.error('Failed to handle cursor move', error as Error);
    }
  }

  /**
   * Handle typing start
   */
  private static async handleTypingStart(socket: AuthenticatedSocket, itemId: string): Promise<void> {
    try {
      if (!socket.userId || !socket.userName) return;

      await CollaborationService.handleTyping(socket.userId, socket.userName, itemId, true);

      // Broadcast to other users watching this item
      socket.to(`item:${itemId}`).emit('user_typing', {
        userId: socket.userId,
        userName: socket.userName,
        isTyping: true,
        itemId,
      });
    } catch (error) {
      Logger.error('Failed to handle typing start', error as Error);
    }
  }

  /**
   * Handle typing stop
   */
  private static async handleTypingStop(socket: AuthenticatedSocket, itemId: string): Promise<void> {
    try {
      if (!socket.userId || !socket.userName) return;

      await CollaborationService.handleTyping(socket.userId, socket.userName, itemId, false);

      // Broadcast to other users watching this item
      socket.to(`item:${itemId}`).emit('user_typing', {
        userId: socket.userId,
        userName: socket.userName,
        isTyping: false,
        itemId,
      });
    } catch (error) {
      Logger.error('Failed to handle typing stop', error as Error);
    }
  }

  /**
   * Handle item lock request
   */
  private static async handleItemLock(socket: AuthenticatedSocket, itemId: string): Promise<void> {
    try {
      if (!socket.userId || !socket.userName) {
        socket.emit('error', { message: 'User not authenticated' });
        return;
      }

      const lockResult = await CollaborationService.lockItem(
        itemId,
        socket.userId,
        socket.userName
      );

      if (lockResult.success) {
        socket.emit('item_locked', {
          itemId,
          lockedBy: socket.userId,
          lockedAt: new Date().toISOString(),
        });

        // Notify other users that the item is locked
        socket.to(`item:${itemId}`).emit('item_lock_changed', {
          itemId,
          isLocked: true,
          lockedBy: {
            id: socket.userId,
            name: socket.userName,
          },
        });
      } else {
        socket.emit('item_lock_failed', {
          itemId,
          reason: lockResult.lockedBy ? `Item is locked by ${lockResult.lockedBy}` : 'Lock failed',
        });
      }
    } catch (error) {
      Logger.error('Failed to handle item lock', error as Error);
      socket.emit('error', { message: 'Failed to lock item' });
    }
  }

  /**
   * Handle item unlock request
   */
  private static async handleItemUnlock(socket: AuthenticatedSocket, itemId: string): Promise<void> {
    try {
      if (!socket.userId) {
        socket.emit('error', { message: 'User not authenticated' });
        return;
      }

      const unlocked = await CollaborationService.unlockItem(itemId, socket.userId);

      if (unlocked) {
        socket.emit('item_unlocked', {
          itemId,
          unlockedAt: new Date().toISOString(),
        });

        // Notify other users that the item is unlocked
        socket.to(`item:${itemId}`).emit('item_lock_changed', {
          itemId,
          isLocked: false,
        });
      } else {
        socket.emit('item_unlock_failed', {
          itemId,
          reason: 'You do not have permission to unlock this item',
        });
      }
    } catch (error) {
      Logger.error('Failed to handle item unlock', error as Error);
      socket.emit('error', { message: 'Failed to unlock item' });
    }
  }

  /**
   * Handle activity tracking
   */
  private static async handleActivityTracking(
    socket: AuthenticatedSocket,
    data: { boardId: string; action: string; itemId?: string; data?: Record<string, any> }
  ): Promise<void> {
    try {
      if (!socket.userId) return;

      await CollaborationService.trackActivity(
        socket.userId,
        data.boardId,
        data.action,
        data.data,
        data.itemId
      );
    } catch (error) {
      Logger.error('Failed to track activity', error as Error);
    }
  }

  /**
   * Handle disconnection
   */
  private static async handleDisconnection(socket: AuthenticatedSocket, reason: string): Promise<void> {
    Logger.websocket(`Client disconnected: ${socket.userEmail} (${socket.id}), reason: ${reason}`);

    if (socket.userId) {
      // Remove from connected users
      this.connectedUsers.delete(socket.userId);

      // Clean up collaboration data
      await CollaborationService.handleDisconnection(socket.id);
    }
  }

  /**
   * Check if user has access to a board
   */
  private static async checkBoardAccess(boardId: string, userId: string): Promise<boolean> {
    try {
      const { BoardService } = await import('./board.service');
      return await BoardService.hasReadAccess(boardId, userId);
    } catch (error) {
      Logger.error('Failed to check board access', error as Error);
      return false;
    }
  }

  // ============================================================================
  // PUBLIC METHODS FOR OTHER SERVICES
  // ============================================================================

  /**
   * Send notification to a specific user
   */
  static sendToUser(userId: string, event: string, data: any): void {
    const socket = this.connectedUsers.get(userId);
    if (socket) {
      socket.emit(event, data);
    }
  }

  /**
   * Send notification to all users in a room
   */
  static sendToRoom(room: string, event: string, data: any): void {
    if (this.io) {
      this.io.to(room).emit(event, data);
    }
  }

  /**
   * Send notification to all users in a board
   */
  static sendToBoard(boardId: string, event: string, data: any): void {
    this.sendToRoom(`board:${boardId}`, event, data);
  }

  /**
   * Send notification to all users watching an item
   */
  static sendToItem(itemId: string, event: string, data: any): void {
    this.sendToRoom(`item:${itemId}`, event, data);
  }

  /**
   * Get connected user count
   */
  static getConnectedUserCount(): number {
    return this.connectedUsers.size;
  }

  /**
   * Get connected users for a specific room
   */
  static async getConnectedUsersInRoom(room: string): Promise<string[]> {
    if (!this.io) return [];

    try {
      const sockets = await this.io.in(room).fetchSockets();
      return sockets
        .map(socket => (socket as AuthenticatedSocket).userId)
        .filter(Boolean) as string[];
    } catch (error) {
      Logger.error('Failed to get connected users in room', error as Error);
      return [];
    }
  }

  /**
   * Check if a user is currently connected
   */
  static isUserConnected(userId: string): boolean {
    return this.connectedUsers.has(userId);
  }

  /**
   * Get the Socket.IO server instance
   */
  static getIO(): SocketIOServer {
    return this.io;
  }
}