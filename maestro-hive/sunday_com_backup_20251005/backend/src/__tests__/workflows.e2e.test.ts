import request from 'supertest';
import { testApp, getTestUser1, getTestUser2 } from './e2e-setup';

describe('E2E Workflow Tests', () => {
  let user1Token: string;
  let user2Token: string;
  let testBoardId: string;
  let testWorkspaceId: string;
  let testItemId: string;

  beforeAll(async () => {
    // Login test users
    const user1Login = await request(testApp)
      .post('/api/v1/auth/login')
      .send(getTestUser1())
      .expect(200);

    const user2Login = await request(testApp)
      .post('/api/v1/auth/login')
      .send(getTestUser2())
      .expect(200);

    user1Token = user1Login.body.data.accessToken;
    user2Token = user2Login.body.data.accessToken;

    // Get test workspace and board IDs
    const workspacesResponse = await request(testApp)
      .get('/api/v1/workspaces')
      .set('Authorization', `Bearer ${user1Token}`)
      .expect(200);

    testWorkspaceId = workspacesResponse.body.data[0].id;

    const boardsResponse = await request(testApp)
      .get(`/api/v1/boards/workspace/${testWorkspaceId}`)
      .set('Authorization', `Bearer ${user1Token}`)
      .expect(200);

    testBoardId = boardsResponse.body.data[0].id;
  });

  describe('Complete Project Management Workflow', () => {
    it('should complete a full project workflow', async () => {
      // 1. Create a new project board
      const newBoardResponse = await request(testApp)
        .post('/api/v1/boards')
        .set('Authorization', `Bearer ${user1Token}`)
        .send({
          name: 'E2E Project Board',
          description: 'Board for E2E testing workflow',
          workspaceId: testWorkspaceId,
        })
        .expect(201);

      const projectBoardId = newBoardResponse.body.data.id;
      expect(newBoardResponse.body.data.name).toBe('E2E Project Board');

      // 2. Add columns to the board
      const columnsToCreate = [
        { name: 'Backlog', color: '#94A3B8' },
        { name: 'Sprint', color: '#3B82F6' },
        { name: 'Review', color: '#F59E0B' },
        { name: 'Completed', color: '#10B981' },
      ];

      for (const column of columnsToCreate) {
        await request(testApp)
          .post(`/api/v1/boards/${projectBoardId}/columns`)
          .set('Authorization', `Bearer ${user1Token}`)
          .send(column)
          .expect(201);
      }

      // 3. Create multiple project items
      const itemsToCreate = [
        {
          name: 'Setup Development Environment',
          description: 'Configure local development environment with Docker',
          itemData: { priority: 'high', estimatedHours: 4 },
        },
        {
          name: 'Design Database Schema',
          description: 'Create ERD and database migration files',
          itemData: { priority: 'high', estimatedHours: 6 },
        },
        {
          name: 'Implement User Authentication',
          description: 'JWT-based authentication with refresh tokens',
          itemData: { priority: 'medium', estimatedHours: 8 },
        },
        {
          name: 'Create API Documentation',
          description: 'OpenAPI documentation for all endpoints',
          itemData: { priority: 'low', estimatedHours: 3 },
        },
      ];

      const createdItems = [];
      for (const itemData of itemsToCreate) {
        const response = await request(testApp)
          .post('/api/v1/items')
          .set('Authorization', `Bearer ${user1Token}`)
          .send({
            ...itemData,
            boardId: projectBoardId,
          })
          .expect(201);

        createdItems.push(response.body.data);
      }

      // 4. Assign items to team members
      for (let i = 0; i < createdItems.length; i++) {
        const assigneeToken = i % 2 === 0 ? user1Token : user2Token;
        await request(testApp)
          .put(`/api/v1/items/${createdItems[i].id}`)
          .set('Authorization', `Bearer ${user1Token}`)
          .send({
            assigneeIds: [
              i % 2 === 0 ? 'user1-id' : 'user2-id' // Would be actual user IDs in real scenario
            ],
          })
          .expect(200);
      }

      // 5. Move items through workflow stages
      for (let i = 0; i < 2; i++) {
        const item = createdItems[i];

        // Move to Sprint
        await request(testApp)
          .put(`/api/v1/items/${item.id}`)
          .set('Authorization', `Bearer ${user1Token}`)
          .send({
            itemData: {
              ...item.itemData,
              status: 'in_progress',
              columnId: 'sprint-column-id',
            },
          })
          .expect(200);

        // Add progress comments
        await request(testApp)
          .post(`/api/v1/comments/${item.id}`)
          .set('Authorization', `Bearer ${user1Token}`)
          .send({
            content: `Started working on: ${item.name}`,
          })
          .expect(201);
      }

      // 6. Complete one item
      const completedItem = createdItems[0];
      await request(testApp)
        .put(`/api/v1/items/${completedItem.id}`)
        .set('Authorization', `Bearer ${user1Token}`)
        .send({
          itemData: {
            ...completedItem.itemData,
            status: 'done',
            columnId: 'completed-column-id',
            completedAt: new Date().toISOString(),
          },
        })
        .expect(200);

      // Add completion comment
      await request(testApp)
        .post(`/api/v1/comments/${completedItem.id}`)
        .set('Authorization', `Bearer ${user1Token}`)
        .send({
          content: 'Task completed successfully! ✅',
        })
        .expect(201);

      // 7. Create a subtask
      await request(testApp)
        .post('/api/v1/items')
        .set('Authorization', `Bearer ${user1Token}`)
        .send({
          name: 'Write unit tests for authentication',
          description: 'Cover all auth endpoints with comprehensive tests',
          boardId: projectBoardId,
          parentId: createdItems[2].id, // Authentication item
          itemData: { priority: 'medium', estimatedHours: 2 },
        })
        .expect(201);

      // 8. Get board statistics
      const statsResponse = await request(testApp)
        .get(`/api/v1/boards/${projectBoardId}/stats`)
        .set('Authorization', `Bearer ${user1Token}`)
        .expect(200);

      expect(statsResponse.body.data).toHaveProperty('totalItems');
      expect(statsResponse.body.data).toHaveProperty('completedItems');
      expect(statsResponse.body.data.totalItems).toBeGreaterThan(0);

      // 9. Search for items
      const searchResponse = await request(testApp)
        .get(`/api/v1/items/board/${projectBoardId}`)
        .query({ search: 'authentication' })
        .set('Authorization', `Bearer ${user1Token}`)
        .expect(200);

      expect(searchResponse.body.data.length).toBeGreaterThan(0);
      expect(searchResponse.body.data[0].name.toLowerCase()).toContain('authentication');

      // 10. Get activity timeline
      const activityResponse = await request(testApp)
        .get(`/api/v1/boards/${projectBoardId}/activity`)
        .set('Authorization', `Bearer ${user1Token}`)
        .expect(200);

      expect(activityResponse.body.data).toBeInstanceOf(Array);
      expect(activityResponse.body.data.length).toBeGreaterThan(0);
    });
  });

  describe('Collaboration Workflow', () => {
    it('should handle real-time collaboration features', async () => {
      // 1. User 1 creates an item
      const itemResponse = await request(testApp)
        .post('/api/v1/items')
        .set('Authorization', `Bearer ${user1Token}`)
        .send({
          name: 'Collaborative Task',
          description: 'Task for testing collaboration features',
          boardId: testBoardId,
          itemData: { priority: 'medium' },
        })
        .expect(201);

      testItemId = itemResponse.body.data.id;

      // 2. User 2 comments on the item
      const commentResponse = await request(testApp)
        .post(`/api/v1/comments/${testItemId}`)
        .set('Authorization', `Bearer ${user2Token}`)
        .send({
          content: 'I can help with this task. What are the requirements?',
        })
        .expect(201);

      // 3. User 1 replies with mentions
      await request(testApp)
        .post(`/api/v1/comments/${testItemId}`)
        .set('Authorization', `Bearer ${user1Token}`)
        .send({
          content: '@user2 Thanks! The requirements are in the description.',
          mentions: ['user2-id'],
        })
        .expect(201);

      // 4. User 2 assigns themselves to the task
      await request(testApp)
        .put(`/api/v1/items/${testItemId}`)
        .set('Authorization', `Bearer ${user2Token}`)
        .send({
          assigneeIds: ['user2-id'],
        })
        .expect(200);

      // 5. Both users can see the item with comments
      const user1ItemView = await request(testApp)
        .get(`/api/v1/items/${testItemId}`)
        .set('Authorization', `Bearer ${user1Token}`)
        .expect(200);

      const user2ItemView = await request(testApp)
        .get(`/api/v1/items/${testItemId}`)
        .set('Authorization', `Bearer ${user2Token}`)
        .expect(200);

      expect(user1ItemView.body.data.id).toBe(user2ItemView.body.data.id);

      // 6. Get comments for the item
      const commentsResponse = await request(testApp)
        .get(`/api/v1/comments/item/${testItemId}`)
        .set('Authorization', `Bearer ${user1Token}`)
        .expect(200);

      expect(commentsResponse.body.data.length).toBe(2);
      expect(commentsResponse.body.data[1].content).toContain('@user2');

      // 7. Add reactions to comments
      const commentId = commentsResponse.body.data[0].id;
      await request(testApp)
        .post(`/api/v1/comments/${commentId}/reactions`)
        .set('Authorization', `Bearer ${user1Token}`)
        .send({ emoji: '👍' })
        .expect(201);

      // 8. Time tracking
      await request(testApp)
        .post(`/api/v1/time/${testItemId}`)
        .set('Authorization', `Bearer ${user2Token}`)
        .send({
          description: 'Initial analysis and planning',
          startTime: new Date().toISOString(),
          durationSeconds: 3600, // 1 hour
          isBillable: true,
        })
        .expect(201);

      // 9. Get time entries
      const timeResponse = await request(testApp)
        .get(`/api/v1/time/item/${testItemId}`)
        .set('Authorization', `Bearer ${user2Token}`)
        .expect(200);

      expect(timeResponse.body.data.length).toBe(1);
      expect(timeResponse.body.data[0].durationSeconds).toBe(3600);
    });
  });

  describe('File Management Workflow', () => {
    it('should handle file upload and management', async () => {
      // Note: This would require actual file upload testing with multipart/form-data
      // For now, we'll test the file metadata endpoints

      // 1. Get files for an item (should be empty initially)
      const filesResponse = await request(testApp)
        .get(`/api/v1/files/item/${testItemId}`)
        .set('Authorization', `Bearer ${user1Token}`)
        .expect(200);

      expect(filesResponse.body.data).toBeInstanceOf(Array);

      // 2. Get presigned upload URL
      const presignedResponse = await request(testApp)
        .post('/api/v1/files/presigned-url')
        .set('Authorization', `Bearer ${user1Token}`)
        .send({
          fileName: 'requirements.pdf',
          fileType: 'application/pdf',
          fileSize: 1024000, // 1MB
          entityType: 'item',
          entityId: testItemId,
        })
        .expect(200);

      expect(presignedResponse.body.data).toHaveProperty('uploadUrl');
      expect(presignedResponse.body.data).toHaveProperty('fileKey');
    });
  });

  describe('Error Handling and Edge Cases', () => {
    it('should handle various error scenarios gracefully', async () => {
      // 1. Try to access non-existent resource
      await request(testApp)
        .get('/api/v1/items/00000000-0000-0000-0000-000000000000')
        .set('Authorization', `Bearer ${user1Token}`)
        .expect(404);

      // 2. Try to create item with invalid data
      await request(testApp)
        .post('/api/v1/items')
        .set('Authorization', `Bearer ${user1Token}`)
        .send({
          // Missing required fields
          description: 'Item without name',
        })
        .expect(400);

      // 3. Try to access resource without authentication
      await request(testApp)
        .get(`/api/v1/items/${testItemId}`)
        .expect(401);

      // 4. Try to access resource with invalid token
      await request(testApp)
        .get(`/api/v1/items/${testItemId}`)
        .set('Authorization', 'Bearer invalid-token')
        .expect(401);

      // 5. Try to update item without permission
      // This would require more complex permission setup

      // 6. Try to create duplicate resource (if applicable)
      // This depends on the specific business rules

      // 7. Handle malformed request body
      await request(testApp)
        .post('/api/v1/items')
        .set('Authorization', `Bearer ${user1Token}`)
        .set('Content-Type', 'application/json')
        .send('{"invalid": json}')
        .expect(400);
    });
  });

  describe('Performance and Load Testing', () => {
    it('should handle multiple concurrent requests', async () => {
      const promises = [];

      // Create multiple items concurrently
      for (let i = 0; i < 10; i++) {
        promises.push(
          request(testApp)
            .post('/api/v1/items')
            .set('Authorization', `Bearer ${user1Token}`)
            .send({
              name: `Concurrent Item ${i}`,
              description: `Description for item ${i}`,
              boardId: testBoardId,
              itemData: { priority: 'low' },
            })
            .expect(201)
        );
      }

      const responses = await Promise.all(promises);
      expect(responses).toHaveLength(10);

      // All items should have unique IDs
      const ids = responses.map(r => r.body.data.id);
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(10);
    });

    it('should handle large data sets efficiently', async () => {
      // Get all items with a large limit
      const startTime = Date.now();

      const response = await request(testApp)
        .get(`/api/v1/items/board/${testBoardId}`)
        .query({ limit: 100 })
        .set('Authorization', `Bearer ${user1Token}`)
        .expect(200);

      const endTime = Date.now();
      const responseTime = endTime - startTime;

      // Response should be fast (under 1 second for this test)
      expect(responseTime).toBeLessThan(1000);
      expect(response.body.data).toBeInstanceOf(Array);
      expect(response.body.meta).toHaveProperty('total');
    });
  });
});