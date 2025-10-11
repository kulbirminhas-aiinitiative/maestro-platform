import { Server as SocketIOServer } from 'socket.io';
import jwt from 'jsonwebtoken';
import { prismaMock } from './setup';
import { WebSocketService } from '@/services/websocket.service';
import { CollaborationService } from '@/services/collaboration.service';

// Mock dependencies
jest.mock('jsonwebtoken');
jest.mock('@/services/collaboration.service');
jest.mock('@/config', () => ({
  config: {
    security: {
      jwtSecret: 'test-secret',
    },
  },
}));

// Mock Socket.IO
const mockSocket = {
  id: 'socket-1',
  userId: 'user-1',
  userEmail: 'test@example.com',
  userName: 'John Doe',
  organizationId: 'org-1',
  handshake: {
    auth: { token: 'valid-token' },
    headers: {},
  },
  join: jest.fn(),
  leave: jest.fn(),
  emit: jest.fn(),
  to: jest.fn(() => ({ emit: jest.fn() })),
  on: jest.fn(),
};

const mockIO = {
  use: jest.fn(),
  on: jest.fn(),
  to: jest.fn(() => ({ emit: jest.fn() })),
  in: jest.fn(() => ({ fetchSockets: jest.fn(() => Promise.resolve([])) })),
} as unknown as SocketIOServer;

