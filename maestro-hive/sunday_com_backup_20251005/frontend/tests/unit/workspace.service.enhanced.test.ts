/**
 * Enhanced Unit Tests for Workspace Service
 * Demonstrates comprehensive testing patterns for Sunday.com platform
 */

import { describe, it, expect, beforeEach, afterEach, jest } from '@jest/globals';
import { WorkspaceService } from '../../backend/src/services/workspace.service';
import { PrismaClient } from '@prisma/client';
import { createMockContext, MockContext } from '../helpers/mock-context';
import { TestDataFactory } from '../helpers/test-data-factory';

// Mock Prisma
jest.mock('@prisma/client');

describe('WorkspaceService', () => {
  let mockCtx: MockContext;
  let service: WorkspaceService;

  beforeEach(() => {
    mockCtx = createMockContext();
    service = new WorkspaceService(mockCtx.prisma);
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  describe('createWorkspace', () => {
    it('should create workspace with valid data', async () => {
      // Arrange
      const userId = 'user-123';
      const workspaceData = {
        name: 'Test Workspace',
        description: 'A test workspace for development',
      };

      const expectedWorkspace = TestDataFactory.createWorkspace({
        ...workspaceData,
        ownerId: userId,
      });

      mockCtx.prisma.workspace.create.mockResolvedValue(expectedWorkspace);

      // Act
      const result = await service.createWorkspace(workspaceData, userId);

      // Assert
      expect(result).toEqual(expectedWorkspace);
      expect(mockCtx.prisma.workspace.create).toHaveBeenCalledWith({
        data: {
          name: workspaceData.name,
          description: workspaceData.description,
          ownerId: userId,
          members: {
            create: {
              userId: userId,
              role: 'OWNER',
              joinedAt: expect.any(Date),
            },
          },
        },
        include: {
          members: {
            include: {
              user: {
                select: {
                  id: true,
                  email: true,
                  firstName: true,
                  lastName: true,
                  avatar: true,
                },
              },
            },
          },
          boards: {
            select: {
              id: true,
              name: true,
              description: true,
              createdAt: true,
              updatedAt: true,
            },
          },
          _count: {
            select: {
              boards: true,
              members: true,
            },
          },
        },
      });
    });

    it('should validate workspace name requirements', async () => {
      // Arrange
      const userId = 'user-123';
      const invalidWorkspaceData = {
        name: '', // Empty name
        description: 'Valid description',
      };

      // Act & Assert
      await expect(
        service.createWorkspace(invalidWorkspaceData, userId)
      ).rejects.toThrow('Workspace name is required and must be between 1-100 characters');
    });

    it('should handle name length validation', async () => {
      // Arrange
      const userId = 'user-123';
      const longName = 'a'.repeat(101); // Exceeds 100 character limit

      const invalidWorkspaceData = {
        name: longName,
        description: 'Valid description',
      };

      // Act & Assert
      await expect(
        service.createWorkspace(invalidWorkspaceData, userId)
      ).rejects.toThrow('Workspace name is required and must be between 1-100 characters');
    });

    it('should handle database errors gracefully', async () => {
      // Arrange
      const userId = 'user-123';
      const workspaceData = {
        name: 'Test Workspace',
        description: 'A test workspace',
      };

      mockCtx.prisma.workspace.create.mockRejectedValue(
        new Error('Database connection failed')
      );

      // Act & Assert
      await expect(
        service.createWorkspace(workspaceData, userId)
      ).rejects.toThrow('Failed to create workspace: Database connection failed');

      expect(mockCtx.prisma.workspace.create).toHaveBeenCalledTimes(1);
    });

    it('should create workspace with minimal required data', async () => {
      // Arrange
      const userId = 'user-123';
      const minimalData = {
        name: 'Minimal Workspace',
      };

      const expectedWorkspace = TestDataFactory.createWorkspace({
        name: minimalData.name,
        description: null,
        ownerId: userId,
      });

      mockCtx.prisma.workspace.create.mockResolvedValue(expectedWorkspace);

      // Act
      const result = await service.createWorkspace(minimalData, userId);

      // Assert
      expect(result).toEqual(expectedWorkspace);
      expect(mockCtx.prisma.workspace.create).toHaveBeenCalledWith({
        data: {
          name: minimalData.name,
          description: undefined,
          ownerId: userId,
          members: {
            create: {
              userId: userId,
              role: 'OWNER',
              joinedAt: expect.any(Date),
            },
          },
        },
        include: expect.any(Object),
      });
    });
  });

  describe('getWorkspaceById', () => {
    it('should return workspace when found', async () => {
      // Arrange
      const workspaceId = 'workspace-123';
      const userId = 'user-123';
      const expectedWorkspace = TestDataFactory.createWorkspace({ id: workspaceId });

      mockCtx.prisma.workspace.findFirst.mockResolvedValue(expectedWorkspace);

      // Act
      const result = await service.getWorkspaceById(workspaceId, userId);

      // Assert
      expect(result).toEqual(expectedWorkspace);
      expect(mockCtx.prisma.workspace.findFirst).toHaveBeenCalledWith({
        where: {
          id: workspaceId,
          members: {
            some: {
              userId: userId,
            },
          },
        },
        include: {
          members: {
            include: {
              user: {
                select: {
                  id: true,
                  email: true,
                  firstName: true,
                  lastName: true,
                  avatar: true,
                },
              },
            },
          },
          boards: {
            select: {
              id: true,
              name: true,
              description: true,
              createdAt: true,
              updatedAt: true,
            },
          },
          _count: {
            select: {
              boards: true,
              members: true,
            },
          },
        },
      });
    });

    it('should return null when workspace not found', async () => {
      // Arrange
      const workspaceId = 'nonexistent-workspace';
      const userId = 'user-123';

      mockCtx.prisma.workspace.findFirst.mockResolvedValue(null);

      // Act
      const result = await service.getWorkspaceById(workspaceId, userId);

      // Assert
      expect(result).toBeNull();
    });

    it('should return null when user has no access to workspace', async () => {
      // Arrange
      const workspaceId = 'workspace-123';
      const userId = 'unauthorized-user';

      mockCtx.prisma.workspace.findFirst.mockResolvedValue(null);

      // Act
      const result = await service.getWorkspaceById(workspaceId, userId);

      // Assert
      expect(result).toBeNull();
      expect(mockCtx.prisma.workspace.findFirst).toHaveBeenCalledWith({
        where: {
          id: workspaceId,
          members: {
            some: {
              userId: userId,
            },
          },
        },
        include: expect.any(Object),
      });
    });
  });

  describe('updateWorkspace', () => {
    it('should update workspace successfully', async () => {
      // Arrange
      const workspaceId = 'workspace-123';
      const userId = 'user-123';
      const updateData = {
        name: 'Updated Workspace Name',
        description: 'Updated description',
      };

      const existingWorkspace = TestDataFactory.createWorkspace({
        id: workspaceId,
        ownerId: userId,
      });

      const updatedWorkspace = {
        ...existingWorkspace,
        ...updateData,
        updatedAt: new Date(),
      };

      mockCtx.prisma.workspace.findFirst.mockResolvedValue(existingWorkspace);
      mockCtx.prisma.workspace.update.mockResolvedValue(updatedWorkspace);

      // Act
      const result = await service.updateWorkspace(workspaceId, updateData, userId);

      // Assert
      expect(result).toEqual(updatedWorkspace);
      expect(mockCtx.prisma.workspace.update).toHaveBeenCalledWith({
        where: { id: workspaceId },
        data: {
          name: updateData.name,
          description: updateData.description,
          updatedAt: expect.any(Date),
        },
        include: expect.any(Object),
      });
    });

    it('should throw error when workspace not found', async () => {
      // Arrange
      const workspaceId = 'nonexistent-workspace';
      const userId = 'user-123';
      const updateData = { name: 'Updated Name' };

      mockCtx.prisma.workspace.findFirst.mockResolvedValue(null);

      // Act & Assert
      await expect(
        service.updateWorkspace(workspaceId, updateData, userId)
      ).rejects.toThrow('Workspace not found or access denied');

      expect(mockCtx.prisma.workspace.update).not.toHaveBeenCalled();
    });

    it('should throw error when user lacks admin permissions', async () => {
      // Arrange
      const workspaceId = 'workspace-123';
      const userId = 'user-123';
      const updateData = { name: 'Updated Name' };

      const workspace = TestDataFactory.createWorkspace({
        id: workspaceId,
        ownerId: 'different-owner',
      });

      // Mock member with MEMBER role (not ADMIN or OWNER)
      mockCtx.prisma.workspace.findFirst.mockResolvedValue({
        ...workspace,
        members: [
          {
            userId: userId,
            role: 'MEMBER',
            joinedAt: new Date(),
          },
        ],
      });

      // Act & Assert
      await expect(
        service.updateWorkspace(workspaceId, updateData, userId)
      ).rejects.toThrow('Insufficient permissions to update workspace');

      expect(mockCtx.prisma.workspace.update).not.toHaveBeenCalled();
    });

    it('should validate update data', async () => {
      // Arrange
      const workspaceId = 'workspace-123';
      const userId = 'user-123';
      const invalidUpdateData = {
        name: '', // Empty name
      };

      // Act & Assert
      await expect(
        service.updateWorkspace(workspaceId, invalidUpdateData, userId)
      ).rejects.toThrow('Workspace name is required and must be between 1-100 characters');

      expect(mockCtx.prisma.workspace.findFirst).not.toHaveBeenCalled();
    });
  });

  describe('deleteWorkspace', () => {
    it('should delete workspace successfully when user is owner', async () => {
      // Arrange
      const workspaceId = 'workspace-123';
      const userId = 'user-123';

      const workspace = TestDataFactory.createWorkspace({
        id: workspaceId,
        ownerId: userId,
      });

      mockCtx.prisma.workspace.findFirst.mockResolvedValue(workspace);
      mockCtx.prisma.workspace.delete.mockResolvedValue(workspace);

      // Act
      const result = await service.deleteWorkspace(workspaceId, userId);

      // Assert
      expect(result).toBe(true);
      expect(mockCtx.prisma.workspace.delete).toHaveBeenCalledWith({
        where: { id: workspaceId },
      });
    });

    it('should throw error when workspace not found', async () => {
      // Arrange
      const workspaceId = 'nonexistent-workspace';
      const userId = 'user-123';

      mockCtx.prisma.workspace.findFirst.mockResolvedValue(null);

      // Act & Assert
      await expect(
        service.deleteWorkspace(workspaceId, userId)
      ).rejects.toThrow('Workspace not found or access denied');

      expect(mockCtx.prisma.workspace.delete).not.toHaveBeenCalled();
    });

    it('should throw error when user is not owner', async () => {
      // Arrange
      const workspaceId = 'workspace-123';
      const userId = 'user-123';

      const workspace = TestDataFactory.createWorkspace({
        id: workspaceId,
        ownerId: 'different-owner',
      });

      mockCtx.prisma.workspace.findFirst.mockResolvedValue(workspace);

      // Act & Assert
      await expect(
        service.deleteWorkspace(workspaceId, userId)
      ).rejects.toThrow('Only workspace owner can delete the workspace');

      expect(mockCtx.prisma.workspace.delete).not.toHaveBeenCalled();
    });

    it('should handle database errors during deletion', async () => {
      // Arrange
      const workspaceId = 'workspace-123';
      const userId = 'user-123';

      const workspace = TestDataFactory.createWorkspace({
        id: workspaceId,
        ownerId: userId,
      });

      mockCtx.prisma.workspace.findFirst.mockResolvedValue(workspace);
      mockCtx.prisma.workspace.delete.mockRejectedValue(
        new Error('Foreign key constraint violation')
      );

      // Act & Assert
      await expect(
        service.deleteWorkspace(workspaceId, userId)
      ).rejects.toThrow('Failed to delete workspace: Foreign key constraint violation');
    });
  });

  describe('addMemberToWorkspace', () => {
    it('should add member successfully', async () => {
      // Arrange
      const workspaceId = 'workspace-123';
      const inviterId = 'inviter-123';
      const memberEmail = 'newmember@example.com';
      const role = 'MEMBER';

      const workspace = TestDataFactory.createWorkspace({
        id: workspaceId,
        ownerId: inviterId,
      });

      const newUser = TestDataFactory.createUser({
        email: memberEmail,
      });

      const memberData = {
        id: 'member-123',
        workspaceId,
        userId: newUser.id,
        role,
        joinedAt: new Date(),
        user: newUser,
      };

      mockCtx.prisma.workspace.findFirst.mockResolvedValue(workspace);
      mockCtx.prisma.user.findUnique.mockResolvedValue(newUser);
      mockCtx.prisma.workspaceMember.findUnique.mockResolvedValue(null); // Not already a member
      mockCtx.prisma.workspaceMember.create.mockResolvedValue(memberData);

      // Act
      const result = await service.addMemberToWorkspace(
        workspaceId,
        memberEmail,
        role,
        inviterId
      );

      // Assert
      expect(result).toEqual(memberData);
      expect(mockCtx.prisma.workspaceMember.create).toHaveBeenCalledWith({
        data: {
          workspaceId,
          userId: newUser.id,
          role,
          joinedAt: expect.any(Date),
        },
        include: {
          user: {
            select: {
              id: true,
              email: true,
              firstName: true,
              lastName: true,
              avatar: true,
            },
          },
        },
      });
    });

    it('should throw error when user not found', async () => {
      // Arrange
      const workspaceId = 'workspace-123';
      const inviterId = 'inviter-123';
      const memberEmail = 'nonexistent@example.com';
      const role = 'MEMBER';

      const workspace = TestDataFactory.createWorkspace({
        id: workspaceId,
        ownerId: inviterId,
      });

      mockCtx.prisma.workspace.findFirst.mockResolvedValue(workspace);
      mockCtx.prisma.user.findUnique.mockResolvedValue(null);

      // Act & Assert
      await expect(
        service.addMemberToWorkspace(workspaceId, memberEmail, role, inviterId)
      ).rejects.toThrow('User with email nonexistent@example.com not found');
    });

    it('should throw error when user already a member', async () => {
      // Arrange
      const workspaceId = 'workspace-123';
      const inviterId = 'inviter-123';
      const memberEmail = 'existing@example.com';
      const role = 'MEMBER';

      const workspace = TestDataFactory.createWorkspace({
        id: workspaceId,
        ownerId: inviterId,
      });

      const existingUser = TestDataFactory.createUser({
        email: memberEmail,
      });

      const existingMember = {
        id: 'existing-member',
        workspaceId,
        userId: existingUser.id,
        role: 'MEMBER',
      };

      mockCtx.prisma.workspace.findFirst.mockResolvedValue(workspace);
      mockCtx.prisma.user.findUnique.mockResolvedValue(existingUser);
      mockCtx.prisma.workspaceMember.findUnique.mockResolvedValue(existingMember);

      // Act & Assert
      await expect(
        service.addMemberToWorkspace(workspaceId, memberEmail, role, inviterId)
      ).rejects.toThrow('User is already a member of this workspace');
    });

    it('should throw error when inviter lacks admin permissions', async () => {
      // Arrange
      const workspaceId = 'workspace-123';
      const inviterId = 'inviter-123';
      const memberEmail = 'newmember@example.com';
      const role = 'MEMBER';

      const workspace = TestDataFactory.createWorkspace({
        id: workspaceId,
        ownerId: 'different-owner',
      });

      // Mock inviter as MEMBER (not ADMIN or OWNER)
      mockCtx.prisma.workspace.findFirst.mockResolvedValue({
        ...workspace,
        members: [
          {
            userId: inviterId,
            role: 'MEMBER',
          },
        ],
      });

      // Act & Assert
      await expect(
        service.addMemberToWorkspace(workspaceId, memberEmail, role, inviterId)
      ).rejects.toThrow('Insufficient permissions to add members');
    });
  });

  describe('getUserWorkspaces', () => {
    it('should return user workspaces', async () => {
      // Arrange
      const userId = 'user-123';
      const workspaces = [
        TestDataFactory.createWorkspace({ name: 'Workspace 1' }),
        TestDataFactory.createWorkspace({ name: 'Workspace 2' }),
      ];

      mockCtx.prisma.workspace.findMany.mockResolvedValue(workspaces);

      // Act
      const result = await service.getUserWorkspaces(userId);

      // Assert
      expect(result).toEqual(workspaces);
      expect(mockCtx.prisma.workspace.findMany).toHaveBeenCalledWith({
        where: {
          members: {
            some: {
              userId: userId,
            },
          },
        },
        include: {
          members: {
            include: {
              user: {
                select: {
                  id: true,
                  email: true,
                  firstName: true,
                  lastName: true,
                  avatar: true,
                },
              },
            },
          },
          _count: {
            select: {
              boards: true,
              members: true,
            },
          },
        },
        orderBy: {
          updatedAt: 'desc',
        },
      });
    });

    it('should return empty array when user has no workspaces', async () => {
      // Arrange
      const userId = 'user-without-workspaces';

      mockCtx.prisma.workspace.findMany.mockResolvedValue([]);

      // Act
      const result = await service.getUserWorkspaces(userId);

      // Assert
      expect(result).toEqual([]);
    });

    it('should handle database errors', async () => {
      // Arrange
      const userId = 'user-123';

      mockCtx.prisma.workspace.findMany.mockRejectedValue(
        new Error('Database query failed')
      );

      // Act & Assert
      await expect(
        service.getUserWorkspaces(userId)
      ).rejects.toThrow('Failed to fetch user workspaces: Database query failed');
    });
  });
});