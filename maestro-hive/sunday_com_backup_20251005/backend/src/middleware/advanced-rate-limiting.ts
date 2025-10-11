import { Request, Response, NextFunction } from 'express';
import { AuthenticatedRequest } from '@/types';
import { RedisService } from '@/config/redis';
import { Logger } from '@/config/logger';
import { RateLimitError } from './enhanced-error-v2';

// ============================================================================
// RATE LIMITING TYPES
// ============================================================================

export interface RateLimitRule {
  windowMs: number;
  maxRequests: number;
  skipSuccessfulRequests?: boolean;
  skipFailedRequests?: boolean;
  keyGenerator?: (req: AuthenticatedRequest) => string;
  skip?: (req: AuthenticatedRequest) => boolean;
  onLimitReached?: (req: AuthenticatedRequest, res: Response) => void;
}

export interface RateLimitResult {
  allowed: boolean;
  remaining: number;
  resetTime: number;
  totalUsage: number;
}

export interface TierLimits {
  [key: string]: {
    api: RateLimitRule;
    upload: RateLimitRule;
    websocket: RateLimitRule;
    ai: RateLimitRule;
  };
}

// ============================================================================
// RATE LIMITING CONFIGURATION
// ============================================================================

export const DEFAULT_TIER_LIMITS: TierLimits = {
  free: {
    api: {
      windowMs: 60 * 1000, // 1 minute
      maxRequests: 100,
    },
    upload: {
      windowMs: 60 * 1000,
      maxRequests: 10,
    },
    websocket: {
      windowMs: 60 * 1000,
      maxRequests: 1000,
    },
    ai: {
      windowMs: 60 * 1000,
      maxRequests: 5,
    },
  },
  pro: {
    api: {
      windowMs: 60 * 1000,
      maxRequests: 500,
    },
    upload: {
      windowMs: 60 * 1000,
      maxRequests: 50,
    },
    websocket: {
      windowMs: 60 * 1000,
      maxRequests: 5000,
    },
    ai: {
      windowMs: 60 * 1000,
      maxRequests: 50,
    },
  },
  enterprise: {
    api: {
      windowMs: 60 * 1000,
      maxRequests: 2000,
    },
    upload: {
      windowMs: 60 * 1000,
      maxRequests: 200,
    },
    websocket: {
      windowMs: 60 * 1000,
      maxRequests: 20000,
    },
    ai: {
      windowMs: 60 * 1000,
      maxRequests: 200,
    },
  },
};

// ============================================================================
// ADVANCED RATE LIMITER
// ============================================================================

export class AdvancedRateLimiter {
  /**
   * Check rate limit using sliding window algorithm
   */
  static async checkRateLimit(
    key: string,
    maxRequests: number,
    windowMs: number,
    weight: number = 1
  ): Promise<RateLimitResult> {
    try {
      const now = Date.now();
      const windowStart = now - windowMs;

      // Use sliding window algorithm with Redis sorted sets
      const pipeline = RedisService.pipeline();

      // Remove expired entries
      pipeline.zremrangebyscore(key, 0, windowStart);

      // Add current request
      pipeline.zadd(key, now, `${now}-${Math.random()}`);

      // Count current requests
      pipeline.zcard(key);

      // Set expiration
      pipeline.expire(key, Math.ceil(windowMs / 1000));

      const results = await pipeline.exec();
      const currentCount = results?.[2]?.[1] as number || 0;

      const allowed = (currentCount * weight) <= maxRequests;
      const remaining = Math.max(0, maxRequests - (currentCount * weight));
      const resetTime = Math.ceil((now + windowMs) / 1000);

      return {
        allowed,
        remaining,
        resetTime,
        totalUsage: currentCount * weight,
      };
    } catch (error) {
      Logger.error('Rate limit check failed', error as Error);
      // On error, allow the request to avoid blocking legitimate traffic
      return {
        allowed: true,
        remaining: 0,
        resetTime: Math.ceil((Date.now() + windowMs) / 1000),
        totalUsage: 0,
      };
    }
  }

  /**
   * Apply burst protection (short-term spike protection)
   */
  static async checkBurstProtection(
    key: string,
    maxBurst: number,
    burstWindowMs: number = 10000 // 10 seconds
  ): Promise<RateLimitResult> {
    const burstKey = `burst:${key}`;
    return this.checkRateLimit(burstKey, maxBurst, burstWindowMs);
  }

  /**
   * Check if IP is in whitelist/blacklist
   */
  static async checkIPRestrictions(ip: string): Promise<{
    allowed: boolean;
    reason?: string;
  }> {
    try {
      // Check blacklist
      const isBlacklisted = await RedisService.sismember('ip_blacklist', ip);
      if (isBlacklisted) {
        return { allowed: false, reason: 'IP blacklisted' };
      }

      // Check whitelist (if exists)
      const whitelistExists = await RedisService.exists('ip_whitelist');
      if (whitelistExists) {
        const isWhitelisted = await RedisService.sismember('ip_whitelist', ip);
        if (!isWhitelisted) {
          return { allowed: false, reason: 'IP not whitelisted' };
        }
      }

      return { allowed: true };
    } catch (error) {
      Logger.error('IP restriction check failed', error as Error);
      return { allowed: true }; // Allow on error
    }
  }

