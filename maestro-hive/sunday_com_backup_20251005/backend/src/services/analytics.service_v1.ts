import { prisma } from '@/config/database';
import { RedisService } from '@/config/redis';
import { Logger } from '@/config/logger';
import {
  AnalyticsFilter,
  AnalyticsMetrics,
  TeamProductivityReport,
  BoardAnalytics,
  UserActivityReport,
} from '@/types';

export class AnalyticsService {
  private static readonly CACHE_TTL = 1800; // 30 minutes

  /**
   * Get board analytics and metrics
   */
  static async getBoardAnalytics(
    boardId: string,
    userId: string,
    period: 'day' | 'week' | 'month' | 'year' = 'month'
  ): Promise<BoardAnalytics> {
    try {
      const cacheKey = `analytics:board:${boardId}:${period}`;
      const cached = await RedisService.getCache(cacheKey);
      if (cached) {
        return JSON.parse(cached);
      }

      // Check if user has access to board
      const hasAccess = await this.checkBoardAccess(boardId, userId);
      if (!hasAccess) {
        throw new Error('Access denied to board');
      }

      const dateRange = this.getDateRange(period);

      const [
        itemStats,
        activityStats,
        memberStats,
        timeStats,
        velocityStats,
      ] = await Promise.all([
        this.getBoardItemStats(boardId, dateRange.start, dateRange.end),
        this.getBoardActivityStats(boardId, dateRange.start, dateRange.end),
        this.getBoardMemberStats(boardId, dateRange.start, dateRange.end),
        this.getBoardTimeStats(boardId, dateRange.start, dateRange.end),
        this.getBoardVelocityStats(boardId, period),
      ]);

      const analytics: BoardAnalytics = {
        boardId,
        period,
        dateRange,
        itemMetrics: itemStats,
        activityMetrics: activityStats,
        memberMetrics: memberStats,
        timeMetrics: timeStats,
        velocityMetrics: velocityStats,
        generatedAt: new Date(),
      };

      // Cache for 30 minutes
      await RedisService.setCache(cacheKey, JSON.stringify(analytics), this.CACHE_TTL);

      return analytics;
    } catch (error) {
      Logger.error('Get board analytics failed', error as Error);
      throw error;
    }
  }

  /**
   * Get user activity report
   */
  static async getUserActivityReport(
    userId: string,
    requestingUserId: string,
    period: 'day' | 'week' | 'month' | 'year' = 'month'
  ): Promise<UserActivityReport> {
    try {
      // Check if user can view the requested user's data
      if (userId !== requestingUserId) {
        const canViewUserData = await this.canViewUserData(requestingUserId, userId);
        if (!canViewUserData) {
          throw new Error('Access denied to user data');
        }
      }

      const dateRange = this.getDateRange(period);

      const [
        activitySummary,
        itemsWorked,
        timeSpent,
        collaborationMetrics,
        productivityTrends,
      ] = await Promise.all([
        this.getUserActivitySummary(userId, dateRange.start, dateRange.end),
        this.getUserItemsWorked(userId, dateRange.start, dateRange.end),
        this.getUserTimeSpent(userId, dateRange.start, dateRange.end),
        this.getUserCollaborationMetrics(userId, dateRange.start, dateRange.end),
        this.getUserProductivityTrends(userId, period),
      ]);

      return {
        userId,
        period,
        dateRange,
        activitySummary,
        itemsWorked,
        timeSpent,
        collaborationMetrics,
        productivityTrends,
        generatedAt: new Date(),
      };
    } catch (error) {
      Logger.error('Get user activity report failed', error as Error);
      throw error;
    }
  }

  /**
   * Get team productivity report
   */
  static async getTeamProductivityReport(
    workspaceId: string,
    userId: string,
    period: 'day' | 'week' | 'month' | 'year' = 'month'
  ): Promise<TeamProductivityReport> {
    try {
      // Check if user has access to workspace
      const hasAccess = await this.checkWorkspaceAccess(workspaceId, userId);
      if (!hasAccess) {
        throw new Error('Access denied to workspace');
      }

      const dateRange = this.getDateRange(period);

      const [
        teamOverview,
        memberPerformance,
        boardsProgress,
        timeDistribution,
        collaborationInsights,
      ] = await Promise.all([
        this.getTeamOverview(workspaceId, dateRange.start, dateRange.end),
        this.getMemberPerformance(workspaceId, dateRange.start, dateRange.end),
        this.getBoardsProgress(workspaceId, dateRange.start, dateRange.end),
        this.getTimeDistribution(workspaceId, dateRange.start, dateRange.end),
        this.getCollaborationInsights(workspaceId, dateRange.start, dateRange.end),
      ]);

      return {
        workspaceId,
        period,
        dateRange,
        teamOverview,
        memberPerformance,
        boardsProgress,
        timeDistribution,
        collaborationInsights,
        generatedAt: new Date(),
      };
    } catch (error) {
      Logger.error('Get team productivity report failed', error as Error);
      throw error;
    }
  }