describe('WebSocketService', () => {
  beforeEach(() => {
    jest.clearAllMocks();

    // Mock JWT verification
    (jwt.verify as jest.Mock).mockReturnValue({
      sub: 'user-1',
      email: 'test@example.com',
    });

    // Mock user lookup
    prismaMock.user.findUnique.mockResolvedValue({
      id: 'user-1',
      email: 'test@example.com',
      firstName: 'John',
      lastName: 'Doe',
      organizations: [
        {
          organizationId: 'org-1',
          role: 'member',
        },
      ],
    } as any);
  });

  describe('initialize', () => {
    it('should initialize WebSocket service', () => {
      WebSocketService.initialize(mockIO);

      expect(mockIO.use).toHaveBeenCalled();
      expect(mockIO.on).toHaveBeenCalledWith('connection', expect.any(Function));
    });
  });

  describe('authentication middleware', () => {
    let authMiddleware: (socket: any, next: any) => Promise<void>;

    beforeEach(() => {
      WebSocketService.initialize(mockIO);
      authMiddleware = (mockIO.use as jest.Mock).mock.calls[0][0];
    });

    it('should authenticate valid token', async () => {
      const next = jest.fn();
      const socket = {
        handshake: {
          auth: { token: 'valid-token' },
          headers: {},
        },
      };

      await authMiddleware(socket, next);

      expect(jwt.verify).toHaveBeenCalledWith('valid-token', 'test-secret');
      expect(prismaMock.user.findUnique).toHaveBeenCalled();
      expect(socket).toMatchObject({
        userId: 'user-1',
        userEmail: 'test@example.com',
        userName: 'John Doe',
        organizationId: 'org-1',
      });
      expect(next).toHaveBeenCalledWith();
    });

    it('should reject missing token', async () => {
      const next = jest.fn();
      const socket = {
        handshake: {
          auth: {},
          headers: {},
        },
      };

      await authMiddleware(socket, next);

      expect(next).toHaveBeenCalledWith(new Error('Authentication token required'));
    });

    it('should reject invalid token', async () => {
      const next = jest.fn();
      const socket = {
        handshake: {
          auth: { token: 'invalid-token' },
          headers: {},
        },
      };

      (jwt.verify as jest.Mock).mockImplementation(() => {
        throw new Error('Invalid token');
      });

      await authMiddleware(socket, next);

      expect(next).toHaveBeenCalledWith(new Error('Authentication failed'));
    });

    it('should reject when user not found', async () => {
      const next = jest.fn();
      const socket = {
        handshake: {
          auth: { token: 'valid-token' },
          headers: {},
        },
      };

      prismaMock.user.findUnique.mockResolvedValue(null);

      await authMiddleware(socket, next);

      expect(next).toHaveBeenCalledWith(new Error('User not found'));
    });
  });

  describe('connection handling', () => {
    let connectionHandler: (socket: any) => void;

    beforeEach(() => {
      WebSocketService.initialize(mockIO);
      connectionHandler = (mockIO.on as jest.Mock).mock.calls[0][1];
    });

    it('should handle new connection', () => {
      connectionHandler(mockSocket);

      expect(mockSocket.on).toHaveBeenCalledWith('join_board', expect.any(Function));
      expect(mockSocket.on).toHaveBeenCalledWith('leave_board', expect.any(Function));
      expect(mockSocket.on).toHaveBeenCalledWith('cursor_move', expect.any(Function));
      expect(mockSocket.on).toHaveBeenCalledWith('typing_start', expect.any(Function));
      expect(mockSocket.on).toHaveBeenCalledWith('typing_stop', expect.any(Function));
      expect(mockSocket.on).toHaveBeenCalledWith('disconnect', expect.any(Function));
    });
  });

  describe('board management', () => {
    beforeEach(() => {
      // Mock board access check
      jest.doMock('@/services/board.service', () => ({
        BoardService: {
          hasReadAccess: jest.fn().mockResolvedValue(true),
        },
      }));
    });

    it('should handle join board successfully', async () => {
      const handleJoinBoard = (WebSocketService as any).handleJoinBoard;

      (CollaborationService.trackPresence as jest.Mock).mockResolvedValue(undefined);

      await handleJoinBoard(mockSocket, 'board-1');

      expect(mockSocket.join).toHaveBeenCalledWith('board:board-1');
      expect(CollaborationService.trackPresence).toHaveBeenCalledWith(
        'user-1',
        'John Doe',
        'board-1',
        'socket-1',
        undefined
      );
      expect(mockSocket.emit).toHaveBeenCalledWith('board_joined', {
        boardId: 'board-1',
        joinedAt: expect.any(String),
      });
    });

    it('should handle leave board', async () => {
      const handleLeaveBoard = (WebSocketService as any).handleLeaveBoard;

      (CollaborationService.removePresence as jest.Mock).mockResolvedValue(undefined);

      await handleLeaveBoard(mockSocket, 'board-1');

      expect(mockSocket.leave).toHaveBeenCalledWith('board:board-1');
      expect(CollaborationService.removePresence).toHaveBeenCalledWith(
        'user-1',
        'board-1',
        'socket-1'
      );
      expect(mockSocket.emit).toHaveBeenCalledWith('board_left', {
        boardId: 'board-1',
        leftAt: expect.any(String),
      });
    });
  });

  describe('collaboration features', () => {
    it('should handle cursor movement', async () => {
      const handleCursorMove = (WebSocketService as any).handleCursorMove;

      (CollaborationService.updateCursor as jest.Mock).mockResolvedValue(undefined);

      const data = {
        boardId: 'board-1',
        cursor: { x: 100, y: 200 },
      };

      await handleCursorMove(mockSocket, data);

      expect(CollaborationService.updateCursor).toHaveBeenCalledWith(
        'user-1',
        'board-1',
        { x: 100, y: 200 }
      );

      expect(mockSocket.to).toHaveBeenCalledWith('board:board-1');
    });

    it('should handle typing start', async () => {
      const handleTypingStart = (WebSocketService as any).handleTypingStart;

      (CollaborationService.handleTyping as jest.Mock).mockResolvedValue(undefined);

      await handleTypingStart(mockSocket, 'item-1');

      expect(CollaborationService.handleTyping).toHaveBeenCalledWith(
        'user-1',
        'John Doe',
        'item-1',
        true
      );

      expect(mockSocket.to).toHaveBeenCalledWith('item:item-1');
    });

    it('should handle typing stop', async () => {
      const handleTypingStop = (WebSocketService as any).handleTypingStop;

      (CollaborationService.handleTyping as jest.Mock).mockResolvedValue(undefined);

      await handleTypingStop(mockSocket, 'item-1');

      expect(CollaborationService.handleTyping).toHaveBeenCalledWith(
        'user-1',
        'John Doe',
        'item-1',
        false
      );

      expect(mockSocket.to).toHaveBeenCalledWith('item:item-1');
    });
  });

  describe('item locking', () => {
    it('should handle successful item lock', async () => {
      const handleItemLock = (WebSocketService as any).handleItemLock;

      (CollaborationService.lockItem as jest.Mock).mockResolvedValue({
        success: true,
      });

      await handleItemLock(mockSocket, 'item-1');

      expect(CollaborationService.lockItem).toHaveBeenCalledWith(
        'item-1',
        'user-1',
        'John Doe'
      );

      expect(mockSocket.emit).toHaveBeenCalledWith('item_locked', {
        itemId: 'item-1',
        lockedBy: 'user-1',
        lockedAt: expect.any(String),
      });

      expect(mockSocket.to).toHaveBeenCalledWith('item:item-1');
    });

    it('should handle failed item lock', async () => {
      const handleItemLock = (WebSocketService as any).handleItemLock;

      (CollaborationService.lockItem as jest.Mock).mockResolvedValue({
        success: false,
        lockedBy: 'Other User',
      });

      await handleItemLock(mockSocket, 'item-1');

      expect(mockSocket.emit).toHaveBeenCalledWith('item_lock_failed', {
        itemId: 'item-1',
        reason: 'Item is locked by Other User',
      });
    });

    it('should handle item unlock', async () => {
      const handleItemUnlock = (WebSocketService as any).handleItemUnlock;

      (CollaborationService.unlockItem as jest.Mock).mockResolvedValue(true);

      await handleItemUnlock(mockSocket, 'item-1');

      expect(CollaborationService.unlockItem).toHaveBeenCalledWith('item-1', 'user-1');

      expect(mockSocket.emit).toHaveBeenCalledWith('item_unlocked', {
        itemId: 'item-1',
        unlockedAt: expect.any(String),
      });

      expect(mockSocket.to).toHaveBeenCalledWith('item:item-1');
    });
  });

  describe('public methods', () => {
    beforeEach(() => {
      WebSocketService.initialize(mockIO);
    });

    it('should send message to user', () => {
      const connectedUsers = new Map();
      connectedUsers.set('user-1', mockSocket);
      (WebSocketService as any).connectedUsers = connectedUsers;

      WebSocketService.sendToUser('user-1', 'test_event', { message: 'test' });

      expect(mockSocket.emit).toHaveBeenCalledWith('test_event', { message: 'test' });
    });

    it('should send message to room', () => {
      WebSocketService.sendToRoom('test-room', 'test_event', { message: 'test' });

      expect(mockIO.to).toHaveBeenCalledWith('test-room');
    });

    it('should send message to board', () => {
      WebSocketService.sendToBoard('board-1', 'test_event', { message: 'test' });

      expect(mockIO.to).toHaveBeenCalledWith('board:board-1');
    });

    it('should send message to item', () => {
      WebSocketService.sendToItem('item-1', 'test_event', { message: 'test' });

      expect(mockIO.to).toHaveBeenCalledWith('item:item-1');
    });

    it('should get connected user count', () => {
      const connectedUsers = new Map();
      connectedUsers.set('user-1', mockSocket);
      connectedUsers.set('user-2', mockSocket);
      (WebSocketService as any).connectedUsers = connectedUsers;

      const count = WebSocketService.getConnectedUserCount();

      expect(count).toBe(2);
    });

    it('should check if user is connected', () => {
      const connectedUsers = new Map();
      connectedUsers.set('user-1', mockSocket);
      (WebSocketService as any).connectedUsers = connectedUsers;

      expect(WebSocketService.isUserConnected('user-1')).toBe(true);
      expect(WebSocketService.isUserConnected('user-2')).toBe(false);
    });
  });

  describe('disconnection handling', () => {
    it('should handle disconnection', async () => {
      const handleDisconnection = (WebSocketService as any).handleDisconnection;

      (CollaborationService.handleDisconnection as jest.Mock).mockResolvedValue(undefined);

      await handleDisconnection(mockSocket, 'client namespace disconnect');

      expect(CollaborationService.handleDisconnection).toHaveBeenCalledWith('socket-1');
    });
  });
});