  /**
   * Implement progressive penalties for repeated violations
   */
  static async applyProgressivePenalty(
    identifier: string,
    violation: string
  ): Promise<{ penaltyMultiplier: number; banDuration?: number }> {
    try {
      const violationKey = `violations:${identifier}`;
      const violationCount = await RedisService.incr(violationKey, 24 * 60 * 60); // 24 hour TTL

      // Progressive penalty scale
      if (violationCount >= 10) {
        // Temporary ban for 1 hour
        await RedisService.setCache(`ban:${identifier}`, '1', 60 * 60);
        return { penaltyMultiplier: 0, banDuration: 60 * 60 };
      } else if (violationCount >= 5) {
        return { penaltyMultiplier: 0.1 }; // Severely restricted
      } else if (violationCount >= 3) {
        return { penaltyMultiplier: 0.5 }; // Half the normal rate
      } else {
        return { penaltyMultiplier: 0.8 }; // Slightly restricted
      }
    } catch (error) {
      Logger.error('Progressive penalty application failed', error as Error);
      return { penaltyMultiplier: 1 };
    }
  }

  /**
   * Check if user/IP is temporarily banned
   */
  static async checkTemporaryBan(identifier: string): Promise<{
    banned: boolean;
    expiresAt?: Date;
  }> {
    try {
      const banInfo = await RedisService.getCache(`ban:${identifier}`);
      if (banInfo) {
        const ttl = await RedisService.ttl(`ban:${identifier}`);
        return {
          banned: true,
          expiresAt: new Date(Date.now() + (ttl * 1000)),
        };
      }
      return { banned: false };
    } catch (error) {
      Logger.error('Ban check failed', error as Error);
      return { banned: false };
    }
  }
}

// ============================================================================
// RATE LIMITING MIDDLEWARE FACTORY
// ============================================================================

export const createRateLimit = (
  limiterType: 'api' | 'upload' | 'websocket' | 'ai',
  customRule?: Partial<RateLimitRule>
) => {
  return async (req: AuthenticatedRequest, res: Response, next: NextFunction): Promise<void> => {
    try {
      // Skip rate limiting for certain conditions
      if (customRule?.skip && customRule.skip(req)) {
        return next();
      }

      // Get user tier for dynamic limits
      const userTier = req.user?.organizations?.[0]?.role === 'owner' ? 'enterprise' :
                      req.user ? 'pro' : 'free';

      const tierLimits = DEFAULT_TIER_LIMITS[userTier];
      const rule = { ...tierLimits[limiterType], ...customRule };

      // Generate rate limit key
      const identifier = rule.keyGenerator ?
        rule.keyGenerator(req) :
        (req.user?.id || req.ip);

      const rateLimitKey = `rate_limit:${limiterType}:${identifier}`;

      // Check temporary ban
      const banCheck = await AdvancedRateLimiter.checkTemporaryBan(identifier);
      if (banCheck.banned) {
        throw new RateLimitError('Temporarily banned due to repeated violations', {
          expiresAt: banCheck.expiresAt,
          banDuration: banCheck.expiresAt ?
            Math.ceil((banCheck.expiresAt.getTime() - Date.now()) / 1000) :
            undefined,
        });
      }

      // Check IP restrictions
      const ipCheck = await AdvancedRateLimiter.checkIPRestrictions(req.ip);
      if (!ipCheck.allowed) {
        throw new RateLimitError(`Access denied: ${ipCheck.reason}`, {
          ipRestriction: true,
          reason: ipCheck.reason,
        });
      }

      // Apply progressive penalties
      const penalty = await AdvancedRateLimiter.applyProgressivePenalty(identifier, limiterType);
      const adjustedLimit = Math.floor(rule.maxRequests * penalty.penaltyMultiplier);

      if (penalty.banDuration) {
        throw new RateLimitError('Access temporarily suspended', {
          banDuration: penalty.banDuration,
          reason: 'Repeated rate limit violations',
        });
      }

      // Check main rate limit
      const result = await AdvancedRateLimiter.checkRateLimit(
        rateLimitKey,
        adjustedLimit,
        rule.windowMs
      );

      // Check burst protection for API endpoints
      if (limiterType === 'api' && !result.allowed) {
        const burstResult = await AdvancedRateLimiter.checkBurstProtection(
          `${rateLimitKey}:burst`,
          Math.ceil(adjustedLimit * 0.1), // 10% of normal limit for burst
          10000 // 10 seconds
        );

        if (!burstResult.allowed) {
          // Record violation for progressive penalties
          await AdvancedRateLimiter.applyProgressivePenalty(identifier, 'burst_violation');
        }
      }

      // Set rate limit headers
      res.set({
        'X-RateLimit-Limit': adjustedLimit.toString(),
        'X-RateLimit-Remaining': result.remaining.toString(),
        'X-RateLimit-Reset': result.resetTime.toString(),
        'X-RateLimit-Used': result.totalUsage.toString(),
      });

      if (penalty.penaltyMultiplier < 1) {
        res.set({
          'X-RateLimit-Penalty': penalty.penaltyMultiplier.toString(),
          'X-RateLimit-Warning': 'Rate limit restrictions applied due to previous violations',
        });
      }

      if (!result.allowed) {
        // Call custom handler if provided
        if (rule.onLimitReached) {
          rule.onLimitReached(req, res);
        }

        throw new RateLimitError('Rate limit exceeded', {
          limit: adjustedLimit,
          used: result.totalUsage,
          resetTime: result.resetTime,
          retryAfter: Math.ceil((result.resetTime * 1000 - Date.now()) / 1000),
        });
      }

      next();
    } catch (error) {
      if (error instanceof RateLimitError) {
        throw error;
      }

      Logger.error('Rate limiting middleware error', error as Error);
      next(); // Allow request to proceed on middleware error
    }
  };
};