  /**
   * Get organization-wide analytics
   */
  static async getOrganizationAnalytics(
    organizationId: string,
    userId: string,
    period: 'day' | 'week' | 'month' | 'year' = 'month'
  ): Promise<AnalyticsMetrics> {
    try {
      // Check if user has admin access to organization
      const hasAccess = await this.checkOrganizationAdminAccess(organizationId, userId);
      if (!hasAccess) {
        throw new Error('Access denied to organization analytics');
      }

      const cacheKey = `analytics:org:${organizationId}:${period}`;
      const cached = await RedisService.getCache(cacheKey);
      if (cached) {
        return JSON.parse(cached);
      }

      const dateRange = this.getDateRange(period);

      const [stats] = await prisma.$queryRaw<Array<{
        totalUsers: bigint;
        activeUsers: bigint;
        totalWorkspaces: bigint;
        totalBoards: bigint;
        totalItems: bigint;
        completedItems: bigint;
        totalTimeSpent: bigint;
        totalComments: bigint;
        totalFiles: bigint;
      }>>`
        SELECT
          COUNT(DISTINCT u.id) as "totalUsers",
          COUNT(DISTINCT CASE
            WHEN al.created_at >= ${dateRange.start.toISOString()}
            THEN al.user_id
          END) as "activeUsers",
          COUNT(DISTINCT w.id) as "totalWorkspaces",
          COUNT(DISTINCT b.id) as "totalBoards",
          COUNT(DISTINCT i.id) as "totalItems",
          COUNT(DISTINCT CASE
            WHEN JSON_EXTRACT(i.item_data, '$.status') = 'Done'
            THEN i.id
          END) as "completedItems",
          COALESCE(SUM(te.duration), 0) as "totalTimeSpent",
          COUNT(DISTINCT c.id) as "totalComments",
          COUNT(DISTINCT f.id) as "totalFiles"
        FROM users u
        LEFT JOIN workspace_members wm ON u.id = wm.user_id
        LEFT JOIN workspaces w ON wm.workspace_id = w.id AND w.organization_id = ${organizationId}
        LEFT JOIN boards b ON w.id = b.workspace_id AND b.deleted_at IS NULL
        LEFT JOIN items i ON b.id = i.board_id AND i.deleted_at IS NULL
        LEFT JOIN activity_log al ON u.id = al.user_id AND al.organization_id = ${organizationId}
        LEFT JOIN time_entries te ON u.id = te.user_id AND te.start_time >= ${dateRange.start.toISOString()}
        LEFT JOIN comments c ON u.id = c.user_id AND c.deleted_at IS NULL
        LEFT JOIN files f ON u.id = f.uploaded_by AND f.deleted_at IS NULL
        WHERE u.organization_id = ${organizationId}
      `;

      const metrics: AnalyticsMetrics = {
        organizationId,
        period,
        dateRange,
        userMetrics: {
          totalUsers: Number(stats.totalUsers),
          activeUsers: Number(stats.activeUsers),
          userGrowth: 0, // Would need historical comparison
        },
        workspaceMetrics: {
          totalWorkspaces: Number(stats.totalWorkspaces),
          averageBoardsPerWorkspace: Number(stats.totalBoards) / Math.max(Number(stats.totalWorkspaces), 1),
        },
        itemMetrics: {
          totalItems: Number(stats.totalItems),
          completedItems: Number(stats.completedItems),
          completionRate: Number(stats.totalItems) > 0
            ? (Number(stats.completedItems) / Number(stats.totalItems)) * 100
            : 0,
        },
        timeMetrics: {
          totalTimeSpent: Number(stats.totalTimeSpent),
          averageTimePerUser: Number(stats.activeUsers) > 0
            ? Number(stats.totalTimeSpent) / Number(stats.activeUsers)
            : 0,
        },
        collaborationMetrics: {
          totalComments: Number(stats.totalComments),
          totalFiles: Number(stats.totalFiles),
          averageCommentsPerItem: Number(stats.totalItems) > 0
            ? Number(stats.totalComments) / Number(stats.totalItems)
            : 0,
        },
        generatedAt: new Date(),
      };

      // Cache for 30 minutes
      await RedisService.setCache(cacheKey, JSON.stringify(metrics), this.CACHE_TTL);

      return metrics;
    } catch (error) {
      Logger.error('Get organization analytics failed', error as Error);
      throw error;
    }
  }

