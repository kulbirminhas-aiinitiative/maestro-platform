import { RedisService } from '@/config/redis';
import { Logger } from '@/config/logger';
import { io } from '@/server';
import { UserPresence } from '@/types';

interface UserActivity {
  userId: string;
  boardId?: string;
  itemId?: string;
  action: string;
  timestamp: Date;
  data?: Record<string, any>;
}

interface ActiveUser {
  userId: string;
  username: string;
  avatarUrl?: string;
  boardId?: string;
  itemId?: string;
  lastActivity: Date;
  socketId: string;
}

export class CollaborationService {
  private static readonly PRESENCE_TTL = 300; // 5 minutes
  private static readonly ACTIVITY_TTL = 3600; // 1 hour
  private static readonly CURSOR_TTL = 30; // 30 seconds

  /**
   * Track user presence on a board
   */
  static async trackPresence(
    userId: string,
    username: string,
    boardId: string,
    socketId: string,
    avatarUrl?: string
  ): Promise<void> {
    try {
      const presenceKey = `presence:board:${boardId}`;
      const userKey = `user:${userId}`;

      const presence: UserPresence = {
        userId,
        username,
        avatarUrl,
        lastSeen: new Date(),
      };

      // Store user presence in Redis
      await Promise.all([
        RedisService.setHash(presenceKey, userKey, JSON.stringify(presence), this.PRESENCE_TTL),
        RedisService.setCache(`socket:${socketId}`, JSON.stringify({ userId, boardId }), this.PRESENCE_TTL),
      ]);

      // Get all active users on this board
      const activeUsers = await this.getActiveUsers(boardId);

      // Emit presence update to all users on the board
      io.to(`board:${boardId}`).emit('presence_updated', {
        boardId,
        activeUsers,
        joinedUser: {
          userId,
          username,
          avatarUrl,
        },
      });

      Logger.websocket(`User ${username} joined board ${boardId}`);
    } catch (error) {
      Logger.error('Failed to track presence', error as Error);
    }
  }

  /**
   * Remove user presence from a board
   */
  static async removePresence(userId: string, boardId: string, socketId?: string): Promise<void> {
    try {
      const presenceKey = `presence:board:${boardId}`;
      const userKey = `user:${userId}`;

      // Remove user from presence
      await RedisService.deleteHashField(presenceKey, userKey);

      if (socketId) {
        await RedisService.deleteCache(`socket:${socketId}`);
      }

      // Get remaining active users
      const activeUsers = await this.getActiveUsers(boardId);

      // Emit presence update to remaining users
      io.to(`board:${boardId}`).emit('presence_updated', {
        boardId,
        activeUsers,
        leftUser: {
          userId,
        },
      });

      Logger.websocket(`User ${userId} left board ${boardId}`);
    } catch (error) {
      Logger.error('Failed to remove presence', error as Error);
    }
  }

  /**
   * Get active users on a board
   */
  static async getActiveUsers(boardId: string): Promise<UserPresence[]> {
    try {
      const presenceKey = `presence:board:${boardId}`;
      const userPresences = await RedisService.getAllHashFields(presenceKey);

      const activeUsers: UserPresence[] = [];

      for (const [userKey, presenceData] of Object.entries(userPresences)) {
        try {
          const presence = JSON.parse(presenceData);
          const lastSeen = new Date(presence.lastSeen);

          // Only include users active within the last 5 minutes
          if (Date.now() - lastSeen.getTime() < this.PRESENCE_TTL * 1000) {
            activeUsers.push(presence);
          }
        } catch (parseError) {
          Logger.error('Failed to parse presence data', parseError as Error);
        }
      }

      return activeUsers;
    } catch (error) {
      Logger.error('Failed to get active users', error as Error);
      return [];
    }
  }

  /**
   * Update user cursor position
   */
  static async updateCursor(
    userId: string,
    boardId: string,
    cursor: { x: number; y: number }
  ): Promise<void> {
    try {
      const cursorKey = `cursor:board:${boardId}:user:${userId}`;

      await RedisService.setCache(
        cursorKey,
        JSON.stringify({ userId, cursor, timestamp: new Date() }),
        this.CURSOR_TTL
      );

      // Emit cursor update to other users on the board (exclude sender)
      io.to(`board:${boardId}`).emit('cursor_updated', {
        userId,
        cursor,
        timestamp: new Date(),
      });
    } catch (error) {
      Logger.error('Failed to update cursor', error as Error);
    }
  }

