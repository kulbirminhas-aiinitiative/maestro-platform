import { AnalyticsService } from '../services/analytics.service';
import { prisma } from '../config/database';
import { RedisService } from '../config/redis';

// Mock external dependencies
jest.mock('../config/database', () => ({
  prisma: {
    board: {
      findUnique: jest.fn(),
    },
    boardMember: {
      findUnique: jest.fn(),
    },
    workspaceMember: {
      findUnique: jest.fn(),
    },
    organizationMember: {
      findUnique: jest.fn(),
    },
    $queryRaw: jest.fn(),
    $queryRawUnsafe: jest.fn(),
  },
}));

jest.mock('../config/redis');

describe('AnalyticsService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('getBoardAnalytics', () => {
    const mockBoardId = 'board-1';
    const mockUserId = 'user-1';

    it('should return board analytics from cache when available', async () => {
      const mockAnalytics = {
        boardId: mockBoardId,
        period: 'month',
        itemMetrics: { totalItems: 10, completedItems: 5 },
        generatedAt: new Date(),
      };

      (RedisService.getCache as jest.Mock).mockResolvedValue(
        JSON.stringify(mockAnalytics)
      );

      const result = await AnalyticsService.getBoardAnalytics(
        mockBoardId,
        mockUserId,
        'month'
      );

      expect(result).toEqual(mockAnalytics);
      expect(prisma.$queryRaw).not.toHaveBeenCalled();
    });

    it('should generate board analytics when not in cache', async () => {
      const mockBoardMember = {
        boardId: mockBoardId,
        userId: mockUserId,
        role: 'member',
      };

      const mockItemStats = {
        totalItems: BigInt(10),
        completedItems: BigInt(5),
        inProgressItems: BigInt(3),
        createdInPeriod: BigInt(2),
        completedInPeriod: BigInt(3),
      };

      const mockActivityStats = {
        totalActivities: BigInt(50),
        uniqueActiveUsers: BigInt(5),
        commentsCount: BigInt(20),
        filesUploadedCount: BigInt(3),
      };

      const mockTimeStats = {
        totalTimeSpent: BigInt(7200),
        billableTime: BigInt(3600),
        timeEntriesCount: BigInt(10),
      };

      (RedisService.getCache as jest.Mock).mockResolvedValue(null);
      (prisma.boardMember.findUnique as jest.Mock).mockResolvedValue(mockBoardMember);
      (prisma.boardMember.findMany as jest.Mock).mockResolvedValue([
        { role: 'admin' },
        { role: 'member' },
        { role: 'member' },
      ]);

      // Mock multiple $queryRaw calls for different stats
      (prisma.$queryRaw as jest.Mock)
        .mockResolvedValueOnce([mockItemStats])
        .mockResolvedValueOnce([mockActivityStats])
        .mockResolvedValueOnce([mockTimeStats])
        .mockResolvedValueOnce([{ completed: BigInt(2) }]);

      const result = await AnalyticsService.getBoardAnalytics(
        mockBoardId,
        mockUserId,
        'month'
      );

      expect(result).toEqual(
        expect.objectContaining({
          boardId: mockBoardId,
          period: 'month',
          itemMetrics: expect.objectContaining({
            totalItems: 10,
            completedItems: 5,
            completionRate: 50,
          }),
          activityMetrics: expect.objectContaining({
            totalActivities: 50,
            uniqueActiveUsers: 5,
          }),
          timeMetrics: expect.objectContaining({
            totalTimeSpent: 7200,
            billableTime: 3600,
          }),
        })
      );

      expect(RedisService.setCache).toHaveBeenCalled();
    });

    it('should throw error when user has no access to board', async () => {
      (RedisService.getCache as jest.Mock).mockResolvedValue(null);
      (prisma.boardMember.findUnique as jest.Mock).mockResolvedValue(null);

      await expect(
        AnalyticsService.getBoardAnalytics(mockBoardId, mockUserId, 'month')
      ).rejects.toThrow('Access denied to board');
    });
  });

  describe('getOrganizationAnalytics', () => {
    const mockOrgId = 'org-1';
    const mockUserId = 'user-1';

    it('should return organization analytics for admin user', async () => {
      const mockOrgMember = {
        organizationId: mockOrgId,
        userId: mockUserId,
        role: 'admin',
      };

      const mockStats = {
        totalUsers: BigInt(50),
        activeUsers: BigInt(30),
        totalWorkspaces: BigInt(5),
        totalBoards: BigInt(25),
        totalItems: BigInt(500),
        completedItems: BigInt(300),
        totalTimeSpent: BigInt(36000),
        totalComments: BigInt(150),
        totalFiles: BigInt(75),
      };

      (RedisService.getCache as jest.Mock).mockResolvedValue(null);
      (prisma.organizationMember.findUnique as jest.Mock).mockResolvedValue(mockOrgMember);
      (prisma.$queryRaw as jest.Mock).mockResolvedValue([mockStats]);

      const result = await AnalyticsService.getOrganizationAnalytics(
        mockOrgId,
        mockUserId,
        'month'
      );

      expect(result).toEqual(
        expect.objectContaining({
          organizationId: mockOrgId,
          period: 'month',
          userMetrics: expect.objectContaining({
            totalUsers: 50,
            activeUsers: 30,
          }),
          itemMetrics: expect.objectContaining({
            totalItems: 500,
            completedItems: 300,
            completionRate: 60,
          }),
        })
      );

      expect(RedisService.setCache).toHaveBeenCalled();
    });

    it('should throw error when user is not admin', async () => {
      const mockOrgMember = {
        organizationId: mockOrgId,
        userId: mockUserId,
        role: 'member',
      };

      (RedisService.getCache as jest.Mock).mockResolvedValue(null);
      (prisma.organizationMember.findUnique as jest.Mock).mockResolvedValue(mockOrgMember);

      await expect(
        AnalyticsService.getOrganizationAnalytics(mockOrgId, mockUserId, 'month')
      ).rejects.toThrow('Access denied to organization analytics');
    });
  });

  describe('getUserActivityReport', () => {
    const mockUserId = 'user-1';
    const mockRequestingUserId = 'user-1';

    it('should return user activity report for own data', async () => {
      const result = await AnalyticsService.getUserActivityReport(
        mockUserId,
        mockRequestingUserId,
        'month'
      );

      expect(result).toEqual(
        expect.objectContaining({
          userId: mockUserId,
          period: 'month',
          activitySummary: expect.any(Object),
          timeSpent: expect.any(Object),
          generatedAt: expect.any(Date),
        })
      );
    });

    it('should check permissions when requesting other users data', async () => {
      const otherUserId = 'user-2';

      // Mock no shared workspace admin access
      (prisma.workspaceMember.findMany as jest.Mock).mockResolvedValue([]);

      await expect(
        AnalyticsService.getUserActivityReport(
          otherUserId,
          mockRequestingUserId,
          'month'
        )
      ).rejects.toThrow('Access denied to user data');
    });
  });

  describe('generateCustomReport', () => {
    const mockUserId = 'user-1';

    it('should generate custom report with organization filter', async () => {
      const mockFilter = {
        organizationId: 'org-1',
        startDate: new Date('2024-01-01'),
        endDate: new Date('2024-01-31'),
      };

      const mockOrgMember = {
        organizationId: mockFilter.organizationId,
        userId: mockUserId,
        role: 'admin',
      };

      const mockData = [
        { id: 'activity-1', action: 'item_created' },
        { id: 'activity-2', action: 'item_updated' },
      ];

      (prisma.organizationMember.findUnique as jest.Mock).mockResolvedValue(mockOrgMember);
      (prisma.$queryRawUnsafe as jest.Mock).mockResolvedValue(mockData);

      const result = await AnalyticsService.generateCustomReport(mockFilter, mockUserId);

      expect(result).toEqual({
        filter: mockFilter,
        data: mockData,
        generatedAt: expect.any(Date),
      });

      expect(prisma.$queryRawUnsafe).toHaveBeenCalledWith(
        expect.stringContaining('SELECT * FROM activity_log WHERE 1=1'),
        mockFilter.organizationId,
        mockFilter.startDate.toISOString(),
        mockFilter.endDate.toISOString()
      );
    });

    it('should throw error for workspace filter without access', async () => {
      const mockFilter = {
        workspaceId: 'workspace-1',
      };

      (prisma.workspaceMember.findUnique as jest.Mock).mockResolvedValue(null);

      await expect(
        AnalyticsService.generateCustomReport(mockFilter, mockUserId)
      ).rejects.toThrow('Access denied to workspace data');
    });
  });
});