  /**
   * Generate custom analytics report
   */
  static async generateCustomReport(
    filter: AnalyticsFilter,
    userId: string
  ): Promise<any> {
    try {
      // Validate access permissions based on filter scope
      if (filter.organizationId) {
        const hasAccess = await this.checkOrganizationAdminAccess(filter.organizationId, userId);
        if (!hasAccess) {
          throw new Error('Access denied to organization data');
        }
      } else if (filter.workspaceId) {
        const hasAccess = await this.checkWorkspaceAccess(filter.workspaceId, userId);
        if (!hasAccess) {
          throw new Error('Access denied to workspace data');
        }
      } else if (filter.boardId) {
        const hasAccess = await this.checkBoardAccess(filter.boardId, userId);
        if (!hasAccess) {
          throw new Error('Access denied to board data');
        }
      }

      // Build dynamic query based on filter
      const queryParts = this.buildCustomQuery(filter);

      const data = await prisma.$queryRawUnsafe(queryParts.query, ...queryParts.params);

      return {
        filter,
        data,
        generatedAt: new Date(),
      };
    } catch (error) {
      Logger.error('Generate custom report failed', error as Error);
      throw error;
    }
  }

  // ============================================================================
  // PRIVATE HELPER METHODS
  // ============================================================================

  private static getDateRange(period: string): { start: Date; end: Date } {
    const end = new Date();
    const start = new Date();

    switch (period) {
      case 'day':
        start.setDate(start.getDate() - 1);
        break;
      case 'week':
        start.setDate(start.getDate() - 7);
        break;
      case 'month':
        start.setMonth(start.getMonth() - 1);
        break;
      case 'year':
        start.setFullYear(start.getFullYear() - 1);
        break;
    }

    return { start, end };
  }

  private static async getBoardItemStats(boardId: string, startDate: Date, endDate: Date) {
    const [stats] = await prisma.$queryRaw<Array<{
      totalItems: bigint;
      completedItems: bigint;
      inProgressItems: bigint;
      createdInPeriod: bigint;
      completedInPeriod: bigint;
    }>>`
      SELECT
        COUNT(*) as "totalItems",
        COUNT(CASE WHEN JSON_EXTRACT(item_data, '$.status') = 'Done' THEN 1 END) as "completedItems",
        COUNT(CASE WHEN JSON_EXTRACT(item_data, '$.status') = 'In Progress' THEN 1 END) as "inProgressItems",
        COUNT(CASE WHEN created_at >= ${startDate.toISOString()} THEN 1 END) as "createdInPeriod",
        COUNT(CASE
          WHEN JSON_EXTRACT(item_data, '$.status') = 'Done'
          AND updated_at >= ${startDate.toISOString()}
          THEN 1
        END) as "completedInPeriod"
      FROM items
      WHERE board_id = ${boardId} AND deleted_at IS NULL
    `;

    return {
      totalItems: Number(stats.totalItems),
      completedItems: Number(stats.completedItems),
      inProgressItems: Number(stats.inProgressItems),
      createdInPeriod: Number(stats.createdInPeriod),
      completedInPeriod: Number(stats.completedInPeriod),
      completionRate: Number(stats.totalItems) > 0
        ? (Number(stats.completedItems) / Number(stats.totalItems)) * 100
        : 0,
    };
  }

  private static async getBoardActivityStats(boardId: string, startDate: Date, endDate: Date) {
    const [stats] = await prisma.$queryRaw<Array<{
      totalActivities: bigint;
      uniqueActiveUsers: bigint;
      commentsCount: bigint;
      filesUploadedCount: bigint;
    }>>`
      SELECT
        COUNT(al.id) as "totalActivities",
        COUNT(DISTINCT al.user_id) as "uniqueActiveUsers",
        COUNT(DISTINCT c.id) as "commentsCount",
        COUNT(DISTINCT f.id) as "filesUploadedCount"
      FROM activity_log al
      LEFT JOIN comments c ON al.board_id = c.board_id AND c.created_at >= ${startDate.toISOString()}
      LEFT JOIN files f ON al.board_id = f.board_id AND f.created_at >= ${startDate.toISOString()}
      WHERE al.board_id = ${boardId}
        AND al.created_at >= ${startDate.toISOString()}
        AND al.created_at <= ${endDate.toISOString()}
    `;

    return {
      totalActivities: Number(stats.totalActivities),
      uniqueActiveUsers: Number(stats.uniqueActiveUsers),
      commentsCount: Number(stats.commentsCount),
      filesUploadedCount: Number(stats.filesUploadedCount),
    };
  }

