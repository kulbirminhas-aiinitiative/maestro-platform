import { PrismaClient, Prisma } from '@prisma/client';
import { prisma } from '@/config/database';
import { Logger } from '@/config/logger';
import { RedisService } from '@/config/redis';

/**
 * Transaction options for controlling transaction behavior
 */
export interface TransactionOptions {
  maxWait?: number; // Maximum time to wait for a transaction slot (ms)
  timeout?: number; // Maximum time to execute the transaction (ms)
  isolationLevel?: Prisma.TransactionIsolationLevel;
}

/**
 * Transaction context for passing transaction instance to services
 */
export type TransactionContext = Omit<PrismaClient, '$connect' | '$disconnect' | '$on' | '$transaction' | '$use'>;

/**
 * Result of a transaction operation
 */
export interface TransactionResult<T> {
  success: boolean;
  data?: T;
  error?: Error;
  rollbackReason?: string;
  duration: number;
}

/**
 * Service for managing database transactions with comprehensive error handling
 * and rollback strategies for complex business operations
 */
export class TransactionService {
  private static readonly DEFAULT_OPTIONS: TransactionOptions = {
    maxWait: 5000, // 5 seconds
    timeout: 10000, // 10 seconds
    isolationLevel: Prisma.TransactionIsolationLevel.ReadCommitted,
  };

  /**
   * Execute a function within a database transaction
   */
  static async execute<T>(
    operation: (tx: TransactionContext) => Promise<T>,
    options: TransactionOptions = {}
  ): Promise<TransactionResult<T>> {
    const startTime = Date.now();
    const mergedOptions = { ...this.DEFAULT_OPTIONS, ...options };
    const operationId = Math.random().toString(36).substring(2, 15);

    Logger.business(`Starting transaction`, {
      operationId,
      options: mergedOptions,
      timestamp: new Date().toISOString(),
    });

    try {
      const result = await prisma.$transaction(
        async (tx) => {
          Logger.business(`Executing transaction operation`, {
            operationId,
            timestamp: new Date().toISOString(),
          });

          return await operation(tx);
        },
        {
          maxWait: mergedOptions.maxWait,
          timeout: mergedOptions.timeout,
          isolationLevel: mergedOptions.isolationLevel,
        }
      );

      const duration = Date.now() - startTime;

      Logger.business(`Transaction completed successfully`, {
        operationId,
        duration,
        timestamp: new Date().toISOString(),
      });

      return {
        success: true,
        data: result,
        duration,
      };
    } catch (error) {
      const duration = Date.now() - startTime;

      Logger.error(`Transaction failed and rolled back`, error as Error, {
        operationId,
        duration,
        timestamp: new Date().toISOString(),
      });

      return {
        success: false,
        error: error as Error,
        duration,
        rollbackReason: (error as Error).message,
      };
    }
  }

  /**
   * Execute multiple operations in a single transaction with compensation actions
   */
  static async executeWithCompensation<T>(
    operations: Array<{
      name: string;
      execute: (tx: TransactionContext) => Promise<any>;
      compensate?: (tx: TransactionContext, result?: any) => Promise<void>;
    }>,
    options: TransactionOptions = {}
  ): Promise<TransactionResult<T[]>> {
    const startTime = Date.now();
    const operationId = Math.random().toString(36).substring(2, 15);
    const results: any[] = [];
    const executedOperations: Array<{ name: string; result: any; compensate?: Function }> = [];

    Logger.business(`Starting compensated transaction`, {
      operationId,
      operationCount: operations.length,
      timestamp: new Date().toISOString(),
    });

    try {
      const result = await this.execute(async (tx) => {
        for (const operation of operations) {
          try {
            Logger.business(`Executing operation: ${operation.name}`, {
              operationId,
              operation: operation.name,
            });

            const opResult = await operation.execute(tx);
            results.push(opResult);
            executedOperations.push({
              name: operation.name,
              result: opResult,
              compensate: operation.compensate,
            });

            Logger.business(`Operation completed: ${operation.name}`, {
              operationId,
              operation: operation.name,
            });
          } catch (error) {
            Logger.error(`Operation failed: ${operation.name}`, error as Error, {
              operationId,
              operation: operation.name,
            });

            // Run compensation actions for previously executed operations
            await this.runCompensationActions(tx, executedOperations.reverse(), operationId);
            throw error;
          }
        }

        return results;
      }, options);

      const duration = Date.now() - startTime;

      Logger.business(`Compensated transaction completed successfully`, {
        operationId,
        duration,
        operationCount: operations.length,
      });

      return result as TransactionResult<T[]>;
    } catch (error) {
      const duration = Date.now() - startTime;

      Logger.error(`Compensated transaction failed`, error as Error, {
        operationId,
        duration,
        operationCount: operations.length,
      });

      return {
        success: false,
        error: error as Error,
        duration,
        rollbackReason: `Failed during operation execution: ${(error as Error).message}`,
      };
    }
  }

