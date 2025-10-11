import { RedisService } from '@/config/redis';
import { Logger } from '@/config/logger';
import { io } from '@/server';
import { UserPresence } from '@/types';
import { CollaborationService } from './collaboration.service';

interface AdvancedCursorPosition {
  x: number;
  y: number;
  itemId?: string;
  field?: string;
  selection?: {
    start: number;
    end: number;
  };
}

interface CollaborativeOperation {
  id: string;
  type: 'insert' | 'delete' | 'retain' | 'update';
  itemId: string;
  field: string;
  position?: number;
  content?: string;
  length?: number;
  userId: string;
  clientId: string;
  timestamp: Date;
}

interface FieldLock {
  itemId: string;
  field: string;
  userId: string;
  username: string;
  lockedAt: Date;
  expiresAt: Date;
}

interface ActivityEvent {
  id: string;
  userId: string;
  boardId: string;
  itemId?: string;
  type: string;
  data: Record<string, any>;
  timestamp: Date;
}

export class EnhancedCollaborationService extends CollaborationService {
  private static readonly LOCK_TTL = 300; // 5 minutes
  private static readonly OPERATION_TTL = 3600; // 1 hour
  private static readonly ACTIVITY_BUFFER_SIZE = 1000;

  /**
   * Track presence with additional state information
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
        // Additional state for enhanced features
        ...(userState && { userState }),
      };

      // Store user presence in Redis with additional metadata
      await Promise.all([
        RedisService.setHash(presenceKey, userKey, JSON.stringify(presence), this.PRESENCE_TTL),
        RedisService.setCache(`socket:${socketId}`, JSON.stringify({ userId, boardId, userState }), this.PRESENCE_TTL),
        // Track socket mapping for advanced features
        RedisService.setCache(`user:${userId}:socket`, socketId, this.PRESENCE_TTL),
      ]);

      // Get all active users on this board
      const activeUsers = await this.getActiveUsers(boardId);

      // Emit enhanced presence update
      io.to(`board:${boardId}`).emit('presence_updated', {
        boardId,
        activeUsers,
        joinedUser: {
          userId,
          username,
          avatarUrl,
          userState,
        },
        timestamp: new Date(),
      });

      Logger.websocket(`Enhanced presence tracked: ${username} joined board ${boardId}`);
    } catch (error) {
      Logger.error('Failed to track enhanced presence', error as Error);
    }
  }

  /**
   * Update cursor position with field-level tracking
   */
  static async updateCursorAdvanced(
    userId: string,
    boardId: string,
    cursor: AdvancedCursorPosition
  ): Promise<void> {
    try {
      const cursorKey = `cursor:board:${boardId}:user:${userId}`;
      const cursorData = {
        userId,
        cursor,
        timestamp: new Date(),
      };

      await RedisService.setCache(
        cursorKey,
        JSON.stringify(cursorData),
        this.CURSOR_TTL
      );

      // Emit enhanced cursor update with field information
      io.to(`board:${boardId}`).emit('cursor_updated_advanced', {
        userId,
        boardId,
        cursor,
        timestamp: new Date(),
      });

      // If cursor is on a specific item, emit to item-specific room as well
      if (cursor.itemId) {
        io.to(`item:${cursor.itemId}`).emit('item_cursor_updated', {
          userId,
          itemId: cursor.itemId,
          field: cursor.field,
          cursor: {
            x: cursor.x,
            y: cursor.y,
          },
          selection: cursor.selection,
          timestamp: new Date(),
        });
      }
    } catch (error) {
      Logger.error('Failed to update advanced cursor', error as Error);
    }
  }

