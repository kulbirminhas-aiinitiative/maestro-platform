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

interface Operation {
  id: string;
  userId: string;
  type: 'insert' | 'delete' | 'retain' | 'update';
  position?: number;
  content?: string;
  length?: number;
  itemId: string;
  field: string;
  timestamp: Date;
  clientId: string;
}

interface ConflictResolution {
  conflictId: string;
  operations: Operation[];
  resolvedOperation: Operation;
  strategy: 'last-write-wins' | 'merge' | 'manual';
  resolvedBy: string;
  resolvedAt: Date;
}

export class EnhancedCollaborationService {
  private static readonly PRESENCE_TTL = 300; // 5 minutes
  private static readonly ACTIVITY_TTL = 3600; // 1 hour
  private static readonly CURSOR_TTL = 30; // 30 seconds
  private static readonly OPERATION_TTL = 86400; // 24 hours
  private static readonly CONFLICT_TTL = 604800; // 1 week

  /**
   * Enhanced presence tracking with detailed user state
   */
  static async trackPresence(
    userId: string,
    username: string,
    boardId: string,
    socketId: string,
    avatarUrl?: string,
    userState?: Record<string, any>
  ): Promise<void> {
    try {
      const presenceKey = `presence:board:${boardId}`;
      const userKey = `user:${userId}`;

      const presence: UserPresence = {
        userId,
        username,
        avatarUrl,
        lastSeen: new Date(),
        cursor: userState?.cursor,
      };

      // Store enhanced presence data
      await Promise.all([
        RedisService.setHash(presenceKey, userKey, JSON.stringify(presence), this.PRESENCE_TTL),
        RedisService.setCache(`socket:${socketId}`, JSON.stringify({
          userId,
          boardId,
          userState: userState || {}
        }), this.PRESENCE_TTL),
        // Track user session for analytics
        this.trackUserSession(userId, boardId, 'join', userState),
      ]);

      const activeUsers = await this.getActiveUsers(boardId);

      // Enhanced presence update with user state
      io.to(`board:${boardId}`).emit('presence_updated', {
        boardId,
        activeUsers,
        joinedUser: {
          userId,
          username,
          avatarUrl,
          userState,
        },
      });

      Logger.websocket(`Enhanced presence: User ${username} joined board ${boardId}`, {
        userId,
        boardId,
        userState,
      });
    } catch (error) {
      Logger.error('Failed to track enhanced presence', error as Error);
    }
  }

  /**
   * Operational Transform for real-time collaborative editing
   */
  static async processOperation(operation: Operation): Promise<{
    transformedOperation: Operation;
    conflicts: ConflictResolution[];
    success: boolean;
  }> {
    try {
      const operationKey = `operations:${operation.itemId}:${operation.field}`;
      const conflictKey = `conflicts:${operation.itemId}:${operation.field}`;

      // Get recent operations on the same field
      const recentOps = await this.getRecentOperations(operation.itemId, operation.field, 100);

      // Apply operational transformation
      const transformResult = await this.transformOperation(operation, recentOps);

      // Store the operation
      await RedisService.listPush(
        operationKey,
        JSON.stringify(transformResult.transformedOperation),
        this.OPERATION_TTL
      );

      // Handle conflicts if any
      let conflicts: ConflictResolution[] = [];
      if (transformResult.hasConflicts) {
        conflicts = await this.resolveConflicts(
          operation.itemId,
          operation.field,
          transformResult.conflictingOperations
        );
      }

      // Broadcast the transformed operation to other users
      await this.broadcastOperation(transformResult.transformedOperation);

      return {
        transformedOperation: transformResult.transformedOperation,
        conflicts,
        success: true,
      };
    } catch (error) {
      Logger.error('Failed to process operation', error as Error);
      return {
        transformedOperation: operation,
        conflicts: [],
        success: false,
      };
    }
  }

