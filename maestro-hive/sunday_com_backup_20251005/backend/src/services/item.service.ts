import { prisma } from '@/config/database';
import { RedisService } from '@/config/redis';
import { Logger } from '@/config/logger';
import { io } from '@/server';
import {
  CreateItemData,
  UpdateItemData,
  ItemFilter,
  ItemSort,
  PaginatedResult,
  PaginationMeta,
} from '@/types';
import { Item, ItemAssignment, User, Comment, BoardService } from '@prisma/client';
import { Decimal } from '@prisma/client/runtime/library';

type ItemWithRelations = Item & {
  assignments?: Array<ItemAssignment & { user: User }>;
  parent?: Item;
  children?: Item[];
  dependencies?: Array<{ predecessor: Item; successor: Item }>;
  comments?: Comment[];
  creator?: User;
  _count?: {
    comments: number;
    children: number;
    dependencies: number;
  };
};

export class ItemService {
  /**
   * Create a new item
   */
  static async create(
    data: CreateItemData,
    creatorId: string
  ): Promise<ItemWithRelations> {
    try {
      // Check if user has access to board
      const hasAccess = await this.checkBoardAccess(data.boardId, creatorId);
      if (!hasAccess) {
        throw new Error('Access denied to board');
      }

      // Calculate position if not provided
      const position = data.position !== undefined
        ? new Decimal(data.position)
        : await this.getNextPosition(data.boardId, data.parentId);

      // Create item with assignments
      const item = await prisma.item.create({
        data: {
          name: data.name,
          description: data.description,
          boardId: data.boardId,
          parentId: data.parentId,
          itemData: data.itemData || {},
          position,
          createdBy: creatorId,
          assignments: data.assigneeIds
            ? {
                create: data.assigneeIds.map((userId) => ({
                  userId,
                  assignedBy: creatorId,
                })),
              }
            : undefined,
        },
        include: {
          assignments: {
            include: {
              user: true,
            },
          },
          parent: true,
          creator: true,
          _count: {
            select: {
              comments: true,
              children: true,
              dependencies: true,
            },
          },
        },
      });

      // Log activity
      await this.logActivity(
        item.boardId,
        item.id,
        creatorId,
        'item_created',
        null,
        {
          name: item.name,
          description: item.description,
          itemData: item.itemData,
        }
      );

      // Emit real-time event
      io.to(`board:${data.boardId}`).emit('item_created', {
        item: {
          id: item.id,
          name: item.name,
          boardId: item.boardId,
          position: item.position.toString(),
          assignees: item.assignments?.map(a => a.user) || [],
        },
        user: {
          id: creatorId,
          name: item.creator?.firstName || 'Unknown',
        },
      });

      Logger.business(`Item created: ${item.name}`, {
        itemId: item.id,
        boardId: data.boardId,
        creatorId,
      });

      return item;
    } catch (error) {
      Logger.error('Item creation failed', error as Error);
      throw error;
    }
  }

