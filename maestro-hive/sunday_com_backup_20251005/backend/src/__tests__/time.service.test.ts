import { TimeService } from '../services/time.service';
import { prisma } from '../config/database';
import { RedisService } from '../config/redis';

// Mock external dependencies
jest.mock('../config/database', () => ({
  prisma: {
    timeEntry: {
      create: jest.fn(),
      findFirst: jest.fn(),
      findMany: jest.fn(),
      count: jest.fn(),
      update: jest.fn(),
      delete: jest.fn(),
    },
    $queryRaw: jest.fn(),
    board: {
      findUnique: jest.fn(),
    },
    item: {
      findUnique: jest.fn(),
    },
    boardMember: {
      findUnique: jest.fn(),
    },
    activityLog: {
      create: jest.fn(),
    },
  },
}));

jest.mock('../config/redis');
jest.mock('../server', () => ({
  io: {
    to: jest.fn().mockReturnValue({
      emit: jest.fn(),
    }),
  },
}));

describe('TimeService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('startTimer', () => {
    const mockUser = { id: 'user-1' };
    const mockTimeEntryData = {
      itemId: 'item-1',
      boardId: 'board-1',
      description: 'Working on feature',
    };

    it('should start a new timer successfully', async () => {
      const mockTimeEntry = {
        id: 'timer-1',
        userId: mockUser.id,
        itemId: mockTimeEntryData.itemId,
        boardId: mockTimeEntryData.boardId,
        description: mockTimeEntryData.description,
        startTime: new Date(),
        isRunning: true,
        user: { firstName: 'John' },
        item: { board: { id: 'board-1' } },
      };

      // Mock successful item access check
      (prisma.item.findUnique as jest.Mock).mockResolvedValue({
        id: 'item-1',
        board: {
          members: [{ userId: mockUser.id }],
          workspace: { members: [] },
        },
      });

      // Mock successful timer creation
      (prisma.timeEntry.create as jest.Mock).mockResolvedValue(mockTimeEntry);

      // Mock stopping existing timers
      (prisma.timeEntry.findMany as jest.Mock).mockResolvedValue([]);

      const result = await TimeService.startTimer(mockTimeEntryData, mockUser.id);

      expect(result).toEqual(mockTimeEntry);
      expect(prisma.timeEntry.create).toHaveBeenCalledWith({
        data: expect.objectContaining({
          userId: mockUser.id,
          itemId: mockTimeEntryData.itemId,
          boardId: mockTimeEntryData.boardId,
          description: mockTimeEntryData.description,
          isRunning: true,
          billable: false,
        }),
        include: expect.any(Object),
      });
    });

    it('should throw error when user has no access to item', async () => {
      // Mock item not found or no access
      (prisma.item.findUnique as jest.Mock).mockResolvedValue(null);

      await expect(
        TimeService.startTimer(mockTimeEntryData, mockUser.id)
      ).rejects.toThrow('Access denied to item');
    });
  });

  describe('stopTimer', () => {
    const mockUser = { id: 'user-1' };

    it('should stop active timer successfully', async () => {
      const mockActiveTimer = {
        id: 'timer-1',
        userId: mockUser.id,
        startTime: new Date(Date.now() - 3600000), // 1 hour ago
        isRunning: true,
        user: { firstName: 'John' },
        item: { board: { id: 'board-1' } },
      };

      const mockUpdatedTimer = {
        ...mockActiveTimer,
        endTime: new Date(),
        duration: 3600, // 1 hour in seconds
        isRunning: false,
      };

      (prisma.timeEntry.findFirst as jest.Mock).mockResolvedValue(mockActiveTimer);
      (prisma.timeEntry.update as jest.Mock).mockResolvedValue(mockUpdatedTimer);

      const result = await TimeService.stopTimer(mockUser.id);

      expect(result).toEqual(mockUpdatedTimer);
      expect(prisma.timeEntry.update).toHaveBeenCalledWith({
        where: { id: mockActiveTimer.id },
        data: expect.objectContaining({
          isRunning: false,
          duration: expect.any(Number),
        }),
        include: expect.any(Object),
      });
    });

    it('should return null when no active timer exists', async () => {
      (prisma.timeEntry.findFirst as jest.Mock).mockResolvedValue(null);

      const result = await TimeService.stopTimer(mockUser.id);

      expect(result).toBeNull();
      expect(prisma.timeEntry.update).not.toHaveBeenCalled();
    });
  });

  describe('getActiveTimer', () => {
    const mockUser = { id: 'user-1' };

    it('should return active timer from cache when available', async () => {
      const mockActiveTimer = {
        id: 'timer-1',
        userId: mockUser.id,
        isRunning: true,
      };

      (RedisService.getCache as jest.Mock).mockResolvedValue(
        JSON.stringify(mockActiveTimer)
      );

      const result = await TimeService.getActiveTimer(mockUser.id);

      expect(result).toEqual(mockActiveTimer);
      expect(prisma.timeEntry.findFirst).not.toHaveBeenCalled();
    });

    it('should return active timer from database when not in cache', async () => {
      const mockActiveTimer = {
        id: 'timer-1',
        userId: mockUser.id,
        isRunning: true,
        user: { firstName: 'John' },
        item: { board: { id: 'board-1' } },
      };

      (RedisService.getCache as jest.Mock).mockResolvedValue(null);
      (prisma.timeEntry.findFirst as jest.Mock).mockResolvedValue(mockActiveTimer);

      const result = await TimeService.getActiveTimer(mockUser.id);

      expect(result).toEqual(mockActiveTimer);
      expect(RedisService.setCache).toHaveBeenCalledWith(
        `active_timer:${mockUser.id}`,
        JSON.stringify(mockActiveTimer),
        86400
      );
    });
  });

  describe('getTimeEntries', () => {
    const mockUser = { id: 'user-1' };

    it('should return paginated time entries', async () => {
      const mockTimeEntries = [
        { id: 'entry-1', userId: mockUser.id, duration: 3600 },
        { id: 'entry-2', userId: mockUser.id, duration: 1800 },
      ];

      (prisma.timeEntry.findMany as jest.Mock).mockResolvedValue(mockTimeEntries);
      (prisma.timeEntry.count as jest.Mock).mockResolvedValue(2);

      const result = await TimeService.getTimeEntries({}, mockUser.id, 1, 10);

      expect(result.data).toEqual(mockTimeEntries);
      expect(result.meta).toEqual({
        page: 1,
        limit: 10,
        total: 2,
        totalPages: 1,
        hasNext: false,
        hasPrev: false,
      });
    });

    it('should apply filters correctly', async () => {
      const filter = {
        billable: true,
        startDate: '2024-01-01',
        endDate: '2024-01-31',
      };

      (prisma.timeEntry.findMany as jest.Mock).mockResolvedValue([]);
      (prisma.timeEntry.count as jest.Mock).mockResolvedValue(0);

      await TimeService.getTimeEntries(filter, mockUser.id);

      expect(prisma.timeEntry.findMany).toHaveBeenCalledWith({
        where: expect.objectContaining({
          userId: mockUser.id,
          billable: true,
          startTime: {
            gte: new Date('2024-01-01'),
            lte: new Date('2024-01-31'),
          },
        }),
        include: expect.any(Object),
        orderBy: { startTime: 'desc' },
        skip: 0,
        take: 50,
      });
    });
  });

  describe('getStatistics', () => {
    const mockUser = { id: 'user-1' };

    it('should return time tracking statistics', async () => {
      const mockStats = {
        totalTime: BigInt(7200),
        billableTime: BigInt(3600),
        entriesCount: BigInt(5),
        averageSessionDuration: 1440,
      };

      const mockTopItems = [
        {
          itemId: 'item-1',
          itemName: 'Task 1',
          totalTime: BigInt(3600),
        },
      ];

      (prisma.$queryRaw as jest.Mock)
        .mockResolvedValueOnce([mockStats])
        .mockResolvedValueOnce(mockTopItems);

      const result = await TimeService.getStatistics(mockUser.id);

      expect(result).toEqual({
        totalTime: 7200,
        billableTime: 3600,
        entriesCount: 5,
        averageSessionDuration: 1440,
        topItems: [
          {
            itemId: 'item-1',
            itemName: 'Task 1',
            totalTime: 3600,
          },
        ],
      });
    });
  });
});