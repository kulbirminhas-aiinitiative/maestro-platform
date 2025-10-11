import { prisma } from '@/config/database';
import { RedisService } from '@/config/redis';
import { Logger } from '@/config/logger';
import { io } from '@/server';
import {
  CreateTimeEntryData,
  UpdateTimeEntryData,
  TimeEntryFilter,
  PaginatedResult,
  PaginationMeta,
} from '@/types';
import { TimeEntry, User, Item, Board } from '@prisma/client';

type TimeEntryWithRelations = TimeEntry & {
  user?: User;
  item?: Item & {
    board?: Board;
  };
};

export class TimeService {
  /**
   * Start a new time entry
   */
  static async startTimer(
    data: CreateTimeEntryData,
    userId: string
  ): Promise<TimeEntryWithRelations> {
    try {
      // Check if user has access to the item
      if (data.itemId) {
        const hasAccess = await this.checkItemAccess(data.itemId, userId);
        if (!hasAccess) {
          throw new Error('Access denied to item');
        }
      }

      // Stop any running timers for this user
      await this.stopActiveTimers(userId);

      // Create new time entry
      const timeEntry = await prisma.timeEntry.create({
        data: {
          userId,
          itemId: data.itemId,
          boardId: data.boardId,
          description: data.description,
          startTime: new Date(),
          isRunning: true,
          billable: data.billable || false,
          metadata: data.metadata || {},
        },
        include: {
          user: true,
          item: {
            include: {
              board: true,
            },
          },
        },
      });

      // Cache active timer
      await RedisService.setCache(
        `active_timer:${userId}`,
        JSON.stringify(timeEntry),
        86400 // 24 hours
      );

      // Emit real-time event
      if (data.boardId) {
        io.to(`board:${data.boardId}`).emit('timer_started', {
          timeEntry: {
            id: timeEntry.id,
            userId,
            startTime: timeEntry.startTime,
            description: timeEntry.description,
          },
          user: {
            id: userId,
            name: timeEntry.user?.firstName || 'Unknown',
          },
        });
      }

      Logger.business(`Timer started`, {
        timeEntryId: timeEntry.id,
        userId,
        itemId: data.itemId,
        boardId: data.boardId,
      });

      return timeEntry;
    } catch (error) {
      Logger.error('Start timer failed', error as Error);
      throw error;
    }
  }

  /**
   * Stop running timer
   */
  static async stopTimer(userId: string): Promise<TimeEntryWithRelations | null> {
    try {
      // Find active timer
      const activeTimer = await prisma.timeEntry.findFirst({
        where: {
          userId,
          isRunning: true,
          endTime: null,
        },
        include: {
          user: true,
          item: {
            include: {
              board: true,
            },
          },
        },
      });

      if (!activeTimer) {
        return null;
      }

      const endTime = new Date();
      const duration = Math.floor((endTime.getTime() - activeTimer.startTime.getTime()) / 1000);

      // Update time entry
      const timeEntry = await prisma.timeEntry.update({
        where: { id: activeTimer.id },
        data: {
          endTime,
          duration,
          isRunning: false,
        },
        include: {
          user: true,
          item: {
            include: {
              board: true,
            },
          },
        },
      });

      // Remove from cache
      await RedisService.deleteCache(`active_timer:${userId}`);

      // Emit real-time event
      if (timeEntry.boardId) {
        io.to(`board:${timeEntry.boardId}`).emit('timer_stopped', {
          timeEntry: {
            id: timeEntry.id,
            userId,
            duration: timeEntry.duration,
            endTime: timeEntry.endTime,
          },
          user: {
            id: userId,
            name: timeEntry.user?.firstName || 'Unknown',
          },
        });
      }

      Logger.business(`Timer stopped`, {
        timeEntryId: timeEntry.id,
        userId,
        duration,
      });

      return timeEntry;
    } catch (error) {
      Logger.error('Stop timer failed', error as Error);
      throw error;
    }
  }

  /**
   * Get active timer for user
   */
  static async getActiveTimer(userId: string): Promise<TimeEntryWithRelations | null> {
    try {
      // Check cache first
      const cached = await RedisService.getCache(`active_timer:${userId}`);
      if (cached) {
        return JSON.parse(cached);
      }

      const activeTimer = await prisma.timeEntry.findFirst({
        where: {
          userId,
          isRunning: true,
          endTime: null,
        },
        include: {
          user: true,
          item: {
            include: {
              board: true,
            },
          },
        },
      });

      if (activeTimer) {
        await RedisService.setCache(
          `active_timer:${userId}`,
          JSON.stringify(activeTimer),
          86400
        );
      }

      return activeTimer;
    } catch (error) {
      Logger.error('Get active timer failed', error as Error);
      throw error;
    }
  }