  /**
   * Lock specific field of an item for editing
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
      const expiresAt = new Date(Date.now() + duration);

      const lockData: FieldLock = {
        itemId,
        field,
        userId,
        username,
        lockedAt: new Date(),
        expiresAt,
      };

      // Try to acquire field-specific lock
      const acquired = await RedisService.setIfNotExists(
        lockKey,
        JSON.stringify(lockData),
        Math.floor(duration / 1000)
      );

      if (acquired) {
        // Emit lock acquired event
        io.to(`item:${itemId}`).emit('field_locked', {
          itemId,
          field,
          lockedBy: { userId, username },
          expiresAt,
          timestamp: new Date(),
        });

        return { success: true, lockType: 'field' };
      } else {
        // Lock already exists, get the owner
        const existingLock = await RedisService.getCache(lockKey);
        if (existingLock) {
          const lockInfo: FieldLock = JSON.parse(existingLock);
          return {
            success: false,
            lockedBy: lockInfo.username,
            lockType: 'field'
          };
        }
        return { success: false, lockType: 'field' };
      }
    } catch (error) {
      Logger.error('Failed to lock item field', error as Error);
      return { success: false };
    }
  }

  /**
   * Release field lock
   */
  static async unlockItemField(itemId: string, field: string, userId: string): Promise<boolean> {
    try {
      const lockKey = `lock:item:${itemId}:field:${field}`;
      const existingLock = await RedisService.getCache(lockKey);

      if (existingLock) {
        const lockInfo: FieldLock = JSON.parse(existingLock);

        // Only allow the lock owner to release it
        if (lockInfo.userId === userId) {
          await RedisService.deleteCache(lockKey);

          // Emit lock released event
          io.to(`item:${itemId}`).emit('field_unlocked', {
            itemId,
            field,
            unlockedBy: { userId },
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
   * Process collaborative operation with operational transformation
   */
  static async processOperation(operation: CollaborativeOperation): Promise<{
    success: boolean;
    transformedOperation?: CollaborativeOperation;
    conflicts: Array<{ type: string; operation: CollaborativeOperation }>;
  }> {
    try {
      const operationKey = `operation:${operation.itemId}:${operation.field}:${operation.id}`;
      const conflictKey = `conflicts:${operation.itemId}:${operation.field}`;

      // Check for concurrent operations
      const concurrentOps = await this.getConcurrentOperations(operation);
      const conflicts: Array<{ type: string; operation: CollaborativeOperation }> = [];

      // Apply operational transformation
      let transformedOperation = operation;

      for (const concurrentOp of concurrentOps) {
        const transformResult = this.transformOperations(transformedOperation, concurrentOp);
        if (transformResult.hasConflict) {
          conflicts.push({
            type: 'concurrent_edit',
            operation: concurrentOp,
          });
        }
        transformedOperation = transformResult.transformedOp;
      }

      // Store the operation
      await RedisService.setCache(
        operationKey,
        JSON.stringify(transformedOperation),
        this.OPERATION_TTL
      );

      // Broadcast the transformed operation to collaborators
      io.to(`item:${operation.itemId}`).emit('operation_applied', {
        operation: transformedOperation,
        conflicts,
        timestamp: new Date(),
      });

      return {
        success: true,
        transformedOperation,
        conflicts,
      };
    } catch (error) {
      Logger.error('Failed to process operation', error as Error);
      return {
        success: false,
        conflicts: [],
      };
    }
  }

  /**
   * Get concurrent operations for transformation
   */
  private static async getConcurrentOperations(operation: CollaborativeOperation): Promise<CollaborativeOperation[]> {
    try {
      const pattern = `operation:${operation.itemId}:${operation.field}:*`;
      const keys = await RedisService.getKeysByPattern(pattern);

      const operations: CollaborativeOperation[] = [];

      for (const key of keys) {
        const opData = await RedisService.getCache(key);
        if (opData) {
          const op: CollaborativeOperation = JSON.parse(opData);
          // Only consider operations from different clients
          if (op.clientId !== operation.clientId && op.timestamp >= operation.timestamp) {
            operations.push(op);
          }
        }
      }

      return operations.sort((a, b) => a.timestamp.getTime() - b.timestamp.getTime());
    } catch (error) {
      Logger.error('Failed to get concurrent operations', error as Error);
      return [];
    }
  }

  /**
   * Transform operations for conflict resolution
   */
  private static transformOperations(op1: CollaborativeOperation, op2: CollaborativeOperation): {
    transformedOp: CollaborativeOperation;
    hasConflict: boolean;
  } {
    // Simplified operational transformation logic
    // In a production system, you'd want more sophisticated OT algorithms

    let hasConflict = false;
    const transformedOp = { ...op1 };

    if (op1.field === op2.field && op1.position !== undefined && op2.position !== undefined) {
      if (op1.type === 'insert' && op2.type === 'insert') {
        // Both are inserts
        if (op2.position <= op1.position) {
          transformedOp.position = op1.position + (op2.content?.length || 0);
        }
      } else if (op1.type === 'insert' && op2.type === 'delete') {
        // Op1 is insert, Op2 is delete
        if (op2.position < op1.position) {
          transformedOp.position = Math.max(0, op1.position - (op2.length || 0));
        }
      } else if (op1.type === 'delete' && op2.type === 'insert') {
        // Op1 is delete, Op2 is insert
        if (op2.position <= op1.position) {
          transformedOp.position = op1.position + (op2.content?.length || 0);
        }
      } else if (op1.type === 'delete' && op2.type === 'delete') {
        // Both are deletes - potential conflict
        hasConflict = true;
        if (op2.position < op1.position) {
          transformedOp.position = Math.max(0, op1.position - (op2.length || 0));
        }
      }
    }

    return { transformedOp, hasConflict };
  }

  /**
   * Get advanced board activity with operation history
   */
  static async getBoardActivityAdvanced(
    boardId: string,
    limit = 50,
    offset = 0,
    includeOperations = false
  ): Promise<{
    activities: ActivityEvent[];
    operations?: CollaborativeOperation[];
    totalCount: number;
  }> {
    try {
      // Get regular activities
      const activities = await this.getBoardActivity(boardId, limit, offset);

      const result: any = {
        activities: activities.map(activity => ({
          id: `${activity.boardId}-${activity.timestamp.getTime()}`,
          userId: activity.userId,
          boardId: activity.boardId,
          itemId: activity.itemId,
          type: activity.action,
          data: activity.data || {},
          timestamp: activity.timestamp,
        })),
        totalCount: activities.length,
      };

      if (includeOperations) {
        // Get recent operations for the board
        const operationPattern = `operation:*:*:*`; // This could be optimized
        const operationKeys = await RedisService.getKeysByPattern(operationPattern);

        const operations: CollaborativeOperation[] = [];
        for (const key of operationKeys.slice(0, limit)) {
          const opData = await RedisService.getCache(key);
          if (opData) {
            operations.push(JSON.parse(opData));
          }
        }

        result.operations = operations
          .filter(op => {
            // Filter operations related to this board's items
            // This is a simplified check - in production you'd want better filtering
            return true; // You'd check if the item belongs to the board
          })
          .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
          .slice(0, limit);
      }

      return result;
    } catch (error) {
      Logger.error('Failed to get advanced board activity', error as Error);
      return {
        activities: [],
        operations: includeOperations ? [] : undefined,
        totalCount: 0,
      };
    }
  }

  /**
   * Clean up expired data with advanced cleanup
   */
  static async cleanupExpiredDataAdvanced(): Promise<void> {
    try {
      // Call parent cleanup
      await this.cleanupExpiredData();

      // Clean up expired field locks
      const lockKeys = await RedisService.getKeysByPattern('lock:item:*:field:*');

      for (const lockKey of lockKeys) {
        const lockData = await RedisService.getCache(lockKey);
        if (lockData) {
          try {
            const lock: FieldLock = JSON.parse(lockData);
            if (new Date() > lock.expiresAt) {
              await RedisService.deleteCache(lockKey);

              // Emit lock expired event
              io.to(`item:${lock.itemId}`).emit('field_lock_expired', {
                itemId: lock.itemId,
                field: lock.field,
                userId: lock.userId,
                timestamp: new Date(),
              });
            }
          } catch (parseError) {
            // Remove invalid lock data
            await RedisService.deleteCache(lockKey);
          }
        }
      }

      // Clean up old operations
      const operationKeys = await RedisService.getKeysByPattern('operation:*');
      const cutoffTime = Date.now() - this.OPERATION_TTL * 1000;

      for (const opKey of operationKeys) {
        const opData = await RedisService.getCache(opKey);
        if (opData) {
          try {
            const operation: CollaborativeOperation = JSON.parse(opData);
            if (operation.timestamp.getTime() < cutoffTime) {
              await RedisService.deleteCache(opKey);
            }
          } catch (parseError) {
            await RedisService.deleteCache(opKey);
          }
        }
      }

      Logger.websocket('Advanced collaboration data cleanup completed');
    } catch (error) {
      Logger.error('Failed to cleanup advanced collaboration data', error as Error);
    }
  }

  /**
   * Get all active field locks for an item
   */
  static async getItemFieldLocks(itemId: string): Promise<FieldLock[]> {
    try {
      const pattern = `lock:item:${itemId}:field:*`;
      const lockKeys = await RedisService.getKeysByPattern(pattern);

      const locks: FieldLock[] = [];

      for (const lockKey of lockKeys) {
        const lockData = await RedisService.getCache(lockKey);
        if (lockData) {
          try {
            const lock: FieldLock = JSON.parse(lockData);
            if (new Date() <= lock.expiresAt) {
              locks.push(lock);
            }
          } catch (parseError) {
            Logger.error('Failed to parse lock data', parseError as Error);
          }
        }
      }

      return locks;
    } catch (error) {
      Logger.error('Failed to get item field locks', error as Error);
      return [];
    }
  }

  /**
   * Force release all locks for a user (useful for cleanup on disconnect)
   */
  static async releaseUserLocks(userId: string): Promise<void> {
    try {
      const pattern = 'lock:item:*:field:*';
      const lockKeys = await RedisService.getKeysByPattern(pattern);

      for (const lockKey of lockKeys) {
        const lockData = await RedisService.getCache(lockKey);
        if (lockData) {
          try {
            const lock: FieldLock = JSON.parse(lockData);
            if (lock.userId === userId) {
              await RedisService.deleteCache(lockKey);

              // Emit lock released event
              io.to(`item:${lock.itemId}`).emit('field_unlocked', {
                itemId: lock.itemId,
                field: lock.field,
                unlockedBy: { userId },
                reason: 'user_disconnect',
                timestamp: new Date(),
              });
            }
          } catch (parseError) {
            Logger.error('Failed to parse lock data during cleanup', parseError as Error);
          }
        }
      }

      Logger.websocket(`Released all locks for user ${userId}`);
    } catch (error) {
      Logger.error('Failed to release user locks', error as Error);
    }
  }
}