import { prisma } from '@/config/database';
import { RedisService } from '@/config/redis';
import { Logger } from '@/config/logger';
import { io } from '@/server';
import { CreateCommentData, PaginatedResult, PaginationMeta } from '@/types';
import { Comment, User, Prisma } from '@prisma/client';

type CommentWithRelations = Comment & {
  user: Pick<User, 'id' | 'firstName' | 'lastName' | 'avatarUrl'>;
  parent?: Comment;
  replies?: Comment[];
  mentions?: Array<{ user: Pick<User, 'id' | 'firstName' | 'lastName' | 'avatarUrl'> }>;
  reactions?: Array<{
    emoji: string;
    count: number;
    users: Array<Pick<User, 'id' | 'firstName' | 'lastName'>>;
  }>;
  _count?: {
    replies: number;
    reactions: number;
  };
};

export class CommentService {
  /**
   * Create a new comment
   */
  static async create(
    itemId: string,
    data: CreateCommentData,
    userId: string
  ): Promise<CommentWithRelations> {
    try {
      // Check if user has access to the item
      const hasAccess = await this.checkItemAccess(itemId, userId);
      if (!hasAccess) {
        throw new Error('Access denied to item');
      }

      // Create comment with mentions
      const comment = await prisma.comment.create({
        data: {
          content: data.content,
          itemId,
          userId,
          parentId: data.parentId,
          attachments: data.attachments || [],
          mentions: data.mentions
            ? {
                create: data.mentions.map(mentionedUserId => ({
                  userId: mentionedUserId,
                })),
              }
            : undefined,
        },
        include: {
          user: {
            select: {
              id: true,
              firstName: true,
              lastName: true,
              avatarUrl: true,
            },
          },
          parent: true,
          mentions: {
            include: {
              user: {
                select: {
                  id: true,
                  firstName: true,
                  lastName: true,
                  avatarUrl: true,
                },
              },
            },
          },
          _count: {
            select: {
              replies: true,
              reactions: true,
            },
          },
        },
      });

      // Get item's board for real-time broadcasting
      const item = await prisma.item.findUnique({
        where: { id: itemId },
        select: { boardId: true },
      });

      // Emit real-time event
      if (item) {
        io.to(`board:${item.boardId}`).emit('comment_created', {
          comment: {
            id: comment.id,
            content: comment.content,
            itemId: comment.itemId,
            userId: comment.userId,
            parentId: comment.parentId,
            createdAt: comment.createdAt,
            user: comment.user,
          },
        });

        // Emit to item-specific room if anyone is watching
        io.to(`item:${itemId}`).emit('comment_created', {
          comment: {
            id: comment.id,
            content: comment.content,
            itemId: comment.itemId,
            userId: comment.userId,
            parentId: comment.parentId,
            createdAt: comment.createdAt,
            user: comment.user,
          },
        });
      }

      // Send notifications to mentioned users
      if (data.mentions?.length) {
        await this.sendMentionNotifications(comment.id, data.mentions, userId, itemId);
      }

      // Invalidate cache
      await this.invalidateCommentCaches(itemId);

      Logger.business(`Comment created on item ${itemId}`, {
        commentId: comment.id,
        userId,
        itemId,
        hasParent: !!data.parentId,
        mentionCount: data.mentions?.length || 0,
      });

      return comment as CommentWithRelations;
    } catch (error) {
      Logger.error('Comment creation failed', error as Error);
      throw error;
    }
  }