  /**
   * Track user activity for analytics and presence
   */
  static async trackActivity(
    userId: string,
    boardId: string,
    action: string,
    data?: Record<string, any>,
    itemId?: string
  ): Promise<void> {
    try {
      const activity: UserActivity = {
        userId,
        boardId,
        itemId,
        action,
        timestamp: new Date(),
        data,
      };

      const activityKey = `activity:board:${boardId}:${Date.now()}`;
      await RedisService.setCache(
        activityKey,
        JSON.stringify(activity),
        this.ACTIVITY_TTL
      );

      // Update user's last activity time
      const presenceKey = `presence:board:${boardId}`;
      const userKey = `user:${userId}`;
      const currentPresence = await RedisService.getHashField(presenceKey, userKey);

      if (currentPresence) {
        const presence = JSON.parse(currentPresence);
        presence.lastSeen = new Date();
        await RedisService.setHash(presenceKey, userKey, JSON.stringify(presence), this.PRESENCE_TTL);
      }

      Logger.websocket(`Activity tracked: ${action} by user ${userId} on board ${boardId}`);
    } catch (error) {
      Logger.error('Failed to track activity', error as Error);
    }
  }

  /**
   * Broadcast real-time event to board members
   */
  static async broadcastToBoardMembers(
    boardId: string,
    event: string,
    data: Record<string, any>,
    excludeUserId?: string
  ): Promise<void> {
    try {
      const eventData = {
        ...data,
        timestamp: new Date().toISOString(),
        boardId,
      };

      if (excludeUserId) {
        // Get all sockets in the board room except the excluded user
        const sockets = await io.in(`board:${boardId}`).fetchSockets();
        const targetSockets = sockets.filter(socket => {
          // Assuming socket has userId attached during authentication
          return (socket as any).userId !== excludeUserId;
        });

        targetSockets.forEach(socket => {
          socket.emit(event, eventData);
        });
      } else {
        io.to(`board:${boardId}`).emit(event, eventData);
      }

      Logger.websocket(`Broadcasted ${event} to board ${boardId}`);
    } catch (error) {
      Logger.error('Failed to broadcast to board members', error as Error);
    }
  }

  /**
   * Handle item locking for editing
   */
  static async lockItem(
    itemId: string,
    userId: string,
    username: string,
    duration = 300000 // 5 minutes default
  ): Promise<{ success: boolean; lockedBy?: string }> {
    try {
      const lockKey = `lock:item:${itemId}`;
      const lockData = JSON.stringify({
        userId,
        username,
        lockedAt: new Date(),
      });

      // Try to acquire lock
      const acquired = await RedisService.setIfNotExists(lockKey, lockData, Math.floor(duration / 1000));

      if (acquired) {
        return { success: true };
      } else {
        // Lock already exists, get the owner
        const existingLock = await RedisService.getCache(lockKey);
        if (existingLock) {
          const lockInfo = JSON.parse(existingLock);
          return { success: false, lockedBy: lockInfo.username };
        }
        return { success: false };
      }
    } catch (error) {
      Logger.error('Failed to lock item', error as Error);
      return { success: false };
    }
  }

  /**
   * Release item lock
   */
  static async unlockItem(itemId: string, userId: string): Promise<boolean> {
    try {
      const lockKey = `lock:item:${itemId}`;
      const existingLock = await RedisService.getCache(lockKey);

      if (existingLock) {
        const lockInfo = JSON.parse(existingLock);

        // Only allow the lock owner to release it
        if (lockInfo.userId === userId) {
          await RedisService.deleteCache(lockKey);
          return true;
        }
      }

      return false;
    } catch (error) {
      Logger.error('Failed to unlock item', error as Error);
      return false;
    }
  }

  /**
   * Handle typing indicators
   */
  static async handleTyping(
    userId: string,
    username: string,
    itemId: string,
    isTyping: boolean
  ): Promise<void> {
    try {
      const typingKey = `typing:item:${itemId}`;

      if (isTyping) {
        // Add user to typing list
        await RedisService.setHash(
          typingKey,
          `user:${userId}`,
          JSON.stringify({ userId, username, timestamp: new Date() }),
          30 // 30 seconds TTL
        );
      } else {
        // Remove user from typing list
        await RedisService.deleteHashField(typingKey, `user:${userId}`);
      }

      // Get current typing users
      const typingUsers = await this.getTypingUsers(itemId);

      // Emit typing status to item subscribers
      io.to(`item:${itemId}`).emit('typing_status', {
        itemId,
        typingUsers,
      });
    } catch (error) {
      Logger.error('Failed to handle typing', error as Error);
    }
  }

