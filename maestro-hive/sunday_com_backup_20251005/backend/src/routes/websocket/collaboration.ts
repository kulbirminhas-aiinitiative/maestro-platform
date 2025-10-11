import { Server as SocketIOServer, Socket } from 'socket.io';
import jwt from 'jsonwebtoken';
import { CollaborationService } from '@/services/collaboration.service';
import { Logger } from '@/config/logger';
import { RedisService } from '@/config/redis';

interface AuthenticatedSocket extends Socket {
  user?: {
    id: string;
    email: string;
    firstName: string;
    lastName: string;
    avatarUrl?: string;
  };
  currentBoard?: string;
  deviceInfo?: {
    type: 'desktop' | 'tablet' | 'mobile';
    os: string;
    browser: string;
  };
}

export function setupCollaborationHandlers(io: SocketIOServer) {
  // Authentication middleware
  io.use(async (socket: AuthenticatedSocket, next) => {
    try {
      const token = socket.handshake.auth.token || socket.handshake.headers.authorization?.split(' ')[1];

      if (!token) {
        return next(new Error('Authentication token required'));
      }

      const decoded = jwt.verify(token, process.env.JWT_SECRET!) as any;

      // Get user info from database or cache
      const userInfo = await RedisService.getCache(`user:${decoded.userId}:info`);
      if (!userInfo) {
        return next(new Error('User not found'));
      }

      socket.user = JSON.parse(userInfo);

      // Extract device info from user agent
      const userAgent = socket.handshake.headers['user-agent'] || '';
      socket.deviceInfo = parseUserAgent(userAgent);

      Logger.websocket(`User ${socket.user.email} connected`, {
        socketId: socket.id,
        userId: socket.user.id,
        deviceInfo: socket.deviceInfo,
      });

      next();
    } catch (error) {
      Logger.error('WebSocket authentication failed', error as Error);
      next(new Error('Authentication failed'));
    }
  });

  io.on('connection', (socket: AuthenticatedSocket) => {
    const user = socket.user!;

    // ========================================================================
    // BOARD PRESENCE
    // ========================================================================

    /**
     * Join board room for real-time collaboration
     */
    socket.on('join_board', async (data: { boardId: string; currentView?: any }) => {
      try {
        const { boardId, currentView } = data;

        // Leave previous board if any
        if (socket.currentBoard) {
          await leaveBoard(socket, socket.currentBoard);
        }

        // Join new board room
        socket.join(`board:${boardId}`);
        socket.currentBoard = boardId;

        // Track presence
        await CollaborationService.trackPresence(
          user.id,
          `${user.firstName} ${user.lastName}`.trim(),
          boardId,
          socket.id,
          {
            avatarUrl: user.avatarUrl,
            deviceInfo: socket.deviceInfo,
            currentView,
          }
        );

        socket.emit('board_joined', {
          boardId,
          success: true,
          timestamp: new Date(),
        });

        Logger.websocket(`User ${user.email} joined board ${boardId}`, {
          socketId: socket.id,
          boardId,
        });
      } catch (error) {
        Logger.error('Join board failed', error as Error);
        socket.emit('board_join_error', {
          message: (error as Error).message,
          timestamp: new Date(),
        });
      }
    });

    /**
     * Leave board room
     */
    socket.on('leave_board', async (data: { boardId: string }) => {
      try {
        await leaveBoard(socket, data.boardId);
        socket.emit('board_left', {
          boardId: data.boardId,
          success: true,
          timestamp: new Date(),
        });
      } catch (error) {
        Logger.error('Leave board failed', error as Error);
        socket.emit('error', {
          type: 'leave_board_error',
          message: (error as Error).message,
        });
      }
    });

    // ========================================================================
    // CURSOR TRACKING
    // ========================================================================

    /**
     * Update cursor position
     */
    socket.on('cursor_update', async (data: {
      boardId: string;
      cursor: {
        x: number;
        y: number;
        itemId?: string;
        field?: string;
        selection?: { start: number; end: number };
        elementId?: string;
      };
    }) => {
      try {
        await CollaborationService.updateCursor(
          user.id,
          data.boardId,
          data.cursor,
          socket.id
        );
      } catch (error) {
        Logger.error('Cursor update failed', error as Error);
      }
    });

    /**
     * Request current cursors for board
     */
    socket.on('get_board_cursors', async (data: { boardId: string }) => {
      try {
        const cursors = await CollaborationService.getBoardCursors(data.boardId);
        socket.emit('board_cursors', {
          boardId: data.boardId,
          cursors,
          timestamp: new Date(),
        });
      } catch (error) {
        Logger.error('Get board cursors failed', error as Error);
      }
    });

    // ========================================================================
    // FIELD LOCKING
    // ========================================================================

    /**
     * Lock field for editing
     */
    socket.on('lock_field', async (data: {
      itemId: string;
      field: string;
      duration?: number;
    }) => {
      try {
        const result = await CollaborationService.lockField(
          data.itemId,
          data.field,
          user.id,
          {
            username: `${user.firstName} ${user.lastName}`.trim(),
            userAvatar: user.avatarUrl,
            duration: data.duration,
          }
        );

        socket.emit('field_lock_result', {
          itemId: data.itemId,
          field: data.field,
          result,
          timestamp: new Date(),
        });

        if (result.success) {
          // Join item-specific room for field updates
          socket.join(`item:${data.itemId}`);
        }
      } catch (error) {
        Logger.error('Field lock failed', error as Error);
        socket.emit('field_lock_result', {
          itemId: data.itemId,
          field: data.field,
          result: {
            success: false,
            message: (error as Error).message,
          },
        });
      }
    });

    /**
     * Unlock field
     */
    socket.on('unlock_field', async (data: {
      itemId: string;
      field: string;
      lockId?: string;
    }) => {
      try {
        const result = await CollaborationService.unlockField(
          data.itemId,
          data.field,
          user.id,
          data.lockId
        );

        socket.emit('field_unlock_result', {
          itemId: data.itemId,
          field: data.field,
          result,
          timestamp: new Date(),
        });
      } catch (error) {
        Logger.error('Field unlock failed', error as Error);
        socket.emit('field_unlock_result', {
          itemId: data.itemId,
          field: data.field,
          result: {
            success: false,
            message: (error as Error).message,
          },
        });
      }
    });

    /**
     * Get item locks
     */
    socket.on('get_item_locks', async (data: { itemId: string }) => {
      try {
        const locks = await CollaborationService.getItemLocks(data.itemId);
        socket.emit('item_locks', {
          itemId: data.itemId,
          locks,
          timestamp: new Date(),
        });
      } catch (error) {
        Logger.error('Get item locks failed', error as Error);
      }
    });

    // ========================================================================
    // OPERATIONAL TRANSFORMATION
    // ========================================================================

    /**
     * Process collaborative operation
     */
    socket.on('collaborative_operation', async (data: {
      operation: {
        id: string;
        type: 'insert' | 'delete' | 'retain' | 'update' | 'format';
        itemId: string;
        field: string;
        position?: number;
        content?: string;
        length?: number;
        attributes?: Record<string, any>;
        clientId: string;
        sequenceNumber: number;
      };
    }) => {
      try {
        const operation = {
          ...data.operation,
          userId: user.id,
          timestamp: new Date(),
        };

        const result = await CollaborationService.processOperation(operation);

        socket.emit('operation_result', {
          operationId: operation.id,
          result,
          timestamp: new Date(),
        });

        if (result.success && result.transformedOperation) {
          // Broadcast to other clients on the same item
          socket.to(`item:${operation.itemId}`).emit('operation_applied', {
            operation: result.transformedOperation,
            conflicts: result.conflicts,
            timestamp: new Date(),
          });
        }
      } catch (error) {
        Logger.error('Collaborative operation failed', error as Error);
        socket.emit('operation_result', {
          operationId: data.operation.id,
          result: {
            success: false,
            conflicts: [],
            message: (error as Error).message,
          },
        });
      }
    });

    // ========================================================================
    // ACTIVITY TRACKING
    // ========================================================================

    /**
     * Update user activity
     */
    socket.on('user_activity', async (data: {
      boardId: string;
      itemId?: string;
      action?: string;
      data?: Record<string, any>;
    }) => {
      try {
        await CollaborationService.updateActivity(user.id, data.boardId, {
          itemId: data.itemId,
          action: data.action,
          data: data.data,
        });
      } catch (error) {
        Logger.error('User activity update failed', error as Error);
      }
    });

    /**
     * Get board activity
     */
    socket.on('get_board_activity', async (data: {
      boardId: string;
      limit?: number;
      offset?: number;
      filters?: {
        userId?: string;
        itemId?: string;
        type?: string;
        startDate?: string;
        endDate?: string;
      };
    }) => {
      try {
        const filters = data.filters ? {
          ...data.filters,
          startDate: data.filters.startDate ? new Date(data.filters.startDate) : undefined,
          endDate: data.filters.endDate ? new Date(data.filters.endDate) : undefined,
        } : {};

        const activities = await CollaborationService.getBoardActivity(
          data.boardId,
          data.limit || 50,
          data.offset || 0,
          filters
        );

        socket.emit('board_activity', {
          boardId: data.boardId,
          activities,
          timestamp: new Date(),
        });
      } catch (error) {
        Logger.error('Get board activity failed', error as Error);
      }
    });

    // ========================================================================
    // SUBSCRIPTION MANAGEMENT
    // ========================================================================

    /**
     * Subscribe to real-time updates
     */
    socket.on('subscribe', async (data: {
      channel: string;
      filters?: {
        itemIds?: string[];
        eventTypes?: string[];
      };
    }) => {
      try {
        await CollaborationService.subscribe({
          subscriptionId: `${socket.id}_${Date.now()}`,
          connectionId: socket.id,
          userId: user.id,
          channel: data.channel,
          filters: data.filters,
          createdAt: new Date(),
        });

        socket.emit('subscription_confirmed', {
          channel: data.channel,
          timestamp: new Date(),
        });
      } catch (error) {
        Logger.error('Subscription failed', error as Error);
        socket.emit('subscription_error', {
          channel: data.channel,
          message: (error as Error).message,
        });
      }
    });

    /**
     * Unsubscribe from updates
     */
    socket.on('unsubscribe', async (data: {
      subscriptionId: string;
    }) => {
      try {
        await CollaborationService.unsubscribe(socket.id, data.subscriptionId);
        socket.emit('unsubscription_confirmed', {
          subscriptionId: data.subscriptionId,
          timestamp: new Date(),
        });
      } catch (error) {
        Logger.error('Unsubscription failed', error as Error);
      }
    });

    // ========================================================================
    // COLLABORATION METRICS
    // ========================================================================

    /**
     * Get collaboration metrics
     */
    socket.on('get_collaboration_metrics', async (data: {
      boardId: string;
      timeRange?: {
        start: string;
        end: string;
      };
    }) => {
      try {
        const timeRange = data.timeRange ? {
          start: new Date(data.timeRange.start),
          end: new Date(data.timeRange.end),
        } : {
          start: new Date(Date.now() - 24 * 60 * 60 * 1000), // Last 24 hours
          end: new Date(),
        };

        const metrics = await CollaborationService.getCollaborationMetrics(
          data.boardId,
          timeRange
        );

        socket.emit('collaboration_metrics', {
          boardId: data.boardId,
          metrics,
          timestamp: new Date(),
        });
      } catch (error) {
        Logger.error('Get collaboration metrics failed', error as Error);
      }
    });

    // ========================================================================
    // DISCONNECTION HANDLING
    // ========================================================================

    socket.on('disconnect', async (reason) => {
      try {
        Logger.websocket(`User ${user.email} disconnected`, {
          socketId: socket.id,
          userId: user.id,
          reason,
        });

        // Clean up presence
        if (socket.currentBoard) {
          await CollaborationService.removePresence(
            user.id,
            socket.currentBoard,
            socket.id
          );
        }

        // Release all locks held by this user
        await CollaborationService.releaseUserLocks(user.id);

        // Clean up subscriptions
        // This would be handled by the cleanup process in CollaborationService
      } catch (error) {
        Logger.error('Disconnect cleanup failed', error as Error);
      }
    });

    // ========================================================================
    // ERROR HANDLING
    // ========================================================================

    socket.on('error', (error) => {
      Logger.error('WebSocket error', error);
    });

    // Send initial connection confirmation
    socket.emit('connected', {
      userId: user.id,
      socketId: socket.id,
      timestamp: new Date(),
    });
  });

  // ============================================================================
  // HELPER FUNCTIONS
  // ============================================================================

  /**
   * Leave board room and clean up presence
   */
  async function leaveBoard(socket: AuthenticatedSocket, boardId: string) {
    if (!socket.user) return;

    socket.leave(`board:${boardId}`);

    if (socket.currentBoard === boardId) {
      socket.currentBoard = undefined;
    }

    await CollaborationService.removePresence(
      socket.user.id,
      boardId,
      socket.id
    );
  }

  /**
   * Parse user agent to extract device info
   */
  function parseUserAgent(userAgent: string): {
    type: 'desktop' | 'tablet' | 'mobile';
    os: string;
    browser: string;
  } {
    const isMobile = /Mobile|Android|iPhone|iPad|iPod|BlackBerry|Windows Phone/i.test(userAgent);
    const isTablet = /iPad|Android(?!.*Mobile)/i.test(userAgent);

    let type: 'desktop' | 'tablet' | 'mobile' = 'desktop';
    if (isTablet) type = 'tablet';
    else if (isMobile) type = 'mobile';

    let os = 'Unknown';
    if (/Windows/i.test(userAgent)) os = 'Windows';
    else if (/Mac/i.test(userAgent)) os = 'macOS';
    else if (/Linux/i.test(userAgent)) os = 'Linux';
    else if (/Android/i.test(userAgent)) os = 'Android';
    else if (/iPhone|iPad|iPod/i.test(userAgent)) os = 'iOS';

    let browser = 'Unknown';
    if (/Chrome/i.test(userAgent)) browser = 'Chrome';
    else if (/Firefox/i.test(userAgent)) browser = 'Firefox';
    else if (/Safari/i.test(userAgent)) browser = 'Safari';
    else if (/Edge/i.test(userAgent)) browser = 'Edge';

    return { type, os, browser };
  }

  // ============================================================================
  // CLEANUP INTERVAL
  // ============================================================================

  // Start cleanup interval for expired data
  const cleanupInterval = CollaborationService.startCleanupInterval();

  // Clean up on server shutdown
  process.on('SIGTERM', () => {
    clearInterval(cleanupInterval);
  });

  process.on('SIGINT', () => {
    clearInterval(cleanupInterval);
  });

  Logger.websocket('Collaboration WebSocket handlers initialized');
}