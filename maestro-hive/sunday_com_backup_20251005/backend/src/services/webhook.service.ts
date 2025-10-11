import { prisma } from '@/config/database';
import { RedisService } from '@/config/redis';
import { Logger } from '@/config/logger';
import {
  CreateWebhookData,
  UpdateWebhookData,
  WebhookEvent,
  WebhookDelivery,
  PaginatedResult,
  PaginationMeta,
} from '@/types';
import { Webhook, WebhookDelivery as PrismaWebhookDelivery } from '@prisma/client';
import crypto from 'crypto';
import axios, { AxiosError } from 'axios';

type WebhookWithDeliveries = Webhook & {
  deliveries?: PrismaWebhookDelivery[];
  _count?: {
    deliveries: number;
  };
};

export class WebhookService {
  private static readonly MAX_RETRY_ATTEMPTS = 3;
  private static readonly RETRY_DELAYS = [1000, 5000, 15000]; // 1s, 5s, 15s
  private static readonly DELIVERY_TIMEOUT = 30000; // 30 seconds

  /**
   * Create a new webhook
   */
  static async create(
    data: CreateWebhookData,
    userId: string
  ): Promise<WebhookWithDeliveries> {
    try {
      // Check if user has access to create webhooks for the resource
      const hasAccess = await this.checkCreateAccess(data, userId);
      if (!hasAccess) {
        throw new Error('Access denied to create webhook');
      }

      // Generate webhook secret
      const secret = this.generateWebhookSecret();

      const webhook = await prisma.webhook.create({
        data: {
          ...data,
          secret,
          createdBy: userId,
          isActive: true,
        },
        include: {
          _count: {
            select: {
              deliveries: true,
            },
          },
        },
      });

      Logger.business(`Webhook created: ${webhook.url}`, {
        webhookId: webhook.id,
        events: webhook.events,
        userId,
      });

      return webhook;
    } catch (error) {
      Logger.error('Webhook creation failed', error as Error);
      throw error;
    }
  }

  /**
   * Get webhook by ID
   */
  static async getById(
    webhookId: string,
    userId: string,
    includeDeliveries = false
  ): Promise<WebhookWithDeliveries | null> {
    try {
      const webhook = await prisma.webhook.findFirst({
        where: {
          id: webhookId,
          deletedAt: null,
        },
        include: {
          deliveries: includeDeliveries
            ? {
                orderBy: { createdAt: 'desc' },
                take: 50, // Latest 50 deliveries
              }
            : false,
          _count: {
            select: {
              deliveries: true,
            },
          },
        },
      });

      if (!webhook) {
        return null;
      }

      // Check access
      const hasAccess = await this.checkWebhookAccess(webhook, userId);
      if (!hasAccess) {
        throw new Error('Access denied to webhook');
      }

      return webhook;
    } catch (error) {
      Logger.error('Get webhook failed', error as Error);
      throw error;
    }
  }

  /**
   * Get webhooks for a resource
   */
  static async getByResource(
    resourceType: 'organization' | 'workspace' | 'board',
    resourceId: string,
    userId: string,
    page = 1,
    limit = 20
  ): Promise<PaginatedResult<WebhookWithDeliveries>> {
    try {
      // Check access to resource
      const hasAccess = await this.checkResourceAccess(resourceType, resourceId, userId);
      if (!hasAccess) {
        throw new Error('Access denied to resource');
      }

      const offset = (page - 1) * limit;

      const whereClause = {
        [resourceType + 'Id']: resourceId,
        deletedAt: null,
      };

      const [webhooks, total] = await Promise.all([
        prisma.webhook.findMany({
          where: whereClause,
          include: {
            _count: {
              select: {
                deliveries: true,
              },
            },
          },
          orderBy: { createdAt: 'desc' },
          skip: offset,
          take: limit,
        }),
        prisma.webhook.count({
          where: whereClause,
        }),
      ]);

      const meta: PaginationMeta = {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
        hasNext: page * limit < total,
        hasPrev: page > 1,
      };

      return { data: webhooks, meta };
    } catch (error) {
      Logger.error('Get webhooks by resource failed', error as Error);
      throw error;
    }
  }

