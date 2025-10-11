import { WebhookService } from '../services/webhook.service';
import { prisma } from '../config/database';
import { RedisService } from '../config/redis';
import axios from 'axios';
import crypto from 'crypto';

// Mock external dependencies
jest.mock('../config/database', () => ({
  prisma: {
    webhook: {
      create: jest.fn(),
      findFirst: jest.fn(),
      findUnique: jest.fn(),
      findMany: jest.fn(),
      count: jest.fn(),
      update: jest.fn(),
    },
    webhookDelivery: {
      create: jest.fn(),
      findUnique: jest.fn(),
      findMany: jest.fn(),
      count: jest.fn(),
      update: jest.fn(),
    },
    organizationMember: {
      findUnique: jest.fn(),
    },
    workspaceMember: {
      findUnique: jest.fn(),
    },
    boardMember: {
      findUnique: jest.fn(),
    },
  },
}));

jest.mock('../config/redis');
jest.mock('axios');
jest.mock('crypto');

describe('WebhookService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('create', () => {
    const mockUser = { id: 'user-1' };
    const mockWebhookData = {
      url: 'https://example.com/webhook',
      events: ['item.created', 'item.updated'],
      organizationId: 'org-1',
      description: 'Test webhook',
    };

    it('should create webhook successfully', async () => {
      const mockSecret = 'webhook-secret-123';
      const mockWebhook = {
        id: 'webhook-1',
        ...mockWebhookData,
        secret: mockSecret,
        createdBy: mockUser.id,
        isActive: true,
        _count: { deliveries: 0 },
      };

      // Mock admin access check
      (prisma.organizationMember.findUnique as jest.Mock).mockResolvedValue({
        organizationId: mockWebhookData.organizationId,
        userId: mockUser.id,
        role: 'admin',
      });

      // Mock secret generation
      (crypto.randomBytes as jest.Mock).mockReturnValue({
        toString: jest.fn().mockReturnValue(mockSecret),
      });

      (prisma.webhook.create as jest.Mock).mockResolvedValue(mockWebhook);

      const result = await WebhookService.create(mockWebhookData, mockUser.id);

      expect(result).toEqual(mockWebhook);
      expect(prisma.webhook.create).toHaveBeenCalledWith({
        data: expect.objectContaining({
          ...mockWebhookData,
          secret: mockSecret,
          createdBy: mockUser.id,
          isActive: true,
        }),
        include: expect.any(Object),
      });
    });

    it('should throw error when user has no admin access', async () => {
      // Mock no admin access
      (prisma.organizationMember.findUnique as jest.Mock).mockResolvedValue({
        organizationId: mockWebhookData.organizationId,
        userId: mockUser.id,
        role: 'member',
      });

      await expect(
        WebhookService.create(mockWebhookData, mockUser.id)
      ).rejects.toThrow('Access denied to create webhook');
    });
  });

  describe('getById', () => {
    const mockWebhookId = 'webhook-1';
    const mockUserId = 'user-1';

    it('should return webhook when user has access', async () => {
      const mockWebhook = {
        id: mockWebhookId,
        url: 'https://example.com/webhook',
        organizationId: 'org-1',
        _count: { deliveries: 5 },
      };

      (prisma.webhook.findFirst as jest.Mock).mockResolvedValue(mockWebhook);
      (prisma.organizationMember.findUnique as jest.Mock).mockResolvedValue({
        organizationId: mockWebhook.organizationId,
        userId: mockUserId,
        role: 'admin',
      });

      const result = await WebhookService.getById(mockWebhookId, mockUserId);

      expect(result).toEqual(mockWebhook);
    });

    it('should return null when webhook not found', async () => {
      (prisma.webhook.findFirst as jest.Mock).mockResolvedValue(null);

      const result = await WebhookService.getById(mockWebhookId, mockUserId);

      expect(result).toBeNull();
    });

    it('should throw error when user has no access', async () => {
      const mockWebhook = {
        id: mockWebhookId,
        organizationId: 'org-1',
      };

      (prisma.webhook.findFirst as jest.Mock).mockResolvedValue(mockWebhook);
      (prisma.organizationMember.findUnique as jest.Mock).mockResolvedValue(null);

      await expect(
        WebhookService.getById(mockWebhookId, mockUserId)
      ).rejects.toThrow('Access denied to webhook');
    });
  });

  describe('deliverWebhook', () => {
    const mockWebhook = {
      id: 'webhook-1',
      url: 'https://example.com/webhook',
      secret: 'webhook-secret',
      events: ['item.created'],
    };

    const mockEvent = {
      type: 'item.created',
      data: { itemId: 'item-1', name: 'Test Item' },
      timestamp: new Date(),
    };

    it('should deliver webhook successfully', async () => {
      const mockResponse = {
        status: 200,
        headers: { 'content-type': 'application/json' },
        data: { success: true },
      };

      const mockDelivery = {
        id: 'delivery-1',
        webhookId: mockWebhook.id,
        eventType: mockEvent.type,
        payload: mockEvent.data,
        status: 'pending',
        attempt: 1,
      };

      (crypto.randomUUID as jest.Mock).mockReturnValue('delivery-1');
      (crypto.createHmac as jest.Mock).mockReturnValue({
        update: jest.fn().mockReturnThis(),
        digest: jest.fn().mockReturnValue('signature-hash'),
      });

      (prisma.webhookDelivery.create as jest.Mock).mockResolvedValue(mockDelivery);
      (axios.post as jest.Mock).mockResolvedValue(mockResponse);

      await WebhookService.deliverWebhook(mockWebhook, mockEvent);

      expect(axios.post).toHaveBeenCalledWith(
        mockWebhook.url,
        expect.objectContaining({
          event: mockEvent.type,
          data: mockEvent.data,
        }),
        expect.objectContaining({
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
            'X-Webhook-Signature': 'signature-hash',
            'X-Webhook-Delivery': 'delivery-1',
          }),
          timeout: 30000,
        })
      );

      expect(prisma.webhookDelivery.update).toHaveBeenCalledWith({
        where: { id: 'delivery-1' },
        data: expect.objectContaining({
          status: 'delivered',
          responseStatus: 200,
        }),
      });
    });

    it('should handle delivery failure', async () => {
      const mockError = new Error('Network error');
      const mockDelivery = {
        id: 'delivery-1',
        webhookId: mockWebhook.id,
        eventType: mockEvent.type,
        payload: mockEvent.data,
        status: 'pending',
        attempt: 1,
      };

      (crypto.randomUUID as jest.Mock).mockReturnValue('delivery-1');
      (crypto.createHmac as jest.Mock).mockReturnValue({
        update: jest.fn().mockReturnThis(),
        digest: jest.fn().mockReturnValue('signature-hash'),
      });

      (prisma.webhookDelivery.create as jest.Mock).mockResolvedValue(mockDelivery);
      (axios.post as jest.Mock).mockRejectedValue(mockError);

      await WebhookService.deliverWebhook(mockWebhook, mockEvent);

      expect(prisma.webhookDelivery.update).toHaveBeenCalledWith({
        where: { id: 'delivery-1' },
        data: expect.objectContaining({
          status: 'failed',
          errorMessage: 'Network error',
        }),
      });
    });
  });

  describe('testWebhook', () => {
    const mockWebhookId = 'webhook-1';
    const mockUserId = 'user-1';

    it('should test webhook endpoint successfully', async () => {
      const mockWebhook = {
        id: mockWebhookId,
        url: 'https://example.com/webhook',
        secret: 'webhook-secret',
        organizationId: 'org-1',
      };

      const mockResponse = {
        status: 200,
        headers: { 'content-type': 'application/json' },
      };

      (prisma.webhook.findUnique as jest.Mock).mockResolvedValue(mockWebhook);
      (prisma.organizationMember.findUnique as jest.Mock).mockResolvedValue({
        organizationId: mockWebhook.organizationId,
        userId: mockUserId,
        role: 'admin',
      });

      (crypto.randomUUID as jest.Mock).mockReturnValue('test-delivery-1');
      (crypto.createHmac as jest.Mock).mockReturnValue({
        update: jest.fn().mockReturnThis(),
        digest: jest.fn().mockReturnValue('test-signature'),
      });

      (axios.post as jest.Mock).mockResolvedValue(mockResponse);

      const result = await WebhookService.testWebhook(mockWebhookId, mockUserId);

      expect(result).toEqual({
        success: true,
        status: 200,
        responseTime: expect.any(Number),
      });

      expect(axios.post).toHaveBeenCalledWith(
        mockWebhook.url,
        expect.objectContaining({
          event: 'webhook.test',
          data: expect.objectContaining({
            message: 'This is a test webhook from Sunday.com',
          }),
        }),
        expect.objectContaining({
          headers: expect.objectContaining({
            'X-Webhook-Test': 'true',
          }),
        })
      );
    });

    it('should handle test webhook failure', async () => {
      const mockWebhook = {
        id: mockWebhookId,
        url: 'https://example.com/webhook',
        secret: 'webhook-secret',
        organizationId: 'org-1',
      };

      const mockError = new Error('Connection refused');

      (prisma.webhook.findUnique as jest.Mock).mockResolvedValue(mockWebhook);
      (prisma.organizationMember.findUnique as jest.Mock).mockResolvedValue({
        organizationId: mockWebhook.organizationId,
        userId: mockUserId,
        role: 'admin',
      });

      (crypto.randomUUID as jest.Mock).mockReturnValue('test-delivery-1');
      (crypto.createHmac as jest.Mock).mockReturnValue({
        update: jest.fn().mockReturnThis(),
        digest: jest.fn().mockReturnValue('test-signature'),
      });

      (axios.post as jest.Mock).mockRejectedValue(mockError);

      const result = await WebhookService.testWebhook(mockWebhookId, mockUserId);

      expect(result).toEqual({
        success: false,
        error: 'Connection refused',
        responseTime: expect.any(Number),
      });
    });
  });

  describe('triggerEvent', () => {
    const mockEvent = {
      type: 'item.created',
      data: {
        itemId: 'item-1',
        boardId: 'board-1',
        organizationId: 'org-1',
      },
      timestamp: new Date(),
    };

    it('should trigger webhooks for relevant subscriptions', async () => {
      const mockWebhooks = [
        {
          id: 'webhook-1',
          url: 'https://example1.com/webhook',
          secret: 'secret1',
          events: ['item.created'],
          organizationId: 'org-1',
        },
        {
          id: 'webhook-2',
          url: 'https://example2.com/webhook',
          secret: 'secret2',
          events: ['item.created', 'item.updated'],
          organizationId: 'org-1',
        },
      ];

      (prisma.webhook.findMany as jest.Mock).mockResolvedValue(mockWebhooks);

      // Mock successful delivery for both webhooks
      jest.spyOn(WebhookService, 'deliverWebhook').mockResolvedValue();

      await WebhookService.triggerEvent(mockEvent);

      expect(prisma.webhook.findMany).toHaveBeenCalledWith({
        where: expect.objectContaining({
          isActive: true,
          deletedAt: null,
          events: { has: mockEvent.type },
          organizationId: mockEvent.data.organizationId,
        }),
      });

      expect(WebhookService.deliverWebhook).toHaveBeenCalledTimes(2);
      expect(WebhookService.deliverWebhook).toHaveBeenCalledWith(mockWebhooks[0], mockEvent);
      expect(WebhookService.deliverWebhook).toHaveBeenCalledWith(mockWebhooks[1], mockEvent);
    });

    it('should handle delivery failures gracefully', async () => {
      const mockWebhooks = [
        {
          id: 'webhook-1',
          url: 'https://example.com/webhook',
          secret: 'secret1',
          events: ['item.created'],
          organizationId: 'org-1',
        },
      ];

      (prisma.webhook.findMany as jest.Mock).mockResolvedValue(mockWebhooks);

      // Mock delivery failure
      jest.spyOn(WebhookService, 'deliverWebhook').mockRejectedValue(new Error('Delivery failed'));

      // Should not throw error
      await expect(WebhookService.triggerEvent(mockEvent)).resolves.not.toThrow();
    });
  });
});