  /**
   * Transform operation against concurrent operations
   */
  private static async transformOperation(
    operation: Operation,
    recentOps: Operation[]
  ): Promise<{
    transformedOperation: Operation;
    hasConflicts: boolean;
    conflictingOperations: Operation[];
  }> {
    let transformedOp = { ...operation };
    const conflictingOps: Operation[] = [];
    let hasConflicts = false;

    // Filter concurrent operations (operations that happened after this client's last known state)
    const concurrentOps = recentOps.filter(op =>
      op.timestamp > operation.timestamp &&
      op.userId !== operation.userId
    );

    for (const concurrentOp of concurrentOps) {
      const transformResult = this.transformOperationPair(transformedOp, concurrentOp);

      if (transformResult.hasConflict) {
        hasConflicts = true;
        conflictingOps.push(concurrentOp);
      }

      transformedOp = transformResult.transformedOperation;
    }

    return {
      transformedOperation: transformedOp,
      hasConflicts,
      conflictingOperations: conflictingOps,
    };
  }

  /**
   * Transform two operations against each other
   */
  private static transformOperationPair(op1: Operation, op2: Operation): {
    transformedOperation: Operation;
    hasConflict: boolean;
  } {
    // Simplified operational transformation logic
    // In a real implementation, you'd need comprehensive OT algorithms

    if (op1.type === 'insert' && op2.type === 'insert') {
      // Two insertions at the same position
      if (op1.position === op2.position) {
        return {
          transformedOperation: {
            ...op1,
            position: op1.position! + (op2.content?.length || 1),
          },
          hasConflict: true,
        };
      }
      // Insert after another insertion
      if (op1.position! > op2.position!) {
        return {
          transformedOperation: {
            ...op1,
            position: op1.position! + (op2.content?.length || 1),
          },
          hasConflict: false,
        };
      }
    } else if (op1.type === 'delete' && op2.type === 'delete') {
      // Two deletions overlapping
      if (this.operationsOverlap(op1, op2)) {
        return {
          transformedOperation: op1, // Keep original for conflict resolution
          hasConflict: true,
        };
      }
    } else if (op1.type === 'update' && op2.type === 'update') {
      // Concurrent updates to the same field
      return {
        transformedOperation: op1,
        hasConflict: true,
      };
    }

    return {
      transformedOperation: op1,
      hasConflict: false,
    };
  }

  /**
   * Check if two operations overlap
   */
  private static operationsOverlap(op1: Operation, op2: Operation): boolean {
    if (!op1.position || !op2.position) return false;

    const op1End = op1.position + (op1.length || 1);
    const op2End = op2.position + (op2.length || 1);

    return !(op1End <= op2.position || op2End <= op1.position);
  }

  /**
   * Resolve conflicts using various strategies
   */
  static async resolveConflicts(
    itemId: string,
    field: string,
    conflictingOps: Operation[]
  ): Promise<ConflictResolution[]> {
    try {
      const resolutions: ConflictResolution[] = [];

      for (const conflictGroup of this.groupConflictingOperations(conflictingOps)) {
        const resolution = await this.resolveConflictGroup(itemId, field, conflictGroup);
        resolutions.push(resolution);

        // Store resolution for audit
        const resolutionKey = `resolution:${resolution.conflictId}`;
        await RedisService.setCache(
          resolutionKey,
          JSON.stringify(resolution),
          this.CONFLICT_TTL
        );
      }

      return resolutions;
    } catch (error) {
      Logger.error('Failed to resolve conflicts', error as Error);
      return [];
    }
  }

  /**
   * Resolve a group of conflicting operations
   */
  private static async resolveConflictGroup(
    itemId: string,
    field: string,
    operations: Operation[]
  ): Promise<ConflictResolution> {
    const conflictId = `conflict_${itemId}_${field}_${Date.now()}`;

    // Apply last-write-wins strategy by default
    const lastOperation = operations.sort((a, b) =>
      b.timestamp.getTime() - a.timestamp.getTime()
    )[0];

    const resolution: ConflictResolution = {
      conflictId,
      operations,
      resolvedOperation: lastOperation,
      strategy: 'last-write-wins',
      resolvedBy: 'system',
      resolvedAt: new Date(),
    };

    // Broadcast conflict resolution
    await this.broadcastConflictResolution(itemId, resolution);

    Logger.websocket(`Conflict resolved: ${conflictId}`, {
      itemId,
      field,
      strategy: resolution.strategy,
      operationCount: operations.length,
    });

    return resolution;
  }