  /**
   * Update webhook
   */
  static async update(
    webhookId: string,
    data: UpdateWebhookData,
    userId: string
  ): Promise<WebhookWithDeliveries> {
    try {
      const existingWebhook = await prisma.webhook.findUnique({
        where: { id: webhookId },
      });

      if (!existingWebhook) {
        throw new Error('Webhook not found');
      }

      // Check access
      const hasAccess = await this.checkWebhookAccess(existingWebhook, userId);
      if (!hasAccess) {
        throw new Error('Access denied to webhook');
      }

      const webhook = await prisma.webhook.update({
        where: { id: webhookId },
        data,
        include: {
          _count: {
            select: {
              deliveries: true,
            },
          },
        },
      });

      Logger.business(`Webhook updated`, {
        webhookId,
        userId,
      });

      return webhook;
    } catch (error) {
      Logger.error('Webhook update failed', error as Error);
      throw error;
    }
  }

  /**
   * Delete webhook
   */
  static async delete(webhookId: string, userId: string): Promise<void> {
    try {
      const existingWebhook = await prisma.webhook.findUnique({
        where: { id: webhookId },
      });

      if (!existingWebhook) {
        throw new Error('Webhook not found');
      }

      // Check access
      const hasAccess = await this.checkWebhookAccess(existingWebhook, userId);
      if (!hasAccess) {
        throw new Error('Access denied to webhook');
      }

      await prisma.webhook.update({
        where: { id: webhookId },
        data: { deletedAt: new Date() },
      });

      Logger.business(`Webhook deleted`, {
        webhookId,
        userId,
      });
    } catch (error) {
      Logger.error('Webhook deletion failed', error as Error);
      throw error;
    }
  }

  /**
   * Trigger webhook event
   */
  static async triggerEvent(event: WebhookEvent): Promise<void> {
    try {
      // Find all active webhooks that should receive this event
      const webhooks = await this.findRelevantWebhooks(event);

      // Process each webhook
      await Promise.allSettled(
        webhooks.map(webhook => this.deliverWebhook(webhook, event))
      );
    } catch (error) {
      Logger.error('Trigger webhook event failed', error as Error);
      // Don't throw error to avoid disrupting main application flow
    }
  }

  /**
   * Deliver webhook to endpoint
   */
  static async deliverWebhook(webhook: Webhook, event: WebhookEvent): Promise<void> {
    const deliveryId = crypto.randomUUID();

    try {
      // Create delivery record
      const delivery = await prisma.webhookDelivery.create({
        data: {
          id: deliveryId,
          webhookId: webhook.id,
          eventType: event.type,
          payload: event.data,
          status: 'pending',
          attempt: 1,
        },
      });

      // Prepare payload
      const payload = {
        id: deliveryId,
        event: event.type,
        timestamp: new Date().toISOString(),
        data: event.data,
      };

      // Generate signature
      const signature = this.generateSignature(JSON.stringify(payload), webhook.secret);

      // Make HTTP request
      const response = await axios.post(webhook.url, payload, {
        headers: {
          'Content-Type': 'application/json',
          'X-Webhook-Signature': signature,
          'X-Webhook-Delivery': deliveryId,
          'User-Agent': 'Sunday.com-Webhooks/1.0',
        },
        timeout: this.DELIVERY_TIMEOUT,
        validateStatus: (status) => status >= 200 && status < 300,
      });

      // Update delivery as successful
      await prisma.webhookDelivery.update({
        where: { id: deliveryId },
        data: {
          status: 'delivered',
          responseStatus: response.status,
          responseHeaders: JSON.stringify(response.headers),
          responseBody: response.data ? JSON.stringify(response.data).substring(0, 1000) : null,
          deliveredAt: new Date(),
        },
      });

      Logger.webhook(`Webhook delivered successfully`, {
        webhookId: webhook.id,
        deliveryId,
        url: webhook.url,
        eventType: event.type,
        responseStatus: response.status,
      });
    } catch (error) {
      const isAxiosError = error instanceof AxiosError;
      const errorMessage = isAxiosError ? error.message : (error as Error).message;
      const responseStatus = isAxiosError ? error.response?.status : null;
      const responseBody = isAxiosError ? JSON.stringify(error.response?.data).substring(0, 1000) : null;

      // Update delivery as failed
      await prisma.webhookDelivery.update({
        where: { id: deliveryId },
        data: {
          status: 'failed',
          responseStatus,
          responseBody,
          errorMessage,
          failedAt: new Date(),
        },
      });

      Logger.webhook(`Webhook delivery failed`, {
        webhookId: webhook.id,
        deliveryId,
        url: webhook.url,
        eventType: event.type,
        error: errorMessage,
        responseStatus,
      });

      // Schedule retry if within retry limits
      await this.scheduleRetry(webhook, event, deliveryId, 1);
    }
  }

