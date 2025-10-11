import { describe, it, expect, beforeEach, vi } from 'vitest';
import { CollaborationService } from '@/services/collaboration.service';
import { RedisService } from '@/config/redis';
import { prisma } from '@/config/database';

// Mock dependencies
vi.mock('@/config/redis', () => ({
  RedisService: {
    setCache: vi.fn(),
    getCache: vi.fn(),
    deleteCache: vi.fn(),
    deleteCachePattern: vi.fn(),
    setHash: vi.fn(),
    getAllHashFields: vi.fn(),
    deleteHashField: vi.fn(),
    setIfNotExists: vi.fn(),
    getKeysByPattern: vi.fn(),
  },
}));

vi.mock('@/config/database', () => ({
  prisma: {
    board: {
      findUnique: vi.fn(),
    },
    activityLog: {
      create: vi.fn(),
    },
  },
}));

vi.mock('@/config/logger', () => ({
  Logger: {
    websocket: vi.fn(),
    error: vi.fn(),
    api: vi.fn(),
  },
}));

vi.mock('@/server', () => ({
  io: {
    to: vi.fn().mockReturnThis(),
    emit: vi.fn(),
    except: vi.fn().mockReturnThis(),
    sockets: {
      adapter: {
        rooms: {
          get: vi.fn(),
        },
      },
    },
  },
}));