  /**
   * Get users currently typing on an item
   */
  static async getTypingUsers(itemId: string): Promise<Array<{ userId: string; username: string }>> {
    try {
      const typingKey = `typing:item:${itemId}`;
      const typingData = await RedisService.getAllHashFields(typingKey);

      const typingUsers: Array<{ userId: string; username: string }> = [];
      const now = Date.now();

      for (const [userKey, userData] of Object.entries(typingData)) {
        try {
          const user = JSON.parse(userData);
          const timestamp = new Date(user.timestamp).getTime();

          // Only include users who were typing within the last 30 seconds
          if (now - timestamp < 30000) {
            typingUsers.push({
              userId: user.userId,
              username: user.username,
            });
          }
        } catch (parseError) {
          Logger.error('Failed to parse typing data', parseError as Error);
        }
      }

      return typingUsers;
    } catch (error) {
      Logger.error('Failed to get typing users', error as Error);
      return [];
    }
  }

  /**
   * Handle socket disconnection cleanup
   */
  static async handleDisconnection(socketId: string): Promise<void> {
    try {
      // Get user info from socket
      const socketData = await RedisService.getCache(`socket:${socketId}`);

      if (socketData) {
        const { userId, boardId } = JSON.parse(socketData);

        // Remove presence
        await this.removePresence(userId, boardId, socketId);

        // Release any item locks held by this user
        // Note: In a production system, you might want to track which items
        // a user has locked to clean them up properly

        Logger.websocket(`Cleaned up disconnected socket ${socketId}`);
      }
    } catch (error) {
      Logger.error('Failed to handle disconnection', error as Error);
    }
  }

  /**
   * Get board activity feed
   */
  static async getBoardActivity(
    boardId: string,
    limit = 50,
    offset = 0
  ): Promise<UserActivity[]> {
    try {
      // Get all activity keys for the board
      const pattern = `activity:board:${boardId}:*`;
      const keys = await RedisService.getKeysByPattern(pattern);

      // Sort keys by timestamp (descending)
      const sortedKeys = keys.sort().reverse();

      // Get the requested slice
      const slicedKeys = sortedKeys.slice(offset, offset + limit);

      const activities: UserActivity[] = [];

      for (const key of slicedKeys) {
        try {
          const activityData = await RedisService.getCache(key);
          if (activityData) {
            activities.push(JSON.parse(activityData));
          }
        } catch (parseError) {
          Logger.error('Failed to parse activity data', parseError as Error);
        }
      }

      return activities;
    } catch (error) {
      Logger.error('Failed to get board activity', error as Error);
      return [];
    }
  }

  /**
   * Clean up expired presence and activity data
   */
  static async cleanupExpiredData(): Promise<void> {
    try {
      // This method should be called periodically (e.g., via cron job)
      // to clean up expired presence and activity data

      // Get all presence keys
      const presenceKeys = await RedisService.getKeysByPattern('presence:board:*');

      for (const presenceKey of presenceKeys) {
        const userPresences = await RedisService.getAllHashFields(presenceKey);

        for (const [userKey, presenceData] of Object.entries(userPresences)) {
          try {
            const presence = JSON.parse(presenceData);
            const lastSeen = new Date(presence.lastSeen);

            // Remove users inactive for more than 10 minutes
            if (Date.now() - lastSeen.getTime() > 600000) {
              await RedisService.deleteHashField(presenceKey, userKey);
            }
          } catch (parseError) {
            // Remove invalid data
            await RedisService.deleteHashField(presenceKey, userKey);
          }
        }
      }

      Logger.websocket('Cleaned up expired collaboration data');
    } catch (error) {
      Logger.error('Failed to cleanup expired data', error as Error);
    }
  }

