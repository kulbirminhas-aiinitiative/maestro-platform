import { prisma } from '@/config/database';
import { Logger } from '@/config/logger';
import { RedisService } from '@/config/redis';
import {
  CreateItemData,
  UpdateItemData,
  BulkUpdateItemsData,
  ItemFilter,
  PaginatedResult,
  SortOption,
  ApiError,
} from '@/types';
import { v4 as uuidv4 } from 'uuid';

export class ItemService {
  /**
   * Create a new item
   */
  static async createItem(
    boardId: string,
    userId: string,
    data: CreateItemData
  ): Promise<any> {
    try {
      // Verify board access
      const hasAccess = await this.verifyBoardAccess(boardId, userId);
      if (!hasAccess) {
        throw new Error('Board not found or access denied');
      }

      // Get next position
      const lastItem = await prisma.item.findFirst({
        where: { boardId, parentId: data.parentId || null },
        orderBy: { position: 'desc' },
      });
      const position = data.position || (lastItem?.position || 0) + 1;

      // Create item
      const item = await prisma.item.create({
        data: {
          id: uuidv4(),
          boardId,
          parentId: data.parentId,
          name: data.name,
          description: data.description,
          itemData: data.data || {},
          position,
          createdBy: userId,
        },
        include: {
          board: {
            select: { id: true, name: true, workspaceId: true },
          },
          parent: {
            select: { id: true, name: true },
          },
          children: {
            select: { id: true, name: true },
            where: { deletedAt: null },
          },
          assignments: {
            include: {
              user: {
                select: { id: true, firstName: true, lastName: true, avatarUrl: true },
              },
            },
          },
          dependencies: {
            include: {
              predecessor: {
                select: { id: true, name: true },
              },
            },
          },
          createdByUser: {
            select: { id: true, firstName: true, lastName: true, avatarUrl: true },
          },
        },
      });

      // Add assignments if provided
      if (data.assigneeIds && data.assigneeIds.length > 0) {
        await this.addAssignments(item.id, userId, data.assigneeIds);
      }

      // Invalidate board cache
      await RedisService.deleteCache(`board:${boardId}`);

      Logger.api(`Item created: ${item.name}`, { itemId: item.id, boardId, userId });

      return item;
    } catch (error) {
      Logger.error('Item creation failed', error as Error);
      throw error;
    }
  }