  private static async getBoardMemberStats(boardId: string, startDate: Date, endDate: Date) {
    const members = await prisma.boardMember.findMany({
      where: { boardId },
      include: { user: true },
    });

    return {
      totalMembers: members.length,
      adminCount: members.filter(m => m.role === 'admin').length,
      memberCount: members.filter(m => m.role === 'member').length,
    };
  }

  private static async getBoardTimeStats(boardId: string, startDate: Date, endDate: Date) {
    const [stats] = await prisma.$queryRaw<Array<{
      totalTimeSpent: bigint;
      billableTime: bigint;
      timeEntriesCount: bigint;
    }>>`
      SELECT
        COALESCE(SUM(duration), 0) as "totalTimeSpent",
        COALESCE(SUM(CASE WHEN billable THEN duration ELSE 0 END), 0) as "billableTime",
        COUNT(*) as "timeEntriesCount"
      FROM time_entries
      WHERE board_id = ${boardId}
        AND start_time >= ${startDate.toISOString()}
        AND start_time <= ${endDate.toISOString()}
        AND is_running = false
    `;

    return {
      totalTimeSpent: Number(stats.totalTimeSpent),
      billableTime: Number(stats.billableTime),
      timeEntriesCount: Number(stats.timeEntriesCount),
      averageSessionDuration: Number(stats.timeEntriesCount) > 0
        ? Number(stats.totalTimeSpent) / Number(stats.timeEntriesCount)
        : 0,
    };
  }

  private static async getBoardVelocityStats(boardId: string, period: string) {
    // Calculate velocity based on completed items over time periods
    const periods = this.getVelocityPeriods(period);

    const velocityData = await Promise.all(
      periods.map(async (p) => {
        const [stats] = await prisma.$queryRaw<Array<{ completed: bigint }>>`
          SELECT COUNT(*) as completed
          FROM items
          WHERE board_id = ${boardId}
            AND JSON_EXTRACT(item_data, '$.status') = 'Done'
            AND updated_at >= ${p.start.toISOString()}
            AND updated_at <= ${p.end.toISOString()}
            AND deleted_at IS NULL
        `;

        return {
          period: p.label,
          completed: Number(stats.completed),
        };
      })
    );

    const totalCompleted = velocityData.reduce((sum, v) => sum + v.completed, 0);
    const averageVelocity = velocityData.length > 0 ? totalCompleted / velocityData.length : 0;

    return {
      velocityData,
      averageVelocity,
      trend: this.calculateTrend(velocityData.map(v => v.completed)),
    };
  }

  private static getVelocityPeriods(period: string) {
    const periods = [];
    const now = new Date();
    const periodCount = period === 'day' ? 7 : period === 'week' ? 4 : 12;

    for (let i = 0; i < periodCount; i++) {
      const end = new Date(now);
      const start = new Date(now);

      if (period === 'day') {
        end.setDate(end.getDate() - i);
        start.setDate(start.getDate() - i - 1);
      } else if (period === 'week') {
        end.setDate(end.getDate() - (i * 7));
        start.setDate(start.getDate() - ((i + 1) * 7));
      } else {
        end.setMonth(end.getMonth() - i);
        start.setMonth(start.getMonth() - i - 1);
      }

      periods.unshift({
        start,
        end,
        label: `${start.toISOString().split('T')[0]} to ${end.toISOString().split('T')[0]}`,
      });
    }

    return periods;
  }

  private static calculateTrend(values: number[]): 'up' | 'down' | 'stable' {
    if (values.length < 2) return 'stable';

    const recent = values.slice(-2);
    if (recent[1] > recent[0]) return 'up';
    if (recent[1] < recent[0]) return 'down';
    return 'stable';
  }

  // Placeholder methods for user and team analytics
  private static async getUserActivitySummary(userId: string, startDate: Date, endDate: Date) {
    // Implementation would be similar to board stats but user-focused
    return {
      itemsCreated: 0,
      itemsCompleted: 0,
      commentsPosted: 0,
      collaborations: 0,
    };
  }

