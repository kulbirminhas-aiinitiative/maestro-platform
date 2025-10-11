import { Router } from 'express';
import { AuthService } from '@/services/auth.service';
import { validate } from '@/middleware/validation';
import { authenticateToken, optionalAuth, rateLimit } from '@/middleware/auth';
import { Logger } from '@/config/logger';
import {
  loginSchema,
  registerSchema,
  refreshTokenSchema,
  forgotPasswordSchema,
  resetPasswordSchema,
} from '@/middleware/express-validation';
import { AuthenticatedRequest } from '@/types';

const router = Router();

/**
 * @route   POST /api/v1/auth/register
 * @desc    Register a new user
 * @access  Public
 */
router.post(
  '/register',
  rateLimit(5, 15 * 60 * 1000), // 5 requests per 15 minutes
  validate(registerSchema),
  async (req, res) => {
    try {
      const { user, tokens } = await AuthService.register(req.body);

      res.status(201).json({
        data: {
          user,
          tokens,
        },
      });
    } catch (error) {
      Logger.error('Registration failed', error as Error);

      res.status(400).json({
        error: {
          type: 'registration_failed',
          message: error instanceof Error ? error.message : 'Registration failed',
        },
      });
    }
  }
);

/**
 * @route   POST /api/v1/auth/login
 * @desc    Login user
 * @access  Public
 */
router.post(
  '/login',
  rateLimit(10, 15 * 60 * 1000), // 10 requests per 15 minutes
  validate(loginSchema),
  async (req, res) => {
    try {
      const { user, tokens } = await AuthService.login(req.body);

      res.json({
        data: {
          user,
          tokens,
        },
      });
    } catch (error) {
      Logger.error('Login failed', error as Error);

      res.status(401).json({
        error: {
          type: 'login_failed',
          message: error instanceof Error ? error.message : 'Login failed',
        },
      });
    }
  }
);

/**
 * @route   POST /api/v1/auth/refresh
 * @desc    Refresh access token
 * @access  Public
 */
router.post(
  '/refresh',
  rateLimit(20, 15 * 60 * 1000), // 20 requests per 15 minutes
  validate(refreshTokenSchema),
  async (req, res) => {
    try {
      const tokens = await AuthService.refreshToken(req.body.refreshToken);

      res.json({
        data: { tokens },
      });
    } catch (error) {
      Logger.error('Token refresh failed', error as Error);

      res.status(401).json({
        error: {
          type: 'token_refresh_failed',
          message: error instanceof Error ? error.message : 'Token refresh failed',
        },
      });
    }
  }
);

/**
 * @route   POST /api/v1/auth/logout
 * @desc    Logout user
 * @access  Private
 */
router.post('/logout', authenticateToken, async (req: AuthenticatedRequest, res) => {
  try {
    const accessToken = req.headers.authorization?.substring(7);
    const refreshToken = req.body.refreshToken;

    if (accessToken) {
      await AuthService.logout(accessToken, refreshToken);
    }

    res.json({
      data: { message: 'Logged out successfully' },
    });
  } catch (error) {
    Logger.error('Logout failed', error as Error);

    res.status(500).json({
      error: {
        type: 'logout_failed',
        message: 'Logout failed',
      },
    });
  }
});

/**
 * @route   POST /api/v1/auth/forgot-password
 * @desc    Send password reset email
 * @access  Public
 */
router.post(
  '/forgot-password',
  rateLimit(3, 15 * 60 * 1000), // 3 requests per 15 minutes
  validate(forgotPasswordSchema),
  async (req, res) => {
    try {
      await AuthService.forgotPassword(req.body.email);

      res.json({
        data: {
          message: 'If an account with that email exists, a password reset link has been sent.',
        },
      });
    } catch (error) {
      Logger.error('Forgot password failed', error as Error);

      res.status(500).json({
        error: {
          type: 'forgot_password_failed',
          message: 'Failed to process password reset request',
        },
      });
    }
  }
);

