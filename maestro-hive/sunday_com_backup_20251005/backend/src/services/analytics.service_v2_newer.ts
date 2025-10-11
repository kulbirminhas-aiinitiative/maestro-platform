import { prisma } from '@/config/database';
import { Logger } from '@/config/logger';
import { RedisService } from '@/config/redis';
import { AnalyticsEvent, AnalyticsQuery, AnalyticsResult } from '@/types';
import { v4 as uuidv4 } from 'uuid';

interface DashboardMetrics {
  productivity: {
    itemsCompleted: number;
    completionRate: number;
    avgTimeToComplete: number;
    trend: 'up' | 'down' | 'stable';
  };
  workload: {
    totalItems: number;
    itemsByStatus: Record<string, number>;
    itemsByPriority: Record<string, number>;
    overdueTasks: number;
  };
  collaboration: {
    activeUsers: number;
    commentsCount: number;
    timeTracked: number;
    boardViews: number;
  };
  team: {
    memberWorkload: Array<{
      userId: string;
      name: string;
      assignedItems: number;
      completedItems: number;
      workloadScore: number;
    }>;
    departmentMetrics: Record<string, any>;
  };
}

interface TimeSeriesData {
  date: string;
  value: number;
  label?: string;
}

interface ReportData {
  summary: Record<string, number>;
  timeSeries: TimeSeriesData[];
  breakdown: Record<string, number>;
  insights: string[];
}

export class AnalyticsService {
  /**
   * Track analytics event
   */
  static async trackEvent(event: AnalyticsEvent): Promise<void> {
    try {
      // Store event in activity log for analytics
      await prisma.activityLog.create({
        data: {
          id: uuidv4(),
          organizationId: event.organizationId,
          workspaceId: event.workspaceId,
          boardId: event.boardId,
          itemId: event.itemId,
          userId: event.userId,
          action: event.eventType,
          entityType: 'analytics_event',
          entityId: uuidv4(),
          metadata: {
            properties: event.properties,
            timestamp: event.timestamp || new Date(),
          },
        },
      });

      // Update real-time metrics in Redis
      await this.updateRealTimeMetrics(event);

      Logger.analytics(`Event tracked: ${event.eventType}`, {
        userId: event.userId,
        organizationId: event.organizationId,
        eventType: event.eventType,
      });
    } catch (error) {
      Logger.error('Track analytics event failed', error as Error);
    }
  }