  /**
   * Handle collaborative editing conflict resolution
   */
  static async handleEditConflict(
    itemId: string,
    userId: string,
    field: string,
    localValue: any,
    currentValue: any,
    timestamp: Date
  ): Promise<{
    resolved: boolean;
    resolvedValue: any;
    conflictStrategy: 'local_wins' | 'remote_wins' | 'merge' | 'manual';
  }> {
    try {
      const conflictKey = `conflict:item:${itemId}:${field}`;

      // Store conflict information
      const conflictData = {
        itemId,
        field,
        userId,
        localValue,
        currentValue,
        timestamp,
        status: 'pending',
      };

      await RedisService.setCache(conflictKey, JSON.stringify(conflictData), 3600); // 1 hour TTL

      // Apply automatic conflict resolution based on field type
      let resolvedValue = currentValue;
      let conflictStrategy: 'local_wins' | 'remote_wins' | 'merge' | 'manual' = 'remote_wins';

      // Timestamp-based resolution (last write wins)
      const lastEdit = await RedisService.getCache(`last_edit:item:${itemId}:${field}`);
      if (lastEdit) {
        const lastEditTime = new Date(lastEdit);
        if (timestamp > lastEditTime) {
          resolvedValue = localValue;
          conflictStrategy = 'local_wins';
        }
      } else {
        resolvedValue = localValue;
        conflictStrategy = 'local_wins';
      }

      // Update last edit timestamp
      await RedisService.setCache(`last_edit:item:${itemId}:${field}`, timestamp.toISOString(), 3600);

      // Broadcast conflict resolution to all users
      io.to(`item:${itemId}`).emit('conflict_resolved', {
        itemId,
        field,
        resolvedValue,
        conflictStrategy,
        resolvedBy: userId,
        timestamp: new Date(),
      });

      Logger.websocket(`Edit conflict resolved for item ${itemId}`, {
        field,
        strategy: conflictStrategy,
        userId,
      });

      return {
        resolved: true,
        resolvedValue,
        conflictStrategy,
      };
    } catch (error) {
      Logger.error('Failed to handle edit conflict', error as Error);
      return {
        resolved: false,
        resolvedValue: currentValue,
        conflictStrategy: 'remote_wins',
      };
    }
  }

  /**
   * Track user selection for real-time collaboration
   */
  static async updateUserSelection(
    userId: string,
    boardId: string,
    selection: {
      itemIds: string[];
      startPosition?: { x: number; y: number };
      endPosition?: { x: number; y: number };
    }
  ): Promise<void> {
    try {
      const selectionKey = `selection:board:${boardId}:user:${userId}`;

      await RedisService.setCache(
        selectionKey,
        JSON.stringify({
          userId,
          boardId,
          selection,
          timestamp: new Date(),
        }),
        this.CURSOR_TTL
      );

      // Emit selection update to other users on the board
      io.to(`board:${boardId}`).emit('user_selection_updated', {
        userId,
        selection,
        timestamp: new Date(),
      });
    } catch (error) {
      Logger.error('Failed to update user selection', error as Error);
    }
  }

  /**
   * Handle bulk operations with conflict detection
   */
  static async handleBulkEdit(
    itemIds: string[],
    changes: Record<string, any>,
    userId: string,
    boardId: string
  ): Promise<{
    success: string[];
    conflicts: Array<{
      itemId: string;
      field: string;
      conflict: any;
    }>;
    errors: Array<{
      itemId: string;
      error: string;
    }>;
  }> {
    try {
      const result = {
        success: [] as string[],
        conflicts: [] as Array<{ itemId: string; field: string; conflict: any }>,
        errors: [] as Array<{ itemId: string; error: string }>,
      };

      // Check for concurrent edits on all items
      for (const itemId of itemIds) {
        try {
          // Check if item is locked by another user
          const lockKey = `lock:item:${itemId}`;
          const existingLock = await RedisService.getCache(lockKey);

          if (existingLock) {
            const lockInfo = JSON.parse(existingLock);
            if (lockInfo.userId !== userId) {
              result.conflicts.push({
                itemId,
                field: 'locked',
                conflict: {
                  type: 'item_locked',
                  lockedBy: lockInfo.username,
                  lockedAt: lockInfo.lockedAt,
                },
              });
              continue;
            }
          }

          result.success.push(itemId);
        } catch (error) {
          result.errors.push({
            itemId,
            error: (error as Error).message,
          });
        }
      }

      // Broadcast bulk edit status
      io.to(`board:${boardId}`).emit('bulk_edit_status', {
        userId,
        itemIds,
        changes,
        result,
        timestamp: new Date(),
      });

      Logger.websocket(`Bulk edit handled for ${itemIds.length} items`, {
        success: result.success.length,
        conflicts: result.conflicts.length,
        errors: result.errors.length,
        userId,
      });

      return result;
    } catch (error) {
      Logger.error('Failed to handle bulk edit', error as Error);
      return {
        success: [],
        conflicts: [],
        errors: itemIds.map(itemId => ({
          itemId,
          error: 'Failed to process bulk edit',
        })),
      };
    }
  }

