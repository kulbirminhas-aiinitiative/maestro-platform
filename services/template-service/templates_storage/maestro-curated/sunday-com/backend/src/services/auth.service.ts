import bcrypt from 'bcryptjs';
import jwt from 'jsonwebtoken';
import { nanoid } from 'nanoid';
import { prisma } from '@/config/database';
import { RedisService } from '@/config/redis';
import { Logger } from '@/config/logger';
import { config } from '@/config';
import {
  AuthTokens,
  AuthUser,
  JwtPayload,
  LoginCredentials,
  RegisterData,
} from '@/types';

export class AuthService {
  /**
   * Register a new user
   */
  static async register(data: RegisterData): Promise<{ user: AuthUser; tokens: AuthTokens }> {
    try {
      // Check if user already exists
      const existingUser = await prisma.user.findUnique({
        where: { email: data.email.toLowerCase() },
      });

      if (existingUser) {
        throw new Error('User already exists with this email');
      }

      // Hash password
      const passwordHash = await bcrypt.hash(data.password, config.security.bcryptRounds);

      // Create user
      const user = await prisma.user.create({
        data: {
          email: data.email.toLowerCase(),
          passwordHash,
          firstName: data.firstName,
          lastName: data.lastName,
          emailVerified: false,
        },
      });

      Logger.auth(`User registered: ${user.email}`, { userId: user.id });

      // Generate tokens
      const tokens = await this.generateTokens(user.id, user.email);

      // Transform user for response
      const authUser: AuthUser = {
        id: user.id,
        email: user.email,
        firstName: user.firstName || undefined,
        lastName: user.lastName || undefined,
        avatarUrl: user.avatarUrl || undefined,
        organizations: [],
      };

      return { user: authUser, tokens };
    } catch (error) {
      Logger.error('Registration failed', error as Error);
      throw error;
    }
  }

  /**
   * Login user with email and password
   */
  static async login(credentials: LoginCredentials): Promise<{ user: AuthUser; tokens: AuthTokens }> {
    try {
      // Find user by email
      const user = await prisma.user.findUnique({
        where: { email: credentials.email.toLowerCase() },
        include: {
          organizationMemberships: {
            include: {
              organization: true,
            },
            where: {
              status: 'active',
            },
          },
        },
      });

      if (!user || user.deletedAt) {
        throw new Error('Invalid email or password');
      }

      // Check password
      if (!user.passwordHash) {
        throw new Error('Please use single sign-on to login');
      }

      const isValidPassword = await bcrypt.compare(credentials.password, user.passwordHash);
      if (!isValidPassword) {
        throw new Error('Invalid email or password');
      }

      // Update last login
      await prisma.user.update({
        where: { id: user.id },
        data: { lastLoginAt: new Date() },
      });

      Logger.auth(`User logged in: ${user.email}`, { userId: user.id });

      // Generate tokens
      const tokens = await this.generateTokens(user.id, user.email);

      // Transform user for response
      const authUser: AuthUser = {
        id: user.id,
        email: user.email,
        firstName: user.firstName || undefined,
        lastName: user.lastName || undefined,
        avatarUrl: user.avatarUrl || undefined,
        organizations: user.organizationMemberships.map((membership) => ({
          id: membership.organization.id,
          name: membership.organization.name,
          role: membership.role,
          permissions: [],
        })),
      };

      return { user: authUser, tokens };
    } catch (error) {
      Logger.error('Login failed', error as Error);
      throw error;
    }
  }

  /**
   * Refresh access token using refresh token
   */
  static async refreshToken(refreshToken: string): Promise<AuthTokens> {
    try {
      // Verify refresh token
      const payload = jwt.verify(refreshToken, config.jwt.refreshSecret) as JwtPayload;

      // Check if user exists
      const user = await prisma.user.findUnique({
        where: { id: payload.sub },
      });

      if (!user || user.deletedAt) {
        throw new Error('User not found');
      }

      // Check if refresh token is blacklisted
      const isBlacklisted = await RedisService.getCache(`blacklist:refresh:${refreshToken}`);
      if (isBlacklisted) {
        throw new Error('Refresh token has been revoked');
      }

      Logger.auth(`Token refreshed for user: ${user.email}`, { userId: user.id });

      // Generate new tokens
      return await this.generateTokens(user.id, user.email);
    } catch (error) {
      Logger.error('Token refresh failed', error as Error);
      throw error;
    }
  }