  /**
   * Execute operations with distributed locking using Redis
   */
  static async executeWithLock<T>(
    lockKey: string,
    operation: (tx: TransactionContext) => Promise<T>,
    options: TransactionOptions & { lockTtl?: number } = {}
  ): Promise<TransactionResult<T>> {
    const lockTtl = options.lockTtl || 30000; // 30 seconds default
    const operationId = Math.random().toString(36).substring(2, 15);
    const fullLockKey = `lock:${lockKey}`;

    Logger.business(`Attempting to acquire lock`, {
      operationId,
      lockKey: fullLockKey,
      lockTtl,
    });

    // Try to acquire lock
    const lockAcquired = await RedisService.setCache(
      fullLockKey,
      operationId,
      lockTtl / 1000,
      'NX' // Only set if not exists
    );

    if (!lockAcquired) {
      Logger.warning(`Failed to acquire lock`, {
        operationId,
        lockKey: fullLockKey,
      });

      return {
        success: false,
        error: new Error(`Could not acquire lock for key: ${lockKey}`),
        duration: 0,
        rollbackReason: 'Lock acquisition failed',
      };
    }

    Logger.business(`Lock acquired, executing transaction`, {
      operationId,
      lockKey: fullLockKey,
    });

    try {
      const result = await this.execute(operation, options);

      // Release lock
      await RedisService.deleteCache(fullLockKey);

      Logger.business(`Transaction completed and lock released`, {
        operationId,
        lockKey: fullLockKey,
        success: result.success,
      });

      return result;
    } catch (error) {
      // Always release lock, even on error
      await RedisService.deleteCache(fullLockKey);

      Logger.error(`Transaction failed, lock released`, error as Error, {
        operationId,
        lockKey: fullLockKey,
      });

      throw error;
    }
  }

  /**
   * Execute a series of operations with rollback points
   */
  static async executeWithSavepoints<T>(
    operations: Array<{
      name: string;
      operation: (tx: TransactionContext) => Promise<any>;
      rollbackToOnError?: string; // Savepoint name to rollback to
    }>,
    options: TransactionOptions = {}
  ): Promise<TransactionResult<T[]>> {
    const operationId = Math.random().toString(36).substring(2, 15);
    const startTime = Date.now();

    Logger.business(`Starting transaction with savepoints`, {
      operationId,
      operationCount: operations.length,
    });

    try {
      const result = await this.execute(async (tx) => {
        const results: any[] = [];
        const savepoints: Record<string, boolean> = {};

        for (const [index, operation] of operations.entries()) {
          const savepointName = `sp_${operation.name}_${index}`;

          try {
            // Create savepoint
            await tx.$executeRaw`SAVEPOINT ${Prisma.raw(savepointName)}`;
            savepoints[savepointName] = true;

            Logger.business(`Created savepoint and executing: ${operation.name}`, {
              operationId,
              savepoint: savepointName,
            });

            const opResult = await operation.operation(tx);
            results.push(opResult);

            Logger.business(`Operation completed: ${operation.name}`, {
              operationId,
              savepoint: savepointName,
            });
          } catch (error) {
            Logger.error(`Operation failed: ${operation.name}`, error as Error, {
              operationId,
              savepoint: savepointName,
            });

            // Rollback to specified savepoint or current one
            const rollbackTarget = operation.rollbackToOnError || savepointName;

            if (savepoints[rollbackTarget]) {
              await tx.$executeRaw`ROLLBACK TO SAVEPOINT ${Prisma.raw(rollbackTarget)}`;

              Logger.business(`Rolled back to savepoint: ${rollbackTarget}`, {
                operationId,
                originalSavepoint: savepointName,
                rollbackTarget,
              });
            }

            throw new Error(`Operation '${operation.name}' failed: ${(error as Error).message}`);
          }
        }

        return results;
      }, options);

      const duration = Date.now() - startTime;

      Logger.business(`Savepoint transaction completed successfully`, {
        operationId,
        duration,
        operationCount: operations.length,
      });

      return result as TransactionResult<T[]>;
    } catch (error) {
      const duration = Date.now() - startTime;

      Logger.error(`Savepoint transaction failed`, error as Error, {
        operationId,
        duration,
        operationCount: operations.length,
      });

      return {
        success: false,
        error: error as Error,
        duration,
        rollbackReason: (error as Error).message,
      };
    }
  }