  /**
   * Get real-time collaboration metrics for a board
   */
  static async getCollaborationMetrics(boardId: string): Promise<{
    activeUsers: number;
    concurrentEdits: number;
    conflictsResolved: number;
    activeLocks: number;
    realtimeConnections: number;
  }> {
    try {
      // Get active users
      const activeUsers = await this.getActiveUsers(boardId);

      // Count concurrent edits (locks)
      const lockKeys = await RedisService.getKeysByPattern(`lock:item:*`);
      let activeLocks = 0;

      for (const lockKey of lockKeys) {
        const lockData = await RedisService.getCache(lockKey);
        if (lockData) {
          activeLocks++;
        }
      }

      // Get conflicts resolved today
      const conflictKeys = await RedisService.getKeysByPattern(`conflict:item:*`);
      let conflictsResolved = 0;

      for (const conflictKey of conflictKeys) {
        const conflictData = await RedisService.getCache(conflictKey);
        if (conflictData) {
          const conflict = JSON.parse(conflictData);
          const conflictDate = new Date(conflict.timestamp);
          const today = new Date();

          if (conflictDate.toDateString() === today.toDateString()) {
            conflictsResolved++;
          }
        }
      }

      // Count real-time connections (approximate)
      const socketCount = io.sockets.adapter.rooms.get(`board:${boardId}`)?.size || 0;

      return {
        activeUsers: activeUsers.length,
        concurrentEdits: 0, // Would need to track active editing sessions
        conflictsResolved,
        activeLocks,
        realtimeConnections: socketCount,
      };
    } catch (error) {
      Logger.error('Failed to get collaboration metrics', error as Error);
      return {
        activeUsers: 0,
        concurrentEdits: 0,
        conflictsResolved: 0,
        activeLocks: 0,
        realtimeConnections: 0,
      };
    }
  }

  /**
   * Create a shareable collaboration session
   */
  static async createCollaborationSession(
    boardId: string,
    userId: string,
    options: {
      expiresIn?: number; // minutes
      allowedUsers?: string[];
      permissions?: string[];
    } = {}
  ): Promise<{
    sessionId: string;
    joinUrl: string;
    expiresAt: Date;
  }> {
    try {
      const sessionId = `collab_${boardId}_${Date.now()}`;
      const expiresIn = options.expiresIn || 60; // default 1 hour
      const expiresAt = new Date(Date.now() + expiresIn * 60 * 1000);

      const sessionData = {
        sessionId,
        boardId,
        createdBy: userId,
        createdAt: new Date(),
        expiresAt,
        allowedUsers: options.allowedUsers || [],
        permissions: options.permissions || ['read', 'comment'],
        isActive: true,
      };

      await RedisService.setCache(
        `collab_session:${sessionId}`,
        JSON.stringify(sessionData),
        expiresIn * 60
      );

      const joinUrl = `${process.env.FRONTEND_URL}/collaborate/${sessionId}`;

      Logger.business('Collaboration session created', {
        sessionId,
        boardId,
        createdBy: userId,
        expiresAt,
      });

      return {
        sessionId,
        joinUrl,
        expiresAt,
      };
    } catch (error) {
      Logger.error('Failed to create collaboration session', error as Error);
      throw error;
    }
  }

  /**
   * Join a collaboration session
   */
  static async joinCollaborationSession(
    sessionId: string,
    userId: string
  ): Promise<{
    success: boolean;
    boardId?: string;
    permissions?: string[];
    error?: string;
  }> {
    try {
      const sessionData = await RedisService.getCache(`collab_session:${sessionId}`);

      if (!sessionData) {
        return {
          success: false,
          error: 'Collaboration session not found or expired',
        };
      }

      const session = JSON.parse(sessionData);

      // Check if session is still active
      if (!session.isActive || new Date() > new Date(session.expiresAt)) {
        return {
          success: false,
          error: 'Collaboration session has expired',
        };
      }

      // Check if user is allowed
      if (session.allowedUsers.length > 0 && !session.allowedUsers.includes(userId)) {
        return {
          success: false,
          error: 'Access denied to this collaboration session',
        };
      }

      // Track session participation
      await RedisService.setHash(
        `collab_session_users:${sessionId}`,
        `user:${userId}`,
        JSON.stringify({
          userId,
          joinedAt: new Date(),
          lastActivity: new Date(),
        }),
        60 * 60 // 1 hour
      );

      return {
        success: true,
        boardId: session.boardId,
        permissions: session.permissions,
      };
    } catch (error) {
      Logger.error('Failed to join collaboration session', error as Error);
      return {
        success: false,
        error: 'Failed to join collaboration session',
      };
    }
  }
}