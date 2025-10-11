import { BoardService } from '../../src/services/board.service';
import {
  TestDataFactory,
  DatabaseHelper,
  MockHelper,
  TestAssertions,
  testPrisma,
} from '../utils/test-helpers';

// Mock external dependencies
const mockRedis = MockHelper.mockRedisService();
const mockIO = MockHelper.mockSocketIO();

describe('BoardService', () => {
  let testUser: any;
  let testOrganization: any;
  let testWorkspace: any;

  beforeAll(async () => {
    await DatabaseHelper.cleanDatabase();
  });

  beforeEach(async () => {
    // Reset mocks
    jest.clearAllMocks();

    // Create test data
    testUser = await TestDataFactory.createUser();
    testOrganization = await TestDataFactory.createOrganization();
    testWorkspace = await TestDataFactory.createWorkspace(testOrganization.id);

    // Create memberships
    await TestDataFactory.createOrganizationMember(testOrganization.id, testUser.id, 'admin');
    await TestDataFactory.createWorkspaceMember(testWorkspace.id, testUser.id, 'admin');
  });

  afterEach(async () => {
    await DatabaseHelper.cleanDatabase();
  });

  afterAll(async () => {
    await testPrisma.$disconnect();
  });

  describe('create', () => {
    it('should create a board successfully', async () => {
      const boardData = {
        name: 'Test Board',
        description: 'Test board description',
        workspaceId: testWorkspace.id,
        isPrivate: false,
        settings: { theme: 'light' },
        columns: [
          { name: 'To Do', color: '#FF0000' },
          { name: 'In Progress', color: '#FFFF00' },
          { name: 'Done', color: '#00FF00' },
        ],
      };

      const board = await BoardService.create(boardData, testUser.id);

      TestAssertions.expectBoardObject(board);
      expect(board.name).toBe(boardData.name);
      expect(board.description).toBe(boardData.description);
      expect(board.workspaceId).toBe(testWorkspace.id);
      expect(board.createdBy).toBe(testUser.id);
      expect(board.columns).toHaveLength(3);
      expect(board.members).toHaveLength(1);
      expect(board.members[0].userId).toBe(testUser.id);
      expect(board.members[0].role).toBe('admin');

      // Verify WebSocket emission
      expect(mockIO.to).toHaveBeenCalledWith(`workspace:${testWorkspace.id}`);
      expect(mockIO.emit).toHaveBeenCalledWith('board_created', expect.any(Object));
    });

    it('should create board without columns', async () => {
      const boardData = {
        name: 'Simple Board',
        workspaceId: testWorkspace.id,
      };

      const board = await BoardService.create(boardData, testUser.id);

      expect(board.columns).toHaveLength(0);
    });

    it('should throw error for non-existent workspace', async () => {
      const boardData = {
        name: 'Test Board',
        workspaceId: 'non-existent-id',
      };

      await expect(BoardService.create(boardData, testUser.id)).rejects.toThrow('Workspace not found');
    });

    it('should throw error for private workspace without access', async () => {
      // Create private workspace without user membership
      const privateWorkspace = await TestDataFactory.createWorkspace(testOrganization.id, {
        isPrivate: true,
      });

      const boardData = {
        name: 'Test Board',
        workspaceId: privateWorkspace.id,
      };

      await expect(BoardService.create(boardData, testUser.id)).rejects.toThrow('Access denied to private workspace');
    });

    it('should set correct column positions', async () => {
      const boardData = {
        name: 'Test Board',
        workspaceId: testWorkspace.id,
        columns: [
          { name: 'First' },
          { name: 'Second' },
          { name: 'Third' },
        ],
      };

      const board = await BoardService.create(boardData, testUser.id);

      expect(board.columns[0].position).toBe(0);
      expect(board.columns[1].position).toBe(1);
      expect(board.columns[2].position).toBe(2);
    });
  });

  describe('getById', () => {
    let testBoard: any;

    beforeEach(async () => {
      testBoard = await TestDataFactory.createBoard(testWorkspace.id, testUser.id);
      await TestDataFactory.createBoardMember(testBoard.id, testUser.id, 'admin');
    });

    it('should retrieve board with basic information', async () => {
      const board = await BoardService.getById(testBoard.id, testUser.id);

      TestAssertions.expectBoardObject(board);
      expect(board.id).toBe(testBoard.id);
    });

    it('should include columns when requested', async () => {
      await TestDataFactory.createBoardColumns(testBoard.id, 3);

      const board = await BoardService.getById(testBoard.id, testUser.id, true);

      expect(board.columns).toHaveLength(3);
      expect(board.columns[0].position).toBe(0);
    });

    it('should include items when requested', async () => {
      const item1 = await TestDataFactory.createItem(testBoard.id, testUser.id);
      const item2 = await TestDataFactory.createItem(testBoard.id, testUser.id);

      const board = await BoardService.getById(testBoard.id, testUser.id, false, true);

      expect(board.items).toHaveLength(2);
    });

    it('should include members when requested', async () => {
      const board = await BoardService.getById(testBoard.id, testUser.id, false, false, true);

      expect(board.members).toHaveLength(1);
      expect(board.members[0].userId).toBe(testUser.id);
    });

    it('should use cache on subsequent requests', async () => {
      // Mock cache hit
      mockRedis.getCache.mockResolvedValueOnce(testBoard);

      const board = await BoardService.getById(testBoard.id, testUser.id);

      expect(mockRedis.getCache).toHaveBeenCalled();
      expect(board).toBe(testBoard);
    });

    it('should return null for non-existent board', async () => {
      const board = await BoardService.getById('non-existent-id', testUser.id);
      expect(board).toBeNull();
    });

    it('should return null for board without access', async () => {
      // Create another user without access
      const otherUser = await TestDataFactory.createUser();

      const board = await BoardService.getById(testBoard.id, otherUser.id);
      expect(board).toBeNull();
    });

    it('should allow access to public board through workspace membership', async () => {
      // Create public board
      const publicBoard = await TestDataFactory.createBoard(testWorkspace.id, testUser.id, {
        isPrivate: false,
      });

      const board = await BoardService.getById(publicBoard.id, testUser.id);
      expect(board).not.toBeNull();
    });
  });

  describe('getByWorkspace', () => {
    let boards: any[];

    beforeEach(async () => {
      // Create multiple boards
      boards = await Promise.all([
        TestDataFactory.createBoard(testWorkspace.id, testUser.id, { name: 'Board 1', position: 1 }),
        TestDataFactory.createBoard(testWorkspace.id, testUser.id, { name: 'Board 2', position: 2 }),
        TestDataFactory.createBoard(testWorkspace.id, testUser.id, { name: 'Board 3', position: 0 }),
      ]);

      // Add user as member to all boards
      for (const board of boards) {
        await TestDataFactory.createBoardMember(board.id, testUser.id);
      }
    });

    it('should return boards ordered by position', async () => {
      const result = await BoardService.getByWorkspace(testWorkspace.id, testUser.id);

      expect(result.data).toHaveLength(3);
      expect(result.data[0].position).toBe(0);
      expect(result.data[1].position).toBe(1);
      expect(result.data[2].position).toBe(2);
    });

    it('should support pagination', async () => {
      const result = await BoardService.getByWorkspace(testWorkspace.id, testUser.id, 1, 2);

      expect(result.data).toHaveLength(2);
      expect(result.meta.page).toBe(1);
      expect(result.meta.limit).toBe(2);
      expect(result.meta.total).toBe(3);
      expect(result.meta.totalPages).toBe(2);
      expect(result.meta.hasNext).toBe(true);
      expect(result.meta.hasPrev).toBe(false);
    });

    it('should filter by folder', async () => {
      // Create folder and move one board to it
      const folder = await testPrisma.folder.create({
        data: {
          workspaceId: testWorkspace.id,
          name: 'Test Folder',
        },
      });

      await testPrisma.board.update({
        where: { id: boards[0].id },
        data: { folderId: folder.id },
      });

      const result = await BoardService.getByWorkspace(testWorkspace.id, testUser.id, 1, 20, folder.id);

      expect(result.data).toHaveLength(1);
      expect(result.data[0].id).toBe(boards[0].id);
    });

    it('should only return accessible boards', async () => {
      // Create private board without user membership
      const privateBoard = await TestDataFactory.createBoard(testWorkspace.id, testUser.id, {
        isPrivate: true,
      });

      // Create another user without access
      const otherUser = await TestDataFactory.createUser();
      await TestDataFactory.createOrganizationMember(testOrganization.id, otherUser.id);
      await TestDataFactory.createWorkspaceMember(testWorkspace.id, otherUser.id);

      const result = await BoardService.getByWorkspace(testWorkspace.id, otherUser.id);

      // Should only see public boards (3 from beforeEach)
      expect(result.data).toHaveLength(3);
    });
  });

  describe('update', () => {
    let testBoard: any;

    beforeEach(async () => {
      testBoard = await TestDataFactory.createBoard(testWorkspace.id, testUser.id);
      await TestDataFactory.createBoardMember(testBoard.id, testUser.id, 'admin');
    });

    it('should update board successfully', async () => {
      const updateData = {
        name: 'Updated Board Name',
        description: 'Updated description',
        settings: { theme: 'dark' },
      };

      const updatedBoard = await BoardService.update(testBoard.id, updateData, testUser.id);

      expect(updatedBoard.name).toBe(updateData.name);
      expect(updatedBoard.description).toBe(updateData.description);
      expect(updatedBoard.settings).toEqual(updateData.settings);

      // Verify cache invalidation
      expect(mockRedis.deleteCachePattern).toHaveBeenCalledWith(`board:${testBoard.id}:*`);

      // Verify WebSocket emission
      expect(mockIO.to).toHaveBeenCalledWith(`board:${testBoard.id}`);
      expect(mockIO.emit).toHaveBeenCalledWith('board_updated', expect.any(Object));
    });

    it('should throw error for unauthorized user', async () => {
      const otherUser = await TestDataFactory.createUser();
      const updateData = { name: 'Hacked Board' };

      await expect(BoardService.update(testBoard.id, updateData, otherUser.id)).rejects.toThrow('Access denied');
    });

    it('should allow partial updates', async () => {
      const updateData = { name: 'Only Name Updated' };

      const updatedBoard = await BoardService.update(testBoard.id, updateData, testUser.id);

      expect(updatedBoard.name).toBe(updateData.name);
      expect(updatedBoard.description).toBe(testBoard.description); // Should remain unchanged
    });
  });

  describe('delete', () => {
    let testBoard: any;

    beforeEach(async () => {
      testBoard = await TestDataFactory.createBoard(testWorkspace.id, testUser.id);
      await TestDataFactory.createBoardMember(testBoard.id, testUser.id, 'admin');
    });

    it('should soft delete board successfully', async () => {
      await BoardService.delete(testBoard.id, testUser.id);

      const deletedBoard = await testPrisma.board.findUnique({
        where: { id: testBoard.id },
      });

      expect(deletedBoard.deletedAt).not.toBeNull();

      // Verify cache invalidation
      expect(mockRedis.deleteCachePattern).toHaveBeenCalled();

      // Verify WebSocket emission
      expect(mockIO.to).toHaveBeenCalledWith(`board:${testBoard.id}`);
      expect(mockIO.emit).toHaveBeenCalledWith('board_deleted', expect.any(Object));
    });

    it('should throw error for unauthorized user', async () => {
      const otherUser = await TestDataFactory.createUser();

      await expect(BoardService.delete(testBoard.id, otherUser.id)).rejects.toThrow('Access denied');
    });

    it('should require admin access for deletion', async () => {
      // Create user with non-admin access
      const memberUser = await TestDataFactory.createUser();
      await TestDataFactory.createOrganizationMember(testOrganization.id, memberUser.id);
      await TestDataFactory.createWorkspaceMember(testWorkspace.id, memberUser.id);
      await TestDataFactory.createBoardMember(testBoard.id, memberUser.id, 'member');

      await expect(BoardService.delete(testBoard.id, memberUser.id)).rejects.toThrow('Access denied');
    });
  });

  describe('column management', () => {
    let testBoard: any;

    beforeEach(async () => {
      testBoard = await TestDataFactory.createBoard(testWorkspace.id, testUser.id);
      await TestDataFactory.createBoardMember(testBoard.id, testUser.id, 'admin');
    });

    describe('createColumn', () => {
      it('should create column successfully', async () => {
        const columnData = {
          name: 'New Column',
          color: '#FF0000',
          settings: { allowMultiple: true },
        };

        const column = await BoardService.createColumn(testBoard.id, columnData, testUser.id);

        expect(column.name).toBe(columnData.name);
        expect(column.boardId).toBe(testBoard.id);
        expect(column.position).toBe(0);
        expect(column.settings).toEqual(columnData.settings);

        // Verify WebSocket emission
        expect(mockIO.to).toHaveBeenCalledWith(`board:${testBoard.id}`);
        expect(mockIO.emit).toHaveBeenCalledWith('column_created', expect.any(Object));
      });

      it('should set correct position for new columns', async () => {
        // Create first column
        const column1 = await BoardService.createColumn(testBoard.id, { name: 'Column 1' }, testUser.id);
        expect(column1.position).toBe(0);

        // Create second column
        const column2 = await BoardService.createColumn(testBoard.id, { name: 'Column 2' }, testUser.id);
        expect(column2.position).toBe(1);
      });

      it('should respect provided position', async () => {
        const columnData = {
          name: 'Positioned Column',
          position: 5,
        };

        const column = await BoardService.createColumn(testBoard.id, columnData, testUser.id);
        expect(column.position).toBe(5);
      });

      it('should throw error for unauthorized user', async () => {
        const otherUser = await TestDataFactory.createUser();
        const columnData = { name: 'Unauthorized Column' };

        await expect(BoardService.createColumn(testBoard.id, columnData, otherUser.id)).rejects.toThrow('Access denied');
      });
    });

    describe('updateColumn', () => {
      let testColumn: any;

      beforeEach(async () => {
        const columns = await TestDataFactory.createBoardColumns(testBoard.id, 1);
        testColumn = columns[0];
      });

      it('should update column successfully', async () => {
        const updateData = {
          name: 'Updated Column',
          color: '#00FF00',
          position: 1,
        };

        const updatedColumn = await BoardService.updateColumn(testColumn.id, updateData, testUser.id);

        expect(updatedColumn.name).toBe(updateData.name);
        expect(updatedColumn.position).toBe(updateData.position);

        // Verify WebSocket emission
        expect(mockIO.to).toHaveBeenCalledWith(`board:${testBoard.id}`);
        expect(mockIO.emit).toHaveBeenCalledWith('column_updated', expect.any(Object));
      });

      it('should throw error for non-existent column', async () => {
        const updateData = { name: 'Non-existent' };

        await expect(BoardService.updateColumn('non-existent-id', updateData, testUser.id)).rejects.toThrow('Column not found');
      });
    });

    describe('deleteColumn', () => {
      let testColumn: any;

      beforeEach(async () => {
        const columns = await TestDataFactory.createBoardColumns(testBoard.id, 1);
        testColumn = columns[0];
      });

      it('should delete column successfully', async () => {
        await BoardService.deleteColumn(testColumn.id, testUser.id);

        const deletedColumn = await testPrisma.boardColumn.findUnique({
          where: { id: testColumn.id },
        });

        expect(deletedColumn).toBeNull();

        // Verify WebSocket emission
        expect(mockIO.to).toHaveBeenCalledWith(`board:${testBoard.id}`);
        expect(mockIO.emit).toHaveBeenCalledWith('column_deleted', expect.any(Object));
      });
    });
  });

  describe('member management', () => {
    let testBoard: any;

    beforeEach(async () => {
      testBoard = await TestDataFactory.createBoard(testWorkspace.id, testUser.id);
      await TestDataFactory.createBoardMember(testBoard.id, testUser.id, 'admin');
    });

    describe('addMember', () => {
      it('should add member successfully', async () => {
        const newUser = await TestDataFactory.createUser();

        const member = await BoardService.addMember(testBoard.id, newUser.id, 'member', {}, testUser.id);

        expect(member.userId).toBe(newUser.id);
        expect(member.boardId).toBe(testBoard.id);
        expect(member.role).toBe('member');

        // Verify WebSocket emission
        expect(mockIO.to).toHaveBeenCalledWith(`board:${testBoard.id}`);
        expect(mockIO.emit).toHaveBeenCalledWith('member_added', expect.any(Object));
      });

      it('should prevent duplicate membership', async () => {
        await expect(BoardService.addMember(testBoard.id, testUser.id, 'member', {}, testUser.id))
          .rejects.toThrow('User is already a member of this board');
      });

      it('should require admin access to add members', async () => {
        const memberUser = await TestDataFactory.createUser();
        const newUser = await TestDataFactory.createUser();
        await TestDataFactory.createBoardMember(testBoard.id, memberUser.id, 'member');

        await expect(BoardService.addMember(testBoard.id, newUser.id, 'member', {}, memberUser.id))
          .rejects.toThrow('Access denied');
      });
    });

    describe('removeMember', () => {
      it('should remove member successfully', async () => {
        const memberUser = await TestDataFactory.createUser();
        await TestDataFactory.createBoardMember(testBoard.id, memberUser.id, 'member');

        await BoardService.removeMember(testBoard.id, memberUser.id, testUser.id);

        const removedMember = await testPrisma.boardMember.findUnique({
          where: {
            boardId_userId: {
              boardId: testBoard.id,
              userId: memberUser.id,
            },
          },
        });

        expect(removedMember).toBeNull();

        // Verify WebSocket emission
        expect(mockIO.to).toHaveBeenCalledWith(`board:${testBoard.id}`);
        expect(mockIO.emit).toHaveBeenCalledWith('member_removed', expect.any(Object));
      });

      it('should prevent removing last admin', async () => {
        await expect(BoardService.removeMember(testBoard.id, testUser.id, testUser.id))
          .rejects.toThrow('Cannot remove the last admin of the board');
      });
    });
  });

  describe('permission helpers', () => {
    let testBoard: any;

    beforeEach(async () => {
      testBoard = await TestDataFactory.createBoard(testWorkspace.id, testUser.id);
    });

    describe('hasReadAccess', () => {
      it('should grant access to board member', async () => {
        await TestDataFactory.createBoardMember(testBoard.id, testUser.id);

        const hasAccess = await BoardService.hasReadAccess(testBoard.id, testUser.id);
        expect(hasAccess).toBe(true);
      });

      it('should grant access to workspace member for public board', async () => {
        const hasAccess = await BoardService.hasReadAccess(testBoard.id, testUser.id);
        expect(hasAccess).toBe(true);
      });

      it('should deny access to private board without membership', async () => {
        const privateBoard = await TestDataFactory.createBoard(testWorkspace.id, testUser.id, {
          isPrivate: true,
        });

        const otherUser = await TestDataFactory.createUser();
        const hasAccess = await BoardService.hasReadAccess(privateBoard.id, otherUser.id);
        expect(hasAccess).toBe(false);
      });
    });

    describe('hasWriteAccess', () => {
      it('should grant write access to board member', async () => {
        await TestDataFactory.createBoardMember(testBoard.id, testUser.id);

        const hasAccess = await BoardService.hasWriteAccess(testBoard.id, testUser.id);
        expect(hasAccess).toBe(true);
      });

      it('should deny write access to non-member', async () => {
        const otherUser = await TestDataFactory.createUser();
        const hasAccess = await BoardService.hasWriteAccess(testBoard.id, otherUser.id);
        expect(hasAccess).toBe(false);
      });
    });

    describe('hasAdminAccess', () => {
      it('should grant admin access to admin member', async () => {
        await TestDataFactory.createBoardMember(testBoard.id, testUser.id, 'admin');

        const hasAccess = await BoardService.hasAdminAccess(testBoard.id, testUser.id);
        expect(hasAccess).toBe(true);
      });

      it('should deny admin access to regular member', async () => {
        await TestDataFactory.createBoardMember(testBoard.id, testUser.id, 'member');

        const hasAccess = await BoardService.hasAdminAccess(testBoard.id, testUser.id);
        expect(hasAccess).toBe(false);
      });
    });
  });

  describe('getStatistics', () => {
    let testBoard: any;

    beforeEach(async () => {
      testBoard = await TestDataFactory.createBoard(testWorkspace.id, testUser.id);
      await TestDataFactory.createBoardMember(testBoard.id, testUser.id, 'admin');
    });

    it('should return correct statistics', async () => {
      // Create test data
      await Promise.all([
        TestDataFactory.createItem(testBoard.id, testUser.id, {
          itemData: { status: 'Done' },
        }),
        TestDataFactory.createItem(testBoard.id, testUser.id, {
          itemData: { status: 'In Progress' },
        }),
      ]);

      await TestDataFactory.createBoardColumns(testBoard.id, 3);

      const stats = await BoardService.getStatistics(testBoard.id);

      expect(stats.totalItems).toBe(2);
      expect(stats.completedItems).toBe(1);
      expect(stats.totalMembers).toBe(1);
      expect(stats.totalColumns).toBe(3);
      expect(typeof stats.activeMembersToday).toBe('number');
    });
  });
});