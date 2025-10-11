import Redis from 'ioredis';
import { logger } from './logger';

// Redis configuration
const redisConfig = {
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379'),
  password: process.env.REDIS_PASSWORD || undefined,
  retryDelayOnFailover: 100,
  enableOfflineQueue: false,
  maxRetriesPerRequest: 3,
  lazyConnect: true,
  keepAlive: 30000,
  connectTimeout: 10000,
  commandTimeout: 5000,
};

// Main Redis client
export const redis = new Redis(redisConfig);

// Pub/Sub Redis clients (separate instances recommended)
export const redisPub = new Redis(redisConfig);
export const redisSub = new Redis(redisConfig);

// Redis event handlers
redis.on('connect', () => {
  logger.info('Redis connected');
});

redis.on('ready', () => {
  logger.info('Redis ready');
});

redis.on('error', (error) => {
  logger.error('Redis error:', error);
});

redis.on('close', () => {
  logger.warn('Redis connection closed');
});

redis.on('reconnecting', (delay) => {
  logger.info(`Redis reconnecting in ${delay}ms`);
});

// Redis utility functions
export class RedisService {
  /**
   * Set cache with TTL
   */
  static async setCache(key: string, value: any, ttl: number = 3600): Promise<void> {
    try {
      await redis.setex(key, ttl, JSON.stringify(value));
    } catch (error) {
      logger.error('Redis setCache error:', error);
      throw error;
    }
  }

  /**
   * Get cached value
   */
  static async getCache<T>(key: string): Promise<T | null> {
    try {
      const value = await redis.get(key);
      return value ? JSON.parse(value) : null;
    } catch (error) {
      logger.error('Redis getCache error:', error);
      return null;
    }
  }

  /**
   * Delete cache key
   */
  static async deleteCache(key: string): Promise<number> {
    try {
      return await redis.del(key);
    } catch (error) {
      logger.error('Redis deleteCache error:', error);
      return 0;
    }
  }

  /**
   * Delete multiple cache keys by pattern
   */
  static async deleteCachePattern(pattern: string): Promise<number> {
    try {
      const keys = await redis.keys(pattern);
      if (keys.length === 0) return 0;
      return await redis.del(...keys);
    } catch (error) {
      logger.error('Redis deleteCachePattern error:', error);
      return 0;
    }
  }

  /**
   * Set user session
   */
  static async setSession(sessionId: string, userData: any, ttl: number = 86400): Promise<void> {
    await this.setCache(`session:${sessionId}`, userData, ttl);
  }

  /**
   * Get user session
   */
  static async getSession(sessionId: string): Promise<any> {
    return await this.getCache(`session:${sessionId}`);
  }

  /**
   * Delete user session
   */
  static async deleteSession(sessionId: string): Promise<number> {
    return await this.deleteCache(`session:${sessionId}`);
  }

  /**
   * Publish real-time update
   */
  static async publishUpdate(channel: string, data: any): Promise<number> {
    try {
      return await redisPub.publish(channel, JSON.stringify(data));
    } catch (error) {
      logger.error('Redis publishUpdate error:', error);
      return 0;
    }
  }

  /**
   * Subscribe to real-time updates
   */
  static async subscribe(channel: string, callback: (data: any) => void): Promise<void> {
    try {
      await redisSub.subscribe(channel);
      redisSub.on('message', (receivedChannel, message) => {
        if (receivedChannel === channel) {
          try {
            const data = JSON.parse(message);
            callback(data);
          } catch (error) {
            logger.error('Redis message parse error:', error);
          }
        }
      });
    } catch (error) {
      logger.error('Redis subscribe error:', error);
    }
  }