  /**
   * Group conflicting operations by conflict type
   */
  private static groupConflictingOperations(operations: Operation[]): Operation[][] {
    const groups: Operation[][] = [];
    const processed = new Set<string>();

    for (const op of operations) {
      if (processed.has(op.id)) continue;

      const group = [op];
      processed.add(op.id);

      // Find related conflicting operations
      for (const otherOp of operations) {
        if (processed.has(otherOp.id)) continue;

        if (this.operationsConflict(op, otherOp)) {
          group.push(otherOp);
          processed.add(otherOp.id);
        }
      }

      if (group.length > 1) {
        groups.push(group);
      }
    }

    return groups;
  }

  /**
   * Check if two operations conflict
   */
  private static operationsConflict(op1: Operation, op2: Operation): boolean {
    return op1.itemId === op2.itemId &&
           op1.field === op2.field &&
           (this.operationsOverlap(op1, op2) ||
            (op1.type === 'update' && op2.type === 'update'));
  }

  /**
   * Get recent operations for an item field
   */
  private static async getRecentOperations(
    itemId: string,
    field: string,
    limit: number = 100
  ): Promise<Operation[]> {
    try {
      const operationKey = `operations:${itemId}:${field}`;
      const operations = await RedisService.listRange(operationKey, -limit, -1);

      return operations.map(op => JSON.parse(op)).sort((a, b) =>
        new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      );
    } catch (error) {
      Logger.error('Failed to get recent operations', error as Error);
      return [];
    }
  }

  /**
   * Broadcast operation to other users
   */
  private static async broadcastOperation(operation: Operation): Promise<void> {
    try {
      // Broadcast to item subscribers
      io.to(`item:${operation.itemId}`).emit('operation_applied', {
        operation,
        timestamp: new Date(),
      });

      // Also broadcast to board subscribers
      const item = await this.getItemBoard(operation.itemId);
      if (item?.boardId) {
        io.to(`board:${item.boardId}`).emit('item_operation', {
          itemId: operation.itemId,
          operation,
          timestamp: new Date(),
        });
      }
    } catch (error) {
      Logger.error('Failed to broadcast operation', error as Error);
    }
  }

  /**
   * Broadcast conflict resolution
   */
  private static async broadcastConflictResolution(
    itemId: string,
    resolution: ConflictResolution
  ): Promise<void> {
    try {
      io.to(`item:${itemId}`).emit('conflict_resolved', {
        itemId,
        resolution,
        timestamp: new Date(),
      });

      const item = await this.getItemBoard(itemId);
      if (item?.boardId) {
        io.to(`board:${item.boardId}`).emit('conflict_notification', {
          itemId,
          conflictId: resolution.conflictId,
          strategy: resolution.strategy,
          timestamp: new Date(),
        });
      }
    } catch (error) {
      Logger.error('Failed to broadcast conflict resolution', error as Error);
    }
  }

  /**
   * Advanced cursor tracking with selection ranges
   */
  static async updateCursorAdvanced(
    userId: string,
    boardId: string,
    cursor: {
      x: number;
      y: number;
      itemId?: string;
      field?: string;
      selection?: { start: number; end: number };
    }
  ): Promise<void> {
    try {
      const cursorKey = `cursor:board:${boardId}:user:${userId}`;
      const detailedCursor = {
        userId,
        cursor,
        timestamp: new Date(),
        itemContext: cursor.itemId ? {
          itemId: cursor.itemId,
          field: cursor.field,
          selection: cursor.selection,
        } : null,
      };

      await RedisService.setCache(
        cursorKey,
        JSON.stringify(detailedCursor),
        this.CURSOR_TTL
      );

      // Emit detailed cursor update
      io.to(`board:${boardId}`).emit('cursor_updated_advanced', {
        userId,
        cursor: detailedCursor.cursor,
        itemContext: detailedCursor.itemContext,
        timestamp: new Date(),
      });

      // If user is editing a specific item, also emit to item subscribers
      if (cursor.itemId) {
        io.to(`item:${cursor.itemId}`).emit('cursor_item_focus', {
          userId,
          itemId: cursor.itemId,
          field: cursor.field,
          selection: cursor.selection,
          timestamp: new Date(),
        });
      }
    } catch (error) {
      Logger.error('Failed to update advanced cursor', error as Error);
    }
  }