  /**
   * Get comment by ID
   */
  static async getById(
    commentId: string,
    userId: string,
    includeReplies = false
  ): Promise<CommentWithRelations | null> {
    try {
      const comment = await prisma.comment.findFirst({
        where: {
          id: commentId,
          deletedAt: null,
          item: {
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
        },
        include: {
          user: {
            select: {
              id: true,
              firstName: true,
              lastName: true,
              avatarUrl: true,
            },
          },
          parent: true,
          replies: includeReplies
            ? {
                where: { deletedAt: null },
                include: {
                  user: {
                    select: {
                      id: true,
                      firstName: true,
                      lastName: true,
                      avatarUrl: true,
                    },
                  },
                },
                orderBy: { createdAt: 'asc' },
              }
            : false,
          mentions: {
            include: {
              user: {
                select: {
                  id: true,
                  firstName: true,
                  lastName: true,
                  avatarUrl: true,
                },
              },
            },
          },
          _count: {
            select: {
              replies: {
                where: { deletedAt: null },
              },
              reactions: true,
            },
          },
        },
      });

      return comment as CommentWithRelations;
    } catch (error) {
      Logger.error('Failed to get comment', error as Error);
      throw error;
    }
  }

  /**
   * Get comments for an item
   */
  static async getByItem(
    itemId: string,
    userId: string,
    page = 1,
    limit = 20,
    includeReplies = true
  ): Promise<PaginatedResult<CommentWithRelations>> {
    try {
      // Check access
      const hasAccess = await this.checkItemAccess(itemId, userId);
      if (!hasAccess) {
        throw new Error('Access denied to item');
      }

      const offset = (page - 1) * limit;

      // Get root comments (comments without parent)
      const [comments, total] = await Promise.all([
        prisma.comment.findMany({
          where: {
            itemId,
            parentId: null,
            deletedAt: null,
          },
          include: {
            user: {
              select: {
                id: true,
                firstName: true,
                lastName: true,
                avatarUrl: true,
              },
            },
            replies: includeReplies
              ? {
                  where: { deletedAt: null },
                  include: {
                    user: {
                      select: {
                        id: true,
                        firstName: true,
                        lastName: true,
                        avatarUrl: true,
                      },
                    },
                    _count: {
                      select: {
                        reactions: true,
                      },
                    },
                  },
                  orderBy: { createdAt: 'asc' },
                }
              : false,
            mentions: {
              include: {
                user: {
                  select: {
                    id: true,
                    firstName: true,
                    lastName: true,
                    avatarUrl: true,
                  },
                },
              },
            },
            _count: {
              select: {
                replies: {
                  where: { deletedAt: null },
                },
                reactions: true,
              },
            },
          },
          orderBy: { createdAt: 'desc' },
          skip: offset,
          take: limit,
        }),
        prisma.comment.count({
          where: {
            itemId,
            parentId: null,
            deletedAt: null,
          },
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

      return {
        data: comments as CommentWithRelations[],
        meta,
      };
    } catch (error) {
      Logger.error('Failed to get item comments', error as Error);
      throw error;
    }
  }

  /**
   * Update comment
   */
  static async update(
    commentId: string,
    content: string,
    userId: string
  ): Promise<CommentWithRelations> {
    try {
      // Check if user owns the comment
      const existingComment = await prisma.comment.findUnique({
        where: { id: commentId },
        select: { userId: true, itemId: true },
      });

      if (!existingComment) {
        throw new Error('Comment not found');
      }

      if (existingComment.userId !== userId) {
        throw new Error('Access denied - you can only edit your own comments');
      }

      const comment = await prisma.comment.update({
        where: { id: commentId },
        data: {
          content,
          editedAt: new Date(),
        },
        include: {
          user: {
            select: {
              id: true,
              firstName: true,
              lastName: true,
              avatarUrl: true,
            },
          },
          parent: true,
          _count: {
            select: {
              replies: {
                where: { deletedAt: null },
              },
              reactions: true,
            },
          },
        },
      });

      // Get item's board for real-time broadcasting
      const item = await prisma.item.findUnique({
        where: { id: existingComment.itemId },
        select: { boardId: true },
      });

      // Emit real-time event
      if (item) {
        io.to(`board:${item.boardId}`).emit('comment_updated', {
          commentId,
          content,
          editedAt: comment.editedAt,
          updatedBy: userId,
        });

        io.to(`item:${existingComment.itemId}`).emit('comment_updated', {
          commentId,
          content,
          editedAt: comment.editedAt,
          updatedBy: userId,
        });
      }

      // Invalidate cache
      await this.invalidateCommentCaches(existingComment.itemId);

      Logger.business(`Comment updated`, {
        commentId,
        itemId: existingComment.itemId,
        userId,
      });

      return comment as CommentWithRelations;
    } catch (error) {
      Logger.error('Comment update failed', error as Error);
      throw error;
    }
  }

  /**
   * Delete comment (soft delete)
   */
  static async delete(commentId: string, userId: string): Promise<void> {
    try {
      // Check if user owns the comment or has admin access
      const comment = await prisma.comment.findUnique({
        where: { id: commentId },
        select: {
          userId: true,
          itemId: true,
          item: {
            select: {
              board: {
                select: {
                  id: true,
                  members: {
                    where: { userId, role: 'admin' },
                  },
                },
              },
            },
          },
        },
      });

      if (!comment) {
        throw new Error('Comment not found');
      }

      const isOwner = comment.userId === userId;
      const isBoardAdmin = comment.item.board.members.length > 0;

      if (!isOwner && !isBoardAdmin) {
        throw new Error('Access denied - you can only delete your own comments or be a board admin');
      }

      await prisma.comment.update({
        where: { id: commentId },
        data: { deletedAt: new Date() },
      });

      // Emit real-time event
      io.to(`board:${comment.item.board.id}`).emit('comment_deleted', {
        commentId,
        itemId: comment.itemId,
        deletedBy: userId,
      });

      io.to(`item:${comment.itemId}`).emit('comment_deleted', {
        commentId,
        itemId: comment.itemId,
        deletedBy: userId,
      });

      // Invalidate cache
      await this.invalidateCommentCaches(comment.itemId);

      Logger.business(`Comment deleted`, {
        commentId,
        itemId: comment.itemId,
        deletedBy: userId,
        isOwner,
        isBoardAdmin,
      });
    } catch (error) {
      Logger.error('Comment deletion failed', error as Error);
      throw error;
    }
  }

  /**
   * Add reaction to comment
   */
  static async addReaction(
    commentId: string,
    emoji: string,
    userId: string
  ): Promise<void> {
    try {
      // Check if user has access to the comment
      const comment = await prisma.comment.findFirst({
        where: {
          id: commentId,
          deletedAt: null,
          item: {
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
        },
        select: { id: true, itemId: true },
      });

      if (!comment) {
        throw new Error('Comment not found or access denied');
      }

      // Check if reaction already exists
      const existingReaction = await prisma.commentReaction.findUnique({
        where: {
          commentId_userId_emoji: {
            commentId,
            userId,
            emoji,
          },
        },
      });

      if (existingReaction) {
        throw new Error('Reaction already exists');
      }

      await prisma.commentReaction.create({
        data: {
          commentId,
          userId,
          emoji,
        },
      });

      // Get updated reaction counts
      const reactions = await this.getCommentReactions(commentId);

      // Emit real-time event
      const item = await prisma.item.findUnique({
        where: { id: comment.itemId },
        select: { boardId: true },
      });

      if (item) {
        io.to(`board:${item.boardId}`).emit('comment_reaction_added', {
          commentId,
          emoji,
          userId,
          reactions,
        });

        io.to(`item:${comment.itemId}`).emit('comment_reaction_added', {
          commentId,
          emoji,
          userId,
          reactions,
        });
      }

      Logger.business(`Reaction added to comment`, {
        commentId,
        emoji,
        userId,
      });
    } catch (error) {
      Logger.error('Add reaction failed', error as Error);
      throw error;
    }
  }

  /**
   * Remove reaction from comment
   */
  static async removeReaction(
    commentId: string,
    emoji: string,
    userId: string
  ): Promise<void> {
    try {
      const reaction = await prisma.commentReaction.findUnique({
        where: {
          commentId_userId_emoji: {
            commentId,
            userId,
            emoji,
          },
        },
        include: {
          comment: {
            select: {
              itemId: true,
              item: {
                select: { boardId: true },
              },
            },
          },
        },
      });

      if (!reaction) {
        throw new Error('Reaction not found');
      }

      await prisma.commentReaction.delete({
        where: {
          commentId_userId_emoji: {
            commentId,
            userId,
            emoji,
          },
        },
      });

      // Get updated reaction counts
      const reactions = await this.getCommentReactions(commentId);

      // Emit real-time event
      io.to(`board:${reaction.comment.item.boardId}`).emit('comment_reaction_removed', {
        commentId,
        emoji,
        userId,
        reactions,
      });

      io.to(`item:${reaction.comment.itemId}`).emit('comment_reaction_removed', {
        commentId,
        emoji,
        userId,
        reactions,
      });

      Logger.business(`Reaction removed from comment`, {
        commentId,
        emoji,
        userId,
      });
    } catch (error) {
      Logger.error('Remove reaction failed', error as Error);
      throw error;
    }
  }

  /**
   * Get comment statistics for an item
   */
  static async getItemCommentStats(itemId: string): Promise<{
    totalComments: number;
    rootComments: number;
    replies: number;
    recentActivity: Date | null;
    topContributors: Array<{
      user: Pick<User, 'id' | 'firstName' | 'lastName' | 'avatarUrl'>;
      commentCount: number;
    }>;
  }> {
    try {
      const [stats] = await prisma.$queryRaw<Array<{
        totalComments: bigint;
        rootComments: bigint;
        replies: bigint;
        recentActivity: Date | null;
      }>>`
        SELECT
          COUNT(*) as totalComments,
          COUNT(CASE WHEN parent_id IS NULL THEN 1 END) as rootComments,
          COUNT(CASE WHEN parent_id IS NOT NULL THEN 1 END) as replies,
          MAX(created_at) as recentActivity
        FROM comments
        WHERE item_id = ${itemId}
        AND deleted_at IS NULL
      `;

      const topContributors = await prisma.$queryRaw<Array<{
        userId: string;
        firstName: string;
        lastName: string;
        avatarUrl: string | null;
        commentCount: bigint;
      }>>`
        SELECT
          u.id as userId,
          u.first_name as firstName,
          u.last_name as lastName,
          u.avatar_url as avatarUrl,
          COUNT(c.id) as commentCount
        FROM users u
        JOIN comments c ON u.id = c.user_id
        WHERE c.item_id = ${itemId}
        AND c.deleted_at IS NULL
        GROUP BY u.id, u.first_name, u.last_name, u.avatar_url
        ORDER BY commentCount DESC
        LIMIT 5
      `;

      return {
        totalComments: Number(stats.totalComments),
        rootComments: Number(stats.rootComments),
        replies: Number(stats.replies),
        recentActivity: stats.recentActivity,
        topContributors: topContributors.map(contributor => ({
          user: {
            id: contributor.userId,
            firstName: contributor.firstName,
            lastName: contributor.lastName,
            avatarUrl: contributor.avatarUrl,
          },
          commentCount: Number(contributor.commentCount),
        })),
      };
    } catch (error) {
      Logger.error('Failed to get comment statistics', error as Error);
      throw error;
    }
  }

  // ============================================================================
  // PRIVATE METHODS
  // ============================================================================

  /**
   * Check if user has access to an item
   */
  private static async checkItemAccess(itemId: string, userId: string): Promise<boolean> {
    try {
      // Import ItemService to avoid circular dependency
      const { ItemService } = await import('./item.service');
      const item = await ItemService.getById(itemId, userId);
      return !!item;
    } catch (error) {
      Logger.error('Failed to check item access', error as Error);
      return false;
    }
  }

  /**
   * Get reaction counts for a comment
   */
  private static async getCommentReactions(commentId: string) {
    const reactions = await prisma.commentReaction.groupBy({
      by: ['emoji'],
      where: { commentId },
      _count: { emoji: true },
    });

    return reactions.map(reaction => ({
      emoji: reaction.emoji,
      count: reaction._count.emoji,
    }));
  }

  /**
   * Send notifications to mentioned users
   */
  private static async sendMentionNotifications(
    commentId: string,
    mentionedUserIds: string[],
    mentionedBy: string,
    itemId: string
  ): Promise<void> {
    try {
      // Get comment and item details
      const comment = await prisma.comment.findUnique({
        where: { id: commentId },
        select: {
          content: true,
          user: {
            select: { firstName: true, lastName: true },
          },
          item: {
            select: {
              name: true,
              board: {
                select: { name: true },
              },
            },
          },
        },
      });

      if (!comment) return;

      // Create notifications for mentioned users
      const notifications = mentionedUserIds
        .filter(userId => userId !== mentionedBy) // Don't notify the person who made the comment
        .map(userId => ({
          userId,
          type: 'mention',
          title: 'You were mentioned in a comment',
          message: `${comment.user.firstName} ${comment.user.lastName} mentioned you in a comment on "${comment.item.name}"`,
          data: {
            commentId,
            itemId,
            boardName: comment.item.board.name,
            itemName: comment.item.name,
            commentContent: comment.content.substring(0, 100),
          },
        }));

      if (notifications.length > 0) {
        await prisma.notification.createMany({
          data: notifications,
        });

        // Send real-time notifications
        notifications.forEach(notification => {
          io.to(`user:${notification.userId}`).emit('notification', {
            ...notification,
            createdAt: new Date(),
          });
        });
      }
    } catch (error) {
      Logger.error('Failed to send mention notifications', error as Error);
      // Don't throw error for notification failures
    }
  }

  /**
   * Invalidate comment-related caches
   */
  private static async invalidateCommentCaches(itemId: string): Promise<void> {
    await Promise.all([
      RedisService.deleteCachePattern(`comments:item:${itemId}:*`),
      RedisService.deleteCachePattern(`item:${itemId}:*`),
    ]);
  }
}