  /**
   * Logout user by blacklisting tokens
   */
  static async logout(accessToken: string, refreshToken?: string): Promise<void> {
    try {
      // Blacklist access token
      const accessPayload = jwt.decode(accessToken) as JwtPayload;
      if (accessPayload && accessPayload.exp) {
        const ttl = accessPayload.exp - Math.floor(Date.now() / 1000);
        if (ttl > 0) {
          await RedisService.setCache(`blacklist:${accessToken}`, true, ttl);
        }
      }

      // Blacklist refresh token if provided
      if (refreshToken) {
        const refreshPayload = jwt.decode(refreshToken) as JwtPayload;
        if (refreshPayload && refreshPayload.exp) {
          const ttl = refreshPayload.exp - Math.floor(Date.now() / 1000);
          if (ttl > 0) {
            await RedisService.setCache(`blacklist:refresh:${refreshToken}`, true, ttl);
          }
        }
      }

      Logger.auth('User logged out');
    } catch (error) {
      Logger.error('Logout failed', error as Error);
      throw error;
    }
  }

  /**
   * Change user password
   */
  static async changePassword(
    userId: string,
    currentPassword: string,
    newPassword: string
  ): Promise<void> {
    try {
      const user = await prisma.user.findUnique({
        where: { id: userId },
      });

      if (!user || user.deletedAt) {
        throw new Error('User not found');
      }

      if (!user.passwordHash) {
        throw new Error('Cannot change password for SSO users');
      }

      // Verify current password
      const isValidPassword = await bcrypt.compare(currentPassword, user.passwordHash);
      if (!isValidPassword) {
        throw new Error('Current password is incorrect');
      }

      // Hash new password
      const newPasswordHash = await bcrypt.hash(newPassword, config.security.bcryptRounds);

      // Update password
      await prisma.user.update({
        where: { id: userId },
        data: { passwordHash: newPasswordHash },
      });

      Logger.auth(`Password changed for user: ${user.email}`, { userId });
    } catch (error) {
      Logger.error('Password change failed', error as Error);
      throw error;
    }
  }

  /**
   * Send password reset email
   */
  static async forgotPassword(email: string): Promise<void> {
    try {
      const user = await prisma.user.findUnique({
        where: { email: email.toLowerCase() },
      });

      if (!user || user.deletedAt) {
        // Don't reveal if user exists
        Logger.auth(`Password reset requested for non-existent user: ${email}`);
        return;
      }

      if (!user.passwordHash) {
        // Don't allow password reset for SSO users
        Logger.auth(`Password reset requested for SSO user: ${email}`);
        return;
      }

      // Generate reset token
      const resetToken = nanoid(32);
      const resetExpires = new Date(Date.now() + 3600000); // 1 hour

      // Store reset token in Redis
      await RedisService.setCache(
        `password_reset:${resetToken}`,
        { userId: user.id, email: user.email },
        3600 // 1 hour TTL
      );

      // TODO: Send password reset email
      Logger.auth(`Password reset token generated for user: ${user.email}`, { userId: user.id });
    } catch (error) {
      Logger.error('Forgot password failed', error as Error);
      throw error;
    }
  }

  /**
   * Reset password using reset token
   */
  static async resetPassword(token: string, newPassword: string): Promise<void> {
    try {
      // Get reset data from Redis
      const resetData = await RedisService.getCache(`password_reset:${token}`);
      if (!resetData) {
        throw new Error('Invalid or expired reset token');
      }

      // Hash new password
      const passwordHash = await bcrypt.hash(newPassword, config.security.bcryptRounds);

      // Update password
      await prisma.user.update({
        where: { id: resetData.userId },
        data: { passwordHash },
      });

      // Delete reset token
      await RedisService.deleteCache(`password_reset:${token}`);

      Logger.auth(`Password reset completed for user: ${resetData.email}`, {
        userId: resetData.userId,
      });
    } catch (error) {
      Logger.error('Password reset failed', error as Error);
      throw error;
    }
  }