  /**
   * Handle advanced item locking with granular field locks
   */
  static async lockItemField(
    itemId: string,
    field: string,
    userId: string,
    username: string,
    duration = 300000 // 5 minutes default
  ): Promise<{ success: boolean; lockedBy?: string; lockType?: string }> {
    try {
      const lockKey = `lock:item:${itemId}:field:${field}`;
      const globalLockKey = `lock:item:${itemId}`;

      const lockData = JSON.stringify({
        userId,
        username,
        field,
        lockedAt: new Date(),
        lockType: 'field',
      });

      // Check for global lock first
      const globalLock = await RedisService.getCache(globalLockKey);
      if (globalLock) {
        const globalLockInfo = JSON.parse(globalLock);
        if (globalLockInfo.userId !== userId) {
          return {
            success: false,
            lockedBy: globalLockInfo.username,
            lockType: 'global',
          };
        }
      }

      // Try to acquire field lock
      const acquired = await RedisService.setIfNotExists(
        lockKey,
        lockData,
        Math.floor(duration / 1000)
      );

      if (acquired) {
        // Notify other users about the field lock
        io.to(`item:${itemId}`).emit('field_locked', {
          itemId,
          field,
          userId,
          username,
          timestamp: new Date(),
        });

        return { success: true, lockType: 'field' };
      } else {
        const existingLock = await RedisService.getCache(lockKey);
        if (existingLock) {
          const lockInfo = JSON.parse(existingLock);
          return {
            success: false,
            lockedBy: lockInfo.username,
            lockType: 'field',
          };
        }
        return { success: false };
      }
    } catch (error) {
      Logger.error('Failed to lock item field', error as Error);
      return { success: false };
    }
  }

  /**
   * Release field lock
   */
  static async unlockItemField(
    itemId: string,
    field: string,
    userId: string
  ): Promise<boolean> {
    try {
      const lockKey = `lock:item:${itemId}:field:${field}`;
      const existingLock = await RedisService.getCache(lockKey);

      if (existingLock) {
        const lockInfo = JSON.parse(existingLock);

        if (lockInfo.userId === userId) {
          await RedisService.deleteCache(lockKey);

          // Notify other users about the field unlock
          io.to(`item:${itemId}`).emit('field_unlocked', {
            itemId,
            field,
            userId,
            timestamp: new Date(),
          });

          return true;
        }
      }

      return false;
    } catch (error) {
      Logger.error('Failed to unlock item field', error as Error);
      return false;
    }
  }

  /**
   * Track user session for analytics
   */
  private static async trackUserSession(
    userId: string,
    boardId: string,
    action: 'join' | 'leave' | 'active',
    metadata?: Record<string, any>
  ): Promise<void> {
    try {
      const sessionKey = `session:${userId}:${boardId}`;
      const sessionData = {
        userId,
        boardId,
        action,
        timestamp: new Date(),
        metadata: metadata || {},
      };

      await RedisService.setCache(
        sessionKey,
        JSON.stringify(sessionData),
        this.ACTIVITY_TTL
      );

      // Aggregate session data for analytics
      const dailyKey = `analytics:sessions:${new Date().toISOString().split('T')[0]}`;
      await RedisService.incrementCounter(dailyKey, this.ACTIVITY_TTL);
    } catch (error) {
      Logger.error('Failed to track user session', error as Error);
    }
  }

  /**
   * Get item board relationship for broadcasting
   */
  private static async getItemBoard(itemId: string): Promise<{ boardId: string } | null> {
    try {
      // This would typically query the database to get the board ID for an item
      // For now, we'll use a cache lookup
      const itemBoardKey = `item_board:${itemId}`;
      const cached = await RedisService.getCache(itemBoardKey);

      if (cached) {
        return JSON.parse(cached);
      }

      // In a real implementation, you'd query the database here
      return null;
    } catch (error) {
      Logger.error('Failed to get item board', error as Error);
      return null;
    }
  }