  /**
   * Get item by ID
   */
  static async getItem(itemId: string, userId: string): Promise<any> {
    try {
      const item = await prisma.item.findFirst({
        where: {
          id: itemId,
          deletedAt: null,
        },
        include: {
          board: {
            select: { id: true, name: true, workspaceId: true },
          },
          parent: {
            select: { id: true, name: true },
          },
          children: {
            select: { id: true, name: true, position: true },
            where: { deletedAt: null },
            orderBy: { position: 'asc' },
          },
          assignments: {
            include: {
              user: {
                select: { id: true, firstName: true, lastName: true, avatarUrl: true },
              },
              assignedBy: {
                select: { id: true, firstName: true, lastName: true },
              },
            },
          },
          dependencies: {
            include: {
              predecessor: {
                select: { id: true, name: true },
              },
              successor: {
                select: { id: true, name: true },
              },
            },
          },
          comments: {
            where: { deletedAt: null },
            include: {
              user: {
                select: { id: true, firstName: true, lastName: true, avatarUrl: true },
              },
            },
            orderBy: { createdAt: 'desc' },
            take: 10, // Latest 10 comments
          },
          timeEntries: {
            include: {
              user: {
                select: { id: true, firstName: true, lastName: true },
              },
            },
            orderBy: { startTime: 'desc' },
            take: 10, // Latest 10 time entries
          },
          createdByUser: {
            select: { id: true, firstName: true, lastName: true, avatarUrl: true },
          },
        },
      });

      if (!item) {
        throw new Error('Item not found');
      }

      // Verify board access
      const hasAccess = await this.verifyBoardAccess(item.boardId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      return item;
    } catch (error) {
      Logger.error('Get item failed', error as Error);
      throw error;
    }
  }

  /**
   * Update item
   */
  static async updateItem(
    itemId: string,
    userId: string,
    data: UpdateItemData
  ): Promise<any> {
    try {
      // Get current item
      const currentItem = await prisma.item.findUnique({
        where: { id: itemId },
        include: { board: true },
      });

      if (!currentItem || currentItem.deletedAt) {
        throw new Error('Item not found');
      }

      // Verify board access
      const hasAccess = await this.verifyBoardAccess(currentItem.boardId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      // Update item
      const item = await prisma.item.update({
        where: { id: itemId },
        data: {
          name: data.name,
          description: data.description,
          itemData: data.data,
          position: data.position,
          updatedAt: new Date(),
        },
        include: {
          board: {
            select: { id: true, name: true, workspaceId: true },
          },
          parent: {
            select: { id: true, name: true },
          },
          children: {
            select: { id: true, name: true },
            where: { deletedAt: null },
          },
          assignments: {
            include: {
              user: {
                select: { id: true, firstName: true, lastName: true, avatarUrl: true },
              },
            },
          },
          createdByUser: {
            select: { id: true, firstName: true, lastName: true, avatarUrl: true },
          },
        },
      });

      // Update assignments if provided
      if (data.assigneeIds !== undefined) {
        await this.updateAssignments(itemId, userId, data.assigneeIds);
      }

      // Invalidate board cache
      await RedisService.deleteCache(`board:${currentItem.boardId}`);

      Logger.api(`Item updated: ${item.name}`, { itemId, userId });

      return item;
    } catch (error) {
      Logger.error('Item update failed', error as Error);
      throw error;
    }
  }

  /**
   * Delete item (soft delete)
   */
  static async deleteItem(itemId: string, userId: string): Promise<void> {
    try {
      const item = await prisma.item.findUnique({
        where: { id: itemId },
        include: { board: true },
      });

      if (!item || item.deletedAt) {
        throw new Error('Item not found');
      }

      // Verify board access
      const hasAccess = await this.verifyBoardAccess(item.boardId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      // Soft delete item and all children
      await this.softDeleteItemTree(itemId);

      // Invalidate board cache
      await RedisService.deleteCache(`board:${item.boardId}`);

      Logger.api(`Item deleted: ${itemId}`, { itemId, userId });
    } catch (error) {
      Logger.error('Item deletion failed', error as Error);
      throw error;
    }
  }

  /**
   * Bulk update items
   */
  static async bulkUpdateItems(
    userId: string,
    data: BulkUpdateItemsData
  ): Promise<any[]> {
    try {
      const results = [];

      // Group items by board for permission checks
      const itemsByBoard = new Map<string, string[]>();

      for (const itemId of data.itemIds) {
        const item = await prisma.item.findUnique({
          where: { id: itemId },
          select: { id: true, boardId: true },
        });

        if (item) {
          if (!itemsByBoard.has(item.boardId)) {
            itemsByBoard.set(item.boardId, []);
          }
          itemsByBoard.get(item.boardId)!.push(itemId);
        }
      }

      // Check permissions for each board
      for (const [boardId, itemIds] of itemsByBoard) {
        const hasAccess = await this.verifyBoardAccess(boardId, userId);
        if (!hasAccess) {
          throw new Error(`Access denied to board: ${boardId}`);
        }

        // Update items in this board
        for (const itemId of itemIds) {
          try {
            const updatedItem = await prisma.item.update({
              where: { id: itemId },
              data: {
                ...data.updates,
                updatedAt: new Date(),
              },
              include: {
                assignments: {
                  include: {
                    user: {
                      select: { id: true, firstName: true, lastName: true, avatarUrl: true },
                    },
                  },
                },
              },
            });

            results.push(updatedItem);
          } catch (error) {
            Logger.error(`Failed to update item ${itemId}`, error as Error);
            // Continue with other items
          }
        }

        // Invalidate board cache
        await RedisService.deleteCache(`board:${boardId}`);
      }

      Logger.api(`Bulk updated ${results.length} items`, { userId });

      return results;
    } catch (error) {
      Logger.error('Bulk update items failed', error as Error);
      throw error;
    }
  }

  /**
   * Get board items with filtering and pagination
   */
  static async getBoardItems(
    boardId: string,
    userId: string,
    filter: ItemFilter = {},
    sort: SortOption[] = [{ field: 'position', direction: 'asc' }],
    page: number = 1,
    limit: number = 50
  ): Promise<PaginatedResult<any>> {
    try {
      // Verify board access
      const hasAccess = await this.verifyBoardAccess(boardId, userId);
      if (!hasAccess) {
        throw new Error('Board not found or access denied');
      }

      const offset = (page - 1) * limit;

      // Build where condition
      const where: any = {
        boardId,
        deletedAt: null,
      };

      if (filter.parentId !== undefined) {
        where.parentId = filter.parentId;
      }

      if (filter.assigneeIds && filter.assigneeIds.length > 0) {
        where.assignments = {
          some: {
            userId: { in: filter.assigneeIds },
          },
        };
      }

      if (filter.search) {
        where.OR = [
          { name: { contains: filter.search, mode: 'insensitive' } },
          { description: { contains: filter.search, mode: 'insensitive' } },
        ];
      }

      if (filter.dueDateFrom || filter.dueDateTo) {
        where.itemData = {};
        if (filter.dueDateFrom) {
          where.itemData.dueDate = { gte: filter.dueDateFrom };
        }
        if (filter.dueDateTo) {
          where.itemData.dueDate = {
            ...where.itemData.dueDate,
            lte: filter.dueDateTo,
          };
        }
      }

      // Build order by
      const orderBy = sort.map((s) => ({ [s.field]: s.direction }));

      const [items, total] = await Promise.all([
        prisma.item.findMany({
          where,
          include: {
            parent: {
              select: { id: true, name: true },
            },
            children: {
              select: { id: true, name: true },
              where: { deletedAt: null },
            },
            assignments: {
              include: {
                user: {
                  select: { id: true, firstName: true, lastName: true, avatarUrl: true },
                },
              },
            },
            createdByUser: {
              select: { id: true, firstName: true, lastName: true, avatarUrl: true },
            },
            _count: {
              select: { comments: true, timeEntries: true },
            },
          },
          orderBy,
          skip: offset,
          take: limit,
        }),
        prisma.item.count({ where }),
      ]);

      return {
        data: items,
        meta: {
          page,
          limit,
          total,
          totalPages: Math.ceil(total / limit),
          hasNext: page * limit < total,
          hasPrev: page > 1,
        },
      };
    } catch (error) {
      Logger.error('Get board items failed', error as Error);
      throw error;
    }
  }

  /**
   * Move item to different position or parent
   */
  static async moveItem(
    itemId: string,
    userId: string,
    targetPosition: number,
    targetParentId?: string
  ): Promise<any> {
    try {
      const item = await prisma.item.findUnique({
        where: { id: itemId },
        include: { board: true },
      });

      if (!item || item.deletedAt) {
        throw new Error('Item not found');
      }

      // Verify board access
      const hasAccess = await this.verifyBoardAccess(item.boardId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      // Update item position and parent
      const updatedItem = await prisma.item.update({
        where: { id: itemId },
        data: {
          position: targetPosition,
          parentId: targetParentId,
          updatedAt: new Date(),
        },
        include: {
          parent: {
            select: { id: true, name: true },
          },
          assignments: {
            include: {
              user: {
                select: { id: true, firstName: true, lastName: true, avatarUrl: true },
              },
            },
          },
        },
      });

      // Invalidate board cache
      await RedisService.deleteCache(`board:${item.boardId}`);

      Logger.api(`Item moved: ${itemId}`, { itemId, targetPosition, targetParentId, userId });

      return updatedItem;
    } catch (error) {
      Logger.error('Move item failed', error as Error);
      throw error;
    }
  }

  /**
   * Add item assignment
   */
  static async addAssignment(
    itemId: string,
    userId: string,
    assigneeId: string
  ): Promise<any> {
    try {
      const item = await prisma.item.findUnique({
        where: { id: itemId },
        include: { board: true },
      });

      if (!item) {
        throw new Error('Item not found');
      }

      // Verify board access
      const hasAccess = await this.verifyBoardAccess(item.boardId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      // Check if assignment already exists
      const existingAssignment = await prisma.itemAssignment.findFirst({
        where: { itemId, userId: assigneeId },
      });

      if (existingAssignment) {
        throw new Error('User is already assigned to this item');
      }

      const assignment = await prisma.itemAssignment.create({
        data: {
          itemId,
          userId: assigneeId,
          assignedBy: userId,
        },
        include: {
          user: {
            select: { id: true, firstName: true, lastName: true, avatarUrl: true },
          },
          assignedBy: {
            select: { id: true, firstName: true, lastName: true },
          },
        },
      });

      Logger.api(`Assignment added: ${assigneeId} to item ${itemId}`, { itemId, assigneeId, userId });

      return assignment;
    } catch (error) {
      Logger.error('Add assignment failed', error as Error);
      throw error;
    }
  }

  /**
   * Remove item assignment
   */
  static async removeAssignment(
    itemId: string,
    userId: string,
    assigneeId: string
  ): Promise<void> {
    try {
      const item = await prisma.item.findUnique({
        where: { id: itemId },
        include: { board: true },
      });

      if (!item) {
        throw new Error('Item not found');
      }

      // Verify board access
      const hasAccess = await this.verifyBoardAccess(item.boardId, userId);
      if (!hasAccess) {
        throw new Error('Access denied');
      }

      const assignment = await prisma.itemAssignment.findFirst({
        where: { itemId, userId: assigneeId },
      });

      if (!assignment) {
        throw new Error('Assignment not found');
      }

      await prisma.itemAssignment.delete({
        where: { id: assignment.id },
      });

      Logger.api(`Assignment removed: ${assigneeId} from item ${itemId}`, { itemId, assigneeId, userId });
    } catch (error) {
      Logger.error('Remove assignment failed', error as Error);
      throw error;
    }
  }

  /**
   * Create item dependency
   */
  static async createDependency(
    predecessorId: string,
    successorId: string,
    userId: string,
    dependencyType: string = 'blocks'
  ): Promise<any> {
    try {
      // Verify both items exist and user has access
      const [predecessor, successor] = await Promise.all([
        prisma.item.findUnique({ where: { id: predecessorId }, include: { board: true } }),
        prisma.item.findUnique({ where: { id: successorId }, include: { board: true } }),
      ]);

      if (!predecessor || !successor) {
        throw new Error('One or both items not found');
      }

      // Verify board access for both items
      const [hasAccessPred, hasAccessSucc] = await Promise.all([
        this.verifyBoardAccess(predecessor.boardId, userId),
        this.verifyBoardAccess(successor.boardId, userId),
      ]);

      if (!hasAccessPred || !hasAccessSucc) {
        throw new Error('Access denied');
      }

      // Check if dependency already exists
      const existingDep = await prisma.itemDependency.findFirst({
        where: { predecessorId, successorId },
      });

      if (existingDep) {
        throw new Error('Dependency already exists');
      }

      // Check for circular dependencies
      const wouldCreateCycle = await this.checkCircularDependency(predecessorId, successorId);
      if (wouldCreateCycle) {
        throw new Error('Would create circular dependency');
      }

      const dependency = await prisma.itemDependency.create({
        data: {
          predecessorId,
          successorId,
          dependencyType,
          createdBy: userId,
        },
        include: {
          predecessor: {
            select: { id: true, name: true },
          },
          successor: {
            select: { id: true, name: true },
          },
        },
      });

      Logger.api(`Dependency created: ${predecessorId} -> ${successorId}`, {
        predecessorId,
        successorId,
        userId,
      });

      return dependency;
    } catch (error) {
      Logger.error('Create dependency failed', error as Error);
      throw error;
    }
  }

  // ============================================================================
  // PRIVATE HELPER METHODS
  // ============================================================================

  /**
   * Verify board access for user
   */
  private static async verifyBoardAccess(boardId: string, userId: string): Promise<boolean> {
    try {
      const access = await prisma.board.findFirst({
        where: {
          id: boardId,
          deletedAt: null,
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
                  some: {
                    userId,
                    role: { in: ['admin', 'member'] },
                  },
                },
              },
            },
          ],
        },
      });

      return !!access;
    } catch (error) {
      return false;
    }
  }

  /**
   * Soft delete item and all its children recursively
   */
  private static async softDeleteItemTree(itemId: string): Promise<void> {
    // Get all children
    const children = await prisma.item.findMany({
      where: { parentId: itemId, deletedAt: null },
      select: { id: true },
    });

    // Recursively delete children
    for (const child of children) {
      await this.softDeleteItemTree(child.id);
    }

    // Delete the item itself
    await prisma.item.update({
      where: { id: itemId },
      data: { deletedAt: new Date() },
    });
  }

  /**
   * Add multiple assignments to an item
   */
  private static async addAssignments(
    itemId: string,
    assignedBy: string,
    assigneeIds: string[]
  ): Promise<void> {
    for (const assigneeId of assigneeIds) {
      try {
        await prisma.itemAssignment.create({
          data: {
            itemId,
            userId: assigneeId,
            assignedBy,
          },
        });
      } catch (error) {
        // Continue with other assignments if one fails
        Logger.error(`Failed to add assignment for user ${assigneeId}`, error as Error);
      }
    }
  }

  /**
   * Update item assignments
   */
  private static async updateAssignments(
    itemId: string,
    assignedBy: string,
    assigneeIds: string[]
  ): Promise<void> {
    // Remove existing assignments
    await prisma.itemAssignment.deleteMany({
      where: { itemId },
    });

    // Add new assignments
    await this.addAssignments(itemId, assignedBy, assigneeIds);
  }

  /**
   * Check if creating a dependency would create a circular reference
   */
  private static async checkCircularDependency(
    predecessorId: string,
    successorId: string
  ): Promise<boolean> {
    // Simple check: see if successor is already a predecessor of predecessor (directly or indirectly)
    const visited = new Set<string>();
    const queue = [successorId];

    while (queue.length > 0) {
      const currentId = queue.shift()!;

      if (visited.has(currentId)) {
        continue;
      }

      if (currentId === predecessorId) {
        return true; // Would create a cycle
      }

      visited.add(currentId);

      // Get all items that depend on the current item
      const dependencies = await prisma.itemDependency.findMany({
        where: { successorId: currentId },
        select: { predecessorId: true },
      });

      for (const dep of dependencies) {
        if (!visited.has(dep.predecessorId)) {
          queue.push(dep.predecessorId);
        }
      }
    }

    return false;
  }
}