  /**
   * Get dashboard metrics for organization
   */
  static async getDashboardMetrics(
    organizationId: string,
    userId: string,
    workspaceId?: string,
    dateRange: { start: Date; end: Date } = {
      start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // 30 days ago
      end: new Date(),
    }
  ): Promise<DashboardMetrics> {
    try {
      // Verify access
      const hasAccess = await this.verifyAnalyticsAccess(organizationId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      // Use cached data if available
      const cacheKey = `dashboard_metrics:${organizationId}:${workspaceId || 'all'}:${dateRange.start.toISOString()}:${dateRange.end.toISOString()}`;
      const cached = await RedisService.getCache(cacheKey);
      if (cached) {
        return cached;
      }

      // Build base query filters
      const baseWhere = {
        board: {
          workspace: {
            organizationId,
            ...(workspaceId && { id: workspaceId }),
          },
        },
        createdAt: {
          gte: dateRange.start,
          lte: dateRange.end,
        },
        deletedAt: null,
      };

      // Get productivity metrics
      const productivity = await this.getProductivityMetrics(baseWhere, dateRange);

      // Get workload metrics
      const workload = await this.getWorkloadMetrics(baseWhere);

      // Get collaboration metrics
      const collaboration = await this.getCollaborationMetrics(organizationId, workspaceId, dateRange);

      // Get team metrics
      const team = await this.getTeamMetrics(organizationId, workspaceId, dateRange);

      const metrics: DashboardMetrics = {
        productivity,
        workload,
        collaboration,
        team,
      };

      // Cache for 15 minutes
      await RedisService.setCache(cacheKey, metrics, 900);

      Logger.analytics('Dashboard metrics generated', {
        organizationId,
        workspaceId,
        userId,
      });

      return metrics;
    } catch (error) {
      Logger.error('Get dashboard metrics failed', error as Error);
      throw error;
    }
  }

  /**
   * Generate analytics report
   */
  static async generateReport(
    organizationId: string,
    userId: string,
    reportType: 'productivity' | 'workload' | 'team' | 'custom',
    query: AnalyticsQuery
  ): Promise<ReportData> {
    try {
      // Verify access
      const hasAccess = await this.verifyAnalyticsAccess(organizationId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      let reportData: ReportData;

      switch (reportType) {
        case 'productivity':
          reportData = await this.generateProductivityReport(query);
          break;
        case 'workload':
          reportData = await this.generateWorkloadReport(query);
          break;
        case 'team':
          reportData = await this.generateTeamReport(query);
          break;
        case 'custom':
          reportData = await this.generateCustomReport(query);
          break;
        default:
          throw new Error(`Invalid report type: ${reportType}`);
      }

      // Track report generation
      await this.trackEvent({
        eventType: 'report_generated',
        userId,
        organizationId,
        workspaceId: query.workspaceId,
        boardId: query.boardId,
        properties: {
          reportType,
          dateRange: {
            start: query.startDate,
            end: query.endDate,
          },
        },
      });

      Logger.analytics(`${reportType} report generated`, {
        organizationId,
        userId,
        reportType,
      });

      return reportData;
    } catch (error) {
      Logger.error('Generate report failed', error as Error);
      throw error;
    }
  }

  /**
   * Get user activity analytics
   */
  static async getUserActivityAnalytics(
    organizationId: string,
    requesterId: string,
    targetUserId?: string,
    dateRange: { start: Date; end: Date } = {
      start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000), // 7 days ago
      end: new Date(),
    }
  ): Promise<{
    summary: {
      itemsCreated: number;
      itemsCompleted: number;
      commentsAdded: number;
      timeLogged: number;
      activeBoards: number;
    };
    dailyActivity: TimeSeriesData[];
    topBoards: Array<{
      boardId: string;
      boardName: string;
      activityCount: number;
    }>;
  }> {
    try {
      // Verify access
      const hasAccess = await this.verifyAnalyticsAccess(organizationId, requesterId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      const userId = targetUserId || requesterId;

      // Get activity summary
      const [itemsCreated, itemsCompleted, commentsAdded, timeEntries, activeBoards] = await Promise.all([
        prisma.item.count({
          where: {
            createdBy: userId,
            createdAt: { gte: dateRange.start, lte: dateRange.end },
            deletedAt: null,
          },
        }),
        prisma.item.count({
          where: {
            board: {
              workspace: { organizationId },
            },
            itemData: {
              path: ['status'],
              in: ['Done', 'Completed'],
            },
            updatedAt: { gte: dateRange.start, lte: dateRange.end },
            deletedAt: null,
          },
        }),
        prisma.comment.count({
          where: {
            userId,
            createdAt: { gte: dateRange.start, lte: dateRange.end },
            deletedAt: null,
          },
        }),
        prisma.timeEntry.aggregate({
          where: {
            userId,
            startTime: { gte: dateRange.start, lte: dateRange.end },
          },
          _sum: { durationSeconds: true },
        }),
        prisma.board.count({
          where: {
            workspace: { organizationId },
            items: {
              some: {
                OR: [
                  { createdBy: userId },
                  { assignments: { some: { userId } } },
                ],
                createdAt: { gte: dateRange.start, lte: dateRange.end },
              },
            },
            deletedAt: null,
          },
        }),
      ]);

      // Get daily activity
      const dailyActivity = await this.getDailyUserActivity(userId, organizationId, dateRange);

      // Get top boards by activity
      const topBoards = await this.getTopBoardsByUserActivity(userId, organizationId, dateRange);

      return {
        summary: {
          itemsCreated,
          itemsCompleted,
          commentsAdded,
          timeLogged: Math.round((timeEntries._sum.durationSeconds || 0) / 3600), // Convert to hours
          activeBoards,
        },
        dailyActivity,
        topBoards,
      };
    } catch (error) {
      Logger.error('Get user activity analytics failed', error as Error);
      throw error;
    }
  }

  /**
   * Get board analytics
   */
  static async getBoardAnalytics(
    boardId: string,
    userId: string,
    dateRange: { start: Date; end: Date } = {
      start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000), // 30 days ago
      end: new Date(),
    }
  ): Promise<{
    summary: {
      totalItems: number;
      completedItems: number;
      completionRate: number;
      avgTimeToComplete: number;
      activeMembers: number;
    };
    trends: {
      itemsCreated: TimeSeriesData[];
      itemsCompleted: TimeSeriesData[];
      teamActivity: TimeSeriesData[];
    };
    distribution: {
      itemsByStatus: Record<string, number>;
      itemsByAssignee: Record<string, number>;
      itemsByPriority: Record<string, number>;
    };
    insights: string[];
  }> {
    try {
      // Verify board access
      const hasAccess = await this.verifyBoardAccess(boardId, userId);
      if (!hasAccess) {
        throw new Error('Board not found or access denied');
      }

      // Get board summary
      const [totalItems, completedItems, timeEntries, activeMembers] = await Promise.all([
        prisma.item.count({
          where: {
            boardId,
            createdAt: { gte: dateRange.start, lte: dateRange.end },
            deletedAt: null,
          },
        }),
        prisma.item.count({
          where: {
            boardId,
            itemData: {
              path: ['status'],
              in: ['Done', 'Completed'],
            },
            updatedAt: { gte: dateRange.start, lte: dateRange.end },
            deletedAt: null,
          },
        }),
        prisma.timeEntry.aggregate({
          where: {
            item: { boardId },
            startTime: { gte: dateRange.start, lte: dateRange.end },
            endTime: { not: null },
          },
          _avg: { durationSeconds: true },
        }),
        prisma.itemAssignment.groupBy({
          by: ['userId'],
          where: {
            item: {
              boardId,
              createdAt: { gte: dateRange.start, lte: dateRange.end },
              deletedAt: null,
            },
          },
          _count: true,
        }),
      ]);

      const completionRate = totalItems > 0 ? (completedItems / totalItems) * 100 : 0;
      const avgTimeToComplete = Math.round((timeEntries._avg.durationSeconds || 0) / 3600); // Convert to hours

      // Get trends
      const trends = await this.getBoardTrends(boardId, dateRange);

      // Get distribution data
      const distribution = await this.getBoardDistribution(boardId, dateRange);

      // Generate insights
      const insights = this.generateBoardInsights({
        totalItems,
        completedItems,
        completionRate,
        avgTimeToComplete,
        activeMembers: activeMembers.length,
        distribution,
      });

      return {
        summary: {
          totalItems,
          completedItems,
          completionRate: Math.round(completionRate * 100) / 100,
          avgTimeToComplete,
          activeMembers: activeMembers.length,
        },
        trends,
        distribution,
        insights,
      };
    } catch (error) {
      Logger.error('Get board analytics failed', error as Error);
      throw error;
    }
  }

  /**
   * Export analytics data
   */
  static async exportData(
    organizationId: string,
    userId: string,
    exportType: 'csv' | 'json' | 'excel',
    query: AnalyticsQuery
  ): Promise<{
    data: any;
    filename: string;
    contentType: string;
  }> {
    try {
      // Verify access
      const hasAccess = await this.verifyAnalyticsAccess(organizationId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      // Get raw data based on query
      const rawData = await this.getRawAnalyticsData(query);

      // Format data based on export type
      let formattedData: any;
      let contentType: string;
      let filename: string;

      const timestamp = new Date().toISOString().split('T')[0];

      switch (exportType) {
        case 'json':
          formattedData = JSON.stringify(rawData, null, 2);
          contentType = 'application/json';
          filename = `analytics_export_${timestamp}.json`;
          break;

        case 'csv':
          formattedData = this.convertToCSV(rawData);
          contentType = 'text/csv';
          filename = `analytics_export_${timestamp}.csv`;
          break;

        case 'excel':
          // In a real implementation, you'd use a library like xlsx
          formattedData = this.convertToExcel(rawData);
          contentType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';
          filename = `analytics_export_${timestamp}.xlsx`;
          break;

        default:
          throw new Error(`Unsupported export type: ${exportType}`);
      }

      // Track export event
      await this.trackEvent({
        eventType: 'data_exported',
        userId,
        organizationId,
        properties: {
          exportType,
          recordCount: Array.isArray(rawData) ? rawData.length : Object.keys(rawData).length,
        },
      });

      Logger.analytics(`Data exported as ${exportType}`, {
        organizationId,
        userId,
        exportType,
      });

      return {
        data: formattedData,
        filename,
        contentType,
      };
    } catch (error) {
      Logger.error('Export analytics data failed', error as Error);
      throw error;
    }
  }

  // ============================================================================
  // PRIVATE HELPER METHODS
  // ============================================================================

  /**
   * Update real-time metrics in Redis
   */
  private static async updateRealTimeMetrics(event: AnalyticsEvent): Promise<void> {
    try {
      const metricsKey = `metrics:${event.organizationId}:${new Date().toISOString().split('T')[0]}`;

      // Increment counters based on event type
      switch (event.eventType) {
        case 'item_created':
          await RedisService.incrementCounter(`${metricsKey}:items_created`);
          break;
        case 'item_completed':
          await RedisService.incrementCounter(`${metricsKey}:items_completed`);
          break;
        case 'comment_added':
          await RedisService.incrementCounter(`${metricsKey}:comments_added`);
          break;
        case 'time_logged':
          await RedisService.incrementCounter(`${metricsKey}:time_logged`, event.properties?.duration || 1);
          break;
      }
    } catch (error) {
      Logger.error('Update real-time metrics failed', error as Error);
    }
  }

  /**
   * Get productivity metrics
   */
  private static async getProductivityMetrics(
    baseWhere: any,
    dateRange: { start: Date; end: Date }
  ): Promise<DashboardMetrics['productivity']> {
    const [itemsCompleted, totalItems, timeEntries] = await Promise.all([
      prisma.item.count({
        where: {
          ...baseWhere,
          itemData: {
            path: ['status'],
            in: ['Done', 'Completed'],
          },
        },
      }),
      prisma.item.count({ where: baseWhere }),
      prisma.timeEntry.aggregate({
        where: {
          item: { ...baseWhere },
          endTime: { not: null },
        },
        _avg: { durationSeconds: true },
      }),
    ]);

    const completionRate = totalItems > 0 ? (itemsCompleted / totalItems) * 100 : 0;
    const avgTimeToComplete = Math.round((timeEntries._avg.durationSeconds || 0) / 3600);

    // Calculate trend (compare with previous period)
    const previousPeriod = {
      start: new Date(dateRange.start.getTime() - (dateRange.end.getTime() - dateRange.start.getTime())),
      end: dateRange.start,
    };

    const previousItemsCompleted = await prisma.item.count({
      where: {
        ...baseWhere,
        createdAt: { gte: previousPeriod.start, lte: previousPeriod.end },
        itemData: {
          path: ['status'],
          in: ['Done', 'Completed'],
        },
      },
    });

    const trend = itemsCompleted > previousItemsCompleted ? 'up' :
                 itemsCompleted < previousItemsCompleted ? 'down' : 'stable';

    return {
      itemsCompleted,
      completionRate: Math.round(completionRate * 100) / 100,
      avgTimeToComplete,
      trend,
    };
  }

  /**
   * Get workload metrics
   */
  private static async getWorkloadMetrics(baseWhere: any): Promise<DashboardMetrics['workload']> {
    const [totalItems, statusData, priorityData, overdueItems] = await Promise.all([
      prisma.item.count({ where: baseWhere }),

      // Get items by status
      prisma.$queryRaw`
        SELECT
          (item_data->>'status') as status,
          COUNT(*) as count
        FROM items i
        JOIN boards b ON i.board_id = b.id
        JOIN workspaces w ON b.workspace_id = w.id
        WHERE w.organization_id = ${baseWhere.board.workspace.organizationId}
          AND i.deleted_at IS NULL
        GROUP BY (item_data->>'status')
      ` as Array<{ status: string; count: bigint }>,

      // Get items by priority
      prisma.$queryRaw`
        SELECT
          (item_data->>'priority') as priority,
          COUNT(*) as count
        FROM items i
        JOIN boards b ON i.board_id = b.id
        JOIN workspaces w ON b.workspace_id = w.id
        WHERE w.organization_id = ${baseWhere.board.workspace.organizationId}
          AND i.deleted_at IS NULL
        GROUP BY (item_data->>'priority')
      ` as Array<{ priority: string; count: bigint }>,

      // Get overdue items
      prisma.$queryRaw`
        SELECT COUNT(*) as count
        FROM items i
        JOIN boards b ON i.board_id = b.id
        JOIN workspaces w ON b.workspace_id = w.id
        WHERE w.organization_id = ${baseWhere.board.workspace.organizationId}
          AND i.deleted_at IS NULL
          AND (i.item_data->>'dueDate')::date < CURRENT_DATE
          AND (i.item_data->>'status') NOT IN ('Done', 'Completed')
      ` as Array<{ count: bigint }>,
    ]);

    const itemsByStatus: Record<string, number> = {};
    statusData.forEach(item => {
      if (item.status) {
        itemsByStatus[item.status] = Number(item.count);
      }
    });

    const itemsByPriority: Record<string, number> = {};
    priorityData.forEach(item => {
      if (item.priority) {
        itemsByPriority[item.priority] = Number(item.count);
      }
    });

    return {
      totalItems,
      itemsByStatus,
      itemsByPriority,
      overdueTasks: Number(overdueItems[0]?.count || 0),
    };
  }

  /**
   * Get collaboration metrics
   */
  private static async getCollaborationMetrics(
    organizationId: string,
    workspaceId: string | undefined,
    dateRange: { start: Date; end: Date }
  ): Promise<DashboardMetrics['collaboration']> {
    const baseWhere = {
      board: {
        workspace: {
          organizationId,
          ...(workspaceId && { id: workspaceId }),
        },
      },
    };

    const [activeUsers, commentsCount, timeTracked, boardViews] = await Promise.all([
      prisma.user.count({
        where: {
          organizationMemberships: {
            some: {
              organizationId,
              status: 'active',
            },
          },
          lastLoginAt: {
            gte: dateRange.start,
          },
        },
      }),

      prisma.comment.count({
        where: {
          item: baseWhere,
          createdAt: { gte: dateRange.start, lte: dateRange.end },
          deletedAt: null,
        },
      }),

      prisma.timeEntry.aggregate({
        where: {
          item: baseWhere,
          startTime: { gte: dateRange.start, lte: dateRange.end },
        },
        _sum: { durationSeconds: true },
      }),

      // Simulate board views - in a real app you'd track these events
      prisma.activityLog.count({
        where: {
          organizationId,
          action: 'board_viewed',
          createdAt: { gte: dateRange.start, lte: dateRange.end },
        },
      }),
    ]);

    return {
      activeUsers,
      commentsCount,
      timeTracked: Math.round((timeTracked._sum.durationSeconds || 0) / 3600), // Convert to hours
      boardViews,
    };
  }

  /**
   * Get team metrics
   */
  private static async getTeamMetrics(
    organizationId: string,
    workspaceId: string | undefined,
    dateRange: { start: Date; end: Date }
  ): Promise<DashboardMetrics['team']> {
    const members = await prisma.user.findMany({
      where: {
        organizationMemberships: {
          some: {
            organizationId,
            status: 'active',
          },
        },
      },
      include: {
        itemAssignments: {
          where: {
            item: {
              board: {
                workspace: {
                  organizationId,
                  ...(workspaceId && { id: workspaceId }),
                },
              },
              createdAt: { gte: dateRange.start, lte: dateRange.end },
              deletedAt: null,
            },
          },
          include: {
            item: true,
          },
        },
      },
    });

    const memberWorkload = members.map(member => {
      const assignedItems = member.itemAssignments.length;
      const completedItems = member.itemAssignments.filter(assignment => {
        const itemData = assignment.item.itemData as any;
        return itemData?.status === 'Done' || itemData?.status === 'Completed';
      }).length;

      // Simple workload score calculation
      const workloadScore = assignedItems > 0 ? (completedItems / assignedItems) * 100 : 0;

      return {
        userId: member.id,
        name: `${member.firstName || ''} ${member.lastName || ''}`.trim() || member.email,
        assignedItems,
        completedItems,
        workloadScore: Math.round(workloadScore),
      };
    });

    return {
      memberWorkload,
      departmentMetrics: {}, // Would be populated from organization structure
    };
  }

  /**
   * Generate productivity report
   */
  private static async generateProductivityReport(query: AnalyticsQuery): Promise<ReportData> {
    // Implementation would generate detailed productivity analysis
    return {
      summary: {
        totalItems: 0,
        completedItems: 0,
        completionRate: 0,
      },
      timeSeries: [],
      breakdown: {},
      insights: ['Productivity report implementation pending'],
    };
  }

  /**
   * Generate workload report
   */
  private static async generateWorkloadReport(query: AnalyticsQuery): Promise<ReportData> {
    // Implementation would generate detailed workload analysis
    return {
      summary: {
        totalWorkload: 0,
        averageWorkload: 0,
      },
      timeSeries: [],
      breakdown: {},
      insights: ['Workload report implementation pending'],
    };
  }

  /**
   * Generate team report
   */
  private static async generateTeamReport(query: AnalyticsQuery): Promise<ReportData> {
    // Implementation would generate detailed team analysis
    return {
      summary: {
        teamSize: 0,
        avgProductivity: 0,
      },
      timeSeries: [],
      breakdown: {},
      insights: ['Team report implementation pending'],
    };
  }

  /**
   * Generate custom report
   */
  private static async generateCustomReport(query: AnalyticsQuery): Promise<ReportData> {
    // Implementation would generate custom analysis based on query
    return {
      summary: {},
      timeSeries: [],
      breakdown: {},
      insights: ['Custom report implementation pending'],
    };
  }

  /**
   * Get daily user activity
   */
  private static async getDailyUserActivity(
    userId: string,
    organizationId: string,
    dateRange: { start: Date; end: Date }
  ): Promise<TimeSeriesData[]> {
    // Implementation would return daily activity data
    return [];
  }

  /**
   * Get top boards by user activity
   */
  private static async getTopBoardsByUserActivity(
    userId: string,
    organizationId: string,
    dateRange: { start: Date; end: Date }
  ): Promise<Array<{ boardId: string; boardName: string; activityCount: number }>> {
    // Implementation would return top boards by activity
    return [];
  }

  /**
   * Get board trends
   */
  private static async getBoardTrends(
    boardId: string,
    dateRange: { start: Date; end: Date }
  ): Promise<{
    itemsCreated: TimeSeriesData[];
    itemsCompleted: TimeSeriesData[];
    teamActivity: TimeSeriesData[];
  }> {
    // Implementation would return board trend data
    return {
      itemsCreated: [],
      itemsCompleted: [],
      teamActivity: [],
    };
  }

  /**
   * Get board distribution data
   */
  private static async getBoardDistribution(
    boardId: string,
    dateRange: { start: Date; end: Date }
  ): Promise<{
    itemsByStatus: Record<string, number>;
    itemsByAssignee: Record<string, number>;
    itemsByPriority: Record<string, number>;
  }> {
    // Implementation would return distribution data
    return {
      itemsByStatus: {},
      itemsByAssignee: {},
      itemsByPriority: {},
    };
  }

  /**
   * Generate board insights
   */
  private static generateBoardInsights(data: any): string[] {
    const insights: string[] = [];

    if (data.completionRate < 50) {
      insights.push('Board completion rate is below 50%. Consider reviewing task complexity.');
    }

    if (data.avgTimeToComplete > 40) {
      insights.push('Average time to complete tasks is high. Consider breaking down larger tasks.');
    }

    if (data.activeMembers < 3) {
      insights.push('Low team engagement. Consider adding more team members or checking workload distribution.');
    }

    return insights;
  }

  /**
   * Get raw analytics data
   */
  private static async getRawAnalyticsData(query: AnalyticsQuery): Promise<any[]> {
    // Implementation would return raw data based on query
    return [];
  }

  /**
   * Convert data to CSV format
   */
  private static convertToCSV(data: any[]): string {
    if (!data.length) return '';

    const headers = Object.keys(data[0]);
    const csvRows = [
      headers.join(','),
      ...data.map(row =>
        headers.map(header => {
          const value = row[header];
          return typeof value === 'string' ? `"${value.replace(/"/g, '""')}"` : value;
        }).join(',')
      ),
    ];

    return csvRows.join('\n');
  }

  /**
   * Convert data to Excel format
   */
  private static convertToExcel(data: any[]): Buffer {
    // In a real implementation, you'd use a library like xlsx
    // For now, return CSV as buffer
    const csvData = this.convertToCSV(data);
    return Buffer.from(csvData, 'utf-8');
  }

  /**
   * Verify analytics access
   */
  private static async verifyAnalyticsAccess(organizationId: string, userId: string): Promise<boolean> {
    try {
      const membership = await prisma.organizationMember.findFirst({
        where: {
          organizationId,
          userId,
          status: 'active',
        },
      });

      return !!membership;
    } catch (error) {
      return false;
    }
  }

  /**
   * Verify board access
   */
  private static async verifyBoardAccess(boardId: string, userId: string): Promise<boolean> {
    try {
      const board = await prisma.board.findFirst({
        where: {
          id: boardId,
          OR: [
            { isPrivate: false },
            {
              members: {
                some: { userId },
              },
            },
            {
              workspace: {
                members: {
                  some: { userId },
                },
              },
            },
          ],
        },
      });

      return !!board;
    } catch (error) {
      return false;
    }
  }
}