  private static async getUserItemsWorked(userId: string, startDate: Date, endDate: Date) {
    return [];
  }

  private static async getUserTimeSpent(userId: string, startDate: Date, endDate: Date) {
    return {
      totalTime: 0,
      billableTime: 0,
      projectBreakdown: [],
    };
  }

  private static async getUserCollaborationMetrics(userId: string, startDate: Date, endDate: Date) {
    return {
      boardsCollaboratedOn: 0,
      usersCollaboratedWith: 0,
      commentsReceived: 0,
    };
  }

  private static async getUserProductivityTrends(userId: string, period: string) {
    return {
      weeklyTrends: [],
      productivityScore: 0,
    };
  }

  // Team analytics placeholder methods
  private static async getTeamOverview(workspaceId: string, startDate: Date, endDate: Date) {
    return {
      totalMembers: 0,
      activeMembers: 0,
      totalBoards: 0,
      totalItems: 0,
      completedItems: 0,
    };
  }

  private static async getMemberPerformance(workspaceId: string, startDate: Date, endDate: Date) {
    return [];
  }

  private static async getBoardsProgress(workspaceId: string, startDate: Date, endDate: Date) {
    return [];
  }

  private static async getTimeDistribution(workspaceId: string, startDate: Date, endDate: Date) {
    return {
      totalTime: 0,
      byMember: [],
      byProject: [],
    };
  }

  private static async getCollaborationInsights(workspaceId: string, startDate: Date, endDate: Date) {
    return {
      communicationIndex: 0,
      crossBoardCollaboration: 0,
      responseTime: 0,
    };
  }

  private static buildCustomQuery(filter: AnalyticsFilter) {
    // Build dynamic SQL query based on filter criteria
    // This is a simplified implementation
    let query = 'SELECT * FROM activity_log WHERE 1=1';
    const params: any[] = [];

    if (filter.organizationId) {
      query += ' AND organization_id = ?';
      params.push(filter.organizationId);
    }

    if (filter.workspaceId) {
      query += ' AND workspace_id = ?';
      params.push(filter.workspaceId);
    }

    if (filter.boardId) {
      query += ' AND board_id = ?';
      params.push(filter.boardId);
    }

    if (filter.startDate) {
      query += ' AND created_at >= ?';
      params.push(filter.startDate.toISOString());
    }

    if (filter.endDate) {
      query += ' AND created_at <= ?';
      params.push(filter.endDate.toISOString());
    }

    query += ' ORDER BY created_at DESC LIMIT 1000';

    return { query, params };
  }

  // Permission check methods
  private static async checkBoardAccess(boardId: string, userId: string): Promise<boolean> {
    try {
      const { BoardService } = await import('./board.service');
      return await BoardService.hasReadAccess(boardId, userId);
    } catch (error) {
      Logger.error('Failed to check board access', error as Error);
      return false;
    }
  }

  private static async checkWorkspaceAccess(workspaceId: string, userId: string): Promise<boolean> {
    try {
      const member = await prisma.workspaceMember.findUnique({
        where: {
          workspaceId_userId: {
            workspaceId,
            userId,
          },
        },
      });
      return !!member;
    } catch (error) {
      Logger.error('Failed to check workspace access', error as Error);
      return false;
    }
  }

  private static async checkOrganizationAdminAccess(organizationId: string, userId: string): Promise<boolean> {
    try {
      const member = await prisma.organizationMember.findUnique({
        where: {
          organizationId_userId: {
            organizationId,
            userId,
          },
        },
      });
      return !!member && (member.role === 'admin' || member.role === 'owner');
    } catch (error) {
      Logger.error('Failed to check organization admin access', error as Error);
      return false;
    }
  }

  private static async canViewUserData(requestingUserId: string, targetUserId: string): Promise<boolean> {
    // Check if requesting user is admin in any shared workspace/organization
    // Simplified implementation - in production you'd want more granular permissions
    try {
      const sharedWorkspaces = await prisma.workspaceMember.findMany({
        where: {
          userId: requestingUserId,
          role: { in: ['admin', 'owner'] },
          workspace: {
            members: {
              some: {
                userId: targetUserId,
              },
            },
          },
        },
      });

      return sharedWorkspaces.length > 0;
    } catch (error) {
      Logger.error('Failed to check user data access', error as Error);
      return false;
    }
  }
}