import { OrganizationService } from '@/services/organization.service';
import { prisma } from '@/config/database';
import {
  TestDataFactory,
  TestCleanup,
  TestMocks,
  PerformanceTestHelpers,
} from './utils/testHelpers';
import { CreateOrganizationData } from '@/types';

describe('OrganizationService', () => {
  let mockRedis: any;
  let mockLogger: any;

  beforeEach(async () => {
    // Setup mocks
    mockRedis = TestMocks.mockRedisService();
    mockLogger = TestMocks.mockLogger();

    // Clean up any existing test data
    await TestCleanup.cleanupTestUsers();
  });

  afterEach(async () => {
    // Restore mocks
    TestMocks.restoreAll();

    // Clean up test data
    await TestCleanup.cleanupAll();
  });

  describe('create', () => {
    it('should create a new organization successfully', async () => {
      const creator = await TestDataFactory.createUser({
        email: 'creator@example.com',
        firstName: 'Jane',
        lastName: 'Creator',
      });

      const organizationData: CreateOrganizationData = {
        name: 'Acme Corporation',
        slug: 'acme-corp',
        description: 'A test organization for Acme',
        settings: { theme: 'light' },
      };

      const organization = await OrganizationService.create(organizationData, creator.id);

      expect(organization).toMatchObject({
        name: 'Acme Corporation',
        slug: 'acme-corp',
        description: 'A test organization for Acme',
        settings: { theme: 'light' },
      });

      expect(organization.members).toHaveLength(1);
      expect(organization.members![0]).toMatchObject({
        userId: creator.id,
        role: 'owner',
        status: 'active',
      });

      expect(organization._count).toEqual({
        members: 1,
        workspaces: 0,
      });

      // Verify business logging
      expect(mockLogger.business).toHaveBeenCalledWith(
        `Organization created: ${organization.name}`,
        {
          organizationId: organization.id,
          creatorId: creator.id,
        }
      );
    });

    it('should throw error if slug is already taken', async () => {
      const creator1 = await TestDataFactory.createUser();
      const creator2 = await TestDataFactory.createUser();

      const organizationData: CreateOrganizationData = {
        name: 'First Organization',
        slug: 'duplicate-slug',
        description: 'First organization',
        settings: {},
      };

      // Create first organization
      await OrganizationService.create(organizationData, creator1.id);

      // Attempt to create second organization with same slug
      const duplicateData: CreateOrganizationData = {
        name: 'Second Organization',
        slug: 'duplicate-slug',
        description: 'Second organization',
        settings: {},
      };

      await expect(
        OrganizationService.create(duplicateData, creator2.id)
      ).rejects.toThrow('Organization slug is already taken');
    });

    it('should handle database errors gracefully', async () => {
      const creator = await TestDataFactory.createUser();

      // Mock database error
      const mockCreate = jest.spyOn(prisma.organization, 'create').mockRejectedValue(
        new Error('Database connection failed')
      );

      const organizationData: CreateOrganizationData = {
        name: 'Test Organization',
        slug: 'test-org',
        description: 'Test organization',
        settings: {},
      };

      await expect(
        OrganizationService.create(organizationData, creator.id)
      ).rejects.toThrow('Database connection failed');

      expect(mockLogger.error).toHaveBeenCalledWith(
        'Organization creation failed',
        expect.any(Error)
      );

      mockCreate.mockRestore();
    });

    it('should complete organization creation within performance threshold', async () => {
      const creator = await TestDataFactory.createUser();

      const organizationData: CreateOrganizationData = {
        name: 'Performance Test Org',
        slug: 'perf-test-org',
        description: 'Testing organization creation performance',
        settings: {},
      };

      const { duration } = await PerformanceTestHelpers.measureExecutionTime(() =>
        OrganizationService.create(organizationData, creator.id)
      );

      // Organization creation should complete within 500ms
      PerformanceTestHelpers.assertExecutionTime(duration, 500);
    });
  });

  describe('getById', () => {
    it('should return organization with basic information', async () => {
      const testOrg = await TestDataFactory.createOrganization({
        name: 'Test Organization',
        slug: 'test-org',
      });

      const organization = await OrganizationService.getById(testOrg.id);

      expect(organization).toMatchObject({
        id: testOrg.id,
        name: 'Test Organization',
        slug: 'test-org',
      });

      expect(organization!.members).toBeUndefined(); // Not included by default
      expect(organization!.workspaces).toBeUndefined(); // Not included by default
      expect(organization!._count).toBeDefined();
    });

    it('should include members when requested', async () => {
      const testOrg = await TestDataFactory.createOrganization();

      const organization = await OrganizationService.getById(
        testOrg.id,
        true, // includeMembers
        false
      );

      expect(organization!.members).toBeDefined();
      expect(organization!.members).toHaveLength(1);
      expect(organization!.members![0]).toMatchObject({
        role: 'owner',
        status: 'active',
      });
      expect(organization!.members![0].user).toBeDefined();
    });

    it('should include workspaces when requested', async () => {
      const testOrg = await TestDataFactory.createOrganization();
      await TestDataFactory.createWorkspace({ name: 'Test Workspace' }, testOrg.id);

      const organization = await OrganizationService.getById(
        testOrg.id,
        false,
        true // includeWorkspaces
      );

      expect(organization!.workspaces).toBeDefined();
      expect(organization!.workspaces).toHaveLength(1);
      expect(organization!.workspaces![0]).toMatchObject({
        name: 'Test Workspace',
      });
    });

    it('should return null for non-existent organization', async () => {
      const organization = await OrganizationService.getById('non-existent-id');
      expect(organization).toBeNull();
    });

    it('should return null for soft-deleted organization', async () => {
      const testOrg = await TestDataFactory.createOrganization();

      // Soft delete the organization
      await prisma.organization.update({
        where: { id: testOrg.id },
        data: { deletedAt: new Date() },
      });

      const organization = await OrganizationService.getById(testOrg.id);
      expect(organization).toBeNull();
    });
  });

  describe('getUserOrganizations', () => {
    it('should return paginated user organizations', async () => {
      const user = await TestDataFactory.createUser();

      // Create multiple organizations for the user
      const org1 = await TestDataFactory.createOrganization(
        { name: 'Alpha Organization' },
        user.id
      );
      const org2 = await TestDataFactory.createOrganization(
        { name: 'Beta Organization' },
        user.id
      );

      const result = await OrganizationService.getUserOrganizations(user.id, 1, 10);

      expect(result.data).toHaveLength(2);
      expect(result.data[0]).toMatchObject({ name: 'Alpha Organization' });
      expect(result.data[1]).toMatchObject({ name: 'Beta Organization' });

      expect(result.meta).toEqual({
        page: 1,
        limit: 10,
        total: 2,
        totalPages: 1,
        hasNext: false,
        hasPrev: false,
      });
    });

    it('should handle pagination correctly', async () => {
      const user = await TestDataFactory.createUser();

      // Create 5 organizations
      for (let i = 0; i < 5; i++) {
        await TestDataFactory.createOrganization(
          { name: `Organization ${i + 1}` },
          user.id
        );
      }

      // Get first page
      const page1 = await OrganizationService.getUserOrganizations(user.id, 1, 2);
      expect(page1.data).toHaveLength(2);
      expect(page1.meta.hasNext).toBe(true);
      expect(page1.meta.hasPrev).toBe(false);

      // Get second page
      const page2 = await OrganizationService.getUserOrganizations(user.id, 2, 2);
      expect(page2.data).toHaveLength(2);
      expect(page2.meta.hasNext).toBe(true);
      expect(page2.meta.hasPrev).toBe(true);

      // Get third page
      const page3 = await OrganizationService.getUserOrganizations(user.id, 3, 2);
      expect(page3.data).toHaveLength(1);
      expect(page3.meta.hasNext).toBe(false);
      expect(page3.meta.hasPrev).toBe(true);
    });

    it('should return empty result for user with no organizations', async () => {
      const user = await TestDataFactory.createUser();

      const result = await OrganizationService.getUserOrganizations(user.id);

      expect(result.data).toHaveLength(0);
      expect(result.meta.total).toBe(0);
    });

    it('should only return active memberships', async () => {
      const user = await TestDataFactory.createUser();
      const testOrg = await TestDataFactory.createOrganization({}, user.id);

      // Deactivate membership
      await prisma.organizationMember.update({
        where: {
          organizationId_userId: {
            organizationId: testOrg.id,
            userId: user.id,
          },
        },
        data: { status: 'inactive' },
      });

      const result = await OrganizationService.getUserOrganizations(user.id);
      expect(result.data).toHaveLength(0);
    });
  });

  describe('update', () => {
    it('should update organization successfully', async () => {
      const testOrg = await TestDataFactory.createOrganization({
        name: 'Original Name',
        slug: 'original-slug',
      });

      const updateData = {
        name: 'Updated Name',
        description: 'Updated description',
      };

      const updatedOrg = await OrganizationService.update(testOrg.id, updateData);

      expect(updatedOrg).toMatchObject({
        id: testOrg.id,
        name: 'Updated Name',
        slug: 'original-slug', // Should remain unchanged
        description: 'Updated description',
      });

      // Verify cache invalidation
      expect(mockRedis.deleteCachePattern).toHaveBeenCalledWith(`org:${testOrg.id}:*`);
      expect(mockRedis.deleteCachePattern).toHaveBeenCalledWith(`permissions:*:${testOrg.id}`);

      expect(mockLogger.business).toHaveBeenCalledWith(
        `Organization updated: ${updatedOrg.name}`,
        { organizationId: testOrg.id }
      );
    });

    it('should validate slug uniqueness when updating slug', async () => {
      const org1 = await TestDataFactory.createOrganization({ slug: 'org-1' });
      const org2 = await TestDataFactory.createOrganization({ slug: 'org-2' });

      await expect(
        OrganizationService.update(org2.id, { slug: 'org-1' })
      ).rejects.toThrow('Organization slug is already taken');
    });

    it('should allow updating slug to same value', async () => {
      const testOrg = await TestDataFactory.createOrganization({ slug: 'test-slug' });

      const updatedOrg = await OrganizationService.update(testOrg.id, {
        slug: 'test-slug',
        name: 'Updated Name',
      });

      expect(updatedOrg.slug).toBe('test-slug');
      expect(updatedOrg.name).toBe('Updated Name');
    });
  });

  describe('delete', () => {
    it('should soft delete organization', async () => {
      const testOrg = await TestDataFactory.createOrganization();

      await OrganizationService.delete(testOrg.id);

      // Verify soft deletion
      const deletedOrg = await prisma.organization.findUnique({
        where: { id: testOrg.id },
      });

      expect(deletedOrg!.deletedAt).not.toBeNull();

      // Verify cache invalidation
      expect(mockRedis.deleteCachePattern).toHaveBeenCalledWith(`org:${testOrg.id}:*`);

      expect(mockLogger.business).toHaveBeenCalledWith(
        'Organization deleted',
        { organizationId: testOrg.id }
      );
    });

    it('should handle non-existent organization gracefully', async () => {
      await expect(
        OrganizationService.delete('non-existent-id')
      ).rejects.toThrow();
    });
  });

  describe('inviteMember', () => {
    it('should invite new user successfully', async () => {
      const testOrg = await TestDataFactory.createOrganization();
      const owner = testOrg.members![0].userId;

      const membership = await OrganizationService.inviteMember(
        testOrg.id,
        'newuser@example.com',
        'member',
        owner
      );

      expect(membership).toMatchObject({
        organizationId: testOrg.id,
        role: 'member',
        status: 'invited', // New user not verified
        invitedBy: owner,
      });

      // Verify user was created
      const newUser = await prisma.user.findUnique({
        where: { email: 'newuser@example.com' },
      });
      expect(newUser).toBeDefined();
      expect(newUser!.emailVerified).toBe(false);

      expect(mockLogger.business).toHaveBeenCalledWith(
        'User invited to organization',
        expect.objectContaining({
          organizationId: testOrg.id,
          email: 'newuser@example.com',
          role: 'member',
          invitedBy: owner,
        })
      );
    });

    it('should invite existing verified user successfully', async () => {
      const testOrg = await TestDataFactory.createOrganization();
      const existingUser = await TestDataFactory.createUser({
        email: 'existing@example.com',
      });
      const owner = testOrg.members![0].userId;

      const membership = await OrganizationService.inviteMember(
        testOrg.id,
        'existing@example.com',
        'admin',
        owner
      );

      expect(membership).toMatchObject({
        organizationId: testOrg.id,
        userId: existingUser.id,
        role: 'admin',
        status: 'active', // Existing verified user
        invitedBy: owner,
      });

      expect(membership.joinedAt).not.toBeNull();
    });

    it('should reactivate inactive membership', async () => {
      const testOrg = await TestDataFactory.createOrganization();
      const existingUser = await TestDataFactory.createUser();
      const owner = testOrg.members![0].userId;

      // Create inactive membership
      await prisma.organizationMember.create({
        data: {
          organizationId: testOrg.id,
          userId: existingUser.id,
          role: 'member',
          status: 'inactive',
          invitedBy: owner,
        },
      });

      const membership = await OrganizationService.inviteMember(
        testOrg.id,
        existingUser.email,
        'admin',
        owner
      );

      expect(membership).toMatchObject({
        organizationId: testOrg.id,
        userId: existingUser.id,
        role: 'admin',
        status: 'active',
        invitedBy: owner,
      });
    });

    it('should throw error if user is already active member', async () => {
      const testOrg = await TestDataFactory.createOrganization();
      const existingUser = await TestDataFactory.createUser();
      const owner = testOrg.members![0].userId;

      // Add user as active member
      await OrganizationService.inviteMember(
        testOrg.id,
        existingUser.email,
        'member',
        owner
      );

      // Try to invite again
      await expect(
        OrganizationService.inviteMember(
          testOrg.id,
          existingUser.email,
          'admin',
          owner
        )
      ).rejects.toThrow('User is already a member of this organization');
    });
  });

  describe('removeMember', () => {
    it('should remove member successfully', async () => {
      const testOrg = await TestDataFactory.createOrganization();
      const memberUser = await TestDataFactory.createUser();
      const owner = testOrg.members![0].userId;

      // Add member
      await OrganizationService.inviteMember(
        testOrg.id,
        memberUser.email,
        'member',
        owner
      );

      // Remove member
      await OrganizationService.removeMember(testOrg.id, memberUser.id);

      // Verify membership is deleted
      const membership = await prisma.organizationMember.findUnique({
        where: {
          organizationId_userId: {
            organizationId: testOrg.id,
            userId: memberUser.id,
          },
        },
      });

      expect(membership).toBeNull();

      // Verify cache invalidation
      expect(mockRedis.deleteCachePattern).toHaveBeenCalledWith(
        `permissions:${memberUser.id}:${testOrg.id}`
      );

      expect(mockLogger.business).toHaveBeenCalledWith(
        'Member removed from organization',
        {
          organizationId: testOrg.id,
          userId: memberUser.id,
        }
      );
    });

    it('should prevent removing last owner', async () => {
      const testOrg = await TestDataFactory.createOrganization();
      const owner = testOrg.members![0].userId;

      await expect(
        OrganizationService.removeMember(testOrg.id, owner)
      ).rejects.toThrow('Cannot remove the last owner of the organization');
    });

    it('should allow removing owner if multiple owners exist', async () => {
      const testOrg = await TestDataFactory.createOrganization();
      const originalOwner = testOrg.members![0].userId;
      const secondOwner = await TestDataFactory.createUser();

      // Make second user an owner
      await OrganizationService.inviteMember(
        testOrg.id,
        secondOwner.email,
        'owner',
        originalOwner
      );

      // Should be able to remove one owner
      await OrganizationService.removeMember(testOrg.id, originalOwner);

      // Verify removal
      const membership = await prisma.organizationMember.findUnique({
        where: {
          organizationId_userId: {
            organizationId: testOrg.id,
            userId: originalOwner,
          },
        },
      });

      expect(membership).toBeNull();
    });
  });

  describe('updateMemberRole', () => {
    it('should update member role successfully', async () => {
      const testOrg = await TestDataFactory.createOrganization();
      const memberUser = await TestDataFactory.createUser();
      const owner = testOrg.members![0].userId;

      // Add member
      await OrganizationService.inviteMember(
        testOrg.id,
        memberUser.email,
        'member',
        owner
      );

      // Update role
      const updatedMember = await OrganizationService.updateMemberRole(
        testOrg.id,
        memberUser.id,
        'admin'
      );

      expect(updatedMember.role).toBe('admin');

      // Verify cache invalidation
      expect(mockRedis.deleteCachePattern).toHaveBeenCalledWith(
        `permissions:${memberUser.id}:${testOrg.id}`
      );

      expect(mockLogger.business).toHaveBeenCalledWith(
        'Member role updated',
        {
          organizationId: testOrg.id,
          userId: memberUser.id,
          newRole: 'admin',
        }
      );
    });

    it('should prevent changing role of last owner', async () => {
      const testOrg = await TestDataFactory.createOrganization();
      const owner = testOrg.members![0].userId;

      await expect(
        OrganizationService.updateMemberRole(testOrg.id, owner, 'admin')
      ).rejects.toThrow('Cannot change role of the last owner');
    });

    it('should allow changing owner role if multiple owners exist', async () => {
      const testOrg = await TestDataFactory.createOrganization();
      const originalOwner = testOrg.members![0].userId;
      const secondOwner = await TestDataFactory.createUser();

      // Make second user an owner
      await OrganizationService.inviteMember(
        testOrg.id,
        secondOwner.email,
        'owner',
        originalOwner
      );

      // Should be able to change one owner's role
      const updatedMember = await OrganizationService.updateMemberRole(
        testOrg.id,
        originalOwner,
        'admin'
      );

      expect(updatedMember.role).toBe('admin');
    });
  });

  describe('hasAccess', () => {
    it('should return true for active member', async () => {
      const testOrg = await TestDataFactory.createOrganization();
      const owner = testOrg.members![0].userId;

      const hasAccess = await OrganizationService.hasAccess(testOrg.id, owner);
      expect(hasAccess).toBe(true);
    });

    it('should return false for non-member', async () => {
      const testOrg = await TestDataFactory.createOrganization();
      const nonMember = await TestDataFactory.createUser();

      const hasAccess = await OrganizationService.hasAccess(testOrg.id, nonMember.id);
      expect(hasAccess).toBe(false);
    });

    it('should return false for inactive member', async () => {
      const testOrg = await TestDataFactory.createOrganization();
      const memberUser = await TestDataFactory.createUser();
      const owner = testOrg.members![0].userId;

      // Add member
      await OrganizationService.inviteMember(
        testOrg.id,
        memberUser.email,
        'member',
        owner
      );

      // Deactivate membership
      await prisma.organizationMember.update({
        where: {
          organizationId_userId: {
            organizationId: testOrg.id,
            userId: memberUser.id,
          },
        },
        data: { status: 'inactive' },
      });

      const hasAccess = await OrganizationService.hasAccess(testOrg.id, memberUser.id);
      expect(hasAccess).toBe(false);
    });

    it('should handle database errors gracefully', async () => {
      const mockFindUnique = jest.spyOn(prisma.organizationMember, 'findUnique')
        .mockRejectedValue(new Error('Database error'));

      const hasAccess = await OrganizationService.hasAccess('org-id', 'user-id');
      expect(hasAccess).toBe(false);

      expect(mockLogger.error).toHaveBeenCalledWith(
        'Failed to check organization access',
        expect.any(Error)
      );

      mockFindUnique.mockRestore();
    });
  });

  describe('getStatistics', () => {
    it('should return organization statistics', async () => {
      const hierarchy = await TestDataFactory.createTestHierarchy({
        users: 5,
        workspaces: 2,
        boards: 3,
        items: 20,
      });

      const stats = await OrganizationService.getStatistics(hierarchy.organization.id);

      expect(stats).toEqual({
        totalMembers: expect.any(Number),
        totalWorkspaces: expect.any(Number),
        totalBoards: expect.any(Number),
        totalItems: expect.any(Number),
        activeUsers30d: expect.any(Number),
      });

      expect(stats.totalMembers).toBeGreaterThan(0);
      expect(stats.totalWorkspaces).toBeGreaterThan(0);
      expect(stats.totalBoards).toBeGreaterThan(0);
      expect(stats.totalItems).toBeGreaterThan(0);
    });

    it('should handle database errors in statistics', async () => {
      const mockQueryRaw = jest.spyOn(prisma, '$queryRaw').mockRejectedValue(
        new Error('Database query failed')
      );

      await expect(
        OrganizationService.getStatistics('org-id')
      ).rejects.toThrow('Database query failed');

      expect(mockLogger.error).toHaveBeenCalledWith(
        'Failed to get organization statistics',
        expect.any(Error)
      );

      mockQueryRaw.mockRestore();
    });
  });

  describe('getMembers', () => {
    it('should return paginated organization members', async () => {
      const testOrg = await TestDataFactory.createOrganization();
      const owner = testOrg.members![0].userId;

      // Add multiple members
      for (let i = 0; i < 5; i++) {
        const user = await TestDataFactory.createUser({
          email: `member${i}@example.com`,
        });
        await OrganizationService.inviteMember(
          testOrg.id,
          user.email,
          'member',
          owner
        );
      }

      const result = await OrganizationService.getMembers(testOrg.id, 1, 3);

      expect(result.data).toHaveLength(3);
      expect(result.meta).toEqual({
        page: 1,
        limit: 3,
        total: 6, // 5 members + 1 owner
        totalPages: 2,
        hasNext: true,
        hasPrev: false,
      });

      // Verify each member has user data
      result.data.forEach(member => {
        expect(member.user).toBeDefined();
        expect(member.status).toBe('active');
      });
    });

    it('should order members correctly (owners first)', async () => {
      const testOrg = await TestDataFactory.createOrganization();
      const originalOwner = testOrg.members![0].userId;

      // Add another owner and some members
      const secondOwner = await TestDataFactory.createUser({
        firstName: 'Alice',
        email: 'alice@example.com',
      });
      await OrganizationService.inviteMember(
        testOrg.id,
        secondOwner.email,
        'owner',
        originalOwner
      );

      const member = await TestDataFactory.createUser({
        firstName: 'Bob',
        email: 'bob@example.com',
      });
      await OrganizationService.inviteMember(
        testOrg.id,
        member.email,
        'member',
        originalOwner
      );

      const result = await OrganizationService.getMembers(testOrg.id, 1, 10);

      // First two should be owners
      expect(result.data[0].role).toBe('owner');
      expect(result.data[1].role).toBe('owner');

      // Last should be member
      expect(result.data[2].role).toBe('member');
    });
  });

  describe('Performance Tests', () => {
    it('should handle large organization queries efficiently', async () => {
      const hierarchy = await TestDataFactory.createTestHierarchy({
        users: 100,
        workspaces: 10,
        boards: 50,
        items: 1000,
      });

      const { duration } = await PerformanceTestHelpers.measureExecutionTime(() =>
        OrganizationService.getById(hierarchy.organization.id, true, true)
      );

      // Should complete within 1 second even with large data
      PerformanceTestHelpers.assertExecutionTime(duration, 1000);
    });

    it('should handle pagination efficiently with large member lists', async () => {
      const testOrg = await TestDataFactory.createOrganization();
      const owner = testOrg.members![0].userId;

      // Create 100 members
      const memberPromises = [];
      for (let i = 0; i < 100; i++) {
        const user = TestDataFactory.createUser({
          email: `member${i}@example.com`,
        });
        memberPromises.push(user);
      }
      const members = await Promise.all(memberPromises);

      const invitePromises = members.map(member =>
        OrganizationService.inviteMember(
          testOrg.id,
          member.email,
          'member',
          owner
        )
      );
      await Promise.all(invitePromises);

      const { duration } = await PerformanceTestHelpers.measureExecutionTime(() =>
        OrganizationService.getMembers(testOrg.id, 1, 20)
      );

      // Pagination should be fast even with many members
      PerformanceTestHelpers.assertExecutionTime(duration, 500);
    });
  });
});