  /**
   * Get comprehensive board activity with operation details
   */
  static async getBoardActivityAdvanced(
    boardId: string,
    limit = 50,
    offset = 0,
    includeOperations = false
  ): Promise<{
    activities: UserActivity[];
    operations?: Operation[];
    conflicts?: ConflictResolution[];
  }> {
    try {
      const activityPattern = `activity:board:${boardId}:*`;
      const activityKeys = await RedisService.getKeysByPattern(activityPattern);

      const sortedKeys = activityKeys.sort().reverse();
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

      const result: any = { activities };

      if (includeOperations) {
        // Get recent operations for all items in the board
        const operationPattern = `operations:*`;
        const operationKeys = await RedisService.getKeysByPattern(operationPattern);
        const operations: Operation[] = [];

        for (const key of operationKeys.slice(0, limit)) {
          try {
            const ops = await RedisService.listRange(key, -10, -1);
            operations.push(...ops.map(op => JSON.parse(op)));
          } catch (parseError) {
            Logger.error('Failed to parse operation data', parseError as Error);
          }
        }

        result.operations = operations.sort((a, b) =>
          new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
        );

        // Get recent conflicts
        const conflictPattern = `resolution:*`;
        const conflictKeys = await RedisService.getKeysByPattern(conflictPattern);
        const conflicts: ConflictResolution[] = [];

        for (const key of conflictKeys.slice(0, 20)) {
          try {
            const conflictData = await RedisService.getCache(key);
            if (conflictData) {
              conflicts.push(JSON.parse(conflictData));
            }
          } catch (parseError) {
            Logger.error('Failed to parse conflict data', parseError as Error);
          }
        }

        result.conflicts = conflicts.sort((a, b) =>
          new Date(b.resolvedAt).getTime() - new Date(a.resolvedAt).getTime()
        );
      }

      return result;
    } catch (error) {
      Logger.error('Failed to get advanced board activity', error as Error);
      return { activities: [] };
    }
  }