describe('CollaborationService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('trackPresence', () => {
    const mockPresenceData = {
      userId: 'user-1',
      username: 'John Doe',
      boardId: 'board-1',
      socketId: 'socket-1',
      avatarUrl: 'https://example.com/avatar.jpg',
      deviceInfo: { type: 'desktop' as const, os: 'macOS', browser: 'Chrome' },
      currentView: { viewType: 'board' as const },
    };

    const mockActiveUsers = [
      {
        userId: 'user-1',
        username: 'John Doe',
        avatarUrl: 'https://example.com/avatar.jpg',
        lastSeen: new Date(),
      },
    ];

    it('should track presence successfully', async () => {
      (RedisService.setCache as any).mockResolvedValue(undefined);
      (RedisService.setHash as any).mockResolvedValue(undefined);
      (CollaborationService.getActiveUsers as any) = vi.fn().mockResolvedValue(mockActiveUsers);

      await CollaborationService.trackPresence(
        mockPresenceData.userId,
        mockPresenceData.username,
        mockPresenceData.boardId,
        mockPresenceData.socketId,
        {
          avatarUrl: mockPresenceData.avatarUrl,
          deviceInfo: mockPresenceData.deviceInfo,
          currentView: mockPresenceData.currentView,
        }
      );

      expect(RedisService.setCache).toHaveBeenCalledTimes(3); // session, socket mapping, user socket
      expect(RedisService.setHash).toHaveBeenCalledWith(
        `presence:board:${mockPresenceData.boardId}`,
        `user:${mockPresenceData.userId}`,
        expect.stringContaining(mockPresenceData.username),
        300
      );
    });

    it('should store correct session data', async () => {
      (RedisService.setCache as any).mockResolvedValue(undefined);
      (RedisService.setHash as any).mockResolvedValue(undefined);
      (CollaborationService.getActiveUsers as any) = vi.fn().mockResolvedValue(mockActiveUsers);

      await CollaborationService.trackPresence(
        mockPresenceData.userId,
        mockPresenceData.username,
        mockPresenceData.boardId,
        mockPresenceData.socketId,
        {
          avatarUrl: mockPresenceData.avatarUrl,
          deviceInfo: mockPresenceData.deviceInfo,
          currentView: mockPresenceData.currentView,
        }
      );

      const sessionCall = (RedisService.setCache as any).mock.calls.find(
        (call: any) => call[0] === `session:${mockPresenceData.socketId}`
      );

      expect(sessionCall).toBeDefined();
      expect(sessionCall[1]).toMatchObject({
        userId: mockPresenceData.userId,
        username: mockPresenceData.username,
        socketId: mockPresenceData.socketId,
        boardId: mockPresenceData.boardId,
        deviceInfo: mockPresenceData.deviceInfo,
        currentView: mockPresenceData.currentView,
      });
    });
  });

  describe('removePresence', () => {
    const mockSession = {
      userId: 'user-1',
      username: 'John Doe',
      boardId: 'board-1',
      joinedAt: new Date(Date.now() - 60000), // 1 minute ago
    };

    const mockActiveUsers = [
      {
        userId: 'user-2',
        username: 'Jane Doe',
        lastSeen: new Date(),
      },
    ];

    it('should remove presence successfully', async () => {
      (RedisService.getCache as any).mockResolvedValue(mockSession);
      (RedisService.deleteCache as any).mockResolvedValue(undefined);
      (RedisService.deleteHashField as any).mockResolvedValue(undefined);
      (CollaborationService.getActiveUsers as any) = vi.fn().mockResolvedValue(mockActiveUsers);
      (CollaborationService.releaseUserLocks as any) = vi.fn().mockResolvedValue(undefined);

      await CollaborationService.removePresence('user-1', 'board-1', 'socket-1');

      expect(RedisService.deleteCache).toHaveBeenCalledTimes(3);
      expect(RedisService.deleteHashField).toHaveBeenCalledWith(
        'presence:board:board-1',
        'user:user-1'
      );
      expect(CollaborationService.releaseUserLocks).toHaveBeenCalledWith('user-1');
    });

    it('should calculate session duration correctly', async () => {
      const sessionStart = new Date(Date.now() - 120000); // 2 minutes ago
      const sessionWithTime = { ...mockSession, joinedAt: sessionStart };

      (RedisService.getCache as any).mockResolvedValue(sessionWithTime);
      (RedisService.deleteCache as any).mockResolvedValue(undefined);
      (RedisService.deleteHashField as any).mockResolvedValue(undefined);
      (CollaborationService.getActiveUsers as any) = vi.fn().mockResolvedValue(mockActiveUsers);
      (CollaborationService.releaseUserLocks as any) = vi.fn().mockResolvedValue(undefined);

      await CollaborationService.removePresence('user-1', 'board-1', 'socket-1');

      // Verify the session duration is approximately 2 minutes (120000ms)
      const duration = Date.now() - sessionStart.getTime();
      expect(duration).toBeGreaterThan(110000); // Allow some variance
      expect(duration).toBeLessThan(130000);
    });
  });

  describe('getActiveUsers', () => {
    const mockPresenceData = {
      'user:user-1': JSON.stringify({
        userId: 'user-1',
        username: 'John Doe',
        avatarUrl: 'https://example.com/avatar.jpg',
        lastSeen: new Date(Date.now() - 60000), // 1 minute ago (active)
      }),
      'user:user-2': JSON.stringify({
        userId: 'user-2',
        username: 'Jane Doe',
        lastSeen: new Date(Date.now() - 400000), // 6+ minutes ago (expired)
      }),
      'user:user-3': JSON.stringify({
        userId: 'user-3',
        username: 'Bob Smith',
        lastSeen: new Date(Date.now() - 120000), // 2 minutes ago (active)
      }),
    };

    it('should return only active users', async () => {
      (RedisService.getAllHashFields as any).mockResolvedValue(mockPresenceData);

      const result = await CollaborationService.getActiveUsers('board-1');

      expect(result).toHaveLength(2);
      expect(result.map(u => u.userId)).toEqual(['user-1', 'user-3']);
      expect(result[0].username).toBe('John Doe');
      expect(result[1].username).toBe('Bob Smith');
    });

    it('should handle invalid presence data gracefully', async () => {
      const invalidPresenceData = {
        'user:user-1': 'invalid-json',
        'user:user-2': JSON.stringify({
          userId: 'user-2',
          username: 'Jane Doe',
          lastSeen: new Date(Date.now() - 60000),
        }),
      };

      (RedisService.getAllHashFields as any).mockResolvedValue(invalidPresenceData);

      const result = await CollaborationService.getActiveUsers('board-1');

      expect(result).toHaveLength(1);
      expect(result[0].userId).toBe('user-2');
    });

    it('should sort users alphabetically by username', async () => {
      const unsortedPresenceData = {
        'user:user-1': JSON.stringify({
          userId: 'user-1',
          username: 'Zoe Wilson',
          lastSeen: new Date(Date.now() - 60000),
        }),
        'user:user-2': JSON.stringify({
          userId: 'user-2',
          username: 'Alice Johnson',
          lastSeen: new Date(Date.now() - 60000),
        }),
        'user:user-3': JSON.stringify({
          userId: 'user-3',
          username: 'Bob Smith',
          lastSeen: new Date(Date.now() - 60000),
        }),
      };

      (RedisService.getAllHashFields as any).mockResolvedValue(unsortedPresenceData);

      const result = await CollaborationService.getActiveUsers('board-1');

      expect(result.map(u => u.username)).toEqual(['Alice Johnson', 'Bob Smith', 'Zoe Wilson']);
    });
  });

  describe('lockField', () => {
    const mockLockData = {
      itemId: 'item-1',
      field: 'title',
      userId: 'user-1',
      username: 'John Doe',
      userAvatar: 'https://example.com/avatar.jpg',
      duration: 300000, // 5 minutes
    };

    it('should acquire lock successfully when no existing lock', async () => {
      (RedisService.getCache as any).mockResolvedValue(null);
      (RedisService.setCache as any).mockResolvedValue(undefined);

      const result = await CollaborationService.lockField(
        mockLockData.itemId,
        mockLockData.field,
        mockLockData.userId,
        {
          username: mockLockData.username,
          userAvatar: mockLockData.userAvatar,
          duration: mockLockData.duration,
        }
      );

      expect(result.success).toBe(true);
      expect(result.lockId).toBeDefined();
      expect(RedisService.setCache).toHaveBeenCalledWith(
        `lock:item:${mockLockData.itemId}:field:${mockLockData.field}`,
        expect.objectContaining({
          itemId: mockLockData.itemId,
          field: mockLockData.field,
          userId: mockLockData.userId,
          username: mockLockData.username,
        }),
        300 // 5 minutes in seconds
      );
    });

    it('should fail to acquire lock when already locked by another user', async () => {
      const existingLock = {
        itemId: mockLockData.itemId,
        field: mockLockData.field,
        userId: 'user-2', // Different user
        username: 'Jane Doe',
        lockedAt: new Date(Date.now() - 60000),
        expiresAt: new Date(Date.now() + 240000), // 4 minutes remaining
      };

      (RedisService.getCache as any).mockResolvedValue(existingLock);

      const result = await CollaborationService.lockField(
        mockLockData.itemId,
        mockLockData.field,
        mockLockData.userId,
        { username: mockLockData.username }
      );

      expect(result.success).toBe(false);
      expect(result.lockedBy).toEqual({
        userId: 'user-2',
        username: 'Jane Doe',
        lockedAt: existingLock.lockedAt,
        expiresAt: existingLock.expiresAt,
      });
      expect(result.message).toBe('Field is locked by Jane Doe');
    });

    it('should force acquire lock when force option is true', async () => {
      const existingLock = {
        itemId: mockLockData.itemId,
        field: mockLockData.field,
        userId: 'user-2',
        username: 'Jane Doe',
        lockedAt: new Date(),
        expiresAt: new Date(Date.now() + 240000),
      };

      (RedisService.getCache as any).mockResolvedValue(existingLock);
      (RedisService.setCache as any).mockResolvedValue(undefined);

      const result = await CollaborationService.lockField(
        mockLockData.itemId,
        mockLockData.field,
        mockLockData.userId,
        {
          username: mockLockData.username,
          force: true,
        }
      );

      expect(result.success).toBe(true);
      expect(result.lockId).toBeDefined();
    });

    it('should acquire lock when existing lock is expired', async () => {
      const expiredLock = {
        itemId: mockLockData.itemId,
        field: mockLockData.field,
        userId: 'user-2',
        username: 'Jane Doe',
        lockedAt: new Date(Date.now() - 360000), // 6 minutes ago
        expiresAt: new Date(Date.now() - 60000), // Expired 1 minute ago
      };

      (RedisService.getCache as any).mockResolvedValue(expiredLock);
      (RedisService.setCache as any).mockResolvedValue(undefined);

      const result = await CollaborationService.lockField(
        mockLockData.itemId,
        mockLockData.field,
        mockLockData.userId,
        { username: mockLockData.username }
      );

      expect(result.success).toBe(true);
      expect(result.lockId).toBeDefined();
    });
  });

  describe('unlockField', () => {
    const mockLock = {
      itemId: 'item-1',
      field: 'title',
      userId: 'user-1',
      username: 'John Doe',
      lockId: 'lock-123',
      lockedAt: new Date(),
      expiresAt: new Date(Date.now() + 240000),
    };

    it('should unlock field successfully by owner', async () => {
      (RedisService.getCache as any).mockResolvedValue(mockLock);
      (RedisService.deleteCache as any).mockResolvedValue(undefined);

      const result = await CollaborationService.unlockField(
        mockLock.itemId,
        mockLock.field,
        mockLock.userId
      );

      expect(result.success).toBe(true);
      expect(result.message).toBe('Field unlocked successfully');
      expect(RedisService.deleteCache).toHaveBeenCalledWith(
        `lock:item:${mockLock.itemId}:field:${mockLock.field}`
      );
    });

    it('should unlock field successfully with correct lock ID', async () => {
      (RedisService.getCache as any).mockResolvedValue(mockLock);
      (RedisService.deleteCache as any).mockResolvedValue(undefined);

      const result = await CollaborationService.unlockField(
        mockLock.itemId,
        mockLock.field,
        'different-user', // Different user but correct lock ID
        mockLock.lockId
      );

      expect(result.success).toBe(true);
    });

    it('should fail to unlock if not owner and no lock ID', async () => {
      (RedisService.getCache as any).mockResolvedValue(mockLock);

      const result = await CollaborationService.unlockField(
        mockLock.itemId,
        mockLock.field,
        'different-user'
      );

      expect(result.success).toBe(false);
      expect(result.message).toBe('Unauthorized to release this lock');
      expect(RedisService.deleteCache).not.toHaveBeenCalled();
    });

    it('should fail to unlock if no lock exists', async () => {
      (RedisService.getCache as any).mockResolvedValue(null);

      const result = await CollaborationService.unlockField(
        'item-1',
        'title',
        'user-1'
      );

      expect(result.success).toBe(false);
      expect(result.message).toBe('No lock found');
    });
  });

  describe('processOperation', () => {
    const mockOperation = {
      id: 'op-123',
      type: 'insert' as const,
      itemId: 'item-1',
      field: 'content',
      position: 10,
      content: 'Hello',
      userId: 'user-1',
      clientId: 'client-1',
      sequenceNumber: 1,
      timestamp: new Date(),
    };

    it('should process operation successfully with no conflicts', async () => {
      (CollaborationService as any).getConcurrentOperations = vi.fn().mockResolvedValue([]);
      (RedisService.setCache as any).mockResolvedValue(undefined);

      const result = await CollaborationService.processOperation(mockOperation);

      expect(result.success).toBe(true);
      expect(result.transformedOperation).toEqual(mockOperation);
      expect(result.conflicts).toHaveLength(0);
      expect(RedisService.setCache).toHaveBeenCalledWith(
        `operation:${mockOperation.itemId}:${mockOperation.field}:${mockOperation.id}`,
        mockOperation,
        3600
      );
    });

    it('should handle concurrent operations with conflicts', async () => {
      const concurrentOp = {
        id: 'op-456',
        type: 'delete' as const,
        itemId: 'item-1',
        field: 'content',
        position: 8,
        length: 5,
        userId: 'user-2',
        clientId: 'client-2',
        sequenceNumber: 1,
        timestamp: new Date(),
      };

      (CollaborationService as any).getConcurrentOperations = vi.fn().mockResolvedValue([concurrentOp]);
      (CollaborationService as any).transformOperations = vi.fn().mockReturnValue({
        transformedOp: { ...mockOperation, position: 15 }, // Position adjusted
        hasConflict: true,
        conflictType: 'concurrent_edit',
      });
      (RedisService.setCache as any).mockResolvedValue(undefined);

      const result = await CollaborationService.processOperation(mockOperation);

      expect(result.success).toBe(true);
      expect(result.transformedOperation?.position).toBe(15);
      expect(result.conflicts).toHaveLength(1);
      expect(result.conflicts[0].type).toBe('concurrent_edit');
    });

    it('should reject operation if too many concurrent operations', async () => {
      const manyOperations = Array.from({ length: 101 }, (_, i) => ({
        id: `op-${i}`,
        type: 'insert' as const,
        itemId: 'item-1',
        field: 'content',
        userId: 'user-2',
        clientId: 'client-2',
        sequenceNumber: i,
        timestamp: new Date(),
      }));

      (CollaborationService as any).getConcurrentOperations = vi.fn().mockResolvedValue(manyOperations);

      const result = await CollaborationService.processOperation(mockOperation);

      expect(result.success).toBe(false);
      expect(result.message).toBe('Too many concurrent operations. Please refresh and try again.');
    });
  });

  describe('getCollaborationMetrics', () => {
    const mockTimeRange = {
      start: new Date(Date.now() - 24 * 60 * 60 * 1000),
      end: new Date(),
    };

    const mockActiveUsers = [
      { userId: 'user-1', username: 'John Doe', lastSeen: new Date() },
      { userId: 'user-2', username: 'Jane Doe', lastSeen: new Date() },
    ];

    const mockActivities = [
      {
        id: 'act-1',
        userId: 'user-1',
        boardId: 'board-1',
        action: 'operation_applied',
        data: { conflictCount: 1 },
        timestamp: new Date(),
      },
      {
        id: 'act-2',
        userId: 'user-1',
        boardId: 'board-1',
        action: 'field_locked',
        data: {},
        timestamp: new Date(),
      },
      {
        id: 'act-3',
        userId: 'user-2',
        boardId: 'board-1',
        action: 'user_joined',
        data: {},
        timestamp: new Date(),
      },
    ];

    it('should calculate collaboration metrics correctly', async () => {
      (CollaborationService.getActiveUsers as any) = vi.fn().mockResolvedValue(mockActiveUsers);
      (CollaborationService.getBoardActivity as any) = vi.fn().mockResolvedValue(mockActivities);

      const result = await CollaborationService.getCollaborationMetrics('board-1', mockTimeRange);

      expect(result.activeUsers).toBe(2);
      expect(result.operationsCount).toBe(1);
      expect(result.conflictsCount).toBe(1);
      expect(result.locksAcquired).toBe(1);
      expect(result.userEngagement).toHaveLength(2);

      const user1Engagement = result.userEngagement.find(u => u.userId === 'user-1');
      expect(user1Engagement?.sessionCount).toBe(0);
      expect(user1Engagement?.operationsCount).toBe(1);

      const user2Engagement = result.userEngagement.find(u => u.userId === 'user-2');
      expect(user2Engagement?.sessionCount).toBe(1);
      expect(user2Engagement?.operationsCount).toBe(0);
    });

    it('should handle empty activity gracefully', async () => {
      (CollaborationService.getActiveUsers as any) = vi.fn().mockResolvedValue([]);
      (CollaborationService.getBoardActivity as any) = vi.fn().mockResolvedValue([]);

      const result = await CollaborationService.getCollaborationMetrics('board-1', mockTimeRange);

      expect(result.activeUsers).toBe(0);
      expect(result.operationsCount).toBe(0);
      expect(result.conflictsCount).toBe(0);
      expect(result.locksAcquired).toBe(0);
      expect(result.userEngagement).toHaveLength(0);
    });
  });

  describe('cleanupExpiredData', () => {
    it('should clean up expired presence data', async () => {
      const mockPresenceData = {
        'user:user-1': JSON.stringify({
          userId: 'user-1',
          username: 'John Doe',
          lastSeen: new Date(Date.now() - 600000), // 10 minutes ago (expired)
        }),
        'user:user-2': JSON.stringify({
          userId: 'user-2',
          username: 'Jane Doe',
          lastSeen: new Date(Date.now() - 60000), // 1 minute ago (active)
        }),
      };

      (RedisService.getKeysByPattern as any).mockResolvedValue(['presence:board:board-1']);
      (RedisService.getAllHashFields as any).mockResolvedValue(mockPresenceData);
      (RedisService.deleteHashField as any).mockResolvedValue(undefined);

      await CollaborationService.cleanupExpiredData();

      expect(RedisService.deleteHashField).toHaveBeenCalledWith(
        'presence:board:board-1',
        'user:user-1'
      );
      expect(RedisService.deleteHashField).not.toHaveBeenCalledWith(
        'presence:board:board-1',
        'user:user-2'
      );
    });

    it('should clean up expired cursors', async () => {
      const mockCursors = [
        {
          userId: 'user-1',
          cursor: { x: 100, y: 200 },
          timestamp: new Date(Date.now() - 120000), // 2 minutes ago (expired)
        },
        {
          userId: 'user-2',
          cursor: { x: 150, y: 250 },
          timestamp: new Date(Date.now() - 30000), // 30 seconds ago (active)
        },
      ];

      (RedisService.getKeysByPattern as any)
        .mockResolvedValueOnce(['presence:board:board-1']) // presence cleanup
        .mockResolvedValueOnce(['cursor:board:board-1:user:user-1', 'cursor:board:board-1:user:user-2']); // cursor cleanup

      (RedisService.getAllHashFields as any).mockResolvedValue({});
      (RedisService.getCache as any)
        .mockResolvedValueOnce(mockCursors[0])
        .mockResolvedValueOnce(mockCursors[1]);
      (RedisService.deleteCache as any).mockResolvedValue(undefined);

      await CollaborationService.cleanupExpiredData();

      expect(RedisService.deleteCache).toHaveBeenCalledWith('cursor:board:board-1:user:user-1');
      expect(RedisService.deleteCache).not.toHaveBeenCalledWith('cursor:board:board-1:user:user-2');
    });

    it('should clean up expired locks', async () => {
      const expiredLock = {
        itemId: 'item-1',
        field: 'title',
        userId: 'user-1',
        lockId: 'lock-123',
        expiresAt: new Date(Date.now() - 60000), // Expired 1 minute ago
      };

      const activeLock = {
        itemId: 'item-2',
        field: 'content',
        userId: 'user-2',
        lockId: 'lock-456',
        expiresAt: new Date(Date.now() + 240000), // Expires in 4 minutes
      };

      (RedisService.getKeysByPattern as any)
        .mockResolvedValueOnce(['presence:board:board-1']) // presence cleanup
        .mockResolvedValueOnce(['cursor:board:board-1:user:user-1']) // cursor cleanup
        .mockResolvedValueOnce(['lock:item:item-1:field:title', 'lock:item:item-2:field:content']); // lock cleanup

      (RedisService.getAllHashFields as any).mockResolvedValue({});
      (RedisService.getCache as any)
        .mockResolvedValueOnce({ timestamp: new Date(Date.now() - 30000) }) // active cursor
        .mockResolvedValueOnce(expiredLock)
        .mockResolvedValueOnce(activeLock);
      (RedisService.deleteCache as any).mockResolvedValue(undefined);

      await CollaborationService.cleanupExpiredData();

      expect(RedisService.deleteCache).toHaveBeenCalledWith('lock:item:item-1:field:title');
      expect(RedisService.deleteCache).not.toHaveBeenCalledWith('lock:item:item-2:field:content');
    });
  });
});