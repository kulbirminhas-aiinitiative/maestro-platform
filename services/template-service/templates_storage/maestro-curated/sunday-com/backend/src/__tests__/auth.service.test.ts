import { AuthService } from '@/services/auth.service';
import { prisma } from '@/config/database';
import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { config } from '@/config';

// Mock Redis service
jest.mock('@/config/redis', () => ({
  RedisService: {
    setCache: jest.fn(),
    getCache: jest.fn(),
    deleteCache: jest.fn(),
  },
}));

describe('AuthService', () => {
  describe('register', () => {
    it('should register a new user successfully', async () => {
      const registerData = {
        email: 'test@example.com',
        password: 'Password123!',
        firstName: 'Test',
        lastName: 'User',
      };

      // Mock prisma findUnique to return null (user doesn't exist)
      const mockFindUnique = jest.spyOn(prisma.user, 'findUnique').mockResolvedValue(null);

      // Mock prisma create
      const mockCreate = jest.spyOn(prisma.user, 'create').mockResolvedValue({
        id: 'user-id',
        email: registerData.email,
        firstName: registerData.firstName,
        lastName: registerData.lastName,
        passwordHash: 'hashed-password',
        emailVerified: false,
        avatarUrl: null,
        timezone: 'UTC',
        locale: 'en',
        settings: {},
        lastLoginAt: null,
        createdAt: new Date(),
        updatedAt: new Date(),
        deletedAt: null,
      });

      const result = await AuthService.register(registerData);

      expect(mockFindUnique).toHaveBeenCalledWith({
        where: { email: registerData.email.toLowerCase() },
      });

      expect(mockCreate).toHaveBeenCalledWith({
        data: {
          email: registerData.email.toLowerCase(),
          passwordHash: expect.any(String),
          firstName: registerData.firstName,
          lastName: registerData.lastName,
          emailVerified: false,
        },
      });

      expect(result.user).toEqual({
        id: 'user-id',
        email: registerData.email,
        firstName: registerData.firstName,
        lastName: registerData.lastName,
        avatarUrl: undefined,
        organizations: [],
      });

      expect(result.tokens).toHaveProperty('accessToken');
      expect(result.tokens).toHaveProperty('refreshToken');
      expect(result.tokens).toHaveProperty('expiresIn');

      // Cleanup mocks
      mockFindUnique.mockRestore();
      mockCreate.mockRestore();
    });

    it('should throw error if user already exists', async () => {
      const registerData = {
        email: 'existing@example.com',
        password: 'Password123!',
        firstName: 'Test',
        lastName: 'User',
      };

      // Mock existing user
      const mockFindUnique = jest.spyOn(prisma.user, 'findUnique').mockResolvedValue({
        id: 'existing-user-id',
        email: registerData.email,
        firstName: 'Existing',
        lastName: 'User',
        passwordHash: 'hashed-password',
        emailVerified: true,
        avatarUrl: null,
        timezone: 'UTC',
        locale: 'en',
        settings: {},
        lastLoginAt: null,
        createdAt: new Date(),
        updatedAt: new Date(),
        deletedAt: null,
      });

      await expect(AuthService.register(registerData)).rejects.toThrow(
        'User already exists with this email'
      );

      mockFindUnique.mockRestore();
    });
  });

  describe('login', () => {
    it('should login user with valid credentials', async () => {
      const loginData = {
        email: 'test@example.com',
        password: 'Password123!',
      };

      const hashedPassword = await bcrypt.hash(loginData.password, 12);

      const mockUser = {
        id: 'user-id',
        email: loginData.email,
        firstName: 'Test',
        lastName: 'User',
        passwordHash: hashedPassword,
        emailVerified: true,
        avatarUrl: null,
        timezone: 'UTC',
        locale: 'en',
        settings: {},
        lastLoginAt: null,
        createdAt: new Date(),
        updatedAt: new Date(),
        deletedAt: null,
        organizationMemberships: [],
      };

      const mockFindUnique = jest.spyOn(prisma.user, 'findUnique').mockResolvedValue(mockUser);
      const mockUpdate = jest.spyOn(prisma.user, 'update').mockResolvedValue(mockUser);

      const result = await AuthService.login(loginData);

      expect(result.user).toEqual({
        id: 'user-id',
        email: loginData.email,
        firstName: 'Test',
        lastName: 'User',
        avatarUrl: undefined,
        organizations: [],
      });

      expect(result.tokens).toHaveProperty('accessToken');
      expect(result.tokens).toHaveProperty('refreshToken');

      mockFindUnique.mockRestore();
      mockUpdate.mockRestore();
    });

    it('should throw error for invalid password', async () => {
      const loginData = {
        email: 'test@example.com',
        password: 'WrongPassword',
      };

      const hashedPassword = await bcrypt.hash('CorrectPassword', 12);

      const mockUser = {
        id: 'user-id',
        email: loginData.email,
        firstName: 'Test',
        lastName: 'User',
        passwordHash: hashedPassword,
        emailVerified: true,
        avatarUrl: null,
        timezone: 'UTC',
        locale: 'en',
        settings: {},
        lastLoginAt: null,
        createdAt: new Date(),
        updatedAt: new Date(),
        deletedAt: null,
        organizationMemberships: [],
      };

      const mockFindUnique = jest.spyOn(prisma.user, 'findUnique').mockResolvedValue(mockUser);

      await expect(AuthService.login(loginData)).rejects.toThrow('Invalid email or password');

      mockFindUnique.mockRestore();
    });

    it('should throw error for non-existent user', async () => {
      const loginData = {
        email: 'nonexistent@example.com',
        password: 'Password123!',
      };

      const mockFindUnique = jest.spyOn(prisma.user, 'findUnique').mockResolvedValue(null);

      await expect(AuthService.login(loginData)).rejects.toThrow('Invalid email or password');

      mockFindUnique.mockRestore();
    });
  });

  describe('refreshToken', () => {
    it('should refresh token with valid refresh token', async () => {
      const userId = 'user-id';
      const email = 'test@example.com';

      // Create a valid refresh token
      const refreshPayload = {
        sub: userId,
        email,
        iat: Math.floor(Date.now() / 1000),
        exp: Math.floor(Date.now() / 1000) + 7 * 24 * 60 * 60, // 7 days
      };

      const validRefreshToken = jwt.sign(refreshPayload, config.jwt.refreshSecret);

      const mockUser = {
        id: userId,
        email,
        firstName: 'Test',
        lastName: 'User',
        passwordHash: 'hashed-password',
        emailVerified: true,
        avatarUrl: null,
        timezone: 'UTC',
        locale: 'en',
        settings: {},
        lastLoginAt: null,
        createdAt: new Date(),
        updatedAt: new Date(),
        deletedAt: null,
      };

      const mockFindUnique = jest.spyOn(prisma.user, 'findUnique').mockResolvedValue(mockUser);

      const result = await AuthService.refreshToken(validRefreshToken);

      expect(result).toHaveProperty('accessToken');
      expect(result).toHaveProperty('refreshToken');
      expect(result).toHaveProperty('expiresIn');

      mockFindUnique.mockRestore();
    });

    it('should throw error for invalid refresh token', async () => {
      const invalidRefreshToken = 'invalid-token';

      await expect(AuthService.refreshToken(invalidRefreshToken)).rejects.toThrow();
    });
  });

  describe('changePassword', () => {
    it('should change password with valid current password', async () => {
      const userId = 'user-id';
      const currentPassword = 'OldPassword123!';
      const newPassword = 'NewPassword123!';

      const hashedCurrentPassword = await bcrypt.hash(currentPassword, 12);

      const mockUser = {
        id: userId,
        email: 'test@example.com',
        firstName: 'Test',
        lastName: 'User',
        passwordHash: hashedCurrentPassword,
        emailVerified: true,
        avatarUrl: null,
        timezone: 'UTC',
        locale: 'en',
        settings: {},
        lastLoginAt: null,
        createdAt: new Date(),
        updatedAt: new Date(),
        deletedAt: null,
      };

      const mockFindUnique = jest.spyOn(prisma.user, 'findUnique').mockResolvedValue(mockUser);
      const mockUpdate = jest.spyOn(prisma.user, 'update').mockResolvedValue(mockUser);

      await AuthService.changePassword(userId, currentPassword, newPassword);

      expect(mockUpdate).toHaveBeenCalledWith({
        where: { id: userId },
        data: { passwordHash: expect.any(String) },
      });

      mockFindUnique.mockRestore();
      mockUpdate.mockRestore();
    });

    it('should throw error for incorrect current password', async () => {
      const userId = 'user-id';
      const currentPassword = 'WrongPassword';
      const newPassword = 'NewPassword123!';

      const hashedCurrentPassword = await bcrypt.hash('CorrectPassword', 12);

      const mockUser = {
        id: userId,
        email: 'test@example.com',
        firstName: 'Test',
        lastName: 'User',
        passwordHash: hashedCurrentPassword,
        emailVerified: true,
        avatarUrl: null,
        timezone: 'UTC',
        locale: 'en',
        settings: {},
        lastLoginAt: null,
        createdAt: new Date(),
        updatedAt: new Date(),
        deletedAt: null,
      };

      const mockFindUnique = jest.spyOn(prisma.user, 'findUnique').mockResolvedValue(mockUser);

      await expect(AuthService.changePassword(userId, currentPassword, newPassword)).rejects.toThrow(
        'Current password is incorrect'
      );

      mockFindUnique.mockRestore();
    });
  });
});