  /**
   * Rate limiting
   */
  static async checkRateLimit(
    key: string,
    limit: number,
    windowMs: number
  ): Promise<{ allowed: boolean; remaining: number; resetTime: number }> {
    try {
      const current = await redis.incr(key);
      const ttl = await redis.ttl(key);

      if (current === 1) {
        await redis.expire(key, Math.ceil(windowMs / 1000));
      }

      const resetTime = Date.now() + (ttl > 0 ? ttl * 1000 : windowMs);
      const remaining = Math.max(0, limit - current);

      return {
        allowed: current <= limit,
        remaining,
        resetTime,
      };
    } catch (error) {
      logger.error('Redis rate limit error:', error);
      return { allowed: true, remaining: limit, resetTime: Date.now() + windowMs };
    }
  }

  /**
   * Cache board data
   */
  static async cacheBoardData(boardId: string, data: any, ttl: number = 1800): Promise<void> {
    await this.setCache(`board:${boardId}`, data, ttl);
  }

  /**
   * Get cached board data
   */
  static async getCachedBoardData(boardId: string): Promise<any> {
    return await this.getCache(`board:${boardId}`);
  }

  /**
   * Invalidate board cache
   */
  static async invalidateBoardCache(boardId: string): Promise<void> {
    await this.deleteCache(`board:${boardId}`);
    await this.deleteCachePattern(`board:${boardId}:*`);
  }

  /**
   * Cache user permissions
   */
  static async cacheUserPermissions(
    userId: string,
    orgId: string,
    permissions: any,
    ttl: number = 3600
  ): Promise<void> {
    await this.setCache(`permissions:${userId}:${orgId}`, permissions, ttl);
  }

  /**
   * Get cached user permissions
   */
  static async getCachedUserPermissions(userId: string, orgId: string): Promise<any> {
    return await this.getCache(`permissions:${userId}:${orgId}`);
  }

  /**
   * Set hash field
   */
  static async setHash(
    key: string,
    field: string,
    value: string,
    ttl?: number
  ): Promise<void> {
    try {
      await redis.hset(key, field, value);
      if (ttl) {
        await redis.expire(key, ttl);
      }
    } catch (error) {
      logger.error('Redis setHash error:', error);
      throw error;
    }
  }

  /**
   * Get hash field
   */
  static async getHashField(key: string, field: string): Promise<string | null> {
    try {
      return await redis.hget(key, field);
    } catch (error) {
      logger.error('Redis getHashField error:', error);
      return null;
    }
  }

  /**
   * Get all hash fields
   */
  static async getAllHashFields(key: string): Promise<Record<string, string>> {
    try {
      return await redis.hgetall(key);
    } catch (error) {
      logger.error('Redis getAllHashFields error:', error);
      return {};
    }
  }

  /**
   * Delete hash field
   */
  static async deleteHashField(key: string, field: string): Promise<number> {
    try {
      return await redis.hdel(key, field);
    } catch (error) {
      logger.error('Redis deleteHashField error:', error);
      return 0;
    }
  }

  /**
   * Set if not exists
   */
  static async setIfNotExists(
    key: string,
    value: string,
    ttl?: number
  ): Promise<boolean> {
    try {
      let result;
      if (ttl) {
        result = await redis.set(key, value, 'EX', ttl, 'NX');
      } else {
        result = await redis.set(key, value, 'NX');
      }
      return result === 'OK';
    } catch (error) {
      logger.error('Redis setIfNotExists error:', error);
      return false;
    }
  }

  /**
   * Get keys by pattern
   */
  static async getKeysByPattern(pattern: string): Promise<string[]> {
    try {
      return await redis.keys(pattern);
    } catch (error) {
      logger.error('Redis getKeysByPattern error:', error);
      return [];
    }
  }
}

// Health check
export const checkRedisHealth = async (): Promise<boolean> => {
  try {
    await redis.ping();
    return true;
  } catch (error) {
    logger.error('Redis health check failed:', error);
    return false;
  }
};

// Graceful shutdown
export const disconnectRedis = async (): Promise<void> => {
  try {
    await redis.quit();
    await redisPub.quit();
    await redisSub.quit();
    logger.info('Redis connections closed');
  } catch (error) {
    logger.error('Error closing Redis connections:', error);
  }
};

export default redis;