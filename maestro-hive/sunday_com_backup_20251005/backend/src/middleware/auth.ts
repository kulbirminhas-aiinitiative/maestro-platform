import { Request, Response, NextFunction } from 'express';
import jwt from 'jsonwebtoken';
import { prisma } from '@/config/database';
import { RedisService } from '@/config/redis';
import { Logger } from '@/config/logger';
import { config } from '@/config';
import { AuthenticatedRequest, AuthUser, JwtPayload } from '@/types';

/**
 * JWT Authentication Middleware
 * Validates JWT tokens and attaches user information to request
 */
export const authenticateToken = async (
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): Promise<void> => {
  try {
    const authHeader = req.headers.authorization;
    const token = authHeader?.startsWith('Bearer ') ? authHeader.substring(7) : null;

    if (!token) {
      res.status(401).json({
        error: {
          type: 'unauthorized',
          message: 'Access token is required',
        },
      });
      return;
    }

    // Verify JWT token
    const payload = jwt.verify(token, config.jwt.secret) as JwtPayload;

    // Check if token is blacklisted (for logout functionality)
    const isBlacklisted = await RedisService.getCache(`blacklist:${token}`);
    if (isBlacklisted) {
      res.status(401).json({
        error: {
          type: 'unauthorized',
          message: 'Token has been revoked',
        },
      });
      return;
    }

    // Get user from database
    const user = await prisma.user.findUnique({
      where: { id: payload.sub },
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
      res.status(401).json({
        error: {
          type: 'unauthorized',
          message: 'User not found or deactivated',
        },
      });
      return;
    }

    // Transform user data for request context
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
        permissions: [], // Will be populated by organization middleware
      })),
    };

    req.user = authUser;

    Logger.auth(`User ${user.email} authenticated`, { userId: user.id });
    next();
  } catch (error) {
    Logger.error('Authentication error', error as Error);

    if (error instanceof jwt.JsonWebTokenError) {
      res.status(401).json({
        error: {
          type: 'unauthorized',
          message: 'Invalid token',
        },
      });
      return;
    }

    res.status(500).json({
      error: {
        type: 'internal_error',
        message: 'Authentication service unavailable',
      },
    });
  }
};

/**
 * Optional Authentication Middleware
 * Validates JWT tokens if present but doesn't require them
 */
export const optionalAuth = async (
  req: AuthenticatedRequest,
  res: Response,
  next: NextFunction
): Promise<void> => {
  const authHeader = req.headers.authorization;
  const token = authHeader?.startsWith('Bearer ') ? authHeader.substring(7) : null;

  if (!token) {
    next();
    return;
  }

  // If token is present, validate it
  await authenticateToken(req, res, next);
};

/**
 * Organization Context Middleware
 * Adds organization context and permissions to the request
 */
export const organizationContext = (organizationParam: string = 'organizationId') => {
  return async (
    req: AuthenticatedRequest,
    res: Response,
    next: NextFunction
  ): Promise<void> => {
    try {
      if (!req.user) {
        res.status(401).json({
          error: {
            type: 'unauthorized',
            message: 'Authentication required',
          },
        });
        return;
      }

      const organizationId = req.params[organizationParam] || req.body.organizationId;

      if (!organizationId) {
        res.status(400).json({
          error: {
            type: 'validation_error',
            message: 'Organization ID is required',
          },
        });
        return;
      }

      // Check if user is member of the organization
      const membership = await prisma.organizationMember.findUnique({
        where: {
          organizationId_userId: {
            organizationId,
            userId: req.user.id,
          },
        },
        include: {
          organization: true,
        },
      });

      if (!membership || membership.status !== 'active') {
        res.status(403).json({
          error: {
            type: 'forbidden',
            message: 'Access denied to organization',
          },
        });
        return;
      }

      // Get or cache user permissions for this organization
      let permissions = await RedisService.getCachedUserPermissions(req.user.id, organizationId);

      if (!permissions) {
        permissions = await getUserPermissions(req.user.id, organizationId);
        await RedisService.cacheUserPermissions(req.user.id, organizationId, permissions);
      }

      req.organization = {
        id: organizationId,
        role: membership.role,
        permissions: permissions.organization.permissions,
      };

      Logger.auth(`Organization context set`, {
        userId: req.user.id,
        organizationId,
        role: membership.role,
      });

      next();
    } catch (error) {
      Logger.error('Organization context error', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to set organization context',
        },
      });
    }
  };
};

/**
 * Permission Check Middleware
 * Validates user has required permissions
 */
export const requirePermissions = (...permissions: string[]) => {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction): void => {
    if (!req.organization) {
      res.status(403).json({
        error: {
          type: 'forbidden',
          message: 'Organization context required',
        },
      });
      return;
    }

    const userPermissions = req.organization.permissions;
    const hasAllPermissions = permissions.every(permission =>
      userPermissions.includes(permission) || userPermissions.includes('*')
    );

    if (!hasAllPermissions) {
      Logger.security(`Permission denied`, {
        userId: req.user?.id,
        organizationId: req.organization.id,
        requiredPermissions: permissions,
        userPermissions,
      });

      res.status(403).json({
        error: {
          type: 'forbidden',
          message: 'Insufficient permissions',
          details: {
            required: permissions,
            missing: permissions.filter(p => !userPermissions.includes(p)),
          },
        },
      });
      return;
    }

    next();
  };
};

