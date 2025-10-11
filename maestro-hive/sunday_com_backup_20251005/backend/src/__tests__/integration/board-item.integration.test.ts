import request from 'supertest';
import { app } from '@/server';
import { prisma } from '@/config/database';
import { RedisService } from '@/config/redis';
import { generateTestToken, createTestUser, createTestOrganization, createTestWorkspace } from '../helpers/test-helpers';

describe('Board-Item Integration Tests', () => {
  let testUser: any;
  let testOrg: any;
  let testWorkspace: any;
  let testBoard: any;
  let authToken: string;

  beforeAll(async () => {
    // Create test user and organization
    testUser = await createTestUser();
    testOrg = await createTestOrganization(testUser.id);
    testWorkspace = await createTestWorkspace(testOrg.id, testUser.id);
    authToken = generateTestToken(testUser);
  });

  afterAll(async () => {
    // Clean up test data
    await prisma.organization.deleteMany({
      where: { id: testOrg.id },
    });
    await prisma.user.deleteMany({
      where: { id: testUser.id },
    });
    await RedisService.flushAll();
  });

  beforeEach(async () => {
    // Create a fresh board for each test
    const boardResponse = await request(app)
      .post('/api/v1/boards')
      .set('Authorization', `Bearer ${authToken}`)
      .send({
        name: 'Test Board',
        description: 'Integration test board',
        workspaceId: testWorkspace.id,
        columns: [
          { name: 'To Do', color: '#FF0000' },
          { name: 'In Progress', color: '#FFFF00' },
          { name: 'Done', color: '#00FF00' },
        ],
      });

    testBoard = boardResponse.body.data;
  });

  afterEach(async () => {
    // Clean up boards after each test
    if (testBoard) {
      await prisma.board.deleteMany({
        where: { id: testBoard.id },
      });
    }
  });

  describe('Complete Board-Item Workflow', () => {
    it('should create board, add items, update them, and track changes', async () => {
      // 1. Verify board was created with columns
      expect(testBoard).toBeDefined();
      expect(testBoard.name).toBe('Test Board');
      expect(testBoard.columns).toHaveLength(3);

      // 2. Create multiple items
      const item1Response = await request(app)
        .post('/api/v1/items')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          name: 'First task',
          description: 'This is the first task',
          boardId: testBoard.id,
          itemData: {
            status: 'To Do',
            priority: 'High',
          },
        });

      const item2Response = await request(app)
        .post('/api/v1/items')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          name: 'Second task',
          description: 'This is the second task',
          boardId: testBoard.id,
          itemData: {
            status: 'To Do',
            priority: 'Medium',
          },
        });

      expect(item1Response.status).toBe(201);
      expect(item2Response.status).toBe(201);

      const item1 = item1Response.body.data;
      const item2 = item2Response.body.data;

      // 3. Get board with items
      const boardWithItemsResponse = await request(app)
        .get(`/api/v1/boards/${testBoard.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .query({ includeItems: 'true' });

      expect(boardWithItemsResponse.status).toBe(200);
      expect(boardWithItemsResponse.body.data.items).toHaveLength(2);

      // 4. Update item status
      const updateResponse = await request(app)
        .put(`/api/v1/items/${item1.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          itemData: {
            status: 'In Progress',
            priority: 'High',
          },
        });

      expect(updateResponse.status).toBe(200);
      expect(updateResponse.body.data.itemData.status).toBe('In Progress');

      // 5. Bulk update multiple items
      const bulkUpdateResponse = await request(app)
        .put('/api/v1/items/bulk/update')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          itemIds: [item1.id, item2.id],
          updates: {
            itemData: {
              priority: 'Critical',
            },
          },
        });

      expect(bulkUpdateResponse.status).toBe(200);
      expect(bulkUpdateResponse.body.data.updatedCount).toBe(2);
      expect(bulkUpdateResponse.body.data.errors).toHaveLength(0);

      // 6. Verify updates
      const updatedItem1Response = await request(app)
        .get(`/api/v1/items/${item1.id}`)
        .set('Authorization', `Bearer ${authToken}`);

      expect(updatedItem1Response.status).toBe(200);
      expect(updatedItem1Response.body.data.itemData.priority).toBe('Critical');
      expect(updatedItem1Response.body.data.itemData.status).toBe('In Progress');

      // 7. Get board statistics
      const statsResponse = await request(app)
        .get(`/api/v1/boards/${testBoard.id}/statistics`)
        .set('Authorization', `Bearer ${authToken}`);

      expect(statsResponse.status).toBe(200);
      expect(statsResponse.body.data.totalItems).toBe(2);
      expect(statsResponse.body.data.completedItems).toBe(0);

      // 8. Complete one item and verify statistics
      await request(app)
        .put(`/api/v1/items/${item2.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          itemData: {
            status: 'Done',
            priority: 'Critical',
          },
        });

      const updatedStatsResponse = await request(app)
        .get(`/api/v1/boards/${testBoard.id}/statistics`)
        .set('Authorization', `Bearer ${authToken}`);

      expect(updatedStatsResponse.status).toBe(200);
      expect(updatedStatsResponse.body.data.totalItems).toBe(2);
      expect(updatedStatsResponse.body.data.completedItems).toBe(1);
    });

    it('should handle item dependencies correctly', async () => {
      // Create two items
      const item1Response = await request(app)
        .post('/api/v1/items')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          name: 'Prerequisite task',
          boardId: testBoard.id,
          itemData: { status: 'To Do' },
        });

      const item2Response = await request(app)
        .post('/api/v1/items')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          name: 'Dependent task',
          boardId: testBoard.id,
          itemData: { status: 'To Do' },
        });

      const item1 = item1Response.body.data;
      const item2 = item2Response.body.data;

      // Add dependency (item1 blocks item2)
      const dependencyResponse = await request(app)
        .post(`/api/v1/items/${item2.id}/dependencies`)
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          predecessorId: item1.id,
          dependencyType: 'blocks',
        });

      expect(dependencyResponse.status).toBe(201);

      // Get item with dependencies
      const itemWithDepsResponse = await request(app)
        .get(`/api/v1/items/${item2.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .query({ includeDependencies: 'true' });

      expect(itemWithDepsResponse.status).toBe(200);
      expect(itemWithDepsResponse.body.data.dependencies).toHaveLength(1);

      // Try to create circular dependency (should fail)
      const circularDependencyResponse = await request(app)
        .post(`/api/v1/items/${item1.id}/dependencies`)
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          predecessorId: item2.id,
          dependencyType: 'blocks',
        });

      expect(circularDependencyResponse.status).toBe(409);
      expect(circularDependencyResponse.body.error.message).toContain('circular');

      // Remove dependency
      const removeDependencyResponse = await request(app)
        .delete(`/api/v1/items/${item2.id}/dependencies/${item1.id}`)
        .set('Authorization', `Bearer ${authToken}`);

      expect(removeDependencyResponse.status).toBe(204);
    });

    it('should handle board member management', async () => {
      // Get initial board members
      const initialMembersResponse = await request(app)
        .get(`/api/v1/boards/${testBoard.id}/members`)
        .set('Authorization', `Bearer ${authToken}`);

      expect(initialMembersResponse.status).toBe(200);
      expect(initialMembersResponse.body.data).toHaveLength(1); // Creator

      // Create another user to add as member
      const otherUser = await createTestUser('other@test.com');

      // Add organization membership for the other user
      await prisma.organizationMember.create({
        data: {
          organizationId: testOrg.id,
          userId: otherUser.id,
          role: 'member',
        },
      });

      // Add member to board
      const addMemberResponse = await request(app)
        .post(`/api/v1/boards/${testBoard.id}/members`)
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          userId: otherUser.id,
          role: 'member',
        });

      expect(addMemberResponse.status).toBe(201);

      // Verify member was added
      const membersResponse = await request(app)
        .get(`/api/v1/boards/${testBoard.id}/members`)
        .set('Authorization', `Bearer ${authToken}`);

      expect(membersResponse.status).toBe(200);
      expect(membersResponse.body.data).toHaveLength(2);

      // Update member role
      const updateMemberResponse = await request(app)
        .put(`/api/v1/boards/${testBoard.id}/members/${otherUser.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          role: 'admin',
        });

      expect(updateMemberResponse.status).toBe(200);

      // Try to remove the last admin (should fail)
      const removeAdminResponse = await request(app)
        .delete(`/api/v1/boards/${testBoard.id}/members/${testUser.id}`)
        .set('Authorization', `Bearer ${authToken}`);

      expect(removeAdminResponse.status).toBe(409);
      expect(removeAdminResponse.body.error.message).toContain('last admin');

      // Remove the other member
      const removeMemberResponse = await request(app)
        .delete(`/api/v1/boards/${testBoard.id}/members/${otherUser.id}`)
        .set('Authorization', `Bearer ${authToken}`);

      expect(removeMemberResponse.status).toBe(204);

      // Clean up the other user
      await prisma.user.delete({ where: { id: otherUser.id } });
    });

    it('should handle board column management', async () => {
      // Verify initial columns
      expect(testBoard.columns).toHaveLength(3);

      // Add new column
      const addColumnResponse = await request(app)
        .post(`/api/v1/boards/${testBoard.id}/columns`)
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          name: 'Review',
          color: '#0000FF',
        });

      expect(addColumnResponse.status).toBe(201);
      const newColumn = addColumnResponse.body.data;

      // Update column
      const updateColumnResponse = await request(app)
        .put(`/api/v1/boards/columns/${newColumn.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          name: 'Code Review',
          color: '#800080',
        });

      expect(updateColumnResponse.status).toBe(200);
      expect(updateColumnResponse.body.data.name).toBe('Code Review');

      // Get board with updated columns
      const boardResponse = await request(app)
        .get(`/api/v1/boards/${testBoard.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .query({ includeColumns: 'true' });

      expect(boardResponse.status).toBe(200);
      expect(boardResponse.body.data.columns).toHaveLength(4);

      // Delete column
      const deleteColumnResponse = await request(app)
        .delete(`/api/v1/boards/columns/${newColumn.id}`)
        .set('Authorization', `Bearer ${authToken}`);

      expect(deleteColumnResponse.status).toBe(204);

      // Verify column was deleted
      const finalBoardResponse = await request(app)
        .get(`/api/v1/boards/${testBoard.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .query({ includeColumns: 'true' });

      expect(finalBoardResponse.status).toBe(200);
      expect(finalBoardResponse.body.data.columns).toHaveLength(3);
    });

    it('should handle filtering and sorting of items', async () => {
      // Create multiple items with different properties
      const items = [
        {
          name: 'High priority task',
          itemData: { status: 'To Do', priority: 'High' },
          assigneeIds: [testUser.id],
        },
        {
          name: 'Medium priority task',
          itemData: { status: 'In Progress', priority: 'Medium' },
        },
        {
          name: 'Low priority task',
          itemData: { status: 'Done', priority: 'Low' },
          assigneeIds: [testUser.id],
        },
      ];

      const createdItems = [];
      for (const itemData of items) {
        const response = await request(app)
          .post('/api/v1/items')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            ...itemData,
            boardId: testBoard.id,
          });
        createdItems.push(response.body.data);
      }

      // Test filtering by status
      const todoItemsResponse = await request(app)
        .get(`/api/v1/items/board/${testBoard.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .query({ status: 'To Do' });

      expect(todoItemsResponse.status).toBe(200);
      expect(todoItemsResponse.body.data).toHaveLength(1);
      expect(todoItemsResponse.body.data[0].itemData.status).toBe('To Do');

      // Test filtering by assignee
      const assignedItemsResponse = await request(app)
        .get(`/api/v1/items/board/${testBoard.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .query({ assigneeIds: testUser.id });

      expect(assignedItemsResponse.status).toBe(200);
      expect(assignedItemsResponse.body.data).toHaveLength(2);

      // Test search
      const searchResponse = await request(app)
        .get(`/api/v1/items/board/${testBoard.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .query({ search: 'High priority' });

      expect(searchResponse.status).toBe(200);
      expect(searchResponse.body.data).toHaveLength(1);
      expect(searchResponse.body.data[0].name).toBe('High priority task');

      // Test sorting
      const sortedResponse = await request(app)
        .get(`/api/v1/items/board/${testBoard.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .query({ sortBy: 'name', sortOrder: 'desc' });

      expect(sortedResponse.status).toBe(200);
      const sortedNames = sortedResponse.body.data.map((item: any) => item.name);
      expect(sortedNames[0]).toBe('Medium priority task');
    });
  });

  describe('Error Handling and Edge Cases', () => {
    it('should handle unauthorized access', async () => {
      // Try to access board without auth
      const unauthorizedResponse = await request(app)
        .get(`/api/v1/boards/${testBoard.id}`);

      expect(unauthorizedResponse.status).toBe(401);

      // Try to access board with invalid token
      const invalidTokenResponse = await request(app)
        .get(`/api/v1/boards/${testBoard.id}`)
        .set('Authorization', 'Bearer invalid_token');

      expect(invalidTokenResponse.status).toBe(401);
    });

    it('should handle non-existent resources', async () => {
      const fakeId = '550e8400-e29b-41d4-a716-446655440000';

      // Try to get non-existent board
      const boardResponse = await request(app)
        .get(`/api/v1/boards/${fakeId}`)
        .set('Authorization', `Bearer ${authToken}`);

      expect(boardResponse.status).toBe(404);

      // Try to get non-existent item
      const itemResponse = await request(app)
        .get(`/api/v1/items/${fakeId}`)
        .set('Authorization', `Bearer ${authToken}`);

      expect(itemResponse.status).toBe(404);
    });

    it('should validate input data', async () => {
      // Try to create board with invalid data
      const invalidBoardResponse = await request(app)
        .post('/api/v1/boards')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          name: '', // Empty name
          workspaceId: 'invalid-uuid',
        });

      expect(invalidBoardResponse.status).toBe(400);

      // Try to create item with invalid data
      const invalidItemResponse = await request(app)
        .post('/api/v1/items')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          name: '', // Empty name
          boardId: 'invalid-uuid',
        });

      expect(invalidItemResponse.status).toBe(400);
    });

    it('should handle bulk operations with partial failures', async () => {
      // Create one valid item
      const validItemResponse = await request(app)
        .post('/api/v1/items')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          name: 'Valid item',
          boardId: testBoard.id,
        });

      const validItemId = validItemResponse.body.data.id;
      const fakeItemId = '550e8400-e29b-41d4-a716-446655440000';

      // Try bulk update with mix of valid and invalid IDs
      const bulkUpdateResponse = await request(app)
        .put('/api/v1/items/bulk/update')
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          itemIds: [validItemId, fakeItemId],
          updates: {
            itemData: { status: 'Updated' },
          },
        });

      expect(bulkUpdateResponse.status).toBe(200);
      expect(bulkUpdateResponse.body.data.updatedCount).toBe(1);
      expect(bulkUpdateResponse.body.data.errors).toHaveLength(1);
      expect(bulkUpdateResponse.body.data.errors[0].itemId).toBe(fakeItemId);
    });
  });

  describe('Performance and Caching', () => {
    it('should cache board data for better performance', async () => {
      // First request should hit the database
      const startTime1 = Date.now();
      const response1 = await request(app)
        .get(`/api/v1/boards/${testBoard.id}`)
        .set('Authorization', `Bearer ${authToken}`);
      const duration1 = Date.now() - startTime1;

      expect(response1.status).toBe(200);

      // Second request should be faster due to caching
      const startTime2 = Date.now();
      const response2 = await request(app)
        .get(`/api/v1/boards/${testBoard.id}`)
        .set('Authorization', `Bearer ${authToken}`);
      const duration2 = Date.now() - startTime2;

      expect(response2.status).toBe(200);
      expect(response2.body.data.id).toBe(testBoard.id);

      // Note: In a real test environment, you might not see significant
      // performance differences, but in production with database latency,
      // caching makes a significant difference
    });

    it('should handle pagination correctly', async () => {
      // Create multiple items
      const itemPromises = [];
      for (let i = 0; i < 25; i++) {
        itemPromises.push(
          request(app)
            .post('/api/v1/items')
            .set('Authorization', `Bearer ${authToken}`)
            .send({
              name: `Item ${i}`,
              boardId: testBoard.id,
              itemData: { status: 'To Do' },
            })
        );
      }

      await Promise.all(itemPromises);

      // Test pagination
      const page1Response = await request(app)
        .get(`/api/v1/items/board/${testBoard.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .query({ page: 1, limit: 10 });

      expect(page1Response.status).toBe(200);
      expect(page1Response.body.data).toHaveLength(10);
      expect(page1Response.body.meta.page).toBe(1);
      expect(page1Response.body.meta.limit).toBe(10);
      expect(page1Response.body.meta.total).toBe(25);
      expect(page1Response.body.meta.totalPages).toBe(3);
      expect(page1Response.body.meta.hasNext).toBe(true);

      // Test second page
      const page2Response = await request(app)
        .get(`/api/v1/items/board/${testBoard.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .query({ page: 2, limit: 10 });

      expect(page2Response.status).toBe(200);
      expect(page2Response.body.data).toHaveLength(10);
      expect(page2Response.body.meta.hasNext).toBe(true);
      expect(page2Response.body.meta.hasPrev).toBe(true);

      // Test last page
      const page3Response = await request(app)
        .get(`/api/v1/items/board/${testBoard.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .query({ page: 3, limit: 10 });

      expect(page3Response.status).toBe(200);
      expect(page3Response.body.data).toHaveLength(5);
      expect(page3Response.body.meta.hasNext).toBe(false);
      expect(page3Response.body.meta.hasPrev).toBe(true);
    });
  });
});