  /**
   * Execute operations in batch with partial failure handling
   */
  static async executeBatch<T>(
    operations: Array<{
      id: string;
      operation: (tx: TransactionContext) => Promise<T>;
    }>,
    options: TransactionOptions & { continueOnError?: boolean } = {}
  ): Promise<{
    successful: Array<{ id: string; result: T }>;
    failed: Array<{ id: string; error: Error }>;
    duration: number;
  }> {
    const operationId = Math.random().toString(36).substring(2, 15);
    const startTime = Date.now();
    const successful: Array<{ id: string; result: T }> = [];
    const failed: Array<{ id: string; error: Error }> = [];

    Logger.business(`Starting batch transaction`, {
      operationId,
      operationCount: operations.length,
      continueOnError: options.continueOnError,
    });

    if (options.continueOnError) {
      // Execute each operation in its own transaction
      for (const op of operations) {
        const result = await this.execute(op.operation, options);

        if (result.success && result.data) {
          successful.push({ id: op.id, result: result.data });
        } else if (result.error) {
          failed.push({ id: op.id, error: result.error });
        }
      }
    } else {
      // Execute all operations in a single transaction
      const result = await this.execute(async (tx) => {
        const results: Array<{ id: string; result: T }> = [];

        for (const op of operations) {
          try {
            const opResult = await op.operation(tx);
            results.push({ id: op.id, result: opResult });
          } catch (error) {
            Logger.error(`Batch operation failed: ${op.id}`, error as Error, {
              operationId,
            });
            throw error;
          }
        }

        return results;
      }, options);

      if (result.success && result.data) {
        successful.push(...result.data);
      } else if (result.error) {
        // All operations failed
        operations.forEach(op => {
          failed.push({ id: op.id, error: result.error! });
        });
      }
    }

    const duration = Date.now() - startTime;

    Logger.business(`Batch transaction completed`, {
      operationId,
      duration,
      successCount: successful.length,
      failureCount: failed.length,
    });

    return { successful, failed, duration };
  }

  /**
   * Run compensation actions for failed operations
   */
  private static async runCompensationActions(
    tx: TransactionContext,
    executedOperations: Array<{ name: string; result: any; compensate?: Function }>,
    operationId: string
  ): Promise<void> {
    Logger.business(`Running compensation actions`, {
      operationId,
      operationCount: executedOperations.length,
    });

    for (const operation of executedOperations) {
      if (operation.compensate) {
        try {
          Logger.business(`Running compensation for: ${operation.name}`, {
            operationId,
            operation: operation.name,
          });

          await operation.compensate(tx, operation.result);

          Logger.business(`Compensation completed for: ${operation.name}`, {
            operationId,
            operation: operation.name,
          });
        } catch (compensationError) {
          Logger.error(`Compensation failed for: ${operation.name}`, compensationError as Error, {
            operationId,
            operation: operation.name,
          });
          // Don't throw here as we want to continue with other compensations
        }
      }
    }
  }

  /**
   * Health check for transaction service
   */
  static async healthCheck(): Promise<{
    healthy: boolean;
    details: Record<string, any>;
  }> {
    try {
      const testResult = await this.execute(async (tx) => {
        // Simple test query
        await tx.$queryRaw`SELECT 1 as test`;
        return true;
      });

      return {
        healthy: testResult.success,
        details: {
          transactionSupport: testResult.success,
          duration: testResult.duration,
          timestamp: new Date().toISOString(),
        },
      };
    } catch (error) {
      return {
        healthy: false,
        details: {
          error: (error as Error).message,
          timestamp: new Date().toISOString(),
        },
      };
    }
  }
}

