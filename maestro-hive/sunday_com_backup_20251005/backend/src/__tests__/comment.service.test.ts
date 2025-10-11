import { prismaMock } from './setup';
import { CommentService } from '@/services/comment.service';
import { RedisService } from '@/config/redis';

// Mock Redis
jest.mock('@/config/redis', () => ({
  RedisService: {
    getCache: jest.fn(),
    setCache: jest.fn(),
    deleteCache: jest.fn(),
    deleteCachePattern: jest.fn(),
  },
}));

// Mock Socket.io
jest.mock('@/server', () => ({
  io: {
    to: jest.fn(() => ({
      emit: jest.fn(),
    })),
  },
}));

// Mock ItemService to avoid circular dependency
jest.mock('@/services/item.service', () => ({
  ItemService: {
    getById: jest.fn(),
  },
}));

describe('CommentService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('create', () => {
    it('should create comment successfully', async () => {
      const mockComment = {
        id: 'comment-1',
        content: 'This is a test comment',
        itemId: 'item-1',
        userId: 'user-1',
        parentId: null,
        attachments: [],
        createdAt: new Date(),
        updatedAt: new Date(),
        editedAt: null,
        deletedAt: null,
        user: {
          id: 'user-1',
          firstName: 'John',
          lastName: 'Doe',
          avatarUrl: 'https://example.com/avatar.jpg',
        },
        mentions: [],
        _count: {
          replies: 0,
          reactions: 0,
        },
      };

      const mockItem = {
        id: 'item-1',
        boardId: 'board-1',
      };

      // Mock ItemService access check
      const { ItemService } = require('@/services/item.service');
      ItemService.getById.mockResolvedValue({ id: 'item-1' });

      prismaMock.comment.create.mockResolvedValue(mockComment as any);
      prismaMock.item.findUnique.mockResolvedValue(mockItem as any);

      const commentData = {
        content: 'This is a test comment',
        parentId: null,
        mentions: ['user-2'],
        attachments: [],
      };

      const result = await CommentService.create('item-1', commentData, 'user-1');

      expect(result).toEqual(mockComment);
      expect(prismaMock.comment.create).toHaveBeenCalledWith({
        data: {
          content: commentData.content,
          itemId: 'item-1',
          userId: 'user-1',
          parentId: null,
          attachments: [],
          mentions: {
            create: [{ userId: 'user-2' }],
          },
        },
        include: expect.any(Object),
      });
    });

    it('should throw error when user has no access to item', async () => {
      const { ItemService } = require('@/services/item.service');
      ItemService.getById.mockResolvedValue(null);

      const commentData = {
        content: 'Test comment',
      };

      await expect(
        CommentService.create('item-1', commentData, 'user-1')
      ).rejects.toThrow('Access denied to item');
    });

    it('should send mention notifications', async () => {
      const mockComment = {
        id: 'comment-1',
        content: 'Test comment with mention',
        itemId: 'item-1',
        userId: 'user-1',
        user: { firstName: 'John', lastName: 'Doe' },
        item: {
          name: 'Test Item',
          board: { name: 'Test Board' },
        },
      };

      const { ItemService } = require('@/services/item.service');
      ItemService.getById.mockResolvedValue({ id: 'item-1' });

      prismaMock.comment.create.mockResolvedValue(mockComment as any);
      prismaMock.item.findUnique.mockResolvedValue({ boardId: 'board-1' } as any);
      prismaMock.comment.findUnique.mockResolvedValue(mockComment as any);
      prismaMock.notification.createMany.mockResolvedValue({ count: 1 } as any);

      const commentData = {
        content: 'Test comment with mention',
        mentions: ['user-2'],
      };

      await CommentService.create('item-1', commentData, 'user-1');

      expect(prismaMock.notification.createMany).toHaveBeenCalledWith({
        data: [
          {
            userId: 'user-2',
            type: 'mention',
            title: 'You were mentioned in a comment',
            message: expect.stringContaining('John Doe mentioned you'),
            data: expect.any(Object),
          },
        ],
      });
    });
  });

  describe('getById', () => {
    it('should get comment by ID successfully', async () => {
      const mockComment = {
        id: 'comment-1',
        content: 'Test comment',
        itemId: 'item-1',
        userId: 'user-1',
        user: {
          id: 'user-1',
          firstName: 'John',
          lastName: 'Doe',
          avatarUrl: null,
        },
        _count: {
          replies: 2,
          reactions: 1,
        },
      };

      prismaMock.comment.findFirst.mockResolvedValue(mockComment as any);

      const result = await CommentService.getById('comment-1', 'user-1');

      expect(result).toEqual(mockComment);
      expect(prismaMock.comment.findFirst).toHaveBeenCalledWith({
        where: {
          id: 'comment-1',
          deletedAt: null,
          item: {
            board: {
              OR: expect.any(Array),
            },
          },
        },
        include: expect.any(Object),
      });
    });

    it('should return null when comment not found', async () => {
      prismaMock.comment.findFirst.mockResolvedValue(null);

      const result = await CommentService.getById('nonexistent-comment', 'user-1');

      expect(result).toBeNull();
    });
  });

  describe('getByItem', () => {
    it('should get comments for an item successfully', async () => {
      const mockComments = [
        {
          id: 'comment-1',
          content: 'First comment',
          itemId: 'item-1',
          userId: 'user-1',
          parentId: null,
          user: { id: 'user-1', firstName: 'John', lastName: 'Doe' },
          replies: [
            {
              id: 'comment-2',
              content: 'Reply to first comment',
              user: { id: 'user-2', firstName: 'Jane', lastName: 'Smith' },
            },
          ],
          _count: { replies: 1, reactions: 0 },
        },
      ];

      const { ItemService } = require('@/services/item.service');
      ItemService.getById.mockResolvedValue({ id: 'item-1' });

      prismaMock.comment.findMany.mockResolvedValue(mockComments as any);
      prismaMock.comment.count.mockResolvedValue(1);

      const result = await CommentService.getByItem('item-1', 'user-1');

      expect(result.data).toEqual(mockComments);
      expect(result.meta).toMatchObject({
        page: 1,
        limit: 20,
        total: 1,
        totalPages: 1,
        hasNext: false,
        hasPrev: false,
      });
    });

    it('should throw error when user has no access to item', async () => {
      const { ItemService } = require('@/services/item.service');
      ItemService.getById.mockResolvedValue(null);

      await expect(
        CommentService.getByItem('item-1', 'user-1')
      ).rejects.toThrow('Access denied to item');
    });
  });

  describe('update', () => {
    it('should update comment successfully', async () => {
      const mockExistingComment = {
        userId: 'user-1',
        itemId: 'item-1',
      };

      const mockUpdatedComment = {
        id: 'comment-1',
        content: 'Updated comment content',
        editedAt: new Date(),
        user: { id: 'user-1', firstName: 'John', lastName: 'Doe' },
        _count: { replies: 0, reactions: 0 },
      };

      prismaMock.comment.findUnique.mockResolvedValue(mockExistingComment as any);
      prismaMock.comment.update.mockResolvedValue(mockUpdatedComment as any);
      prismaMock.item.findUnique.mockResolvedValue({ boardId: 'board-1' } as any);

      const result = await CommentService.update('comment-1', 'Updated comment content', 'user-1');

      expect(result).toEqual(mockUpdatedComment);
      expect(prismaMock.comment.update).toHaveBeenCalledWith({
        where: { id: 'comment-1' },
        data: {
          content: 'Updated comment content',
          editedAt: expect.any(Date),
        },
        include: expect.any(Object),
      });
    });

    it('should throw error when comment not found', async () => {
      prismaMock.comment.findUnique.mockResolvedValue(null);

      await expect(
        CommentService.update('nonexistent-comment', 'New content', 'user-1')
      ).rejects.toThrow('Comment not found');
    });

    it('should throw error when user is not comment owner', async () => {
      const mockExistingComment = {
        userId: 'user-2', // Different user
        itemId: 'item-1',
      };

      prismaMock.comment.findUnique.mockResolvedValue(mockExistingComment as any);

      await expect(
        CommentService.update('comment-1', 'New content', 'user-1')
      ).rejects.toThrow('Access denied - you can only edit your own comments');
    });
  });

  describe('delete', () => {
    it('should delete comment successfully when user is owner', async () => {
      const mockComment = {
        userId: 'user-1',
        itemId: 'item-1',
        item: {
          board: {
            id: 'board-1',
            members: [], // No admin members
          },
        },
      };

      prismaMock.comment.findUnique.mockResolvedValue(mockComment as any);
      prismaMock.comment.update.mockResolvedValue({} as any);

      await CommentService.delete('comment-1', 'user-1');

      expect(prismaMock.comment.update).toHaveBeenCalledWith({
        where: { id: 'comment-1' },
        data: { deletedAt: expect.any(Date) },
      });
    });

    it('should delete comment successfully when user is board admin', async () => {
      const mockComment = {
        userId: 'user-2', // Different user
        itemId: 'item-1',
        item: {
          board: {
            id: 'board-1',
            members: [{ userId: 'user-1', role: 'admin' }], // User is admin
          },
        },
      };

      prismaMock.comment.findUnique.mockResolvedValue(mockComment as any);
      prismaMock.comment.update.mockResolvedValue({} as any);

      await CommentService.delete('comment-1', 'user-1');

      expect(prismaMock.comment.update).toHaveBeenCalledWith({
        where: { id: 'comment-1' },
        data: { deletedAt: expect.any(Date) },
      });
    });

    it('should throw error when user has no permission to delete', async () => {
      const mockComment = {
        userId: 'user-2', // Different user
        itemId: 'item-1',
        item: {
          board: {
            id: 'board-1',
            members: [], // No admin members
          },
        },
      };

      prismaMock.comment.findUnique.mockResolvedValue(mockComment as any);

      await expect(
        CommentService.delete('comment-1', 'user-1')
      ).rejects.toThrow('Access denied - you can only delete your own comments or be a board admin');
    });
  });

  describe('addReaction', () => {
    it('should add reaction successfully', async () => {
      const mockComment = {
        id: 'comment-1',
        itemId: 'item-1',
      };

      prismaMock.comment.findFirst.mockResolvedValue(mockComment as any);
      prismaMock.commentReaction.findUnique.mockResolvedValue(null);
      prismaMock.commentReaction.create.mockResolvedValue({} as any);
      prismaMock.commentReaction.groupBy.mockResolvedValue([
        { emoji: '👍', _count: { emoji: 1 } },
      ]);
      prismaMock.item.findUnique.mockResolvedValue({ boardId: 'board-1' } as any);

      await CommentService.addReaction('comment-1', '👍', 'user-1');

      expect(prismaMock.commentReaction.create).toHaveBeenCalledWith({
        data: {
          commentId: 'comment-1',
          userId: 'user-1',
          emoji: '👍',
        },
      });
    });

    it('should throw error when reaction already exists', async () => {
      const mockComment = {
        id: 'comment-1',
        itemId: 'item-1',
      };

      const mockExistingReaction = {
        commentId: 'comment-1',
        userId: 'user-1',
        emoji: '👍',
      };

      prismaMock.comment.findFirst.mockResolvedValue(mockComment as any);
      prismaMock.commentReaction.findUnique.mockResolvedValue(mockExistingReaction as any);

      await expect(
        CommentService.addReaction('comment-1', '👍', 'user-1')
      ).rejects.toThrow('Reaction already exists');
    });
  });

  describe('removeReaction', () => {
    it('should remove reaction successfully', async () => {
      const mockReaction = {
        commentId: 'comment-1',
        userId: 'user-1',
        emoji: '👍',
        comment: {
          itemId: 'item-1',
          item: {
            boardId: 'board-1',
          },
        },
      };

      prismaMock.commentReaction.findUnique.mockResolvedValue(mockReaction as any);
      prismaMock.commentReaction.delete.mockResolvedValue({} as any);
      prismaMock.commentReaction.groupBy.mockResolvedValue([]);

      await CommentService.removeReaction('comment-1', '👍', 'user-1');

      expect(prismaMock.commentReaction.delete).toHaveBeenCalledWith({
        where: {
          commentId_userId_emoji: {
            commentId: 'comment-1',
            userId: 'user-1',
            emoji: '👍',
          },
        },
      });
    });

    it('should throw error when reaction not found', async () => {
      prismaMock.commentReaction.findUnique.mockResolvedValue(null);

      await expect(
        CommentService.removeReaction('comment-1', '👍', 'user-1')
      ).rejects.toThrow('Reaction not found');
    });
  });

  describe('getItemCommentStats', () => {
    it('should get comment statistics for an item', async () => {
      const mockStats = [
        {
          totalComments: BigInt(5),
          rootComments: BigInt(3),
          replies: BigInt(2),
          recentActivity: new Date(),
        },
      ];

      const mockContributors = [
        {
          userId: 'user-1',
          firstName: 'John',
          lastName: 'Doe',
          avatarUrl: null,
          commentCount: BigInt(3),
        },
      ];

      prismaMock.$queryRaw.mockResolvedValueOnce(mockStats).mockResolvedValueOnce(mockContributors);

      const result = await CommentService.getItemCommentStats('item-1');

      expect(result).toMatchObject({
        totalComments: 5,
        rootComments: 3,
        replies: 2,
        recentActivity: expect.any(Date),
        topContributors: [
          {
            user: {
              id: 'user-1',
              firstName: 'John',
              lastName: 'Doe',
              avatarUrl: null,
            },
            commentCount: 3,
          },
        ],
      });
    });
  });
});