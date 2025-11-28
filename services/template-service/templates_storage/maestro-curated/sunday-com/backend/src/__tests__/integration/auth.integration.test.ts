import request from 'supertest';
import { app } from '@/server';
import { prisma } from '@/config/database';
import {
  TestDataFactory,
  TestCleanup,
  TestMocks,
  ApiTestHelpers,
} from '../utils/testHelpers';
import jwt from 'jsonwebtoken';
import { config } from '@/config';

describe('Authentication API Integration Tests', () => {
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

  describe('POST /api/auth/register', () => {
    it('should register a new user successfully', async () => {
      const userData = {
        email: 'newuser@example.com',
        password: 'Password123!',
        firstName: 'New',
        lastName: 'User',
      };

      const response = await request(app)
        .post('/api/auth/register')
        .send(userData)
        .expect(201);

      ApiTestHelpers.assertApiResponse(response, 201);

      expect(response.body.data).toHaveProperty('user');
      expect(response.body.data).toHaveProperty('tokens');

      const { user, tokens } = response.body.data;

      expect(user).toMatchObject({
        email: 'newuser@example.com',
        firstName: 'New',
        lastName: 'User',
      });

      expect(user).not.toHaveProperty('passwordHash');

      expect(tokens).toHaveProperty('accessToken');
      expect(tokens).toHaveProperty('refreshToken');
      expect(tokens).toHaveProperty('expiresIn');

      // Verify user was created in database
      const dbUser = await prisma.user.findUnique({
        where: { email: 'newuser@example.com' },
      });
      expect(dbUser).toBeTruthy();
    });

    it('should return 400 for missing required fields', async () => {
      const response = await request(app)
        .post('/api/auth/register')
        .send({
          email: 'test@example.com',
          // Missing password, firstName, lastName
        })
        .expect(400);

      ApiTestHelpers.assertApiResponse(response, 400);
      expect(response.body.error).toContain('validation');
    });

    it('should return 400 for invalid email format', async () => {
      const response = await request(app)
        .post('/api/auth/register')
        .send({
          email: 'invalid-email',
          password: 'Password123!',
          firstName: 'Test',
          lastName: 'User',
        })
        .expect(400);

      ApiTestHelpers.assertApiResponse(response, 400);
    });

    it('should return 400 for weak password', async () => {
      const response = await request(app)
        .post('/api/auth/register')
        .send({
          email: 'test@example.com',
          password: '123',
          firstName: 'Test',
          lastName: 'User',
        })
        .expect(400);

      ApiTestHelpers.assertApiResponse(response, 400);
    });

    it('should return 409 for existing email', async () => {
      // Create existing user
      await TestDataFactory.createUser({
        email: 'existing@example.com',
      });

      const response = await request(app)
        .post('/api/auth/register')
        .send({
          email: 'existing@example.com',
          password: 'Password123!',
          firstName: 'Test',
          lastName: 'User',
        })
        .expect(409);

      ApiTestHelpers.assertApiResponse(response, 409);
      expect(response.body.error).toContain('already exists');
    });

    it('should handle database errors gracefully', async () => {
      // Mock database error
      const mockCreate = jest.spyOn(prisma.user, 'create').mockRejectedValue(
        new Error('Database connection failed')
      );

      const response = await request(app)
        .post('/api/auth/register')
        .send({
          email: 'test@example.com',
          password: 'Password123!',
          firstName: 'Test',
          lastName: 'User',
        })
        .expect(500);

      ApiTestHelpers.assertApiResponse(response, 500);

      mockCreate.mockRestore();
    });
  });

  describe('POST /api/auth/login', () => {
    let testUser: any;

    beforeEach(async () => {
      testUser = await TestDataFactory.createUser({
        email: 'testuser@example.com',
        firstName: 'Test',
        lastName: 'User',
      });
    });

    it('should login with valid credentials', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'testuser@example.com',
          password: 'TestPassword123!', // Default password from factory
        })
        .expect(200);

      ApiTestHelpers.assertApiResponse(response, 200);

      const { user, tokens } = response.body.data;

      expect(user).toMatchObject({
        id: testUser.id,
        email: 'testuser@example.com',
        firstName: 'Test',
        lastName: 'User',
      });

      expect(tokens).toHaveProperty('accessToken');
      expect(tokens).toHaveProperty('refreshToken');

      // Verify token is valid
      const decoded = jwt.verify(tokens.accessToken, config.jwt.accessSecret);
      expect(decoded).toHaveProperty('sub', testUser.id);
    });

    it('should return 401 for invalid email', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'nonexistent@example.com',
          password: 'TestPassword123!',
        })
        .expect(401);

      ApiTestHelpers.assertApiResponse(response, 401);
      expect(response.body.error).toContain('Invalid email or password');
    });

    it('should return 401 for invalid password', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'testuser@example.com',
          password: 'WrongPassword123!',
        })
        .expect(401);

      ApiTestHelpers.assertApiResponse(response, 401);
      expect(response.body.error).toContain('Invalid email or password');
    });

    it('should return 400 for missing credentials', async () => {
      const response = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'testuser@example.com',
          // Missing password
        })
        .expect(400);

      ApiTestHelpers.assertApiResponse(response, 400);
    });

    it('should update last login time', async () => {
      const beforeLogin = new Date();

      await request(app)
        .post('/api/auth/login')
        .send({
          email: 'testuser@example.com',
          password: 'TestPassword123!',
        })
        .expect(200);

      const updatedUser = await prisma.user.findUnique({
        where: { id: testUser.id },
      });

      expect(updatedUser?.lastLoginAt).toBeTruthy();
      expect(updatedUser?.lastLoginAt!.getTime()).toBeGreaterThanOrEqual(beforeLogin.getTime());
    });

    it('should rate limit login attempts', async () => {
      // Make multiple failed login attempts
      const promises = Array(10).fill(0).map(() =>
        request(app)
          .post('/api/auth/login')
          .send({
            email: 'testuser@example.com',
            password: 'WrongPassword123!',
          })
      );

      const responses = await Promise.all(promises);

      // Some requests should be rate limited
      const rateLimitedResponses = responses.filter(r => r.status === 429);
      expect(rateLimitedResponses.length).toBeGreaterThan(0);
    });
  });

  describe('POST /api/auth/refresh', () => {
    let testUser: any;
    let authTokens: any;

    beforeEach(async () => {
      testUser = await TestDataFactory.createAuthenticatedUser({
        email: 'testuser@example.com',
      });
      authTokens = testUser.tokens;
    });

    it('should refresh tokens with valid refresh token', async () => {
      const response = await request(app)
        .post('/api/auth/refresh')
        .send({
          refreshToken: authTokens.refreshToken,
        })
        .expect(200);

      ApiTestHelpers.assertApiResponse(response, 200);

      const { accessToken, refreshToken, expiresIn } = response.body.data;

      expect(accessToken).toBeTruthy();
      expect(refreshToken).toBeTruthy();
      expect(expiresIn).toBeGreaterThan(0);

      // New tokens should be different from old ones
      expect(accessToken).not.toBe(authTokens.accessToken);
      expect(refreshToken).not.toBe(authTokens.refreshToken);

      // New access token should be valid
      const decoded = jwt.verify(accessToken, config.jwt.accessSecret);
      expect(decoded).toHaveProperty('sub', testUser.id);
    });

    it('should return 401 for invalid refresh token', async () => {
      const response = await request(app)
        .post('/api/auth/refresh')
        .send({
          refreshToken: 'invalid-refresh-token',
        })
        .expect(401);

      ApiTestHelpers.assertApiResponse(response, 401);
      expect(response.body.error).toContain('Invalid');
    });

    it('should return 401 for expired refresh token', async () => {
      // Create expired refresh token
      const expiredToken = jwt.sign(
        {
          sub: testUser.id,
          email: testUser.email,
          iat: Math.floor(Date.now() / 1000) - 10000,
          exp: Math.floor(Date.now() / 1000) - 5000, // Expired 5 seconds ago
        },
        config.jwt.refreshSecret
      );

      const response = await request(app)
        .post('/api/auth/refresh')
        .send({
          refreshToken: expiredToken,
        })
        .expect(401);

      ApiTestHelpers.assertApiResponse(response, 401);
    });

    it('should return 400 for missing refresh token', async () => {
      const response = await request(app)
        .post('/api/auth/refresh')
        .send({})
        .expect(400);

      ApiTestHelpers.assertApiResponse(response, 400);
    });
  });

  describe('GET /api/auth/me', () => {
    let testUser: any;

    beforeEach(async () => {
      testUser = await TestDataFactory.createAuthenticatedUser({
        email: 'testuser@example.com',
      });
    });

    it('should return user profile with valid token', async () => {
      const response = await ApiTestHelpers.authenticatedRequest(
        request(app).get('/api/auth/me'),
        testUser.tokens.accessToken
      ).expect(200);

      ApiTestHelpers.assertApiResponse(response, 200);

      expect(response.body.data).toMatchObject({
        id: testUser.id,
        email: 'testuser@example.com',
        firstName: testUser.firstName,
        lastName: testUser.lastName,
      });

      expect(response.body.data).not.toHaveProperty('passwordHash');
      expect(response.body.data).toHaveProperty('organizations');
    });

    it('should return 401 for missing token', async () => {
      const response = await request(app)
        .get('/api/auth/me')
        .expect(401);

      ApiTestHelpers.assertApiResponse(response, 401);
      expect(response.body.error).toContain('token');
    });

    it('should return 401 for invalid token', async () => {
      const response = await request(app)
        .get('/api/auth/me')
        .set('Authorization', 'Bearer invalid-token')
        .expect(401);

      ApiTestHelpers.assertApiResponse(response, 401);
    });

    it('should return 401 for expired token', async () => {
      // Create expired token
      const expiredToken = jwt.sign(
        {
          sub: testUser.id,
          email: testUser.email,
          iat: Math.floor(Date.now() / 1000) - 10000,
          exp: Math.floor(Date.now() / 1000) - 5000, // Expired 5 seconds ago
        },
        config.jwt.accessSecret
      );

      const response = await request(app)
        .get('/api/auth/me')
        .set('Authorization', `Bearer ${expiredToken}`)
        .expect(401);

      ApiTestHelpers.assertApiResponse(response, 401);
    });

    it('should include user organizations', async () => {
      // Create organization with user as member
      const organization = await TestDataFactory.createOrganization({}, testUser.id);

      const response = await ApiTestHelpers.authenticatedRequest(
        request(app).get('/api/auth/me'),
        testUser.tokens.accessToken
      ).expect(200);

      expect(response.body.data.organizations).toHaveLength(1);
      expect(response.body.data.organizations[0]).toMatchObject({
        id: organization.id,
        name: organization.name,
        role: 'owner',
      });
    });
  });

  describe('POST /api/auth/logout', () => {
    let testUser: any;

    beforeEach(async () => {
      testUser = await TestDataFactory.createAuthenticatedUser({
        email: 'testuser@example.com',
      });
    });

    it('should logout successfully with valid token', async () => {
      const response = await ApiTestHelpers.authenticatedRequest(
        request(app).post('/api/auth/logout'),
        testUser.tokens.accessToken
      ).expect(200);

      ApiTestHelpers.assertApiResponse(response, 200);

      // Token should be invalidated (added to blacklist)
      expect(mockRedis.setCache).toHaveBeenCalledWith(
        expect.stringContaining('blacklist:'),
        expect.any(String),
        expect.any(Number)
      );
    });

    it('should return 401 for missing token', async () => {
      const response = await request(app)
        .post('/api/auth/logout')
        .expect(401);

      ApiTestHelpers.assertApiResponse(response, 401);
    });

    it('should return 401 for invalid token', async () => {
      const response = await request(app)
        .post('/api/auth/logout')
        .set('Authorization', 'Bearer invalid-token')
        .expect(401);

      ApiTestHelpers.assertApiResponse(response, 401);
    });
  });

  describe('POST /api/auth/forgot-password', () => {
    let testUser: any;

    beforeEach(async () => {
      testUser = await TestDataFactory.createUser({
        email: 'testuser@example.com',
      });
    });

    it('should send password reset email for valid email', async () => {
      const response = await request(app)
        .post('/api/auth/forgot-password')
        .send({
          email: 'testuser@example.com',
        })
        .expect(200);

      ApiTestHelpers.assertApiResponse(response, 200);

      // Should store reset token in cache
      expect(mockRedis.setCache).toHaveBeenCalledWith(
        expect.stringContaining('password-reset:'),
        expect.any(String),
        expect.any(Number)
      );
    });

    it('should return success even for non-existent email (security)', async () => {
      const response = await request(app)
        .post('/api/auth/forgot-password')
        .send({
          email: 'nonexistent@example.com',
        })
        .expect(200);

      ApiTestHelpers.assertApiResponse(response, 200);
    });

    it('should return 400 for invalid email format', async () => {
      const response = await request(app)
        .post('/api/auth/forgot-password')
        .send({
          email: 'invalid-email',
        })
        .expect(400);

      ApiTestHelpers.assertApiResponse(response, 400);
    });

    it('should rate limit password reset requests', async () => {
      // Make multiple requests
      const promises = Array(5).fill(0).map(() =>
        request(app)
          .post('/api/auth/forgot-password')
          .send({
            email: 'testuser@example.com',
          })
      );

      const responses = await Promise.all(promises);

      // Some requests should be rate limited
      const rateLimitedResponses = responses.filter(r => r.status === 429);
      expect(rateLimitedResponses.length).toBeGreaterThan(0);
    });
  });

  describe('POST /api/auth/reset-password', () => {
    let testUser: any;
    let resetToken: string;

    beforeEach(async () => {
      testUser = await TestDataFactory.createUser({
        email: 'testuser@example.com',
      });

      // Mock reset token in cache
      resetToken = 'valid-reset-token';
      mockRedis.getCache.mockResolvedValue(testUser.id);
    });

    it('should reset password with valid token', async () => {
      const newPassword = 'NewPassword123!';

      const response = await request(app)
        .post('/api/auth/reset-password')
        .send({
          token: resetToken,
          password: newPassword,
        })
        .expect(200);

      ApiTestHelpers.assertApiResponse(response, 200);

      // Should delete reset token from cache
      expect(mockRedis.deleteCache).toHaveBeenCalledWith(
        expect.stringContaining('password-reset:')
      );

      // Should be able to login with new password
      const loginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'testuser@example.com',
          password: newPassword,
        })
        .expect(200);

      expect(loginResponse.body.data.user.id).toBe(testUser.id);
    });

    it('should return 400 for invalid token', async () => {
      mockRedis.getCache.mockResolvedValue(null);

      const response = await request(app)
        .post('/api/auth/reset-password')
        .send({
          token: 'invalid-token',
          password: 'NewPassword123!',
        })
        .expect(400);

      ApiTestHelpers.assertApiResponse(response, 400);
      expect(response.body.error).toContain('Invalid or expired');
    });

    it('should return 400 for weak password', async () => {
      const response = await request(app)
        .post('/api/auth/reset-password')
        .send({
          token: resetToken,
          password: '123',
        })
        .expect(400);

      ApiTestHelpers.assertApiResponse(response, 400);
    });

    it('should return 400 for missing fields', async () => {
      const response = await request(app)
        .post('/api/auth/reset-password')
        .send({
          token: resetToken,
          // Missing password
        })
        .expect(400);

      ApiTestHelpers.assertApiResponse(response, 400);
    });
  });

  describe('PUT /api/auth/change-password', () => {
    let testUser: any;

    beforeEach(async () => {
      testUser = await TestDataFactory.createAuthenticatedUser({
        email: 'testuser@example.com',
      });
    });

    it('should change password with valid current password', async () => {
      const response = await ApiTestHelpers.authenticatedRequest(
        request(app)
          .put('/api/auth/change-password')
          .send({
            currentPassword: 'TestPassword123!',
            newPassword: 'NewPassword123!',
          }),
        testUser.tokens.accessToken
      ).expect(200);

      ApiTestHelpers.assertApiResponse(response, 200);

      // Should be able to login with new password
      const loginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'testuser@example.com',
          password: 'NewPassword123!',
        })
        .expect(200);

      expect(loginResponse.body.data.user.id).toBe(testUser.id);
    });

    it('should return 400 for incorrect current password', async () => {
      const response = await ApiTestHelpers.authenticatedRequest(
        request(app)
          .put('/api/auth/change-password')
          .send({
            currentPassword: 'WrongPassword123!',
            newPassword: 'NewPassword123!',
          }),
        testUser.tokens.accessToken
      ).expect(400);

      ApiTestHelpers.assertApiResponse(response, 400);
      expect(response.body.error).toContain('Current password is incorrect');
    });

    it('should return 400 for weak new password', async () => {
      const response = await ApiTestHelpers.authenticatedRequest(
        request(app)
          .put('/api/auth/change-password')
          .send({
            currentPassword: 'TestPassword123!',
            newPassword: '123',
          }),
        testUser.tokens.accessToken
      ).expect(400);

      ApiTestHelpers.assertApiResponse(response, 400);
    });

    it('should return 401 for missing authentication', async () => {
      const response = await request(app)
        .put('/api/auth/change-password')
        .send({
          currentPassword: 'TestPassword123!',
          newPassword: 'NewPassword123!',
        })
        .expect(401);

      ApiTestHelpers.assertApiResponse(response, 401);
    });
  });

  describe('Performance Tests', () => {
    it('should handle concurrent login requests', async () => {
      // Create multiple test users
      const users = await Promise.all(
        Array(10).fill(0).map((_, i) =>
          TestDataFactory.createUser({
            email: `user${i}@example.com`,
          })
        )
      );

      // Make concurrent login requests
      const loginPromises = users.map(user =>
        request(app)
          .post('/api/auth/login')
          .send({
            email: user.email,
            password: 'TestPassword123!',
          })
      );

      const startTime = Date.now();
      const responses = await Promise.all(loginPromises);
      const duration = Date.now() - startTime;

      // All requests should succeed
      responses.forEach(response => {
        expect(response.status).toBe(200);
      });

      // Should complete within reasonable time
      expect(duration).toBeLessThan(2000); // 2 seconds for 10 concurrent requests
    });

    it('should complete authentication workflow within performance threshold', async () => {
      const testUser = await TestDataFactory.createUser({
        email: 'perftest@example.com',
      });

      const startTime = Date.now();

      // Complete auth workflow: login -> get profile -> logout
      const loginResponse = await request(app)
        .post('/api/auth/login')
        .send({
          email: 'perftest@example.com',
          password: 'TestPassword123!',
        });

      const token = loginResponse.body.data.tokens.accessToken;

      await ApiTestHelpers.authenticatedRequest(
        request(app).get('/api/auth/me'),
        token
      );

      await ApiTestHelpers.authenticatedRequest(
        request(app).post('/api/auth/logout'),
        token
      );

      const duration = Date.now() - startTime;

      // Complete workflow should finish within 500ms
      expect(duration).toBeLessThan(500);
    });
  });
});