/**
 * Decorator for automatic transaction wrapping
 */
export function WithTransaction(options: TransactionOptions = {}) {
  return function (target: any, propertyName: string, descriptor: PropertyDescriptor) {
    const method = descriptor.value;

    descriptor.value = async function (...args: any[]) {
      const result = await TransactionService.execute(async (tx) => {
        // Replace prisma instance with transaction context
        const originalPrisma = (this as any).prisma || prisma;
        (this as any).prisma = tx;

        try {
          return await method.apply(this, args);
        } finally {
          // Restore original prisma instance
          (this as any).prisma = originalPrisma;
        }
      }, options);

      if (!result.success) {
        throw result.error;
      }

      return result.data;
    };

    return descriptor;
  };
}

/**
 * Utility functions for common transaction patterns
 */
export class TransactionUtils {
  /**
   * Create a board with all related entities in a single transaction
   */
  static async createBoardWithRelations(data: {
    board: any;
    columns: any[];
    members: any[];
    items?: any[];
  }): Promise<TransactionResult<any>> {
    return TransactionService.executeWithCompensation([
      {
        name: 'create_board',
        execute: async (tx) => {
          const board = await tx.board.create({ data: data.board });
          return board;
        },
      },
      {
        name: 'create_columns',
        execute: async (tx) => {
          if (data.columns.length === 0) return [];

          const columns = await Promise.all(
            data.columns.map((column, index) =>
              tx.boardColumn.create({
                data: {
                  ...column,
                  boardId: data.board.id,
                  position: index,
                },
              })
            )
          );
          return columns;
        },
      },
      {
        name: 'create_members',
        execute: async (tx) => {
          if (data.members.length === 0) return [];

          const members = await Promise.all(
            data.members.map(member =>
              tx.boardMember.create({
                data: {
                  ...member,
                  boardId: data.board.id,
                },
              })
            )
          );
          return members;
        },
      },
      {
        name: 'create_items',
        execute: async (tx) => {
          if (!data.items || data.items.length === 0) return [];

          const items = await Promise.all(
            data.items.map(item =>
              tx.item.create({
                data: {
                  ...item,
                  boardId: data.board.id,
                },
              })
            )
          );
          return items;
        },
      },
    ]);
  }

  /**
   * Bulk update items with dependency validation
   */
  static async bulkUpdateItems(
    itemUpdates: Array<{ id: string; data: any }>
  ): Promise<TransactionResult<any[]>> {
    return TransactionService.execute(async (tx) => {
      const results = [];

      for (const update of itemUpdates) {
        // Check if item exists and user has permissions
        const existingItem = await tx.item.findUnique({
          where: { id: update.id },
          include: { board: true },
        });

        if (!existingItem) {
          throw new Error(`Item ${update.id} not found`);
        }

        // Validate dependencies if moving items
        if (update.data.parentId) {
          await this.validateItemDependencies(tx, update.id, update.data.parentId);
        }

        const updatedItem = await tx.item.update({
          where: { id: update.id },
          data: update.data,
        });

        results.push(updatedItem);
      }

      return results;
    });
  }

  /**
   * Validate item dependencies to prevent circular references
   */
  private static async validateItemDependencies(
    tx: TransactionContext,
    itemId: string,
    parentId: string
  ): Promise<void> {
    // Check for circular dependencies
    const checkCircular = async (currentId: string, targetId: string, visited = new Set<string>()): Promise<boolean> => {
      if (visited.has(currentId)) return true;
      if (currentId === targetId) return true;

      visited.add(currentId);

      const children = await tx.item.findMany({
        where: { parentId: currentId },
        select: { id: true },
      });

      for (const child of children) {
        if (await checkCircular(child.id, targetId, visited)) {
          return true;
        }
      }

      return false;
    };

    const hasCircularDependency = await checkCircular(parentId, itemId);

    if (hasCircularDependency) {
      throw new Error(`Circular dependency detected: cannot set ${parentId} as parent of ${itemId}`);
    }
  }
}