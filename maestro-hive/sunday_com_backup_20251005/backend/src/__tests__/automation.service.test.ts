import { prismaMock } from './setup';
import { AutomationService } from '@/services/automation.service';
import { RedisService } from '@/config/redis';

// Mock Redis
jest.mock('@/config/redis', () => ({
  RedisService: {
    getCache: jest.fn(),
    setCache: jest.fn(),
    deleteCache: jest.fn(),
    deleteCachePattern: jest.fn(),
  },
}));

// Mock Socket.io
jest.mock('@/server', () => ({
  io: {
    to: jest.fn(() => ({
      emit: jest.fn(),
    })),
    in: jest.fn(() => ({
      fetchSockets: jest.fn(() => Promise.resolve([])),
    })),
  },
}));

describe('AutomationService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('createRule', () => {
    it('should create automation rule successfully', async () => {
      const mockRule = {
        id: 'rule-1',
        name: 'Auto-assign urgent items',
        description: 'Automatically assign urgent items to team lead',
        trigger: {
          type: 'item_created',
          conditions: { priority: 'high' },
        },
        conditions: { priority: { equals: 'urgent' } },
        actions: [
          {
            type: 'assign_item',
            parameters: { userId: 'team-lead-id' },
          },
        ],
        isEnabled: true,
        organizationId: 'org-1',
        boardId: 'board-1',
        createdBy: 'user-1',
        createdAt: new Date(),
        updatedAt: new Date(),
        deletedAt: null,
      };

      prismaMock.automationRule.create.mockResolvedValue(mockRule as any);

      const ruleData = {
        name: 'Auto-assign urgent items',
        description: 'Automatically assign urgent items to team lead',
        trigger: {
          type: 'item_created',
          conditions: { priority: 'high' },
        },
        conditions: { priority: { equals: 'urgent' } },
        actions: [
          {
            type: 'assign_item',
            parameters: { userId: 'team-lead-id' },
          },
        ],
        isEnabled: true,
      };

      const result = await AutomationService.createRule(
        ruleData,
        'user-1',
        'org-1',
        'board-1'
      );

      expect(result).toEqual(mockRule);
      expect(prismaMock.automationRule.create).toHaveBeenCalledWith({
        data: {
          name: ruleData.name,
          description: ruleData.description,
          trigger: ruleData.trigger,
          conditions: ruleData.conditions,
          actions: ruleData.actions,
          isEnabled: true,
          createdBy: 'user-1',
          organizationId: 'org-1',
          boardId: 'board-1',
        },
      });
    });

    it('should validate rule configuration', async () => {
      const invalidRuleData = {
        name: 'Invalid rule',
        trigger: {
          type: 'item_created',
          // Missing conditions
        },
        actions: [], // Empty actions array
      };

      await expect(
        AutomationService.createRule(invalidRuleData as any, 'user-1', 'org-1')
      ).rejects.toThrow('At least one action is required');
    });
  });

  describe('updateRule', () => {
    it('should update automation rule successfully', async () => {
      const mockUpdatedRule = {
        id: 'rule-1',
        name: 'Updated rule name',
        isEnabled: false,
        updatedAt: new Date(),
      };

      prismaMock.automationRule.update.mockResolvedValue(mockUpdatedRule as any);

      const updates = {
        name: 'Updated rule name',
        isEnabled: false,
      };

      const result = await AutomationService.updateRule('rule-1', updates, 'user-1');

      expect(result).toEqual(mockUpdatedRule);
      expect(prismaMock.automationRule.update).toHaveBeenCalledWith({
        where: { id: 'rule-1' },
        data: {
          name: 'Updated rule name',
          isEnabled: false,
          updatedAt: expect.any(Date),
        },
      });
    });
  });

  describe('deleteRule', () => {
    it('should soft delete automation rule', async () => {
      prismaMock.automationRule.update.mockResolvedValue({} as any);

      await AutomationService.deleteRule('rule-1', 'user-1');

      expect(prismaMock.automationRule.update).toHaveBeenCalledWith({
        where: { id: 'rule-1' },
        data: { deletedAt: expect.any(Date) },
      });
    });
  });

  describe('getRules', () => {
    it('should get automation rules for organization', async () => {
      const mockRules = [
        {
          id: 'rule-1',
          name: 'Rule 1',
          isEnabled: true,
          organizationId: 'org-1',
          boardId: null,
        },
        {
          id: 'rule-2',
          name: 'Rule 2',
          isEnabled: true,
          organizationId: 'org-1',
          boardId: 'board-1',
        },
      ];

      prismaMock.automationRule.findMany.mockResolvedValue(mockRules as any);

      const result = await AutomationService.getRules('org-1');

      expect(result).toEqual(mockRules);
      expect(prismaMock.automationRule.findMany).toHaveBeenCalledWith({
        where: {
          organizationId: 'org-1',
          deletedAt: null,
          isEnabled: true,
        },
        orderBy: { createdAt: 'desc' },
      });
    });

    it('should filter rules by board when provided', async () => {
      const mockRules = [
        {
          id: 'rule-2',
          name: 'Board Rule',
          isEnabled: true,
          organizationId: 'org-1',
          boardId: 'board-1',
        },
      ];

      prismaMock.automationRule.findMany.mockResolvedValue(mockRules as any);

      const result = await AutomationService.getRules('org-1', 'board-1');

      expect(result).toEqual(mockRules);
      expect(prismaMock.automationRule.findMany).toHaveBeenCalledWith({
        where: {
          organizationId: 'org-1',
          boardId: 'board-1',
          deletedAt: null,
          isEnabled: true,
        },
        orderBy: { createdAt: 'desc' },
      });
    });
  });

  describe('executeTrigger', () => {
    beforeEach(() => {
      (RedisService.getCache as jest.Mock).mockResolvedValue('0');
      (RedisService.setCache as jest.Mock).mockResolvedValue(undefined);
    });

    it('should execute matching automation rules', async () => {
      const mockRule = {
        id: 'rule-1',
        name: 'Status Change Rule',
        trigger: {
          type: 'item_updated',
          conditions: {},
        },
        conditions: {
          status: { equals: 'done' },
        },
        actions: [
          {
            type: 'send_notification',
            parameters: {
              userIds: ['user-1'],
              message: 'Item completed!',
            },
          },
        ],
        organizationId: 'org-1',
        boardId: 'board-1',
      };

      prismaMock.automationRule.findMany.mockResolvedValue([mockRule] as any);
      prismaMock.itemAssignment.create.mockResolvedValue({} as any);
      prismaMock.notification.create.mockResolvedValue({} as any);
      prismaMock.automationExecution.create.mockResolvedValue({} as any);

      const context = {
        entityType: 'item' as const,
        entityId: 'item-1',
        action: 'item_updated',
        userId: 'user-1',
        organizationId: 'org-1',
        boardId: 'board-1',
        oldValues: { status: 'in_progress' },
        newValues: { status: 'done' },
      };

      await AutomationService.executeTrigger(context);

      expect(prismaMock.automationRule.findMany).toHaveBeenCalled();
      expect(prismaMock.automationExecution.create).toHaveBeenCalled();
    });

    it('should respect rate limiting', async () => {
      (RedisService.getCache as jest.Mock).mockResolvedValue('100'); // Over limit

      const context = {
        entityType: 'item' as const,
        entityId: 'item-1',
        action: 'item_updated',
        userId: 'user-1',
        organizationId: 'org-1',
      };

      await AutomationService.executeTrigger(context);

      expect(prismaMock.automationRule.findMany).not.toHaveBeenCalled();
    });

    it('should not execute when no rules match', async () => {
      prismaMock.automationRule.findMany.mockResolvedValue([]);

      const context = {
        entityType: 'item' as const,
        entityId: 'item-1',
        action: 'item_updated',
        userId: 'user-1',
        organizationId: 'org-1',
      };

      await AutomationService.executeTrigger(context);

      expect(prismaMock.automationExecution.create).not.toHaveBeenCalled();
    });
  });

  describe('testRule', () => {
    it('should test rule without executing actions', async () => {
      const mockRule = {
        id: 'rule-1',
        trigger: {
          type: 'item_created',
          conditions: {},
        },
        conditions: {
          priority: { equals: 'high' },
        },
        actions: [
          {
            type: 'assign_item',
            parameters: { userId: 'user-1' },
          },
        ],
      };

      prismaMock.automationRule.findUnique.mockResolvedValue(mockRule as any);

      const testContext = {
        entityType: 'item' as const,
        entityId: 'item-1',
        action: 'item_created',
        userId: 'user-1',
        organizationId: 'org-1',
        newValues: { priority: 'high' },
      };

      const result = await AutomationService.testRule('rule-1', testContext);

      expect(result).toMatchObject({
        triggered: true,
        conditionResults: {
          priority: true,
        },
        simulatedActions: [
          {
            type: 'assign_item',
            parameters: { userId: 'user-1' },
            wouldExecute: true,
          },
        ],
      });
    });

    it('should return false for non-matching conditions', async () => {
      const mockRule = {
        id: 'rule-1',
        trigger: {
          type: 'item_created',
          conditions: {},
        },
        conditions: {
          priority: { equals: 'high' },
        },
        actions: [
          {
            type: 'assign_item',
            parameters: { userId: 'user-1' },
          },
        ],
      };

      prismaMock.automationRule.findUnique.mockResolvedValue(mockRule as any);

      const testContext = {
        entityType: 'item' as const,
        entityId: 'item-1',
        action: 'item_created',
        userId: 'user-1',
        organizationId: 'org-1',
        newValues: { priority: 'low' }, // Different priority
      };

      const result = await AutomationService.testRule('rule-1', testContext);

      expect(result).toMatchObject({
        triggered: true,
        conditionResults: {
          priority: false,
        },
        simulatedActions: [
          {
            type: 'assign_item',
            parameters: { userId: 'user-1' },
            wouldExecute: false,
          },
        ],
      });
    });

    it('should throw error when rule not found', async () => {
      prismaMock.automationRule.findUnique.mockResolvedValue(null);

      const testContext = {
        entityType: 'item' as const,
        entityId: 'item-1',
        action: 'item_created',
        userId: 'user-1',
        organizationId: 'org-1',
      };

      await expect(
        AutomationService.testRule('nonexistent-rule', testContext)
      ).rejects.toThrow('Automation rule not found');
    });
  });

  describe('getExecutionHistory', () => {
    it('should get execution history for organization', async () => {
      const mockExecutions = [
        {
          ruleId: 'rule-1',
          organizationId: 'org-1',
          triggeredBy: {
            entityType: 'item',
            entityId: 'item-1',
            action: 'item_created',
            userId: 'user-1',
          },
          executedActions: [
            {
              type: 'assign_item',
              success: true,
              result: { assignedTo: 'user-2' },
            },
          ],
          executedAt: new Date(),
        },
      ];

      prismaMock.automationExecution.findMany.mockResolvedValue(mockExecutions as any);

      const result = await AutomationService.getExecutionHistory('org-1');

      expect(result).toHaveLength(1);
      expect(result[0]).toMatchObject({
        ruleId: 'rule-1',
        triggeredBy: expect.any(Object),
        executedActions: expect.any(Array),
      });
    });

    it('should filter by rule ID when provided', async () => {
      prismaMock.automationExecution.findMany.mockResolvedValue([]);

      await AutomationService.getExecutionHistory('org-1', 'rule-1', 25);

      expect(prismaMock.automationExecution.findMany).toHaveBeenCalledWith({
        where: {
          organizationId: 'org-1',
          ruleId: 'rule-1',
        },
        orderBy: { executedAt: 'desc' },
        take: 25,
      });
    });
  });
});