  /**
   * Get item by ID
   */
  static async getById(
    itemId: string,
    userId: string,
    includeComments = false,
    includeChildren = false,
    includeDependencies = false
  ): Promise<ItemWithRelations | null> {
    try {
      const cacheKey = `item:${itemId}:${includeComments}:${includeChildren}:${includeDependencies}`;
      const cached = await RedisService.getCache(cacheKey);
      if (cached) {
        return cached;
      }

      const item = await prisma.item.findFirst({
        where: {
          id: itemId,
          deletedAt: null,
          board: {
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
        },
        include: {
          assignments: {
            include: {
              user: true,
            },
          },
          parent: true,
          children: includeChildren
            ? {
                where: { deletedAt: null },
                orderBy: { position: 'asc' },
              }
            : false,
          dependencies: includeDependencies
            ? {
                include: {
                  predecessor: true,
                  successor: true,
                },
              }
            : false,
          comments: includeComments
            ? {
                where: { deletedAt: null },
                include: {
                  user: true,
                },
                orderBy: { createdAt: 'desc' },
                take: 10, // Latest 10 comments
              }
            : false,
          creator: true,
          _count: {
            select: {
              comments: {
                where: { deletedAt: null },
              },
              children: {
                where: { deletedAt: null },
              },
              dependencies: true,
            },
          },
        },
      });

      if (item) {
        await RedisService.setCache(cacheKey, item, 300); // 5 minutes
      }

      return item;
    } catch (error) {
      Logger.error('Failed to get item', error as Error);
      throw error;
    }
  }

  /**
   * Get items for a board with filtering and sorting
   */
  static async getByBoard(
    boardId: string,
    userId: string,
    filter: ItemFilter = {},
    sort: ItemSort[] = [{ field: 'position', direction: 'asc' }],
    page = 1,
    limit = 50
  ): Promise<PaginatedResult<ItemWithRelations>> {
    try {
      // Check board access
      const hasAccess = await this.checkBoardAccess(boardId, userId);
      if (!hasAccess) {
        throw new Error('Access denied to board');
      }

      const offset = (page - 1) * limit;

      // Build where clause
      const whereClause: any = {
        boardId,
        deletedAt: null,
        ...(filter.parentId !== undefined && { parentId: filter.parentId }),
        ...(filter.assigneeIds?.length && {
          assignments: {
            some: {
              userId: { in: filter.assigneeIds },
            },
          },
        }),
        ...(filter.search && {
          OR: [
            { name: { contains: filter.search, mode: 'insensitive' } },
            { description: { contains: filter.search, mode: 'insensitive' } },
          ],
        }),
        ...(filter.status?.length && {
          itemData: {
            path: ['status'],
            in: filter.status,
          },
        }),
        ...(filter.dueDateFrom && {
          itemData: {
            path: ['dueDate'],
            gte: filter.dueDateFrom,
          },
        }),
        ...(filter.dueDateTo && {
          itemData: {
            path: ['dueDate'],
            lte: filter.dueDateTo,
          },
        }),
      };

      // Build order by clause
      const orderBy = sort.map(s => {
        switch (s.field) {
          case 'position':
            return { position: s.direction };
          case 'created_at':
            return { createdAt: s.direction };
          case 'updated_at':
            return { updatedAt: s.direction };
          case 'name':
            return { name: s.direction };
          case 'due_date':
            return {
              itemData: {
                path: ['dueDate'],
                sort: s.direction,
              },
            };
          default:
            return { position: 'asc' };
        }
      });

      const [items, total] = await Promise.all([
        prisma.item.findMany({
          where: whereClause,
          include: {
            assignments: {
              include: {
                user: true,
              },
            },
            parent: true,
            creator: true,
            _count: {
              select: {
                comments: {
                  where: { deletedAt: null },
                },
                children: {
                  where: { deletedAt: null },
                },
                dependencies: true,
              },
            },
          },
          orderBy,
          skip: offset,
          take: limit,
        }),
        prisma.item.count({
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

      return { data: items, meta };
    } catch (error) {
      Logger.error('Failed to get board items', error as Error);
      throw error;
    }
  }

  /**
   * Update item
   */
  static async update(
    itemId: string,
    data: UpdateItemData,
    userId: string
  ): Promise<ItemWithRelations> {
    try {
      // Get current item for change tracking
      const currentItem = await prisma.item.findUnique({
        where: { id: itemId },
        include: {
          assignments: true,
        },
      });

      if (!currentItem) {
        throw new Error('Item not found');
      }

      // Check board access
      const hasAccess = await this.checkBoardAccess(currentItem.boardId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      // Prepare update data
      const updateData: any = {};
      if (data.name !== undefined) updateData.name = data.name;
      if (data.description !== undefined) updateData.description = data.description;
      if (data.parentId !== undefined) updateData.parentId = data.parentId;
      if (data.itemData !== undefined) updateData.itemData = data.itemData;
      if (data.position !== undefined) updateData.position = new Decimal(data.position);

      // Handle assignee updates
      if (data.assigneeIds !== undefined) {
        const currentAssigneeIds = currentItem.assignments.map(a => a.userId);
        const newAssigneeIds = data.assigneeIds;

        const toRemove = currentAssigneeIds.filter(id => !newAssigneeIds.includes(id));
        const toAdd = newAssigneeIds.filter(id => !currentAssigneeIds.includes(id));

        updateData.assignments = {
          deleteMany: toRemove.length > 0 ? { userId: { in: toRemove } } : undefined,
          create: toAdd.map(userId => ({
            userId,
            assignedBy: userId,
          })),
        };
      }

      const item = await prisma.item.update({
        where: { id: itemId },
        data: updateData,
        include: {
          assignments: {
            include: {
              user: true,
            },
          },
          parent: true,
          creator: true,
          _count: {
            select: {
              comments: {
                where: { deletedAt: null },
              },
              children: {
                where: { deletedAt: null },
              },
              dependencies: true,
            },
          },
        },
      });

      // Track changes for activity log
      const changes: any = {};
      if (data.name && data.name !== currentItem.name) {
        changes.name = { old: currentItem.name, new: data.name };
      }
      if (data.description !== undefined && data.description !== currentItem.description) {
        changes.description = { old: currentItem.description, new: data.description };
      }
      if (data.itemData) {
        // Track specific field changes in itemData
        const oldData = currentItem.itemData as any;
        const newData = data.itemData;
        for (const [key, value] of Object.entries(newData)) {
          if (oldData[key] !== value) {
            changes[`data.${key}`] = { old: oldData[key], new: value };
          }
        }
      }

      // Log activity
      if (Object.keys(changes).length > 0) {
        await this.logActivity(
          item.boardId,
          itemId,
          userId,
          'item_updated',
          currentItem.itemData,
          item.itemData,
          { changes }
        );
      }

      // Invalidate caches
      await this.invalidateCaches(itemId, item.boardId);

      // Emit real-time event
      io.to(`board:${item.boardId}`).emit('item_updated', {
        itemId,
        changes,
        updatedBy: userId,
      });

      Logger.business(`Item updated: ${item.name}`, {
        itemId,
        boardId: item.boardId,
        userId,
      });

      return item;
    } catch (error) {
      Logger.error('Item update failed', error as Error);
      throw error;
    }
  }

  /**
   * Delete item (soft delete)
   */
  static async delete(itemId: string, userId: string): Promise<void> {
    try {
      const item = await prisma.item.findUnique({
        where: { id: itemId },
      });

      if (!item) {
        throw new Error('Item not found');
      }

      // Check board access
      const hasAccess = await this.checkBoardAccess(item.boardId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      await prisma.item.update({
        where: { id: itemId },
        data: { deletedAt: new Date() },
      });

      // Log activity
      await this.logActivity(
        item.boardId,
        itemId,
        userId,
        'item_deleted',
        item.itemData,
        null
      );

      // Invalidate caches
      await this.invalidateCaches(itemId, item.boardId);

      // Emit real-time event
      io.to(`board:${item.boardId}`).emit('item_deleted', {
        itemId,
        boardId: item.boardId,
        deletedBy: userId,
      });

      Logger.business(`Item deleted`, {
        itemId,
        boardId: item.boardId,
        userId,
      });
    } catch (error) {
      Logger.error('Item deletion failed', error as Error);
      throw error;
    }
  }

  /**
   * Bulk update items
   */
  static async bulkUpdate(
    itemIds: string[],
    updates: {
      itemData?: Record<string, any>;
      assigneeIds?: string[];
      parentId?: string;
    },
    userId: string
  ): Promise<{ updatedCount: number; errors: Array<{ itemId: string; error: string }> }> {
    try {
      const results = {
        updatedCount: 0,
        errors: [] as Array<{ itemId: string; error: string }>,
      };

      // Process items in batches
      const batchSize = 10;
      for (let i = 0; i < itemIds.length; i += batchSize) {
        const batch = itemIds.slice(i, i + batchSize);

        await Promise.allSettled(
          batch.map(async (itemId) => {
            try {
              await this.update(itemId, updates, userId);
              results.updatedCount++;
            } catch (error) {
              results.errors.push({
                itemId,
                error: (error as Error).message,
              });
            }
          })
        );
      }

      Logger.business(`Bulk update completed`, {
        totalItems: itemIds.length,
        updatedCount: results.updatedCount,
        errorCount: results.errors.length,
        userId,
      });

      return results;
    } catch (error) {
      Logger.error('Bulk update failed', error as Error);
      throw error;
    }
  }

  /**
   * Bulk delete items
   */
  static async bulkDelete(
    itemIds: string[],
    userId: string
  ): Promise<{ deletedCount: number; errors: Array<{ itemId: string; error: string }> }> {
    try {
      const results = {
        deletedCount: 0,
        errors: [] as Array<{ itemId: string; error: string }>,
      };

      // Process items in batches
      const batchSize = 10;
      for (let i = 0; i < itemIds.length; i += batchSize) {
        const batch = itemIds.slice(i, i + batchSize);

        await Promise.allSettled(
          batch.map(async (itemId) => {
            try {
              await this.delete(itemId, userId);
              results.deletedCount++;
            } catch (error) {
              results.errors.push({
                itemId,
                error: (error as Error).message,
              });
            }
          })
        );
      }

      Logger.business(`Bulk delete completed`, {
        totalItems: itemIds.length,
        deletedCount: results.deletedCount,
        errorCount: results.errors.length,
        userId,
      });

      return results;
    } catch (error) {
      Logger.error('Bulk delete failed', error as Error);
      throw error;
    }
  }

  /**
   * Add dependency between items
   */
  static async addDependency(
    predecessorId: string,
    successorId: string,
    dependencyType: string = 'blocks',
    userId: string
  ): Promise<void> {
    try {
      // Check if both items exist and user has access
      const [predecessor, successor] = await Promise.all([
        prisma.item.findUnique({ where: { id: predecessorId } }),
        prisma.item.findUnique({ where: { id: successorId } }),
      ]);

      if (!predecessor || !successor) {
        throw new Error('One or both items not found');
      }

      // Check board access for both items
      const [hasAccessToPredecessor, hasAccessToSuccessor] = await Promise.all([
        this.checkBoardAccess(predecessor.boardId, userId),
        this.checkBoardAccess(successor.boardId, userId),
      ]);

      if (!hasAccessToPredecessor || !hasAccessToSuccessor) {
        throw new Error('Access denied to one or both items');
      }

      // Check for circular dependencies
      const hasCircularDependency = await this.checkCircularDependency(predecessorId, successorId);
      if (hasCircularDependency) {
        throw new Error('Creating this dependency would create a circular dependency');
      }

      await prisma.itemDependency.create({
        data: {
          predecessorId,
          successorId,
          dependencyType,
          createdBy: userId,
        },
      });

      // Invalidate caches
      await Promise.all([
        this.invalidateCaches(predecessorId, predecessor.boardId),
        this.invalidateCaches(successorId, successor.boardId),
      ]);

      Logger.business(`Item dependency added`, {
        predecessorId,
        successorId,
        dependencyType,
        userId,
      });
    } catch (error) {
      Logger.error('Add dependency failed', error as Error);
      throw error;
    }
  }

  /**
   * Remove dependency between items
   */
  static async removeDependency(
    predecessorId: string,
    successorId: string,
    userId: string
  ): Promise<void> {
    try {
      await prisma.itemDependency.delete({
        where: {
          predecessorId_successorId: {
            predecessorId,
            successorId,
          },
        },
      });

      Logger.business(`Item dependency removed`, {
        predecessorId,
        successorId,
        userId,
      });
    } catch (error) {
      Logger.error('Remove dependency failed', error as Error);
      throw error;
    }
  }

  // ============================================================================
  // PRIVATE METHODS
  // ============================================================================

  /**
   * Check if user has access to board
   */
  private static async checkBoardAccess(boardId: string, userId: string): Promise<boolean> {
    try {
      // Import BoardService to avoid circular dependency
      const { BoardService } = await import('./board.service');
      return await BoardService.hasReadAccess(boardId, userId);
    } catch (error) {
      Logger.error('Failed to check board access', error as Error);
      return false;
    }
  }

  /**
   * Get next position for item
   */
  private static async getNextPosition(boardId: string, parentId?: string): Promise<Decimal> {
    const lastItem = await prisma.item.findFirst({
      where: {
        boardId,
        parentId,
        deletedAt: null,
      },
      orderBy: { position: 'desc' },
      select: { position: true },
    });

    if (lastItem) {
      return lastItem.position.add(1);
    }

    return new Decimal(1);
  }

  /**
   * Move item to new position and/or parent
   */
  static async move(
    itemId: string,
    data: {
      position: number;
      parentId?: string | null;
      boardId?: string;
    },
    userId: string
  ): Promise<{
    item: ItemWithRelations;
    affectedItems: Array<{
      itemId: string;
      oldPosition: number;
      newPosition: number;
    }>;
  }> {
    try {
      // Get current item
      const currentItem = await prisma.item.findUnique({
        where: { id: itemId },
        include: {
          assignments: {
            include: {
              user: true,
            },
          },
          parent: true,
          creator: true,
        },
      });

      if (!currentItem) {
        throw new Error('Item not found');
      }

      // Check access to current board
      const hasCurrentAccess = await this.checkBoardAccess(currentItem.boardId, userId);
      if (!hasCurrentAccess) {
        throw new Error('Access denied to current board');
      }

      const targetBoardId = data.boardId || currentItem.boardId;

      // Check access to target board if different
      if (data.boardId && data.boardId !== currentItem.boardId) {
        const hasTargetAccess = await this.checkBoardAccess(data.boardId, userId);
        if (!hasTargetAccess) {
          throw new Error('Access denied to target board');
        }
      }

      const newPosition = new Decimal(data.position);
      const affectedItems: Array<{
        itemId: string;
        oldPosition: number;
        newPosition: number;
      }> = [];

      // Get items that need position updates
      const itemsToUpdate = await prisma.item.findMany({
        where: {
          boardId: targetBoardId,
          parentId: data.parentId,
          id: { not: itemId },
          position: { gte: newPosition },
          deletedAt: null,
        },
        orderBy: { position: 'asc' },
      });

      // Update positions of affected items
      for (const item of itemsToUpdate) {
        const oldPos = Number(item.position);
        const newPos = oldPos + 1;

        await prisma.item.update({
          where: { id: item.id },
          data: { position: new Decimal(newPos) },
        });

        affectedItems.push({
          itemId: item.id,
          oldPosition: oldPos,
          newPosition: newPos,
        });
      }

      // Update the moved item
      const updatedItem = await prisma.item.update({
        where: { id: itemId },
        data: {
          position: newPosition,
          parentId: data.parentId,
          boardId: targetBoardId,
        },
        include: {
          assignments: {
            include: {
              user: true,
            },
          },
          parent: true,
          creator: true,
          _count: {
            select: {
              comments: true,
              children: true,
              dependencies: true,
            },
          },
        },
      });

      // Log activity
      await this.logActivity(
        targetBoardId,
        itemId,
        userId,
        'item_moved',
        {
          position: Number(currentItem.position),
          parentId: currentItem.parentId,
          boardId: currentItem.boardId,
        },
        {
          position: data.position,
          parentId: data.parentId,
          boardId: targetBoardId,
        }
      );

      // Emit real-time event
      io.to(`board:${currentItem.boardId}`).emit('item_moved', {
        itemId,
        from: {
          position: Number(currentItem.position),
          parentId: currentItem.parentId,
          boardId: currentItem.boardId,
        },
        to: {
          position: data.position,
          parentId: data.parentId,
          boardId: targetBoardId,
        },
        affectedItems,
        movedBy: userId,
      });

      // If moved to different board, emit to target board too
      if (data.boardId && data.boardId !== currentItem.boardId) {
        io.to(`board:${data.boardId}`).emit('item_moved', {
          itemId,
          from: {
            position: Number(currentItem.position),
            parentId: currentItem.parentId,
            boardId: currentItem.boardId,
          },
          to: {
            position: data.position,
            parentId: data.parentId,
            boardId: targetBoardId,
          },
          affectedItems,
          movedBy: userId,
        });
      }

      // Invalidate caches
      await this.invalidateCaches(itemId, currentItem.boardId);
      if (data.boardId && data.boardId !== currentItem.boardId) {
        await this.invalidateCaches(itemId, data.boardId);
      }

      Logger.business(`Item moved: ${updatedItem.name}`, {
        itemId,
        from: {
          position: Number(currentItem.position),
          parentId: currentItem.parentId,
          boardId: currentItem.boardId,
        },
        to: {
          position: data.position,
          parentId: data.parentId,
          boardId: targetBoardId,
        },
        userId,
      });

      return {
        item: updatedItem,
        affectedItems,
      };
    } catch (error) {
      Logger.error('Item move failed', error as Error);
      throw error;
    }
  }

  /**
   * Check for circular dependencies
   */
  private static async checkCircularDependency(
    predecessorId: string,
    successorId: string
  ): Promise<boolean> {
    try {
      // Use recursive CTE to check for circular dependencies
      const result = await prisma.$queryRaw<Array<{ exists: boolean }>>`
        WITH RECURSIVE dependency_path AS (
          SELECT successor_id, predecessor_id, 1 as depth
          FROM item_dependencies
          WHERE successor_id = ${successorId}

          UNION ALL

          SELECT id.successor_id, dp.predecessor_id, dp.depth + 1
          FROM item_dependencies id
          INNER JOIN dependency_path dp ON id.predecessor_id = dp.successor_id
          WHERE dp.depth < 10
        )
        SELECT EXISTS(
          SELECT 1 FROM dependency_path
          WHERE successor_id = ${predecessorId}
        ) as exists
      `;

      return result[0]?.exists || false;
    } catch (error) {
      Logger.error('Failed to check circular dependency', error as Error);
      return false;
    }
  }

  /**
   * Log activity for audit trail
   */
  private static async logActivity(
    boardId: string,
    itemId: string,
    userId: string,
    action: string,
    oldValues: any,
    newValues: any,
    metadata: any = {}
  ): Promise<void> {
    try {
      // Get organization and workspace IDs
      const board = await prisma.board.findUnique({
        where: { id: boardId },
        select: {
          workspace: {
            select: {
              id: true,
              organizationId: true,
            },
          },
        },
      });

      if (board) {
        await prisma.activityLog.create({
          data: {
            organizationId: board.workspace.organizationId,
            workspaceId: board.workspace.id,
            boardId,
            itemId,
            userId,
            action,
            entityType: 'item',
            entityId: itemId,
            oldValues,
            newValues,
            metadata,
          },
        });
      }
    } catch (error) {
      Logger.error('Failed to log activity', error as Error);
      // Don't throw error for activity logging failures
    }
  }

  /**
   * Invalidate related caches
   */
  private static async invalidateCaches(itemId: string, boardId: string): Promise<void> {
    await Promise.all([
      RedisService.deleteCachePattern(`item:${itemId}:*`),
      RedisService.deleteCachePattern(`board:${boardId}:*`),
    ]);
  }
}