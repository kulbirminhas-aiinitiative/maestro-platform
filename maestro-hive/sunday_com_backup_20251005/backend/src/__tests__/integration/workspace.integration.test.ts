/**
 * Integration Tests for Workspace Management
 * Tests the complete workspace lifecycle and permissions
 */

import request from 'supertest';
import { app } from '../../server';
import { PrismaClient } from '@prisma/client';
import { createTestUser, createTestOrganization, cleanupTestData } from '../helpers/testHelpers';

describe('Workspace Integration Tests', () => {
  let prisma: PrismaClient;
  let testUser: any;
  let testOrg: any;
  let authToken: string;

  beforeAll(async () => {
    prisma = new PrismaClient();
    await prisma.$connect();
  });

  beforeEach(async () => {
    // Create test user and organization
    testUser = await createTestUser(prisma);
    testOrg = await createTestOrganization(prisma, testUser.id);

    // Get auth token
    const loginResponse = await request(app)
      .post('/api/v1/auth/login')
      .send({
        email: testUser.email,
        password: 'testPassword123!'
      });

    authToken = loginResponse.body.token;
  });

  afterEach(async () => {
    await cleanupTestData(prisma);
  });

  afterAll(async () => {
    await prisma.$disconnect();
  });

  describe('POST /api/v1/workspaces', () => {
    it('should create a new workspace successfully', async () => {
      const workspaceData = {
        name: 'Test Workspace',
        description: 'A test workspace for development',
        organizationId: testOrg.id
      };

      const response = await request(app)
        .post('/api/v1/workspaces')
        .set('Authorization', `Bearer ${authToken}`)
        .send(workspaceData)
        .expect(201);

      expect(response.body).toMatchObject({
        id: expect.any(String),
        name: workspaceData.name,
        description: workspaceData.description,
        organizationId: testOrg.id,
        ownerId: testUser.id
      });

      // Verify workspace exists in database
      const workspace = await prisma.workspace.findUnique({
        where: { id: response.body.id }
      });
      expect(workspace).toBeTruthy();
      expect(workspace?.name).toBe(workspaceData.name);
    });

    it('should fail to create workspace without authentication', async () => {
      const workspaceData = {
        name: 'Test Workspace',
        description: 'A test workspace for development',
        organizationId: testOrg.id
      };

      await request(app)
        .post('/api/v1/workspaces')
        .send(workspaceData)
        .expect(401);
    });

    it('should fail to create workspace with invalid organization', async () => {
      const workspaceData = {
        name: 'Test Workspace',
        description: 'A test workspace for development',
        organizationId: 'invalid-org-id'
      };

      await request(app)
        .post('/api/v1/workspaces')
        .set('Authorization', `Bearer ${authToken}`)
        .send(workspaceData)
        .expect(400);
    });

    it('should fail to create workspace with missing required fields', async () => {
      const workspaceData = {
        description: 'A test workspace for development'
        // Missing name and organizationId
      };

      await request(app)
        .post('/api/v1/workspaces')
        .set('Authorization', `Bearer ${authToken}`)
        .send(workspaceData)
        .expect(400);
    });
  });

  describe('GET /api/v1/workspaces', () => {
    let testWorkspace: any;

    beforeEach(async () => {
      // Create a test workspace
      testWorkspace = await prisma.workspace.create({
        data: {
          name: 'Test Workspace',
          description: 'Test description',
          organizationId: testOrg.id,
          ownerId: testUser.id
        }
      });
    });

    it('should retrieve user workspaces successfully', async () => {
      const response = await request(app)
        .get('/api/v1/workspaces')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body).toHaveProperty('workspaces');
      expect(Array.isArray(response.body.workspaces)).toBe(true);
      expect(response.body.workspaces).toHaveLength(1);
      expect(response.body.workspaces[0]).toMatchObject({
        id: testWorkspace.id,
        name: testWorkspace.name,
        description: testWorkspace.description
      });
    });

    it('should support pagination', async () => {
      // Create multiple workspaces
      for (let i = 0; i < 5; i++) {
        await prisma.workspace.create({
          data: {
            name: `Workspace ${i}`,
            description: `Description ${i}`,
            organizationId: testOrg.id,
            ownerId: testUser.id
          }
        });
      }

      const response = await request(app)
        .get('/api/v1/workspaces?page=1&limit=3')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body.workspaces).toHaveLength(3);
      expect(response.body).toHaveProperty('pagination');
      expect(response.body.pagination).toMatchObject({
        page: 1,
        limit: 3,
        total: expect.any(Number),
        totalPages: expect.any(Number)
      });
    });

    it('should filter workspaces by organization', async () => {
      // Create another organization and workspace
      const anotherOrg = await createTestOrganization(prisma, testUser.id);
      await prisma.workspace.create({
        data: {
          name: 'Another Workspace',
          description: 'Another description',
          organizationId: anotherOrg.id,
          ownerId: testUser.id
        }
      });

      const response = await request(app)
        .get(`/api/v1/workspaces?organizationId=${testOrg.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body.workspaces).toHaveLength(1);
      expect(response.body.workspaces[0].organizationId).toBe(testOrg.id);
    });
  });

  describe('GET /api/v1/workspaces/:id', () => {
    let testWorkspace: any;

    beforeEach(async () => {
      testWorkspace = await prisma.workspace.create({
        data: {
          name: 'Test Workspace',
          description: 'Test description',
          organizationId: testOrg.id,
          ownerId: testUser.id
        }
      });
    });

    it('should retrieve workspace details successfully', async () => {
      const response = await request(app)
        .get(`/api/v1/workspaces/${testWorkspace.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(200);

      expect(response.body).toMatchObject({
        id: testWorkspace.id,
        name: testWorkspace.name,
        description: testWorkspace.description,
        organizationId: testOrg.id,
        ownerId: testUser.id
      });
    });

    it('should return 404 for non-existent workspace', async () => {
      await request(app)
        .get('/api/v1/workspaces/non-existent-id')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(404);
    });

    it('should deny access to unauthorized user', async () => {
      // Create another user
      const anotherUser = await createTestUser(prisma, 'another@test.com');
      const anotherLoginResponse = await request(app)
        .post('/api/v1/auth/login')
        .send({
          email: anotherUser.email,
          password: 'testPassword123!'
        });

      await request(app)
        .get(`/api/v1/workspaces/${testWorkspace.id}`)
        .set('Authorization', `Bearer ${anotherLoginResponse.body.token}`)
        .expect(403);
    });
  });

  describe('PUT /api/v1/workspaces/:id', () => {
    let testWorkspace: any;

    beforeEach(async () => {
      testWorkspace = await prisma.workspace.create({
        data: {
          name: 'Test Workspace',
          description: 'Test description',
          organizationId: testOrg.id,
          ownerId: testUser.id
        }
      });
    });

    it('should update workspace successfully', async () => {
      const updateData = {
        name: 'Updated Workspace',
        description: 'Updated description'
      };

      const response = await request(app)
        .put(`/api/v1/workspaces/${testWorkspace.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .send(updateData)
        .expect(200);

      expect(response.body).toMatchObject({
        id: testWorkspace.id,
        name: updateData.name,
        description: updateData.description
      });

      // Verify update in database
      const updatedWorkspace = await prisma.workspace.findUnique({
        where: { id: testWorkspace.id }
      });
      expect(updatedWorkspace?.name).toBe(updateData.name);
      expect(updatedWorkspace?.description).toBe(updateData.description);
    });

    it('should deny update to non-owner', async () => {
      const anotherUser = await createTestUser(prisma, 'another@test.com');
      const anotherLoginResponse = await request(app)
        .post('/api/v1/auth/login')
        .send({
          email: anotherUser.email,
          password: 'testPassword123!'
        });

      const updateData = {
        name: 'Updated Workspace',
        description: 'Updated description'
      };

      await request(app)
        .put(`/api/v1/workspaces/${testWorkspace.id}`)
        .set('Authorization', `Bearer ${anotherLoginResponse.body.token}`)
        .send(updateData)
        .expect(403);
    });

    it('should validate update data', async () => {
      const invalidUpdateData = {
        name: '', // Empty name should be invalid
        description: 'Updated description'
      };

      await request(app)
        .put(`/api/v1/workspaces/${testWorkspace.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .send(invalidUpdateData)
        .expect(400);
    });
  });

  describe('DELETE /api/v1/workspaces/:id', () => {
    let testWorkspace: any;

    beforeEach(async () => {
      testWorkspace = await prisma.workspace.create({
        data: {
          name: 'Test Workspace',
          description: 'Test description',
          organizationId: testOrg.id,
          ownerId: testUser.id
        }
      });
    });

    it('should delete workspace successfully', async () => {
      await request(app)
        .delete(`/api/v1/workspaces/${testWorkspace.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .expect(204);

      // Verify deletion in database
      const deletedWorkspace = await prisma.workspace.findUnique({
        where: { id: testWorkspace.id }
      });
      expect(deletedWorkspace).toBeNull();
    });

    it('should deny deletion to non-owner', async () => {
      const anotherUser = await createTestUser(prisma, 'another@test.com');
      const anotherLoginResponse = await request(app)
        .post('/api/v1/auth/login')
        .send({
          email: anotherUser.email,
          password: 'testPassword123!'
        });

      await request(app)
        .delete(`/api/v1/workspaces/${testWorkspace.id}`)
        .set('Authorization', `Bearer ${anotherLoginResponse.body.token}`)
        .expect(403);
    });

    it('should return 404 for non-existent workspace', async () => {
      await request(app)
        .delete('/api/v1/workspaces/non-existent-id')
        .set('Authorization', `Bearer ${authToken}`)
        .expect(404);
    });
  });

  describe('Workspace Permissions', () => {
    let testWorkspace: any;
    let memberUser: any;
    let memberToken: string;

    beforeEach(async () => {
      testWorkspace = await prisma.workspace.create({
        data: {
          name: 'Test Workspace',
          description: 'Test description',
          organizationId: testOrg.id,
          ownerId: testUser.id
        }
      });

      // Create member user
      memberUser = await createTestUser(prisma, 'member@test.com');
      const memberLoginResponse = await request(app)
        .post('/api/v1/auth/login')
        .send({
          email: memberUser.email,
          password: 'testPassword123!'
        });
      memberToken = memberLoginResponse.body.token;

      // Add member to workspace
      await prisma.workspaceMember.create({
        data: {
          workspaceId: testWorkspace.id,
          userId: memberUser.id,
          role: 'MEMBER'
        }
      });
    });

    it('should allow member to view workspace', async () => {
      const response = await request(app)
        .get(`/api/v1/workspaces/${testWorkspace.id}`)
        .set('Authorization', `Bearer ${memberToken}`)
        .expect(200);

      expect(response.body.id).toBe(testWorkspace.id);
    });

    it('should deny member from updating workspace', async () => {
      const updateData = {
        name: 'Updated by Member',
        description: 'Should not work'
      };

      await request(app)
        .put(`/api/v1/workspaces/${testWorkspace.id}`)
        .set('Authorization', `Bearer ${memberToken}`)
        .send(updateData)
        .expect(403);
    });

    it('should deny member from deleting workspace', async () => {
      await request(app)
        .delete(`/api/v1/workspaces/${testWorkspace.id}`)
        .set('Authorization', `Bearer ${memberToken}`)
        .expect(403);
    });
  });

  describe('Workspace Activity Logging', () => {
    let testWorkspace: any;

    beforeEach(async () => {
      testWorkspace = await prisma.workspace.create({
        data: {
          name: 'Test Workspace',
          description: 'Test description',
          organizationId: testOrg.id,
          ownerId: testUser.id
        }
      });
    });

    it('should log workspace creation', async () => {
      // Check that activity log was created
      const activities = await prisma.activity.findMany({
        where: {
          entityType: 'WORKSPACE',
          entityId: testWorkspace.id,
          action: 'CREATED'
        }
      });

      expect(activities).toHaveLength(1);
      expect(activities[0]).toMatchObject({
        userId: testUser.id,
        entityType: 'WORKSPACE',
        entityId: testWorkspace.id,
        action: 'CREATED'
      });
    });

    it('should log workspace updates', async () => {
      const updateData = {
        name: 'Updated Workspace',
        description: 'Updated description'
      };

      await request(app)
        .put(`/api/v1/workspaces/${testWorkspace.id}`)
        .set('Authorization', `Bearer ${authToken}`)
        .send(updateData);

      const activities = await prisma.activity.findMany({
        where: {
          entityType: 'WORKSPACE',
          entityId: testWorkspace.id,
          action: 'UPDATED'
        }
      });

      expect(activities).toHaveLength(1);
      expect(activities[0]).toMatchObject({
        userId: testUser.id,
        entityType: 'WORKSPACE',
        entityId: testWorkspace.id,
        action: 'UPDATED'
      });
    });
  });
});