// ============================================================================
// SPECIALIZED RATE LIMITERS
// ============================================================================

export const apiRateLimit = createRateLimit('api');

export const uploadRateLimit = createRateLimit('upload', {
  keyGenerator: (req) => `upload:${req.user?.id || req.ip}`,
  skip: (req) => req.method === 'GET', // Skip GET requests for uploads
});

export const aiRateLimit = createRateLimit('ai', {
  keyGenerator: (req) => `ai:${req.user?.id || req.ip}`,
  onLimitReached: (req, res) => {
    Logger.warn('AI rate limit exceeded', {
      userId: req.user?.id,
      ip: req.ip,
      endpoint: req.path,
    });
  },
});

export const websocketRateLimit = createRateLimit('websocket', {
  keyGenerator: (req) => `ws:${req.user?.id || req.ip}`,
});

// ============================================================================
// AUTHENTICATION RATE LIMITING
// ============================================================================

export const authRateLimit = createRateLimit('api', {
  maxRequests: 5, // Very restrictive for auth endpoints
  windowMs: 15 * 60 * 1000, // 15 minutes
  keyGenerator: (req) => `auth:${req.ip}`, // IP-based for auth
  onLimitReached: (req, res) => {
    Logger.security('Authentication rate limit exceeded', {
      ip: req.ip,
      userAgent: req.get('User-Agent'),
      endpoint: req.path,
    });
  },
});

// ============================================================================
// RATE LIMIT MONITORING
// ============================================================================

export class RateLimitMonitor {
  /**
   * Get rate limit statistics for monitoring
   */
  static async getStatistics(timeframe: 'hour' | 'day' = 'hour'): Promise<{
    totalRequests: number;
    blockedRequests: number;
    topLimitedIPs: Array<{ ip: string; violations: number }>;
    topLimitedUsers: Array<{ userId: string; violations: number }>;
  }> {
    try {
      const timeKey = timeframe === 'hour' ?
        new Date().toISOString().slice(0, 13) : // YYYY-MM-DDTHH
        new Date().toISOString().slice(0, 10);  // YYYY-MM-DD

      const [totalRequests, blockedRequests] = await Promise.all([
        RedisService.getCache(`stats:requests:${timeKey}`) || '0',
        RedisService.getCache(`stats:blocked:${timeKey}`) || '0',
      ]);

      // Get top violators (this would need more complex Redis operations in production)
      const topLimitedIPs: Array<{ ip: string; violations: number }> = [];
      const topLimitedUsers: Array<{ userId: string; violations: number }> = [];

      return {
        totalRequests: parseInt(totalRequests),
        blockedRequests: parseInt(blockedRequests),
        topLimitedIPs,
        topLimitedUsers,
      };
    } catch (error) {
      Logger.error('Failed to get rate limit statistics', error as Error);
      return {
        totalRequests: 0,
        blockedRequests: 0,
        topLimitedIPs: [],
        topLimitedUsers: [],
      };
    }
  }

  /**
   * Alert on suspicious activity
   */
  static async checkSuspiciousActivity(): Promise<void> {
    try {
      const stats = await this.getStatistics('hour');

      // Alert if blocked requests exceed threshold
      if (stats.blockedRequests > 1000) {
        Logger.security('High rate limit violations detected', {
          blockedRequests: stats.blockedRequests,
          totalRequests: stats.totalRequests,
          blockRatio: stats.blockedRequests / stats.totalRequests,
        });
      }

      // Check for potential DDoS
      if (stats.totalRequests > 100000) {
        Logger.security('Potential DDoS attack detected', {
          totalRequests: stats.totalRequests,
          timestamp: new Date(),
        });
      }
    } catch (error) {
      Logger.error('Suspicious activity check failed', error as Error);
    }
  }
}

// ============================================================================
// EXPORTS
// ============================================================================

export {
  AdvancedRateLimiter,
  createRateLimit,
  RateLimitMonitor,
};