  /**
   * Retry webhook delivery
   */
  static async retryDelivery(deliveryId: string, userId: string): Promise<void> {
    try {
      const delivery = await prisma.webhookDelivery.findUnique({
        where: { id: deliveryId },
        include: { webhook: true },
      });

      if (!delivery) {
        throw new Error('Delivery not found');
      }

      // Check access
      const hasAccess = await this.checkWebhookAccess(delivery.webhook, userId);
      if (!hasAccess) {
        throw new Error('Access denied to webhook');
      }

      if (delivery.status === 'delivered') {
        throw new Error('Delivery already successful');
      }

      // Create new delivery attempt
      const newDeliveryId = crypto.randomUUID();
      const newAttempt = delivery.attempt + 1;

      if (newAttempt > this.MAX_RETRY_ATTEMPTS) {
        throw new Error('Maximum retry attempts exceeded');
      }

      // Reconstruct event
      const event: WebhookEvent = {
        type: delivery.eventType,
        data: delivery.payload as any,
        timestamp: new Date(),
      };

      await this.deliverWebhook(delivery.webhook, event);
    } catch (error) {
      Logger.error('Retry webhook delivery failed', error as Error);
      throw error;
    }
  }

  /**
   * Get webhook deliveries
   */
  static async getDeliveries(
    webhookId: string,
    userId: string,
    page = 1,
    limit = 50
  ): Promise<PaginatedResult<PrismaWebhookDelivery>> {
    try {
      const webhook = await prisma.webhook.findUnique({
        where: { id: webhookId },
      });

      if (!webhook) {
        throw new Error('Webhook not found');
      }

      // Check access
      const hasAccess = await this.checkWebhookAccess(webhook, userId);
      if (!hasAccess) {
        throw new Error('Access denied to webhook');
      }

      const offset = (page - 1) * limit;

      const [deliveries, total] = await Promise.all([
        prisma.webhookDelivery.findMany({
          where: { webhookId },
          orderBy: { createdAt: 'desc' },
          skip: offset,
          take: limit,
        }),
        prisma.webhookDelivery.count({
          where: { webhookId },
        }),
      ]);

      const meta: PaginationMeta = {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
        hasNext: page * limit < total,
        hasPrev: page > 1,
      };

      return { data: deliveries, meta };
    } catch (error) {
      Logger.error('Get webhook deliveries failed', error as Error);
      throw error;
    }
  }

  /**
   * Test webhook endpoint
   */
  static async testWebhook(webhookId: string, userId: string): Promise<{
    success: boolean;
    status?: number;
    error?: string;
    responseTime: number;
  }> {
    try {
      const webhook = await prisma.webhook.findUnique({
        where: { id: webhookId },
      });

      if (!webhook) {
        throw new Error('Webhook not found');
      }

      // Check access
      const hasAccess = await this.checkWebhookAccess(webhook, userId);
      if (!hasAccess) {
        throw new Error('Access denied to webhook');
      }

      const startTime = Date.now();

      // Create test event
      const testEvent: WebhookEvent = {
        type: 'webhook.test',
        data: {
          message: 'This is a test webhook from Sunday.com',
          timestamp: new Date().toISOString(),
          webhookId: webhook.id,
        },
        timestamp: new Date(),
      };

      // Prepare payload
      const payload = {
        id: crypto.randomUUID(),
        event: testEvent.type,
        timestamp: testEvent.timestamp.toISOString(),
        data: testEvent.data,
      };

      // Generate signature
      const signature = this.generateSignature(JSON.stringify(payload), webhook.secret);

      try {
        const response = await axios.post(webhook.url, payload, {
          headers: {
            'Content-Type': 'application/json',
            'X-Webhook-Signature': signature,
            'X-Webhook-Test': 'true',
            'User-Agent': 'Sunday.com-Webhooks/1.0',
          },
          timeout: this.DELIVERY_TIMEOUT,
          validateStatus: (status) => status >= 200 && status < 300,
        });

        const responseTime = Date.now() - startTime;

        return {
          success: true,
          status: response.status,
          responseTime,
        };
      } catch (error) {
        const responseTime = Date.now() - startTime;
        const isAxiosError = error instanceof AxiosError;

        return {
          success: false,
          status: isAxiosError ? error.response?.status : undefined,
          error: error instanceof Error ? error.message : 'Unknown error',
          responseTime,
        };
      }
    } catch (error) {
      Logger.error('Test webhook failed', error as Error);
      throw error;
    }
  }

  // ============================================================================
  // PRIVATE METHODS
  // ============================================================================

  private static generateWebhookSecret(): string {
    return crypto.randomBytes(32).toString('hex');
  }

