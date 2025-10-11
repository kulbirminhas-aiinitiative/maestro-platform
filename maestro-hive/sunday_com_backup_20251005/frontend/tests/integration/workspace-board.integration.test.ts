/**
 * Integration Tests for Workspace-Board Workflows
 * Tests complete user workflows across multiple services
 */

import request from 'supertest';
import { app } from '../../backend/src/server';
import { PrismaClient } from '@prisma/client';
import { TestDataFactory } from '../helpers/test-data-factory';
import { setupTestDatabase, cleanupTestDatabase } from '../helpers/test-database';

const prisma = new PrismaClient();

describe('Workspace-Board Integration', () => {
  let authToken: string;
  let userId: string;
  let workspaceId: string;

  beforeAll(async () => {
    await setupTestDatabase();
  });

  afterAll(async () => {
    await cleanupTestDatabase();
    await prisma.$disconnect();
  });

  beforeEach(async () => {
    // Create and authenticate test user
    const userData = TestDataFactory.createUser({
      email: 'integration.test@example.com',
      password: 'SecurePassword123',
    });

    const registerResponse = await request(app)
      .post('/api/auth/register')
      .send(userData)
      .expect(201);

    userId = registerResponse.body.user.id;

    const loginResponse = await request(app)
      .post('/api/auth/login')
      .send({
        email: userData.email,
        password: userData.password,
      })
      .expect(200);

    authToken = loginResponse.body.token;
  });

  afterEach(async () => {
    // Clean up test data
    await prisma.workspaceMember.deleteMany();
    await prisma.board.deleteMany();
    await prisma.workspace.deleteMany();
    await prisma.user.deleteMany();
  });

  describe('Complete Workspace-Board Workflow', () => {
    it('should allow complete workspace and board management lifecycle', async () => {
      // Step 1: Create workspace
      const workspaceData = {
        name: 'Integration Test Workspace',
        description: 'A workspace for integration testing',
      };

      const createWorkspaceResponse = await request(app)
        .post('/api/workspaces')
        .set('Authorization', `Bearer ${authToken}`)
        .send(workspaceData)
        .expect(201);

      expect(createWorkspaceResponse.body).toMatchObject({
        name: workspaceData.name,
        description: workspaceData.description,
        ownerId: userId,
      });

      workspaceId = createWorkspaceResponse.body.id;

      // Step 2: Verify workspace appears in user's workspace list
      const getUserWorkspacesResponse = await request(app)
        .get('/api/workspaces')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(getUserWorkspacesResponse.body).toHaveLength(1);
      expect(getUserWorkspacesResponse.body[0].id).toBe(workspaceId);

      // Step 3: Create board in workspace
      const boardData = {
        name: 'Sprint Planning Board',
        description: 'Board for managing sprint tasks',
        workspaceId: workspaceId,
      };

      const createBoardResponse = await request(app)
        .post('/api/boards')
        .set('Authorization', `Bearer ${authToken}`)
        .send(boardData)
        .expect(201);

      expect(createBoardResponse.body).toMatchObject({
        name: boardData.name,
        description: boardData.description,
        workspaceId: workspaceId,
      });

      const boardId = createBoardResponse.body.id;

      // Step 4: Verify board has default columns
      const getBoardResponse = await request(app)
        .get(`/api/boards/${boardId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(getBoardResponse.body.columns).toHaveLength(3);
      expect(getBoardResponse.body.columns.map(c => c.name)).toEqual([
        'To Do',
        'In Progress',
        'Done',
      ]);

      // Step 5: Get boards in workspace
      const getWorkspaceBoardsResponse = await request(app)
        .get(`/api/boards/workspace/${workspaceId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(getWorkspaceBoardsResponse.body).toHaveLength(1);
      expect(getWorkspaceBoardsResponse.body[0].id).toBe(boardId);

      // Step 6: Update workspace details
      const updateWorkspaceData = {
        name: 'Updated Integration Workspace',
        description: 'Updated description for testing',
      };

      const updateWorkspaceResponse = await request(app)
        .put(`/api/workspaces/${workspaceId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .send(updateWorkspaceData)
        .expect(200);

      expect(updateWorkspaceResponse.body).toMatchObject(updateWorkspaceData);

      // Step 7: Update board details
      const updateBoardData = {
        name: 'Updated Sprint Board',
        description: 'Updated board description',
      };

      const updateBoardResponse = await request(app)
        .put(`/api/boards/${boardId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .send(updateBoardData)
        .expect(200);

      expect(updateBoardResponse.body).toMatchObject(updateBoardData);

      // Step 8: Verify updated workspace still contains updated board
      const getUpdatedWorkspaceResponse = await request(app)
        .get(`/api/workspaces/${workspaceId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(getUpdatedWorkspaceResponse.body.name).toBe(updateWorkspaceData.name);
      expect(getUpdatedWorkspaceResponse.body.boards).toHaveLength(1);
      expect(getUpdatedWorkspaceResponse.body.boards[0].name).toBe(updateBoardData.name);
    });

    it('should handle workspace member management with board access', async () => {
      // Step 1: Create workspace
      const workspaceData = {
        name: 'Team Collaboration Workspace',
        description: 'Workspace for team collaboration testing',
      };

      const createWorkspaceResponse = await request(app)
        .post('/api/workspaces')
        .set('Authorization', `Bearer ${authToken}`)
        .send(workspaceData)
        .expect(201);

      workspaceId = createWorkspaceResponse.body.id;

      // Step 2: Create board in workspace
      const boardData = {
        name: 'Team Board',
        description: 'Board for team collaboration',
        workspaceId: workspaceId,
      };

      const createBoardResponse = await request(app)
        .post('/api/boards')
        .set('Authorization', `Bearer ${authToken}`)
        .send(boardData)
        .expect(201);

      const boardId = createBoardResponse.body.id;

      // Step 3: Create another user
      const secondUserData = TestDataFactory.createUser({
        email: 'seconduser@example.com',
        password: 'SecurePassword123',
      });

      await request(app)
        .post('/api/auth/register')
        .send(secondUserData)
        .expect(201);

      // Step 4: Add second user to workspace
      const addMemberResponse = await request(app)
        .post(`/api/workspaces/${workspaceId}/members`)
        .set('Authorization', `Bearer ${authToken}`)
        .send({
          email: secondUserData.email,
          role: 'MEMBER',
        })
        .expect(201);

      expect(addMemberResponse.body.user.email).toBe(secondUserData.email);
      expect(addMemberResponse.body.role).toBe('MEMBER');

      // Step 5: Login as second user
      const secondUserLoginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: secondUserData.email,
          password: secondUserData.password,
        })
        .expect(200);

      const secondUserToken = secondUserLoginResponse.body.token;

      // Step 6: Verify second user can access workspace
      const getWorkspaceAsSecondUserResponse = await request(app)
        .get(`/api/workspaces/${workspaceId}`)
        .set('Authorization', `Bearer ${secondUserToken}`)
        .expect(200);

      expect(getWorkspaceAsSecondUserResponse.body.id).toBe(workspaceId);
      expect(getWorkspaceAsSecondUserResponse.body.members).toHaveLength(2);

      // Step 7: Verify second user can access board in workspace
      const getBoardAsSecondUserResponse = await request(app)
        .get(`/api/boards/${boardId}`)
        .set('Authorization', `Bearer ${secondUserToken}`)
        .expect(200);

      expect(getBoardAsSecondUserResponse.body.id).toBe(boardId);

      // Step 8: Verify second user appears in workspace member list
      const getWorkspaceMembersResponse = await request(app)
        .get(`/api/workspaces/${workspaceId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      const memberEmails = getWorkspaceMembersResponse.body.members.map(m => m.user.email);
      expect(memberEmails).toContain('integration.test@example.com');
      expect(memberEmails).toContain('seconduser@example.com');

      // Step 9: Remove member from workspace
      const secondUserId = getWorkspaceMembersResponse.body.members.find(
        m => m.user.email === 'seconduser@example.com'
      ).userId;

      await request(app)
        .delete(`/api/workspaces/${workspaceId}/members/${secondUserId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(204);

      // Step 10: Verify second user can no longer access workspace
      await request(app)
        .get(`/api/workspaces/${workspaceId}`)
        .set('Authorization', `Bearer ${secondUserToken}`)
        .expect(404);

      // Step 11: Verify second user can no longer access board
      await request(app)
        .get(`/api/boards/${boardId}`)
        .set('Authorization', `Bearer ${secondUserToken}`)
        .expect(404);
    });

    it('should handle workspace deletion with cascading board deletion', async () => {
      // Step 1: Create workspace
      const workspaceData = {
        name: 'Deletion Test Workspace',
        description: 'Workspace for testing deletion',
      };

      const createWorkspaceResponse = await request(app)
        .post('/api/workspaces')
        .set('Authorization', `Bearer ${authToken}`)
        .send(workspaceData)
        .expect(201);

      workspaceId = createWorkspaceResponse.body.id;

      // Step 2: Create multiple boards in workspace
      const board1Data = {
        name: 'Board 1',
        description: 'First board',
        workspaceId: workspaceId,
      };

      const board2Data = {
        name: 'Board 2',
        description: 'Second board',
        workspaceId: workspaceId,
      };

      const createBoard1Response = await request(app)
        .post('/api/boards')
        .set('Authorization', `Bearer ${authToken}`)
        .send(board1Data)
        .expect(201);

      const createBoard2Response = await request(app)
        .post('/api/boards')
        .set('Authorization', `Bearer ${authToken}`)
        .send(board2Data)
        .expect(201);

      const board1Id = createBoard1Response.body.id;
      const board2Id = createBoard2Response.body.id;

      // Step 3: Verify boards exist
      await request(app)
        .get(`/api/boards/${board1Id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      await request(app)
        .get(`/api/boards/${board2Id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      // Step 4: Delete workspace
      await request(app)
        .delete(`/api/workspaces/${workspaceId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(204);

      // Step 5: Verify workspace no longer exists
      await request(app)
        .get(`/api/workspaces/${workspaceId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(404);

      // Step 6: Verify boards were also deleted (cascading delete)
      await request(app)
        .get(`/api/boards/${board1Id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(404);

      await request(app)
        .get(`/api/boards/${board2Id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(404);

      // Step 7: Verify workspace no longer appears in user's workspace list
      const getUserWorkspacesResponse = await request(app)
        .get('/api/workspaces')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(getUserWorkspacesResponse.body).toHaveLength(0);
    });
  });

  describe('Permission Validation', () => {
    it('should enforce workspace permissions for board operations', async () => {
      // Step 1: Create workspace as first user
      const workspaceData = {
        name: 'Permission Test Workspace',
        description: 'Testing permission enforcement',
      };

      const createWorkspaceResponse = await request(app)
        .post('/api/workspaces')
        .set('Authorization', `Bearer ${authToken}`)
        .send(workspaceData)
        .expect(201);

      workspaceId = createWorkspaceResponse.body.id;

      // Step 2: Create second user (not a member)
      const unauthorizedUserData = TestDataFactory.createUser({
        email: 'unauthorized@example.com',
        password: 'SecurePassword123',
      });

      await request(app)
        .post('/api/auth/register')
        .send(unauthorizedUserData)
        .expect(201);

      const unauthorizedLoginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: unauthorizedUserData.email,
          password: unauthorizedUserData.password,
        })
        .expect(200);

      const unauthorizedToken = unauthorizedLoginResponse.body.token;

      // Step 3: Unauthorized user should not be able to create board in workspace
      const boardData = {
        name: 'Unauthorized Board',
        description: 'This should fail',
        workspaceId: workspaceId,
      };

      await request(app)
        .post('/api/boards')
        .set('Authorization', `Bearer ${unauthorizedToken}`)
        .send(boardData)
        .expect(403);

      // Step 4: Create board as workspace owner
      const authorizedBoardData = {
        name: 'Authorized Board',
        description: 'This should succeed',
        workspaceId: workspaceId,
      };

      const createBoardResponse = await request(app)
        .post('/api/boards')
        .set('Authorization', `Bearer ${authToken}`)
        .send(authorizedBoardData)
        .expect(201);

      const boardId = createBoardResponse.body.id;

      // Step 5: Unauthorized user should not be able to access board
      await request(app)
        .get(`/api/boards/${boardId}`)
        .set('Authorization', `Bearer ${unauthorizedToken}`)
        .expect(404);

      // Step 6: Unauthorized user should not be able to update board
      await request(app)
        .put(`/api/boards/${boardId}`)
        .set('Authorization', `Bearer ${unauthorizedToken}`)
        .send({ name: 'Hacked Board Name' })
        .expect(404);

      // Step 7: Unauthorized user should not be able to delete board
      await request(app)
        .delete(`/api/boards/${boardId}`)
        .set('Authorization', `Bearer ${unauthorizedToken}`)
        .expect(404);

      // Step 8: Workspace owner should still have full access
      await request(app)
        .get(`/api/boards/${boardId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      await request(app)
        .put(`/api/boards/${boardId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .send({ name: 'Updated Board Name' })
        .expect(200);
    });
  });

  describe('Error Handling', () => {
    it('should handle invalid workspace references in board creation', async () => {
      // Attempt to create board with non-existent workspace
      const boardData = {
        name: 'Orphaned Board',
        description: 'Board without valid workspace',
        workspaceId: 'non-existent-workspace-id',
      };

      const response = await request(app)
        .post('/api/boards')
        .set('Authorization', `Bearer ${authToken}`)
        .send(boardData)
        .expect(400);

      expect(response.body.error).toContain('Invalid workspace');
    });

    it('should handle concurrent workspace operations', async () => {
      // Create workspace
      const workspaceData = {
        name: 'Concurrency Test Workspace',
        description: 'Testing concurrent operations',
      };

      const createWorkspaceResponse = await request(app)
        .post('/api/workspaces')
        .set('Authorization', `Bearer ${authToken}`)
        .send(workspaceData)
        .expect(201);

      workspaceId = createWorkspaceResponse.body.id;

      // Attempt multiple simultaneous board creations
      const boardPromises = Array.from({ length: 5 }, (_, index) =>
        request(app)
          .post('/api/boards')
          .set('Authorization', `Bearer ${authToken}`)
          .send({
            name: `Concurrent Board ${index + 1}`,
            description: `Board created concurrently ${index + 1}`,
            workspaceId: workspaceId,
          })
      );

      const responses = await Promise.all(boardPromises);

      // All board creations should succeed
      responses.forEach(response => {
        expect(response.status).toBe(201);
        expect(response.body.workspaceId).toBe(workspaceId);
      });

      // Verify all boards were created
      const getWorkspaceBoardsResponse = await request(app)
        .get(`/api/boards/workspace/${workspaceId}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(getWorkspaceBoardsResponse.body).toHaveLength(5);
    });
  });
});