  /**
   * Get active users with enhanced presence information
   */
  static async getActiveUsers(boardId: string): Promise<(UserPresence & {
    isTyping?: boolean;
    currentItem?: string;
    lockStatus?: Array<{ itemId: string; field: string; type: string }>;
  })[]> {
    try {
      const presenceKey = `presence:board:${boardId}`;
      const userPresences = await RedisService.getAllHashFields(presenceKey);

      const activeUsers = [];

      for (const [userKey, presenceData] of Object.entries(userPresences)) {
        try {
          const presence = JSON.parse(presenceData);
          const lastSeen = new Date(presence.lastSeen);

          if (Date.now() - lastSeen.getTime() < this.PRESENCE_TTL * 1000) {
            // Get additional user state
            const userId = presence.userId;
            const typingUsers = await this.getTypingUsersForBoard(boardId);
            const userLocks = await this.getUserLocks(userId);

            activeUsers.push({
              ...presence,
              isTyping: typingUsers.some(tu => tu.userId === userId),
              lockStatus: userLocks,
            });
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
   * Get typing users for a board
   */
  private static async getTypingUsersForBoard(boardId: string): Promise<Array<{ userId: string; username: string }>> {
    try {
      // Get all typing keys for items in this board
      const typingPattern = `typing:item:*`;
      const typingKeys = await RedisService.getKeysByPattern(typingPattern);

      const allTypingUsers = [];

      for (const key of typingKeys) {
        const typingData = await RedisService.getAllHashFields(key);

        for (const [userKey, userData] of Object.entries(typingData)) {
          try {
            const user = JSON.parse(userData);
            const timestamp = new Date(user.timestamp).getTime();

            if (Date.now() - timestamp < 30000) {
              allTypingUsers.push({
                userId: user.userId,
                username: user.username,
              });
            }
          } catch (parseError) {
            Logger.error('Failed to parse typing data', parseError as Error);
          }
        }
      }

      return allTypingUsers;
    } catch (error) {
      Logger.error('Failed to get typing users for board', error as Error);
      return [];
    }
  }

  /**
   * Get locks held by a user
   */
  private static async getUserLocks(userId: string): Promise<Array<{ itemId: string; field: string; type: string }>> {
    try {
      const lockPattern = `lock:*`;
      const lockKeys = await RedisService.getKeysByPattern(lockPattern);
      const userLocks = [];

      for (const key of lockKeys) {
        try {
          const lockData = await RedisService.getCache(key);
          if (lockData) {
            const lock = JSON.parse(lockData);
            if (lock.userId === userId) {
              // Parse lock key to extract item and field info
              const keyParts = key.split(':');
              if (keyParts.length >= 3) {
                userLocks.push({
                  itemId: keyParts[2],
                  field: keyParts[4] || 'global',
                  type: lock.lockType || 'global',
                });
              }
            }
          }
        } catch (parseError) {
          Logger.error('Failed to parse lock data', parseError as Error);
        }
      }

      return userLocks;
    } catch (error) {
      Logger.error('Failed to get user locks', error as Error);
      return [];
    }
  }

  /**
   * Enhanced cleanup with operation and conflict cleanup
   */
  static async cleanupExpiredDataAdvanced(): Promise<void> {
    try {
      // Clean up expired presence data
      await this.cleanupExpiredPresence();

      // Clean up old operations
      await this.cleanupOldOperations();

      // Clean up resolved conflicts
      await this.cleanupResolvedConflicts();

      // Clean up expired locks
      await this.cleanupExpiredLocks();

      Logger.websocket('Advanced collaboration data cleanup completed');
    } catch (error) {
      Logger.error('Failed to cleanup advanced collaboration data', error as Error);
    }
  }

  private static async cleanupExpiredPresence(): Promise<void> {
    const presenceKeys = await RedisService.getKeysByPattern('presence:board:*');

    for (const presenceKey of presenceKeys) {
      const userPresences = await RedisService.getAllHashFields(presenceKey);

      for (const [userKey, presenceData] of Object.entries(userPresences)) {
        try {
          const presence = JSON.parse(presenceData);
          const lastSeen = new Date(presence.lastSeen);

          if (Date.now() - lastSeen.getTime() > 600000) { // 10 minutes
            await RedisService.deleteHashField(presenceKey, userKey);
          }
        } catch (parseError) {
          await RedisService.deleteHashField(presenceKey, userKey);
        }
      }
    }
  }

  private static async cleanupOldOperations(): Promise<void> {
    const operationKeys = await RedisService.getKeysByPattern('operations:*');

    for (const key of operationKeys) {
      // Keep only last 1000 operations per item/field
      await RedisService.listTrim(key, -1000, -1);
    }
  }

  private static async cleanupResolvedConflicts(): Promise<void> {
    const conflictKeys = await RedisService.getKeysByPattern('resolution:*');

    for (const key of conflictKeys) {
      try {
        const conflictData = await RedisService.getCache(key);
        if (conflictData) {
          const conflict = JSON.parse(conflictData);
          const resolvedAt = new Date(conflict.resolvedAt);

          // Remove conflicts older than 1 week
          if (Date.now() - resolvedAt.getTime() > this.CONFLICT_TTL * 1000) {
            await RedisService.deleteCache(key);
          }
        }
      } catch (parseError) {
        await RedisService.deleteCache(key);
      }
    }
  }

  private static async cleanupExpiredLocks(): Promise<void> {
    // Redis TTL will handle most locks, but clean up any orphaned ones
    const lockKeys = await RedisService.getKeysByPattern('lock:*');

    for (const key of lockKeys) {
      try {
        const lockData = await RedisService.getCache(key);
        if (lockData) {
          const lock = JSON.parse(lockData);
          const lockedAt = new Date(lock.lockedAt);

          // Remove locks older than 1 hour (in case TTL failed)
          if (Date.now() - lockedAt.getTime() > 3600000) {
            await RedisService.deleteCache(key);
          }
        }
      } catch (parseError) {
        await RedisService.deleteCache(key);
      }
    }
  }
}