  /**
   * Create time entry (manual entry)
   */
  static async create(
    data: CreateTimeEntryData & { duration: number; date: Date },
    userId: string
  ): Promise<TimeEntryWithRelations> {
    try {
      // Check access to item if provided
      if (data.itemId) {
        const hasAccess = await this.checkItemAccess(data.itemId, userId);
        if (!hasAccess) {
          throw new Error('Access denied to item');
        }
      }

      const startTime = new Date(data.date);
      const endTime = new Date(startTime.getTime() + (data.duration * 1000));

      const timeEntry = await prisma.timeEntry.create({
        data: {
          userId,
          itemId: data.itemId,
          boardId: data.boardId,
          description: data.description,
          startTime,
          endTime,
          duration: data.duration,
          isRunning: false,
          billable: data.billable || false,
          metadata: data.metadata || {},
        },
        include: {
          user: true,
          item: {
            include: {
              board: true,
            },
          },
        },
      });

      Logger.business(`Manual time entry created`, {
        timeEntryId: timeEntry.id,
        userId,
        duration: data.duration,
      });

      return timeEntry;
    } catch (error) {
      Logger.error('Create time entry failed', error as Error);
      throw error;
    }
  }

  /**
   * Update time entry
   */
  static async update(
    timeEntryId: string,
    data: UpdateTimeEntryData,
    userId: string
  ): Promise<TimeEntryWithRelations> {
    try {
      // Get existing entry
      const existingEntry = await prisma.timeEntry.findUnique({
        where: { id: timeEntryId },
      });

      if (!existingEntry) {
        throw new Error('Time entry not found');
      }

      // Check ownership or admin access
      if (existingEntry.userId !== userId) {
        // Check if user has admin access to the board
        if (existingEntry.boardId) {
          const hasAdminAccess = await this.checkBoardAdminAccess(existingEntry.boardId, userId);
          if (!hasAdminAccess) {
            throw new Error('Access denied');
          }
        } else {
          throw new Error('Access denied');
        }
      }

      // Prepare update data
      const updateData: any = {};
      if (data.description !== undefined) updateData.description = data.description;
      if (data.billable !== undefined) updateData.billable = data.billable;
      if (data.metadata !== undefined) updateData.metadata = data.metadata;

      // Handle duration updates for completed entries
      if (data.duration !== undefined && !existingEntry.isRunning) {
        updateData.duration = data.duration;
        updateData.endTime = new Date(existingEntry.startTime.getTime() + (data.duration * 1000));
      }

      const timeEntry = await prisma.timeEntry.update({
        where: { id: timeEntryId },
        data: updateData,
        include: {
          user: true,
          item: {
            include: {
              board: true,
            },
          },
        },
      });

      Logger.business(`Time entry updated`, {
        timeEntryId,
        userId,
      });

      return timeEntry;
    } catch (error) {
      Logger.error('Update time entry failed', error as Error);
      throw error;
    }
  }

  /**
   * Delete time entry
   */
  static async delete(timeEntryId: string, userId: string): Promise<void> {
    try {
      const existingEntry = await prisma.timeEntry.findUnique({
        where: { id: timeEntryId },
      });

      if (!existingEntry) {
        throw new Error('Time entry not found');
      }

      // Check ownership or admin access
      if (existingEntry.userId !== userId) {
        if (existingEntry.boardId) {
          const hasAdminAccess = await this.checkBoardAdminAccess(existingEntry.boardId, userId);
          if (!hasAdminAccess) {
            throw new Error('Access denied');
          }
        } else {
          throw new Error('Access denied');
        }
      }

      await prisma.timeEntry.delete({
        where: { id: timeEntryId },
      });

      // Clear cache if it was an active timer
      if (existingEntry.isRunning) {
        await RedisService.deleteCache(`active_timer:${existingEntry.userId}`);
      }

      Logger.business(`Time entry deleted`, {
        timeEntryId,
        userId,
      });
    } catch (error) {
      Logger.error('Delete time entry failed', error as Error);
      throw error;
    }
  }

  /**
   * Get time entries with filtering
   */
  static async getTimeEntries(
    filter: TimeEntryFilter,
    userId: string,
    page = 1,
    limit = 50
  ): Promise<PaginatedResult<TimeEntryWithRelations>> {
    try {
      const offset = (page - 1) * limit;

      // Build where clause
      const whereClause: any = {
        ...(filter.userId && { userId: filter.userId }),
        ...(filter.itemId && { itemId: filter.itemId }),
        ...(filter.boardId && { boardId: filter.boardId }),
        ...(filter.billable !== undefined && { billable: filter.billable }),
        ...(filter.isRunning !== undefined && { isRunning: filter.isRunning }),
        ...(filter.startDate && {
          startTime: { gte: new Date(filter.startDate) },
        }),
        ...(filter.endDate && {
          startTime: { lte: new Date(filter.endDate) },
        }),
      };

      // If not admin, restrict to user's own entries or entries they can view
      if (!filter.userId || filter.userId === userId) {
        whereClause.userId = userId;
      } else {
        // Check if user has admin access to view other users' time entries
        // This would require additional logic based on board/workspace permissions
      }

      const [timeEntries, total] = await Promise.all([
        prisma.timeEntry.findMany({
          where: whereClause,
          include: {
            user: true,
            item: {
              include: {
                board: true,
              },
            },
          },
          orderBy: { startTime: 'desc' },
          skip: offset,
          take: limit,
        }),
        prisma.timeEntry.count({
          where: whereClause,
        }),
      ]);

      const meta: PaginationMeta = {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
        hasNext: page * limit < total,
        hasPrev: page > 1,
      };

      return { data: timeEntries, meta };
    } catch (error) {
      Logger.error('Get time entries failed', error as Error);
      throw error;
    }
  }