/**
 * @route   POST /api/v1/auth/reset-password
 * @desc    Reset password using token
 * @access  Public
 */
router.post(
  '/reset-password',
  rateLimit(5, 15 * 60 * 1000), // 5 requests per 15 minutes
  validate(resetPasswordSchema),
  async (req, res) => {
    try {
      await AuthService.resetPassword(req.body.token, req.body.password);

      res.json({
        data: { message: 'Password reset successfully' },
      });
    } catch (error) {
      Logger.error('Password reset failed', error as Error);

      res.status(400).json({
        error: {
          type: 'password_reset_failed',
          message: error instanceof Error ? error.message : 'Password reset failed',
        },
      });
    }
  }
);

/**
 * @route   POST /api/v1/auth/change-password
 * @desc    Change user password
 * @access  Private
 */
router.post('/change-password', authenticateToken, async (req: AuthenticatedRequest, res) => {
  try {
    const { currentPassword, newPassword } = req.body;

    if (!currentPassword || !newPassword) {
      return res.status(400).json({
        error: {
          type: 'validation_error',
          message: 'Current password and new password are required',
        },
      });
    }

    await AuthService.changePassword(req.user!.id, currentPassword, newPassword);

    res.json({
      data: { message: 'Password changed successfully' },
    });
  } catch (error) {
    Logger.error('Password change failed', error as Error);

    res.status(400).json({
      error: {
        type: 'password_change_failed',
        message: error instanceof Error ? error.message : 'Password change failed',
      },
    });
  }
});

/**
 * @route   POST /api/v1/auth/verify-email
 * @desc    Verify email address
 * @access  Public
 */
router.post('/verify-email', async (req, res) => {
  try {
    const { token } = req.body;

    if (!token) {
      return res.status(400).json({
        error: {
          type: 'validation_error',
          message: 'Verification token is required',
        },
      });
    }

    await AuthService.verifyEmail(token);

    res.json({
      data: { message: 'Email verified successfully' },
    });
  } catch (error) {
    Logger.error('Email verification failed', error as Error);

    res.status(400).json({
      error: {
        type: 'email_verification_failed',
        message: error instanceof Error ? error.message : 'Email verification failed',
      },
    });
  }
});

/**
 * @route   GET /api/v1/auth/me
 * @desc    Get current user profile
 * @access  Private
 */
router.get('/me', authenticateToken, async (req: AuthenticatedRequest, res) => {
  try {
    const user = await AuthService.getProfile(req.user!.id);

    res.json({
      data: { user },
    });
  } catch (error) {
    Logger.error('Get profile failed', error as Error);

    res.status(500).json({
      error: {
        type: 'get_profile_failed',
        message: 'Failed to get user profile',
      },
    });
  }
});

/**
 * @route   PUT /api/v1/auth/me
 * @desc    Update current user profile
 * @access  Private
 */
router.put('/me', authenticateToken, async (req: AuthenticatedRequest, res) => {
  try {
    const allowedFields = ['firstName', 'lastName', 'avatarUrl', 'timezone', 'locale', 'settings'];
    const updateData: any = {};

    // Filter allowed fields
    for (const field of allowedFields) {
      if (req.body[field] !== undefined) {
        updateData[field] = req.body[field];
      }
    }

    const user = await AuthService.updateProfile(req.user!.id, updateData);

    res.json({
      data: { user },
    });
  } catch (error) {
    Logger.error('Profile update failed', error as Error);

    res.status(500).json({
      error: {
        type: 'profile_update_failed',
        message: 'Failed to update profile',
      },
    });
  }
});

/**
 * @route   GET /api/v1/auth/check
 * @desc    Check if user is authenticated
 * @access  Public
 */
router.get('/check', optionalAuth, async (req: AuthenticatedRequest, res) => {
  res.json({
    data: {
      authenticated: !!req.user,
      user: req.user || null,
    },
  });
});

export default router;