  private static generateSignature(payload: string, secret: string): string {
    return crypto
      .createHmac('sha256', secret)
      .update(payload)
      .digest('hex');
  }

  private static async findRelevantWebhooks(event: WebhookEvent): Promise<Webhook[]> {
    const whereConditions: any = {
      isActive: true,
      deletedAt: null,
      events: {
        has: event.type,
      },
    };

    // Add resource-specific filters based on event data
    if (event.data.organizationId) {
      whereConditions.organizationId = event.data.organizationId;
    }
    if (event.data.workspaceId) {
      whereConditions.workspaceId = event.data.workspaceId;
    }
    if (event.data.boardId) {
      whereConditions.boardId = event.data.boardId;
    }

    return await prisma.webhook.findMany({
      where: whereConditions,
    });
  }

  private static async scheduleRetry(
    webhook: Webhook,
    event: WebhookEvent,
    deliveryId: string,
    attempt: number
  ): Promise<void> {
    if (attempt >= this.MAX_RETRY_ATTEMPTS) {
      return;
    }

    const delay = this.RETRY_DELAYS[attempt - 1] || this.RETRY_DELAYS[this.RETRY_DELAYS.length - 1];

    // In a production environment, you'd use a proper job queue (Redis, Bull, etc.)
    // For now, we'll use setTimeout for simple retries
    setTimeout(async () => {
      try {
        await this.deliverWebhook(webhook, event);
      } catch (error) {
        Logger.error('Webhook retry failed', error as Error);
      }
    }, delay);
  }

  private static async checkCreateAccess(
    data: CreateWebhookData,
    userId: string
  ): Promise<boolean> {
    try {
      if (data.organizationId) {
        return await this.checkOrganizationAdminAccess(data.organizationId, userId);
      }
      if (data.workspaceId) {
        return await this.checkWorkspaceAdminAccess(data.workspaceId, userId);
      }
      if (data.boardId) {
        return await this.checkBoardAdminAccess(data.boardId, userId);
      }
      return false;
    } catch (error) {
      Logger.error('Failed to check create access', error as Error);
      return false;
    }
  }

  private static async checkWebhookAccess(webhook: Webhook, userId: string): Promise<boolean> {
    try {
      if (webhook.organizationId) {
        return await this.checkOrganizationAdminAccess(webhook.organizationId, userId);
      }
      if (webhook.workspaceId) {
        return await this.checkWorkspaceAdminAccess(webhook.workspaceId, userId);
      }
      if (webhook.boardId) {
        return await this.checkBoardAdminAccess(webhook.boardId, userId);
      }
      return false;
    } catch (error) {
      Logger.error('Failed to check webhook access', error as Error);
      return false;
    }
  }

  private static async checkResourceAccess(
    resourceType: string,
    resourceId: string,
    userId: string
  ): Promise<boolean> {
    try {
      switch (resourceType) {
        case 'organization':
          return await this.checkOrganizationAdminAccess(resourceId, userId);
        case 'workspace':
          return await this.checkWorkspaceAdminAccess(resourceId, userId);
        case 'board':
          return await this.checkBoardAdminAccess(resourceId, userId);
        default:
          return false;
      }
    } catch (error) {
      Logger.error('Failed to check resource access', error as Error);
      return false;
    }
  }

  private static async checkOrganizationAdminAccess(
    organizationId: string,
    userId: string
  ): Promise<boolean> {
    try {
      const member = await prisma.organizationMember.findUnique({
        where: {
          organizationId_userId: {
            organizationId,
            userId,
          },
        },
      });
      return !!member && (member.role === 'admin' || member.role === 'owner');
    } catch (error) {
      Logger.error('Failed to check organization admin access', error as Error);
      return false;
    }
  }

  private static async checkWorkspaceAdminAccess(
    workspaceId: string,
    userId: string
  ): Promise<boolean> {
    try {
      const member = await prisma.workspaceMember.findUnique({
        where: {
          workspaceId_userId: {
            workspaceId,
            userId,
          },
        },
      });
      return !!member && member.role === 'admin';
    } catch (error) {
      Logger.error('Failed to check workspace admin access', error as Error);
      return false;
    }
  }

  private static async checkBoardAdminAccess(boardId: string, userId: string): Promise<boolean> {
    try {
      const member = await prisma.boardMember.findUnique({
        where: {
          boardId_userId: {
            boardId,
            userId,
          },
        },
      });
      return !!member && member.role === 'admin';
    } catch (error) {
      Logger.error('Failed to check board admin access', error as Error);
      return false;
    }
  }
}