/**
 * Role-based Access Control Middleware
 */
export const requireRole = (...roles: string[]) => {
  return (req: AuthenticatedRequest, res: Response, next: NextFunction): void => {
    if (!req.organization) {
      res.status(403).json({
        error: {
          type: 'forbidden',
          message: 'Organization context required',
        },
      });
      return;
    }

    if (!roles.includes(req.organization.role)) {
      Logger.security(`Role check failed`, {
        userId: req.user?.id,
        organizationId: req.organization.id,
        userRole: req.organization.role,
        requiredRoles: roles,
      });

      res.status(403).json({
        error: {
          type: 'forbidden',
          message: 'Insufficient role privileges',
          details: {
            required: roles,
            current: req.organization.role,
          },
        },
      });
      return;
    }

    next();
  };
};

/**
 * Resource Ownership Middleware
 * Validates user owns or has access to specific resource
 */
export const requireResourceAccess = (resourceType: string, resourceIdParam: string = 'id') => {
  return async (
    req: AuthenticatedRequest,
    res: Response,
    next: NextFunction
  ): Promise<void> => {
    try {
      if (!req.user || !req.organization) {
        res.status(403).json({
          error: {
            type: 'forbidden',
            message: 'Authentication and organization context required',
          },
        });
        return;
      }

      const resourceId = req.params[resourceIdParam];
      const hasAccess = await checkResourceAccess(
        req.user.id,
        req.organization.id,
        resourceType,
        resourceId
      );

      if (!hasAccess) {
        Logger.security(`Resource access denied`, {
          userId: req.user.id,
          organizationId: req.organization.id,
          resourceType,
          resourceId,
        });

        res.status(403).json({
          error: {
            type: 'forbidden',
            message: 'Access denied to resource',
          },
        });
        return;
      }

      next();
    } catch (error) {
      Logger.error('Resource access check error', error as Error);
      res.status(500).json({
        error: {
          type: 'internal_error',
          message: 'Failed to verify resource access',
        },
      });
    }
  };
};

/**
 * Rate Limiting Middleware
 */
export const rateLimit = (limit: number, windowMs: number) => {
  return async (
    req: AuthenticatedRequest,
    res: Response,
    next: NextFunction
  ): Promise<void> => {
    try {
      const identifier = req.user?.id || req.ip;
      const key = `rate_limit:${identifier}:${req.route?.path || req.path}`;

      const result = await RedisService.checkRateLimit(key, limit, windowMs);

      res.set({
        'X-RateLimit-Limit': limit.toString(),
        'X-RateLimit-Remaining': result.remaining.toString(),
        'X-RateLimit-Reset': result.resetTime.toString(),
      });

      if (!result.allowed) {
        res.status(429).json({
          error: {
            type: 'rate_limit_exceeded',
            message: 'Too many requests',
            details: {
              limit,
              resetTime: result.resetTime,
            },
          },
        });
        return;
      }

      next();
    } catch (error) {
      Logger.error('Rate limiting error', error as Error);
      next(); // Continue on rate limiting errors
    }
  };
};

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Get user permissions for an organization
 */
async function getUserPermissions(userId: string, organizationId: string) {
  const membership = await prisma.organizationMember.findUnique({
    where: {
      organizationId_userId: {
        organizationId,
        userId,
      },
    },
  });

  if (!membership) {
    throw new Error('User is not a member of this organization');
  }

  // Define role-based permissions
  const rolePermissions: Record<string, string[]> = {
    owner: ['*'], // All permissions
    admin: [
      'org:read', 'org:write', 'org:admin',
      'workspace:read', 'workspace:write', 'workspace:admin',
      'board:read', 'board:write', 'board:admin',
      'item:read', 'item:write', 'item:delete',
      'user:read', 'user:invite', 'user:manage',
      'analytics:read',
    ],
    member: [
      'org:read',
      'workspace:read', 'workspace:write',
      'board:read', 'board:write',
      'item:read', 'item:write',
      'comment:read', 'comment:write',
      'file:read', 'file:write',
    ],
  };

  return {
    organization: {
      id: organizationId,
      role: membership.role,
      permissions: rolePermissions[membership.role] || rolePermissions.member,
    },
  };
}

/**
 * Check if user has access to a specific resource
 */
async function checkResourceAccess(
  userId: string,
  organizationId: string,
  resourceType: string,
  resourceId: string
): Promise<boolean> {
  try {
    switch (resourceType) {
      case 'workspace':
        const workspace = await prisma.workspace.findFirst({
          where: {
            id: resourceId,
            organizationId,
            OR: [
              { isPrivate: false },
              {
                members: {
                  some: { userId },
                },
              },
            ],
          },
        });
        return !!workspace;

      case 'board':
        const board = await prisma.board.findFirst({
          where: {
            id: resourceId,
            workspace: { organizationId },
            OR: [
              { isPrivate: false },
              {
                members: {
                  some: { userId },
                },
              },
            ],
          },
        });
        return !!board;

      case 'item':
        const item = await prisma.item.findFirst({
          where: {
            id: resourceId,
            board: {
              workspace: { organizationId },
            },
          },
        });
        return !!item;

      default:
        return false;
    }
  } catch (error) {
    Logger.error('Resource access check failed', error as Error);
    return false;
  }
}