  /**
   * Verify email address
   */
  static async verifyEmail(token: string): Promise<void> {
    try {
      // Get verification data from Redis
      const verificationData = await RedisService.getCache(`email_verification:${token}`);
      if (!verificationData) {
        throw new Error('Invalid or expired verification token');
      }

      // Update user email verification status
      await prisma.user.update({
        where: { id: verificationData.userId },
        data: { emailVerified: true },
      });

      // Delete verification token
      await RedisService.deleteCache(`email_verification:${token}`);

      Logger.auth(`Email verified for user: ${verificationData.email}`, {
        userId: verificationData.userId,
      });
    } catch (error) {
      Logger.error('Email verification failed', error as Error);
      throw error;
    }
  }

  /**
   * Get user profile
   */
  static async getProfile(userId: string): Promise<AuthUser> {
    try {
      const user = await prisma.user.findUnique({
        where: { id: userId },
        include: {
          organizationMemberships: {
            include: {
              organization: true,
            },
            where: {
              status: 'active',
            },
          },
        },
      });

      if (!user || user.deletedAt) {
        throw new Error('User not found');
      }

      return {
        id: user.id,
        email: user.email,
        firstName: user.firstName || undefined,
        lastName: user.lastName || undefined,
        avatarUrl: user.avatarUrl || undefined,
        organizations: user.organizationMemberships.map((membership) => ({
          id: membership.organization.id,
          name: membership.organization.name,
          role: membership.role,
          permissions: [],
        })),
      };
    } catch (error) {
      Logger.error('Get profile failed', error as Error);
      throw error;
    }
  }

  /**
   * Update user profile
   */
  static async updateProfile(
    userId: string,
    data: {
      firstName?: string;
      lastName?: string;
      avatarUrl?: string;
      timezone?: string;
      locale?: string;
      settings?: Record<string, any>;
    }
  ): Promise<AuthUser> {
    try {
      const user = await prisma.user.update({
        where: { id: userId },
        data,
        include: {
          organizationMemberships: {
            include: {
              organization: true,
            },
            where: {
              status: 'active',
            },
          },
        },
      });

      Logger.auth(`Profile updated for user: ${user.email}`, { userId });

      return {
        id: user.id,
        email: user.email,
        firstName: user.firstName || undefined,
        lastName: user.lastName || undefined,
        avatarUrl: user.avatarUrl || undefined,
        organizations: user.organizationMemberships.map((membership) => ({
          id: membership.organization.id,
          name: membership.organization.name,
          role: membership.role,
          permissions: [],
        })),
      };
    } catch (error) {
      Logger.error('Profile update failed', error as Error);
      throw error;
    }
  }

  // ============================================================================
  // PRIVATE METHODS
  // ============================================================================

  /**
   * Generate JWT access and refresh tokens
   */
  private static async generateTokens(userId: string, email: string): Promise<AuthTokens> {
    const now = Math.floor(Date.now() / 1000);
    const accessTokenExpiry = now + 24 * 60 * 60; // 24 hours
    const refreshTokenExpiry = now + 7 * 24 * 60 * 60; // 7 days

    // Access token payload
    const accessPayload: JwtPayload = {
      sub: userId,
      email,
      iat: now,
      exp: accessTokenExpiry,
    };

    // Refresh token payload
    const refreshPayload: JwtPayload = {
      sub: userId,
      email,
      iat: now,
      exp: refreshTokenExpiry,
    };

    // Generate tokens
    const accessToken = jwt.sign(accessPayload, config.jwt.secret);
    const refreshToken = jwt.sign(refreshPayload, config.jwt.refreshSecret);

    return {
      accessToken,
      refreshToken,
      expiresIn: accessTokenExpiry,
    };
  }
}