  /**
   * Get time tracking statistics
   */
  static async getStatistics(
    userId: string,
    startDate?: Date,
    endDate?: Date,
    boardId?: string
  ): Promise<{
    totalTime: number;
    billableTime: number;
    entriesCount: number;
    averageSessionDuration: number;
    topItems: Array<{ itemId: string; itemName: string; totalTime: number }>;
  }> {
    try {
      const whereClause: any = {
        userId,
        isRunning: false,
        ...(startDate && { startTime: { gte: startDate } }),
        ...(endDate && { startTime: { lte: endDate } }),
        ...(boardId && { boardId }),
      };

      const [stats] = await prisma.$queryRaw<Array<{
        totalTime: bigint;
        billableTime: bigint;
        entriesCount: bigint;
        averageSessionDuration: number;
      }>>`
        SELECT
          COALESCE(SUM(duration), 0) as "totalTime",
          COALESCE(SUM(CASE WHEN billable THEN duration ELSE 0 END), 0) as "billableTime",
          COUNT(*) as "entriesCount",
          COALESCE(AVG(duration), 0) as "averageSessionDuration"
        FROM time_entries
        WHERE user_id = ${userId}
          AND is_running = false
          ${startDate ? `AND start_time >= ${startDate.toISOString()}` : ''}
          ${endDate ? `AND start_time <= ${endDate.toISOString()}` : ''}
          ${boardId ? `AND board_id = ${boardId}` : ''}
      `;

      // Get top items by time spent
      const topItems = await prisma.$queryRaw<Array<{
        itemId: string;
        itemName: string;
        totalTime: bigint;
      }>>`
        SELECT
          te.item_id as "itemId",
          i.name as "itemName",
          SUM(te.duration) as "totalTime"
        FROM time_entries te
        INNER JOIN items i ON te.item_id = i.id
        WHERE te.user_id = ${userId}
          AND te.is_running = false
          AND te.item_id IS NOT NULL
          ${startDate ? `AND te.start_time >= ${startDate.toISOString()}` : ''}
          ${endDate ? `AND te.start_time <= ${endDate.toISOString()}` : ''}
          ${boardId ? `AND te.board_id = ${boardId}` : ''}
        GROUP BY te.item_id, i.name
        ORDER BY "totalTime" DESC
        LIMIT 10
      `;

      return {
        totalTime: Number(stats.totalTime),
        billableTime: Number(stats.billableTime),
        entriesCount: Number(stats.entriesCount),
        averageSessionDuration: stats.averageSessionDuration,
        topItems: topItems.map(item => ({
          itemId: item.itemId,
          itemName: item.itemName,
          totalTime: Number(item.totalTime),
        })),
      };
    } catch (error) {
      Logger.error('Get time statistics failed', error as Error);
      throw error;
    }
  }

  // ============================================================================
  // PRIVATE METHODS
  // ============================================================================

  /**
   * Stop all active timers for a user
   */
  private static async stopActiveTimers(userId: string): Promise<void> {
    const activeTimers = await prisma.timeEntry.findMany({
      where: {
        userId,
        isRunning: true,
        endTime: null,
      },
    });

    for (const timer of activeTimers) {
      const endTime = new Date();
      const duration = Math.floor((endTime.getTime() - timer.startTime.getTime()) / 1000);

      await prisma.timeEntry.update({
        where: { id: timer.id },
        data: {
          endTime,
          duration,
          isRunning: false,
        },
      });
    }

    // Clear cache
    await RedisService.deleteCache(`active_timer:${userId}`);
  }

  /**
   * Check if user has access to item
   */
  private static async checkItemAccess(itemId: string, userId: string): Promise<boolean> {
    try {
      const item = await prisma.item.findUnique({
        where: { id: itemId },
        include: {
          board: {
            include: {
              members: {
                where: { userId },
              },
              workspace: {
                include: {
                  members: {
                    where: { userId },
                  },
                },
              },
            },
          },
        },
      });

      if (!item) return false;

      // Board members have access
      if (item.board.members.length > 0) return true;

      // If board is not private, workspace members have access
      if (!item.board.isPrivate && item.board.workspace.members.length > 0) return true;

      return false;
    } catch (error) {
      Logger.error('Failed to check item access', error as Error);
      return false;
    }
  }

  /**
   * Check if user has admin access to board
   */
  private static async checkBoardAdminAccess(boardId: string, userId: string): Promise<boolean> {
    try {
      const member = await prisma.boardMember.findUnique({
        where: {
          boardId_userId: {
            boardId,
            userId,
          },
        },
      });

      return !!member && member.role === 'admin';
    } catch (error) {
      Logger.error('Failed to check board admin access', error as Error);
      return false;
    }
  }
}